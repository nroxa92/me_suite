# ME17Suite — ECU Tuning Alat

**Profesionalni alat za tuning Bosch ME17.8.5 ECU-a na svim Rotax motorima (Sea-Doo / Spark)**

---

## O alatu

ME17Suite je desktop aplikacija u Pythonu za čitanje, uređivanje i pisanje kalibracionih mapa direktno u binarni ECU fajl. Namijenjena je iskusnim tunerima koji rade sa Sea-Doo i Spark vozilima.

**Podržani ECU:** Bosch ME17.8.5
**MCU:** Infineon TC1762 (TriCore arhitektura, Little Endian)
**Veličina binarnog fajla:** 1,540,096 bajta (0x178000)

---

## Podržani motori i SW varijante

| SW ID | Motor / Model | Snaga | God. | Mapa |
|-------|--------------|-------|------|------|
| 10SW066726 | Rotax ACE 1630 SC | 300 HP | 2021 | 56 mapa |
| 10SW054296 | Rotax ACE 1630 SC | 300 HP | 2020 | 56 mapa |
| 10SW040039 | Rotax ACE 1630 SC (NPRo base) | 300 HP | 2019 | 54 mapa |
| 10SW023910 | Rotax ACE 1630 SC | 300 HP | 2018 | 61 mapa |
| 10SW053727 | Rotax ACE 1630 SC | 230 HP | 2020–21 | 53 mape |
| 10SW053729 | Rotax ACE 1630 NA | 130/170 HP | 2020–21 | 62 mape |
| 10SW053774 | Rotax ACE 1630 NA (GTI 90) | 90 HP | 2020–21 | 60 mapa |
| 10SW039116 | Rotax 900 HO ACE (Spark) | 90 HP | 2019–21 | 54 mape |
| 10SW011328 | Rotax 900 HO ACE (Spark) | 90 HP | 2016–18 | 54 mape |
| 10SW025021 | Rotax 4-TEC 1503 SC | 230 HP | 2018 | 59 mapa |
| 10SW025022/25752 | Rotax 4-TEC 1503 NA | 130/155 HP | 2018 | 60 mapa |
| 10SW040008 | Rotax 4-TEC 1503 | 130–230 HP | 2019 | 59 mapa |
| 10SW040962 | Rotax 4-TEC 1503 | 130 HP | 2020 | 59 mapa |

---

## Mogućnosti

### Mape kalibracije (56+ po ECU tipu)
- **Paljenje (Ignition timing)** — 19 tablica 12×12, razlučivost 0.75°/bit (base, knock, aux SC, extended, fallback)
- **Ubrizgavanje (Injection)** — injector linearization curve + GTI 2D fuel mapa (12×16), sve varijante
- **Moment (Torque)** — 16×16 BE Q8 s mirror kopijom; fizička krivulja momenta (30pt, Nm)
- **Lambda/AFR** — 12×18 LE Q15 s mirror kopijom + adapt/trim/bias/eff (KFWIRKBA)
- **SC correction/bypass** — 9×7 correction mapa + 3 kopije bypass opcoda
- **Ograničivač okretaja (Rev limiter)** — period-encoded LE u16 (formula: 40MHz×60/(ticks×58))
- **KFPED (drive-by-wire)** — 10×20 throttle pedal mapa
- **Knock params** — 52×u16 (104B) potpuna knock tablica
- **Thermal enrichment, Accel enrichment, Temp fuel correction, Decel/DFCO, Deadtime** — sve podržano

### Checksum
- Automatska provjera CRC32-HDLC checksuma (BOOT regija 0x0000–0x7EFF)
- Meet-in-the-middle inverzni CRC za izračun novog CS bez Bosch privatnog ključa
- Promjena CODE mapa ne zahtijeva promjenu checksuma

### Upravljanje greškama (DTC)
- **121 DTC kod** — 111 P-kodova (ECM) + 10 U16Ax CAN timeout kodova
- Pregled, uključivanje, isključivanje i potpuno onemogućavanje praćenja grešaka
- Podržano za sve 1630 ACE i GTI 1503 varijante
- DTC off blokiran za Spark 900 (single-storage arhitektura — sigurnosna mjera)

### CAN Bus
- **Diagnostic bus (500 kbps)** — live dekodiranje IDs: 0x0102 (RPM), 0x0110 (temp), 0x0342 (MAP/MAT), 0x0516 (HW ID), 0x04CD (DESS)
- **Cluster bus (250 kbps)** — ECU→SAT poruke (0x0578, 0x0400, 0x0408), SAT heartbeat (0x0186, 0x01CD)
- XOR checksum validacija + rolling counter praćenje
- CSV logging, statistike po CAN ID-u

