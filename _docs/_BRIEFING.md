# _BRIEFING.md — Kompletan Kontekst Projekta ME17Suite
# Za: Claude Code agente koji rade na ovom projektu
# Datum kreiranja: Mart 2026
# Autor: Inžinjer za ECU tuning (profesionalno iskustvo sa Bosch ME17.x)

---

## 1. MISIJA PROJEKTA

Gradimo **ME17Suite** — profesionalni desktop alat za ECU tuning Bosch ME17.8.5
kontrolne jedinice na Rotax ACE 1630 motoru (Sea-Doo 300 HP jetski).

**Zašto ne koristiti WinOLS ili postojeće alate?**
- WinOLS je skup i kompliciran za svakodnevnu upotrebu
- Postojeći alati nemaju podršku za ovaj specifični ECU/motor
- Trebamo vlastiti alat koji razumije naš specifičan binary format
- Cilj: jednostavan UI koji skriva kompleksnost binarnog formata

**Što alat mora raditi:**
1. Učitati .bin fajl (OEM dump ili postojeći tune)
2. Prikazati sve poznate mape u čitljivom obliku (tablice s bojama)
3. Dozvoliti editovanje mapa s validacijom (ne može unijeti nenormalnu vrijednost)
4. Usporediti dva fajla side-by-side (ORI vs tune) s diff highlightom
5. Sačuvati modificirani .bin s ispravnim checksumom
6. Flashati na ECU (budući cilj, nije implementirano)

---

## 2. HARDWARE I ECU DETALJI

### Motor
- **Rotax ACE 1630** — 3-cilindar, inline, turbocharged
- ~300 HP u Sport modu (+ 30 HP boost u Sport+ modu)
- Vozilo: Sea-Doo RXP-X 300 / RXT-X 300

### ECU
- **Bosch ME17.8.5** — automotive-grade, Bosch AUTOSAR
- Flashanje: K-Line / CAN (KTAG klon, Xhorse Multiprog, ili DIUS4 programmer)
- Workflow: dump → edituj → flash nazad

### Mikroprocesor unutar ECU-a
- **Infineon TC1762** — TriCore arhitektura (RISC + DSP + MCU)
- **Little Endian** (važno za čitanje u16/u32 vrijednosti!)
- Flash bazna adresa: **0x80000000** (sve pointer-e treba offsetirat za ovo)
- 2MB internal flash, podijeljeno na boot/code/cal sektore

---

## 3. BINARY FORMAT — ANATOMIJA FAJLA

### Veličina: 1,540,096 bajtova (0x178000)

```
Offset       Veličina  Naziv   Sadržaj
─────────────────────────────────────────────────────────────
0x000000   64KB (0x10000)  BOOT   Bootloader, SW identifikatori,
                                   checksum vrijednosti, sigurnosni
                                   mehanizmi
0x010000  320KB (0x50000)  CODE   TriCore firmware + sve MAPE!
                                   Ovdje su sve podatkovne tablice
                                   koje nas zanimaju za tuning.
0x060000    1MB (0x100000) CAL    *** PAŽNJA: IZGLEDA KAO KALIBRACIJA
                                   ALI JE TRICORE BYTEKOD! ***
                                   Bosch AUTOSAR/ASCET kompajlirani
                                   kod s ugrađenim parametrima.
                                   Nemoj pisati ovdje bez razumijevanja!
0x160000   96KB (0x18000)  EMPTY  0x00 fill, nekorišteno
```

### Identifikatori (uvijek provjeri pri loadu)
```python
MCU_STRING = b"VME17 SB_V05.01.02"  # @ 0x01FE50
SW_ID_OFFSET = 0x001A               # 10 ASCII bajtova
```

### Naši testni fajlovi
| Fajl | SW ID | Opis |
|------|-------|------|
| ori_300.bin | 10SW066726 | OEM dump — polazna točka |
| npro_stg2_300.bin | 10SW040039 | NPRo Stage 2 tune — referentni tune |

**VAŽNO:** ORI i STG2 imaju **različite firmware baze** (različiti SW ID)!
NPRo je promijenio i CODE i kalibraciju, ne samo mape. Ovo znači da direktno
kopiranje između fajlova s različitim SW ID-jem može biti opasno.

---

## 4. MAPE — ŠTO SMO OTKRILI

