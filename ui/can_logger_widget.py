"""
ME17Suite — CAN Logger Widget
Live CAN bus acquisition + log viewer za BRP Sea-Doo ME17.8.5 ECU.

Zahtijeva IXXAT USB-to-CAN adapter i python-can paket za live snimanje.
Otvaranje log fajlova radi i bez hardvera.

Hardware: IXXAT USB-to-CAN, BRP CAN bus @ 250 kbps, standard 11-bit frames.
"""

import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QComboBox, QSplitter, QHeaderView,
    QFrame, QCheckBox, QFileDialog, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont

from core.can_logger import CanLoggerThread, LogFile
from core.can_decoder import (
    CanDecoder,
    CAN_RPM, CAN_TEMP, CAN_ENGINE_HOURS,
    CAN_ENGINE_FLAGS, CAN_DTC, CAN_EOT_MUX, CAN_BROADCAST,
    CAN_SPARK_EGT, CAN_SPARK_THB,
)


# ─── _GaugeTile ──────────────────────────────────────────────────────────────

class _GaugeTile(QFrame):
    """Jedna kartica s live parametrom (label + vrijednost + jedinica)."""

    _COLOR_NORMAL = "#9cdcfe"
    _COLOR_WARN   = "#EF5350"
    _COLOR_INACT  = "#3A3A46"

    def __init__(self, label: str, unit: str, warn_above: float = None, parent=None):
        super().__init__(parent)
        self._warn_above = warn_above

        self.setStyleSheet(
            "QFrame {"
            "  background:#1a1a1d;"
            "  border:1px solid #2A2A32;"
            "  border-radius:4px;"
            "  padding:6px;"
            "}"
        )

        lo = QVBoxLayout(self)
        lo.setContentsMargins(6, 4, 6, 4)
        lo.setSpacing(2)

        self._lbl_name = QLabel(label)
        self._lbl_name.setStyleSheet("color:#555555; font-size:12px; border:none; background:transparent;")
        self._lbl_name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lo.addWidget(self._lbl_name)

        self._lbl_value = QLabel("—")
        self._lbl_value.setStyleSheet(
            f"color:{self._COLOR_INACT}; font-size:28px; font-weight:bold;"
            " font-family:Consolas; border:none; background:transparent;"
        )
        self._lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(self._lbl_value)

        self._lbl_unit = QLabel(unit)
        self._lbl_unit.setStyleSheet("color:#404050; font-size:11px; border:none; background:transparent;")
        self._lbl_unit.setAlignment(Qt.AlignmentFlag.AlignRight)
        lo.addWidget(self._lbl_unit)

    def set_value(self, v: float) -> None:
        """Ažuriraj prikaz; primjeni warn boju ako je prekoračen limit."""
        if isinstance(v, float):
            if v == int(v):
                text = str(int(v))
            else:
                text = f"{v:.1f}"
        else:
            text = str(v)

        if self._warn_above is not None and v > self._warn_above:
            color = self._COLOR_WARN
        else:
            color = self._COLOR_NORMAL

        self._lbl_value.setText(text)
        self._lbl_value.setStyleSheet(
            f"color:{color}; font-size:28px; font-weight:bold;"
            " font-family:Consolas; border:none; background:transparent;"
        )

    def set_inactive(self) -> None:
        """Postavi '—' i neutralnu (sivu) boju."""
        self._lbl_value.setText("—")
        self._lbl_value.setStyleSheet(
            f"color:{self._COLOR_INACT}; font-size:28px; font-weight:bold;"
            " font-family:Consolas; border:none; background:transparent;"
        )


# ─── Boje redova po CAN ID-u ──────────────────────────────────────────────────

def _row_color(can_id: int) -> str:
    if can_id in (0x0108, 0x0110, 0x012C, 0x013C):
        return "#cccccc"
    if can_id in (0x0134, 0x0154):
        return "#9cdcfe"
    if can_id == 0x0148:
        return "#4ec9b0"
    return "#666666"


# ─── CanLoggerWidget ──────────────────────────────────────────────────────────

