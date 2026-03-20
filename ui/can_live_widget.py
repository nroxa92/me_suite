"""
ME17Suite — CAN Live Decode Widget
Live prikaz CAN busa u realnom vremenu (IXAAT VCI4 USB-to-CAN).

Komponente:
  CanWorker     — QThread, čita python-can bus.recv() loop
  CanLiveWidget — dashboard + ID tablica + log strip
  CanLivePanel  — container s kontrolama (bitrate, kanal, start/stop)

Diagnostic bus:  500 kbps  (OBD konektor / IXAAT bench)
Cluster bus:     250 kbps  (Delphi 20-pin J1 pin2/3)
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QComboBox, QPlainTextEdit, QSplitter,
    QGroupBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False

try:
    from core.can_decoder import (
        CanDecoder, validate_checksum, extract_rolling_counter,
        decode_riding_mode,
    )
    DECODER_AVAILABLE = True
except ImportError:
    CanDecoder = None  # type: ignore[assignment,misc]
    DECODER_AVAILABLE = False

# ─── Boje (dark theme) ────────────────────────────────────────────────────────

BG_MAIN      = "#111113"
BG_PANEL     = "#1A1A1E"
BG_WIDGET    = "#16161A"
ACCENT       = "#4FC3F7"
TEXT_PRIMARY = "#E8E8EC"
TEXT_DIM     = "#7A7A8A"
GREEN        = "#4CAF50"
ORANGE       = "#FF9800"
RED          = "#F44336"
YELLOW       = "#FFC107"

MONO_FONT  = QFont("Consolas", 9)
LARGE_FONT = QFont("Segoe UI", 48, QFont.Weight.Bold)
MED_FONT   = QFont("Segoe UI", 14, QFont.Weight.Bold)
LABEL_FONT = QFont("Segoe UI", 9)

# ─── IdStats — identično can_sniffer.py, ali bez CSV ─────────────────────────

class _IdStats:
    __slots__ = (
        "count", "first_ts", "last_ts", "last_data", "dlc",
        "checksum_errors", "rolling_ctr_jumps",
        "_prev_data", "_prev_rc",
    )

    def __init__(self) -> None:
        self.count            = 0
        self.first_ts: float | None = None
        self.last_ts: float  = 0.0
        self.last_data: bytes | None = None
        self.dlc              = 0
        self.checksum_errors  = 0
        self.rolling_ctr_jumps = 0
        self._prev_data: bytes | None = None
        self._prev_rc: int | None = None

    def update(self, ts: float, data: bytes) -> None:
        self.count += 1
        if self.first_ts is None:
            self.first_ts = ts
        self.last_ts  = ts
        self.dlc      = len(data)
        self.last_data = bytes(data)
        self._prev_data = self.last_data

        # XOR checksum (samo DLC=8)
        if len(data) == 8 and DECODER_AVAILABLE:
            if not validate_checksum(data):
                self.checksum_errors += 1

        # Rolling counter jump
        if len(data) >= 7 and DECODER_AVAILABLE:
            rc = extract_rolling_counter(data)
            if self._prev_rc is not None:
                if rc != (self._prev_rc + 1) & 0x0F:
                    self.rolling_ctr_jumps += 1
            self._prev_rc = rc

    @property
    def freq_hz(self) -> float:
        if self.count < 2 or self.last_ts == self.first_ts:
            return 0.0
        return (self.count - 1) / (self.last_ts - self.first_ts)


def _format_decoded(decoded: dict) -> str:
    """Formatira CanDecoder.decode() rezultat u kratki string za log."""
    if not decoded.get("decoded"):
        return ""
    skip = {"can_id", "raw", "decoded", "checksum_ok", "rolling_ctr",
            "hw_id_raw", "frame_type", "alive_byte"}
    parts = []
    for k, v in decoded.items():
        if k in skip:
            continue
        if isinstance(v, float):
            parts.append(f"{k}={v:.1f}")
        elif isinstance(v, list):
            parts.append(f"{k}=[{','.join(str(x) for x in v)}]")
        else:
            parts.append(f"{k}={v}")
    return "  ".join(parts)


# ─── CanWorker — QThread ──────────────────────────────────────────────────────

class CanWorker(QThread):
    """
    Background thread koji čita python-can bus.recv() petlju.

    Signali:
        message_received(arb_id, timestamp, data) — svaki primljeni frejm
        error_occurred(msg)                        — greška busa ili drivera
    """

    message_received = pyqtSignal(int, float, bytes)
    error_occurred   = pyqtSignal(str)

    def __init__(self, bitrate: int = 500_000, channel: int = 0, parent=None):
        super().__init__(parent)
        self._bitrate  = bitrate
        self._channel  = channel
        self._running  = False

    def run(self) -> None:
        if not CAN_AVAILABLE:
            self.error_occurred.emit("python-can nije instaliran (pip install python-can)")
            return

        try:
            bus = can.Bus(
                interface="ixxat",
                channel=self._channel,
                bitrate=self._bitrate,
                receive_own_messages=False,
                monitor=True,   # pasivni monitor mod — ne šalje ACK
            )
        except Exception as exc:
            self.error_occurred.emit(f"IXXAT nije pronađen: {exc}")
            return

        self._running = True
        try:
            while self._running:
                try:
                    msg = bus.recv(timeout=0.1)
                except Exception as exc:
                    if "overrun" in str(exc).lower():
                        # Buffer overrun — preskoči, ne zaustavljaj
                        continue
                    self.error_occurred.emit(f"Bus greška: {exc}")
                    break

                if msg is None:
                    continue

                ts   = msg.timestamp or time.time()
                mid  = msg.arbitration_id
                data = bytes(msg.data)
                self.message_received.emit(mid, ts, data)
        finally:
            try:
                bus.shutdown()
            except Exception:
                pass
            self._running = False

    def stop(self) -> None:
        """Zaustavi petlju i pričekaj kraj threada (max 2s)."""
        self._running = False
        self.wait(2000)


# ─── DashCard — jedan tile na dashboardu ─────────────────────────────────────

class _DashCard(QFrame):
    """Tile s labelom naslova i velikom vrijednosti."""

    def __init__(self, title: str, unit: str = "", big: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._unit = unit
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid #2A2A32; border-radius:6px;"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(LABEL_FONT)
        self._title_lbl.setStyleSheet(f"color:{TEXT_DIM}; border:none;")
        lay.addWidget(self._title_lbl)

        self._value_lbl = QLabel("—")
        font = LARGE_FONT if big else MED_FONT
        self._value_lbl.setFont(font)
        self._value_lbl.setStyleSheet(f"color:{ACCENT}; border:none;")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._value_lbl)

    def set_value(self, val: str | int | float, color: str | None = None) -> None:
        text = f"{val}{' ' + self._unit if self._unit else ''}"
        self._value_lbl.setText(text)
        c = color or ACCENT
        self._value_lbl.setStyleSheet(f"color:{c}; border:none;")


# ─── CanLiveWidget — glavni widget ───────────────────────────────────────────

class CanLiveWidget(QWidget):
    """
    Prikazuje live CAN decode u tri zone:
      1. Dashboard — ključni parametri u velikim tilovima
      2. CAN ID tablica — statistika po ID-u (ažurira se svakih 2s)
      3. Log strip — scrollable hex+decode log (max 500 linija)
    """

    # Kolone ID tablice
    _COL_ID      = 0
    _COL_HZ      = 1
    _COL_DLC     = 2
    _COL_BYTES   = 3
    _COL_DECODED = 4
    _COL_CS      = 5
    _COL_RC      = 6

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN}; color:{TEXT_PRIMARY};")

        # Stanje
        self._stats:   dict[int, _IdStats] = defaultdict(_IdStats)
        self._msg_count = 0
        self._start_ts: float | None = None

        # Live dashboard vrijednosti
        self._rpm:          float | None = None
        self._coolant:      int | None   = None
        self._hours:        float | None = None
        self._dtc_count:    int          = 0
        self._engine_state: str          = "—"
        self._riding_mode:  str          = "—"

        self._build_ui()

        # Timer za ažuriranje tablice (svake 2s)
        self._table_timer = QTimer(self)
        self._table_timer.setInterval(2000)
        self._table_timer.timeout.connect(self._refresh_table)

        # Timer za ažuriranje dashboarda (svake 250ms)
        self._dash_timer = QTimer(self)
        self._dash_timer.setInterval(250)
        self._dash_timer.timeout.connect(self._refresh_dashboard)

    # ── Izgradnja UI-a ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Splitter: (dashboard+tablica) | log
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        # 1. Dashboard
        dash_box = QGroupBox("Live vrijednosti")
        dash_box.setStyleSheet(
            f"QGroupBox {{ color:{ACCENT}; border:1px solid #2A2A32; "
            f"border-radius:6px; margin-top:8px; padding-top:4px; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:10px; }}"
        )
        dash_grid = QGridLayout(dash_box)
        dash_grid.setContentsMargins(8, 12, 8, 8)
        dash_grid.setSpacing(8)

        self._card_rpm     = _DashCard("RPM",           "",    big=True)
        self._card_coolant = _DashCard("Coolant",        "°C",  big=False)
        self._card_hours   = _DashCard("Engine hours",   "h",   big=False)
        self._card_dtc     = _DashCard("DTC count",      "",    big=False)
        self._card_running = _DashCard("Engine state",   "",    big=False)
        self._card_mode    = _DashCard("Riding mode",    "",    big=False)

        dash_grid.addWidget(self._card_rpm,     0, 0, 2, 1)
        dash_grid.addWidget(self._card_coolant, 0, 1)
        dash_grid.addWidget(self._card_hours,   0, 2)
        dash_grid.addWidget(self._card_dtc,     0, 3)
        dash_grid.addWidget(self._card_running, 1, 1)
        dash_grid.addWidget(self._card_mode,    1, 2)
        dash_grid.setColumnStretch(0, 2)
        dash_grid.setColumnStretch(1, 1)
        dash_grid.setColumnStretch(2, 1)
        dash_grid.setColumnStretch(3, 1)

        top_layout.addWidget(dash_box)

        # 2. CAN ID tablica
        tbl_box = QGroupBox("CAN ID statistika")
        tbl_box.setStyleSheet(
            f"QGroupBox {{ color:{ACCENT}; border:1px solid #2A2A32; "
            f"border-radius:6px; margin-top:8px; padding-top:4px; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:10px; }}"
        )
        tbl_layout = QVBoxLayout(tbl_box)
        tbl_layout.setContentsMargins(4, 12, 4, 4)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Hz", "DLC", "Last bytes", "Decoded", "CS", "RC"]
        )
        self._table.setFont(MONO_FONT)
        self._table.setStyleSheet(
            f"QTableWidget {{ background:{BG_WIDGET}; color:{TEXT_PRIMARY}; "
            f"gridline-color:#2A2A32; border:none; }}"
            f"QHeaderView::section {{ background:{BG_PANEL}; color:{ACCENT}; "
            f"border:1px solid #2A2A32; padding:3px; }}"
            f"QTableWidget::item {{ padding:2px 6px; }}"
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        tbl_layout.addWidget(self._table)
        top_layout.addWidget(tbl_box)

        splitter.addWidget(top_widget)

        # 3. Log strip
        log_box = QGroupBox("Log")
        log_box.setStyleSheet(
            f"QGroupBox {{ color:{ACCENT}; border:1px solid #2A2A32; "
            f"border-radius:6px; margin-top:8px; padding-top:4px; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:10px; }}"
        )
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(4, 12, 4, 4)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._log.setFont(MONO_FONT)
        self._log.setStyleSheet(
            f"background:{BG_WIDGET}; color:{TEXT_PRIMARY}; border:none;"
        )
        log_layout.addWidget(self._log)
        splitter.addWidget(log_box)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

    # ── Javne metode (poziva CanLivePanel) ────────────────────────────────────

    def start_timers(self) -> None:
        self._table_timer.start()
        self._dash_timer.start()

    def stop_timers(self) -> None:
        self._table_timer.stop()
        self._dash_timer.stop()

    def clear(self) -> None:
        """Resetuj sva stanja (poziva se pri Stop-u)."""
        self._stats.clear()
        self._msg_count = 0
        self._start_ts  = None
        self._rpm         = None
        self._coolant     = None
        self._hours       = None
        self._dtc_count   = 0
        self._engine_state = "—"
        self._riding_mode  = "—"
        self._table.setRowCount(0)
        self._log.clear()
        self._refresh_dashboard()

    # ── Slot: prima poruku iz CanWorkera ──────────────────────────────────────

    def on_message(self, arb_id: int, ts: float, data: bytes) -> None:
        """Obrađuje svaki primljeni CAN frejm (poziva se iz GUI threada via signal)."""
        if self._start_ts is None:
            self._start_ts = ts
        self._msg_count += 1

        # Ažuriraj statistiku
        self._stats[arb_id].update(ts, data)

        # Dekodiraj
        decoded: dict = {}
        if DECODER_AVAILABLE and CanDecoder is not None:
            try:
                decoded = CanDecoder.decode(arb_id, data)
            except Exception:
                pass

        # Ažuriraj live parametre za dashboard
        self._update_live_params(arb_id, decoded)

        # Log linija
        self._append_log(arb_id, ts, data, decoded)

    # ── Interni update metodi ─────────────────────────────────────────────────

    def _update_live_params(self, arb_id: int, decoded: dict) -> None:
        """Izvuci ključne vrijednosti iz dekodirane poruke."""
        if not decoded.get("decoded"):
            return

        if arb_id == 0x0102:
            # RPM + coolant
            if "rpm" in decoded:
                self._rpm = decoded["rpm"]
            if "coolant_c" in decoded:
                self._coolant = decoded["coolant_c"]

        elif arb_id == 0x0110:
            if "coolant_c" in decoded and self._coolant is None:
                self._coolant = decoded["coolant_c"]

        elif arb_id == 0x0108:
            # Cluster bus RPM (fallback ako 0x0102 nije prisutan)
            if "rpm" in decoded and self._rpm is None:
                self._rpm = decoded["rpm"]

        elif arb_id == 0x012C:
            if "engine_hours" in decoded:
                self._hours = decoded["engine_hours"]

        elif arb_id == 0x0103:
            if "dtc_count" in decoded:
                self._dtc_count = decoded["dtc_count"]
            if "engine_state" in decoded:
                self._engine_state = decoded["engine_state"].upper()

        elif arb_id == 0x013C:
            # Riding mode iz engine flags
            if "sport_mode" in decoded:
                if decoded.get("limp_mode"):
                    self._riding_mode = "LIMP"
                elif decoded.get("eco_mode"):
                    self._riding_mode = "ECO"
                elif decoded.get("sport_mode"):
                    self._riding_mode = "SPORT"
                elif decoded.get("cruise_mode"):
                    self._riding_mode = "CRUISE"
                else:
                    self._riding_mode = "NORMAL"
            if "engine_state" in decoded:
                self._engine_state = decoded["engine_state"].upper()

        elif arb_id == 0x017C:
            if "dtc_count" in decoded:
                self._dtc_count = decoded["dtc_count"]

    def _append_log(self, arb_id: int, ts: float, data: bytes, decoded: dict) -> None:
        """Dodaj liniju u log strip."""
        t = datetime.fromtimestamp(ts).strftime("%H:%M:%S.") + f"{int(ts % 1 * 1000):03d}"
        hex_str = data.hex(' ').upper() if data else ""
        dec_str = _format_decoded(decoded)
        line = f"[{t}] 0x{arb_id:04X}  {len(data)}B  {hex_str:<23}  {dec_str}"
        self._log.appendPlainText(line)

    # ── Timer callbacki ───────────────────────────────────────────────────────

    def _refresh_dashboard(self) -> None:
        """Ažuriraj dashboard tile-ove."""
        # RPM
        if self._rpm is not None:
            self._card_rpm.set_value(int(self._rpm), ACCENT)
        else:
            self._card_rpm.set_value("—", TEXT_DIM)

        # Coolant
        if self._coolant is not None:
            c = GREEN if self._coolant < 95 else (ORANGE if self._coolant < 105 else RED)
            self._card_coolant.set_value(self._coolant, c)
        else:
            self._card_coolant.set_value("—", TEXT_DIM)

        # Engine hours
        if self._hours is not None:
            self._card_hours.set_value(f"{self._hours:.1f}", TEXT_PRIMARY)
        else:
            self._card_hours.set_value("—", TEXT_DIM)

        # DTC count
        if self._dtc_count > 0:
            self._card_dtc.set_value(self._dtc_count, RED)
        else:
            self._card_dtc.set_value("0", GREEN)

        # Engine state
        state_color = {
            "RUNNING": GREEN,
            "CRANKING": YELLOW,
            "LIMP": RED,
            "OFF": TEXT_DIM,
        }.get(self._engine_state.upper(), TEXT_DIM)
        self._card_running.set_value(self._engine_state, state_color)

        # Riding mode
        self._card_mode.set_value(self._riding_mode, ACCENT)

    def _refresh_table(self) -> None:
        """Ažuriraj CAN ID tablicu (svake 2s). Sortabilno po Hz."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._stats))

        for row, (mid, s) in enumerate(
            sorted(self._stats.items(), key=lambda x: -x[1].freq_hz)
        ):
            # ID
            id_item = QTableWidgetItem(f"0x{mid:04X}")
            id_item.setFont(MONO_FONT)

            # Hz
            hz_item = QTableWidgetItem(f"{s.freq_hz:.1f}")
            hz_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            # DLC
            dlc_item = QTableWidgetItem(str(s.dlc))
            dlc_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )

            # Last bytes
            hex_str = s.last_data.hex(' ').upper() if s.last_data else ""
            bytes_item = QTableWidgetItem(hex_str)
            bytes_item.setFont(MONO_FONT)

            # Decoded
            dec_str = ""
            if DECODER_AVAILABLE and CanDecoder is not None and s.last_data:
                try:
                    d = CanDecoder.decode(mid, s.last_data)
                    dec_str = _format_decoded(d)
                except Exception:
                    pass
            decoded_item = QTableWidgetItem(dec_str)

            # CS — checksum error count
            cs_str   = "ok" if s.checksum_errors == 0 else f"!{s.checksum_errors}"
            cs_item  = QTableWidgetItem(cs_str)
            cs_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )

            # RC — rolling counter jump count
            rc_str  = "0" if s.rolling_ctr_jumps == 0 else f"!{s.rolling_ctr_jumps}"
            rc_item = QTableWidgetItem(rc_str)
            rc_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )

            # Boja reda
            cs_ok  = s.checksum_errors == 0
            rc_ok  = s.rolling_ctr_jumps == 0

            if not cs_ok:
                row_color = QColor(ORANGE)
            elif not rc_ok:
                row_color = QColor(RED)
            else:
                row_color = QColor(GREEN)

            row_color.setAlpha(40)  # blagi fill
            brush = QBrush(row_color)

            items = [id_item, hz_item, dlc_item, bytes_item,
                     decoded_item, cs_item, rc_item]
            for col, item in enumerate(items):
                item.setBackground(brush)
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)


