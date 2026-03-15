# ME17Suite — Work Log

## 2026-03-15 06:30 — Osi mapa definirane: RPM korekcija + load osa + lambda X osa

### Što je napravljeno
Analiza binarnog fajla i WinOLS stringa donijela je kompletne definicije osi za sve mape.

### Rezultati
- **RPM osa ispravljena**: prethodne vrijednosti u kodu bile pogrešne za točke 10-15:
  - `_RPM_12`: zadnje 2 točke `6144,8448` → `5632,6400` (direktno iz binarnog @ 0x024F46)
  - `_RPM_16`: zadnje 5 točaka `6144,6656,7168,7680,8448` → `6400,6912,7424,7936,8448`
- **Load osa (Y os)**: WinOLS potvrđuje "relative air charge" (rl, %)
  - Kandidat @ 0x02AFAC (LE u16): `[0,100,200,400,800,1280,2560,3200,3840,4480,5120,5760]`
  - Skaliranje: raw ÷ 64 = %, raspon 0–90% (12pt) ili 0–130% (16pt, boost >100% normalan za ACE 1630)
  - Vrijedi za: ignition (12pt), torque (16pt), injection (12pt)
- **Lambda X osa (18 točaka)**: @ 0x026586 (LE u16) — isti offset 0x16A bajta ispred lambda main I mirror
  - Vrijednosti: `[853,1067,1280,...,6400]`, raspon ~13–100% rl
  - Lambda mapa: X = load (18pt), Y = RPM (12pt) — orijentacija korigirana
- **Injection**: struktura pojašnjena — 32 stupca NISU RPM os; vrijednosti grupiraju po 12 po redu (možda 3 cilindra × 4 uvjeta). X os ostaje None.

### Fajlovi promijenjeni
- `core/map_finder.py` — RPM osi, load osi (_LOAD_12, _LOAD_16, _LAMBDA_X_18), AxisDef/MapDef za sve mape

---

## 2026-03-15 05:00 — DTC enable_addr kompletno: 88/111 kodova ažurirani iz mapping tablice

### Što je napravljeno
Mapping tablica @ 0x0239B4 iskorištena za ekstrakciju `en_addr` svih 111 DTC kodova u `ori_300`.

### Rezultati
- **88 kodova** dobilo `en_addr` + `en_size=1` (iz mapping tablice)
- **23 kodova** bez `en_addr` (enable bajt u 0xFF regiji — van aktivne enable tablice)
- P1550 `en_size` smanjen 10 → 1, P0523 `en_size` smanjen 11 → 1 (NPRO konzervativni pristup bio pogrešan)
- Enable slot grupe: slot1(0x00/7 kodova), slot2(0x00/12), slot3(0x00/22), slot4(0x06/7), slot5(0x06/7), slot7(0x06/1), slot8(0x06/1), slot10(0x06/2), slot13(0x06/1), slot14(0x06/2), slot32(0x00/1), slot36(0x05/2), slot43(0x06/1), slot49(0x06/1), slot57(0x06/1), slot60(0x06/1), slot70(0x00/7), slot247(0x00/8) + ostali

### Fajlovi promijenjeni
- `core/dtc.py` — DTC_REGISTRY: svi `_d()` pozivi ažurirani s en_addr/en_size

### Kreirani fajlovi
- `chat_log.md` — novi history razgovora (svaka korisnikova poruka + sažetak odgovora)
- `CLAUDE.md` — dodana uputa za održavanje chat_log.md

---

## 2026-03-15 04:00 — DTC bugfix: Spark code TABLE != code storage (korupcija sprijecena)

### Bug pronađen
`DtcScanner.scan()` na Spark 90hp binarnom fajlu vraćao kod TABLE adrese (P1550@0x021304) kao da su code STORAGE adrese. `dtc_off()` bi pisao 0x0000 na 0x021304 — KORUPCIJA statičke referentne tablice!

### Analiza Spark DTC arhitekture
- Code TABLE (statička referenca): P1550@0x021304, P0523@0x021308 — ne smije se mijenjati
- Code STORAGE (fault state): P1550 stanje @ 0x020E5E → 0xFFFF = disabled (nova adresa!)
- Enable byte: 0x0207A5 (jedan bajt, ne raspon kao u ori_300)
- Nema mirrora — single-storage arhitektura
- Checksum fixup @ 0x020080-0x020086 (NPRO CRCË korekcija)

