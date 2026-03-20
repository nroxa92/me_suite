"""
ME17Suite — MapEditorWidget
Profesionalni inline editor za 2D/1D mape (PyQt6).

Značajke:
  - Inline edit s dvostrukim klikom (QLineEdit in-place)
  - Enter = potvrdi, Esc = odustani
  - Prikazuje DISPLAY vrijednosti (scale/offset iz MapDef)
  - Narančasta pozadina = dirty ćelija
  - Ctrl+Z / Ctrl+Y = undo / redo (max 20 koraka)
  - Bulk edit: označi više ćelija → upiši vrijednost
  - Paste iz clipboarda (Tab-separated values, Excel kompatibilno)
  - Validacija raw raspona s crvenim borderom i tooltipom
  - X-os (RPM) kao header kolona, Y-os (Load) kao header redci
"""

from __future__ import annotations

from typing import Optional
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QApplication, QToolTip, QSizePolicy,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut, QClipboard

from core.map_finder import FoundMap, MapDef
from core.map_editor import MapEditor


# ─── Stilske konstante ────────────────────────────────────────────────────────

BG_MAIN      = "#111113"
BG_HEADER    = "#1A1A2E"
BG_DIRTY     = "#3A2800"
BG_NORMAL    = "#1C1C1F"
BG_SELECTED  = "#1C2A3A"
CLR_DIRTY    = "#FF8C00"
CLR_SELECTED = "#4FC3F7"
CLR_ERROR    = "#FF3333"
CLR_TEXT     = "#E0E0E0"
CLR_HEADER   = "#888888"
CLR_LABEL    = "#FF8C00"
FONT_FAMILY  = "Consolas"
FONT_SIZE    = 10

DARK_STYLESHEET = f"""
QWidget {{
    background-color: {BG_MAIN};
    color: {CLR_TEXT};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}pt;
}}

QTableWidget {{
    background-color: {BG_NORMAL};
    gridline-color: #2A2A2E;
    border: 1px solid #2A2A2E;
    selection-background-color: {BG_SELECTED};
    selection-color: {CLR_TEXT};
    outline: none;
}}

QTableWidget::item {{
    padding: 2px 4px;
    border: 1px solid transparent;
}}

QTableWidget::item:selected {{
    background-color: {BG_SELECTED};
    border: 1px solid {CLR_SELECTED};
    color: {CLR_TEXT};
}}

QHeaderView {{
    background-color: {BG_HEADER};
}}

QHeaderView::section {{
    background-color: {BG_HEADER};
    color: {CLR_HEADER};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}pt;
    font-weight: bold;
    border: 1px solid #2A2A2E;
    padding: 2px 4px;
}}

QPushButton {{
    background-color: #222228;
    color: {CLR_TEXT};
    border: 1px solid #3A3A44;
    border-radius: 3px;
    padding: 3px 10px;
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}pt;
}}

QPushButton:hover {{
    background-color: #2A2A38;
    border-color: #5A5A6E;
}}

QPushButton:pressed {{
    background-color: #181820;
}}

QPushButton:disabled {{
    color: #555560;
    border-color: #2A2A2E;
}}

QPushButton#applyBtn {{
    background-color: #1A3A1A;
    border-color: #3A7A3A;
    color: #88EE88;
}}

QPushButton#applyBtn:hover {{
    background-color: #1F4A1F;
    border-color: #4A8A4A;
}}

QPushButton#applyBtn:disabled {{
    background-color: #141A14;
    border-color: #2A3A2A;
    color: #3A5A3A;
}}

QLabel {{
    background-color: transparent;
    color: {CLR_TEXT};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}pt;
}}

QLabel#dirtyLabel {{
    color: {CLR_LABEL};
    font-weight: bold;
}}
"""


# ─── UndoStack ────────────────────────────────────────────────────────────────

