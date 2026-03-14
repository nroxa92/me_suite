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
    QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QBrush, QAction, QFont, QKeySequence

from core.engine import ME17Engine
from core.map_finder import MapFinder, FoundMap, MapDef
from core.map_editor import MapEditor, EditResult
from core.checksum import ChecksumEngine
from core.dtc import DtcEngine, DTC_REGISTRY, DtcStatus


# ─── Stylesheet ───────────────────────────────────────────────────────────────

STYLESHEET = """
* {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #cccccc;
}

QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
}

/* ── MENUBAR ── */
QMenuBar {
    background: #323233;
    color: #cccccc;
    border-bottom: 1px solid #111;
    padding: 2px 4px;
    font-size: 13px;
}
QMenuBar::item {
    padding: 4px 10px;
    border-radius: 3px;
    background: transparent;
}
QMenuBar::item:selected { background: #444444; color: #ffffff; }
QMenu {
    background: #252526;
    color: #cccccc;
    border: 1px solid #454545;
    padding: 3px 0;
}
QMenu::item { padding: 5px 20px 5px 12px; }
QMenu::item:selected { background: #04395e; color: #ffffff; }
QMenu::separator { height: 1px; background: #333333; margin: 3px 0; }

/* ── TOOLBAR ── */
QToolBar {
    background: #2d2d2d;
    border-bottom: 1px solid #111;
    padding: 4px 8px;
    spacing: 3px;
}
QToolBar::separator { width: 1px; background: #555555; margin: 3px 5px; }
QToolButton {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 12px;
    color: #cccccc;
    font-size: 13px;
}
QToolButton:hover { background: #4a4a4a; border-color: #666666; }
QToolButton:pressed { background: #2a2a2a; }
QToolButton:checked { background: #0e639c; border-color: #1177bb; color: #ffffff; }

/* ── GUMBI ── */
QPushButton {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 12px;
    color: #cccccc;
    font-size: 13px;
    min-height: 26px;
}
QPushButton:hover { background: #4a4a4a; border-color: #666666; }
QPushButton:pressed { background: #2a2a2a; }
QPushButton:disabled { background: #2a2a2a; color: #555555; border-color: #3a3a3a; }
QPushButton#btn_primary {
    background: #0e639c;
    border-color: #1177bb;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btn_primary:hover { background: #1177bb; }
QPushButton#primary {
    background: #0e639c;
    border-color: #1177bb;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#primary:hover { background: #1177bb; }
QPushButton#btn_success { background: #007a4d; border-color: #009960; color: #ffffff; }
QPushButton#btn_danger { background: #3c3c3c; border-color: #555555; color: #f48771; }
QPushButton#btn_danger:hover { background: #4a2020; border-color: #f48771; }

/* ── TREE WIDGET ── */
QTreeWidget {
    background: #252526;
    border: none;
    color: #cccccc;
    font-size: 13px;
    outline: none;
    show-decoration-selected: 1;
}
QTreeWidget::item { padding: 4px 4px; border-left: 2px solid transparent; }
QTreeWidget::item:hover { background: #2a2d2e; }
QTreeWidget::item:selected {
    background: #04395e;
    color: #ffffff;
    border-left: 2px solid #0e639c;
}
QTreeWidget::branch { background: #252526; }

/* ── TABLICA ── */
QTableWidget {
    background: #1e1e1e;
    border: none;
    gridline-color: #2a2a2a;
    color: #cccccc;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    selection-background-color: #04395e;
}
QTableWidget::item { padding: 2px 4px; border: none; }
QTableWidget::item:selected { background: #04395e; color: #ffffff; }
QHeaderView::section {
    background: #2d2d2d;
    color: #666666;
    padding: 4px 6px;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
    font-family: "Consolas", monospace;
    font-size: 11px;
    font-weight: normal;
}

/* ── SCROLL BAROVI ── */
QScrollBar:vertical { background: #252526; width: 10px; border: none; }
QScrollBar::handle:vertical {
    background: #555555; border-radius: 5px; min-height: 20px; margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #777777; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #252526; height: 10px; border: none; }
QScrollBar::handle:horizontal {
    background: #555555; border-radius: 5px; min-width: 20px; margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #777777; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── TAB WIDGET ── */
QTabWidget::pane { border: none; border-top: 1px solid #333333; background: #252526; }
QTabBar::tab {
    background: #252526;
    color: #969696;
    padding: 7px 20px;
    border-top: 2px solid transparent;
    font-size: 13px;
}
QTabBar::tab:hover { color: #cccccc; background: #2d2d2d; }
QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; border-top-color: #0e639c; }

/* ── LINE EDIT ── */
QLineEdit {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 10px;
    color: #cccccc;
    font-size: 13px;
    selection-background-color: #0e639c;
}
QLineEdit:focus { border-color: #0e639c; background: #2a2a2a; }
QLineEdit::placeholder { color: #555555; }

/* ── SPLITTER ── */
QSplitter::handle { background: #333333; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* ── STATUS BAR ── */
QStatusBar {
    background: #007acc;
    color: rgba(255,255,255,0.9);
    font-family: "Consolas", monospace;
    font-size: 12px;
    border-top: none;
}
QStatusBar::item { border-right: 1px solid rgba(255,255,255,0.2); padding: 0 12px; }
QStatusBar QLabel { color: rgba(255,255,255,0.9); font-family: "Consolas", monospace; font-size: 12px; }

/* ── LABELE ── */
QLabel#lbl_map_title {
    font-family: "Consolas", monospace; font-size: 14px; font-weight: bold; color: #9cdcfe;
}
QLabel#lbl_section {
    font-size: 11px; font-weight: bold; letter-spacing: 1px; color: #999999;
}
QLabel#lbl_value_big {
    font-family: "Consolas", monospace; font-size: 32px; color: #9cdcfe; font-weight: bold;
}
QLabel#lbl_addr { font-family: "Consolas", monospace; font-size: 11px; color: #555555; }
QLabel#lbl_ok   { color: #4ec9b0; font-weight: bold; }
QLabel#lbl_warn { color: #e5c07b; font-weight: bold; }
QLabel#lbl_error { color: #f48771; font-weight: bold; }

/* ── GROUP BOX ── */
QGroupBox {
    border: 1px solid #333333;
    border-radius: 5px;
    margin-top: 8px;
    padding: 8px;
    color: #999999;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    background: #252526;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    background: #252526;
}

/* ── COMBO BOX ── */
QComboBox {
    background: #3c3c3c; border: 1px solid #555555; border-radius: 4px;
    padding: 5px 10px; color: #cccccc; font-size: 13px; min-height: 26px;
}
QComboBox:hover { border-color: #666666; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #252526; border: 1px solid #555555;
    selection-background-color: #04395e; color: #cccccc;
}

/* ── LIST WIDGET ── */
QListWidget {
    background: #252526; border: none; color: #cccccc;
    font-family: "Consolas", monospace; font-size: 12px; outline: none;
}
QListWidget::item { padding: 3px 8px; border-bottom: 1px solid #2a2a2a; }
QListWidget::item:hover { background: #2a2d2e; }
QListWidget::item:selected { background: #04395e; color: #ffffff; }

/* ── TOOLTIP ── */
QToolTip {
    background: #2d2d2d; color: #cccccc; border: 1px solid #555555;
    padding: 4px 8px; font-size: 12px; border-radius: 3px;
}

/* ── MESSAGE BOX ── */
QMessageBox { background: #252526; color: #cccccc; }

/* ── PROGRESS BAR ── */
QProgressBar {
    background: #3c3c3c; border: 1px solid #555555; border-radius: 4px;
    height: 6px; text-align: center; color: transparent;
}
QProgressBar::chunk { background: #0e639c; border-radius: 4px; }
"""


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
        "dtc":         ("❗ DTC / Faults","#9cdcfe"),
        "misc":        ("  Other",         "#9cdcfe"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self._all: list[FoundMap] = []
        self._compare: list[FoundMap] = []

        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        self._hdr = QLabel("  MAP LIBRARY")
        self._hdr.setStyleSheet(
            "background:#252526; color:#666666; font-size:11px; font-weight:bold; "
            "padding:6px 8px; border-bottom:1px solid #333333; letter-spacing:1.5px;"
        )
        lo.addWidget(self._hdr)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Pretraži mape...")
        self.search.setFixedHeight(32)
        self.search.setObjectName("search_maps")
        self.search.setStyleSheet(
            "background:#2a2a2a; border:none; border-bottom:1px solid #333333; "
            "border-radius:0; padding:4px 10px; color:#cccccc; font-size:13px;"
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
        self._render(maps)

    def mark_diff(self, compare: list[FoundMap]):
        """Označi mape koje se razlikuju od fajla 2 (žuta boja stavke)."""
        self._compare = compare
        self._render(self._all)

    def _filter(self, t: str):
        self._render([m for m in self._all if t.lower() in m.defn.name.lower()] if t else self._all)

    def _render(self, maps: list[FoundMap]):
        self.tree.clear()
        cats = {}
        for key, (label, color) in self.CATEGORIES.items():
            it = QTreeWidgetItem(self.tree, [label])
            it.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Bold))
            it.setForeground(0, QBrush(QColor("#9cdcfe")))
            it.setSizeHint(0, QSize(0, 28))
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
            ch.setFont(0, QFont("Segoe UI", 13))
            if is_diff:
                ch.setForeground(0, QBrush(QColor("#e5c07b")))   # žuta = razlika
                ch.setToolTip(0, f"0x{fm.address:06X}  {dims}  {fm.defn.unit}\n"
                                  f"[RAZLIKA vs Fajl 2]\n{fm.defn.description}")
            else:
                ch.setForeground(0, QBrush(QColor("#cccccc")))
                ch.setToolTip(0, f"0x{fm.address:06X}  {dims}  {fm.defn.unit}\n{fm.defn.description}")
            ch.setSizeHint(0, QSize(0, 26))
            ch.setData(0, Qt.ItemDataRole.UserRole, fm)
        for it in cats.values():
            it.setHidden(it.childCount() == 0)

    def _click(self, item: QTreeWidgetItem):
        fm = item.data(0, Qt.ItemDataRole.UserRole)
        if fm: self.map_selected.emit(fm)