class CanLoggerWidget(QWidget):
    """CAN Logger tab — live snimanje i pregled log fajlova."""

    _MAX_ROWS     = 2000
    _TRIM_ROWS    = 500   # brisati prvih N kad se dosegne max

    def __init__(self, parent=None):
        super().__init__(parent)

        self._thread: CanLoggerThread | None = None
        self._connected    = False
        self._rec_active   = False
        self._rec_messages: list[tuple[float, int, bytes]] = []
        self._rec_start    = 0.0
        self._msg_count    = 0

        self._rec_timer = QTimer(self)
        self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._update_rec_timer)

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        lo.addWidget(self._build_header())
        lo.addWidget(self._build_body(), 1)

    # ── Header bar ────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setStyleSheet("background:#252526; border-bottom:1px solid #333333;")
        h = QHBoxLayout(hdr)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(12)

        title = QLabel("CAN LOGGER")
        title.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px;"
        )
        h.addWidget(title)

        # Kanal
        ch_lbl = QLabel("IXXAT ch:")
        ch_lbl.setStyleSheet("color:#888888; font-size:12px;")
        h.addWidget(ch_lbl)

        self._ch_combo = QComboBox()
        self._ch_combo.addItems(["0", "1", "2", "3"])
        self._ch_combo.setFixedWidth(60)
        self._ch_combo.setStyleSheet(
            "QComboBox { background:#1e1e1e; color:#C8C8D0; border:1px solid #333333;"
            "  border-radius:3px; padding:2px 6px; font-family:Consolas; font-size:12px; }"
            "QComboBox::drop-down { border:none; }"
        )
        h.addWidget(self._ch_combo)

        # Spoji / Odspoji
        self._btn_connect = QPushButton("Spoji")
        self._btn_connect.setFixedHeight(26)
        self._btn_connect.setStyleSheet(self._btn_style())
        self._btn_connect.clicked.connect(self._on_connect_clicked)
        h.addWidget(self._btn_connect)

        # Snimi / Stop
        self._btn_record = QPushButton("⏺  Snimi")
        self._btn_record.setFixedHeight(26)
        self._btn_record.setEnabled(False)
        self._btn_record.setStyleSheet(self._btn_style())
        self._btn_record.clicked.connect(self._on_record_clicked)
        h.addWidget(self._btn_record)

        # Otvori log
        self._btn_open = QPushButton("Otvori log...")
        self._btn_open.setFixedHeight(26)
        self._btn_open.setStyleSheet(self._btn_style())
        self._btn_open.clicked.connect(self._on_open_clicked)
        h.addWidget(self._btn_open)

        sep = QLabel("|")
        sep.setStyleSheet("color:#444444; font-size:14px; padding:0 4px;")
        h.addWidget(sep)

        # Status
        self._status_lbl = QLabel("● Nije spojeno")
        self._status_lbl.setStyleSheet("color:#EF5350; font-size:12px; font-family:Consolas;")
        h.addWidget(self._status_lbl)

        h.addStretch()

        # REC timer
        self._rec_timer_lbl = QLabel("")
        self._rec_timer_lbl.setStyleSheet(
            "color:#EF5350; font-size:12px; font-family:Consolas; font-weight:bold;"
        )
        h.addWidget(self._rec_timer_lbl)

        return hdr

    @staticmethod
    def _btn_style() -> str:
        return (
            "QPushButton {"
            "  background:#2d2d30; color:#C8C8D0; border:1px solid #444444;"
            "  border-radius:3px; padding:2px 10px; font-size:12px;"
            "}"
            "QPushButton:hover { background:#3e3e42; }"
            "QPushButton:disabled { color:#555555; border-color:#333333; }"
            "QPushButton:checked { background:#1e3a1e; color:#4CAF50; border-color:#4CAF50; }"
        )

    # ── Glavni sadržaj (splitter) ─────────────────────────────────────────────

    def _build_body(self) -> QSplitter:
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(1)
        split.setStyleSheet("QSplitter::handle { background:#333333; }")
        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setSizes([580, 420])
        return split

    # ── Lijevo: Live parametri ────────────────────────────────────────────────

    def _build_left(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(12, 12, 6, 12)
        lo.setSpacing(8)

        hdr_lbl = QLabel("LIVE PARAMETRI")
        hdr_lbl.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr_lbl)

        # Tile definicije: (ključ, label, jedinica, warn_above)
        tile_defs = [
            ("RPM",       "RPM",     "rpm",  7000),
            ("ECT °C",    "ECT",     "°C",   95),
            ("EOT °C",    "EOT",     "°C",   120),
            ("MAP kPa",   "MAP",     "kPa",  None),
            ("TPS %",     "TPS",     "%",    None),
            ("MAT °C",    "MAT",     "°C",   None),
            ("EGT °C",    "EGT",     "°C",   None),
            ("Brzina km/h","Brzina", "km/h", None),
            ("Gorivo %",  "Gorivo",  "%",    None),
            ("Sati h",    "Sati",    "h",    None),
        ]

        self._tiles: dict[str, _GaugeTile] = {}
        grid = QGridLayout()
        grid.setSpacing(6)

        for idx, (key, lbl, unit, warn) in enumerate(tile_defs):
            tile = _GaugeTile(lbl, unit, warn_above=warn)
            self._tiles[key] = tile
            row = idx // 3
            col = idx % 3
            grid.addWidget(tile, row, col)

        lo.addLayout(grid)

        legend = QLabel(
            "● dekodiranje potvrđeno  ■ procijenjeno  □ bench-only"
        )
        legend.setStyleSheet("color:#404050; font-size:11px;")
        lo.addWidget(legend)

        lo.addStretch()
        return w

    # ── Desno: Raw CAN log ────────────────────────────────────────────────────

    def _build_right(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(6, 12, 12, 12)
        lo.setSpacing(6)

        # Header red
        hdr_lo = QHBoxLayout()
        hdr_lo.setSpacing(8)

        raw_lbl = QLabel("RAW CAN LOG")
        raw_lbl.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px;"
        )
        hdr_lo.addWidget(raw_lbl)
        hdr_lo.addStretch()

        self._chk_autoscroll = QCheckBox("Auto-scroll")
        self._chk_autoscroll.setChecked(True)
        self._chk_autoscroll.setStyleSheet(
            "QCheckBox { color:#888888; font-size:12px; }"
            "QCheckBox::indicator { width:13px; height:13px; }"
        )
        hdr_lo.addWidget(self._chk_autoscroll)

        btn_clear = QPushButton("Očisti")
        btn_clear.setFixedHeight(22)
        btn_clear.setStyleSheet(self._btn_style())
        btn_clear.clicked.connect(self._clear_table)
        hdr_lo.addWidget(btn_clear)

        lo.addLayout(hdr_lo)

        # Tablica
        self._log_table = QTableWidget(0, 4)
        self._log_table.setHorizontalHeaderLabels(["Vr (s)", "ID", "Hex", "Decoded"])

        hh = self._log_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._log_table.setColumnWidth(0, 80)
        self._log_table.setColumnWidth(1, 70)
        self._log_table.setColumnWidth(2, 180)
        self._log_table.verticalHeader().hide()
        self._log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._log_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._log_table.setFont(QFont("Consolas", 11))
        self._log_table.setStyleSheet(
            "QTableWidget {"
            "  background:#111113; color:#C8C8D0; gridline-color:#222222;"
            "  border:1px solid #333333;"
            "}"
            "QTableWidget::item { padding:1px 4px; }"
            "QHeaderView::section {"
            "  background:#1e1e1e; color:#666666; border:none;"
            "  border-bottom:1px solid #333333; padding:3px 6px; font-size:11px;"
            "}"
        )
        # Fiksna visina reda 18px
        self._log_table.verticalHeader().setDefaultSectionSize(18)

        lo.addWidget(self._log_table, 1)

        # Status bar
        self._stats_lbl = QLabel("0 poruka")
        self._stats_lbl.setStyleSheet("color:#555555; font-size:11px; font-family:Consolas;")
        lo.addWidget(self._stats_lbl)

        return w

    # ── Gumbi — logika ────────────────────────────────────────────────────────

    def _on_connect_clicked(self) -> None:
        if not self._connected:
            self._do_connect()
        else:
            self._do_disconnect()

    def _do_connect(self) -> None:
        channel = int(self._ch_combo.currentText())
        self._thread = CanLoggerThread(channel=channel, bitrate=250_000)
        self._thread.message_received.connect(self._on_message)
        self._thread.connection_status.connect(self._on_connection_status)
        self._thread.connect_bus()
        self._thread.start()
        self._btn_connect.setText("Odspoji")
        self._ch_combo.setEnabled(False)

    def _do_disconnect(self) -> None:
        if self._thread is not None:
            # Zaustavi snimanje ako je aktivno
            if self._rec_active:
                self._stop_recording()
            self._thread.stop()
            self._thread = None

        self._connected = False
        self._btn_connect.setText("Spoji")
        self._ch_combo.setEnabled(True)
        self._btn_record.setEnabled(False)
        self._btn_record.setText("⏺  Snimi")
        self._status_lbl.setText("● Nije spojeno")
        self._status_lbl.setStyleSheet("color:#EF5350; font-size:12px; font-family:Consolas;")

        for tile in self._tiles.values():
            tile.set_inactive()

    def _on_connection_status(self, connected: bool, msg: str) -> None:
        if connected:
            self._connected = True
            self._status_lbl.setText("● Spojeno  250 kbps")
            self._status_lbl.setStyleSheet(
                "color:#4CAF50; font-size:12px; font-family:Consolas;"
            )
            self._btn_record.setEnabled(True)
        else:
            self._connected = False
            self._status_lbl.setText(f"● {msg}")
            self._status_lbl.setStyleSheet(
                "color:#EF5350; font-size:12px; font-family:Consolas;"
            )
            self._btn_record.setEnabled(False)
            self._btn_connect.setText("Spoji")
            self._ch_combo.setEnabled(True)

    def _on_record_clicked(self) -> None:
        if not self._rec_active:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self) -> None:
        self._rec_messages = []
        self._rec_start    = time.time()
        self._rec_active   = True
        self._btn_record.setText("⏹  Stop")
        self._rec_timer.start()
        self._update_rec_timer()

    def _stop_recording(self) -> None:
        self._rec_active = False
        self._rec_timer.stop()
        self._rec_timer_lbl.setText("")
        self._btn_record.setText("⏺  Snimi")

        if not self._rec_messages:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Spremi CAN log",
            "",
            "CAN log fajlovi (*.txt);;Svi fajlovi (*)",
        )
        if path:
            start_wall = datetime.fromtimestamp(self._rec_start).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )
            LogFile.save(path, self._rec_messages, start_time=start_wall)

    def _update_rec_timer(self) -> None:
        elapsed = int(time.time() - self._rec_start)
        hh = elapsed // 3600
        mm = (elapsed % 3600) // 60
        ss = elapsed % 60
        self._rec_timer_lbl.setText(f"REC  {hh:02d}:{mm:02d}:{ss:02d}")

    def _on_open_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Otvori CAN log",
            "",
            "CAN log fajlovi (*.txt);;Svi fajlovi (*)",
        )
        if not path:
            return

        try:
            messages = LogFile.load(path)
        except Exception as e:
            self._status_lbl.setText(f"● Greška: {e}")
            self._status_lbl.setStyleSheet(
                "color:#EF5350; font-size:12px; font-family:Consolas;"
            )
            return

        self._clear_table()
        for ts, can_id, data in messages:
            self._append_row(ts, can_id, data)

    # ── Poruka primljena (live) ───────────────────────────────────────────────

    def _on_message(self, timestamp: float, can_id: int, data: bytes) -> None:
        self._append_row(timestamp, can_id, data)

        # Ažuriraj tile-ove
        self._update_tiles(can_id, data)

        # Snimanje
        if self._rec_active:
            self._rec_messages.append((timestamp, can_id, data))

    def _update_tiles(self, can_id: int, data: bytes) -> None:
        try:
            if can_id == CAN_RPM:
                self._tiles["RPM"].set_value(CanDecoder.decode_rpm(data))
                self._tiles["TPS %"].set_value(CanDecoder.decode_throttle_from_rpm_msg(data))
                self._tiles["MAP kPa"].set_value(CanDecoder.decode_map_from_rpm_msg(data))

            elif can_id == CAN_TEMP:
                self._tiles["ECT °C"].set_value(CanDecoder.decode_coolant_temp(data))
                self._tiles["MAT °C"].set_value(CanDecoder.decode_iat(data))

            elif can_id == CAN_ENGINE_HOURS:
                self._tiles["Sati h"].set_value(CanDecoder.decode_engine_hours(data))

            elif can_id == CAN_EOT_MUX:          # 0x0316
                self._tiles["EOT °C"].set_value(CanDecoder.decode_eot_316(data))

            elif can_id == CAN_BROADCAST:         # 0x0342
                d = CanDecoder.decode_mux_342(data)
                if "ect_c"    in d: self._tiles["ECT °C"].set_value(d["ect_c"])
                if "map_hpa"  in d: self._tiles["MAP kPa"].set_value(d["map_hpa"] / 10.0)
                if "mat_c"    in d: self._tiles["MAT °C"].set_value(d["mat_c"])

            elif can_id == CAN_SPARK_EGT:         # 0x0103 — Spark EGT + TPS
                self._tiles["EGT °C"].set_value(CanDecoder.decode_spark_egt(data))
                self._tiles["TPS %"].set_value(CanDecoder.decode_spark_tps_103(data))

            elif can_id == CAN_SPARK_THB:         # 0x0104 — Spark throttle body
                self._tiles["TPS %"].set_value(CanDecoder.decode_spark_throttle_body(data))

        except Exception:
            pass   # ne rušiti GUI zbog loše poruke

    # ── Tablica: dodavanje redova ─────────────────────────────────────────────

    def _append_row(self, timestamp: float, can_id: int, data: bytes) -> None:
        # Trim ako smo pri limitu
        if self._log_table.rowCount() >= self._MAX_ROWS:
            for _ in range(self._TRIM_ROWS):
                self._log_table.removeRow(0)

        decoded_str = self._build_decoded_str(can_id, data)
        hex_str     = data.hex(" ").upper()
        color       = _row_color(can_id)

        row = self._log_table.rowCount()
        self._log_table.insertRow(row)

        cells = [
            (f"{timestamp:.3f}", Qt.AlignmentFlag.AlignCenter),
            (f"0x{can_id:04X}",  Qt.AlignmentFlag.AlignCenter),
            (hex_str,            Qt.AlignmentFlag.AlignLeft),
            (decoded_str,        Qt.AlignmentFlag.AlignLeft),
        ]
        for col, (txt, align) in enumerate(cells):
            item = QTableWidgetItem(txt)
            item.setForeground(QBrush(QColor(color)))
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | align
            )
            self._log_table.setItem(row, col, item)

        self._msg_count += 1
        self._stats_lbl.setText(f"{self._msg_count} poruka")

        if self._chk_autoscroll.isChecked():
            self._log_table.scrollToBottom()

    @staticmethod
    def _build_decoded_str(can_id: int, data: bytes) -> str:
        """Kratki dekodirani string za tablicu (max ~40 znakova)."""
        try:
            d = CanDecoder.decode(can_id, data)
        except Exception:
            return ""

        if not d.get("decoded"):
            return ""

        skip = {"can_id", "raw", "decoded"}
        parts = [
            f"{k}={v}"
            for k, v in d.items()
            if k not in skip
        ]
        return "  ".join(parts[:3])

    # ── Pomoćne metode ────────────────────────────────────────────────────────

    def _clear_table(self) -> None:
        self._log_table.setRowCount(0)
        self._msg_count = 0
        self._stats_lbl.setText("0 poruka")

    # ── Public API ────────────────────────────────────────────────────────────

    def clear_session(self) -> None:
        """Resetiraj sve — poziva se pri učitavanju novog .bin fajla."""
        if self._connected:
            self._do_disconnect()
        self._clear_table()
        self._rec_messages = []
        self._rec_active   = False
        self._rec_timer.stop()
        self._rec_timer_lbl.setText("")
        self._btn_record.setText("⏺  Snimi")
        for tile in self._tiles.values():
            tile.set_inactive()
