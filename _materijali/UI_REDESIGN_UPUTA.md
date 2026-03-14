# ME17Suite — Uputa za UI Redesign (v2a Medium Dark)
# Za: Claude Code agent — ui/main_window.py

## CILJ
Preraditi vizualni stil `ui/main_window.py` prema priloženom predlošku v2a.
**NE mijenjati logiku** — samo stilove, font, veličine, boje, razmake.
Sve klase i metode ostaju iste.

---

## PALETA BOJA (QSS varijable — koristiti dosljedno svugdje)

```
Pozadina aplikacije:   #1e1e1e
Panel pozadina:        #252526
Toolbar/bar:           #2d2d2d
Hover highlight:       #2a2d2e
Aktivna selekcija:     #04395e
Border tamni:          #111111
Border srednji:        #333333
Border svjetli:        #555555

Tekst glavni:          #cccccc
Tekst sekundarni:      #969696
Tekst prigušen:        #666666

Akcent plavi:          #0e639c   (gumbi, aktivne stavke)
Akcent hover plavi:    #1177bb
Akcent teal:           #4ec9b0   (OK status, checksum)
Akcent žuti:           #e5c07b   (modificirano, upozorenje)
Akcent crveni:         #f48771   (DTC, greška, danger)
Akcent ljubičasti:     #9cdcfe   (identifikatori, naslovi mapa)

Statusbar pozadina:    #007acc
```

---

## GLOBAL STYLESHEET

