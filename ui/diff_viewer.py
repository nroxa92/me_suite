"""
ME17Suite — Map Diff Viewer
Side-by-side usporedba ECU mapa između dva firmware fajla.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QTableWidget, QTableWidgetItem, QListWidget,
    QListWidgetItem, QPushButton, QHeaderView, QTextEdit,
    QFileDialog, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont

from core.engine import ME17Engine
from core.map_differ import MapDiffer, MapDiff


# ─── Palette: diff boje ───────────────────────────────────────────────────────

_COL_F1_CHANGED = "#2d3a1e"    # tamno zelena — ova ćelija promijenjena u F1
_COL_F2_CHANGED = "#3a1e1e"    # tamno crvena — ova ćelija promijenjena u F2
_COL_HEADER     = "#2d2d2d"
_FG_F1          = "#b5cea8"    # zelena tekst
_FG_F2          = "#f48771"    # crvena tekst
_FG_SAME        = "#cccccc"


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _heat_color(val: float, min_v: float, max_v: float) -> QColor:
    """Viridis-like paleta: tamno plava → zelena → žuta."""
    if max_v == min_v:
        return QColor("#3c3c3c")
    t = _clamp((val - min_v) / (max_v - min_v), 0.0, 1.0)
    # plava(0) → cyan(0.33) → zelena(0.5) → žuta(0.75) → bijela(1.0)
    if t < 0.33:
        f = t / 0.33
        r = int(20  + f * 0)
        g = int(20  + f * 110)
        b = int(120 + f * 80)
    elif t < 0.66:
        f = (t - 0.33) / 0.33
        r = int(20  + f * 130)
        g = int(130 + f * 50)
        b = int(200 - f * 150)
    else:
        f = (t - 0.66) / 0.34
        r = int(150 + f * 80)
        g = int(180 + f * 50)
        b = int(50  - f * 30)
    return QColor(r, g, b)


# ─── Heatmap tablica ──────────────────────────────────────────────────────────

class MapHeatTable(QTableWidget):
    """Prikazuje vrijednosti jedne mape kao heatmap tablicu."""

    def __init__(self, label: str, color_header: str, parent=None):
        super().__init__(0, 0, parent)
        self._label_color = color_header
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setDefaultSectionSize(54)
        self.verticalHeader().setDefaultSectionSize(28)
        self.setFont(QFont("Consolas", 11))
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

    def load_map(self, diff: MapDiff, values: list[float], mark_changed: bool,
                 min_v: float, max_v: float, axis_x: list | None = None, axis_y: list | None = None):
        """Popuni tablicu s vrijednostima i heatmap bojama."""
        rows = diff.rows; cols = diff.cols
        self.setRowCount(rows); self.setColumnCount(cols)

        # Zaglavlja osi
        if axis_x and len(axis_x) == cols:
            self.setHorizontalHeaderLabels([f"{v:.4g}" for v in axis_x])
        else:
            self.setHorizontalHeaderLabels([str(c) for c in range(cols)])

        if axis_y and len(axis_y) == rows:
            self.setVerticalHeaderLabels([f"{v:.4g}" for v in axis_y])
        else:
            self.setVerticalHeaderLabels([str(r) for r in range(rows)])

        # Set s promijenjenim ćelijama za brzo lookup
        changed_cells: set[tuple[int,int]] = set()
        if mark_changed:
            for c in diff.cells:
                changed_cells.add((c.row, c.col))

        for idx, val in enumerate(values):
            r = idx // cols; c = idx % cols
            item = QTableWidgetItem(f"{val:.4g}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if (r, c) in changed_cells:
                item.setBackground(QBrush(QColor(
                    _COL_F1_CHANGED if not mark_changed else _COL_F2_CHANGED
                )))
                item.setForeground(QBrush(QColor(_FG_F2 if mark_changed else _FG_F1)))
            else:
                bg = _heat_color(val, min_v, max_v)
                item.setBackground(QBrush(bg))
                # Tamniji background → svjetliji tekst
                brightness = (bg.red()*299 + bg.green()*587 + bg.blue()*114) // 1000
                item.setForeground(QBrush(QColor("#ffffff" if brightness < 100 else "#1a1a1a")))

            self.setItem(r, c, item)


# ─── MapDiffDetailWidget ──────────────────────────────────────────────────────

class MapDiffDetailWidget(QWidget):
    """Side-by-side prikaz jedne mape — F1 lijevo, F2 desno."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)

        # Header
        self._hdr = QLabel("  — odaberi mapu —")
        self._hdr.setStyleSheet(
            "color:#9cdcfe; font-family:Consolas; font-size:13px; font-weight:bold; "
            "background:#252526; padding:6px 10px; border-bottom:1px solid #333333;"
        )
        lo.addWidget(self._hdr)

        # Info bar
        self._info = QLabel("")
        self._info.setStyleSheet(
            "color:#666666; font-family:Consolas; font-size:11px; "
            "background:#1e1e1e; padding:4px 10px;"
        )
        lo.addWidget(self._info)

        # Side-by-side tablice
        split = QSplitter(Qt.Orientation.Horizontal)

        left_w = QWidget()
        left_lo = QVBoxLayout(left_w); left_lo.setContentsMargins(0,0,0,0); left_lo.setSpacing(0)
        self._lbl1 = QLabel("  FAJL 1")
        self._lbl1.setStyleSheet("color:#9cdcfe; font-size:11px; font-weight:bold; padding:3px 8px; background:#1a2a3a;")
        left_lo.addWidget(self._lbl1)
        self._tbl1 = MapHeatTable("F1", "#1a2a3a")
        left_lo.addWidget(self._tbl1, 1)
        split.addWidget(left_w)

        right_w = QWidget()
        right_lo = QVBoxLayout(right_w); right_lo.setContentsMargins(0,0,0,0); right_lo.setSpacing(0)
        self._lbl2 = QLabel("  FAJL 2")
        self._lbl2.setStyleSheet("color:#f48771; font-size:11px; font-weight:bold; padding:3px 8px; background:#3a1a1a;")
        right_lo.addWidget(self._lbl2)
        self._tbl2 = MapHeatTable("F2", "#3a1a1a")
        right_lo.addWidget(self._tbl2, 1)
        split.addWidget(right_w)

        lo.addWidget(split, 1)

        # Delta legenda
        legend = QLabel(
            "  Zelena pozadina = promijenjena ćelija (Fajl 1)  |  "
            "Crvena pozadina = promijenjena ćelija (Fajl 2)  |  "
            "Heatmap = relativna razina vrijednosti"
        )
        legend.setStyleSheet(
            "color:#555555; font-size:11px; background:#1a1a1a; "
            "padding:4px 10px; border-top:1px solid #333333;"
        )
        lo.addWidget(legend)

    def show_diff(self, diff: MapDiff, vals1: list[float], vals2: list[float],
                  sw1: str = "Fajl 1", sw2: str = "Fajl 2",
                  axis_x: list | None = None, axis_y: list | None = None):
        self._hdr.setText(f"  {diff.name}  —  0x{diff.address:06X}  [{diff.rows}×{diff.cols}]")
        self._lbl1.setText(f"  {sw1}")
        self._lbl2.setText(f"  {sw2}")

        min_v = min(min(vals1), min(vals2)) if vals1 and vals2 else 0.0
        max_v = max(max(vals1), max(vals2)) if vals1 and vals2 else 1.0

        self._tbl1.load_map(diff, vals1, mark_changed=False, min_v=min_v, max_v=max_v,
                            axis_x=axis_x, axis_y=axis_y)
        self._tbl2.load_map(diff, vals2, mark_changed=True,  min_v=min_v, max_v=max_v,
                            axis_x=axis_x, axis_y=axis_y)

        changed_cnt = diff.changed_count
        total = diff.total_cells
        max_d = diff.max_delta
        avg_d = diff.avg_delta
        self._info.setText(
            f"  Promijenjeno: {changed_cnt}/{total} ({diff.changed_pct:.0f}%)  |  "
            f"Maks Δ: {max_d:+.4g} {diff.unit}  |  "
            f"Prosj. Δ: {avg_d:+.4g} {diff.unit}"
        )


