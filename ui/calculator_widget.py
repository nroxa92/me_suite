"""
ME17Suite — Calculator Widget
AFR/Lambda, Boost, Timing, Injection helper za Rotax ACE 1630.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox,
    QSlider, QTabWidget, QFrame, QComboBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from core.calculators import MapCalculator


# ─── Helper: sekcijski label ──────────────────────────────────────────────────

def _sec(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("lbl_section")
    return lbl


def _val_lbl(text: str = "—") -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Consolas", 13))
    lbl.setStyleSheet("color:#9cdcfe; padding:4px 0;")
    return lbl


def _sep() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("background:#333333; max-height:1px; margin:4px 0;")
    return f


def _styled_box(color: str = "#252526") -> QGroupBox:
    box = QGroupBox()
    box.setStyleSheet(f"QGroupBox {{ background:{color}; border:1px solid #333333; border-radius:5px; padding:10px; margin-top:0; }}")
    return box


# ─── Tab 1: AFR / Lambda ──────────────────────────────────────────────────────

class AfrTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(16, 16, 16, 16); lo.setSpacing(12)

        lo.addWidget(_sec("AFR / LAMBDA KONVERTER"))

        # Input row
        inp_lo = QHBoxLayout(); inp_lo.setSpacing(8)
        self._afr_in = QLineEdit()
        self._afr_in.setPlaceholderText("AFR (npr. 13.2)")
        self._afr_in.setMaximumWidth(150)
        self._afr_in.textChanged.connect(self._from_afr)
        inp_lo.addWidget(QLabel("AFR →"))
        inp_lo.addWidget(self._afr_in)
        inp_lo.addStretch()
        lo.addLayout(inp_lo)

        inp2_lo = QHBoxLayout(); inp2_lo.setSpacing(8)
        self._lam_in = QLineEdit()
        self._lam_in.setPlaceholderText("Lambda (npr. 0.898)")
        self._lam_in.setMaximumWidth(150)
        self._lam_in.textChanged.connect(self._from_lambda)
        inp2_lo.addWidget(QLabel("Lambda →"))
        inp2_lo.addWidget(self._lam_in)
        inp2_lo.addStretch()
        lo.addLayout(inp2_lo)

        # Vrsta goriva
        fuel_lo = QHBoxLayout(); fuel_lo.setSpacing(8)
        fuel_lo.addWidget(QLabel("Gorivo:"))
        self._fuel_combo = QComboBox()
        self._fuel_combo.addItems(["Benzin (14.7)", "E10 (14.08)", "E85 (9.76)"])
        self._fuel_combo.setMaximumWidth(160)
        self._fuel_combo.currentIndexChanged.connect(lambda: self._from_afr())
        fuel_lo.addWidget(self._fuel_combo)
        fuel_lo.addStretch()
        lo.addLayout(fuel_lo)

        lo.addWidget(_sep())

        # Rezultati
        grid = QGridLayout(); grid.setSpacing(8); grid.setColumnStretch(1, 1)
        self._r_afr   = _val_lbl()
        self._r_lam   = _val_lbl()
        self._r_desc  = _val_lbl()
        self._r_e10   = _val_lbl()
        self._r_e85   = _val_lbl()

        grid.addWidget(QLabel("AFR:"),    0, 0); grid.addWidget(self._r_afr,  0, 1)
        grid.addWidget(QLabel("Lambda:"), 1, 0); grid.addWidget(self._r_lam,  1, 1)
        grid.addWidget(QLabel("Status:"), 2, 0); grid.addWidget(self._r_desc, 2, 1)
        grid.addWidget(_sep(),            3, 0, 1, 2)
        grid.addWidget(QLabel("Ekv. E10 AFR:"), 4, 0); grid.addWidget(self._r_e10, 4, 1)
        grid.addWidget(QLabel("Ekv. E85 AFR:"), 5, 0); grid.addWidget(self._r_e85, 5, 1)
        lo.addLayout(grid)

        lo.addWidget(_sep())
        lo.addWidget(_sec("REFERENTNE VRIJEDNOSTI"))
        ref = QLabel(
            "Stoich benzin: λ=1.000  |  AFR=14.70\n"
            "WOT target:    λ=0.85–0.90  |  AFR=12.5–13.2\n"
            "Cruise:        λ=0.97–1.03  |  AFR=14.3–15.1\n"
            "Decel cutoff:  λ→∞ (bez ubrizgavanja)\n\n"
            "ORI 300hp lambda mapa: 0.965–1.073\n"
            "STG2 300hp lambda mapa: 0.984–1.080"
        )
        ref.setFont(QFont("Consolas", 11))
        ref.setStyleSheet("color:#666666; padding:8px; background:#252526; border:1px solid #333333; border-radius:4px;")
        lo.addWidget(ref)

        lo.addStretch()
        self._updating = False

    def _fuel_key(self) -> str:
        return ["petrol", "e10", "e85"][self._fuel_combo.currentIndex()]

    def _from_afr(self):
        if self._updating: return
        self._updating = True
        try:
            afr = float(self._afr_in.text().replace(",", "."))
            fuel = self._fuel_key()
            lam = MapCalculator.afr_to_lambda(afr, fuel)
            self._lam_in.setText(f"{lam:.5f}")
            self._update_results(afr, lam)
        except (ValueError, ZeroDivisionError):
            self._clear_results()
        finally:
            self._updating = False

    def _from_lambda(self):
        if self._updating: return
        self._updating = True
        try:
            lam = float(self._lam_in.text().replace(",", "."))
            fuel = self._fuel_key()
            afr = MapCalculator.lambda_to_afr(lam, fuel)
            self._afr_in.setText(f"{afr:.4f}")
            self._update_results(afr, lam)
        except (ValueError, ZeroDivisionError):
            self._clear_results()
        finally:
            self._updating = False

    def _update_results(self, afr: float, lam: float):
        self._r_afr.setText(f"{afr:.4f}")
        self._r_lam.setText(f"{lam:.5f}")
        desc = MapCalculator.afr_description(afr)
        color = "#f48771" if "OPASNO" in desc or "KRITIČNO" in desc else \
                "#e5c07b" if ("Bogato" in desc or "sirovo" in desc) else "#4ec9b0"
        self._r_desc.setText(desc)
        self._r_desc.setStyleSheet(f"color:{color}; padding:4px 0; font-family:Consolas; font-size:13px;")
        self._r_e10.setText(f"{MapCalculator.lambda_to_afr(lam, 'e10'):.4f}")
        self._r_e85.setText(f"{MapCalculator.lambda_to_afr(lam, 'e85'):.4f}")

    def _clear_results(self):
        for w in (self._r_afr, self._r_lam, self._r_desc, self._r_e10, self._r_e85):
            w.setText("—")


# ─── Tab 2: Boost kalkulator ──────────────────────────────────────────────────

class BoostTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(16, 16, 16, 16); lo.setSpacing(12)

        lo.addWidget(_sec("SC BOOST KALKULATOR  —  ORI 300hp reference"))

        # RPM slider
        rpm_lo = QVBoxLayout(); rpm_lo.setSpacing(4)
        rpm_hdr = QHBoxLayout()
        rpm_hdr.addWidget(QLabel("RPM:"))
        self._rpm_lbl = QLabel("4000")
        self._rpm_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._rpm_lbl.setStyleSheet("color:#9cdcfe;")
        rpm_hdr.addWidget(self._rpm_lbl); rpm_hdr.addStretch()
        rpm_lo.addLayout(rpm_hdr)
        self._rpm_sl = QSlider(Qt.Orientation.Horizontal)
        self._rpm_sl.setRange(1000, 7500); self._rpm_sl.setValue(4000); self._rpm_sl.setTickInterval(500)
        self._rpm_sl.valueChanged.connect(self._update)
        rpm_lo.addWidget(self._rpm_sl)
        lo.addLayout(rpm_lo)

        # Load slider
        load_lo = QVBoxLayout(); load_lo.setSpacing(4)
        load_hdr = QHBoxLayout()
        load_hdr.addWidget(QLabel("Gas (load %):"))
        self._load_lbl = QLabel("80%")
        self._load_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._load_lbl.setStyleSheet("color:#9cdcfe;")
        load_hdr.addWidget(self._load_lbl); load_hdr.addStretch()
        load_lo.addLayout(load_hdr)
        self._load_sl = QSlider(Qt.Orientation.Horizontal)
        self._load_sl.setRange(0, 100); self._load_sl.setValue(80)
        self._load_sl.valueChanged.connect(self._update)
        load_lo.addWidget(self._load_sl)
        lo.addLayout(load_lo)

        lo.addWidget(_sep())

        # Rezultati grid
        grid = QGridLayout(); grid.setSpacing(10); grid.setColumnStretch(1, 1)

        self._r_bypass_raw = _val_lbl()
        self._r_bypass_pct = _val_lbl()
        self._r_bar_abs    = _val_lbl()
        self._r_bar_gauge  = _val_lbl()
        self._r_psi        = _val_lbl()
        self._r_mmhg       = _val_lbl()

        rows = [
            ("ORI bypass (raw 0-255):", self._r_bypass_raw),
            ("ORI bypass (% otvoren):", self._r_bypass_pct),
            ("Boost (bar abs):",        self._r_bar_abs),
            ("Boost (bar gauge):",      self._r_bar_gauge),
            ("Boost (PSI gauge):",      self._r_psi),
            ("Boost (mmHg gauge):",     self._r_mmhg),
        ]
        for i, (lbl, widget) in enumerate(rows):
            grid.addWidget(QLabel(lbl), i, 0)
            grid.addWidget(widget,      i, 1)
        lo.addLayout(grid)

        lo.addWidget(_sep())

        # Napomena
        note = QLabel(
            "NAPOMENA: Procjena bazirana na ORI 300hp bypass mapi.\n"
            "Bypass 0% = puni boost (bypass zatvoren).\n"
            "Bypass 100% = nema boosta (SC bypass potpuno otvoren).\n"
            "Stvarni boost ovisi o stanju SC-a, filtera zraka i temp."
        )
        note.setFont(QFont("Consolas", 11))
        note.setStyleSheet("color:#666666; padding:8px; background:#252526; border:1px solid #333333; border-radius:4px;")
        lo.addWidget(note)

        lo.addStretch()
        self._update()

    def _update(self):
        rpm  = self._rpm_sl.value()
        load = self._load_sl.value()
        self._rpm_lbl.setText(str(rpm))
        self._load_lbl.setText(f"{load}%")

        res = MapCalculator.recommended_bypass(rpm, load)
        self._r_bypass_raw.setText(str(res["bypass_raw"]))
        self._r_bypass_pct.setText(f"{res['bypass_pct']:.1f}%")
        self._r_bar_abs.setText(f"{res['boost_bar_abs']:.3f} bar")
        self._r_bar_gauge.setText(f"{res['boost_bar_gauge']:+.3f} bar")
        self._r_psi.setText(f"{res['boost_psi']:+.2f} PSI")
        self._r_mmhg.setText(f"{res['boost_mmhg']:+.0f} mmHg")


# ─── Tab 3: Timing kalkulator ─────────────────────────────────────────────────

class TimingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(16, 16, 16, 16); lo.setSpacing(12)

        lo.addWidget(_sec("TIMING KALKULATOR  —  Rotax ACE 1630"))

        # RPM slider
        rpm_lo = QVBoxLayout(); rpm_lo.setSpacing(4)
        rpm_hdr = QHBoxLayout()
        rpm_hdr.addWidget(QLabel("RPM:"))
        self._rpm_lbl = QLabel("4000")
        self._rpm_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._rpm_lbl.setStyleSheet("color:#9cdcfe;")
        rpm_hdr.addWidget(self._rpm_lbl); rpm_hdr.addStretch()
        rpm_lo.addLayout(rpm_hdr)
        self._rpm_sl = QSlider(Qt.Orientation.Horizontal)
        self._rpm_sl.setRange(1000, 7500); self._rpm_sl.setValue(4000)
        self._rpm_sl.valueChanged.connect(self._update)
        rpm_lo.addWidget(self._rpm_sl)
        lo.addLayout(rpm_lo)

        # Load slider
        load_lo = QVBoxLayout(); load_lo.setSpacing(4)
        load_hdr = QHBoxLayout()
        load_hdr.addWidget(QLabel("Load %:"))
        self._load_lbl = QLabel("80%")
        self._load_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._load_lbl.setStyleSheet("color:#9cdcfe;")
        load_hdr.addWidget(self._load_lbl); load_hdr.addStretch()
        load_lo.addLayout(load_hdr)
        self._load_sl = QSlider(Qt.Orientation.Horizontal)
        self._load_sl.setRange(0, 100); self._load_sl.setValue(80)
        self._load_sl.valueChanged.connect(self._update)
        load_lo.addWidget(self._load_sl)
        lo.addLayout(load_lo)

        # Base timing override
        base_lo = QHBoxLayout(); base_lo.setSpacing(8)
        base_lo.addWidget(QLabel("Baza (°BTDC, prazno=ORI):"))
        self._base_in = QLineEdit()
        self._base_in.setPlaceholderText("ORI automatski")
        self._base_in.setMaximumWidth(130)
        self._base_in.textChanged.connect(self._update)
        base_lo.addWidget(self._base_in); base_lo.addStretch()
        lo.addLayout(base_lo)

        lo.addWidget(_sep())

        # Rezultati
        grid = QGridLayout(); grid.setSpacing(10); grid.setColumnStretch(1, 1)
        self._r_base    = _val_lbl()
        self._r_corr    = _val_lbl()
        self._r_recomm  = _val_lbl()
        self._r_risk    = _val_lbl()
        self._r_note    = _val_lbl()
        self._r_note.setWordWrap(True)

        rows = [
            ("ORI bazni timing:",     self._r_base),
            ("Preporučena korekcija:", self._r_corr),
            ("Preporučeno:",          self._r_recomm),
            ("Razina rizika:",        self._r_risk),
            ("Napomena:",             self._r_note),
        ]
        for i, (lbl, widget) in enumerate(rows):
            grid.addWidget(QLabel(lbl), i, 0)
            grid.addWidget(widget,      i, 1)
        lo.addLayout(grid)

        lo.addWidget(_sep())

        note = QLabel(
            "NAPOMENA: ORI raspon 24.0–33.75° BTDC  |  STG2 max 36.75°\n"
            "Safety limit: WARN >38.25° · ERROR >43.5°\n"
            "Knock trim mape (IGN #08 #09): imaju drugačiji format — ne miješati."
        )
        note.setFont(QFont("Consolas", 11))
        note.setStyleSheet("color:#666666; padding:8px; background:#252526; border:1px solid #333333; border-radius:4px;")
        lo.addWidget(note)

        lo.addStretch()
        self._update()

    def _update(self):
        rpm  = self._rpm_sl.value()
        load = self._load_sl.value()
        self._rpm_lbl.setText(str(rpm))
        self._load_lbl.setText(f"{load}%")

        base = None
        raw_base = self._base_in.text().strip().replace(",", ".")
        if raw_base:
            try:
                base = float(raw_base)
            except ValueError:
                pass

        res = MapCalculator.calc_timing_correction(rpm, load, base)
        self._r_base.setText(f"{res['base_timing']:.2f}° BTDC")
        corr = res["correction"]
        self._r_corr.setText(f"{corr:+.2f}°")
        self._r_corr.setStyleSheet(
            f"color:{'#f48771' if corr < -3 else '#e5c07b' if corr < 0 else '#4ec9b0'}; "
            "padding:4px 0; font-family:Consolas; font-size:13px;"
        )
        self._r_recomm.setText(f"{res['recommended']:.2f}° BTDC")
        risk = res["risk_level"]
        self._r_risk.setText(risk)
        color = {"OK": "#4ec9b0", "WARN": "#e5c07b", "ERROR": "#f48771"}.get(risk, "#cccccc")
        self._r_risk.setStyleSheet(f"color:{color}; padding:4px 0; font-family:Consolas; font-size:13px; font-weight:bold;")
        self._r_note.setText(res["note"])


# ─── Tab 4: Injection kalkulator ──────────────────────────────────────────────

class InjectionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(16, 16, 16, 16); lo.setSpacing(12)

        lo.addWidget(_sec("INJECTION KALKULATOR  —  ACE 1630 injektori"))

        # Pulse width input
        pulse_lo = QHBoxLayout(); pulse_lo.setSpacing(8)
        pulse_lo.addWidget(QLabel("Trajanje impulsa (ms):"))
        self._pulse_in = QLineEdit()
        self._pulse_in.setPlaceholderText("npr. 4.9")
        self._pulse_in.setMaximumWidth(120)
        self._pulse_in.textChanged.connect(self._update)
        pulse_lo.addWidget(self._pulse_in); pulse_lo.addStretch()
        lo.addLayout(pulse_lo)

        # RPM slider
        rpm_lo = QVBoxLayout(); rpm_lo.setSpacing(4)
        rpm_hdr = QHBoxLayout()
        rpm_hdr.addWidget(QLabel("RPM:"))
        self._rpm_lbl = QLabel("6000")
        self._rpm_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self._rpm_lbl.setStyleSheet("color:#9cdcfe;")
        rpm_hdr.addWidget(self._rpm_lbl); rpm_hdr.addStretch()
        rpm_lo.addLayout(rpm_hdr)
        self._rpm_sl = QSlider(Qt.Orientation.Horizontal)
        self._rpm_sl.setRange(1000, 7500); self._rpm_sl.setValue(6000)
        self._rpm_sl.valueChanged.connect(self._update)
        rpm_lo.addWidget(self._rpm_sl)
        lo.addLayout(rpm_lo)

        lo.addWidget(_sep())

        grid = QGridLayout(); grid.setSpacing(10); grid.setColumnStretch(1, 1)
        self._r_duty   = _val_lbl()
        self._r_flow   = _val_lbl()
        self._r_status = _val_lbl()
        grid.addWidget(QLabel("Duty cycle:"),      0, 0); grid.addWidget(self._r_duty,   0, 1)
        grid.addWidget(QLabel("Protok inj.:"),     1, 0); grid.addWidget(self._r_flow,   1, 1)
        grid.addWidget(QLabel("Status:"),          2, 0); grid.addWidget(self._r_status, 2, 1)
        lo.addLayout(grid)

        lo.addWidget(_sep())
        note = QLabel(
            "OEM injektori ACE 1630: ~330 cc/min @ 300 kPa (56 PSI)\n"
            "Sekvencijalni, 3 komada (1 po cilindru)\n"
            "DC formula: pulse / (2x60000/RPM) x100  (4-taktni ciklus)\n"
            "ORI WOT procjena: ~4.9ms @ 6000rpm = ~24.5% DC\n\n"
            "NAPOMENA: Jedinica 'ms' je procjena. Stvarna jedinica\n"
            "iz A2L fajla nije potvrdjena — moguca je mg/takt."
        )
        note.setFont(QFont("Consolas", 11))
        note.setStyleSheet("color:#666666; padding:8px; background:#252526; border:1px solid #333333; border-radius:4px;")
        lo.addWidget(note)
        lo.addStretch()

    def _update(self):
        rpm = self._rpm_sl.value()
        self._rpm_lbl.setText(str(rpm))
        try:
            pulse = float(self._pulse_in.text().replace(",", "."))
            duty  = MapCalculator.ms_to_duty_cycle(pulse, rpm)
            flow  = MapCalculator.injector_flow_cc_min(duty)
            self._r_duty.setText(f"{duty:.1f}%")
            self._r_flow.setText(f"{flow:.1f} cc/min")
            color = "#f48771" if duty > 95 else "#e5c07b" if duty > 85 else "#4ec9b0"
            status = "PREVISOKO — rizik od kratkog zatvaranja" if duty > 95 else \
                     "Visoko — blizu max kapaciteta" if duty > 85 else "OK"
            self._r_status.setText(status)
            self._r_status.setStyleSheet(f"color:{color}; padding:4px 0; font-family:Consolas; font-size:13px;")
        except ValueError:
            self._r_duty.setText("—")
            self._r_flow.setText("—")
            self._r_status.setText("—")


# ─── CalculatorWidget (glavni widget) ────────────────────────────────────────

class CalculatorWidget(QWidget):
    """
    Kalkulator tab u ME17Suite.
    Sadrži 4 sub-taba: AFR/Lambda, Boost, Timing, Injection.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)

        hdr = QLabel("  KALKULATOR  —  Rotax ACE 1630")
        hdr.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px; "
            "background:#252526; padding:6px 10px; border-bottom:1px solid #333333;"
        )
        lo.addWidget(hdr)

        tabs = QTabWidget(); tabs.setDocumentMode(True)
        tabs.addTab(AfrTab(),       "AFR / Lambda")
        tabs.addTab(BoostTab(),     "Boost")
        tabs.addTab(TimingTab(),    "Timing")
        tabs.addTab(InjectionTab(), "Injection")
        lo.addWidget(tabs, 1)
