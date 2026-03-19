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
  Lambda adapt baza      @ 0x0268A0                           LE u16, 12×18, Q15 (85% conf.)
  Lambda trim (korekcija)@ 0x026DB8                           LE u16, 12×18, Q15
  Accel enrichment       @ 0x028059                           LE u16, 5×5, Q14 (kompleksan format)
  Temp fuel correction   @ 0x025E50                           LE u16, 1×156, Q14
  Start injection (1D)   @ 0x025CDC                           LE u16, 1×6 + 6-pt osa
  Ign correction (2D u8) @ 0x022374                           u8,  8×8, ugrađene osi
  Thermal enrichment     @ 0x02AA42                           LE u16, 8×7, /64=%, CTS 80-150°C
  Eff correction         @ 0x0259D2                           LE u16, 10×7, Q15 (ugradj. Y-os, KFWIRKBA sub)
  Overtemp lambda        @ 0x025ADA                           LE u16, 1×63, Q15, 0xFFFF=SC bypass
  Neutral corr           @ 0x025B58                           LE u16, 1×63, Q14≈1.004
  SC boost factor        @ 0x025DF8                           LE u16, 1×40, Q14=1.224 (+22%)
  Lambda eff (KFWIRKBA)  @ 0x02AE5E                           LE u16, 41×18, Q15 (Y-os @ 0x02AE40)
    — 300hp SC: bypass (redovi=X-os lambda vrijednosti); GTI90 NA: aktivni faktori 0.51-0.71

Napomene:
  - CAL regija (0x060000+) je TriCore bytekod — ne pisati!
  - Sve mape su iskljucivo u CODE regiji.
  - KFWIRKBA: SC bypass kalibracija vs NA aktivna korekcija — ovisno o varijanti.
  - GTI90 lambda main @ 0x0266F0: flat 0.984 (neutralna); mirror @ 0x026C08: aktivna kalibracija.
  - Spark 2019 == Spark 2021: 0 razlika (isti SW 10SW039116).
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
    name        = "Rev limiter — scalar",
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
    name        = "Rev limiter — soft/mid/hard",
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
#   10-15  Pomocne timing mape — ANALIZIRANO (2026-03-18):
#           Apsolutne timing mape (25.5–33.75° raspon, isti kao #00-#07)
#           Grupa A (#10,#12,#14): uzi raspon 25.5–30°, sve 144 celije aktivne
#           Grupa B (#11,#13,#15): siri raspon 24–33.75°, #11/#13 imaju "dip" redove (24°)
#           #15: SC/boost-specificna — 130hp NA ima bitno nizi advance (26.5° vs 29.8°)
#           NPRo STG2 mijenja SVE (dodan advance +2.25 do +9.0°)
#   16-17  POTVRDJENO NPRo STG2: aktivne timing mape izvan prvobitnih 16 (0x02C030, 0x02C0C0)
#   18     Uvjetna/parcijalna mapa — prvih 3 reda aktivni, ostali 0 (STG2 mijenja)
#          R00-R02 identicni #11.R04-R06; 130hp ima konstantnih 25.5° (sigurnosni fallback)
# VAZNO: tocni uvjeti aktivacije NISU verificirani bez A2L fajla.
_IGN_NAMES = [
    "Paljenje — Osnovna 1",                  # 00
    "Paljenje — Osnovna 2",                  # 01
    "Paljenje — Osnovna 3",                  # 02
    "Paljenje — Osnovna 4",                  # 03
    "Paljenje — Osnovna 5",                  # 04
    "Paljenje — Osnovna 6",                  # 05
    "Paljenje — Osnovna 7",                  # 06
    "Paljenje — Osnovna 8",                  # 07
    "Paljenje — Knock korekcija 1",          # 08  POTVRDJENO: knock delta/trim mapa
    "Paljenje — Knock korekcija 2",          # 09  POTVRDJENO: knock delta/trim mapa
    "Paljenje — Pomocna A1 (uski raspon)",   # 10  apsolutna, 25.5-30°, svi uvjeti aktivni
    "Paljenje — Pomocna B1 (dip redak R7)",  # 11  apsolutna, 24-33.75°, knock/decel dip @ R07
    "Paljenje — Pomocna A2 (uski raspon)",   # 12  apsolutna, 25.5-30°, svi uvjeti aktivni
    "Paljenje — Pomocna B2 (dip redak R9)",  # 13  apsolutna, 24-33.75°, knock/decel dip @ R09
    "Paljenje — Pomocna A3 (uski raspon)",   # 14  apsolutna, 25.5-30°, svi uvjeti aktivni
    "Paljenje — Pomocna B3/SC",              # 15  SC/boost-specificna (130hp NA bitno drugacija)
    "Paljenje — Prosirena 1",                # 16  POTVRDJENO: NPRo STG2 mijenja (0x02C030)
    "Paljenje — Prosirena 2",                # 17  POTVRDJENO: NPRo STG2 mijenja (0x02C0C0)
    "Paljenje — Uvjetna/Fallback",           # 18  parcijalna: R00-R02==#11.R04-06, 130hp=25.5°
]

