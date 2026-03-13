"""
ME17Suite — Signature-Based Map Finder
Bosch ME17.8.5 by Rotax (Sea-Doo 300 / TC1762)

Sve potvrdjene mape (CODE regija 0x010000-0x05FFFF):

  RPM osa   (3× mirror)  @ 0x024F46 / 0x025010 / 0x0250DC   BE u16, 1×16
  Rev limit (5 lokacija) @ 0x022096, 0x0220B6, 0x0220C0,
                           0x02B72A, 0x02B73E                 LE u16, scalar
  Ignition  (16 mapa)    @ 0x02B730, stride 144B              u8, 12×12, 0.75°/bit
  Injection main+mirror  @ 0x02439C / 0x02451C (+0x180)      LE u16, 12×32
  Torque    main+mirror  @ 0x02A0D8 / 0x02A5F0 (+0x518)      BE u16, 16×16, Q8
  Lambda    main+mirror  @ 0x0266F0 / 0x026C08 (+0x518)      LE u16, 12×18, Q15

Napomene:
  - CAL regija (0x060000+) je TriCore bytekod — ne pisati!
  - Sve mape su iskljucivo u CODE regiji.
  - Ignition osi (RPM × Load) jos nisu identificirane.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable

from .engine import ME17Engine, CAL_START, CAL_END, CODE_START, CODE_END


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class AxisDef:
    count:      int
    byte_order: str    # "BE" | "LE"
    dtype:      str    # "u16" | "u8"
    scale:      float = 1.0
    unit:       str   = ""
    values:     list  = None   # poznate vrijednosti ose (None = nepoznate)


@dataclass
class MapDef:
    name:          str
    description:   str
    category:      str     # "ignition"|"injection"|"torque"|"lambda"|"rpm_limiter"|"axis"|"misc"
    rows:          int
    cols:          int
    byte_order:    str   = "BE"
    dtype:         str   = "u16"   # "u8" | "u16" | "i16"
    scale:         float = 1.0
    offset_val:    float = 0.0
    unit:          str   = ""
    axis_x:        Optional[AxisDef] = None
    axis_y:        Optional[AxisDef] = None
    raw_min:       int   = 0
    raw_max:       int   = 0xFFFF
    mirror_offset: int   = 0       # bajtova od pocetka do mirror kopije (0 = nema)
    notes:         str   = ""

    @property
    def cell_bytes(self) -> int:
        """Velicina jedne celije u bajtovima."""
        return 1 if self.dtype == "u8" else 2

    @property
    def total_bytes(self) -> int:
        return self.rows * self.cols * self.cell_bytes


@dataclass
class FoundMap:
    defn:    MapDef
    address: int
    sw_id:   str
    data:    list[int]   # sirove (raw) vrijednosti, flat lista

    @property
    def display_values(self) -> list[float]:
        if self.defn.scale == 0.0:
            return [float(v) for v in self.data]
        return [v * self.defn.scale + self.defn.offset_val for v in self.data]

    def get_2d_raw(self) -> list[list[int]]:
        c = self.defn.cols
        return [self.data[i*c:(i+1)*c] for i in range(self.defn.rows)]

    def get_2d_display(self) -> list[list[float]]:
        vals = self.display_values
        c = self.defn.cols
        return [vals[i*c:(i+1)*c] for i in range(self.defn.rows)]


# ─── Poznate RPM ose ──────────────────────────────────────────────────────────

# Prvih 12 od 16 tocaka RPM ose — koristimo za ignition (12×12)
_RPM_12 = [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 4608, 5120, 6144, 8448]

# Svih 16 tocaka — za torque (16×16)
_RPM_16 = [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096,
           4608, 5120, 5632, 6144, 6656, 7168, 7680, 8448]

_RPM_AXIS_12 = AxisDef(count=12, byte_order="BE", dtype="u16",
                        scale=1.0, unit="rpm", values=_RPM_12)
_RPM_AXIS_16 = AxisDef(count=16, byte_order="BE", dtype="u16",
                        scale=1.0, unit="rpm", values=_RPM_16)


# ─── RPM osa definicija ───────────────────────────────────────────────────────

_RPM_SIG = bytes([0x02,0x00, 0x04,0x00, 0x06,0x00,
                  0x08,0x00, 0x0A,0x00, 0x0C,0x00])

_RPM_AXIS_DEF = MapDef(
    name        = "rpm_axis",
    description = "RPM osa — 16 tacaka, 512–8448 rpm (3× mirror)",
    category    = "axis",
    rows=1, cols=16,
    byte_order  = "BE", dtype = "u16",
    scale       = 1.0, unit = "rpm",
    raw_min     = 256, raw_max = 9000,
    notes       = "Potvrdjeno: ORI @ 0x024F46 / 0x025010 / 0x0250DC",
)


# ─── Rev limiter ─────────────────────────────────────────────────────────────

_REV_SCALAR_DEF = MapDef(
    name        = "rev_limiter_scalar",
    description = "Rev limiter — individualni prag (scalar u16 LE)",
    category    = "rpm_limiter",
    rows=1, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, unit = "rpm",
    raw_min     = 4000, raw_max = 13000,
    notes       = "Potvrdjene lokacije: 0x022096, 0x0220B6, 0x0220C0, 0x02B72A, 0x02B73E",
)

# 5 poznatih adresa rev limitera
_REV_KNOWN_ADDRS = [0x022096, 0x0220B6, 0x0220C0, 0x02B72A, 0x02B73E]

_REV_LIMIT_HEUR = MapDef(
    name        = "rev_limiter_table",
    description = "Rev limiter tabela — soft/mid/hard pragovi, stride 0x18",
    category    = "rpm_limiter",
    rows=1, cols=3,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, unit = "rpm",
    raw_min     = 4000, raw_max = 13000,
    notes       = "Heuristicki scan: stride 0x18, soft<mid<hard",
)


# ─── Ignition mape ────────────────────────────────────────────────────────────

IGN_BASE   = 0x02B730
IGN_STRIDE = 144          # 12 × 12 × 1 bajt (u8)
IGN_COUNT  = 16

# Pretpostavljeni nazivi (3 cilindra × 5 uvjeta + 1 global)
# Redoslijed ce biti potvrđen analizom podataka
_IGN_NAMES = [
    "ign_cyl1_normal",  # 0
    "ign_cyl2_normal",  # 1
    "ign_cyl3_normal",  # 2
    "ign_cyl1_hot",     # 3
    "ign_cyl2_hot",     # 4
    "ign_cyl3_hot",     # 5
    "ign_cyl1_knock",   # 6
    "ign_cyl2_knock",   # 7
    "ign_cyl3_knock",   # 8
    "ign_cyl1_decel",   # 9
    "ign_cyl2_decel",   # 10
    "ign_cyl3_decel",   # 11
    "ign_enrich_1",     # 12
    "ign_enrich_2",     # 13
    "ign_enrich_3",     # 14
    "ign_global",       # 15
]

def _make_ign_def(idx: int) -> MapDef:
    addr = IGN_BASE + idx * IGN_STRIDE
    return MapDef(
        name         = _IGN_NAMES[idx],
        description  = f"Ignition map #{idx:02d} — {_IGN_NAMES[idx]} @ 0x{addr:06X}",
        category     = "ignition",
        rows=12, cols=12,
        byte_order   = "BE",    # single byte, endian nebitan
        dtype        = "u8",
        scale        = 0.75,    # °/bit
        offset_val   = 0.0,
        unit         = "°BTDC",
        axis_x       = _RPM_AXIS_12,
        axis_y       = None,    # Load osa nepoznata
        raw_min      = 16,      # 12° BTDC minimum
        raw_max      = 56,      # 42° BTDC maksimum (sigurnosni limit)
        mirror_offset= 0,
        notes        = (
            f"Ignition mapa #{idx:02d}. "
            "Scale: 0.75°/bit (raw 34 = 25.5° BTDC). "
            "ORI: 24–33.75°, STG2: 25.5–36.75°. "
            "Load osa nije identificirana — vjerovatno MAP% ili mg/stroke."
        ),
    )

_IGN_DEFS = [_make_ign_def(i) for i in range(IGN_COUNT)]


# ─── Injection mapa ───────────────────────────────────────────────────────────

INJ_MAIN          = 0x02439C
INJ_MIRROR        = 0x02451C
INJ_MIRROR_OFFSET = INJ_MIRROR - INJ_MAIN   # 0x180

_INJ_DEF = MapDef(
    name          = "injection_duration",
    description   = "Injection duration mapa — trajanje ubrizgavanja, 12×32 u16 LE",
    category      = "injection",
    rows=12, cols=32,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw",      # fizikalna jedinica nepoznata (μs ili 0.1μs)
    axis_x        = None,       # 32 stupca — os nepoznata
    axis_y        = None,       # 12 redova — os nepoznata
    raw_min       = 0,
    raw_max       = 0xFFFF,
    mirror_offset = INJ_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{INJ_MAIN:06X}, mirror @ 0x{INJ_MIRROR:06X} (+0x{INJ_MIRROR_OFFSET:X}). "
        "ORI max ~49151, STG2 max 65535 (saturirano — agresivan tune). "
        "Fizikalna jedinica nepoznata bez A2L fajla (vjerovatno μs ili 0.1μs)."
    ),
)


# ─── Torque mapa ─────────────────────────────────────────────────────────────

_TORQUE_DEF = MapDef(
    name          = "torque_efficiency",
    description   = "Torque efficiency — faktor momenta 16×16, Q8 BE (0x80=100%)",
    category      = "torque",
    rows=16, cols=16,
    byte_order    = "BE", dtype = "u16",
    scale         = 1.0 / 128.0,
    offset_val    = 0.0,
    unit          = "factor",
    axis_x        = _RPM_AXIS_16,
    axis_y        = None,
    raw_min       = 80,
    raw_max       = 200,
    mirror_offset = 0x518,
    notes         = (
        "Main @ 0x02A0D8, mirror @ 0x02A5F0 (+0x518). "
        "LSB uvijek 0x00 — podatak je u MSB bajtu. "
        "0x80=128=1.0=100%, ORI: 93–120%, STG2: 93–123%."
    ),
)


# ─── Lambda mapa ─────────────────────────────────────────────────────────────

LAM_MAIN          = 0x0266F0
LAM_MIRROR        = 0x026C08
LAM_MIRROR_OFFSET = LAM_MIRROR - LAM_MAIN   # 0x518

_LAMBDA_DEF = MapDef(
    name          = "lambda_correction",
    description   = "Lambda correction mapa — AFR korekcija 12×18, Q15 LE",
    category      = "lambda",
    rows=12, cols=18,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,   # Q15: 32768 = 1.0 (λ=1.0 = stoichiometric)
    offset_val    = 0.0,
    unit          = "λ",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 16384,    # λ = 0.5 (bogat limit)
    raw_max       = 65535,    # λ ≈ 2.0 (siromasan limit)
    mirror_offset = LAM_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{LAM_MAIN:06X}, mirror @ 0x{LAM_MIRROR:06X} (+0x{LAM_MIRROR_OFFSET:X}). "
        "Q15 format: raw / 32768 = lambda faktor. "
        "32768 = λ1.0 (stoichiometric), tipicni opseg 0.8–1.2."
    ),
)


# ─── Scanner ──────────────────────────────────────────────────────────────────

class MapFinder:
    """
    Pronalazi i validira sve poznate mape u ME17.8.5 binarnom fajlu.

    Strategije:
      1. Known-address scan  — ignition, injection, torque, lambda, rev scalars
      2. Signature scan      — RPM ose (pattern matching)
      3. Heuristic scan      — rev limiter tabele (stride-0x18 pattern)
    """

    def __init__(self, engine: ME17Engine):
        self.eng = engine
        self.results: list[FoundMap] = []

    def find_all(self, progress_cb: Optional[Callable] = None) -> list[FoundMap]:
        self.results = []
        self._scan_rpm_axes(progress_cb)
        self._scan_rev_limiter_known(progress_cb)
        self._scan_rev_limiter_heuristic(progress_cb)
        self._scan_ignition(progress_cb)
        self._scan_injection(progress_cb)
        self._scan_torque(progress_cb)
        self._scan_lambda(progress_cb)
        return self.results

    # ── RPM Axis scan ─────────────────────────────────────────────────────────

    def _scan_rpm_axes(self, cb=None):
        if cb: cb("Trazim RPM ose...")
        data = self.eng.get_bytes()
        found = []

        for i in range(CODE_START, CODE_END - len(_RPM_SIG), 2):
            if data[i:i+len(_RPM_SIG)] == _RPM_SIG:
                vals = [int.from_bytes(data[i+j*2:i+j*2+2], 'big') for j in range(16)]
                if self._monotone(vals) and vals[-1] < 10000:
                    found.append(i)
                    self.results.append(FoundMap(
                        defn    = _RPM_AXIS_DEF,
                        address = i,
                        sw_id   = self._sw(),
                        data    = vals,
                    ))

        if cb: cb(f"  RPM ose: {len(found)} pronadjene @ {[f'0x{a:06X}' for a in found]}")

    # ── Rev limiter — poznate adrese ──────────────────────────────────────────

    def _scan_rev_limiter_known(self, cb=None):
        if cb: cb("Trazim rev limiter (poznate adrese)...")
        data = self.eng.get_bytes()
        found = []

        for addr in _REV_KNOWN_ADDRS:
            if addr + 2 > len(data):
                continue
            val = int.from_bytes(data[addr:addr+2], 'little')
            if 4000 <= val <= 13000:
                defn = MapDef(
                    name          = f"rev_lim_0x{addr:06X}",
                    description   = f"Rev limiter scalar @ 0x{addr:06X} = {val} rpm",
                    category      = "rpm_limiter",
                    rows=1, cols=1,
                    byte_order    = "LE", dtype = "u16",
                    scale         = 1.0, unit = "rpm",
                    raw_min       = 4000, raw_max = 13000,
                    notes         = _REV_SCALAR_DEF.notes,
                )
                self.results.append(FoundMap(
                    defn    = defn,
                    address = addr,
                    sw_id   = self._sw(),
                    data    = [val],
                ))
                found.append((addr, val))

        if cb:
            cb(f"  Rev scalars: {len(found)} @ {[f'0x{a:06X}={v}rpm' for a,v in found]}")

    # ── Rev limiter — heuristicki scan ────────────────────────────────────────

    def _scan_rev_limiter_heuristic(self, cb=None):
        if cb: cb("Trazim rev limiter tabele (heuristika)...")
        data = self.eng.get_bytes()

        SOFT_MIN, SOFT_MAX = 5000, 9500
        MID_MIN,  MID_MAX  = 7000, 11000
        HARD_MIN, HARD_MAX = 9000, 13000
        STRIDE = 0x18
        MIN_STEP = 200    # minimalna razlika izmedju pragova

        candidates = []
        for base in range(CODE_START, CODE_END - STRIDE * 2, 2):
            s = int.from_bytes(data[base:base+2],                    'little')
            m = int.from_bytes(data[base+STRIDE:base+STRIDE+2],     'little')
            h = int.from_bytes(data[base+STRIDE*2:base+STRIDE*2+2], 'little')

            if (SOFT_MIN <= s <= SOFT_MAX and
                MID_MIN  <= m <= MID_MAX  and
                HARD_MIN <= h <= HARD_MAX and
                m - s >= MIN_STEP and
                h - m >= MIN_STEP and
                # Susjedni bajtovi moraju biti nula (alignment provjera)
                data[base+2] == 0 and data[base+3] == 0):
                candidates.append((base, [s, m, h]))

        # Dedupliciraj — uzmi samo prvi u grupi unutar 8B
        deduped = []
        last = -999
        for base, vals in candidates:
            if base - last > 8:
                deduped.append((base, vals))
                last = base

        if cb: cb(f"  Rev tabele: {len(deduped)} @ {[f'0x{a:06X}' for a,_ in deduped[:5]]}")

        for base, vals in deduped[:5]:
            defn = MapDef(
                name          = f"rev_table_0x{base:06X}",
                description   = f"Rev limiter tabela @ 0x{base:06X} (soft/mid/hard)",
                category      = "rpm_limiter",
                rows=1, cols=3,
                byte_order    = "LE", dtype = "u16",
                scale         = 1.0, unit = "rpm",
                raw_min       = 4000, raw_max = 13000,
                notes         = "Heuristicki scan, stride 0x18: [soft, mid, hard]",
            )
            self.results.append(FoundMap(
                defn    = defn,
                address = base,
                sw_id   = self._sw(),
                data    = vals,
            ))

    # ── Ignition scan ─────────────────────────────────────────────────────────

    def _scan_ignition(self, cb=None):
        if cb: cb("Trazim ignition mape...")
        data = self.eng.get_bytes()
        found = 0

        for idx in range(IGN_COUNT):
            addr = IGN_BASE + idx * IGN_STRIDE
            if addr + IGN_STRIDE > len(data):
                continue

            raw = list(data[addr:addr + IGN_STRIDE])

            # Validacija: sve vrijednosti u fizikalnom opsegu (12°–42° BTDC)
            if not all(16 <= v <= 58 for v in raw):
                if cb: cb(f"  Ignition #{idx:02d} @ 0x{addr:06X}: validacija pala — preskacam")
                continue

            # Mora biti nekakva varijacija (nije sve ista vrijednost)
            if max(raw) - min(raw) < 2:
                if cb: cb(f"  Ignition #{idx:02d} @ 0x{addr:06X}: nema varijacije — preskacam")
                continue

            self.results.append(FoundMap(
                defn    = _IGN_DEFS[idx],
                address = addr,
                sw_id   = self._sw(),
                data    = raw,
            ))
            found += 1
            if cb: cb(f"  Ignition #{idx:02d} {_IGN_NAMES[idx]:20s} @ 0x{addr:06X}"
                      f"  raw=[{min(raw)}–{max(raw)}]"
                      f"  ({min(raw)*0.75:.1f}°–{max(raw)*0.75:.1f}°BTDC)")

        if cb: cb(f"  Ignition: {found}/{IGN_COUNT} mapa pronadjeno")

    # ── Injection scan ────────────────────────────────────────────────────────

    def _scan_injection(self, cb=None):
        if cb: cb("Trazim injection mapu...")
        data = self.eng.get_bytes()

        addr = INJ_MAIN
        n    = _INJ_DEF.rows * _INJ_DEF.cols   # 12 × 32 = 384
        size = n * 2                             # u16 LE = 2 bajta

        if addr + size > len(data):
            if cb: cb("  Injection: adresa van granica fajla")
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: mora imati vrijednosti, ne smije biti sve nule
        non_zero = sum(1 for v in vals if v > 0)
        if non_zero < n // 4:
            if cb: cb(f"  Injection @ 0x{addr:06X}: previse nula ({non_zero}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _INJ_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Injection @ 0x{addr:06X}  12×32  raw=[{min(vals)}–{max(vals)}]"
                  f"  mirror @ 0x{INJ_MIRROR:06X}")

    # ── Torque scan ───────────────────────────────────────────────────────────

    def _scan_torque(self, cb=None):
        if cb: cb("Trazim torque efficiency mapu...")
        data = self.eng.get_bytes()

        for addr in [0x02A0D8, 0x02A5F0]:
            n = 256  # 16 × 16
            if addr + n * 2 > len(data):
                continue

            valid = True
            vals  = []
            for i in range(n):
                o  = addr + i * 2
                hi = data[o]
                lo = data[o + 1]
                if lo != 0x00:
                    valid = False; break
                if not (80 <= hi <= 210):
                    valid = False; break
                vals.append((hi << 8) | lo)

            if not valid:
                continue

            self.results.append(FoundMap(
                defn    = _TORQUE_DEF,
                address = addr,
                sw_id   = self._sw(),
                data    = vals,
            ))
            if cb: cb(f"  Torque @ 0x{addr:06X}  16×16  MSB=[{min(v>>8 for v in vals)}–{max(v>>8 for v in vals)}]")

    # ── Lambda scan ───────────────────────────────────────────────────────────

    def _scan_lambda(self, cb=None):
        if cb: cb("Trazim lambda mapu...")
        data = self.eng.get_bytes()

        addr = LAM_MAIN
        n    = _LAMBDA_DEF.rows * _LAMBDA_DEF.cols   # 12 × 18 = 216
        size = n * 2

        if addr + size > len(data):
            if cb: cb("  Lambda: adresa van granica fajla")
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: Q15 lambda vrijednosti trebaju biti u razumnom opsegu
        # λ 0.5–2.0 → raw 16384–65535
        non_zero = sum(1 for v in vals if v > 100)
        if non_zero < n // 2:
            if cb: cb(f"  Lambda @ 0x{addr:06X}: previse nula — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _LAMBDA_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))

        disp_min = min(vals) / 32768.0
        disp_max = max(vals) / 32768.0
        if cb: cb(f"  Lambda @ 0x{addr:06X}  12x18  lam=[{disp_min:.3f}-{disp_max:.3f}]"
                  f"  mirror @ 0x{LAM_MIRROR:06X}")

    # ── Diff-guided scanner ───────────────────────────────────────────────────

    def find_changed_regions(self, other: ME17Engine, min_block: int = 32) -> list[dict]:
        """Usporedi dva fajla i vrati listu promijenjenih blokova."""
        diffs = self.eng.diff(other)
        if not diffs:
            return []

        blocks = []
        start = diffs[0][0]
        prev  = start

        for addr, _, _ in diffs[1:]:
            if addr - prev > 16:
                if prev - start >= min_block:
                    blocks.append({
                        "start":   start,
                        "end":     prev,
                        "size":    prev - start + 1,
                        "in_cal":  CAL_START <= start <= CAL_END,
                        "in_code": CODE_START <= start <= CODE_END,
                    })
                start = addr
            prev = addr

        if prev - start >= min_block:
            blocks.append({
                "start":   start,
                "end":     prev,
                "size":    prev - start + 1,
                "in_cal":  CAL_START <= start <= CAL_END,
                "in_code": CODE_START <= start <= CODE_END,
            })

        return blocks

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sw(self) -> str:
        return self.eng.info.sw_id if self.eng.info else "?"

    @staticmethod
    def _monotone(vals: list[int]) -> bool:
        return all(vals[i] <= vals[i+1] for i in range(len(vals)-1))