class UndoStack:
    """Jednostavna implementacija undo/redo stoga za editovanje ćelija tablice."""

    def __init__(self, max_size: int = 20):
        self._max  = max_size
        self._undo: deque[tuple] = deque()   # (row, col, old_val, new_val)
        self._redo: deque[tuple] = deque()

    def push(self, row: int, col: int, old_val: float, new_val: float) -> None:
        """Dodaj novu promjenu u undo stog. Briše redo stog."""
        self._undo.append((row, col, old_val, new_val))
        if len(self._undo) > self._max:
            self._undo.popleft()
        self._redo.clear()

    def undo(self) -> tuple | None:
        """Vrati zadnju promjenu. Vraća (row, col, old_val) ili None."""
        if not self._undo:
            return None
        row, col, old_val, new_val = self._undo.pop()
        self._redo.append((row, col, old_val, new_val))
        return (row, col, old_val)

    def redo(self) -> tuple | None:
        """Ponovi zadnju poništenu promjenu. Vraća (row, col, new_val) ili None."""
        if not self._redo:
            return None
        row, col, old_val, new_val = self._redo.pop()
        self._undo.append((row, col, old_val, new_val))
        return (row, col, new_val)

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return len(self._undo) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo) > 0

    @property
    def undo_count(self) -> int:
        return len(self._undo)


# ─── MapEditorWidget ──────────────────────────────────────────────────────────