# ─── CanLivePanel — container s kontrolama ───────────────────────────────────

class CanLivePanel(QWidget):
    """
    Wrapper oko CanLiveWidget s kontrolama:
      - ComboBox: bitrate (500kbps/250kbps)
      - ComboBox: kanal (0/1)
      - Gumb: Start / Stop
      - Status label
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN}; color:{TEXT_PRIMARY};")

        self._worker:  CanWorker | None = None
        self._running  = False
        self._msg_count = 0
        self._rate_ts:  float = 0.0
        self._rate_cnt: int   = 0

        self._build_ui()
        self._check_availability()

    # ── Izgradnja UI-a ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(
            f"background:{BG_PANEL}; border-bottom:1px solid #2A2A32;"
        )
        toolbar.setFixedHeight(44)
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 4, 8, 4)
        tb_lay.setSpacing(8)

        # Bitrate
        tb_lay.addWidget(QLabel("Bitrate:"))
        self._bitrate_combo = QComboBox()
        self._bitrate_combo.addItem("500 kbps — Diagnostic", 500_000)
        self._bitrate_combo.addItem("250 kbps — Cluster",    250_000)
        self._bitrate_combo.setStyleSheet(
            f"background:{BG_WIDGET}; color:{TEXT_PRIMARY}; border:1px solid #2A2A32;"
            f" border-radius:4px; padding:2px 6px;"
        )
        tb_lay.addWidget(self._bitrate_combo)

        # Kanal
        tb_lay.addWidget(QLabel("Kanal:"))
        self._channel_combo = QComboBox()
        self._channel_combo.addItem("0", 0)
        self._channel_combo.addItem("1", 1)
        self._channel_combo.setStyleSheet(
            f"background:{BG_WIDGET}; color:{TEXT_PRIMARY}; border:1px solid #2A2A32;"
            f" border-radius:4px; padding:2px 6px;"
        )
        tb_lay.addWidget(self._channel_combo)

        tb_lay.addSpacing(16)

        # Start/Stop gumb
        self._btn = QPushButton("Start")
        self._btn.setFixedWidth(80)
        self._btn.setStyleSheet(
            f"QPushButton {{ background:{GREEN}; color:#000; border-radius:4px; "
            f"padding:4px 12px; font-weight:bold; }}"
            f"QPushButton:disabled {{ background:#333; color:#666; }}"
            f"QPushButton:hover {{ background:#66BB6A; }}"
        )
        self._btn.clicked.connect(self._toggle)
        tb_lay.addWidget(self._btn)

        tb_lay.addSpacing(16)

        # Status label
        self._status_lbl = QLabel("Nije spojeno")
        self._status_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        tb_lay.addWidget(self._status_lbl)

        tb_lay.addStretch()

        # Msg/s label
        self._rate_lbl = QLabel("")
        self._rate_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:9pt;")
        tb_lay.addWidget(self._rate_lbl)

        root.addWidget(toolbar)

        # Glavni widget
        self._live = CanLiveWidget(self)
        root.addWidget(self._live)

        # Rate timer (svake sekunde)
        self._rate_timer = QTimer(self)
        self._rate_timer.setInterval(1000)
        self._rate_timer.timeout.connect(self._update_rate)

    # ── Provjera dostupnosti ──────────────────────────────────────────────────

    def _check_availability(self) -> None:
        if not CAN_AVAILABLE:
            self._status_lbl.setText("python-can nije instaliran (pip install python-can)")
            self._status_lbl.setStyleSheet(f"color:{ORANGE};")
            self._btn.setEnabled(False)
            return

        if not DECODER_AVAILABLE:
            self._status_lbl.setText("Upozorenje: CanDecoder nije dostupan")
            self._status_lbl.setStyleSheet(f"color:{YELLOW};")

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _toggle(self) -> None:
        if self._running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        bitrate = self._bitrate_combo.currentData()
        channel = self._channel_combo.currentData()

        self._live.clear()
        self._msg_count = 0
        self._rate_cnt  = 0
        self._rate_ts   = time.monotonic()

        self._worker = CanWorker(bitrate=bitrate, channel=channel, parent=self)
        self._worker.message_received.connect(self._on_message)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)

        self._worker.start()
        self._running = True
        self._live.start_timers()
        self._rate_timer.start()

        self._btn.setText("Stop")
        self._btn.setStyleSheet(
            f"QPushButton {{ background:{RED}; color:#fff; border-radius:4px; "
            f"padding:4px 12px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:#EF5350; }}"
        )
        self._status_lbl.setText(f"Snifam...  {bitrate//1000} kbps  ch{channel}")
        self._status_lbl.setStyleSheet(f"color:{GREEN};")

        # Onemogući kontrole za vrijeme rada
        self._bitrate_combo.setEnabled(False)
        self._channel_combo.setEnabled(False)

    def _stop(self) -> None:
        self._running = False
        self._live.stop_timers()
        self._rate_timer.stop()

        if self._worker:
            self._worker.stop()
            self._worker = None

        self._btn.setText("Start")
        self._btn.setStyleSheet(
            f"QPushButton {{ background:{GREEN}; color:#000; border-radius:4px; "
            f"padding:4px 12px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:#66BB6A; }}"
        )
        self._status_lbl.setText("Zaustavljeno")
        self._status_lbl.setStyleSheet(f"color:{TEXT_DIM};")
        self._rate_lbl.setText("")
        self._bitrate_combo.setEnabled(True)
        self._channel_combo.setEnabled(True)

    # ── Signali iz workera ────────────────────────────────────────────────────

    def _on_message(self, arb_id: int, ts: float, data: bytes) -> None:
        self._msg_count += 1
        self._rate_cnt  += 1
        self._live.on_message(arb_id, ts, data)

    def _on_error(self, msg: str) -> None:
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{RED};")
        self._stop()

    def _on_worker_done(self) -> None:
        """Worker thread završio (normalno ili greškom)."""
        if self._running:
            self._stop()

    # ── Rate label update ─────────────────────────────────────────────────────

    def _update_rate(self) -> None:
        now   = time.monotonic()
        dt    = now - self._rate_ts
        rate  = self._rate_cnt / dt if dt > 0 else 0.0
        self._rate_lbl.setText(f"{rate:.0f} msg/s  |  ukupno: {self._msg_count}")
        self._rate_ts  = now
        self._rate_cnt = 0

    # ── Cleanup pri zatvaranju ────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._running:
            self._stop()
        super().closeEvent(event)
