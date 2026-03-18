"""
ME17Suite — EEPROM Viewer widget
Prikazuje parsirane EEPROM podatke: identifikacija, datumi, odometar, dealer.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QLineEdit,
    QTextEdit, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.eeprom import EepromParser, EepromInfo


class _FieldRow(QWidget):
    """Label + vrijednost red u gridu."""
    def __init__(self, label: str, value: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(label + ":")
        lbl.setFixedWidth(170)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("color: #8899AA; font-size: 12px;")

        self._val = QLabel(value)
        self._val.setStyleSheet("color: #E0E8F0; font-size: 12px; font-weight: bold;")
        self._val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(lbl)
        layout.addSpacing(8)
        layout.addWidget(self._val)
        layout.addStretch()

    def set_value(self, v: str):
        self._val.setText(v)

    def set_color(self, color: str):
        self._val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")


class EepromWidget(QWidget):
    """Tab za pregled EEPROM sadržaja."""

    eeprom_loaded = pyqtSignal(object)   # EepromInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info: EepromInfo | None = None
        self._parser = EepromParser()
        self._build_ui()

    # ── gradnja UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 10, 12, 10)

        # ── toolbar ──────────────────────────────────────────────────────────
        bar = QHBoxLayout()
        self._btn_open = QPushButton("Otvori EEPROM (.bin)")
        self._btn_open.setFixedHeight(32)
        self._btn_open.setStyleSheet("""
            QPushButton { background: #2A6EBB; color: white; border-radius: 4px;
                          font-size: 12px; padding: 0 14px; }
            QPushButton:hover { background: #3A7ECC; }
        """)
        self._btn_open.clicked.connect(self._open_file)

        self._lbl_file = QLabel("Nije učitan fajl")
        self._lbl_file.setStyleSheet("color: #667788; font-size: 11px;")

        bar.addWidget(self._btn_open)
        bar.addSpacing(10)
        bar.addWidget(self._lbl_file)
        bar.addStretch()
        root.addLayout(bar)

        # ── separator ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #334455;")
        root.addWidget(sep)

        # ── scroll area s podacima ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        # ── grupe polja ──────────────────────────────────────────────────────
        self._grp_id    = self._make_group("Identifikacija vozila")
        self._grp_sw    = self._make_group("Software verzije")
        self._grp_dates = self._make_group("Datumi programiranja")
        self._grp_odo   = self._make_group("Radni sati / Odometar")
        self._grp_dealer = self._make_group("Dealer / servis")
        self._grp_errors = self._make_group("Dijagnostika / upozorenja")

        # ID polja
        self._f_hull    = self._add_field(self._grp_id, "Hull ID / VIN")
        self._f_serial  = self._add_field(self._grp_id, "ECU serijski broj")
        self._f_model   = self._add_field(self._grp_id, "Procijenjeni model")
        self._f_my      = self._add_field(self._grp_id, "Model godina (kod)")

        # SW polja
        self._f_mpem    = self._add_field(self._grp_sw, "MPEM SW ID")
        self._f_svc     = self._add_field(self._grp_sw, "Servisni SW ID")
        self._f_hw_type = self._add_field(self._grp_sw, "HW tip ECU-a")

        # Datumi
        self._f_date1   = self._add_field(self._grp_dates, "Prvo programiranje")
        self._f_date2   = self._add_field(self._grp_dates, "Zadnje ažuriranje")
        self._f_pcount  = self._add_field(self._grp_dates, "Broj programiranja")

        # Radni sati / odometar
        self._f_odo_raw = self._add_field(self._grp_odo, "Radni sati (odo)")
        self._f_odo_note = self._add_field(self._grp_odo, "Sirova vrijednost (min)")
        self._f_odo_note.set_value("—")
        self._f_odo_note.set_color("#AAAAAA")

        # Dealer
        self._f_dealer  = self._add_field(self._grp_dealer, "Naziv dealera")

        # Errors
        self._errors_text = QTextEdit()
        self._errors_text.setReadOnly(True)
        self._errors_text.setMaximumHeight(80)
        self._errors_text.setStyleSheet(
            "background: #1A2530; color: #FF9944; font-size: 11px; border: 1px solid #334455;"
        )
        self._errors_text.setPlaceholderText("Nema upozorenja.")
        self._grp_errors.layout().addWidget(self._errors_text)

        for grp in [self._grp_id, self._grp_sw, self._grp_dates, self._grp_odo,
                    self._grp_dealer, self._grp_errors]:
            content_layout.addWidget(grp)

        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _make_group(self, title: str) -> QGroupBox:
        grp = QGroupBox(title)
        grp.setStyleSheet("""
            QGroupBox {
                color: #99BBCC; font-size: 12px; font-weight: bold;
                border: 1px solid #334455; border-radius: 5px; margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        grp.setLayout(QVBoxLayout())
        grp.layout().setSpacing(0)
        grp.layout().setContentsMargins(10, 8, 10, 8)
        return grp

    def _add_field(self, grp: QGroupBox, label: str) -> _FieldRow:
        row = _FieldRow(label)
        grp.layout().addWidget(row)
        return row

    # ── učitavanje fajla ─────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori EEPROM dump", "",
            "Binary fajlovi (*.bin);;Svi fajlovi (*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        info = self._parser.parse(path)
        self._info = info
        import os
        self._lbl_file.setText(os.path.basename(path))
        self._populate(info)
        self.eeprom_loaded.emit(info)

    def load_bytes(self, data: bytes, label: str = "<buffer>"):
        info = self._parser.parse_bytes(data, label)
        self._info = info
        self._lbl_file.setText(label)
        self._populate(info)
        self.eeprom_loaded.emit(info)

    def _populate(self, info: EepromInfo):
        ok_color   = "#7DEFA0"
        warn_color = "#FFCC44"
        na_color   = "#667788"

        def _v(val: str, fallback: str = "—") -> str:
            return val.strip() if val.strip() else fallback

        self._f_hull.set_value(_v(info.hull_id))
        self._f_hull.set_color(ok_color if info.hull_id else na_color)

        self._f_serial.set_value(_v(info.serial_ecu))

        model = info.mpem_model_guess()
        self._f_model.set_value(model)
        self._f_model.set_color(ok_color if "hp" in model else warn_color)

        my = info.model_year_guess()
        self._f_my.set_value(my if my else "—")

        self._f_mpem.set_value(_v(info.mpem_sw))
        self._f_svc.set_value(_v(info.service_sw))
        hw_labels = {"062": "HW 062 — 1.5L (GTI 130/155, RXT 1.5L do 2016)",
                     "063": "HW 063 — Spark 90/115hp (900 ACE)",
                     "064": "HW 064 — 1.6L (300hp RXP/RXT/GTX, GTI SE 155)"}
        self._f_hw_type.set_value(hw_labels.get(info.hw_type, _v(info.hw_type, "Nepoznat")))

        self._f_date1.set_value(_v(info.date_first_prog))
        self._f_date2.set_value(_v(info.date_last_update))
        self._f_pcount.set_value(str(info.prog_count) if info.prog_count else "—")

        self._f_odo_raw.set_value(info.odo_hhmm())
        self._f_odo_note.set_value(str(info.odo_raw) if info.odo_raw else "—")
        self._f_odo_note.set_color("#667788")

        self._f_dealer.set_value(_v(info.dealer_name, "Nije programirano"))

        if info.errors:
            self._errors_text.setPlainText("\n".join(info.errors))
        else:
            self._errors_text.setPlainText("")
            self._errors_text.setPlaceholderText("Nema upozorenja.")

    def show_entry(self, key: str):
        pass  # TODO: scroll to / highlight entry