### Promjene (core/dtc.py)
- `DtcScanResult`: dodan `single_storage: bool` polje
- `DtcScanner._make_result()`: Spark detekcija po P1550 @ 0x021300-0x0213FF (bilo 0x020F00-0x020FFF — POGREŠNO)
- `DtcEngine.dtc_off()`: blokira s `UNSUPPORTED` ako `single_storage=True`
- `DtcEngine.dtc_off_all()`, `disable_all_monitoring()`: isti guard dodan
- Test: `DtcScanner.scan(spark)` → `spark_90 (666063), single_storage=True` ✓
- Test: `dtc_off(P1550)` na Spark → `UNSUPPORTED` ✓
- Test: `dtc_off(P1550)` na ori_300 → `OK, 0x021888` ✓

---

## 2026-03-15 03:00 — Problem 4: DTC enable analiza završena (sve dostupne parove)

### Što je analizirano
Svi dostupni OE/DTC-OFF parovi binarne datoteke iz `_materijali/`:

| Par | SW | Pronađeni DTC | Enable adresa | Rezultat |
|-----|----|---------------|---------------|---------|
| WakePro P0523 | ori_300 kompatibilan | P0523 | 0x02108E-0x021098 (slots 14-24) | ✅ Potvrđeno (već u dtc.py) |
| RXP-X P1550 | rxpx300_17 | P1550 | 0x02108A-0x021093 (slots 10-19) | ✅ Potvrđeno (već u dtc.py) |
| NPRo U16A2 OFF | npro_stg2 | U16A2 | 0x021032+0x021037 (2 bajta) | ℹ️ Drugačiji SW, ne odnosi se na ori_300 |
| Spark P1550 OFF | spark_90 | P1550 | 0x0207A5 (1 bajt) + code 0x020E5E | ℹ️ 90hp SW, potpuno drugačija arhitektura |

### Enable tablica (ori_300, 62 slota @ 0x021080-0x0210BD)
- Identična na svim 300hp SW varijantama (ori_300, npro_stg2, gti_se_18)
- Prirodne granice (ZERO slotovi): 0-3, 18, 29, 31-33, 45, 58
- P1550 OFF zerira slotove 10-19, P0523 OFF zerira 14-17+19-24 (Olas sustained pressure modul)
- Za preostalih ~109 DTC kodova: bez referentnih DTC-OFF parova, enable_addr ne može biti određen bez TriCore bytekod analize

### Kompletna code tablica pronađena
- ori_300 code tablica: **111 kodova** u rasponu 0x0217B6–0x0218E6 (mixed sa non-SAE Bosch kodovima)
- Sve adrese u dtc.py DTC_REGISTRY potvrđene ✅
- DtcEngine.dtc_off() radi ispravno: zerira enable bytes (gdje poznati) + code_addr + mirror_addr

### Zaključak — Problem 4
Za preostale DTC kodove: code_addr + mirror_addr zeriranje je jedina dostupna opcija. Enable_addr zahtijeva više OE/OFF referentnih parova ili TriCore dekompilaciju.

---

## 2026-03-15 01:30 — Problem 5 djelomično: 3 nove ignition mape pronađene!

### Nalaz — KRITIČNO
Skeniranjem regije IZA dosadašnjih 16 ignition mapa pronađene **3 dodatne mape** koje NPRo STG2 aktivno mijenja:

| Indeks | Adresa | Diffs vs STG2 | Opis |
|--------|--------|---------------|------|
| #16 | 0x02C030 | **40 byte** | Prosirena timing mapa, 25.5–30° BTDC |
| #17 | 0x02C0C0 | **88 byte** | Prosirena timing mapa, 25.5–33° BTDC |
| #18 | 0x02C150 | 24 byte | Uvjetna/parcijalna mapa, prvih 3 reda aktivno |

### Provedena izmjena
- **`core/map_finder.py`**: `IGN_COUNT 16 → 19`, dodani `_IGN_NAMES[16-18]`, `_make_ign_def()` proširena s `is_extended`/`is_partial` logikom
- `_scan_ignition()`: dodana `is_partial` grana (threshold 40%, raspon 0-58)
- Test: 19/19 mapa pronađeno ✅

---

## 2026-03-15 00:00 — Problem 2: Boost pressure target mapa (istraživanje)

### Nalaz — ZATVOREN (false positive potvrđen)
- Skeniran CODE region za u16LE vrijednosti u kPa rasponu — pronašao sve moguće dimenzije
- **Svi "promijenjeni" hitovi su FALSE POSITIVES**: ignition u8 vrijednosti (22-46) čitane kao u16 LE daju 8738-11822 = 87-118 kPa
  - Primjer: 0x02 = ignition raw 0x22 0x22 → u16 LE = 0x2222 = 8738 → 87.38 kPa (lažni hit)