```python
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
QMenuBar::item:selected {
    background: #444444;
    color: #ffffff;
}
QMenu {
    background: #252526;
    color: #cccccc;
    border: 1px solid #454545;
    padding: 3px 0;
}
QMenu::item {
    padding: 5px 20px 5px 12px;
}
QMenu::item:selected {
    background: #04395e;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #333333;
    margin: 3px 0;
}

/* ── TOOLBAR ── */
QToolBar {
    background: #2d2d2d;
    border-bottom: 1px solid #111;
    padding: 4px 8px;
    spacing: 3px;
}
QToolBar::separator {
    width: 1px;
    background: #555555;
    margin: 3px 5px;
}
QToolButton {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 12px;
    color: #cccccc;
    font-size: 13px;
}
QToolButton:hover {
    background: #4a4a4a;
    border-color: #666666;
}
QToolButton:pressed {
    background: #2a2a2a;
}
QToolButton:checked {
    background: #0e639c;
    border-color: #1177bb;
    color: #ffffff;
}

/* ── GUMBI (QPushButton) ── */
QPushButton {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 12px;
    color: #cccccc;
    font-size: 13px;
    min-height: 26px;
}
QPushButton:hover {
    background: #4a4a4a;
    border-color: #666666;
}
QPushButton:pressed {
    background: #2a2a2a;
}
QPushButton#btn_primary {
    background: #0e639c;
    border-color: #1177bb;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#btn_primary:hover {
    background: #1177bb;
}
QPushButton#btn_success {
    background: #007a4d;
    border-color: #009960;
    color: #ffffff;
}
QPushButton#btn_danger {
    background: #3c3c3c;
    border-color: #555555;
    color: #f48771;
}
QPushButton#btn_danger:hover {
    background: #4a2020;
    border-color: #f48771;
}

/* ── TREE WIDGET (mapa library) ── */
QTreeWidget {
    background: #252526;
    border: none;
    color: #cccccc;
    font-size: 13px;
    outline: none;
    show-decoration-selected: 1;
}
QTreeWidget::item {
    padding: 4px 4px;
    border-left: 2px solid transparent;
}
QTreeWidget::item:hover {
    background: #2a2d2e;
}
QTreeWidget::item:selected {
    background: #04395e;
    color: #ffffff;
    border-left: 2px solid #0e639c;
}
QTreeWidget::branch {
    background: #252526;
}

/* ── TABLICA (mapa grid) ── */
QTableWidget {
    background: #1e1e1e;
    border: none;
    gridline-color: #2a2a2a;
    color: #cccccc;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    selection-background-color: #04395e;
}
QTableWidget::item {
    padding: 2px 4px;
    border: none;
}
QTableWidget::item:selected {
    background: #04395e;
    color: #ffffff;
}
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
QScrollBar:vertical {
    background: #252526;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #555555;
    border-radius: 5px;
    min-height: 20px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #777777; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #252526;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #555555;
    border-radius: 5px;
    min-width: 20px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #777777; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── TAB WIDGET ── */
QTabWidget::pane {
    border: none;
    border-top: 1px solid #333333;
    background: #252526;
}
QTabBar::tab {
    background: #252526;
    color: #969696;
    padding: 7px 20px;
    border-top: 2px solid transparent;
    font-size: 13px;
}
QTabBar::tab:hover { color: #cccccc; background: #2d2d2d; }
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #ffffff;
    border-top-color: #0e639c;
}

/* ── LINE EDIT (search, input) ── */
QLineEdit {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 10px;
    color: #cccccc;
    font-size: 13px;
    selection-background-color: #0e639c;
}
QLineEdit:focus {
    border-color: #0e639c;
    background: #2a2a2a;
}
QLineEdit::placeholder { color: #555555; }

/* ── SPLITTER ── */
QSplitter::handle {
    background: #333333;
}
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* ── STATUS BAR ── */
QStatusBar {
    background: #007acc;
    color: rgba(255, 255, 255, 0.9);
    font-family: "Consolas", monospace;
    font-size: 12px;
    border-top: none;
}
QStatusBar::item {
    border-right: 1px solid rgba(255,255,255,0.2);
    padding: 0 12px;
}
QStatusBar QLabel {
    color: rgba(255, 255, 255, 0.9);
    font-family: "Consolas", monospace;
    font-size: 12px;
}

/* ── LABEL STILOVI (posebni) ── */
QLabel#lbl_map_title {
    font-family: "Consolas", monospace;
    font-size: 14px;
    font-weight: bold;
    color: #9cdcfe;
}
QLabel#lbl_section {
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    color: #999999;
    text-transform: uppercase;
}
QLabel#lbl_value_big {
    font-family: "Consolas", monospace;
    font-size: 32px;
    color: #9cdcfe;
    font-weight: bold;
}
QLabel#lbl_addr {
    font-family: "Consolas", monospace;
    font-size: 11px;
    color: #555555;
}
QLabel#lbl_ok    { color: #4ec9b0; font-weight: bold; }
QLabel#lbl_warn  { color: #e5c07b; font-weight: bold; }
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
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    background: #252526;
}

/* ── COMBO BOX ── */
QComboBox {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 10px;
    color: #cccccc;
    font-size: 13px;
    min-height: 26px;
}
QComboBox:hover { border-color: #666666; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #252526;
    border: 1px solid #555555;
    selection-background-color: #04395e;
    color: #cccccc;
}

/* ── TOOLTIP ── */
QToolTip {
    background: #2d2d2d;
    color: #cccccc;
    border: 1px solid #555555;
    padding: 4px 8px;
    font-size: 12px;
    border-radius: 3px;
}

/* ── MESSAGE BOX ── */
QMessageBox {
    background: #252526;
    color: #cccccc;
}

/* ── PROGRESS BAR ── */
QProgressBar {
    background: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: #0e639c;
    border-radius: 4px;
}
"""
```

---

## VELIČINE I LAYOUT

### Minimalna veličina prozora
```python
win.setMinimumSize(1280, 720)
win.resize(1440, 900)
```

### Sidebar širina
```python
sidebar.setFixedWidth(220)        # lijevi sidebar (Map Library)
properties_panel.setFixedWidth(270)  # desni Properties panel
```

### Visine panela
```python
toolbar_height     = 42   # px
tabs_height        = 34   # px
map_header_height  = 38   # px
bottom_panel_height = 110  # px (Hex + Log)
statusbar_height   = 24   # px
```

### Ćelije tablice
```python
table.verticalHeader().setDefaultSectionSize(32)    # visina retka
table.horizontalHeader().setDefaultSectionSize(54)  # širina stupca
table.setFont(QFont("Consolas", 10))                 # monospace
table.horizontalHeader().setFont(QFont("Consolas", 9))
# Zaglavlje retka (y-os)
table.verticalHeader().setDefaultSectionSize(32)
table.verticalHeader().setFont(QFont("Consolas", 9))
table.verticalHeader().setFixedWidth(44)
```