### Metodologija otkrivanja
1. Binarna usporedba ORI vs STG2 (diff analysis)
2. Heuristički scan za poznate obrasce (RPM ose, Q8 vrijednosti...)
3. Pointer analiza — pronašli 754 LE pointera u CODE koji pokazuju na CAL
   (ali CAL je bytekod, ne mape — slepa ulica)
4. Sve prave mape su u **CODE regiji** (0x010000–0x05FFFF)

### Formati podataka koji se koriste
| Format | Opis | Primjer dekodera |
|--------|------|-----------------|
| u8 | 1 bajt, unsigned | raw = data[addr] |
| u16 BE | 2 bajta, Big Endian | (d[a]<<8)|d[a+1] |
| u16 LE | 2 bajta, Little Endian | d[a]|(d[a+1]<<8) |
| u16 Q8 | 2 bajta BE, samo MSB nosi data | MSB/128 = % |
| u16 Q15 LE | 2 bajta LE, fiksni zarez | val/32768 = λ-ratio |

### Ignition mape — najvažniji nalaz
16 mapa paljenja, svaka 12×12 ćelija, u8 format:
- Scale: **0.75°/bit** → raw 34 = 25.5° BTDC
- ORI opseg: 24°–33.8° BTDC
- STG2 opseg: 25.5°–36.8° BTDC (NPRo dao +3° do +6° advance)
- Raspored: blokovi svako 144 bajtova od 0x02B730
- Pretpostavljamo: 3 cilindra × ~5 uvjeta (normal/hot/knock/enrich/decel/global)
- **Osi mape (RPM × Load) još nisu identificirane!** — TODO

### Injection mapa — 3-4× veće vrijednosti u STG2
- Format: u16 LE, 12×32 ćelija
- ORI: max ~49151, STG2: max 65535 (saturirano!)
- NPRo je dramatično povećao injection duration — agresivan tune
- Fizikalna jedinica: vjerojatno μs ili 0.1μs — nepoznato bez A2L

### Mirror logika
Torque i Lambda mape imaju identične kopije (mirrore):
- Torque mirror offset: **+0x518** od glavne mape
- Lambda mirror offset: **+0x518** od glavne mape
- Pri editovanju: uvijek pisati u oba!

---

## 5. TRENUTNO STANJE KODA

### core/engine.py ✅ STABILAN
- Učitava/čuva .bin fajl s validacijom (veličina, MCU string, SW ID)
- Read/write primitivi: u8, u16 BE/LE, u32, arrays
- Region protection — ne može se pisati van CODE (za sada)
- Dirty flag, diff, diff_summary metode

### core/map_finder.py ✅ STABILAN
- `MapDef` dataclass — descriptor mape (adresa, dim, dtype, scale, unit...)
- `FoundMap` dataclass — rezultat skeniranja (raw vrijednosti, display, diff)
- `find_maps(ori, stg)` — skenira i vraća svih 30 mapa
- `find_changed_regions()` — za diff prikaz

### core/map_editor.py ✅ STABILAN
- `write_cell()` — validirana promjena jedne ćelije
- `write_map()` — batch write s range provjerom
- `write_rev_limit_row()` — enforcement: soft < mid < hard

### core/checksum.py ⚠️ NEDOVRŠEN
- CRC32 algoritam implementiran (Bosch poly 0x04C11DB7)
- **Lokacije checksum-a u BOOT regiji NEPOZNATE**
- `update_all()` vraća NOT_IMPLEMENTED
- ECU trenutno prihvata fajlove bez ispravnog checksum-a (testirati!)

### ui/main_window.py ✅ FUNKCIONALAN
- Adaptive dual-file UI (fajl 1 → scan → opcijalno fajl 2 → diff)
- `MapTreeWidget` — sidebar tree, kategorije: ignition/injection/torque/lambda...
- `MapTableWidget` — heat-map boje, diff ćelije žuto highlighted
- `DiffWidget` — skriven dok se ne učita fajl 2
- `ScanWorker(QThread)` — background scan, progress bar
- Side-by-side usporedba kad su oba fajla učitana

---

## 6. AGENTI — PLAN RADA

Ovaj projekt je organiziran da Claude Code agenti rade specijalizirane zadatke.
Svaki agent dobiva ovaj briefing + specifičan task.

### Agent: ANALYZER
**Zadatak:** Analiza novih .bin fajlova iz `_materijal/`
```
Trebaš:
1. Pročitati sve .bin fajlove u _materijal/
2. Identifikirati SW ID i MCU string
3. Usporediti s ori_300.bin — naći razlike
4. Dokumentirati nova otkrića u _materijal/FINDINGS.md
5. Ažurirati map_finder.py ako pronađeš nove mape
```

