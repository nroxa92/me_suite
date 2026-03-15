"""
ME17Suite — Map Calculators
Rotax ACE 1630 / Bosch ME17.8.5

Čiste matematičke funkcije + lookup tablice bazirane na stvarnim ORI vrijednostima.
Nema dependency na engine/map_finder — može se koristiti standalone.
"""

from __future__ import annotations
import math


# ─── Konstante ───────────────────────────────────────────────────────────────

STOICH_PETROL  = 14.7   # AFR lambda=1.0 za benzin
STOICH_E10     = 14.08  # AFR lambda=1.0 za E10
STOICH_E85     = 9.76   # AFR lambda=1.0 za E85

ATM_BAR        = 1.01325  # 1 atm u bar

# ACE 1630 SC karakteristike (iz ORI firmware analize)
# SC bypass mapa (ORI 300hp): 7 RPM kolona × 7 load redova
# Bypass 0=puni boost, 255=bez boosta (linearno 0-100% otvoreni bypass)
_ORI_BYPASS_RPM_COLS  = [1050, 2100, 3150, 4200, 5250, 6300, 7350]
_ORI_BYPASS_LOAD_ROWS = [51, 77, 102, 128, 154, 179, 205]   # 0x33–0xCD

# ORI bypass vrijednosti (raw 0-255, niže = više boosta)
# Iz firmware scan @ 0x0205A8, 300hp ORI
_ORI_BYPASS_MAP = [
    [205, 205, 192, 166, 154, 154, 154],   # load 51  (nizak)
    [205, 205, 192, 128, 102,  64,  51],   # load 77
    [205, 205, 179, 115,  77,  51,  38],   # load 102
    [205, 205, 166, 102,  64,  38,  38],   # load 128
    [205, 192, 154,  89,  51,  38,  38],   # load 154
    [205, 192, 128,  77,  51,  38,  38],   # load 179
    [205, 192, 115,  64,  38,  38,  38],   # load 205 (WOT)
]

# Maks boost (bar gauge) pri 0% bypass, 7000rpm — iz manualnih mjerenja RXP300
_SC_MAX_BOOST_GAUGE = 0.62   # ~9 PSI max gauge pri WOT

# ORI ignition timing lookup (aprox. iz firmware @ 0x02B730, map idx 0, srednji load)
# Baza za timing korekciju
_ORI_TIMING_RPM = [1000, 1500, 2000, 2500, 3000, 3500, 4000,
                   4500, 5000, 5500, 6000, 6500]
_ORI_TIMING_BASE = [24.0, 25.5, 27.0, 28.5, 30.0, 31.5, 33.0,
                    33.75, 33.75, 33.0, 30.75, 28.5]


# ─── Klasa MapCalculator ─────────────────────────────────────────────────────