# ─── Heatmap paleta ───────────────────────────────────────────────────────────

MAP_COLORS_IGN = [
    (QColor("#1c3461"), QColor("#7eb8f7")),  # c0 — najhladniji
    (QColor("#1a4a6a"), QColor("#7ec8f7")),  # c1
    (QColor("#0d6b5c"), QColor("#7ef7e0")),  # c2
    (QColor("#1a6b2a"), QColor("#7ef79e")),  # c3
    (QColor("#4a6b0a"), QColor("#d0f77e")),  # c4 — sredina
    (QColor("#7a6000"), QColor("#f7d87e")),  # c5
    (QColor("#8a3800"), QColor("#f7b07e")),  # c6
    (QColor("#8a1800"), QColor("#f77e7e")),  # c7
    (QColor("#7a0020"), QColor("#f77ea8")),  # c8 — najvrući
]

def _cell_colors(raw_val: int, raw_min: int, raw_max: int):
    """Vrati (bg, fg) QColor par prema heatmap paleti."""
    p = (raw_val - raw_min) / max(raw_max - raw_min, 1)
    idx = min(int(p * len(MAP_COLORS_IGN)), len(MAP_COLORS_IGN) - 1)
    return MAP_COLORS_IGN[idx]


# ─── Map Table View ───────────────────────────────────────────────────────────

