# ME17Suite — ECU Tuning Tool

**Profesionalni alat za tuning Bosch ME17.8.5 ECU-a na Rotax ACE 1630 motoru (Sea-Doo 300/260 HP serija)**

---

## O alatu

ME17Suite je desktop aplikacija pisana u Pythonu koja omogućava čitanje, editovanje i pisanje kalibracionih mapa direktno u binarni ECU fajl. Namijenjena je iskusnim tunerima koji rade s Sea-Doo vozilima opremljenim Rotax ACE 1630 motorom (model godine 2014+).

**Podržani ECU:** Bosch ME17.8.5
**MCU:** Infineon TC1762 (TriCore arhitektura, Little Endian)
**Motori:** Rotax ACE 1630 T (260 HP), 1630 HO (300 HP)
**Vozila:** Sea-Doo RXP-X 300, RXT-X 300, GTX 300, Wake Pro 230, i dr.

---

## Mogućnosti

### Mape kalibracije
- **Ignition timing** — 16 tablica 12×12, rezolucija 0.75°/bit, s RPM i opterećenjem osima
- **Injection** — 12×32 tablica s mirror kopijom, u16 LE format
- **Torque limiting** — 16×16 Q8 format s mirror kopijom
- **Lambda/AFR** — 12×18 Q15 LE format s mirror kopijom
- **Rev limiter** — 5 neovisnih lokacija
- **RPM osi** — 3 tablice s 16 točaka svaka

### Checksum engine
- Automatska verifikacija CRC32-HDLC checksuma (BOOT regija 0x0000–0x7EFF)
- Meet-in-the-middle inverz za izračun novog CS bez Bosch privatnog ključa
- Promjena CODE mapa ne zahtijeva promjenu checksuma

### DTC management
- Pregled i deaktivacija fault kodova (P-kodova)
- Podržani: P0523 (uljni tlak), P1550 (tlak punjenja), i dr.

### GUI (PyQt6)
- Pretraživač mapa (search + tree view)
- Heat-map vizualizacija tablica s osima
- Properties panel s 3 taba (info, edit, hex)
- Undo/Redo (neograničen)
- CSV export
- Direktni unos vrijednosti
- Hex + log strip

---

## Struktura projekta

```
me_suite/
├── main.py                 # Pokretanje aplikacije
├── core/
│   ├── engine.py           # Load/save, read/write primitivi
│   ├── map_finder.py       # 30 potvrđenih mapa, skeniranje
│   ├── map_editor.py       # Editovanje s zaštitom i undo/redo
│   ├── checksum.py         # CRC32-HDLC verifikacija i korekcija
│   └── dtc.py              # DTC deaktivacija
├── ui/
│   └── main_window.py      # PyQt6 GUI
└── test/
    └── test_core.py        # Testovi
```

---

## Pokretanje

```bash
cd me_suite
python main.py
```

**Zahtjevi:** Python 3.14+, PyQt6

---

## Tehnički detalji — Memorijska mapa

| Regija | Raspon | Opis |
|--------|--------|------|
| BOOT | 0x0000–0x7EFF | Boot loader, header, CS @ 0x30, RSA potpis |
| Gap | 0x7F00–0xFFFF | DEADBEEF terminator, TC1762 BROM startup |
| CODE | 0x10000–0x5FFFF | Kalibracijske mape (tuning) |
| CAL | 0x60000–0x177FFF | TriCore bytekod — READ-ONLY! |

---

## Napomena

Alat je razvijen za edukativne i istraživačke svrhe. Izmjena ECU softvera može utjecati na jamstvo i sigurnost vozila. Koristiti odgovorno.
