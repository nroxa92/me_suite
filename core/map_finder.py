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

# Osa opterecenja — pretpostavlja se MAP% ili mg/stroke (12 tocaka, nepoznate vrijednosti)
# Za Rotax ACE 1630 s superchargerom: MAP > 100% je moguc (boost)
# Za tocne vrijednosti potreban je A2L/ASAP2 fajl
_LOAD_AXIS_12 = AxisDef(count=12, byte_order="BE", dtype="u16",
                         scale=1.0, unit="%MAP", values=None)  # vrijednosti nepoznate


# ─── RPM osa definicija ───────────────────────────────────────────────────────

_RPM_SIG = bytes([0x02,0x00, 0x04,0x00, 0x06,0x00,
                  0x08,0x00, 0x0A,0x00, 0x0C,0x00])

_RPM_AXIS_DEF = MapDef(
    name        = "RPM osa (globalna)",
    description = (
        "Globalna RPM osa za sve 2D mape — 16 tocaka, 512–8448 rpm. "
        "Promjena ove ose mijenja X-os svih mapa koje je koriste (ignition, torque). "
        "Postoje 3 identicne kopije (mirror) u binarnom fajlu."
    ),
    category    = "axis",
    rows=1, cols=16,
    byte_order  = "BE", dtype = "u16",
    scale       = 1.0, unit = "rpm",
    raw_min     = 256, raw_max = 9000,
    notes       = "Potvrdjeno: 3× mirror @ 0x024F46 / 0x025010 / 0x0250DC",
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

# Nazivi ignition mapa — 16 mapa svakih 144B (12×12 u8, 0.75°/bit):
#   00-07  Osnovna timing mapa (razliciti uvjeti: toplina, load, boost...)
#   08-09  Knock delta/trim — POTVRDJENO: negativni pomaci, manji raspon = retard korekcija
#   10-15  Pomocna mapa (neidentificirana: moguce cold start, decel, overrun)
# VAZNO: uvjeti i redoslijed po cilindru NISU verificirani bez A2L fajla.
_IGN_NAMES = [
    "Paljenje — Osnovna 1",          # 00
    "Paljenje — Osnovna 2",          # 01
    "Paljenje — Osnovna 3",          # 02
    "Paljenje — Osnovna 4",          # 03
    "Paljenje — Osnovna 5",          # 04
    "Paljenje — Osnovna 6",          # 05
    "Paljenje — Osnovna 7",          # 06
    "Paljenje — Osnovna 8",          # 07
    "Paljenje — Knock korekcija 1",  # 08  POTVRDJENO: knock delta/trim mapa
    "Paljenje — Knock korekcija 2",  # 09  POTVRDJENO: knock delta/trim mapa
    "Paljenje — Pomocna 1",          # 10  neidentificirana
    "Paljenje — Pomocna 2",          # 11  neidentificirana
    "Paljenje — Pomocna 3",          # 12  neidentificirana
    "Paljenje — Pomocna 4",          # 13  neidentificirana
    "Paljenje — Pomocna 5",          # 14  neidentificirana
    "Paljenje — Pomocna 6",          # 15  neidentificirana
]

def _make_ign_def(idx: int) -> MapDef:
    addr = IGN_BASE + idx * IGN_STRIDE
    is_knock = idx in (8, 9)
    return MapDef(
        name         = _IGN_NAMES[idx],
        description  = (
            f"Korekcija predpaljenja za knock/detonaciju #{idx-7} — "
            "negativne vrijednosti = kasnjenje (retard). "
            "Automatski se oduzima od osnovne mape pri detekciji detonacije."
            if is_knock else
            f"Kut predpaljenja (timing advance) — mapa #{idx:02d}. "
            "Osi: RPM (x) × opterecenje/MAP (y). "
            "Razlicite mape aktivne su za razlicite uvjete (toplina, boost, stanje motora)."
        ),
        category     = "ignition",
        rows=12, cols=12,
        byte_order   = "BE",
        dtype        = "u8",
        scale        = 0.75,    # 0.75°/bit
        offset_val   = 0.0,
        unit         = "°BTDC" if not is_knock else "°",
        axis_x       = _RPM_AXIS_12,
        axis_y       = _LOAD_AXIS_12,
        raw_min      = 0  if is_knock else 16,
        raw_max      = 40 if is_knock else 56,
        mirror_offset= 0,
        notes        = (
            f"Adresa: 0x{addr:06X}. Scale: 0.75°/bit. "
            + ("KNOCK TRIM: retard delta oduzet od osnove pri detonaciji. " if is_knock else
               "ORI: 24–33.75° BTDC, STG2: do 36.75° BTDC. ")
            + "Os Y: pretpostavljeno MAP/opterecenje, nije verificirano bez A2L."
        ),
    )

_IGN_DEFS = [_make_ign_def(i) for i in range(IGN_COUNT)]


# ─── Injection mapa ───────────────────────────────────────────────────────────

INJ_MAIN          = 0x02439C
INJ_MIRROR        = 0x02451C
INJ_MIRROR_OFFSET = INJ_MIRROR - INJ_MAIN   # 0x180

_INJ_DEF = MapDef(
    name          = "Ubrizgavanje — pulsna sirina",
    description   = (
        "Trajanje ubrizgavanja (pulsna sirina injektora) — 12×32 tablica. "
        "Vece vrijednosti = vise goriva. "
        "Osi: pretpostavljeno RPM (stupci) × opterecenje/MAP (redovi). "
        "ORI max ~49151, STG2 saturiran na 65535 (agresivan tune)."
    ),
    category      = "injection",
    rows=12, cols=32,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw [µs?]",   # fizikalna jedinica nepoznata bez A2L
    axis_x        = None,          # 32 stupca — nepoznata os (vjerojatno RPM prosireniji)
    axis_y        = _LOAD_AXIS_12, # 12 redova — opterecenje/MAP
    raw_min       = 0,
    raw_max       = 0xFFFF,
    mirror_offset = INJ_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{INJ_MAIN:06X}, mirror @ 0x{INJ_MIRROR:06X} (+0x{INJ_MIRROR_OFFSET:X}). "
        "ORI max ~49151, STG2 max 65535. "
        "Fizikalna jedinica nepoznata bez A2L (vjerojatno µs ili 0.1µs). "
        "32 stupca = sirniji RPM raspon od ignition (12 stupaca)."
    ),
)


