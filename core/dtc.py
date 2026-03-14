"""
ME17Suite — DTC Manager
Bosch ME17.8.5 / TC1762

Upravljanje DTC (Diagnostic Trouble Code) fault kodovima.

=== STRUKTURA DTC U ME17.8.5 ===

  Code storage — dva mjesta (main + mirror):
    Raspon main:   0x021700-0x0218FF  (LE u16)
    Raspon mirror: 0x021A66-0x021C65  (LE u16)
    Mirror offset: UVIJEK main + 0x0366  (verificirano na 111 kodova u ori_300)

  Enable tablica @ 0x021080-0x0210BD (52 bajta):
    Svaki bajt = enable flag jednog DTC senzorskog kanala:
      0x06 = aktivno pracenje (fault se pali)
      0x05 = djelomicno pracenje
      0x04 = samo upozorenje (nema limp mode)
      0x00 = iskljuceno

  DTC OFF (kompletno):
    1. Zero code storage main (LE u16 = 0x0000)
    2. Zero code storage mirror (main + 0x0366)
    3. Zero enable bajte za taj DTC kanal

  Vazno: Checksum se NE mijenja za DTC OFF (samo CODE regija)

=== ADRESE (ori_300, SW 10SW066726) ===
  Verificirano skeniranjem svih 111 ECM P-kodova.
  Mirror offset 0x0366 potvrden za sve.

=== PODRSKA MOTORA ===
  Rotax ACE 1630 300hp  — RXP-X 300, RXT-X 300, GTX 300, Wake Pro 230 (2016+)
                          SW varijante: ori_300 (offset 0x0366), rxpx300_17 (0x0362)
  Rotax 900 HO/ACE 90hp — Sea-Doo Spark 2014+ (SW 666063, offset 0x0368)
  NISU PODRZANI:
    Rotax 1503/1504 4-TEC 260hp — RXT-X 260 (pre-2016, stariji blok, SW 524060)
                                   DTC tablica single-storage, drugacija arhitektura
    Rotax ACE 1630 230hp         — noviji 1.6L blok, SW nepoznat
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Optional


# ─── Mirror offset (globalna konstanta, verificirana) ─────────────────────────

MIRROR_OFFSET = 0x0366

# ─── Enable tablica ───────────────────────────────────────────────────────────

ENABLE_TABLE_START = 0x021080   # pocetak enable tablice
ENABLE_TABLE_END   = 0x0210BE   # kraj (ekskluzivno) — 62 bajta
ENABLE_ACTIVE_VALS = (0x04, 0x05, 0x06)


# ─── DTC definicija ───────────────────────────────────────────────────────────

@dataclass
class DtcDef:
    code:         int
    module:       str    # "ECM", "IS", "CLUSTER", "IBR"
    name:         str
    code_addr:    int    # main code storage (LE u16) u ori_300
    # enable_addr / enable_size: None = koristiti globalnu tablicu
    enable_addr:  Optional[int] = None
    enable_size:  int = 0

    @property
    def p_code(self) -> str:
        return f"P{self.code:04X}"

    @property
    def mirror_addr(self) -> int:
        return self.code_addr + MIRROR_OFFSET


# ─── DTC Registry (111 ECM kodova, ori_300 SW 10SW066726) ────────────────────

def _d(code, module, name, addr, en_addr=None, en_size=0):
    return DtcDef(code=code, module=module, name=name,
                  code_addr=addr, enable_addr=en_addr, enable_size=en_size)

DTC_REGISTRY: dict[int, DtcDef] = {d.code: d for d in [

    # ── MAP senzor (pritisak usisnog kolektora) ───────────────────────────────
    _d(0x0106, "ECM", "MAP Sensor Out of Range",           0x0217EE),
    _d(0x0107, "ECM", "MAP Sensor Short to Ground",        0x0217EC),
    _d(0x0108, "ECM", "MAP Sensor Open/Short to Battery",  0x0217EA),

    # ── IAT senzor (temperatura usisnog zraka) ────────────────────────────────
    _d(0x0112, "ECM", "IAT Sensor Short to Ground",        0x0218BA),
    _d(0x0113, "ECM", "IAT Sensor Open/Short to Battery",  0x0218BC),

    # ── Coolant temperatura ───────────────────────────────────────────────────
    _d(0x0116, "ECM", "Coolant Temp Signal Not Plausible", 0x0218C6),
    _d(0x0117, "ECM", "Coolant Temp Short to Ground",      0x0218C2),
    _d(0x0118, "ECM", "Coolant Temp Open/Disconnected",    0x0218C4),
    _d(0x0217, "ECM", "Coolant Temp High Detected",        0x0218C0),

    # ── TPS (polozaj leptira) ─────────────────────────────────────────────────
    _d(0x0122, "ECM", "TPS1 Short Circuit to GND",         0x021894),
    _d(0x0123, "ECM", "TPS1 Short Circuit to Battery",     0x021890),
    _d(0x0222, "ECM", "TPS2 Short Circuit to GND",         0x021896),
    _d(0x0223, "ECM", "TPS2 Short Circuit to Battery",     0x021892),
    _d(0x212C, "ECM", "TPS2 Electrical Lower-Range",       0x0217E4),
    _d(0x212D, "ECM", "TPS2 Electrical Upper-Range",       0x0217E2),
    _d(0x2620, "ECM", "TPS Value Not Plausible",           0x0217E6),
    _d(0x2621, "ECM", "TPS Electrical Lower-Range",        0x0217E0),
    _d(0x2622, "ECM", "TPS Electrical Upper-Range",        0x0217DE),
    _d(0x2159, "ECM", "TAS Synchronization Error",         0x021828),
    _d(0x1120, "ECM", "TOPS Violation TPS2",               0x0217DC),

    # ── Intake air temp / pressure ────────────────────────────────────────────
    _d(0x0127, "ECM", "Intake Air Temp Sensor Fault",      0x0218B8),
    _d(0x2279, "ECM", "Air Intake Manifold Leak",          0x0217E8),
    _d(0x1106, "ECM", "Altitude Correction Not Plausible", 0x0218E6),

    # ── Lambda / O2 senzor ────────────────────────────────────────────────────
    # NAPOMENA: Rotax ACE 1630 i 900 HO ne koriste fizicku lambda sondu.
    # Lambda mapa u kalibraciji je open-loop AFR korekcija (bez feedbacka).
    # P003x (heater PS) kodovi su prisutni u binarnom fajlu ali nikad ne okidaju.
    _d(0x0130, "ECM", "O2 Sensor Downstream",              0x021858),
    _d(0x0131, "ECM", "O2 Sensor Signal Low",              0x021856),
    _d(0x0132, "ECM", "O2 Sensor Signal High",             0x021854),
    _d(0x0133, "ECM", "O2 Sensor Slow Response",           0x02184E),
    _d(0x0135, "ECM", "O2 Sensor Heater Fault",            0x02182C),
    _d(0x1030, "ECM", "Lambda Heater Power Stage",         0x021834),
    _d(0x1130, "ECM", "Lambda Sensor Upstream Catalyst",   0x02185A),

    # ── Mixture adaptation (lambda korekcija) ─────────────────────────────────
    _d(0x0171, "ECM", "Mixture Adaptation Lean (upper)",   0x021844),
    _d(0x0172, "ECM", "Mixture Adaptation Rich (lower)",   0x021846),
    _d(0x1171, "ECM", "Additive Mixture Trim Lean",        0x021848),
    _d(0x1172, "ECM", "Additive Mixture Trim Rich",        0x02184A),

    # ── Temperatura ulja ──────────────────────────────────────────────────────
    _d(0x0197, "ECM", "Oil Temp Sensor Low",               0x0218CA),
    _d(0x0198, "ECM", "Oil Temp Sensor High",              0x0218C8),

    # ── Injektori power stage ─────────────────────────────────────────────────
    _d(0x0201, "ECM", "Injector 1 Power Stage Open",       0x021826),
    _d(0x0202, "ECM", "Injector 2 Power Stage Open",       0x02181A),
    _d(0x0203, "ECM", "Injector 3 Power Stage Open",       0x021820),

    # ── Injektori (direktni) ──────────────────────────────────────────────────
    _d(0x0261, "ECM", "Injector 1 Open/Short to GND",      0x021824),
    _d(0x0262, "ECM", "Injector 1 Short to Battery",       0x021822),
    _d(0x0264, "ECM", "Injector 2 Open/Short to GND",      0x021818),
    _d(0x0265, "ECM", "Injector 2 Short to Battery",       0x021816),
    _d(0x0267, "ECM", "Injector 3 Open/Short to GND",      0x02181E),
    _d(0x0268, "ECM", "Injector 3 Short to Battery",       0x02181C),

    # ── Fuel pump ─────────────────────────────────────────────────────────────
    _d(0x0231, "ECM", "Fuel Pump Open/Short to Ground",    0x0217BC),
    _d(0x0232, "ECM", "Fuel Pump Short to Battery",        0x0217BE),

    # ── Misfire ───────────────────────────────────────────────────────────────
    _d(0x0300, "ECM", "Multiple Misfire Detected",         0x02185C),
    _d(0x0301, "ECM", "Misfire Cylinder 1",                0x021862),
    _d(0x0302, "ECM", "Misfire Cylinder 2",                0x02185E),
    _d(0x0303, "ECM", "Misfire Cylinder 3",                0x021860),

    # ── Knock senzor ─────────────────────────────────────────────────────────
    _d(0x0325, "ECM", "Knock Sensor Fault",                0x021842),

    # ── Crank / Cam senzori ───────────────────────────────────────────────────
    _d(0x0335, "ECM", "Crankshaft Signal Error",           0x021814),
    _d(0x0340, "ECM", "Camshaft Signal Error",             0x021812),

    # ── Ignition coil / Power Stage ───────────────────────────────────────────
    _d(0x0357, "ECM", "Ignition Coil 1 Short to Y+",       0x02183A),
    _d(0x0358, "ECM", "Ignition Coil 2 Short to Y+",       0x021836),
    _d(0x0359, "ECM", "Ignition Coil 3 Short to Y+",       0x021838),
    _d(0x0360, "ECM", "Ignition PS Max Error Cyl3",        0x021840),
    _d(0x0361, "ECM", "Ignition PS Max Error Cyl1",        0x02183C),
    _d(0x0362, "ECM", "Ignition PS Max Error Cyl2",        0x02183E),

    # ── Speed senzor ──────────────────────────────────────────────────────────
    _d(0x0500, "ECM", "Vehicle Speed Sensor Open",         0x0218E2),
    _d(0x0501, "ECM", "Vehicle Speed Sensor Fault",        0x0218E0),

    # ── Starter / DESS ────────────────────────────────────────────────────────
    _d(0x0512, "ECM", "Starter Motor Stage Fault",         0x0218A0),
    _d(0x0513, "ECM", "Invalid DESS Key",                  0x021882),

    # ── Oil pressure (Olas senzor) ────────────────────────────────────────────
    _d(0x0520, "ECM", "Oil Pressure Switch Functional Problem", 0x02188E),
    _d(0x0523, "ECM", "Oil Pressure Sensor Fault",         0x02188C,
       en_addr=0x02108E, en_size=11),
    _d(0x0524, "ECM", "Low Oil Pressure Condition",        0x02188A),
    _d(0x0298, "ECM", "Oil Pressure Derived Fault",        0x0218D6),

    # ── EGT (temperatura ispusnih plinova) ────────────────────────────────────
    _d(0x0544, "ECM", "EGT Sensor Open/Short to Battery",  0x0218B6),
    _d(0x0545, "ECM", "EGT Sensor Short to Ground",        0x0218B2),
    _d(0x0546, "ECM", "EGT Sensor Short to Battery",       0x0218B4),
    _d(0x2080, "ECM", "EGT Sensor B Low",                  0x0218B0),
    _d(0x2081, "ECM", "EGT Sensor B High",                 0x0218AE),
    _d(0x2428, "ECM", "High EGT Detected",                 0x0218AC),

    # ── Battery napon ─────────────────────────────────────────────────────────
    _d(0x0560, "ECM", "Battery Voltage Not Plausible",     0x0218DE),
    _d(0x0562, "ECM", "Battery Voltage Too Low",           0x0218DC),
    _d(0x0563, "ECM", "Battery Voltage Too High",          0x0218DA),

    # ── ECM self-diagnostics ──────────────────────────────────────────────────
    _d(0x0606, "ECM", "ECM ADC Fault",                     0x0217B6),
    _d(0x0610, "ECM", "ECM Variant Coding Fault",          0x0218E4),
    _d(0x062F, "ECM", "ECM EEPROM Fault",                  0x0217DA),
    _d(0x0650, "ECM", "ECM Field ADC Fault",               0x021868),
    _d(0x2610, "ECM", "ECM RTC Fault",                     0x02186A),

    # ── TOPS (Throttle Override Protection System) ────────────────────────────
    _d(0x1502, "ECM", "TOPS Switch Short to GND",          0x0218D2),
    _d(0x1503, "ECM", "TOPS Switch Short to 12V",          0x0218CC),
    _d(0x1504, "ECM", "TOPS Switch Open Circuit",          0x0218CE),
    _d(0x1505, "ECM", "TOPS Switch Active",                0x0218D0),
    _d(0x1506, "ECM", "TOPS Switch Fault Non-Plausible",   0x0218D4),
    _d(0x1509, "ECM", "TOPS Functional Fault",             0x0218D8),

    # ── Boost / Olas senzor ───────────────────────────────────────────────────
    _d(0x1550, "ECM", "Boost/Olas Pressure Sensor Fault",  0x021888,
       en_addr=0x02108A, en_size=10),

    # ── Throttle actuator (DBW motor) ─────────────────────────────────────────
    _d(0x1610, "ECM", "Throttle Actuator Power Stage A",   0x0217F0),
    _d(0x1611, "ECM", "Throttle Actuator Power Stage B",   0x0217F2),
    _d(0x1612, "ECM", "Throttle Actuator Return Spring",   0x0217F4),
    _d(0x1613, "ECM", "Throttle Actuator Default Position",0x0217F6),
    _d(0x1614, "ECM", "Throttle Actuator Pos Monitoring",  0x0217F8),
    _d(0x1615, "ECM", "Throttle Actuator Default Check",   0x0217FA),
    _d(0x1616, "ECM", "Throttle Actuator Learning Fault",  0x0217FC),
    _d(0x1619, "ECM", "Throttle Actuator Upper Limit",     0x021802),
    _d(0x1620, "ECM", "Throttle Actuator Lower Limit",     0x021804),
    _d(0x1621, "ECM", "Throttle Actuator Abort Adapt",     0x021808),
    _d(0x1622, "ECM", "Throttle Actuator Repeated Abort",  0x021806),

    # ── DESS key ──────────────────────────────────────────────────────────────
    _d(0x1647, "ECM", "DESS Key Communication A",          0x0218A6),
    _d(0x1648, "ECM", "DESS Key Communication B",          0x0218A4),
    _d(0x1649, "ECM", "DESS Key Communication C",          0x0218A2),
    _d(0x1651, "ECM", "DESS Key Voltage Low",              0x021866),
    _d(0x1652, "ECM", "DESS Key Voltage High",             0x021864),
    _d(0x1654, "ECM", "DESS Key Out of Range",             0x02184C),
    _d(0x1657, "ECM", "DESS Key Signal A",                 0x021852),
    _d(0x1658, "ECM", "DESS Key Signal B",                 0x021850),

    # ── iBR (Intelligent Brake and Reverse) ───────────────────────────────────
    _d(0x1661, "IS",  "iBR Malfunction",                   0x02189A),
    _d(0x1662, "IS",  "iBR Torque Request Not Plausible",  0x02189C),

    # ── Main relay ────────────────────────────────────────────────────────────
    _d(0x1679, "ECM", "Main Relay Sticking",               0x0218A8),

]}


# ─── DTC Status ───────────────────────────────────────────────────────────────

@dataclass
class DtcStatus:
    defn:          DtcDef
    enable_values: list[int]
    code_main:     int
    code_mirror:   int

    @property
    def is_active(self) -> bool:
        return any(b != 0x00 for b in self.enable_values) or self.code_main != 0

    @property
    def is_off(self) -> bool:
        return (all(b == 0x00 for b in self.enable_values)
                and self.code_main == 0 and self.code_mirror == 0)

    @property
    def status_str(self) -> str:
        if self.is_off:
            return "OFF"
        active = sum(1 for b in self.enable_values if b != 0)
        code_s = f"  code=0x{self.code_main:04X}" if self.code_main else ""
        return f"AKTIVAN ({active}/{len(self.enable_values)} en){code_s}"


# ─── DTC Scanner — runtime detekcija tablice ──────────────────────────────────

class DtcScanResult:
    """Rezultat dinamickog skeniranja DTC tablice u binarnom fajlu."""
    def __init__(self, mirror_offset: int, addrs: dict, sw_hint: str = ""):
        self.mirror_offset = mirror_offset          # potvrdjeni mirror offset
        self.addrs: dict[int, int] = addrs          # {dtc_code: main_addr}
        self.sw_hint = sw_hint

    def __repr__(self):
        return (f"DtcScanResult(offset=0x{self.mirror_offset:04X}, "
                f"codes={len(self.addrs)}, hint={self.sw_hint!r})")


class DtcScanner:
    """
    Dinamicki pronalazi DTC code storage tablicu u ME17.8.5 binarnom fajlu.

    Radi za sve poznate SW verzije:
      ori_300 (10SW066726) — offset 0x0366, baza ~0x021700
      rxpx300_17           — offset 0x0362, baza ~0x021700
      spark_90 (666063)    — offset 0x0368, baza ~0x020F00
    """

    # Skup kodova za detekciju — svi bi trebali biti u tablici
    ANCHOR_CODES = {
        0x0106, 0x0107, 0x0108,
        0x0112, 0x0113,
        0x0116, 0x0117, 0x0118,
        0x0122, 0x0123,
        0x0300, 0x0301, 0x0302,
        0x0335, 0x0340,
        0x0512, 0x0523,
        0x1550, 0x1610, 0x1611,
        0x1647, 0x1648,
    }
    # Siri skup za mapiranje adresa
    ALL_CODES = set(DTC_REGISTRY.keys())

    CODE_REGION_START = 0x010000
    CODE_REGION_END   = 0x060000
    OFFSET_MIN = 0x0280
    OFFSET_MAX = 0x0600
    ANCHOR_THRESHOLD = 10   # min anchor kodova za detekciju

    @classmethod
    def scan(cls, data: bytes) -> Optional["DtcScanResult"]:
        """
        Skeniraj binary i vrati DtcScanResult ili None ako tablica nije nadjena.

        Podrzava:
          - Mirror-pair storage: main + mirror (off 0x0280-0x0600) — 300hp i 90hp Spark
          - Single storage: samo jedan primjerak, bez mirrora — 260hp (SW 524060)
        """
        region_end = min(cls.CODE_REGION_END, len(data))
        # DTC tablica je uvijek u 0x020000-0x025000 za poznate SW verzije
        VOTE_START = 0x020000
        VOTE_END   = min(0x025000, region_end)

        # Korak 1: nadji sve adrese anchor kodova u glasonom prozoru
        code_to_addrs: dict[int, list[int]] = {}
        for addr in range(VOTE_START, VOTE_END - 1, 2):
            val = struct.unpack_from("<H", data, addr)[0]
            if val in cls.ANCHOR_CODES:
                code_to_addrs.setdefault(val, []).append(addr)

        if not code_to_addrs:
            return None

        # Korak 2: glasanje za mirror offset — samo unutar VOTE prozora
        # Filtriraj kodove koji se pojavljuju previse puta (lazni pozitivni iz kalibracijskih tablica)
        from collections import Counter
        offset_votes: Counter = Counter()
        for code, addrs in code_to_addrs.items():
            if len(addrs) < 2 or len(addrs) > 4:
                continue  # previse pojava = nije DTC storage, preskoci
            for i, a1 in enumerate(addrs):
                for a2 in addrs[i + 1:]:
                    off = a2 - a1
                    if cls.OFFSET_MIN <= off <= cls.OFFSET_MAX:
                        offset_votes[off] += 1

        # Korak 3a: mirror-pair mode (najcesci slucaj)
        if offset_votes:
            best_offset, best_votes = offset_votes.most_common(1)[0]
            if best_votes >= 5:
                found_addrs: dict[int, int] = {}
                # Skupljaj parove samo u VOTE prozoru da izbjegnemo lazne pozitivne
                for addr in range(VOTE_START, VOTE_END - 1, 2):
                    val = struct.unpack_from("<H", data, addr)[0]
                    if val not in cls.ALL_CODES:
                        continue
                    mirror = addr + best_offset
                    if mirror + 2 <= len(data):
                        if struct.unpack_from("<H", data, mirror)[0] == val and val not in found_addrs:
                            found_addrs[val] = addr
                if len(found_addrs) >= cls.ANCHOR_THRESHOLD:
                    return cls._make_result(found_addrs, best_offset)

        # Korak 3b: fallback — single storage (bez mirrora), npr. rxtx_260
        # Trazi gusti klaster DTC kodova u prozoru 1KB
        best_window_addr = 0
        best_window_count = 0
        best_window_codes: dict[int, int] = {}
        WINDOW = 0x800
        for start in range(cls.CODE_REGION_START, cls.CODE_REGION_END - WINDOW, 0x100):
            window: dict[int, int] = {}
            for off in range(0, WINDOW, 2):
                if start + off + 2 > len(data):
                    break
                val = struct.unpack_from("<H", data, start + off)[0]
                if val in cls.ALL_CODES and val not in window:
                    window[val] = start + off
            if len(window) > best_window_count:
                best_window_count = len(window)
                best_window_addr = start
                best_window_codes = dict(window)

        if best_window_count >= cls.ANCHOR_THRESHOLD:
            # Single storage — mirror offset = 0 (koristit ce isti addr za oboje)
            return cls._make_result(best_window_codes, 0, single_storage=True)

        return None

    @classmethod
    def _make_result(cls, found_addrs: dict, offset: int,
                     single_storage: bool = False) -> "DtcScanResult":
        # Odredi SW hint
        p1550 = found_addrs.get(0x1550, 0)
        if p1550 == 0x02187E:
            sw_hint = "rxpx300_17 (SW ~17)"
        elif p1550 == 0x021888:
            sw_hint = "ori_300 (10SW066726)"
        elif 0x020F00 <= p1550 <= 0x020FFF:
            sw_hint = "spark_90 (666063)"
        elif single_storage:
            p106 = found_addrs.get(0x0106, 0)
            sw_hint = f"single-storage (P0106@0x{p106:06X})"
        else:
            sw_hint = f"unknown-pair (P1550@0x{p1550:06X})"
        return DtcScanResult(offset, found_addrs, sw_hint)


# ─── DTC Engine ───────────────────────────────────────────────────────────────

class DtcEngine:
    """
    DTC provjera i iskljucivanje za ME17.8.5.

    Automatski detektira DTC tablicu za bilo koji SW:
      - ori_300 (offset 0x0366), rxpx300_17 (0x0362), spark_90 (0x0368)
    Checksum se NE mijenja (sve promjene su u CODE regiji).
    """

    def __init__(self, engine):
        self.eng = engine
        self._scan: Optional[DtcScanResult] = None
        self._rescan()

    def _rescan(self):
        """(Re)skeniraj ucitani binary za DTC tablicu."""
        self._scan = DtcScanner.scan(self.eng.get_bytes())

    def _resolve(self, dtc_code: int) -> tuple[int, int]:
        """
        Vrati (main_addr, mirror_addr) za dati DTC kod.
        Prioritet: skenirano > registry default.
        Za single-storage (offset=0): mirror_addr = main_addr.
        """
        if self._scan and dtc_code in self._scan.addrs:
            main = self._scan.addrs[dtc_code]
            if self._scan.mirror_offset == 0:
                return main, main   # single-storage: isti addr
            return main, main + self._scan.mirror_offset
        defn = DTC_REGISTRY.get(dtc_code)
        if defn:
            return defn.code_addr, defn.mirror_addr
        return 0, 0

    @property
    def scan_result(self) -> Optional[DtcScanResult]:
        return self._scan

    @property
    def mirror_offset(self) -> int:
        return self._scan.mirror_offset if self._scan else MIRROR_OFFSET

    def get_status(self, dtc_code: int) -> Optional[DtcStatus]:
        defn = DTC_REGISTRY.get(dtc_code)
        if not defn:
            return None
        data = self.eng.get_bytes()
        if defn.enable_addr and defn.enable_size:
            enable_vals = [data[defn.enable_addr + i] for i in range(defn.enable_size)]
        else:
            enable_vals = []
        main_addr, mirror_addr = self._resolve(dtc_code)
        if main_addr == 0:
            return None
        code_main   = struct.unpack_from("<H", data, main_addr)[0]
        code_mirror = struct.unpack_from("<H", data, mirror_addr)[0]
        return DtcStatus(defn, enable_vals, code_main, code_mirror)

    def get_all_status(self) -> list[DtcStatus]:
        return [s for code in DTC_REGISTRY if (s := self.get_status(code)) is not None]

    def get_active(self) -> list[DtcStatus]:
        """Vrati samo aktivne (neprazne) DTC-ove."""
        return [s for s in self.get_all_status() if s.is_active]

    def dtc_off(self, dtc_code: int) -> dict:
        """
        Isklju?i DTC:
          1. Zero enable bajti (ako su poznati)
          2. Zero main code storage
          3. Zero mirror code storage
        """
        defn = DTC_REGISTRY.get(dtc_code)
        if not defn:
            return {"status": "ERROR", "message": f"Nepoznati DTC: P{dtc_code:04X}"}

        main_addr, mirror_addr = self._resolve(dtc_code)
        if main_addr == 0:
            return {"status": "ERROR",
                    "message": f"{defn.p_code} — adresa nije nadjena u ovom binarnom fajlu."}

        status_before = self.get_status(dtc_code)
        if status_before and status_before.is_off:
            return {"status": "ALREADY_OFF",
                    "message": f"{defn.p_code} je vec iskljucen."}

        # Enable bajti
        if defn.enable_addr and defn.enable_size:
            for i in range(defn.enable_size):
                self.eng.write_u8(defn.enable_addr + i, 0x00)

        # Code storage
        self.eng.write_u16_le(main_addr,   0x0000)
        self.eng.write_u16_le(mirror_addr, 0x0000)

        return {
            "status":        "OK",
            "message":       f"{defn.p_code} ({defn.name}) — iskljucen.",
            "main_addr":     f"0x{main_addr:06X}",
            "mirror_addr":   f"0x{mirror_addr:06X}",
            "enable_before": [hex(b) for b in (status_before.enable_values if status_before else [])],
            "code_before":   f"0x{status_before.code_main:04X}" if status_before else "?",
            "bytes_changed": (defn.enable_size if defn.enable_addr else 0) + 4,
        }

    def dtc_on(self, dtc_code: int, enable_value: int = 0x06) -> dict:
        """Vrati DTC pracenje. NAPOMENA: enable_value se postavlja uniformno."""
        defn = DTC_REGISTRY.get(dtc_code)
        if not defn:
            return {"status": "ERROR", "message": f"Nepoznati DTC: P{dtc_code:04X}"}
        if enable_value not in (0x04, 0x05, 0x06):
            return {"status": "ERROR", "message": f"Nevazeca enable vrijednost: 0x{enable_value:02X}"}

        main_addr, mirror_addr = self._resolve(dtc_code)
        if main_addr == 0:
            return {"status": "ERROR",
                    "message": f"{defn.p_code} — adresa nije nadjena."}

        if defn.enable_addr and defn.enable_size:
            for i in range(defn.enable_size):
                self.eng.write_u8(defn.enable_addr + i, enable_value)

        self.eng.write_u16_le(main_addr,   defn.code)
        self.eng.write_u16_le(mirror_addr, defn.code)

        return {"status": "OK",
                "message": f"{defn.p_code} ({defn.name}) — ukljucen (en=0x{enable_value:02X})."}

    def dtc_off_all(self) -> dict:
        """Isklj?uci sve poznate ECM DTC-ove."""
        results = {}
        for code in DTC_REGISTRY:
            r = self.dtc_off(code)
            results[f"P{code:04X}"] = r
        changed = sum(1 for r in results.values() if r["status"] == "OK")
        return {
            "status":  "OK",
            "results": results,
            "total":   len(results),
            "changed": changed,
        }

    def disable_all_monitoring(self) -> dict:
        """
        Iskljuci cijelu enable tablicu (0x021080-0x0210BD).
        Najjaca opcija — ECU nece detektirati niti jedan fault.
        Koristiti oprezno: neke greske stite motor (misfire, oil pressure).
        """
        count = 0
        for addr in range(ENABLE_TABLE_START, ENABLE_TABLE_END):
            if self.eng.get_bytes()[addr] in ENABLE_ACTIVE_VALS:
                self.eng.write_u8(addr, 0x00)
                count += 1
        return {"status": "OK",
                "message": f"Enable tablica ociscena — {count} bajta nuliran.",
                "bytes_changed": count}
