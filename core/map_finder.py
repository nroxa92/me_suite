"""
ME17Suite — Signature-Based Map Finder
Bosch ME17.8.5 by Rotax (Sea-Doo 300 / TC1762)

Sve potvrdjene mape (CODE regija 0x010000-0x05FFFF):

  RPM osa   (3× mirror)  @ 0x024F46 / 0x025010 / 0x0250DC   BE u16, 1×16
  Rev limit (2 lokacije) @ 0x02B72A, 0x02B73E                 LE u16, scalar (=8738 rpm)
  Ignition  (19 mapa)    @ 0x02B730, stride 144B              u8, 12×12, 0.75°/bit
  Injection main+mirror  @ 0x02436C / 0x0244EC (+0x180)      LE u16, 6×32
  SC corr   (boost comp) @ 0x02220E                           LE u16, 9×7, Q14
  Torque    main+mirror  @ 0x02A0D8 / 0x02A5F0 (+0x518)      BE u16, 16×16, Q8
  Lambda    main+mirror  @ 0x0266F0 / 0x026C08 (+0x518)      LE u16, 12×18, Q15
  Lambda bias/trim       @ 0x0265D6                           LE u16, 1×141, Q15
  Lambda trim (korekcija)@ 0x026DB8                           LE u16, 12×18, Q15
  Accel enrichment       @ 0x028059                           LE u16, 5×5, Q14 (kompleksan format)
  Temp fuel correction   @ 0x025E50                           LE u16, 1×156, Q14
  Start injection (1D)   @ 0x025CDC                           LE u16, 1×6 + 6-pt osa
  Ign correction (2D u8) @ 0x022374                           u8,  8×8, ugrađene osi
  Thermal enrichment     @ 0x02AA42                           LE u16, 8×7, /64=%, CTS 80-150°C
  Eff correction         @ 0x0259D2                           LE u16, 10×7, Q15 (ugradj. Y-os)
  Overtemp lambda        @ 0x025ADA                           LE u16, 1×63, Q15, 0xFFFF=SC bypass
  Neutral corr           @ 0x025B58                           LE u16, 1×63, Q14≈1.004
  SC boost factor        @ 0x025DF8                           LE u16, 1×40, Q14=1.224 (+22%)
  Lambda eff (KFWIRKBA)  @ 0x02AE5E                           LE u16, 41×18, Q15 (Y-os @ 0x02AE40)

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
# Verificirano direktnim citanjem iz binarnog fajla @ 0x024F46 (BE u16, 16 tocaka)
# Prethodne vrijednosti u kodu bile su pogresne za tocke 10-15!

# Prvih 12 od 16 tocaka RPM ose — koristimo za ignition (12×12)
_RPM_12 = [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 4608, 5120, 5632, 6400]

# Svih 16 tocaka — za torque (16×16)
_RPM_16 = [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096,
           4608, 5120, 5632, 6400, 6912, 7424, 7936, 8448]

_RPM_AXIS_12 = AxisDef(count=12, byte_order="BE", dtype="u16",
                        scale=1.0, unit="rpm", values=_RPM_12)
_RPM_AXIS_16 = AxisDef(count=16, byte_order="BE", dtype="u16",
                        scale=1.0, unit="rpm", values=_RPM_16)

# ─── Osa relativnog punjenja (rl — relative air charge) ───────────────────────
# Y osa za ignition, injection, lambda, torque mape.
# Izvor: analiza binarnog fajla @ 0x02AFAC (LE u16, 12 tocaka), 0x02AE30 (16 tocaka)
# Potvrdeno prisutnoscu istog niza u vise mjesta uz ignition i torque mape.
# WinOLS opis: "relative air charge" (rl, %)
#
# Skaliranje: raw ÷ 64 = postotak relativnog punjenja (procjena bez A2L):
#   0 = 0%, 100 = 1.56%, 1280 = 20%, 5760 = 90%, 6400 = 100%, 8320 = 130% (boost)
# Za Rotax ACE 1630 s komprimirajucim punjenjem: >100% je normalno pri punom gasu.

_LOAD_12 = [0, 100, 200, 400, 800, 1280, 2560, 3200, 3840, 4480, 5120, 5760]
_LOAD_16 = [0, 100, 200, 400, 800, 1280, 2560, 3200, 3840, 4480, 5120, 5760,
            6400, 7040, 7680, 8320]

_LOAD_AXIS_12 = AxisDef(count=12, byte_order="LE", dtype="u16",
                         scale=1.0/64.0, unit="load [%]", values=_LOAD_12)
_LOAD_AXIS_16 = AxisDef(count=16, byte_order="LE", dtype="u16",
                         scale=1.0/64.0, unit="load [%]", values=_LOAD_16)

# X osa za lambda mapu (18 stupaca) — Load (rl)
# Verificirano prisutnošću identičnog niza tocno 0x16A bajta ispred lambda mape
# i njezinog mirrora (@0x026586 i @0x026A9E — isti offset za obje kopije)
# Raspon: ~13% do 100% relativnog punjenja (lambda se prati samo pri redu opterecenja)
_LAMBDA_X_18 = [853, 1067, 1280, 1493, 1707, 1920, 2133, 2347,
                2560, 2773, 2987, 3200, 3413, 3840, 4267, 4693, 5547, 6400]
_LAMBDA_LOAD_AXIS_18 = AxisDef(count=18, byte_order="LE", dtype="u16",
                                scale=1.0/64.0, unit="load [%]", values=_LAMBDA_X_18)


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
    notes       = "Potvrdjene lokacije: 0x02B72A, 0x02B73E (=8738 rpm). "
                  "Adresi 0x022096/0x0220B6/0x0220C0 su unutar 2D mape — NISU rev limiteri!",
)

# 2 potvrdjene adrese rev limitera (ostale su bile pogresno identificirane — unutar 2D tablice)
_REV_KNOWN_ADDRS = [0x02B72A, 0x02B73E]

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
IGN_COUNT  = 19

# Nazivi ignition mapa — 19 mapa svakih 144B (12×12 u8, 0.75°/bit):
#   00-07  Osnovna timing mapa (razliciti uvjeti: toplina, load, boost...)
#   08-09  Knock delta/trim — POTVRDJENO: negativni pomaci, manji raspon = retard korekcija
#   10-15  Pomocna mapa (neidentificirana: moguce cold start, decel, overrun)
#   16-17  POTVRDJENO NPRo STG2: aktivne timing mape izvan prvobitnih 16 (0x02C030, 0x02C0C0)
#   18     Uvjetna/parcijalna mapa — prvih 3 reda aktivni, ostali 0 (STG2 mijenja)
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
    "Paljenje — Prosirena 1",        # 16  POTVRDJENO: NPRo STG2 mijenja (0x02C030)
    "Paljenje — Prosirena 2",        # 17  POTVRDJENO: NPRo STG2 mijenja (0x02C0C0)
    "Paljenje — Uvjetna",            # 18  parcijalna mapa, prvih 3 reda aktivni
]

def _make_ign_def(idx: int) -> MapDef:
    addr = IGN_BASE + idx * IGN_STRIDE
    is_knock    = idx in (8, 9)
    is_extended = idx in (16, 17)
    is_partial  = idx == 18
    return MapDef(
        name         = _IGN_NAMES[idx],
        description  = (
            f"Korekcija predpaljenja za knock/detonaciju #{idx-7} — "
            "negativne vrijednosti = kasnjenje (retard). "
            "Automatski se oduzima od osnovne mape pri detekciji detonacije."
            if is_knock else
            f"Kut predpaljenja (timing advance) — prosirena mapa #{idx:02d}. "
            "POTVRDJENO: NPRo STG2 mijenja ovu mapu. "
            "Osi: RPM (x) × opterecenje/MAP (y)."
            if is_extended else
            f"Uvjetna/parcijalna timing mapa #{idx:02d}. "
            "Prvih 3 reda aktivni (28.5–34.5°), ostatak nula. STG2 djelomicno mijenja."
            if is_partial else
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
        raw_min      = 0  if (is_knock or is_partial) else 16,
        raw_max      = 40 if is_knock else 58,
        mirror_offset= 0,
        notes        = (
            f"Adresa: 0x{addr:06X}. Scale: 0.75°/bit. "
            + ("KNOCK TRIM: retard delta oduzet od osnove pri detonaciji. " if is_knock else
               "POTVRDJENO NPRo STG2 mapa. ORI: 25.5–30°, STG2: vise. " if is_extended else
               "UVJETNA: aktivna samo u odredjenim uvjetima. " if is_partial else
               "ORI: 24–33.75° BTDC, STG2: do 36.75° BTDC. ")
            + "Os Y: relativno punjenje rl [%] — kandidat @ 0x02AFAC (LE u16, ÷64). "
            + "Skaliranje procijenjeno bez A2L; A2L potvrda: WinOLS string 'relative air charge'."
        ),
    )

_IGN_DEFS = [_make_ign_def(i) for i in range(IGN_COUNT)]


# ─── Injection mapa ───────────────────────────────────────────────────────────

INJ_MAIN          = 0x02436C   # ISPRAVLJENO: bio 0x02439C (pogreška +0x30)
INJ_MIRROR        = 0x0244EC   # ISPRAVLJENO: 0x02436C + 0x180
INJ_MIRROR_OFFSET = INJ_MIRROR - INJ_MAIN   # 0x180

_INJ_DEF = MapDef(
    name          = "Ubrizgavanje — relativna masa goriva (rk) [Q15]",
    description   = (
        "Relativna masa goriva (rk) — 16x12 tablica (load x RPM). "
        "Q15 format: 32768 = 1.0 (100% bazno gorivo), >32768 = obogacivanje (SC). "
        "Redovi 0-1 = nula (nema ubrizgavanja ispod praga). "
        "Redovi 14-15 = nula (padding/neaktivni). "
        "Svi stupci identicni unutar reda = RPM ne utjece na kolicinu goriva u ovoj tablici. "
        "STG2 povecava sve vrijednosti (agresivniji map). "
        "Osi: Y = razina opterecenja (16 tocaka), X = RPM (12 tocaka, sve jednake per row)."
    ),
    category      = "injection",
    rows=16, cols=12,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "rk [Q15]",
    axis_x        = None,   # 12-pt RPM os (sve celije identicne unutar reda — RPM neovisan)
    axis_y        = None,   # 16-pt load os @ ~0x024342 (potrebna A2L potvrda)
    raw_min       = 0,
    raw_max       = 65535,
    mirror_offset = INJ_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{INJ_MAIN:06X}, mirror @ 0x{INJ_MIRROR:06X} (+0x{INJ_MIRROR_OFFSET:X}=0x180). "
        "Dims ISPRAVLJENE: bile 6x32 (pogresno), stvarno 16x12. "
        "Adresa 0x02436C tocna (red 0 i 1 = 0, podaci od reda 2=328 na 0x02439C). "
        "Scale = Q15 (rk = rel. fuel mass), RKTI funkcija pretvara rk -> te (ms). "
        "Y-os 10pt @ 0x024342: [1280,2560..12800] (vjerojatno RLSOL load). "
        "STG2: sve vrijednosti povecane (agresivniji fuel map). "
    ),
)


# ─── Torque mapa ─────────────────────────────────────────────────────────────

_TORQUE_DEF = MapDef(
    name          = "Moment — ogranicenje [%]",
    description   = (
        "Ogranicenje momenta motora — 16×16 tablica. "
        "100% = puni moment dozvoljen, <100% = ogranicenje (limp mode, TOPS, toplinski). "
        ">100% = moze se desiti pri boost (SCJ kompenzacija). "
        "ORI: 93–120%, STG2: 93–123%. "
        "Osi: RPM × opterecenje motora [%]."
    ),
    category      = "torque",
    rows=16, cols=16,
    byte_order    = "BE", dtype = "u16",
    scale         = 100.0 / 32768.0,   # raw = MSB<<8; (MSB<<8)*100/32768 = MSB*100/128 = %
    offset_val    = 0.0,
    unit          = "%",
    axis_x        = _RPM_AXIS_16,
    axis_y        = _LOAD_AXIS_16,
    raw_min       = 20480,   # 80% = 80*32768/100 = 26214 (spusteni na 20480 za provjeru)
    raw_max       = 51200,   # 156% (STG2 max ~123% = 40304, 160% sigurnosni strop)
    mirror_offset = 0x518,
    notes         = (
        "Main @ 0x02A0D8, mirror @ 0x02A5F0 (+0x518). "
        "LSB uvijek 0x00 — podatak samo u MSB. "
        "raw = (MSB << 8); display = raw * 100 / 32768 = MSB * 100 / 128. "
        "ORI raspon: 93.0–119.5%, STG2: 92.2–122.7%. "
        "Povecanje = vise momenta (deaktivacija ogranicenja). "
        "TOPS sistem koristi ovu tablicu za zastitu — pazljivo pri povecavanju."
    ),
)


# ─── Lambda mapa ─────────────────────────────────────────────────────────────

LAM_MAIN          = 0x0266F0
LAM_MIRROR        = 0x026C08
LAM_MIRROR_OFFSET = LAM_MIRROR - LAM_MAIN   # 0x518

_LAMBDA_DEF = MapDef(
    name          = "Lambda — ciljni AFR (open-loop)",
    description   = (
        "Ciljni omjer zraka/goriva (AFR) — 12×18 tablica (Q15 LE). "
        "Rotax ACE 1630/900 NEMA fizicku lambda sondu — open-loop AFR cilj iz mape. "
        "lambda = AFR / 14.7:  1.000 = stoehiometrija (AFR 14.7:1), "
        "0.900 = bogato (AFR 13.2:1, puni gas), 1.050 = siromasno (AFR 15.4:1, stednja). "
        "ORI raspon: 0.965–1.073 (AFR 14.2–15.8). STG2: 0.984–1.080 (AFR 14.5–15.9). "
        "Osi: X = opterecenje [%] (18 tocaka), Y = RPM (12 tocaka)."
    ),
    category      = "lambda",
    rows=12, cols=18,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,   # Q15: 32768 = 1.0
    offset_val    = 0.0,
    unit          = "lambda",
    axis_x        = _LAMBDA_LOAD_AXIS_18,   # rl load os, 18 tocaka @ 0x026586
    axis_y        = _RPM_AXIS_12,           # RPM os, 12 tocaka (redovi = RPM)
    raw_min       = 16384,   # lambda = 0.50 (max bogato)
    raw_max       = 65535,   # lambda = 2.00 (max siromasno)
    mirror_offset = LAM_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{LAM_MAIN:06X}, mirror @ 0x{LAM_MIRROR:06X} (+0x{LAM_MIRROR_OFFSET:X}). "
        "Q15 format: raw / 32768 = lambda. 32768 = lambda 1.0 (stehiometrijsko). "
        "Tipicni raspon: 0.80 (bogato, puni gas) do 1.05 (malo siromasno, stednja). "
        "NEMA feedback loop — promjena ove mape direktno mijenja AFR. "
        "X os (load) @ 0x026586 LE u16, Y os (RPM) = globalna RPM os @ 0x024F46."
    ),
)


# ─── SC bypass / ETA control mapa ────────────────────────────────────────────
#
# Identificirana diff analizom ori_300 vs wake230 (isti motor ACE 1630, ali razlicit SC).
# wake230 ima slabiji SC (260hp SC geometrija), ORI vrijednosti mu su znatno nize.
# npro_stg2 ima max vrijednosti (bypass minimiziran = max boost).
#
# Fizikalni smisao: ECU kontrolira bypass ventil SC-a.
#   Vise raw vrijednosti = bypass ventil OTVOREN = SC bypassed = manji boost
#   Manje raw vrijednosti (38) = bypass ZATVOREN = puni boost
#   255 = bypass potpuno otvoren (dijagonala mape = prijelazna tocka)
#
# X os @ 0x020509: [63, 75, 88, 100, 113, 138, 163]
#   Moguce: MAP senzor (kPa) ili ETA pozicija (%)
#   100 = referencna tocka (atmosferski tlak ili 100% ETA)
#   Ispod 100 = vakuum/parcijalni gas, iznad 100 = boost/puni gas
#
# Y os @ 0x020524: [51, 77, 102, 128, 154, 179, 205]
#   Moguce: relativno opterecenje ili ETA pozicija (%) x 128 = 100%
#   Evenly spaced ~25 koraka → linearna os
#
# Napomena: tocno skaliranje potrebuje A2L potvrdu.

SC_MAIN   = 0x020534
SC_MIRROR = 0x0205A8
SC_MIRROR_OFFSET = SC_MIRROR - SC_MAIN   # 0x74

# Treća kopija SC mape (0x029993) — identificirana diff analizom ori vs stg2
# NPRo mijenja i ovu kopiju (drugačije vrijednosti od 0x0205A8), mogući drugi uvjeti
SC_EXTRA  = 0x029993

# SC X-os: MAP senzor vrijednosti interpretirane kao kPa → /100 = bar (abs.)
#   100 = 1.00 bar = atmosferski tlak (bez boosta)
#   163 = 1.63 bar = 0.63 bar nadtlaka (boost pressure above atm.)
#   63  = 0.63 bar = podtlak (vakuum, zatvorena zaklopka)
_SC_X_AXIS_VALS = [63, 75, 88, 100, 113, 138, 163]   # raw kPa vrijednosti
_SC_X_AXIS_BAR  = [round(v * 0.01, 2) for v in _SC_X_AXIS_VALS]  # [0.63, 0.75, 0.88, 1.00, 1.13, 1.38, 1.63]

# SC Y-os: opterecenje u %, 128 = 100%
_SC_Y_AXIS_VALS = [51, 77, 102, 128, 154, 179, 205]
_SC_Y_AXIS_PCT  = [round(v * 100.0/128.0, 1) for v in _SC_Y_AXIS_VALS]  # [39.8, 60.2, 79.7, 100.0, 120.3, 139.8, 160.2]

_SC_X_AXIS = AxisDef(count=7, byte_order="BE", dtype="u8",
                      scale=0.01, unit="bar (abs.)", values=_SC_X_AXIS_VALS)
_SC_Y_AXIS = AxisDef(count=7, byte_order="BE", dtype="u8",
                      scale=100.0/128.0, unit="load [%]", values=_SC_Y_AXIS_VALS)

_SC_DEF = MapDef(
    name          = "SC bypass ventil — otvorenost [%]",
    description   = (
        "Otvorenost bypass ventila kompresora — 7×7 tablica. "
        "0% = bypass ZATVOREN = MAKSIMALNI boost (ventil blokira obilazak). "
        "100% = bypass POTPUNO OTVOREN = NULA boosta (zrak zaobilazi kompresor). "
        "X os: tlak usisnog zraka (MAP) u bar aps. (1.00 bar = atmosfera). "
        "Y os: opterecenje motora [%] (100% = nominalno, >100% = boost uvjeti). "
        "ori_300: 14.9–80.4%, wake230: 12.2–31.0%, stg2: 14.9–100.0%."
    ),
    category      = "misc",
    rows=7, cols=7,
    byte_order    = "BE",
    dtype         = "u8",
    scale         = 100.0 / 255.0,   # raw 0-255 → 0-100% bypass otvorenost
    offset_val    = 0.0,
    unit          = "% bypass",
    axis_x        = _SC_X_AXIS,
    axis_y        = _SC_Y_AXIS,
    raw_min       = 0,
    raw_max       = 255,
    mirror_offset = SC_MIRROR_OFFSET,
    notes         = (
        f"Main @ 0x{SC_MAIN:06X}, mirror @ 0x{SC_MIRROR:06X} (+0x{SC_MIRROR_OFFSET:X}). "
        "NISKA vrijednost = vise boosta! ORI min=14.9% (puni boost), max=80.4%. "
        "X os (MAP): [0.63, 0.75, 0.88, 1.00, 1.13, 1.38, 1.63] bar aps. @ 0x020509. "
        "Y os (load): [39.8, 60.2, 79.7, 100.0, 120.3, 139.8, 160.2] % @ 0x020524."
    ),
)


# ─── Cold start enrichment ───────────────────────────────────────────────────
#
# Parametri bogaćenja pri hladnom startu — 1D tablica 6 vrijednosti @ 0x02586A.
# ECU dodaje ovu količinu goriva (raw jedinice) u prvih N sekundi nakon hladnog starta.
# NPRo STG2 smanjio prvu vrijednost 500 → 100 (manje bogaćenja pri -30°C i sl.)
# i neznatno smanjio 1096 → 1075.
#
# Kontekst: ispred i iza tablice nalazi se temperaturna os (CTS) i NTC lookup:
#   @ 0x025880 (1×11 u16 LE): timing/decay parametri (4, 6, 8, 10, 20, 40, 60, 120, 240, 480, 960)
#   @ 0x025896 (1×10 u16 LE): CTS temperaturna os u °C = [37..157]
#   @ 0x0258AA (1×10 u16 LE): NTC ADC lookup [5383..1425] — hardware kalibracija (ne editirati!)

COLD_START_ADDR = 0x02586A

_COLD_START_DEF = MapDef(
    name          = "Cold start — bogaćenje gorivom",
    description   = (
        "Faktor bogaćenja gorivom pri hladnom startu — 6 vrijednosti (1D tablica). "
        "Veće = više goriva pri hladnom startu. "
        "ori_300: [500, 1000, 1690, 1126, 1096, 1024]. "
        "NPRo STG2: [100, 1000, 1690, 1126, 1075, 1024] — smanjeno za 80%. "
        "Raspon: od najhladnijeg do toplog pokretanja."
    ),
    category      = "misc",
    rows=1, cols=6,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw (u16)",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 0,
    raw_max       = 5000,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{COLD_START_ADDR:06X}. "
        "NPRo STG2: [0]=500→100, [4]=1096→1075. "
        "Susjedne tablice @ 0x025880 (decay timing), 0x025896 (CTS temp os °C), "
        "0x0258AA (NTC ADC lookup — hardware, ne editirati!)."
    ),
)

# CTS temperaturna os @ 0x025896 — 10 točaka [37..157] u °C
CTS_TEMP_AXIS_ADDR = 0x025896
_CTS_TEMP_AXIS_VALS = [37, 51, 64, 77, 91, 104, 117, 131, 144, 157]

_CTS_TEMP_AXIS_DEF = MapDef(
    name          = "CTS — temperaturna os (°C)",
    description   = (
        "Temperaturna os senzora rashladne tekućine (CTS) za cold start i korekcijske tablice. "
        "10 točaka od 37°C do 157°C (u16 LE, raw = °C). "
        "Raspon pokriven: hladni motor (37°C) do pregrijanja (157°C)."
    ),
    category      = "axis",
    rows=1, cols=10,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0, unit = "°C",
    raw_min       = 0, raw_max = 200,
    axis_x        = None, axis_y = None,
    notes         = (
        f"@ 0x{CTS_TEMP_AXIS_ADDR:06X}. "
        "Odmah slijedi NTC ADC lookup @ 0x0258AA (hardware kalibracija)."
    ),
)


# ─── Knock threshold parametri ────────────────────────────────────────────────
#
# Blok od 24× u16 LE vrijednosti @ 0x0256F8 koji kontrolira knock detekciju.
# Format u8 parova: svake 2 bajta = 2 parametra (vjerojatno po cilindru).
#
# Poznate vrijednosti:
#   [00-01] = 44237 (0xACCD) — prag detekcije knocka (threshold high) → NPRo: 65535
#   [02+]   = 7967  (0x1F1F) = [31,31] u8 — nominalni prag knocka per-cyl → NPRo: [154,154]
#
# NPRo STG2 promjene:
#   [00-01]: 44237 → 65535 (povišen threshold = teže aktivirati smanjenje timinga)
#   [03,04,09,10,15,16,17,20,21]: 7967 → 39578 (31→154 u8 — agresivniji knock limit)
#   [05,11,22]: 7967 → 8090 (31→154 samo low byte)
#
# NAPOMENA: točna 2D struktura nepoznata bez A2L — iskazano kao flat 1D.

KNOCK_PARAMS_ADDR = 0x0256F8

_KNOCK_PARAMS_DEF = MapDef(
    name          = "Knock — parametri praga detekcije",
    description   = (
        "Parametri praga detekcije detonacije (knock threshold) — 24 vrijednosti (1D). "
        "Veće = viši prag = ECU teže detektira knock = manje retard korekcija. "
        "Format: u8 parovi (svaka u16 = 2 bajta = 2 param). "
        "ori_300: [0-1]=44237, [2+]=7967. "
        "NPRo STG2: [0-1]=65535, selektivno [3,4,9,10...]=39578 (agresivnija tuning mapa)."
    ),
    category      = "misc",
    rows=1, cols=24,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw (u16)",
    axis_x        = None, axis_y = None,
    raw_min       = 0, raw_max = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{KNOCK_PARAMS_ADDR:06X}. "
        "Kao u8 parovi: 0x1F=31 nominalni, 0x9A=154 NPRo agresivni, 0xFF=255 max. "
        "Točna 2D struktura zahtijeva A2L potvrdu."
    ),
)


# ─── SC load injection correction ────────────────────────────────────────────
#
# Identificirana diff analizom 4 SW varijanti (130/170/230/300hp 2021).
# 130/170hp SVE 16384 (neutralno) → nema SC, NA motor ili SC disabled.
# 230hp: 16728-30900 (slabiji SC), 300hp: 5325-35895 (jaki SC, dijagonalni).
#
# Struktura: 7-točkasta X-os (RPM) @ 0x022200, tablica 9×7 Q14 @ 0x02220E.
#   X-os (u16 LE, /8 = RPM): ori_300 = [10000,15000,18000,20000,24000,32000,34000]
#     → RPM: [1250, 1875, 2250, 2500, 3000, 4000, 4250]
#   Y-os (9 redova): neidentificirana — vjerojatno load ili MAP
# Q14: 16384 = 1.0 = neutralna korekcija, >16384 = bogaćenje, <16384 = osiromašivanje

SC_CORR_Y_ADDR = 0x0221EC   # Y-os: 9× u16 LE (raw/64 = rl %)  — direktno ispred X-osi
SC_CORR_X_ADDR = 0x022200   # X-os: 7× u16 LE (raw/8 = RPM)
SC_CORR_ADDR   = 0x02220E   # tablica: 9×7 u16 LE Q14

# ori_300 (300hp SC): Y raspon 47–180% rl (boost operating range)
# 130/170/230hp: Y raspon 8–109% rl (NA raspon) — RAZLIKUJE SE PO SW!
_SC_CORR_X_VALS = [1250, 1875, 2250, 2500, 3000, 4000, 4250]  # ori_300 RPM os
_SC_CORR_Y_VALS = [3000, 4000, 6000, 7000, 8000, 8500, 9500, 10500, 11500]  # ori_300, raw /64=rl%

_SC_CORR_X_AXIS = AxisDef(count=7, byte_order="LE", dtype="u16",
                            scale=1.0/8.0, unit="rpm", values=_SC_CORR_X_VALS)
_SC_CORR_Y_AXIS = AxisDef(count=9, byte_order="LE", dtype="u16",
                            scale=1.0/64.0, unit="load [%]", values=_SC_CORR_Y_VALS)

_SC_CORR_DEF = MapDef(
    name          = "SC boost — korekcija goriva [%]",
    description   = (
        "Korekcija goriva za SC boost opterecenje — 9×7 tablica. "
        "0% = neutralno (bez korekcije), +100% = duplo vise goriva, -50% = upola manje. "
        "Primjer: ori_300 raspon -67.5% do +119.1% (masivna SC boost kompenzacija). "
        "130/170hp: SVE 0% (NA motor, bez SC, nema korekcije). "
        "X os: RPM, Y os: opterecenje motora [%] — RAZLIKUJE SE po SW varijanti! "
        "300hp Y: 47–180% (boost raspon), 130/230hp Y: 8–109% (NA raspon)."
    ),
    category      = "injection",
    rows=9, cols=7,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 16384.0,   # Q14: 16384 = 0% korekcija; prikaz u % od/+/- baznog ubrizgavanja
    offset_val    = -100.0,             # 0% offset: raw 16384 → 16384*100/16384 - 100 = 0%
    unit          = "% korekcija",
    axis_x        = _SC_CORR_X_AXIS,
    axis_y        = _SC_CORR_Y_AXIS,
    raw_min       = 4096,   # -75% (maks. osiromašivanje)
    raw_max       = 49152,  # +200% (trostruko bogacenje)
    mirror_offset = 0,
    notes         = (
        f"Y-os @ 0x{SC_CORR_Y_ADDR:06X} (9× u16 LE, /64=rl%), "
        f"X-os @ 0x{SC_CORR_X_ADDR:06X} (7× u16 LE, /8=RPM), "
        f"tablica @ 0x{SC_CORR_ADDR:06X}. "
        "ori_300 Y: [46.9, 62.5, 93.8, 109.4, 125.0, 132.8, 148.4, 164.1, 179.7] rl%. "
        "130/230hp Y: [7.8, 15.6, 23.4, 31.2, 46.9, 62.5, 78.1, 93.8, 109.4] rl%. "
        "Dijagonalni pattern = SC boost kompenzacija aktivna samo pri visokom opterecenju."
    ),
)


# ─── Temperature fuel correction ─────────────────────────────────────────────
#
# Korekcija goriva indexirana temperaturom/uvjetima — 156× u16 LE Q14 @ 0x025E50.
# Lokacija: 0x025E50–0x025F88 (312 bajta = 156 u16).
#
# Karakteristike po SW:
#   300hp:    flat ~1.208 (+20.8% enrichment) — hladni/boost kompenzacija
#   130/170hp: ~1.0 minimalna korekcija
#   230hp:    0.816 (-18.4% lean) — decel/CTS temp lean korekcija
#
# Fizikalni smisao: korekcija ubrizgavanja po temperaturi rashladne tekucine (CTS).
# Motor ACE 1630/900 nema senzor temperature goriva ni IAT — jedini termalni senzor je CTS.
# Vrijednosti padaju od ~121% (hladan motor) prema ~68% (vruci motor) = warm-up enrichment.
# X-os: implicit index (0-155), nema binarnih oznaka (ne postoji axis u ECU za ovu tablicu).

TEMP_FUEL_ADDR = 0x025E50

_TEMP_FUEL_DEF = MapDef(
    name          = "Gorivo — CTS warm-up korekcija [%]",
    description   = (
        "Korekcija ubrizgavanja po temperaturi rashladne tekucine (CTS) — 156 tocaka. "
        "Warm-up enrichment: hladan motor dobiva vise goriva (do +21%), "
        "topli motor manje (do -33%). Nema senzora temp. goriva niti IAT. "
        "X-os: implicitni indeks 0-155 (nema binarnih oznaka u ECU). "
        "0% = neutralno (=16384 Q14). "
        "300hp: flat +20.8% (SC korekcija). "
        "230hp: -18.4%. 130/170hp: ~neutralno."
    ),
    category      = "injection",
    rows=1, cols=156,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 16384.0,
    offset_val    = -100.0,
    unit          = "%",
    axis_x        = None,   # nema osi u ECU -- implicit CTS index 0-155
    axis_y        = None,
    raw_min       = 8192,   # -50%
    raw_max       = 32768,  # +100%
    mirror_offset = 0,
    notes         = (
        f"@ 0x{TEMP_FUEL_ADDR:06X}-0x025F88 (156x u16 LE Q14, 312B). "
        "CTS-indexed warm-up enrichment. Bez fizicke X-osi u ECU. "
        "300hp: +20.8%, 230hp: -18.4%, 130/170hp: ~0%. STG2=ORI."
    ),
)


# ─── Lambda bias (AFR trim) ───────────────────────────────────────────────────
#
# Lambda korekcija/bias odmah ispred lambda mape — 141× u16 LE Q15 @ 0x0265D6.
# Q15: 32768 = lambda 1.0 (stoehiometrijsko), >32768 = lean, <32768 = bogato.
#
# Vrijednosti po SW:
#   300hp:    ~32922 → +0.47% lean bias
#   130/170hp: ~32744 → -0.07% (neutralno)
#   230hp:    ~33558 → +2.41% lean bias (SC kompenzacija za boost?)
#
# Pozicija: 0x0265D6–0x026706 = 0x130 bajta = 304B → 152 u16
# Napomena: 141 je originalna procjena — treba verificirati točan count.

LAMBDA_BIAS_ADDR = 0x0265D6

_LAMBDA_BIAS_DEF = MapDef(
    name          = "Lambda bias — AFR korekcija [%]",
    description   = (
        "AFR trim/bias uz lambda target mapu — 141 vrijednosti (1D). "
        "0% = neutralno (nema korekcije). +2% = 2% siromasnije od ciljne mape. "
        "-2% = 2% bogatije od ciljne mape. "
        "300hp: +0.47% (blagi lean), 230hp: +2.41% (lean bias za SC), 130/170hp: -0.07% (neutralno). "
        "Smjesten odmah ispred lambda mape @ 0x0266F0."
    ),
    category      = "lambda",
    rows=1, cols=141,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 32768.0,
    offset_val    = -100.0,
    unit          = "%",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 16384,   # lambda 0.5
    raw_max       = 65535,   # lambda 2.0
    mirror_offset = 0,
    notes         = (
        f"@ 0x{LAMBDA_BIAS_ADDR:06X}–0x026706 (141× u16 LE Q15). "
        "Odmah ispred lambda main mape @ 0x0266F0. "
        "300hp +0.47% lean, 230hp +2.41% lean, 130/170hp neutralno. "
        "Fizikalni smisao: globalni AFR trim po uvjetu/načinu rada ECU-a."
    ),
)


# ─── Lambda zaštitna / max injection mapa ─────────────────────────────────────
#
# 12×13 tablica u16 LE @ 0x02469C (312B = 156 u16), odmah iza injection mirrora.
# Dijagonalni pattern: dolje-lijevo (idle) = male vrijednosti, gore-desno (WOT) = 65535.
# ORI 300hp: raspon 1311–58982 (dijagonalni step pattern)
# NPRo STG2: SVE saturirano na 65535 (maksimalna sloboda za bogaćenje — WOT tune)
# ORI 230hp = ORI 130hp = ORI 300hp (identično u svim SW varijantama)
#
# Fizikalni smisao (procjena bez A2L):
#   Moguće: KFLFMXSUB (max lambda za komponentnu zaštitu) ili
#   KFMSANPKW (max injection za normalnu operaciju) — ME17 standard.
#   Gornja granica koliko ECU smije ubrizgati u pojedinoj RPM×load ćeliji.
#   BitEdit ME17.8.5 lista: "Lambda efficiency" / "Target lambda for knock protection"

LAMBDA_PROT_ADDR = 0x02469C

_LAMBDA_PROT_DEF = MapDef(
    name          = "Lambda zaštita — max ubrizgavanje [Q15]",
    description   = (
        "Gornja granica ubrizgavanja / lambda zaštitna mapa — 12×13 tablica. "
        "Dijagonalni pattern: idle (dolje-lijevo) = malo, WOT (gore-desno) = 65535. "
        "ORI: 1311–58982 (dijagonalni step). NPRo STG2: SVE 65535 (max sloboda). "
        "Identično u 300/230/130hp (zajednička baza). "
        "Procjena: Q15 gornja granica lambde ili max injection za zaštitu komponenti."
    ),
    category      = "lambda",
    rows=12, cols=13,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "lambda (Q15)",
    axis_x        = None,   # 13 kolona — neidentificirana os
    axis_y        = _LOAD_AXIS_12,
    raw_min       = 0,
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{LAMBDA_PROT_ADDR:06X} (12×13 u16 LE Q15, 312B). "
        "Odmah iza injection mirrora (0x024660). "
        "STG2 saturira sve na 65535 — tipicno za WOT/performance tune. "
        "ME17 standard naziv: KFLFMXSUB ili KFMSANPKW (A2L potvrda potrebna). "
        "13. kolona puni se postepeno (dijagonalni shift po redu)."
    ),
)


# ─── Lambda trim (korekcija lambde po RPM×load) ───────────────────────────────
#
# 12×18 Q15 tablica @ 0x026DB8 — odmah iza lambda mirrora (mirror završava @ 0x026D20,
# razmak 0x98=152B između mirrora i trima).
# Iste dimenzije kao lambda main/mirror (12 RPM × 18 load točaka).
# Fizikalni smisao: aditivna lambda korekcija po RPM×load — trim na lambda target mapu.
#
# Vrijednosti po SW (svi malo različiti = per-motor kalibracija):
#   300hp ORI:  0.965–1.001 (blagi lean bias na visokim load točkama)
#   300hp STG2: 0.984–0.999 (izravnano — NPRo unificirao korekciju)
#   130hp:      0.984–1.001 (viši load malo richer)
#   230hp:      0.970–1.014 (veće varijacije — SC kompenzacija?)

LAMBDA_TRIM_ADDR = 0x026DB8

_LAMBDA_TRIM_DEF = MapDef(
    name          = "Lambda trim — korekcija po RPM×load [%]",
    description   = (
        "Additivna lambda korekcija uz lambda target mapu — 12×18 Q15 tablica. "
        "0% = neutralno (nema korekcije lambda cilja). "
        "+2% = 2% siromasnije od lambda mape. -2% = 2% bogatije. "
        "Razlikuje se po HP varijanti — per-motor kalibracija. "
        "300hp: 0.965–1.001 lambda, 230hp: 0.970–1.014, 130hp: 0.984–1.001. "
        "Osi: X = opterecenje [%] (18 tocaka), Y = RPM (12 tocaka) — iste kao lambda mapa."
    ),
    category      = "lambda",
    rows=12, cols=18,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 32768.0,
    offset_val    = -100.0,
    unit          = "%",
    axis_x        = _LAMBDA_LOAD_AXIS_18,
    axis_y        = _RPM_AXIS_12,
    raw_min       = 27000,   # lambda ~0.82
    raw_max       = 38000,   # lambda ~1.16
    mirror_offset = 0,
    notes         = (
        f"@ 0x{LAMBDA_TRIM_ADDR:06X} (12×18 u16 LE Q15, 432B). "
        "Odmah iza lambda mirrora (0x026C08+432=0x026D20, razmak 0x98). "
        "Sve 216 vrijednosti u Q15 opsegu — potvrdjeno binarnim skanom. "
        "Iste dimenzije kao lambda main/mirror. A2L naziv: KFLAMTRIM ili KFLLAFACR."
    ),
)


# ─── Ubrzavajuće obogaćivanje (KFMSWUP ekvivalent) ───────────────────────────
#
# Kompleksan blok @ 0x028059 (132B) — 1B global + 5 redova × 23B (svaki ima ugrađenu os).
# Svaki red: 1B marker + 6×u16 dTPS os + 5×u16 Q14 faktori ubrizgavanja
# dTPS os (delta-throttle/s): [0, 5, 150, 200, 350, 1500] °/s
# 5 RPM redova (indeksirani marker bajtem 4/5 — razlike po brzini motora)
#
# STG2 razlike: dTPS os promijenjena na [0, 5, 150, 300, 600, 900] i Q14 vrijednosti
# bitno povećane (do 2.64× = 164% obogaćivanja) — agresivnija tranzijentna korekcija.
#
# Tipični Q14 faktori:
#   ORI: 0.760–1.600 (76%–160%) → malo obogaćivanje pri naglom pliniranju
#   STG2: 0.480–2.640 (48%–264%) → mnogo agresivnija tranzijentna korekcija
#
# Analogno Bosch A2L: KFMSWUP (Kraftstoffmengen-Schub-Abschalt-Unterbrechung)
# ili KFVDHKK (Verbrauchskorrektur Dynamisch) — bez A2L ne možemo potvrditi točan naziv.

ACCEL_ENRICH_ADDR = 0x028059

_ACCEL_ENRICH_DEF = MapDef(
    name          = "Ubrzanje — tranzijentno obogaćivanje [%]",
    description   = (
        "Faktor obogaćivanja goriva pri naglom gazu (KFMSWUP ekvivalent) — 5×5 tablica. "
        "Svaki red je jedan RPM uvjet, stupci = dTPS razine (brz. promjene zaklopke). "
        "dTPS os [°/s]: ORI=[0,5,150,200,350,1500], STG2=[0,5,150,300,600,900]. "
        "100% = neutralno (nema korekcije). <100% = decel. >100% = ubrzanje. "
        "ORI: 76–160%, STG2: 48–264% (mnogo agresivnija tranzijentna korekcija). "
        "Pažnja: kompleksan binarni format — svaki red ugrađuje vlastitu os u binariju."
    ),
    category      = "injection",
    rows=5, cols=5,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 16384.0,
    offset_val    = -100.0,
    unit          = "% korekcija",
    axis_x        = AxisDef(count=6, byte_order="LE", dtype="u16",
                             scale=1.0, unit="dTPS [°/s]",
                             values=[0, 5, 150, 200, 350, 1500]),  # ORI os
    axis_y        = None,  # RPM redovi — neidentificirani bez A2L
    raw_min       = 4096,   # -75%
    raw_max       = 49152,  # +200%
    mirror_offset = 0,
    notes         = (
        f"@ 0x{ACCEL_ENRICH_ADDR:06X} (132B). Format: 1B global + 5×(1B+6×u16 os+5×u16 data). "
        "Svaki red ugrađuje vlastitu 6-tocku dTPS os — nestandarni Bosch format. "
        "ORI dTPS: [0,5,150,200,350,1500]°/s; STG2: [0,5,150,300,600,900]°/s. "
        "ME17.8.5 A2L analogno: KFMSWUP ili KFVDHKK. Potvrdjeno binarnim skanom svih SW varijanti."
    ),
)


# ─── Thermal fuel enrichment (overtemp protection) — 8×7 ────────────────────
#
# Tablica obogaćivanja goriva pri visokim temperaturama motora @ 0x02AA42.
# Y-os (temperatura) ugrađena ISPRED tablice @ 0x02AA32: [80,90,100,110,120,130,140,150]°C.
# Dimenzije: 8 redova (temp) × 7 stupaca (neidentificirani parametar) = 56 u16 LE.
# Skala: /64 = % (195–210% bogatstvo pri normalnim uvjetima SC motora).
#
# Fizikalni smisao: ECU daje više goriva pri visokim CTS temp. — hlađenje klipova SC.
# STG2 značajno smanjuje ove vrijednosti (dijagonalni pattern, posebno col-0 svake temp):
#   row 0 (80°C):  ORI 195.2% → STG2 105.0% (uklanja toplinsku zaštitu!)
#   row 7 (150°C): ORI 188.5% → STG2 162.0% (manji utjecaj)
#
# 130hp/082806: potpuno drugačiji sadržaj (N/A motor bez SC toplinske zaštite).
# X-os (load intern, 7 točaka) @ 0x02AA02: [6400,8000,9600,11200,12800,14400,16000]
# Iste interne load jedinice kao KFWIRKBA Y-os (korak=1600, raspon=6400–16000).
# Fizikalni smisao: opterećenje motora — 6400=niski load, 16000=puni load.

THERM_ENRICH_XAXIS_ADDR = 0x02AA02  # 7× u16 LE load os [6400..16000]
THERM_ENRICH_AXIS_ADDR  = 0x02AA32  # 8× u16 LE CTS temp os [80..150]°C
THERM_ENRICH_ADDR       = 0x02AA42  # 8×7 u16 LE /64 = %

_THERM_ENRICH_DEF = MapDef(
    name          = "Toplinsko obogacivanje goriva — visoka temp [%]",
    description   = (
        "Korekcija goriva pri prekoracenju temperature rashladne tekucine (CTS). "
        "8 temp. uvjeta (Y) × 7 load stupaca (X). "
        "Skala: raw/64 = % (195-210% = bogato za SC hladjenje). "
        "STG2 agresivno smanjuje (105-162%) — uklanja SC toplinsku zastitu. "
        "Dijagonalni pattern = ECU progresivno reducira zastitu po load stupcu. "
        "CTS os: [80..150]°C. Load X-os: [6400..16000] intern (isti format KFWIRKBA)."
    ),
    category      = "injection",
    rows=8, cols=7,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 64.0,
    offset_val    = 0.0,
    unit          = "% goriva",
    axis_x        = AxisDef(count=7, byte_order="LE", dtype="u16",
                             scale=1.0, unit="load [intern]",
                             values=[6400, 8000, 9600, 11200, 12800, 14400, 16000]),
    axis_y        = AxisDef(count=8, byte_order="LE", dtype="u16",
                             scale=1.0, unit="°C",
                             values=[80, 90, 100, 110, 120, 130, 140, 150]),
    raw_min       = 8192,   # 128%
    raw_max       = 16384,  # 256%
    mirror_offset = 0,
    notes         = (
        f"@ 0x{THERM_ENRICH_ADDR:06X} (8x7 u16 LE, 112B). "
        "X-os (load) @ 0x02AA02: [6400..16000] (7 val, korak 1600). "
        "Y-os (CTS) @ 0x02AA32: [80..150]°C (8 val). "
        "raw/64=%. ORI: 168-210% (SC toplinsko obogacivanje). "
        "STG2: 105-208% (smanjuje zastitu za performance). "
        "130hp/082806: potpuno drugaciji layout."
    ),
)


# ─── Efficiency correction after deadtime (Q15, 2D) — TODO ───────────────────
#
# Blok Q15 korekcijskih faktora odmah iza deadtime tablice @ 0x0259C4.
# Struktura: 7 preambula u16 (os?) + ~75 u16 podataka ≈ 82 u16 ukupno.
#   Preambula @ 0x0259C4: [13093, 16442, 19783, 24919, 30059, 35203, 43920]
#   Podaci @ 0x0259D2: ~75 u16, od kojih je 73 u Q15 rasponu (1.00–1.22)
#
# Pattern: dijagonalne vrijednosti (korekcija pada prema 1.000 za niže load).
# IDENTIČNO u ori_300 i stg2 (STG2 ne mijenja).
# 130hp: potpuno drugačiji sadržaj.
#
# Struktura potvrđena binarnim skanom (2026-03-16):
#   - 10 redova × 7 u16: col[0] = ugrađena Y-os (Q15 lambda?), col[1-6] = podaci
#   - X-os (preambula) @ 0x0259C4: [0.40,0.50,0.60,0.76,0.92,1.07,1.34] λ Q15
#   - Y-os (embedded, col[0]): row0=0.40, row1=1.10, row2=1.00, ... (neuređene)
#   - Dijagonalni pattern karakterističan za Bosch lambda Wirkungsgrad tablicu
#   - Odmah iza deadtime (0x025900–0x0259C2, 14×7)
# TODO: fizikalni smisao (A2L potrebno za potvrdu — moguće KFWIRKBA sub-table)

EFF_CORR_AXIS_ADDR = 0x0259C4   # 7× u16 Q15 X-os (lambda 0.40–1.34)
EFF_CORR_ADDR      = 0x0259D2   # 10×7 u16 Q15: col[0]=Y-os, col[1-6]=podaci

_EFF_CORR_DEF = MapDef(
    name          = "Lambda efikasnost — Q15 2D [TODO fizikalni smisao]",
    description   = (
        "2D Q15 lambda-efikasnost tablica odmah iza deadtime-a. "
        "Format: 10 redova × 7 u16 (col[0]=ugradjeni Y lambda, col[1-6]=faktori). "
        "X-os @ 0x0259C4: lambda [0.40, 0.50, 0.60, 0.76, 0.92, 1.07, 1.34]. "
        "Faktori Q15: 0.60–1.22 (efikasnost ub. + korekcija lambda). "
        "Dijagonalni pattern = KFWIRKBA-kompatibilni Bosch format. "
        "STG2 = ORI (nije modificirano — tuneri ne diraju). "
        "TODO: potvrditi fizikalni smisao s A2L — moguće KFWIRKBA sub-table."
    ),
    category      = "lambda",
    rows=10, cols=7,    # col[0] = ugrađena Y-os, col[1-6] = stvarni podaci
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "faktor Q15",
    axis_x        = AxisDef(count=7, byte_order="LE", dtype="u16",
                             scale=1.0 / 32768.0, unit="lambda",
                             values=[13093, 16442, 19783, 24919, 30059, 35203, 43920]),
    axis_y        = None,   # TODO: col[0] svakoga reda = embedded Y-os
    raw_min       = 19000,  # ~0.58 λ
    raw_max       = 50000,  # ~1.53 λ
    mirror_offset = 0,
    notes         = (
        f"@ 0x{EFF_CORR_ADDR:06X} (10×7 u16 Q15, 140B). X-os @ 0x{EFF_CORR_AXIS_ADDR:06X}. "
        "col[0] = ugradjeni Y-os (lambda Q15). Odmah iza deadtime 0x025900. "
        "Identično u ORI/STG2/082806. 130hp: drugaciji layout. "
        "TODO: fizikalni potvrda — KFWIRKBA ili IAT/CTS lambda correction."
    ),
)


# ─── Lambda efficiency sub-tablica A (0xFFFF bypass za SC) ───────────────────
#
# 63 u16 @ 0x025ADA: SVE = 65535 (0xFFFF) za 300hp SC — bypass/disabled.
# 130hp NA: Q15 vrijednosti ~0.855–0.926 = aktivna lambda Wirkungsgrad korekcija.
# Header u16 @ 0x025AD8 = 64 = separator byte između prethodnog i ovog bloka.
#
# Fizikalni smisao (potvrđeno cross-ref s 130hp):
#   300hp SC: ne koristi ovu korekciju — postavljeno na max (0xFFFF = bypass)
#   130hp NA: KFWIRKBA-kompatibilni lambda efficiency faktori 0.855–0.926
#
# Oba bloka (A @ 0x025ADA + B @ 0x025B58) zajedno čine KFWIRKBA lambda-eff
# sub-tablicu specifičnu za NA motore. SC motor ih oba ignorira (bypass).

OVERTEMP_LAMBDA_ADDR = 0x025ADA

_OVERTEMP_LAMBDA_DEF = MapDef(
    name          = "Lambda efikasnost sub-A (0xFFFF=SC bypass)",
    description   = (
        "Lambda Wirkungsgrad sub-tablica A — 63 u16 Q15. "
        "300hp SC: sve 0xFFFF = bypass (SC ne koristi ovu korekciju). "
        "130hp NA: aktivne Q15 vrijednosti ~0.855–0.926 (lambda efficiency). "
        "Odmah iza flat-16448 regije (0x025AD0–0x025AD6) i separator byte-a (0x025AD8=64). "
        "Zajedno sa sub-tablicom B (0x025B58) = KFWIRKBA NA motor efficiency sub-set."
    ),
    category      = "lambda",
    rows=1, cols=63,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "faktor Q15",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 27000,   # ~0.82 λ (NA) ili 65535 (SC)
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{OVERTEMP_LAMBDA_ADDR:06X} (63× u16 = 126B). "
        "SC: sve 0xFFFF. NA: Q15 0.855-0.926. "
        "Separator @ 0x025AD8 = 64. "
        "KFWIRKBA lambda efficiency sub-A (NA-specific)."
    ),
)


# ─── Lambda efficiency sub-tablica B (flat Q14≈1.004 za SC) ──────────────────
#
# 63 u16 @ 0x025B58: SVE = 16448 (Q14 = 1.004) za 300hp SC — praktički neutralno.
# 130hp NA: Q15 vrijednosti ~0.855–0.933 = aktivna KFWIRKBA sub-tablica B.
#
# Odmah iza sub-tablice A (0x025ADA + 63×2 = 0x025B56, + 2B gap = 0x025B58).
# 300hp: oba bloka (A + B) zajedno = KFWIRKBA lambda efficiency za NA motor
# SC motor koristi bypass (A=0xFFFF, B=1.004≈neutral).

NEUTRAL_CORR_ADDR = 0x025B58

_NEUTRAL_CORR_DEF = MapDef(
    name          = "Lambda efikasnost sub-B (Q14=1.004 za SC)",
    description   = (
        "Lambda Wirkungsgrad sub-tablica B — 63 u16 Q14. "
        "300hp SC: flat 16448 = Q14 1.004 (+0.4%, neutralno = bypass). "
        "130hp NA: aktivne Q15 vrijednosti ~0.855–0.933 (lambda efficiency). "
        "Odmah iza sub-tablice A (0x025ADA + 126B + 2B gap). "
        "Zajedno s sub-A = KFWIRKBA lambda efficiency za NA motore. "
        "SC motor ne koristi — oba bloka efektivno bypassana."
    ),
    category      = "lambda",
    rows=1, cols=63,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 16384.0,
    offset_val    = -100.0,
    unit          = "% (Q14)",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 14000,
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{NEUTRAL_CORR_ADDR:06X} (63× u16 = 126B). "
        "300hp SC: flat 16448 = Q14 1.004. "
        "130hp NA: Q15 0.855-0.933. "
        "KFWIRKBA lambda efficiency sub-B (NA-specific, SC bypass)."
    ),
)


# ─── SC boost fuel factor (flat Q14=1.224 = +22.4% for 300hp) ────────────────
#
# 40 u16 @ 0x025DF8: SVE = 20046 (Q14 = 1.224 = +22.4%) za 300hp SC.
# 130hp NA + 8-pt os ispred: SVE = 0 (tablica nije aktivna za NA motor).
# STG2: identično (tuneri ne diraju ovu kalibraciju).
#
# Lambda os (8 točaka) ispred @ 0x025DE8: [22352,25693,29035,32632,35973,39315,42912,48045]
#   Q15 = [0.682, 0.784, 0.886, 0.996, 1.098, 1.200, 1.310, 1.466]
#   Raspon: lambda 0.68–1.47 (SC motor pokriva širi lambda raspon)
#   130hp NA: os i data su SVE NULE (ova regija nije aktivna za NA)
#
# Fizikalni smisao: BAZNA SC KOREKCIJA GORIVA po lambdi = +22.4% za SC motor
#   vs. NA motor koji ne koristi ovu tablicu (sve 0).
#   Moguće: KFMSWSC (SC base fuel offset) ili lambda-indexed SC enrichment.
# Lokacija: neposredno ispred TEMP_FUEL tablice (0x025E50).

SC_BOOST_FACTOR_AXIS_ADDR = 0x025DE8  # 8× u16 Q15 lambda os
SC_BOOST_FACTOR_ADDR      = 0x025DF8  # 40× u16 Q14 (+22.4% za SC)

_SC_BOOST_FACTOR_DEF = MapDef(
    name          = "SC bazno obogacivanje po lambdi (+22.4%)",
    description   = (
        "Bazna SC korekcija goriva — 40 u16 flat = 20046 (Q14 = 1.224 = +22.4%). "
        "130hp NA: sve nule (tablica nije aktivna). "
        "STG2 = ORI (tuneri ne mijenjaju). "
        "Lambda os (8 tocaka) @ 0x025DE8: [0.682, 0.784, 0.886, 0.996, 1.098, 1.200, 1.310, 1.466]. "
        "SC motor koristi ovu korekciju neovisno o lambda uvjetu (+22.4% flat). "
        "NA motor ne aktivira ovu tablicu (sve 0 — nema SC enrichment)."
    ),
    category      = "injection",
    rows=1, cols=40,
    byte_order    = "LE", dtype = "u16",
    scale         = 100.0 / 16384.0,
    offset_val    = -100.0,
    unit          = "% (Q14)",
    axis_x        = AxisDef(count=8, byte_order="LE", dtype="u16",
                             scale=1.0 / 32768.0, unit="lambda",
                             values=[22352, 25693, 29035, 32632, 35973, 39315, 42912, 48045]),
    axis_y        = None,
    raw_min       = 0,       # NA motor: 0
    raw_max       = 24576,   # SC ~150%
    mirror_offset = 0,
    notes         = (
        f"@ 0x{SC_BOOST_FACTOR_ADDR:06X} (40× u16 = 80B). "
        f"Lambda os (8pt) @ 0x{SC_BOOST_FACTOR_AXIS_ADDR:06X}: [0.682..1.466] Q15. "
        "300hp SC: flat 20046 = Q14 +22.4%. "
        "130hp NA: sve 0 (os i data). STG2: identican kao ORI. "
        "Bazna SC enrichment korekcija. A2L naziv: moguće KFMSWSC ili SC lambda correction."
    ),
)


# ─── Lambda efficiency (KFWIRKBA) — 41×18 uniformna matrica ──────────────────
#
# Tablica @ 0x02AE40–0x02B421. Uniformna 41×18 matrica (LE u16 Q15).
# Y-os (load, 15 vrijednosti) @ 0x02AE40:
#   [3840,4480,5120,5760,6400,7040,7680,8320,8960,9600,10240,11520,12800,14080,15360]
# X-os (lambda, 18 točaka Q15):
#   [21627,24186,26605,29158,31174,32652,35204,36749,38765,40580,42125,
#    44342,47029,49152,52756,55509,58982,58982]
#   = [0.66, 0.74, 0.81, 0.89, 0.95, 1.00, 1.07, 1.12, 1.18, 1.24, 1.29,
#      1.35, 1.44, 1.50, 1.61, 1.69, 1.80, 1.80]
#
# STG2: sve vrijednosti λ>1.0 (x-indeksi 6-17) → 0xFFFF (lean bypass).
# Efekt: ECU ignorira lean-side korekciju efikasnosti (max power priority).
# Napomena: redovi 9-11 i 20-21 sadrže Y-os nastavke (Bosch multi-axis format).
# Podaci @ 0x02AE5E = 0x02AE40 + 30B (iza Y-osi), 41×18×2 = 1476B.

LAMBDA_EFF_YAXIS_ADDR = 0x02AE40  # 15× u16 LE load Y-os
LAMBDA_EFF_ADDR       = 0x02AE5E  # 41×18 u16 LE podaci

_LAMBDA_EFF_DEF = MapDef(
    name          = "Lambda efikasnost (KFWIRKBA) — 41×18 Q15",
    description   = (
        "Lambda Wirkungsgrad (efficiency) tablica — 41×18 uniformna matrica. "
        "X-os (lambda, 18 tocaka Q15): 0.66-1.80. "
        "Y-os (load, 15 vrijednosti @ 0x02AE40): 3840-15360. "
        "STG2: lambda>1.0 (lean side) → 0xFFFF — uklanja lean korekciju. "
        "Fizikalni smisao: ECU skalira injection po lambda efikasnosti. "
        "Redovi 9-11 i 20-21 sadrze Y-os nastavke (Bosch multi-axis)."
    ),
    category      = "lambda",
    rows=41, cols=18,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "faktor Q15",
    axis_x        = AxisDef(count=18, byte_order="LE", dtype="u16",
                             scale=1.0 / 32768.0, unit="lambda",
                             values=[21627, 24186, 26605, 29158, 31174, 32652,
                                     35204, 36749, 38765, 40580, 42125, 44342,
                                     47029, 49152, 52756, 55509, 58982, 58982]),
    axis_y        = AxisDef(count=15, byte_order="LE", dtype="u16",
                             scale=1.0, unit="load",
                             values=[3840, 4480, 5120, 5760, 6400, 7040, 7680,
                                     8320, 8960, 9600, 10240, 11520, 12800, 14080, 15360]),
    raw_min       = 0,
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        "@ 0x02AE5E-0x02B421 (1476B). Y-os @ 0x02AE40 (15 load val). "
        "STG2: lean (lambda>1.0) na 0xFFFF. A2L: KFWIRKBA."
    ),
)


# ─── Start injection (cranking fuel) — 1D ────────────────────────────────────
#
# 1D tablica goriva pri pokretanju motora (cranking) @ 0x025CDC.
# Format: 6× u16 LE osa + 6× u16 LE podaci = 12 u16 = 24 bajta.
# Mirror odmah iza: 0x025CF6 (offset +0x1A = 26B, uključujući 2B separator).
#
# Os (6 točaka): [0, 1024, 1707, 3413, 5120, 7680] — neidentificirana (CTS? RPM?)
# Podaci: [1732, 2581, 3045, 7108, 10765, 18404]
# Rastuć os → rastuće vrijednosti (hladniji uvjet = više goriva pri cranking-u?).
#
# STG2 i ORI: IDENTIČNI — nije touchiran.
# 130hp, 082806: potpuno drugačiji sadržaj na istoj adresi (drugi layout).

START_INJ_ADDR = 0x025CDC

_START_INJ_DEF = MapDef(
    name          = "Start — gorivo pri pokretanju (1D) [raw]",
    description   = (
        "Kranking gorivo (start injection) — 1D tablica, 6 RPM točaka. "
        "Format: ugrađena 6-točkovna RPM os + 6 podatkovnih vrijednosti. "
        "RPM os: [0, 1024, 1707, 3413, 5120, 7680] rpm — isti encoding kao globalna RPM os. "
        "1707 rpm = idle, 7680 rpm = gornji raspon. "
        "Podaci: rastuće injekcijske vrijednosti (1732–18404 raw) — vise goriva pri visem RPM. "
        "Mirror na 0x025CF6 (+0x1A od baze). "
        "STG2 ne mijenja — identično u svim SC varijantama."
    ),
    category      = "injection",
    rows=1, cols=6,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw",
    axis_x        = AxisDef(count=6, byte_order="LE", dtype="u16",
                             scale=1.0, unit="rpm",
                             values=[0, 1024, 1707, 3413, 5120, 7680]),
    axis_y        = None,
    raw_min       = 0,
    raw_max       = 65535,
    mirror_offset = 0x1A,
    notes         = (
        f"@ 0x{START_INJ_ADDR:06X} (12× u16: 6 os + 6 podaci, 24B). "
        "Mirror @ 0x025CF6 (+0x1A). RPM os — isti encoding kao globalna RPM os. "
        "STG2=ORI. 130hp/082806 ima razliciti layout na istoj adresi."
    ),
)


# ─── Ignition correction / efficiency (2D u8) ─────────────────────────────────
#
# 8×8 u8 tablica korekcije paljenja @ 0x022364.
# Ispred tablice su ugrađene 2 osi (svaka 8× u8):
#   Y os @ 0x022364: [75, 100, 150, 163, 175, 181, 188, 200]
#   X os @ 0x02236C: [53, 80, 107, 120, 147, 187, 227, 255]
#   Podaci @ 0x022374: 8×8 u8 = 64 bajta (kraj @ 0x0223B3)
#
# Vrijednosti: 145–200 (u8). STG2 capuje sve >180 na 180.
# Interpretacija: moguće knock retard limit ili ignition efficiency factor.
# Pozicija u binariju: odmah iza rev-limiter zone (0x022096–0x0220C0).
# 130hp: potpuno drugačiji sadržaj — aktivno kalibriran po HP varijanti.
#
# Skaliranje: nepoznato bez A2L. Vrijednosti ≈ efekt kuta (°BTDC × faktor?).

IGN_CORR_ADDR = 0x022374   # Start podatkovnog dijela (poslije 2×8B osi)
IGN_CORR_AXIS_ADDR = 0x022364  # Y-os (prva os, 8× u8)

_IGN_CORR_DEF = MapDef(
    name          = "Paljenje — korekcija/efikasnost (2D u8)",
    description   = (
        "2D korekcijska tablica paljenja — 8×8 u8 vrijednosti. "
        "Osi ugrađene kao u8 ispred podataka (nije standardni format). "
        "Y os: [75,100,150,163,175,181,188,200] (load/ETA?). "
        "X os: [53,80,107,120,147,187,227,255] (temp/RPM?). "
        "ORI: 145–200, STG2 capuje sve >180 = maksimalni sigurnosni limit. "
        "Fizikalni smisao: knock retard limit ili ignition efficiency (bez A2L). "
        "Razlikuje se između 300hp i 130hp — aktivno kalibriran."
    ),
    category      = "ignition",
    rows=8, cols=8,
    byte_order    = "LE", dtype = "u8",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw (u8)",
    axis_x        = AxisDef(count=8, byte_order="LE", dtype="u8",
                             scale=1.0, unit="?",
                             values=[53, 80, 107, 120, 147, 187, 227, 255]),
    axis_y        = AxisDef(count=8, byte_order="LE", dtype="u8",
                             scale=1.0, unit="?",
                             values=[75, 100, 150, 163, 175, 181, 188, 200]),
    raw_min       = 100,
    raw_max       = 255,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{IGN_CORR_ADDR:06X} (8×8 u8 = 64B). Osi @ 0x{IGN_CORR_AXIS_ADDR:06X} (2×8 u8). "
        "STG2 cap: sve vrijednosti >180 → 180 (knock protection). "
        "Os iza 0x022360: [7,0,8,8] su tail prethodnog bloka. "
        "A2L naziv nepoznat — moguće KFZW2 (Zündwinkelkorrektur) ili KFWIRKBA."
    ),
)


# ─── Torque optimal / driver demand mapa ──────────────────────────────────────
#
# Blok Q8 vrijednosti @ 0x02A7F0 (odmah iza torque mirrora) — 93–107% raspon.
# Torque mirror (0x02A5F0) završava na 0x02A5F0 + 512B = 0x02A7F0 — ODMAH iza!
# 300hp: 93.0–107.0%, 230hp: 90.6–107.8%, 130hp: 92.2–107.7%
# NPRo STG2: pomiče na 93.0–107.0% (malo drugačije raspoređeno)
#
# BitEdit lista za ME17.8.5 ima "Optimal torque" — ovo je DRUGI torque blok.
# Mogući fizikalni smisao: torque efficiency korekcija ili driver demand torque
# (KFWDKMSN/KFOPTTURB — optimalni torque po uvjetu paljenja/lambda).

TORQUE_OPT_ADDR = 0x02A7F0

_TORQUE_OPT_DEF = MapDef(
    name          = "Torque optimal / driver demand [%]",
    description   = (
        "Drugi torque blok odmah iza torque mirrora — Q8 format, 93–107% raspon. "
        "Manji raspon od glavne torque mape (93–119%). "
        "Moguće: 'Optimal torque' ili 'Driver demand torque' (BitEdit ME17.8.5). "
        "300hp: 93–107%, 230hp: 90–108%, 130hp: 92–108%. "
        "Razlikuje se po HP varijanti — aktivno kalibriran."
    ),
    category      = "torque",
    rows=16, cols=16,
    byte_order    = "BE", dtype = "u16",
    scale         = 100.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "%",
    axis_x        = _RPM_AXIS_16,
    axis_y        = _LOAD_AXIS_16,
    raw_min       = 24576,   # 75%
    raw_max       = 40960,   # 125%
    mirror_offset = 0,
    notes         = (
        f"@ 0x{TORQUE_OPT_ADDR:06X}. Odmah iza torque mirrora (0x02A7F0). "
        "Q8 format: raw × 100/32768 = %. LSB uvijek 0x00. "
        "BitEdit naziv: 'Optimal torque'. "
        "300hp ORI: 93-107%, STG2: slicno ali preraspoređeno. "
        "A2L potvrda potrebna za tocne osi i fizikalni smisao."
    ),
)


# ─── Injector deadtime ────────────────────────────────────────────────────────
#
# Hardware konstanta — ne tunable! Kompenzira kašnjenje otvaranja injektora.
# 7 kolona × ~20 redova u16 LE @ 0x025900 (struktura procjenjena, bez A2L).
# Identično u svim SW varijantama (hardware-fixed karakteristika injektora).
#
# Kontekst ME17 standard (ASAP2: TVKL — "Totzeitkennlinie"):
#   X os = napon baterije (battery voltage), Y os = temperatura/uvjet
#   Vrijednosti = kašnjenje u µs (tipično 0.5–2.5 ms za high-impedancije injektore)

DEADTIME_ADDR = 0x025900

_DEADTIME_DEF = MapDef(
    name          = "Injektori — deadtime korekcija (read-only)",
    description   = (
        "Kašnjenje otvaranja injektora (deadtime / Totzeit) — hardware konstanta. "
        "NE MIJENJATI — kalibrirano za fizičke injektore (330cc/min). "
        "7 kolona, ~20 redova (u16 LE). X os: napon baterije. "
        "ECU automatski kompenzira za napon pri svakom ubrizgavanju. "
        "Identično u svim SW varijantama (130/170/230/300hp)."
    ),
    category      = "misc",
    rows=14, cols=7,
    byte_order    = "LE", dtype = "u16",
    scale         = 0.001,     # procjena: µs ili ms, A2L needed
    offset_val    = 0.0,
    unit          = "µs (est.)",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 0,
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{DEADTIME_ADDR:06X}. Hardware konstanta — NE EDITIRATI. "
        "98 u16 = 14×7 (potvrdjeno binarnim skanom: prvi >3000 @ idx 98). "
        "Identično u svim analiziranim SW varijantama. "
        "ME17 ASAP2 naziv: TVKL (Totzeitkennlinie)."
    ),
)


# ─── DFCO (Deceleration Fuel Cut-Off) pragovi ─────────────────────────────────
#
# 7 RPM prag vrijednosti @ 0x02202E (u16 LE, direktni RPM, bez skale).
# Razlikuje se po HP varijanti:
#   130/170hp:  [853, 1067, 1280, 1493, 1707, 2133, 2560]
#   300hp:      [1067, 1280, 1493, 1707, 2133, 2560, 3413]
#
# Fizikalni smisao: ECU prekida ubrizgavanje (fuel cut) pri deceleraciji
# ispod ovih RPM pragova, ovisno o uvjetu (temperature, throttle position, gear).

DFCO_ADDR = 0x02202E

_DFCO_DEF = MapDef(
    name          = "DFCO — pragovi isključivanja goriva",
    description   = (
        "RPM pragovi za Deceleration Fuel Cut-Off (DFCO) — 7 vrijednosti. "
        "ECU prekida ubrizgavanje pri padu RPM ispod ovih pragova pri deceleraciji. "
        "130/170hp: [853–2560 rpm] (niži pragovi — ranije aktivacija DFCO). "
        "300hp: [1067–3413 rpm] (viši pragovi — konzervativnija DFCO za SC motor). "
        "Povećanje vrijednosti = DFCO aktivniji na višim RPM = manje goriva pri usporavanju."
    ),
    category      = "misc",
    rows=1, cols=7,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "rpm",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 500,
    raw_max       = 5000,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{DFCO_ADDR:06X} (7× u16 LE, direktni RPM). "
        "130/170hp: [853, 1067, 1280, 1493, 1707, 2133, 2560]. "
        "300hp: [1067, 1280, 1493, 1707, 2133, 2560, 3413]. "
        "ME17 ASAP2 naziv: NLLSOL (Leerlaufdrehzahlsollwert). "
        "DFCO smanjuje potrošnju i emisije — promjena utječe na osjet deceleracije."
    ),
)


# ─── Idle RPM target ──────────────────────────────────────────────────────────
#
# Tablica ciljnog ralantija — 5×12 u16 LE @ 0x02B600.
# Vrijednosti direktno u RPM (bez skale): 1840–3340 rpm.
# Identično u svim analiziranim SW varijantama (130/170/230/300hp).
#
# 5 redova: vjerojatno uvjeti (CTS temp, AC load, neutral, gear...),
# 12 kolona: vjerojatno temperaturni ili vremenski stupnjevi.
#
# Napomena: ECU specs kažu 1700±50 rpm, ali firmware pokazuje 1840 rpm
# (SC parasitni gubitak ~140 rpm kompenzira ECU setpointom).

IDLE_RPM_ADDR = 0x02B600

_IDLE_RPM_DEF = MapDef(
    name          = "Ralanti — ciljni RPM",
    description   = (
        "Ciljni RPM ralantija — 5×12 tablica (u16 LE, direktni RPM). "
        "ECU regulira prigušni ventil i paljenje prema ovim setpointima. "
        "Raspon: 1840–3340 rpm (topli ralanti ~1840, hladni start ~3340). "
        "Identično u svim SW varijantama (130/170/230/300hp). "
        "5 redova: uvjeti rada (temperatura, AC, neutral, gear...). "
        "12 kolona: temperaturni/vremenski stupnjevi."
    ),
    category      = "misc",
    rows=5, cols=12,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "rpm",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 600,
    raw_max       = 4500,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{IDLE_RPM_ADDR:06X} (5×12 u16 LE, direktni RPM, bez skale). "
        "Identično u svim 9 analiziranih SW varijanti. "
        "Topli ralanti: ~1840 rpm (ECU spec kaže 1700, razlika = SC parasitni gubitak). "
        "Hladni start: ~3340 rpm. Dimenzije potvrđene binarnim skanom. "
        "ME17 ASAP2 naziv: NLLSOL (ciljni RPM ralantija)."
    ),
)


# ─── Spark 900 ACE — mape ─────────────────────────────────────────────────────
#
# SW ID: "1037544876" (NPRo STG2), "1037525897" (ORI 2014)
# Sve adrese verificirane na npro_stg2_spark.bin (0x178000 B)
#
# Injection struktura (potvrđena mirror analizom):
#   RPM os (20pt): 0x02225A, u16 LE, 1920-6656 RPM (raw/4)
#   Load os (30pt): 0x022282, u16 LE, 3999-33600
#   Injection data: 0x0222BE, 30×20, u16 LE, range 479-4443 µs
#   Mirror: +0x518 = 0x0227D6 (potvrđeno 0 diffs na 600 u16)
#
# Ignition (6 karti, 12×12 u8, 0.75°/bit):
#   Base: 0x026A76, stride: 0x90 (=144B), range 12-57 (9°-42.75°BTDC)
#   Mirror: +0x140 od base (potvrđeno za karti 0-5)
#
# Lambda (open-loop AFR cilj, 4 kopije):
#   Primary: 0x025F5C, 8×16, u16 LE Q15, λ 0.737-1.004
#   Copies: +0x122 svaka (0x025F5C / 0x02607E / 0x0261A0 / 0x0262C2)

_SPARK_INJ_RPM_AXIS_DEF = MapDef(
    name         = "Spark RPM os (20pt)",
    description  = "Spark 900 ACE RPM osa za injection mape. 20 točaka, u16 LE. "
                   "Stvarni RPM = raw / 4. Raspon: 1920-6656 RPM.",
    category     = "axis",
    rows=1, cols=20,
    byte_order   = "LE", dtype = "u16",
    scale        = 0.25,
    offset_val   = 0.0,
    unit         = "RPM",
    raw_min      = 7680, raw_max = 26624,
    notes        = "@ 0x02225A. RPM = raw/4. 20 točaka: 1920-6656 RPM.",
)

_SPARK_INJ_LOAD_AXIS_DEF = MapDef(
    name         = "Spark load os (30pt)",
    description  = "Spark 900 ACE load osa za injection mape. 30 točaka, u16 LE. "
                   "Raspon: 3999-33600 (relativno opterećenje).",
    category     = "axis",
    rows=1, cols=30,
    byte_order   = "LE", dtype = "u16",
    scale        = 1.0,
    offset_val   = 0.0,
    unit         = "",
    raw_min      = 3999, raw_max = 33600,
    notes        = "@ 0x022282. 30 točaka: 3999-33600.",
)

_SPARK_INJ_DEF = MapDef(
    name          = "Spark ubrizgavanje (KFTIUP) [µs]",
    description   = (
        "Spark 900 ACE injection map. 30×20 tablica (load × RPM). "
        "Vrijednosti u µs ili BRP internim jedinicama. "
        "Veće vrijednosti = dulje ubrizgavanje = više goriva. "
        "ORI raspon: 479-4443, STG2 raspon slično. "
        "Osi: Y = opterećenje (30pt @ 0x022282), X = RPM (20pt @ 0x02225A)."
    ),
    category      = "injection",
    rows=30, cols=20,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "µs",
    raw_min       = 400, raw_max = 5000,
    mirror_offset = 0x518,
    notes         = (
        "Spark 900 ACE. Primary @ 0x0222BE, mirror @ 0x0227D6 (+0x518). "
        "Mirror potvrđen: 0 razlika na 600 u16 vrijednosti. "
        "RPM os 20pt @ 0x02225A (raw/4=RPM, 1920-6656). "
        "Load os 30pt @ 0x022282 (3999-33600)."
    ),
)

_SPARK_IGN_NAMES = [
    "base_low_load",
    "base_mid_load",
    "base_high_load",
    "boost_low",
    "boost_mid",
    "idle",
]

def _make_spark_ign_def(idx: int) -> MapDef:
    addr = 0x026A76 + idx * 0x90
    return MapDef(
        name          = f"Spark paljenje #{idx:02d} [{_SPARK_IGN_NAMES[idx] if idx < len(_SPARK_IGN_NAMES) else 'map'}]",
        description   = (
            f"Spark 900 ACE ignition mapa #{idx}. 12×12 u8, 0.75°/bit. "
            f"Vrijednosti 12-57 = 9°-42.75° pred TMT. "
            f"Smanjiti za detonacije, povećati pažljivo za performanse. "
            f"Mirror na +0x140 od base."
        ),
        category      = "ignition",
        rows=12, cols=12,
        byte_order    = "LE", dtype = "u8",
        scale         = 0.75,
        offset_val    = 0.0,
        unit          = "° BTDC",
        raw_min       = 10, raw_max = 60,
        notes         = f"Spark 900. @ 0x{addr:06X}, stride=0x90. Mirror na 0x{addr+0x140:06X}.",
    )

_SPARK_IGN_DEFS = [_make_spark_ign_def(i) for i in range(6)]

_SPARK_LAMBDA_DEF = MapDef(
    name          = "Spark lambda cilj (open-loop) [λ]",
    description   = (
        "Spark 900 ACE open-loop AFR korekcija. 8×16 tablica. "
        "Q15 format: 32768 = 1.0 (λ=1.0, stoichiometric AFR=14.7). "
        "Vrijednosti <32768 = bogato (više goriva), >32768 = siromasno. "
        "Raspon: 0.737–1.004 λ. 4 identične kopije."
    ),
    category      = "lambda",
    rows=8, cols=16,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "λ",
    raw_min       = 24000, raw_max = 33000,
    mirror_offset = 0x122,
    notes         = (
        "Spark 900 ACE. 4 kopije: @ 0x025F5C / 0x02607E / 0x0261A0 / 0x0262C2. "
        "Offset između kopija: +0x122 (290B). Svaka kopija 256B (8×16×2). "
        "Lambda = raw / 32768. Ne postoji fizička lambda sonda!"
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
        is_spark = self._sw().startswith("1037") and not self._sw().startswith("10SW")

        if is_spark:
            # Spark 900 ACE mape (SW: 1037xxxxxx)
            if progress_cb: progress_cb(f"Spark 900 ACE SW detektiran ({self._sw()})...")
            self._scan_spark_injection(progress_cb)
            self._scan_spark_ignition(progress_cb)
            self._scan_spark_lambda(progress_cb)
        else:
            # 300hp / 260hp ACE 1630 mape (SW: 10SWxxxxxx ili nepoznat)
            self._scan_rpm_axes(progress_cb)
            self._scan_rev_limiter_known(progress_cb)
            self._scan_rev_limiter_heuristic(progress_cb)
            self._scan_ignition(progress_cb)
            self._scan_injection(progress_cb)
            self._scan_torque(progress_cb)
            self._scan_lambda(progress_cb)
            self._scan_sc(progress_cb)
            self._scan_cold_start(progress_cb)
            self._scan_knock_params(progress_cb)
            self._scan_cts_temp_axis(progress_cb)
            self._scan_sc_correction(progress_cb)
            self._scan_temp_fuel(progress_cb)
            self._scan_lambda_bias(progress_cb)
            self._scan_lambda_prot(progress_cb)
            self._scan_lambda_trim(progress_cb)
            self._scan_torque_opt(progress_cb)
            self._scan_deadtime(progress_cb)
            self._scan_dfco(progress_cb)
            self._scan_idle_rpm(progress_cb)
            self._scan_accel_enrich(progress_cb)
            self._scan_start_inj(progress_cb)
            self._scan_ign_corr(progress_cb)
            self._scan_therm_enrich(progress_cb)
            self._scan_eff_corr(progress_cb)
            self._scan_overtemp_lambda(progress_cb)
            self._scan_neutral_corr(progress_cb)
            self._scan_sc_boost_factor(progress_cb)
            self._scan_lambda_eff(progress_cb)
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

            # Validacija: knock mape (idx 8,9) imaju retard delta 0-40,
            # normalne timing mape imaju raspon 16-58 (12°–43.5° BTDC).
            # Uvjetne/parcijalne mape (idx 18) imaju 0-58 raspon, niski threshold.
            # Soft threshold: >=80% vrijednosti mora biti u rasponu (robusno na padding/boundary data)
            is_knock   = idx in (8, 9)
            is_partial = idx == 18
            if is_knock or is_partial:
                in_range = sum(1 for v in raw if 0 <= v <= 58)
                threshold = 0.40  # parcijalne mape imaju mnogo nula
            else:
                in_range = sum(1 for v in raw if 16 <= v <= 58)
                threshold = 0.80
            valid_frac = in_range / len(raw)
            if valid_frac < threshold:
                if cb: cb(f"  Ignition #{idx:02d} @ 0x{addr:06X}: "
                          f"validacija pala ({in_range}/{len(raw)} = {valid_frac:.0%}) — preskacam")
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
        n    = _INJ_DEF.rows * _INJ_DEF.cols   # 16 × 12 = 192
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
        if cb: cb(f"  Injection @ 0x{addr:06X}  16x12  raw=[{min(vals)}-{max(vals)}]"
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

    # ── SC bypass scan ────────────────────────────────────────────────────────

    def _scan_sc(self, cb=None):
        if cb: cb("Trazim SC bypass mapu...")
        data = self.eng.get_bytes()

        addr = SC_MAIN
        n    = _SC_DEF.rows * _SC_DEF.cols  # 7 × 7 = 49
        if addr + n > len(data):
            if cb: cb("  SC: adresa van granica fajla")
            return

        vals = list(data[addr:addr + n])

        # Validacija: mora imati mijesane vrijednosti (nije sve nula ili sve 255)
        non_trivial = sum(1 for v in vals if 0 < v < 255)
        if non_trivial < n // 4:
            if cb: cb(f"  SC @ 0x{addr:06X}: nedovoljno raznolikih vrijednosti — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _SC_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  SC bypass @ 0x{addr:06X}  7x7  raw=[{min(vals)}-{max(vals)}]"
                  f"  mirror @ 0x{SC_MIRROR:06X}")

        # Treća kopija @ SC_EXTRA
        if SC_EXTRA + n <= len(data):
            vals2 = list(data[SC_EXTRA:SC_EXTRA + n])
            non_trivial2 = sum(1 for v in vals2 if 0 < v < 255)
            if non_trivial2 >= n // 4:
                extra_def = MapDef(
                    name          = "SC bypass ventil — extra kopija [%]",
                    description   = _SC_DEF.description + " (3. kopija @ 0x029993, moguce alternativni uvjeti/rezim)",
                    category      = "misc",
                    rows=7, cols=7,
                    byte_order    = "BE", dtype = "u8",
                    scale         = 100.0 / 255.0, unit = "% bypass",
                    axis_x        = _SC_X_AXIS,
                    axis_y        = _SC_Y_AXIS,
                    raw_min       = 0, raw_max = 255,
                    mirror_offset = 0,
                    notes         = f"Extra kopija @ 0x{SC_EXTRA:06X}. NPRo mijenja i ovu kopiju s razlicitim vrijednostima.",
                )
                self.results.append(FoundMap(
                    defn    = extra_def,
                    address = SC_EXTRA,
                    sw_id   = self._sw(),
                    data    = vals2,
                ))
                if cb: cb(f"  SC extra  @ 0x{SC_EXTRA:06X}  7x7  raw=[{min(vals2)}-{max(vals2)}]")

    # ── Cold start enrichment scan ────────────────────────────────────────────

    def _scan_cold_start(self, cb=None):
        if cb: cb("Tražim cold start enrichment tablicu...")
        data = self.eng.get_bytes()

        addr = COLD_START_ADDR
        n = 6
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: mora imati raznolike vrijednosti (nije sve nule)
        if max(vals) == 0 or len(set(vals)) < 2:
            if cb: cb(f"  Cold start @ 0x{addr:06X}: nema valjanog sadržaja — preskačem")
            return

        self.results.append(FoundMap(
            defn    = _COLD_START_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Cold start @ 0x{addr:06X}  1×6  vals={vals}")

    # ── Knock parameters scan ─────────────────────────────────────────────────

    def _scan_knock_params(self, cb=None):
        if cb: cb("Tražim knock threshold parametre...")
        data = self.eng.get_bytes()

        addr = KNOCK_PARAMS_ADDR
        n = 24
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: tipični ORI sadržaj — barem jedan u rasponu 7000-50000
        valid = any(7000 <= v <= 50000 for v in vals)
        if not valid:
            if cb: cb(f"  Knock @ 0x{addr:06X}: nema valjanog sadržaja — preskačem")
            return

        self.results.append(FoundMap(
            defn    = _KNOCK_PARAMS_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Knock params @ 0x{addr:06X}  1×24  "
                  f"[0]={vals[0]}  [2]={vals[2]}  [3]={vals[3]}")

    # ── CTS temperature axis scan ─────────────────────────────────────────────

    def _scan_cts_temp_axis(self, cb=None):
        if cb: cb("Tražim CTS temperaturnu os...")
        data = self.eng.get_bytes()

        addr = CTS_TEMP_AXIS_ADDR
        n = 10
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: mora biti rastuća os u °C rasponu [20..200]
        if not (all(20 <= v <= 200 for v in vals) and self._monotone(vals)):
            if cb: cb(f"  CTS temp os @ 0x{addr:06X}: validacija pala — preskačem")
            return

        self.results.append(FoundMap(
            defn    = _CTS_TEMP_AXIS_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  CTS temp os @ 0x{addr:06X}  1×10  [{vals[0]}..{vals[-1]}]°C")

    # ── SC load injection correction scan ────────────────────────────────────

    def _scan_sc_correction(self, cb=None):
        if cb: cb("Tražim SC load injection correction...")
        data = self.eng.get_bytes()

        addr = SC_CORR_ADDR
        n    = _SC_CORR_DEF.rows * _SC_CORR_DEF.cols  # 9 × 7 = 63
        if addr + n * 2 > len(data):
            if cb: cb(f"  SC correction: adresa van granica fajla")
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: barem neke vrijednosti u Q14 rasponu korekcije
        in_range = sum(1 for v in vals if 4096 <= v <= 49152)
        if in_range < n // 2:
            if cb: cb(f"  SC correction @ 0x{addr:06X}: premalo Q14 vrijednosti — preskačem")
            return

        # Dinamički čitamo Y-os iz fajla (razlikuje se po SW: 300hp vs 130/230hp)
        y_vals = [int.from_bytes(data[SC_CORR_Y_ADDR + i*2: SC_CORR_Y_ADDR + i*2 + 2], 'little')
                  for i in range(9)]
        x_vals = [int.from_bytes(data[SC_CORR_X_ADDR + i*2: SC_CORR_X_ADDR + i*2 + 2], 'little')
                  for i in range(7)]
        y_axis = AxisDef(count=9, byte_order="LE", dtype="u16",
                         scale=1.0/64.0, unit="rl [%]", values=y_vals)
        x_axis = AxisDef(count=7, byte_order="LE", dtype="u16",
                         scale=1.0/8.0, unit="rpm", values=x_vals)

        from dataclasses import replace
        defn = replace(_SC_CORR_DEF, axis_x=x_axis, axis_y=y_axis)

        self.results.append(FoundMap(
            defn    = defn,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        vmin = min(vals) / 16384.0
        vmax = max(vals) / 16384.0
        y_pct = [round(v/64, 1) for v in y_vals]
        if cb: cb(f"  SC correction @ 0x{addr:06X}  9×7  factor=[{vmin:.3f}–{vmax:.3f}]"
                  f"  Y=[{y_pct[0]}–{y_pct[-1]}]rl%")

    # ── Temperature fuel correction scan ─────────────────────────────────────

    def _scan_temp_fuel(self, cb=None):
        if cb: cb("Tražim temperature fuel correction...")
        data = self.eng.get_bytes()

        addr = TEMP_FUEL_ADDR
        n    = _TEMP_FUEL_DEF.cols  # 156
        if addr + n * 2 > len(data):
            if cb: cb(f"  Temp fuel: adresa van granica fajla")
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: Q14 korekcija — barem 80% u rasponu 0.5×–2.0× (8192–32768)
        in_range = sum(1 for v in vals if 8192 <= v <= 32768)
        if in_range < int(n * 0.80):
            if cb: cb(f"  Temp fuel @ 0x{addr:06X}: premalo Q14 vrijednosti ({in_range}/{n}) — preskačem")
            return

        self.results.append(FoundMap(
            defn    = _TEMP_FUEL_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        vmin = min(vals) / 16384.0
        vmax = max(vals) / 16384.0
        if cb: cb(f"  Temp fuel @ 0x{addr:06X}  1×156  factor=[{vmin:.3f}–{vmax:.3f}]")

    # ── Lambda bias scan ──────────────────────────────────────────────────────

    def _scan_lambda_bias(self, cb=None):
        if cb: cb("Tražim lambda bias tablicu...")
        data = self.eng.get_bytes()

        addr = LAMBDA_BIAS_ADDR
        n    = _LAMBDA_BIAS_DEF.cols  # 141
        if addr + n * 2 > len(data):
            if cb: cb(f"  Lambda bias: adresa van granica fajla")
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: Q15 lambda 0.5–2.0 → raw 16384–65535
        in_range = sum(1 for v in vals if 16384 <= v <= 65535)
        if in_range < n // 2:
            if cb: cb(f"  Lambda bias @ 0x{addr:06X}: premalo Q15 vrijednosti — preskačem")
            return

        self.results.append(FoundMap(
            defn    = _LAMBDA_BIAS_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        avg = sum(vals) / len(vals) / 32768.0
        if cb: cb(f"  Lambda bias @ 0x{addr:06X}  1×141  avg_lambda={avg:.4f}")

    # ── Lambda protection / max injection scan ───────────────────────────────

    def _scan_lambda_prot(self, cb=None):
        if cb: cb("Trazim lambda zastitnu tablicu...")
        data = self.eng.get_bytes()

        addr = LAMBDA_PROT_ADDR
        n    = _LAMBDA_PROT_DEF.rows * _LAMBDA_PROT_DEF.cols  # 12×13 = 156
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: dijagonalni pattern — vrijednosti moraju biti rastuće u opsegu
        non_zero = sum(1 for v in vals if v > 100)
        if non_zero < n // 2:
            if cb: cb(f"  Lambda prot @ 0x{addr:06X}: previse nula — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _LAMBDA_PROT_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        vmin = min(vals) / 32768.0
        vmax = max(vals) / 32768.0
        if cb: cb(f"  Lambda prot @ 0x{addr:06X}  12x13  [{vmin:.3f}-{vmax:.3f}]")

    # ── Lambda trim scan ──────────────────────────────────────────────────────

    def _scan_lambda_trim(self, cb=None):
        if cb: cb("Trazim lambda trim tablicu...")
        data = self.eng.get_bytes()

        addr = LAMBDA_TRIM_ADDR
        n    = _LAMBDA_TRIM_DEF.rows * _LAMBDA_TRIM_DEF.cols  # 12×18 = 216
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: sve Q15 vrijednosti moraju biti u lambda opsegu 0.82–1.16
        # (raw 27000–38000). Lambda trim je uska korekcija, ne ide daleko od 1.0.
        in_range = sum(1 for v in vals if 25000 < v < 40000)
        if in_range < int(n * 0.90):
            if cb: cb(f"  Lambda trim @ 0x{addr:06X}: premalo Q15 vrijednosti ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _LAMBDA_TRIM_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        vmin = min(vals) / 32768.0
        vmax = max(vals) / 32768.0
        if cb: cb(f"  Lambda trim @ 0x{addr:06X}  12×18  lambda=[{vmin:.3f}–{vmax:.3f}]")

    # ── Acceleration enrichment scan ─────────────────────────────────────────

    def _scan_accel_enrich(self, cb=None):
        if cb: cb("Trazim ubrzavajuce obogacivanje...")
        data = self.eng.get_bytes()

        addr = ACCEL_ENRICH_ADDR
        # Format: 1B global + 5 redova × (1B marker + 6×u16 os + 5×u16 data) = 1 + 5×23 = 116B
        # + 21B footer = ukupno ~132B. Čitamo samo 5×5 data vrijednosti.
        ROWS, COLS = 5, 5
        AXIS_U16   = 6   # 6-tocka dTPS os ugradjene u svaki red
        ROW_BYTES  = (AXIS_U16 + COLS) * 2  # 22B po redu (6 axis + 5 data, sve u16 LE)

        if addr + 1 + ROWS * ROW_BYTES > len(data):
            return

        # Provjeri globalni bajt (4 ili 2)
        global_b = data[addr]
        if global_b not in (0x02, 0x04):
            if cb: cb(f"  Accel enrich @ 0x{addr:06X}: neocekivani global byte {global_b:#x} — preskacam")
            return

        # Izvadi 5×5 vrijednosti i ugradjenu os
        # Struktura: 1B global + 5×(6×u16 axis + 5×u16 data) = 1 + 5×22 = 111B
        import struct
        vals = []
        embedded_axis = None
        for row in range(ROWS):
            row_off = 1 + row * ROW_BYTES  # 1B global offset pa redovi
            axis_off = row_off             # os odmah na pocetku reda
            data_off = axis_off + AXIS_U16 * 2
            if embedded_axis is None:
                embedded_axis = [struct.unpack_from('<H', data, addr + axis_off + i*2)[0]
                                 for i in range(AXIS_U16)]
            for col in range(COLS):
                v = struct.unpack_from('<H', data, addr + data_off + col*2)[0]
                vals.append(v)

        # Validacija: Q14 faktori 0.3×–3.0× (4915–49152)
        in_range = sum(1 for v in vals if 4000 < v < 55000)
        if in_range < ROWS * COLS * 3 // 4:
            if cb: cb(f"  Accel enrich @ 0x{addr:06X}: validacija Q14 pala — preskacam")
            return

        # Dinamički ažuriraj X-os iz ugrađenih vrijednosti
        from dataclasses import replace
        x_axis = AxisDef(count=6, byte_order="LE", dtype="u16",
                         scale=1.0, unit="dTPS [°/s]", values=embedded_axis)
        defn = replace(_ACCEL_ENRICH_DEF, axis_x=x_axis)

        self.results.append(FoundMap(
            defn    = defn,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        vmin = min(vals) / 16384.0
        vmax = max(vals) / 16384.0
        if cb: cb(f"  Accel enrich @ 0x{addr:06X}  5×5  factor=[{vmin:.3f}–{vmax:.3f}]  "
                  f"dTPS_os={embedded_axis}")

    # ── Start injection scan ──────────────────────────────────────────────────

    def _scan_start_inj(self, cb=None):
        if cb: cb("Trazim start injection tablicu...")
        data = self.eng.get_bytes()

        addr   = START_INJ_ADDR
        N_AXIS = 6
        N_DATA = 6
        total  = N_AXIS + N_DATA  # 12 u16 = 24B

        if addr + total * 2 > len(data):
            return

        axis_vals = [int.from_bytes(data[addr + i*2: addr+i*2+2], 'little')
                     for i in range(N_AXIS)]
        data_vals = [int.from_bytes(data[addr + (N_AXIS+i)*2: addr+(N_AXIS+i)*2+2], 'little')
                     for i in range(N_DATA)]

        # Validacija: os mora biti rastuća, podaci > 0
        if not (self._monotone(axis_vals) and all(v > 0 for v in data_vals)):
            if cb: cb(f"  Start inj @ 0x{addr:06X}: validacija pala — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _START_INJ_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = data_vals,
        ))
        if cb: cb(f"  Start inj @ 0x{addr:06X}  1×6  axis={axis_vals}  data={data_vals}")

    # ── Ignition correction table (2D u8) scan ────────────────────────────────

    def _scan_ign_corr(self, cb=None):
        if cb: cb("Trazim ignition correction tablicu (2D u8)...")
        data = self.eng.get_bytes()

        axis_addr = IGN_CORR_AXIS_ADDR  # 2×8 u8 osi
        data_addr = IGN_CORR_ADDR       # 8×8 u8 podaci
        ROWS, COLS = 8, 8
        n = ROWS * COLS

        if data_addr + n > len(data):
            return

        y_axis = list(data[axis_addr:     axis_addr + COLS])
        x_axis = list(data[axis_addr + COLS: axis_addr + COLS*2])
        vals   = list(data[data_addr:     data_addr + n])

        # Validacija: obje osi rastuće, vrijednosti 100-255
        if not (self._monotone(y_axis) and self._monotone(x_axis)):
            if cb: cb(f"  Ign corr @ 0x{data_addr:06X}: osi nisu rastuće — preskacam")
            return
        in_range = sum(1 for v in vals if 100 <= v <= 255)
        if in_range < n * 3 // 4:
            if cb: cb(f"  Ign corr @ 0x{data_addr:06X}: validacija pala ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _IGN_CORR_DEF,
            address = data_addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Ign corr @ 0x{data_addr:06X}  8×8 u8  [{min(vals)}-{max(vals)}]")

    # ── Thermal fuel enrichment scan ─────────────────────────────────────────

    def _scan_therm_enrich(self, cb=None):
        if cb: cb("Trazim thermal fuel enrichment tablicu...")
        data = self.eng.get_bytes()

        xax_addr  = THERM_ENRICH_XAXIS_ADDR
        axis_addr = THERM_ENRICH_AXIS_ADDR
        addr      = THERM_ENRICH_ADDR
        ROWS, COLS = 8, 7
        n = ROWS * COLS

        if addr + n * 2 > len(data):
            return

        x_axis = [int.from_bytes(data[xax_addr + i*2: xax_addr+i*2+2], 'little')
                  for i in range(COLS)]
        y_axis = [int.from_bytes(data[axis_addr + i*2: axis_addr+i*2+2], 'little')
                  for i in range(ROWS)]
        vals   = [int.from_bytes(data[addr + i*2: addr+i*2+2], 'little')
                  for i in range(n)]

        # Validacija: X-os monotona load (6400-16000), Y-os rastuća CTS 70-160°C
        if not (self._monotone(x_axis) and 5000 <= x_axis[0] <= 8000 and x_axis[-1] <= 20000):
            if cb: cb(f"  Therm enrich @ 0x{addr:06X}: X-os validacija pala — preskacam")
            return
        if not (self._monotone(y_axis) and 60 <= y_axis[0] <= 100 and y_axis[-1] <= 200):
            if cb: cb(f"  Therm enrich @ 0x{addr:06X}: Y-os validacija pala — preskacam")
            return
        in_range = sum(1 for v in vals if 8000 <= v <= 17000)
        if in_range < n * 3 // 4:
            if cb: cb(f"  Therm enrich @ 0x{addr:06X}: vrijednosti van opsega ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _THERM_ENRICH_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        pct_min = min(vals) / 64
        pct_max = max(vals) / 64
        if cb: cb(f"  Therm enrich @ 0x{addr:06X}  8×7  [{pct_min:.0f}–{pct_max:.0f}%]  temp_os={y_axis}")

    # ── Efficiency correction (Q15, after deadtime) scan ─────────────────────

    def _scan_eff_corr(self, cb=None):
        if cb: cb("Trazim efficiency correction Q15 tablicu (iza deadtime)...")
        data = self.eng.get_bytes()

        # Provjeravamo preambulu (7 ugrađenih osi vrijednosti)
        ax_addr = EFF_CORR_AXIS_ADDR
        d_addr  = EFF_CORR_ADDR
        ROWS, COLS = 10, 7
        n = ROWS * COLS

        if d_addr + n * 2 > len(data):
            return

        preambula = [int.from_bytes(data[ax_addr + i*2: ax_addr+i*2+2], 'little')
                     for i in range(7)]
        vals = [int.from_bytes(data[d_addr + i*2: d_addr+i*2+2], 'little')
                for i in range(n)]

        # Validacija: preambula rastuća, >70% u Q15 rasponu (25000-50000)
        if not self._monotone(preambula):
            if cb: cb(f"  Eff corr @ 0x{ax_addr:06X}: preambula nije rastuća — preskacam")
            return
        in_range = sum(1 for v in vals if 25000 <= v <= 50000)
        if in_range < n * 7 // 10:
            if cb: cb(f"  Eff corr @ 0x{d_addr:06X}: Q15 validacija pala ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _EFF_CORR_DEF,
            address = d_addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        q15_min = min(v for v in vals if v > 1000) / 32768
        q15_max = max(vals) / 32768
        if cb: cb(f"  Eff corr @ 0x{d_addr:06X}  10×7 Q15  [{q15_min:.3f}–{q15_max:.3f}]")

    # ── Overtemp lambda disable (all-0xFFFF for SC) scan ─────────────────────

    def _scan_overtemp_lambda(self, cb=None):
        if cb: cb("Trazim overtemp lambda disable tablicu...")
        data = self.eng.get_bytes()

        addr = OVERTEMP_LAMBDA_ADDR
        n    = 63
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr+i*2+2], 'little') for i in range(n)]

        # Za SC 300hp: sve 0xFFFF — prihvaćamo i tu varijantu
        # Za 130hp NA: Q15 vrijednosti ~27000-32000
        all_ff  = sum(1 for v in vals if v == 65535)
        in_q15  = sum(1 for v in vals if 25000 <= v <= 35000)
        if all_ff < n // 2 and in_q15 < n // 2:
            if cb: cb(f"  Overtemp lambda @ 0x{addr:06X}: nije ni SC ni NA pattern — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _OVERTEMP_LAMBDA_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if all_ff > n // 2:
            if cb: cb(f"  Overtemp lambda @ 0x{addr:06X}  1×63  sve 0xFFFF (SC bypass)")
        else:
            if cb: cb(f"  Overtemp lambda @ 0x{addr:06X}  1×63  Q15=[{min(vals)}-{max(vals)}] (NA)")

    # ── Neutral correction factor (flat Q14 ~1.004) scan ─────────────────────

    def _scan_neutral_corr(self, cb=None):
        if cb: cb("Trazim neutral correction (flat Q14) tablicu...")
        data = self.eng.get_bytes()

        addr = NEUTRAL_CORR_ADDR
        n    = 63
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr+i*2+2], 'little') for i in range(n)]

        # 300hp: sve 16448 ili blizu; 130hp: Q15 raspršene vrijednosti
        flat_16k = sum(1 for v in vals if 14000 <= v <= 18000)
        if flat_16k < n // 2:
            if cb: cb(f"  Neutral corr @ 0x{addr:06X}: nije prepoznat pattern — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _NEUTRAL_CORR_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Neutral corr @ 0x{addr:06X}  1×63  flat={vals[0]} (Q14={vals[0]/16384:.3f})")

    # ── SC boost fuel factor (flat Q14=1.224) scan ────────────────────────────

    def _scan_sc_boost_factor(self, cb=None):
        if cb: cb("Trazim SC boost fuel factor tablicu...")
        data = self.eng.get_bytes()

        ax_addr = SC_BOOST_FACTOR_AXIS_ADDR
        addr    = SC_BOOST_FACTOR_ADDR
        n       = 40
        if addr + n * 2 > len(data):
            return

        # Validacija lambda osi (8× u16 Q15 na SC_BOOST_FACTOR_AXIS_ADDR)
        ax_vals = [int.from_bytes(data[ax_addr + i*2: ax_addr+i*2+2], 'little') for i in range(8)]
        vals    = [int.from_bytes(data[addr    + i*2: addr    +i*2+2], 'little') for i in range(n)]

        # 300hp: lambda os rastuća 22352-48045; 130hp: sve 0
        ax_ok   = self._monotone(ax_vals) and ax_vals[0] > 20000
        ax_zero = all(v == 0 for v in ax_vals)
        all_zero = all(v == 0 for v in vals)
        flat_sc  = sum(1 for v in vals if 16000 <= v <= 24000)

        if ax_zero and all_zero:
            # NA motor — os i podaci su nule
            self.results.append(FoundMap(
                defn=_SC_BOOST_FACTOR_DEF, address=addr, sw_id=self._sw(), data=vals))
            if cb: cb(f"  SC boost factor @ 0x{addr:06X}  1×40  sve 0 (NA motor)")
        elif (ax_ok or ax_zero) and flat_sc >= n * 3 // 4:
            self.results.append(FoundMap(
                defn=_SC_BOOST_FACTOR_DEF, address=addr, sw_id=self._sw(), data=vals))
            pct = vals[0] / 16384 * 100 - 100
            lam = f"{ax_vals[0]/32768:.3f}–{ax_vals[-1]/32768:.3f}" if ax_ok else "n/a"
            if cb: cb(f"  SC boost factor @ 0x{addr:06X}  1×40  flat={vals[0]} (+{pct:.1f}%)"
                      f"  lambda_os=[{lam}]")
        else:
            if cb: cb(f"  SC boost factor @ 0x{addr:06X}: nije prepoznat pattern — preskacam")

    # ── Lambda efficiency (KFWIRKBA) — 41×18 uniformna matrica ──────────────────

    def _scan_lambda_eff(self, cb=None):
        if cb: cb("Trazim lambda efficiency (KFWIRKBA) tablicu...")
        data = self.eng.get_bytes()

        yax_addr = LAMBDA_EFF_YAXIS_ADDR
        d_addr   = LAMBDA_EFF_ADDR
        ROWS, COLS = 41, 18
        n = ROWS * COLS

        if d_addr + n * 2 > len(data):
            return

        # Validacija Y-osi @ yax_addr (15 rastuće load vrijednosti, tipično 3840-15360)
        yax = [int.from_bytes(data[yax_addr + i*2: yax_addr+i*2+2], 'little') for i in range(15)]
        if not self._monotone(yax) or yax[0] < 1000 or yax[-1] > 30000:
            if cb: cb(f"  Lambda eff @ 0x{yax_addr:06X}: Y-os nije rastuci load — preskacam")
            return

        # Validacija prvog reda @ d_addr (18 Q15 lambda vrijednosti ~21627-58982)
        row0 = [int.from_bytes(data[d_addr + i*2: d_addr+i*2+2], 'little') for i in range(18)]
        lam_ok = sum(1 for v in row0 if 18000 <= v <= 65535)
        if lam_ok < 14:
            if cb: cb(f"  Lambda eff @ 0x{d_addr:06X}: red 0 nije lambda Q15 — preskacam")
            return

        # Citaj 41×18 = 738 u16
        vals = [int.from_bytes(data[d_addr + i*2: d_addr+i*2+2], 'little') for i in range(n)]

        self.results.append(FoundMap(
            defn    = _LAMBDA_EFF_DEF,
            address = d_addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        # Samo non-zero vrijednosti za min
        nonzero = [v for v in vals if v > 0]
        q15_min = min(nonzero) / 32768 if nonzero else 0
        q15_max = max(vals) / 32768
        if cb: cb(f"  Lambda eff @ 0x{d_addr:06X}  41x18 Q15  [{q15_min:.3f}-{q15_max:.3f}]"
                  f"  Y-os=[{yax[0]}..{yax[-1]}]")

    # ── Torque optimal / driver demand scan ───────────────────────────────────

    def _scan_torque_opt(self, cb=None):
        if cb: cb("Trazim optimal torque tablicu...")
        data = self.eng.get_bytes()

        addr = TORQUE_OPT_ADDR
        n    = _TORQUE_OPT_DEF.rows * _TORQUE_OPT_DEF.cols  # 16×16 = 256
        if addr + n * 2 > len(data):
            return

        vals = []
        valid = True
        for i in range(n):
            o  = addr + i * 2
            hi = data[o]
            lo = data[o + 1]
            if lo != 0x00:
                valid = False; break
            if not (60 <= hi <= 220):   # 46-169% raspon
                valid = False; break
            vals.append((hi << 8) | lo)

        if not valid:
            if cb: cb(f"  Torque opt @ 0x{addr:06X}: validacija pala — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _TORQUE_OPT_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Torque opt @ 0x{addr:06X}  16x16  [{min(v>>8 for v in vals)}-{max(v>>8 for v in vals)}] MSB")

    # ── Injector deadtime scan ────────────────────────────────────────────────

    def _scan_deadtime(self, cb=None):
        if cb: cb("Trazim injector deadtime tablicu...")
        data = self.eng.get_bytes()

        addr = DEADTIME_ADDR
        n    = _DEADTIME_DEF.rows * _DEADTIME_DEF.cols  # 14 × 7 = 98
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: deadtime vrijednosti su relativno male i ujednacene
        non_zero = sum(1 for v in vals if v > 0)
        if non_zero < n // 2:
            if cb: cb(f"  Deadtime @ 0x{addr:06X}: previse nula — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _DEADTIME_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Deadtime @ 0x{addr:06X}  14x7  raw=[{min(vals)}-{max(vals)}] (read-only)")

    # ── DFCO thresholds scan ──────────────────────────────────────────────────

    def _scan_dfco(self, cb=None):
        if cb: cb("Trazim DFCO pragove...")
        data = self.eng.get_bytes()

        addr = DFCO_ADDR
        n    = 7
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: rastuci niz RPM vrijednosti u razumnom rasponu
        if not (all(400 <= v <= 5000 for v in vals) and self._monotone(vals)):
            if cb: cb(f"  DFCO @ 0x{addr:06X}: validacija pala — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _DFCO_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  DFCO @ 0x{addr:06X}  1×7  [{vals[0]}-{vals[-1]}] rpm")

    # ── Idle RPM target scan ──────────────────────────────────────────────────

    def _scan_idle_rpm(self, cb=None):
        if cb: cb("Trazim idle RPM target tablicu...")
        data = self.eng.get_bytes()

        addr = IDLE_RPM_ADDR
        n    = _IDLE_RPM_DEF.rows * _IDLE_RPM_DEF.cols  # 5 × 12 = 60
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: RPM vrijednosti ralantija 600-4500, vecina u tome rasponu
        in_range = sum(1 for v in vals if 600 <= v <= 4500)
        if in_range < n * 3 // 4:
            if cb: cb(f"  Idle RPM @ 0x{addr:06X}: validacija pala ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _IDLE_RPM_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Idle RPM @ 0x{addr:06X}  5×12  [{min(vals)}-{max(vals)}] rpm")

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

    # ── Spark 900 ACE — scanneri ──────────────────────────────────────────────

    def _scan_spark_injection(self, cb=None):
        if cb: cb("Trazim Spark injection mapu...")
        data = self.eng.get_bytes()

        # RPM os (20pt) @ 0x02225A
        rpm_addr = 0x02225A
        if rpm_addr + 40 <= len(data):
            rpm_vals = [int.from_bytes(data[rpm_addr+i*2:rpm_addr+i*2+2], 'little') for i in range(20)]
            if self._monotone(rpm_vals) and 7000 <= rpm_vals[0] <= 9000:
                self.results.append(FoundMap(
                    defn    = _SPARK_INJ_RPM_AXIS_DEF,
                    address = rpm_addr,
                    sw_id   = self._sw(),
                    data    = rpm_vals,
                ))
                if cb: cb(f"  Spark RPM os @ 0x{rpm_addr:06X}: {[v//4 for v in rpm_vals[:5]]}...{[v//4 for v in rpm_vals[-3:]]} RPM")

        # Load os (30pt) @ 0x022282
        load_addr = 0x022282
        if load_addr + 60 <= len(data):
            load_vals = [int.from_bytes(data[load_addr+i*2:load_addr+i*2+2], 'little') for i in range(30)]
            if self._monotone(load_vals) and 3000 <= load_vals[0] <= 5000:
                self.results.append(FoundMap(
                    defn    = _SPARK_INJ_LOAD_AXIS_DEF,
                    address = load_addr,
                    sw_id   = self._sw(),
                    data    = load_vals,
                ))
                if cb: cb(f"  Spark load os @ 0x{load_addr:06X}: {load_vals[:3]}...{load_vals[-3:]}")

        # Injection data (30x20) @ 0x0222BE
        addr = 0x0222BE
        n    = _SPARK_INJ_DEF.rows * _SPARK_INJ_DEF.cols  # 30×20 = 600
        size = n * 2  # u16 = 1200 bytes

        if addr + size > len(data):
            if cb: cb(f"  Spark injection: izvan granica @ 0x{addr:06X}")
            return

        vals = [int.from_bytes(data[addr+i*2:addr+i*2+2], 'little') for i in range(n)]
        mn, mx = min(vals), max(vals)

        if _SPARK_INJ_DEF.raw_min <= mn and mx <= _SPARK_INJ_DEF.raw_max + 1000:
            self.results.append(FoundMap(
                defn    = _SPARK_INJ_DEF,
                address = addr,
                sw_id   = self._sw(),
                data    = vals,
            ))
            mirror = addr + _SPARK_INJ_DEF.mirror_offset
            if cb: cb(f"  Spark injection @ 0x{addr:06X}  raw=[{mn}–{mx}]"
                      f"  mirror @ 0x{mirror:06X}")
        else:
            if cb: cb(f"  Spark injection @ 0x{addr:06X}: validacija pala raw=[{mn}–{mx}]")

    def _scan_spark_ignition(self, cb=None):
        if cb: cb("Trazim Spark ignition mape...")
        data = self.eng.get_bytes()
        found = 0

        for idx in range(6):  # 6 karti (0-5), potvrđena mirror kopija
            addr = 0x026A76 + idx * 0x90
            if addr + 144 > len(data):
                continue
            raw = list(data[addr:addr + 144])
            in_range = sum(1 for v in raw if 10 <= v <= 60)
            var = max(raw) - min(raw)
            if in_range / 144 >= 0.90 and var >= 10:
                self.results.append(FoundMap(
                    defn    = _SPARK_IGN_DEFS[idx],
                    address = addr,
                    sw_id   = self._sw(),
                    data    = raw,
                ))
                found += 1
                if cb: cb(f"  Spark ignition #{idx:02d} @ 0x{addr:06X}"
                          f"  raw=[{min(raw)}–{max(raw)}]"
                          f"  ({min(raw)*0.75:.1f}°–{max(raw)*0.75:.1f}°BTDC)")

        if cb: cb(f"  Spark ignition: {found}/6 karti pronađeno")

    def _scan_spark_lambda(self, cb=None):
        if cb: cb("Trazim Spark lambda mape...")
        data = self.eng.get_bytes()

        addrs = [0x025F5C, 0x02607E, 0x0261A0, 0x0262C2]
        n = _SPARK_LAMBDA_DEF.rows * _SPARK_LAMBDA_DEF.cols  # 8×16 = 128
        size = n * 2  # 256B

        found = 0
        for addr in addrs:
            if addr + size > len(data):
                continue
            vals = [int.from_bytes(data[addr+i*2:addr+i*2+2], 'little') for i in range(n)]
            mn, mx = min(vals), max(vals)
            if _SPARK_LAMBDA_DEF.raw_min <= mn and mx <= _SPARK_LAMBDA_DEF.raw_max + 1000:
                self.results.append(FoundMap(
                    defn    = _SPARK_LAMBDA_DEF,
                    address = addr,
                    sw_id   = self._sw(),
                    data    = vals,
                ))
                found += 1
                if cb: cb(f"  Spark lambda @ 0x{addr:06X}  λ=[{mn/32768:.3f}–{mx/32768:.3f}]")

        if cb: cb(f"  Spark lambda: {found}/4 kopija pronađeno")

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