class MapTableView(QWidget):
    cell_clicked = pyqtSignal(int, int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        # Badge bar (naziv mape + dim/dtype/unit/addr)
        self._map_bar = QWidget()
        self._map_bar.setStyleSheet("background:#252526; border-bottom:1px solid #333333;")
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

        self.btn_copy  = _btn("Copy")
        self.btn_csv   = _btn("Export CSV")
        self.btn_reset = _btn("Reset")
        self.btn_reset.setObjectName("btn_danger")
        for b in [self.btn_copy, self.btn_csv, self.btn_reset]:
            b.setFixedHeight(26)
            b.hide()
            mbl.addWidget(b)

        lo.addWidget(self._map_bar)

        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setDefaultSectionSize(54)
        self.table.horizontalHeader().setFont(QFont("Consolas", 9))
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setFont(QFont("Consolas", 9))
        self.table.verticalHeader().setFixedWidth(44)
        self.table.setFont(QFont("Consolas", 10))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(lambda r,c: self._fm and self.cell_clicked.emit(r,c,self._fm))
        lo.addWidget(self.table, 1)

        self._fm:  FoundMap | None = None
        self._fm2: FoundMap | None = None

    @staticmethod
    def _make_badge(text: str, style: str = "blue") -> QLabel:
        lbl = QLabel(text)
        colors = {
            "blue":  "background:#0e3a5c;color:#9cdcfe;border:1px solid #0e639c;",
            "green": "background:#0d3321;color:#4ec9b0;border:1px solid #4ec9b0;",
            "gray":  "background:#2a2a2a;color:#888888;border:1px solid #444444;",
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

        rows, cols = defn.rows, defn.cols
        data  = fm.data
        data2 = compare.data if compare else None

        self.table.setRowCount(rows); self.table.setColumnCount(cols)

        x_labels = ([str(v) for v in defn.axis_x.values[:cols]]
                    if defn.axis_x and defn.axis_x.values else [str(c) for c in range(cols)])
        y_labels  = ([str(v) for v in defn.axis_y.values[:rows]]
                    if defn.axis_y and defn.axis_y.values else [f"r{r}" for r in range(rows)])
        self.table.setHorizontalHeaderLabels(x_labels)
        self.table.setVerticalHeaderLabels(y_labels)

        mn = min(data) if data else 0
        mx = max(data) if data else 1

        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx >= len(data): break
                raw = data[idx]
                txt = (f"{raw * defn.scale:.1f}" if defn.dtype == "u8"
                       else f"{raw * defn.scale:.3f}" if defn.scale != 0
                       else f"0x{raw:04X}")
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setData(Qt.ItemDataRole.UserRole, raw)
                if data2 and idx < len(data2) and data2[idx] != raw:
                    item.setBackground(QBrush(QColor("#3a3010")))
                    item.setForeground(QBrush(QColor("#e5c07b")))
                else:
                    bg, fg = _cell_colors(raw, mn, mx)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))
                self.table.setItem(r, c, item)

    def refresh_cell(self, row: int, col: int, new_raw: int):
        defn = self._fm.defn
        txt  = (f"{new_raw * defn.scale:.1f}" if defn.dtype == "u8"
                else f"{new_raw * defn.scale:.3f}" if defn.scale != 0
                else f"0x{new_raw:04X}")
        item = self.table.item(row, col)
        if not item: return
        item.setText(txt); item.setData(Qt.ItemDataRole.UserRole, new_raw)
        mn = min(self._fm.data); mx = max(self._fm.data)
        bg, fg = _cell_colors(new_raw, mn, mx)
        item.setBackground(QBrush(bg))
        item.setForeground(QBrush(fg))

    def clear(self):
        self._fm = None; self.table.setRowCount(0); self.table.setColumnCount(0)
        self._lbl_name.setText("Odaberi mapu iz stabla")
        for b in [self._badge_dim, self._badge_unit, self._badge_addr,
                  self.btn_copy, self.btn_csv, self.btn_reset]:
            b.hide()


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
            "background:#252526; color:#666666; font-size:11px; font-weight:bold; "
            "padding:6px 8px; border-bottom:1px solid #333333; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        lo.addWidget(self.tabs, 1)

        # ── Tab 0: Celija ──────────────────────────────────────────────────
        cell_w = QWidget()
        cell_lo = QVBoxLayout(cell_w); cell_lo.setContentsMargins(8,8,8,8); cell_lo.setSpacing(6)

        self._pos_lbl = QLabel("Odaberi ćeliju")
        self._pos_lbl.setStyleSheet("color:#888888; font-size:12px;")
        cell_lo.addWidget(self._pos_lbl)

        # Big value frame s border-left akcentom
        val_frame = QFrame()
        val_frame.setStyleSheet("""
            QFrame {
                background: #2a2a2a;
                border: 1px solid #333333;
                border-left: 3px solid #0e639c;
                border-radius: 5px;
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
            kl = QLabel(k+":"); kl.setStyleSheet("color:#888888; font-size:13px;")
            vl = QLabel("—")
            vl.setFont(QFont("Consolas", 11))
            vl.setStyleSheet("color:#9cdcfe; font-size:12px; font-weight:bold;")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            sg.addWidget(kl, i, 0); sg.addWidget(vl, i, 1)
            self._st[k] = vl
        map_lo.addWidget(stats_g)

        notes_g = QGroupBox("NAPOMENE")
        nl = QVBoxLayout(notes_g); nl.setContentsMargins(6,6,6,6)
        self._notes = QLabel("—")
        self._notes.setWordWrap(True)
        self._notes.setStyleSheet("color:#666666; font-size:12px;")
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
            kl = QLabel(k+":"); kl.setStyleSheet("color:#888888; font-size:13px;")
            vl = QLabel("—")
            vl.setFont(QFont("Consolas", 11))
            vl.setStyleSheet("color:#9cdcfe; font-size:12px; font-weight:bold;")
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
        mem_txt.setStyleSheet("color:#666666; font-size:12px;")
        ml.addWidget(mem_txt)
        ecu_lo.addWidget(mem_g)
        ecu_lo.addStretch()
        self.tabs.addTab(ecu_w, "ECU")

    # ── Public update metode ──────────────────────────────────────────────────

    def show_ecu(self, eng: ME17Engine):
        info = eng.info
        cs   = ChecksumEngine(eng).verify()
        self._ecu["Model"].setText("ME17.8.5")
        self._ecu["SW ID"].setText(info.sw_id)
        self._ecu["SW ID"].setStyleSheet("color:#9cdcfe; font-size:12px; font-weight:bold;")
        self._ecu["MCU"].setText("TC1762 LE" if info.mcu_confirmed else "NEPOTVRDJEN")
        self._ecu["Velicina"].setText(f"{info.file_size // 1024} KB")
        self._ecu["Platform"].setText("VM_CB.04.80.00" if info.platform_confirmed else "—")
        ok = cs.get("sw_id", {}).get("status") == "OK"
        self._ecu["Checksum"].setText("SW OK" if ok else "PENDING")
        self._ecu["Checksum"].setStyleSheet(
            f"color:{'#4ec9b0' if ok else '#e5c07b'}; font-size:12px; font-weight:bold;"
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
                "background:#2a1010; border:1px solid #f48771; border-radius:4px; padding:5px 10px;"
            )
            QTimer.singleShot(800, lambda: self._inp.setStyleSheet(""))


# ─── Hex Strip ────────────────────────────────────────────────────────────────

class HexStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        hdr = QLabel("  HEX VIEW")
        hdr.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px; "
            "padding:3px 8px; background:#252526; border-bottom:1px solid #333333;"
        )
        lo.addWidget(hdr)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 12))
        self.text.setStyleSheet(
            "QTextEdit { background:#252526; color:#666666; border:none; padding:6px 10px; }"
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
                f'<span style="color:#569cd6">0x{addr+i:06X}:</span>  '
                f'<span style="color:#888888">{hx}</span>  '
                f'<span style="color:#444444">{asc}</span>'
            )
        self.text.setHtml("<br>".join(lines))


# ─── Log Strip ────────────────────────────────────────────────────────────────

class LogStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        hdr = QLabel("  LOG")
        hdr.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px; "
            "padding:3px 8px; background:#252526; border-bottom:1px solid #333333;"
        )
        lo.addWidget(hdr)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 12))
        self.text.setStyleSheet(
            "QTextEdit { background:#252526; color:#969696; border:none; padding:6px 8px; }"
        )
        lo.addWidget(self.text, 1)

    def log(self, msg: str, level: str = "info"):
        colors = {"ok": "#4ec9b0", "info": "#9cdcfe", "warn": "#e5c07b", "err": "#f48771"}
        ts = datetime.now().strftime("%H:%M:%S")
        color = colors.get(level, "#969696")
        self.text.append(
            f'<span style="color:#555555">{ts}</span> '
            f'<span style="color:{color}">{msg}</span>'
        )
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())


# ─── Diff widget ──────────────────────────────────────────────────────────────

class DiffWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(12,12,12,12); lo.setSpacing(8)
        self.lbl = QLabel("Ucitaj oba fajla za diff")
        self.lbl.setStyleSheet("color:#666666; padding:8px; font-size:13px;")
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
            "color:#9cdcfe; padding:8px; background:#252526; border-bottom:1px solid #333333; font-size:13px;"
        )
        blocks = MapFinder(eng1).find_changed_regions(eng2, min_block=16)
        self.table.setRowCount(len(blocks))
        colors = {
            "CAL":  ("#0d3321","#4ec9b0"),
            "CODE": ("#0e3a5c","#9cdcfe"),
            "BOOT": ("#3a2a00","#e5c07b"),
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
    action_done = pyqtSignal(str)   # poruka za log strip

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dtc_eng: DtcEngine | None = None
        self._cur_code: int | None = None

        # Horizontalni split: lista lijevo, detalji desno
        root_lo = QHBoxLayout(self)
        root_lo.setContentsMargins(0, 0, 0, 0)
        root_lo.setSpacing(0)

        # ── Lijeva kolona: DTC lista ───────────────────────────────────────────
        left_w = QWidget()
        left_w.setFixedWidth(240)
        left_w.setStyleSheet("background:#252526; border-right:1px solid #333333;")
        left_lo = QVBoxLayout(left_w); left_lo.setContentsMargins(0,0,0,0); left_lo.setSpacing(0)

        lst_hdr = QLabel("  DTC LISTA")
        lst_hdr.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px; "
            "padding:6px 8px; border-bottom:1px solid #333333;"
        )
        left_lo.addWidget(lst_hdr)

        self._dtc_list = QListWidget()
        self._dtc_list.setFont(QFont("Consolas", 12))
        self._dtc_list.itemClicked.connect(self._on_list_click)
        left_lo.addWidget(self._dtc_list, 1)

        root_lo.addWidget(left_w)

        # ── Desna kolona: detalji odabranog DTC ───────────────────────────────
        right_w = QWidget()
        right_lo = QVBoxLayout(right_w)
        right_lo.setContentsMargins(16, 12, 16, 12)
        right_lo.setSpacing(8)

        # Zaglavlje
        self._hdr = QLabel("  DTC MANAGER")
        self._hdr.setStyleSheet(
            "color:#f48771; font-size:11px; font-weight:bold; letter-spacing:1.5px; "
            "background:#252526; padding:6px 8px; border-bottom:1px solid #333333;"
        )
        right_lo.addWidget(self._hdr)

        # Status row
        status_row = QHBoxLayout(); status_row.setSpacing(16)

        self._code_lbl = QLabel("—")
        self._code_lbl.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self._code_lbl.setStyleSheet("color:#f48771; font-size:18px; font-weight:bold;")
        status_row.addWidget(self._code_lbl)

        self._name_lbl = QLabel("")
        self._name_lbl.setStyleSheet("color:#969696; font-size:12px;")
        status_row.addWidget(self._name_lbl)

        status_row.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#4ec9b0; font-size:12px; font-weight:bold;")
        status_row.addWidget(self._status_lbl)

        right_lo.addLayout(status_row)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#333333; max-height:1px;")
        right_lo.addWidget(sep)

        # Enable bajti
        grp_enable = QGroupBox("Enable bajti  (0x06=aktivno · 0x05=djelom. · 0x04=upoz. · 0x00=isključeno)")
        grp_lo = QVBoxLayout(grp_enable)
        self._enable_tbl = QTableWidget(1, 1)
        self._enable_tbl.setMaximumHeight(72)
        self._enable_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._enable_tbl.verticalHeader().hide()
        grp_lo.addWidget(self._enable_tbl)
        right_lo.addWidget(grp_enable)

        # Code storage
        grp_code = QGroupBox("Code storage (LE u16)")
        code_lo = QGridLayout(grp_code)
        kl_main = QLabel("Main:"); kl_main.setStyleSheet("color:#888888;")
        code_lo.addWidget(kl_main, 0, 0)
        self._code_main_lbl = QLabel("—")
        self._code_main_lbl.setFont(QFont("Consolas", 11))
        self._code_main_lbl.setStyleSheet("color:#9cdcfe; font-weight:bold;")
        code_lo.addWidget(self._code_main_lbl, 0, 1)
        kl_mir = QLabel("Mirror:"); kl_mir.setStyleSheet("color:#888888;")
        code_lo.addWidget(kl_mir, 1, 0)
        self._code_mirror_lbl = QLabel("—")
        self._code_mirror_lbl.setFont(QFont("Consolas", 11))
        self._code_mirror_lbl.setStyleSheet("color:#9cdcfe; font-weight:bold;")
        code_lo.addWidget(self._code_mirror_lbl, 1, 1)
        code_lo.setColumnStretch(2, 1)
        right_lo.addWidget(grp_code)

        # Notes + upozorenje
        self._notes_lbl = QLabel("")
        self._notes_lbl.setStyleSheet("color:#666666; font-size:12px;")
        self._notes_lbl.setWordWrap(True)
        right_lo.addWidget(self._notes_lbl)

        warn_lbl = QLabel("⚠  Isključivanje DTC-a deaktivira zaštitu motora!")
        warn_lbl.setStyleSheet("color:#e5c07b; font-size:12px; font-weight:bold;")
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

        self._btn_all_off = QPushButton("Svi DTC OFF")
        self._btn_all_off.setObjectName("btn_danger")
        self._btn_all_off.setFixedHeight(32)
        self._btn_all_off.clicked.connect(self._do_all_off)
        btn_row.addWidget(self._btn_all_off)

        self._btn_disable_all = QPushButton("Disable All Monitor")
        self._btn_disable_all.setObjectName("btn_danger")
        self._btn_disable_all.setFixedHeight(32)
        self._btn_disable_all.setToolTip(
            "Nulira cijelu enable tablicu (0x021080–0x0210BD).\n"
            "Najjača opcija — ECU neće detektirati niti jedan fault.\n"
            "Koristiti oprezno: neke greške štite motor (misfire, oil pressure)."
        )
        self._btn_disable_all.clicked.connect(self._do_disable_all)
        btn_row.addWidget(self._btn_disable_all)

        btn_row.addStretch()

        self._btn_on = QPushButton("DTC ON — Vrati")
        self._btn_on.setObjectName("btn_success")
        self._btn_on.setFixedHeight(32)
        self._btn_on.clicked.connect(self._do_on)
        btn_row.addWidget(self._btn_on)

        right_lo.addLayout(btn_row)

        root_lo.addWidget(right_w, 1)

        self._set_buttons_enabled(False)

    def set_engine(self, eng: DtcEngine | None):
        self._dtc_eng = eng
        self._set_buttons_enabled(eng is not None)
        self._populate_list()

    def _populate_list(self):
        """Napuni DTC listu sa svim poznatim kodovima iz registra."""
        self._dtc_list.clear()
        for code, defn in sorted(DTC_REGISTRY.items()):
            item = QListWidgetItem(f"  {defn.p_code}  {defn.name}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            if self._dtc_eng:
                status = self._dtc_eng.get_status(code)
                if status and status.is_off:
                    item.setForeground(QBrush(QColor("#555555")))
                else:
                    item.setForeground(QBrush(QColor("#f48771")))
            else:
                item.setForeground(QBrush(QColor("#666666")))
            self._dtc_list.addItem(item)

    def _on_list_click(self, item: QListWidgetItem):
        code = item.data(Qt.ItemDataRole.UserRole)
        if code is not None:
            self.show_dtc(code)

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
            self._status_lbl.setStyleSheet("color:#4ec9b0; font-size:12px; font-weight:bold;")
        else:
            self._status_lbl.setText("● AKTIVAN")
            self._status_lbl.setStyleSheet("color:#f48771; font-size:12px; font-weight:bold;")

        # Osvježi boju u listi
        for i in range(self._dtc_list.count()):
            it = self._dtc_list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == self._cur_code:
                it.setForeground(QBrush(QColor("#555555") if status.is_off else QColor("#f48771")))
                break

        # Enable tablica
        n = len(status.enable_values)
        self._enable_tbl.setColumnCount(n)
        self._enable_tbl.setRowCount(1)
        hdrs = [f"+{i}" for i in range(n)]
        self._enable_tbl.setHorizontalHeaderLabels(hdrs)
        for i, val in enumerate(status.enable_values):
            item = QTableWidgetItem(f"0x{val:02X}")
            if val == 0x00:
                item.setForeground(QBrush(QColor("#4ec9b0")))
            elif val == 0x06:
                item.setForeground(QBrush(QColor("#f48771")))
            else:
                item.setForeground(QBrush(QColor("#e5c07b")))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._enable_tbl.setItem(0, i, item)

        # Code labels
        addr_main   = defn.code_addr
        addr_mirror = defn.mirror_addr
        self._code_main_lbl.setText(
            f"0x{status.code_main:04X}  (addr 0x{addr_main:06X})"
        )
        self._code_mirror_lbl.setText(
            f"0x{status.code_mirror:04X}  (addr 0x{addr_mirror:06X})"
        )

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
        # Osvježi listu
        self._populate_list()

    def _set_buttons_enabled(self, enabled: bool):
        self._btn_off.setEnabled(enabled)
        self._btn_on.setEnabled(enabled)
        self._btn_all_off.setEnabled(enabled)
        self._btn_disable_all.setEnabled(enabled)


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
        self.editor:  MapEditor  | None = None
        self.dtc_eng: DtcEngine  | None = None
        self.maps1:   list[FoundMap]    = []
        self.maps2:   list[FoundMap]    = []
        self._cur:    FoundMap   | None = None

        # Undo / Redo
        self._undo: list[UndoCmd] = []
        self._redo: list[UndoCmd] = []

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

        self.btn_open1 = _btn("+ Fajl 1", "primary")
        self.btn_open1.clicked.connect(self._load1); tb.addWidget(self.btn_open1)

        self.btn_open2 = _btn("+ Fajl 2")
        self.btn_open2.clicked.connect(self._load2)
        self.btn_open2.setEnabled(False); tb.addWidget(self.btn_open2)

        tb.addSeparator()

        self.btn_save = _btn("Spremi")
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setEnabled(False); tb.addWidget(self.btn_save)

        tb.addSeparator()

        self.btn_scan = _btn("Skeniraj  F5", "primary")
        self.btn_scan.clicked.connect(self.scan_maps)
        self.btn_scan.setEnabled(False); tb.addWidget(self.btn_scan)

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
        self._file_lbl.setStyleSheet("color:#666666; padding:0 10px; font-size:13px;")
        tb.addWidget(self._file_lbl)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0); self.progress.setMaximumHeight(2); self.progress.hide()

        # Central
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self.progress)

        main_split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(main_split, 1)

        # ── Lijevi sidebar ─────────────────────────────────────────────────
        self.map_lib = MapLibraryPanel()
        self.map_lib.map_selected.connect(self._on_map_selected)
        main_split.addWidget(self.map_lib)

        # ── Centar: mapa + hex + log (vertikalni split) ────────────────────
        center_vsplit = QSplitter(Qt.Orientation.Vertical)

        # Tab widget (Mapa | DTC | Diff)
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.map_view = MapTableView()
        self.map_view.cell_clicked.connect(self._on_cell_click)
        self.map_view.btn_csv.clicked.connect(self._export_csv)
        self.tabs.addTab(self.map_view, "Mapa")

        self.dtc_panel = DtcPanel()
        self.dtc_panel.action_done.connect(lambda msg: self.log_strip.log(msg, "ok"))
        self._dtc_tab = self.tabs.addTab(self.dtc_panel, "DTC")

        self.diff_widget = DiffWidget()
        self._diff_tab = self.tabs.addTab(self.diff_widget, "Diff")
        self.tabs.setTabVisible(self._diff_tab, False)
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
        main_split.addWidget(self.props)

        main_split.setSizes([220, 950, 270])
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)
        main_split.setStretchFactor(2, 0)

        # Status bar
        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage("ME17Suite — Ucitaj .bin fajl  (Ctrl+1)")

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
        self._add_action(fm, "Izlaz  (Ctrl+Q)",    "Ctrl+Q", self.close)

        em = mb.addMenu("Editovanje")
        self._add_action(em, "Undo  (Ctrl+Z)",     "Ctrl+Z", self._undo_action)
        self._add_action(em, "Redo  (Ctrl+Y)",     "Ctrl+Y", self._redo_action)

        tm = mb.addMenu("Alati")
        self._add_action(tm, "Skeniraj mape  (F5)", "F5",    self.scan_maps)
        self._add_action(tm, "Prikazi Diff",         "",      self._show_diff)
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

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load1(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Otvori Fajl 1", str(Path.home()), "Binary (*.bin);;Svi fajlovi (*)"
        )
        if not path: return
        try:
            eng = ME17Engine(); info = eng.load(path)
            self.eng1 = eng; self.editor = MapEditor(eng)
            self.dtc_eng = DtcEngine(eng); self.dtc_panel.set_engine(self.dtc_eng)
            name = Path(path).name
            self._file_lbl.setText(
                f"  <b style='color:#9cdcfe'>{info.sw_id}</b>"
                f"  <span style='color:#888888'>{name}</span>"
            )
            self._file_lbl.setTextFormat(Qt.TextFormat.RichText)
            self.btn_open2.setEnabled(True); self.btn_save.setEnabled(True)
            self.btn_scan.setEnabled(True)
            self.props.show_ecu(eng)
            self.log_strip.log(f"Ucitan: {name}", "ok")
            self.log_strip.log(f"SW: {info.sw_id} — {info.sw_desc}", "info")
            self.log_strip.log(f"MCU: {'TC1762 OK' if info.mcu_confirmed else 'NEPOTVRDJEN'}", "info")
            self.status.showMessage(f"{info.sw_id}  —  {info.sw_desc}")
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
            w = ScanWorker(eng); w.finished.connect(self._done2); w.start(); self._w2 = w
        except Exception as e:
            QMessageBox.critical(self, "Greska", str(e))

    def _save(self):
        if not self.eng1: return
        if not self.eng1.dirty:
            self.status.showMessage("Nema izmjena."); return
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
        self.progress.show(); self.status.showMessage("Skeniranje...")
        self.log_strip.log("Skeniranje mapa...", "info")
        w = ScanWorker(self.eng1)
        w.progress.connect(self.status.showMessage)
        w.finished.connect(self._done1); w.start(); self._w1 = w

    def _done1(self, maps):
        self.maps1 = maps; self.progress.hide()
        self.map_lib.populate(maps)
        self.log_strip.log(f"Pronadjeno {len(maps)} mapa.", "ok")
        self.status.showMessage(f"{len(maps)} mapa pronadjeno.")

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
                if self.eng1: self.hex_strip.show(self.eng1, fm.address)
                self.status.showMessage(
                    f"DTC {fm.defn.name}  @  0x{fm.address:06X}  —  enable {fm.defn.cols}B"
                )
            return

        fm2 = next((m for m in self.maps2 if m.defn.name == fm.defn.name), None)
        self.map_view.show_map(fm, fm2)
        self.props.show_map_stats(fm)
        if self.eng1: self.hex_strip.show(self.eng1, fm.address)
        self.tabs.setCurrentIndex(0)
        cmp = "  |  Fajl 2 aktivna" if fm2 else ""
        self.status.showMessage(f"{fm.defn.name}  @  0x{fm.address:06X}  {fm.defn.rows}×{fm.defn.cols}  {fm.defn.unit}{cmp}")

    # ── Cell click ────────────────────────────────────────────────────────────

    def _on_cell_click(self, row: int, col: int, fm: FoundMap):
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

        result = self.editor.write_cell(self._cur, row, col, display_val)
        if not result.ok:
            self.log_strip.log(f"GRESKA: {result.message}", "err")
            self.status.showMessage(f"GRESKA: {result.message}"); return

        new_raw = round((display_val - defn.offset_val) / defn.scale) if defn.scale else 0
        self._cur.data[idx] = new_raw

        # Undo stack
        self._undo.append(UndoCmd(self._cur, row, col, old_raw, new_raw))
        self._redo.clear(); self._upd_undo_btns()

        self.map_view.refresh_cell(row, col, new_raw)
        self.props.show_cell(row, col, self._cur)
        self.props.show_map_stats(self._cur)
        self.log_strip.log(result.message, "warn")
        self.status.showMessage(result.message)

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

    # ── Diff ──────────────────────────────────────────────────────────────────

    def _show_diff(self):
        if not (self.eng1 and self.eng2):
            self.status.showMessage("Ucitaj oba fajla."); return
        self.diff_widget.show_diff(self.eng1, self.eng2)
        self.tabs.setCurrentIndex(self._diff_tab)

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