---

## BOJE ĆELIJA MAPE (heatmap)

### Ignition / u8 mapa (25.5° – 36° BTDC)
```python
# raw vrijednosti 32–48, scale 0.75°/bit
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

def get_cell_color(raw_val, raw_min, raw_max):
    p = (raw_val - raw_min) / max(raw_max - raw_min, 1)
    idx = min(int(p * len(MAP_COLORS_IGN)), len(MAP_COLORS_IGN) - 1)
    return MAP_COLORS_IGN[idx]  # (bg, fg)

# Primjena na TableWidgetItem:
bg, fg = get_cell_color(raw, raw_min, raw_max)
item.setBackground(QBrush(bg))
item.setForeground(QBrush(fg))
```

### Diff highlight (modificirane ćelije)
```python
DIFF_OUTLINE_COLOR = QColor("#e5c07b")  # žuta

# Za ćelije koje su modificirane u STG2:
item.setData(Qt.ItemDataRole.UserRole, "modified")
# U custom delegate ili nakon setItem():
item.setBackground(QBrush(QColor("#3a3010")))  # tamno žuta pozadina
```

---

## SIDEBAR — Map Library Panel

### Kategorije (font, boja, padding)
```python
cat_item = QTreeWidgetItem([f"⚡ Ignition"])
cat_item.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Bold))
cat_item.setForeground(0, QBrush(QColor("#9cdcfe")))
cat_item.setSizeHint(0, QSize(0, 28))

# Mapa stavka
map_item = QTreeWidgetItem(["ign_cyl2_normal"])
map_item.setFont(0, QFont("Segoe UI", 13))
map_item.setForeground(0, QBrush(QColor("#cccccc")))
map_item.setSizeHint(0, QSize(0, 26))

# Dim tekst (12×12) — desna strana
map_item.setText(1, "12×12")
map_item.setFont(1, QFont("Consolas", 10))
map_item.setForeground(1, QBrush(QColor("#555555")))

# Modificirano (narančasta točka) — kao ikona ili tekst
map_item.setIcon(0, modified_icon)  # ili setForeground za cijeli red
```

### Search box
```python
search = QLineEdit()
search.setPlaceholderText("🔍  Pretraži mape...")
search.setFixedHeight(32)
search.setObjectName("search_maps")
# Styling već pokriven u STYLESHEET QLineEdit
```

---

## MAP BAR (iznad tablice)

```python
# Horizontalni layout s elementima:
# [naziv mape] [badge 12×12·u8] [badge 0.75°/bit·°BTDC] [badge @0x02B7C0] --- [Copy] [Smooth] [Reset]

lbl_name = QLabel("ign_cyl2_normal")
lbl_name.setObjectName("lbl_map_title")   # → Consolas, 14px, #9cdcfe

# Badge labels
def make_badge(text, style="blue"):
    lbl = QLabel(text)
    colors = {
        "blue":  ("background:#0e3a5c;color:#9cdcfe;border:1px solid #0e639c;",),
        "green": ("background:#0d3321;color:#4ec9b0;border:1px solid #4ec9b0;",),
        "gray":  ("background:#2a2a2a;color:#888;border:1px solid #444;",),
    }
    lbl.setStyleSheet(f"""
        QLabel {{
            {colors[style][0]}
            border-radius: 10px;
            padding: 2px 8px;
            font-family: Consolas;
            font-size: 11px;
            font-weight: bold;
        }}
    """)
    return lbl

badge_dim  = make_badge("12×12 · u8", "blue")
badge_unit = make_badge("0.75°/bit · °BTDC", "green")
badge_addr = make_badge("@ 0x02B7C0", "gray")
```

---

## PROPERTIES PANEL (desno)

### Sekcija s grupom
```python
def make_section(title):
    group = QGroupBox(title)
    group.setStyleSheet("""
        QGroupBox {
            border: 1px solid #333;
            border-radius: 5px;
            margin-top: 8px;
            padding: 8px;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            color: #999;
            background: #252526;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            background: #252526;
        }
    """)
    return group
```

