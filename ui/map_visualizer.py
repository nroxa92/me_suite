"""
ME17Suite — Map Visualizer
PyQt6 widgeti za profesionalnu vizualizaciju kalibracijskih mapa.

Widgeti:
  MapHeatWidget   — 2D heat mapa (JET paleta), klik, hover, selekcija
  MapDeltaWidget  — usporedba dvije mape (A vs B), delta prikaz
  MapMiniPreview  — mini preview (100×60) za tree/listu
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtWidgets import QWidget, QToolTip, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics

from core.map_finder import FoundMap, MapDef


# ─── Konstante stila ───────────────────────────────────────────────────────────

_BG_COLOR        = QColor("#111113")
_GRID_COLOR      = QColor("#2A2A3A")
_SEL_BORDER      = QColor("#FFD700")   # žuta — odabrana ćelija
_HEADER_BG       = QColor("#1A1A2E")
_HEADER_FG       = QColor("#8899BB")
_CELL_FONT_SIZE  = 7
_HEADER_FONT_SIZE = 6
_MIN_CELL_W      = 38
_MIN_CELL_H      = 22
_HEADER_W        = 46   # širina Y-os headera (lijevo)
_HEADER_H        = 18   # visina X-os headera (gore)

# ─── JET paleta ───────────────────────────────────────────────────────────────

def _jet_color(t: float) -> QColor:
    """
    JET paleta: 0.0 = tamno plava, 0.25 = cyan, 0.5 = zelena,
                0.75 = žuta, 1.0 = crvena.
    t je klampan na [0.0, 1.0].
    """
    t = max(0.0, min(1.0, t))

    # Segmenti: plava→cyan→zelena→žuta→crvena
    if t < 0.125:
        # tamno plava → plava
        s = t / 0.125
        r = 0
        g = 0
        b = int(128 + 127 * s)
    elif t < 0.375:
        # plava → cyan
        s = (t - 0.125) / 0.25
        r = 0
        g = int(255 * s)
        b = 255
    elif t < 0.625:
        # cyan → zelena → žuta
        s = (t - 0.375) / 0.25
        r = int(255 * s)
        g = 255
        b = int(255 * (1.0 - s))
    elif t < 0.875:
        # žuta → crvena
        s = (t - 0.625) / 0.25
        r = 255
        g = int(255 * (1.0 - s))
        b = 0
    else:
        # crvena → tamno crvena
        s = (t - 0.875) / 0.125
        r = int(255 * (1.0 - 0.5 * s))
        g = 0
        b = 0

    return QColor(r, g, b)


def _text_color_for_bg(bg: QColor) -> QColor:
    """Bijeli tekst na tamnoj pozadini, crni na svijetloj."""
    lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
    return QColor(Qt.GlobalColor.white) if lum < 140 else QColor(Qt.GlobalColor.black)


def _format_axis_label(val: float, unit: str) -> str:
    """Kratki label za osi — bez decimalnih mjesta za cijele brojeve."""
    if val == int(val):
        return f"{int(val)}"
    return f"{val:.1f}"


# ─── MapHeatWidget ─────────────────────────────────────────────────────────────

class MapHeatWidget(QWidget):
    """
    2D heat mapa za kalibracijske tablice.

    Signali:
      cell_clicked(row, col, display_value) — klik na ćeliju
    """

    cell_clicked = pyqtSignal(int, int, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._found_map: Optional[FoundMap] = None
        self._display:   list[list[float]] = []
        self._rows:      int = 0
        self._cols:      int = 0
        self._val_min:   float = 0.0
        self._val_max:   float = 1.0

        self._sel_row: int = -1
        self._sel_col: int = -1

        self._hover_row: int = -1
        self._hover_col: int = -1

        # Fontovi
        self._cell_font   = QFont("Consolas", _CELL_FONT_SIZE, QFont.Weight.Bold)
        self._header_font = QFont("Consolas", _HEADER_FONT_SIZE)

    # ── Javno API ─────────────────────────────────────────────────────────────

    def set_map(self, found_map: FoundMap) -> None:
        """Postavi mapu za prikaz. Automatski računa min/max."""
        self._found_map = found_map
        self._display   = found_map.get_2d_display()
        self._rows      = found_map.defn.rows
        self._cols      = found_map.defn.cols
        self._sel_row   = -1
        self._sel_col   = -1
        self._hover_row = -1
        self._hover_col = -1

        flat = found_map.display_values
        if flat:
            self._val_min = min(flat)
            self._val_max = max(flat)
            if self._val_max == self._val_min:
                self._val_max = self._val_min + 1.0
        else:
            self._val_min, self._val_max = 0.0, 1.0

        self.update()

    def set_cell_selected(self, row: int, col: int) -> None:
        """Programski označi ćeliju."""
        self._sel_row = row
        self._sel_col = col
        self.update()

    def clear(self) -> None:
        self._found_map = None
        self._display   = []
        self._rows = self._cols = 0
        self.update()

    # ── Geometrija ────────────────────────────────────────────────────────────

    def _cell_rect(self, row: int, col: int) -> QRect:
        """Vrati QRect ćelije (bez headera)."""
        cw, ch = self._cell_size()
        x = _HEADER_W + col * cw
        y = _HEADER_H + row * ch
        return QRect(x, y, cw, ch)

    def _cell_size(self) -> tuple[int, int]:
        """Dinamička veličina ćelije ovisno o prostoru."""
        if not self._rows or not self._cols:
            return _MIN_CELL_W, _MIN_CELL_H
        avail_w = max(self.width()  - _HEADER_W, self._cols * _MIN_CELL_W)
        avail_h = max(self.height() - _HEADER_H, self._rows * _MIN_CELL_H)
        cw = avail_w // self._cols
        ch = avail_h // self._rows
        return max(cw, _MIN_CELL_W), max(ch, _MIN_CELL_H)

    def _cell_at(self, pos: QPoint) -> tuple[int, int]:
        """Vrati (row, col) za točku, ili (-1,-1) ako je izvan mreže."""
        if not self._rows:
            return -1, -1
        cw, ch = self._cell_size()
        col = (pos.x() - _HEADER_W) // cw
        row = (pos.y() - _HEADER_H) // ch
        if 0 <= row < self._rows and 0 <= col < self._cols:
            return int(row), int(col)
        return -1, -1

    def _normalized(self, val: float) -> float:
        span = self._val_max - self._val_min
        if span == 0:
            return 0.5
        return (val - self._val_min) / span

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Pozadina
        p.fillRect(self.rect(), _BG_COLOR)

        if not self._found_map or not self._rows:
            p.setPen(QColor("#555566"))
            p.setFont(QFont("Consolas", 10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Nema podataka")
            return

        cw, ch = self._cell_size()
        defn    = self._found_map.defn

        # ── Ćelije ──────────────────────────────────────────────────────────
        p.setFont(self._cell_font)

        for r in range(self._rows):
            for c in range(self._cols):
                val  = self._display[r][c]
                t    = self._normalized(val)
                bg   = _jet_color(t)
                rect = self._cell_rect(r, c)

                p.fillRect(rect, bg)

                # Grid linije
                p.setPen(QPen(_GRID_COLOR, 1))
                p.drawRect(rect.adjusted(0, 0, -1, -1))

                # Hover highlight (lagana bijela overlay)
                if r == self._hover_row and c == self._hover_col:
                    overlay = QColor(255, 255, 255, 30)
                    p.fillRect(rect, overlay)

                # Tekst u ćeliji
                text_col = _text_color_for_bg(bg)
                p.setPen(text_col)
                label = self._format_cell_value(val, defn)
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # ── Odabrana ćelija — žuti border ───────────────────────────────────
        if 0 <= self._sel_row < self._rows and 0 <= self._sel_col < self._cols:
            sel_rect = self._cell_rect(self._sel_row, self._sel_col)
            pen = QPen(_SEL_BORDER, 2)
            p.setPen(pen)
            p.drawRect(sel_rect.adjusted(1, 1, -1, -1))

        # ── X-os header (RPM / gornja traka) ────────────────────────────────
        p.setFont(self._header_font)
        p.fillRect(QRect(0, 0, self.width(), _HEADER_H), _HEADER_BG)

        x_labels = self._x_axis_labels()
        for c in range(self._cols):
            rect = QRect(_HEADER_W + c * cw, 0, cw, _HEADER_H)
            p.setPen(_HEADER_FG)
            lbl = x_labels[c] if c < len(x_labels) else str(c)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, lbl)

        # X-os naziv
        if defn.axis_x and defn.axis_x.unit:
            p.setPen(QColor("#6677AA"))
            p.drawText(QRect(0, 0, _HEADER_W, _HEADER_H),
                       Qt.AlignmentFlag.AlignCenter, defn.axis_x.unit[:4])

        # ── Y-os header (Load / lijeva traka) ───────────────────────────────
        p.fillRect(QRect(0, _HEADER_H, _HEADER_W, self.height()), _HEADER_BG)

        y_labels = self._y_axis_labels()
        for r in range(self._rows):
            rect = QRect(0, _HEADER_H + r * ch, _HEADER_W, ch)
            p.setPen(_HEADER_FG)
            lbl = y_labels[r] if r < len(y_labels) else str(r)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, lbl)

        # Gornji lijevi kut (prazno)
        p.fillRect(QRect(0, 0, _HEADER_W, _HEADER_H), _HEADER_BG)

        # ── Color bar (desno, uski strip) ────────────────────────────────────
        self._draw_colorbar(p)

        p.end()

    def _draw_colorbar(self, p: QPainter) -> None:
        """Vertikalni color bar na desnoj strani s min/max labelama."""
        bar_w  = 12
        bar_x  = self.width() - bar_w - 2
        bar_y  = _HEADER_H
        bar_h  = self.height() - _HEADER_H - 4
        if bar_h < 20:
            return

        for i in range(bar_h):
            t = 1.0 - i / bar_h   # gore = max (crvena)
            p.setPen(_jet_color(t))
            p.drawLine(bar_x, bar_y + i, bar_x + bar_w, bar_y + i)

        # Labele min/max
        p.setFont(QFont("Consolas", 6))
        p.setPen(QColor("#AABBCC"))
        defn = self._found_map.defn
        max_lbl = self._format_cell_value(self._val_max, defn)
        min_lbl = self._format_cell_value(self._val_min, defn)
        p.drawText(bar_x - 28, bar_y + 8, max_lbl)
        p.drawText(bar_x - 28, bar_y + bar_h - 2, min_lbl)

    # ── Formatiranje ──────────────────────────────────────────────────────────

    @staticmethod
    def _format_cell_value(val: float, defn: MapDef) -> str:
        """Formatiraj vrijednost ćelije za prikaz."""
        if defn.scale != 0 and abs(defn.scale) < 0.1:
            return f"{val:.3f}"
        if defn.scale != 0 and abs(defn.scale) < 1.0:
            return f"{val:.2f}"
        if val == int(val):
            return str(int(val))
        return f"{val:.1f}"

    def _x_axis_labels(self) -> list[str]:
        defn = self._found_map.defn
        if defn.axis_x and defn.axis_x.values:
            return [_format_axis_label(v, defn.axis_x.unit)
                    for v in defn.axis_x.values[:self._cols]]
        return [str(c) for c in range(self._cols)]

    def _y_axis_labels(self) -> list[str]:
        defn = self._found_map.defn
        if defn.axis_y and defn.axis_y.values:
            return [_format_axis_label(v, defn.axis_y.unit)
                    for v in defn.axis_y.values[:self._rows]]
        return [str(r) for r in range(self._rows)]

    # ── Događaji ─────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            row, col = self._cell_at(event.pos())
            if row >= 0:
                self._sel_row = row
                self._sel_col = col
                val = self._display[row][col]
                self.cell_clicked.emit(row, col, val)
                self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        row, col = self._cell_at(event.pos())
        if row != self._hover_row or col != self._hover_col:
            self._hover_row = row
            self._hover_col = col
            self.update()

        if row >= 0 and self._found_map:
            val  = self._display[row][col]
            defn = self._found_map.defn
            unit = defn.unit or ""

            # X-os label (RPM)
            x_labels = self._x_axis_labels()
            x_lbl    = x_labels[col] if col < len(x_labels) else str(col)
            x_name   = (defn.axis_x.unit if defn.axis_x and defn.axis_x.unit
                        else "Col")

            # Y-os label (Load)
            y_labels = self._y_axis_labels()
            y_lbl    = y_labels[row] if row < len(y_labels) else str(row)
            y_name   = (defn.axis_y.unit if defn.axis_y and defn.axis_y.unit
                        else "Row")

            val_str = self._format_cell_value(val, defn)
            tip = (f"{x_name}: {x_lbl}  |  {y_name}: {y_lbl}"
                   f"\nVrijednost: {val_str} {unit}"
                   f"\n[{row}, {col}]")
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_row = -1
        self._hover_col = -1
        self.update()

    def sizeHint(self) -> QSize:
        if self._rows and self._cols:
            w = _HEADER_W + self._cols * _MIN_CELL_W + 50
            h = _HEADER_H + self._rows * _MIN_CELL_H + 10
            return QSize(max(w, 400), max(h, 300))
        return QSize(500, 350)


# ─── MapDeltaWidget ────────────────────────────────────────────────────────────

class MapDeltaWidget(QWidget):
    """
    Usporedba dvije mape — prikazuje razliku (map_b - map_a).

    Boje:
      zelena  = povećano (pozitivni delta)
      crvena  = smanjeno (negativni delta)
      sivo    = isto (delta == 0)
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._map_a:    Optional[FoundMap] = None
        self._map_b:    Optional[FoundMap] = None
        self._delta:    list[list[float]]  = []
        self._rows:     int = 0
        self._cols:     int = 0
        self._max_abs:  float = 1.0

        self._hover_row: int = -1
        self._hover_col: int = -1

        self._cell_font   = QFont("Consolas", _CELL_FONT_SIZE, QFont.Weight.Bold)
        self._header_font = QFont("Consolas", _HEADER_FONT_SIZE)

    def set_maps(self, map_a: FoundMap, map_b: FoundMap) -> None:
        """
        Postavi dvije mape za usporedbu.
        map_a = referentna (stock), map_b = nova (tune).
        Delta = map_b - map_a.
        """
        if map_a.defn.rows != map_b.defn.rows or map_a.defn.cols != map_b.defn.cols:
            raise ValueError(
                f"Dimenzije ne odgovaraju: "
                f"{map_a.defn.rows}×{map_a.defn.cols} vs "
                f"{map_b.defn.rows}×{map_b.defn.cols}"
            )

        self._map_a = map_a
        self._map_b = map_b
        self._rows  = map_a.defn.rows
        self._cols  = map_a.defn.cols

        a_vals = map_a.get_2d_display()
        b_vals = map_b.get_2d_display()

        self._delta = [
            [b_vals[r][c] - a_vals[r][c] for c in range(self._cols)]
            for r in range(self._rows)
        ]

        flat_abs = [abs(self._delta[r][c])
                    for r in range(self._rows)
                    for c in range(self._cols)]
        self._max_abs = max(flat_abs) if flat_abs else 1.0
        if self._max_abs == 0:
            self._max_abs = 1.0

        self._hover_row = -1
        self._hover_col = -1
        self.update()

    def clear(self) -> None:
        self._map_a = self._map_b = None
        self._delta = []
        self._rows  = self._cols = 0
        self.update()

    # ── Geometrija ────────────────────────────────────────────────────────────

    def _cell_size(self) -> tuple[int, int]:
        if not self._rows or not self._cols:
            return _MIN_CELL_W, _MIN_CELL_H
        avail_w = max(self.width()  - _HEADER_W, self._cols * _MIN_CELL_W)
        avail_h = max(self.height() - _HEADER_H, self._rows * _MIN_CELL_H)
        cw = avail_w // self._cols
        ch = avail_h // self._rows
        return max(cw, _MIN_CELL_W), max(ch, _MIN_CELL_H)

    def _cell_rect(self, row: int, col: int) -> QRect:
        cw, ch = self._cell_size()
        return QRect(_HEADER_W + col * cw, _HEADER_H + row * ch, cw, ch)

    def _cell_at(self, pos: QPoint) -> tuple[int, int]:
        if not self._rows:
            return -1, -1
        cw, ch = self._cell_size()
        col = (pos.x() - _HEADER_W) // cw
        row = (pos.y() - _HEADER_H) // ch
        if 0 <= row < self._rows and 0 <= col < self._cols:
            return int(row), int(col)
        return -1, -1

    @staticmethod
    def _delta_color(delta: float, max_abs: float) -> QColor:
        """
        Zelena za pozitivno, crvena za negativno, sivo za nulu.
        Intenzitet ovisi o relativnoj veličini delte.
        """
        if max_abs == 0 or delta == 0:
            return QColor("#3A3A4A")  # sivo

        t = min(abs(delta) / max_abs, 1.0)
        base_intensity = int(60 + 195 * t)

        if delta > 0:
            # zelena
            r = int(20  * (1 - t))
            g = base_intensity
            b = int(20  * (1 - t))
        else:
            # crvena
            r = base_intensity
            g = int(20 * (1 - t))
            b = int(20 * (1 - t))

        return QColor(r, g, b)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.fillRect(self.rect(), _BG_COLOR)

        if not self._map_a or not self._rows:
            p.setPen(QColor("#555566"))
            p.setFont(QFont("Consolas", 10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Nema podataka — postavi dvije mape")
            return

        cw, ch = self._cell_size()
        defn_a = self._map_a.defn

        # ── Ćelije ──────────────────────────────────────────────────────────
        p.setFont(self._cell_font)

        for r in range(self._rows):
            for c in range(self._cols):
                d    = self._delta[r][c]
                bg   = self._delta_color(d, self._max_abs)
                rect = self._cell_rect(r, c)

                p.fillRect(rect, bg)

                # Grid
                p.setPen(QPen(_GRID_COLOR, 1))
                p.drawRect(rect.adjusted(0, 0, -1, -1))

                # Hover
                if r == self._hover_row and c == self._hover_col:
                    p.fillRect(rect, QColor(255, 255, 255, 30))

                # Tekst
                text_col = _text_color_for_bg(bg)
                p.setPen(text_col)
                label = self._format_delta(d, defn_a)
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # ── Headeri ─────────────────────────────────────────────────────────
        p.setFont(self._header_font)

        # X-os (gore)
        p.fillRect(QRect(0, 0, self.width(), _HEADER_H), _HEADER_BG)
        x_labels = self._x_labels()
        for c in range(self._cols):
            rect = QRect(_HEADER_W + c * cw, 0, cw, _HEADER_H)
            p.setPen(_HEADER_FG)
            lbl = x_labels[c] if c < len(x_labels) else str(c)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, lbl)

        # Y-os (lijevo)
        p.fillRect(QRect(0, _HEADER_H, _HEADER_W, self.height()), _HEADER_BG)
        y_labels = self._y_labels()
        for r in range(self._rows):
            rect = QRect(0, _HEADER_H + r * ch, _HEADER_W, ch)
            p.setPen(_HEADER_FG)
            lbl = y_labels[r] if r < len(y_labels) else str(r)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, lbl)

        # Gornji lijevi kut + naslov
        p.fillRect(QRect(0, 0, _HEADER_W, _HEADER_H), _HEADER_BG)
        p.setPen(QColor("#6677AA"))
        p.drawText(QRect(0, 0, _HEADER_W, _HEADER_H),
                   Qt.AlignmentFlag.AlignCenter, "Δ")

        # Legenda (dolje desno)
        self._draw_legend(p)
        p.end()

    def _draw_legend(self, p: QPainter) -> None:
        """Mini legenda: zelena=+, sivo=0, crvena=-."""
        items = [
            (QColor("#3CB043"), "+veće"),
            (QColor("#3A3A4A"), "=isto"),
            (QColor("#CC2222"), "-manje"),
        ]
        x = self.width() - 80
        y = self.height() - 14 * len(items) - 4
        if y < 0:
            return
        p.setFont(QFont("Consolas", 6))
        for i, (col, txt) in enumerate(items):
            ry = y + i * 14
            p.fillRect(x, ry, 10, 10, col)
            p.setPen(QColor("#AABBCC"))
            p.drawText(x + 13, ry + 9, txt)

    # ── Formatiranje ──────────────────────────────────────────────────────────

    @staticmethod
    def _format_delta(d: float, defn: MapDef) -> str:
        if d == 0:
            return "0"
        sign = "+" if d > 0 else ""
        if abs(defn.scale) < 0.1 and defn.scale != 0:
            return f"{sign}{d:.3f}"
        if abs(defn.scale) < 1.0 and defn.scale != 0:
            return f"{sign}{d:.2f}"
        if d == int(d):
            return f"{sign}{int(d)}"
        return f"{sign}{d:.1f}"

    def _x_labels(self) -> list[str]:
        defn = self._map_a.defn
        if defn.axis_x and defn.axis_x.values:
            return [_format_axis_label(v, defn.axis_x.unit)
                    for v in defn.axis_x.values[:self._cols]]
        return [str(c) for c in range(self._cols)]

    def _y_labels(self) -> list[str]:
        defn = self._map_a.defn
        if defn.axis_y and defn.axis_y.values:
            return [_format_axis_label(v, defn.axis_y.unit)
                    for v in defn.axis_y.values[:self._rows]]
        return [str(r) for r in range(self._rows)]

    # ── Događaji ─────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        row, col = self._cell_at(event.pos())
        if row != self._hover_row or col != self._hover_col:
            self._hover_row = row
            self._hover_col = col
            self.update()

        if row >= 0 and self._map_a and self._map_b:
            d    = self._delta[row][col]
            defn = self._map_a.defn
            unit = defn.unit or ""

            a_val = self._map_a.get_2d_display()[row][col]
            b_val = self._map_b.get_2d_display()[row][col]

            x_lbl = (self._x_labels()[col] if col < len(self._x_labels())
                     else str(col))
            y_lbl = (self._y_labels()[row] if row < len(self._y_labels())
                     else str(row))

            x_name = (defn.axis_x.unit if defn.axis_x and defn.axis_x.unit
                      else "Col")
            y_name = (defn.axis_y.unit if defn.axis_y and defn.axis_y.unit
                      else "Row")

            tip = (
                f"{x_name}: {x_lbl}  |  {y_name}: {y_lbl}\n"
                f"A (stock): {a_val:.3f} {unit}\n"
                f"B (tune):  {b_val:.3f} {unit}\n"
                f"Δ (B−A):   {self._format_delta(d, defn)} {unit}"
            )
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_row = -1
        self._hover_col = -1
        self.update()

    def sizeHint(self) -> QSize:
        if self._rows and self._cols:
            w = _HEADER_W + self._cols * _MIN_CELL_W + 20
            h = _HEADER_H + self._rows * _MIN_CELL_H + 10
            return QSize(max(w, 400), max(h, 300))
        return QSize(500, 350)


