"""
ME17Suite — CAN Network Widget
Prikaz i upravljanje CAN porukama ECU ↔ SAT (gauge cluster)

Podrzani SAT tipovi:
  - Spark SAT 2014-2024 (MC9S08DZ60)
  - GTI/GTS SAT 2012-2020 (MC9S08DZ128)
  - MS/VS SAT 2020+ (Renesas V850 D70F3554M)

Izvor podataka: binarna analiza ECU flash dumpova (2021)
  - GTI/SC 1630 CAN table  @ 0x0433BC  (10SW066726)
  - Spark 900 HO CAN table @ 0x042EC4  (10SW053774)
  - CAN TX timing table    @ table_addr - 14 (LE u16 array, ms)
  - CAN descriptor struct  @ CODE region 0x0173C0+ (5A opcode entries)

Payload formati: vidjeti core/can_decoder.py za detalje.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QSplitter, QHeaderView, QFrame, QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont


# ─── CAN ID baza podataka ─────────────────────────────────────────────────────
#
# Payload format (u zagradama):
#   0x0108 [0]=flags [1:3]=RPM_raw_BE (RPM=raw*0.25) [3]=TPS% [4]=MAP_kPa
#   0x0110 [0]=flags [1]=coolant(raw-40=°C) [2]=IAT(raw-40=°C)
#   0x012C [0:4]=seconds_BE (/3600=h) [4:6]=service_remaining_BE (*0.1h)
#   0x013C [0]=state(0=off,1=crank,2=run,3=limp) [1]=MIL [2]=rev_lim
#   0x017C [0]=dtc_count [1:3]=code1_BE [3]=status1 [4:6]=code2_BE
#   0x0214 session/extended diag (BRP proprietary)
#
# CAN TX timing (ms) iz ECU binarne analize — vidjeti core/can_decoder.py

# CAN ID: (opis poruke s payload formatom, tip: "common" | "spark" | "gti_sc")
CAN_ID_INFO: dict[int, tuple[str, str]] = {
    0x0108: ("Engine speed  [RPM=raw*0.25, TPS, MAP]  @18ms",        "common"),
    0x0110: ("Coolant/IAT temp  [byte1-40=°C]  @131-147ms",          "common"),
    0x012C: ("Engine hours/service  [u32BE sec/3600=h]  @196-223ms", "common"),
    0x0138: ("Throttle / speed status  @20-22ms",                    "common"),
    0x013C: ("Engine status flags  [state,MIL,revlim]  @20-22ms",    "common"),
    0x015B: ("Main ECU broadcast A  @8ms",                           "common"),
    0x015C: ("Main ECU broadcast B  @16-22ms",                       "common"),
    0x017C: ("DTC / fault status  [count,code1,code2]  event-driven","common"),
    0x0214: ("Extended diagnostics  @132-148ms",                     "common"),
    0x0134: ("Spark-specific A  @20ms",                              "spark"),
    0x0154: ("Spark-specific B  @16ms",                              "spark"),
    0x0148: ("GTI/SC 1630 specific  @22ms",                          "gti_sc"),
    0x00BF: ("GTI extra config 1  (DLC=1, 0xFF)",                    "gti_sc"),
    0x00CD: ("GTI extra config 2  (DLC=1, 0xFF)",                    "gti_sc"),
    0x00DC: ("GTI extra config 3  (DLC=1, 0xFF)",                    "gti_sc"),
    # sdtpro / field-verified IDs (engine running, live broadcast)
    0x0103: ("Spark EGT / TPS broadcast  [sdtpro: d[4]*1.0125-60=°C, d[6:8]=TPS]  @~50ms",  "spark"),
    0x0104: ("Spark throttle body  [sdtpro: d[0:2]/100=°]  @~50ms",                          "spark"),
    0x0316: ("Engine oil temp  [sdtpro: d[3]*0.943-17.2=°C]  @~50ms",                        "common"),
    0x0342: ("MUX broadcast  [sdtpro: d[0]=0xDE→ECT, 0xAA→MAP_hPa, 0xC1→MAT]  @~20ms",     "common"),
}

# Fizicke adrese CAN ID tablice u binarnom fajlu (BE u16, 0x0000 terminated)
# Potvrdjeno binarnom analizom ECU flash dumpova (2021):
#   spark @ 0x042EC4: 015B 0154 0134 013C 015C 0138 0108 0214 012C 0110 0108 017C 0000
#   gti300 @ 0x0433BC: 015B 015C 0148 013C 015C 0138 0108 0214 012C 0110 0108 017C 0000
# CAN timing table @ (addr - 14): LE u16 array, ms period per ID (index-matched)
CAN_TABLE_ADDR: dict[str, int] = {
    "spark":  0x042EC4,   # Spark ECU (SW: 1037xxxxxx / 10SW011328 / 10SW053774)
    "gti300": 0x0433BC,   # GTI/SC 1630 ECU (SW: 10SWxxxxxx)
}

# CAN timing table offset relative to CAN ID table (14 bytes = 7 LE u16 before IDs)
# Full timing: @ CAN_TABLE_ADDR - 14  (10 entries, LE u16, ms period)
CAN_TIMING_OFFSET: int = -14

# ECU CAN ID profili — potvrdjeni binarnom analizom ECU flash-a (2021)
# Redosljed odgovara CAN TX redoslijedu u ECU tablici
ECU_PROFILES: dict[str, list[int]] = {
    "spark": [
        0x015B, 0x0154, 0x0134, 0x013C, 0x015C, 0x0138,
        0x0108, 0x0214, 0x012C, 0x0110, 0x017C,
    ],
    "gti300": [
        0x015B, 0x015C, 0x0148, 0x013C, 0x0138,
        0x0108, 0x0214, 0x012C, 0x0110, 0x017C,
        0x00BF, 0x00CD, 0x00DC,
    ],
}

# SAT CAN profili — ID-ovi koje SAT PRIMA (subscribe lista)
# Odredjeno analizom SAT <-> ECU kompatibilnosti i ECU TX profila
# Napomena: SAT firmware dumpovi imaju entropy 7.997 (enkriptirani/komprimirani) —
#   direktna binarna analiza nije moguca; profili su izvedeni iz ECU TX analize.
SAT_PROFILES: dict[str, dict] = {
    "Spark SAT  (MC9S08DZ60)": {
        "subscribed_ids": [
            0x015B, 0x0154, 0x0134, 0x013C, 0x015C, 0x0138,
            0x0108, 0x0214, 0x012C, 0x0110, 0x017C,
        ],
        "mcu": "Freescale MC9S08DZ60  (HCS08, 8-bit)",
        "notes": (
            "SAT firmware dumpovi (0x4F840B) imaju entropy ~8.0 (enkriptirani/comprimirani).\n"
            "Profil izveden iz ECU TX analize — potvrdjeni sparring ECU 300hp+Spark SAT.\n"
            "ID-ovi 0x0134 i 0x0154 su Spark-specificni — GTI ECU ih ne salje."
        ),
    },
    "GTI/GTS SAT  (MC9S08DZ128)": {
        "subscribed_ids": [
            0x015B, 0x015C, 0x0148, 0x013C, 0x0138,
            0x0108, 0x0214, 0x012C, 0x0110, 0x017C,
        ],
        "mcu": "Freescale MC9S08DZ128  (HCS08, 8-bit)",
        "notes": (
            "Nativni SAT za GTI/GTS. SAT firmware (0x4F440B) enkriptiran — bez CAN ID-ova.\n"
            "Profil izveden iz ECU GTI TX tablice @ 0x0433BC.\n"
            "0x0148 = GTI/SC 1630 specificna poruka."
        ),
    },
    "MS/VS SAT  2020+  (Renesas V850)": {
        "subscribed_ids": [
            0x015B, 0x015C, 0x0148, 0x013C, 0x0138,
            0x0108, 0x0214, 0x012C, 0x0110, 0x017C,
        ],
        "mcu": "Renesas V850ES/SF3  (D70F3554M, 32-bit)",
        "notes": (
            "Noviji model SAT (2020+ MS/VS serija). Pretpostavka: isti ID set kao GTI SAT.\n"
            "Direktna binarna analiza firmware-a nije dostupna."
        ),
    },
}

# SAT konfiguracije — generirane iz SAT_PROFILES
# Odvojeno za backward-kompatibilnost widgeta
SAT_CONFIGS: dict[str, dict] = {
    "Spark SAT  2014-2024  (MC9S08DZ60)": {
        "ids": SAT_PROFILES["Spark SAT  (MC9S08DZ60)"]["subscribed_ids"],
        "mcu":   SAT_PROFILES["Spark SAT  (MC9S08DZ60)"]["mcu"],
        "notes": (
            "POTVRDJENO: 300hp ECU + Spark SAT = radi bez izmjena.\n"
            "230hp ECU koristi isti CAN ID set kao 300hp — ocekuje se da radi.\n"
            "ID-ovi 0x0134 i 0x0154 su Spark-specificni — ECU ih ne salje,\n"
            "prikazne pozicije za te poruke bit ce prazne.\n"
            "SAT firmware (325KB) je enkriptiran — direktna CAN analiza nije moguca."
        ),
        "dump":  r"C:\Users\SeaDoo\Desktop\MCU\MC9S08DZ60",
    },
    "GTI/GTS SAT  2012-2020  (MC9S08DZ128)": {
        "ids": SAT_PROFILES["GTI/GTS SAT  (MC9S08DZ128)"]["subscribed_ids"],
        "mcu":   SAT_PROFILES["GTI/GTS SAT  (MC9S08DZ128)"]["mcu"],
        "notes": (
            "Nativni SAT za GTI/GTS ECU. Kompatibilan sa 300hp ECU-om\n"
            "(identicni zajednicki CAN ID set).\n"
            "SAT firmware (325KB) je enkriptiran — direktna CAN analiza nije moguca.\n"
            "0x0148 = GTI/SC 1630 specificna poruka (Spark ECU ne salje)."
        ),
        "dump":  r"C:\Users\SeaDoo\Desktop\MCU\MC9S08DZ128",
    },
    "MS/VS SAT  2020+  (Renesas V850 D70F3554M)": {
        "ids": SAT_PROFILES["MS/VS SAT  2020+  (Renesas V850)"]["subscribed_ids"],
        "mcu":   SAT_PROFILES["MS/VS SAT  2020+  (Renesas V850)"]["mcu"],
        "notes": (
            "Noviji model SAT (2020+ MS/VS serija). Renesas V850 MCU.\n"
            "Pretpostavka kompatibilnosti — MCU dump analiza u toku.\n"
            "Pretpostavlja se isti ID set kao GTI SAT."
        ),
        "dump":  r"C:\Users\SeaDoo\Desktop\MCU\D70F3554M",
    },
}

# SW ID skupovi za detekciju tipa ECU-a
_SPARK_SW_IDS: set[str] = {"10SW011328"}
_SC_1630_SW_IDS: set[str] = {
    "10SW066726", "10SW040039", "10SW004672", "10SW082806", "10SW053727",
}


def _detect_ecu_type(sw_id: str) -> str:
    """Vrati 'spark' ili 'gti300' na osnovu SW ID-a."""
    if sw_id.startswith("1037") or sw_id in _SPARK_SW_IDS:
        return "spark"
    return "gti300"   # default: GTI/SC 1630 format


def _make_sep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background:#333333; max-height:1px; margin:4px 0;")
    return sep


# ─── CAN Network Widget ───────────────────────────────────────────────────────

class CanNetworkWidget(QWidget):
    """CAN Network tab — prikaz ECU CAN ID-ova i kompatibilnosti sa SAT-om."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._eng        = None
        self._sw_id      = ""
        self._ecu_type   = "gti300"
        self._live_ids:    list[int] = []
        self._profile_ids: list[int] = ECU_PROFILES["gti300"].copy()

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # ── Header bar ──────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet("background:#252526; border-bottom:1px solid #333333;")
        hdr_lo = QHBoxLayout(hdr)
        hdr_lo.setContentsMargins(12, 6, 12, 6)
        hdr_lo.setSpacing(16)

        t = QLabel("CAN NETWORK")
        t.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1.5px;"
        )
        hdr_lo.addWidget(t)

        self._ecu_lbl = QLabel("ECU: —  ·  CAN table: —")
        self._ecu_lbl.setStyleSheet(
            "color:#9cdcfe; font-family:Consolas; font-size:12px;"
        )
        hdr_lo.addWidget(self._ecu_lbl)
        hdr_lo.addStretch()

        self._btn_read = QPushButton("Citaj iz binarnog")
        self._btn_read.setFixedHeight(26)
        self._btn_read.setEnabled(False)
        self._btn_read.setToolTip(
            "Procitaj aktivne CAN ID-ove direktno iz ucitanog .bin fajla\n"
            "(iz poznate adrese CAN ID tablice u CODE regiji)"
        )
        self._btn_read.clicked.connect(self._read_from_binary)
        hdr_lo.addWidget(self._btn_read)

        lo.addWidget(hdr)

        # ── Glavni splitter: ECU | SAT ────────────────────────────────────
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(1)
        split.setStyleSheet("QSplitter::handle { background:#333333; }")

        # ── Lijevo: ECU CAN ID-ovi ─────────────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 6, 12)
        ll.setSpacing(6)

        lh_lo = QHBoxLayout(); lh_lo.setSpacing(8)
        ll_title = QLabel("ECU TX poruke  (salje SAT-u)")
        ll_title.setStyleSheet("color:#9cdcfe; font-size:13px; font-weight:bold;")
        lh_lo.addWidget(ll_title)
        self._source_lbl = QLabel("(profil)")
        self._source_lbl.setStyleSheet(
            "color:#555555; font-size:11px; font-family:Consolas;"
        )
        lh_lo.addWidget(self._source_lbl)
        lh_lo.addStretch()
        ll.addLayout(lh_lo)

        self._ecu_table = QTableWidget(0, 4)
        self._ecu_table.setHorizontalHeaderLabels(["CAN ID", "Dec", "Opis", "Vrsta"])
        eh = self._ecu_table.horizontalHeader()
        eh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        eh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        eh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        eh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._ecu_table.setColumnWidth(0, 82)
        self._ecu_table.setColumnWidth(1, 56)
        self._ecu_table.verticalHeader().hide()
        self._ecu_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._ecu_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._ecu_table.setFont(QFont("Consolas", 12))
        ll.addWidget(self._ecu_table, 1)

        legend_lo = QHBoxLayout(); legend_lo.setSpacing(16)
        for txt, col in [
            ("zajednicki", "#cccccc"),
            ("spark-specific", "#9cdcfe"),
            ("gti/sc-specific", "#4ec9b0"),
        ]:
            lbl = QLabel(f"■ {txt}")
            lbl.setStyleSheet(
                f"color:{col}; font-size:11px; font-family:Consolas;"
            )
            legend_lo.addWidget(lbl)
        legend_lo.addStretch()
        ll.addLayout(legend_lo)

        proto_note = QLabel(
            "Protokol: BRP proprietarni CAN  ·  250 kbps  ·  standard 11-bit frames"
        )
        proto_note.setStyleSheet(
            "color:#444444; font-size:11px; font-family:Consolas; padding:2px 0;"
        )
        ll.addWidget(proto_note)

        split.addWidget(left)

        # ── Desno: SAT selektor + kompatibilnost ───────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 12, 12, 12)
        rl.setSpacing(6)

        rl_title = QLabel("SAT kompatibilnost")
        rl_title.setStyleSheet("color:#4ec9b0; font-size:13px; font-weight:bold;")
        rl.addWidget(rl_title)

        sat_row = QHBoxLayout(); sat_row.setSpacing(8)
        sat_lbl = QLabel("SAT:")
        sat_lbl.setStyleSheet("color:#888888; font-size:13px;")
        sat_row.addWidget(sat_lbl)
        self._sat_combo = QComboBox()
        self._sat_combo.addItems(list(SAT_CONFIGS.keys()))
        self._sat_combo.currentIndexChanged.connect(self._update_compat)
        sat_row.addWidget(self._sat_combo, 1)
        rl.addLayout(sat_row)

        self._sat_info_lbl = QLabel()
        self._sat_info_lbl.setStyleSheet(
            "color:#666666; font-size:12px; background:#252526; "
            "border:1px solid #333333; border-radius:4px; padding:6px 8px;"
        )
        self._sat_info_lbl.setWordWrap(True)
        rl.addWidget(self._sat_info_lbl)

        rl.addWidget(_make_sep())

        compat_title = QLabel("CAN ID matrica")
        compat_title.setStyleSheet(
            "color:#4ec9b0; font-size:12px; font-weight:bold;"
        )
        rl.addWidget(compat_title)

        self._compat_table = QTableWidget(0, 5)
        self._compat_table.setHorizontalHeaderLabels(
            ["CAN ID", "Dec", "Opis", "ECU", "SAT"]
        )
        ch = self._compat_table.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        ch.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        ch.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        ch.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        ch.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._compat_table.setColumnWidth(0, 82)
        self._compat_table.setColumnWidth(1, 56)
        self._compat_table.setColumnWidth(3, 44)
        self._compat_table.setColumnWidth(4, 44)
        self._compat_table.verticalHeader().hide()
        self._compat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._compat_table.setFont(QFont("Consolas", 12))
        rl.addWidget(self._compat_table, 1)

        rec_hdr = QLabel("PREPORUKA")
        rec_hdr.setStyleSheet(
            "color:#666666; font-size:11px; font-weight:bold; letter-spacing:1px;"
        )
        rl.addWidget(rec_hdr)

        self._rec_text = QTextEdit()
        self._rec_text.setReadOnly(True)
        self._rec_text.setMaximumHeight(90)
        self._rec_text.setFont(QFont("Consolas", 11))
        self._rec_text.setStyleSheet(
            "QTextEdit { background:#252526; color:#888888; border:1px solid #333333; "
            "border-radius:4px; padding:6px 8px; }"
        )
        rl.addWidget(self._rec_text)

        split.addWidget(right)
        split.setSizes([480, 460])
        lo.addWidget(split, 1)

        # Inicijalni prikaz s default profilom
        self._populate_ecu_table()
        self._update_compat()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_engine(self, eng) -> None:
        """Postavi engine — pozovi nakon ucitavanja novog .bin fajla."""
        self._eng = eng
        if eng and eng.loaded and eng.info:
            sw = eng.info.sw_id or ""
            self._sw_id    = sw
            self._ecu_type = _detect_ecu_type(sw)
            addr           = CAN_TABLE_ADDR.get(self._ecu_type, CAN_TABLE_ADDR["gti300"])
            ecu_desc       = "Spark 900 ACE" if self._ecu_type == "spark" else "GTI/SC 1630"
            self._ecu_lbl.setText(
                f"ECU: {sw}  [{ecu_desc}]  ·  CAN table @ 0x{addr:06X}"
            )
            self._btn_read.setEnabled(True)
            self._profile_ids = ECU_PROFILES.get(self._ecu_type, ECU_PROFILES["gti300"]).copy()
            self._live_ids    = []
            self._source_lbl.setText("(profil — klikni 'Citaj iz binarnog' za live podatke)")
        else:
            self._sw_id    = ""
            self._ecu_type = "gti300"
            self._ecu_lbl.setText("ECU: —  ·  CAN table: —")
            self._btn_read.setEnabled(False)
            self._profile_ids = ECU_PROFILES["gti300"].copy()
            self._live_ids    = []
            self._source_lbl.setText("(profil)")

        self._populate_ecu_table()
        self._update_compat()

    # ── Private ───────────────────────────────────────────────────────────────

    def _read_from_binary(self):
        if not self._eng or not self._eng.loaded:
            return
        addr = CAN_TABLE_ADDR.get(self._ecu_type, CAN_TABLE_ADDR["gti300"])
        try:
            data = self._eng.get_bytes()
            ids: list[int] = []
            for i in range(0, 64, 2):       # max 32 ID-a
                if addr + i + 2 > len(data):
                    break
                val = (data[addr + i] << 8) | data[addr + i + 1]   # BE u16
                if val == 0x0000:
                    break
                if 0x001 <= val <= 0x7FF:   # valjan 11-bit CAN ID
                    ids.append(val)

            if ids:
                self._live_ids = ids
                self._source_lbl.setText(
                    f"(binarni fajl @ 0x{addr:06X} — {len(ids)} ID-ova procitano)"
                )
                self._populate_ecu_table()
                self._update_compat()
            else:
                self._source_lbl.setText(f"(binarni @ 0x{addr:06X} — nema valjanih ID-ova)")
        except Exception as e:
            self._source_lbl.setText(f"(greska pri citanju: {e})")

    def _current_ids(self) -> list[int]:
        return self._live_ids if self._live_ids else self._profile_ids

    def _populate_ecu_table(self):
        ids = self._current_ids()
        self._ecu_table.setRowCount(0)
        seen: set[int] = set()
        for cid in ids:
            if cid in seen:
                continue
            seen.add(cid)
            desc, tip = CAN_ID_INFO.get(cid, ("Nepoznata poruka", "?"))
            color = self._id_color(tip)

            row = self._ecu_table.rowCount()
            self._ecu_table.insertRow(row)
            for j, txt in enumerate([f"0x{cid:04X}", str(cid), desc, tip]):
                item = QTableWidgetItem(txt)
                item.setForeground(QBrush(QColor(color)))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter |
                    (Qt.AlignmentFlag.AlignLeft if j >= 2 else Qt.AlignmentFlag.AlignCenter)
                )
                self._ecu_table.setItem(row, j, item)

    def _update_compat(self):
        sat_name = self._sat_combo.currentText()
        if sat_name not in SAT_CONFIGS:
            return
        sat     = SAT_CONFIGS[sat_name]
        sat_ids = set(sat["ids"])
        ecu_ids = set(self._current_ids())
        all_ids = sorted(sat_ids | ecu_ids)

        self._sat_info_lbl.setText(
            f"MCU: {sat['mcu']}\n{sat['notes']}"
        )

        self._compat_table.setRowCount(0)
        missing: list[int] = []
        extra:   list[int] = []

        for cid in all_ids:
            in_ecu = cid in ecu_ids
            in_sat = cid in sat_ids
            desc = CAN_ID_INFO.get(cid, ("?", "?"))[0]

            if in_ecu and in_sat:
                fg = "#4ec9b0"
                bg = None
            elif in_ecu and not in_sat:
                fg = "#888888"
                bg = None
                extra.append(cid)
            elif not in_ecu and in_sat:
                fg = "#e5c07b"
                bg = "#252010"
                missing.append(cid)
            else:
                continue

            row = self._compat_table.rowCount()
            self._compat_table.insertRow(row)
            for j, txt in enumerate([
                f"0x{cid:04X}", str(cid), desc,
                "✓" if in_ecu else "—",
                "✓" if in_sat else "—",
            ]):
                item = QTableWidgetItem(txt)
                item.setForeground(QBrush(QColor(fg)))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter |
                    (Qt.AlignmentFlag.AlignLeft if j == 2 else Qt.AlignmentFlag.AlignCenter)
                )
                if bg:
                    item.setBackground(QBrush(QColor(bg)))
                self._compat_table.setItem(row, j, item)

        self._build_recommendation(missing, extra)

    def _build_recommendation(self, missing: list[int], extra: list[int]):
        lines: list[str] = []
        if not missing and not extra:
            lines.append("✓ Potpuna kompatibilnost — plug & play!")
        else:
            if not missing:
                lines.append("✓ SAT prima sve poruke koje ECU salje.")
            else:
                lines.append(
                    f"⚠ SAT ocekuje {len(missing)} poruke koje ECU ne salje: "
                    + ", ".join(f"0x{x:04X}" for x in missing)
                )
                lines.append("  Prikazne pozicije za te poruke bit ce prazne/0.")
            if extra:
                lines.append(
                    f"i ECU salje {len(extra)} extra poruke koje SAT ignorira: "
                    + ", ".join(f"0x{x:04X}" for x in extra)
                )
        self._rec_text.setPlainText("\n".join(lines))

    def show_id(self, can_id: int):
        pass  # TODO: scroll to / highlight CAN ID row

    @staticmethod
    def _id_color(tip: str) -> str:
        return {
            "common": "#cccccc",
            "spark":  "#9cdcfe",
            "gti_sc": "#4ec9b0",
        }.get(tip, "#888888")