# ─── Torque mapa ─────────────────────────────────────────────────────────────

_TORQUE_DEF = MapDef(
    name          = "Moment — faktor ogranicenja [%]",
    description   = (
        "Faktor ogranicenja momenta — 16×16 tablica (Q8 format). "
        "ECU mnozi zahtijevani moment s ovim faktorom. "
        "100% = puni moment, <100% = ogranicenje (limp mode, TOPS, toplinski). "
        "Osi: RPM (x) × opterecenje/MAP (y). "
        "Format: raw MSB / 128 = faktor (0x80=1.0=100%)."
    ),
    category      = "torque",
    rows=16, cols=16,
    byte_order    = "BE", dtype = "u16",
    scale         = 1.0 / 128.0,
    offset_val    = 0.0,
    unit          = "%",
    axis_x        = _RPM_AXIS_16,
    axis_y        = _LOAD_AXIS_12,   # 16 redova ali axis def ima 12 — TODO: identificirati
    raw_min       = 80,
    raw_max       = 200,
    mirror_offset = 0x518,
    notes         = (
        "Main @ 0x02A0D8, mirror @ 0x02A5F0 (+0x518). "
        "LSB uvijek 0x00 — podatak samo u MSB. "
        "ORI raspon: 93–120%, STG2: 93–123%. "
        "Povecanje vrijednosti = vise momenta (deaktivacija ogranicenja). "
        "Paziti: TOPS sistem koristi ovu tablicu za zastitu."
    ),
)