# ─── MapMiniPreview ────────────────────────────────────────────────────────────

class MapMiniPreview(QWidget):
    """
    Mali preview widget (100×60px) za prikaz u tree/listi.
    Prikazuje samo boje — bez teksta, za brz pregled.
    """

    _FIXED_W = 100
    _FIXED_H = 60

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._FIXED_W, self._FIXED_H)

        self._display:  list[list[float]] = []
        self._rows:     int = 0
        self._cols:     int = 0
        self._val_min:  float = 0.0
        self._val_max:  float = 1.0

    def set_map(self, found_map: FoundMap) -> None:
        self._display = found_map.get_2d_display()
        self._rows    = found_map.defn.rows
        self._cols    = found_map.defn.cols

        flat = found_map.display_values
        if flat:
            self._val_min = min(flat)
            self._val_max = max(flat)
            if self._val_max == self._val_min:
                self._val_max = self._val_min + 1.0
        else:
            self._val_min, self._val_max = 0.0, 1.0

        self.update()

    def clear(self) -> None:
        self._display = []
        self._rows = self._cols = 0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), _BG_COLOR)

        if not self._rows or not self._cols:
            p.setPen(QColor("#444455"))
            p.setFont(QFont("Consolas", 7))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "—")
            p.end()
            return

        cw = self._FIXED_W / self._cols
        ch = self._FIXED_H / self._rows
        span = self._val_max - self._val_min

        for r in range(self._rows):
            for c in range(self._cols):
                val = self._display[r][c]
                t   = (val - self._val_min) / span if span else 0.5
                bg  = _jet_color(t)

                x = int(c * cw)
                y = int(r * ch)
                w = int((c + 1) * cw) - x
                h = int((r + 1) * ch) - y

                p.fillRect(QRect(x, y, w, h), bg)

        # Tanki border oko cijelog widgeta
        p.setPen(QPen(_GRID_COLOR, 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.end()

    def sizeHint(self) -> QSize:
        return QSize(self._FIXED_W, self._FIXED_H)