class MapEditorWidget(QWidget):
    """
    Profesionalni inline editor za 2D/1D ECU mape.

    Signali:
        map_applied(str)   — emitira se nakon uspješnog Apply, argument = ime mape
        map_changed(bool)  — True ako postoje dirty promjene, False ako ne
    """

    map_applied = pyqtSignal(str)
    map_changed  = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._fm:      Optional[FoundMap]  = None
        self._editor:  Optional[MapEditor] = None

        # Originalne display vrijednosti (2D)
        self._orig:    list[list[float]]   = []
        # Trenutne display vrijednosti (2D, može biti dirty)
        self._current: list[list[float]]   = []
        # Skup (row, col) dirty ćelija
        self._dirty:   set[tuple[int,int]] = set()
        # Skup (row, col) ćelija s greškom validacije
        self._errors:  set[tuple[int,int]] = set()

        self._undo_stack = UndoStack(max_size=20)
        self._suppress_signals = False   # sprječava beskonačne rekurzije pri programatskom setanju

        self._setup_ui()
        self._setup_shortcuts()

    # ── UI izgradnja ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setStyleSheet(DARK_STYLESHEET)
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._btn_undo = QPushButton("Undo (0)")
        self._btn_undo.setEnabled(False)
        self._btn_undo.setMinimumWidth(90)
        self._btn_undo.clicked.connect(self._on_undo)

        self._btn_redo = QPushButton("Redo")
        self._btn_redo.setEnabled(False)
        self._btn_redo.setMinimumWidth(60)
        self._btn_redo.clicked.connect(self._on_redo)

        self._btn_reset_row = QPushButton("Reset row")
        self._btn_reset_row.setEnabled(False)
        self._btn_reset_row.clicked.connect(self._on_reset_row)

        self._btn_reset_all = QPushButton("Reset all")
        self._btn_reset_all.setEnabled(False)
        self._btn_reset_all.clicked.connect(self.reset_all)

        self._lbl_dirty = QLabel("")
        self._lbl_dirty.setObjectName("dirtyLabel")
        self._lbl_dirty.setMinimumWidth(100)

        self._btn_apply = QPushButton("Apply")
        self._btn_apply.setObjectName("applyBtn")
        self._btn_apply.setEnabled(False)
        self._btn_apply.setMinimumWidth(70)
        self._btn_apply.clicked.connect(self.apply_changes)

        toolbar.addWidget(self._btn_undo)
        toolbar.addWidget(self._btn_redo)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._btn_reset_row)
        toolbar.addWidget(self._btn_reset_all)
        toolbar.addStretch()
        toolbar.addWidget(self._lbl_dirty)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._btn_apply)

        root.addLayout(toolbar)

        # Tablica
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_cell_double_click)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.keyPressEvent = self._table_key_press   # type: ignore[method-assign]

        root.addWidget(self._table)

    def _setup_shortcuts(self) -> None:
        sc_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        sc_undo.activated.connect(self._on_undo)

        sc_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        sc_redo.activated.connect(self._on_redo)

    # ── Javno sučelje ─────────────────────────────────────────────────────────

    def set_found_map(self, fm: FoundMap, editor: MapEditor) -> None:
        """Postavi mapu za editovanje. Briše sve pending promjene."""
        self._fm     = fm
        self._editor = editor

        # Čitaj originalne vrijednosti (iz editora, koji čita iz binarnog fajla)
        display_2d = editor.read_map(fm)
        self._orig    = [list(row) for row in display_2d]
        self._current = [list(row) for row in display_2d]

        self._dirty.clear()
        self._errors.clear()
        self._undo_stack.clear()

        self._rebuild_table()
        self._update_ui_state()

    def apply_changes(self) -> bool:
        """
        Primjeni sve dirty promjene na ECU binary.
        Poziva MapEditor.write_map s trenutnim display vrijednostima.
        Vraća True ako je OK.
        """
        if not self._fm or not self._editor:
            return False
        if not self._dirty:
            return True
        if self._errors:
            return False

        result = self._editor.write_map(self._fm, self._current)
        if result.ok:
            # Ažuriraj originale na novo stanje
            self._orig  = [list(row) for row in self._current]
            self._dirty.clear()
            self._errors.clear()
            self._undo_stack.clear()
            self._refresh_all_cells()
            self._update_ui_state()
            self.map_applied.emit(self._fm.defn.name)
            return True
        return False

    def reset_all(self) -> None:
        """Vrati sve ćelije na originalne vrijednosti."""
        if not self._orig:
            return
        self._current = [list(row) for row in self._orig]
        self._dirty.clear()
        self._errors.clear()
        self._undo_stack.clear()
        self._refresh_all_cells()
        self._update_ui_state()

    def has_changes(self) -> bool:
        """True ako postoje dirty (neprimijenjene) promjene."""
        return len(self._dirty) > 0

    # ── Izgradnja tablice ─────────────────────────────────────────────────────

    def _rebuild_table(self) -> None:
        """Izgradnja tablice od nule (poziva se samo pri set_found_map)."""
        defn = self._fm.defn
        self._suppress_signals = True

        self._table.clear()
        self._table.setRowCount(defn.rows)
        self._table.setColumnCount(defn.cols)

        # Header kolona (X-os, npr. RPM)
        x_labels = self._get_axis_labels(defn.axis_x, defn.cols, "X")
        self._table.setHorizontalHeaderLabels(x_labels)

        # Header redaka (Y-os, npr. Load%)
        y_labels = self._get_axis_labels(defn.axis_y, defn.rows, "Y")
        self._table.setVerticalHeaderLabels(y_labels)

        # Bold font za headere
        h_font = QFont(FONT_FAMILY, FONT_SIZE)
        h_font.setBold(True)
        self._table.horizontalHeader().setFont(h_font)
        self._table.verticalHeader().setFont(h_font)

        # Popuni ćelije
        for r in range(defn.rows):
            for c in range(defn.cols):
                val = self._current[r][c]
                item = QTableWidgetItem(self._fmt(val, defn))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(r, c, item)
                self._apply_cell_style(r, c)

        self._suppress_signals = False

    def _get_axis_labels(self, axis_def, count: int, fallback_prefix: str) -> list[str]:
        """Vrati liste labela za os (RPM, Load%, ili generirani X0..Xn)."""
        if axis_def is not None and axis_def.values:
            vals = axis_def.values
            unit = axis_def.unit or ""
            # Ako ima točno toliko vrijednosti
            if len(vals) >= count:
                return [f"{v}{unit}" for v in vals[:count]]
            # Manje vrijednosti nego kolona — iskoristi što ima + upotpuni
            labels = [f"{v}{unit}" for v in vals]
            labels += [f"{fallback_prefix}{i}" for i in range(len(vals), count)]
            return labels
        # Bez osi — generirani headeri
        return [f"{fallback_prefix}{i}" for i in range(count)]

    def _fmt(self, val: float, defn: MapDef) -> str:
        """Formatira display vrijednost za prikaz u ćeliji."""
        if defn.dtype == "u8":
            # Integer-like prikaz za u8
            return f"{val:.2f}" if defn.scale not in (1.0, 0.75) else f"{int(round(val))}"
        if defn.scale != 0 and defn.scale < 0.01:
            return f"{val:.5f}"
        if defn.scale != 0 and defn.scale < 0.1:
            return f"{val:.4f}"
        return f"{val:.3f}"

    # ── Stilizacija ćelija ────────────────────────────────────────────────────

    def _apply_cell_style(self, row: int, col: int) -> None:
        """Primjeni boju pozadine i border na ćeliju prema njenom stanju."""
        item = self._table.item(row, col)
        if item is None:
            return

        key = (row, col)
        is_dirty = key in self._dirty
        is_error = key in self._errors

        if is_error:
            item.setBackground(QColor("#3A0000"))
            item.setForeground(QColor(CLR_ERROR))
            item.setToolTip(f"Van raspona: {self._get_range_str()}")
        elif is_dirty:
            item.setBackground(QColor(BG_DIRTY))
            item.setForeground(QColor(CLR_DIRTY))
            item.setToolTip("")
        else:
            item.setBackground(QColor(BG_NORMAL))
            item.setForeground(QColor(CLR_TEXT))
            item.setToolTip("")

    def _refresh_all_cells(self) -> None:
        """Ažuriraj tekst i stil svih ćelija iz self._current."""
        if not self._fm:
            return
        defn = self._fm.defn
        self._suppress_signals = True
        for r in range(defn.rows):
            for c in range(defn.cols):
                item = self._table.item(r, c)
                if item:
                    item.setText(self._fmt(self._current[r][c], defn))
                    self._apply_cell_style(r, c)
        self._suppress_signals = False

    def _refresh_cell(self, row: int, col: int) -> None:
        """Ažuriraj jednu ćeliju."""
        if not self._fm:
            return
        defn = self._fm.defn
        item = self._table.item(row, col)
        if item:
            item.setText(self._fmt(self._current[row][col], defn))
            self._apply_cell_style(row, col)

    def _get_range_str(self) -> str:
        """Vrati string s rasponom raw vrijednosti za tooltip."""
        if not self._fm:
            return "0–255"
        defn = self._fm.defn
        raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max
        disp_min = defn.raw_min * defn.scale + defn.offset_val
        disp_max = raw_max * defn.scale + defn.offset_val
        return f"{disp_min:.3f}–{disp_max:.3f} {defn.unit}"

    # ── UI stanje (gumbi, labeli) ─────────────────────────────────────────────

    def _update_ui_state(self) -> None:
        """Ažuriraj gumbe i dirty label prema trenutnom stanju."""
        n_dirty    = len(self._dirty)
        has_dirty  = n_dirty > 0
        has_undo   = self._undo_stack.can_undo
        has_redo   = self._undo_stack.can_redo
        has_errors = len(self._errors) > 0

        self._btn_undo.setEnabled(has_undo)
        self._btn_undo.setText(f"Undo ({self._undo_stack.undo_count})")
        self._btn_redo.setEnabled(has_redo)
        self._btn_reset_all.setEnabled(has_dirty)
        self._btn_apply.setEnabled(has_dirty and not has_errors)

        if has_dirty:
            self._lbl_dirty.setText(f"+{n_dirty} promjena")
        else:
            self._lbl_dirty.setText("")

        if not self._suppress_signals:
            self.map_changed.emit(has_dirty)

    # ── Editovanje ćelija ─────────────────────────────────────────────────────

    def _on_cell_double_click(self, row: int, col: int) -> None:
        """Otvori inline editor za ćeliju na dvostruki klik."""
        self._start_inline_edit(row, col)

    def _start_inline_edit(self, row: int, col: int) -> None:
        """Postavi ćeliju u edit mod pomoću QLineEdit delegata."""
        # Omogući edit trigger samo za ovu akciju
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self._table.editItem(self._table.item(row, col))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Poveži se na kraj editovanja
        editor = self._table.itemDelegate()
        # Koristimo closeEditor signal umjesto direktnog pristupa QLineEditu
        # Ovo se obrađuje u _table_key_press i commitData
        self._editing_cell = (row, col)

    def _commit_cell_edit(self, row: int, col: int, text: str) -> None:
        """Parsaj i validaraj unos, ažuriraj stanje."""
        if not self._fm:
            return
        defn = self._fm.defn

        text = text.strip().replace(",", ".")
        try:
            display_val = float(text)
        except ValueError:
            # Loš format — vrati staro
            self._refresh_cell(row, col)
            return

        # Konverzija u raw za validaciju
        if defn.scale == 0.0:
            self._refresh_cell(row, col)
            return

        raw = round((display_val - defn.offset_val) / defn.scale)
        raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max

        old_display = self._current[row][col]

        if not (defn.raw_min <= raw <= raw_max):
            # Nevalidan unos — označi grešku ali zadrži vrijednost radi prikaza
            self._errors.add((row, col))
            # Zaokruži na granicu i spremi (prikaži grešku ali ostavi dirty)
            clamped_raw = max(defn.raw_min, min(raw_max, raw))
            clamped_display = clamped_raw * defn.scale + defn.offset_val
            self._current[row][col] = display_val   # zadrži unos radi feedbacka
            item = self._table.item(row, col)
            if item:
                item.setText(text)
                item.setBackground(QColor("#3A0000"))
                item.setForeground(QColor(CLR_ERROR))
                item.setToolTip(f"Van raspona: {self._get_range_str()}")
            self._dirty.add((row, col))
            self._update_ui_state()
            return

        # Validan unos
        # Zaokruži display na najbliži valid raw
        snapped_display = raw * defn.scale + defn.offset_val
        self._errors.discard((row, col))

        if snapped_display != old_display:
            self._undo_stack.push(row, col, old_display, snapped_display)
            self._current[row][col] = snapped_display
            self._dirty.add((row, col))
        # Ako orig == current, makni iz dirty
        if self._current[row][col] == self._orig[row][col]:
            self._dirty.discard((row, col))

        self._refresh_cell(row, col)
        self._update_ui_state()

    def _set_cell_value(self, row: int, col: int, display_val: float,
                        push_undo: bool = True) -> None:
        """Programatski postavi vrijednost ćelije (za undo/redo/bulk edit)."""
        if not self._fm:
            return
        defn = self._fm.defn

        if defn.scale == 0.0:
            return

        raw = round((display_val - defn.offset_val) / defn.scale)
        raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max

        old_display = self._current[row][col]

        if not (defn.raw_min <= raw <= raw_max):
            return   # Ne postavljaj nevalidne vrijednosti programatski

        snapped = raw * defn.scale + defn.offset_val
        if push_undo and snapped != old_display:
            self._undo_stack.push(row, col, old_display, snapped)

        self._current[row][col] = snapped
        self._errors.discard((row, col))

        if snapped == self._orig[row][col]:
            self._dirty.discard((row, col))
        else:
            self._dirty.add((row, col))

        self._refresh_cell(row, col)

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def _on_undo(self) -> None:
        result = self._undo_stack.undo()
        if result is None:
            return
        row, col, old_val = result
        # Postavi staru vrijednost bez novog undo push-a
        self._set_cell_value(row, col, old_val, push_undo=False)
        self._update_ui_state()

    def _on_redo(self) -> None:
        result = self._undo_stack.redo()
        if result is None:
            return
        row, col, new_val = result
        self._set_cell_value(row, col, new_val, push_undo=False)
        self._update_ui_state()

    # ── Reset row ─────────────────────────────────────────────────────────────

    def _on_reset_row(self) -> None:
        """Vrati sve ćelije u selektiranim redovima na originalne vrijednosti."""
        if not self._fm or not self._orig:
            return
        rows = set(idx.row() for idx in self._table.selectedIndexes())
        for r in sorted(rows):
            for c in range(self._fm.defn.cols):
                orig_val = self._orig[r][c]
                if self._current[r][c] != orig_val:
                    self._undo_stack.push(r, c, self._current[r][c], orig_val)
                    self._current[r][c] = orig_val
                    self._dirty.discard((r, c))
                    self._errors.discard((r, c))
                    self._refresh_cell(r, c)
        self._update_ui_state()

    # ── Selekcija ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        has_sel = bool(self._table.selectedIndexes())
        self._btn_reset_row.setEnabled(has_sel and self.has_changes())

    # ── Tipkovnica (bulk edit, paste, navigacija) ─────────────────────────────

    def _table_key_press(self, event) -> None:
        """Presreće tipke na tablici za bulk edit i paste."""
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        key  = event.key()
        mods = event.modifiers()

        # Paste (Ctrl+V)
        if mods == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V:
            self._paste_from_clipboard()
            return

        # Ctrl+Z / Ctrl+Y — proslijedi widgetu (shortcutovi su registrirani)
        if mods == Qt.KeyboardModifier.ControlModifier and key in (Qt.Key.Key_Z, Qt.Key.Key_Y):
            QTableWidget.keyPressEvent(self._table, event)
            return

        # Delete / Backspace — ne briši (nema smisla za ECU kalibracije)

        # Alfanumerički znakovi → bulk edit (ako je više ćelija selektirano)
        selected = self._table.selectedIndexes()
        if len(selected) > 1 and event.text() and not mods & Qt.KeyboardModifier.ControlModifier:
            # Pokreni bulk edit dijalog/inline za prvu selektiranu ćeliju
            # ali primijeni na sve selektirane
            self._start_bulk_edit(selected, event.text())
            return

        # F2 ili Enter → edit fokusirane ćelije
        if key in (Qt.Key.Key_F2, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            idx = self._table.currentIndex()
            if idx.isValid():
                self._start_inline_edit(idx.row(), idx.column())
            return

        # Sve ostalo proslijedi
        QTableWidget.keyPressEvent(self._table, event)

    def _start_bulk_edit(self, indexes, initial_text: str = "") -> None:
        """Bulk edit — inline editor na prvoj selektiranoj ćeliji, primjeni na sve."""
        if not indexes or not self._fm:
            return

        # Sortiraj po row, col
        first = sorted(indexes, key=lambda i: (i.row(), i.column()))[0]
        r0, c0 = first.row(), first.column()

        # Privremeno omogući edit
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self._table.setCurrentCell(r0, c0)

        item = self._table.item(r0, c0)
        if item:
            # Postavi initial text za editor
            self._table.editItem(item)
            delegate = self._table.itemDelegate()
            # Pokušaj direktno postaviti tekst u editor (PyQt6 persistentEditor pristup)
            # Jednostavniji pristup: koristimo QTableWidget internu mehaniku
            # i pratimo rezultat kroz commitData

        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._pending_bulk_indexes = [(i.row(), i.column()) for i in indexes]

    def _paste_from_clipboard(self) -> None:
        """Paste Tab-separated vrijednosti iz clipboarda (Excel kompatibilno)."""
        if not self._fm:
            return

        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            return

        # Parse TSV
        rows_data = []
        for line in text.strip().splitlines():
            row_vals = []
            for cell in line.split("\t"):
                cell = cell.strip().replace(",", ".")
                try:
                    row_vals.append(float(cell))
                except ValueError:
                    row_vals.append(None)
            rows_data.append(row_vals)

        # Početna ćelija = gornji lijevi kut selekcije
        selected = self._table.selectedIndexes()
        if not selected:
            start_row, start_col = 0, 0
        else:
            start_row = min(i.row() for i in selected)
            start_col = min(i.column() for i in selected)

        defn  = self._fm.defn
        for dr, row_vals in enumerate(rows_data):
            r = start_row + dr
            if r >= defn.rows:
                break
            for dc, val in enumerate(row_vals):
                c = start_col + dc
                if c >= defn.cols or val is None:
                    continue
                old = self._current[r][c]
                self._set_cell_value(r, c, val, push_undo=True)

        self._update_ui_state()

    # ── Delegate commitData hook ──────────────────────────────────────────────
    # PyQt6 ne pruža jednostavan način da presretnemo kraj edit sesije bez
    # custom delegata. Koristimo itemChanged signal kao zamjenu.

    def _connect_item_changed(self) -> None:
        """Poveži itemChanged na commit (zove se jednom u setup-u)."""
        self._table.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Poziva se kad se item promijeni (uključujući programatske promjene)."""
        if self._suppress_signals:
            return
        row = item.row()
        col = item.column()
        text = item.text()
        self._commit_cell_edit(row, col, text)

        # Bulk: primijeni na sve ostale selektirane ćelije
        pending = getattr(self, "_pending_bulk_indexes", None)
        if pending:
            for r, c in pending:
                if (r, c) != (row, col):
                    self._set_cell_value(r, c, self._parse_display(text), push_undo=True)
            self._pending_bulk_indexes = []
            self._update_ui_state()

    def _parse_display(self, text: str) -> float:
        """Parsa tekst u float, vraća 0.0 pri grešci."""
        try:
            return float(text.strip().replace(",", "."))
        except ValueError:
            return 0.0


# ─── Inicijalizacija (poveži signale nakon __init__) ──────────────────────────

# Monkey-patch: poveži itemChanged u __init__ nakon što je _table napravljen
_orig_init = MapEditorWidget.__init__

def _patched_init(self, parent=None):
    _orig_init(self, parent)
    self._connect_item_changed()

MapEditorWidget.__init__ = _patched_init  # type: ignore[method-assign]
