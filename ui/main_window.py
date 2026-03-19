"""
ME17Suite — Main Window (PyQt6)
Bosch ME17.8.5 by Rotax — ECU Binary Editor

Layout:
  Menubar | Toolbar
  ┌──────────────┬─────────────────────────┬──────────────────┐
  │  Map Library │   Map Table             │  [Cell|Map|ECU]  │
  │  search+tree │   RPM×Load axes         │   tabs           │
  │              │   heat-map colors       │                  │
  │              ├─────────────────────────┤                  │
  │              │  Hex (taller)           │                  │
  │              ├─────────────────────────┤                  │
  │              │  Log (shorter)          │                  │
  └──────────────┴─────────────────────────┴──────────────────┘
  StatusBar
"""

import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar, QFileDialog,
    QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QMessageBox,
    QProgressBar, QFrame, QPushButton, QHeaderView, QScrollArea,
    QLineEdit, QToolBar, QTextEdit, QGroupBox, QSizePolicy,
    QListWidget, QListWidgetItem, QSlider, QDialog,
    QStackedWidget, QMenu, QToolButton, QComboBox, QDoubleSpinBox,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QBrush, QAction, QFont, QKeySequence, QIcon, QPixmap, QPainter

from core.engine import ME17Engine
from core.map_finder import MapFinder, FoundMap, MapDef
from core.map_editor import MapEditor, EditResult
from core.checksum import ChecksumEngine
from core.dtc import DtcEngine, DTC_REGISTRY, DtcStatus
from core.safety_validator import SafetyValidator, Level as SvLevel
from core.map_differ import MapDiffer
from ui.calculator_widget import CalculatorWidget
from ui.diff_viewer import MapDiffWidget
from ui.eeprom_widget import EepromWidget
from ui.can_network_widget import CanNetworkWidget


# ─── Stylesheet ───────────────────────────────────────────────────────────────

STYLESHEET = """
* {
    font-family: "IBM Plex Sans", "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #C8C8D0;
}

QMainWindow, QWidget {
    background-color: #111113;
    color: #C8C8D0;
}

/* ── MENUBAR ── */
QMenuBar {
    background: #1c2b4a;
    color: rgba(255,255,255,0.75);
    border-bottom: 1px solid #2A2A32;
    padding: 2px 4px;
    font-size: 13px;
}
QMenuBar::item {
    padding: 4px 10px;
    border-radius: 3px;
    background: transparent;
}
QMenuBar::item:selected { background: rgba(255,255,255,0.12); color: #ffffff; }
QMenu {
    background: #1C1C1F;
    color: #C8C8D0;
    border: 1px solid #3A3A48;
    padding: 3px 0;
}
QMenu::item { padding: 5px 20px 5px 12px; }
QMenu::item:selected { background: #1A2F4A; color: #4FC3F7; }
QMenu::separator { height: 1px; background: #2A2A32; margin: 3px 0; }

/* ── TOOLBAR ── */
QToolBar {
    background: #1C1C1F;
    border-bottom: 2px solid #2A2A32;
    padding: 4px 8px;
    spacing: 3px;
}
QToolBar::separator { width: 1px; background: #2A2A32; margin: 3px 6px; }
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 10px;
    color: #808090;
    font-size: 12px;
}
QToolButton:hover { background: #111113; border-color: #2A2A32; color: #C8C8D0; }
QToolButton:pressed { background: #141418; }
QToolButton:checked { background: #1A2F4A; border-color: #4FC3F7; color: #4FC3F7; }

/* ── GUMBI ── */
QPushButton {
    background: #1C1C1F;
    border: 1px solid #2A2A32;
    border-radius: 3px;
    padding: 4px 10px;
    color: #808090;
    font-size: 12px;
    min-height: 24px;
}
QPushButton:hover { background: #111113; border-color: #3A3A48; color: #C8C8D0; }
QPushButton:pressed { background: #141418; }
QPushButton:disabled { background: #141418; color: #505060; border-color: #2A2A32; }
QPushButton#btn_primary {
    background: #4FC3F7;
    border-color: #4FC3F7;
    color: #111113;
    font-weight: bold;
}
QPushButton#btn_primary:hover { background: #29B6F6; border-color: #29B6F6; }
QPushButton#primary {
    background: #4FC3F7;
    border-color: #4FC3F7;
    color: #111113;
    font-weight: bold;
}
QPushButton#primary:hover { background: #29B6F6; border-color: #29B6F6; }
QPushButton#btn_success { background: #1a3a2a; border-color: #4CAF50; color: #4CAF50; }
QPushButton#btn_danger { background: #1C1C1F; border-color: #2A2A32; color: #EF5350; }
QPushButton#btn_danger:hover { background: #2a1010; border-color: #EF5350; }

/* ── TREE WIDGET ── */
QTreeWidget {
    background: #1C1C1F;
    border: none;
    color: #C8C8D0;
    font-size: 12px;
    outline: none;
    show-decoration-selected: 1;
}
QTreeWidget::item { padding: 4px 4px; border-left: 3px solid transparent; }
QTreeWidget::item:hover { background: #111113; }
QTreeWidget::item:selected {
    background: #1A2F4A;
    color: #4FC3F7;
    border-left: 3px solid #4FC3F7;
}
QTreeWidget::branch { background: #1C1C1F; }

/* ── TABLICA ── */
QTableWidget {
    background: #111113;
    border: none;
    gridline-color: #1C1C1F;
    color: #C8C8D0;
    font-family: "IBM Plex Mono", "Consolas", "Courier New", monospace;
    font-size: 11px;
    selection-background-color: #1A2F4A;
}
QTableWidget::item { padding: 2px 4px; border: none; }
QTableWidget::item:selected { background: #1A2F4A; color: #4FC3F7; }
QHeaderView::section {
    background: #141418;
    color: #505060;
    padding: 3px 5px;
    border: none;
    border-right: 1px solid #2A2A32;
    border-bottom: 1px solid #2A2A32;
    font-family: "IBM Plex Mono", "Consolas", monospace;
    font-size: 10px;
    font-weight: normal;
}

/* ── SCROLL BAROVI ── */
QScrollBar:vertical { background: #141418; width: 8px; border: none; }
QScrollBar::handle:vertical {
    background: #2A2A32; border-radius: 4px; min-height: 20px; margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #3A3A48; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #141418; height: 8px; border: none; }
QScrollBar::handle:horizontal {
    background: #2A2A32; border-radius: 4px; min-width: 20px; margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #3A3A48; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── TAB WIDGET ── */
QTabWidget::pane { border: none; border-top: 1px solid #2A2A32; background: #1C1C1F; }
QTabBar::tab {
    background: #141418;
    color: #808090;
    padding: 5px 16px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-size: 12px;
}
QTabBar::tab:hover { color: #C8C8D0; background: rgba(255,255,255,0.04); }
QTabBar::tab:selected { background: #1C1C1F; color: #4FC3F7; border-color: #2A2A32; font-weight: 500; }

/* ── LINE EDIT ── */
QLineEdit {
    background: #111113;
    border: 1px solid #2A2A32;
    border-radius: 3px;
    padding: 4px 8px;
    color: #C8C8D0;
    font-size: 12px;
    selection-background-color: #1A2F4A;
}
QLineEdit:focus { border-color: #4FC3F7; background: #141418; }
QLineEdit::placeholder { color: #505060; }

/* ── SPLITTER ── */
QSplitter::handle { background: #2A2A32; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* ── STATUS BAR ── */
QStatusBar {
    background: #1c2b4a;
    color: rgba(255,255,255,0.85);
    font-family: "IBM Plex Mono", "Consolas", monospace;
    font-size: 11px;
    border-top: none;
}
QStatusBar::item { border-right: 1px solid rgba(255,255,255,0.1); padding: 0 12px; }
QStatusBar QLabel { color: rgba(255,255,255,0.85); font-family: "IBM Plex Mono", "Consolas", monospace; font-size: 11px; }

/* ── LABELE ── */
QLabel#lbl_map_title {
    font-family: "IBM Plex Mono", "Consolas", monospace; font-size: 13px; font-weight: bold; color: #4FC3F7;
}
QLabel#lbl_section {
    font-size: 10px; font-weight: bold; letter-spacing: 1.5px; color: #808090; text-transform: uppercase;
}
QLabel#lbl_value_big {
    font-family: "IBM Plex Mono", "Consolas", monospace; font-size: 32px; color: #4FC3F7; font-weight: bold;
}
QLabel#lbl_addr { font-family: "IBM Plex Mono", "Consolas", monospace; font-size: 11px; color: #505060; }
QLabel#lbl_ok   { color: #4CAF50; font-weight: bold; }
QLabel#lbl_warn { color: #FFB74D; font-weight: bold; }
QLabel#lbl_error { color: #EF5350; font-weight: bold; }

/* ── GROUP BOX ── */
QGroupBox {
    border: 1px solid #2A2A32;
    border-radius: 4px;
    margin-top: 8px;
    padding: 8px;
    color: #808090;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1px;
    background: #1C1C1F;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    background: #1C1C1F;
}

/* ── COMBO BOX ── */
QComboBox {
    background: #111113; border: 1px solid #2A2A32; border-radius: 3px;
    padding: 4px 8px; color: #C8C8D0; font-size: 12px; min-height: 24px;
}
QComboBox:hover { border-color: #3A3A48; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #1C1C1F; border: 1px solid #3A3A48;
    selection-background-color: #1A2F4A; color: #C8C8D0;
}

/* ── LIST WIDGET ── */
QListWidget {
    background: #1C1C1F; border: none; color: #C8C8D0;
    font-family: "IBM Plex Mono", "Consolas", monospace; font-size: 12px; outline: none;
}
QListWidget::item { padding: 4px 8px; border-bottom: 1px solid #2A2A32; }
QListWidget::item:hover { background: #111113; }
QListWidget::item:selected { background: #1A2F4A; color: #4FC3F7; }

/* ── TOOLTIP ── */
QToolTip {
    background: #1C1C1F; color: #C8C8D0; border: 1px solid #3A3A48;
    padding: 4px 8px; font-size: 11px; border-radius: 3px;
}

/* ── MESSAGE BOX ── */
QMessageBox { background: #1C1C1F; color: #C8C8D0; }

/* ── PROGRESS BAR ── */
QProgressBar {
    background: #141418; border: 1px solid #2A2A32; border-radius: 3px;
    height: 4px; text-align: center; color: transparent;
}
QProgressBar::chunk { background: #4FC3F7; border-radius: 3px; }
"""


# ─── Category color map ───────────────────────────────────────────────────────

CATEGORY_COLORS: dict[str, str] = {
    "injection":   "#4ec9b0",   # teal
    "ignition":    "#f97316",   # orange
    "torque":      "#a855f7",   # purple
    "lambda":      "#22d3ee",   # cyan
    "rpm_limiter": "#ef4444",   # red
    "axis":        "#6b7280",   # gray
    "misc":        "#84cc16",   # lime
    "dtc":         "#f59e0b",   # amber
}

# ─── SW variant accent colors ─────────────────────────────────────────────────

def _sw_accent_color(sw_id: str) -> str:
    """Return accent bar color for the given SW ID."""
    if not sw_id:
        return "#333333"
    if "066726" in sw_id or "054296" in sw_id or "040039" in sw_id:
        return "#f97316"   # 300hp SC — orange
    if "053727" in sw_id:
        return "#f59e0b"   # 230hp SC — amber
    if "053729" in sw_id:
        return "#4ec9b0"   # 130/170hp NA — teal
    if "039116" in sw_id or "011328" in sw_id or "544876" in sw_id:
        return "#a855f7"   # Spark 900 — purple
    if "053774" in sw_id:
        return "#22d3ee"   # GTI 90 — cyan
    if "025752" in sw_id or "040008" in sw_id or "040962" in sw_id:
        return "#84cc16"   # GTI 155 — lime
    return "#333333"


def _sw_badge_color(sw_id: str) -> str:
    """Return bold label color for the SW ID badge in status bar."""
    col = _sw_accent_color(sw_id)
    return col if col != "#333333" else "#9cdcfe"


def _category_icon(category: str) -> QIcon:
    """Return a 12×12 filled circle QIcon in the category color."""
    color_hex = CATEGORY_COLORS.get(category, "#888888")
    pix = QPixmap(12, 12)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, 10, 10)
    painter.end()
    return QIcon(pix)


# ─── Category-aware heatmap palettes ──────────────────────────────────────────

# Each palette: list of (bg_QColor, fg_QColor) from coldest to hottest
_PAL_INJECTION = [
    (QColor("#0d0d1a"), QColor("#9999cc")),
    (QColor("#1a0d2e"), QColor("#b07fcc")),
    (QColor("#2e0d2e"), QColor("#cc7fcc")),
    (QColor("#3e1010"), QColor("#e08080")),
    (QColor("#5a1a10"), QColor("#f09070")),
    (QColor("#7a2008"), QColor("#f0b060")),
    (QColor("#963010"), QColor("#f5c840")),
    (QColor("#b04010"), QColor("#ffd60a")),
    (QColor("#c85010"), QColor("#ffe060")),
]

_PAL_IGNITION = [
    (QColor("#0d0d2e"), QColor("#8888cc")),
    (QColor("#0d1a3e"), QColor("#8899dd")),
    (QColor("#0d2a5a"), QColor("#7ab0ee")),
    (QColor("#0d3a70"), QColor("#7ac0f8")),
    (QColor("#1a4a80"), QColor("#9cd4f8")),
    (QColor("#2a5a90"), QColor("#c0e0f8")),
    (QColor("#3a6aa0"), QColor("#d8ecf8")),
    (QColor("#4a80c0"), QColor("#eef6fc")),
    (QColor("#6090e0"), QColor("#f8fafd")),
]

_PAL_TORQUE = [
    (QColor("#0d1a0d"), QColor("#80b080")),
    (QColor("#0d2a0d"), QColor("#80c880")),
    (QColor("#0d3a0d"), QColor("#80e080")),
    (QColor("#1a4a10"), QColor("#a0f090")),
    (QColor("#2a5a10"), QColor("#c0f080")),
    (QColor("#4a6a10"), QColor("#d8f060")),
    (QColor("#6a7010"), QColor("#f0e840")),
    (QColor("#8a6808"), QColor("#f8c820")),
    (QColor("#a06010"), QColor("#f8a820")),
]

_PAL_LAMBDA = [
    (QColor("#0d1a2e"), QColor("#6699bb")),
    (QColor("#0d2240"), QColor("#55aacc")),
    (QColor("#0d2e52"), QColor("#44bbdd")),
    (QColor("#0d3a64"), QColor("#33ccee")),
    (QColor("#0d4876"), QColor("#22ddee")),
    (QColor("#0d5588"), QColor("#44eef0")),
    (QColor("#0d6490"), QColor("#77eff4")),
    (QColor("#0d70a0"), QColor("#aaf0f8")),
    (QColor("#0d80b8"), QColor("#caf0f8")),
]

_PAL_DEFAULT = [
    (QColor("#1c3461"), QColor("#7eb8f7")),
    (QColor("#1a4a6a"), QColor("#7ec8f7")),
    (QColor("#0d6b5c"), QColor("#7ef7e0")),
    (QColor("#1a6b2a"), QColor("#7ef79e")),
    (QColor("#4a6b0a"), QColor("#d0f77e")),
    (QColor("#7a6000"), QColor("#f7d87e")),
    (QColor("#8a3800"), QColor("#f7b07e")),
    (QColor("#8a1800"), QColor("#f77e7e")),
    (QColor("#7a0020"), QColor("#f77ea8")),
]

_CATEGORY_PALETTES: dict[str, list] = {
    "injection":   _PAL_INJECTION,
    "ignition":    _PAL_IGNITION,
    "torque":      _PAL_TORQUE,
    "lambda":      _PAL_LAMBDA,
}