### Big value display
```python
# Okvir s velikom vrijednošću
frame = QFrame()
frame.setStyleSheet("""
    QFrame {
        background: #2a2a2a;
        border: 1px solid #333;
        border-left: 3px solid #0e639c;
        border-radius: 5px;
    }
""")
layout = QVBoxLayout(frame)

lbl_val  = QLabel("33.0°")
lbl_val.setObjectName("lbl_value_big")
lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

lbl_unit = QLabel("BTDC (Before Top Dead Centre)")
lbl_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
lbl_unit.setStyleSheet("color:#666; font-size:12px;")

lbl_raw = QLabel("RAW: 0x2C (44) · ADDR: 0x02B82C")
lbl_raw.setObjectName("lbl_addr")
lbl_raw.setAlignment(Qt.AlignmentFlag.AlignCenter)
```

### Step gumbi (6 komada, 2×3 grid)
```python
step_grid = QGridLayout()
steps = [
    ("▲ +0.75°", +0.75), ("▼ −0.75°", -0.75),
    ("▲ +1.5°",  +1.5),  ("▼ −1.5°",  -1.5),
    ("▲ +3.0°",  +3.0),  ("▼ −3.0°",  -3.0),
]
for i, (label, delta) in enumerate(steps):
    btn = QPushButton(label)
    btn.setFixedHeight(30)
    btn.setFont(QFont("Consolas", 11))
    btn.clicked.connect(lambda _, d=delta: self._step_cell(d))
    step_grid.addWidget(btn, i // 2, i % 2)
```

### Property row (key/value)
```python
def make_prop_row(key, value, value_style=""):
    row = QWidget()
    row.setFixedHeight(26)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)

    lbl_k = QLabel(key)
    lbl_k.setStyleSheet("color: #888; font-size: 13px;")

    lbl_v = QLabel(value)
    lbl_v.setFont(QFont("Consolas", 11))
    lbl_v.setStyleSheet(f"color: #9cdcfe; font-size: 12px; font-weight: bold; {value_style}")
    lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight)

    layout.addWidget(lbl_k)
    layout.addStretch()
    layout.addWidget(lbl_v)

    # Separator linija ispod
    row.setStyleSheet("border-bottom: 1px solid #2d2d2d;")
    return row
```

---

## HEX VIEW I LOG STRIP (donji panel)

```python
hex_view = QTextEdit()
hex_view.setReadOnly(True)
hex_view.setFont(QFont("Consolas", 12))
hex_view.setStyleSheet("""
    QTextEdit {
        background: #252526;
        color: #666666;
        border: none;
        border-right: 1px solid #333;
        padding: 6px 10px;
    }
""")

# Format hex retka (HTML u QTextEdit):
def format_hex_line(addr, data_bytes, highlight_idx=None):
    addr_html = f'<span style="color:#569cd6">0x{addr:06X}:</span>'
    bytes_html = ""
    for i, b in enumerate(data_bytes):
        hex_str = f"0x{b:02X}"
        if i == highlight_idx:
            bytes_html += f'<span style="color:#e5c07b;background:rgba(229,192,123,0.15)">{hex_str}</span> '
        else:
            bytes_html += f'<span>{hex_str}</span> '
    return f"{addr_html}  {bytes_html}"
```

```python
log_strip = QTextEdit()
log_strip.setReadOnly(True)
log_strip.setFont(QFont("Consolas", 12))
log_strip.setStyleSheet("""
    QTextEdit {
        background: #252526;
        color: #969696;
        border: none;
        padding: 6px 8px;
    }
""")

# Log metoda
LOG_COLORS = {
    "ok":   "#4ec9b0",
    "info": "#9cdcfe",
    "warn": "#e5c07b",
    "err":  "#f48771",
}
def log(msg, level="info"):
    from datetime import datetime
    t = datetime.now().strftime("%H:%M:%S")
    color = LOG_COLORS.get(level, "#969696")
    html = f'<span style="color:#555">{t}</span> <span style="color:{color}">{msg}</span>'
    log_strip.append(html)
```

---

## STATUS BAR