def _make_ign_def(idx: int) -> MapDef:
    addr = IGN_BASE + idx * IGN_STRIDE
    is_knock    = idx in (8, 9)
    is_extended = idx in (16, 17)
    is_partial  = idx == 18
    is_aux_a    = idx in (10, 12, 14)   # Pomocna grupa A: uski raspon 25.5-30deg
    is_aux_b    = idx in (11, 13)       # Pomocna grupa B: siri raspon 24-33.75deg, dip redak
    is_aux_sc   = idx == 15             # Pomocna B3/SC: SC/boost-specificna
    return MapDef(
        name         = _IGN_NAMES[idx],
        description  = (
            f"Korekcija predpaljenja za knock/detonaciju #{idx-7} -- "
            "negativne vrijednosti = kasnjenje (retard). "
            "Automatski se oduzima od osnovne mape pri detekciji detonacije."
            if is_knock else
            f"Kut predpaljenja (timing advance) -- prosirena mapa #{idx:02d}. "
            "POTVRDJENO: NPRo STG2 mijenja ovu mapu. "
            "Osi: RPM (x) x opterecenje/MAP (y)."
            if is_extended else
            "Uvjetna/parcijalna timing mapa -- fallback ili specijalni uvjet. "
            "Prvih 3 reda aktivni (R00-R02 identicni #11.R04-R06); ostatak nula. "
            "130hp NA: konstantnih 25.5deg (sigurnosni minimum). STG2 djelomicno mijenja."
            if is_partial else
            f"Pomocna timing mapa A#{(idx-10)//2+1} -- uzi raspon (25.5-30deg BTDC). "
            "Sve 144 celije aktivne. NPRo STG2 dodaje +2.25 do +6.75deg. "
            "Osi: RPM (x) x opterecenje/MAP (y). Tocni uvjeti aktivacije nepoznati (nema A2L)."
            if is_aux_a else
            f"Pomocna timing mapa B#{(idx-11)//2+1} -- siri raspon (24-33.75deg BTDC). "
            "Sadrzi 'dip' redak s retardiranim timingom (24-24.75deg) -- znak knock/decel zone. "
            f"Dip redak: R{'07' if idx==11 else '09'}. NPRo STG2 dodaje +2.25 do +9.0deg."
            if is_aux_b else
            "Pomocna timing mapa B3 -- SC/boost-specificna. "
            "300hp SC: 25.5-33.75deg (avg 29.8deg). 130hp NA: bitno nizi advance (avg 26.5deg) s flat redovima. "
            "Razlika 130hp/300hp ukazuje na kompresorem uvjetovanu aktivaciju. NPRo dodaje +2.25 do +9.0deg."
            if is_aux_sc else
            f"Kut predpaljenja (timing advance) -- mapa #{idx:02d}. "
            "Osi: RPM (x) x opterecenje/MAP (y). "
            "Razlicite mape aktivne su za razlicite uvjete (toplina, boost, stanje motora)."
        ),
        category     = "ignition",
        rows=12, cols=12,
        byte_order   = "BE",
        dtype        = "u8",
        scale        = 0.75,    # 0.75deg/bit
        offset_val   = 0.0,
        unit         = "degBTDC" if not is_knock else "deg",
        axis_x       = _RPM_AXIS_12,
        axis_y       = _LOAD_AXIS_12,
        raw_min      = 0  if (is_knock or is_partial) else 16,
        raw_max      = 40 if is_knock else 58,
        mirror_offset= 0,
        notes        = (
            f"Adresa: 0x{addr:06X}. Scale: 0.75deg/bit. "
            + ("KNOCK TRIM: retard delta oduzet od osnove pri detonaciji. " if is_knock else
               "POTVRDJENO NPRo STG2 mapa. ORI: 25.5-30deg, STG2: vise. " if is_extended else
               "UVJETNA FALLBACK: aktivna samo u odredjenim uvjetima, R00-R02==#11.R04-06. " if is_partial else
               "AUX A: apsolutna timing, uski raspon 25.5-30deg. NPRo modificira. " if is_aux_a else
               "AUX B: apsolutna timing, siri raspon + dip redak (knock/decel zona). " if is_aux_b else
               "AUX SC: SC/boost-specificna timing. 130hp ima konzervativniju kalibraciju. " if is_aux_sc else
               "ORI: 24-33.75deg BTDC, STG2: do 36.75deg BTDC. ")
            + "Os Y: relativno punjenje rl [%] -- kandidat @ 0x02AFAC (LE u16, /64). "
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
    axis_x        = _RPM_AXIS_16,   # 16pt RPM u16 BE @ 0x024F46 (poznata RPM os)
    axis_y        = _LOAD_AXIS_12,  # 12pt load u16 LE @ 0x02AE30 (globalna os, potvrđena)
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
# Blok od 52× u16 LE vrijednosti @ 0x0256F8–0x02575F koji kontrolira knock detekciju.
# Format u8 parova: svake 2 bajta = 2 parametra (vjerojatno po cilindru).
# ISPRAVKA 2026-03-18: prvobitno dokumentirano kao 24 u16 — binarni scan potvrdio 52 u16 (104B).
# Regije 0x025738 (6B) i 0x02574E (4B) su nastavak istog bloka, ne zasebne vrijednosti.
#
# Poznate vrijednosti:
#   [00-01] = 44237 (0xACCD) — prag detekcije knocka (threshold high) → NPRo: 65535
#   [02+]   = 7967  (0x1F1F) = [31,31] u8 — nominalni prag knocka per-cyl → NPRo: [154,154]
#   Repetirajući pattern: header (44237/65535) + grupe od 7967/39578/8090
#
# NPRo STG2 promjene:
#   [00-01]: 44237 → 65535 (povišen threshold = teže aktivirati smanjenje timinga)
#   [03,04,09,10,15,16,17,20,21]: 7967 → 39578 (31→154 u8 — agresivniji knock limit)
#   [05,11,22]: 7967 → 8090 (31→154 samo low byte)
#   230hp: sve ostaju na 7967 (NPRo STG2 ne mijenja 230hp knock parametre)
#
# NAPOMENA: točna 2D struktura nepoznata bez A2L — iskazano kao flat 1D.

KNOCK_PARAMS_ADDR = 0x0256F8

_KNOCK_PARAMS_DEF = MapDef(
    name          = "Knock — parametri praga detekcije",
    description   = (
        "Parametri praga detekcije detonacije (knock threshold) — 52 vrijednosti (1D). "
        "Veće = viši prag = ECU teže detektira knock = manje retard korekcija. "
        "Format: u8 parovi (svaka u16 = 2 bajta = 2 param). "
        "ori_300: [0-1]=44237, [2+]=7967. "
        "NPRo STG2: [0-1]=65535, selektivno [3,4,9,10...]=39578 (agresivnija tuning mapa). "
        "Blok: 0x0256F8–0x02575F (104B). 230hp: sve na 7967 (STG2 ne mijenja)."
    ),
    category      = "misc",
    rows=1, cols=52,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw (u16)",
    axis_x        = None, axis_y = None,
    raw_min       = 0, raw_max = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{KNOCK_PARAMS_ADDR:06X}–0x02575F (52×u16 LE = 104B). "
        "Kao u8 parovi: 0x1F=31 nominalni, 0x9A=154 NPRo agresivni, 0xFF=255 max. "
        "Ispravka 2026-03-18: prvobitno 24, stvarno 52 u16 — binarni scan potvrdio. "
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
    axis_x        = AxisDef(count=13, byte_order="LE", dtype="u16",
                            scale=1.0/32768.0, unit="λ",
                            values=[656, 1967, 3933, 5899, 7865, 9830, 13107,
                                    19661, 26214, 32768, 39321, 45875, 52428]),
                            # @ 0x02480A (Q15: 0.02–1.60 λ, 13pt)
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


# ─── Lambda adaptacijska baza (short-term fuel trim base) ─────────────────────
#
# 12×18 Q15 tablica @ 0x0268A0 — odmah iza lambda main (0x0266F0+432=0x0268A0).
# Offset od lambda main: točno +0x1B0 = +432B = veličina lambda main tablice.
#
# POTVRĐENO diff analizom (2026-03-18/19):
#   NPRo STG2 mijenja 105/216 vrijednosti
#   Sve 3 HP varijante (300hp/230hp/130hp) imaju bitno različite vrijednosti
#   → aktivno kalibrirana per-HP mapa (nije padding niti const)
#
# Vrijednosti (Q15, raw/32768=lambda):
#   300hp ORI 2021: 31656–34035 → λ 0.966–1.039 (112 unique vrijednosti, uska kalibracija)
#   300hp STG2:     105/216 vrijednosti promijenjeno (vs ORI)
#   300hp 2020 vs 2021: 105/216 razlika! SW različit (10SW054296 vs 10SW066726)
#   230hp:          33064–34710 → λ 1.009–1.059 (9 unique — lean bias)
#   130hp:          32742–33581 → λ 0.999–1.025 (8 unique — gotovo neutralan)
#   GTI90:          32258–33213 → λ 0.984–1.014 (5 unique — flat)
#   ZAKLJUČAK: 300hp ima najkompleksniju kalibraciju (112 unique), GTI90 najravniju (5 unique)
#
# Fizikalni smisao: baza za short-term adaptaciju lambda (KFLAMBAS ili ekvivalent).
# ECU koristi ovu mapu kao početnu točku za adaptivne korekcije goriva.
# Dimenzije identične lambda main: 12 RPM × 18 load točaka.
# Confidence: 90% (podignuto — svi 4 varijante potvrđene s koherentnim kalibracijama).

LAMBDA_ADAPT_ADDR = 0x0268A0

_LAMBDA_ADAPT_DEF = MapDef(
    name          = "Lambda adaptacijska baza (STF trim base)",
    description   = (
        "Lambda adaptacijska baza — 12×18 Q15 tablica @ 0x0268A0. "
        "Odmah iza lambda main mape (0x0266F0 + 432B = 0x0268A0). "
        "Fizikalni smisao: baza za short-term fuel trim adaptaciju (KFLAMBAS ili equiv). "
        "ECU koristi kao startnu točku za adaptivne korekcije goriva. "
        "Per-HP varijanta: 300hp/230hp/130hp imaju različite kalibracije. "
        "NPRo STG2 mijenja 105/216 vrijednosti — aktivno tunirano."
    ),
    category      = "lambda",
    rows=12, cols=18,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,   # Q15: 32768 = 1.0
    offset_val    = 0.0,
    unit          = "lambda",
    axis_x        = _LAMBDA_LOAD_AXIS_18,
    axis_y        = _RPM_AXIS_12,
    raw_min       = 25000,   # lambda ~0.76
    raw_max       = 40000,   # lambda ~1.22
    mirror_offset = 0,
    notes         = (
        f"@ 0x{LAMBDA_ADAPT_ADDR:06X} (12×18 u16 LE Q15 = 432B). "
        "Offset +0x1B0 od lambda main (0x0266F0). "
        "300hp 2021: λ 0.966–1.039 (112 unique), 230hp: λ 1.009–1.059 (9u), "
        "130hp: λ 0.999–1.025 (8u), GTI90: λ 0.984–1.014 (5u). "
        "NPRo STG2: 105/216 razlika. 2020 vs 2021 300hp: 105/216 razlika (razl. SW). "
        "Confidence 90%."
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


# ─── Efficiency correction after deadtime (Q15, 2D) — sub-table ─────────────
#
# Blok Q15 korekcijskih faktora odmah iza deadtime tablice @ 0x0259C4.
# Struktura: 7 preambula u16 (X-os) + 10×7 u16 podataka (col[0]=embedded Y-os).
#   Preambula @ 0x0259C4: [13093, 16442, 19783, 24919, 30059, 35203, 43920]
#     = [0.40, 0.50, 0.60, 0.76, 0.92, 1.07, 1.34] λ (Q15 lambda vrijednosti)
#   Podaci @ 0x0259D2: 10 redova × 7 u16 (col[0]=embedded Y-os, col[1-6]=faktori)
#
# Pattern: dijagonalni (korekcija pada prema 1.000 za niže load/lambda kombinacije).
# IDENTIČNO u ori_300, stg2 i 082806 (STG2 NE mijenja ovu tablicu).
# 130hp: potpuno drugačiji sadržaj — drugačija kalibracija NA motora.
#
# Fizikalni smisao (bez A2L, ali potvrđeno cross-ref analizom 2026-03-18):
#   Ova 2D sub-tablica je KFWIRKBA lambda efficiency sub-skup za kratki lambda
#   raspon (0.40-1.34). Komplementarna je glavnoj KFWIRKBA tablici @ 0x02AE5E.
#   col[0] = embedded Y-os (lambda referentne točke za interpolaciju).
#   col[1-6] = faktori efikasnosti po X-os (lambda) točkama.
#   Može biti korištena za specijalne uvjete (cranking, warm-up, overrun)
#   gdje lambda raspon je niži od normalnog radnog raspona.
#   Confidence: ~65% (bez A2L — struktura jasna, namjena pretpostavljena).

EFF_CORR_AXIS_Y_ADDR = 0x0259C4   # 14× u8 Y-os lambda (0.37–1.71, scale /100)
EFF_CORR_AXIS_X_ADDR = 0x0259D2   # 10× u8 X-os lambda (0.37–1.44, scale /100)
EFF_CORR_ADDR        = 0x0259DC   # 14×10 u8 data (ISPRAVKA: bilo 0x0259D2 s dim 10×7 u16)
# Backwards compat alias
EFF_CORR_AXIS_ADDR   = EFF_CORR_AXIS_Y_ADDR

_EFF_CORR_DEF = MapDef(
    name          = "Lambda — efikasnost sub-tablica (KFWIRKBA 2D sub)",
    description   = (
        "KFWIRKBA 2D lambda-efikasnost sub-tablica odmah iza deadtime-a. "
        "14 redova (izmjerena lambda) × 10 kolona (referentna lambda). u8, scale /128. "
        "Y-os: λ 0.37–1.71 (izmjerena). X-os: λ 0.37–1.44 (referentna). "
        "Vrijednosti 128–159 → 1.0–1.24 (korekcijski faktor ≥ 1.0). "
        "Kod visokih lambda (Y≥1.44) sve ćelije = 1.0 (nema korekcije). "
        "STG2 = ORI (ne mijenja). 130hp: drugačija kalibracija. "
        "Namjena: KFWIRKBA efektivnost pri bogatim mješavinama (enrichment correction)."
    ),
    category      = "lambda",
    rows=14, cols=10,   # ISPRAVKA: bilo 10×7 u16 (pogrešno čitanje u8 osi kao u16)
    byte_order    = "BE", dtype = "u8",
    scale         = 1.0 / 128.0,
    offset_val    = 0.0,
    unit          = "faktor /128",
    axis_x        = AxisDef(count=10, byte_order="BE", dtype="u8",
                             scale=1.0 / 100.0, unit="λ (ref.)",
                             values=[37, 51, 64, 77, 91, 104, 117, 131, 137, 144]),
    axis_y        = AxisDef(count=14, byte_order="BE", dtype="u8",
                             scale=1.0 / 100.0, unit="λ (izmjerena)",
                             values=[37, 51, 58, 64, 71, 77, 87, 97, 107, 117, 131, 137, 144, 171]),
    raw_min       = 108,
    raw_max       = 170,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{EFF_CORR_ADDR:06X} (ISPRAVKA: bilo 0x0259D2 dim 10×7 u16). "
        "14×10=140 u8. Count @ 0x0259C2:[0E,0A]. "
        f"Y-os @ 0x{EFF_CORR_AXIS_Y_ADDR:06X} (14 u8), X-os @ 0x{EFF_CORR_AXIS_X_ADDR:06X} (10 u8). "
        "Kraj 0x025A68. 130hp: drugačija kalibracija. GTI90: razlika vs 300hp."
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
    name          = "Lambda — zaštita pretemperature (SC=bypass)",
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
    name          = "Lambda — neutral korekcija (Q14)",
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
# 130hp NA (1630): varijabilna [+23.9%..−1.2%], NIJE sve nule!
# GTI 90 NA (900cc): flat −18.4% (13364).
# 4tec1503 (GTI 130/155/230hp 2019/2020): flat 23130 (Q14 = 1.412 = +41.2%!) — potvrđeno 2026-03-19
#   Svi 1503 dumpovi (130/155/230hp 2019, 130hp 2020) = IDENTIČNO flat 23130.
#   Osi lambda OS (@ 0x025DE8) = identično 1630 130hp → [15413–39315] = [0.470–1.200].
#   NAPOMENA: +41.2% je viši nego 300hp SC (+22.4%) — razlog nepoznat bez A2L!
#   Mogući uzrok: drugačija logika fuel managementa na 1503 motoru, ili drugačija interpretacija tablice.
# STG2: identično (tuneri ne diraju ovu kalibraciju).
#
# Lambda os (8 točaka) ispred @ 0x025DE8 — razlikuje se po SW:
#   300hp: [22352–48045] = [0.682–1.466]
#   130/170hp (1630) + GTI 155 (1503): [15413–39315] = [0.470–1.200]
#   GTI 90: [12072–37772] = [0.368–1.153]
#
# Fizikalni smisao: nepoznat — nije pouzdani indikator SC motora.
#   Moguće: KFMSWSC (SC base fuel offset) ili opća lambda fuel korekcija.
# Lokacija: neposredno ispred TEMP_FUEL tablice (0x025E50).

SC_BOOST_FACTOR_AXIS_ADDR = 0x025DE8  # 8× u16 Q15 lambda os
SC_BOOST_FACTOR_ADDR      = 0x025DF8  # 40× u16 Q14 (+22.4% za SC)

_SC_BOOST_FACTOR_DEF = MapDef(
    name          = "SC — bazni faktor obogaćivanja [Q14]",
    description   = (
        "Bazna SC korekcija goriva — 40 u16 flat = 20046 (Q14 = 1.224 = +22.4%). "
        "300hp SC: flat 20046 (+22.4%). "
        "1630 130hp NA: varijabilna [16191–20303] (ne nule!). "
        "4tec1503 (svi 2019/2020 varianti): flat 23130 (Q14=1.412 = +41.2%) — potvrdjeno 2026-03-19. "
        "GTI90: flat 13364 (−18.4%). "
        "STG2 = ORI (tuneri ne mijenjaju). "
        "Lambda os (8 tocaka) @ 0x025DE8 razlikuje se po varijanti. "
        "Fizikalni smisao nepoznat bez A2L — nije pouzdani SC indikator."
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
        f"@ 0x{SC_BOOST_FACTOR_ADDR:06X} (40x u16 = 80B). "
        f"Lambda os (8pt) @ 0x{SC_BOOST_FACTOR_AXIS_ADDR:06X}: razl. po varijanti. "
        "300hp SC: flat 20046 = Q14 +22.4%. "
        "1630 130hp NA: var. [16191-20303]. "
        "4tec1503 (sve varijante 2019/2020): flat 23130 = Q14 +41.2% (potvrdjeno 2026-03-19). "
        "GTI90: flat 13364 = -18.4%. STG2: identican kao ORI. "
        "A2L naziv: moguce KFMSWSC ili SC lambda correction."
    ),
)


# ─── Lambda efficiency (KFWIRKBA) — 41×18 uniformna matrica ──────────────────
#
# Tablica @ 0x02AE40–0x02B421. Uniformna 41×18 matrica (LE u16 Q15).
# Y-os (load, 15 vrijednosti) @ 0x02AE40 — RAZLIKUJE SE PO VARIJANTI:
#   300hp SC: [3840,4480,5120,5760,6400,7040,7680,8320,8960,9600,10240,11520,12800,14080,15360]
#   GTI90 NA: [3840,4480,5120,5760,6400,7040,7680,8320,8960,9600,10240,10880,11520,12160,12800]
#   (gornja granica: 15360 za SC/visoki boost, 12800 za GTI90/NA)
#
# X-os (lambda, 18 točaka Q15) ugrađena je u RED 0 matrice (Bosch multi-block format):
#   300hp SC redovi 0-8: lambda X-os vrijednosti = BYPASS kalibracija
#   [21627,24186,26605,29158,31174,32652,35204,36749,38765,40580,42125,
#    44342,47029,49152,52756,55509,58982,58982]
#   = [0.66, 0.74, 0.81, 0.89, 0.95, 1.00, 1.07, 1.12, 1.18, 1.24, 1.29,
#      1.35, 1.44, 1.50, 1.61, 1.69, 1.80, 1.80]
#
# KLJUCNI NALAZ (binarni scan 2026-03-18):
#   300hp SC: redovi 0-8 ponavljaju lambda X-os vrijednosti = BYPASS (SC motor
#     ne koristi lambda efficiency korekciju — mapa je "identity" mapping).
#   GTI90 NA: AKTIVNA kalibracija, redovi 0-4 = [0.514-0.710] — stvarni
#     efikasnosni faktori za NA motor (rl load range 60-200%, λ 0.51-0.71).
#   130hp NA: sličan bypass ali s drugačijim X-os vrednostima ([19988-43254],
#     λ 0.61-1.32 — uži raspon od 300hp SC).
#   Red 9 @ svakoj varijanti: separator [4617, 64736, 65136, ...] = zajednički.
#
# STG2: sve vrijednosti λ>1.0 (x-indeksi 6-17) → 0xFFFF (lean bypass).
# Efekt: ECU ignorira lean-side korekciju efikasnosti (max power priority).
# Redovi 9-11 i 20-21 sadrže Y-os nastavke (Bosch multi-axis format).
# Podaci @ 0x02AE5E = 0x02AE40 + 30B (iza Y-osi), 41×18×2 = 1476B.

LAMBDA_EFF_YAXIS_ADDR = 0x02AE40  # 15× u16 LE load Y-os
LAMBDA_EFF_ADDR       = 0x02AE5E  # 41×18 u16 LE podaci

_LAMBDA_EFF_DEF = MapDef(
    name          = "Lambda efikasnost (KFWIRKBA) — 41×18 Q15",
    description   = (
        "Lambda Wirkungsgrad (efficiency) korekcijska tablica — 41×18 matrica. "
        "300hp SC: BYPASS kalibracija (redovi = lambda X-os, ECU ignorira korekciju). "
        "GTI90 NA: AKTIVNA (faktori 0.51-0.71 = stvarna lambda efficiency korekcija). "
        "X-os (lambda, 18 tocaka Q15): 0.66-1.80 (ugradjeno u red 0 matrice). "
        "Y-os (load, 15 vrijednosti @ 0x02AE40): 3840-15360 (SC) ili 3840-12800 (GTI90). "
        "STG2: lambda>1.0 (lean side) → 0xFFFF — uklanja lean korekciju za performance. "
        "A2L naziv: KFWIRKBA (Wirkungsgrad — efficiency correction factor)."
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
        "@ 0x02AE5E-0x02B421 (1476B). Y-os @ 0x02AE40 (15 load val, var. po SW). "
        "300hp SC: bypass (redovi=X-os). GTI90 NA: aktiva (0.51-0.71). "
        "STG2: lean (lambda>1.0) na 0xFFFF. A2L: KFWIRKBA (lambda Wirkungsgrad). "
        "Binarno potvrdeno: 300hp vs GTI90 vs 130hp scan 2026-03-18."
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
#   Y os @ 0x022364: 300hp=[75,100,150,163,175,181,188,200], 130hp=[63,100,125,150,175,181,188,200]
#   X os @ 0x02236C: 300hp=[53,80,107,120,147,187,227,255], 130hp=[33,47,60,73,80,100,120,127]
#   Podaci @ 0x022374: 8×8 u8 = 64 bajta (kraj @ 0x0223B3)
#
# IDENTIFIKACIJA OSI (2026-03-19):
#   Y os: raw × 40 = RPM → 300hp: [3000,4000,6000,6520,7000,7240,7520,8000] RPM
#                          130hp: [2520,4000,5000,6000,7000,7240,7520,8000] RPM
#   X os: raw / 2.55 = load% → 300hp: [20.8,31.4,42.0,47.1,57.6,73.3,89.0,100.0]%
#                               130hp max=127 → norm /1.27: [26.0,37.0,47.2,57.5,63.0,78.7,94.5,100.0]%
#   VARIJANTA-SPECIFIČNO! 300hp koristi skalu /255=100%, 130hp koristi /127=100%.
#   Fizikalni smisao: motor efficiency / torque correction factor po RPM × load.
#
# Vrijednosti: 145–200 (u8). 128 = 100% (neutralno), ~160 = 125%, 200 = 156%.
# STG2 capuje sve >180 na 180 — ograničava max korekciju (knock protection).
# 300hp vs 130hp: RAZLIKUJE SE u obje osi i podacima.
# Skaliranje: raw/128 = faktor ili raw * 100/128 = % (bez A2L potvrde).

IGN_CORR_ADDR = 0x022374   # Start podatkovnog dijela (poslije 2×8B osi)
IGN_CORR_AXIS_ADDR = 0x022364  # Y-os (prva os, 8× u8)

_IGN_CORR_DEF = MapDef(
    name          = "Paljenje — korekcija po RPM×load",
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
                             scale=100.0/255.0, unit="load [%]",  # /2.55 = %; 300hp norma
                             values=[53, 80, 107, 120, 147, 187, 227, 255]),
    axis_y        = AxisDef(count=8, byte_order="LE", dtype="u8",
                             scale=40.0, unit="rpm",   # raw × 40 = RPM
                             values=[75, 100, 150, 163, 175, 181, 188, 200]),
    raw_min       = 100,
    raw_max       = 255,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{IGN_CORR_ADDR:06X} (8×8 u8 = 64B). Osi @ 0x{IGN_CORR_AXIS_ADDR:06X} (2×8 u8). "
        "Y-os (RPM): raw × 40 = RPM, 300hp=[3000–8000], 130hp=[2520–8000]. "
        "X-os (load%): raw/2.55 = %, 300hp max=255=100%, 130hp max=127=100% (normirani). "
        "VARIJANTA-SPECIFIČAN SADRŽAJ: osi se razlikuju za 300hp vs 130hp. "
        "STG2 cap: sve > 180 → 180 (ograničava torque/timing korekciju). "
        "A2L naziv nepoznat — moguće KFZW2 ili KFMDREG. Confidence 70%."
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
    name          = "Moment — optimalni / vozačev zahtjev [%]",
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
#
# ISPRAVLJENA STRUKTURA (binarnom analizom 2026-03-19):
#   @ 0x025876: count bytes [0x0E=14, 0x0A=10] (dva u16 LE)
#   @ 0x02587A: X-os — 14 vrijednosti trajanja impulsa (u16 LE, direktno µs):
#               [1, 2, 3, 4, 6, 8, 10, 20, 40, 60, 120, 240, 480, 960]
#   @ 0x025896: Y-os — 10 vrijednosti temperature (u16 LE, direktno °C):
#               [37, 51, 64, 77, 91, 104, 117, 131, 144, 157]
#   @ 0x0258AA: 10×14 u16 LE data (10 temp × 14 duration = 280B, ends 0x0259C2)
#   → 0x0259C2: count bytes za KFWIRKBA [0x0E, 0x0A] — potvrda granice
#
# Vrijednosti × 0.5µs: raspon 512–2692µs (0.5–2.7ms pri hladnom/niskom naponu)
# Smanjuje se s temperaturom (topliji motor = brži injektor otvor = kraći deadtime)
# Identično u svim SW varijantama (hardware-fixed karakteristika injektora).
# ME17 ASAP2 naziv: TVKL (Totzeitkennlinie). Stara adresa 0x025900 bila POGREŠNA.

DEADTIME_ADDR = 0x0258AA    # ISPRAVKA: bila 0x025900 (sredina tablice)

_DEADTIME_AXIS_X = AxisDef(
    count=14, byte_order="LE", dtype="u16", scale=1.0, unit="µs (trajanje impulsa)",
    values=[1, 2, 3, 4, 6, 8, 10, 20, 40, 60, 120, 240, 480, 960],
)
_DEADTIME_AXIS_Y = AxisDef(
    count=10, byte_order="LE", dtype="u16", scale=1.0, unit="°C",
    values=[37, 51, 64, 77, 91, 104, 117, 131, 144, 157],
)

_DEADTIME_DEF = MapDef(
    name          = "Injektori — deadtime korekcija (read-only)",
    description   = (
        "Kašnjenje otvaranja injektora (deadtime / Totzeit) — hardware konstanta. "
        "NE MIJENJATI — kalibrirano za fizičke injektore (330cc/min). "
        "10 redova (temperatura) × 14 kolona (trajanje impulsa). "
        "ECU automatski kompenzira pri svakom ubrizgavanju. "
        "Manji deadtime pri višim temp (topliji injektor — brže otvaranje). "
        "Identično u svim SW varijantama (130/170/230/300hp)."
    ),
    category      = "misc",
    rows=10, cols=14,          # ISPRAVKA: bilo 14×7 (pogrešno)
    byte_order    = "LE", dtype = "u16",
    scale         = 0.5,       # × 0.5 µs/raw
    offset_val    = 0.0,
    unit          = "µs",
    axis_x        = _DEADTIME_AXIS_X,
    axis_y        = _DEADTIME_AXIS_Y,
    raw_min       = 1000,
    raw_max       = 6000,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{DEADTIME_ADDR:06X} (ISPRAVKA: bila 0x025900). "
        "10×14=140 u16 LE. Count bytes @ 0x025876: [14,10]. "
        "X-os @ 0x02587A: trajanje [1-960µs]. Y-os @ 0x025896: temp [37-157°C]. "
        "Kraj @ 0x0259C2 = count bytes za KFWIRKBA [0E,0A]. "
        "300hp vs 130hp: praktički identični. ME17 ASAP2: TVKL."
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


# ─── Decel/DFCO RPM ramp tablica ──────────────────────────────────────────────
#
# Kompleksna struktura @ 0x028C30–0x028D8F (16 unosa × 22B svaki = 352B).
# Svaki unos: 3× u16 (RPM period ticks, period-encoded) + 8× u16 (load os vrijednosti).
#
# Period encoding: RPM = 40,000,000 × 60 / (ticks × 58)
#   Manji ticks = viši RPM (period encoding)
#
# POTVRĐENO diff analizom (2026-03-18/19):
#   300hp ORI 2021: col[0]=8636–7041t (4791–5877 RPM), col[1]=9653–8554t (4287–4837 RPM)
#                   col[2]=10670 KONSTANTAN (3878 RPM) — hard decel threshold
#                   load os=[0,1054,1842,2911,4129,5336,6474,7556] (rastuci, 8 tocaka)
#   300hp STG2: t+431 viši ticks → RPM[0]=4563–5117 (SPO za 200-300 RPM), col[2]=3694 RPM
#   130hp ORI:  col[0]=3856–3718t (10731–11129 RPM!), col[2]=4784t (8649 RPM)
#               DRASTIČNO DRUGAČIJE — 130hp ima viši RPM raspon (do 11000 RPM u ticks)
#               load os=[0,648,966,1237,1438,1866,2564,3230] (niži load raspon)
#   GTI90:      col[0]=4471t (9255 RPM), col[1]=4879t, col[2]=5158t — vlastiti raspon
#   Spark 900:  E0 = 64256t (643 RPM!) i 65280 → nema validnih DFCO ramp vrijednosti
#               Spark ne koristi ovu strukturu na ovaj način
#
# Svaki unos = 1 kondicionalna load zona (8 load vrijednosti = X-os load segmenti).
# Fizikalni smisao: DFCO/decel RPM ramp — per-load RPM pragovi za fuel cut re-engage.
# ZAKLJUČAK: 1630 ACE je jedini koji ima smislene vrijednosti; Spark binarno null/garbage.
# Confidence: 80% (podignuto — višestruko potvrđeno, Spark negativno potvrđen).

DECEL_RPM_CUT_ADDR = 0x028C30
_DECEL_RPM_CUT_ENTRY_SIZE = 22   # 3×u16 RPM ticks + 8×u16 load os = 11×u16 = 22B
_DECEL_RPM_CUT_ENTRIES    = 16

_DECEL_RPM_CUT_DEF = MapDef(
    name          = "Decel RPM ramp — DFCO per-load pragovi",
    description   = (
        "Deceleration/DFCO RPM ramp tablica — 16 unosa × 22B = 352B. "
        "Svaki unos: 3 RPM period-ticks + 8 load-os vrijednosti. "
        "Period enc: RPM = 40MHz×60/(ticks×58). Manji ticks = viši RPM. "
        "300hp: col[2]=10670t=3878 RPM (const), col[0]=4791–5877 RPM po load. "
        "130hp: col[0]=10731–11129 RPM (puno viši nego 300hp!), col[2]=8649 RPM. "
        "GTI90: col[0]=9255 RPM (vlastiti raspon). Spark: nema validnih vrijednosti. "
        "STG2 smanjuje RPM limite → fuel cut se vraća pri nižem RPM (NVH). "
        "Confidence: 80% (1630 ACE-specifično, Spark negativno potvrđen)."
    ),
    category      = "misc",
    rows=16, cols=11,      # 16 unosa × 11 u16 (3 RPM + 8 load)
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,   # raw ticks; koristiti RPM=40e6×60/(v×58) za konverziju
    offset_val    = 0.0,
    unit          = "ticks (period enc.)",
    axis_x        = AxisDef(count=11, byte_order="LE", dtype="u16",
                            scale=1.0/32768.0, unit="omjer Q15",
                            values=[0, 6554, 13107, 19661, 26214, 32768,
                                    39322, 45875, 52429, 58982, 65535]),
                            # @ 0x028C0A (Q15: 0.0–2.0 raspon)
    axis_y        = AxisDef(count=16, byte_order="LE", dtype="u16",
                            scale=0.01, unit="mg/hub (air mass)",
                            values=[6000, 7200, 8800, 10400, 12000, 14000, 16000, 18000,
                                    20000, 22000, 24000, 26000, 28000, 30000, 32000, 36000]),
                            # @ 0x028BEA (60–360 mg/hub)
    raw_min       = 1000,  # ticks: ~34571 RPM max (nerealno visoko)
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{DECEL_RPM_CUT_ADDR:06X}–0x028D8F (16×22B = 352B). "
        "Stride = 22B po unosu (ne ravnomjerna 2D matrica). "
        "RPM konv: 40,000,000×60/(ticks×58). "
        "300hp: col[0-1] silazni DFCO prag, col[2]=5348 RPM const hard cut. "
        "STG2 hard cut: 11199t=3695 RPM (vs ORI 3879t=5348 RPM). "
        "Confidence 75% — bez A2L potvrde točne strukture."
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
    axis_x        = AxisDef(count=12, byte_order="LE", dtype="u16",
                            scale=1.0, unit="°C",
                            values=[24, 37, 51, 64, 77, 91, 104, 117, 144, 171, 197, 251]),
                            # @ 0x02B5DE (temperatura rashladne tekućine, 12pt)
    axis_y        = AxisDef(count=5, byte_order="LE", dtype="u16",
                            scale=1.0, unit="RPM setpoint",
                            values=[3340, 3220, 3100, 2990, 2880]),
                            # @ 0x02B5F6 (5 uvjeta/modova rada, 3340→2880 RPM)
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
    axis_x        = AxisDef(count=20, byte_order="LE", dtype="u16",
                            scale=1.0/4.0, unit="RPM",
                            values=[7680, 8704, 9728, 10624, 11648, 12672, 13696, 14720,
                                    15616, 16640, 17664, 18688, 19712, 20608, 21632, 22656,
                                    23680, 24704, 25600, 26624]),
                            # @ 0x02225A (raw/4 = RPM, 1920–6656)
    axis_y        = AxisDef(count=30, byte_order="LE", dtype="u16",
                            scale=1.0, unit="load [raw]",
                            values=[3999, 4800, 5600, 7400, 9200, 10800, 11600, 12200,
                                    12600, 13200, 13720, 14560, 15600, 16400, 17000, 17600,
                                    18800, 19600, 20400, 21600, 22800, 24000, 24960, 25800,
                                    26680, 27680, 29000, 30720, 32000, 33600]),
                            # @ 0x022282 (load, 3999–33600)
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

_SPARK_IGN_DEFS = [_make_spark_ign_def(i) for i in range(8)]  # maps 0-7 (6+7 were previously missed)

# Spark ignition series B — narrow range (20-27°), second ignition group
# 8 maps @ 0x0295C0, stride 144B; maps 0-4 modified by STG2, 5-7 flat fallback
def _make_spark_ign_b_def(idx: int) -> MapDef:
    addr = 0x0295C0 + idx * 0x90
    flat = idx >= 5
    return MapDef(
        name          = f"Spark paljenje B #{idx:02d} [{'flat-fallback' if flat else 'low-range'}]",
        description   = (
            f"Spark 900 ACE ignition serija B, mapa #{idx}. 12×12 u8, 0.75°/bit. "
            f"Uski raspon 20.25–27.0° (niži od serije A). "
            f"{'Flat @ 27raw=20.25° (sigurna rezervna mapa, STG2 ne mijenja).' if flat else 'STG2 povećava za +2-7°.'} "
            f"Vjerojatno: uvjeti s aktivnim knock retardom / adaptacijom."
        ),
        category      = "ignition",
        rows=12, cols=12,
        byte_order    = "LE", dtype = "u8",
        scale         = 0.75,
        offset_val    = 0.0,
        unit          = "° BTDC",
        raw_min       = 5, raw_max = 65,
        notes         = f"Spark 900. @ 0x{addr:06X}, stride=0x90. Serija B #{idx}. {'flat=20.25°' if flat else 'STG2 modificira'}.",
    )

_SPARK_IGN_B_DEFS = [_make_spark_ign_b_def(i) for i in range(8)]

# Spark ignition series B2 — identičan format, svi modificirani od STG2
# 8 maps @ 0x029B60, stride 144B
def _make_spark_ign_b2_def(idx: int) -> MapDef:
    addr = 0x029B60 + idx * 0x90
    return MapDef(
        name          = f"Spark paljenje B2 #{idx:02d}",
        description   = (
            f"Spark 900 ACE ignition serija B2, mapa #{idx}. 12×12 u8, 0.75°/bit. "
            f"Raspon 20.25–27.0°. Svi modificirani od STG2 (+2-7°). "
            f"Vjerojatno: warm-up ili adaptation uvjeti."
        ),
        category      = "ignition",
        rows=12, cols=12,
        byte_order    = "LE", dtype = "u8",
        scale         = 0.75,
        offset_val    = 0.0,
        unit          = "° BTDC",
        raw_min       = 5, raw_max = 65,
        notes         = f"Spark 900. @ 0x{addr:06X}, stride=0x90. Serija B2 #{idx}. STG2 modificira sve.",
    )

_SPARK_IGN_B2_DEFS = [_make_spark_ign_b2_def(i) for i in range(8)]

# Spark ignition series C — u16LE format, visoke vrijednosti (×0.25°/bit)
# 3 maps @ 0x02803A, stride 144B; 72 u16LE values per map, MSB always 0
def _make_spark_ign_c_def(idx: int) -> MapDef:
    addr = 0x02803A + idx * 0x90
    return MapDef(
        name          = f"Spark paljenje C #{idx:02d} [u16 format]",
        description   = (
            f"Spark 900 ACE ignition serija C, mapa #{idx}. "
            f"72 u16LE vrijednosti (MSB uvijek 0), ×0.25°/bit. "
            f"Raspon 110–125 raw = 27.5–31.25° BTDC. "
            f"STG2 mijenja za +0.5–1.0°. Format: u16 ali efektivno u8×2 po ćeliji."
        ),
        category      = "ignition",
        rows=9, cols=8,
        byte_order    = "LE", dtype = "u16",
        scale         = 0.25,
        offset_val    = 0.0,
        unit          = "° BTDC",
        raw_min       = 100, raw_max = 135,
        notes         = f"Spark 900. @ 0x{addr:06X}. u16LE × 0.25 deg/bit. MSB=0. 72 vals=144B. STG2 mod.",
    )

_SPARK_IGN_C_DEFS = [_make_spark_ign_c_def(i) for i in range(3)]

# ── Spark aux tablice (POTVRĐENE binarnim skanom 2026-03-19) ─────────────────
# Sve adrese verificirane usporedbom s GTI90 (10SW053774) koji ima identičan motor.

_SPARK_DFCO_DEF = MapDef(
    name        = "Spark — DFCO pragovi isključivanja goriva",
    description = "Spark 900 ACE DFCO (Deceleration Fuel Cut-Off) RPM pragovi. "
                  "7 vrijednosti u16 LE. Identične vrijednosti kao GTI90. "
                  "Adresa: 0x021748.",
    category    = "misc",
    rows=7, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, offset_val = 0.0,
    unit        = "RPM",
    raw_min     = 500, raw_max = 4000,
    notes       = "Spark 900 ACE. @ 0x021748. Identično s GTI90 @ 0x02202E.",
)

_SPARK_COLD_START_DEF = MapDef(
    name        = "Spark — Cold start bogaćenje gorivom",
    description = "Spark 900 ACE enrichment pri hladnom startu. "
                  "6 vrijednosti u16 LE, po temperaturnim točkama. "
                  "Adresa: 0x0241F8. Identično s GTI90.",
    category    = "fuel",
    rows=6, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, offset_val = 0.0,
    unit        = "raw",
    raw_min     = 50, raw_max = 2000,
    notes       = "Spark 900 ACE. @ 0x0241F8. Identično s GTI90 @ 0x02586A.",
)

_SPARK_DEADTIME_DEF = MapDef(
    name        = "Spark — Injektori deadtime (read-only)",
    description = "Spark 900 ACE injektor mrtvo vrijeme po naponu baterije. "
                  "8×8 = 64 vrijednosti u16 LE, period-encoded (ticks @ 40MHz). "
                  "raw 12000-13440 ticks = ~300-336µs. Samo za prikaz, ne mijenjati!",
    category    = "fuel",
    rows=8, cols=8,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 40000.0,
    offset_val  = 0.0,
    unit        = "µs",
    axis_x      = AxisDef(count=8, byte_order="LE", dtype="u16",
                          scale=0.1, unit="V (napon)",
                          values=[80, 90, 100, 110, 120, 130, 140, 150]),
                          # @ 0x028794 (8pt u16 LE, /10 = 8.0-15.0V baterija)
    axis_y      = AxisDef(count=8, byte_order="LE", dtype="u8",
                          scale=0.1, unit="ms (trajanje injekcije)",
                          values=[4, 10, 20, 40, 60, 80, 100, 120]),
                          # @ 0x028784 (8pt u8, svaki pohranjen 2× kao par: [4,4,10,10,...])
                          # /10 = 0.4ms-12ms bazno trajanje injekcije
    raw_min     = 8000, raw_max = 14500,
    notes       = "Spark 900 ACE. @ 0x0287A4. Period ticks @ 40MHz. "
                  "Count bytes [8,8] @ 0x028780. "
                  "Y-os (trajanje): 8pt u8 pohranjena kao para @ 0x028784 = [4,4,10,10,...,120,120]. "
                  "X-os (napon): 8pt u16 LE @ 0x028794 = [80..150]/10 = [8.0..15.0V]. "
                  "Veca vrijednost deadtime pri manjem naponu i ducem impulsu. "
                  "RAZLIKUJE SE od GTI90 @ 0x025900 (GTI90 = 14×7). "
                  "2018 vs 2021 Spark: neznatno drugacije vrijednosti. Samo za prikaz!",
)

_SPARK_START_INJ_DEF = MapDef(
    name        = "Spark — Gorivo pri pokretanju (cranking)",
    description = "Spark 900 ACE injection količina pri pokretanju (cranking). "
                  "1D tablica 6 točaka po temperaturi. Adresa: 0x024676.",
    category    = "fuel",
    rows=6, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, offset_val = 0.0,
    unit        = "raw",
    raw_min     = 200, raw_max = 6000,
    notes       = "Spark 900 ACE. @ 0x024676. Slična struktura kao GTI90 @ 0x025CDC, "
                  "ali različite vrijednosti: Spark [341,565,1001,2397,4363,5089].",
)

_SPARK_KNOCK_DEF = MapDef(
    name        = "Spark — Knock parametri praga detekcije",
    description = "Spark 900 ACE knock sensor threshold parametri. "
                  "24 vrijednosti u16 LE. Identično GTI90. Adresa: 0x02408C.",
    category    = "misc",
    rows=24, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, offset_val = 0.0,
    unit        = "raw",
    raw_min     = 7000, raw_max = 65535,
    notes       = "Spark 900 ACE. @ 0x02408C. Identično s GTI90 @ 0x0256F8.",
)

_SPARK_WARMUP_DEF = MapDef(
    name        = "Spark — CTS warm-up korekcija goriva [%]",
    description = "Spark 900 ACE temperaturna korekcija goriva pri zagrijavanju. "
                  "156 u16 LE Q15 vrijednosti. Identična početna vrijednost kao GTI90 (13364). "
                  "Adresa: 0x024786.",
    category    = "fuel",
    rows=156, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 16384.0,
    offset_val  = 0.0,
    unit        = "%",
    raw_min     = 10000, raw_max = 25000,
    notes       = "Spark 900 ACE. @ 0x024786. Q14 format (~13364/16384=0.816 → 81.6%). "
                  "2018 (10SW011328) max=24415, 2021 max=13364 — prosiren raw_max na 25000. "
                  "Analogno GTI90 @ 0x025E50.",
)

# FALSE POSITIVE — unutar injection tablice @ 0x0222BE
# 0x0224A0 = 0x0222BE + 482B = redak 8, stupac 1 od 30×20 injection tablice
# _SPARK_IDLE_RPM_DEF = MapDef(
#     name        = "Spark — Ralanti ciljni RPM (5×12)",
#     description = "Spark 900 ACE idle RPM target tablica. "
#                   "5 temperaturnih zona × 12 RPM točaka = 60 u16 LE vrijednosti. "
#                   "Raspon ~1513–2648 RPM. Adresa: 0x0224A0.",
#     category    = "misc",
#     rows=5, cols=12,
#     byte_order  = "LE", dtype = "u16",
#     scale       = 1.0, offset_val = 0.0,
#     unit        = "RPM",
#     raw_min     = 1400, raw_max = 3000,
#     notes       = "Spark 900 ACE. @ 0x0224A0. Format 5×12 = 60 rpm vrijednosti.",
# )

_SPARK_REV_LIMITER_DEF = MapDef(
    name        = "Spark — Rev limiter hard cut (scalar)",
    description = "Spark 900 ACE rev limiter, period-encoded. "
                  "5120 ticks @ 40MHz → 8081 RPM hard cut. "
                  "Formula: RPM = 40e6 × 60 / (ticks × 58). (60-2 kotačić, 3-cil.)",
    category    = "rpm_limiter",
    rows=1, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0,
    offset_val  = 0.0,
    unit        = "ticks",
    raw_min     = 4000, raw_max = 8000,
    notes       = "Spark 900 ACE. @ 0x028E34. Identičan u 2018 i 2021 (5120 ticks = 8081 RPM). "
                  "STG2 Spark NE mijenja rev limiter! Ramp tablica @ 0x028E2E (16 val).",
)

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


# ── Spark NOVE mape (binarni scan 2026-03-18) ─────────────────────────────────
# Adrese verificirane na Spark 2021 (10SW039116), Spark 2018 (10SW011328) i STG2.
# Uspoređeno s GTI90 (10SW053774) koji dijeli isti fizički motor.

_SPARK_TORQUE_DEF = MapDef(
    name        = "Spark — Momenti ograničenje (torque limit)",
    description = (
        "Spark 900 ACE torque limit mapa. 30×20 u16 BE, Q8 format (/256). "
        "Vrijednosti 108–128 raw BE (27648–32768) = ~108–128% relativna snaga. "
        "Adresa: 0x027D9A. Mirror: 0x0282B2 (+0x518). "
        "Count bytes [30,20] @ 0x027D32 potvrđen na 2018 i 2021 binarnom."
    ),
    category    = "torque",
    rows=30, cols=20,
    byte_order  = "BE", dtype = "u16",
    scale       = 1.0 / 256.0,
    offset_val  = 0.0,
    unit        = "Nm (rel.)",
    raw_min     = 27000, raw_max = 33000,
    mirror_offset = 0x518,
    axis_x      = AxisDef(count=20, byte_order="LE", dtype="u16",
                          scale=1.0, unit="brzina motora [raw]",
                          values=[188, 234, 266, 297, 359, 406, 469, 547,
                                  625, 703, 781, 859, 938, 1016, 1094, 1172,
                                  1250, 1329, 1407, 1563]),
                          # @ 0x027D72 (20pt u16 LE, RPM raw)
    axis_y      = AxisDef(count=30, byte_order="LE", dtype="u16",
                          scale=1.0, unit="opterecenje [raw]",
                          values=[4000, 4800, 5600, 7400, 9200, 10800, 11600, 12200,
                                  12600, 13200, 13720, 14560, 15200, 16120, 16800, 17600,
                                  18800, 19600, 20400, 21600, 23040, 24000, 24960, 25800,
                                  26680, 27680, 29000, 30720, 32000, 33600]),
                          # @ 0x027D36 (30pt u16 LE, load raw)
    notes       = (
        "Spark 900 ACE. @ 0x027D9A, mirror @ 0x0282B2 (+0x518=1200B). "
        "30×20=600 u16 BE. Q8: raw/256. Count bytes [30,20] @ 0x027D32. "
        "Y-os (load 30pt) @ 0x027D36, X-os (RPM 20pt) @ 0x027D72. "
        "Binarno verificirano na 2021 (10SW039116). Mirror potvrđen: identičan blok."
    ),
)

_SPARK_LAMBDA_TRIM_DEF = MapDef(
    name        = "Spark — Lambda korekcija po RPM×Load (trim)",
    description = (
        "Spark 900 ACE lambda trim mapa — korekcija otvorene petlje. "
        "30×20 u16 LE Q15. Q15=32768 → 1.0 (stoich). "
        "Vrijednosti 31935–32903 = λ 0.975–1.004. "
        "2021 vs 2018: 240/600 razlika (ECU specifično podešavanje). "
        "Adresa: 0x024EC4."
    ),
    category    = "lambda",
    rows=30, cols=20,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 32768.0,
    offset_val  = 0.0,
    unit        = "λ korekcija",
    axis_x      = AxisDef(count=20, byte_order="LE", dtype="u16",
                          scale=1.0, unit="brzina motora [raw]",
                          values=[640, 853, 1067, 1280, 1493, 1707, 1920, 2133,
                                  2347, 2560, 2773, 2987, 3200, 3413, 3627, 3840,
                                  4053, 4267, 4480, 4693]),
                          # @ 0x024E9C (20pt u16 LE, ista os za sve lambda trim kopije)
    axis_y      = AxisDef(count=30, byte_order="LE", dtype="u16",
                          scale=1.0, unit="opterecenje [raw]",
                          values=[4800, 5600, 7600, 8800, 10000, 10800, 11600, 12600,
                                  13200, 13800, 14400, 14800, 15500, 16200, 17400, 18400,
                                  19200, 20200, 21600, 22000, 23000, 23440, 24200, 25600,
                                  26400, 28000, 29000, 30000, 31000, 32000]),
                          # @ 0x024E60 (30pt u16 LE)
    raw_min     = 31000, raw_max = 34000,
    mirror_offset = 0,
    notes       = (
        "Spark 900 ACE. @ 0x024EC4. 30×20=600 u16 LE. "
        "Q15 korekcija lambda cilja. 2021 vs 2018 razlika: 240/600 vrijednosti. "
        "Lambda (RPM,load) × trim = efektivna ciljana lambda. "
        "Identičan raspon kao GTI lambda trim @ 0x026DB8. "
        "Osi: Y-load @ 0x024E60, X-speed @ 0x024E9C. Count bytes [30,20] @ 0x024E5C."
    ),
)

_SPARK_OVERTEMP_LAMBDA_DEF = MapDef(
    name        = "Spark — Overtemp lambda zaštita",
    description = (
        "Spark 900 ACE lambda korekcija pri visokoj temperaturi. "
        "63 u16 LE Q15. Vrijednosti 5398–46613 = 0.165–1.423 λ (bogaćenje pri prehrijavanju). "
        "IDENTIČNE vrijednosti kao GTI90 overtemp lambda @ 0x025ADA. "
        "Adresa: 0x024468. Jednako 2018 i 2021."
    ),
    category    = "lambda",
    rows=63, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 32768.0,
    offset_val  = 0.0,
    unit        = "λ",
    raw_min     = 5000, raw_max = 50000,
    mirror_offset = 0,
    notes       = (
        "Spark 900 ACE. @ 0x024468. 63 u16 LE Q15. "
        "Identično GTI90 @ 0x025ADA (byte-for-byte iste vrijednosti). "
        "Nema razlike 2021 vs 2018. "
        "Bogati smjesu pri prehrijavanju (zaštita klipa)."
    ),
)

# FALSE POSITIVE — 2B unutar injection tablice @ 0x0222BE
# 0x0222C0 = 0x0222BE + 2, tj. drugi element injection tablice (30×20 u16 LE)
# _SPARK_LAMBDA_PROT_DEF = MapDef(
#     name        = "Spark — Lambda zaštitni prag (protection)",
#     description = (
#         "Spark 900 ACE lambda zaštita — donji pragovi lambda korekcije. "
#         "12×18 u16 LE. Mali Q15 raw vrijednosti (508–2154 = 0.015–0.066). "
#         "Identično na Spark 2021 i 2018. Mirror kopija @ 0x0227D8 (+0x518). "
#         "Adresa: 0x0222C0."
#     ),
#     category    = "lambda",
#     rows=12, cols=18,
#     byte_order  = "LE", dtype = "u16",
#     scale       = 1.0 / 32768.0,
#     offset_val  = 0.0,
#     unit        = "λ prag",
#     raw_min     = 400, raw_max = 2500,
#     mirror_offset = 0x518,
#     notes       = (
#         "Spark 900 ACE. @ 0x0222C0, mirror @ 0x0227D8 (+0x518=1304B). "
#         "12×18=216 u16 LE. Mali Q15 raw (508-2154 = 0.015-0.066). "
#         "Isti na 2021 i 2018 Sparku. "
#         "Donji threshold lambda korekcije."
#     ),
# )

_SPARK_THERM_ENRICH_DEF = MapDef(
    name        = "Spark — Toplinska korekcija goriva (therm enrich)",
    description = (
        "Spark 900 ACE korekcija goriva pri različitim temperaturama hladnjaka. "
        "8×7 u16 LE. Dijeljeno s 64 = %. Vrijednosti 9766–14400 = 152–225%. "
        "Slično GTI90 therm enrich @ 0x02AA42. "
        "Adresa: 0x025BAA. Nema mirrora."
    ),
    category    = "fuel",
    rows=8, cols=7,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 64.0,
    offset_val  = 0.0,
    unit        = "%",
    raw_min     = 8500, raw_max = 15000,
    mirror_offset = 0,
    notes       = (
        "Spark 900 ACE. @ 0x025BAA. 8×7=56 u16 LE. "
        "/64 = faktor obogaćivanja (%). 152-225% = bogata pri zagrijavanju. "
        "2018 (10SW011328) min=8741 (53.4%) — prosiren raw_min na 8500. "
        "Slično GTI90 @ 0x02AA42 ali Spark vrijednosti nešto drugačije. "
        "Razlika 2021 vs 2018: 3/56 vrijednosti."
    ),
)

_SPARK_LAMBDA_TRIM2_DEF = MapDef(
    name        = "Spark — Lambda korekcija 2 (trim mirror)",
    description = (
        "Spark 900 ACE druga lambda trim tablica — parnjak lambda trimu @ 0x024EC4. "
        "30×20 u16 LE Q15. ORI: uglavnom flat 32258 (λ=0.984). "
        "STG2: mijenja 650/600 vrijednosti — aktivan tuning unos. "
        "Osi: load axis copy @ 0x025378, col axis @ 0x0253B4. "
        "Adresa: 0x0253DC."
    ),
    category    = "lambda",
    rows=30, cols=20,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 32768.0,
    offset_val  = 0.0,
    unit        = "λ korekcija",
    axis_x      = AxisDef(count=20, byte_order="LE", dtype="u16",
                          scale=1.0, unit="brzina motora [raw]",
                          values=[640, 853, 1067, 1280, 1493, 1707, 1920, 2133,
                                  2347, 2560, 2773, 2987, 3200, 3413, 3627, 3840,
                                  4053, 4267, 4480, 4693]),
                          # @ 0x0253B4 (20pt u16 LE, ista skala kao trim 1)
    axis_y      = AxisDef(count=30, byte_order="LE", dtype="u16",
                          scale=1.0, unit="opterecenje [raw]",
                          values=[4800, 5600, 7400, 8600, 9600, 11000, 12200, 13200,
                                  14560, 15600, 16400, 17000, 17600, 18800, 19600, 20400,
                                  20800, 21600, 22800, 23400, 24000, 24800, 25800, 26680,
                                  27680, 29000, 29800, 30720, 32000, 33600]),
                          # @ 0x025378 (30pt u16 LE, STG2 mijenja 19/30 vrijednosti)
    raw_min     = 29000, raw_max = 34000,
    mirror_offset = 0,
    notes       = (
        "Spark 900 ACE. @ 0x0253DC. Odmah iza load+col osi @ 0x025378. "
        "ORI flat 32258=0.984. STG2 varijira 0.89-1.03 (aktivna kalibracija). "
        "Završava @ 0x02588C. Parnjak lambda trim 1 @ 0x024EC4. "
        "Osi: Y-load @ 0x025378 (30pt), X-speed @ 0x0253B4 (20pt). Count bytes [30,20] @ 0x025374."
    ),
)

_SPARK_LOAD_AXIS2_DEF = MapDef(
    name        = "Spark — Load os 2 (kopija za lambda trim 2)",
    description = (
        "Spark 900 ACE load (relativno punjenje) os — kopija za lambda trim 2. "
        "30 u16 LE vrijednosti. Identičan sadržaj kao @ 0x022282. "
        "STG2 mijenja 19/30 vrijednosti (proširuje gornji raspon). "
        "Adresa: 0x025378."
    ),
    category    = "axis",
    rows=30, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0, offset_val = 0.0,
    unit        = "raw load",
    raw_min     = 3000, raw_max = 35000,
    notes       = "Spark 900. @ 0x025378. 30pt load os za lambda trim 2. STG2 proširuje.",
)

_SPARK_LAMBDA_XAXIS_DEF = MapDef(
    name        = "Spark — Lambda X-os (16pt u8, /128=λ)",
    description = (
        "Spark 900 ACE X-os za lambda kopije (8×16 tablice). "
        "16 u8 vrijednosti, /128 = lambda (0.258–1.094λ ORI). "
        "STG2 proširuje raspon: 0.313–1.875λ (širi lean-side). "
        "Adresa: 0x024775 (neparno poravnanje — u8 format!). "
        "Korelira s lambda kopijama @ 0x025F5C (8 redova × 16 osi)."
    ),
    category    = "axis",
    rows=16, cols=1,
    byte_order  = "LE", dtype = "u8",
    scale       = 1.0 / 128.0,
    offset_val  = 0.0,
    unit        = "λ",
    raw_min     = 30, raw_max = 245,
    notes       = (
        "Spark 900. @ 0x024775 (u8, neporavnato!). 16B. "
        "ORI: [33-140] /128 = 0.258-1.094λ. STG2: [40-240] /128 = 0.313-1.875λ. "
        "X-os za lambda kopije 1-4 (svaka 8×16 = 8 redova × 16 X-točaka)."
    ),
)

_SPARK_THERM_ENRICH2_DEF = MapDef(
    name        = "Spark — Toplinska korekcija 2 (Q14, 42 vrijednosti)",
    description = (
        "Spark 900 ACE druga toplinska korekcija goriva. "
        "42 u16 LE Q14 vrijednosti. Raspon 0.706–0.816 (bogato, ispod stoich). "
        "STG2 mijenja svih 42 vrijednosti (značajna kalibracija). "
        "Adresa: 0x0248C2. Smještena neposredno iza warm-up tablice."
    ),
    category    = "fuel",
    rows=42, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 16384.0,
    offset_val  = 0.0,
    unit        = "lambda faktor",
    raw_min     = 11000, raw_max = 14000,
    notes       = (
        "Spark 900. @ 0x0248C2. 42 u16 LE Q14. Iza warm-up @ 0x024786. "
        "ORI: 11565-13364 = Q14 0.706-0.816 (bogaćenje). "
        "STG2: mijenja sve vrijednosti. Vjerojatno low-temp fuel trim."
    ),
)

_SPARK_NEUTRAL_CORR_DEF = MapDef(
    name        = "Spark — Korekcija u neutralu (neutral corr)",
    description = (
        "Spark 900 ACE korekcija goriva/napona u neutralnom položaju. "
        "80 u16 LE Q14. Sve vrijednosti = 16384 (Q14=1.0 = nema korekcije). "
        "Identično na 2021, 2018 i STG2. "
        "Adresa: 0x0237AC."
    ),
    category    = "misc",
    rows=80, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 16384.0,
    offset_val  = 0.0,
    unit        = "faktor",
    raw_min     = 16000, raw_max = 16500,
    mirror_offset = 0,
    notes       = (
        "Spark 900 ACE. @ 0x0237AC. 80 u16 LE Q14=1.0. "
        "Sve vrijednosti = 16384 (neutral = nema korekcije). "
        "GTI90 koristi 16448 (1.004) na svojoj adresi. "
        "Identično na svim Spark SW varijantama."
    ),
)

# Lambda os za load-korekcijsku tablicu (9pt Q15, lambda vrijednosti)
# Verificirano: ORI = [2686..49844] = Q15 [0.082..1.521], sentinel 65535 na offset+18
# NPRo STG2 prosiruje gornji raspon: [3996..40438] = Q15 [0.122..1.235]
_SPARK_LAMBDA_LOAD_AXIS_DEF = MapDef(
    name        = "Spark — Lambda load os (9pt Q15)",
    description = (
        "Spark 900 ACE lambda os za load-korekcijsku tablicu. "
        "9 u16 LE Q15 vrijednosti + 65535 sentinel. "
        "ORI: Q15 = [0.082, 0.110, 0.173, 0.244, 0.326, 0.427, 0.553, 0.800, 1.521]. "
        "NPRo STG2: prosiruje gornji raspon do Q15=1.235 (lean-side proširenje). "
        "Adresa: 0x023910. Y-os za lambda korekcijsku tablicu @ 0x027036."
    ),
    category    = "axis",
    rows=9, cols=1,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 32768.0,
    offset_val  = 0.0,
    unit        = "lambda",
    raw_min     = 2000, raw_max = 55000,
    notes       = (
        "Spark 900 ACE. @ 0x023910. 9 u16 LE Q15 + 65535 sentinel (offset+18). "
        "ORI: [2686, 3607, 5685, 8002, 10694, 13999, 18118, 26214, 49844]. "
        "NPRo: [3996, 6228, 10272, 19142, 25764, 32350, 40438, 49838]. "
        "Y-os za Spark lambda load correction @ 0x027036."
    ),
)

# Lambda korekcija po load-u (9x3 Q15, opada s porastom opterecenja)
# Verificirano: ORI opada 0.992->0.730, NPRo STG2 postavlja sve na 32768 (1.0 = iskljucuje)
# Format: 9 redova x 3 kolone (3 identične vrijednosti po redu — simetricna struktura)
_SPARK_LAMBDA_LOAD_CORR_DEF = MapDef(
    name        = "Spark — Lambda korekcija po load-u (9x3 Q15)",
    description = (
        "Spark 900 ACE lambda korekcija faktora po relativnom opterecenju. "
        "9 redova × 3 kolone u16 LE Q15. Svaki red ima 3 identične vrijednosti. "
        "ORI: opada od 0.992 do 0.730 (smanjuje obogacenje pri visokom load-u). "
        "NPRo STG2: postavlja sve na 32768 (Q15=1.0 = iskljucena korekcija). "
        "Adresa: 0x027036. Y-os @ 0x023910 (lambda), X-os load @ 0x02706C (12pt)."
    ),
    category    = "lambda",
    rows=9, cols=3,
    byte_order  = "LE", dtype = "u16",
    scale       = 1.0 / 32768.0,
    offset_val  = 0.0,
    unit        = "lambda faktor",
    raw_min     = 22000, raw_max = 33500,
    mirror_offset = 0,
    notes       = (
        "Spark 900 ACE. @ 0x027036. 9x3 u16 LE Q15 = 54B. "
        "ORI: [32522x3, 32070x3, 31179x3, 29948x3, 29127x3, 28551x3, 28223x3, 25481x3, 23921x3] "
        "= Q15 [0.992, 0.979, 0.952, 0.914, 0.889, 0.871, 0.861, 0.778, 0.730]. "
        "NPRo: sve 32768 (1.0 = neutralizirano). "
        "Confidence: 80% — NPRo modificira, dakle tunabilno."
    ),
)


# ─── GTI 155 / NA motor mape ──────────────────────────────────────────────────
#
# GTI SE 155 (1.5L ATM, SW 10SW025752) i srodnih NA motornih varijanti.
# Adrese verificirane binarnim skanom gti_155_18_10SW025752.bin (2026-03-18).
#
# Razlike od 300hp ACE 1630 (SC motor):
#   Injection: potpuno drugačiji format — direktne vrijednosti (ne Q15 rk)
#     @ 0x022066, 16×12, u16 LE, range ~3193–14432 raw (vs. 300hp Q15 @ 0x02439C)
#   Ignition:  šire timing vrijednosti (do 67 raw = 50.25°) — NA nema knock-ograničenje SC-a
#     Serija 8 mapa @ 0x028310, stride 144B (vs. 300hp @ 0x02B730 niži raspon)
#     NAPOMENA: 300hp adresa 0x02B730 prolazi validaciju i za GTI (range 33-43) — obje serije
#   Rev limiter: 7700 rpm potvrđeno na više mjesta (0x02B72A kod GTI = 8481 = trash 0x2121!)
#
# RPM os za GTI injection: 12-pt @ 0x02202E (u16 LE):
#   [853, 1152, 1408, 1707, 2005, 2261, 2560, 2816, 3413, 3968, 4139, 4267]
# Load os za GTI injection: 16-pt @ 0x022046 (u16 LE):
#   [5200, 6000, 8000, 10000, 12000, 14000, 16000, 18000,
#    20000, 22000, 24000, 26000, 28000, 29200, 30000, 32000]

# SW ID-ovi za Rotax 1630 ACE SC varijante (300hp, 230hp)
# Koriste 300hp injection format @ 0x02436C
_300HP_SW_IDS = {
    "10SW066726",  # ori_300, rxpx300_21 (2016-2021, RXP/RXT/GTX 300hp)
    "10SW054296",  # 300hp SC 2020 ORI (2020 model year 300hp, pronađen u dumps/2020/1630ace/)
    "10SW040039",  # npro_stg2_300 (300hp NPRo tune, radi s 2020 i 2021 ORI)
    "10SW004672",  # rxpx300_16 (300hp)
    "10SW082806",  # backup_flash (noviji 300hp variant)
    "10SW053727",  # GTI SE 230 / Wake Pro 230 2021 (Rotax 1630 SC, 230hp)
    # 10SW053729 (GTI SE 130/170 2021) — NA motor, injection @ 0x022066 (GTI format) → nije ovdje!
}

# Poznati Spark 900 ACE SW ID-ovi s "10SW0" prefiksom (starija 666-serija HW063)
# Ovi nemaju "1037" prefiks ali su verificirani Spark binariji
_SPARK_10SW_IDS = {
    "10SW011328",  # Spark 90 2016/2018 (HW063, BOOT eraziran, 666-serija)
    "10SW039116",  # Spark 90 2019-2021 (HO ACE, razlicit CODE layout od 2016)
    "1037544876",  # NPRo Spark 900 ACE Stage 2 (decimalni format, BOOT djelomično izmijenjen)
}

# GTI RPM os (12 točaka)
_GTI_RPM_12 = [853, 1152, 1408, 1707, 2005, 2261, 2560, 2816, 3413, 3968, 4139, 4267]
_GTI_RPM_AXIS_12 = AxisDef(count=12, byte_order="LE", dtype="u16",
                             scale=1.0, unit="rpm", values=_GTI_RPM_12)

# GTI Load os (16 točaka)
_GTI_LOAD_16 = [5200, 6000, 8000, 10000, 12000, 14000, 16000, 18000,
                20000, 22000, 24000, 26000, 28000, 29200, 30000, 32000]
_GTI_LOAD_AXIS_16 = AxisDef(count=16, byte_order="LE", dtype="u16",
                              scale=1.0, unit="load [raw]", values=_GTI_LOAD_16)

GTI_INJ_MAIN          = 0x022066
GTI_INJ_MIRROR_OFFSET = 0x518  # TODO: mirror offset za GTI nije potvrđen s 0 razlika

_GTI_INJ_DEF = MapDef(
    name          = "GTI — ubrizgavanje (direktno) [raw]",
    description   = (
        "GTI 155 / NA motor injection map — 16×12 tablica. "
        "DRUGAČIJI format od 300hp: direktne vrijednosti (ne Q15 rk). "
        "Range ~3193–14432 raw. Veće = dulje ubrizgavanje = više goriva. "
        "Osi: Y = opterećenje (16pt @ 0x022046), X = RPM (12pt @ 0x02202E). "
        "Nema SC korekcija — NA motor."
    ),
    category      = "injection",
    rows=16, cols=12,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0,
    offset_val    = 0.0,
    unit          = "raw",
    axis_x        = _GTI_RPM_AXIS_12,
    axis_y        = _GTI_LOAD_AXIS_16,
    raw_min       = 100,
    raw_max       = 65535,
    mirror_offset = 0,
    notes         = (
        f"@ 0x{GTI_INJ_MAIN:06X} (16×12 u16 LE, 384B). "
        "RPM os @ 0x02202E (12pt LE u16). Load os @ 0x022046 (16pt LE u16). "
        "GTI 155 specifično — NA motor, ne Q15 format. "
        "300hp injection @ 0x02439C (Q15 rk) i dalje prisutna kao sekundarna."
    ),
)

# GTI ignition — serija 8 mapa @ 0x028310, stride 144B
# Raw range 40-67 (30°-50.25°BTDC) — NA motor ima širi timing od SC motora
# Validacijski prag širi (16-70) jer NA timer dopušta do 52.5°
GTI_IGN_BASE   = 0x028310
GTI_IGN_STRIDE = 144
GTI_IGN_COUNT  = 8

_GTI_IGN_NAMES = [
    "GTI Paljenje — OS 1 (low load)",
    "GTI Paljenje — OS 2 (mid load)",
    "GTI Paljenje — OS 3 (high load)",
    "GTI Paljenje — OS 4",
    "GTI Paljenje — OS 5",
    "GTI Paljenje — OS 6",
    "GTI Paljenje — OS 7",
    "GTI Paljenje — OS 8",
]

def _make_gti_ign_def(idx: int) -> MapDef:
    addr = GTI_IGN_BASE + idx * GTI_IGN_STRIDE
    return MapDef(
        name          = _GTI_IGN_NAMES[idx],
        description   = (
            f"GTI 155 NA motor — timing mapa #{idx}. 12×12 u8, 0.75°/bit. "
            f"Vrijednosti 40-67 = 30°-50.25° pred TMT. "
            f"NA motor dopušta viši timing (nema knock-ograničenja SC boosta). "
            f"Serija od 8 mapa @ 0x028310, stride 144B."
        ),
        category      = "ignition",
        rows=12, cols=12,
        byte_order    = "BE",
        dtype         = "u8",
        scale         = 0.75,
        offset_val    = 0.0,
        unit          = "°BTDC",
        axis_x        = _RPM_AXIS_12,
        axis_y        = _LOAD_AXIS_12,
        raw_min       = 16,
        raw_max       = 70,
        mirror_offset = 0,
        notes         = (
            f"GTI 155. @ 0x{addr:06X}, stride=144B. "
            "NA motor: viši timing (40-67 raw = 30-50.25°) vs 300hp SC (33-47 raw). "
            "Validacija: 16-70 raspon (širi od 300hp 16-58)."
        ),
    )

_GTI_IGN_DEFS = [_make_gti_ign_def(i) for i in range(GTI_IGN_COUNT)]


# ─── Lambda efficiency lookup (4 kopije × 256B u8) ────────────────────────────
#
# 4 identična bloka po 256B (16×16 u8) @ 0x0275FD, 0x02771F, 0x027841, 0x027963
# stride između kopija = 290B (256B podaci + 34B X-os između kopija)
#
# IDENTIFICIRANO NPRo diff analizom (2026-03-19):
#   NPRo STG2 mijenja C0 i C1 (prvih 2 stupca) svih 16 redova: +5 do +8 raw
#   SC 300hp ORI: 102–115 raw → /128 = 0.797–0.898 (niži faktori)
#   NA 130hp:     107–120 raw → /128 = 0.836–0.938 (viši faktori, razlika!)
#   SC vs NA: KOMPLETNO RAZLIČITI (222/240 razlika u prvom bloku)
#   300hp vs 230hp SC: 56/240 razlika (C2-C3 malo niži za 300hp)
#
# Između kopija: 34B sadrži X-os vrijednosti u8 (lambda /128 = 0.125–1.773)
# Fizikalni smisao: lambda efficiency korekcija po load × lambda uvjetu
# Analogno KFWIRKBA ali u u8 formatu s 4 kopije (možda po cilindru ili uvjetu)
# Skaliranje: /128 = faktor; 300hp SC raspon 0.797–0.898 (niža efikasnost = boost)
# Confidence: 70% (nema A2L potvrde naziva)

LAMBDA_EFF_U8_ADDR_1 = 0x0275FD  # kopija 1
LAMBDA_EFF_U8_ADDR_2 = 0x02771F  # kopija 2
LAMBDA_EFF_U8_ADDR_3 = 0x027841  # kopija 3
LAMBDA_EFF_U8_ADDR_4 = 0x027963  # kopija 4
LAMBDA_EFF_U8_STRIDE = 290        # 256B podaci + 34B X-os

_LAMBDA_EFF_U8_DEF = MapDef(
    name          = "Lambda efikasnost u8 lookup (4x kopija)",
    description   = (
        "Lambda efficiency lookup u8 format — 16×16 × 4 kopije @ 0x0275FD. "
        "Svaka kopija: 256B u8 podaci + 34B X-os (lambda u8, /128). "
        "Stride izmedju kopija: 290B. SC300: 0.797-0.898, NA130: 0.836-0.938. "
        "NPRo STG2: prvih 2 stupca svih redova +5 do +8 (lean-side povecanje). "
        "SC vs NA: RAZLICITI (222/240 razlika) — SC ima nizi faktor (boost efikasnost). "
        "Fizikalni smisao: lambda Wirkungsgrad u8 sub-lookup (analogno KFWIRKBA). "
        "Confidence: 70% (nema A2L potvrde, namjena pretpostavljena)."
    ),
    category      = "lambda",
    rows=16, cols=16,
    byte_order    = "BE", dtype = "u8",
    scale         = 1.0 / 128.0,
    offset_val    = 0.0,
    unit          = "faktor /128",
    axis_x        = None,   # X-os u8 embedded per copy (@ copy_start+256B, 16 u8 /100)
                            # Copy1 X-os @ 0x0275DF: [45,50,75,100,113,120,125,145,150,158,162,169,175,188,200,208]
    axis_y        = AxisDef(count=16, byte_order="BE", dtype="u8",
                            scale=1.0/100.0, unit="λ (izmjerena)",
                            values=[20, 33, 67, 80, 93, 100, 107, 113, 120, 127,
                                    133, 140, 147, 167, 187, 227]),
                            # @ 0x0275CF (16 u8 /100 = 0.20–2.27 λ)
    raw_min       = 85,     # min valjanost
    raw_max       = 130,    # max valjanost
    mirror_offset = 0,      # kopije su stride 290B, ne direktni mirror_offset
    notes         = (
        f"4 kopije: 0x{LAMBDA_EFF_U8_ADDR_1:06X}, 0x{LAMBDA_EFF_U8_ADDR_2:06X}, "
        f"0x{LAMBDA_EFF_U8_ADDR_3:06X}, 0x{LAMBDA_EFF_U8_ADDR_4:06X}. "
        "Stride = 290B (256B data + 34B X-os u8). Skaliranje: raw/128 = faktor. "
        "NPRo STG2: C0,C1 svih redova +5 do +8 (lean-side korekcija). "
        "SC300 vs NA130: 222/240 razlika. 300hp vs 230hp: 56/240. "
        "Confidence 70% — moguce A2L naziv KFWIRKBA u8 sub (specijalni uvjeti)."
    ),
)


# ─── Lambda threshold parametri (KFWIRKBA adjacent) ───────────────────────────
#
# 158B (79 u16 LE) blok Q15 lambda vrijednosti @ 0x02B378.
# Odmah ISPRED ignition bloka (0x02B730 - 0x02B378 = 952B prostor).
# Sadrži 2 grupe lambda vrijednosti (rastuće i padajuće sekvence):
#   ORI 300hp SC: λ 0.43–1.80 (prva sekvenca rastuća, zatim padajuća)
#   ORI 130hp NA: λ 0.61–1.32 (drugačiji raspon — KOMPLETNO RAZLIČITI od SC)
#   NPRo STG2: SVE na 0xFFFF/0xFFFE (bypass svih lambda zaštitnih pragova)
#
# Prvih 14B (0x02B378 addr) promijenjeno STG2,
# još 122B (0x02B39C) promijenjeno STG2 — ukupno 136B mijenja STG2.
#
# Fizikalni smisao: KFWIRKBA lambda threshold parametri koji definiraju
# lambda opseg za KFWIRKBA korekciju. STG2 bypass = ECU ignorira sve lambda-
# zaštitne pragove (max performanse, bez toplinske zaštite).
# SC300 vs NA130: 79/79 razlika — potpuno drugačija kalibracija po varijanti.
# Confidence: 75% (Q15 lambda format potvrđen, namjena pretpostavljena)

LAMBDA_THRESH_ADDR = 0x02B378

_LAMBDA_THRESH_DEF = MapDef(
    name          = "Lambda thresholds — KFWIRKBA pragovi [Q15]",
    description   = (
        "Lambda zastitni pragovi za KFWIRKBA korekciju — 79 u16 LE Q15 vrijednosti. "
        "Odmah ispred ignition bloka (0x02B730). "
        "ORI 300hp SC: lam 0.43-1.80 (siroki raspon). ORI 130hp NA: lam 0.61-1.32 (uzi). "
        "NPRo STG2: SVE 0xFFFF/0xFFFE = bypass svih pragova (max performanse). "
        "SC vs NA: KOMPLETNO RAZLICITI (79/79 razlika). "
        "Confidence: 75% (Q15 format potvrdjen, A2L naziv nepoznat)."
    ),
    category      = "lambda",
    rows=1, cols=79,
    byte_order    = "LE", dtype = "u16",
    scale         = 1.0 / 32768.0,
    offset_val    = 0.0,
    unit          = "lambda Q15",
    axis_x        = None,
    axis_y        = None,
    raw_min       = 14000,   # lam 0.43
    raw_max       = 65535,   # lam 2.0 (bypass)
    mirror_offset = 0,
    notes         = (
        f"@ 0x{LAMBDA_THRESH_ADDR:06X} (79x u16 LE Q15 = 158B). "
        "Odmah ispred ignition bloka 0x02B730 (0x02B416 kraj STG2 promjena). "
        "SC300 raspon: lam 0.43-1.80. NA130: lam 0.61-1.32. "
        "STG2: sve 0xFFFF = bypass lambda zastita (WOT tune). "
        "Confidence 75% — dvije sekvence (rastuca + padajuca lambda)."
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

    def _is_spark(self) -> bool:
        sw = self._sw()
        # Numerički format 1037xxxxxx (npro_spark, alen_spark i sl.)
        if sw.startswith("1037") and not sw.startswith("10SW"):
            return True
        # Stariji 10SW format s poznatim Spark SW ID-ovima (HW063, 666-serija)
        return sw in _SPARK_10SW_IDS

    def _is_gti_na(self) -> bool:
        """GTI/NA motor detekcija: 10SW... ali NIJE u listi poznatih SC ni Spark SW-ova.
        Primjeri: 10SW025752 (GTI 155 2018), 10SW053774 (GTI 90 2021, Rotax 900 HO)."""
        sw = self._sw()
        return sw.startswith("10SW") and sw not in _300HP_SW_IDS and sw not in _SPARK_10SW_IDS

    def find_all(self, progress_cb: Optional[Callable] = None) -> list[FoundMap]:
        self.results = []
        is_spark  = self._is_spark()
        is_gti_na = self._is_gti_na()

        if is_spark:
            # Spark 900 ACE mape (SW: 1037xxxxxx ili 10SW011328/039116)
            if progress_cb: progress_cb(f"Spark 900 ACE SW detektiran ({self._sw()})...")
            self._scan_spark_injection(progress_cb)
            self._scan_spark_ignition(progress_cb)
            self._scan_spark_lambda(progress_cb)
            self._scan_spark_aux(progress_cb)
        else:
            # 300hp / 260hp ACE 1630 mape (SW: 10SWxxxxxx ili nepoznat)
            # Za GTI/NA: standardni scan + GTI-specifični extras
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
            self._scan_lambda_adapt(progress_cb)
            self._scan_torque_opt(progress_cb)
            self._scan_deadtime(progress_cb)
            self._scan_dfco(progress_cb)
            self._scan_decel_rpm_cut(progress_cb)
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
            self._scan_lambda_thresh(progress_cb)

            # ── GTI / NA motor specifično ──────────────────────────────────
            if is_gti_na:
                if progress_cb: progress_cb(f"GTI/NA motor SW detektiran ({self._sw()}) — dodajem GTI mape...")
                self._scan_gti_injection(progress_cb)
                self._scan_gti_ignition_extra(progress_cb)

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
                    name          = f"Rev limiter — scalar (0x{addr:06X})",
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
                name          = f"Rev limiter — soft/mid/hard (0x{base:06X})",
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

            # Flat mapa (sve ista vrijednost) je OK — neke SW verzije imaju stock flat mape

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
                    name          = "SC bypass ventil — kopija 2 [%]",
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
        n = 52
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
        if cb: cb(f"  Knock params @ 0x{addr:06X}  1×52  "
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

    # ── Lambda adaptation base scan ───────────────────────────────────────────

    def _scan_lambda_adapt(self, cb=None):
        if cb: cb("Trazim lambda adaptacijsku bazu...")
        data = self.eng.get_bytes()

        addr = LAMBDA_ADAPT_ADDR
        n    = _LAMBDA_ADAPT_DEF.rows * _LAMBDA_ADAPT_DEF.cols  # 12×18 = 216
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: Q15 lambda vrijednosti blizu 1.0 (0.76–1.22 = raw 25000–40000)
        # Lambda adapt je uska mapa (baza adaptacije), ne ide predaleko od stehiometrijskog
        in_range = sum(1 for v in vals if 25000 <= v <= 40000)
        if in_range < int(n * 0.85):
            if cb: cb(f"  Lambda adapt @ 0x{addr:06X}: premalo Q15 vrijednosti ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _LAMBDA_ADAPT_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        vmin = min(vals) / 32768.0
        vmax = max(vals) / 32768.0
        if cb: cb(f"  Lambda adapt @ 0x{addr:06X}  12×18  lambda=[{vmin:.3f}–{vmax:.3f}]")

    # ── Decel RPM cut scan ────────────────────────────────────────────────────

    def _scan_decel_rpm_cut(self, cb=None):
        if cb: cb("Trazim decel/DFCO RPM ramp tablicu...")
        data = self.eng.get_bytes()

        addr    = DECEL_RPM_CUT_ADDR
        entries = _DECEL_RPM_CUT_ENTRIES    # 16
        stride  = _DECEL_RPM_CUT_ENTRY_SIZE # 22B per entry
        total   = entries * stride           # 352B

        if addr + total > len(data):
            return

        # Čitamo sve u16 LE kao flat listu (entries×11 u16)
        n    = entries * 11
        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: col[2] (index 2 u svakom unosu od 11) mora biti period-ticks
        # 300hp ORI: col[2] svih 16 = 3879 (konst.) ili slično
        # Provjeri barem da su vrijednosti period-ticks (1000–65535) i ne sve nule
        col2_vals = [vals[i * 11 + 2] for i in range(entries)]
        valid = all(1000 <= v <= 65535 for v in col2_vals) and len(set(col2_vals)) <= 3
        if not valid:
            if cb: cb(f"  Decel RPM cut @ 0x{addr:06X}: neočekivani sadržaj col[2] — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _DECEL_RPM_CUT_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        rpm_col2 = 40_000_000 * 60 // (col2_vals[0] * 58) if col2_vals[0] else 0
        if cb: cb(f"  Decel RPM cut @ 0x{addr:06X}  16×11  col2={col2_vals[0]}t≈{rpm_col2}RPM")

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

        # Validacija: os mora biti rastuća, podaci monotono rastuci (0 je OK na pocetku)
        if not (self._monotone(axis_vals) and self._monotone(data_vals) and max(data_vals) > 0):
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
        # Vrijednosti mogu biti u razlicitim rasponima po SW verziji — dovoljno je osi OK
        if max(vals) == 0:
            if cb: cb(f"  Ign corr @ 0x{data_addr:06X}: sve nule — preskacam")
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

        # KFWIRKBA: 14×10 u8 @ EFF_CORR_ADDR (0x0259DC)
        # Validacija: Y-os (14 u8 @ 0x0259C4) rastuća, X-os (10 u8 @ 0x0259D2) rastuća
        d_addr = EFF_CORR_ADDR
        ROWS, COLS = 14, 10
        n = ROWS * COLS    # 140 u8

        if d_addr + n > len(data):
            return

        y_axis = list(data[EFF_CORR_AXIS_Y_ADDR: EFF_CORR_AXIS_Y_ADDR + 14])
        x_axis = list(data[EFF_CORR_AXIS_X_ADDR: EFF_CORR_AXIS_X_ADDR + 10])
        vals   = list(data[d_addr: d_addr + n])

        # Validacija: osi rastuće, data u rasponu 100–180
        if not self._monotone(y_axis) or not self._monotone(x_axis):
            if cb: cb(f"  Eff corr @ 0x{d_addr:06X}: osi nisu rastuće — preskacam")
            return
        in_range = sum(1 for v in vals if _EFF_CORR_DEF.raw_min <= v <= _EFF_CORR_DEF.raw_max)
        if in_range < n * 6 // 10:
            if cb: cb(f"  Eff corr @ 0x{d_addr:06X}: u8 validacija pala ({in_range}/{n}) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _EFF_CORR_DEF,
            address = d_addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Eff corr @ 0x{d_addr:06X}  14×10 u8  [{min(vals)}–{max(vals)}] /128")

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

        # Prihvati bilo koji flat Q14 faktor > 0.5 (300hp=16448, 170hp=23130 itd.)
        flat_16k = sum(1 for v in vals if 8000 <= v <= 30000)
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
        ax_ok   = self._monotone(ax_vals) and ax_vals[0] > 10000
        ax_zero = all(v == 0 for v in ax_vals)
        all_zero = all(v == 0 for v in vals)
        flat_sc  = sum(1 for v in vals if 16000 <= v <= 24000)

        if ax_zero and all_zero:
            # NA motor — os i podaci su nule
            self.results.append(FoundMap(
                defn=_SC_BOOST_FACTOR_DEF, address=addr, sw_id=self._sw(), data=vals))
            if cb: cb(f"  SC boost factor @ 0x{addr:06X}  1×40  sve 0 (NA motor)")
        elif (ax_ok or ax_zero) and flat_sc >= n // 2:
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
        n    = _DEADTIME_DEF.rows * _DEADTIME_DEF.cols  # 10 × 14 = 140
        if addr + n * 2 > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: deadtime vrijednosti u rasponu 512–3000µs (raw/0.5)
        non_zero = sum(1 for v in vals if _DEADTIME_DEF.raw_min <= v <= _DEADTIME_DEF.raw_max)
        if non_zero < n * 6 // 10:
            if cb: cb(f"  Deadtime @ 0x{addr:06X}: premalo valjanih vrijednosti — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _DEADTIME_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  Deadtime @ 0x{addr:06X}  10x14  raw=[{min(vals)}-{max(vals)}] (read-only)")

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

        # ── Serija A: 8 mapa @ 0x026A76 + idx*0x90 (manji raspon 10-60 validacija) ──
        for idx in range(8):  # 8 karti (0-7), potvrđeno 2026-03-19
            addr = 0x026A76 + idx * 0x90
            if addr + 144 > len(data):
                continue
            raw = list(data[addr:addr + 144])
            in_range = sum(1 for v in raw if 5 <= v <= 65)
            var = max(raw) - min(raw)
            if in_range / 144 >= 0.90 and var >= 8:
                self.results.append(FoundMap(
                    defn    = _SPARK_IGN_DEFS[idx],
                    address = addr,
                    sw_id   = self._sw(),
                    data    = raw,
                ))
                found += 1
                if cb: cb(f"  Spark ign A#{idx:02d} @ 0x{addr:06X}"
                          f"  raw=[{min(raw)}-{max(raw)}]"
                          f"  ({min(raw)*0.75:.1f}-{max(raw)*0.75:.1f}deg)")

        # ── Serija B: 8 mapa @ 0x0295C0 + idx*0x90 (uski raspon 20-27°) ──
        for idx in range(8):
            addr = 0x0295C0 + idx * 0x90
            if addr + 144 > len(data):
                continue
            raw = list(data[addr:addr + 144])
            in_range = sum(1 for v in raw if 5 <= v <= 65)
            if in_range / 144 >= 0.88:
                self.results.append(FoundMap(
                    defn    = _SPARK_IGN_B_DEFS[idx],
                    address = addr,
                    sw_id   = self._sw(),
                    data    = raw,
                ))
                found += 1
                if cb: cb(f"  Spark ign B#{idx:02d} @ 0x{addr:06X}"
                          f"  raw=[{min(raw)}-{max(raw)}]"
                          f"  ({min(raw)*0.75:.1f}-{max(raw)*0.75:.1f}deg)"
                          f"  {'flat' if len(set(raw))==1 else ''}")

        # ── Serija B2: 8 mapa @ 0x029B60 + idx*0x90 (svi modificirani STG2) ──
        for idx in range(8):
            addr = 0x029B60 + idx * 0x90
            if addr + 144 > len(data):
                continue
            raw = list(data[addr:addr + 144])
            in_range = sum(1 for v in raw if 5 <= v <= 65)
            if in_range / 144 >= 0.88:
                self.results.append(FoundMap(
                    defn    = _SPARK_IGN_B2_DEFS[idx],
                    address = addr,
                    sw_id   = self._sw(),
                    data    = raw,
                ))
                found += 1
                if cb: cb(f"  Spark ign B2#{idx:02d} @ 0x{addr:06X}"
                          f"  raw=[{min(raw)}-{max(raw)}]"
                          f"  ({min(raw)*0.75:.1f}-{max(raw)*0.75:.1f}deg)")

        # ── Serija C: 3 mape @ 0x02803A + idx*0x90 (u16LE, ×0.25°/bit) ──
        for idx in range(3):
            addr = 0x02803A + idx * 0x90
            if addr + 144 > len(data):
                continue
            # Ova serija je u16LE format: 72 vrijednosti s MSB=0
            vals = [int.from_bytes(data[addr+i*2:addr+i*2+2], 'little') for i in range(72)]
            odd_zeros = sum(1 for i in range(72) if data[addr+i*2+1] == 0)
            in_range = sum(1 for v in vals if 100 <= v <= 135)
            if odd_zeros >= 60 and in_range >= 50:
                self.results.append(FoundMap(
                    defn    = _SPARK_IGN_C_DEFS[idx],
                    address = addr,
                    sw_id   = self._sw(),
                    data    = vals,
                ))
                found += 1
                if cb: cb(f"  Spark ign C#{idx:02d} @ 0x{addr:06X}"
                          f"  u16LE raw=[{min(vals)}-{max(vals)}]"
                          f"  ({min(vals)*0.25:.2f}-{max(vals)*0.25:.2f}deg)")

        if cb: cb(f"  Spark ignition: {found}/27 mapa pronađeno (A:8 + B:8 + B2:8 + C:3)")

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

    def _scan_spark_aux(self, cb=None):
        """Spark 900 ACE pomoćne mape — DFCO, cold start, deadtime, idle RPM,
        knock, warm-up, start inj.  Sve adrese potvrđene binarnim skanom 2026-03-19."""
        if cb: cb("Trazim Spark aux tablice...")
        data = self.eng.get_bytes()
        sw   = self._sw()

        def _read_u16le_n(addr, n):
            return [int.from_bytes(data[addr+i*2:addr+i*2+2], 'little') for i in range(n)]

        def _add(defn, addr, vals):
            self.results.append(FoundMap(defn=defn, address=addr, sw_id=sw, data=vals))

        # ─ DFCO @ 0x021748 (7 u16 LE) ─
        addr = 0x021748
        vals = _read_u16le_n(addr, 7)
        if all(_SPARK_DFCO_DEF.raw_min <= v <= _SPARK_DFCO_DEF.raw_max for v in vals):
            _add(_SPARK_DFCO_DEF, addr, vals)
            if cb: cb(f"  Spark DFCO @ 0x{addr:06X}  [{min(vals)}..{max(vals)}] RPM")
        else:
            if cb: cb(f"  Spark DFCO @ 0x{addr:06X}: validacija pala {vals}")

        # ─ Cold start enrichment @ 0x0241F8 (6 u16 LE) ─
        addr = 0x0241F8
        vals = _read_u16le_n(addr, 6)
        if all(_SPARK_COLD_START_DEF.raw_min <= v <= _SPARK_COLD_START_DEF.raw_max for v in vals):
            _add(_SPARK_COLD_START_DEF, addr, vals)
            if cb: cb(f"  Spark cold start @ 0x{addr:06X}  {vals}")
        else:
            if cb: cb(f"  Spark cold start @ 0x{addr:06X}: validacija pala {vals}")

        # ─ Knock threshold @ 0x02408C (24 u16 LE) ─
        addr = 0x02408C
        vals = _read_u16le_n(addr, 24)
        if any(v >= _SPARK_KNOCK_DEF.raw_min for v in vals) and any(v == 65535 for v in vals):
            _add(_SPARK_KNOCK_DEF, addr, vals)
            if cb: cb(f"  Spark knock @ 0x{addr:06X}  n=24")
        else:
            if cb: cb(f"  Spark knock @ 0x{addr:06X}: validacija pala")

        # ─ Deadtime @ 0x0287A4 (8×8 = 64 u16 LE, period-encoded) ─
        addr = 0x0287A4
        n    = _SPARK_DEADTIME_DEF.rows * _SPARK_DEADTIME_DEF.cols  # 64
        vals = _read_u16le_n(addr, n)
        if all(_SPARK_DEADTIME_DEF.raw_min <= v <= _SPARK_DEADTIME_DEF.raw_max for v in vals):
            _add(_SPARK_DEADTIME_DEF, addr, vals)
            if cb: cb(f"  Spark deadtime @ 0x{addr:06X}  8×8  [{min(vals)}..{max(vals)}] ticks")
        else:
            if cb: cb(f"  Spark deadtime @ 0x{addr:06X}: validacija pala [{min(vals)}..{max(vals)}]")

        # ─ Start injection @ 0x024676 (6 u16 LE) ─
        addr = 0x024676
        vals = _read_u16le_n(addr, 6)
        if (self._monotone(vals) and vals[0] > 0 and
                all(_SPARK_START_INJ_DEF.raw_min <= v <= _SPARK_START_INJ_DEF.raw_max for v in vals)):
            _add(_SPARK_START_INJ_DEF, addr, vals)
            if cb: cb(f"  Spark start inj @ 0x{addr:06X}  {vals}")
        else:
            if cb: cb(f"  Spark start inj @ 0x{addr:06X}: validacija pala {vals}")

        # ─ Warm-up fuel @ 0x024786 (156 u16 LE) ─
        addr = 0x024786
        n    = _SPARK_WARMUP_DEF.rows * _SPARK_WARMUP_DEF.cols  # 156
        vals = _read_u16le_n(addr, n)
        if all(_SPARK_WARMUP_DEF.raw_min <= v <= _SPARK_WARMUP_DEF.raw_max for v in vals):
            _add(_SPARK_WARMUP_DEF, addr, vals)
            if cb: cb(f"  Spark warm-up @ 0x{addr:06X}  n={n}  [{min(vals)}..{max(vals)}]")
        else:
            if cb: cb(f"  Spark warm-up @ 0x{addr:06X}: validacija pala")

        # ─ Idle RPM @ 0x0224A0 — PRESKOČENO (false positive, unutar injection tablice) ─
        # Adresa 0x0224A0 = 0x0222BE + 482B (redak 8, stupac 1 od 30×20 injection tablice)

        # ─ Rev limiter hard cut @ 0x028E34 (scalar u16 LE, period ticks) ─
        addr = 0x028E34
        v    = int.from_bytes(data[addr:addr+2], 'little')
        if _SPARK_REV_LIMITER_DEF.raw_min <= v <= _SPARK_REV_LIMITER_DEF.raw_max:
            rpm = int(40_000_000 * 60 / (v * 58)) if v > 0 else 0
            _add(_SPARK_REV_LIMITER_DEF, addr, [v])
            if cb: cb(f"  Spark rev limiter @ 0x{addr:06X}  {v} ticks = {rpm} RPM")
        else:
            if cb: cb(f"  Spark rev limiter @ 0x{addr:06X}: neočekivana vrijednost {v}")

        # ─ Torque limit @ 0x027D9A (30×20 u16 BE Q8, mirror +0x518=0x0282B2) ─
        addr   = 0x027D9A
        n_torq = _SPARK_TORQUE_DEF.rows * _SPARK_TORQUE_DEF.cols  # 600
        if addr + n_torq * 2 <= len(data):
            vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'big') for i in range(n_torq)]
            if all(_SPARK_TORQUE_DEF.raw_min <= v <= _SPARK_TORQUE_DEF.raw_max for v in vals):
                _add(_SPARK_TORQUE_DEF, addr, vals)
                if cb: cb(f"  Spark torque @ 0x{addr:06X}  30×20 BE Q8  [{min(vals)}–{max(vals)}]")
            else:
                if cb: cb(f"  Spark torque @ 0x{addr:06X}: validacija pala [{min(vals)}–{max(vals)}]")

        # ─ Lambda trim @ 0x024EC4 (30×20 u16 LE Q15) ─
        addr   = 0x024EC4
        n_lt   = _SPARK_LAMBDA_TRIM_DEF.rows * _SPARK_LAMBDA_TRIM_DEF.cols  # 600
        if addr + n_lt * 2 <= len(data):
            vals = _read_u16le_n(addr, n_lt)
            if all(_SPARK_LAMBDA_TRIM_DEF.raw_min <= v <= _SPARK_LAMBDA_TRIM_DEF.raw_max for v in vals):
                _add(_SPARK_LAMBDA_TRIM_DEF, addr, vals)
                if cb: cb(f"  Spark lambda trim @ 0x{addr:06X}  30×20 LE Q15  "
                           f"[{min(vals)/32768:.3f}–{max(vals)/32768:.3f}]λ")
            else:
                if cb: cb(f"  Spark lambda trim @ 0x{addr:06X}: validacija pala "
                           f"[{min(vals)}–{max(vals)}]")

        # ─ Overtemp lambda @ 0x024468 (63 u16 LE Q15) ─
        addr  = 0x024468
        n_ovt = _SPARK_OVERTEMP_LAMBDA_DEF.rows * _SPARK_OVERTEMP_LAMBDA_DEF.cols  # 63
        if addr + n_ovt * 2 <= len(data):
            vals = _read_u16le_n(addr, n_ovt)
            if all(_SPARK_OVERTEMP_LAMBDA_DEF.raw_min <= v <= _SPARK_OVERTEMP_LAMBDA_DEF.raw_max for v in vals):
                _add(_SPARK_OVERTEMP_LAMBDA_DEF, addr, vals)
                if cb: cb(f"  Spark overtemp λ @ 0x{addr:06X}  n=63 Q15  "
                           f"[{min(vals)/32768:.3f}–{max(vals)/32768:.3f}]λ")
            else:
                if cb: cb(f"  Spark overtemp λ @ 0x{addr:06X}: validacija pala")

        # ─ Lambda protection @ 0x0222C0 — PRESKOČENO (false positive, unutar injection tablice) ─
        # Adresa 0x0222C0 = 0x0222BE + 2 (drugi element 30×20 injection tablice)

        # ─ Therm enrich @ 0x025BAA (8×7 u16 LE, /64=%) ─
        addr   = 0x025BAA
        n_therm = _SPARK_THERM_ENRICH_DEF.rows * _SPARK_THERM_ENRICH_DEF.cols  # 56
        if addr + n_therm * 2 <= len(data):
            vals = _read_u16le_n(addr, n_therm)
            if all(_SPARK_THERM_ENRICH_DEF.raw_min <= v <= _SPARK_THERM_ENRICH_DEF.raw_max for v in vals):
                _add(_SPARK_THERM_ENRICH_DEF, addr, vals)
                if cb: cb(f"  Spark therm enrich @ 0x{addr:06X}  8×7 LE  "
                           f"[{min(vals)/64:.1f}%–{max(vals)/64:.1f}%]")
            else:
                if cb: cb(f"  Spark therm enrich @ 0x{addr:06X}: validacija pala "
                           f"[{min(vals)}–{max(vals)}]")

        # ─ Neutral corr @ 0x0237AC (80 u16 LE Q14, flat=1.0) ─
        addr   = 0x0237AC
        n_neut = _SPARK_NEUTRAL_CORR_DEF.rows * _SPARK_NEUTRAL_CORR_DEF.cols  # 80
        if addr + n_neut * 2 <= len(data):
            vals = _read_u16le_n(addr, n_neut)
            if all(_SPARK_NEUTRAL_CORR_DEF.raw_min <= v <= _SPARK_NEUTRAL_CORR_DEF.raw_max for v in vals):
                _add(_SPARK_NEUTRAL_CORR_DEF, addr, vals)
                if cb: cb(f"  Spark neutral corr @ 0x{addr:06X}  n=80 Q14  "
                           f"flat={vals[0]/16384:.4f}")
            else:
                if cb: cb(f"  Spark neutral corr @ 0x{addr:06X}: validacija pala "
                           f"[{min(vals)}-{max(vals)}]")

        # ─ Lambda trim 2 @ 0x0253DC (30×20 u16 LE Q15, parnjak lambda trim 1) ─
        addr   = 0x0253DC
        n_lt2  = _SPARK_LAMBDA_TRIM2_DEF.rows * _SPARK_LAMBDA_TRIM2_DEF.cols  # 600
        if addr + n_lt2 * 2 <= len(data):
            vals = _read_u16le_n(addr, n_lt2)
            in_range = sum(1 for v in vals if _SPARK_LAMBDA_TRIM2_DEF.raw_min <= v <= _SPARK_LAMBDA_TRIM2_DEF.raw_max)
            if in_range >= n_lt2 * 0.90:
                _add(_SPARK_LAMBDA_TRIM2_DEF, addr, vals)
                if cb: cb(f"  Spark lambda trim2 @ 0x{addr:06X}  30x20 Q15  "
                           f"[{min(vals)/32768:.3f}-{max(vals)/32768:.3f}]")
            else:
                if cb: cb(f"  Spark lambda trim2 @ 0x{addr:06X}: validacija pala "
                           f"[{min(vals)}-{max(vals)}]")

        # ─ Load axis copy 2 @ 0x025378 (30pt u16 LE, za lambda trim 2) ─
        addr   = 0x025378
        n_la2  = _SPARK_LOAD_AXIS2_DEF.rows * _SPARK_LOAD_AXIS2_DEF.cols  # 30
        if addr + n_la2 * 2 <= len(data):
            vals = _read_u16le_n(addr, n_la2)
            if self._monotone(vals) and 3000 <= vals[0] <= 6000 and vals[-1] <= 40000:
                _add(_SPARK_LOAD_AXIS2_DEF, addr, vals)
                if cb: cb(f"  Spark load axis2 @ 0x{addr:06X}  n=30  {vals[0]}-{vals[-1]}")
            else:
                if cb: cb(f"  Spark load axis2 @ 0x{addr:06X}: validacija pala {vals[:4]}")

        # ─ Lambda X-axis @ 0x024775 (16pt u8, /128=lambda) ─
        addr = 0x024775
        if addr + 16 <= len(data):
            raw_u8 = list(data[addr:addr + 16])
            mono = all(raw_u8[i] < raw_u8[i+1] for i in range(len(raw_u8)-1))
            in_range = sum(1 for v in raw_u8 if _SPARK_LAMBDA_XAXIS_DEF.raw_min <= v <= _SPARK_LAMBDA_XAXIS_DEF.raw_max)
            if mono and in_range >= 14:
                _add(_SPARK_LAMBDA_XAXIS_DEF, addr, raw_u8)
                if cb: cb(f"  Spark lambda X-os @ 0x{addr:06X}  n=16 u8  "
                           f"[{raw_u8[0]/128:.3f}-{raw_u8[-1]/128:.3f}]lambda")
            else:
                if cb: cb(f"  Spark lambda X-os @ 0x{addr:06X}: validacija pala {raw_u8[:4]}")

        # ─ Thermal enrich 2 @ 0x0248C2 (42 u16 LE Q14, low-temp fuel trim) ─
        addr   = 0x0248C2
        n_te2  = _SPARK_THERM_ENRICH2_DEF.rows * _SPARK_THERM_ENRICH2_DEF.cols  # 42
        if addr + n_te2 * 2 <= len(data):
            vals = _read_u16le_n(addr, n_te2)
            in_range = sum(1 for v in vals if _SPARK_THERM_ENRICH2_DEF.raw_min <= v <= _SPARK_THERM_ENRICH2_DEF.raw_max)
            if in_range >= n_te2 * 0.85:
                _add(_SPARK_THERM_ENRICH2_DEF, addr, vals)
                if cb: cb(f"  Spark therm enrich2 @ 0x{addr:06X}  n=42 Q14  "
                           f"[{min(vals)/16384:.4f}-{max(vals)/16384:.4f}]")
            else:
                if cb: cb(f"  Spark therm enrich2 @ 0x{addr:06X}: validacija pala "
                           f"[{min(vals)}-{max(vals)}]")

        # ─ Lambda load os @ 0x023910 (9pt Q15, Y-os za load-korekcijsku tablicu) ─
        addr = 0x023910
        if addr + 20 <= len(data):
            vals = _read_u16le_n(addr, 9)
            sentinel = int.from_bytes(data[addr+18:addr+20], 'little')
            if (self._monotone(vals) and 2000 <= vals[0] <= 10000
                    and vals[-1] <= 55000 and sentinel == 65535):
                _add(_SPARK_LAMBDA_LOAD_AXIS_DEF, addr, vals)
                if cb: cb(f"  Spark lambda load os @ 0x{addr:06X}  n=9  "
                           f"[{vals[0]/32768:.3f}-{vals[-1]/32768:.3f}]lambda")
            else:
                if cb: cb(f"  Spark lambda load os @ 0x{addr:06X}: validacija pala "
                           f"{vals[:4]} sentinel={sentinel}")

        # ─ Lambda load correction @ 0x027036 (9x3 Q15, opada 0.992->0.730, NPRo=1.0) ─
        addr  = 0x027036
        n_llc = _SPARK_LAMBDA_LOAD_CORR_DEF.rows * _SPARK_LAMBDA_LOAD_CORR_DEF.cols  # 27
        if addr + n_llc * 2 <= len(data):
            vals = _read_u16le_n(addr, n_llc)
            mn, mx = min(vals), max(vals)
            all_flat = all(v == 32768 for v in vals)
            in_range = all(_SPARK_LAMBDA_LOAD_CORR_DEF.raw_min <= v
                           <= _SPARK_LAMBDA_LOAD_CORR_DEF.raw_max for v in vals)
            if in_range or all_flat:
                _add(_SPARK_LAMBDA_LOAD_CORR_DEF, addr, vals)
                if all_flat:
                    if cb: cb(f"  Spark lambda load corr @ 0x{addr:06X}  9x3 Q15  "
                               "[NPRo: sve 1.0]")
                else:
                    if cb: cb(f"  Spark lambda load corr @ 0x{addr:06X}  9x3 Q15  "
                               f"[{mn/32768:.3f}-{mx/32768:.3f}]lambda")
            else:
                if cb: cb(f"  Spark lambda load corr @ 0x{addr:06X}: validacija pala "
                           f"[{mn}-{mx}]")

        if cb: cb("  Spark aux tablice: skeniranje zavrseno")

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

    # ── GTI / NA motor scan metode ────────────────────────────────────────────

    def _scan_gti_injection(self, cb=None):
        """GTI 155 injection @ 0x022066 — 16×12, direktni format (ne Q15 rk)."""
        if cb: cb("GTI: tražim injection mapu (direktni format)...")
        data = self.eng.get_bytes()

        addr = GTI_INJ_MAIN
        n    = _GTI_INJ_DEF.rows * _GTI_INJ_DEF.cols  # 16 × 12 = 192
        if addr + n * 2 > len(data):
            if cb: cb(f"  GTI injection: adresa van granica fajla")
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little') for i in range(n)]

        # Validacija: sve vrijednosti nenula, raspon 1000-65535, nije flat
        non_zero = sum(1 for v in vals if v > 100)
        if non_zero < n * 0.9:
            if cb: cb(f"  GTI injection @ 0x{addr:06X}: previse nula ({non_zero}/{n}) — preskacam")
            return

        # Provjeri da NIJE Q15 flat format (300hp ima mnoge flat redove = nisko-varijantno)
        # GTI direktni format treba varijaciju > 500 po redu
        row_vars = [max(vals[r*12:(r+1)*12]) - min(vals[r*12:(r+1)*12]) for r in range(16)]
        varied_rows = sum(1 for v in row_vars if v > 100)
        if varied_rows < 6:
            if cb: cb(f"  GTI injection @ 0x{addr:06X}: premalo varijacije (flat Q15 format?) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _GTI_INJ_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        if cb: cb(f"  GTI injection @ 0x{addr:06X}  16×12  raw=[{min(vals)}-{max(vals)}]")

    def _scan_gti_ignition_extra(self, cb=None):
        """GTI ignition serija @ 0x028310 — 8 mapa, širi raspon (16-70 raw = do 52.5°)."""
        if cb: cb("GTI: tražim ignition extra seriju (@ 0x028310)...")
        data = self.eng.get_bytes()
        found = 0

        for idx in range(GTI_IGN_COUNT):
            addr = GTI_IGN_BASE + idx * GTI_IGN_STRIDE
            if addr + GTI_IGN_STRIDE > len(data):
                continue

            raw = list(data[addr:addr + GTI_IGN_STRIDE])

            # Validacija: NA motor ima timing do ~67 raw (50.25°)
            in_range = sum(1 for v in raw if 16 <= v <= 70)
            threshold = 0.55  # niži prag jer je raspon širi
            if in_range / len(raw) < threshold:
                if cb: cb(f"  GTI IGN extra #{idx} @ 0x{addr:06X}: validacija pala — preskacam")
                continue

            if max(raw) - min(raw) < 3:
                continue

            self.results.append(FoundMap(
                defn    = _GTI_IGN_DEFS[idx],
                address = addr,
                sw_id   = self._sw(),
                data    = raw,
            ))
            found += 1
            if cb: cb(f"  GTI IGN extra #{idx} @ 0x{addr:06X}"
                      f"  raw=[{min(raw)}-{max(raw)}] ({min(raw)*0.75:.1f}°-{max(raw)*0.75:.1f}°BTDC)")

        if cb: cb(f"  GTI ignition extra: {found}/{GTI_IGN_COUNT} pronadjeno")

    # ── Lambda efficiency u8 (4 kopije × 16×16) scan ─────────────────────────

    def _scan_lambda_eff_u8(self, cb=None):
        if cb: cb("Trazim lambda efikasnost u8 lookup (4 kopije × 16x16)...")
        data = self.eng.get_bytes()

        ROWS, COLS = 16, 16
        n = ROWS * COLS  # 256B po kopiji

        found = 0
        for copy_idx in range(4):
            addr = LAMBDA_EFF_U8_ADDR_1 + copy_idx * LAMBDA_EFF_U8_STRIDE
            if addr + n > len(data):
                continue

            raw = list(data[addr: addr + n])

            # Validacija: u8 vrijednosti u rasponu 85-130 (/128 = 0.664-1.016)
            in_range = sum(1 for v in raw if 85 <= v <= 130)
            if in_range / n < 0.70:
                if cb: cb(f"  LambdaEffU8 kopija {copy_idx+1} @ 0x{addr:06X}: validacija pala ({in_range}/{n} u rasponu) — preskacam")
                continue

            if max(raw) - min(raw) < 3:
                continue

            # Svakom kopijom pripada isti MapDef, ali s adresom te kopije
            import copy as _copy
            defn_copy = _copy.copy(_LAMBDA_EFF_U8_DEF)
            defn_copy.name = f"Lambda efikasnost u8 lookup — kopija {copy_idx+1}"
            defn_copy.notes = (
                f"Kopija {copy_idx+1}/4 @ 0x{addr:06X}. "
                f"Stride={LAMBDA_EFF_U8_STRIDE}B (256B data + 34B X-os). "
                "NPRo STG2: C0,C1 svih redova +5 do +8. "
                "SC300 vs NA130: 222/240 razlika. Confidence 70%."
            )

            self.results.append(FoundMap(
                defn    = defn_copy,
                address = addr,
                sw_id   = self._sw(),
                data    = raw,
            ))
            found += 1
            if cb: cb(f"  LambdaEffU8 kopija {copy_idx+1} @ 0x{addr:06X}"
                      f"  16x16 u8  raw=[{min(raw)}-{max(raw)}]"
                      f"  /128=[{min(raw)/128:.3f}-{max(raw)/128:.3f}]")

        if cb: cb(f"  Lambda eff u8: {found}/4 kopija pronadjeno")

    # ── Lambda threshold pragovi (KFWIRKBA adjacent) scan ────────────────────

    def _scan_lambda_thresh(self, cb=None):
        if cb: cb("Trazim lambda threshold parametre (KFWIRKBA pragovi)...")
        data = self.eng.get_bytes()

        addr = LAMBDA_THRESH_ADDR
        COLS = 79
        n_bytes = COLS * 2  # 158B u16 LE

        if addr + n_bytes > len(data):
            return

        vals = [int.from_bytes(data[addr + i*2: addr + i*2 + 2], 'little')
                for i in range(COLS)]

        # Validacija: Q15 lambda vrijednosti — normalnu raspon 14000-65535
        # STG2 postavlja na 0xFFFF (bypass); ORI ima 0.43-1.80 lambda raspon
        in_range = sum(1 for v in vals if 14000 <= v <= 65535)
        if in_range < COLS * 0.70:
            if cb: cb(f"  LambdaThresh @ 0x{addr:06X}: validacija pala ({in_range}/{COLS} u rasponu) — preskacam")
            return

        self.results.append(FoundMap(
            defn    = _LAMBDA_THRESH_DEF,
            address = addr,
            sw_id   = self._sw(),
            data    = vals,
        ))
        lam_min = min(vals) / 32768
        lam_max = max(vals) / 32768
        if cb: cb(f"  LambdaThresh @ 0x{addr:06X}  1x79 u16 LE Q15"
                  f"  lambda=[{lam_min:.3f}-{lam_max:.3f}]")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sw(self) -> str:
        return self.eng.info.sw_id if self.eng.info else "?"

    @staticmethod
    def _monotone(vals: list[int]) -> bool:
        return all(vals[i] <= vals[i+1] for i in range(len(vals)-1))
