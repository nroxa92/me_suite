# ME17Suite — ECU Tuning Alat

**Profesionalni alat za tuning Bosch ME17.8.5 ECU-a na Rotax ACE 1630 motoru (Sea-Doo 300/260 HP serija)**

---

## O alatu

ME17Suite je desktop aplikacija u Pythonu koja omogućava čitanje, uređivanje i pisanje kalibracionih mapa direktno u binarni ECU fajl. Namijenjena je iskusnim tunerima koji rade sa Sea-Doo vozilima opremljenim Rotax ACE 1630 motorom (model godine 2014+).

**Podržani ECU:** Bosch ME17.8.5
**MCU:** Infineon TC1762 (TriCore arhitektura, Little Endian)
**Motori:** Rotax ACE 1630 T (260 HP), 1630 HO (300 HP)
**Vozila:** Sea-Doo RXP-X 300, RXT-X 300, GTX 300, Wake Pro 230 i dr.

---

## Mogućnosti

### Mape kalibracije
- **Paljenje (Ignition timing)** — 16 tablica 12×12, razlučivost 0.75°/bit, s RPM i opterećenjem kao osima
- **Ubrizgavanje (Injection)** — tablica 12×32 s mirror kopijom, u16 LE format
- **Ograničenje okretnog momenta (Torque limiting)** — 16×16 Q8 format s mirror kopijom
- **Lambda/AFR** — 12×18 Q15 LE format s mirror kopijom
- **Ograničivač broja okretaja (Rev limiter)** — 5 neovisnih lokacija
- **RPM osi** — 3 tablice sa 16 točaka svaka

### Checksum
- Automatska provjera CRC32-HDLC checksuma (BOOT regija 0x0000–0x7EFF)
- Meet-in-the-middle inverz za izračun novog CS bez Bosch privatnog ključa
- Promjena CODE mapa ne zahtijeva promjenu checksuma

### Upravljanje greškama (DTC)
- Pregled i isključivanje kodova grešaka (P-kodova)
- Podržani: P0523 (tlak ulja), P1550 (tlak punjenja) i dr.

### Grafičko sučelje (PyQt6)
- Pretraživač mapa (pretraga + prikaz stabla)
- Heat-map prikaz tablica s osima
- Upravljačka ploča sa 3 kartice (info, uređivanje, hex)
- Poništi/Ponovi (neograničeno)
- CSV izvoz
- Izravni unos vrijednosti
- Hex + log traka

---

## Struktura projekta

```
me_suite/
├── main.py                 # Pokretanje aplikacije
├── core/
│   ├── engine.py           # Učitavanje/spremanje, primitivi za čitanje/pisanje
│   ├── map_finder.py       # 30 potvrđenih mapa, skeniranje
│   ├── map_editor.py       # Uređivanje sa zaštitom i poništi/ponovi
│   ├── checksum.py         # CRC32-HDLC provjera i ispravak
│   └── dtc.py              # Isključivanje DTC grešaka
├── ui/
│   └── main_window.py      # PyQt6 grafičko sučelje
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
| BOOT | 0x0000–0x7EFF | Bootloader, zaglavlje, CS @ 0x30, RSA potpis |
| Gap | 0x7F00–0xFFFF | DEADBEEF završni marker, TC1762 BROM startup |
| CODE | 0x10000–0x5FFFF | Kalibracijske mape (tuning) |
| CAL | 0x60000–0x177FFF | TriCore bajtkod — SAMO ZA ČITANJE! |

---

## Napomena

Alat je razvijen u istraživačke svrhe. Izmjena ECU softvera može utjecati na jamstvo i sigurnost vozila. Koristiti odgovorno.