# ─── Lambda mapa ─────────────────────────────────────────────────────────────

LAM_MAIN          = 0x0266F0
LAM_MIRROR        = 0x026C08
LAM_MIRROR_OFFSET = LAM_MIRROR - LAM_MAIN   # 0x518

_LAMBDA_DEF = MapDef(
    name          = "Lambda — ciljni AFR (open-loop)",
    description   = (
        "Ciljni lambda faktor za ubrizgavanje — 12×18 tablica (Q15 LE). "
        "Rotax ACE 1630/900 NEMA fizicku lambda sondu — ovo je open-loop AFR cilj "
        "preracunat iz mape (ne iz mjerenja). "
        "lambda < 1.0 = bogata smjesa (vise goriva, hladjenje klipa, puni gas). "
        "lambda > 1.0 = siromasna smjesa (stednja, parcijalno opterecenje). "
        "Osi: RPM (x) × opterecenje/MAP (y)."
    ),
    category      = "lambda",
    rows=12, cols=18,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,   # Q15: 32768 = 1.0
    offset_val    = 0.0,
    unit          = "λ",
    axis_x        = None,    # 18 stupaca — nepoznata os (vise od 12 RPM tocaka)
    axis_y        = _LOAD_AXIS_12,
    raw_min       = 16384,   # λ = 0.50 (max bogato)
    raw_max       = 65535,   # λ = 2.00 (max siromasno)
    mirror_offset = LAM_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{LAM_MAIN:06X}, mirror @ 0x{LAM_MIRROR:06X} (+0x{LAM_MIRROR_OFFSET:X}). "
        "Q15 format: raw / 32768 = lambda. 32768 = λ1.0 (stehiometrijsko). "
        "Tipicni raspon: 0.80 (bogato, puni gas) do 1.05 (malo siromasno, stednja). "
        "NEMA feedback loop — promjena ove mape direktno mijenja AFR."
    ),
)


# ─── DTC definicije ──────────────────────────────────────────────────────────
#
# TODO (Faza 6): adrese ovise o SW verziji — ovo su referentne adrese za ori_300
# (SW 10SW066726). Potrebna provjera na svakom novom fajlu.
#
# Struktura DTC u ME17.8.5:
#   Enable tablica @ ~0x021080: svaki bajt = jedan DTC senzor
#     0x06 = aktivno praćenje, 0x05 = djelomično, 0x04 = samo upozorenje, 0x00 = isključeno
#   DTC code storage (LE u16): dva mjesta (main + mirror)
#
# Referentne adrese (rxpx300_17, SW 10SW066726 — provjereno diff analizom):
#   P1550 enable:  0x02108A (10B)  |  P1550 code: 0x02187E + mirror 0x021BE0
# Verificirane adrese za ori_300:
#   P1550 code @ 0x021888, mirror @ 0x021BEE
#   P0523 code @ 0x02188C, mirror @ 0x021BF2

# P1550 — senzor tlaka punjenja (turbo boost sensor)
_DTC_P1550_ENABLE_ADDR = 0x02108A   # 10B enable flags (zajednicki za vise DTC-ova)
_DTC_P1550_CODE_ADDR   = 0x021888   # 2B LE u16 = 0x1550 (ori_300 adresa)
_DTC_P1550_MIRROR_ADDR = 0x021BEE   # 2B LE u16 mirror (ori_300 adresa)