# ─── MapDiffWidget (glavni widget) ───────────────────────────────────────────

class MapDiffWidget(QWidget):
    """
    Kompletni diff viewer widget.
    Koristi se u main_window.py kao tab.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._differ: MapDiffer | None = None
        self._diffs: list[MapDiff] = []
        self._sw1 = "Fajl 1"
        self._sw2 = "Fajl 2"

        lo = QVBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)

        # Toolbar
        tb = QWidget()
        tb.setStyleSheet("background:#2d2d2d; border-bottom:1px solid #111;")
        tb_lo = QHBoxLayout(tb); tb_lo.setContentsMargins(8, 4, 8, 4); tb_lo.setSpacing(6)

        self._status_lbl = QLabel("Ucitaj oba fajla i skeniranjem pokretaj Diff")
        self._status_lbl.setStyleSheet("color:#666666; font-size:12px;")
        tb_lo.addWidget(self._status_lbl)
        tb_lo.addStretch()

        self._btn_report = QPushButton("Izvoz Markdown...")
        self._btn_report.setFixedHeight(24)
        self._btn_report.setEnabled(False)
        self._btn_report.clicked.connect(self._export_report)
        tb_lo.addWidget(self._btn_report)

        lo.addWidget(tb)

        # Horizontalni split: lista lijevo, detalji desno
        h_split = QSplitter(Qt.Orientation.Horizontal)

        # Lijevo: lista promijenjenih mapa
        left_w = QWidget(); left_w.setFixedWidth(300)
        left_w.setStyleSheet("background:#252526;")
        left_lo = QVBoxLayout(left_w); left_lo.setContentsMargins(0, 0, 0, 0); left_lo.setSpacing(0)

        list_hdr = QLabel("  PROMIJENJENE MAPE")
        list_hdr.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px; "
            "padding:6px 8px; border-bottom:1px solid #333333;"
        )
        left_lo.addWidget(list_hdr)

        self._map_list = QListWidget()
        self._map_list.setFont(QFont("Consolas", 11))
        self._map_list.itemClicked.connect(self._on_map_selected)
        left_lo.addWidget(self._map_list, 1)

        h_split.addWidget(left_w)

        # Desno: side-by-side detail
        self._detail = MapDiffDetailWidget()
        h_split.addWidget(self._detail)
        h_split.setSizes([300, 900])

        lo.addWidget(h_split, 1)

    def load_diff(self, differ: MapDiffer, sw1: str = "Fajl 1", sw2: str = "Fajl 2"):
        """Izvrši usporedbu i popuni listu."""
        self._differ = differ
        self._sw1 = sw1
        self._sw2 = sw2
        self._diffs = differ.compare_all_maps()

        self._map_list.clear()
        for d in self._diffs:
            item = QListWidgetItem()
            pct = d.changed_pct
            color = "#f48771" if pct >= 50 else "#e5c07b" if pct >= 20 else "#9cdcfe"
            item.setText(f"{d.name}  ({d.changed_count}/{d.total_cells})")
            item.setForeground(QBrush(QColor(color)))
            item.setData(Qt.ItemDataRole.UserRole, d.name)
            self._map_list.addItem(item)

        total_changed = sum(d.changed_count for d in self._diffs)
        self._status_lbl.setText(
            f"  {len(self._diffs)} mapa s promjenama  |  {total_changed} ćelija ukupno  |  "
            f"{sw1} vs {sw2}"
        )
        self._status_lbl.setStyleSheet("color:#9cdcfe; font-size:12px;")
        self._btn_report.setEnabled(True)

        if self._diffs:
            self._map_list.setCurrentRow(0)
            self._show_diff(self._diffs[0])

    def _on_map_selected(self, item: QListWidgetItem):
        name = item.data(Qt.ItemDataRole.UserRole)
        diff = next((d for d in self._diffs if d.name == name), None)
        if diff:
            self._show_diff(diff)

    def _show_diff(self, diff: MapDiff):
        if self._differ is None:
            return
        res = self._differ.get_values_for_map(diff.name)
        if res is None:
            return
        vals1, vals2 = res

        # Pokušaj dohvatiti osi iz skeniranih mapa
        from core.map_finder import MapFinder
        axis_x = None; axis_y = None
        maps1 = self._differ._maps1
        fm1 = next((fm for fm in maps1 if fm.defn.name == diff.name), None)
        if fm1 and fm1.defn.axis_x:
            axis_x = fm1.defn.axis_x.values
        if fm1 and fm1.defn.axis_y:
            axis_y = fm1.defn.axis_y.values

        self._detail.show_diff(diff, vals1, vals2,
                               sw1=self._sw1, sw2=self._sw2,
                               axis_x=axis_x, axis_y=axis_y)

    def _export_report(self):
        if self._differ is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Spremi Diff Report", "diff_report.md",
            "Markdown (*.md);;Svi fajlovi (*)"
        )
        if not path:
            return
        report = self._differ.generate_diff_report()
        Path(path).write_text(report, encoding="utf-8")