class MapCalculator:
    """
    Kalkulator za ECU mape Rotax ACE 1630.

    Sve metode su statičke — nema state-a, nema dependency-ja.
    """

    # ── AFR / Lambda ──────────────────────────────────────────────────────────

    @staticmethod
    def afr_to_lambda(afr: float, fuel: str = "petrol") -> float:
        """Konverzija AFR → lambda. fuel: 'petrol', 'e10', 'e85'."""
        stoich = {"petrol": STOICH_PETROL, "e10": STOICH_E10, "e85": STOICH_E85}.get(fuel, STOICH_PETROL)
        if stoich == 0:
            raise ValueError("Stoichiometric AFR ne može biti 0.")
        return afr / stoich

    @staticmethod
    def lambda_to_afr(lam: float, fuel: str = "petrol") -> float:
        """Konverzija lambda → AFR."""
        stoich = {"petrol": STOICH_PETROL, "e10": STOICH_E10, "e85": STOICH_E85}.get(fuel, STOICH_PETROL)
        return lam * stoich

    @staticmethod
    def afr_description(afr: float) -> str:
        """Opisna klasifikacija AFR-a."""
        if afr < 11.0:  return "KRITIČNO BOGATO — zalijevanje, lambda <0.75"
        if afr < 12.9:  return "Bogato — enrichment, WOT tipično 12.5-13.5"
        if afr < 14.2:  return "Blago bogato — tipično pri djelomičnom gasu"
        if afr < 15.2:  return "Stoichiometrično — lambda ≈1.0, EGO korekcija"
        if afr < 16.5:  return "Blago sirovo — cruise/decel"
        return              "OPASNO SIROVO — rizik lean misfire/oštećenja"

    # ── Pritisak ──────────────────────────────────────────────────────────────

    @staticmethod
    def bar_to_psi(bar: float) -> float:
        return bar * 14.5038

    @staticmethod
    def psi_to_bar(psi: float) -> float:
        return psi / 14.5038

    @staticmethod
    def bar_to_mmhg(bar: float) -> float:
        return bar * 750.062

    @staticmethod
    def bar_abs_to_gauge(bar_abs: float) -> float:
        """Apsolutni tlak → manometarski (gauge) tlak."""
        return bar_abs - ATM_BAR

    @staticmethod
    def bar_gauge_to_abs(bar_gauge: float) -> float:
        return bar_gauge + ATM_BAR

    # ── SC Bypass → Boost ─────────────────────────────────────────────────────

    @staticmethod
    def bypass_raw_to_pct(raw: int) -> float:
        """Raw bypass vrijednost (0-255) → % otvaranja (0%=maks boost, 100%=bez boosta)."""
        return raw * 100.0 / 255.0

    @staticmethod
    def bypass_pct_to_bar_abs(bypass_pct: float, rpm: float) -> float:
        """
        Procijenjeni boost (bar abs) na temelju % otvaranja bypass ventila i RPM.
        Model baziran na ORI 300hp karakteristikama.
        rpm_factor: SC efikasnost raste linearno do 6000rpm.
        """
        rpm_factor = min(max(rpm, 0.0) / 6000.0, 1.0)
        boost_avail = _SC_MAX_BOOST_GAUGE * rpm_factor
        boost_actual = boost_avail * (1.0 - bypass_pct / 100.0)
        return ATM_BAR + boost_actual

    @staticmethod
    def recommended_bypass(rpm: float, load_pct: float) -> dict:
        """
        Preporučena ORI bypass vrijednost za zadani RPM i load (0-100%).

        Interpolira iz ORI bypass mape.
        Vraća dict: raw, pct, boost_bar_abs, boost_bar_gauge, boost_psi
        """
        # load_pct 0-100% → row indeks (rows su 51-205 = 40-161% raw)
        load_raw = load_pct * 205.0 / 100.0
        load_raw = max(51.0, min(205.0, load_raw))

        # Bilinear interpolacija po RPM i load
        rpm_clamped = max(_ORI_BYPASS_RPM_COLS[0], min(_ORI_BYPASS_RPM_COLS[-1], rpm))
        load_clamped = max(_ORI_BYPASS_LOAD_ROWS[0], min(_ORI_BYPASS_LOAD_ROWS[-1], load_raw))

        # Pronađi okolne indekse
        ci = 0
        for i, r in enumerate(_ORI_BYPASS_RPM_COLS[:-1]):
            if rpm_clamped >= r: ci = i

        ri = 0
        for i, l in enumerate(_ORI_BYPASS_LOAD_ROWS[:-1]):
            if load_clamped >= l: ri = i

        # Interpolacija
        r0, r1 = _ORI_BYPASS_RPM_COLS[ci], _ORI_BYPASS_RPM_COLS[min(ci+1, len(_ORI_BYPASS_RPM_COLS)-1)]
        l0, l1 = _ORI_BYPASS_LOAD_ROWS[ri], _ORI_BYPASS_LOAD_ROWS[min(ri+1, len(_ORI_BYPASS_LOAD_ROWS)-1)]

        tr = (rpm_clamped - r0) / (r1 - r0) if r1 != r0 else 0.0
        tl = (load_clamped - l0) / (l1 - l0) if l1 != l0 else 0.0

        ci1 = min(ci+1, len(_ORI_BYPASS_RPM_COLS)-1)
        ri1 = min(ri+1, len(_ORI_BYPASS_LOAD_ROWS)-1)

        v00 = _ORI_BYPASS_MAP[ri][ci]
        v10 = _ORI_BYPASS_MAP[ri1][ci]
        v01 = _ORI_BYPASS_MAP[ri][ci1]
        v11 = _ORI_BYPASS_MAP[ri1][ci1]

        raw = v00 * (1-tr)*(1-tl) + v01 * tr*(1-tl) + v10 * (1-tr)*tl + v11 * tr*tl
        raw = int(round(raw))
        pct = MapCalculator.bypass_raw_to_pct(raw)
        bar_abs = MapCalculator.bypass_pct_to_bar_abs(pct, rpm)

        return {
            "bypass_raw":       raw,
            "bypass_pct":       round(pct, 1),
            "boost_bar_abs":    round(bar_abs, 3),
            "boost_bar_gauge":  round(bar_abs - ATM_BAR, 3),
            "boost_psi":        round(MapCalculator.bar_to_psi(bar_abs - ATM_BAR), 2),
            "boost_mmhg":       round(MapCalculator.bar_to_mmhg(bar_abs - ATM_BAR), 0),
        }

    # ── Timing ────────────────────────────────────────────────────────────────

    @staticmethod
    def base_timing_at_rpm(rpm: float) -> float:
        """ORI bazni timing (° BTDC) pri zadanom RPM, srednji load."""
        if rpm <= _ORI_TIMING_RPM[0]:
            return _ORI_TIMING_BASE[0]
        if rpm >= _ORI_TIMING_RPM[-1]:
            return _ORI_TIMING_BASE[-1]
        for i in range(len(_ORI_TIMING_RPM) - 1):
            r0, r1 = _ORI_TIMING_RPM[i], _ORI_TIMING_RPM[i+1]
            if r0 <= rpm <= r1:
                t = (rpm - r0) / (r1 - r0)
                return _ORI_TIMING_BASE[i] * (1-t) + _ORI_TIMING_BASE[i+1] * t
        return _ORI_TIMING_BASE[-1]

    @staticmethod
    def calc_timing_correction(rpm: float, load_pct: float, base_timing: float | None = None) -> dict:
        """
        Preporučena korekcija timinga za Rotax ACE 1630.

        Parametri:
          rpm        — vrtljaji motora (min 1000, max 7500)
          load_pct   — opterećenje 0-100%
          base_timing — bazni timing; None = koristi ORI vrijednost

        Vraća dict: base, correction_deg, recommended, risk_level, note
        """
        if base_timing is None:
            base_timing = MapCalculator.base_timing_at_rpm(rpm)

        # Korekcija bazirana na kombinaciji RPM + load
        # ORI knock zone: visok RPM + visok load = najveći rizik
        correction = 0.0
        risk = "OK"
        note = ""

        if rpm > 6000 and load_pct > 80:
            correction = -2.25   # jedan korak (0.75° × 3)
            risk = "WARN"
            note = "Visok RPM + visok load — reduciraj 2-3° od STG2 max"
        elif rpm > 6500 and load_pct > 70:
            correction = -3.0
            risk = "WARN"
            note = "Oprez: zona povećanog rizika knock-a pri SC boostu"
        elif rpm > 7000 and load_pct > 60:
            correction = -4.5
            risk = "ERROR"
            note = "KRITIČNA ZONA — redovni knock pri 7000rpm WOT bez intercoolera"
        elif load_pct > 90 and rpm > 5000:
            correction = -1.5
            risk = "WARN"
            note = "WOT zona — preporučena konzervativna kalibracija"
        else:
            note = "Sigurna zona — ORI timing prihvatljiv"

        recommended = base_timing + correction
        recommended = max(0.0, min(43.5, recommended))   # hard limit

        return {
            "base_timing":   round(base_timing, 2),
            "correction":    round(correction, 2),
            "recommended":   round(recommended, 2),
            "risk_level":    risk,
            "note":          note,
        }

    # ── Injection ─────────────────────────────────────────────────────────────

    @staticmethod
    def ms_to_duty_cycle(pulse_ms: float, rpm: float) -> float:
        """
        Trajanje impulsa injektora (ms) → duty cycle (%).
        cycle_time = 2 × (60/rpm) × 1000  [ms] — 4-taktni motor.
        """
        if rpm <= 0: return 0.0
        cycle_ms = 2.0 * 60000.0 / rpm
        return min(100.0, pulse_ms * 100.0 / cycle_ms)

    @staticmethod
    def injector_flow_cc_min(duty_pct: float, rated_cc_min: float = 330.0) -> float:
        """
        Procijenjeni protok injektora (cc/min) pri zadanom duty cycle-u.
        ACE 1630 OEM injektori: ~330 cc/min @ 300 kPa.
        """
        return rated_cc_min * duty_pct / 100.0