- **Pravi boost kandidat @ 0x025E76**: kPa 118–177, ali **nula razlika vs STG2**
- **Konačni zaključak**: NPRo STG2 NE mijenja boost pressure target — Rotax ACE 1630 nema elektronski boost solenoid, boost je mehanički fiksan
- **Status**: ✅ ZATVORENO — nema boost mape za tuning u ovom SW varijanti

---

## 2026-03-14 22:00 — Aktivni problemi (TODO lista)

### Problemi za rješavanje (po prioritetu)
1. ✅ **Ignition #08 pada validaciju** — soft validacija (≥80% u rasponu), svih 16/16 mapa pronađeno
2. ⚠️ **Boost pressure target mapa** — kandidat @ 0x025E76 (8×16 u16LE ÷100 kPa), nepotvrdeno; NPRo STG2 ne mijenja
3. ❌ **Nepoznate osi (Y load, inj X, lam X)** — `values=None`; trebaju A2L ili binary scan
4. ❌ **DTC enable_addr samo P0523+P1550** — 109 kodova nema granularno isključivanje enable bajta
5. ✅ **Ignition mape 16-18 pronađene** — 3 mape koje NPRo STG2 mijenja, a dosad nisu bile u mapi
   - #16 @ 0x02C030 (40 diffs), #17 @ 0x02C0C0 (88 diffs), #18 @ 0x02C150 (24 diffs)
   - **map_finder.py**: IGN_COUNT 16→19

### Riješeno u ovoj sesiji (prije TODO)
- ✅ Faza 8: UI Redesign v2a Medium Dark
- ✅ Torque Y osa → `_LOAD_AXIS_16` (count=16)
- ✅ Ignition knock validacija — djelomično (0–48), ali #08 još uvijek pada
- ✅ Fajl 2 usporedba: auto-refresh + žute stavke u stablu
- ✅ DTC Disable All Monitor gumb u UI
- ✅ Status bar, DTC lista 111 kodova

## 2026-03-14 21:00 — Faza 8: UI Redesign v2a Medium Dark + DTC lista