### Agent: UI_DEVELOPER
**Zadatak:** Poboljšanje PyQt6 GUI-a
```
Trebaš:
1. Implementirati mapu paljenja s osi prikazom (RPM × Load)
2. Dodati editovanje ćelija dvoklikom (QLineEdit u tablici)
3. Implementirati undo/redo (Ctrl+Z / Ctrl+Y)
4. Dodati export u CSV/Excel
5. Poboljšati heat-map boje (crvena=visoko, plava=nisko)
Pokretaj: python main.py za testiranje
```

### Agent: CHECKSUM_ENGINEER
**Zadatak:** Reverse engineering checksum mehanizma
```
Trebaš:
1. Analizirati BOOT regiju (0x000000-0x00FFFF) oba fajla
2. Pronaći gdje su checksum vrijednosti pohranjene
3. Identificirati koji opseg podataka se checksum-a
4. Implementirati ispravni update_all() u checksum.py
5. Testirati: flashaj modificirani fajl, provjeri prihvata li ECU
Hint: Bosch koristi CRC32 poly 0x04C11DB7, ali može biti i CRC16
```

### Agent: MAP_RESEARCHER
**Zadatak:** Istraživanje neidentificiranih mapa
```
Trebaš:
1. Pronaći osi za ignition mapu (12 RPM tačaka × 12 Load tačaka)
   - RPM osa vjerojatno blizu 0x02B730 (ispred mapa)
   - Load osa nepoznata (MAP senzor % ili mg/stroke?)
2. Identificirati fizikalnu jedinicu injection mape (μs? mg?)
3. Pronaći boost/wastegate mapu (boost control)
4. Dokumentirati u _materijal/MAP_RESEARCH.md
```

---

## 7. CODING STANDARDI

```python
# UVIJEK ovako (apsolutni importi):
from core.engine import ME17Engine
from core.map_finder import find_maps, MapDef

# NIKAD ovako (relativni importi — pucaju!):
from ..core.engine import ME17Engine

# Test pokretanje — uvijek iz me_suite root:
# cd C:\Users\SeaDoo\Desktop\me_suite
# python test/test_core.py

# Type hints gdje je moguće
def find_maps(ori: bytes, stg: Optional[bytes] = None) -> list[FoundMap]:

# Komentari na engleskom u kodu, komunikacija sa mnom na BCS
```

---

## 8. SIGURNOSNA PRAVILA

1. **Nikad ne piši u CAL regiju** (0x060000+) bez potpunog razumijevanja
2. **Uvijek provjeri SW ID** pri loadu — ne miješati fajlove s različitim SW ID-jem
3. **Backup prije flash-a** — uvijek sačuvaj original
4. **Testirati na bench ECU-u** prvi put, ne na vozilu
5. **Checksum mora biti ispravan** prije flasha (implementirati!)
6. **Rev limiter minimum:** ne postavljati ispod 6000 rpm (motorski razlozi)
7. **Ignition advance limit:** ne ići iznad 42° BTDC (detonacija!)

---

## 9. FOLDER _materijal/

```
_materijal/
├── _BRIEFING.md              ← ovaj fajl
├── FINDINGS.md               ← (kreirati) nova otkrića iz novih dumpova
├── MAP_RESEARCH.md           ← (kreirati) istraživanje neidentificiranih mapa
├── ori_300.bin               ← OEM dump, nikad ne modificirati!
├── npro_stg2_300.bin         ← NPRo Stage 2 referenca
└── [novi dumpovi...]         ← dodavat ćemo tokom rada
```

**Za svaki novi dump koji dodam, Analyzer agent treba:**
- Provjeriti SW ID i MCU string
- Napraviti diff s ori_300.bin
- Identificirati koje su mape promijenjene i kako
- Dokumentirati u FINDINGS.md

---

## 10. KOMUNIKACIJA

- Inžinjer govori BCS (bosanski/srpski/hrvatski)
- Odgovori mogu biti na BCS ili engleskom
- Tehnički termini ostaju na engleskom (map, offset, LE, BE...)
- Uvijek objasni ŠTO radiš i ZAŠTO — to je obrazovni projekt

---

*Kraj briefing-a. Sretan rad!*
*Ako nešto nije jasno, pitaj inžinjera — on ima profesionalno iskustvo s Bosch ECU-ima.*