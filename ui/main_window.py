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
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QBrush, QAction, QFont, QKeySequence

from core.engine import ME17Engine
from core.map_finder import MapFinder, FoundMap, MapDef
from core.map_editor import MapEditor, EditResult
from core.checksum import ChecksumEngine


# ─── Stylesheet ───────────────────────────────────────────────────────────────

STYLESHEET = """
* { font-family: "Consolas", "Courier New", monospace; font-size: 12px; }
QMainWindow, QWidget { background-color: #252529; color: #C8C8D0; }

QMenuBar {
    background: #1A1A1E; color: #606070;
    border-bottom: 1px solid #303038; padding: 2px 4px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 3px; }
QMenuBar::item:selected { background: #2A2A32; color: #E0E0E8; }
QMenu {
    background: #1E1E22; color: #C8C8D0;
    border: 1px solid #303038; padding: 2px 0;
}
QMenu::item { padding: 5px 20px 5px 12px; }
QMenu::item:selected { background: #1E3A5F; color: #4FC3F7; }
QMenu::separator { height: 1px; background: #303038; margin: 4px 0; }

QToolBar {
    background: #1A1A1E; border-bottom: 1px solid #303038;
    padding: 3px 8px; spacing: 2px;
}
QToolBar::separator { background: #303038; width: 1px; margin: 4px 6px; }

QSplitter::handle { background: #303038; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical   { height: 1px; }

QTreeWidget {
    background: #1A1A1E; border: none; color: #707080; outline: none;
}
QTreeWidget::item { padding: 3px 4px; }
QTreeWidget::item:selected {
    background: #1A2F4A; color: #4FC3F7;
    border-left: 2px solid #4FC3F7;
}
QTreeWidget::item:hover:!selected { background: #222228; }
QTreeWidget::branch { background: #1A1A1E; }

QTabWidget::pane {
    border: none; border-top: 1px solid #303038; background: #202024;
}
QTabBar { background: #1A1A1E; }
QTabBar::tab {
    background: #1A1A1E; color: #484858; padding: 5px 14px;
    border: none; border-bottom: 2px solid transparent; margin-right: 1px;
}
QTabBar::tab:selected { color: #4FC3F7; border-bottom: 2px solid #4FC3F7; background: #202024; }
QTabBar::tab:hover:!selected { color: #808090; }

QTableWidget {
    background: #1A1A1E; border: none; color: #C0C0C8;
    gridline-color: #222228; outline: none;
}
QTableWidget::item { padding: 2px 4px; }
QTableWidget::item:selected { background: #1A2F4A; color: #4FC3F7; }
QHeaderView::section {
    background: #1E1E22; color: #484858; border: none;
    border-right: 1px solid #222228; border-bottom: 1px solid #222228;
    padding: 2px 5px; font-size: 10px;
}

QPushButton {
    background: #222228; color: #808090;
    border: 1px solid #303038; border-radius: 3px;
    padding: 3px 9px; min-height: 22px;
}
QPushButton:hover  { background: #2A2A32; color: #C0C0C8; border-color: #3A3A48; }
QPushButton:pressed { background: #1A2F4A; color: #4FC3F7; }
QPushButton#primary { background: #1A3A5A; color: #4FC3F7; border-color: #2A4A6A; }
QPushButton#primary:hover { background: #1E4468; }
QPushButton#warn { background: #2A1A10; color: #FF8C42; border-color: #3A2A18; }
QPushButton#warn:hover { background: #362010; }
QPushButton:disabled { color: #303038; border-color: #252528; background: #1E1E22; }

QLineEdit {
    background: #1A1A1E; border: 1px solid #303038; border-radius: 3px;
    color: #C8C8D0; padding: 3px 7px;
}
QLineEdit:focus { border-color: #4FC3F7; }
QLineEdit::placeholder { color: #363646; }

QTextEdit { background: #141418; border: none; color: #404858; font-size: 11px; }

QGroupBox {
    border: 1px solid #303038; border-radius: 3px;
    margin-top: 14px; padding: 4px 4px 4px 4px; color: #454555;
    font-size: 10px; letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 5px; left: 7px; top: 1px;
}

QScrollBar:vertical { background: #1A1A1E; width: 6px; border: none; }
QScrollBar::handle:vertical { background: #303040; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #3A3A50; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1A1A1E; height: 6px; border: none; }
QScrollBar::handle:horizontal { background: #303040; border-radius: 3px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QStatusBar {
    background: #141418; color: #404050;
    border-top: 1px solid #222228; padding: 0 8px; font-size: 11px;
}
QStatusBar::item { border: none; }
QProgressBar { background: #252529; border: none; height: 2px; color: transparent; }
QProgressBar::chunk { background: #4FC3F7; }
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
        "ignition":    ("Ignition",      "#FFB74D"),
        "injection":   ("Injection",     "#FF7043"),
        "torque":      ("Torque",        "#81C784"),
        "lambda":      ("Lambda / AFR",  "#64B5F6"),
        "rpm_limiter": ("Rev Limiter",   "#EF5350"),
        "axis":        ("RPM Axes",      "#BA68C8"),
        "dtc":         ("DTC / Faults",  "#F06292"),
        "misc":        ("Other",          "#90A4AE"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200); self.setMaximumWidth(260)
        self._all: list[FoundMap] = []

        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        self._hdr = QLabel("  MAP LIBRARY")
        self._hdr.setStyleSheet(
            "background:#1A1A1E; color:#404050; font-size:10px; "
            "padding:5px 8px; border-bottom:1px solid #303038; letter-spacing:1.5px;"
        )
        lo.addWidget(self._hdr)

        self.search = QLineEdit()
        self.search.setPlaceholderText("  search...")
        self.search.setStyleSheet(
            "background:#141418; border:none; border-bottom:1px solid #303038; "
            "border-radius:0; padding:4px 8px; color:#808090;"
        )
        self.search.textChanged.connect(self._filter)
        lo.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(10)
        self.tree.itemClicked.connect(self._click)
        lo.addWidget(self.tree, 1)

    def populate(self, maps: list[FoundMap]):
        self._all = maps
        self._hdr.setText(f"  MAP LIBRARY — {len(maps)}")
        self._render(maps)

    def _filter(self, t: str):
        self._render([m for m in self._all if t.lower() in m.defn.name.lower()] if t else self._all)

    def _render(self, maps: list[FoundMap]):
        self.tree.clear()
        cats = {}
        for key, (label, color) in self.CATEGORIES.items():
            it = QTreeWidgetItem(self.tree, [f"  {label}"])
            it.setForeground(0, QColor(color))
            it.setExpanded(True)
            cats[key] = it
        for fm in maps:
            dims = f"{fm.defn.rows}×{fm.defn.cols}" if fm.defn.rows > 1 else "scalar"
            ch = QTreeWidgetItem(cats.get(fm.defn.category, cats["misc"]),
                                 [f"  {fm.defn.name}"])
            ch.setForeground(0, QColor("#707080"))
            ch.setToolTip(0, f"0x{fm.address:06X}  {dims}  {fm.defn.unit}\n{fm.defn.description}")
            ch.setData(0, Qt.ItemDataRole.UserRole, fm)
        for it in cats.values():
            it.setHidden(it.childCount() == 0)

    def _click(self, item: QTreeWidgetItem):
        fm = item.data(0, Qt.ItemDataRole.UserRole)
        if fm: self.map_selected.emit(fm)


# ─── Map Table View ───────────────────────────────────────────────────────────

class MapTableView(QWidget):
    cell_clicked = pyqtSignal(int, int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        self.hdr = QLabel("  Select a map from the tree")
        self.hdr.setStyleSheet(
            "color:#363646; padding:5px 10px; background:#1A1A1E; "
            "border-bottom:1px solid #303038; font-size:11px;"
        )
        lo.addWidget(self.hdr)

        # Action bar
        ab = QWidget(); ab.setStyleSheet("background:#1E1E22; border-bottom:1px solid #303038;")
        abl = QHBoxLayout(ab); abl.setContentsMargins(6,2,6,2); abl.setSpacing(4)
        self.btn_copy  = _btn("Copy")
        self.btn_csv   = _btn("Export CSV")
        self.btn_reset = _btn("Reset", "warn")
        for b in [self.btn_copy, self.btn_csv, self.btn_reset]:
            b.setFixedHeight(22); abl.addWidget(b)
        abl.addStretch()
        self._meta = QLabel(); self._meta.setStyleSheet("color:#383848; font-size:10px;")
        abl.addWidget(self._meta)
        self.action_bar = ab; self.action_bar.hide()
        lo.addWidget(ab)

        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(lambda r,c: self._fm and self.cell_clicked.emit(r,c,self._fm))
        lo.addWidget(self.table, 1)

        self._fm:  FoundMap | None = None
        self._fm2: FoundMap | None = None

    def show_map(self, fm: FoundMap, compare: FoundMap | None = None):
        self._fm = fm; self._fm2 = compare
        defn = fm.defn

        self.hdr.setText(
            f"  <b style='color:#4FC3F7'>{defn.name}</b>"
            f"  <span style='color:#383848'>@0x{fm.address:06X}</span>"
            f"  <span style='color:#484858'>{defn.rows}×{defn.cols}"
            f"  {defn.dtype}  ×{defn.scale}  {defn.unit}</span>"
        )
        self.hdr.setTextFormat(Qt.TextFormat.RichText)
        self.hdr.setStyleSheet("padding:5px 10px; background:#1A1A1E; border-bottom:1px solid #303038; font-size:11px;")
        self._meta.setText(f"mirror +0x{defn.mirror_offset:X}" if defn.mirror_offset else "")
        self.action_bar.show()

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
        rng = mx - mn if mx != mn else 1

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
                bg = self._heat((raw - mn) / rng)
                if data2 and idx < len(data2) and data2[idx] != raw:
                    bg = QColor("#28200A"); item.setForeground(QBrush(QColor("#FFD54F")))
                item.setBackground(QBrush(bg))
                self.table.setItem(r, c, item)

    def refresh_cell(self, row: int, col: int, new_raw: int):
        defn = self._fm.defn
        txt  = (f"{new_raw * defn.scale:.1f}" if defn.dtype == "u8"
                else f"{new_raw * defn.scale:.3f}" if defn.scale != 0
                else f"0x{new_raw:04X}")
        item = self.table.item(row, col)
        if not item: return
        item.setText(txt); item.setData(Qt.ItemDataRole.UserRole, new_raw)
        mn  = min(self._fm.data); mx = max(self._fm.data)
        rng = mx - mn if mx != mn else 1
        item.setBackground(QBrush(self._heat((new_raw - mn) / rng)))
        item.setForeground(QBrush(QColor("#E0E0E8")))

    def clear(self):
        self._fm = None; self.table.setRowCount(0); self.table.setColumnCount(0)
        self.hdr.setText("  Select a map from the tree")
        self.hdr.setStyleSheet("color:#363646; padding:5px 10px; background:#1A1A1E; border-bottom:1px solid #303038; font-size:11px;")
        self.action_bar.hide()

    @staticmethod
    def _heat(t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        if t < 0.33:
            tt = t / 0.33
            r,g,b = int(20+tt*12), int(24+tt*32), int(44+tt*10)
        elif t < 0.66:
            tt = (t-0.33)/0.33
            r,g,b = int(32+tt*28), int(56-tt*10), int(54-tt*20)
        else:
            tt = (t-0.66)/0.34
            r,g,b = int(60+tt*48), int(46-tt*18), int(34-tt*14)
        return QColor(max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))


# ─── Properties panel — 3 taba ────────────────────────────────────────────────

class PropertiesPanel(QWidget):
    edit_requested = pyqtSignal(int, int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260); self.setMaximumWidth(310)
        self._fm:      FoundMap | None = None
        self._row = self._col = 0

        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        hdr = QLabel("  PROPERTIES")
        hdr.setStyleSheet(
            "background:#1A1A1E; color:#404050; font-size:10px; "
            "padding:5px 8px; border-bottom:1px solid #303038; letter-spacing:1.5px;"
        )
        lo.addWidget(hdr)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        lo.addWidget(self.tabs, 1)

        # ── Tab 0: Celija ──────────────────────────────────────────────────
        cell_w = QWidget()
        cell_lo = QVBoxLayout(cell_w); cell_lo.setContentsMargins(8,8,8,8); cell_lo.setSpacing(6)

        self._pos_lbl = QLabel("Select a cell")
        self._pos_lbl.setStyleSheet("color:#404050; font-size:10px;")
        cell_lo.addWidget(self._pos_lbl)

        self._val_lbl = QLabel("—")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._val_lbl.setStyleSheet(
            "color:#4FC3F7; font-size:30px; font-weight:bold; "
            "background:#1A1A1E; border:1px solid #303038; border-radius:3px; padding:6px;"
        )
        cell_lo.addWidget(self._val_lbl)

        self._raw_lbl = QLabel("—")
        self._raw_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._raw_lbl.setStyleSheet("color:#383848; font-size:10px;")
        cell_lo.addWidget(self._raw_lbl)

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
        self._addr_lbl.setStyleSheet("color:#303040; font-size:10px;")
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
            kl = QLabel(k+":"); kl.setStyleSheet("color:#454555; font-size:11px;")
            vl = QLabel("—");   vl.setStyleSheet("color:#707080; font-size:11px;")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            sg.addWidget(kl, i, 0); sg.addWidget(vl, i, 1)
            self._st[k] = vl
        map_lo.addWidget(stats_g)

        notes_g = QGroupBox("NAPOMENE")
        nl = QVBoxLayout(notes_g); nl.setContentsMargins(6,6,6,6)
        self._notes = QLabel("—")
        self._notes.setWordWrap(True)
        self._notes.setStyleSheet("color:#3A3A4A; font-size:10px; line-height:140%;")
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
            kl = QLabel(k+":"); kl.setStyleSheet("color:#454555; font-size:11px;")
            vl = QLabel("—");   vl.setStyleSheet("color:#707080; font-size:11px;")
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
        mem_txt.setStyleSheet("color:#3A3A4A; font-size:10px; line-height:160%;")
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
        self._ecu["SW ID"].setStyleSheet("color:#4FC3F7; font-size:11px;")
        self._ecu["MCU"].setText("TC1762 LE" if info.mcu_confirmed else "NEPOTVRDJEN")
        self._ecu["Velicina"].setText(f"{info.file_size // 1024} KB")
        self._ecu["Platform"].setText("VM_CB.04.80.00" if info.platform_confirmed else "—")
        ok = cs.get("sw_id", {}).get("status") == "OK"
        self._ecu["Checksum"].setText("SW OK" if ok else "PENDING")
        self._ecu["Checksum"].setStyleSheet(
            f"color:{'#4CAF50' if ok else '#FFB74D'}; font-size:11px;"
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
                "background:#2A1010; border:1px solid #EF5350; border-radius:3px; padding:3px 7px;"
            )
            QTimer.singleShot(800, lambda: self._inp.setStyleSheet(""))


# ─── Hex Strip ────────────────────────────────────────────────────────────────

class HexStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        hdr = QLabel("  HEX VIEW")
        hdr.setStyleSheet(
            "color:#303040; font-size:10px; letter-spacing:1.5px; "
            "padding:2px 8px; background:#141418; border-bottom:1px solid #222228;"
        )
        lo.addWidget(hdr)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        lo.addWidget(self.text, 1)

    def show(self, eng: ME17Engine, addr: int, length: int = 64):
        if not eng or not eng.loaded: return
        data  = eng.get_bytes()
        lines = []
        for i in range(0, min(length, len(data)-addr), 16):
            ch  = data[addr+i: addr+i+16]
            hx  = " ".join(f"{b:02X}" for b in ch)
            asc = "".join(chr(b) if 32 <= b < 127 else "·" for b in ch)
            lines.append(
                f'<span style="color:#263646">0x{addr+i:06X}</span>  '
                f'<span style="color:#383848">{hx:<47}</span>  '
                f'<span style="color:#2E3040">{asc}</span>'
            )
        self.text.setHtml("<br>".join(lines))


# ─── Log Strip ────────────────────────────────────────────────────────────────

class LogStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        hdr = QLabel("  LOG")
        hdr.setStyleSheet(
            "color:#303040; font-size:10px; letter-spacing:1.5px; "
            "padding:2px 8px; background:#141418; border-bottom:1px solid #222228;"
        )
        lo.addWidget(hdr)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        lo.addWidget(self.text, 1)

    def log(self, msg: str, level: str = "info"):
        colors = {"ok":"#4CAF50","info":"#4FC3F7","warn":"#FFB74D","err":"#EF5350"}
        ts = datetime.now().strftime("%H:%M:%S")
        self.text.append(
            f'<span style="color:#263030">{ts}</span>  '
            f'<span style="color:{colors.get(level,"#606070")}">{msg}</span>'
        )
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())


# ─── Diff widget ──────────────────────────────────────────────────────────────

class DiffWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(12,12,12,12); lo.setSpacing(8)
        self.lbl = QLabel("Ucitaj oba fajla za diff")
        self.lbl.setStyleSheet("color:#363646; padding:8px;")
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
            "color:#4FC3F7; padding:8px; background:#1A1A1E; border-bottom:1px solid #303038;"
        )
        blocks = MapFinder(eng1).find_changed_regions(eng2, min_block=16)
        self.table.setRowCount(len(blocks))
        colors = {
            "CAL":  ("#1A3020","#81C784"),
            "CODE": ("#1A2030","#64B5F6"),
            "BOOT": ("#302010","#FFB74D"),
        }
        for i, b in enumerate(blocks):
            reg = "CAL" if b["in_cal"] else ("CODE" if b["in_code"] else "BOOT")
            bg, fg = colors.get(reg, ("#252529","#C0C0C8"))
            for j, txt in enumerate([reg, f"0x{b['start']:06X}", f"0x{b['end']:06X}", f"{b['size']:,} B"]):
                item = QTableWidgetItem(txt)
                item.setBackground(QBrush(QColor(bg)))
                if j == 0: item.setForeground(QBrush(QColor(fg)))
                self.table.setItem(i, j, item)


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
        self.eng1:   ME17Engine | None = None
        self.eng2:   ME17Engine | None = None
        self.editor: MapEditor  | None = None
        self.maps1:  list[FoundMap]    = []
        self.maps2:  list[FoundMap]    = []
        self._cur:   FoundMap   | None = None

        # Undo / Redo
        self._undo: list[UndoCmd] = []
        self._redo: list[UndoCmd] = []

        self._build_ui()
        self._build_menus()
        self.setWindowTitle("ME17Suite  —  Bosch ME17.8.5 Rotax Editor")
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
        self._file_lbl.setStyleSheet("color:#383848; padding:0 10px; font-size:11px;")
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

        # Tab widget (Mapa | Diff)
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.map_view = MapTableView()
        self.map_view.cell_clicked.connect(self._on_cell_click)
        self.map_view.btn_csv.clicked.connect(self._export_csv)
        self.tabs.addTab(self.map_view, "Mapa")

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

        main_split.setSizes([230, 970, 265])
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
            name = Path(path).name
            self._file_lbl.setText(
                f"  <b style='color:#4FC3F7'>{info.sw_id}</b>"
                f"  <span style='color:#383848'>{name}</span>"
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
        self.log_strip.log(f"Fajl 2: {len(maps)} mapa.", "info")

    # ── Map selection ─────────────────────────────────────────────────────────

    def _on_map_selected(self, fm: FoundMap):
        self._cur = fm
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
