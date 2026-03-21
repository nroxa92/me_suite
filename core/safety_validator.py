"""
ME17Suite — Safety Validator
Bosch ME17.8.5 / Rotax ACE 1630

Limiti kalibrirani na temelju stvarnih firmware vrijednosti:
  - ori_300 (ORI, 10SW066726)   — sigurna referentna baza
  - npro_stg2_300 (STG2)        — potvrđene gornje granice
  - sve poznate ORI varijante (300/230/170/130hp SC/NA, Spark 900, GTI 1503)

Tri razine:
  OK       — vrijednost unutar normalnog raspona
  WARNING  — vrijednost izvan tipičnog raspona, ali ne nužno opasna
  ERROR    — vrijednost koja može oštetiti motor ili uzrokovati kvar

Rev limiter — binarno izmjereni ECU limiti (≠ manual WOT RPM):
  300hp SC = 8158 RPM (5072t) | 230hp SC (1630) = 8158 RPM (5072t, =300hp!)
  130/170hp NA = 7892 RPM (5243t) — ISTI SW = ISTI ECU limit!
  Spark 900    = 8081 RPM (5120 ticks, soft-cut)
  GTI 1503     = 7699–8072 RPM (ovisno o SW)
  GTI90 ≈ 7043 RPM
  Manual WOT RPM (dijagnostički, u vodi) je VIŠI od ECU limita — bez opterećenja svi vrte više.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .map_finder import MapDef, FoundMap


class Level(Enum):
    OK      = "ok"
    WARNING = "warn"
    ERROR   = "error"


@dataclass
class ValidationResult:
    level:   Level
    message: str

    @property
    def ok(self) -> bool:
        """True ako edit smije proći (OK ili WARNING — samo ERROR blokira)."""
        return self.level != Level.ERROR


# ─── Limiti po kategoriji ─────────────────────────────────────────────────────
#
# Svi limiti su u DISPLAY vrijednostima (raw * scale + offset),
# tj. istim jedinicama koje korisnik vidi u tablici.
#
# Ignition (°BTDC, scale=0.75):
#   ORI: 24.0–33.75°  |  STG2: 25.5–36.75°  |  Knock map: 0–170° (trim, ne timing!)
#   WARN  > 38.25° (raw 51) — iznad STG2 max + mali buffer
#   ERROR > 43.50° (raw 58) — abs. max fizikalnog OEM raspona (raw u8 max=58 u ignition scanu)
#
# Lambda (bezdimenzione, scale=1/32768):
#   ORI:  0.965–1.073  |  STG2: 0.984–1.080
#   WARN_RICH  < 0.88  — bogato van normalnog, ali poznate stage tune idu do 0.85
#   WARN_LEAN  > 1.05  — siromasno; rizik od lean misfire pri punom gasu
#   ERROR_RICH < 0.75  — opasno bogato, neizgoreno gorivo, pregrijavanje katalizatora (N/A)
#   ERROR_LEAN > 1.15  — opasno siromasno, pistons/valves pri punom gasu
#
# Fuel 2D mapa (Q15, scale=1/32767, unit="Q15"):
#   Relativna masa goriva (0.0 = isključeno, 1.0 = puna doza)
#   ORI max: 300hp=0.944, 230hp=0.785, 170/130hp=0.524, GTI 1503=0.440
#   Q15 fizikalni max = 32767/32767 = 1.0 (ne može biti > 1.0)
#   WARN  > 1.0  — iznad Q15 max, neočekivano (može značiti overflow ili greška)
#   ERROR > 1.1  — sigurno pogrešan unos, nije fizikalno izvedivo
#
# Injection pulse (raw u16, scale=1.0):
#   Max hardware limit: 65535  |  ORI max: ~49151 (75%)  |  STG2: saturira na 65535
#   Bez fizičke A2L jedinice — ne možemo dati smisleni ERROR limit na raw vrijednosti.
#   WARN > 62000 — iznad 94.6% kapaciteta, rizik od kratkog zatvaranja injektora
#
# Torque factor (display = 100.0/32768.0, unit=%):
#   ORI: 92.97–119.53%  |  STG2: ~91–122%
#   WARN  > 125.0% — iznad STG2 max uz buffer
#   ERROR > 160.0% — fizikalno nemoguće za ACE 1630
#
# SC bypass (display = 100/255, unit="% bypass"):
#   0% = puni boost (bypass zatvoren)  |  100% = nema boosta (bypass otvoren)
#   Nema opasne vrijednosti per se — samo informativan prikaz
#
# SC correction (Q14 → %, scale=100/16384, offset=-100, unit="% korekcija"):
#   ORI 300hp: -67.5 do +119.09%  |  0% = neutralno (raw 16384)
#   WARN  > +150% — iznad ORI max uz 25% buffer (raw ~24576)
#   ERROR > +250% — prekomjerna korekcija, gotovo sigurno pogrešan unos
#
# Temp fuel / lambda bias (isti format kao SC correction, unit="%"):
#   WARN > +80%  — >80% obogaćivanja od nominalnog
#   ERROR > +150%
#
# Rev limiter (period-encoded ticks):
#   Binarno izmjereni ECU limiti (NE manual WOT RPM):
#     300/230hp SC=8158 RPM (5072t), 130/170hp NA=7892 RPM (5243t, ISTI SW = isti limit!)
#     Spark 900=8081 RPM (5120t), GTI 1503=7699–8072 RPM, GTI90=~7043 RPM
#   WARN  > 8700 rpm — iznad svih poznatih stock ECU limita (SC max = 8158 RPM)
#   ERROR > 9200 rpm — iznad fizikalnog max Rotax ACE 1630

_IGNITION_WARN_DEG  = 38.25
_IGNITION_ERROR_DEG = 43.50
_IGNITION_MIN_DEG   = 0.0    # 0° = retard (dozvoljeno u knock trim mapama)

_LAMBDA_WARN_RICH   = 0.88
_LAMBDA_WARN_LEAN   = 1.05
_LAMBDA_ERROR_RICH  = 0.75
_LAMBDA_ERROR_LEAN  = 1.15

_FUEL_Q15_WARN  = 1.0    # Q15 fizikalni max; >1.0 je neočekivano
_FUEL_Q15_ERROR = 1.1    # sigurno greška — nije fizikalno izvedivo

_INJECTION_WARN_RAW  = 62000
_INJECTION_ERROR_RAW = 65535   # fizički max — samo warn, ne error

_TORQUE_WARN_DISP  = 125.0   # > STG2 max ~122%
_TORQUE_ERROR_DISP = 160.0   # fizikalno nemoguće za ACE 1630

_SC_CORR_WARN   = 150.0   # +150% korekcija — iznad ORI max (+119%)
_SC_CORR_ERROR  = 250.0   # +250% — prekomjerno, gotovo sigurno greška

_REV_WARN_RPM  = 8700    # iznad svih poznatih stock varijanti (170hp NA=8440)
_REV_ERROR_RPM = 9200    # iznad fizikalnog max Rotax ACE 1630

_FACTOR_WARN  = 80.0    # +80% obogaćivanja
_FACTOR_ERROR = 150.0   # +150% — prekomjerno


# ─── SafetyValidator ──────────────────────────────────────────────────────────

class SafetyValidator:
    """
    Validira unos korisnika pri editiranju mapa ME17.8.5.

    Metode:
      validate_edit(defn, row, col, display_val) → ValidationResult
      batch_validate(fm)                         → list[ValidationResult]
    """

    def validate_edit(self, defn: "MapDef", row: int, col: int,
                      display_val: float) -> ValidationResult:
        """
        Validira jednu promjenu ćelije.
        Vraća ValidationResult s razinom OK/WARNING/ERROR i porukom.
        """
        cat = defn.category

        if cat == "ignition":
            return self._check_ignition(defn, display_val)

        if cat == "lambda":
            return self._check_lambda(defn, display_val)

        if cat == "injection":
            return self._check_injection(defn, display_val)

        if cat == "fuel":
            return self._check_fuel(defn, display_val)

        if cat == "torque":
            return self._check_torque(display_val)

        if cat == "rpm_limiter":
            return self._check_rev_limiter(display_val)

        # Sve ostalo — osnovni range check iz MapDef
        return self._check_generic(defn, display_val)

    def batch_validate(self, fm: "FoundMap") -> list[ValidationResult]:
        """
        Validira sve ćelije mape.
        Vraća samo one s razinom WARNING ili ERROR (OK se preskače).
        """
        defn   = fm.defn
        issues = []
        disp   = fm.display_values

        for idx, val in enumerate(disp):
            row = idx // defn.cols
            col = idx %  defn.cols
            res = self.validate_edit(defn, row, col, val)
            if res.level != Level.OK:
                issues.append(ValidationResult(
                    level   = res.level,
                    message = f"[{row},{col}] {res.message}",
                ))

        return issues

    # ── Per-category checks ───────────────────────────────────────────────────

    def _check_ignition(self, defn: "MapDef", deg: float) -> ValidationResult:
        # Knock trim mape (idx 8-9) imaju drugačiji raspon — large values su OK
        is_knock = "Knock" in defn.name or "knock" in defn.name
        if is_knock:
            # Knock trim: 0-170° su viđene u ORI, ne validiramo isto kao timing mape
            if deg < 0:
                return ValidationResult(Level.ERROR,
                    f"Knock trim negativan ({deg:.2f}°) — raw vrijednost ispod nule.")
            return ValidationResult(Level.OK, "")

        if deg > _IGNITION_ERROR_DEG:
            return ValidationResult(Level.ERROR,
                f"Paljenje {deg:.2f}° BTDC prelazi max ({_IGNITION_ERROR_DEG}°). "
                f"Rizik od detonacije i oštećenja motora.")
        if deg > _IGNITION_WARN_DEG:
            return ValidationResult(Level.WARNING,
                f"Paljenje {deg:.2f}° BTDC iznad preporučenog ({_IGNITION_WARN_DEG}°). "
                f"STG2 max je 36.75°. Provjerite knock senzor pri testiranju.")
        if deg < _IGNITION_MIN_DEG:
            return ValidationResult(Level.WARNING,
                f"Paljenje {deg:.2f}° — negativna vrijednost (retard). Normalno samo u uvjetnoj mapi.")
        return ValidationResult(Level.OK, "")

    def _check_lambda(self, defn: "MapDef", lam: float) -> ValidationResult:
        # Lambda bias tablica: malo širi raspon je prihvatljiv
        is_bias = "bias" in defn.name.lower() or "trim" in defn.name.lower()
        err_rich  = _LAMBDA_ERROR_RICH  if not is_bias else 0.70
        err_lean  = _LAMBDA_ERROR_LEAN  if not is_bias else 1.20
        warn_rich = _LAMBDA_WARN_RICH   if not is_bias else 0.85
        warn_lean = _LAMBDA_WARN_LEAN   if not is_bias else 1.08

        if lam < err_rich:
            return ValidationResult(Level.ERROR,
                f"Lambda {lam:.4f} kritično bogato (min {err_rich}). "
                f"Rizik od zalijevanja injektora i pregrijavanja.")
        if lam > err_lean:
            return ValidationResult(Level.ERROR,
                f"Lambda {lam:.4f} kritično siromasno (max {err_lean}). "
                f"Rizik od lean misfire i ostecenja klipova pri punom gasu.")
        if lam < warn_rich:
            return ValidationResult(Level.WARNING,
                f"Lambda {lam:.4f} bogato — izvan ORI raspona. "
                f"Stage tune dopušta do ~0.85 pri WOT.")
        if lam > warn_lean:
            return ValidationResult(Level.WARNING,
                f"Lambda {lam:.4f} siromasno — iznad ORI max 1.073. "
                f"Pratite EGT pri testiranju.")
        return ValidationResult(Level.OK, "")

    def _check_injection(self, defn: "MapDef", val: float) -> ValidationResult:
        # Q15 fuel mape (unit="Q15", scale≈1/32767) — relativna masa goriva 0.0–1.0
        if getattr(defn, "unit", "") == "Q15":
            return self._check_fuel_q15(val)

        # SC correction, temp fuel, lambda bias — prikazani kao % (offset=-100)
        # scale ~ 100/16384 ili 100/32768 → uvijek < 0.01
        is_factor = defn.scale < 0.01   # Q14/Q15 → % format
        if is_factor:
            if val > _SC_CORR_ERROR:
                return ValidationResult(Level.ERROR,
                    f"Korekcija +{val:.1f}% prelazi max (+{_SC_CORR_ERROR}%). "
                    f"Gotovo sigurno pogresan unos.")
            if val > _SC_CORR_WARN:
                return ValidationResult(Level.WARNING,
                    f"Korekcija +{val:.1f}% iznad ORI max (+119%). "
                    f"Provjeri pri testiranju.")
            if val < -90.0:
                return ValidationResult(Level.ERROR,
                    f"Korekcija {val:.1f}% — gotovo iskljucen injektor.")
            return ValidationResult(Level.OK, "")

        # Injection pulse width (ms, scale=0.0001)
        # ORI max ~4.9ms, warn pri >6.0ms (zauzece >90% ciklusa pri WOT)
        if val > 6.0:
            return ValidationResult(Level.WARNING,
                f"Injection {val:.4f} ms — visoko ubrizgavanje (>6ms). "
                f"ORI WOT max ~4.9ms. Provjeri tlak goriva (386-414 kPa).")
        if val < 0:
            return ValidationResult(Level.ERROR, f"Injection pulse negativan ({val:.4f} ms).")
        return ValidationResult(Level.OK, "")

    def _check_torque(self, val: float) -> ValidationResult:
        if val > _TORQUE_ERROR_DISP:
            return ValidationResult(Level.ERROR,
                f"Torque {val:.1f}% — prekomjerno, vjerojatno pogresan unos. "
                f"ORI raspon: 92.97–119.53%, STG2 max ~122%.")
        if val > _TORQUE_WARN_DISP:
            return ValidationResult(Level.WARNING,
                f"Torque {val:.1f}% iznad STG2 max (~122%). "
                f"Pazi na TOPS zastitu motora.")
        if val < 50.0:
            return ValidationResult(Level.WARNING,
                f"Torque {val:.1f}% — prekomjerno smanjen, motor nece razviti snagu.")
        return ValidationResult(Level.OK, "")

    def _check_fuel_q15(self, val: float) -> ValidationResult:
        """Q15 relativna masa goriva (0.0 = isključeno, 1.0 = max duty)."""
        if val > _FUEL_Q15_ERROR:
            return ValidationResult(Level.ERROR,
                f"Gorivo Q15 {val:.4f} — iznad fizikalnog max ({_FUEL_Q15_ERROR}). "
                f"Sigurno pogresan unos (raw overflow ili tipfehler).")
        if val > _FUEL_Q15_WARN:
            return ValidationResult(Level.WARNING,
                f"Gorivo Q15 {val:.4f} > 1.0 — iznad normalnog Q15 raspona. "
                f"ORI max: 300hp=0.944, 230hp=0.785, 130/170hp=0.524.")
        if val < 0.0:
            return ValidationResult(Level.ERROR,
                f"Gorivo Q15 {val:.4f} negativno — nije moguće.")
        return ValidationResult(Level.OK, "")

    def _check_fuel(self, defn: "MapDef", val: float) -> ValidationResult:
        """Category 'fuel' — cold start enrichment, deadtime, ostale fuel tablice."""
        # Deadtime mape su read-only (unit="µs") — ne validiramo granično
        unit = getattr(defn, "unit", "")
        if unit in ("µs", "raw"):
            return self._check_generic(defn, val)
        # Q15 format
        if unit == "Q15":
            return self._check_fuel_q15(val)
        return self._check_generic(defn, val)

    def _check_rev_limiter(self, rpm: float) -> ValidationResult:
        if rpm > _REV_ERROR_RPM:
            return ValidationResult(Level.ERROR,
                f"Rev limiter {rpm:.0f} rpm iznad max ({_REV_ERROR_RPM} rpm). "
                f"Rizik od mehanickog kvara motora (klipovi/ventili).")
        if rpm > _REV_WARN_RPM:
            return ValidationResult(Level.WARNING,
                f"Rev limiter {rpm:.0f} rpm iznad svih poznatih stock vrijednosti "
                f"(170hp NA max=8440 rpm). Provjeri ventile i ulje pod opterecenjem.")
        if rpm < 3000:
            return ValidationResult(Level.WARNING,
                f"Rev limiter {rpm:.0f} rpm prenizak — motor nece razviti punu snagu.")
        return ValidationResult(Level.OK, "")

    def _check_generic(self, defn: "MapDef", val: float) -> ValidationResult:
        """Generički provjera: raw_min/raw_max iz MapDef konvertiran u display."""
        if defn.scale and defn.scale != 0:
            disp_min = defn.raw_min * defn.scale + defn.offset_val
            disp_max = defn.raw_max * defn.scale + defn.offset_val
            if val < disp_min:
                return ValidationResult(Level.WARNING,
                    f"Vrijednost {val:.3f} ispod min {disp_min:.3f} {defn.unit}.")
            if val > disp_max:
                return ValidationResult(Level.WARNING,
                    f"Vrijednost {val:.3f} iznad max {disp_max:.3f} {defn.unit}.")
        return ValidationResult(Level.OK, "")