### EEPROM
- Parse sva 3 HW tipa (064/063/062) — ODO, Hull ID, ECU serijski, dealer info
- HW 064 (ACE 1630 + GTI90), HW 063 (Spark 90), HW 062 (4-TEC 1503)
- Sigurno editiranje polja: hull_id, dealer_name, datumi programiranja

### Grafičko sučelje (PyQt6)
- Pretraživač mapa s puno-tekstualnom pretragom i stablom kategorija
- **Heat-map vizualizacija** (JET paleta) s RPM/Load osima i live tooltipom
- **3D surface plot** (matplotlib) za svaku mapu
- **Map Editor** s dirty cell označavanjem i bulk operacijama
- **CAN Live dashboard** — RPM, coolant, hours, DTC, riding mode, gauges
- **EEPROM preglednik/editor**
- **Diff Viewer** — usporedba dva firmware-a, heat delta prikaz
- **Kalkulator** — AFR↔lambda, boost, timing, injection konverzije
- **DTC panel** — pregled i upravljanje kodovima grešaka
- Undo/Redo stack, CSV izvoz, Hex viewer, Log strip
- Dark tema (#111113 pozadina, #4FC3F7 akcent)

---

## Struktura projekta

```
me_suite/
├── main.py                    # Pokretanje aplikacije
├── core/
│   ├── engine.py              # Load/save, read/write primitivi (u8/u16 BE/LE/i16)
│   ├── map_finder.py          # Signature skeneri — 56 mapa (300hp), 52 (Spark), 60 (GTI90)
│   ├── map_editor.py          # Safe write s auto-mirror sync, backup/restore
│   ├── checksum.py            # CRC32-HDLC verifikacija + MITM inverzni solver
│   ├── dtc.py                 # DTC_REGISTRY (121 kod), DtcEngine, dtc_off/dtc_on
│   ├── can_decoder.py         # CanDecoder — sve CAN ID formule, XOR checksum
│   ├── eeprom.py              # EepromParser/Editor — HW 062/063/064
│   ├── safety_validator.py    # Validacija limita (OK/WARNING/ERROR)
│   └── map_differ.py          # Usporedba firmware-a, CellDiff statistika
├── ui/
│   ├── main_window.py         # Glavni prozor, svi tabovi, dark tema
│   ├── map_visualizer.py      # MapHeatWidget (JET), MapDeltaWidget, MapMiniPreview
│   ├── map_editor_widget.py   # MapEditorWidget, UndoStack, paste TSV/Excel
│   ├── can_live_widget.py     # CanLivePanel, CanWorker(QThread), dashboard
│   ├── can_network_widget.py  # CAN bus topologija (grafički prikaz)
│   ├── can_logger_widget.py   # CSV logging s gauge prikazom
│   ├── diff_viewer.py         # MapDiffWidget — firmware usporedba
│   ├── eeprom_widget.py       # EEPROM preglednik/editor
│   └── calculator_widget.py   # Tuning kalkulatori (AFR, boost, timing, injection)
├── tools/
│   ├── can_sniffer.py         # IXXAT VCI4 USB-to-CAN, pasivni sniff, CSV log
│   └── did_map.py             # UDS/KWP live data (34 DID-a)
└── test/
    └── test_core.py           # Unit testovi
```

---

## Pokretanje

```bash
cd me_suite
python main.py
```

**Zahtjevi:** Python 3.14+, PyQt6, python-can (za CAN funkcije)

---

## Tehnički detalji — Memorijska mapa

| Regija | Raspon | Opis |
|--------|--------|------|
| BOOT | 0x0000–0x7EFF | Bootloader, zaglavlje, CS @ 0x30, RSA potpis |
| Gap | 0x7F00–0xFFFF | DEADBEEF marker, TC1762 BROM startup |
| CODE | 0x010000–0x05FFFF | Kalibracijske mape — tuning prostor |
| CAL | 0x060000–0x15FFFF | TriCore bajtkod — **SAMO ZA ČITANJE!** |

**Checksum:** CRC32-HDLC (poly=0xEDB88320), BOOT regija, CS @ 0x30 uključen, residua=0x6E23044F
**CODE promjene ne zahtijevaju CS promjenu.**

---

## Napomena

Alat je razvijen u istraživačke svrhe. Izmjena ECU softvera može utjecati na jamstvo i sigurnost vozila. Koristiti odgovorno.