```python
sb = self.statusBar()
sb.setFixedHeight(24)
# Styling je u STYLESHEET

# Labele u statusbaru
def make_sb_label(text, bold=False):
    lbl = QLabel(text)
    lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    lbl.setStyleSheet("color: rgba(255,255,255,0.9); padding: 0 12px;")
    return lbl

lbl_hw      = make_sb_label("● MULTIPROG", bold=True)
lbl_hw.setStyleSheet("color: #4ec9b0; padding: 0 12px; font-weight: bold;")
lbl_file    = make_sb_label("ori_300.bin", bold=True)
lbl_modified = make_sb_label("● 42 promjene")
lbl_modified.setStyleSheet("color: #e5c07b; padding: 0 12px;")
lbl_cs      = make_sb_label("Checksum: OK")
lbl_cursor  = make_sb_label("RPM:3072 / R:9")
lbl_version = make_sb_label("ME17Suite v0.6.0")
lbl_version.setStyleSheet("color: rgba(255,255,255,0.4); padding: 0 12px;")

sb.addWidget(lbl_hw)
sb.addWidget(lbl_file)
sb.addWidget(lbl_modified)
sb.addWidget(lbl_cs)
sb.addWidget(lbl_cursor)
sb.addPermanentWidget(lbl_version)
```

---

## DTC PANEL STILOVI

```python
# DTC stavka u listi — crvena točka za aktivne
dtc_item = QListWidgetItem()
dtc_item.setFont(QFont("Consolas", 12))
# Aktivni DTC → crvena boja
dtc_item.setForeground(QBrush(QColor("#f48771")))
# Isključeni DTC → prigušena siva
dtc_item.setForeground(QBrush(QColor("#555555")))

# DTC OFF gumb
btn_off = QPushButton("DTC OFF")
btn_off.setObjectName("btn_danger")  # → crvena boja
btn_off.setFixedHeight(30)

# Upozorenje za opasne DTC-ove
warn_label = QLabel("⚠ Ovo isključuje zaštitu motora!")
warn_label.setStyleSheet("color: #e5c07b; font-size: 12px; font-weight: bold;")
```

---

## FONT HIJERARHIJA — SAŽETAK

| Element | Font | Veličina | Boja |
|---|---|---|---|
| Naziv mape (naslov) | Consolas | 14px bold | #9cdcfe |
| Sidebar stavke | Segoe UI | 13px | #cccccc |
| Sidebar kategorije | Segoe UI | 12px bold | #9cdcfe |
| Ćelije tablice | Consolas | 13px bold | (heatmap) |
| Osi tablice (header) | Consolas | 11px | #666666 |
| Big value | Consolas | 32px bold | #9cdcfe |
| Property key | Segoe UI | 13px | #888888 |
| Property value | Consolas | 12px bold | #9cdcfe |
| Hex view | Consolas | 12px | #666666 |
| Log | Consolas | 12px | (level boja) |
| Status bar | Consolas | 12px | rgba(255,255,255,0.9) |
| Badge (etikete) | Consolas | 11px bold | (badge boja) |

---

## CHECKLIST ZA IMPLEMENTACIJU

- [ ] Zamijeniti STYLESHEET u `main_window.py` s gornjim
- [ ] Promijeniti font svih labela → Segoe UI 13px
- [ ] Promijeniti font tablice → Consolas 13px, visina retka 32px
- [ ] Dodati badge labele u map_bar (dim, unit, addr)
- [ ] Ažurirati heatmap boje prema paleti
- [ ] Implementirati `make_prop_row()` u PropertiesPanel
- [ ] Ažurirati hex_view s HTML formatiranjem
- [ ] Ažurirati log_strip s HTML i bojama
- [ ] Statusbar: plava pozadina #007acc, Consolas 12px
- [ ] Minimalna veličina prozora: 1280×720

## NAPOMENE

1. **NE mijenjati** logiku klasa `UndoCmd`, `ScanWorker`, `DtcEngine`
2. **NE mijenjati** nazive metoda ni signala
3. Sve `setObjectName()` pozive dodati PRIJE `setStyleSheet()`
4. Testirati pokretanjem: `python main.py`
5. Ćelije tablice: koristiti `QTableWidgetItem` + `setBackground`/`setForeground`, ne CSS