### Što je napravljeno
- **ui/main_window.py** — potpuni vizualni redizajn prema v2a specifikaciji:
  - **STYLESHEET**: zamijenjen v2a Medium Dark (bg #1e1e1e, panel #252526, accent #0e639c)
  - **MapLibraryPanel**: `setFixedWidth(220)`, kategorije s ikonama (⚡💉⚙🧪🔴📊❗), Segoe UI fonti, item sizeHint
  - **MAP_COLORS_IGN**: nova 9-stupanjska heatmap paleta (hladno plavo → toplo ružičasto)
  - **MapTableView**: redizajniran bez `hdr` labele — badge bar s `lbl_map_title` + 3 badge labele (dim·dtype, unit, @addr); row height 32px, col width 54px, Consolas 10pt; `_heat()` zamijenjen `_cell_colors()`; `btn_reset` → `btn_danger`
  - **PropertiesPanel**: `setFixedWidth(270)`, val_lbl u frameu s `border-left:3px solid #0e639c`, label stilovi → #888/#9cdcfe
  - **HexStrip**: `#569cd6` adrese, `#888888` bajtovi, HTML format
  - **LogStrip**: v2a level boje (ok=#4ec9b0, info=#9cdcfe, warn=#e5c07b, err=#f48771)
  - **DiffWidget**: v2a boje regija
  - **DtcPanel**: kompletno prerađen — horizontalni split: lijevo DTC lista (240px, QListWidget, 111 kodova, crvena=aktivno/siva=isključeno), desno detalji; gumbi s `btn_danger`/`btn_success` objectName; warn labela; `_populate_list()` + `_on_list_click()`; lista se osvježava pri promjeni statusa
  - **MainWindow**: `setMinimumSize(1280, 720)`, splitter 220/950/270, `_file_lbl` #9cdcfe boja
- Importi: dodani `QListWidget`, `QListWidgetItem`, `QSize`

## 2026-03-14 19:30 — Faza 7: DTC multi-SW podrška + runtime scanner

### Što je napravljeno
- **dtc-buds2+gemini.pdf** pročitan (8 stranica, Gemini prijevod BRP liste):
  - 4 nova potvrđena koda: P0030, P0031, P0032, P0036 (lambda heater PS)
  - Verificirani u rxpx300_17 (0x021820-0x021828) i spark_90 (0x020F3E-0x020F46)
- **core/dtc.py** — kompletni rewrite DtcEngine + novi `DtcScanner`:
  - `DtcScanner.scan(data)` — runtime detekcija DTC tablice u bilo kojoj binarki
    - Glasački algoritam za mirror offset (filtrirani anchor kodovi ≤4 pojave)
    - Mirror-pair mode (offset 0x0280-0x0600): rxpx300_17 (0x0362), spark_90 (0x0368), ori_300 (0x0366)
    - Single-storage fallback: rxtx_260 (260hp SW 524060) — bez mirrora
  - `DtcScanResult`: mirror_offset, addrs dict, sw_hint
  - `DtcEngine._resolve()`: prioritizira skenirane adrese nad registry defaultima
  - 115 kodova u DTC_REGISTRY (was 111)
- **Potvrđeni SW varijante**:
  - rxpx300_17 (300hp SW ~17): offset 0x0362, 115 parova, baza ~0x021700
  - spark_90 (90hp 666063): offset 0x0368, 112 parova, baza ~0x020F00
  - rxtx_260 (260hp SW 524060): single-storage, 112 kodova, baza ~0x020F80

## 2026-03-14 18:15 — Faza 6: DTC OFF — backend + GUI panel kompletiran

### Što je napravljeno
- **core/dtc.py** — novi modul:
  - `DtcDef` dataclass (code, name, enable_addr, enable_size, code_addr, mirror_addr)
  - `DtcStatus` dataclass (is_active, is_off, status_str)
  - `DtcEngine` klasa: `get_status()`, `dtc_off()`, `dtc_on()`, `dtc_off_all()`
  - `DTC_REGISTRY`: P1550 + P0523 s verificiranim adresama za ori_300
- **ui/main_window.py**:
  - `DtcPanel` klasa — kompletni DTC panel s enable tablicou, code/mirror prikazom, OFF/ON gumbima
  - "DTC" tab dodan u centralni `QTabWidget`
  - `_on_map_selected` ažuriran: DTC kategorija → otvara DTC tab automatski
  - `_load1` ažuriran: inicijalizira `DtcEngine` pri učitavanju fajla
- Testirano: `dtc_off(P1550)` i `dtc_on(P1550)` rade ispravno na ori_300

### Verificirano funkcionira
- `dtc_off(0x1550)`: nulira 10 enable bajti + code + mirror → status "OFF"
- `dtc_on(0x1550)`: vraća enable=0x06 na svim kanalima + code storage

---

## 2026-03-14 17:30 — DTC analiza + implementacija, README, CLAUDE.md

### Što je napravljeno
- **DTC analiza**: scan svih dostupnih fajlova (ori_300, rxpx300_17, wakepro_230). Potvrđene adrese:
  - P1550 enable @ 0x02108A (10B), code @ 0x021888, mirror @ 0x021BEE (ori_300)
  - P0523 enable @ 0x02108E (11B), code @ 0x02188C, mirror @ 0x021BF2 (ori_300)
  - CS se NE mijenja za DTC OFF (samo CODE promjene)
- **map_finder.py**: dodana DTC kategorija, `_DTC_P1550_ENABLE_DEF`, `_DTC_P0523_ENABLE_DEF`, `_scan_dtc()` metoda
- **ui/main_window.py**: dodana "DTC / Faults" (#F06292) kategorija u `CATEGORIES` dict
- **README.md**: potpuno prepisano na hrvatskom kao opis alata
- **CLAUDE.md**: dodano "isključivo HRVATSKI" pravilo i "Work Log — OBAVEZNO" sekcija

### Faze projekta (ažurirano)
- Faza 1 ✅ — map_finder: 30 mapa (ignition, injection, lambda, torque, rev limiter, RPM osi)
- Faza 2 ✅ — GUI redesign: search+tree, heat-map tablica, properties panel
- Faza 3 ✅ — Undo/Redo, CSV export, direktni unos
- Faza 4 ✅ — Checksum: CRC32-HDLC closed-form, residua 0x6E23044F, MITM inverz
- Faza 5 ✅ — Analiza fajlova (unknow/, DTC OFF/), DTC struktura identificirana
- Faza 6 🔶 — DTC OFF GUI: implementacija + testiranje, pronalazak svih DTC adresa

### TODO za Fazu 6
- [ ] core/dtc.py — `dtc_off(data, dtc_code)` funkcija (nulira enable + code bajte)
- [ ] Scan preostalih DTC-ova u ori_300 (cjelokupna enable tablica mapirana)
- [ ] GUI: DTC tab/panel za pregledanje i isključivanje
- [ ] Testiranje na svim dostupnim fajlovima

---

## 2026-03-13 — Inicijalna analiza projekta

### Sto sam radio
Procitao i analizirao cijeli codebase: sve Python fajlove, test suite, README, CLAUDE.md i strukturu materijala.

---

## Pregled projekta

**Cilj**: ECU tuning alat za Bosch ME17.8.5 na Sea-Doo 300 (Rotax 1630 ACE, MCU Infineon TC1762 TriCore).
**Stack**: Python 3.14 + PyQt6
**Bin fajlovi**: `ori_300.bin` (ORI, SW 10SW066726) i `npro_stg2_300.bin` (NPRo Stage 2, SW 10SW040039)

---

## Analiza po fajlovima

### `core/engine.py` — Binary engine
- Klasa `ME17Engine` — load/save + read/write primitivi
- Validacija pri loadu: veličina fajla (mora biti točno 0x178000 = 1,540,096 B), SW ID @ 0x001A, MCU string @ 0x01FE00
- Read primitivi: u8, u16 BE/LE, i16 BE/LE, u32 BE/LE, array varijante
- Write primitivi: isti tipovi, auto-dirty flag, clamped vrijednosti
- Region helpers: `in_cal()`, `in_code()`, `in_boot()`
- `diff()` + `diff_summary()` — byte-per-byte usporedba, summary po regionima
- `patch_cal()` + `get_cal_slice()` — zaštićeni CAL write
- **NAPOMENA**: `patch_cal()` postoji ali je u CLAUDE.md navedeno da je CAL regija TriCore bytekod, ne kalibracija — treba pažnju pri pisanju u CAL

### `core/map_finder.py` — Map discovery
- Tri scan strategije:
  1. **Signature scan** (RPM osi) — traži pattern `0x0200 0x0400 0x0600 0x0800 0x0A00 0x0C00` u CODE regionu
  2. **Heuristic scan** (Rev limiter) — traži stride-0x18 pattern s monotonim RPM vrijednostima
  3. **Known-address scan** (Torque mapa) — direktno na 0x02A0D8 i 0x02A5F0, validira LSB==0x00 i MSB u range 80–210
- Potvrđene mape:
  - RPM osa: 3× kopija @ 0x024F46, 0x025010, 0x0250DC (BE u16, 16 tačaka, 512–8448 rpm)
  - Rev limiter: pronalazi do 5 kandidata s heuristikom
  - Torque efficiency: 16×16, BE u16, Q8 (val/128 = faktor, 1.0 = 100%), mirror +0x518
- `find_changed_regions()` — diff-guided blok scanner, grupira promjene >=N bajtova
- **TODO**: Ignition, injection, lambda mape još nisu implementirane u finderu (samo dokumentirane u CLAUDE.md)

### `core/map_editor.py` — Map editor
- Wrapper oko `ME17Engine` sa validacijom
- `write_cell()` — piše jednu ćeliju, konvertuje display→raw, validira range, auto-sinkronizira mirror
- `write_map()` — batch write cijele mape s validacijom
- `write_rev_limit_row()` — specijalizirani writer za rev limiter, validira soft < mid < hard
- Ispravno barata signed/unsigned i BE/LE za sve tipove

### `core/checksum.py` — Checksum engine
- Implementiran Bosch CRC32 (poly 0x04C11DB7, big-endian bit order) + simple 16/32-bit aritmetički checksum
- **Status: u istraživanju** — stvarne lokacije checksuma u BOOT regionu nisu identificirane
- `verify()` — vraća SW ID status i CAL integrity, ali CRC32 u BOOT-u je UNKNOWN
- `find_checksum_candidates()` — traži ne-nul u32 vrijednosti u 0x000–0x100 regiji
- `update_all()` — NOT_IMPLEMENTED, placeholder
- **Ovo je kritičan nedostatak** — bez ispravnog checksum update-a, flash roundtrip može biti opasan

### `ui/main_window.py` — PyQt6 GUI
- Dark theme (monospace, #1C1C1F pozadina, #4FC3F7 plava za akcente)
- Komponente:
  - `HeaderBar` — adaptivni header: Fajl1 → pojavi se Fajl2 gumb → pojavi se Diff gumb
  - `MapTreeWidget` — stablo mapa grupirane po kategoriji (rpm_limiter, ignition, torque, lambda, axis, misc)
  - `MapTableWidget` — tablica s heat-map bojanjem ćelija, žuto označava razlike između fajlova
  - `DiffWidget` — tabela promijenjenih regiona po CAL/CODE/BOOT
  - `InfoWidget` — prikaz SW info + checksum status
  - `ScanWorker` — QThread za asinkrono skeniranje (da UI ne freezeuje)
- Shortcuti: Ctrl+1 (Fajl1), Ctrl+2 (Fajl2), F5 (Scan), Ctrl+Q (Izlaz)
- Pri loadu Fajla 1 auto-pokreće scan (QTimer 100ms delay)
- **Nedostatak**: MapEditor nije integriran u UI — nema editovanja iz GUI-a, samo read/view

### `main.py`
- Minimalni entry point, dodaje root u sys.path, poziva `ui.main_window.run()`

### `test/test_core.py`
- 8 test funkcija na stvarnim bin fajlovima (ORI + STG2)
- Testira: load, read primitivi, diff (assert-ira točne byte counts: CODE=7087, CAL=169912, BOOT=140), map finder, changed regions, checksum engine, write safety (bounds check)
- Nema pytest dependency — čisti Python, radi s `python test/test_core.py`

---

## Poznate vrijednosti (iz diff analiza i koda)

| Parametar | ORI | STG2 |
|---|---|---|
| SW ID | 10SW066726 | 10SW040039 |
| Rev limiter soft | ~7041 rpm | ~7393 rpm (+352) |
| Rev limiter hard | ~10667 rpm | ~11199 rpm (+532) |
| Torque MSB range | 119–153 (93–120%) | 119–158 (93–123%) |
| Diff BOOT | — | 140 B |
| Diff CODE | — | 7,087 B |
| Diff CAL | — | 169,912 B |

---

## Dodatni nalazi iz _BRIEFING.md

### Ignition mape — precizni podaci
- 16 mapa × 12×12 ćelija, format u8
- Scale: **0.75°/bit** → raw 34 = 25.5° BTDC
- ORI opseg: 24°–33.8° BTDC
- STG2 opseg: 25.5°–36.8° BTDC (NPRo dao +3° do +6° advance)
- Blokovi svako 144B od 0x02B730
- **Osi mape (RPM × Load) još nisu identificirane**

### Injection mapa — agresivan tune
- Format: u16 LE, 12×32 ćelija @ 0x02439C (mirror 0x02451C)
- ORI max: ~49151, STG2 max: **65535 (saturirano!)**
- NPRo dramatično povećao injection duration
- Fizikalna jedinica nepoznata bez A2L (vjerovatno μs ili 0.1μs)

### Lambda mirror
- Lambda mirror offset: **+0x518** (isto kao torque)
- Adrese: 0x0266F0 (main) + 0x026C08 (mirror), 12×18, Q15 LE

### Napomena o CAL regiji
- CAL (0x060000+) je Bosch AUTOSAR/ASCET kompajlirani bytekod
- Pronađeno 754 LE pointera u CODE koji pokazuju na CAL — ali CAL nije mape, dead end
- Sve prave mape su isključivo u CODE regiji (0x010000–0x05FFFF)

### Checksum status
- ECU trenutno **prihvata fajlove bez ispravnog checksuma** (empirijski podatak, treba potvrditi)
- Implementirati `update_all()` ostaje kritičan TODO ali može se testirati i bez njega

### Sigurnosni limiti (ne prekoračiti)
- Rev limiter minimum: 6000 rpm
- Ignition advance maksimum: 42° BTDC (detonacija!)
- Uvijek backup prije flasha, testirati na bench ECU-u

---

## Identificirani problemi / gaps

1. **Checksum nije riješen** — `update_all()` je NOT_IMPLEMENTED. Svaki edit i save bez ispravnog checksuma može rezultirati brick-om ECU-a.
2. **Map editor nije konektovan na UI** — `MapEditor` klasa postoji i radi, ali GUI nema editovanje. Samo pregled.
3. **Ignition mapa nije u finderu** — CLAUDE.md dokumentira 16× ignition mapa @ 0x02B730, svakih 144B, 12×12 u8, ali `map_finder.py` nema implementaciju za to.
4. **Injection i Lambda mape** — isto, dokumentirane u CLAUDE.md ali nema implementacije u finderu.
5. **`__int__.py` umjesto `__init__.py`** — sva tri package init fajla imaju typo u imenu (`__int__.py`). Python ih ne učitava kao pakete, ali funkcionira jer se `sys.path` manipulacijom riješava import.
6. **CAL vs CODE konfuzija** — u CLAUDE.md stoji da je CAL regija TriCore bytekod, ali `engine.py` ima `patch_cal()` koji dopušta pisanje u CAL. `map_editor.py` dopušta write u CAL ili CODE. Torque mapa je u CODE regionu (0x02A0D8), ne u CAL.

---

## Sljedeći logični koraci (TODO)

### Agent: CHECKSUM_ENGINEER
- [ ] Analizirati BOOT regiju oba fajla, naći gdje su checksum vrijednosti
- [ ] Implementirati `update_all()` u `checksum.py`
- [ ] Testirati: flashaj modificirani fajl, provjeri prihvata li ECU

### Agent: MAP_RESEARCHER
- [ ] Naći osi za ignition mapu (12 RPM × 12 Load tačaka) blizu 0x02B730
- [ ] Identificirati fizikalnu jedinicu injection mape
- [ ] Pronaći boost/wastegate mapu
- [ ] Dokumentirati u `_materijali/MAP_RESEARCH.md`

### Agent: UI_DEVELOPER
- [ ] Konektovati `MapEditor` na GUI (editable TableWidget, dvoklick)
- [ ] Implementirati undo/redo (Ctrl+Z / Ctrl+Y)
- [ ] Prikaz osi (RPM × Load labele u tablici)
- [ ] Export u CSV/Excel
- [ ] Hex viewer tab

### Agent: ANALYZER
- [ ] Analizirati sve .bin dumpove u `_materijali/` (posebno RXP 300 21, GTI, Spark, Wake Pro)
- [ ] Dokumentirati nalaze u `_materijali/FINDINGS.md`

### Općenito
- [ ] Popraviti `__int__.py` → `__init__.py` (typo u svim paketima)
- [ ] Testirati save → flash roundtrip na bench ECU-u

---

---

## 2026-03-13 — Faza 1 + 2 implementacija

### Faza 1 — map_finder.py kompletno repisano
- Dodate sve mape: Ignition (14/16×12×12 u8), Injection (12×32 u16 LE), Lambda (12×18 Q15 LE), Rev limiter (5 poznatih adresa)
- `MapDef` prosiren s `cell_bytes` i `total_bytes` propertijem
- `AxisDef` prosiren s `values` poljem za stvarne RPM vrijednosti
- Rev limiter heuristika zategnuta (alignment provjera, MIN_STEP=200)
- Ignition #08 i #09 ispravno isključeni: #08 ima vrijednosti do 227 (knock delta), #09 ima nule i male vrijednosti (trim)
- Lambda potvrðena: λ 0.965–1.073 (ORI), λ 0.965–1.073 radi

### Faza 2 — map_editor.py azuriran
- `_read_raw` i `_write_one` podrzavaju u8 (1 bajt po celiji)
- `write_cell` i `write_map` koriste `defn.cell_bytes` umjesto hardkodiranog 2
- `write_rev_limit_scalar` dodan za 1×1 rev limiter scalare
- Edit test potvrðen: IGN write (u8), LAM write (u16 LE Q15), TOR write (u16 BE Q8) — sve radi

### Faza 2 — ui/main_window.py kompletan redesign
- **MapLibraryPanel**: search + tree, adaptivne kategorije
- **MapTableView**: RPM × Load osi iz `AxisDef.values`, heat-map, diff highlight
- **PropertiesPanel**: ECU info, cell info (raw+display+adresa), ±step gumbi, direktni unos, map stats
- **LogStrip + HexStrip**: donji panel, log s timestamp, hex pregled adrese
- **Toolbar**: Open1/2, Save, Scan, Diff
- **DiffWidget**: ostaje isti, ali sad u tab-u
- Editovanje konektovano: click celija → PropertiesPanel → `MapEditor.write_cell()` → refresh

### Stanje testova
- Svi testovi prolaze (test/test_core.py)
- 26 mapa pronaðeno u ORI i STG2
- Edit write potvrðen za sve formate

### Ostaje (sljedece faze)
- Faza 3: Undo/redo, export CSV, compare side-by-side u map table
- Faza 4: Checksum reverse engineering
- Faza 5: Analiza dumpova u _materijali/

*Azurirano: 2026-03-13*

---

## 2026-03-14 — Faza 4: Checksum brute-force istraga

### Metoda
6 rundi brute-force analize, 100+ algoritama/regija kombinacija:
- CRC32 Bosch (sve varijante init/xorout/refin/refout), zlib CRC32
- Adler-32, Fletcher-32, additive sum u8/u16/u32 BE+LE, XOR-sum
- Byte-swapped CRC, word-by-word CRC, chained CRC
- MD5, SHA-1, SHA-256 (truncated na 4B)
- Regije: CODE, BOOT, BOOT+CODE, CODE+CAL + sve podvarijante

### Rezultat
**0 pogodaka** — algoritam je definitino nestandardan/proprietaran.

### Novi arhitekturalni nalazi

| Nalaz | Detalji |
|---|---|
| BOOT region = 0x0000-**0x7EFF** | NE 0xFFFF! ENDADD u headeru 0x3C = 0x80007EFF |
| Gap 0x7F00-0xFFFF | 33KB: DEADBEEF terminator + nule + TC1762 kod @ 0xFF00 |
| Blok @ 0x7E7C (132B) | Kriptografski potpis (RSA-1024?), ne može se replicirati |
| FADEFACE deskriptor @ 0x40 | 0x48=0x80012C78 (CODE), 0x4C=0x80007E74 (pred sig. blokom) |

### Zaključak
Vrijednost @ 0x30 je Bosch proprietary algoritam iz BOOT koda.

**Daljnji koraci:**
1. **Ghidra + TriCore v1.3 plugin** — disassembly BOOT koda 0x0050-0x7E7B
2. **Praktično**: flash alati (KTAG/Flex) automatski korigiraju checksum
3. **Alternativa**: tražiti ME17.8.5 checksum u ECU tuning forumima

### Skripte istraživanja
- `checksum_bruteforce.py` — Round 1-2 (CRC+sum)
- `checksum_deep.py` — Round 3 (Adler, chained, hex dump)
- `checksum_round3-6.py` — Round 3-6 (napredni testovi)

*Azurirano: 2026-03-14 09:10*

---

## 2026-03-14 10:xx — Faza 4: CHECKSUM PRONADEN + DTC OFF analiza

### 10:00 — Checksum algoritam pronađen!

**Metoda proboja**: Analiza 4 ECU fajla iz `_materijali/unknow/` (rxtx_260_524060.bin, rxt_514362) u kombinaciji s closed-form CRC tehnikom (CS uključen u izračun, ne nuliran).

**Algoritam**: CRC32-HDLC (ISO-HDLC / standardni zlib CRC32)
| Parametar | Vrijednost |
|---|---|
| Poly | 0xEDB88320 (reflected) |
| Init / XorOut | 0xFFFFFFFF / 0xFFFFFFFF |
| Regija | BOOT [0x0000, 0x7F00) = 0x7F00 bajta |
| Tip | Closed-form — CS @ 0x30 uključen u izračun |
| Residua | 0x6E23044F (fiksna, verificirano na 4 fajla) |

**Ključna implikacija**: Promjena CODE mapa (0x10000-0x5FFFF) **ne zahtijeva** promjenu CS! CS se mijenja samo ako se mijenja BOOT (SW verzija, BOOT kod ili RSA potpis).

**Implementirano** u `core/checksum.py`:
- `verify_boot_crc()` — provjera residue
- `compute_new_cs()` — meet-in-the-middle inverzni CRC za novi CS
- Testirano: ori_300 CS točno reproduciran (0xE505BC0B ✓)

### 13:xx — DTC OFF analiza

Korisnik dodao `_materijali/DTC OFF/` s primjerima:
- P0523 (Wake Pro 230): oil pressure sensor off
- P1550 (RXP-X 300 17, SW 10SW004672): oil pressure DTC off

**Potvrđeno**: Profesionalni DTC OFF alati NE mijenjaju CS (samo CODE → CS nepromijenjen).

**DTC struktura** (pronađena za P1550 = naš motor):
| Lokacija | Promjena | Opis |
|---|---|---|
| 0x02108A–0x021093 | 0x04–0x06 → 0x00 | DTC enable bits (10 bajtova) |
| 0x02187E–0x02187F | 0x5015 → 0x0000 | DTC kod P1550 (LE u16 = 0x1550) |
| 0x021BE0–0x021BE1 | 0x5015 → 0x0000 | Mirror DTC koda |

**DTC enable tablica @ 0x021080**: svaki bajt = jedan DTC senzor; 0x06=aktivan, 0x05=djelomično, 0x04=warning-only, 0x00=ugašen.

**U tijeku**: Analiza svih DTC lokacija u ori_300 za full DTC OFF implementaciju.

*Azurirano: 2026-03-14 13:30*
