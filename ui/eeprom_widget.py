"""
ME17Suite — EEPROM Viewer + Editor widget
Prikazuje i omogućava editiranje parsirani EEPROM podaci: identifikacija, datumi, odometar, dealer.

Editabilna polja: Hull ID, dealer naziv, datumi programiranja, broj programiranja.
Read-only polja: ECU serial, MPEM SW, servisni SW, HW tip, radni sati (circular buffer).

EEPROM nema checksum — izmjene se direktno upisuju.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QGroupBox, QLineEdit,
    QTextEdit, QScrollArea, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.eeprom import EepromParser, EepromEditor, EepromInfo


class _ReadField(QWidget):
    """Read-only red: label + vrijednost."""
    def __init__(self, label: str, value: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(label + ":")
        lbl.setFixedWidth(180)
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


class _EditField(QWidget):
    """Editabilni red: label + QLineEdit."""
    changed = pyqtSignal()

    def __init__(self, label: str, max_len: int, placeholder: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(label + ":")
        lbl.setFixedWidth(180)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("color: #8899AA; font-size: 12px;")

        self._edit = QLineEdit()
        self._edit.setMaxLength(max_len)
        self._edit.setPlaceholderText(placeholder)
        self._edit.setFixedWidth(220)
        self._edit.setStyleSheet("""
            QLineEdit {
                background: #1A2530; color: #C8E0F0; font-size: 12px;
                border: 1px solid #3A5570; border-radius: 3px; padding: 2px 6px;
            }
            QLineEdit:focus { border: 1px solid #4FC3F7; }
        """)
        self._edit.textChanged.connect(self.changed.emit)

        layout.addWidget(lbl)
        layout.addSpacing(8)
        layout.addWidget(self._edit)
        layout.addStretch()

    def value(self) -> str:
        return self._edit.text()

    def set_value(self, v: str):
        self._edit.blockSignals(True)
        self._edit.setText(v)
        self._edit.blockSignals(False)


class EepromWidget(QWidget):
    """Tab za pregled i editiranje EEPROM sadržaja."""

    eeprom_loaded = pyqtSignal(object)   # EepromInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info: EepromInfo | None = None
        self._editor: EepromEditor | None = None
        self._current_path: str = ""
        self._parser = EepromParser()
        self._dirty = False
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

        self._btn_save = QPushButton("Spremi izmjene")
        self._btn_save.setFixedHeight(32)
        self._btn_save.setEnabled(False)
        self._btn_save.setStyleSheet("""
            QPushButton { background: #2A7A2A; color: white; border-radius: 4px;
                          font-size: 12px; padding: 0 14px; }
            QPushButton:hover { background: #3A8A3A; }
            QPushButton:disabled { background: #2A3A2A; color: #556655; }
        """)
        self._btn_save.clicked.connect(self._save_file)

        self._btn_save_as = QPushButton("Spremi kao...")
        self._btn_save_as.setFixedHeight(32)
        self._btn_save_as.setEnabled(False)
        self._btn_save_as.setStyleSheet("""
            QPushButton { background: #3A5A3A; color: white; border-radius: 4px;
                          font-size: 12px; padding: 0 14px; }
            QPushButton:hover { background: #4A6A4A; }
            QPushButton:disabled { background: #2A3A2A; color: #556655; }
        """)
        self._btn_save_as.clicked.connect(self._save_file_as)

        self._lbl_file = QLabel("Nije učitan fajl")
        self._lbl_file.setStyleSheet("color: #667788; font-size: 11px;")

        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet("color: #FFCC44; font-size: 11px;")

        bar.addWidget(self._btn_open)
        bar.addSpacing(6)
        bar.addWidget(self._btn_save)
        bar.addSpacing(4)
        bar.addWidget(self._btn_save_as)
        bar.addSpacing(10)
        bar.addWidget(self._lbl_file)
        bar.addSpacing(10)
        bar.addWidget(self._lbl_status)
        bar.addStretch()
        root.addLayout(bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #334455;")
        root.addWidget(sep)

        # ── scroll area ───────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        # ── Identifikacija (read-only) ────────────────────────────────────────
        grp_id = self._make_group("Identifikacija vozila")
        self._f_hull    = self._add_read(grp_id, "Hull ID / VIN")
        self._f_serial  = self._add_read(grp_id, "ECU serijski broj")
        self._f_model   = self._add_read(grp_id, "Procijenjeni model")
        self._f_my      = self._add_read(grp_id, "Model godina (kod)")

        # ── SW verzije (read-only) ────────────────────────────────────────────
        grp_sw = self._make_group("Software verzije")
        self._f_mpem    = self._add_read(grp_sw, "MPEM SW ID")
        self._f_svc     = self._add_read(grp_sw, "Servisni SW ID")
        self._f_hw_type = self._add_read(grp_sw, "HW tip ECU-a")

        # ── Radni sati (read-only) ────────────────────────────────────────────
        grp_odo = self._make_group("Radni sati / Odometar  (read-only — circular buffer)")
        self._f_odo_hhmm = self._add_read(grp_odo, "Radni sati")
        self._f_odo_raw  = self._add_read(grp_odo, "Sirova vrijednost (min)")
        self._f_odo_raw.set_color("#667788")

        # ── Editabilna polja ──────────────────────────────────────────────────
        grp_edit = self._make_group("Editabilna polja  ✏")
        grp_edit.setStyleSheet(grp_edit.styleSheet().replace("#99BBCC", "#4FC3F7"))

        note = QLabel("  Hull ID, dealer naziv, datumi i broj programiranja se mogu direktno mijenjati."
                      "  EEPROM nema checksum — izmjene su sigurne.")
        note.setStyleSheet("color: #778899; font-size: 11px;")
        note.setWordWrap(True)
        grp_edit.layout().addWidget(note)

        self._e_hull   = self._add_edit(grp_edit, "Hull ID / VIN", 12, "YDVxxxxxxxxx")
        self._e_dealer = self._add_edit(grp_edit, "Naziv dealera", 16, "max 16 znakova")
        self._e_date1  = self._add_edit(grp_edit, "Prvo programiranje", 8, "DD-MM-YY")
        self._e_date2  = self._add_edit(grp_edit, "Zadnje ažuriranje", 8, "DD-MM-YY")

        # Broj programiranja — SpinBox
        pcount_row = QWidget()
        pcount_layout = QHBoxLayout(pcount_row)
        pcount_layout.setContentsMargins(0, 2, 0, 2)
        lbl_pc = QLabel("Broj programiranja:")
        lbl_pc.setFixedWidth(180)
        lbl_pc.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl_pc.setStyleSheet("color: #8899AA; font-size: 12px;")
        self._e_pcount = QSpinBox()
        self._e_pcount.setRange(0, 255)
        self._e_pcount.setFixedWidth(80)
        self._e_pcount.setStyleSheet("""
            QSpinBox {
                background: #1A2530; color: #C8E0F0; font-size: 12px;
                border: 1px solid #3A5570; border-radius: 3px; padding: 2px 4px;
            }
            QSpinBox:focus { border: 1px solid #4FC3F7; }
        """)
        self._e_pcount.valueChanged.connect(self._on_edit_changed)
        pcount_layout.addWidget(lbl_pc)
        pcount_layout.addSpacing(8)
        pcount_layout.addWidget(self._e_pcount)
        pcount_layout.addStretch()
        grp_edit.layout().addWidget(pcount_row)

        # ── Greške / upozorenja ───────────────────────────────────────────────
        grp_errors = self._make_group("Dijagnostika / upozorenja")
        self._errors_text = QTextEdit()
        self._errors_text.setReadOnly(True)
        self._errors_text.setMaximumHeight(80)
        self._errors_text.setStyleSheet(
            "background: #1A2530; color: #FF9944; font-size: 11px; border: 1px solid #334455;"
        )
        self._errors_text.setPlaceholderText("Nema upozorenja.")
        grp_errors.layout().addWidget(self._errors_text)

        for grp in [grp_id, grp_sw, grp_odo, grp_edit, grp_errors]:
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

    def _add_read(self, grp: QGroupBox, label: str) -> _ReadField:
        row = _ReadField(label)
        grp.layout().addWidget(row)
        return row

    def _add_edit(self, grp: QGroupBox, label: str, max_len: int, placeholder: str = "") -> _EditField:
        row = _EditField(label, max_len, placeholder)
        row.changed.connect(self._on_edit_changed)
        grp.layout().addWidget(row)
        return row

    # ── učitavanje ────────────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori EEPROM dump", "",
            "Binary fajlovi (*.bin);;Svi fajlovi (*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        try:
            self._editor = EepromEditor(path)
        except ValueError as e:
            QMessageBox.warning(self, "Greška EEPROM-a", str(e))
            return
        self._current_path = path
        info = self._editor.get_info()
        self._info = info
        import os
        self._lbl_file.setText(os.path.basename(path))
        self._dirty = False
        self._populate(info)
        self._populate_edit(info)
        self._btn_save.setEnabled(False)
        self._btn_save_as.setEnabled(True)
        self._lbl_status.setText("")
        self.eeprom_loaded.emit(info)

    def load_bytes(self, data: bytes, label: str = "<buffer>"):
        try:
            self._editor = EepromEditor.from_bytes(data, label)
        except ValueError as e:
            QMessageBox.warning(self, "Greška EEPROM-a", str(e))
            return
        self._current_path = ""
        info = self._editor.get_info()
        self._info = info
        self._lbl_file.setText(label)
        self._dirty = False
        self._populate(info)
        self._populate_edit(info)
        self._btn_save.setEnabled(False)
        self._btn_save_as.setEnabled(True)
        self._lbl_status.setText("")
        self.eeprom_loaded.emit(info)

    # ── populacija prikaza ────────────────────────────────────────────────────

    def _populate(self, info: EepromInfo):
        ok   = "#7DEFA0"
        warn = "#FFCC44"
        na   = "#667788"

        def _v(val: str, fallback: str = "—") -> str:
            return val.strip() if val.strip() else fallback

        self._f_hull.set_value(_v(info.hull_id))
        self._f_hull.set_color(ok if info.hull_id else na)
        self._f_serial.set_value(_v(info.serial_ecu))
        model = info.mpem_model_guess()
        self._f_model.set_value(model)
        self._f_model.set_color(ok if "hp" in model else warn)
        my = info.model_year_guess()
        self._f_my.set_value(my if my else "—")

        self._f_mpem.set_value(_v(info.mpem_sw))
        self._f_svc.set_value(_v(info.service_sw))
        hw_labels = {
            "062": "HW 062 — 1.5L (GTI 130/155, RXT 1.5L do 2016)",
            "063": "HW 063 — Spark 90/115hp (900 ACE)",
            "064": "HW 064 — 1.6L (300hp RXP/RXT/GTX, GTI SE 155)",
        }
        self._f_hw_type.set_value(hw_labels.get(info.hw_type, _v(info.hw_type, "Nepoznat")))

        self._f_odo_hhmm.set_value(info.odo_hhmm())
        self._f_odo_hhmm.set_color(ok if info.odo_raw > 0 else na)
        self._f_odo_raw.set_value(str(info.odo_raw) if info.odo_raw else "—")

        self._errors_text.setPlainText("\n".join(info.errors) if info.errors else "")
        self._errors_text.setPlaceholderText("Nema upozorenja.")

    def _populate_edit(self, info: EepromInfo):
        self._e_hull.set_value(info.hull_id.strip())
        self._e_dealer.set_value(info.dealer_name.strip())
        self._e_date1.set_value(info.date_first_prog.strip())
        self._e_date2.set_value(info.date_last_update.strip())
        self._e_pcount.blockSignals(True)
        self._e_pcount.setValue(info.prog_count)
        self._e_pcount.blockSignals(False)

    # ── editiranje i snimanje ─────────────────────────────────────────────────

    def _on_edit_changed(self):
        if self._editor is None:
            return
        self._dirty = True
        self._btn_save.setEnabled(bool(self._current_path))
        self._btn_save_as.setEnabled(True)
        self._lbl_status.setText("● Nespremljene izmjene")
        self._lbl_status.setStyleSheet("color: #FFCC44; font-size: 11px;")

    def _apply_edits(self) -> bool:
        """Primijeni izmjene na editor. Vraća False ako validacija ne prođe."""
        if self._editor is None:
            return False
        try:
            self._editor.set_hull_id(self._e_hull.value())
            self._editor.set_dealer_name(self._e_dealer.value())
            self._editor.set_date_first_prog(self._e_date1.value())
            self._editor.set_date_last_update(self._e_date2.value())
            self._editor.set_prog_count(self._e_pcount.value())
            return True
        except ValueError as e:
            QMessageBox.warning(self, "Greška validacije", str(e))
            return False

    def _save_file(self):
        if not self._current_path or self._editor is None:
            return
        if not self._apply_edits():
            return
        try:
            self._editor.save(self._current_path)
            self._dirty = False
            self._btn_save.setEnabled(False)
            self._lbl_status.setText("✔ Spremljeno")
            self._lbl_status.setStyleSheet("color: #7DEFA0; font-size: 11px;")
        except Exception as e:
            QMessageBox.critical(self, "Greška snimanja", str(e))

    def _save_file_as(self):
        if self._editor is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Spremi EEPROM kao", "",
            "Binary fajlovi (*.bin);;Svi fajlovi (*)"
        )
        if not path:
            return
        if not self._apply_edits():
            return
        try:
            self._editor.save(path)
            self._current_path = path
            import os
            self._lbl_file.setText(os.path.basename(path))
            self._dirty = False
            self._btn_save.setEnabled(False)
            self._lbl_status.setText("✔ Spremljeno")
            self._lbl_status.setStyleSheet("color: #7DEFA0; font-size: 11px;")
        except Exception as e:
            QMessageBox.critical(self, "Greška snimanja", str(e))

    def get_modified_bytes(self) -> bytes | None:
        """Vraća modificirani EEPROM kao bytes (za integraciju)."""
        if self._editor is None:
            return None
        if not self._apply_edits():
            return None
        return self._editor.get_bytes()

    def show_entry(self, key: str):
        pass  # TODO: scroll to / highlight entry
