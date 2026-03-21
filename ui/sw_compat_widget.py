"""
ME17Suite — SW Kompatibilnost Widget
Prikazuje kompatibilnost učitanog (ili odabranog) SW ID-a s dostupnim mapama alata.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QFrame, QComboBox,
    QWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont


# ─── Kompatibilnost podaci ─────────────────────────────────────────────────────

# Kategorije mapa: (id, prikazni naziv, adresa/opis)
MAP_CATEGORIES = [
    ("fuel_2d",        "Gorivo / Fuel 2D",        "0x022066",  "12×16 Q15 LE, RPM×Load"),
    ("ignition_full",  "Paljenje / Ignition",      "0x02B730",  "19 mapa, 12×12 u8, 0.75°/bit"),
    ("lambda",         "Lambda / AFR",             "0x0266F0",  "12×18 Q15 LE + mirror"),
    ("rev_limiter",    "Rev Limiter",              "0x028E96",  "Period-encoded u16 LE"),
    ("sc_bypass",      "SC Bypass",                "0x0205A8",  "3 kopije: 0x020534/A8/0x029993"),
    ("sc_correction",  "SC Korekcija",             "0x02220E",  "9×7 Q14 LE"),
    ("boost",          "Boost Faktor",             "0x025DF8",  "1×40 Q14 LE"),
    ("temp_fuel",      "Temp. Korekcija goriva",   "0x025E50",  "1×156 Q14 LE"),
    ("lambda_trim",    "Lambda Trim",              "0x026DB8",  "12×18 Q15 LE"),
    ("torque",         "Torque / Moment",          "0x02A0D8",  "16×16 BE Q8 + mirror"),
    ("kfped",          "KFPED (drive-by-wire)",    "0x029548",  "10×20 u8 + mirror"),
    ("dtc_off",        "DTC Off",                  "0x021080",  "121 kodova (111 P + 10 U16Ax)"),
    ("checksum",       "Checksum Fix",             "0x000030",  "CRC32-HDLC BOOT region"),
]

# SW ID → razina podrške i popis problema (kategorija ID-a koji nije podržan)
COMPAT_DATA = {
    "10SW000776": {
        "level": "limited",
        "model": "1503 SC 2016",
        "year": "2016",
        "issues": ["fuel_2d", "boost", "temp_fuel", "lambda_trim", "torque", "ignition_full"],
        "upgrade": ["10SW025021", "10SW040008"],
        "upgrade_note": "1503 SC 230hp 2018 ili 1503 2019 (svi)",
    },
    "10SW000778": {
        "level": "limited",
        "model": "1503 SC 260hp 2016",
        "year": "2016",
        "issues": ["fuel_2d", "boost", "temp_fuel", "lambda_trim", "torque", "ignition_full"],
        "upgrade": ["10SW025021"],
        "upgrade_note": "1503 SC 230hp 2018 (najbliži SC ekvivalent)",
    },
    "10SW004675": {
        "level": "limited",
        "model": "1630 ACE SC 300hp 2016",
        "year": "2016",
        "issues": ["fuel_2d", "boost", "temp_fuel", "lambda_trim", "torque"],
        "upgrade": ["10SW040039"],
        "upgrade_note": "1630 ACE SC 300hp 2019 (NPRo base, puna podrška)",
    },
    "10SW012999": {
        "level": "partial",
        "model": "1503 SC 230hp 2017",
        "year": "2017",
        "issues": ["boost", "temp_fuel", "lambda_trim", "torque"],
        "upgrade": ["10SW025021"],
        "upgrade_note": "1503 SC 230hp 2018 (isti motor, puna podrška)",
    },
}

# Opis statusa za svaki nivo
LEVEL_LABELS = {
    "full":    ("PUNA PODRŠKA",  "#4CAF50"),
    "partial": ("PARCIJALNA",    "#FF8C00"),
    "limited": ("OGRANIČENA",    "#EF5350"),
}

# Boje za status
STATUS_COLORS = {
    "ok":   ("#1a3a1a", "#4CAF50", "✓"),
    "warn": ("#2a1f00", "#FF8C00", "⚠"),
    "bad":  ("#2a1010", "#EF5350", "✗"),
}

# Poznati SW ID-evi s punom podrškom (za dropdown)
KNOWN_FULL_SW = [
    ("10SW023910", "300hp SC 2018", "2018"),
    ("10SW040039", "300hp SC 2019 (NPRo base)", "2019"),
    ("10SW053727", "230hp SC 2020-2021", "2020"),
    ("10SW053729", "130/170hp NA 2020-2021", "2020"),
    ("10SW053774", "GTI90 2020-2021", "2020"),
    ("10SW039116", "Spark 900 2019-2021", "2019"),
    ("10SW025021", "GTI 1503 230hp SC 2018", "2018"),
    ("10SW025022", "GTI 1503 130hp NA 2018", "2018"),
    ("10SW025752", "GTI 1503 155hp NA 2018", "2018"),
    ("10SW040008", "GTI 1503 2019 (sve snage)", "2019"),
    ("10SW040962", "GTI 1503 130hp 2020", "2020"),
    ("10SW054296", "300hp SC 2020", "2020"),
    ("10SW066726", "300hp SC 2021", "2021"),
    ("10SW011328", "Spark 900 2016/2018", "2016"),
]


def _get_compat(sw_id: str) -> dict:
    """Vrati compat dict za dani SW ID — unknown/full ako nije u listi ograničenih."""
    if sw_id in COMPAT_DATA:
        return COMPAT_DATA[sw_id]
    # Provjeri je li poznati full-support SW
    for sw, model, year in KNOWN_FULL_SW:
        if sw_id == sw:
            return {"level": "full", "model": model, "year": year, "issues": [], "upgrade": [], "upgrade_note": ""}
    # Decimalni format (npr. 1037xxxxxx) = pre-2016, samo dokumentacija
    if sw_id.startswith("1037") or sw_id.startswith("1038"):
        return {
            "level": "limited",
            "model": "Pre-2016 (stari format)",
            "year": "pre-2016",
            "issues": [c[0] for c in MAP_CATEGORIES],
            "upgrade": [],
            "upgrade_note": "Nema direktnog upgradea — drugačija ECU generacija.",
        }
    # Sve ostalo (10SW2018+) = puna podrška
    return {"level": "full", "model": "Nepoznat (pretpostavljam punu podršku)", "year": "—", "issues": [], "upgrade": [], "upgrade_note": ""}


# ─── Widget ───────────────────────────────────────────────────────────────────

class SwCompatWidget(QDialog):
    """Modalni dijalog — SW kompatibilnost s mapama alata."""

    STYLESHEET = """
    QDialog {
        background: #111113;
        color: #C8C8D0;
    }
    QLabel {
        color: #C8C8D0;
        font-size: 13px;
    }
    QTableWidget {
        background: #18181c;
        border: 1px solid #2a2a32;
        gridline-color: #2a2a32;
        color: #C8C8D0;
        font-size: 12px;
        selection-background-color: #1A2F4A;
        border-radius: 4px;
    }
    QTableWidget::item { padding: 4px 8px; border: none; }
    QHeaderView::section {
        background: #141418;
        color: #808090;
        padding: 4px 8px;
        border: none;
        border-right: 1px solid #2a2a32;
        border-bottom: 1px solid #2a2a32;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 0.8px;
    }
    QScrollBar:vertical { background: #141418; width: 8px; border: none; }
    QScrollBar::handle:vertical { background: #2A2A32; border-radius: 4px; min-height: 20px; margin: 2px; }
    QScrollBar::handle:vertical:hover { background: #3A3A48; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QPushButton {
        background: #1C1C1F;
        border: 1px solid #2A2A32;
        border-radius: 3px;
        padding: 5px 18px;
        color: #C8C8D0;
        font-size: 12px;
        min-height: 26px;
    }
    QPushButton:hover { background: #1A2F4A; border-color: #4FC3F7; color: #4FC3F7; }
    QComboBox {
        background: #1C1C1F;
        border: 1px solid #2A2A32;
        border-radius: 3px;
        padding: 4px 8px;
        color: #C8C8D0;
        font-size: 12px;
        min-height: 26px;
    }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView {
        background: #1C1C1F;
        border: 1px solid #2A2A32;
        color: #C8C8D0;
        selection-background-color: #1A2F4A;
    }
    QFrame#sep {
        background: #2a2a32;
        max-height: 1px;
        border: none;
    }
    """

    def __init__(self, parent=None, sw_id: str = ""):
        super().__init__(parent)
        self.setWindowTitle("SW Kompatibilnost — ME17Suite")
        self.setModal(True)
        self.setMinimumSize(780, 580)
        self.resize(860, 640)
        self.setStyleSheet(self.STYLESHEET)

        self._active_sw = sw_id.strip()
        self._build_ui()
        if self._active_sw:
            self._refresh(self._active_sw)
        else:
            self._refresh_combo()

    # ── UI gradnja ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        # ── Naslov ─────────────────────────────────────────────────────────────
        title_lbl = QLabel("SW Kompatibilnost")
        title_lbl.setStyleSheet("font-size:18px; font-weight:bold; color:#4FC3F7; letter-spacing:0.5px;")
        root.addWidget(title_lbl)

        sub_lbl = QLabel("Provjera podržanosti mapa za odabrani SW ID")
        sub_lbl.setStyleSheet("font-size:12px; color:#606070;")
        root.addWidget(sub_lbl)

        sep0 = QFrame(); sep0.setObjectName("sep"); sep0.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep0)

        # ── SW odabir ──────────────────────────────────────────────────────────
        sw_row = QHBoxLayout(); sw_row.setSpacing(10)
        sw_label = QLabel("SW ID:")
        sw_label.setStyleSheet("color:#808090; font-size:12px;")
        sw_label.setFixedWidth(50)
        sw_row.addWidget(sw_label)

        self._sw_lbl = QLabel(self._active_sw or "—")
        self._sw_lbl.setStyleSheet(
            "font-family:'IBM Plex Mono','Consolas',monospace; font-size:15px; "
            "font-weight:bold; color:#E0E0E0; min-width:140px;"
        )
        sw_row.addWidget(self._sw_lbl)

        self._model_lbl = QLabel("")
        self._model_lbl.setStyleSheet("color:#808090; font-size:12px;")
        sw_row.addWidget(self._model_lbl)

        sw_row.addStretch()

        # Dropdown za ručni odabir
        sw_row.addWidget(QLabel("Provjeri:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(280)
        self._combo.setToolTip("Odaberi SW ID za provjeru kompatibilnosti")
        self._populate_combo()
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        sw_row.addWidget(self._combo)

        root.addLayout(sw_row)

        sep1 = QFrame(); sep1.setObjectName("sep"); sep1.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep1)

        # ── Tablica ────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["KATEGORIJA MAPE", "ADRESA", "NAPOMENA"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 260)
        self._table.setColumnWidth(1, 110)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(True)
        root.addWidget(self._table, 1)

        # ── Info box (upgrade prijedlog) ───────────────────────────────────────
        self._info_frame = QFrame()
        self._info_frame.setStyleSheet(
            "QFrame { background:#1a1f0a; border:1px solid #5a6a20; border-radius:4px; padding:8px; }"
        )
        info_lo = QVBoxLayout(self._info_frame)
        info_lo.setContentsMargins(12, 8, 12, 8)
        info_lo.setSpacing(4)
        self._info_title = QLabel()
        self._info_title.setStyleSheet("font-weight:bold; font-size:12px; color:#B8CC40;")
        self._info_body = QLabel()
        self._info_body.setStyleSheet("color:#C8C8D0; font-size:12px;")
        self._info_body.setWordWrap(True)
        info_lo.addWidget(self._info_title)
        info_lo.addWidget(self._info_body)
        self._info_frame.hide()
        root.addWidget(self._info_frame)

        sep2 = QFrame(); sep2.setObjectName("sep"); sep2.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep2)

        # ── Status bar ─────────────────────────────────────────────────────────
        footer = QHBoxLayout(); footer.setSpacing(14)

        self._count_lbl = QLabel()
        self._count_lbl.setStyleSheet("font-size:12px; color:#808090;")
        footer.addWidget(self._count_lbl)

        footer.addStretch()

        self._badge = QLabel()
        self._badge.setStyleSheet("font-size:11px; font-weight:bold; padding:3px 12px; border-radius:3px;")
        footer.addWidget(self._badge)

        btn_close = QPushButton("Zatvori")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        root.addLayout(footer)

    # ── Pomoćne metode ─────────────────────────────────────────────────────────

    def _populate_combo(self):
        """Puni dropdown sa svim poznatim SW ID-evima."""
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("— odaberi SW ID —", "")

        # Ograničeni / parcijalni
        for sw_id, data in sorted(COMPAT_DATA.items()):
            lvl = data["level"]
            icon = "⚠" if lvl == "partial" else "✗"
            self._combo.addItem(f"{icon} {sw_id}  —  {data['model']}", sw_id)

        # Puni
        for sw_id, model, year in KNOWN_FULL_SW:
            self._combo.addItem(f"✓ {sw_id}  —  {model}", sw_id)

        # Postavi na aktivni SW ako postoji
        if self._active_sw:
            for i in range(self._combo.count()):
                if self._combo.itemData(i) == self._active_sw:
                    self._combo.setCurrentIndex(i)
                    break
            else:
                # Nije u listi — dodaj ga na vrh
                self._combo.insertItem(1, f"  {self._active_sw}  (učitani)", self._active_sw)
                self._combo.setCurrentIndex(1)

        self._combo.blockSignals(False)

    def _on_combo_changed(self, idx: int):
        sw = self._combo.itemData(idx)
        if sw:
            self._refresh(sw)

    def _refresh_combo(self):
        """Ako nema učitanog SW-a — prikaži placeholder."""
        self._sw_lbl.setText("—")
        self._model_lbl.setText("Učitaj ECU ili odaberi iz dropdown-a")
        self._table.setRowCount(0)
        self._badge.setText("")
        self._count_lbl.setText("")
        self._info_frame.hide()

    def _refresh(self, sw_id: str):
        """Osvježi tablicu za dani SW ID."""
        self._sw_lbl.setText(sw_id)
        compat = _get_compat(sw_id)
        level = compat.get("level", "full")
        issues = set(compat.get("issues", []))
        model = compat.get("model", "—")
        year = compat.get("year", "—")

        self._model_lbl.setText(f"  {model}  ·  {year}")

        # ── Popuni tablicu ─────────────────────────────────────────────────────
        self._table.setRowCount(len(MAP_CATEGORIES))
        ok_count = 0
        for row, (cat_id, name, addr, note) in enumerate(MAP_CATEGORIES):
            if cat_id in issues:
                s = "bad"
            else:
                s = "ok"
                ok_count += 1

            bg, fg, icon = STATUS_COLORS[s]

            # Kolona 0: naziv kategorije s ikonom
            name_item = QTableWidgetItem(f"  {icon}  {name}")
            name_item.setForeground(QBrush(QColor(fg)))
            name_item.setBackground(QBrush(QColor(bg)))
            ft = QFont(); ft.setBold(True)
            name_item.setFont(ft)
            self._table.setItem(row, 0, name_item)

            # Kolona 1: adresa
            addr_item = QTableWidgetItem(addr)
            addr_item.setForeground(QBrush(QColor("#4FC3F7")))
            addr_item.setBackground(QBrush(QColor(bg)))
            addr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, addr_item)

            # Kolona 2: napomena
            note_str = note
            if cat_id in issues:
                note_str += "  — nije podržano za ovaj SW"
            note_item = QTableWidgetItem(note_str)
            note_item.setForeground(QBrush(QColor("#808090") if s == "ok" else QColor("#c08040")))
            note_item.setBackground(QBrush(QColor(bg)))
            self._table.setItem(row, 2, note_item)

            self._table.setRowHeight(row, 30)

        # ── Brojač ─────────────────────────────────────────────────────────────
        total = len(MAP_CATEGORIES)
        self._count_lbl.setText(f"{ok_count} od {total} kategorija podržano")

        # ── Badge ──────────────────────────────────────────────────────────────
        badge_text, badge_color = LEVEL_LABELS.get(level, ("PUNA PODRŠKA", "#4CAF50"))
        self._badge.setText(badge_text)
        self._badge.setStyleSheet(
            f"font-size:11px; font-weight:bold; padding:3px 12px; border-radius:3px; "
            f"background:{badge_color}22; border:1px solid {badge_color}; color:{badge_color};"
        )

        # ── Upgrade prijedlog ──────────────────────────────────────────────────
        upgrades = compat.get("upgrade", [])
        upgrade_note = compat.get("upgrade_note", "")
        if upgrades and level != "full":
            upg_str = "  ·  ".join(upgrades)
            self._info_title.setText(f"⬆  Preporučeni SW upgrade")
            self._info_body.setText(
                f"Za punu podršku svih mapa, razmotri upgrade na:  {upg_str}\n{upgrade_note}"
            )
            self._info_frame.show()
        else:
            self._info_frame.hide()

    # ── Javno sučelje ──────────────────────────────────────────────────────────

    def set_sw_id(self, sw_id: str):
        """Postavi SW ID izvana (npr. kad se učita novi ECU)."""
        self._active_sw = sw_id.strip()
        self._populate_combo()
        if self._active_sw:
            self._refresh(self._active_sw)
        else:
            self._refresh_combo()