_DTC_P1550_ENABLE_DEF = MapDef(
    name        = "DTC P1550 — Enable flags",
    description = "Bajti koji kontroliraju nadzor senzora tlaka punjenja (P1550). "
                  "0x06=aktivno, 0x05=djelomično, 0x04=upozorenje, 0x00=isključeno. "
                  "TODO: adresa ovisna o SW verziji — provjeriti za svaki fajl.",
    category    = "dtc",
    rows        = 1,
    cols        = 10,
    byte_order  = "LE",
    dtype       = "u8",
    scale       = 1.0,
    unit        = "",
    notes       = f"Enable @ 0x{_DTC_P1550_ENABLE_ADDR:06X} (10B), "
                  f"code @ 0x{_DTC_P1550_CODE_ADDR:06X}, mirror @ 0x{_DTC_P1550_MIRROR_ADDR:06X}",
)

_DTC_P0523_CODE_ADDR   = 0x02188C   # 2B LE u16 = 0x0523 (ori_300)
_DTC_P0523_MIRROR_ADDR = 0x021BF2   # 2B LE u16 mirror (ori_300)

_DTC_P0523_ENABLE_DEF = MapDef(
    name        = "DTC P0523 — Enable flags",
    description = "Bajti koji kontroliraju nadzor senzora tlaka ulja (P0523). "
                  "0x06=aktivno, 0x05=djelomično, 0x04=upozorenje, 0x00=isključeno. "
                  "TODO: adresa ovisna o SW verziji — provjeriti za svaki fajl.",
    category    = "dtc",
    rows        = 1,
    cols        = 11,
    byte_order  = "LE",
    dtype       = "u8",
    scale       = 1.0,
    unit        = "",
    notes       = f"code @ 0x{_DTC_P0523_CODE_ADDR:06X}, mirror @ 0x{_DTC_P0523_MIRROR_ADDR:06X}",
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
        self._scan_dtc(progress_cb)
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

    # ── DTC scanner ──────────────────────────────────────────────────────────

    def _scan_dtc(self, cb=None):
        """
        Čita DTC enable bajte i kodove iz poznatih adresa.
        TODO (Faza 6): adrese ovise o SW verziji — trenutno kalibrirano za ori_300.
        """
        if cb: cb("Tražim DTC enable tablice...")
        data = self.eng.get_bytes()

        # P1550 — senzor tlaka punjenja
        enable_vals = [data[_DTC_P1550_ENABLE_ADDR + i] for i in range(10)]
        code_le = data[_DTC_P1550_CODE_ADDR] | (data[_DTC_P1550_CODE_ADDR + 1] << 8)
        mirror_le = data[_DTC_P1550_MIRROR_ADDR] | (data[_DTC_P1550_MIRROR_ADDR + 1] << 8)
        active = any(b in (0x04, 0x05, 0x06) for b in enable_vals) or code_le == 0x1550
        if active:
            self.results.append(FoundMap(
                defn    = _DTC_P1550_ENABLE_DEF,
                address = _DTC_P1550_ENABLE_ADDR,
                sw_id   = self._sw(),
                data    = enable_vals,
            ))
            if cb: cb(f"  DTC P1550 @ 0x{_DTC_P1550_ENABLE_ADDR:06X}  code=0x{code_le:04X}  "
                      f"mirror=0x{mirror_le:04X}  enable={[hex(b) for b in enable_vals]}")

        # P0523 — senzor tlaka ulja
        enable_vals_0523 = [data[0x02108E + i] for i in range(11)]
        code_le_0523 = data[_DTC_P0523_CODE_ADDR] | (data[_DTC_P0523_CODE_ADDR + 1] << 8)
        active_0523 = any(b in (0x04, 0x05, 0x06) for b in enable_vals_0523) or code_le_0523 == 0x0523
        if active_0523:
            self.results.append(FoundMap(
                defn    = _DTC_P0523_ENABLE_DEF,
                address = 0x02108E,
                sw_id   = self._sw(),
                data    = enable_vals_0523,
            ))
            if cb: cb(f"  DTC P0523 @ 0x{0x02108E:06X}  code=0x{code_le_0523:04X}  "
                      f"enable={[hex(b) for b in enable_vals_0523]}")

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