def _cell_colors_cat(raw_val: int, raw_min: int, raw_max: int,
                     category: str = "") -> tuple[QColor, QColor]:
    """Return (bg, fg) QColor pair using category-specific heatmap palette."""
    palette = _CATEGORY_PALETTES.get(category, _PAL_DEFAULT)
    p = (raw_val - raw_min) / max(raw_max - raw_min, 1)
    idx = min(int(p * len(palette)), len(palette) - 1)
    return palette[idx]


# ─── Undo/Redo komanda ────────────────────────────────────────────────────────

@dataclass
class UndoCmd:
    fm:      FoundMap
    row:     int
    col:     int
    old_raw: int
    new_raw: int


# ─── Toolbar gumb helper ──────────────────────────────────────────────────────

def _btn(label: str, obj: str = "") -> QPushButton:
    b = QPushButton(label)
    b.setFixedHeight(26)
    if obj: b.setObjectName(obj)
    return b


# ─── Map Library (lijevi sidebar) ─────────────────────────────────────────────

class MapLibraryPanel(QWidget):
    map_selected = pyqtSignal(object)

    CATEGORIES = {
        "ignition":    ("⚡ Ignition",    "#9cdcfe"),
        "injection":   ("💉 Injection",   "#9cdcfe"),
        "torque":      ("⚙ Torque",       "#9cdcfe"),
        "lambda":      ("🧪 Lambda / AFR","#9cdcfe"),
        "rpm_limiter": ("🔴 Rev Limiter", "#9cdcfe"),
        "axis":        ("📊 RPM Axes",    "#9cdcfe"),
        "misc":        ("  Other",         "#9cdcfe"),
    }

    # SW variant filter opcije — (label, sw_id_substring ili "all")
    SW_FILTERS = [
        ("Sve varijante",       "all"),
        ("300hp SC",            "066726"),
        ("230hp SC",            "053727"),
        ("130/170hp NA",        "053729"),
        ("GTI 90",              "053774"),
        ("Spark 900",           "039116"),
        ("GTI 130/155",         "025752"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self._all: list[FoundMap] = []
        self._compare: list[FoundMap] = []
        self._sw_filter = "all"

        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        self._hdr = QLabel("  MAP LIBRARY")
        self._hdr.setStyleSheet(
            "background:#141418; color:#808090; font-size:10px; font-weight:bold; "
            "padding:6px 10px; border-bottom:1px solid #2A2A32; letter-spacing:1.5px;"
        )
        lo.addWidget(self._hdr)

        # ── SW variant filter dropdown ────────────────────────────────────────
        self._sw_combo = QComboBox()
        self._sw_combo.setFixedHeight(28)
        self._sw_combo.setStyleSheet(
            "background:#111113; border:none; border-bottom:1px solid #2A2A32; "
            "border-radius:0; padding:2px 10px; color:#4FC3F7; font-size:12px;"
        )
        for label, _ in self.SW_FILTERS:
            self._sw_combo.addItem(label)
        self._sw_combo.currentIndexChanged.connect(self._on_sw_filter_changed)
        lo.addWidget(self._sw_combo)

        self.search = QLineEdit()
        self.search.setPlaceholderText("  Pretraži mape...")
        self.search.setFixedHeight(30)
        self.search.setObjectName("search_maps")
        self.search.setStyleSheet(
            "background:#111113; border:none; border-bottom:1px solid #2A2A32; "
            "border-radius:0; padding:4px 10px; color:#C8C8D0; font-size:12px;"
        )
        self.search.textChanged.connect(self._filter)
        lo.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        self.tree.itemClicked.connect(self._click)
        lo.addWidget(self.tree, 1)

    def populate(self, maps: list[FoundMap], compare: list[FoundMap] | None = None):
        self._all = maps
        self._compare = compare or []
        n = len(maps)
        self._hdr.setText(f"  MAP LIBRARY — {n}")
        self._render(self._filtered_maps())

    def mark_diff(self, compare: list[FoundMap]):
        """Označi mape koje se razlikuju od fajla 2 (žuta boja stavke)."""
        self._compare = compare
        self._render(self._filtered_maps())

    def auto_set_sw_filter(self, sw_id: str):
        """Automatski odaberi odgovarajući SW filter na osnovu učitanog sw_id."""
        for i, (label, key) in enumerate(self.SW_FILTERS):
            if key != "all" and key in sw_id:
                self._sw_combo.setCurrentIndex(i)
                return
        self._sw_combo.setCurrentIndex(0)

    def _on_sw_filter_changed(self, idx: int):
        _, key = self.SW_FILTERS[idx]
        self._sw_filter = key
        self._render(self._filtered_maps())

    def _filtered_maps(self) -> list[FoundMap]:
        """Vrati mape filtrirane po SW varijanti i search tekstu."""
        maps = self._all
        if self._sw_filter != "all":
            maps = [m for m in maps if self._sw_filter in m.sw_id]
        t = self.search.text()
        if t:
            maps = [m for m in maps if t.lower() in m.defn.name.lower()]
        return maps

    def _filter(self, t: str):
        self._render(self._filtered_maps())

    def _render(self, maps: list[FoundMap]):
        self.tree.clear()
        cats = {}
        for key, (label, color) in self.CATEGORIES.items():
            it = QTreeWidgetItem(self.tree, [label])
            it.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            it.setForeground(0, QBrush(QColor("#808090")))
            it.setSizeHint(0, QSize(0, 26))
            it.setExpanded(True)
            cats[key] = it
        # Indeks mapa iz fajla 2 po imenu za brzu usporedbu
        cmp_by_name = {m.defn.name: m for m in self._compare}

        for fm in maps:
            dims = f"{fm.defn.rows}×{fm.defn.cols}" if fm.defn.rows > 1 else "scalar"
            ch = QTreeWidgetItem(cats.get(fm.defn.category, cats["misc"]))

            # Provjeri razlikuje li se od fajla 2
            fm2 = cmp_by_name.get(fm.defn.name)
            is_diff = fm2 is not None and fm.data != fm2.data

            name_txt = f"  {'● ' if is_diff else ''}{fm.defn.name}"
            ch.setText(0, name_txt)
            ch.setFont(0, QFont("Segoe UI", 12))
            # Category color badge icon (12×12 filled circle)
            ch.setIcon(0, _category_icon(fm.defn.category))
            if is_diff:
                ch.setForeground(0, QBrush(QColor("#FFB74D")))   # žuta = razlika
                ch.setToolTip(0, f"0x{fm.address:06X}  {dims}  {fm.defn.unit}\n"
                                  f"[RAZLIKA vs Fajl 2]\n{fm.defn.description}")
            else:
                ch.setForeground(0, QBrush(QColor("#C8C8D0")))
                ch.setToolTip(0, f"0x{fm.address:06X}  {dims}  {fm.defn.unit}\n{fm.defn.description}")
            ch.setSizeHint(0, QSize(0, 24))
            ch.setData(0, Qt.ItemDataRole.UserRole, fm)
        for it in cats.values():
            it.setHidden(it.childCount() == 0)

    def _click(self, item: QTreeWidgetItem):
        fm = item.data(0, Qt.ItemDataRole.UserRole)
        if fm: self.map_selected.emit(fm)


# ─── DTC Sidebar Panel ────────────────────────────────────────────────────────

class DtcSidebarPanel(QWidget):
    dtc_selected = pyqtSignal(int)

    # Top-level kategorije: (slovo, raspon_lo, raspon_hi, boja)
    _CAT_GROUPS = [
        ("P — Powertrain", 0x0000, 0x3FFF, "#f48771"),
        ("C — Chassis",    0x4000, 0x7FFF, "#9cdcfe"),
        ("B — Body",       0x8000, 0xBFFF, "#e5c07b"),
        ("U — Network",    0xC000, 0xFFFF, "#a855f7"),
    ]
    # Podgrupe unutar kategorije: (label, second_digit, boja)
    _SUB_LABELS = {
        0: "— Standardni (OEM/SAE)",
        1: "— Proizvođač (BRP/Bosch)",
        2: "— Standardni prošireni",
        3: "— Dostupno",
    }
    _COLOR_ACTIVE = "#4CAF50"   # zelena  — DTC aktivan (monitoring ON)
    _COLOR_OFF    = "#EF5350"   # crvena  — DTC isključen (OFF)
    _COLOR_NONE   = "#505060"   # siva    — nije učitan fajl

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dtc_eng = None
        self._all_items: list[tuple[int, QTreeWidgetItem]] = []

        lo = QVBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)

        hdr = QLabel("  DTC LISTA")
        hdr.setStyleSheet(
            "background:#141418; color:#808090; font-size:10px; font-weight:bold; "
            "padding:6px 10px; border-bottom:1px solid #2A2A32; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr)

        self._search = QLineEdit()
        self._search.setPlaceholderText("  Filtriraj DTC...")
        self._search.setFixedHeight(30)
        self._search.setStyleSheet(
            "background:#111113; border:none; border-bottom:1px solid #2A2A32; "
            "border-radius:0; padding:4px 10px; color:#C8C8D0; font-size:12px;"
        )
        self._search.textChanged.connect(self._filter)
        lo.addWidget(self._search)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.itemClicked.connect(self._click)
        lo.addWidget(self.tree, 1)

        self._build_tree()

    def _build_tree(self):
        self.tree.clear()
        self._all_items.clear()

        # Grupiraj kodove: cat_letter → sub_digit → [code]
        from collections import defaultdict
        buckets: dict[tuple[int,int], list] = defaultdict(list)
        for code, defn in sorted(DTC_REGISTRY.items()):
            cat_idx  = (code >> 14) & 3   # 0=P,1=C,2=B,3=U
            sub_digit = (code >> 12) & 3   # 0,1,2,3
            buckets[(cat_idx, sub_digit)].append((code, defn))

        for cat_idx, (cat_label, lo_c, hi_c, cat_color) in enumerate(self._CAT_GROUPS):
            # Provjeri ima li kodova u ovoj kategoriji
            has_any = any(k[0] == cat_idx for k in buckets)
            if not has_any:
                continue

            cat_item = QTreeWidgetItem(self.tree, [cat_label])
            cat_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            cat_item.setForeground(0, QBrush(QColor(cat_color)))
            cat_item.setSizeHint(0, QSize(0, 26))
            cat_item.setExpanded(True)

            for sub_digit in range(4):
                entries = buckets.get((cat_idx, sub_digit), [])
                if not entries:
                    continue

                # Subgrupa npr. "P0 — Standardni (OEM/SAE)"
                cat_char = "PCBU"[cat_idx]
                sub_label = f"  {cat_char}{sub_digit}xxx {self._SUB_LABELS.get(sub_digit, '')}"
                sub_item = QTreeWidgetItem(cat_item, [sub_label])
                sub_item.setFont(0, QFont("Segoe UI", 9))
                sub_item.setForeground(0, QBrush(QColor("#505060")))
                sub_item.setSizeHint(0, QSize(0, 22))
                sub_item.setExpanded(True)

                for code, defn in entries:
                    ch = QTreeWidgetItem(sub_item, [f"    {defn.p_code}"])
                    ch.setFont(0, QFont("Consolas", 11))
                    ch.setSizeHint(0, QSize(0, 20))
                    ch.setForeground(0, QBrush(QColor(self._COLOR_NONE)))
                    ch.setData(0, Qt.ItemDataRole.UserRole, code)
                    self._all_items.append((code, ch))

    def set_engine(self, dtc_eng):
        self._dtc_eng = dtc_eng
        self.refresh_status()

    def refresh_status(self):
        for code, ch in self._all_items:
            if self._dtc_eng:
                status = self._dtc_eng.get_status(code)
                color = self._COLOR_OFF if (status and status.is_off) else self._COLOR_ACTIVE
            else:
                color = self._COLOR_NONE
            ch.setForeground(0, QBrush(QColor(color)))

    def refresh_one(self, code: int, is_off: bool):
        color = self._COLOR_OFF if is_off else self._COLOR_ACTIVE
        for c, ch in self._all_items:
            if c == code:
                ch.setForeground(0, QBrush(QColor(color)))
                break

    def _filter(self, txt: str):
        for code, ch in self._all_items:
            defn = DTC_REGISTRY.get(code)
            visible = (not txt or
                       txt.lower() in (defn.p_code if defn else "").lower() or
                       txt.lower() in (defn.name if defn else "").lower())
            ch.setHidden(not visible)
        # Sakrij prazne podgrupe i kategorije
        for i in range(self.tree.topLevelItemCount()):
            cat = self.tree.topLevelItem(i)
            cat_empty = True
            for j in range(cat.childCount()):
                sub = cat.child(j)
                sub_empty = all(sub.child(k).isHidden() for k in range(sub.childCount()))
                sub.setHidden(sub_empty)
                if not sub_empty:
                    cat_empty = False
            cat.setHidden(cat_empty)

    def _click(self, item: QTreeWidgetItem):
        code = item.data(0, Qt.ItemDataRole.UserRole)
        if code is not None:
            self.dtc_selected.emit(code)


# ─── EEPROM Sidebar Panel ─────────────────────────────────────────────────────

class EepromSidebarPanel(QWidget):
    entry_selected = pyqtSignal(str)  # emits entry key/name

    _ENTRIES = [
        ("ODO — kilometre",         "odo",      "Ukupni prijeđeni put"),
        ("Sati motora",             "hours",    "Sati rada motora"),
        ("HW tip / model",          "hw_type",  "Hardware tip ECU-a (063/064)"),
        ("Serijska tvornice",       "serial",   "Serijski broj ECU-a"),
        ("Boot checksums",          "boot_cs",  "BOOT checksum blokovi"),
        ("Nadmorska visina",        "altitude", "Kompenzacija nadmorske visine"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        lo = QVBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)

        hdr = QLabel("  EEPROM")
        hdr.setStyleSheet(
            "background:#141418; color:#808090; font-size:10px; font-weight:bold; "
            "padding:6px 10px; border-bottom:1px solid #2A2A32; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr)

        self._list = QListWidget()
        self._list.setFont(QFont("Consolas", 12))
        self._list.setStyleSheet("background:#1C1C1F; border:none;")
        self._list.itemClicked.connect(self._click)
        lo.addWidget(self._list, 1)

        for label, key, desc in self._ENTRIES:
            item = QListWidgetItem(f"  {label}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(desc)
            item.setForeground(QBrush(QColor("#4FC3F7")))
            self._list.addItem(item)

    def _click(self, item: QListWidgetItem):
        key = item.data(Qt.ItemDataRole.UserRole)
        if key:
            self.entry_selected.emit(key)


# ─── CAN Sidebar Panel ────────────────────────────────────────────────────────

class CanSidebarPanel(QWidget):
    id_selected = pyqtSignal(int)   # emits CAN ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ids: list[tuple[int, str]] = []

        lo = QVBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)

        hdr = QLabel("  CAN ID-ovi")
        hdr.setStyleSheet(
            "background:#141418; color:#808090; font-size:10px; font-weight:bold; "
            "padding:6px 10px; border-bottom:1px solid #2A2A32; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr)

        self._search = QLineEdit()
        self._search.setPlaceholderText("  Filtriraj...")
        self._search.setFixedHeight(30)
        self._search.setStyleSheet(
            "background:#111113; border:none; border-bottom:1px solid #2A2A32; "
            "border-radius:0; padding:4px 10px; color:#C8C8D0; font-size:12px;"
        )
        self._search.textChanged.connect(self._filter)
        lo.addWidget(self._search)

        self._list = QListWidget()
        self._list.setFont(QFont("Consolas", 12))
        self._list.setStyleSheet("background:#1C1C1F; border:none;")
        self._list.itemClicked.connect(self._click)
        lo.addWidget(self._list, 1)

    def populate(self, ids: list[tuple[int, str]]):
        """ids = list of (can_id, description)"""
        self._ids = ids
        self._render(ids)

    def _render(self, ids):
        self._list.clear()
        for can_id, desc in ids:
            item = QListWidgetItem(f"  0x{can_id:03X}  {desc}")
            item.setData(Qt.ItemDataRole.UserRole, can_id)
            item.setForeground(QBrush(QColor("#4CAF50")))
            self._list.addItem(item)

    def _filter(self, txt: str):
        filtered = [(i, d) for i, d in self._ids
                    if not txt or txt.lower() in f"0x{i:03X}".lower() or txt.lower() in d.lower()]
        self._render(filtered)

    def _click(self, item: QListWidgetItem):
        can_id = item.data(Qt.ItemDataRole.UserRole)
        if can_id is not None:
            self.id_selected.emit(can_id)


# ─── Heatmap paleta (legacy alias — koristi _cell_colors_cat) ─────────────────

def _cell_colors(raw_val: int, raw_min: int, raw_max: int, category: str = ""):
    """Vrati (bg, fg) QColor par prema category-aware heatmap paleti."""
    return _cell_colors_cat(raw_val, raw_min, raw_max, category)


# ─── Axis label formatter ─────────────────────────────────────────────────────

def _format_axis_labels(axis, count: int, fallback_prefix: str = "") -> list[str]:
    """
    Formatiraj labele za header tablice na osnovu AxisDef.
    - RPM os (unit="rpm"): prikaži kao "512", "1024"...
    - Load os (unit sadrži "load" ili "%"): prikaži kao "0%", "2%", "20%"...
    - Ostalo: prikaži skaliranu vrijednost
    - Bez AxisDef: fallback na indeks
    """
    from core.map_finder import AxisDef
    if not axis or not axis.values:
        if fallback_prefix:
            return [f"{fallback_prefix}{i}" for i in range(count)]
        return [str(i) for i in range(count)]

    vals = axis.values[:count]
    unit = (axis.unit or "").lower()
    scale = axis.scale if axis.scale not in (0.0, 1.0) else 1.0

    if "rpm" in unit or unit == "rpm":
        # RPM: prikaži kao cijeli broj
        return [str(int(v)) for v in vals]
    elif "load" in unit or "%" in unit:
        # Load (relative air charge): raw ÷ 64 = %
        return [f"{v/64:.0f}%" for v in vals]
    elif scale != 1.0:
        # Skalirane vrijednosti — 1 decimala
        return [f"{v * scale:.1f}" for v in vals]
    else:
        # Raw vrijednosti kao int
        return [str(int(v)) for v in vals]


# ─── Map Table View ───────────────────────────────────────────────────────────

class MapTableView(QWidget):
    cell_clicked       = pyqtSignal(int, int, object)
    bulk_edit_requested = pyqtSignal(list, str, float)   # [(row,col),...], op, val

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        # Badge bar (naziv mape + dim/dtype/unit/addr)
        self._map_bar = QWidget()
        self._map_bar.setStyleSheet("background:#141418; border-bottom:1px solid #2A2A32;")
        mbl = QHBoxLayout(self._map_bar); mbl.setContentsMargins(8,4,8,4); mbl.setSpacing(6)

        self._lbl_name = QLabel("Odaberi mapu iz stabla")
        self._lbl_name.setObjectName("lbl_map_title")
        mbl.addWidget(self._lbl_name)

        self._badge_dim  = self._make_badge("", "blue")
        self._badge_unit = self._make_badge("", "green")
        self._badge_addr = self._make_badge("", "gray")
        for b in [self._badge_dim, self._badge_unit, self._badge_addr]:
            b.hide(); mbl.addWidget(b)

        mbl.addStretch()

        # Zoom slider ─────────────────────────────────────────────────
        self._zoom_lbl = QLabel("100%")
        self._zoom_lbl.setStyleSheet(
            "color:#4FC3F7;font-size:11px;font-family:Consolas;min-width:36px;"
        )
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(50, 400)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(100)
        self._zoom_slider.setFixedHeight(18)
        self._zoom_slider.setToolTip("Zoom heatmape (50%–400%)")
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self._zoom_sep = QFrame()
        self._zoom_sep.setFrameShape(QFrame.Shape.VLine)
        self._zoom_sep.setStyleSheet("color:#444;")
        self._zoom_sep.setFixedHeight(20)
        for w in [self._zoom_sep, self._zoom_slider, self._zoom_lbl]:
            w.hide()
            mbl.addWidget(w)

        # 3D plot gumb ─────────────────────────────────────────────────
        self.btn_3d = _btn("3D")
        self.btn_3d.setFixedHeight(26)
        self.btn_3d.setFixedWidth(36)
        self.btn_3d.setToolTip("3D surface plot (matplotlib)")
        self.btn_3d.hide()
        self.btn_3d.clicked.connect(self._show_3d_surface)
        mbl.addWidget(self.btn_3d)

        self.btn_copy  = _btn("Copy")
        self.btn_csv   = _btn("Export CSV")
        self.btn_reset = _btn("Reset")
        self.btn_reset.setObjectName("btn_danger")
        for b in [self.btn_copy, self.btn_csv, self.btn_reset]:
            b.setFixedHeight(26)
            b.hide()
            mbl.addWidget(b)

        lo.addWidget(self._map_bar)

        # Axis info bar — naziv i jedinica svake osi
        self._axis_bar = QWidget()
        self._axis_bar.setStyleSheet(
            "background:#111113; border-bottom:1px solid #2A2A32;"
        )
        ab_lo = QHBoxLayout(self._axis_bar)
        ab_lo.setContentsMargins(50, 3, 8, 3); ab_lo.setSpacing(24)
        # 50px lijevi margin ≈ širina vertical headera (44px) + malo prostora

        self._lbl_yaxis = QLabel()
        self._lbl_yaxis.setStyleSheet(
            "color:#4CAF50; font-size:10px; font-family:Consolas; font-weight:bold;"
        )
        self._lbl_xaxis = QLabel()
        self._lbl_xaxis.setStyleSheet(
            "color:#4FC3F7; font-size:10px; font-family:Consolas; font-weight:bold;"
        )
        ab_lo.addWidget(self._lbl_yaxis)
        ab_lo.addWidget(self._lbl_xaxis)
        ab_lo.addStretch()
        self._axis_bar.hide()
        lo.addWidget(self._axis_bar)

        # Horizontalni splitter: Fajl 1 (lijevo) | Fajl 2 (desno, skriveno dok nema compare)
        self._tables_split = QSplitter(Qt.Orientation.Horizontal)

        # ── Fajl 1 pane ───────────────────────────────────────────────────────
        t1_pane = QWidget()
        t1_lo = QVBoxLayout(t1_pane); t1_lo.setContentsMargins(0,0,0,0); t1_lo.setSpacing(0)
        self._lbl_f1 = QLabel()
        self._lbl_f1.setStyleSheet(
            "background:#141418;color:#4FC3F7;font-size:11px;font-weight:bold;"
            "padding:3px 8px;border-bottom:1px solid #2A2A32;"
        )
        self._lbl_f1.hide()
        t1_lo.addWidget(self._lbl_f1)

        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setDefaultSectionSize(64)
        self.table.horizontalHeader().setFont(QFont("Consolas", 9))
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setFont(QFont("Consolas", 9))
        self.table.verticalHeader().setFixedWidth(44)
        self.table.setFont(QFont("Consolas", 10))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(lambda r,c: self._fm and self.cell_clicked.emit(r,c,self._fm))
        t1_lo.addWidget(self.table, 1)
        self._tables_split.addWidget(t1_pane)

        # ── Fajl 2 pane (compare, read-only) ──────────────────────────────────
        self._t2_pane = QWidget()
        t2_lo = QVBoxLayout(self._t2_pane); t2_lo.setContentsMargins(0,0,0,0); t2_lo.setSpacing(0)
        self._lbl_f2 = QLabel()
        self._lbl_f2.setStyleSheet(
            "background:#141418;color:#FFB74D;font-size:11px;font-weight:bold;"
            "padding:3px 8px;border-bottom:1px solid #2A2A32;"
        )
        t2_lo.addWidget(self._lbl_f2)

        self.table2 = QTableWidget()
        self.table2.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table2.horizontalHeader().setDefaultSectionSize(64)
        self.table2.horizontalHeader().setFont(QFont("Consolas", 9))
        self.table2.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table2.verticalHeader().setDefaultSectionSize(32)
        self.table2.verticalHeader().setFont(QFont("Consolas", 9))
        self.table2.verticalHeader().setFixedWidth(44)
        self.table2.setFont(QFont("Consolas", 10))
        self.table2.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t2_lo.addWidget(self.table2, 1)
        self._t2_pane.hide()
        self._tables_split.addWidget(self._t2_pane)

        # Sinkronizirani scroll (blockSignals sprječava beskonačnu petlju)
        def _sync(src, dst):
            def _do(v):
                dst.blockSignals(True); dst.setValue(v); dst.blockSignals(False)
            src.valueChanged.connect(_do)
        _sync(self.table.verticalScrollBar(),   self.table2.verticalScrollBar())
        _sync(self.table2.verticalScrollBar(),  self.table.verticalScrollBar())
        _sync(self.table.horizontalScrollBar(), self.table2.horizontalScrollBar())
        _sync(self.table2.horizontalScrollBar(),self.table.horizontalScrollBar())

        # ── Bulk Edit Toolbar (vidljiv samo pri višestrukoj selekciji) ──────────
        self._bulk_bar = QWidget()
        self._bulk_bar.setStyleSheet(
            "background:#141418; border-top:1px solid #2A2A32; border-bottom:1px solid #2A2A32;"
        )
        bulk_lo = QHBoxLayout(self._bulk_bar)
        bulk_lo.setContentsMargins(8, 3, 8, 3)
        bulk_lo.setSpacing(6)

        lbl_bulk = QLabel("Selektirano:")
        lbl_bulk.setStyleSheet("color:#4FC3F7; font-size:11px; font-family:Consolas;")
        bulk_lo.addWidget(lbl_bulk)

        self._lbl_sel_count = QLabel("0")
        self._lbl_sel_count.setStyleSheet(
            "color:#4FC3F7; font-size:11px; font-family:Consolas; font-weight:bold;"
        )
        bulk_lo.addWidget(self._lbl_sel_count)

        bulk_lo.addSpacing(8)

        self._btn_scale = _btn("× Scale")
        self._btn_scale.setToolTip("Množi selektirane ćelije s postotkom (npr. 105%)")
        self._btn_scale.setFixedHeight(22)
        self._btn_scale.clicked.connect(self._bulk_scale)
        bulk_lo.addWidget(self._btn_scale)

        self._btn_offset_bulk = _btn("+ Offset")
        self._btn_offset_bulk.setToolTip("Dodaj konstantu svim selektiranim ćelijama")
        self._btn_offset_bulk.setFixedHeight(22)
        self._btn_offset_bulk.clicked.connect(self._bulk_offset)
        bulk_lo.addWidget(self._btn_offset_bulk)

        self._btn_smooth = _btn("~ Smooth")
        self._btn_smooth.setToolTip("Linearna interpolacija između prvih i zadnjih selektiranih")
        self._btn_smooth.setFixedHeight(22)
        self._btn_smooth.clicked.connect(self._bulk_smooth)
        bulk_lo.addWidget(self._btn_smooth)

        self._btn_copy_ref = _btn("↕ Copy REF")
        self._btn_copy_ref.setToolTip("Kopiraj vrijednosti iz referentnog (ORI) fajla za selektirane ćelije")
        self._btn_copy_ref.setFixedHeight(22)
        self._btn_copy_ref.clicked.connect(self._bulk_copy_ref)
        bulk_lo.addWidget(self._btn_copy_ref)

        bulk_lo.addStretch()
        self._bulk_bar.hide()
        lo.addWidget(self._bulk_bar)

        lo.addWidget(self._tables_split, 1)

        self._fm:  FoundMap | None = None
        self._fm2: FoundMap | None = None

        # Prati selekciju za bulk toolbar
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    @staticmethod
    def _make_badge(text: str, style: str = "blue") -> QLabel:
        lbl = QLabel(text)
        colors = {
            "blue":  "background:#1A2F4A;color:#4FC3F7;border:1px solid #4FC3F7;",
            "green": "background:#1a3a2a;color:#4CAF50;border:1px solid #4CAF50;",
            "gray":  "background:#141418;color:#808090;border:1px solid #2A2A32;",
        }
        lbl.setStyleSheet(f"""
            QLabel {{
                {colors.get(style, colors['gray'])}
                border-radius: 10px;
                padding: 2px 8px;
                font-family: Consolas;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        return lbl

    def show_map(self, fm: FoundMap, compare: FoundMap | None = None):
        self._fm = fm; self._fm2 = compare
        defn = fm.defn

        self._lbl_name.setText(defn.name)
        self._badge_dim.setText(f"{defn.rows}×{defn.cols} · {defn.dtype}")
        self._badge_unit.setText(f"×{defn.scale} · {defn.unit}" if defn.unit else f"×{defn.scale}")
        self._badge_addr.setText(f"@ 0x{fm.address:06X}")
        for b in [self._badge_dim, self._badge_unit, self._badge_addr,
                  self.btn_copy, self.btn_csv, self.btn_reset]:
            b.show()

        # Zoom slider i 3D gumb — vidljivi samo za 2D mape
        is_2d = defn.rows >= 2 and defn.cols >= 2
        for w in [self._zoom_sep, self._zoom_slider, self._zoom_lbl]:
            w.setVisible(True)
        self.btn_3d.setVisible(is_2d)

        # Prikaži/sakrij drugi panel
        if compare:
            self._lbl_f1.setText(f"  Fajl 1  —  {fm.sw_id}")
            self._lbl_f1.show()
            self._lbl_f2.setText(f"  Fajl 2  —  {compare.sw_id}  @ 0x{compare.address:06X}")
            self._t2_pane.show()
        else:
            self._lbl_f1.hide()
            self._t2_pane.hide()

        rows, cols = defn.rows, defn.cols
        data  = fm.data
        data2 = compare.data if compare else None

        self.table.setRowCount(rows); self.table.setColumnCount(cols)
        if compare:
            self.table2.setRowCount(rows); self.table2.setColumnCount(cols)

        x_labels = _format_axis_labels(defn.axis_x, cols)
        y_labels  = _format_axis_labels(defn.axis_y, rows, fallback_prefix="r")
        self.table.setHorizontalHeaderLabels(x_labels)
        self.table.setVerticalHeaderLabels(y_labels)
        if compare:
            self.table2.setHorizontalHeaderLabels(x_labels)
            self.table2.setVerticalHeaderLabels(y_labels)

        # Axis info bar
        if defn.axis_x or defn.axis_y:
            xd = defn.axis_x
            yd = defn.axis_y
            x_txt = (f"→  X:  {xd.unit}  ({xd.count} pt,  {xd.dtype})" if xd and xd.unit
                     else f"→  X:  {xd.count} stupaca" if xd else "")
            y_txt = (f"↓  Y:  {yd.unit}  ({yd.count} pt,  {yd.dtype})" if yd and yd.unit
                     else f"↓  Y:  {yd.count} redova" if yd else "")
            self._lbl_xaxis.setText(x_txt)
            self._lbl_yaxis.setText(y_txt)
            self._axis_bar.show()
        else:
            self._axis_bar.hide()

        mn  = min(data)  if data  else 0
        mx  = max(data)  if data  else 1
        mn2 = min(data2) if data2 else mn
        mx2 = max(data2) if data2 else mx

        def _fmt(raw, d):
            if d.dtype == "u8":
                return f"{raw * d.scale + d.offset_val:.1f}"
            elif d.scale != 0:
                return f"{raw * d.scale + d.offset_val:.3f}"
            else:
                return f"0x{raw:04X}"

        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx >= len(data): break
                raw = data[idx]
                is_diff = data2 and idx < len(data2) and data2[idx] != raw

                item = QTableWidgetItem(_fmt(raw, defn))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setData(Qt.ItemDataRole.UserRole, raw)
                if is_diff:
                    item.setBackground(QBrush(QColor("#3a3010")))
                    item.setForeground(QBrush(QColor("#e5c07b")))
                else:
                    bg, fg = _cell_colors(raw, mn, mx, defn.category)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))
                self.table.setItem(r, c, item)

                # Drugi panel (Fajl 2)
                if data2 and idx < len(data2):
                    raw2 = data2[idx]
                    item2 = QTableWidgetItem(_fmt(raw2, defn))
                    item2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    item2.setData(Qt.ItemDataRole.UserRole, raw2)
                    if is_diff:
                        item2.setBackground(QBrush(QColor("#3a1000")))
                        item2.setForeground(QBrush(QColor("#f48771")))
                    else:
                        bg2, fg2 = _cell_colors(raw2, mn2, mx2, defn.category)
                        item2.setBackground(QBrush(bg2))
                        item2.setForeground(QBrush(fg2))
                    self.table2.setItem(r, c, item2)

    def _on_zoom_changed(self, val: int):
        """Skalira visinu redova i sirinu stupaca heatmape."""
        self._zoom_lbl.setText(f"{val}%")
        col_w = max(28, int(64 * val / 100))
        row_h = max(16, int(32 * val / 100))
        font_pt = max(7, int(10 * val / 100))
        for tbl in (self.table, self.table2):
            tbl.horizontalHeader().setDefaultSectionSize(col_w)
            tbl.verticalHeader().setDefaultSectionSize(row_h)
            f = tbl.font(); f.setPointSize(font_pt); tbl.setFont(f)

    def _show_3d_surface(self):
        """Otvara 3D surface plot u novom prozoru (matplotlib)."""
        if not self._fm or self._fm.defn.rows < 2 or self._fm.defn.cols < 2:
            return

        try:
            import numpy as np
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        except ImportError:
            QMessageBox.warning(self, "3D plot", "matplotlib nije instaliran.")
            return

        fm   = self._fm
        rows = fm.defn.rows
        cols = fm.defn.cols
        Z    = np.array(fm.display_values, dtype=float).reshape(rows, cols)

        # Osi: koristimo poznate vrijednosti ili indekse
        x_vals = (fm.defn.axis_x.values if fm.defn.axis_x and fm.defn.axis_x.values
                  else list(range(cols)))
        y_vals = (fm.defn.axis_y.values if fm.defn.axis_y and fm.defn.axis_y.values
                  else list(range(rows)))

        # Ako os ima scale != 1.0, primijenimo ga
        if fm.defn.axis_x and fm.defn.axis_x.scale not in (1.0, 0.0):
            x_vals = [v * fm.defn.axis_x.scale for v in x_vals]
        if fm.defn.axis_y and fm.defn.axis_y.scale not in (1.0, 0.0):
            y_vals = [v * fm.defn.axis_y.scale for v in y_vals]

        X, Y = np.meshgrid(x_vals[:cols], y_vals[:rows])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"3D — {fm.defn.name}")
        dlg.resize(820, 620)
        dlg.setStyleSheet("background:#111113;")
        dlg_lo = QVBoxLayout(dlg)
        dlg_lo.setContentsMargins(4, 4, 4, 4)

        fig = Figure(figsize=(8, 5.5), facecolor="#111113")
        ax  = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#111113")
        fig.patch.set_facecolor("#111113")

        surf = ax.plot_surface(X, Y, Z, cmap="viridis", linewidth=0, antialiased=True)
        fig.colorbar(surf, ax=ax, shrink=0.5, pad=0.08,
                     label=fm.defn.unit or "raw")

        x_unit = (fm.defn.axis_x.unit if fm.defn.axis_x else "col")
        y_unit = (fm.defn.axis_y.unit if fm.defn.axis_y else "row")
        ax.set_xlabel(x_unit, color="#4FC3F7", labelpad=8)
        ax.set_ylabel(y_unit, color="#4CAF50", labelpad=8)
        ax.set_zlabel(fm.defn.unit or "val", color="#FFB74D", labelpad=8)
        ax.set_title(fm.defn.name, color="#C8C8D0", pad=10)

        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.fill = False
        ax.tick_params(colors="#888888")
        ax.xaxis.line.set_color("#555555")
        ax.yaxis.line.set_color("#555555")
        ax.zaxis.line.set_color("#555555")

        canvas = FigureCanvasQTAgg(fig)
        dlg_lo.addWidget(canvas)

        close_btn = _btn("Zatvori")
        close_btn.setFixedHeight(28)
        close_btn.clicked.connect(dlg.accept)
        close_btn.setStyleSheet("margin:4px;")
        dlg_lo.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()

    def refresh_cell(self, row: int, col: int, new_raw: int):
        defn = self._fm.defn
        if defn.dtype == "u8":
            txt = f"{new_raw * defn.scale + defn.offset_val:.1f}"
        elif defn.scale != 0:
            txt = f"{new_raw * defn.scale + defn.offset_val:.3f}"
        else:
            txt = f"0x{new_raw:04X}"
        item = self.table.item(row, col)
        if not item: return
        item.setText(txt); item.setData(Qt.ItemDataRole.UserRole, new_raw)
        mn = min(self._fm.data); mx = max(self._fm.data)
        bg, fg = _cell_colors(new_raw, mn, mx, self._fm.defn.category)
        item.setBackground(QBrush(bg))
        item.setForeground(QBrush(fg))

    def clear(self):
        self._fm = None; self._fm2 = None
        self.table.setRowCount(0); self.table.setColumnCount(0)
        self.table2.setRowCount(0); self.table2.setColumnCount(0)
        self._lbl_f1.hide(); self._t2_pane.hide(); self._axis_bar.hide()
        self._lbl_name.setText("Odaberi mapu iz stabla")
        for b in [self._badge_dim, self._badge_unit, self._badge_addr,
                  self.btn_copy, self.btn_csv, self.btn_reset,
                  self._zoom_sep, self._zoom_slider, self._zoom_lbl, self.btn_3d]:
            b.hide()
        self._zoom_slider.setValue(100)
        self._bulk_bar.hide()

    # ── Selekcija — bulk toolbar ───────────────────────────────────────────────

    def _on_selection_changed(self):
        sel = self.table.selectedItems()
        n = len(sel)
        if n > 1:
            self._lbl_sel_count.setText(str(n))
            self._bulk_bar.show()
        else:
            self._bulk_bar.hide()

    def _get_selected_cells(self) -> list[tuple[int, int]]:
        """Vrati listu (row, col) selektiranih ćelija."""
        seen = set()
        cells = []
        for item in self.table.selectedItems():
            rc = (item.row(), item.column())
            if rc not in seen:
                seen.add(rc)
                cells.append(rc)
        return sorted(cells)

    def _bulk_scale(self):
        """Dialog: unesi postotak, primijeni na sve selektirane ćelije."""
        if not self._fm: return
        cells = self._get_selected_cells()
        if not cells: return
        dlg = QDialog(self)
        dlg.setWindowTitle("Scale ×%")
        dlg.setFixedSize(300, 130)
        dlg.setStyleSheet("background:#1C1C1F; color:#C8C8D0;")
        lo = QVBoxLayout(dlg); lo.setContentsMargins(16, 12, 16, 12); lo.setSpacing(8)
        lo.addWidget(QLabel(f"Scale {len(cells)} ćelija (postotak):"))
        spin = QDoubleSpinBox()
        spin.setRange(1.0, 500.0); spin.setValue(100.0); spin.setSingleStep(1.0)
        spin.setSuffix(" %"); spin.setDecimals(1)
        lo.addWidget(spin)
        btn_row = QHBoxLayout()
        ok_btn = _btn("Primijeni", "primary"); ok_btn.setFixedHeight(26)
        ca_btn = _btn("Odustani");             ca_btn.setFixedHeight(26)
        ok_btn.clicked.connect(dlg.accept); ca_btn.clicked.connect(dlg.reject)
        btn_row.addStretch(); btn_row.addWidget(ca_btn); btn_row.addWidget(ok_btn)
        lo.addLayout(btn_row)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        pct = spin.value() / 100.0
        self.bulk_edit_requested.emit(cells, "scale", pct)

    def _bulk_offset(self):
        """Dialog: unesi konstantu, dodaj svim selektiranim ćelijama."""
        if not self._fm: return
        cells = self._get_selected_cells()
        if not cells: return
        dlg = QDialog(self)
        dlg.setWindowTitle("Offset +")
        dlg.setFixedSize(300, 130)
        dlg.setStyleSheet("background:#1C1C1F; color:#C8C8D0;")
        lo = QVBoxLayout(dlg); lo.setContentsMargins(16, 12, 16, 12); lo.setSpacing(8)
        lo.addWidget(QLabel(f"Dodaj offset {len(cells)} ćelijama:"))
        spin = QDoubleSpinBox()
        spin.setRange(-9999.0, 9999.0); spin.setValue(0.0); spin.setSingleStep(0.1)
        spin.setDecimals(4)
        lo.addWidget(spin)
        btn_row = QHBoxLayout()
        ok_btn = _btn("Primijeni", "primary"); ok_btn.setFixedHeight(26)
        ca_btn = _btn("Odustani");             ca_btn.setFixedHeight(26)
        ok_btn.clicked.connect(dlg.accept); ca_btn.clicked.connect(dlg.reject)
        btn_row.addStretch(); btn_row.addWidget(ca_btn); btn_row.addWidget(ok_btn)
        lo.addLayout(btn_row)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        self.bulk_edit_requested.emit(cells, "offset", spin.value())

    def _bulk_smooth(self):
        """Linearna interpolacija između prvih i zadnjih selektiranih po retku."""
        if not self._fm: return
        cells = self._get_selected_cells()
        if len(cells) < 3: return
        self.bulk_edit_requested.emit(cells, "smooth", 0.0)

    def _bulk_copy_ref(self):
        """Kopiraj vrijednosti iz referentnog (Fajl 2) za selektirane ćelije."""
        if not self._fm or not self._fm2: return
        cells = self._get_selected_cells()
        if not cells: return
        self.bulk_edit_requested.emit(cells, "copy_ref", 0.0)

    # ── Delta overlay (Diff prikaz) ────────────────────────────────────────────

    def show_map_diff(self, fm_ori: "FoundMap", fm_new: "FoundMap"):
        """
        Prikaži novu mapu s delta overlay: "37 (+3)" format.
        Ćelije bez promjene — normalna boja.
        Ćelije s porastom — zelena nijansa.
        Ćelije s padom — crvena nijansa.
        """
        self._fm  = fm_new
        self._fm2 = fm_ori
        defn = fm_new.defn

        self._lbl_name.setText(f"Δ {defn.name}")
        self._badge_dim.setText(f"{defn.rows}×{defn.cols} · {defn.dtype}")
        self._badge_unit.setText(f"×{defn.scale} · {defn.unit}" if defn.unit else f"×{defn.scale}")
        self._badge_addr.setText(f"@ 0x{fm_new.address:06X}")
        for b in [self._badge_dim, self._badge_unit, self._badge_addr,
                  self.btn_copy, self.btn_csv]:
            b.show()
        self.btn_reset.hide()

        rows, cols = defn.rows, defn.cols
        self.table.setRowCount(rows); self.table.setColumnCount(cols)

        x_labels = _format_axis_labels(defn.axis_x, cols)
        y_labels  = _format_axis_labels(defn.axis_y, rows, fallback_prefix="r")
        self.table.setHorizontalHeaderLabels(x_labels)
        self.table.setVerticalHeaderLabels(y_labels)

        data_new = fm_new.data
        data_ori = fm_ori.data
        mn = min(data_new) if data_new else 0
        mx = max(data_new) if data_new else 1

        # Max delta za normalizaciju intenziteta boje
        max_delta = max(abs(data_new[i] - data_ori[i])
                        for i in range(min(len(data_new), len(data_ori)))
                        ) if data_ori else 1
        max_delta = max(max_delta, 1)

        def _fmt_delta(raw_n, raw_o, d):
            disp_n = raw_n * d.scale + d.offset_val if d.scale else float(raw_n)
            delta  = raw_n - raw_o
            if d.dtype == "u8":
                base = f"{disp_n:.1f}"
            elif d.scale != 0:
                base = f"{disp_n:.3f}"
            else:
                base = f"0x{raw_n:04X}"
            if delta > 0:
                return f"{base} (+{delta})"
            elif delta < 0:
                return f"{base} ({delta})"
            return base

        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx >= len(data_new): break
                raw_n = data_new[idx]
                raw_o = data_ori[idx] if idx < len(data_ori) else raw_n
                delta = raw_n - raw_o

                txt  = _fmt_delta(raw_n, raw_o, defn)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setData(Qt.ItemDataRole.UserRole, raw_n)

                if delta == 0:
                    bg, fg = _cell_colors(raw_n, mn, mx)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))
                elif delta > 0:
                    intensity = min(int(delta / max_delta * 160), 160)
                    item.setBackground(QBrush(QColor(0, 30 + intensity, 10)))
                    item.setForeground(QBrush(QColor("#7ef79e")))
                else:
                    intensity = min(int(abs(delta) / max_delta * 160), 160)
                    item.setBackground(QBrush(QColor(30 + intensity, 10, 10)))
                    item.setForeground(QBrush(QColor("#f77e7e")))

                self.table.setItem(r, c, item)

        self._lbl_f1.hide()
        self._t2_pane.hide()


# ─── Properties panel — 3 taba ────────────────────────────────────────────────

class PropertiesPanel(QWidget):
    edit_requested = pyqtSignal(int, int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(270)
        self._fm:      FoundMap | None = None
        self._row = self._col = 0

        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        hdr = QLabel("  PROPERTIES")
        hdr.setStyleSheet(
            "background:#141418; color:#808090; font-size:10px; font-weight:bold; "
            "padding:6px 10px; border-bottom:1px solid #2A2A32; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        lo.addWidget(self.tabs, 1)

        # ── Tab 0: Celija ──────────────────────────────────────────────────
        cell_w = QWidget()
        cell_lo = QVBoxLayout(cell_w); cell_lo.setContentsMargins(8,8,8,8); cell_lo.setSpacing(6)

        self._pos_lbl = QLabel("Odaberi ćeliju")
        self._pos_lbl.setStyleSheet("color:#808090; font-size:12px;")
        cell_lo.addWidget(self._pos_lbl)

        # Big value frame s border-left akcentom
        val_frame = QFrame()
        val_frame.setStyleSheet("""
            QFrame {
                background: #1A2F4A;
                border: 1px solid #2A4A6A;
                border-left: 3px solid #4FC3F7;
                border-radius: 4px;
            }
        """)
        val_fl = QVBoxLayout(val_frame); val_fl.setContentsMargins(8,8,8,8); val_fl.setSpacing(2)

        self._val_lbl = QLabel("—")
        self._val_lbl.setObjectName("lbl_value_big")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_fl.addWidget(self._val_lbl)

        self._raw_lbl = QLabel("—")
        self._raw_lbl.setObjectName("lbl_addr")
        self._raw_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_fl.addWidget(self._raw_lbl)

        cell_lo.addWidget(val_frame)

        # Step gumbi — 2×2 grid
        step_grid = QGridLayout(); step_grid.setSpacing(3)
        self._btn_dd = _btn("▼▼"); self._btn_d = _btn("▼")
        self._btn_u  = _btn("▲");  self._btn_uu = _btn("▲▲")
        for i, b in enumerate([self._btn_dd, self._btn_d, self._btn_u, self._btn_uu]):
            b.setFixedHeight(26); step_grid.addWidget(b, 0, i)
        cell_lo.addLayout(step_grid)

        self._btn_dd.clicked.connect(lambda: self._step(-5))
        self._btn_d.clicked.connect(lambda:  self._step(-1))
        self._btn_u.clicked.connect(lambda:  self._step(1))
        self._btn_uu.clicked.connect(lambda: self._step(5))

        # Direktni unos
        inp_lo = QHBoxLayout(); inp_lo.setSpacing(4)
        self._inp = QLineEdit(); self._inp.setPlaceholderText("direct input...")
        self._inp.returnPressed.connect(self._set_val)
        btn_set = _btn("Set", "primary"); btn_set.setFixedHeight(26); btn_set.clicked.connect(self._set_val)
        inp_lo.addWidget(self._inp, 1); inp_lo.addWidget(btn_set)
        cell_lo.addLayout(inp_lo)

        self._addr_lbl = QLabel("—")
        self._addr_lbl.setObjectName("lbl_addr")
        cell_lo.addWidget(self._addr_lbl)
        cell_lo.addStretch()
        self._cell_w = cell_w
        self.tabs.addTab(cell_w, "Cell")

        # ── Tab 1: Mapa ────────────────────────────────────────────────────
        map_w = QWidget()
        map_lo = QVBoxLayout(map_w); map_lo.setContentsMargins(8,8,8,8); map_lo.setSpacing(6)

        stats_g = QGroupBox("STATISTIKA")
        sg = QGridLayout(stats_g); sg.setSpacing(3)
        self._st: dict[str, QLabel] = {}
        for i, k in enumerate(["Min","Max","Prosjek","Raspon","Celije","Mirror"]):
            kl = QLabel(k+":"); kl.setStyleSheet("color:#808090; font-size:12px;")
            vl = QLabel("—")
            vl.setFont(QFont("Consolas", 11))
            vl.setStyleSheet("color:#4FC3F7; font-size:11px; font-weight:bold;")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            sg.addWidget(kl, i, 0); sg.addWidget(vl, i, 1)
            self._st[k] = vl
        map_lo.addWidget(stats_g)

        notes_g = QGroupBox("NAPOMENE")
        nl = QVBoxLayout(notes_g); nl.setContentsMargins(6,6,6,6)
        self._notes = QLabel("—")
        self._notes.setWordWrap(True)
        self._notes.setStyleSheet("color:#505060; font-size:12px;")
        nl.addWidget(self._notes)
        map_lo.addWidget(notes_g)
        map_lo.addStretch()
        self.tabs.addTab(map_w, "Mapa")

        # ── Tab 2: ECU ─────────────────────────────────────────────────────
        ecu_w = QWidget()
        ecu_lo = QVBoxLayout(ecu_w); ecu_lo.setContentsMargins(8,8,8,8); ecu_lo.setSpacing(6)

        ecu_g = QGroupBox("ECU INFORMATION")
        eg = QGridLayout(ecu_g); eg.setSpacing(3)
        self._ecu: dict[str, QLabel] = {}
        for i, k in enumerate(["Model","SW ID","MCU","Velicina","Checksum","Platform"]):
            kl = QLabel(k+":"); kl.setStyleSheet("color:#808090; font-size:12px;")
            vl = QLabel("—")
            vl.setFont(QFont("Consolas", 11))
            vl.setStyleSheet("color:#4FC3F7; font-size:11px; font-weight:bold;")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            eg.addWidget(kl, i, 0); eg.addWidget(vl, i, 1)
            self._ecu[k] = vl
        ecu_lo.addWidget(ecu_g)

        mem_g = QGroupBox("MEMORY LAYOUT")
        ml = QVBoxLayout(mem_g); ml.setContentsMargins(6,6,6,6)
        mem_txt = QLabel(
            "BOOT  0x000000–0x00FFFF  64 KB\n"
            "CODE  0x010000–0x05FFFF  320 KB\n"
            "CAL   0x060000–0x15FFFF  1 MB  [bytekod]\n"
            "FILL  0x160000–0x178000  96 KB"
        )
        mem_txt.setFont(QFont("Consolas", 10))
        mem_txt.setStyleSheet("color:#505060; font-size:12px;")
        ml.addWidget(mem_txt)
        ecu_lo.addWidget(mem_g)
        ecu_lo.addStretch()
        self.tabs.addTab(ecu_w, "ECU")

        # ── Tab 3: DTC detalji ─────────────────────────────────────────────
        dtc_w = QWidget()
        dtc_lo = QVBoxLayout(dtc_w); dtc_lo.setContentsMargins(8, 8, 8, 8); dtc_lo.setSpacing(6)

        self._dtc_code_lbl = QLabel("—")
        self._dtc_code_lbl.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self._dtc_code_lbl.setStyleSheet("color:#EF5350; font-size:18px; font-weight:bold;")
        dtc_lo.addWidget(self._dtc_code_lbl)

        self._dtc_name_lbl = QLabel("")
        self._dtc_name_lbl.setStyleSheet("color:#808090; font-size:12px;")
        self._dtc_name_lbl.setWordWrap(True)
        dtc_lo.addWidget(self._dtc_name_lbl)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:#2A2A32; max-height:1px;")
        dtc_lo.addWidget(sep2)

        cs_g = QGroupBox("Code storage (LE u16)")
        csg = QGridLayout(cs_g); csg.setSpacing(3)
        kl_m = QLabel("Main:"); kl_m.setStyleSheet("color:#808090;")
        csg.addWidget(kl_m, 0, 0)
        self._dtc_main_lbl = QLabel("—")
        self._dtc_main_lbl.setFont(QFont("Consolas", 11))
        self._dtc_main_lbl.setStyleSheet("color:#4FC3F7; font-weight:bold;")
        csg.addWidget(self._dtc_main_lbl, 0, 1)
        kl_mir = QLabel("Mirror:"); kl_mir.setStyleSheet("color:#808090;")
        csg.addWidget(kl_mir, 1, 0)
        self._dtc_mirror_lbl = QLabel("—")
        self._dtc_mirror_lbl.setFont(QFont("Consolas", 11))
        self._dtc_mirror_lbl.setStyleSheet("color:#4FC3F7; font-weight:bold;")
        csg.addWidget(self._dtc_mirror_lbl, 1, 1)
        csg.setColumnStretch(2, 1)
        dtc_lo.addWidget(cs_g)

        self._dtc_notes_lbl = QLabel("")
        self._dtc_notes_lbl.setStyleSheet("color:#505060; font-size:12px;")
        self._dtc_notes_lbl.setWordWrap(True)
        dtc_lo.addWidget(self._dtc_notes_lbl)

        dtc_lo.addStretch()
        self._dtc_tab_idx = self.tabs.addTab(dtc_w, "DTC")

        # ── Tab 4: History (undo history) ──────────────────────────────────
        hist_w = QWidget()
        hist_lo = QVBoxLayout(hist_w); hist_lo.setContentsMargins(4, 4, 4, 4); hist_lo.setSpacing(4)

        hist_hdr = QLabel("UNDO HISTORY")
        hist_hdr.setStyleSheet(
            "color:#808090; font-size:10px; font-weight:bold; letter-spacing:1px; padding:2px 4px;"
        )
        hist_lo.addWidget(hist_hdr)

        self._hist_list = QListWidget()
        self._hist_list.setFont(QFont("Consolas", 11))
        self._hist_list.setStyleSheet(
            "background:#111113; border:none; font-size:11px;"
        )
        self._hist_list.setToolTip("Klik na stavku = undo do te točke")
        self._hist_list.itemClicked.connect(self._hist_item_clicked)
        hist_lo.addWidget(self._hist_list, 1)

        hist_btn_row = QHBoxLayout()
        self._btn_hist_clear = _btn("Obriši history"); self._btn_hist_clear.setFixedHeight(24)
        self._btn_hist_clear.clicked.connect(self._hist_clear)
        hist_btn_row.addStretch(); hist_btn_row.addWidget(self._btn_hist_clear)
        hist_lo.addLayout(hist_btn_row)

        self._hist_tab_idx = self.tabs.addTab(hist_w, "History")
        self._hist_undo_ref: list = []   # referenca na MainWindow._undo (postavlja se izvana)

    # ── Public update metode ──────────────────────────────────────────────────

    def show_ecu(self, eng: ME17Engine):
        info = eng.info
        cs   = ChecksumEngine(eng).verify()
        self._ecu["Model"].setText("ME17.8.5")
        self._ecu["SW ID"].setText(info.sw_id)
        self._ecu["SW ID"].setStyleSheet("color:#4FC3F7; font-size:11px; font-weight:bold;")
        self._ecu["MCU"].setText("TC1762 LE" if info.mcu_confirmed else "NEPOTVRDJEN")
        self._ecu["Velicina"].setText(f"{info.file_size // 1024} KB")
        self._ecu["Platform"].setText("VM_CB.04.80.00" if info.platform_confirmed else "—")
        ok = cs.get("sw_id", {}).get("status") == "OK"
        self._ecu["Checksum"].setText("SW OK" if ok else "PENDING")
        self._ecu["Checksum"].setStyleSheet(
            f"color:{'#4CAF50' if ok else '#FFB74D'}; font-size:11px; font-weight:bold;"
        )

    def show_map_stats(self, fm: FoundMap):
        self._fm = fm
        defn = fm.defn; data = fm.data
        if not data: return
        disp = fm.display_values
        mn = min(disp); mx = max(disp); avg = sum(disp)/len(disp)
        u = defn.unit
        self._st["Min"].setText(f"{mn:.3f} {u}")
        self._st["Max"].setText(f"{mx:.3f} {u}")
        self._st["Prosjek"].setText(f"{avg:.3f} {u}")
        self._st["Raspon"].setText(f"{mx-mn:.3f} {u}")
        self._st["Celije"].setText(f"{defn.rows}×{defn.cols} = {len(data)}")
        self._st["Mirror"].setText(f"+0x{defn.mirror_offset:X}" if defn.mirror_offset else "—")
        self._notes.setText(defn.notes[:280] if defn.notes else "—")
        # Step labele
        s = defn.scale
        self._btn_d.setText(f"▼ -{s:.3g}")
        self._btn_u.setText(f"▲ +{s:.3g}")
        self._btn_dd.setText(f"▼▼ -{s*5:.3g}")
        self._btn_uu.setText(f"▲▲ +{s*5:.3g}")
        self.tabs.setCurrentIndex(1)

    def show_cell(self, row: int, col: int, fm: FoundMap):
        self._fm = fm; self._row = row; self._col = col
        defn = fm.defn
        idx  = row * defn.cols + col
        raw  = fm.data[idx] if idx < len(fm.data) else 0
        disp = raw * defn.scale + defn.offset_val if defn.scale else float(raw)
        addr = fm.address + idx * defn.cell_bytes
        self._val_lbl.setText(f"{disp:.2f}")
        self._pos_lbl.setText(f"[{row},{col}]  {defn.unit}")
        self._raw_lbl.setText(f"raw {raw}  (0x{raw:0{defn.cell_bytes*2}X})")
        self._addr_lbl.setText(f"ADDR 0x{addr:06X}")
        self._inp.setText(f"{disp:.4f}")
        self.tabs.setCurrentIndex(0)

    def show_dtc_details(self, status: "DtcStatus"):
        defn = status.defn
        self._dtc_code_lbl.setText(defn.p_code)
        self._dtc_name_lbl.setText(defn.name)
        self._dtc_main_lbl.setText(
            f"0x{status.code_main:04X}  (addr 0x{defn.code_addr:06X})"
        )
        self._dtc_mirror_lbl.setText(
            f"0x{status.code_mirror:04X}  (addr 0x{defn.mirror_addr:06X})"
        )
        self._dtc_notes_lbl.setText(defn.notes[:300] if defn.notes else "—")
        self.tabs.setCurrentIndex(self._dtc_tab_idx)

    # ── History tab ───────────────────────────────────────────────────────────

    def push_history(self, cmd: "UndoCmd"):
        """Dodaj unos u History listu (poziva se nakon svake promjene)."""
        ts = datetime.now().strftime("%H:%M:%S")
        defn = cmd.fm.defn
        old_disp = cmd.old_raw * defn.scale + defn.offset_val if defn.scale else float(cmd.old_raw)
        new_disp = cmd.new_raw * defn.scale + defn.offset_val if defn.scale else float(cmd.new_raw)
        txt = (f"{ts}  [{cmd.row},{cmd.col}]  "
               f"{old_disp:.3g} → {new_disp:.3g}  {defn.unit}  |  {defn.name}")
        item = QListWidgetItem(txt)
        item.setForeground(QBrush(QColor("#4FC3F7")))
        item.setData(Qt.ItemDataRole.UserRole, id(cmd))
        # Dodaj na vrh (najnovije na vrhu)
        self._hist_list.insertItem(0, item)
        # Maks 100 stavki
        while self._hist_list.count() > 100:
            self._hist_list.takeItem(self._hist_list.count() - 1)
        # Pohrani referencu na cmd za undo do točke
        item.setData(Qt.ItemDataRole.UserRole + 1, cmd)

    def _hist_item_clicked(self, item: QListWidgetItem):
        """Undo do kliknute točke u historiji — emitira signal prema MainWindow."""
        cmd = item.data(Qt.ItemDataRole.UserRole + 1)
        if cmd is not None:
            self.undo_to_cmd_requested.emit(cmd)

    def _hist_clear(self):
        self._hist_list.clear()

    undo_to_cmd_requested = pyqtSignal(object)

    # ── Delta prikaz u Cell tabu ──────────────────────────────────────────────

    def show_cell_with_delta(self, row: int, col: int, fm: "FoundMap", fm_ori: "FoundMap | None" = None):
        """Prikaži cell info s delta ako je dostupna referentna mapa."""
        self.show_cell(row, col, fm)
        if fm_ori:
            defn = fm.defn
            idx  = row * defn.cols + col
            raw_new = fm.data[idx] if idx < len(fm.data) else 0
            raw_ori = fm_ori.data[idx] if idx < len(fm_ori.data) else raw_new
            delta_raw = raw_new - raw_ori
            if delta_raw != 0:
                delta_disp = delta_raw * defn.scale if defn.scale else float(delta_raw)
                sign = "+" if delta_disp >= 0 else ""
                self._addr_lbl.setText(
                    f"ADDR 0x{fm.address + idx * defn.cell_bytes:06X}  "
                    f"Δ {sign}{delta_disp:.3g} {defn.unit}"
                )
                self._addr_lbl.setStyleSheet(
                    "color:#4CAF50; font-family:Consolas; font-size:11px;" if delta_raw > 0
                    else "color:#EF5350; font-family:Consolas; font-size:11px;"
                )
            else:
                self._addr_lbl.setStyleSheet("")

    # ── Private ───────────────────────────────────────────────────────────────

    def _step(self, steps: int):
        if not self._fm: return
        defn = self._fm.defn
        if defn.scale == 0: return
        idx  = self._row * defn.cols + self._col
        raw  = self._fm.data[idx] if idx < len(self._fm.data) else 0
        raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max
        new_raw  = max(defn.raw_min, min(raw_max, raw + steps))
        new_disp = new_raw * defn.scale + defn.offset_val
        self.edit_requested.emit(self._row, self._col, new_disp)

    def _set_val(self):
        if not self._fm: return
        try:
            val = float(self._inp.text().replace(",", "."))
            self.edit_requested.emit(self._row, self._col, val)
            self._inp.setStyleSheet("")
        except ValueError:
            self._inp.setStyleSheet(
                "background:#2a1010; border:1px solid #EF5350; border-radius:3px; padding:4px 8px;"
            )
            QTimer.singleShot(800, lambda: self._inp.setStyleSheet(""))


# ─── Hex Strip ────────────────────────────────────────────────────────────────

class HexStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        hdr = QLabel("  HEX VIEW")
        hdr.setStyleSheet(
            "color:#808090; font-size:10px; font-weight:bold; letter-spacing:1.5px; "
            "padding:3px 10px; background:#141418; border-bottom:1px solid #2A2A32;"
        )
        lo.addWidget(hdr)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 11))
        self.text.setStyleSheet(
            "QTextEdit { background:#141418; color:#808090; border:none; padding:6px 10px; }"
        )
        lo.addWidget(self.text, 1)

    def show(self, eng: ME17Engine, addr: int, length: int = 64):
        if not eng or not eng.loaded: return
        data  = eng.get_bytes()
        lines = []
        for i in range(0, min(length, len(data)-addr), 16):
            ch  = data[addr+i: addr+i+16]
            hx  = " ".join(f"0x{b:02X}" for b in ch)
            asc = "".join(chr(b) if 32 <= b < 127 else "·" for b in ch)
            lines.append(
                f'<span style="color:#4FC3F7">0x{addr+i:06X}:</span>  '
                f'<span style="color:#808090">{hx}</span>  '
                f'<span style="color:#505060">{asc}</span>'
            )
        self.text.setHtml("<br>".join(lines))


# ─── Log Strip ────────────────────────────────────────────────────────────────

class LogStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        hdr = QLabel("  LOG")
        hdr.setStyleSheet(
            "color:#808090; font-size:10px; font-weight:bold; letter-spacing:1.5px; "
            "padding:3px 10px; background:#141418; border-bottom:1px solid #2A2A32;"
        )
        lo.addWidget(hdr)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 11))
        self.text.setStyleSheet(
            "QTextEdit { background:#1C1C1F; color:#808090; border:none; padding:6px 8px; }"
        )
        lo.addWidget(self.text, 1)

    def log(self, msg: str, level: str = "info"):
        colors = {"ok": "#4CAF50", "info": "#4FC3F7", "warn": "#FFB74D", "err": "#EF5350"}
        ts = datetime.now().strftime("%H:%M:%S")
        color = colors.get(level, "#808090")
        self.text.append(
            f'<span style="color:#505060">{ts}</span> '
            f'<span style="color:{color}">{msg}</span>'
        )
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())


# ─── Diff widget ──────────────────────────────────────────────────────────────

class DiffWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(12,12,12,12); lo.setSpacing(8)
        self.lbl = QLabel("Ucitaj oba fajla za diff")
        self.lbl.setStyleSheet("color:#505060; padding:8px; font-size:12px;")
        lo.addWidget(self.lbl)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Region","Start","End","Velicina"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        lo.addWidget(self.table, 1)

    def show_diff(self, eng1: ME17Engine, eng2: ME17Engine):
        s = eng1.diff_summary(eng2)
        self.lbl.setText(
            f"  BOOT: {s['BOOT']:,} B    CODE: {s['CODE']:,} B    "
            f"CAL: {s['CAL']:,} B    Ukupno: {sum(s.values()):,} B razlicito"
        )
        self.lbl.setStyleSheet(
            "color:#4FC3F7; padding:8px; background:#141418; border-bottom:1px solid #2A2A32; font-size:12px;"
        )
        blocks = MapFinder(eng1).find_changed_regions(eng2, min_block=16)
        self.table.setRowCount(len(blocks))
        colors = {
            "CAL":  ("#1a3a2a","#4CAF50"),
            "CODE": ("#1A2F4A","#4FC3F7"),
            "BOOT": ("#3a2a00","#FFB74D"),
        }
        for i, b in enumerate(blocks):
            reg = "CAL" if b["in_cal"] else ("CODE" if b["in_code"] else "BOOT")
            bg, fg = colors.get(reg, ("#252529","#C0C0C8"))
            for j, txt in enumerate([reg, f"0x{b['start']:06X}", f"0x{b['end']:06X}", f"{b['size']:,} B"]):
                item = QTableWidgetItem(txt)
                item.setBackground(QBrush(QColor(bg)))
                if j == 0: item.setForeground(QBrush(QColor(fg)))
                self.table.setItem(i, j, item)


# ─── DTC Panel ────────────────────────────────────────────────────────────────

class DtcPanel(QWidget):
    """
    Prikaz i upravljanje DTC fault kodovima.
    Prikazuje se u centralnom tab widgetu kad korisnik klikne DTC u sidebaru.
    """
    action_done = pyqtSignal(str)        # poruka za log strip
    dtc_status_changed = pyqtSignal(int, bool)  # (code, is_off) — za sidebar

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dtc_eng: DtcEngine | None = None
        self._cur_code: int | None = None

        root_lo = QVBoxLayout(self)
        root_lo.setContentsMargins(0, 0, 0, 0)
        root_lo.setSpacing(0)

        # ── Detalji odabranog DTC ─────────────────────────────────────────────
        right_w = QWidget()
        right_lo = QVBoxLayout(right_w)
        right_lo.setContentsMargins(16, 12, 16, 12)
        right_lo.setSpacing(8)

        # Zaglavlje
        self._hdr = QLabel("  DTC MANAGER")
        self._hdr.setStyleSheet(
            "color:#EF5350; font-size:10px; font-weight:bold; letter-spacing:1.5px; "
            "background:#141418; padding:6px 10px; border-bottom:1px solid #2A2A32;"
        )
        right_lo.addWidget(self._hdr)

        # Status row
        status_row = QHBoxLayout(); status_row.setSpacing(16)

        self._code_lbl = QLabel("—")
        self._code_lbl.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self._code_lbl.setStyleSheet("color:#EF5350; font-size:18px; font-weight:bold;")
        status_row.addWidget(self._code_lbl)

        self._name_lbl = QLabel("")
        self._name_lbl.setStyleSheet("color:#808090; font-size:12px;")
        status_row.addWidget(self._name_lbl)

        status_row.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#4CAF50; font-size:12px; font-weight:bold;")
        status_row.addWidget(self._status_lbl)

        right_lo.addLayout(status_row)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#2A2A32; max-height:1px;")
        right_lo.addWidget(sep)

        # Notes + upozorenje
        self._notes_lbl = QLabel("")
        self._notes_lbl.setStyleSheet("color:#505060; font-size:12px;")
        self._notes_lbl.setWordWrap(True)
        right_lo.addWidget(self._notes_lbl)

        warn_lbl = QLabel("⚠  Isključivanje DTC-a deaktivira zaštitu motora!")
        warn_lbl.setStyleSheet("color:#FFB74D; font-size:12px; font-weight:bold;")
        right_lo.addWidget(warn_lbl)

        right_lo.addStretch()

        # Gumbi
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)

        self._btn_off = QPushButton("DTC OFF — Isključi")
        self._btn_off.setObjectName("btn_danger")
        self._btn_off.setFixedHeight(32)
        self._btn_off.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._btn_off.clicked.connect(self._do_off)
        btn_row.addWidget(self._btn_off)

        self._btn_on = QPushButton("DTC ON — Vrati")
        self._btn_on.setObjectName("btn_success")
        self._btn_on.setFixedHeight(32)
        self._btn_on.clicked.connect(self._do_on)
        btn_row.addWidget(self._btn_on)

        btn_row.addStretch()

        # Napredne funkcije — dropdown
        self._btn_advanced = QToolButton()
        self._btn_advanced.setText("▾ Napredno")
        self._btn_advanced.setFixedHeight(32)
        self._btn_advanced.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        adv_menu = QMenu(self._btn_advanced)
        act_all_off = adv_menu.addAction("Svi DTC OFF")
        act_all_off.triggered.connect(self._do_all_off)
        adv_menu.addSeparator()
        act_dis_all = adv_menu.addAction("Disable All Monitor")
        act_dis_all.setToolTip(
            "Nulira cijelu enable tablicu (0x021080–0x0210BD).\n"
            "Najjača opcija — ECU neće detektirati niti jedan fault.\n"
            "Koristiti oprezno: neke greške štite motor (misfire, oil pressure)."
        )
        act_dis_all.triggered.connect(self._do_disable_all)
        self._btn_advanced.setMenu(adv_menu)
        self._btn_all_off = None
        self._btn_disable_all = None
        btn_row.addWidget(self._btn_advanced)

        right_lo.addLayout(btn_row)

        root_lo.addWidget(right_w)

        self._set_buttons_enabled(False)

    def set_engine(self, eng: DtcEngine | None):
        self._dtc_eng = eng
        self._set_buttons_enabled(eng is not None)

    def show_dtc(self, dtc_code: int):
        """Prikaži status zadanog DTC-a."""
        self._cur_code = dtc_code
        if not self._dtc_eng:
            return
        status = self._dtc_eng.get_status(dtc_code)
        if not status:
            self._hdr.setText(f"  DTC P{dtc_code:04X} — NEPOZNAT")
            return
        self._refresh_display(status)

    def _refresh_display(self, status: DtcStatus):
        defn = status.defn
        self._hdr.setText(f"  DTC — {defn.p_code}  {defn.name}")
        self._code_lbl.setText(defn.p_code)
        self._name_lbl.setText(defn.name)

        if status.is_off:
            self._status_lbl.setText("● OFF")
            self._status_lbl.setStyleSheet("color:#4CAF50; font-size:12px; font-weight:bold;")
        else:
            self._status_lbl.setText("● AKTIVAN")
            self._status_lbl.setStyleSheet("color:#EF5350; font-size:12px; font-weight:bold;")

        # Obavijesti sidebar o promjeni statusa
        self.dtc_status_changed.emit(self._cur_code, status.is_off)

        self._notes_lbl.setText(defn.notes)
        self._set_buttons_enabled(True)
        self._btn_off.setEnabled(not status.is_off)
        self._btn_on.setEnabled(status.is_off)

    def _do_off(self):
        if not self._dtc_eng or self._cur_code is None:
            return
        result = self._dtc_eng.dtc_off(self._cur_code)
        msg = result.get("message", "")
        if result["status"] in ("OK", "ALREADY_OFF"):
            self.action_done.emit(f"DTC OFF: {msg}")
            status = self._dtc_eng.get_status(self._cur_code)
            if status:
                self._refresh_display(status)
        else:
            self.action_done.emit(f"GREŠKA: {msg}")

    def _do_all_off(self):
        if not self._dtc_eng:
            return
        result = self._dtc_eng.dtc_off_all()
        changed = result.get("changed", 0)
        total = result.get("total", 0)
        self.action_done.emit(f"Svi DTC OFF: {changed}/{total} isključeno.")
        if self._cur_code:
            status = self._dtc_eng.get_status(self._cur_code)
            if status:
                self._refresh_display(status)
        self.dtc_status_changed.emit(-1, True)  # -1 = sve promijenjene

    def _do_on(self):
        if not self._dtc_eng or self._cur_code is None:
            return
        result = self._dtc_eng.dtc_on(self._cur_code)
        msg = result.get("message", "")
        if result["status"] == "OK":
            self.action_done.emit(f"DTC ON: {msg}")
            status = self._dtc_eng.get_status(self._cur_code)
            if status:
                self._refresh_display(status)
        else:
            self.action_done.emit(f"GREŠKA: {msg}")

    def _do_disable_all(self):
        if not self._dtc_eng:
            return
        result = self._dtc_eng.disable_all_monitoring()
        self.action_done.emit(f"Disable All Monitor: {result.get('message', '')}")

    def _set_buttons_enabled(self, enabled: bool):
        self._btn_off.setEnabled(enabled)
        self._btn_on.setEnabled(enabled)
        self._btn_advanced.setEnabled(enabled)


# ─── Scan worker ──────────────────────────────────────────────────────────────

class ScanWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, eng: ME17Engine):
        super().__init__(); self.engine = eng

    def run(self):
        f = MapFinder(self.engine)
        self.finished.emit(f.find_all(progress_cb=lambda m: self.progress.emit(m)))


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.eng1:    ME17Engine | None = None
        self.eng2:    ME17Engine | None = None
        self.eng_ref: ME17Engine | None = None   # referentni (ORI) fajl za side-by-side
        self.editor:  MapEditor  | None = None
        self.dtc_eng: DtcEngine  | None = None
        self.maps1:   list[FoundMap]    = []
        self.maps2:   list[FoundMap]    = []
        self.maps_ref: list[FoundMap]   = []
        self._cur:    FoundMap   | None = None

        # Undo / Redo
        self._undo: list[UndoCmd] = []
        self._redo: list[UndoCmd] = []

        self._validator = SafetyValidator()

        self._build_ui()
        self._build_menus()
        self.setWindowTitle("ME17Suite  —  Bosch ME17.8.5 Rotax Editor")
        self.setMinimumSize(1280, 720)
        self.resize(1440, 900)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar
        tb = QToolBar(); tb.setMovable(False)
        self.addToolBar(tb)

        self.btn_file = _btn("+ FILE", "primary")
        self.btn_file.setToolTip("Učitaj ECU .bin  (Ctrl+1)")
        self.btn_file.clicked.connect(self._load1)
        self._act_file = tb.addWidget(self.btn_file)

        self.btn_swap = _btn("↔ Swap")
        self.btn_swap.setToolTip("Zamijeni aktivni fajl  (Ctrl+1)")
        self.btn_swap.clicked.connect(self._load1)
        self._act_swap = tb.addWidget(self.btn_swap)
        self._act_swap.setVisible(False)

        self.btn_compare = _btn("+ Compare")
        self.btn_compare.setToolTip("Dodaj fajl za usporedbu  (Ctrl+2)")
        self.btn_compare.clicked.connect(self._load2)
        self._act_compare = tb.addWidget(self.btn_compare)
        self._act_compare.setVisible(False)

        self.btn_ref = _btn("+ REF")
        self.btn_ref.setToolTip("Učitaj referentni (ORI) fajl za side-by-side prikaz")
        self.btn_ref.clicked.connect(self._load_ref)
        self._act_ref = tb.addWidget(self.btn_ref)
        self._act_ref.setVisible(False)

        tb.addSeparator()

        self.btn_save = _btn("Spremi")
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setEnabled(False); tb.addWidget(self.btn_save)

        tb.addSeparator()

        self.btn_diff = _btn("Diff")
        self.btn_diff.clicked.connect(self._show_diff)
        self.btn_diff.setEnabled(False); tb.addWidget(self.btn_diff)

        tb.addSeparator()

        self.btn_undo = _btn("↩ Undo")
        self.btn_undo.clicked.connect(self._undo_action)
        self.btn_undo.setEnabled(False); tb.addWidget(self.btn_undo)

        self.btn_redo = _btn("↪ Redo")
        self.btn_redo.clicked.connect(self._redo_action)
        self.btn_redo.setEnabled(False); tb.addWidget(self.btn_redo)

        tb.addSeparator()

        self._file_lbl = QLabel("  nema fajla")
        self._file_lbl.setStyleSheet("color:#808090; padding:0 10px; font-size:12px;")
        tb.addWidget(self._file_lbl)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0); self.progress.setMaximumHeight(2); self.progress.hide()

        # Central
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Accent bar (2px color line under toolbar, changes per SW variant) ─
        self._accent_bar = QFrame()
        self._accent_bar.setFixedHeight(2)
        self._accent_bar.setStyleSheet("background:#2A2A32; border:none;")
        root.addWidget(self._accent_bar)

        root.addWidget(self.progress)

        main_split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(main_split, 1)

        # ── Lijevi sidebar (stack: MapLibrary / DtcSidebar) ────────────────
        self._sidebar_stack = QStackedWidget()
        self.map_lib = MapLibraryPanel()
        self.map_lib.map_selected.connect(self._on_map_selected)
        self.dtc_sidebar = DtcSidebarPanel()
        self.dtc_sidebar.dtc_selected.connect(self._on_dtc_sidebar_selected)
        self.eeprom_sidebar = EepromSidebarPanel()
        self.eeprom_sidebar.entry_selected.connect(self._on_eeprom_entry_selected)
        self.can_sidebar = CanSidebarPanel()
        self.can_sidebar.id_selected.connect(self._on_can_id_selected)
        self._sidebar_stack.addWidget(self.map_lib)        # page 0
        self._sidebar_stack.addWidget(self.dtc_sidebar)    # page 1
        self._sidebar_stack.addWidget(self.eeprom_sidebar) # page 2
        self._sidebar_stack.addWidget(self.can_sidebar)    # page 3
        main_split.addWidget(self._sidebar_stack)

        # ── Centar: mapa + hex + log (vertikalni split) ────────────────────
        center_vsplit = QSplitter(Qt.Orientation.Vertical)

        # Tab widget (Map Editor | DTC Off | Diff | CAN Network | ...)
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.map_view = MapTableView()
        self.map_view.cell_clicked.connect(self._on_cell_click)
        self.map_view.btn_csv.clicked.connect(self._export_csv)
        self.map_view.bulk_edit_requested.connect(self._on_bulk_edit)
        self.tabs.addTab(self.map_view, "Map Editor")

        self.dtc_panel = DtcPanel()
        self.dtc_panel.action_done.connect(lambda msg: self.log_strip.log(msg, "ok"))
        self._dtc_tab = self.tabs.addTab(self.dtc_panel, "DTC Off")

        self.diff_widget = DiffWidget()
        self._diff_tab = self.tabs.addTab(self.diff_widget, "Diff")
        self.tabs.setTabVisible(self._diff_tab, False)

        self.map_diff_widget = MapDiffWidget()
        self._map_diff_tab = self.tabs.addTab(self.map_diff_widget, "Map Diff")
        self.tabs.setTabVisible(self._map_diff_tab, False)

        self.calc_widget = CalculatorWidget()
        self._calc_tab = self.tabs.addTab(self.calc_widget, "Kalkulator")

        self.eeprom_widget = EepromWidget()
        self._eeprom_tab = self.tabs.addTab(self.eeprom_widget, "EEPROM")

        self.can_widget = CanNetworkWidget()
        self._can_tab = self.tabs.addTab(self.can_widget, "CAN Network")

        # Vizualno naglasavanje kljucnih tabova
        _tb = self.tabs.tabBar()
        _tb.setTabTextColor(0, QColor("#9cdcfe"))               # Map Editor — plava
        _tb.setTabTextColor(self._dtc_tab, QColor("#f48771"))   # DTC Off — narandzasta
        _tb.setTabTextColor(self._can_tab, QColor("#4ec9b0"))   # CAN Network — teal

        self.tabs.currentChanged.connect(self._on_tab_changed)
        center_vsplit.addWidget(self.tabs)

        # Hex + Log — vertikalni split
        hl_split = QSplitter(Qt.Orientation.Vertical)
        self.hex_strip = HexStrip()
        self.log_strip = LogStrip()
        hl_split.addWidget(self.hex_strip)
        hl_split.addWidget(self.log_strip)
        hl_split.setSizes([110, 60])
        hl_split.setMinimumHeight(100)
        center_vsplit.addWidget(hl_split)

        center_vsplit.setSizes([680, 170])
        main_split.addWidget(center_vsplit)

        # ── Desni properties panel ─────────────────────────────────────────
        self.props = PropertiesPanel()
        self.props.edit_requested.connect(self._on_edit)
        self.props.undo_to_cmd_requested.connect(self._undo_to_cmd)
        main_split.addWidget(self.props)

        main_split.setSizes([270, 900, 270])
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)
        main_split.setStretchFactor(2, 0)

        # Status bar — with gauge labels
        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage("ME17Suite — Ucitaj .bin fajl  (Ctrl+1)")

        # Permanent gauge labels (right side of status bar)
        self._sb_sw_lbl = QLabel("")
        self._sb_sw_lbl.setStyleSheet(
            "font-family:Consolas; font-size:11px; font-weight:bold; "
            "padding:0 10px; color:#4FC3F7;"
        )
        self._sb_sw_lbl.hide()
        self.status.addPermanentWidget(self._sb_sw_lbl)

        self._sb_maps_lbl = QLabel("")
        self._sb_maps_lbl.setStyleSheet(
            "font-family:Consolas; font-size:10px; "
            "background:#1A2F4A; color:#4FC3F7; border-radius:8px; "
            "padding:1px 8px; margin:0 4px;"
        )
        self._sb_maps_lbl.hide()
        self.status.addPermanentWidget(self._sb_maps_lbl)

        self._sb_region_lbl = QLabel("")
        self._sb_region_lbl.setStyleSheet(
            "font-family:Consolas; font-size:10px; "
            "background:#3a2a00; color:#FFB74D; border-radius:8px; "
            "padding:1px 8px; margin:0 4px;"
        )
        self._sb_region_lbl.hide()
        self.status.addPermanentWidget(self._sb_region_lbl)

        # Scan progress animation state
        self._scan_dots = 0
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._scan_progress_tick)
        self._scan_msg_base = "Skeniranje"

    # ── Accent bar + status gauge helpers ─────────────────────────────────────

    def _update_accent_bar(self, sw_id: str):
        """Update the 2px accent bar color based on SW variant."""
        color = _sw_accent_color(sw_id)
        self._accent_bar.setStyleSheet(f"background:{color}; border:none;")

    def _update_sb_sw(self, sw_id: str, n_maps: int | None = None):
        """Update the status bar SW ID badge and optionally maps count."""
        if sw_id:
            color = _sw_badge_color(sw_id)
            self._sb_sw_lbl.setStyleSheet(
                f"font-family:Consolas; font-size:11px; font-weight:bold; "
                f"padding:0 10px; color:{color};"
            )
            self._sb_sw_lbl.setText(sw_id)
            self._sb_sw_lbl.show()
        if n_maps is not None:
            self._sb_maps_lbl.setText(f"  {n_maps} mapa  ")
            self._sb_maps_lbl.show()

    def _update_sb_region(self, addr: int | None):
        """Show BOOT/CODE/CAL region badge when a map is selected."""
        if addr is None:
            self._sb_region_lbl.hide()
            return
        if addr < 0x010000:
            region, bg, fg = "BOOT", "#3a2a00", "#FFB74D"
        elif addr < 0x060000:
            region, bg, fg = "CODE", "#1A2F4A", "#4FC3F7"
        else:
            region, bg, fg = "CAL", "#1a3a2a", "#4CAF50"
        self._sb_region_lbl.setStyleSheet(
            f"font-family:Consolas; font-size:10px; "
            f"background:{bg}; color:{fg}; border-radius:8px; "
            f"padding:1px 8px; margin:0 4px;"
        )
        self._sb_region_lbl.setText(f"  {region}  ")
        self._sb_region_lbl.show()

    def _scan_progress_cb(self, msg: str):
        """Progress callback during map scan — animated dots in status bar."""
        self._scan_msg_base = msg
        # Timer already running if scan is in progress

    def _scan_progress_tick(self):
        """QTimer slot — cycles 1/2/3 dots on the status bar message."""
        self._scan_dots = (self._scan_dots % 3) + 1
        dots = "." * self._scan_dots
        self.status.showMessage(f"{self._scan_msg_base}{dots}")

    def _build_menus(self):
        mb = self.menuBar()

        fm = mb.addMenu("Fajl")
        self._add_action(fm, "Otvori Fajl 1  (Ctrl+1)", "Ctrl+1", self._load1)
        self._add_action(fm, "Otvori Fajl 2  (Ctrl+2)", "Ctrl+2", self._load2)
        fm.addSeparator()
        self._add_action(fm, "Spremi  (Ctrl+S)",   "Ctrl+S", self._save)
        self._add_action(fm, "Spremi kao...",       "",       self._save_as)
        fm.addSeparator()
        self._add_action(fm, "Export CSV...",       "",       self._export_csv)
        fm.addSeparator()
        self._add_action(fm, "Otvori EEPROM dump...", "",    self._open_eeprom)
        fm.addSeparator()
        self._add_action(fm, "Izlaz  (Ctrl+Q)",    "Ctrl+Q", self.close)

        em = mb.addMenu("Editovanje")
        self._add_action(em, "Undo  (Ctrl+Z)",     "Ctrl+Z", self._undo_action)
        self._add_action(em, "Redo  (Ctrl+Y)",     "Ctrl+Y", self._redo_action)

        tm = mb.addMenu("Alati")
        self._add_action(tm, "Skeniraj mape  (F5)", "F5",    self.scan_maps)
        self._add_action(tm, "Prikazi Diff (regije)", "",     self._show_diff)
        self._add_action(tm, "Prikazi Map Diff",      "",     self._show_map_diff)
        tm.addSeparator()
        self._add_action(tm, "Kalkulator  (Ctrl+K)", "Ctrl+K",
                         lambda: self.tabs.setCurrentIndex(self._calc_tab))
        tm.addSeparator()
        self._add_action(tm, "Checksum analiza...", "",       self._checksum_analysis)

        hm = mb.addMenu("Pomoc")
        self._add_action(hm, "O programu", "", self._about)

    @staticmethod
    def _add_action(menu, label, shortcut, slot):
        a = QAction(label, menu.parent())
        if shortcut: a.setShortcut(shortcut)
        a.triggered.connect(slot)
        menu.addAction(a)

    # ── Tab / Sidebar ─────────────────────────────────────────────────────────

    def _on_tab_changed(self, idx: int):
        if idx == self._dtc_tab:
            self._sidebar_stack.setCurrentIndex(1)
        elif idx == self._eeprom_tab:
            self._sidebar_stack.setCurrentIndex(2)
        elif idx == self._can_tab:
            self._sidebar_stack.setCurrentIndex(3)
        else:
            self._sidebar_stack.setCurrentIndex(0)

    def _on_dtc_sidebar_selected(self, code: int):
        self.dtc_panel.show_dtc(code)
        if self.dtc_eng:
            status = self.dtc_eng.get_status(code)
            if status:
                self.props.show_dtc_details(status)

    def _on_dtc_status_changed(self, code: int, is_off: bool):
        if code == -1:
            # sve promijenjene (Svi DTC OFF)
            self.dtc_sidebar.refresh_status()
        else:
            self.dtc_sidebar.refresh_one(code, is_off)
            if self.dtc_eng:
                status = self.dtc_eng.get_status(code)
                if status:
                    self.props.show_dtc_details(status)

    def _on_eeprom_entry_selected(self, key: str):
        self.eeprom_widget.show_entry(key)

    def _on_can_id_selected(self, can_id: int):
        self.can_widget.show_id(can_id)

    def _populate_can_sidebar(self):
        from ui.can_network_widget import CAN_ID_INFO
        ids = sorted(CAN_ID_INFO.items())
        self.can_sidebar.populate([(can_id, info[0]) for can_id, info in ids])

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load1(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori Fajl 1", str(Path.home()), "Binary (*.bin);;Svi fajlovi (*)"
        )
        if not path: return
        try:
            eng = ME17Engine(); info = eng.load(path)
            self.eng1 = eng; self.editor = MapEditor(eng)
            self.dtc_eng = DtcEngine(eng)
            self.dtc_panel.set_engine(self.dtc_eng)
            self.dtc_panel.dtc_status_changed.connect(self._on_dtc_status_changed)
            self.dtc_sidebar.set_engine(self.dtc_eng)
            self.can_widget.set_engine(eng)
            # Napuni CAN sidebar s ID-ovima iz widgeta
            self._populate_can_sidebar()
            name = Path(path).name
            self._file_lbl.setText(
                f"  <b style='color:#9cdcfe'>{info.sw_id}</b>"
                f"  <span style='color:#888888'>{name}</span>"
            )
            self._file_lbl.setTextFormat(Qt.TextFormat.RichText)
            self._act_file.setVisible(False)
            self._act_swap.setVisible(True)
            self._act_compare.setVisible(True)
            self._act_ref.setVisible(True)
            self.btn_save.setEnabled(True)
            # Auto-postavi SW variant filter u Map Library
            self.map_lib.auto_set_sw_filter(info.sw_id)
            # Update accent bar and SW badge
            self._update_accent_bar(info.sw_id)
            self._update_sb_sw(info.sw_id)
            self.props.show_ecu(eng)
            self.log_strip.log(f"Ucitan: {name}", "ok")
            self.log_strip.log(f"SW: {info.sw_id} — {info.sw_desc}", "info")
            self.log_strip.log(f"MCU: {'TC1762 OK' if info.mcu_confirmed else 'NEPOTVRDJEN'}", "info")
            self.status.showMessage(f"{info.sw_id}  —  {info.sw_desc}")
            self.setWindowTitle(f"ME17Suite  —  {info.sw_id}  [{name}]")
            self._undo.clear(); self._redo.clear(); self._upd_undo_btns()
            QTimer.singleShot(100, self.scan_maps)
        except Exception as e:
            QMessageBox.critical(self, "Greska", str(e))
            self.log_strip.log(f"Greska: {e}", "err")

    def _load2(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori Fajl 2", str(Path.home()), "Binary (*.bin);;Svi fajlovi (*)"
        )
        if not path: return
        try:
            eng = ME17Engine(); info = eng.load(path)
            self.eng2 = eng; name = Path(path).name
            self.log_strip.log(f"Fajl 2: {name}", "ok")
            self.log_strip.log(f"SW: {info.sw_id} — {info.sw_desc}", "info")
            self.btn_diff.setEnabled(True)
            self.tabs.setTabVisible(self._diff_tab, True)
            self.tabs.setTabVisible(self._map_diff_tab, True)
            w = ScanWorker(eng); w.finished.connect(self._done2); w.start(); self._w2 = w
        except Exception as e:
            QMessageBox.critical(self, "Greska", str(e))

    def _load_ref(self):
        """Učitaj referentni fajl za ORI/REF side-by-side prikaz."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori referentni (ORI) fajl", str(Path.home()),
            "Binary (*.bin);;Svi fajlovi (*)"
        )
        if not path: return
        try:
            eng = ME17Engine(); info = eng.load(path)
            self.eng_ref = eng; name = Path(path).name
            self.log_strip.log(f"REF: {name}", "ok")
            self.log_strip.log(f"REF SW: {info.sw_id} — {info.sw_desc}", "info")
            w = ScanWorker(eng); w.finished.connect(self._done_ref); w.start(); self._w_ref = w
        except Exception as e:
            QMessageBox.critical(self, "Greska ucitavanja REF", str(e))

    def _done_ref(self, maps: list["FoundMap"]):
        self.maps_ref = maps
        self.log_strip.log(f"REF: {len(maps)} mapa.", "ok")
        # Ako je trenutno prikazana mapa, osvježi s REF
        if self._cur and self._cur.defn.category != "dtc":
            self._on_map_selected(self._cur)
        # Ažuriraj REF label u tablici
        if self.eng_ref:
            info = self.eng_ref.info
            self.map_view._lbl_f2.setText(
                f"  REF  —  {info.sw_id}  (read-only)"
            )

    def _save(self):
        if not self.eng1: return
        if not self.eng1.dirty:
            self.status.showMessage("Nema izmjena."); return

        # Auto-checksum provjera pri save
        try:
            cs_eng = ChecksumEngine(self.eng1)
            old_cs = self.eng1.get_bytes()[0x30:0x34]
            old_cs_val = int.from_bytes(old_cs, "little")
            # Provjeri promjenu checksuma
            cs_result = cs_eng.verify()
            cs_status = cs_result.get("sw_id", {}).get("status", "")
            if cs_status != "OK":
                reply = QMessageBox.question(
                    self, "Checksum",
                    f"Checksum nije ispravan (status: {cs_status}).\n"
                    f"Trenutni: 0x{old_cs_val:08X}\n\n"
                    "Napomena: Promjena CODE mapa ne zahtijeva promjenu CS.\n"
                    "CS je potreban samo za promjene u BOOT regiji.\n\n"
                    "Spremi svejedno?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        except Exception:
            pass  # checksum provjera nije kritična

        self.eng1.save()
        self.log_strip.log("Fajl snimljen.", "ok")
        self.status.showMessage("Snimljeno.")

    def _save_as(self):
        if not self.eng1: return
        path, _ = QFileDialog.getSaveFileName(
            self, "Spremi kao", str(Path.home()), "Binary (*.bin);;Svi fajlovi (*)"
        )
        if path:
            self.eng1.save(path)
            self.log_strip.log(f"Snimljeno kao: {Path(path).name}", "ok")

    # ── Scan ──────────────────────────────────────────────────────────────────

    def scan_maps(self):
        if not self.eng1: return
        self.progress.show()
        self._scan_msg_base = "Skeniranje"
        self._scan_dots = 0
        self._scan_timer.start(400)
        self.status.showMessage("Skeniranje...")
        self.log_strip.log("Skeniranje mapa...", "info")
        w = ScanWorker(self.eng1)
        w.progress.connect(self._scan_progress_cb)
        w.finished.connect(self._done1); w.start(); self._w1 = w

    def _done1(self, maps):
        self.maps1 = maps
        self._scan_timer.stop()
        self.progress.hide()
        self.map_lib.populate(maps)
        self.log_strip.log(f"Pronadjeno {len(maps)} mapa.", "ok")
        self.status.showMessage(f"✓ {len(maps)} mapa učitano.")
        # Update maps count badge in status bar
        if self.eng1:
            self._update_sb_sw(self.eng1.info.sw_id, len(maps))

    def _done2(self, maps):
        self.maps2 = maps
        self.log_strip.log(f"Fajl 2: {len(maps)} mapa pronadjeno.", "ok")
        # Označi razlike u stablu
        self.map_lib.mark_diff(maps)
        # Osvježi trenutno prikazanu mapu da se doda usporedba
        if self._cur and self._cur.defn.category != "dtc":
            self._on_map_selected(self._cur)

    # ── Map selection ─────────────────────────────────────────────────────────

    def _on_map_selected(self, fm: FoundMap):
        self._cur = fm
        if fm.defn.category == "dtc":
            # DTC tab: prikaži DTC panel umjesto tablice mapa
            dtc_code = DTC_REGISTRY and next(
                (code for code, d in DTC_REGISTRY.items() if d.p_code in fm.defn.name),
                None
            )
            if dtc_code and self.dtc_eng:
                self.dtc_panel.show_dtc(dtc_code)
                self.tabs.setCurrentIndex(self._dtc_tab)
                status = self.dtc_eng.get_status(dtc_code)
                if status: self.props.show_dtc_details(status)
                if self.eng1: self.hex_strip.show(self.eng1, fm.address)
                self.status.showMessage(
                    f"DTC {fm.defn.name}  @  0x{fm.address:06X}  —  enable {fm.defn.cols}B"
                )
            return

        # Pronađi compare mapu — prioritet: REF fajl, zatim Fajl 2
        fm_ref = next((m for m in self.maps_ref if m.defn.name == fm.defn.name), None)
        fm2    = next((m for m in self.maps2    if m.defn.name == fm.defn.name), None)
        compare = fm_ref or fm2

        self.map_view.show_map(fm, compare)
        # Ažuriraj label za REF vs Fajl 2
        if compare:
            src = "REF" if fm_ref else "Fajl 2"
            self.map_view._lbl_f2.setText(
                f"  {src}  —  {compare.sw_id}  @ 0x{compare.address:06X}  (read-only)"
            )
        self.props.show_map_stats(fm)
        if self.eng1: self.hex_strip.show(self.eng1, fm.address)
        self.tabs.setCurrentIndex(0)
        cmp = "  |  REF aktivna" if fm_ref else ("  |  Fajl 2 aktivna" if fm2 else "")
        self.status.showMessage(f"{fm.defn.name}  @  0x{fm.address:06X}  {fm.defn.rows}×{fm.defn.cols}  {fm.defn.unit}{cmp}")
        # Region badge in status bar
        self._update_sb_region(fm.address)

    # ── Cell click ────────────────────────────────────────────────────────────

    def _on_cell_click(self, row: int, col: int, fm: FoundMap):
        # Pronađi referentnu mapu za delta prikaz
        fm_ref = next((m for m in self.maps_ref if m.defn.name == fm.defn.name), None)
        fm_cmp = fm_ref or next((m for m in self.maps2 if m.defn.name == fm.defn.name), None)
        if fm_cmp:
            self.props.show_cell_with_delta(row, col, fm, fm_cmp)
        else:
            self.props.show_cell(row, col, fm)
        addr = fm.address + (row * fm.defn.cols + col) * fm.defn.cell_bytes
        if self.eng1: self.hex_strip.show(self.eng1, addr)
        raw = fm.data[row * fm.defn.cols + col]
        self.status.showMessage(
            f"{fm.defn.name}  [{row},{col}]  raw:{raw}  disp:{raw*fm.defn.scale:.3f}{fm.defn.unit}"
            f"  ADDR:0x{addr:06X}"
        )

    # ── Edit + Undo/Redo ──────────────────────────────────────────────────────

    def _on_edit(self, row: int, col: int, display_val: float):
        if not self.editor or not self._cur: return
        defn = self._cur.defn
        idx  = row * defn.cols + col
        old_raw = self._cur.data[idx] if idx < len(self._cur.data) else 0

        # Safety validation — ERROR blokira, WARNING propušta s porukom
        sv = self._validator.validate_edit(defn, row, col, display_val)
        if sv.level == SvLevel.ERROR:
            self.log_strip.log(f"SIGURNOST BLOKIRA: {sv.message}", "err")
            self.status.showMessage(f"Blokirano: {sv.message}")
            return
        if sv.level == SvLevel.WARNING:
            self.log_strip.log(f"UPOZORENJE: {sv.message}", "warn")
            self.status.showMessage(f"Upozorenje: {sv.message}")

        result = self.editor.write_cell(self._cur, row, col, display_val)
        if not result.ok:
            self.log_strip.log(f"GRESKA: {result.message}", "err")
            self.status.showMessage(f"GRESKA: {result.message}"); return

        new_raw = round((display_val - defn.offset_val) / defn.scale) if defn.scale else 0
        self._cur.data[idx] = new_raw

        # Undo stack
        cmd = UndoCmd(self._cur, row, col, old_raw, new_raw)
        self._undo.append(cmd)
        self._redo.clear(); self._upd_undo_btns()

        # History panel
        self.props.push_history(cmd)

        self.map_view.refresh_cell(row, col, new_raw)
        self.props.show_cell(row, col, self._cur)
        self.props.show_map_stats(self._cur)
        self.log_strip.log(result.message, "warn")
        self.status.showMessage(result.message)

    def _on_bulk_edit(self, cells: list, op: str, val: float):
        """Bulk operacija na selektiranim ćelijama s Undo podrškom."""
        if not self.editor or not self._cur: return
        defn = self._cur.defn

        cmds = []
        for row, col in cells:
            idx = row * defn.cols + col
            if idx >= len(self._cur.data): continue
            old_raw = self._cur.data[idx]
            disp_old = old_raw * defn.scale + defn.offset_val if defn.scale else float(old_raw)

            if op == "scale":
                new_disp = disp_old * val
            elif op == "offset":
                new_disp = disp_old + val
            elif op == "copy_ref":
                if self._fm2_for_cur():
                    fm2 = self._fm2_for_cur()
                    new_raw = fm2.data[idx] if idx < len(fm2.data) else old_raw
                    new_disp = new_raw * defn.scale + defn.offset_val if defn.scale else float(new_raw)
                else:
                    continue
            elif op == "smooth":
                # Smooth: obradi po retku
                row_cells = [(r, c) for r, c in cells if r == row]
                if len(row_cells) < 2: continue
                row_cells.sort(key=lambda x: x[1])
                first_c = row_cells[0][1]
                last_c  = row_cells[-1][1]
                n_span  = last_c - first_c
                if n_span == 0: continue
                idx_first = row * defn.cols + first_c
                idx_last  = row * defn.cols + last_c
                d_first = self._cur.data[idx_first] * defn.scale + defn.offset_val if defn.scale else float(self._cur.data[idx_first])
                d_last  = self._cur.data[idx_last]  * defn.scale + defn.offset_val if defn.scale else float(self._cur.data[idx_last])
                t = (col - first_c) / n_span
                new_disp = d_first + t * (d_last - d_first)
            else:
                continue

            # Primijeni promjenu kroz editor
            result = self.editor.write_cell(self._cur, row, col, new_disp)
            if result.ok:
                new_raw = round((new_disp - defn.offset_val) / defn.scale) if defn.scale else int(new_disp)
                # Clamp na raw_max
                raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max
                new_raw = max(defn.raw_min, min(raw_max, new_raw))
                self._cur.data[idx] = new_raw
                self.map_view.refresh_cell(row, col, new_raw)
                cmds.append(UndoCmd(self._cur, row, col, old_raw, new_raw))

        if cmds:
            # Dodaj sve promjene u undo stack
            self._undo.extend(cmds)
            self._redo.clear()
            self._upd_undo_btns()
            for cmd in cmds:
                self.props.push_history(cmd)
            self.log_strip.log(f"Bulk {op}: {len(cmds)} ćelija promijenjeno.", "ok")
            self.status.showMessage(f"Bulk {op}: {len(cmds)} ćelija.")

    def _fm2_for_cur(self) -> "FoundMap | None":
        """Vrati referentnu mapu (REF ili Fajl 2) za trenutnu mapu."""
        if not self._cur: return None
        return (next((m for m in self.maps_ref if m.defn.name == self._cur.defn.name), None)
                or next((m for m in self.maps2  if m.defn.name == self._cur.defn.name), None))

    def _undo_action(self):
        if not self._undo or not self.editor: return
        cmd = self._undo.pop()
        self._apply_cmd(cmd, cmd.old_raw)
        self._redo.append(cmd); self._upd_undo_btns()
        self.log_strip.log(f"Undo: [{cmd.row},{cmd.col}] {cmd.new_raw} -> {cmd.old_raw}", "info")

    def _redo_action(self):
        if not self._redo or not self.editor: return
        cmd = self._redo.pop()
        self._apply_cmd(cmd, cmd.new_raw)
        self._undo.append(cmd); self._upd_undo_btns()
        self.log_strip.log(f"Redo: [{cmd.row},{cmd.col}] {cmd.old_raw} -> {cmd.new_raw}", "info")

    def _apply_cmd(self, cmd: UndoCmd, target_raw: int):
        defn = cmd.fm.defn
        disp = target_raw * defn.scale + defn.offset_val if defn.scale else float(target_raw)
        self.editor.write_cell(cmd.fm, cmd.row, cmd.col, disp)
        cmd.fm.data[cmd.row * defn.cols + cmd.col] = target_raw
        if cmd.fm is self._cur:
            self.map_view.refresh_cell(cmd.row, cmd.col, target_raw)
            self.props.show_cell(cmd.row, cmd.col, cmd.fm)

    def _undo_to_cmd(self, target_cmd):
        """Undo do (i uključujući) zadanu komandu iz History liste."""
        if not self.editor: return
        while self._undo:
            cmd = self._undo[-1]
            self._undo.pop()
            self._apply_cmd(cmd, cmd.old_raw)
            self._redo.append(cmd)
            self._upd_undo_btns()
            self.log_strip.log(f"Undo: [{cmd.row},{cmd.col}] {cmd.new_raw} → {cmd.old_raw}", "info")
            if cmd is target_cmd:
                break

    def _upd_undo_btns(self):
        self.btn_undo.setEnabled(bool(self._undo))
        self.btn_redo.setEnabled(bool(self._redo))
        u = len(self._undo); r = len(self._redo)
        self.btn_undo.setText(f"Undo ({u})" if u else "Undo")
        self.btn_redo.setText(f"Redo ({r})" if r else "Redo")

    # ── CSV Export ────────────────────────────────────────────────────────────

    def _export_csv(self):
        fm = self._cur
        if not fm:
            self.status.showMessage("Odaberi mapu za export."); return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", str(Path.home() / f"{fm.defn.name}.csv"), "CSV (*.csv)"
        )
        if not path: return
        defn = fm.defn
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                # Header: naziv mape, adresa, format
                w.writerow([f"# {defn.name}", f"@0x{fm.address:06X}",
                            f"{defn.rows}x{defn.cols}", defn.dtype, f"x{defn.scale}", defn.unit])
                # X osa
                x = (defn.axis_x.values[:defn.cols]
                     if defn.axis_x and defn.axis_x.values else list(range(defn.cols)))
                w.writerow([""] + [str(v) for v in x])
                # Redovi
                grid = fm.get_2d_display()
                for r_idx, row in enumerate(grid):
                    y_lbl = (str(defn.axis_y.values[r_idx])
                             if defn.axis_y and defn.axis_y.values and r_idx < len(defn.axis_y.values)
                             else str(r_idx))
                    w.writerow([y_lbl] + [f"{v:.4f}" for v in row])
            self.log_strip.log(f"CSV export: {Path(path).name}", "ok")
            self.status.showMessage(f"Exportovano: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Export greska", str(e))

    # ── EEPROM ────────────────────────────────────────────────────────────────

    def _open_eeprom(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori EEPROM dump", "",
            "Binary fajlovi (*.bin);;Svi fajlovi (*)"
        )
        if not path:
            return
        self.eeprom_widget.load_file(path)
        self.tabs.setCurrentIndex(self._eeprom_tab)
        self.log_strip.log(f"EEPROM učitan: {path}", "ok")

    # ── Diff ──────────────────────────────────────────────────────────────────

    def _show_diff(self):
        if not (self.eng1 and self.eng2):
            self.status.showMessage("Ucitaj oba fajla."); return
        self.diff_widget.show_diff(self.eng1, self.eng2)
        self.tabs.setCurrentIndex(self._diff_tab)

    def _show_map_diff(self):
        if not (self.eng1 and self.eng2):
            self.status.showMessage("Ucitaj oba fajla."); return
        info1 = self.eng1.get_info() if hasattr(self.eng1, "get_info") else None
        info2 = self.eng2.get_info() if hasattr(self.eng2, "get_info") else None
        sw1 = info1.sw_id if info1 else "Fajl 1"
        sw2 = info2.sw_id if info2 else "Fajl 2"
        self.log_strip.log("Map Diff: skeniranje mapa...", "info")
        try:
            differ = MapDiffer(self.eng1, self.eng2)
            self.map_diff_widget.load_diff(differ, sw1, sw2)
            self.tabs.setCurrentIndex(self._map_diff_tab)
            self.log_strip.log("Map Diff: gotovo.", "ok")
        except Exception as e:
            self.log_strip.log(f"Map Diff greska: {e}", "err")

    # ── Checksum analiza ──────────────────────────────────────────────────────

    def _checksum_analysis(self):
        if not self.eng1:
            self.status.showMessage("Ucitaj fajl."); return
        cs = ChecksumEngine(self.eng1)
        results = cs.verify()
        candidates = cs.find_checksum_candidates()

        lines = ["=== CHECKSUM ANALIZA ===\n"]
        for k, v in results.items():
            if isinstance(v, dict):
                lines.append(f"{k}:")
                for kk, vv in v.items(): lines.append(f"  {kk}: {vv}")
            else:
                lines.append(f"{k}: {v}")

        lines.append(f"\n=== KANDIDATI U BOOT 0x000-0x100 ({len(candidates)} komada) ===")
        for c in candidates[:20]:
            lines.append(f"  {c['offset']:>4}  {c['value']}  {c['type']}")

        if self.eng2:
            lines.append("\n=== BOOT DIFF (ORI vs STG2) ===")
            boot_diffs = cs.analyze_boot_diff(self.eng2)
            lines.append(f"  Promijenjenih bajtova u BOOT: {boot_diffs['total_changed']}")
            lines.append(f"  Blokovi (>=4B): {len(boot_diffs['blocks'])}")
            for b in boot_diffs['blocks']:
                lines.append(
                    f"  0x{b['offset']:06X}  {b['size']}B  "
                    f"ORI:{b['val_ori']}  STG2:{b['val_stg2']}"
                )

        txt = "\n".join(lines)
        QMessageBox.information(self, "Checksum analiza", txt[:3000])
        self.log_strip.log("Checksum analiza zavrsena.", "info")

    # ── About ─────────────────────────────────────────────────────────────────

    def _about(self):
        QMessageBox.information(self, "O programu",
            "ME17Suite\nBosch ME17.8.5 by Rotax\n\n"
            "MCU: Infineon TC1762 (TriCore, Little Endian)\n"
            "SW: 10SW066726 (ORI) / 10SW040039 (NPRo STG2)\n\n"
            "Mape: Ignition 14×12×12, Injection 12×32,\n"
            "      Torque 16×16, Lambda 12×18, Rev Limiter×5\n\n"
            "Faza 3: Undo/Redo, CSV export\n"
            "Faza 4: Checksum analiza (u toku)"
        )

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_F5: self.scan_maps()
        super().keyPressEvent(e)


# ─── Entry ────────────────────────────────────────────────────────────────────

def run():
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    win = MainWindow()
    win.show()
    return app.exec()
