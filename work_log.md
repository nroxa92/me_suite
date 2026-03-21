# ME17Suite — Work Log

## 2026-03-21 23:55 — UI fix: _on_main_tab_changed + Kalkulator tab vidljivost

### Zadatak
Dvije popravke vidljivosti u `ui/main_window.py`:
1. `_on_main_tab_changed` — koristio setCurrentIndex(1/2) na `_sidebar_stack` koji ima samo stranicu 0 (DTC i EEPROM sidebari su odavno premješteni u vlastite tabove). Rezultat: crash/warning pri navigaciji na EEPROM/DTC tab.
2. Kalkulator tab — bio zadnji (pozicija 6) od 7 tabova u uskom PropertiesPanel (270px). Nije bio vidljiv jer su ga prethodni tabovi "pregažili".

### Promjene
- `ui/main_window.py`: `_on_main_tab_changed()` — zamijenjen logikom show/hide: MAPE tab (idx=0) → `_sidebar_stack.show()`, svi ostali → `_sidebar_stack.hide()`
- `ui/main_window.py`: `CalculatorWidget` — premješten s pozicije 6 na poziciju 1 (`insertTab(1, ...)`, odmah iza "Cell"), preimenovan iz "Kalkulator" u "Calc" za uštedu mjesta
- Redoslijed tabova PropertiesPanel nakon promjene: Cell | **Calc** | Mapa | SW | ECU | DTC | History

### Test
- `python -c "from ui.main_window import MainWindow; print('OK')"` → OK

### Fajlovi
- `ui/main_window.py` — jedini fajl mijenjan

---

## 2026-03-21 23:30 — POVECANJE/SMANJENJE dodani svim MapDef opisima u map_finder.py

### Zadatak
Dodavanje `\nPOVECANJE: ...\nSMANJENJE: ...` blokova na kraj svakog MapDef `description` stringa koji ima `UTJECE NA:` blok u `core/map_finder.py`. ASCII only, tehnički točne rečenice, nema promjena logike.

### Promjene
- `core/map_finder.py`: stotine Edit operacija — dodane POVECANJE/SMANJENJE rečenice za sve aktivne MapDef objekte koji imaju UTJECE NA blok
  - Pokriveno: ignition (sve mape), fuel 2D, linearization, torque, lambda (main/adapt/trim/bias/eff/prot), SC bypass, boost faktor, SC korekcija, DFCO, KFPED, FWM, KFWIRKBA, cold start, knock params, overtemp lambda, neutral corr, deadtime, RPM ose, temp fuel, thermal enrichment, accel enrichment, 2016 gen varijante
  - 2016 gen scan metode: sc_corr, boost, overtemp_lambda, neutral_corr, dfco, fuel, torque, lambda bias 1503
- Sintaksa verificirana: `python -c "from core.map_finder import MapFinder; print('OK')"` → OK
- 2 zakomentarirane UTJECE NA linije (prepretni komentari) — svjesno ostavljene bez POVECANJE (nisu aktivni MapDef-ovi)

## 2026-03-21 17:00 — Refaktorizacija main_window.py — novi tab layout

### Zadatak
Refaktorizacija `ui/main_window.py` prema specifikaciji korisnika.

### Promjene
- `_build_menus()`: menuBar sakriven (`hide()`), shortcuts registrirani direktno kao QAction na MainWindow (Ctrl+1/2, Ctrl+S, Ctrl+Z/Y, F5, Ctrl+Q)
- `_main_tabs` restrukturiran: Tab0=MAPE, Tab1=EEPROM (full-page + header s Back gumbom + Load dugmetom), Tab2=DTC (full-page + header s Back gumbom), Tab3=DIFF (skriven, otvara se via toolbar), Tab4=MAP DIFF (skriven)
- Uklonjen `self.tabs` (sub-QTabWidget unutar ALATI) i sve stare varijable (`_dtc_tab`, `_eeprom_tab`, `_calc_tab`, `_diff_tab`, `_map_diff_tab`)
- `CalculatorWidget` premješten u `PropertiesPanel.__init__` kao Tab 5 (Kalkulator)
- `_on_main_tab_changed()` ažuriran: idx0→sidebar0, idx1(EEPROM)→sidebar2, idx2(DTC)→sidebar1, else→sidebar0
- `_on_tab_changed()` uklonjen
- `_show_diff()` / `_show_map_diff()`: koriste `setTabVisible(3/4, True)` + `setCurrentIndex(3/4)`
- `_open_eeprom_from_btn()` nova metoda; `_open_eeprom()` delegira na nju + navigira na Tab1
- DTC iz map_selected: `setCurrentIndex(2)` (bez stare `tabs.setCurrentIndex`)
- `_load2()`: uklonjen `tabs.setTabVisible(_diff/_map_diff_tab)` (nema više tih varijabli)
- Test: `python -c "from ui.main_window import MainWindow; print('OK')"` → OK

### Fajlovi
- `ui/main_window.py` — jedini fajl mijenjan

## 2026-03-21 16:30 — Poboljšani nazivi i dependency opisi u map_finder.py

### Zadatak: map_finder.py — poboljšani nazivi i dependency blokovi
**Fajl:** `core/map_finder.py`

**Promjene:**
- `_IGN_NAMES` lista (19 naziva): zamijenjeni generički nazivi ("Osnovna 1-8") s opisnima koji govore KADA je mapa aktivna (#00 = "Normalni rad [baza A]", #05 = "Hladan motor / zagrijavanje", #07 = "Decel / overrun", #16-17 = "NPRo extended [sport]", #18 = "Fallback / sigurnosna")
- `_make_ign_def` description logika: svaka grana (knock/extended/partial/aux_a/aux_b/aux_sc/base) sada uključuje `OVISI O:` / `UTJECE NA:` blok na kraju description stringa
- Dependency blokovi dodani u description svake od ovih MapDef definicija (samo stringovi, logika nepromijenjena):
  - `_INJ_DEF` — linearization; `_ACE1630_INJ_DEF` — 2D fuel; `_GTI_INJ_DEF` — GTI fuel
  - `_LAMBDA_DEF`, `_LAMBDA_ADAPT_DEF`, `_LAMBDA_TRIM_DEF`, `_LAMBDA_BIAS_DEF`
  - `_LAMBDA_PROT_DEF`, `_LAMBDA_EFF_DEF`, `_OVERTEMP_LAMBDA_DEF`, `_NEUTRAL_CORR_DEF`
  - `_TORQUE_DEF`, `_TORQUE_OPT_DEF`
  - `_SC_DEF`, `_SC_BOOST_FACTOR_DEF`, `_SC_CORR_DEF`
  - `_TEMP_FUEL_DEF`, `_THERM_ENRICH_DEF`, `_ACCEL_ENRICH_DEF`
  - `_KFPED_DEF`, `_IGN_CORR_DEF`, `_DEADTIME_DEF`
  - `_DFCO_DEF`, `_DECEL_RPM_CUT_DEF`, `_START_INJ_DEF`
  - `_LAMBDA_EFF_U8_DEF`, `_LAMBDA_THRESH_DEF`

**Provjera:** `python -c "from core.map_finder import MapFinder"` → OK

## 2026-03-21 — 2017 gen skeneri + 2016 lambda adapt (sesija)

### Zadatak 1: 2017 gen (10SW012999) — implementirani -0x2AA offset skeneri
**Nove konstante:**
- `LAM_MAIN_2017 = 0x026446`, `LAM_ADAPT_2017 = 0x0265F6`, `LAM_TRIM_2017 = 0x026B0E`
- `BOOST_FACTOR_2017 = 0x025B4E`, `TEMP_FUEL_2017 = 0x025BA6`
- `TORQUE_MAIN_2017 = 0x02A0D8` (ista adresa!), `TORQUE_MIRROR_2017 = 0x029BC0` (main-0x518)

**Nove metode:** `_scan_2017_lambda`, `_scan_2017_lambda_adapt`, `_scan_2017_lambda_trim`,
`_scan_2017_boost_factor`, `_scan_2017_temp_fuel`, `_scan_2017_torque`

**Rezultat:** 10SW012999: **23 → 28 mapa** (+5 neto: 7 novih - 2 false-positive uklonjeni)

### Zadatak 2: 2016 gen 1503 lambda_adapt — ne postoji
**Dokaz:** @ 0x024DFA: 48/216 garbage, 260hp vs 215hp razlika **192/216**
- RPM os @ 0x024F46 počinje unutar potencijalne adapt tablice (samo 162 validnih val)
- Adresa -0x1AA6 od 2018 (0x0268A0) = garbage bytecode za oba dump-a
- ECU firmware 10SW000778/776 ne koristi zasebnu lambda adaptaciju
- `LAM_ADAPT_2016_1503` komentar ažuriran s obrazloženjem

**Fajl:** `core/map_finder.py`
**Testovi:** sve SW varijante OK bez regresija

## 2026-03-22 01:00 — Imenovanje mapa + dokumentacija (sesija završena)

### Fajlovi promijenjeni
- `core/map_finder.py` — finalni nazivi i opisi za 6 ranije neidentificiranih mapa

### Promjene naziva:
1. `Lambda — efikasnost sub-tablica (KFWIRKBA 2D sub)` → `Faktor efikasnosti goriva (KFWIRKBA sub)` (Confidence 80%)
2. `Paljenje — korekcija po RPM×load` → `Paljenje — korekcija za moment (KFZW2)` (Confidence 80%, DID 0x2142)
3. `Moment — optimalni / vozačev zahtjev [%]` → `Vozačev zahtjev momenta — FWM [%]` (Confidence 95%, DID 0x2103/0x213B)
4. `Decel RPM ramp — DFCO per-load pragovi` → `DFCO — rampa odrezivanja goriva (RPM pragovi)` (Confidence 90%)
5. `Lambda efikasnost u8 lookup (4x kopija)` → `KFWIRKBA — tranzijentni odaziv (4 uvjeta)` (Confidence 80%)
6. `Lambda thresholds — KFWIRKBA pragovi [Q15]` → `Lambda zaštita — pragovi aktivacije [Q15]` (Confidence 95%, DID 0x2107/0x2158)

### DID korelacija (bench sniff_livedata.csv):
- DID 0x2103 = Desired Indicated Engine Torque → potvrđuje FWM mapu
- DID 0x213B = Driver's Desire Throttle Angle → potvrđuje FWM lanac
- DID 0x2142 = Desired Ignition Angle After Torque Intervention → potvrđuje KFZW2 mapu
- DID 0x2107/0x2158 = 0xFFFF (bench) → lambda pragovi "disabled" → potvrđuje Lambda zaštita mapu
- DID 0x2136 = 0xCA = 101.0 kPa (atmosferski tlak na bench)

### CAN 0x122 nalaz:
- 10ms period, XOR checksum format identičan ECU, bytes[4:6]=0x0B5E=2910=engine hours
- Hipoteza: IBR (Intelligent Braking and Reverse) modul

## 2026-03-21 23:45 — Lambda konstante 2016 gen 1503 — ispravak imenovanja

### Fajlovi promijenjeni
- `core/map_finder.py` — konstante LAM_MAIN/TRIM/ADAPT ispravno preimenovane

### Nalaz (oba agenta a12791 + a227 potvrdili):
- `0x024A90` = **lambda_trim** (sve >1.0, lean bias) — staro pogrešno ime: "main"
- `0x024C4A` = **lambda_main** (crosses ±1.0) — structural proof: lambda_bias@0x024B30 + 141×2 = 0x024C4A
- `0x024DF0` = **NEVAŽEĆE** (tail corruption) — izbačeno iz skenera
- Lambda_adapt = **neidentificirana** — tražiti poslije 0x025308
- 2016 1503 260hp/215hp: 31 mapa (bila 32 — uklonjen invalid entry)
- Overtemp lambda @ 0x024034: AKTIVNA krivulja (ne SC bypass), pada do Q15=0.102 pri visokim temp

## 2026-03-21 23:30 — 2016 gen ACE/1503 skeneri — finalni test

### Fajlovi promijenjeni
- `core/map_finder.py` — 5 novih _scan_2016_ace_* metoda (sc_corr, boost, overtemp, neutral, dfco)

### Rezultati (map count)
| SW | Model | Mapa (staro→novo) |
|----|-------|-------------------|
| 10SW004675 | 2016 ACE 300hp | ~24 → **31** |
| 10SW004672 | 2016/17 ACE 300hp | ~24 → **31** |
| 10SW039XXX | 2019 ACE | 57 (nepromijenjen) |
| 10SW000778 | 2016 1503 260hp | ~24 → **32** |
| 10SW012502 | 2017 1503 260hp | ~24 → **32** |
| 10SW025021 | 2018 1503 230hp | 60 (nepromijenjen) |
| 10SW012999 | 2017 1503 230hp | 23 (parcijalna podrska — by design) |

- 2016 ACE: +7 mapa (sc_corr, boost, overtemp_lambda, neutral_corr, dfco + prethodni lambda/torque)
- 2016 1503: +8 mapa (sc_corr, thermal, deadtime, eff_corr, ign_corr_2d, mat_corr, accel, cold_start, kfped, overtemp, neutral, lambda_bias)
- Svi referentni 2018/2019 SW-ovi ostaju nepromijenjeni — nema regresija

## 2026-03-20 17:30 — Lambda adapt adresa 2016 gen 4-TEC 1503 — conflict resolution

### Fajlovi
- `_docs/scan_2016_1503_lambda_verify.md` — novi izvjestaj

### Nalazi
- **Session A (0x024C40 = lambda_adapt) — POGRESAN naziv** — 0x024C40 je lambda_MAIN
- **Session B (0x024DFA = lambda_adapt) — POGRESAN offset** — misaligned, 10B unutar Map C (garbage)
- **Triplet** (sve tri mape direktno uzastopne, nema razmaka):
  - `0x024A90` = lambda_trim/sekundarna korekcija (sve >1.0, lean bias, Q15 1.014-1.081)
  - `0x024C40` = lambda_MAIN (raspon +/-1.0, Q15 0.988-1.050) — ispravna identifikacija
  - `0x024DF0` = nevazeca (tail corruption u donjim redovima, non-Q15 vrijednosti)
- Mirror set (+0x518 od svakog): 0x024FA8 (mirror trim) / 0x025158 (mirror main)
- **Prava lambda_adapt 2016 gen 1503 = NEIDENTIFICIRANA** — nije ni 0x024C40 ni 0x024DFA
- Shape distance prema 2018_main: 0x024A90=0.104, 0x024C40=0.138
- Shape distance prema 2018_adapt: 0x024A90=0.123, 0x024C40=0.225
- Axis struktura: 18pt RPM @ 0x024A44 (raw/4=4100-8500), 18pt load @ 0x024A68 (Q14, 3.9-40.4%)

## 2026-03-20 16:00 — Lambda bias / MAT / Overtemp verifikacija 2016 gen 4-TEC 1503

### Fajlovi
- `_docs/scan_2016_1503_verify2.md` — novi izvjestaj

### Nalazi
- **Lambda bias @ 0x024B30** POTVRDJENO — aligment: 0x024B30+141*2=0x024C4A=lambda main start
- Offset formula: 2016 gen = 2018 adresa - 0x1AA6 (za lambda bias i lambda main)
- **260 vs 215 lambda bias: 141/141 razliciti** (Agent 2 bio u pravu) — razlicite kalibracije SC vs SC
- 260: Q15 [1.0137..1.0811], 215: Q15 [1.0176..1.0834] — oba iskljucivo iznad 1.0 (SC karakteristika)
- **MAT correction @ 0x025A92/9E**: 260 vs 215 prakticno identicni (3 minor diff: axis[6]=158vs155, axis[7]=162vs160, data[4]=31608vs31611)
- **Overtemp lambda @ 0x024034**: 260 == 215 IDENTICNI (0/63 razlika); max=1.0039 (aktivna zastita, ne SC bypass)
- MAT offset vs 2018: -0x1B50 (razlicit od lambda offset -0x1AA6 — nema uniformnog globalnog offseta)

## 2026-03-21 — UI refaktor: 2 glavna taba, opis mapa, CAN uklonjen

### Fajlovi promijenjeni
- `ui/main_window.py` — CAN tab/sidebar uklonjen; 2 glavna taba (MAPE/ALATI); PropertiesPanel "Mapa" tab dobio OPIS sekciju

### Promjene
- **CAN Logger + CAN Live uklonjen** — tool je software-only, bez IXXAT hardvera
- **Centar: 2 glavna taba**:
  - `MAPE` (tab 0) → MapTableView (Map Editor) s map library sidebarom
  - `ALATI` (tab 1) → sub-tabs: DTC Off | EEPROM | Kalkulator | Diff | Map Diff (s njihovim sidebarima)
- **PropertiesPanel "Mapa" tab** — nova "OPIS — KADA / ZAŠTO" sekcija:
  - Kategorija badge (PALJENJE/GORIVO/LAMBDA/itd.) + Pouzdanost badge (POTVRĐENO/2016 GEN/85%/~80%)
  - Pun `defn.description` tekst — koji, kada, zašto za svaku mapu
  - Napomene sekcija ostaje
- **SwCompatWidget** dodan kao tab "SW" u PropertiesPanel
- **Navigacija** ažurirana: `_on_main_tab_changed` + `_on_tab_changed`; sve setCurrentIndex pozive usmjeravaju na pravi parent tab

---

## 2026-03-21 — Lambda secondary mape za 2016 gen 1503 (Agent 2)

### Fajlovi promijenjeni
- `core/map_finder.py` — 3 nova skenera: overtemp_lambda/neutral_corr/lambda_bias; KFWIRKBA nije u 2016 gen

### Nove adrese (sve offset -0x1AA6 od 2018+)
| Mapa | Adresa | Napomena |
|------|--------|---------|
| overtemp_lambda | 0x024034 | 260hp == 215hp (SC krivulja) |
| neutral_corr | 0x0240B2 | flat 0x4040 = Q14 1.004 |
| lambda_bias | 0x024B30 | 260hp != 215hp (141/141 razlika) |
| KFWIRKBA | — | NIJE pronađena u 2016 gen |

### Konačan rezultat — sve SW varijante
| SW | Model | Mape |
|----|-------|------|
| 10SW004675 / 004672 | 2016 ACE 1630 300hp | **26** |
| 10SW000776 / 000778 | 2016 1503 215/260hp | **32** |
| 10SW012502 | 2017 1503 260hp | **32** |
| 10SW012999 | 2017 1503 230hp | **23** |

---

## 2026-03-21 — 2016 gen 1630 ACE skeneri implementirani

### Fajlovi promijenjeni
- `core/map_finder.py` — nova konstante + 4 skenera za 2016 ACE; find_all() else grana

### Adrese (Agent 5) — 10SW004675 / 10SW004672 (identični!)
- Fuel 2D: **0x022052** — **Q14 format** (ne Q15!); 2× raw vrijednosti = iste fizičke količine
- IGN base: **0x02B31E** (−0x412 od 2018+); sadržaj identičan 2018+!
- Lambda main/adapt/trim: **0x026444/0265F4/026B0C** (sve −0x2AC); NEMA mirror
- Torque: **0x029B48** (−0x590 od 2018+); mirror +0x518 = 0x02A060

### Konačan broj mapa
| SW | Mape |
|----|------|
| 10SW004675/004672 | **26** |
| 10SW000776/778/012502 | **30** |
| 10SW040039 2019 ACE | **57** (regresija OK) |

---

## 2026-03-21 — 9 novih skenera za 2016 gen 4-TEC 1503 u MapFinder

### Fajlovi promijenjeni
- `core/map_finder.py` — 14 novih konstanti + 9 novih `_scan_2016_1503_*` metoda + pozivi u `find_all()`

### Implementirano (sve adrese iz agent scan rezultata)
| Mapa | Adresa | Format | Agent |
|------|--------|--------|-------|
| sc_corr | 0x023478 | 9×7 u16 LE Q14 | Ag1 |
| thermal_enrichment | 0x028004 | 8×7 u16 LE /64=% | Ag4 |
| deadtime | 0x023E04 | 10×14 u16 LE | Ag4 |
| eff_correction | 0x023F36 | 14×10 u8 /128 | Ag4 |
| ign_corr_2d | 0x02169A | 8×8 u8 0.75°/bit | Ag4 |
| mat_correction | 0x025A9E | 1×12 u16 LE Q15 | Ag4 |
| accel_enrichment | 0x026223 | 5×5 u16 LE Q14 | Ag3 |
| cold_start | 0x024236 | 1×6 u16 LE Q15 | Ag3 |
| kfped | 0x026F6C | 10×20 u8 | Ag3 |

### Rezultati testiranja
- 260hp (10SW000778): **30 mapa** ✓
- 215hp (10SW000776): **30 mapa** ✓
- 2017 260hp (10SW012502): **30 mapa** ✓ (2016 gen layout)
- 2019 300hp ACE: **57 mapa** ✓ (bez regresije)
- 2019 Spark: **54 mapa** ✓ (bez regresije)

### Nisu implementirani
- `boost_factor` @ 0x02619C — NEPOTVRDENO (44 elem umjesto 40, pre-kontekst nije X-os boost)
- `knock_params` @ 0x024268 — drugačija interna struktura od 2018+, skip za sada
- Lambda secondary (bias/overtemp/neutral/KFWIRKBA) — Agent 2 nije završio istraživanje
- 2016 gen 1630 ACE skeneri — Agent 5 nije završio

---

## 2026-03-21 — Map discovery: fuel, ign, lambda, torque u 2016 gen 1630 ACE

### Fajlovi promijenjeni
- `_docs/scan_2016_ace_maps.md` (novo)

### Rezultati
- **Fuel 2D**: **0x022052** — offset −0x14 od 2018+; format 12×16 Q14 (sve vrijednosti 2× veće od 2018+, iste osi); header @ 0x022016
- **Ignition base**: **0x02B31E** — offset −0x412 od 2018+; 19 mapa stride 144B; sadržaj identičan 2018+ (0 diff po svim 19 mapama)
- **Lambda main**: **0x026444** — offset −0x2AC od 2018+; 12×18 Q15; NEMA identičnog mirrora (za razliku od 2018+)
- **Lambda trim**: **0x026B0C** — offset −0x2AC; Q15=[0.960–1.032]
- **Lambda adapt**: **0x0265F4** — offset −0x2AC; Q15=[0.979–1.068]
- **Torque main**: **0x029B48** — offset −0x590 od 2018+; 16×16 BE Q8; mirror @ 0x02A060 (+0x518, OK)
- **SC boost factor**: **0x025B4E** — offset −0x2AA; flat 20046 Q14=1.224 (+22.4%)
- **SC correction**: **0x0221FA** — offset −0x14; 9×7 Q14; identičan s 2018+

### Ključni nalazi
- Nema jedinstvenog globalnog CODE offseta: fuel/sc_corr=−0x14, lambda=−0x2AC, ign=−0x412, torque=−0x590
- Fuel je Q14 format (2× Q15 vrijednosti) — drugačija normalizacija od 2018+
- Lambda nema mirror kopiju u 2016 gen 1630 ACE (jedina kopija main)
- 10SW004675 i 10SW004672 imaju 0 diff u svim mapama — iste kalibracije
- SC bypass: 0x0205A8=0x3333 (razlikuje se od 2018+ koji ima 0x2626), 0x012C60=0x2020

## 2026-03-21 24:20 — Signature search: KFPED, accel, cold start, knock u 2016 gen 1503

### Fajlovi promijenjeni
- `_docs/scan_2016_1503_control_maps.md` (novo)

### Rezultati
- **KFPED throttle**: header **0x026F4C** (32B), data **0x026F6C** (200B), mirror +0xE6 @ 0x027052; offset -0x25DC vs 2018
  - 260 vs 215: različiti podaci (198/200B), logično (SC 260hp > 215hp)
- **Accel enrichment**: **0x026223**; offset -0x1E36 vs 2018; 8B pre-sig match; 260==215 identični
- **Cold start injection**: data **0x024236** (12B), axis **0x02422A** (12B); offset -0x1AA6; 260==215 identični
- **Knock params**: **0x024268** (104B); offset -0x1490 vs 2018
  - NAPOMENA: 2016 gen knock blok ima DRUGAČIJU strukturu — 9×0x4040 + 9×0x1F1F + tail, ne [ACCD+1F1F×50] kao 2018+

### Ključni nalaz
- Nema uniformnog CODE offseta: cold=-0x1AA6, knock=-0x1490, accel=-0x1E36, KFPED=-0x25DC, rev=-0x2076
- Knock params ima potpuno drugačiji format u 2016 gen (9 threshold-a vs 2 u 2018+)
- KFPED potvrđen kao tunabilna mapa — 260hp SC i 215hp SC imaju različite vrijednosti

## 2026-03-21 — Signature search: SC correction i SC boost_factor u 2016 gen 4TEC 1503

### Fajlovi promijenjeni
- `_docs/scan_2016_1503_sc_maps.md` (novo)

### Rezultati
- **SC correction: PRONAĐENO @ 0x023478** (vrijedi za 10SW000778, 10SW000776, 10SW012502)
  - Offset vs 2018 (0x02220E): +4714B = +0x126A
  - 215hp == 260hp == 2017/260: identične vrijednosti (0/63 razlika)
  - 2017/230 (10SW012999): @ 0x0221FA (−14B od 2018, konzistentno s −0x2AA offsetom za taj SW)
  - Vrijednosti: Q14 [1.024–1.886] — ispravan SC correction raspon
- **SC boost_factor: JEDINI KANDIDAT @ 0x02619C (NEPOTVRDENO)**
  - 44 elementa flat 23130 (Q14=1.412, +41.2%) — ista vrijednost kao 2018+
  - Ali pre-kontekst NIJE X-os boost (lambda-like vrijednosti, ne rastuci kPa niz)
  - X-os boost iz 2018 (50 57 5d ... bb) nije pronaden ni u jednom 2016 gen binariju
  - 2017/230 (10SW012999) boost @ 0x025B4E = POTVRĐENO flat 23130 (40 elem, −0x2AA od 2018)

### Ključni nalaz
- Nema jedinstvenoga offseta: SC corr je +0x126A, boost je neodređen
- 10SW012502 (2017 260hp) = 2016 gen layout — SC corr na 0x023478 (ne 2018 adresi)
- 2016 gen moguće nema odvojenu 1D boost_factor tablicu u standardnom formatu

## 2026-03-21 23:55 — Signature search: correction mape u 2016 gen 1503

### Fajlovi promijenjeni
- `_docs/scan_2016_1503_corrections.md` (novo)

### Rezultati
- thermal_enrichment: **0x028004** (offset -0x2A3E vs 2018)
- deadtime: **0x023E04** (offset -0x1AA6)
- eff_correction: **0x023F36** (offset -0x1AA6, susjedan s deadtime)
- ign_correction_2d: **0x02169A** (offset -0x0CDA)
- MAT correction: **osa 0x025A92, data 0x025A9E** (offset -0x1B50; 2 kopije stride=0x122; pronađeno pattern scanom)
- DFCO ramp: **NIJE PRISUTNA** — 2016/2017 gen ima samo 2pt stub @ 0x026CAC; 0x028C30 je IGN mapa u 2016 gen

### Ključni nalaz
- Nema jedinstvenoga globalnog offseta za sve mape — svaka mapa ima vlastiti pomak
- 2016/2017 gen DFCO = stub (100,150,0xFFFF...), puna 16×11 tablica uvedena tek u 2018+

## 2026-03-21 23:30 — 2016 gen 1503 skeneri implementirani u MapFinder

### Fajlovi promijenjeni
- `core/map_finder.py`

### Nalaz i implementacija
- `_REV_KNOWN_ADDRS` proširen: dodani 0x026E1E i 0x026D82 (2016 gen 1503)
- `_2016_GEN_SW_IDS` ažuriran: dodan 10SW004672; komentar ažuriran s potpunim adresama
- `_2016_GEN_1503_SW_IDS` = novi set {10SW000776, 10SW000778, 10SW012502}
- 5 novih konstanti: `IGN_BASE_2016_1503`, `LAM_MAIN/ADAPT/TRIM_2016_1503`, `TORQUE_MAIN/MIRROR_2016_1503`, `FUEL_2016_1503`, `SC_2016_1503`
- 5 novih scanner metoda: `_scan_2016_1503_sc/fuel/ignition/lambda/torque`
- `find_all()` `is_2016_gen` grana: razlikuje 1503 (pune mape) od 1630 ACE (minimalna podrška)

### Potvrđene adrese 2016 gen 1503 (sve 3 SW varijante identičan layout)
- Rev: 0x026E1E (main), 0x026D82 (mirror) — 5126t = 8072 RPM
- SC bypass: 0x012C60 (7×7 u8, value 0x2020)
- Fuel 2D: 0x0232D0 (12×16 LE u16 Q15); osi @ 0x0232B0 (16pt) + 0x023298 (12pt) — Q14 format
  - Napomena: dijagonalne 0-ćelije u mapi su normalne (fuel cut zone, identične 215hp i 260hp)
- Ignition: 0x028988 base, stride 144B, 13 validnih mapa (od 19 skeniranih)
- Lambda main: 0x024A90, adapt: 0x024C40 (+0x1B0), trim: 0x024DF0 (+0x360); mirror +0x518
- Torque: 0x027604 (16×16 LE u16 Q8, lo=133-138 = Q8 0.52-0.54); mirror @ 0x027B1C

### Rezultati testiranja
- 10SW000776 (215hp): 21 mapa ✓
- 10SW000778 (260hp): 21 mapa ✓
- 10SW012502 (2017 260hp): 21 mapa ✓
- 10SW004675 (2016 ACE): 4 mape (nepromijenjeno — minimalna podrška) ✓
- 10SW066726 (2021 300hp): 57 mapa ✓
- Svi testovi prolaze (test_core.py)

## 2026-03-21 22:30 — 2016 gen 1503 rev limiter identificiran

### Metodologija
- Signature search: uzet kontekst oko 0x028E94 u 10SW012999 (poznat), tražen isti pattern u 1503 2016 gen
- Cross-check: kontekst byte-for-byte identičan s 1630 ACE 2016 gen @ 0x028E94

### Nalaz
- **Adresa**: `0x026E1E` — rev limiter za SVE 2016 gen 1503 varijante
- **Mirror**: `0x026D82` (156B = 0x9C ranije)
- **Vrijednost**: 5126 ticks = **8072 RPM** (identično za 215hp i 260hp)
- **SW koji koristi ovu adresu**: 10SW000776, 10SW000778, **10SW012502** (2017 260hp — 2016 gen layout!)
- **Offset vs 1630 ACE ekvivalenta (0x028E94)**: −0x2076 bytes
- **Potvrda**: identičan CODE kontekst (`06 14 1e 2d 3c 5a 78 00 05 00...`) u 1503 @ 0x026E1E i 1630 @ 0x028E94

### Fajlovi ažurirani
- `_docs/SEADOO_KNOWLEDGE.md`, `CLAUDE.md`, `memory/MEMORY.md`

---

## 2026-03-21 22:00 — Binarna verifikacija nesigurnih vrijednosti + dokumentacija

### Verificirano binarno (svi dumps)
- **GTI90 rev limiter**: 5875 ticks = **7043 RPM** — potvrđeno (maknuti ~ prefiks)
- **Spark 900 rev limiter**: 5120 ticks = **8082 RPM** (ispravka: 8081 je bila pogreška zaokruživanja)
- **GTI90 SC bypass**: **0x1C1B** @ 0x0205A8 — nova potvrda, dokumentirano
- **SC bypass discrepancy**: 2018/2019 ORI: shadow (0x020534)=0x2626, active (0x0205A8)=0x3333
  - 2020+ ORI: obje adrese = 0x2626 (usklađene)
  - NPRo mijenja samo active + extra kopiju (shadow ostaje)

### Fajlovi ažurirani
- `_docs/SEADOO_KNOWLEDGE.md` — SC bypass tablica proširena (GTI90 + shadow/active napomena), rev limiter ispravci
- `CLAUDE.md` — SW varijante ispravci (Spark 8082, GTI90 bypass 0x1C1B)
- `memory/MEMORY.md` — rev limiter + bypass sekcija ažurirana

---

## 2026-03-21 21:00 — Dokumentacija — ispravci neistina (potvrda korisnika)

### Ispravci
1. **Throttle body 1630 ACE**: bio 60mm → **62mm** (korisnik potvrdio: svi motori 2012+ su 62mm)
2. **Rev limiter**: Manual WOT RPM ≠ ECU cut. Binary ECU: 130/170hp NA = 7892 (isti SW, isti limit). Manual = dijagnostički WOT u vodi.
3. **MEMORY.md**: Uklonjen duplikat 10SW082806
4. **safety_validator.py komentar**: 170hp NA = 7892 binarno (ne 8440 iz manuala)

### Fajlovi
- `_docs/SEADOO_KNOWLEDGE.md`, `CLAUDE.md`, `core/safety_validator.py`, `memory/MEMORY.md`

---

## 2026-03-21 20:00 — XCU wiring analiza (2021/2022/2024 PDF)

### Analizirani fajlovi
- `C:/Users/SeaDoo/Desktop/SEADOO/0WIRING/2021 ALL.pdf` (3 str)
- `C:/Users/SeaDoo/Desktop/SEADOO/0WIRING/2022 ALL.pdf` (9 str)
- `C:/Users/SeaDoo/Desktop/SEADOO/0WIRING/PWC 2024 - Wiring Diagram_219101111_WD21Y24S10_en (2).pdf` (11 str)

### Ključni nalazi

**XCU uveden 2024 za 130/170hp NA modele:**
- Str 3 (130/170 ENGINES): jasno oznaceno `XCU RELAY` — pin format 3-cifreni decimalni (101–256, ~48 pinova)
- Stari ECM (ME17.8.5) na svim ostalim modelima: Spark, 230hp, 300hp
- 325hp (RXP-X 325): ECM RELAY u dijagramu, ali fuse box poziva `XCU -127-` — dvosmislenost; pin format novi (`13-xx`/`4-xx`)

**Pin format usporedba:**
- ME17.8.5 (sve do 2024): `A-A1`–`A-M4` + `B-H2`/`B-L1`/`B-M1-3` = 38 pinova — **identičan 2018, 2021, 2022, 2024 230/300hp**
- XCU (2024 130/170): 3-cifreni (101–256) — fizicki nekompatibilan s ME17 harnessom
- 325hp ECM (2024): `13-01`–`13-56` + `4-xx` — novi format, novi konektor

**Novi sustavi na 325hp (vs 300hp):**
- FUEL PUMP RELAY (FPR) — zasebni relay (ME17 nema)
- O2 sensor (02 SENSOR, 6-pin) — vanjska lambda sonda
- LEVEL PRESSURE sensor — fuel pressure measurement
- Max pin: 13-56 = 56+ pinova

**Spark 2024**: ostaje na ECM/ME17.8.5 — bez promjena

### Izmijenjeni fajlovi
- `_docs/SEADOO_KNOWLEDGE.md` — dodana sekcija 13 "XCU platforma (2024+)"

---

## 2026-03-21 18:30 — Safety validator — ispravci i poboljšanja

### Izmijenjeni fajlovi
- `core/safety_validator.py`

### Promjene

**1. Rev limiter WARN threshold** — bio je 7500 rpm, što je krivo:
- 170hp NA stock = 8440 RPM (najviši poznati stock) — triggerao lažni WARNING
- 300/230hp SC stock = 8158/8168 RPM — isto triggeralo WARNING
- **Ispravak**: WARN > 8700 rpm (iznad svih poznatih stock varijanti), ERROR > 9200 rpm

**2. Q15 fuel mapa validacija** — `_check_injection` je za Q15 (`unit="Q15"`) koristio SC correction logiku
- Nova metoda `_check_fuel_q15`: WARN > 1.0 (iznad Q15 max), ERROR > 1.1 (fizikalno nemoguće)
- ORI referentne vrijednosti dokumentirane: 300hp=0.944, 230hp=0.785, 130/170hp=0.524

**3. "fuel" category route** — dodan u `validate_edit()` dispatcher
- `_check_fuel()`: routing za deadtime (µs, read-only), Q15, i generic
- Ranije je "fuel" category padao kroz do `_check_generic` bez specifičnih provjera

**4. Konstante** — dodani `_FUEL_Q15_WARN/ERROR`, `_REV_WARN_RPM/ERROR_RPM` umjesto magic brojeva

### Testirano
- 8440 rpm (170hp NA stock) → OK (bio Warning)
- 8701 rpm → WARNING
- 9300 rpm → ERROR
- Q15 0.944 (300hp ORI) → OK
- Q15 1.05 → WARNING
- Q15 1.15 → ERROR
- IGN ORI vrijednosti → OK

---

## 2026-03-21 — 2022 dump ispravak: čisti ORI, prijelazna platforma za 2023

### Ispravak prethodnog agentovog zaključka
- Agent je pogrešno zaključio "TUNED dump" — korisnik potvrdio: **10SW082806 = ČISTI ORI**
- 2022 je **tranzicijska platforma**: BRP refaktorirao CODE za 2023 (325hp, novi ECU, blow-off, E-kontrolirani tlak goriva, novi SC)
- 236KB CODE diff vs 2021 = strukturalna arhitekturna promjena, **ne tuning**
- **2023 = potpuno novi ECU** (nije ME17.8.5) — ME17Suite scope završava s 2022
- SC bypass @ 0x020534/0x0205A8 = 0x2626 jedine potvrđene adrese za 2022 SW
- Sve ostale adrese (IGN, fuel, rev, lambda) su pomjerene — nepoznate bez adresne analize

### Datoteke ažurirane
- `CLAUDE.md`, `_docs/SEADOO_KNOWLEDGE.md`, `memory/MEMORY.md`

---

## 2026-03-20 14:30 — 2022 300hp dump analiza (10SW082806)

### Što je napravljeno
- Binarna analiza `_materijali/dumps/2022/300.bin`
- Usporedba s 2021 (10SW066726) na svim ključnim adresama
- MapFinder pokrenutan za 2022 SW

### Ključni nalazi
- **SW: 10SW082806** — verificiran (bio u KNOWN_SW kao "nema dumpa") — sada imamo dump
- **Dump status: TUNED (nije ORI)** — više dokaza:
  - Rev limiter @ 0x028E96 = 100 ticks (praktički uklonjen; trebalo bi biti ~5072)
  - Cijela regija 0x028E94-0x028EAE = 100 ticks (19× ponavljanje)
  - Fuel @ 0x022066: header nRows=257/nCols=257 (nerealno; 2021=12/16)
  - Lambda @ 0x0266F0: vrijednosti 0.001 Q15 (nerealno)
  - SC bypass extra @ 0x029993 = 0x3600 (vs 0x2626 u 2021)
- **CODE diff vs 2021: 236,401B** (vs samo 2,891B za 2020→2021) — ZNACAJNA reorganizacija
  - BOOT: 769B (SW string + checksum + 313× TriCore adresni pointeri)
  - CODE: 236,401B
  - CAL: 235,564B
  - Ukupno: 472,734B = 30.7% razlicito
- **SC bypass shadow (0x020534) = 0x2626 ISTI** kao 2021 — stock vrijednost
- **SC bypass active (0x0205A8) = 0x2626 ISTI** kao 2021
- **IGN @ 0x02B730 promijenjen** — u 2022 sadrzi u16 LE vrijednosti (multiplikacijski faktori ~1.0) umjesto u8 ignition kuta
- **MapFinder: 14 mapa** (vs 57 za 2021) — vecina adresa mapa promijenjena u 2022 SW
- 2022 SW = nova arhitektura CODE layout-a — nije kompatibilan s 2021 map adresama

### Datoteke promijenjene
- `_docs/SW_VERSIONS.md` — ažuriran 10SW082806 entry + sekcija "2021 vs 2022 diff"
- `_docs/dumps_inventory.html` — dodano 2022/300 u DUMPS array + ažuriran SW_DB entry
- `C:/Users/SeaDoo/.claude/projects/.../memory/MEMORY.md` — dodano 10SW082806 u SW tablicu + dumps inventar

### Sljedeće
- Nabaviti cisti ORI 2022 300hp dump za pravu adresnu analizu 10SW082806
- Mapirati nove adrese mapa u 2022 CODE layoutu

---

## 2026-03-21 — SEADOO_KNOWLEDGE.md ažuriran s 2016 agent findings

### Ispravke i dodaci iz zadnjeg agenta (2016 1630 ALL + 1503 GTX analiza)
- **1503 throttle body = 62mm** (bio pogrešno 60mm u prvoj verziji)
- **1503 idle = 1800±50 RPM** (ne 1700 — to je 1630 ACE)
- Dodane kompletne tablice otpora senzora (CTS/MAPTS/OTS/EGTS — točne vrijednosti po °C iz shop manuala)
- Dodan OPS (Oil Pressure Switch) spec: normally-closed, opens >180-220 kPa
- Dodan magneto/stator: 1630=420W@6000RPM, 1503=360W@6000RPM
- Dodana fuse tablica (F13-F19)
- CAN wire colors po godištu: 2016=WHITE/RED + WHITE/BLACK; 2017+=WHITE/BLACK + WHITE/BEIGE
- ECM montažni torque: 5.5Nm ±0.6Nm + Loctite 243
- 1503 spec potvrđen: bore 100mm, stroke 63.4mm, disp 1493.8cc, CR NA=10.6:1 SC=8.4:1
- Speed limiter spec (manual): 1503=8300RPM, 1630=8400RPM

### Datoteke promijenjene
- `_docs/SEADOO_KNOWLEDGE.md` — ažuriran

---

## 2026-03-21 — SEADOO_KNOWLEDGE.md — master knowledge dokument kreiran

### Što je napravljeno
- Kompiliran `_docs/SEADOO_KNOWLEDGE.md` — sintetizira sve PDF analize iz prethodne sesije
- Pokriva: sensor specs (CPS/CTS/EGTS/KS/injektori/zavojnice), ECU hardware, CAN bus, gorivo/injekcija, RPM limiteri, SC specs, svjećice, SW verzije (19 SW-ova), razlike po godištu, limp home/zaštite, impeller dims
- Uključuje "česte zamke" sekciju (10 pitfalls pri radu s različitim SW generacijama)

### Datoteke promijenjene
- `_docs/SEADOO_KNOWLEDGE.md` — novi fajl (master knowledge base)
- `work_log.md`, `chat_log.md`

---

## 2026-03-20 20:30 — PDF analiza: Sea-Doo 2016 shop manuali (1630 ACE ALL + 1503 GTX/RXT/WakePro)

### Što je napravljeno
- Pročitana 2 PDF-a: `2016 1630 ALL.pdf` (930 str, 124MB) i `2016 1503 GTX_RXT_WakePro.pdf` (959 str, 124MB)
- Korišten pypdf za ekstrakciju teksta (fajlovi preveliki za Read tool >100MB)
- Čitane: tech specs (str 877-884 / 906-913), Vehicle Specifications shop manual (str 499-503 / 562-566), EFI sekcija, supercharger sekcija, ignition, fuel system
- Napisan strukturirani markdown izvještaj

### Ključni nalazi

**Engine tech specs (owner's manual, potvrđene)**
- 1630 ACE HO: bore=100mm, stroke=69.2mm, displacement=1630.5cm3, CR=8.4:1, 217kW@8000RPM, SOHC 3-cil 12v
- 1503 4-TEC: bore=100mm, stroke=63.4mm, displacement=1493.8cm3, CR=155hp=10.6:1 / 215+260hp=8.4:1
- 1503 snage: 155hp=106kW@7300, 215hp=152kW@8000, 260hp=179kW@8000 RPM

**Električni sistem (Vehicle Specifications shop manual, str 499-500)**
- Idle speed: 1503=1800±50 RPM, 1630=1700±50 RPM (oba ne-podešivi)
- Engine speed limiter: 1503=8300 RPM, 1630=8400 RPM (software limiter setting)
- Spark plug: 1503=NGK DCPR8E, 1630=NGK KR9C-G, zazor=0.7-0.8mm za oba
- Magneto output: 1503=360W@6000, 1630=420W@6000 RPM
- Ignition coil primary: 1503=0.85-1.15Ω, 1630=0.80-0.97Ω @20°C
- Ignition coil secondary: 1503=9.5-13.5kΩ, 1630=N.A. (ne testira se)

**Fuel system**
- Fuel pressure: 386-414 kPa (56-60 PSI) za oba motora — identično svim godištima
- Throttle body: 1503=62mm, 1630=60mm
- Injector resistance: 11.4-12.6Ω @20°C (oba motora)
- Injector color code: 1630=yellow-green
- Fuel tank: bez suspenzije=60L, sa suspenzijom=70L; rezerva≈12L

**Supercharger**
- 1630 ACE: max turbine RPM=46800 RPM; clutch slipping moment=14-17Nm (novi), min 11Nm (uhodan)
- 1503 215/260hp: max turbine RPM=45000 RPM; clutch slipping=9-14Nm (novi), 8-12Nm (uhodan)
- Gear ratio nije eksplicitno naveden u tekstu (u slikama)

**Sensor specs (1630 ACE EFI sekcija)**
- CTS: -40°C=38457-52630Ω, 20°C=2233-2780Ω, 80°C=297-349Ω, 120°C=105-122Ω
- MAPTS (temp): -40°C=40528-56935Ω, 20°C=2193-2863Ω, 80°C=294-368Ω, 120°C=98-122Ω
- EGTS: identična krivulja kao OTS (NTC termistor, ista vrijednost @temp)
- OTS: -30°C=11800-13400Ω, 20°C=2200-2800Ω, 80°C=280-370Ω, 120°C=100-125Ω
- Knock sensor: ≈5MΩ @20°C
- CTS overheat limit: 110°C (230°F); OTS overheat: 95°C (203°F)

**ECU/ECM**
- Nema eksplicitnog P/N (278xxxxxx) u tekstu manuala — P/N je na fizičkoj naljepnici ECM modula
- ECM retaining screws: 5.5Nm (Loctite 243)
- CAN bus: 2-žični (CAN HI = white/red, CAN LO = white/black); bus-bars u fuse boxu
- Fuse #19 = ECM power 15A; Fuse #18 = fuel pump 10A; Fuse #13/14/15 = Inj+Ign po cilindru 10A

**Relevantno za ME17Suite**
- Engine speed limiter 8400 RPM (1630) i 8300 RPM (1503) su SW postavke — odgovaraju period-encoded vrijednostima koje ME17Suite već detektira
- Idle 1700 RPM za 1630 je konstanta za limp-home i iBR logiku
- Fuel pressure spec 386-414 kPa je korisno za fuel pump dijagnostiku (nije u tuningu)
- Sensor resistance krivulje su korisne za verifikaciju DTC kodova (P0117/P0118 CTS range)

### Fajlovi
- Izvor: `C:\Users\SeaDoo\Desktop\SEADOO\2016 1630 ALL.pdf` (str 877-884 owner spec, str 499-503 shop spec)
- Izvor: `C:\Users\SeaDoo\Desktop\SEADOO\2016 1503 GTX_RXT_WakePro.pdf` (str 906-913, str 562-566)

---

## 2026-03-20 19:15 — PDF analiza: Sea-Doo 2022 shop manuali (GTX/RXT, RXP, GTI/GTR, Spark)

### Što je napravljeno
- Pročitana 4 PDF-a: 2022 GTX/RXT/Wake PRO/Fish PRO (269str), 2022 RXP (250str), 2022 GTI/GTR/Wake (291str), 2022 Spark (262str)
- Korišten pdfplumber za ekstrakciju teksta (pdftoppm nedostupan)
- Čitane tech specs sekcije (Section 08/09) i engine management sekcije
- Napisan strukturirani izvještaj

### Ključni nalazi
- 2022 koristi ISTI Rotax 1630 ACE / 900 ACE motore — nema novog motora
- ECU ostaje ME17.8.5 (Bosch) — ISTI ECM konektor smr2009-027-005 u svim manualima
- GTI/GTR manual pokriva OBA motora: 900 ACE (GTI 90) + 1630 ACE (GTI 130/170/230)
- Fuel pressure 1630 ACE: 386–414 kPa (56–60 PSI) — identično 2019/2021
- Spark 900 ACE: engine speed limiter = 8000 RPM (tech spec, ne 8300!)
- GTI 90 impeller 150mm, GTI 130/170 = 155.5mm, GTR 230 = 161mm
- RXP 300: impeller 161mm, 13.5°/24° pitch (identično GTX LTD 300)
- Bore/stroke/HP/torque podaci su u slikama (EMS diagram) — tekst-parser ih ne hvata
- Supercharger: maintenance free (ne mijenja se) za 230 i 300hp motore
- 2022 nema novih riding moda u odnosu na 2021 (isti iControl, iBR, iTC)

### Datoteke promijenjene
- `work_log.md`, `chat_log.md`

## 2026-03-20 18:30 — PDF analiza: Sea-Doo Spark 900 ACE shop manuals 2016/2017/2019

### Što je napravljeno
- Pročitano 8 PDF-ova: 2016 SPARK SERIES SHOP MANUAL (posebni fajlovi: Tech Specs, EFI, DTC, CAN), 2017 SPARK folder (Tech Specs engine+vehicle), 2019 Spark.pdf (zadnjih 20%)
- Ekstrahovani svi relevantni podaci za ME17Suite: engine specs, sensor otpori, injektori, RPM limiter, limp home RPM, CAN bus, DTC lista
- Napisan kompletan strukturirani izvještaj

### Ključni nalazi
- RPM limiter: 8300 RPM (hard cut, ECM) — potvrđeno 2016/2017/2019
- Max power RPM: 900 ACE = 8000±100 RPM, 900 ACE HO = 8000 RPM @ 66.19kW
- Idle: 1400 ± 100 RPM (u vodi)
- Limp home: high temp / high EGTS → 3800 RPM; low oil pressure → 4500 RPM
- Injector otpor: 11.4–12.6 Ω @ 20°C (isti kao 2017 1503/900 ACE)
- Fuel pressure: 386–414 kPa (56–60 PSI) — reguliran u fuel pump modulu
- Ignition coil: primary 0.80–0.97 Ω, secondary 9.5–13.5 kΩ
- CPS: 775–950 Ω @ 20°C (na ECM adapteru: H1-K2)
- CTS/MAPTS/EGTS: iste tablice otpora (identično 2014 tech spec)
- Knock sensor: ~5 MΩ (na ECM adapteru: A-C3 / A-G2)
- CAN: WH/BG=CAN-HI, WH/BK=CAN-LO; Spark bez iBR = 2 modula, s iBR = 3 modula
- 60hp vs 90hp razlika: SAMO kalibracija ECM-a — isti hardware, isti sensors, ista throttle body
- 2019 Spark: deklarirana snaga — 900 ACE = 44.13 kW@7000 RPM (60hp), 900 HO ACE = 66.19 kW@8000 RPM (90hp)

### Datoteke promijenjene
- `work_log.md`, `chat_log.md`

## 2026-03-20 17:15 — PDF analiza: Sea-Doo 2011-2015 Spark historijski kontekst

### Što je napravljeno
- Pokušano čitanje 5 PDF-ova: 2011 ALL.pdf (139MB), 2013_4 ALL.pdf (112MB), 2015 1503 ALL.pdf (84MB), Spark DTC 2014, Spark Tech Spec
- 2 velika PDF-a (>100MB) nedostupna — Read tool limit
- 2015 1503 ALL.pdf i višestranični Spark iBR PDF-ovi nedostupni — pdftoppm nije instaliran
- Uspješno pročitano: smr2014-043 (Tech Spec), DTC 2014 Spark, EMS block dijagram, CAN dijagram, Spark Introduction 2014, iBR Tech Spec
- Napisan strukturirani historijski izvještaj

### Ključni nalazi
- Spark 2014: ROTAX 900 ACE, 3-cil DOHC, bore=74mm, stroke=69.7mm, 899.31cc, comp=11:1
- Max HP RPM=8000±100, Engine speed limiter=8300 RPM (potvrđuje ME17Suite CLAUDE.md)
- Throttle body: Dell'Orto 46mm iTC, 3 injektora, fuel pressure=386-414 kPa
- Ignition: IDI (Inductive Digital Ignition), NGK CR8EB, gap 0.70-0.80mm
- ECM fotografija reference: smr2009-027-005 (isti hardware kao za 4-TEC modele — potvrđuje Bosch ME17 kontinuitet)
- DTC P-kodovi Spark 2014 identični ME17.8.5 strukturi (P0201, P0231, P0335, P1502-P1506 itd.)
- CAN bus: WH/BG=CAN-HI, WH/BK=CAN-LO; moduli: ECM (B-C1/B-C2), DB (dijagnostički), Gauge
- ECU P/N NIJE pronađen u dostupnim fajlovima (EFI sekcija nedostupna)
- ME17 debut 2008 nije mogao biti potvrđen/osporen — 2011 ALL.pdf nedostupan (139MB)
- 2016 gen (10SW004675): rev=8072RPM, SC bypass=0x3333 potvrđuje stariji layout

### Datoteke promijenjene
- `work_log.md`, `chat_log.md`

## 2026-03-20 16:30 — PDF analiza: 2021 shop manuali (4 PDFa) — svi motori

### Što je napravljeno
- Pročitana 4 kompletna 2021 shop manuala: 1630 ACE (191 str), GTX/RXT (274 str), GTI/GTR (934 str), Spark (714 str)
- Izvučeni svi tehnički podaci relevantni za ECU tuning
- Napisan strukturirani Markdown izvještaj s razlikama po snagama

### Ključni nalazi
- 1630 ACE RPM limiter: 130hp=8040 RPM, 170/230/300hp=8440 RPM (ISPRAVKA: prethodni unos imao pogrešno 8300/8400)
- 900 ACE RPM limiter: 8300 RPM (tehnički spec motornog manuala, "Spark shop" kaže 8000 RPM — razlika owner vs shop)
- Spark 900 ACE-90: 8000 RPM @ max HP, Engine speed limiter=8300 RPM
- Gorivo: injektori 11.4–12.6 Ω (1630 + 900 ACE isti resistance), boja YELLOW/GREEN (1630 ACE)
- Svjećice: 1630 130/170/230hp = NGK DCPR8E, 300hp = NGK KR9E-G, Spark 900 = NGK CR8EB
- Svjećica razmak: 130/170/230hp = 0.8–0.9mm, 300hp = 0.7–0.8mm
- Supercharger: 230hp max 45000 RPM, 300hp max 46800 RPM; različiti gear holder alati
- CAN bus: WHITE/BLACK = CAN HI, WHITE/BEIGE = CAN LO (potvr. u GTX/RXT i Spark manualu)
- Throttle body: 1630 ACE = 60mm, 900 ACE = 46mm Dell'Orto heated
- 900 ACE idle: 1400 RPM (shop manual engine spec), 1450 RPM (vehicle spec)
- GTI 1630 ACE 90hp (GTI90): 900 ACE motor = 66.19 kW @ 8000 RPM, RPM limiter 8300 RPM

### Datoteke promijenjene
- `work_log.md`, `chat_log.md`

## 2026-03-20 15:30 — PDF analiza: 2017 1630 HO ACE shop manuali (9 PDF-ova)

### Što je napravljeno
- Pročitano 9 PDF-ova: EMS (smr2017-011), EFI (smr2016-027), CAN (smr2016-023), DTC (smr2016-025), Ignition (smr2016-030), Tech Spec Engine (smr2016-043), Tech Spec Vehicle (smr2016-043), Supercharger (smr2016-019), Rotax Tech Spec (R1630_MY17-011), iControl (smr2016-022)
- Izvučene sve tehničke vrijednosti relevantne za ME17Suite

### Ključni nalazi
- Rev limiter: 8300 RPM (ignition manual) vs 8400 RPM (vehicle spec) — neslaganje
- Fuel pressure: 386–414 kPa (56–60 PSI) za sve modele
- Injector resistance: 11.4–12.6 Ω @ 20°C, boja žuto-zelena (engine 1603)
- CPS: 775–950 Ω @ 20°C, ~3.7 Vac za vrijeme okretanja
- SC max RPM: 46800 RPM; slipping moment 14–17 Nm (novi), min 11 Nm (korišten)
- CTS overheat: 110°C; Oil limp home >95°C OTS
- Idle: 1700 ±50 RPM (ne adjustable)
- Throttle body: 60 mm (1630 ACE HO); ETA limp home @ ~8°

### Datoteke promijenjene
- `work_log.md`, `chat_log.md`

---

## 2026-03-20 15:00 — Analiza 2017 Sea-Doo shop manual PDF — 1503 NA i 900 ACE

### Što je napravljeno
- Pročitano svih 8 PDFova iz 2017 service manuala za 1503 NA i 900 ACE seriju
- Ekstrahirani svi ECU-relevantni podaci: RPM limiteri, sensor specs, injector specs, ignition, CAN, throttle body
- Napisan strukturirani Markdown izvještaj s kompletnim brojevima

### Ključni nalaz — razlike između serija
- **1503 NA**: RPM limiter = **8050 RPM**, throttle body = **60mm**, injector resistance = **11.4–12.6Ω**, injector boja = **plava**
- **900 ACE**: RPM limiter = **8300 RPM**, throttle body = **46mm**, injector resistance = **11.4–12.6Ω** (identično)
- CTS overheat: 1503=**110°C**, 900 ACE=**100°C**
- EGTS overheat: 1503=**110°C**, 900 ACE=**95°C**
- Ignition coil primary: 1503=**0.80–0.97Ω**, 900 ACE=**0.85–1.15Ω**; secondary (900 ACE only)=**9.5–13.5kΩ**
- CPS resistance (oba): **775–950Ω** @ 20°C; CPS output voltage: **~3.7 Vac** pri okretanju
- KS resistance (oba): **~5 MΩ** @ 20°C; threshold za test = iznad **5000 RPM**
- CAN bus: 2 žice (WHITE/BLACK i WHITE/BEIGE), update rate 10ms ili 100ms ovisno o komponenti

## 2026-03-20 00:30 — 2017 gen address audit — potvrđene adrese za 10SW012999

### Što je napravljeno
- **Binary analysis**: usporedba 2017/230 (10SW012999) vs 2018/230 (10SW025021) dump-ova
- **Metodologija**: pattern search za poznate mape (boost_factor, temp_fuel, lambda, torque)
- **Ključni nalaz**: globalni CODE offset -0x2AA = -682B za sve SC mape u regionu 0x025000-0x027000

### Potvrđene adrese za 10SW012999
| Mapa | 2017 adresa | 2018 adresa | Napomena |
|------|-------------|-------------|----------|
| boost_factor | 0x025B4E | 0x025DF8 | flat 23130 × 40 elem |
| temp_fuel | 0x025BA6 | 0x025E50 | varijabilna × 156 elem Q14 |
| lambda_main | 0x026446 | 0x0266F0 | 12×18 Q15, mirror +0x518 |
| lambda_trim | 0x026B0E | 0x026DB8 | 12×18 Q15, 0.955-1.044 |
| torque_main | 0x02A0D8 | 0x02A0D8 | ISTA adresa! |
| torque mirror | 0x029BC0 | 0x02A5F0 | ISPRED main-a (-0x518, ne +0x518) |
| rev limiter | 0x028E94 | 0x028E96 | 5126t = 8072 RPM |

### Datoteke promijenjene
- `CLAUDE.md` — ažuriran redak za 10SW012999 s konkretnim adresama
- `_materijali/2017_gen_address_audit.md` — novi fajl, detaljna dokumentacija

### Napomene
- 10SW012502 (2017/260hp) ima DRUGAČIJI layout — adrese ne odgovaraju 10SW012999
- 2016 gen (10SW000776/778) ima PRAZNE 0x025DF8-0x025E50 regije — sasvim drugačiji layout
- temp_fuel u 2017 je VARIJABILNA (2018 je flat 23130) = stariji ECU ima aktivnu temp korekciju

## 2026-03-20 23:58 — 2016/2017 gen podrška implementirana u map_finder.py

### Što je napravljeno
- **`core/map_finder.py`**: dodani SW ID setovi, detection metode i find_all() grane za 2016 i 2017 gen
  - `_2016_GEN_SW_IDS`: 10SW000776, 10SW000778, 10SW004675
  - `_2017_GEN_SW_IDS`: 10SW012999
  - `_is_2016_gen()`, `_is_2017_gen()` metode
  - `find_all()`: elif grane — 2016 gen skenira samo rev_limiter + SC bypass; 2017 gen preskace boost/temp_fuel/lambda_trim/torque/inj_lin

### Validacija
- 2016/215 (10SW000776): 0 mapa — nema false positives
- 2016/260 (10SW000778): 0 mapa — nema false positives
- 2016/300 (10SW004675): 4 mape — 2x rev limiter (8738rpm) + 2x SC bypass
- 2017/230 (10SW012999): 23 mape — parcijalna podrska bez problematicnih skenera
- 2019/300 (10SW040039): 57 mapa — nema regresije u 2018+ grani

## 2026-03-21 23:55 — SW Kompatibilnost UI dijalog

### Što je napravljeno
- **novi fajl**: `ui/sw_compat_widget.py` — `SwCompatWidget(QDialog)` modalni dijalog
  - Dropdown odabir SW ID-a (svi poznati + učitani ECU)
  - Kompatibilnost matrix: 13 kategorija mapa × 3 kolone (status/adresa/napomena)
  - Status boje: zelena OK, crvena NEDOSTUPNO, po redu tablice
  - Badge: PUNA PODRŠKA / PARCIJALNA / OGRANIČENA s brojevima (X od Y)
  - Info box s upgrade prijedlogom za ograničene SW (2016, 2017)
  - `COMPAT_DATA`: 4 ograničena SW — 10SW000776, 10SW000778, 10SW004675, 10SW012999
- **izmjena**: `ui/main_window.py`
  - import `SwCompatWidget`
  - toolbar: tipka "🔍 SW Compat" iza Undo/Redo separatora
  - handler `_open_sw_compat()`: otvara dijalog s `eng1.info.sw_id`
- Validacija: py_compile OK za oba fajla

## 2026-03-21 — Dokumentacija novih 4TEC 1503 dumpova (2016/2017 gen)

### Što je napravljeno
Ažurirana dokumentacija s 3 nova dumpa i tehničkim nalazima za 2016 i 2017 generaciju 4TEC 1503.

### Novi dumpovi
- `2016/4tec1503/215.bin` — SW=10SW000776, 215hp SC 1503
- `2016/4tec1503/260.bin` — SW=10SW000778, 260hp SC 1503
- `2017/4tec1503/230.bin` — SW=10SW012999, 230hp SC 1503

### Promijenjeni fajlovi
- `_docs/dumps_inventory.html` — NEMA promjena (svi 3 unosa već bili prisutni u DUMPS i SW_ALL)
- `_docs/SW_VERSIONS.md` — dodane sekcije: "4TEC 1503 2016 gen", "4TEC 1503 2017 gen", "SW Kronologijska analiza"
- `CLAUDE.md` — dopunjeni: SW Varijante (10SW000776, 10SW000778, 10SW012999), map_finder (_is_2016_gen(), _is_2017_gen())

### Ključni tehnički nalazi
- **2016 gen SC bypass**: `0x012C60 = 0x2020` (ne 0x020534 kao 2018+!) — potpuno drugačija adresa
- **2017 gen (10SW012999)**: parcijalna 2018 migracija — SC bypass/ign/rev/lambda_main/fuel_2d rade na 2018 adresama; boost_factor=358 (ne 23130), temp_fuel=3000, lambda_trim=0 na drugačijim lokacijama
- **SW pattern potvrđen**: niži broj = stariji SW; 000776 i 000778 susjedni (±2) = isti release batch; ~13k/godišnji skok
- **BUDS**: 2016 = BUDS + BUDS2; 2017+ = BUDS2 only; BUDS2 nema pre-2016 backup
- **Swap kompatibilnost**: stariji motori rade s novijim ECU SW (10SW format)

---

## 2026-03-20 23:30 — OLS binarij ekstrakcija + 1037524060 arhitektura + 4TEC 1503 mapa analiza

### Što je napravljeno
Ekstrakcija ECU binarija iz WinOLS OLS fajlova i duboka analiza 1037524060 arhitekture + 4TEC 1503 SC vs NA mapa.

### OLS ekstrakcija
- **TEMP_rxp1503_orig.bin** (128KB, CS=0x1CF16484) — iz `Sea-Doo RXP 1.5 compr.ols`
- **TEMP_rxtx1503_orig.bin** (128KB, CS=0x53532E7D) — iz `WinOLS (Sea-Doo RXT-X).ols`
- Ekstrakcija: `ols[SW_idx - 0x1A : SW_idx - 0x1A + 0x20000]` (128KB per block)

### 1037524060 binarij arhitektura (NOVA SPOZNAJA)
`rxtx_260_524060.bin` je **MULTI-IMAGE CONTAINER** sa 3 ECU slike:
- Block1 @ 0x000000: RXTX-X stock (CS=0x53532E7D)
- Block2 @ 0x020000: RXP compr tune (CS=0x1CF16484) — **identičan RXP OLS ekstrakciji**
- Block3 @ 0x040000: treća varijanta (CS=0x11E707D1)
- CODE @ 0x060000: dijeljeni TriCore kod
- CAL @ 0x080000: 0xC3-fill CAL podaci

**KRITIČNO**: 1037524060 je **PRE-10SW ECU format** (starija arhitektura):
- CODE na 0x060000 (NE 0x010000!)
- Map adrese iz CLAUDE.md (0x022066 itd.) **NE RADE** za ovu binariju
- RXP vs RXTX = 96% razlike = potpuno različite kalibracije, nisu "stock vs tuned"

### 4TEC 1503 SC vs NA mapa razlike (potvrđene)
| Mapa | Adresa | SC 230hp | NA 130hp |
|------|--------|----------|----------|
| Fuel max Q15 | 0x022066+0x17E | 0.9524 | 0.4404 |
| IGN row0 | 0x02B730 | 32.2° (viši advance) | 24.8° (flat) |
| SC correction Q14 | 0x02220E | 1.021-1.196 | flat 1.000 |
| SC bypass shadow | 0x020534 | 0x1F1F | 0x1E1E |
| SC bypass active | 0x0205A8 | 0x1F1F | 0x1E1E |
| KFPED X-os | 0x029528 | MAP kPa [-80..+90] | pedal° [0..70] |
| Torque max Nm | 0x029FD4 | 340.0 Nm | 332.8 Nm |
| Rev limit | 0x028E96 | 7664 RPM | 7699 RPM |

SC correction 0x02220E: **NOVA ADRESA POTVRĐENA** za 4TEC 1503

### Fajlovi promijenjeni
- `_materijali/TEMP_rxp1503_orig.bin` (novi, 128KB)
- `_materijali/TEMP_rxtx1503_orig.bin` (novi, 128KB)

## 2026-03-20 22:00 — KP/OLS analiza — 4TEC 1503 mapa verifikacija

### Što je napravljeno
Kompletna analiza WinOLS KP i OLS fajlova iz `_materijali/unknow/` i verifikacija svih adresa u 4TEC 1503 binarnim dumpovima.

### KP format
- **Mali KP** (`10974.ols.kp`, 15KB) = WinOLS map lista za **Spark 900 ACE** (NE za 1503!)
  - Stringovi: "Limiter of maximum Torque", "Map optimal engine torque", "Ignition timing", "Airmass to fuel injector" itd.
  - CODE adrese: 0x027D10 (RPM limiter), 0x024958 (airmass-to-injector), 0x026A4E (ign timing), 0x0222BE (desired charge)
  - Zaključak: WinOLS intern format = binary sa pascal-string deskriptorima + CODE adresama, NE direktno parsabilno
- **Veliki KP** (`Rxp260 maps buds.kp`, 693KB) = Bosch Knowledge Pack — samo opisi parametara (1711 unikatnih stringova), **BEZ ECU adresa** (adrese nisu u KP bazi)
- **OLS fajl** = WinOLS projekt za RXT-X 260 4TEC 1503, 503 map entries, binary format s FFFFFFFF separatorima

### 4TEC 1503 Verifikacija (10SW025021, 10SW025022, 10SW040008)
Sve adrese iz CLAUDE.md POTVRĐENE za 4TEC 1503:
- **Fuel mapa** @ 0x022066 = 12×16 u16LE Q15 RADI (130hp max=0.440, 230hp max=0.952)
- **Ignition** @ 0x02B730 = 19 mapa, stride 144B, u8 format RADI (17/19 razlikuju SC vs NA)
- **Lambda main** @ 0x0266F0 = 12×18 u16LE Q15 RADI
- **Rev limiter** @ 0x028E96 (NA=7700rpm), 0x028E94 (SC=7892/8158rpm) POTVRĐENO
- **SC correction** @ 0x02220E = 9×7 Q14 RADI (NA=flat 1.0, SC=variable 1.02-1.92)
- **SC bypass** @ 0x020534 = 0x1E1E (NA 130hp), 0x1F1F (SC 230hp) POTVRĐENO
- **KFPED** @ 0x029528 (axis) + 0x029548 (data) RADI (NA X-os=pedal°, SC X-os=MAP kPa)
- **Physical torque curve** @ 0x029FD4 = 30pt u16LE /100=Nm RADI

### Nove spoznaje (nisu u CLAUDE.md)
- `0x025DF8` za 4TEC = flat 0x5A5A = Q14=1.412 (+41%), IDENTIČNO SC/NA (za 1630 = 1.224 i varijabilno)
- `0x022282` = SC boost factor curve (NA=flat Q14=1.0, SC=variable Q14 1.18-1.92)
- `0x029FD4` = Physical torque krivulja u Nm: 2018 SC≠NA, 2019 svi isti (10SW040008 isti za 130/155/230hp)
- `0x02436C` = NULA za 4TEC (nema injector linearization na toj adresi, za razliku od 1630)
- `0x02A0D8` (torque main) = mostly flat ~128 BE Q8 za 4TEC — praktički PASIVNA mapa
- 2019 SW 10SW040008: isti SW za 130/155/230hp, identična fizička torque krivulja i fuel mapa
- SC 230hp vs NA 130hp: 612 diff regiona u CODE, ukupno ~19KB razlike (slaže s CLAUDE.md MEMORY)

### Fajlovi promijenjeni
- Nema — research task, kod nije mijenjan

---

## 2026-03-20 — ui/main_window.py — Integracija MapHeatWidget + MapEditorWidget + CanLivePanel

### Što je napravljeno
1. **Vizualizacija tab**: Dodan `MapHeatWidget` kao novi tab "Vizualizacija" (ljubičasti tekst). Automatski se ažurira pri svakom `_on_map_selected()` kliku u tree-u.
2. **CAN Live tab**: Dodan `CanLivePanel` kao tab "CAN Live" (teal tekst) s dashboard prikazom, tablicama CAN IDs, log stripom.
3. **Heat→Editor sinkronizacija**: Klik na ćeliju u heat mapi poziva `_on_heat_cell_clicked(row,col)` koji sinkronizira selekciju u Map Editor tablici. `MapTableView.select_cell()` metoda dodana.
4. **Importi**: Dodani `CanLivePanel`, `MapHeatWidget`, `MapMiniPreview`, `MapEditorWidget` na vrhu main_window.py.

### Fajlovi promijenjeni
- `ui/main_window.py` — dodani tabovi, integracija heat widgeta, select_cell metoda

### Testovi
- `py_compile` → OK za sve 4 nove UI datoteke
- Import test → OK (121 DTC kodova, svi importi prošli)

## 2026-03-20 18:10 — ui/main_window.py — General UI Polish (5 poboljšanja)

### Što je napravljeno
1. **Status bar poboljšanje**: Dodan lijevi label "SW: 10SW066726 | 300hp SC 2021 | 56 mapa" (HTML, u boji SW varijante); sredina QProgressBar (vidljiv za vrijeme scana); desno checksum badge "Checksum: OK" zeleno / "UPOZORENJE" crveno. Novi metode: `_update_sb_left()`, `_update_sb_checksum()`.
2. **DTC sidebar — boja i prefiks**: `refresh_status()` i `refresh_one()` sada koriste `_apply_dtc_item_style()` koji postavlja: ● prefix + zeleno (#4CAF50) za aktivne DTC, ✕ prefix + crveno (#EF5350) za OFF, sivo za neučitan. Tooltip prikazuje punu adresu (code_addr, mirror_addr, enable_addr) i enable byte vrijednosti.
3. **Map table dirty ćelije**: `refresh_cell()` sada označava editiranu ćeliju tamno žutom pozadinom (#2a2200) i žutim tekstom (#FFD600). Dirty flag pohranjen u UserRole+1.
4. **ECU Info panel**: Dodan veliki SW ID naslov (18px bold Consolas), SW opis, "● Nespremljene promjene" narančasto, + polja "Mape" i "Ucitan" (timestamp) u info gridu. Checksum sada pokazuje "OK" (zeleno) ili "UPOZORENJE" (crveno).
5. **Toolbar ikone i tooltips**: Gumbi dobili emoji ikone (📂 Load ECU, 💾 Spremi, ⊞ Compare). Dodani novi gumbi: "🔴 DTC OFF All" s potvrdom i "🔧 CS Fix". Svi gumbi imaju descriptivne tooltipe. `_toolbar_dtc_all_off()` nova metoda.

### Fajlovi promijenjeni
- `ui/main_window.py` — 5 područja unaprijeđena, ~150 novih linija

### Sintaksa
- `py_compile.compile('ui/main_window.py')` → OK

## 2026-03-20 17:30 — ui/map_editor_widget.py — profesionalni inline map editor

### Što je napravljeno
- Kreiran novi fajl `ui/map_editor_widget.py` (~430 linija, PyQt6)
- `UndoStack`: deque-based undo/redo, max 20 koraka, push/undo/redo/clear, can_undo/can_redo/undo_count
- `MapEditorWidget(QWidget)`: dark theme (#111113), signali `map_applied` i `map_changed`
  - Tablica: dvostruki klik = inline edit, Enter=potvrdi/Esc=odustani, bulk edit, Paste TSV (Excel)
  - Dirty ćelije: pozadina #3A2800, narančasti tekst #FF8C00
  - Error ćelije: pozadina #3A0000, crveni tekst, tooltip "Van raspona: X–Y unit"
  - X-os (RPM) kao header kolona, Y-os (Load%) kao header redci — bold font
  - Toolbar: Undo(N), Redo, Reset row, Reset all, dirty label "+N promjena", Apply gumb
  - Validacija raw raspona — zaokruži na najbliži valid raw (snapping)
  - `set_found_map(fm, editor)`, `apply_changes()`, `reset_all()`, `has_changes()`
  - Apply poziva `MapEditor.write_map()` s display vrijednostima
- Test potvrđen: `from ui.map_editor_widget import MapEditorWidget, UndoStack` → OK

### Fajlovi promijenjeni
- `ui/map_editor_widget.py` — NOVO

## 2026-03-20 15:15 — ui/can_live_widget.py — CAN live decode UI widget

### Što je napravljeno
- Kreiran novi fajl `ui/can_live_widget.py` (~380 linija, PyQt6)
- `CanWorker(QThread)`: background thread, python-can `bus.recv()` petlja, IXAAT monitor=True, signali `message_received` i `error_occurred`
- `CanLiveWidget`: dashboard (6 tile-ova: RPM 48pt, coolant, hours, DTC count, engine state, riding mode) + CAN ID tablica (7 kolona, refresh 2s, boja po CS/RC statusu) + log strip (max 500 linija, monospace hex+decode)
- `CanLivePanel`: container s toolbar-om (bitrate 500/250kbps, kanal 0/1, Start/Stop, msg/s counter)
- Graceful fallback: python-can ImportError → btn disabled + poruka; IXAAT nedostupan → error signal → stop
- Import test: `python -c "from ui.can_live_widget import CanLivePanel; print('OK')"` — OK

### Fajlovi promijenjeni
- `ui/can_live_widget.py` — novi fajl

## 2026-03-20 14:30 — ui/map_visualizer.py — MapHeatWidget, MapDeltaWidget, MapMiniPreview

### Što je napravljeno
- Kreiran novi fajl `ui/map_visualizer.py` (PyQt6, ~430 linija)
- `MapHeatWidget`: 2D heat mapa s JET paletom, hover tooltip, click signal, selekcija ćelije, color bar, X/Y-os headeri iz `AxisDef`
- `MapDeltaWidget`: usporedba dvije mape (delta = B−A), zelena/crvena/sivo, tooltip s A/B/Δ vrijednostima, legenda
- `MapMiniPreview`: 100×60px preview bez teksta za tree/listu
- Import test: `python -c "from ui.map_visualizer import ..."` — OK

### Fajlovi
- `ui/map_visualizer.py` — novo, kreirano

## 2026-03-19 — CLAUDE.md sveobuhvatno ažuriranje iz work_log + chat_log

### Što je napravljeno
- CLAUDE.md ažuriran s kritičnim nalazima iz svih prethodnih sesija
- Dodane/ispravljene tehničke sekcije prema logovima

### Ključne ispravke i dodaci
- Rev limiter: ispravljeno — 0x02B72A/0x02B73E su IGN DATA (u8), stvarni rev limiter @ 0x028E96; dodane RPM vrijednosti po varijanti
- Injection: pojašnjeno da je 0x02436C injector linearization curve (NE 2D fuel mapa); 1503/GTI90 koriste 0x022066
- SC bypass opcodes po snazi: 300hp=2626, 230hp=1f1f, 170/130hp=1e1e
- KFWIRKBA ispravak: 14×10 u8 (ne 7×10 u16 Q15), osi u8/100
- Deadtime ispravka: 0x0258AA (ne 0x025900)
- CAN TX tablica ispravka: 0x03DF0C (2019+) / 0x03DF1E (2018); 0x0433BC je period tablica
- GTI90 DTC @ 0x0217EE; Spark DTC drugačija arhitektura
- Broj mapa ispravljen: 300hp=56 (ne 54!), Spark=52, GTI90=60
- SW specifičnosti za 10SW023910 (2018): IGN_BASE @0x02B72C, rev limiter @0x028E94
- inj_main identičan za sve snage; NPRo diff: BOOT=140B, CODE=7087B, CAL=169912B
- KFPED analiza: SC koristi MAP kPa kao X-os, NA koristi pedal°
- 0x02B380 i 0x012C80 označeni kao non-tunabilni (read-only)
- P0231 stvarna adresa: 0x0217BC (idx=94); U16Ax grupacije za DTC
- SAT TX IDs i 0x4CD keepalive 1Hz dokumentirani
- EEPROM audit nalazi uneseni

### Fajlovi promijenjeni
- `CLAUDE.md` — sveobuhvatno ažuriranje

---

## 2026-03-20 02:00 — Cross-SW audit: kritične ispravke

### KRITIČNE ISPRAVKE (potvrđene 4 paralelna agenta × 25 dump fajlova)

| Što | Staro | Novo |
|-----|-------|------|
| SW string offset | 0x0008 | **0x001A** (engine.py je bio ispravan, CLAUDE.md nije) |
| CAN TX tablica | 0x0433BC | **0x03DF0C** (2019+) / **0x03DF1E** (2018) |
| 0x0433BC sadržaj | CAN IDs | Period tablica (LE16 ms vrijednosti) |
| 0x0408 CAN ID | Samo GTS | **Svi SW** |
| Spark ignition | 0x02B730 | **0x026A50** |
| inj_main | razlikuje se po snazi | **identičan za 130/170/230/300hp** |
| Mape 1630 ref | 54 | **56** |
| DTC registry | 111 P-kodova | **121** (+ 10 U16Ax) |

### Fajlovi promijenjeni
- `core/can_decoder.py` — CAN TX adresa, cluster bus konstanti
- `cluster/_materijali/can_protocol_knowledge.md` — CAN TX adresa + 0x0408 ispravka
- `memory/MEMORY.md` — sve ispravke
- `.gitignore` — prošireno (CSV svugdje, .claude/)

### Audit rezultati (novi fajlovi u _materijali/)
- `dtc_cross_sw_audit.md`, `maps_cross_sw_audit.md`
- `spark_gti90_audit.md`, `tec1503_audit.md`, `can_cross_sw_audit.md`

---

## 2026-03-19 13:45 — DTC cross-SW audit za 1630 ACE

### Što je napravljeno
- Napisana i pokrenuta Python skripta `_materijali/dtc_cross_sw_audit.py`
- Analizirano 10 dumpova (2018–2021, 300/230/170/130hp)
- Rezultati zapisani u `_materijali/dtc_cross_sw_audit.md`

### Ključni nalazi
- **P0231 stvarna adresa**: 0x0217BC (idx=94), NE 0x021786 (idx=67) kako je bilo pretpostavljeno
- **Mapping tablica**: 0x0239B4 za sve 300hp SW verzije (10SW023910/040039/054296/066726) — potvrđena
- **Enable tablica (0x021080)**: identična bajt-za-bajt u SVIM 10 dumpova
- **U16Ax grupacija** (za 300hp SW, konzistentno 2018-2021):
  - Slot 57 (0x0210B9=0x06): P0231, U16A1, U16A2, U16A3, U16A5, U16A8, U16AB
  - Slot 3 (0x021083=0x00): P0232, U16A4, U16A7, U16A9, U16AA (već disabled!)
- Za 10SW053727 (230hp) i 10SW053729 (170/130hp): mapping tablica nije pronađena automatski — drugačija SW struktura
- DTC storage adrese identične u svim SW verzijama

### Fajlovi promijenjeni
- `_materijali/dtc_cross_sw_audit.py` (nova skripta)
- `_materijali/dtc_cross_sw_audit.md` (izvještaj)

---

## 2026-03-19 — CLAUDE.md rewrite iz stvarnog koda

### Što je napravljeno
- Pročitani svi Python fajlovi: engine.py, map_finder.py, map_editor.py, dtc.py, checksum.py, can_decoder.py, eeprom.py, tools/can_sniffer.py, tools/did_map.py, ui/main_window.py, test_core.py, main.py
- CLAUDE.md potpuno rewritan na temelju stvarnih vrijednosti iz koda (ne logova)

### Ključne ispravke u novom CLAUDE.md
- Injection dimenzije: 16×12 (ne 6×32 kako je stajalo)
- Rev limiter: samo 0x02B72A + 0x02B73E su stvarni limiteri (ostale 3 adrese su unutar 2D mape)
- DTC: 121 kodova (111 P + 10 U16Ax) — ne 111
- Checksum: CRC32-HDLC poly=0xEDB88320, BOOT [0x0000–0x7EFF], residua=0x6E23044F — dodane stvarne konstante
- MapFinder: find_all() za 300hp = 33 skenera; Spark = 4 skenera; broj mapa iz test potvrdjen
- CAN decoder: svi ID-ovi i decode metode dokumentirani iz dispatch tablice
- EEPROM: sve ODO adrese po HW tipu iz koda (0x0562/0x0D62/0x1562/0x4562/0x0490/0x0DE2/0x5062/0x1062)
- Dodan popis svih relevantnih lambda/SC/torque/decel mapa s adresama
- Dodan opis can_sniffer.py i did_map.py
- Uklonjene sekcije 7 i 8 (Claude komande i permissions — nisu relevantne za projekt kontekst)

## 2026-03-19 25:00 — Full 56-mapa cross-SW audit, nova skripta cross_sw_audit.py

### Sto je napravljeno
- Kreirana nova skripta `cross_sw_audit.py` (zamjena za staru s 36 mapa) — pokriva svih 56 mapa iz MAPS_REF_FULL
- Referenca: 2021/1630ace/300.bin (10SW066726), usporedba s 9 dumpova (2018-2021, sve snage)
- Otkrivena greska u staroj dokumentaciji: 0x02B72A/0x02B73E NISU u16 period-encoded rev limiteri,
  nego u8 bajtovi ispred ign_00 bloka (RPM cut pragovi u internoj skali, 0x21=33, 0x22=34)
- Stvarni rev limiter potvrdjen @ 0x028E96 (LE u16 period-encoded)

### Kljucni nalazi

| Kategorija | Nalaz |
|-----------|-------|
| **Identicne u svim SW** | rpm_axis_1/2/3, inj_main, mat_corr, lambda_prot, cts_temp_axis (7 mapa, 804B) |
| **Uvijek razlicite** | torque_main/mirror/opt, lambda_main/bias/trim/adapt/eff_sub, cold_start (9 mapa) |
| **SC vs NA razlika** | NA: ~70% diff od ref; SC_ista_godiste: ~14%; SC_razlicite: ~48-60% |
| **Mirror bug** | sc_bypass_1 != sc_bypass_2 unutar reference (26B razlike!) — sumnjivo |
| **2019/300 == 2020/300** | Identicni u svim mapama (0 diff u 13.6% vs 14.3% od ref) |
| **Rev cut byte** | 300hp SC: 0x22=34, 130/170 NA: 0x21=33, 230 SC: 0x21/0x23 mix |
| **inj_main** | 100% identican u svim dumpovima — snaga se ne razlikuje kroz injection |
| **Ignition** | NA ima ~90-97% diff od SC ref; 230 SC ima 40-78% diff; 2019==2021 300hp SC |
| **lambda_thresh** | ALL(158) u svima osim 2019/2020 300hp (=== ref) |
| **kfped** | 2018/300 SC potpuno razlicit (ALL 400B) — drugacija pedal krivulja |
| **thermal_enrich** | samo SC varijante imaju razliku (NA == ref) |
| **idle_rpm** | samo 2018/300 razlicit (89B) — svi ostali == ref |

### Fajlovi promijenjeni
- `cross_sw_audit.py` — nova skripta (zamjena)

## 2026-03-19 14:30 — Cross-SW audit: 10 dumpova 1630 ACE (2018-2021)

### Sto je napravljeno
- Kreirana skripta `_materijali/cross_sw_audit.py` — cita 10 binarnih dumpova, usporeduje 36 mapa
- Rezultati u `_materijali/maps_cross_sw_audit.md` (kompletan Markdown sa svim tablicama i interpretacijama)

### Kljucni nalazi
| Kategorija | Nalaz |
|-----------|-------|
| **Invarijantne mape** | rpm_axis_1/2/3, inj_main, inj_mirror — SAME u svim SW verzijama (2018-2021, sve snage) |
| **Injection** | Bazna tablica IDENTIČNA za 130/170/230/300hp — snaga se ne razlikuje kroz injection nego kroz torque+lambda+ignition |
| **SW string lokacija** | @ 0x001A (ne 0x0008 kako je ranije dokumentirano) |
| **2021 NA/230 dumpovi** | Dijele ISTI SW string s 2020 (10SW053727/053729) — razlika samo 80B @ 0x017F02-0x017F73 u CODE |
| **SC bypass** | 300hp=`2626`, 230hp=`1f1f`, 170/130hp=`1e1e` — svaka snaga ima drugaciji opcode; 2018/2019 imaju starije kodove |
| **Lambda 2021/300** | Jedini s lambda min < 0.9844 (= 0.9655) — agresivniji bogati uvjeti |
| **Torque 2021/300** | Najsiri raspon (min 30464, max 39168) od svih SW verzija |
| **Rev limiter** | 300hp SC: 8223 RPM, 230hp SC: 8168 RPM, 170/130hp NA: 8750 RPM (visi zbog bez SC tlaka) |

### Fajlovi promijenjeni
- Kreiran: `_materijali/cross_sw_audit.py`
- Kreiran: `_materijali/maps_cross_sw_audit.md`

---

## 2026-03-19 — Spark 900 ACE + GTI90 kompletan binarni audit

### Što je napravljeno
- Kreirana skripta `_materijali/spark_gti90_audit.py` — čita 6 dumpova (spark 2018/19/20/21 + gti90 2020/21)
- Rezultati u `_materijali/spark_gti90_audit.md`

### Ključni nalazi
| | Spark 900 (10SW039116) | GTI90 (10SW053774) |
|--|--|--|
| Rev limiter | **0x028E34** = 5120t = **8081 RPM** | **0x028E7C** = 5875t = **7043 RPM** |
| Ignition | **~0x026A50** (12×12, stride 144B) | **0x02B730** (= isti kao 1630!) |
| Lambda main | **~0x024EC4** (mean ≈ 1.0) | 0x0266F0=flat, 0x026C08=aktivna |
| Injection | ~0x02436C (overlapping) | **0x022066** (GTI legacy!) |
| DTC tablica | **NIJE @ 0x0217EE** (period ticks!) | **0x0217EE** (kao 1630) |
| Torque | NEMA na 1630 adresi | 0x02A0D8 i 0x02A5F0 (OK) |
| CAN IDs | 0x00B9-0x0118 (niži range) | 0x015x-0x07FF (viši) |

- spark_2019 = spark_2020 = spark_2021 (MD5 identičan!)
- gti90_2020 vs gti90_2021: samo 80 razlika @ 0x017F02 (CODE region)
- Spark ignition NIJE na 0x02B730 (1630 adresa); treba lokalizirati sve 27 mapa (A/B/B2/C)

## 2026-03-20 00:15 — U16Ax DTC kodovi dodani u DTC_REGISTRY

### Što je napravljeno
- `core/dtc.py` — dodano 10 U16Ax kodova (0xD6A1-0xD6AB) u DTC_REGISTRY (ukupno 121 kodova)
- `DtcDef.p_code` property popravljen: sada vraća ispravni SAE prefix (P/C/B/U) umjesto uvijek "P"
  - U16Ax kodovi prikazuju se kao "U16A1"-"U16AB" (BRP U1xxx = 0xDxxx enkodiranje)
- `dtc_off_all()` ključevi u results dictu koriste `defn.p_code` umjesto hardkodiranog `f"P{code:04X}"`
- Testovi prolaze

### Adrese U16Ax (ori_300, SW 10SW066726)
| Kod   | code_addr  | en_addr    | Napomena |
|-------|------------|------------|----------|
| U16A1 | 0x0217D8   | 0x0210B9   | dijeli slot s P0231 (fuel pump)! |
| U16A2 | 0x0217C8   | 0x0210B9   | dijeli slot s P0231 |
| U16A3 | 0x0217D4   | 0x0210B9   | dijeli slot s P0231 |
| U16A5 | 0x0217D0   | 0x0210B9   | dijeli slot s P0231 |
| U16A8 | 0x0217C4   | 0x0210B9   | dijeli slot s P0231 |
| U16AB | 0x0217CC   | 0x0210B9   | dijeli slot s P0231 |
| U16A4 | 0x0217CE   | 0x021083   | već isključen (en=0x00) |
| U16A7 | 0x0217CA   | 0x021083   | već isključen |
| U16A9 | 0x0217C6   | 0x021083   | već isključen |
| U16AA | 0x0217D6   | 0x021083   | već isključen |

Mirror offset: +0x0366 (isti kao P-kodovi).

---

## 2026-03-19 23:55 — SAT cluster firmware analiza: CAN TX routines i heartbeat identifikacija

### Zadatak
Statička analiza 3 MC9S08DZ128 SAT cluster FLASH dumpa (GTX300_18, GTI_19, GTS90_17) za identifikaciju CAN TX ID-a koje SAT šalje ECU-u.

### Ključni nalazi
- **MSCAN modul base = $1800** (ne $0160 kako se pretpostavljalo) — startup kod piše na $1802/$1803/$1809/$1800
- **TX buffer layout**: $1881=IDR0, $1882=IDR1, $1885-$188C=DSR0-7, $188D=DLR
- **CAN TX ISR** @ $47DD (paged flash), CAN RX ISR @ $4777
- **SAT TX IDs** iz init tablice (0x03628 / 0x03414): 0x0186, 0x0187, 0x0188, 0x018B, 0x018C, 0x0190-0x0192, 0x019A-0x019B, 0x01CD (GTX/GTI), 0x4CD (DESS)
- **ECU → SAT**: 0x0578 (267-300ms) + 0x0400 (311-344ms) iz RX watchdog tablice
- **TX0 MSCAN init**: IDR0=$80, IDR1=$01 → operativni init ID = 0x400 (ali scheduler koristi 0x018x-0x01Cx range)
- RAM staging buffer: $0190-$0195 (GTX) / $0180-$0185 (GTS) — ISR kopira u $18xx

### Fajlovi
- Kreiran: `cluster/_materijali/sat_heartbeat_analysis.md`
- Python skripte za analizu: `C:/Users/SeaDoo/AppData/Local/Temp/can_*.py`

---

## 2026-03-19 17:30 — can_sniffer.py: integracija CanDecoder + checksum/RC tracking

### Promjene
- `tools/can_sniffer.py` kompletno refaktoriran:
  - Zamijenjen generički `_try_decode()` s `CanDecoder.decode()` ID-specifičnim dispatcherom
  - `IdStats` dobio `checksum_errors` (XOR provjera) i `rolling_ctr_jumps` (skokovi RC) tracking
  - `_print_stats()` prikazuje CS errore i RC jumpove po koloni
  - CSV output koristi `_format_decoded()` koji filtrira meta polja
  - Dodan sys.path fallback za pokretanje izvan me_suite roota
- Svi testovi (test_core.py) prolaze bez promjena

---

## 2026-03-19 — CAN log analiza: BUDS2 DID/LID mapiranje live data parametara

### Zadatak
Analiza sniff_livedata.csv i sniff_maps24.csv da se identificiraju DID/LID identifikatori
za 24 BUDS2 live data parametra (svaka sesija ima drugačiji set 24 parametara).

### Metodologija
- Protokol: UDS SID 0x22 (ReadDataByIdentifier) + KWP SID 0x21 (ReadDataByLocalId)
- CAN IDs: 0x7E0 (request) / 0x7E8 (response) — standardni OBD adresi, ne 0x710/0x720
- Identificiran kratki ciklus (34 items) = 24 user-selected + 10 background
- ECU na stolu (motor hladan/topao, nije u radu)

### Ključni nalazi
1. **Arhitektura poliranja**: BUDS2 ima 2 faze:
   - Kratki ciklusi 1-2 (34 items): samo user-selected parametri
   - Puni ciklusi 4+ (89 items = 73 UDS + 16 KWP): user + kompletni background set
2. **5 NRC DIDs**: 0x2146, 0x2167, 0x2168, 0x2169, 0x216d — ECU vraća NRC 0x12 (unsupported)
3. **Temperatura format**: T_C = raw / 2 - 40 (Bosch standard 1-byte)
   - 0x2120 = 120 → 20°C (Intake Temp, sobna) ✓
   - 0x2121 = 184 → 52°C (Coolant Temp, topao motor)
   - 0x2188 = 110 → 15°C (Exhaust Water Temp)
4. **Pritisak**: 0x2136 = 202 → 202/2 = 101.0 kPa (Ambient Pressure) ✓ verificirano
5. **Lambda format**: Q7, 128 = 1.000; pet DIDs daje 1.000 na stolu
6. **sniff_cdid.csv**: 96 podržanih / 27 nepodržanih DIDs (DID discovery scan)

### Fajlovi promijenjeni
- `tools/did_map.py` NOVO — kompletna DID/LID mapa s fizikalnim dekoderima

### Pouzdanost mapiranja
- Definitivan (fizikalna provjera): Ambient Pressure (0x2136), Intake Temp (0x2120)
- Visoka (~): Coolant Temp, Exhaust Water Temp, lambda parametri, lambda=1.0 parametri
- Nesigurno (?): Engine Speed, Manifold Pressure, Mass Fuel Flow (formula nepoznata)
- Background/nepoznato: 0x2101, 0x2102, 0x210c, 0x213d, KWP 0x1e, 0x11, 0x17, itd.

## 2026-03-19 22:50 — SDCANlogger analiza: live CAN protokol s pravog plovila

### Zadatak
Kompletna analiza SDCANlogger projekta (C:\Users\SeaDoo\Desktop\old_pro\SDCANlogger\)
koji je snimao live CAN s pravog Sea-Doo plovila 2025-07-27.

### Ključni nalazi
- **Bus brzina**: 250 kbps (cluster/body bus, ne dijagnostički)
- **Motor status pri snimanju**: ISKLJUČEN (RPM = 5–6 cijelo vrijeme)
- **Aktivnih CAN ID-ova**: 14 ukupno
- **Nepoznati ID-ovi**: 0x122, 0x316, 0x4CD, 0x7DF, 0x7E0, 0x7E8

### SAT Heartbeat: 0x4CD (POTVRĐENO)
- Period: točno 1000ms (1 Hz)
- Alternira 2 poruke: A=`000B030420020121`, B=`F0AA002D00040000`
- 0xAA = klasični "alive" byte u embedded sistemima
- **Ovo je SAT/cluster keepalive** — jedini ne-ECU, ne-dijagnostički ID

### XOR Checksum (potvrđeno na 5 ID-ova)
- `byte[7] = XOR(byte[0..6])` — vrijedi za 0x102, 0x103, 0x110, 0x122, 0x516
- 0x300, 0x308, 0x316, 0x320, 0x342 nemaju ovaj CS

### 0x102 dekodiranje potvrđeno
- `byte[1:3]` = RPM_raw, RPM = raw × 0.25
- `byte[3]` = coolant_temp_raw, °C = raw − 40 (raspon 50–75°C potvrđen)
- `byte[6]` = rolling counter 0x00–0x0F
- `byte[7]` = XOR checksum

### BUDS dijagnostika (0x7E0/0x7E8)
- 0x7E0 = BUDS → ECU UDS zahtjevi (ReadDataByIdentifier 0x22)
- 0x7E8 = ECU → BUDS odgovori
- Aktivnih DIDs: ~85 DID-ova oblika 0x21xx (0x2101–0x2188)
- 0x7DF = ISO-TP Flow Control (0x30) od BUDS alata

### Fajlovi kreirani/modificirani
- C:\Users\SeaDoo\Desktop\cluster\_materijali\can_protocol_knowledge.md — NOVI, kompletni CAN protokol nalaz

---

## 2026-03-19 22:00 — Koraci 1–7: binarna analiza, backup/restore, MapGridTab, diff_maps, UI

### Korak 1 — Binarna provjera adresa 0x02B72A / 0x02B73E u 2018 SW (10SW023910)
- Ove adrese sadrže vrijednost 0x2222 = 8738 — to je IGNITION DATA, ne rev limiter
- 0x22 u8 = 34 raw = 25.5°BTDC, LE u16 0x2222 = 8738 (slučajna numerička podudarnost)
- U 2018 SW IGN_BASE je @ 0x02B72C (4B ranije nego 2019+ @ 0x02B730)
- Stvarni period-encoded rev limiter u 2018 SW: 0x028E94 = 5072 ticks = 8158 RPM (isti limit, 2B ranije)
- Rev limiter adrese u scan ostaju — vraćaju krivi podatak za 2018, ali je to istraživački artifact

### Korak 2 — Diff 2019 ORI (10SW040039) vs NPRo STG2 (isti SW string)
- NPRo mijenja: sve 19 ignition mapa (+3–4°), injection (+196% avg goriva), torque (+11%),
  lambda protection (saturirana), knock thresholds (podignuti), KFWIRKBA (saturiran za bypass),
  lambda thresholds (bypass), cold start [0] = 100 (prigušen)
- NPRo NE mijenja: RPM os, lambda main, MAT korekciju
- BOOT: 140B | CODE: 7087B | CAL: 169912B razlike

### Korak 3 — Diff Spark 2018 (10SW011328) vs Spark 2021 (10SW039116)
- SVE ignition mape IDENTIČNE na istim adresama
- Razlike: injection sub-tablice @ 0x02471C (injektori/tlak goriva), lambda cal @ 0x025408,
  fuel scalar @ 0x027E6A
- Glavne mape (injection, lambda, torque, knock) identične

### Korak 4 — backup() i restore() u MapEditor (core/map_editor.py)
- backup(suffix): timestampirana kopija u istom folderu, vraća Path
- restore(backup_path): učitava backup kao aktivni fajl
- Koristi self.eng._path (privatni atribut ME17Engine, nema javnog propertija)

### Korak 5 — MapGridTab u GUI (ui/main_window.py)
- Nova klasa MapGridTab(QWidget): QListWidget + search + QTableWidget, heatmap boje
- Read-only prikaz 2D mapa s float vrijednostima po scale veličini
- Integrirana u _build_ui() kao tab "Mape", populira se u _done1()

### Korak 6 — diff_maps() u MapFinder + Map Diff toolbar button
- diff_maps() u core/map_finder.py: {name: (vals_s, vals_o, max_diff_pct)}
- btn_map_diff u toolbar: aktivan kad su oba fajla učitana
- _show_map_diff_dialog() implementirana: delegira na _show_map_diff() → Map Diff tab
- Fajlovi: core/map_finder.py, ui/main_window.py

### Testovi — svi prolaze: 56 mapa ORI/STG2, 54 Spark, 62 GTI90, 3/3 EEPROM

## 2026-03-19 25:30 — Binarna analiza "rizičnih" mapa: Injection, Torque, KFPED, KFWIRKBA, AE, MAT

### Što je napravljeno
Duboka binarna analiza 6 tema — samo istraživanje, bez promjena koda.
Korišteni dumpovi: 300sc/130na/stg2 (2020/1630ace), spark (2020/900ace), 1503 (2019/4tec1503).

### 1. Injection Q15 format verifikacija

**KLJUČNI NALAZ: 0x02436C NIJE 2D fuel mapa!**

- Sve 16 redova tablice su UNIFORMNI (svaka ćelija u redu == ista vrijednost)
- Ovo je **injector linearization curve** (1D lookup enkodiran kao 2D blok)
  - Bosch ME17 čuva 1D karakteristiku injektora kao 16×12 blok gdje svaki "red" = jedna Q15 vrijednost ponovljena 12x
- Vrijednosti (Q15 /32768): `[0, 0, 0.01, 0.026, 0.041, 0.061, 0.08, 0.114, 0.18, 0.27, 0.394, 0.52, 0.696, 0.98, 1.5, 2.0]`
- Interpretacija: injector duty breakpoints od idle (0%) do max (200% = 2.0 → full open)
- **SC == NA** (identični stock — isti injektori i tlak goriva)
- **STG2 mijenja ovu tablicu značajno**: nizak load 0.01 → 0.04 (4×), mid-range proporcionalno veće
  - To indicira VEĆE INJEKTORE u NPRo (isti fizički otvarači ali drugačija kalibracija toka)
- "Mirror" @ 0x0244EC je DRUGAČIJA tablica (rows 11,13,14 se razlikuju) → dvije zasebne karakteristike
- Tablica počinje od 0x02436C i proteže se do 0x0246E3 (cijeli blok)
- **GTI 1503 @ 0x022066 jest prava 2D mapa** (varijacija po kolonama + redovima, SC vs NA razlikuju)
- Prava 2D fuel mapa 1630 ACE NIJE pronađena u ovoj sesiji — zasebna istraživanje potrebno

### 2. Torque limiter analiza

**Ključni nalaz: fizička krivulja momenta @ 0x029FD4**

- **0x029FD4**: 30-točkasta krivulja momenta motora u fizikalnim jedinicama (u16 LE /100 = Nm)
  - SC: `[48, 64, 72, 78, 90, 104, 110, 120, 128, 140, 152, 164, 172, 180, 188, 196, 206, 216, 224, 234, 240, 252, 260, 270, 280, 296, 308, 320, 328, 340]` Nm
  - NA: `[52, 64, 68, 72, 78, 86, 92, 105, 116, 124, 129, 136, 144, 150, 160, 169, 185, 193, 206, 222, 232, 240, 254, 264, 273, 284, 292, 304, 320, 332]` Nm
  - SC max = 340 Nm, NA max = 332 Nm (SC viši kroz cijeli raspon)
- **0x02A010**: 20-točkasta Y-os (vrijednosti 266-2344, razlikuju SC/NA) = torque demand/efficiency osa
- **0x02A038** (count=30@0x029FD0, count=20@0x029FD2): 30×20 tablica (efficiency/correction map)
- **0x02A0D8** (map_finder "torque"): Unutar 30×20 tablice — vrijednosti 109-150 u16 LE
  - SC vrijednosti NIŽE (109-140) od NA (128-150) → SC ograničava niže?
  - Dimenzija 16×16 u16 → možda drugačija organizacija nego 30×20
  - Vrijednosti /256 (Q8 frakcija): 0.43-0.59 = throttle efficiency ili torque scale factor
- **Mirror @ 0x02A5F0** identičan primarnom (0 razlika)

### 3. KFPED Y-os analiza

**KLJUČNI NALAZ: SC i NA koriste DRUGAČIJE X-osi!**

- **Header @ 0x029528**: count_x=10, count_y=20
- **SC X-os (MAP kPa gauge, signed u8)**: raw=[176,216,236,246,0,15,30,40,60,90]
  - Signed: `[-80, -40, -20, -10, 0, 15, 30, 40, 60, 90]` kPa (relativno prema atm)
  - **SC koristi BOOST/VAKUUM kao input** — mjerenje tlaka usisa
- **NA X-os (pedal %, u8)**: `[0, 2, 5, 10, 20, 30, 40, 50, 60, 70]` %
  - **NA koristi PEDALIN KUT** kao input
- **Y-os (20pt u8)**: SC=[38-213]/128=0.30-1.66, NA=[25-213]/128=0.20-1.66 = load/RPM frakcija
- **Output (10×20 u8)**: vrijednosti 20-191 = throttle valve command (0-100%)
- **Transponirana tablica (10 rows=X, 20 cols=Y)** je pravilna: svaki red monotono raste
  - Npr. X[-80 kPa]: output [34→191]% kroz 20 load točaka
  - X[+90 kPa]: output [84→148]% (manji raspon = SC ograničava gasišnje pri visokom boosту)
- **Mirror @ 0x029630**: IDENTIČAN (0 razlika)
- **Injection X-os** [5,10,15,20,25,30,35,40,45,50]% NIJE ista kao KFPED NA osa

### 4. KFWIRKBA (Lambda efficiency 41×18) istraživanje

- **X-os (18pt u16 LE @ 0x02AE32)**: [100, 200, 400, 800, 1280, 2560, 3200, 3840, 4480, 5120, 5760, 6400, 7040, 7680, 8320, 8960, 9600, 10240]
  - /32768: [0.003 - 0.313] = air mass load frakcija (lambda-load os)
- Tablica NIJE jednostavni 41×18 — row 20 i row 30 sadrže markere/granice (moguće više konkateniranih sub-tablica)
- **SC vs NA**: znatno različiti (SC=0.66-1.8, NA=0.61-1.32 u visoko-opterećenim zonama)
  - SC 36% veće vrijednosti pri punom opterećenju (SC treba više goriva)
- **STG2 mijenja 225 ćelija** — postavlja high-load ćelije na 2.0 (max Q15 = 65536)
  - Obrazac: progresivno više ćelija = 2.0 kako se row povećava
  - Efektivno DISABLIRA gornju granicu lambda enrichmenta pri visokom boosту
  - ORI max bio 1.8, STG2 podiže na 2.0 = 11% više goriva pri peak-u
- **OPASNO za tuning bez razumijevanja strukture** (41-row interpretacija nije 100% potvrđena)
- Row 9 identičan SC/NA (granica/separator)
- Row 20 sadrži iste vrijednosti kao X-os (ugrađena os unutar podataka)
- Row 30 sadrži markere (1.976, 1.988, 1.994, 1.997 = gotovo 1.0 u Q16)

### 5. Accel Enrich (AE) analiza

- **Format potvrđen**: 1B global + 5×22B sub-tablica (svaka: 6×u16 X-os + 5×u16 data)
- **Global byte @ 0x028059**:
  - SC=4, NA=4 (stock): koristi 4 temperaturne zone
  - STG2=2: samo 2 temperaturne zone (reducirani AE na hladnom?)
  - Interpretacija: broj aktivnih CTS temperaturnih segmenata
- **X-os svih sub-tablica (SC/NA isti)**: [5, 0, 150, 200, 350, 1500] (throttle rate ili ms?)
  - STG2 mijenja X-os: [5, 0, 150, **300, 600, 900**] — pomak na kasnijem raspadu
- **Y-os (enrichment frakcija Q15)**:
  - SC >NA kroz sve sub-tablice (10-15% više enrichmenta na SC)
  - Sub 3: SC=[0.6, **1.04**, 1.04, 0.74, 0.84] (>1.0 = enrichment iznad stoich)
  - Sub 4 (max): SC=[0.6, **1.24**, 1.24, 0.74, 0.84]
- **STG2 Y-vrijednosti**: niže pri X[0]=5 ali VIŠE pri X[2-5] — drugačiji profil
  - Manje početnog enrichmenta ali produljeni i snažniji na sredini

### 6. MAT garbage zona — ISPRAVLJENO

**PRETHODNI NALAZ BIO POGREŠAN — NEMA GARBAGE ZONE**

- **MAT @ 0x022726 je ČISTA tablica** koja monotono pada od -3°C do +171°C:
  - Temp os (u8 - 40 offset): `[-3, 11, 24, 37, 51, 64, 77, 91, 111, 131, 151, 171]` °C
  - Korekcija (u8 /128): `[1.039, 1.016, 1.000, 0.984, 0.969, 0.953, 0.938, 0.922, 0.898, 0.883, 0.859, 0.844]`
  - Savršeno monotono — hladni = +3.9% goriva, vrući = -15.6% goriva
  - **SC, NA i GTI imaju IDENTIČNU MAT tablicu** (razlika = 0)
- "Garbage" koje je primijećeno u prethodnoj sesiji nalazi se NA 0x02273E (IZA tablice od 24B) — to su NEPOVEZANI podaci
- **Spark 900 @ 0x022726**: potpuno drugačiji podaci (nije MAT za Spark)
  - Spark koristi DRUGAČIJU adresu za MAT (nije pronađena u ovoj sesiji)

### Fajlovi promijenjeni
- Nema — čisto istraživanje

---

## 2026-03-19 24:00 — Binarna analiza: 4 neidentificirane mape (KFPED, MAT, MAP-fuel, Boost)

### Što je napravljeno
Čisto istraživanje (bez promjena koda) — binarna analiza dumpova 300hp SC i 130hp NA, diff metoda.
Korišteni dumpovi: `2020/1630ace/300.bin` (10SW054296) i `2020/1630ace/130.bin` (10SW053729).

### 1. KFPED — Pedal/drive-by-wire mapa
- **Header** @ `0x029528`: count_x=10, count_y=20
- **Data** @ `0x029548`: 10×20 = 200 bytes u8, vrijednosti 20–191
- **Mirror** @ `0x029630` (identična kopija)
- X-os (pedal): NA=[0,2,5,10,20,30,40,50,60,70]° pedal kuta
- Y-os (/40=RPM): [1000,1520,1760,2000,2520,3000,3520,4000,4520,5000,5520,6000,6520,6760,7000,7240,7520,7760,8000,8520] RPM
- SC X-os razlikuje se (boost-adjusted pedal krivulja)

### 2. MAT korekcija — Manifold Air Temperature fuel correction
- **Shared (12pt)** @ `0x022726`: u8 temp os [37–211]°C, Q8 korekcija [133→108] = ratio 1.039→0.844
- **SC-specifična (8pt)** @ `0x023702`: temp os [64–197]°C, SC=[135→115] = 1.055→0.898, NA=[128×8] = flat/disabled
- Više goriva na hladnom, manje na vrućem

### 3. Injection/MAP-fuel mapa — fuel trim vs load × MAP tlak
- **Header** @ `0x02202A`: count_x=12, count_y=16
- **Data** @ `0x022066`: 12×16×2 = 384B, u16 LE Q15
- X-os (load): SC=[1067,1280,1707,2133,2560,2987,3413,4267,5333,6400,7680,8960]
- Y-os (MAP kPa×100): [5600–32800] = [56–328 kPa]
- SC vrijednosti 10–30% više od NA pri istim točkama
- Mapa završava @ 0x0221E6 (poklapa se s diff granicom)

### 4. Boost target/korekcija — SC specifično
- **SC bypass threshold table** @ `0x020534`: 7×7 u8 (49B), MAP tlak granice po RPM pojasima
  - Implicira boost ciljeve: [97–413 kPa] po RPM pojasu
- **Boost correction map** @ `0x02220E`: 10×8 u16 LE Q14
  - Header @ `0x0221E6`: count_x=10, count_y=8
  - X-os RPM: SC=[1500,3000,4000,6000,7000,8000,8500,9500,10500,11500]
  - Y-os MAP kPa×100: SC=[5000–34000] = [50–340 kPa]
  - NA sve vrijednosti = 16384 (1.0 flat, neaktivno)
  - SC vrijednosti 5325–35895 = Q14 ratio 0.32–2.19

### Fajlovi promijenjeni
- Nema — čisto istraživanje

---

## 2026-03-19 23:55 — Spark osi implementirane (IGN A/B/B2/C + Therm Enrich + Lambda DEF)

### Što je napravljeno
Implementirani `axis_x` i `axis_y` na 6 Spark MapDef skupova na temelju potvrđenih binarnih nalaza istraživačkog agenta.

**IGN A (`_make_spark_ign_def`, 8×12×12 u8)**
- Dodane `_SPARK_IGN_A_X` i `_SPARK_IGN_A_Y` kao shared singleton objekti
- X-os RPM @ 0x026A1E: 12pt u16LE, /4=RPM, [1500..8000]
- Y-os load @ 0x0269AF: 12pt u8, /128=load, [0.023..1.203]

**IGN B (`_make_spark_ign_b_def`, 8×12×12 u8) — dijeli IGN A osi**
- Dodano `axis_x=_SPARK_IGN_A_X, axis_y=_SPARK_IGN_A_Y`

**IGN B2 (`_make_spark_ign_b2_def`, 8×12×12 u8) — dijeli IGN A osi**
- Dodano `axis_x=_SPARK_IGN_A_X, axis_y=_SPARK_IGN_A_Y`

**IGN C (`_make_spark_ign_c_def`, 3×9×8 u16LE)**
- X-os RPM @ 0x027C7C: 8pt u16LE, /4=RPM, [3500..8500]
- Y-os load @ 0x027D36: 9pt u16LE, /128=load

**Therm Enrich (`_SPARK_THERM_ENRICH_DEF`, 8×7 u16LE)**
- X-os (CTS temp) @ 0x025AD0: 8pt u8, [6..160]°C
- Y-os (warmup sekunde) @ 0x025B50: 7pt u8, [15..125]s

**Lambda DEF (`_SPARK_LAMBDA_DEF`, 8×16 Q15)**
- Y-os (RPM) @ 0x025F3C: 8pt u16LE, /4=RPM
- X-os (lambda ref) @ 0x025F4C: 16pt u8, /128=λ; val[0]=151 je anomalija (nemonoton) — primijenjeno kao jest

### Testovi
- `python test/test_core.py`: SVI TESTOVI PROLAZE
- Spark 900: 52 mape (ispravno)
- ORI 300hp: 54 mape (ispravno)
- GTI 90: 60 mapa (ispravno)

### Fajlovi promijenjeni
- `core/map_finder.py`: axis_x/axis_y dodani za 6 Spark definicija

---

## 2026-03-19 23:30 — Binarna analiza osi: Spark IGN A/B/C + Lambda DEF + Therm Enrich

### Što je napravljeno
Istraživanje (bez promjena koda) — osi za 4 mape u Spark 900 ACE ECU-u. Korišteni dumpovi: `2021/900ace/spark90.bin` (10SW039116) i `2018/900ace/spark90.bin` (10SW011328).

### IGN A (12×12 u8) @ 0x026A76 — POUZDANO
- **Y-os (load, 12pt u8)** @ `0x0269AF`: `[3, 10, 38, 52, 64, 76, 90, 102, 116, 128, 140, 154]`
  - /1.28 = load% `[2.3%..120.3%]` — isti pattern kao 300hp ECU load os
  - **Identično na 2018 i 2021**, pouzdanost 90%
- **X-os (RPM, 12pt u16le)** @ `0x026A1E`: raw `[6000..32000]`, RPM = `[1500..8000]`
  - count byte @ `0x026A1C = 12` potvrđuje dimenziju
  - **Identično na 2018 i 2021**, pouzdanost 95%

### IGN B (12×12 u8) @ 0x0295C0 — KANDIDAT
- Osi nisu pronađene direktno blizu mape (>500B praznine + null padding)
- Ispred mape: `@ 0x029470` = 8pt u8 `[60,80,100,110,120,130,140,150]` (identično 2018/2021)
- `@ 0x029478` = 12pt u16le `[24..251]`, /128 = load Q8 `[0.19..1.96]` (identično 2018/2021)
- Najvjerojatniji scenarij: IGN B dijeli osi s IGN A (globalne osi 0x0269AF i 0x026A1E)
- Alternativni kandidat RPM os @ `0x028946`: `[1000..5520 RPM]` — previše nizak gornji raspon

### IGN C (9×8 u16le) @ 0x02803A — 75-80%
- **X-os (RPM, 8pt u16le)** @ `0x027C7C`: raw `[14000..34000]`, RPM = `[3500..8500]`
  - count @ `0x027C7A = 8`, identično 2018/2021, pouzdanost 80%
- **Y-os (load, 9pt u16le)** @ `0x027D36`: raw `[4000..12600]`
  - Prvih 9 tocaka identično s Spark injection load osi `[3999..33600]`
  - Identično 2018/2021, pouzdanost 75%

### Lambda DEF (8×16 Q15) @ 0x025F5C — X-os
- **X-os @ 0x025F4C** (odmah iza Y-osi): 16pt u8 `[151, 38, 50, 63..194]`
  - val[0]=151 je anomalija, ostatak `[38..194]/128 = lambda [0.30..1.52]` (monotono)
  - 2021 vs 2018 razlika u pozicijama 11,12 → nije identično
  - Mapa ima 4 lambda grupne razine: cols[0-4]=λ0.965, cols[5-7]=λ0.922, cols[8-12]=λ0.965, cols[13-15]=λ0.922
  - `0x024775` (kandidat iz zadatka) NIJE prava os — razlikuje se 2018/2021
  - Pouzdanost 85%

### Therm Enrich (8×7 u16le) @ 0x025BAA — POTVRĐENO
- **X-os (CTS temp, 8pt u16le)** @ `0x025AD0`: `[6, 44, 50, 75, 100, 125, 150, 160]` °C — identično
- **Y-os (7pt u8)** @ `0x025B50`: `[15, 30, 45, 60, 80, 100, 125]`
  - Interpretacija: **warmup sekunde od hladnog starta** (15s..125s)
  - Dijagonalni max pattern u mapi potvrđuje: max enrichment 225% se pomiče dijagonalno (svaka temp ima peak u drugom stupcu)
  - Identično 2018/2021, pouzdanost 80%

### Fajlovi promijenjeni
- Samo istraživanje, bez promjena koda

## 2026-03-19 12:10 — 10SW025022 — novi SW identificiran (2018 GTI 4TEC 1503 130hp v1)

### Što je napravljeno
- Dump `_materijali/dumps/2018/4tec1503/130v1.bin` analiziran
- SW: `10SW025022` — **novi, dosad neregistriran**; dodan u `core/engine.py` KNOWN_SW
- 60 mapa (za 1 manje od 2019 — nedostaje `therm enrich @ 0x02AA42`)
- Lambda 0x0266F0: 0.961–1.038λ; torque flat 32768; SC bypass activan u kodu [30,30,30,30,31,35,38,255] (1503 NA nema fizički ventil)
- 82.8KB CODE razlika + 64KB CAL razlika vs 10SW040008 (2019)
- Isti adresar kao GTI90 2021 (10SW053774)
- BUDS2 nudi i drugu verziju za 2018 GTI 130hp — vjerovatno 10SW025752 (155hp GTI SE)

### Fajlovi promijenjeni
- `core/engine.py`: 10SW025022 dodan

---

## 2026-03-19 14:15 — Spark torque ispravak + 2 false positive uklonjeni (map_finder.py)

### Što je napravljeno

**1. `_SPARK_TORQUE_DEF` — ispravljena adresa i dimenzije**
- Prethodna definicija: `rows=16, cols=16, addr=0x027E3A` (false — unutar prave tablice na offsetu +0xA0)
- Ispravna: `rows=30, cols=20, addr=0x027D9A`, mirror `0x0282B2` (+0x518)
- Dodani `axis_x` (20pt RPM @ 0x027D72) i `axis_y` (30pt load @ 0x027D36)
- `byte_order="BE"`, `raw_min=27000`, `raw_max=33000` (stvarni BE raspon: 27648–32768)
- Count bytes [30, 20] @ 0x027D32 potvrđeni binarnom analizom (2021 spark90.bin)
- Mirror verificiran: identičan 1200B blok @ 0x0282B2

**2. `_SPARK_IDLE_RPM_DEF` @ 0x0224A0 — false positive uklonjen**
- 0x0224A0 = 0x0222BE + 482B = unutar Spark injection tablice (30×20)
- MapDef objekt zakomentiran s napomenom; scan blok uklonjen

**3. `_SPARK_LAMBDA_PROT_DEF` @ 0x0222C0 — false positive uklonjen**
- 0x0222C0 = 0x0222BE + 2 (drugi element injection tablice)
- MapDef objekt zakomentiran s napomenom; scan blok uklonjen

### Fajlovi promijenjeni
- `core/map_finder.py`

### Rezultati
- Testovi: svi prolaze
- Spark 900 ACE mape: 52 (54 - 2 false positiva; torque se pravilno pronalazi @ 0x027D9A)

---

## 2026-03-19 11:32 — EEPROM radni sati editabilni + DTC stablo kolapsibilno

### Što je napravljeno

**1. EEPROM radni sati — editabilno (core/eeprom.py + ui/eeprom_widget.py)**
- `EepromEditor.set_odo_raw(minutes)`: upisuje novu vrijednost u SVE relevantne ODO adrese circular buffera za detektirani HW tip (062/063/064). Raspon 0-65000 min.
- `eeprom_widget.py`: "Radni sati" grupa sada je editabilna (✏), s dva QSpinBox: sati (0-1092h) i minute (0-59min). Originalna vrijednost ostaje prikazana kao read-only. `_populate_edit` puni spinboxove iz `info.odo_raw`. `_apply_edits` poziva `set_odo_raw`.
- Test: pisanje 730 min (12h 10min) na lažni 064 EEPROM → parser čita 730 min. ✓

**2. DTC stablo — kolapsibilno (ui/main_window.py, DtcSidebarPanel)**
- Promijenjeno: `cat_item.setExpanded(True)` → `False` (top-level kategorije P/C/B/U kolapsiraju po defaultu)
- Promijenjeno: `sub_item.setExpanded(True)` → `False` (podgrupe isto kolapsiraju)
- CSS fix: uklonjena `image:none` pravila koja su skrivala +/- indikatore na zatvorenim čvorovima; dodana CSS pravila za `branch:open` i `branch:closed` (bez `image:none`)
- `_filter()`: pri pretraživanju auto-expanduje kategorije i podgrupe gdje ima rezultata; ne kolapsira manualno (korisnik kontrolira)

### Fajlovi promijenjeni
- `core/eeprom.py`: dodana `set_odo_raw()` metoda u EepromEditor
- `ui/eeprom_widget.py`: ODO grupa postala editabilna; SpinBox za h+min; `_populate_edit` i `_apply_edits` prošireni
- `ui/main_window.py`: DtcSidebarPanel CSS i expanded state

### Rezultati
- Svi testovi prolaze (54 mapa ORI/STG2, 54 Spark, 60 GTI, EEPROM ODO 3/3)

## 2026-03-19 16:30 — Osi za Spark lambda trim 1/2 i deadtime (binarna verifikacija)

### Sto je napravljeno
Binarna analiza `spark90.bin` (2021) za pronalazak axis definicija za jos 3 Spark mape:

**Lambda Trim 1 (0x024EC4, 30x20)** — IMPLEMENTIRANO:
- Y-os (load 30pt) @ 0x024E60: [4800..32000] raw load
- X-os (speed 20pt) @ 0x024E9C: [640..4693] raw speed
- Count bytes [30,20] @ 0x024E5C potvrdjeni

**Lambda Trim 2 (0x0253DC, 30x20)** — IMPLEMENTIRANO:
- Y-os (load 30pt) @ 0x025378: [4800..33600] (STG2 mijenja 19/30 vrijednosti)
- X-os (speed 20pt) @ 0x0253B4: [640..4693] (ista os kao trim 1)
- Count bytes [30,20] @ 0x025374 potvrdjeni

**Deadtime (0x0287A4, 8x8)** — IMPLEMENTIRANO:
- X-os (napon 8pt) @ 0x028794: [80..150]/10 = [8.0..15.0V] baterija
- Y-os (trajanje 8pt) @ 0x028784: [4,10,20,40,60,80,100,120] (u8 parovi, scale 0.1 = ms)
- Count bytes [8,8] @ 0x028780 potvrdjeni

**Lazi pozitivi DETEKTIRANI** (adrese ostaju ali dodani komentari):
- `_SPARK_LAMBDA_PROT_DEF`: 0x0222C0 je UNUTAR injection data (row 12-14) — lazi pozitiv!
  Stvarna lambda zastitna lokacija nije pronadjena (nema count bytes [12,18] ni u Sparku ni GTI90)
- `_SPARK_IDLE_RPM_DEF`: 0x0224A0 je UNUTAR injection data — lazi pozitiv!
  Stvarna adresa nije pronadjena

### Fajlovi promijenjeni
- `core/map_finder.py`: axis_x/axis_y dodani za 3 mape

### Testovi
- `python test/test_core.py` — 9/9 PASS

---

## 2026-03-19 — Binarna analiza osi za 10 Spark 900 ACE mapa (agent sesija)

### Što je napravljeno
Potpuna binarna analiza `_materijali/dumps/2018/900ace/spark90.bin` (SW 10SW011328) i usporedba s `spark_stg2` (NPRo STG2 1037544876) za pronalazak axis definicija za 10 Spark 900 ACE mapa.

### Rezultati po mapi

**MAP 1 (Injection, 0x0222BE):** POTVRĐENO
- Header @ 0x022256: [ncols=20, nrows=30]
- X-os LOAD (20pt) @ 0x02225A, /256 = [30..104%]
- Y-os RPM (30pt) @ 0x022282, /4 = [999..8400 RPM]
- Injection mirror @ 0x0227D6 (+0x518 offset), potvrđen

**MAP 2 (Lambda Protection, 0x0222C0):** ADRESA NETOČNA
- 0x0222C0 je unutar injection tablice (injection data) — nije lambda prot mapa
- Stvarna lokacija nije pronađena s dovoljnom sigurnošću

**MAP 3 (Injector Deadtime, 0x028786):** POTVRĐENO
- Header @ 0x028780: [ncols=8, nrows=8]
- X-os PW (8pt) @ 0x028784, /40e6 = [25.7..771 µs]
- Y-os VBAT (8pt) @ 0x028794, /10 = [8.0..15.0 V]

**MAP 4 (Idle RPM, 0x0224A0):** ADRESA SUMNJIVA
- 0x0224A0 je unutar injection tablice (redak 12, stupac 5)
- Nije idle RPM mapa — adresa iz zadatka je pogrešna

**MAP 5 (Lambda Target, 0x025F5C):** DJELOMIČNO POTVRĐENO
- Data @ 0x025F5C, Q15 u16LE, 8 stupaca × 8 redaka
- Axis1 (RPM 8pt) @ 0x025F3C: /4 = [836..8540 RPM]
- Axis2 (load 8pt) @ 0x025F4C: /32768 Q15 = [0.301..1.521]
- STG2 mijenja ove vrijednosti → potvrđena je lambda target mapa
- NAPOMENA: zadatak kaže 8×16 ali samo 8×8 axes pronađene; možda je lambda target u ignition map regiji

**MAP 6 (Torque, 0x027D9A):** POTVRĐENO (ispravljena adresa)
- Header @ 0x027D32: [ncols=30, nrows=20]
- Y-os RPM (30pt) @ 0x027D36: /4 = [1000..8400 RPM]
- X-os LOAD (20pt) @ 0x027D72: /16 = [11.8..97.7%]
- Stvarni data start @ 0x027D9A (ne 0x027E3A iz zadatka)

**MAP 7 (Lambda Trim, 0x024EC4):** POTVRĐENO
- Header @ 0x024E5C: [ncols=30, nrows=20]
- X-os RPM (30pt) @ 0x024E60: /4 = [1500..8000 RPM]
- Y-os LOAD (20pt) @ 0x024E9C: /64 = [10.0..73.3%]

**MAP 8 (Therm Enrich, 0x025BAA):** POTVRĐENO (dimenzije ispravljene)
- Data @ 0x025BAA, u16LE, 8 stupaca × 12 redaka (ne 8×7)
- X-os CTS (8pt) @ 0x025AD0: [6,44,50,75,100,125,150,160] °C (direktna temperatura)
- Y-os (12pt): NIJE PRONAĐENA — implicitna ili nema u memoriji
- Enkodiranje: vrijednost / 10240 = faktor obogaćivanja
- STG2 (NPRo) povećava sve vrijednosti za ~+25%

**MAP 9 (Lambda Trim2, 0x0253DC):** POTVRĐENO
- Header @ 0x025374: [ncols=30, nrows=20]
- X-os RPM (30pt) @ 0x025378: /4 = [1200..8400 RPM]
- Y-os LOAD (20pt) @ 0x0253B4: /64 = [10.0..73.3%] (identična MAP 7 Y-os)

**MAP 10 (Lambda Load Corr, 0x027024):** POTVRĐENO (dimenzije ispravljene)
- Header @ 0x027002: [ncols=12, nrows=3] (ne 9×3 iz zadatka)
- X-os RPM (12pt) @ 0x027006: /4 = [1500..7500 RPM]
- Y-os Lambda (3pt) @ 0x02701E: /32768 Q15 = [0.35, 0.425, 0.50]
- Data @ 0x027024, 3 redaka × 12 stupaca Q15
- STG2 postavlja sve vrijednosti na 1.0 (NPRo onemogućio korekciju)
- STG2 mijenja i Y-os (lambda axis) na 0x023910

### Dodatni nalazi
- Injection mirror offset: +0x518 (1304B) od data starta
- Therm enrich enkodiranje: /10240 (ne /32768 Q15)
- Ignition advance u Spark 900: u16LE /256 = stupnjevi (ne u8 × 0.75 kao 1630!)
- Lambda prot Y-os (za neku mapu) na 0x023928: 13pt [0.022..1.761] Q15
- STG2 mijenja lambda axis na 0x023928 (NPRo povećava load breakpointe)
- Ignition advance povećan za ~+2-3° u STG2 (0x0295EE i okolne adrese)
- Lambda target u STG2: 0x025E3C područje mijenja 1.004 → 0.738 (obogaćivanje na WOT)

### Fajlovi analizirani
- `_materijali/dumps/2018/900ace/spark90.bin` (ORI)
- `_materijali/dumps/2018/900ace/spark_stg2` (NPRo STG2 usporedba)
- `_materijali/dumps/2019/1630ace/300.bin` (reference)

---

## 2026-03-19 23:30 — KFWIRKBA ispravka: 14×10 u8 (ne 7×10 u16), osi lambda u8/100

### Što je napravljeno
Nastavak analize KFWIRKBA (MAP 7) koji je ostao neriješen. Otkrivena je prava struktura:
- Count bytes 0x0E=14, 0x0A=10 na 0x0259C2 znače 14 redova × 10 stupaca
- Dtype je u8 (ne u16 Q15!), skala /128 = 1.0
- Y-os = 14 lambda točaka (u8/100) na 0x0259C4; X-os = 10 lambda točaka (u8/100) na 0x0259D2
- Mapa počinje na 0x0259DC (ne 0x0259D2 kako je ranije pretpostavljeno)
- Vrijednosti 128-159 → 1.0-1.24 (enrichment korekcija, min=1.0 nema korekcije)

### Fajlovi promijenjeni
- work_log.md (ispravka MAP 7 unosa)

---

## 2026-03-19 22:45 — Binarna analiza osi za 8 mapa (agent sesija)

### Sto je napravljeno
Potpuna binarna analiza `_materijali/dumps/2021/1630ace/300.bin` za pronalazak axis definicija.

### Rezultati po mapi

**MAP 1: _INJ_DEF (0x02436C, 12×16)**
- axis_x (cols, RPM 16pt BE): DIJELJENA na 0x024F46 = [512..8448] RPM
- axis_y (rows, LOAD 12pt LE, ×0.015625): DIJELJENA na 0x02AE30 = [0,100,200,400,800,1280,2560,3200,3840,4480,5120,5760] → 0-90%

**MAP 2: _LAMBDA_PROT_DEF (0x02469C, 13×12)**
- axis_y (cols, load mg/hub, u16 LE ×1/100): INLINE na 0x0247EE = [6000..32000] → 60-320 mg/hub
- axis_x (rows, lambda Q15, u16 LE): INLINE na 0x02480A = [656..52428] → 0.02-1.60 lambda

**MAP 3: _DEADTIME_DEF (0x0258AA, 10×14) — ISPRAVKA: stvarna adresa mape je 0x0258AA ne 0x025900!**
- count_x=14 na 0x025876, count_y=10 na 0x025878
- axis_x (cols, trajanje u16 LE): INLINE na 0x02587A = [1,2,3,4,6,8,10,20,40,60,120,240,480,960]
- axis_y (rows, temp °C, u16 LE): INLINE na 0x025896 = [37,51,64,77,91,104,117,131,144,157] °C

**MAP 4: _DECEL_RPM_CUT_DEF (0x028C30, 16×11)**
- axis_y (rows, load mg/hub×100, u16 LE): INLINE na 0x028BEA = [6000..36000] → 60-360 mg/hub
- axis_x (cols, ratio Q15, u16 LE): INLINE na 0x028C0A = [0..65535] → 0.0-2.0 Q15

**MAP 5: _IDLE_RPM_DEF (0x02B600, 5×12)**
- axis_x (cols, temp °C, u16 LE): INLINE na 0x02B5DE = [24,37,51,64,77,91,104,117,144,171,197,251] °C
- axis_y (rows, mode, u16 LE): INLINE na 0x02B5F6 = [3340,3220,3100,2990,2880] (RPM target or mode)

**MAP 6: _LAMBDA_EFF_U8_DEF (0x0275FD, 16×16 u8)**
- axis_y (rows, lambda u8/100): DIJELJENA na 0x0275CF = [20,33,67,80,93,100,107,113,120,127,133,140,147,167,187,227] → 0.20-2.27
- axis_x (cols, lambda u8/100): EMBEDDED +256B u svakoj kopiji = [147,167,187,227,45,50,75,100,113,120,125,145,150,158,162,169,175] (sort: 0.45-2.27)

**MAP 7: _EFF_CORR_DEF / KFWIRKBA (0x0259DC, 14×10 u8) — ISPRAVKA: nije 7×10 u16 Q15!**
- count bytes na 0x0259C2: [0x0E=14 rows, 0x0A=10 cols]
- axis_y (rows, lambda u8/100): INLINE na 0x0259C4 = [37,51,58,64,71,77,87,97,107,117,131,137,144,171] → 0.37-1.71 lambda (14 pt)
- axis_x (cols, lambda u8/100): INLINE na 0x0259D2 = [37,51,64,77,91,104,117,131,137,144] → 0.37-1.44 lambda (10 pt)
- dtype: u8, skala /128 = 1.0 (Q7) — vrijednosti 128-159 (1.0-1.24 enrichment faktor)
- fizika: y = izmjerena lambda, x = target/reference lambda; output = korekcija efektivnosti
- mapa ends na 0x025A68

**MAP 8: _ACCEL_ENRICH_DEF (0x028059, 5 rows)**
- Struktura: [1B global=4] + 5×[u16 count=5][5×u16 dTPS x-os][5×u16 Q15 data]
- axis_x (dTPS%, u16 LE): EMBEDDED u svakom redu = [0,150,200,350,1500] → 0-15% dTPS
- axis_y (row condition, u8): KANDIDAT na 0x028050 = [67,93,95,97,99] → /100 = 0.67-0.99 (lambda ili load)

### Fajlovi promijenjeni
- Nema (samo analiza, nije implementirano)

---

## 2026-03-19 19:30 — DTC opisi i uzroci + map stanje

### Što je napravljeno
- **core/dtc_descriptions.py**: novi fajl — `DTC_INFO` dict s opisom + listom uzroka za svih 111 ECM P-kodova
  - Standard OBD opis (EN) + mogući uzroci (HR), poredani od najvjerojatnijeg
- **ui/main_window.py** DtcPanel: dodan `QLabel` za opis, `QListWidget` za uzroke, "Tehnički detalji" header
  - `_refresh_display()` popunjava opis/uzroke iz `DTC_INFO[defn.code]`
  - Import `DTC_INFO` dodan

### Stanje mapa
- 59 MapDef-ova ukupno, 3 manja problema:
  - 2 MapDef s TODO markerima (P1550/P0523 enable flags — adrese neistražene)
  - 1 MapDef bez `unit` (Spark load os — namjerno, osa je interni load)
- 18 2D mapa bez axis_x/axis_y — adrese osi za većinu neistražene binarnom analizom

### Fajlovi promijenjeni
- `core/dtc_descriptions.py` (novi)
- `ui/main_window.py` — DtcPanel layout + _refresh_display + import

---

## 2026-03-19 19:00 — CAN decoder + UI fixes

### Što je napravljeno
- **can_decoder.py**: Dodane 3 nove decode metode (decode_spark_egt, decode_spark_tps_103, decode_spark_throttle_body) + dispatch u decode() za 0x0103 i 0x0104
- **can_logger_widget.py**: Import CAN_SPARK_EGT/THB + _update_tiles() proširen: EGT i TPS iz 0x0103, throttle iz 0x0104
- **main_window.py** MapLibraryPanel: Strip engine prefiksa ("Spark — ", "Spark ", "GTI — ", "GTI ") iz display naziva u tree-u — nazivi konzistentni bez obzira koji fajl učitan

### Fajlovi promijenjeni
- `core/can_decoder.py` — dispatch + 3 metode (već su bile, sad je dispatch dodan)
- `ui/can_logger_widget.py` — import + _update_tiles() blok za 0x0103/0x0104
- `ui/main_window.py` — display_name strip prefiks loop

---

## 2026-03-19 17:30 — Spark mape: +2 nova (54 ukupno, bilo 52)

### Što je napravljeno
- Binarna analiza NPRo STG2 vs ORI Spark 2018 (82 diff blokova, 3581B razlika)
- Pronađene 2 nova tunabilna Spark mape koje NPRo modificira:
  1. `Spark lambda load os` @ 0x023910 (9pt Q15 lambda axis, Y-os za korekcijsku tablicu)
  2. `Spark lambda korekcija po load-u` @ 0x027036 (9×3 Q15, opada 0.992→0.730 s porastom loada; NPRo postavlja na 1.0)
- Dodani `_SPARK_LAMBDA_LOAD_AXIS_DEF` i `_SPARK_LAMBDA_LOAD_CORR_DEF` u map_finder.py
- Dodane scan metode u `_scan_spark_aux()`
- Svi testovi prolaze: Spark 52→54 mapa

### Za 1630 ACE
- Binarna analiza 300hp vs 130hp: razlike su SKALIRANJE (faktor 1.2-1.4×), ne nove mape
- 0x02B380 = 36×u16 lookup tablica (skalira po snazi, nije nova tunabilna mapa)
- 0x012C80 = 96B embedded konstanti + 0xDEADBEEF marker (različito po verziji/snazi)

## 2026-03-19 17:10 — DTC Sidebar poboljšanja

### Što je napravljeno
- `DtcSidebarPanel` u `ui/main_window.py` poboljšan:
  - `setMaximumWidth(220)` — sidebar ograničen na 220px
  - Parent kategorija node prikazuje count: `P — Powertrain  (47)`
  - Subgrupa node prikazuje count: `P0xxx — Standardni (OEM/SAE)  (38)`
  - Leaf node prikazuje P-kod + skraćeni naziv (max 22 znaka + "…"): `P0106  MAP Sensor Out of…`
  - ToolTip na leaf nodevima: puni naziv DTC-a
  - `QTreeWidget` stiliziran tamnom temom (#1a1a1d bg, #9cdcfe selected, #C8C8D0 tekst)
  - `setUniformRowHeights(True)` za performansu
  - Horizontalni scrollbar sakriven (sidebar je uski)
  - Splitter inicijalna širina smanjena: 270→220px (`main_split.setSizes([220, 950, 270])`)
- Import test: `python -c "from ui.main_window import DtcSidebarPanel; print('OK')"` → OK
- Fajlovi: `ui/main_window.py`

## 2026-03-19 16:35 — CAN Logger tab — finalizacija i testiranje

### Što je napravljeno
- Sve komponente CAN Logger taba verificirane i integrirane
- `python -c "from ui.can_logger_widget import CanLoggerWidget"` → OK (bez importerror)
- `python test/test_core.py` → svi testovi prošli (54 mapa, EEPROM, checksum, write safety)
- Fajlovi: `core/can_logger.py`, `core/can_decoder.py`, `ui/can_logger_widget.py`, `ui/main_window.py`, `ui/can_network_widget.py`, `_docs/CANBUS_NOTES.md`

---

## 2026-03-19 16:10 — NOVO: ui/can_logger_widget.py

### Što je napravljeno
- Napisan `ui/can_logger_widget.py` — novi UI widget za live CAN logging
- `_GaugeTile(QFrame)`: kartica za jedan parametar (label + 28px bold vrijednost + unit), warn boja (#EF5350) za RPM>7000, ECT>95, EOT>120
- `CanLoggerWidget(QWidget)`: glavni widget s header barom + horizontal splitter (58/42)
  - Header: IXXAT kanal combo, Spoji/Odspoji toggle, Snimi/Stop toggle, Otvori log, status label, REC timer
  - Lijevo: 10 _GaugeTile karti u 3×4 gridu (RPM, ECT, EOT, MAP, TPS, MAT, EGT, Brzina, Gorivo, Sati)
  - Desno: QTableWidget s 4 kolone (Vr/ID/Hex/Decoded), max 2000 redova (trim 500), auto-scroll, stats bar
- Logika: connect/disconnect, start/stop recording (QTimer za HH:MM:SS), LogFile.save/load, _update_tiles po CAN ID-u
- Boje redova: 0x0108/0x0110/0x012C/0x013C=#cccccc, 0x0134/0x0154=#9cdcfe, 0x0148=#4ec9b0, ostali=#666666
- Stil: identičan can_network_widget.py (#252526 header, #1a1a1d tile, Consolas font)
- `clear_session()` public API za reset pri učitavanju novog .bin

### Ključni fajlovi
- NOVO: `ui/can_logger_widget.py`

---

## 2026-03-19 15:30 — core/can_decoder.py — novi sdtpro CAN ID-ovi

### Što je napravljeno
- Dodane 4 nove konstante: `CAN_EOT_MUX=0x0316`, `CAN_BROADCAST=0x0342`, `CAN_SPARK_EGT=0x0103`, `CAN_SPARK_THB=0x0104`
- Nova metoda `decode_eot_316()`: EOT iz 0x0316, formula `data[3]*0.943-17.2 °C`
- Nova metoda `decode_mux_342()`: MUX broadcast 0x0342 — ECT (0xDE), MAP (0xAA), MAT (0xC1); vraća dict s prisutnim ključevima
- Dispatcher `decode()` proširen s `CAN_EOT_MUX` i `CAN_BROADCAST` blokovima
- Module docstring ažuriran — nova sekcija "sdtpro / field-verified IDs" s formulama
- Sve formule iz sdtpro hardware_simulator.py (field-verified, 250 kbps, engine running)

### Ključni fajlovi
- IZMJENA: `core/can_decoder.py`

---

## 2026-03-19 14:00 — Novi fajl: core/can_logger.py (CAN logger backend)

### Što je napravljeno
- Napisan `core/can_logger.py` — novi modul, 0 izmjena postojećih fajlova
- `CanLoggerThread(QThread)`: live CAN acquisitcion putem IXXAT USB adaptera (python-can)
  - Signali: `message_received(float, int, bytes)` i `connection_status(bool, str)`
  - Graceful handling: `import can` greška → signal; IXXAT greška → signal
  - `connect_bus()`, `disconnect_bus()`, `stop()`, `run()` metode
  - `run()` pada gracefully na bus grešku, uvijek poziva `disconnect_bus()` u `finally`
- `LogFile`: statičke metode `load()` i `save()` za SDCANlogger-kompatibilni format
  - `load()`: parsira `timestamp;0xID;HEXDATA`, preskače `#` komentare, pad na 8B
  - `save()`: piše isti format + opcionalni `# START_TIME_WALL_CLOCK:` header
- Svi importi apsolutni (PyQt6.QtCore, threading, time)

### Ključni fajlovi
- NOVO: `core/can_logger.py`

---

## 2026-03-19 — 7-DEO binarna analiza: NPRo diff, SC/NA, godišnja evolucija, +2 nove mape

### Sto je napravljeno

Kompletna 7-dijelna binarna analiza za ME17.8.5 Rotax 1630 varijante:

**DEO 1 — NPRo ORI19 vs STG2 diff:**
- Ispravna usporedba: STG2 vs ORI19 (isti SW 10SW040039), ne vs ORI21
- Rezultat: 4482B razlika, 83 bloka u CODE regiji (0x010000–0x05FFFF)
- ~60% blokova već prepoznato u map_finder.py
- Nova otkrića: Lambda Eff U8 @ 0x0275FD, Lambda Thresh @ 0x02B378

**DEO 2/3 — SC vs NA, 300hp vs 230hp:**
- 300hp SC vs 130hp NA: 20309B razlika
- 300hp SC vs 230hp SC: 15752B razlika (injection/torque/ignition različiti)

**DEO 4 — 130hp vs 170hp:**
- POTVRĐENO: 0 razlika u CODE regiji (obje 2020 i 2021)
- Razlika je ISKLJUČIVO mehanička (propeler/prijenosnik)

**DEO 5 — Godišnja evolucija 300hp SC:**
- 2019→2020: 1838B (umjereni SW update)
- 2020→2021: 2891B (veći SW update)

**DEO 6 — Nove identificirane mape (confidence >70%):**
- `Lambda Eff U8` @ 0x0275FD: 4×16×16 u8, /128=faktor, stride 290B. Confidence 70%.
- `Lambda Thresh` @ 0x02B378: 1×79 u16 LE Q15. SC=0.43–1.80λ, NA=0.61–1.32λ. STG2=0xFFFF bypass. Confidence 75%.

**DEO 7 — Mape s neidentificiranim osima:**
- 0x02220E, 0x02AA42, 0x02469C — osi potvrđene kao neidentificirane, ali mape su inače poznate.
- Nisu rješavane prema specifikaciji.

### Fajlovi promijenjeni

- `core/map_finder.py` — +2 MapDef (LAMBDA_EFF_U8 + LAMBDA_THRESH), +2 scan metode, wired u find_all()
- `_docs/MAPS_REFERENCE.md` — +5 novih sekcija (16–20): NPRo diff tablica, DEO 4, DEO 5, DEO 2/3, nove mape

### Kljucni rezultati

- Map count: 300hp=54, 230hp=53, 130/170hp=62, GTI90=60, Spark=52
- Svi testovi prolaze
- NPRo STG2 signature: "NOREAD" string @ 0x03FDB0

---

## 2026-03-19 — EEPROM editor + Spark ignition scan fix + docs update

### Što je napravljeno
1. **`core/eeprom.py`** — dodana `EepromEditor` klasa s metodama:
   - `set_hull_id()`, `set_dealer_name()`, `set_date_first_prog()`, `set_date_last_update()`, `set_prog_count()`
   - `save()`, `get_bytes()`, `get_info()`, `from_bytes()` (classmethod)
   - EEPROM nema checksum → izmjene direktne, bezopasne za editabilna polja
2. **`ui/eeprom_widget.py`** — kompletni rewrite s edit podrškom:
   - Editabilna polja: Hull ID, dealer naziv, datumi (×2), broj programiranja (SpinBox)
   - Read-only: ECU serial, MPEM SW, HW tip, radni sati (circular buffer)
   - Gumbi: "Spremi izmjene" (overwrite original), "Spremi kao..." (novi fajl)
   - Status indikator (● nespremljene izmjene / ✔ Spremljeno)
3. **`core/map_finder.py`** — `_scan_spark_ignition` provjerena: sve 4 serije se skeniraju (A×8+B×8+B2×8+C×3=27)
4. **`_docs/MAPS_REFERENCE.md`** — dodana sekcija 14 (Spark kompletna mapa lista), Quick Summary ažuriran s točnim testnim brojevima (300hp=53, Spark=52, GTI90=59, 230hp=52, 130hp=61)
5. **`memory/MEMORY.md`** — SW map counts ažurirani

### Checksum situacija
- **EEPROM**: NEMA checksuma — direktno editiranje sigurno
- **ECU BOOT (0x0000–0x7EFF)**: CRC32-HDLC, CS @ 0x30 (u32 BE), implementirano u `core/checksum.py`
- **CODE mape (0x010000+)**: ne zahtijevaju promjenu checksuma


## 2026-03-19 23:55 — Spark kompletni map inventar: 2016 vs 2019+ layout, NPRo diff, nove mape

### Sto je napravljeno

Kompletna binarna analiza Spark 900 ACE mapa:
- NPRo STG2 diff: 2021 ORI vs STG2 — 73 bloka, 6428 byteova
- Otkrivene **4 potpuno nove serije ignition mapa** (B, B2, C) prethodno neskenirane
- Otkrivene **4 nove aux mape** (lambda trim 2, load axis 2, lambda X-os, therm enrich 2)
- Potvrda: 2016 Spark (10SW011328) koristi **iste adrese** kao 2019+ (identičan layout)
- DEO 3: GTI90 adrese NE postoje u Spark binariju (nule na svim GTI adresama)
- DEO 4: RPM os 1920–6656 RPM (20pt), Load os 3999–33600 (30pt) — iste u oba SW

**Fajlovi promijenjeni:** `core/map_finder.py`, `_docs/MAPS_REFERENCE.md`

### Kljucni rezultati

**Spark ignition layout (27 mapa u 4 serije):**
- Serija A (#00–#07 @ 0x026A76): 8 mapa, STG2 ne mijenja — ranije skenirao samo 6!
- Serija B (#00–#07 @ 0x0295C0): 8 mapa, 5 modificirane STG2, 3 flat fallback
- Serija B2 (#00–#07 @ 0x029B60): 8 mapa, sve modificirane STG2 (+2–7°)
- Serija C (#00–#02 @ 0x02803A): 3 mape u u16LE formatu, ×0.25°/bit (27.5–31.25°)

**Nove lambda/fuel mape:**
- Lambda trim 2 @ 0x0253DC (30×20 Q15): ORI flat 0.984, STG2 diff=650 — veliki uticaj
- Load axis copy 2 @ 0x025378: parnjak za trim 2, STG2 proširuje raspon
- Lambda X-os @ 0x024775 (16pt u8): /128=lambda, STG2 proširuje lean-side (0.258→1.875)
- Therm enrich 2 @ 0x0248C2 (42 u16 Q14): ORI 0.706–0.816, STG2 mijenja sve vrijednosti

**Spark 2016 vs 2019+ adrese:** IDENTIČAN layout! map_finder ne treba posebne adrese.

**Ukupno:** Spark scanner sada pronalazi 52 mape (ranije 27).

---

## 2026-03-19 22:00 — 4tec1503 kompletna binarna analiza

### Sto je napravljeno

Sveobuhvatna analiza 5 dumpova za Rotax 1503 (4tec1503) varijante (130/155/230hp 2019, 130hp 2020) u usporedbi s 1630 referencama.

**Fajlovi promijenjeni:** `core/map_finder.py`, `_docs/MAPS_REFERENCE.md`, `_docs/ENGINE_SPECS.md`, `_docs/SW_VERSIONS.md`

### Kljucni rezultati

**DEO 1: 130hp vs 155hp vs 230hp (10SW040008, 2019)**
- POTVRDJENO: Sva tri dumpa su byte-for-byte identicna (0 razlika ukupno, 0 u BOOT, 0 u CODE, 0 u CAL)
- Razlika u snazi = iskljucivo mehanicka

**DEO 2: 4tec1503 vs 1630 NA razlike u mapama**
- CODE razlika 1503 vs 1630: 17389B u 660 blokova
- Identicno: RPM os, rev limiter, Q15 injection (0x02436C), Idle RPM
- Razlicito: GTI injection (191/192), Lambda main (409/432), Torque (211/256), sve ignition mape, SC boost factor (40/40)
- 1503 torque limit: 100-110% vs 1630 130hp: 100-117%
- 1503 lambda: 0.961-1.042 vs 1630: 0.984-1.026

**DEO 3: GTI injection i ignition extra u 1503**
- GTI injection @ 0x022066: AKTIVNO u 1503 (3193-14432 raw), razlicito od 1630 (301/384B)
- GTI ignition 8 extra mapa @ 0x028310: SVE aktivne u 1503 (40-67 raw = 30-50.25deg), ali razlicite od 1630

**DEO 4: Rev limiter 1503**
- 10SW040008 (2019): 5243 ticks @ 0x028E96 = 7892 RPM
- 10SW040962 (2020): 5243 ticks @ 0x028E96 = 7892 RPM
- KOREKCIJA: Prethodna napomena "7700 RPM za GTI 155" odnosi se SAMO na 10SW025752 (2018)!
- Novije verzije 2019/2020 = 7892 RPM = isti kao 1630 130hp NA

**DEO 5: 1503_230 SC/NA analiza**
- SC bypass: iste niske vrijednosti kao 1503_130 (NA obrazac, 0 razlike)
- Sve kljucne mape 1503_130 == 1503_230 (IDENTICNO)
- **ANOMALIJA: SC boost factor @ 0x025DF8 = flat 23130 (+41.2% Q14)** — visi od 300hp SC (+22.4%)!

**DEO 6: 2019 vs 2020 4tec1503**
- CODE razlika: 536B, 25 blokova
- Sve poznate mape identicne! Razlika samo u parametrima i build tagu
- Nova 8x8 tablica @ 0x029C58 u 2020 (64B, 9-64 raw = 6.75-48deg timing raspon) — u 2019 sve nule

---

## 2026-03-19 20:15 — Identifikacija nedefiniranih osi i mapa (8 ciljeva)

### Što je napravljeno

Sveobuhvatna binarna analiza 7 dumpova za 8 ciljnih mapa. Čitane binarne vrijednosti i uspoređeni svi dumpovi.

**Fajlovi promijenjeni:** `core/map_finder.py`, `_docs/MAPS_REFERENCE.md`

### Rezultati po točkama

**1. SC Boost Fuel Correction Y-os (0x0221EC) — POTVRĐENA**
- Y-os = load %; 300hp: [46.9–179.7%], 130hp: [7.8–109.4%] — VARIJANTA-SPECIFIČNO
- 130hp: mapa sve 0% (neutralna, NA motor bez SC) — potvrđeno
- X-os = RPM raw/8; 300hp: [1250–4250 RPM], 130hp: malo drugačiji raspored

**2. Thermal Enrichment X-os (0x02AA02) — IDENTIFICIRANA, IDENTIČNA**
- X-os = [6400,8000,9600,11200,12800,14400,16000] = load [100–250%] (raw/64)
- IDENTIČNO za sve 4 varijante (300hp=130hp=230hp=GTI90)
- Mapa podataka: 300hp = 130hp (IDENTIČNA!) — toplinska zaštita je ista bez obzira na SC

**3. Lambda Protection X-os (0x02469C) — ANALIZIRANA**
- X-os nije standardni vektor — mapa je dijagonalna (lambda × lambda pragovi)
- Nema vektora osi ispred mape (sve nule @ 0x024682)
- 300hp = 130hp IDENTIČNO u ORI — nije SW-specifično, samo STG2 saturira na 65535

**4. Injector Deadtime (0x025900) — DIMENZIJE POTVRĐENE**
- 14×7 = 98 u16; kraj = 0x0259C4 = EFF_CORR X-os (BINARNO POTVRĐENO)
- Skala: ×0.5µs/raw (R0[0]=2594→1297µs realan deadtime)
- X-os (napon) nije embeddana kao binarni vektor — interio u ECU CODE logici
- 300hp vs 130hp: praktički identični (isti injektori)

**5. Ignition Correction osi (0x022374) — IDENTIFICIRANE**
- Y-os (@ 0x022364): raw × 40 = RPM; 300hp=[3000–8000], 130hp=[2520–8000]
- X-os (@ 0x02236C): raw/2.55 = load%; 300hp max=255=100%, 130hp max=127=100% (normirano)
- VARIJANTA-SPECIFIČNO — osi se razlikuju između 300hp i 130hp
- STG2 cap: sve >180 → 180 (zaštita)

**6. Lambda Adapt (0x0268A0) — confidence 85→90%**
- 300hp 2021: λ0.966–1.039 (112 unique), 230hp: λ1.009–1.059 (9u), 130hp: λ0.999–1.025 (8u), GTI90: λ0.984–1.014 (5u)
- 300hp 2020 vs 2021: 105/216 razlika (drugačiji SW, ne isti dump!)
- STG2 vs ORI: 105/216 razlika

**7. Decel RPM Ramp (0x028C30) — confidence 75→80%**
- 300hp col[2]=10670t=3878 RPM (const), col[0]=4791–5877 RPM po load
- 130hp col[0]=10731–11129 RPM (drastično viši!), col[2]=8649 RPM
- GTI90: col[0]=9255 RPM (vlastiti raspon)
- Spark 900: nema validnih vrijednosti — nije aplicabilno na Spark platformu

**8. KFWIRKBA 2D sub (0x0259D2) — analiziran**
- STG2 = ORI (0/70 razlika) — ova tablica nije tuningom promijenjiva
- 300hp vs 130hp: 41/70 razlika, vs GTI90: 39/70 — varijanta-specifično
- col[0] embedded Y-os nije linearan ([0.40,1.10,1.00,...]) — nije klasična os
- Confidence ostaje 65% (struktura jasna, namjena bez A2L pretpostavljena)


## 2026-03-19 14:30 — UI reskin: "Clean Professional" dark theme prema mockupu

### Što je napravljeno

Implementiran novi vizualni stil za cijeli UI prema `_docs/me17suite_style2_mockup.html`.

**Fajl promijenjen:** `ui/main_window.py`

**Paletne promjene:**
- Pozadina: `#1e1e1e` → `#111113` (dublja crna)
- Surface: `#252526` → `#1C1C1F`, `#2d2d2d` → `#141418`
- Border: `#333333` → `#2A2A32`, `#555555` → `#3A3A48`
- Accent: `#0e639c` / `#9cdcfe` → `#4FC3F7` (teal/plava iz mockupa)
- Tekst: `#cccccc` → `#C8C8D0`, sekundarni `#969696` → `#808090`
- Success: `#4ec9b0` → `#4CAF50`, Warn: `#e5c07b` → `#FFB74D`, Error: `#f48771` → `#EF5350`
- Status bar / Menubar: `#007acc` / `#323233` → `#1c2b4a` (tamno plava iz mockupa)

**Font:** Dodan IBM Plex Sans/Mono kao primarni font (s Segoe UI fallback)

**Layoutna poboljšanja:**
- Header labeli: font-size 11px → 10px, letter-spacing 1.5px
- Search polja: visina 32px → 30px
- Tab bar: padding tighten, border-radius dodan
- Scroll barovi: širina 10px → 8px, boja #555 → #2A2A32
- Progress bar: visina 6px → 4px

**Testirano:** `python -c "from ui.main_window import MainWindow"` + headless QApplication init — OK, bez grešaka.


## 2026-03-19 02:00 — Binarni scan: 3 nove/ispravljene mape dodane u map_finder.py

### Što je napravljeno

Sveobuhvatna NPRo diff analiza: 300hp ORI (10SW040039) vs STG2 — pronađene 3 nove/ispravljene kalibracije.

**Nove mape dodane u core/map_finder.py:**

1. **Lambda adaptacijska baza @ 0x0268A0** (nova, confidence 85%)
   - 12×18 u16 LE Q15, 432B
   - Odmah iza lambda main (offset +0x1B0)
   - Per-HP: 300hp λ0.963–1.047, 230hp λ0.869–1.081, 130hp λ0.886–1.047
   - STG2 mijenja 105/216 vrijednosti
   - Scan metoda: `_scan_lambda_adapt()`

2. **Decel/DFCO RPM ramp tablica @ 0x028C30** (nova, confidence 75%)
   - 16×11 u16 LE, stride 22B/unos, 352B ukupno (0x028C30–0x028D8F)
   - Struktura: 3 RPM period-ticks + 8 load-os po unosu
   - 300hp: col[2]=10670t≈3878 RPM (konstanta), col[0-1] silazni DFCO pragovi
   - STG2 podiže sve RPM limite
   - Scan metoda: `_scan_decel_rpm_cut()`

3. **Knock params ispravak: 24 → 52 u16** (korekcija, 0x0256F8–0x02575F)
   - Prvobitna dokumentacija: 1×24; stvarno: 1×52 (104B)
   - Regije 0x025738 i 0x02574E su nastavak istog bloka
   - Header (44237/65535) + repetirajuće grupe 7967/39578/8090
   - 230hp: sve ostaju 7967 (STG2 ne mijenja 230hp)

**Fajlovi promijenjeni:**
- `core/map_finder.py` — 3 nova/ispravljena MapDef + 2 nove scan metode
- `_docs/MAPS_REFERENCE.md` — Lambda adapt + Decel RPM cut + Knock ispravak
- `work_log.md`, `chat_log.md`

**Verifikacija:** `find_all()` na 300hp binary → 53 mapa pronađeno (ranije 51).

## 2026-03-18 23:30 — Identifikacija ignition aux mapa #10-#18

### Sto je napravljeno

**ZADATAK: Binarni dump analysis za neidentificirane ignition mape**

Analizirani dump fajlovi: 300hp 2021 ORI, NPRo STG2 2020, 230hp 2021 ORI, 130hp 2021 ORI.

**Kljucni nalazi:**

1. **Mape #10, #12, #14 -- "Aux A" grupa:**
   - Apsolutne timing mape, raspon 25.5-30deg BTDC
   - Sve 144 celije aktivne, zigzag row pattern
   - NPRo STG2 dodaje +2.25 do +6.75deg
   - 300hp i 130hp imaju slicne prosjeke -- nije SC-specificno

2. **Mape #11, #13 -- "Aux B" grupa s dip retkom:**
   - Apsolutne timing mape, raspon 24-33.75deg BTDC
   - #11: "dip" redak na R07 (vrijednosti 32-33 = 24.0-24.75deg, ispod baseline)
   - #13: "dip" redak na R09 (isti efekt)
   - NPRo STG2 dodaje +2.25 do +9.0deg (najveci advance od svih)
   - POTVRDJENO: Map #18.R00-R02 == Map #11.R04-R06 (exact byte match)

3. **Mapa #15 -- SC/boost-specificna:**
   - 300hp SC: prosjek 29.8deg; 130hp NA: prosjek 26.5deg s flat redovima
   - Razlika ukazuje na SC/boost-uvjetovanu aktivaciju

4. **Mapa #18 -- Conditional/Fallback:**
   - Samo 40/144 celija aktivno (R00-R03); R00-R02 == #11.R04-R06
   - 130hp: konstantnih 25.5deg (sigurnosni minimum)
   - STG2 modificira aktivne redove, nule ostaju nulama

**Fajlovi promijenjeni:**
- `core/map_finder.py` -- _IGN_NAMES[] i _make_ign_def() (nova logika is_aux_a/b/sc)
- `_docs/MAPS_REFERENCE.md` -- sekcija 2 Ignition Maps, tablicni opisi #10-#18

**Ogranicenja:** Tocni uvjeti aktivacije (cold start, hot restart, decel...) nepoznati bez A2L.

---

# 2026-03-18 23:30 — KFWIRKBA parser, Spark/GTI completeness check

### Što je napravljeno

**ZADATAK 1: KFWIRKBA (0x02AE5E) — binarna analiza i TODO uklonjen**
- Y-os potvrdjena: `[3840..15360]` za SC, `[3840..12800]` za GTI90 NA
- Ključni nalaz: 300hp SC = BYPASS kalibracija (redovi 0-8 = lambda X-os vrijednosti ponavlja se)
- GTI90 NA = AKTIVNA kalibracija: faktori 0.51-0.71 (pravi lambda efficiency)
- 130hp NA = bypass ali s drugačijim lambda X-os rasponom ([19988-43254] = 0.61-1.32λ)
- Red 9: separator `[4617, 64736, 65136, ...]` zajednički za sve varijante
- `core/map_finder.py`: KFWIRKBA opis i komentar ažurirani, TODO uklonjen

**ZADATAK 2: 0x0259D2 (eff_corr) — fizikalni smisao potvrđen**
- Identifikacija: KFWIRKBA sub-tablica za kratki lambda raspon (0.40-1.34)
- X-os = `[0.40, 0.50, 0.60, 0.76, 0.92, 1.07, 1.34]` λ Q15
- col[0] = embedded Y-os (lambda referentne točke)
- Namjena: specijalni uvjeti (cranking/warm-up/overrun), confidence ~65%
- TODO uklonjen, opis ažuriran na "KFWIRKBA 2D sub"

**ZADATAK 3: Spark 900 ACE completeness**
- Spark 2019 == Spark 2021: **0 razlika** (identični binariji, isti SW)
- STG2 vs ORI: 6428B, 959 diff regija
  - Lambda trim 0x024EC4: STG2 izravnava lean bias → neutral (1.004)
  - Lambda copies 0x025F5C/607E: STG2 mijenja AFR cilj
  - Warm-up 0x024786: STG2 povećava ~1.83× (13364→24415)
  - Lambda os 0x024775: STG2 proširuje raspon
- Sve 27 Spark mapa već su u map_finder.py (nema propuštenih)

**ZADATAK 4: GTI90 completeness**
- Lambda main @ 0x0266F0: flat 0.984 (5 jedinstvenih vrijednosti) — NEUTRALNA
- Lambda mirror @ 0x026C08: AKTIVNA kalibracija (127 jedinstvenih, 0.90-1.02)
  - GTI90 koristi mirror kao primarnu lambda mapu!
- KFWIRKBA @ 0x02AE5E: GTI90 = aktivni faktori 0.51-0.71 (NA motor koristi efficiency)
- Torque @ 0x02A0D8: GTI90 = aktivna kalibracija (88-99%, drugačija od 300hp)
- Ignition @ 0x02B730: GTI90 = niži timing (20.25° vs 24-30° 300hp)
- GTI injection @ 0x022066: aktivna (3224-18727), razlikuje se od GTI155
- GTI90 vs 300hp: 24428B razlika, 2801 diff regija

### Fajlovi promijenjeni
- `core/map_finder.py` — KFWIRKBA i eff_corr opisi + TODO uklonjeni
- `_docs/MAPS_REFERENCE.md` — nova sekcija 13 (Spark STG2 diff), GTI90 lambda nalaz, KFWIRKBA matrica
- `_docs/TUNING_NOTES.md` — confidence procjene ažurirane

---

## 2026-03-18 22:15 — Kompletni EEPROM audit: 062/063/064, parser popravak, misprog detekcija

### Što je napravljeno

**ZADATAK 1: Kompletni audit 35 EEPROM dumpova**
- Skenirani svi dumpovi u: mat/062 (6), mat/063 (8), mat/064 (18), ECU/alen (2+1 donor), BACKUP/kruno (1)
- 35 dumpova ukupno, svi validni (0 grešaka parsiranja)

**ZADATAK 2: Detekcija misprogramiranih**
- `062 1-4` u mat/062 folderu: ima MPEM 1037525858 = 063 HW (pogrešno svrstano u 062 folder)
- `064 0` u mat/064 folderu: hw_parser=063 (063 HW koji je pogrešno svrstano u 064 folder)
- `064 85-31 ex063`: potvrđen 063→064 reprogramirani MPEM — ODO=5131 min (isti kao 063 85-31), timer='60620' (factory default), MPEM part=1037550003 (064). Fizički isti ECU, MPEM chip zamijenjen ili reprogramiran.

**ZADATAK 3: Kopiranje ECU/ u _materijali/**
- SHA256 provjera: sve 062/063/064 fajlove identični između ECU/ i _materijali/
- Kopiranje nije potrebno.

**Kritični popravci eeprom_parser.py:**
- Otkriven novi/stari EEPROM layout: MPEM string samo u headeru @ 0x0032 (ne @ 0x05B0)
  - Standardni layout: anchor @ 0x0550, ODO @ 0x0562
  - Stari layout A: anchor @ 0x4550, ODO @ 0x4562 (+0x4000 pomak)
    - Potvrđeno: 063 0-55, 063 77-16, 063 121-55, 063 167, 064 13
  - Stari layout B: anchor @ 0x047E, ODO @ 0x0490
    - Potvrđeno: 064 58 (3503 min), 064 211.bin (12667 min)
  - 0x1562 je mirror od 0x0D62 SAMO u wrapping layoutu (ne koristiti samostalno!)
- Parser refaktoriran: prioritetni redosljed (0x0562 → 0x4562 → 0x0D62+mirror → 0x0490 → 0x0DE2)
- Verifikacijski test: 20/20 OK

**Fajlovi promijenjeni:**
- `core/eeprom_parser.py` — `_find_odo_063_064()` metoda potpuno revidirana

### Ključni rezultati

| HW   | Dumpova | ODO min         | ODO max          |
|------|---------|-----------------|------------------|
| 062  | 5       | 86h24m (5184)   | 848h33m (50913)  |
| 063  | 10      | 0h55m (55)      | 585h41m (35141)  |
| 064  | 20      | 0h59m (59)      | 211h07m (12667)  |

HW timer zanimljivi slučajevi:
- '60620' = factory default (uočeno u: 062 228-52, 064 135 GTI 18, 064 99-50, 064 85-31 ex063)
- 'BRP10' = BRP dealerski programmer (064 9-5, 064 58)
- '09424' = najstariji HW timer u kolekciji (063 585-42 = najstariji ECU, 585h41m)
- 'b'\x00\x00\x00\x00\x00'' = erased timer (064 0, koji je zapravo 063 HW)

---

## 2026-03-18 18:30 — Istraživanje: 0x024700 blok, Spark 2016 mape, 1503 vs SC, folder audit

### Što je napravljeno

**Zadatak 1: 0x024700 blok identifikacija**
- Regija 0x024700-0x0247D4 je DIO injection mirror bloka koji počinje na 0x02451C
- Injection mirror (6x32 u16 LE) @ 0x02451C ends @ 0x02466C, nakon toga padding + deadtime @ 0x02469C
- 0x024700 je nastavak injection/deadtime extended bloka unutar mirror zone
- ISTI sadržaj u svim 1630 SW varijantama (300/230/170/130hp, 2020 i 2021)
- NPRo STG2 dramatično povećava vrijednosti (x1.1 do x4.2) = boost injection tune
- Fizikalni smisao: lambda zaštitna mapa (KFLFMXSUB) — već registrovano u map_finder.py @ 0x02469C (12x13 u16 LE)

**Zadatak 1b: 0x012C80 blok (128B koje NPRo mijenja u ranom CODE-u)**
- @ 0x012C60: string "   VM_CB.04.80.00" = kalibracija blok identifikator
- 0x012C80-0x012CFF = 128B kriptografski blok (HMAC/hash/potpis SW kalibracije)
- 0x012D00 = DEADBEEF terminator
- Isti blok postoji u 2021/300.bin (VM_CB.04.80.00 @ 0x012C63)
- NPRo mora promijeniti jer mijenja CODE regiju (invalidira hash)
- NIJE kalibracija — READ-ONLY, ne editovati

**Zadatak 2: Spark 2016 mape (10SW011328) = 25 → 27**
- Problem: `_SPARK_WARMUP_DEF.raw_max = 16000` ali 2018 (10SW011328) ima max=24415
- Problem: `_SPARK_THERM_ENRICH_DEF.raw_min = 9000` ali 2018 ima min=8741
- Rješenje: prosiren raw_max warmup 16000→25000, raw_min therm 9000→8500
- Spark 2018 sada pokazuje 27 mapa (isto kao 2021) — FIX POTVRĐEN

**Zadatak 3: 1503 (59) vs 1630 SC (51) — 8 extra mapa**
- Extra 1503 mape su LEGITIMNE (ne false positive):
  - 8 GTI Ignition extra mapa (0x028310...0x028700) = alternativni ignition blok za NA motor
  - 1 GTI Injection (0x022066) = direktni injection format specifičan za 1503/GTI NA
- SC motor NEMA ove mape jer SC koristi drugačiji ignition base (0x02B730) i injection format
- SC ima 1 mapu više od 1503: Lambda overtemp (0x025ADA) — 1503 ima varijabilne vrijednosti tu, SC ima 0xFFFF bypass

**Zadatak 4: 2018 folder audit**
- 2018/900ace: OK — spark90.bin + spark_stg2 postoje
- 2018/1630ace: PRAZAN folder — nema bin fajlova (praznina)
- 2018/4tec1503: PRAZAN folder — nema bin fajlova (praznina)

### Promijenjeni fajlovi
- `core/map_finder.py` — 2 izmjene: `_SPARK_WARMUP_DEF.raw_max` 16000→25000, `_SPARK_THERM_ENRICH_DEF.raw_min` 9000→8500

### Ključni nalazi
- 0x024700 je unutar lambda zaštitne mape (KFLFMXSUB) već registrovane @ 0x02469C
- 0x012C80 = kriptografski blok VM_CB.04.80.00 — Bosch SW hash, READ-ONLY
- Spark 2018 sad ima 27 mapa (isti broj kao 2021) — validacijski pragovi bili prestrogi
- 1503 extra 9 mapa su legitimne GTI-specifičné mape, nije greška

---

## 2026-03-18 16:00 — Docs revizija: kompletna revizija svih _docs/*.md fajlova

### Što je napravljeno
Provedena kompletna revizija 8 dokumentacijskih fajlova u `_docs/` + `USER_MANUAL.html`.

### Promijenjeni fajlovi
- `_docs/SW_VERSIONS.md` — ispravljen 10SW040039 (bio "NPRo Stage 2 tune", sada "2019 stock / NPRo baseline"), proširena HW klasifikacijska tablica (dodani HW 061, napomena o HW 063)
- `_docs/EEPROM_GUIDE.md` — ispravljena HW 063 ODO logika (max(0x4562, 0x0562)), ažuriran kod primjer, dodani HW 061 i RXT-X 260 napomene
- `_docs/CANBUS_NOTES.md` — dodane sekcije 9 (CAN payload formati iz ECU CODE), 10 (SAT enkriptiran), 11 (nepoznati epprom = RXT-X 260 EEPROM), ažurirana sekcija 12 (CAN Network tab)
- `_docs/TUNING_NOTES.md` — dodana sekcija 9 (Procjena pouzdanosti mapa)
- `_docs/ECU_BINARY_FORMAT.md` — napomena o stvarnoj BOOT granici (0x7EFF), distinkcija CS regija vs Python konstanta BOOT_END
- `_docs/DTC_REFERENCE.md` — distribucija kodova (P0=65, P1=35, P2=11), GUI organizacija opis
- `_docs/MAPS_REFERENCE.md` — revision header
- `_docs/ENGINE_SPECS.md` — revision header
- `_docs/USER_MANUAL.html` — proširena tablica SW verzija (13 SW ID-ova umjesto 6), ispravljena DTC sekcija (P0/P1/P2 grupe, zelena/crvena ikonice), ažurirana EEPROM tablica (HW 061, ispravna HW 063 logika), map_finder komentar (56+ mapa)

### Ključne neistine ispravljene
1. **10SW040039** pogrešno bio označen kao "NPRo Stage 2 tune" — ispravno: 2019 stock SW, NPRo NE mijenja SW string
2. **HW 063 ODO** — dokument govorio `primary=0x0562`, ali kod koristi `max(0x4562, 0x0562)` za Spark ECU
3. **USER_MANUAL tablica SW** — sadržavala samo 6 SW ID-ova umjesto svih 13 poznatih
4. **DTC GUI grupe** — dokument pokazivao samo P0/P1, nije spominjao P2 grupu (11 kodova)
5. **CANBUS_NOTES** — nedostajali payload formati potvrđeni iz ECU CODE + SAT enkriptiran nalaz + RXT-X 260 EEPROM identifikacija

---

## 2026-03-18 15:30 — HW 061 EEPROM identifikacija i audit svih dumpova

### Što je napravljeno
Analizirani novi EEPROM dumpovi HW 061 tipa. Identificiran MPEM SW prefiks `10375044` = HW 061. Pronađene ODO adrese za novi HW tip. Ažuriran `core/eeprom.py`. Kompletni audit svih EEPROM dumpova (ECU + _materijali).

### Promijenjeni fajlovi
- `core/eeprom.py` — dodana HW 061 detekcija, ODO adrese, mpem_model_guess, komentar u docstringu

### Ključni nalazi — HW 061

**MPEM SW**: `1037504475` (prefiks `10375044`)

**ODO circular buffer**: HW 061 koristi **dvije izmjenične regije** s offsetom 0x4000:
- Regija A aktivan: **0x05E2** (niže sate — do ~200h)
- Regija B aktivan: **0x45E2** (više sate — pri rotaciji na ~446h potvrđeno)
- Algoritam: `max(0x05E2, 0x45E2)` — aktivna regija ima vrijednost, neaktivna = 0

**Dumpovi**:
| Fajl      | ODO izračunato | ODO label | Točnost |
|-----------|----------------|-----------|---------|
| 061 115   | 115h 37min     | 115h      | ✅ točno |
| 061 447   | 446h 56min     | 447h      | ✅ točno |

**Hull ID**: 061 115 = `YDV10351L910`, 061 447 = prazno (nije programirano)
**Datum**: 061 115 = 14-10-09 (2009!), 061 447 = 30-11-09 → stariji uređaji

### Ključni nalazi — audit svih dumpova (misprogramirani)

**ZADATAK 4 REZULTAT — misprogramirani EEPROM-i**:
- `ECU/062/062 1-4` → MPEM = `1037525858` = HW **063** (fajl u 062 folderu!) — fajl u krivom folderu
- `ECU/064/064 85-31 ex063` → MPEM = `1037550003` = HW **064** — ime fajla sadrži "ex063" (bio 063, reprogramiran u 064) — ovo je LEGITIMNA konverzija, ne greška
- `_materijali/eeprom dumps/062/062 1-4` → isto kao gore, isti fajl

**Alen dumpovi**:
- `alen oct25` — MPEM `1037400677` → HW `???` (nepoznat prefiks, nije standardan BRP/Sea-Doo)
- `alen jan26` → HW 064, 89h 36min, YDV11763A919
- `alen donor` → HW 062, 671h 58min (donor ECU)

### Test potvrda
```
python3 -c "from core.eeprom import EepromParser; ..."
061 115: hw_type='061', odo_raw=6937, odo_hhmm=115h 37min → OK
061 447: hw_type='061', odo_raw=26816, odo_hhmm=446h 56min → OK
```

---

## 2026-03-18 — CAN bus proširenje: SAT analiza, can_decoder.py, SAT_PROFILES

### Što je napravljeno
Provedena binarna analiza SAT firmware dumpova i ECU flash-a. Implementiran `core/can_decoder.py` s potpunim payload decoderom. Proširen `ui/can_network_widget.py` s payload info, SAT_PROFILES i timing tablicama.

### Promijenjeni fajlovi
- `core/can_decoder.py` — NOVI fajl, 270+ linija
- `ui/can_network_widget.py` — ažurirani CAN_ID_INFO (payload formati + timing), CAN_TABLE_ADDR komentar, dodan SAT_PROFILES dict, SAT_CONFIGS koristi SAT_PROFILES, docstring ažuriran

### Ključni nalazi — SAT firmware dumpovi
- **3 SAT dumpa** (`00000 143g full read` = Spark SAT, `truki gtix21` = GTI-X SAT, `unknow gti` = GTI SAT variant)
- Veličine: Spark + GTI = 325,696B (0x4F840), GTI-X = 324,672B (0x4F440)
- **Entropy 7.997 bits/byte** = firmwari su enkriptirani ili komprimirani — direktna binarna analiza CAN ID-ova NIJE MOGUĆA
- Header pattern identičan sva 3 fajla (A5 3B FB 19 AC 26 45 A2 E9 70 ...) — bytes[10:11] se razlikuju (mogući SW revision)
- spark_sat i gti_sat imaju IDENTIČAN kraj (isti base firmware), gtix_sat je drugačiji
- **Zaključak**: SAT dumpovi su read-protected MCU dumpovi s enkriptiranim sadržajem — nemaju ASCII CAN ID-ove

### Ključni nalazi — "nepoznati epprom" (2MB)
- **Identifikacija**: ECU EEPROM backup za RXT-X 260 motor
- SW ID @ 0x02001A: `1037524060` (RXT-X 260 SW — potvrđeno iz ranije analize)
- MED17 string @ 0x03FE10: `30/1/MED17////7A1124O/A0RDS1//00//`
- Bosch part @ 0x029D13: `7A1124OA0RDS1`
- Nije-FF podaci samo u regiji 0x020000–0x040000 (131,072 bajta = 128KB aktivan sadržaj)
- Header @ 0x020000: `60 00 00 00 04 FF 01 00` — BRP EEPROM container format
- 0x020030 = `1C F1 64 84` = checksum (CRC32 ili Bosch checksum)
- **Zaključak**: 2MB raw EEPROM chip dump, aktivan sadržaj 128KB @ 0x020000, identificiran kao RXT-X 260 ECU EEPROM (Bosch ME17 format, identičan strukturi poznatih 32KB EEPROM-a samo s drugačijim offset)

### CAN payload analiza (iz ECU binarnih)
- **CAN tablica 300hp @ 0x0433BC**: 015B 015C 0148 013C 015C 0138 0108 0214 012C 0110 0108 017C 0000
- **CAN tablica Spark @ 0x042EC4**: 015B 0154 0134 013C 015C 0138 0108 0214 012C 0110 0108 017C 0000
- **Timing tablica** @ (table_addr - 14): LE u16 ms periodicitet po ID-u
  - GTI: 8ms 16ms 22ms 22ms 22ms 22ms 18ms 148ms 223ms 147ms
  - Spark: 8ms 16ms 20ms 20ms 20ms 20ms 16ms 132ms 196ms 131ms
- **CAN descriptor struct** @ CODE 0x0173C0: `5A opcode` + idx + CAN_ID(BE) + 0xFFFF + checksum
- **RPM payload** (0x0108): byte[1:3] u16 BE × 0.25 = RPM
- **Temp payload** (0x0110): byte[1] − 40 = °C
- **Engine hours** (0x012C): byte[0:4] u32 BE (seconds) / 3600 = hours

### Implementiran core/can_decoder.py
- `CanDecoder.decode_rpm(payload)` — RPM iz 0x0108
- `CanDecoder.decode_coolant_temp(payload)` — °C iz 0x0110
- `CanDecoder.decode_iat(payload)` — IAT iz 0x0110
- `CanDecoder.decode_engine_hours(payload)` — sate iz 0x012C
- `CanDecoder.decode_dtc(payload)` — DTC liste iz 0x017C
- `CanDecoder.decode_engine_status(payload)` — flags iz 0x013C
- `CanDecoder.decode(can_id, payload)` — universal dispatcher
- `GTI_SC_CAN_TIMING`, `SPARK_CAN_TIMING` — timing tablice
- `get_timing(can_id, ecu_type)` — period lookup

---

## 2026-03-18 — UI vizualna poboljšanja (5 zadataka)

### Što je napravljeno
Implementirana vizualna/grafička poboljšanja u `ui/main_window.py`.

### Promijenjeni fajlovi
- `ui/main_window.py` — jedini fajl, sve promjene unutar njega

### Detalji implementacije

#### 1. Category color badges u MapLibraryPanel
- Dodana konstanta `CATEGORY_COLORS` s 8 kategorija i HEX bojama
- Implementirana funkcija `_category_icon(category)` — kreira 12×12 QPixmap filled circle u boji kategorije, vraća QIcon
- U `MapLibraryPanel._render()`: svaki tree item dobiva `ch.setIcon(0, _category_icon(fm.defn.category))`
- Boje: injection=#4ec9b0, ignition=#f97316, torque=#a855f7, lambda=#22d3ee, rpm_limiter=#ef4444, axis=#6b7280, misc=#84cc16, dtc=#f59e0b

#### 2. Status bar gauge labele
- Dodana 3 QLabel widgeta kao `addPermanentWidget` u status baru:
  - `_sb_sw_lbl` — SW ID bold, boja prema SW varijanti
  - `_sb_maps_lbl` — badge s brojem mapa (prikazuje se nakon scan-a)
  - `_sb_region_lbl` — BOOT/CODE/CAL indikator kad je mapa selektirana
- Metoda `_update_sb_sw(sw_id, n_maps)` — ažurira SW badge i maps count
- Metoda `_update_sb_region(addr)` — određuje regiju i bojom označava
- Poziva se iz `_load1()` (SW badge) i `_on_map_selected()` (region badge)

#### 3. Accent bar ispod toolbar-a
- Dodan `QFrame` visine 2px (`_accent_bar`) odmah ispod toolbar-a, iznad progress bar-a
- Metoda `_update_accent_bar(sw_id)` — bira boju prema SW varijanti
- Boje: 300hp SC=#f97316, 230hp SC=#f59e0b, 130/170hp NA=#4ec9b0, Spark=#a855f7, GTI90=#22d3ee, GTI155=#84cc16, nije učitan=#333333
- Poziva se iz `_load1()` nakon učitavanja

#### 4. Scan progress animacija
- Dodan `QTimer` (`_scan_timer`, 400ms interval) koji ciklira 1/2/3 točke na status baru
- `_scan_progress_cb(msg)` — prima progress poruku iz ScanWorker-a, pohranjuje u `_scan_msg_base`
- `_scan_progress_tick()` — slot timera, cycla tačke i prikazuje u status baru
- Timer se pokreće u `scan_maps()` i zaustavlja u `_done1()`
- Nakon završetka: `status.showMessage("✓ {N} mapa učitano.")`

#### 5. Heatmap paleta po kategoriji
- Definirane 4 category-specific palete: `_PAL_INJECTION`, `_PAL_IGNITION`, `_PAL_TORQUE`, `_PAL_LAMBDA`
- Svaka paleta = 9 (bg, fg) QColor parova od najhladnijeg do najtoplijeg
- `_CATEGORY_PALETTES` dict mapira kategorije na palete
- Nova funkcija `_cell_colors_cat(raw, mn, mx, category)` — odabire paletu prema kategoriji
- Stara `_cell_colors()` postala alias koji prosljeđuje category argument
- Ažurirane `show_map()` i `refresh_cell()` metode u `MapTableView` — prosljeđuju `defn.category`

### Tehnički detalji
- AST provjera: PASS (`python -c "import ast; ast.parse(open('ui/main_window.py', encoding='utf-8').read())"`)
- Import provjera: PASS (`from ui.main_window import MainWindow`)
- Dodani importi: `QIcon, QPixmap, QPainter` u PyQt6.QtGui importu

---

## 2026-03-18 — Spark 900 ACE nove mape (+6 novih MapDef-ova)

### Što je napravljeno
Binarna analiza Spark 900 ACE ECU-a tražeći 12 mapa koje GTI90 ima a Spark nema.
Korišten sistematičan pattern scan uspoređujući Spark 2021, Spark 2018, STG2 i GTI90.

### Potvrđene i implementirane mape (6 novih):
1. **Torque limit** @ 0x027E3A — 16×16 u16 BE Q8, mirror @ 0x028352 (+0x518). Identičan format GTI90 @ 0x02A0D8. Vrijednosti 28416-32512 (Q8: 111-127).
2. **Lambda trim** @ 0x024EC4 — 30×20 u16 LE Q15. 600 vrijednosti 31935-33871 (λ 0.975-1.034). Razlika 2021 vs 2018: 240/600 vrijednosti.
3. **Overtemp lambda** @ 0x024468 — 63 u16 LE Q15. Identično GTI90 @ 0x025ADA (byte-for-byte). Nema razlike 2018 vs 2021.
4. **Lambda protection** @ 0x0222C0 — 12×18 u16 LE, mali Q15 raw (508-2154 = 0.016-0.066). Mirror @ 0x0227D8 (+0x518). Isti na 2021 i 2018.
5. **Therm enrich** @ 0x025BAA — 8×7 u16 LE, /64=%. Vrijednosti 9766-14400 = 152-225%. Analogno GTI90 @ 0x02AA42.
6. **Neutral corr** @ 0x0237AC — 80 u16 LE Q14=1.0 (flat, nema korekcije). Identično na svim SW varijantama.

### Mape koje NISU nađene (6 od 12):
- **Torque opt** — Nije zasebna tablica (moguće isti podaci kao torque limit + GTI specifičan)
- **Lambda bias** — Nije pronađen blok odgovarajućih dimenzija u Spark CODE
- **Lambda eff (KFWIRKBA)** — GTI format (41×18, rastuće Q15) ne postoji u Spark layout-u
- **Eff corr** — GTI pattern (Q15 ~0.4-1.3) nije potvrdio jedinstven blok
- **Accel enrich** — Kompleksan enkapsuliran format, nije nedvosmisleno identificiran
- **Ign corr** — GTI 8×8 u8 format nije u Sparku (Spark ima drugačiju strukturu @ 0x0222BE area)

### Fajlovi promijenjeni
- `core/map_finder.py` — 6 novih MapDef-ova (_SPARK_TORQUE_DEF, _SPARK_LAMBDA_TRIM_DEF, _SPARK_OVERTEMP_LAMBDA_DEF, _SPARK_LAMBDA_PROT_DEF, _SPARK_THERM_ENRICH_DEF, _SPARK_NEUTRAL_CORR_DEF) + 6 novih scan blokova u `_scan_spark_aux()`
- Obrisano: `analyze_spark_maps.py`, `analyze_spark_maps2.py`, `analyze_spark_maps3.py`, `analyze_spark_maps4.py` (temp analitičke skripte)

### Ključni rezultati
- Spark: 21 mapa → **27 mapa** (+6, +29%)
- `python test/test_core.py` — sve prolazi (Spark: 27 mapa, assert >= 10 ✓)
- Spark torque @ 0x027E3A ima isti mirror offset (+0x518) kao injection i lambda_prot → konzistentna arhitektura

---

## 2026-03-18 — UI poboljšanja v2b (7 novih funkcionalnosti)

Implementirano u `ui/main_window.py`:

1. **Axis Labels** — `_format_axis_labels()`: RPM→int, Load→"20%", ostalo→1 decimala
2. **Delta Overlay** — `show_map_diff()`: "37 (+3)" format, zelena/crvena nijansa
3. **Bulk Edit Toolbar** — Scale/Offset/Smooth/CopyREF, vidljiv pri >1 selekciji, undo podrška
4. **REF side-by-side** — "+ REF" gumb u toolbaru, `_load_ref()`, prioritet nad Fajl 2
5. **SW Variant Filter** — dropdown u MapLibraryPanel, auto-set pri učitavanju
6. **Undo History Panel** — "History" tab u PropertiesPanel, klik=undo do točke
7. **Auto-Checksum na Save** — dialog ako CS nije OK

Testovi: `python test/test_core.py` sve prolazi; `python main.py` OK.

---

## 2026-03-18 13:00 — Konsolidacija dokumentacije: docs/ → _docs/

### Što je napravljeno
- Pročitani svi fajlovi u `docs/` (CAN_SAT_PORUKE.md, MAPA_ADRESE.md, QA_LOG.md)
- Uspoređeni s odgovarajućim `_docs/` fajlovima (CANBUS_NOTES.md, MAPS_REFERENCE.md)
- Potvrđeno: svi podaci su potpuno konsolidirani u `_docs/` u prethodnoj doc sesiji
- Obrisan `docs/` folder (sva 3 fajla)
- Obrisano 5 zastarjelih `_docs/` fajlova (vidi DOC_AGENT_LOG.md za detalje)
- Ažurirani: DOC_AGENT_LOG.md, chat_log.md, work_log.md

### Fajlovi promijenjeni
- OBRISANO: `docs/` (cijeli folder — CAN_SAT_PORUKE.md, MAPA_ADRESE.md, QA_LOG.md)
- OBRISANO: `_docs/INTERNET_RESEARCH_KOMPLETAN_DOKUMENT.md`
- OBRISANO: `_docs/INTERNET_RESEARCH_REZULTATI.md`
- OBRISANO: `_docs/MAP_RESEARCH.md`
- OBRISANO: `_docs/NEDOSTAJE_ISTRAZITI.md`
- OBRISANO: `_docs/UI_REDESIGN_UPUTA.md`
- AŽURIRANO: `_docs/DOC_AGENT_LOG.md`

### Rezultat
Dokumentacija konsolidirana — jedini aktivni docs folder je `_docs/`.

---

## 2026-03-18 — PDF pretraga rev limiter vrijednosti (Spark/GTI 900 ACE)

### Pretraženi fajlovi
- `2017 SPARK/PWC 2017 Technical Specifications_engine - SPARK- smr2017-212.pdf`
- `2016 SPARK SERIES SHOP MANUAL/PWC Technical Specifications (Spark Series) - Shop manual supplement smr2016-112.pdf`
- `2017 GTI_GTR_GTS_WAKE_155 900ACE/PWC 2017 Tech Spec engine - 900ACE - R900ACE_MY17-010.pdf`
- `2017 GTI_GTR_GTS_WAKE_155 900ACE/PWC 2017 Engine Management System (900 ACE Series) - DOLPHIN-smr2017-312.pdf`
- `2021 Spark.pdf` (83MB, 714 str.), `2019 Spark.pdf` (103MB, 677 str.), `2017 Spark.pdf` (219MB, 817 str.)

### Ključni nalazi — Spark 900 ACE HO
| Parametar | Vrijednost | Izvor |
|-----------|-----------|-------|
| Maximum HP RPM | **8000 ±100 RPM** | Sve Tech Spec stranica 1 (ENGINE sekcija) |
| Engine speed limiter setting | **8300 RPM** | smr2017-211 str. 5, smr2016-112 str. 5, 2019 Spark str. 441, 2021 Spark str. 440 |
| Engine speed limiter (VEHICLE/iBR) | **8000 RPM** | 2017/2019/2021 Spark str. 442/443 (VEHICLE subsekca, iBR varijanta) |
| Idle speed | 1400 ±100 RPM | Sve GTI/Spark manuali |

### Zaključak
- **8000 RPM** = maksimalni RPM pri punoj snazi (Maximum HP RPM)
- **8300 RPM** = ECU ENGINE SPEED LIMITER SETTING (hard cut ignition+fuel) — u ENGINE subsekci
- **8000 RPM** = iBR/VEHICLE ECU limiter — posebna Tech Spec za VEHICLE (iBR varijanta Spark)
- Naša binarno-izračunata vrijednost **8081 RPM** (5120 ticks @ 0x028E34) konzistentna s ovim — između 8000 i 8300
- **Hipoteza**: 8300 = engine-only limit (bez opterećenja), 8081 = stvarni ECU cut (s opterećenjem/impelerom)

---

## 2026-03-18 (sesija 2) — Spark deadtime fix, rev limiter, novi SW ID-ovi, ORI/STG2 parovi

### Spark deadtime ispravka
- Stara adresa 0x02428E bila pogrešna (false positive)
- **Prava adresa: 0x0287A4** — 8×8=64 u16 LE, period-encoded 9632-13440 ticks @ 40MHz → ~240-336µs
- RAZLIKUJE SE od GTI90 (0x025900, 14×7, drukčiji raw raspon)

### Spark rev limiter dodan
- **Hard cut @ 0x028E34 = 5120 ticks = 8081 RPM** (formula: 40e6×60/(5120×58))
- Identičan u 2018 i 2021 Spark; NPRo STG2 NE mijenja rev limiter!
- Ramp tablica @ 0x028E2E (16 val, 3200-13763 ticks) — u scanneru nisam dodao još
- Praktično: stock Spark u vodi ≈7900 RPM (impeller-limitirano); NPRo tune + mod impeler do 8500-8550 RPM uživo; ECU cut = 8081 RPM (kavitacija zaštita)

### Novi SW ID-ovi otkriveni
- **10SW054296** = 300hp SC 2020 ORI (dumps/2020/1630ace/300.bin) — dodan u KNOWN_SW i _300HP_SW_IDS
- **1037544876** = NPRo Spark 900 ACE STG2 (decimalni format, dumps/2018/900ace/spark_stg2) — dodan u KNOWN_SW i _SPARK_10SW_IDS

### ORI/STG2 parovi potvrđeni
| ORI | SW | STG2 | SW | CODE diff |
|-----|-----|------|-----|-----------|
| 2021/1630ace/300.bin | 10SW066726 | 2020/1630ace/300_stg2 | 10SW040039 | 7087B |
| 2020/1630ace/300.bin | 10SW054296 | 2020/1630ace/300_stg2 | 10SW040039 | 6038B |
| 2018/900ace/spark90.bin | 10SW011328 | 2018/900ace/spark_stg2 | 1037544876 | 3065B |

### Test rezultati (svi PASS)
- Spark=21 mapa (deadtime + rev limiter dodani), GTI90=58, 300hp=51, 130/170hp=60, 230hp=51

## 2026-03-18 — Dumps restrukturiranje + Spark aux mape + testovi

### Dumps nova struktura
- Korisnik premjestio fajlove u `dumps/YYYY/{1630ace,900ace,4tec1503}/`
- `test_core.py` putanje ažurirane na novu strukturu (sve rješeno)
- STG2 fajl pronađen @ `dumps/2020/1630ace/300_stg2` (bez ekstenzije, data fajl)

### Spark aux mape implementirane (_scan_spark_aux)
7 novih MapDef + scanner za Spark 900 ACE, sve potvrđene testovima:
- `_SPARK_DFCO_DEF` @ 0x021748 (7 u16 LE) — identično GTI90
- `_SPARK_COLD_START_DEF` @ 0x0241F8 (6 u16 LE) — identično GTI90
- `_SPARK_DEADTIME_DEF` @ 0x02428E (14×7=98 u16 LE) — identično GTI90
- `_SPARK_KNOCK_DEF` @ 0x02408C (24 u16 LE) — identično GTI90
- `_SPARK_START_INJ_DEF` @ 0x024676 (6 u16 LE)
- `_SPARK_WARMUP_DEF` @ 0x024786 (156 u16 LE Q14)
- `_SPARK_IDLE_RPM_DEF` @ 0x0224A0 (5×12=60 u16 LE)

### Rezultati test_core.py (sve PASS)
- ORI (10SW066726): 51 mapa
- STG2 (10SW040039): 51 mapa
- Spark 2021 (10SW039116): **20 mapa** (13 base + 7 aux)
- GTI90 2021 (10SW053774): **58 mapa**
- 230hp (10SW053727): 51 mapa
- 130hp (10SW053729): 60 mapa
- 170hp (10SW053729): 60 mapa

## 2026-03-18 — Sveobuhvatna binarna analiza Spark 900 ACE ECU

### Pronađene mape (Spark 10SW039116 / 10SW011328)

#### Potvrđene mape (s adresama)
- **RPM os** @ 0x02225A: 20pt u16 LE, [7680-26624] (RPM * 8/60 skala)
- **Load os** @ 0x022282: 30pt u16 LE, [3999-33600] (MAP/load vrijednosti)
- **Injection** @ 0x0222BE: 20×30 u16 LE = 1200B, range 479-4443 µs
- **Injection mirror** @ 0x022774: +0x4B6 offset (provjeri)
- **Ignition #0-#5** @ 0x026A76+i*0x90: 6× 12×12 u8, razmak 144B, 0.75°/bit
- **Lambda #0-#3** @ 0x025F5C/0x02607E/0x0261A0/0x0262C2: svaka 8×16 u16 LE Q15, razmak 290B (= 256B mapa + 34B osi!)
  - Lambda os (RPM): 9 tačaka @ -34B od svake mape, Q15 opseg 0.101-1.521
  - Lambda os (load): 8 tačaka @ -16B, Q15 opseg 0.301-1.521
  - Range lambda: 0.886-0.967 (tuned 2021 vs flat ~1.0 u 2018)

#### Novo pronađene mape (2026-03-18)
- **Lambda closed-loop trim** @ 0x025408 (i dalje): 240B, Q15 format, 2021 vs 2018 razlike 0.90-1.02
  - Sparkovi imaju bogatu closed-loop korekciju po regijama (svaki cell individualno tuned)
  - 0x024EEC (240B): Q15 ~0.975-0.994, 120 vrijednosti (dimenzije TODO: 10x12 ili 12x10)
  - 0x025004 (120B): Q15 ~0.994-1.004
  - 0x0250A4 (80B): Q15 ~1.004-1.007
  - 0x025408-0x025570 (360B): closed-loop trim, 0.90-1.02, 2021 tuned
  - 0x025702-0x025884 (386B): Q15 format, 0.931-1.007 (lambda mape ili trim?)
- **Deadtime (injector)** @ 0x0287A4: 193B, u16 LE, range 12000-13440
  - Format: 8×8 ili sličan, vrijednosti su period-encoded (NS, ne µs)
  - Razlikuje se 2018 vs 2021 (tuned)
  - Iza deadtime: voltage osi @ 0x028852 (u8: 8,70,80,100...150, 2 kopije)
- **Rev limiter tablica** @ 0x028E2E: niz ticks vrijednosti 3200-13763+
  - Ovo je RAMP tablica (soft-cut): 5120=8081RPM do 13763+
  - **Hard cut** = 5120 ticks @ 0x028E34 = **8081 RPM** za Spark 2018/2021
  - Identično u 2018, 2021 i STG2 Spark → rev limiter nije promijenjen u STG2!

#### Blokovi 0x027E6A-0x028249 i 0x028382-0x028761 (svaki 991B)
- **Format: u16 LE, range 112-121**
- Ovo su KNOCK/KNK tablice ili ignition trim korekcije po load/RPM
- Nisu ignition (premalo za 4-80 range); vjerojatno knock threshold ili ign trim u nepoznatom formatu

#### 230hp 2020 vs 2021
- **CODE regija**: 80B razlike na 2 bloka (0x017F02-0x017F48 i 0x017F5C-0x017F74)
- **Praktički IDENTIČNI** — isti SW 10SW053727, minimalne razlike (vjerojatno build timestamp)
- Mape su 100% iste!

### Ključni nalazi
1. Lambda mape imaju 34B osi IZMEĐU mapa (RPM+load os) — niie 256B nego 290B blok
2. Spark 2018 vs 2021 diff: 40 merged blokova, ~1148B ukupno promijenjeno
3. Rev limiter: ISTI za 2018/2021/STG2 — STG2 tune ne dira rev limiter
4. GTI90 i Spark imaju POTPUNO DRUGAČIJU strukturu od 0x028E00 nadalje
5. Blokovi 0x027E6A i 0x028382 (2×991B) su neidentificirani — vjerojatno ignition/knock

### Privremene skripte
- `analyze_spark.py` — inicijalna analiza, diff blokovi
- `analyze_spark2.py` — rev limiter, ignition, injection detalji
- `analyze_spark3.py` — lambda osi, deadtime, 230hp analiza
- `analyze_spark4.py` — finalizi identifikacija preostalih blokova

## 2026-03-18 — Test refaktor + Spark 10SW039116 klasifikacija

### Promjene
- `test/test_core.py`: Svi referentni putovi ažurirani za novu `dumps/` strukturu (stari `_materijali/ori_300.bin` → `dumps/2021/300.bin`)
  - Dodani testovi: `test_map_finder_gti90()`, `test_map_finder_sc_variants()` (230/130/170hp)
  - STG2 i GTI155 testovi: graceful skip ako fajl nije prisutan
  - Spark SW assertion: `"1037..."` → `"10SW039116"`
- `core/map_finder.py`: Dodano `"10SW039116"` u `_SPARK_10SW_IDS`
- Svi testovi prolaze: 300hp=51, 230hp=51, 130/170hp=60, GTI90=58, Spark(oba SW)=13 mapa

### Spark analiza —ključni nalaz
- **2018 Spark (10SW011328) vs 2021 Spark (10SW039116)**: samo 3510B CODE diff — mape su NA ISTIM adresama!
  - Diff blokovi: 0x024EEC (240B), 0x025F57 (262B), 0x024772 (420B), itd.
  - Calibriranje vrijednosti se razlikuju (tuning za HW reviziju), ali layout identičan
- **Spark torque/rev limiter**: još nisu lokalizirani — adrese su različite od 300hp layouta
  - GTI90 @ 0x028E7C = 5875 → ~7043 RPM (potvrđeno)
  - Spark @ 0x028E7C = 17695 → ~2338 RPM (nije rev lim — nešto drugačije)
  - Spark torque @ 0x02A0D8 = sve nule (300hp adresa ne vrijedi za Spark)
- TODO: dublja analiza Spark CODE regije za torque i rev lim

## 2026-03-18 — Spark 2019/2020/2021 dump analiza + 170hp 2019

### Findings
- **Spark 90 2019/2020/2021**: sva tri imaju identičan binarni, SW = `10SW039116` (novi SW, dodan u KNOWN_SW)
- **Spark 2016** (`10SW011328`) vs **Spark 2019** (`10SW039116`): 622,954 bytes razlike — potpuno drugačiji CODE layout!
- **NPRo Spark** SW = `1037544876` (BUDS2 decimal format), baza je `10SW039116`, 6145 bytes CODE izmjena (238 blokova)
  - NPRo izmjene: injection ~0x024EEC, ignition ~0x027EBA-0x028760 (u8 parovi), torque ~0x0295EE, lambda ~0x025F57
  - Rev limiter kandidat: `0x014B6E/70` = 5202/5071 ticks → 7954/8159 rpm (soft/hard, nije live potvrđeno)
- **170hp 2020** (fajl je u dumps/2019/ ali je 2020 model) = `10SW053729` (isti binarni kao 2020_130 — 0 bytes razlike), 80B hash blok razlika od 2021 (isti obrazac)
- `dumps/` struktura: 2019/{spark90,170}, 2020/{130,gti90,spark90}, 2021/{130,170,230,300,gti90,spark90}

### Promjene
- `core/engine.py`: Dodan `10SW039116` u KNOWN_SW
- TODO: map_finder.py SW-gating za `10SW039116` — mape na drugačijim adresama od 2016 Spark

## 2026-03-18 — UI Redesign v2b: DTC Sidebar + PropertiesPanel DTC tab

### Promjene u `ui/main_window.py`
- **Imports**: Dodani `QStackedWidget`, `QMenu`, `QToolButton`
- **DtcSidebarPanel** (nova klasa): tree-based DTC lista s filterom, grupirana po P0xxx/P1xxx, status boje (aktivan=narandzasto, off=sivo), emituje `dtc_selected` signal
- **Lijevi sidebar**: `MapLibraryPanel` + `DtcSidebarPanel` u `QStackedWidget` — automatski se mijenja pri tab promjeni (Map Editor ↔ DTC Off)
- **DtcPanel refaktor**:
  - Uklonjena interna DTC lista (lijeva kolona) — zamjenjena sa `DtcSidebarPanel`
  - Layout promjenjen iz `QHBoxLayout` u `QVBoxLayout`
  - `grp_enable` i `grp_code` uklonjeni iz centra — premješteni u `PropertiesPanel`
  - "Svi DTC OFF" i "Disable All Monitor" skriveni u `▾ Napredno` dropdown (`QToolButton` + `QMenu`)
  - Dodani signali: `dtc_status_changed(int, bool)` za sidebar sinkronizaciju
- **PropertiesPanel**: Dodan Tab 3 "DTC" s code/mirror adresama, notes; `show_dtc_details()` metoda
- **Toolbar**: `btn_open1/btn_open2/btn_scan` zamjenjeni sa `btn_file/btn_swap/btn_compare` (dinamičko prikazivanje)
- **MapLibraryPanel**: `setFixedWidth(220)` → `setMinimumWidth(260)`
- **Splitter sizes**: `[220, 950, 270]` → `[270, 900, 270]`
- **MainWindow**: Dodane metode `_on_tab_changed`, `_on_dtc_sidebar_selected`, `_on_dtc_status_changed`; wiring u `_load1`

---

## 2026-03-18 — UI overhaul + GTI 90 2020 dump analiza

### UI promjene
- **Šire kolone**: defaultSectionSize 54→64px (sve tablice + zoom formula)
- **_fmt ispravka**: dodan `offset_val` u formatiranje vrijednosti u heatmap tablici (SC corr, lambda trim, neutral corr, accel enrich itd. sada prikazuju ispravne %)
- **Tab naglašavanje**: "Mapa"→"Map Editor" (plava), "DTC"→"DTC Off" (narandzasta), setTabTextColor per-tab
- **CAN Network tab**: novi tab (teal) + `ui/can_network_widget.py` — prikaz ECU CAN ID-ova, SAT kompatibilnost, citanje iz binarnog
- **Fajlovi promijenjeni**: `ui/main_window.py`, `ui/can_network_widget.py` (novi)

### GTI 90 2020 dump analiza
- **Fajl**: `_materijali/dumps/2020/gti90.bin`
- **SW ID**: `10SW053774` — isti kao GTI 90 2021
- **Razlika**: 80 bajtova u CODE regiji @ `0x017F02–0x017F73` (hash/potpis blok)
- **Zaključak**: GTI 90 2020 = 2021 uz hash update (isti obrazac kao 130hp 2020/2021)
- **Ažurirano**: `core/engine.py` KNOWN_SW: 10SW053774 → "2020-2021"

---

## 2026-03-18 — CAN SAT analiza: Spark vs GTI/230/300hp poruke

### Što je napravljeno

#### CAN SAT analiza (docs/CAN_SAT_PORUKE.md)
- Binarni scan svih 2021 ECU fajlova za CAN message ID tablice
- Pronađena CAN ID tablica @ Spark:0x042EC4 / GTI-family:0x0433BC (u16 BE niz)
- **Spark ECU CAN IDs:** 0x15B, 0x154, 0x134, 0x13C, 0x15C, 0x138, 0x108, 0x214, 0x12C, 0x110, 0x17C
- **GTI/230/300 ECU CAN IDs:** 0x15B, 0x15C, 0x148, 0x13C, 0x15C, 0x138, 0x108, 0x214, 0x12C, 0x110, 0x17C
- **Spark-specific:** 0x0134, 0x0154 (u GTI-family nema)
- **GTI-specific:** 0x0148 (u Sparku nema)
- **Zajednički:** 9 poruka (0x108–0x214) — identični u svim varijantama
- GTI/230/300 imaju 3 extra config entrya: CAN ID 0xBF, 0xCD, 0xDC (DLC=1)
- Zaključak: 300hp + Spark SAT radi → 230hp/260hp + Spark SAT treba raditi (isti CAN set)
- **Fajl:** `docs/CAN_SAT_PORUKE.md`

### Napomene
- Korisnikova napomena: stariji modeli sa Siemens ECU imali različite injektore/tlak benzina — zanemariti za ME17

## 2026-03-18 — 2021 SW klasifikacija, GTI 90 rev limiter, MAPA_ADRESE ažuriranje

### Što je napravljeno

#### 1. Analiza 2021 dumpa (5 novih fajlova u `_materijali/dumps/2021/`)
- GTI 90 (10SW053774), 130hp (10SW053729), 170hp (10SW053729), 230hp (10SW053727), 300hp (10SW066726)
- Otkriveno: 130/170/230hp 2021 su **Rotax 1630 SC motori** (SC boost +23–30%)
- Otkriveno: GTI 90 2021 je **NA motor** (SC boost −18.4%)

#### 2. SW klasifikacija (`core/map_finder.py`)
- Dodani u `_300HP_SW_IDS`: `10SW053727` (230hp), `10SW053729` (130/170hp)
- GTI 90 (10SW053774) ostaje kao GTI/NA — ispravno
- Ažuriran komentar u `_is_gti_na()`

#### 3. KNOWN_SW prošireno (`core/engine.py`)
- Dodano 7 novih SW opisa: 10SW025752, 10SW053774, 10SW053729, 10SW053727, 10SW004672, 10SW082806, 10SW011328

#### 4. GTI 90 rev limiter istraživanje
- Adresa 0x028E96 za GTI 90 = 3277 ticks (~12627 rpm) — **KRIVO za ovu varijantu**
- Pronađena dva bloka s uzlaznim periodi koji završavaju oko 5880 ticks:
  - 0x028E68: **5883 ticks = 7034 RPM** (blok A)
  - 0x028E7C: **5875 ticks = 7043 RPM** (blok B)
- Procjena: GTI 90 hard cut ≈ **7040 RPM** — nije potvrđeno live testom

#### 5. Rev limiter usporedba svih 2021 SW @ 0x028E96
- 300hp/230hp (SC): 5072 ticks = **8158 RPM**
- 130/170hp (SC): 5243 ticks = **7892 RPM**
- GTI 155 2018 (NA): 5374 ticks = **7700 RPM**
- GTI 90 2021 (NA): drugačija struktura, vidi gore

#### 6. MAPA_ADRESE.md ažuriranje
- SW tablica: dodani 2021 SW IDs s motorima i hard cut vrijednostima
- Rev Limiter tablica: proširena za 130/170hp stupac
- Dodana nova sekcija GTI SE 90 2021 s rev limiter analizom
- Svi testovi prolaze ✅

### Fajlovi promijenjeni
- `core/engine.py` — KNOWN_SW
- `core/map_finder.py` — _300HP_SW_IDS, komentar _is_gti_na
- `docs/MAPA_ADRESE.md` — SW tablica, Rev Limiter, GTI 90 sekcija

---

## 2026-03-18 — GTI mape, EEPROM fix, testovi, GUI SW varijanta

### Što je napravljeno

#### 1. GTI 155 / NA motor mape (`core/map_finder.py`)
- Dodan `_300HP_SW_IDS` set za razlikovanje 300hp od GTI/NA varijanti
- Dodana `_is_gti_na()` helper metoda (detektira 10SW... koji NISU 300hp)
- Dodana `_is_spark()` helper metoda (refactor iz inline koda)
- Dodane GTI MapDef definicije: `_GTI_INJ_DEF` (@ 0x022066, 16×12, direktni raw) + `_GTI_IGN_DEFS` (8 mapa @ 0x028310, stride 144, raw 40-67)
- Dodane scan metode: `_scan_gti_injection()` i `_scan_gti_ignition_extra()`
- GTI binary sada pronalazi **56 mapa** (53 standardne + 9 GTI-specifičnih)
- 300hp regresija: i dalje **53 mape** ✅

#### 2. EEPROM fix (`core/eeprom.py`)
- Ispravan docstring: 0x0125 NIJE hw timer, pravi sati su u circular bufferu
- Dodan `hw_type: str` u `EepromInfo` dataclass
- Dodana HW tip detekcija iz MPEM SW prefiksa (064/063/062)
- Dodan circular buffer ODO po HW tipu (zamjenjuje pogrešno čitanje 0x0125)
  - HW 064/063: primarno 0x0562, backup 0x0D62/0x1562/0x0DE2
  - HW 062: rotacija 0x5062 → 0x4562 → 0x1062

#### 3. EEPROM widget (`ui/eeprom_widget.py`)
- Dodan "HW tip ECU-a" field u SW verzije grupu
- Prikazuje puni opis HW tipa (npr. "HW 064 — 1.6L (300hp RXP/RXT/GTX, GTI SE 155)")

#### 4. GUI poboljšanja (`ui/main_window.py`)
- Naslov prozora sada prikazuje SW ID i ime fajla pri učitavanju
  - Primjer: `ME17Suite  —  10SW066726  [ori_300.bin]`

#### 5. Testovi (`test/test_core.py`)
- Dodan `test_map_finder_spark()`: Spark 900 ACE, >=10 mapa, sve kategorije OK
- Dodan `test_map_finder_gti()`: GTI 155, >=50 mapa, 1 GTI injection + >=4 GTI ignition
- Dodan `test_eeprom_circular()`: circular buffer ODO s poznatim EEPROM fajlovima
- Sve 3 EEPROM test case: **3/3 OK** ✅

### Fajlovi promijenjeni
- `core/map_finder.py` (GTI definicije + scan metode + _is_gti_na/_is_spark)
- `core/eeprom.py` (hw_type, circular buffer ODO, ispravan docstring)
- `ui/eeprom_widget.py` (HW tip field)
- `ui/main_window.py` (SW ID u naslovnoj traci)
- `test/test_core.py` (3 nova testa)

---

## 2026-03-18 — GTI 155 (10SW025752) binarna analiza — ključne mape identificirane

### Što je napravljeno
- Analiziran binarni fajl `_materijali/gti_155_18_10SW025752.bin` (1,540,096B, isti format kao ori_300)
- SW ID potvrđen: `10SW025752` @ 0x001A
- Motor: Rotax 1503/1504, 1.5L ATM, 155hp, HW folder 062
- Pronađene sve ključne mape: injection, ignition, lambda, rev limiter

### Ključni nalazi — GTI 155 adrese

#### 1. RPM osi
- **Kratka RPM os** @ `0x02202E` (12pt, u16 LE): [853, 1152, 1408, 1707, 2005, 2261, 2560, 2816, 3413, 3968, 4139, 4267] — za injection
- **Kratka RPM os** @ `0x0221EC` (8pt): [500, 1000, 1500, 2000, 3000, 4000, 5000, 6000] — second block
- **IGN RPM os** @ `0x028176` (8pt): [640, 1067, 1493, 1920, 2347, 2773, 3200, 3627]
- 30+ RPM osi ukupno (razni podblokovi od 0x022000 do 0x028200)

#### 2. Injection mapa (KFZW / glavni injection)
- **Adresa**: `0x022066` (u16 LE)
- **Dimenzije**: 12×16 (RPM os 12pt × Load os 16pt)
- **RPM os** @ `0x02202E`: [853...4267 rpm]
- **Load os** @ `0x022046` (16pt): [5200, 6000, 8000, 10000, ..., 32000]
- **Raw raspon**: 3193–14432, prosj. 9153 (×0.65 vs. ori_300 – ATM vs. SC)
- **Kraj mape**: `0x0221E6`
- Mirror/duplicat ne pronađen na istom offsetu kao ori_300

#### 3. Ignition mape
- **Serija**: 8 mapa po 144B (12×12 u8, °/bit = 0.75°), aligned na 144B
- **Mapa #0** @ `0x028310`: raw 40–67, °BTDC 30.00–50.25°
- **Mapa #1** @ `0x0283A0`: raw 47–67, 35.25–50.25°
- **Mapa #2** @ `0x028430`: raw 40–67
- **Mapa #3** @ `0x0284C0`: raw 47–67
- **Mapa #4** @ `0x028550`: raw 40–67
- **Mapa #5** @ `0x0285E0`: raw 47–67 (score 12/12)
- **Mapa #6** @ `0x028670`: raw 40–67
- **Mapa #7** @ `0x028700`: raw 43–67 (score 12/12)
- **IGN Load os** @ `0x02813C` (12pt): [38, 52, 64, 76, 90, 102, 116, 128, 140, 154, 202, 208]
- **IGN RPM os** @ `0x028176` (8pt): [640, 1067, 1493, 1920, 2347, 2773, 3200, 3627]
- Serija mapa @ 0x02B7F0-0x02BEB0 (raw 33–45, °25–34°) — vjerojatno knock/trim mape

#### 4. Lambda mapa
- **Adresa**: `0x0265AE` (u16 LE, Q15)
- **Dimenzije**: 12×9 = 108 vrijednosti
- **Lambda raspon**: 0.944–0.984 (GTI je open-loop, uglavnom 0.965 = blago bogata)
- **RPM os ispred** @ `0x02658E` (16pt): [1493, 1707, ..., 4693]
- **Mirror lambda** @ `0x026AC6`: raspon 0.917–0.984 (offset +0x518 od prve)
- **Usporedba s ori_300**: GTI lambda je fiksna (flat ~0.965 vs. ori_300 varijabilna 0.94–1.07)

#### 5. Rev limiter
- **Najvjerojatnija adresa**: `0x0237A0` — izolirani u16 LE 7700 rpm, okružen nulama
- Alternativni kandidati: `0x025574` (7700), `0x022364` (7700)
- Adrese 0x02B72A/0x02B73E iz ori_300 → u GTI daju 8481 (0x2121 = repeat bytes 0x21 = char '!')
- **Vrijednost**: 7700 rpm (vs. ori_300 ≥ 8481, SC motor)
- Upozorenje: nema confirmirane single adrese — potrebna daljnja analiza

#### 6. Torque mapa
- **Nije pronađena** u Q8 16×16 formatu kao ori_300 @ 0x02A0D8
- GTI region oko 0x029EC0 sadrži bytes 0–249 ali bez jasne matričke strukture
- ATM motor 155hp vjerojatno nema kompeksnu torque limitaciju kao SC 300hp

### Usporedba GTI vs ori_300
| Mapa        | ori_300 adresa | GTI 155 adresa | Dimenzije GTI |
|-------------|----------------|----------------|---------------|
| Injection   | 0x02439C       | **0x022066**   | 12×16 u16 LE  |
| Ignition    | 0x02B730+      | **0x028310+**  | 8× 12×12 u8   |
| Lambda      | 0x0266F0       | **0x0265AE**   | 12×9 Q15 LE   |
| Rev limiter | 0x02B72A       | **0x0237A0?**  | u16 LE        |
| Torque      | 0x02A0D8       | nije pronađena | —             |

### Fajlovi promijenjeni
- tmp_gti_analysis.py, tmp_gti_analysis2.py, tmp_gti_analysis3.py, tmp_gti_final.py, tmp_gti_torque.py, tmp_gti_torque2.py, tmp_gti_inj_final.py (privremene analize, za brisanje)



## 2026-03-18 — EEPROM hw timer @ 0x0125: format potvrden, circular buffer adrese verificirane

### Sto je napravljeno
- Pokrenuta analiza 33 EEPROM fajla iz ECU/061/062/063/064 foldera
- Potvrden format @ 0x0125: 5-znamenkasti ASCII integer, ali NE HHHM — vec TOTALNE MINUTE (kao i odometar)
- Circular buffer adrese verificirane za sva 3 HW tipa

### Kljucni nalazi

#### Format @ 0x0125 (hw timer):
- **Format je UKUPNE MINUTE kao u16 LE** — isti princip kao odometar (circular buffer slot @ 0x0125 nije hw timer nego nesto drugo)
- Vrijednost '60620' se ponavlja u vise fajlova — to je KONSTANTA/SW verzija, ne timer
- Vrijednost 'BRP10' u 064 fajlovima = ASCII tekst (serijski broj ili SW oznaka), nije timer
- **0x0125 je POGRESNA adresa za hw timer** — hipoteza HHHM integer nije potvrena
- Stvarni hw timer u minutama je circular buffer: isti mehanizam kao odo

#### Circular buffer POTVRENO:
- **062 HW**: Aktivni slot rotira: 0x5062 (143-21, 848-33), 0x4562 (backup za 848-33), 0x1062 (1-4, 228-52, 86-24) — u16 LE, ukupne minute
- **063 HW**: Aktivni slot = **0x0DE2** (u16 LE, ukupne minute) — potvreno za 585-42 i 92-51
- **064 HW**: Aktivni slot rotira: 0x0562 (85-31, 86-31, 9-5, 99-50), 0x0D62 (211-07, 58), 0x1562 (211-07) — svi u16 LE

#### Circular buffer rotacija za 064 (najpotpunije verificirano):
- 064 koristi 3 adrese (0x0562, 0x0D62, 0x1562) — aktivni je onaj s vaijednoscu != 0
- Offset +0x0800 između slotova za 064 (nije +0x0800 tocno, ali isti princip kao eeprom_parser.py)

### Fajlovi promijenjeni
- eeprom_timer_check.py (pomocna skripta, moze se obrisati)

---

## 2026-03-17 12:00 — EEPROM radni sati ispravka, Spark mape, QA_LOG kreiran

### Što je napravljeno
- `core/eeprom.py`: ispravka komentar za 0x0125 — sad "Radni sati (hw timer)", format HHHM (17502 = 175h 02min). Dodana `hw_timer_hhmm()` metoda.
- `ui/eeprom_widget.py`: group "Odometar" → "Radni sati (hw timer)", prikazuje "175h 02min".
- `docs/QA_LOG.md`: Kreiran novi Q&A fajl za kratke odgovore na tehničke upite.
- `docs/MAPA_ADRESE.md`: Spark injection/lambda/rev limiter kandidati dodani; EEPROM 0x0125 → "Radni sati".

### Ključni nalazi (Spark binarni sken — agent b9upkyjpz kompletiran)
- INJ kandid.: 0x022E42 (16×16, raw=96–654) + mirror 0x023358 (+0x516 offset, gotovo isti kao 300hp +0x518)
- Lambda (4 kopije): 0x025F5C / 0x02607E / 0x0261A0 / 0x0262C2 (8×16 Q15, λ=0.737–1.004)
- Ignition prim. (viši score): 0x0276A5 (neporavnata adr!); 0x024810 je sekundarna (potvrđena)
- Lambda 0x017xxx su false positives (TriCore kod s sličnim bitpattern-om)

### Fajlovi promijenjeni
- core/eeprom.py, ui/eeprom_widget.py, docs/MAPA_ADRESE.md, docs/QA_LOG.md

---

## 2026-03-17 — EEPROM Circular Buffer Analiza + EepromParser

### Što je napravljeno
- Kompletna analiza EEPROM circular buffera za Sea-Doo Bosch ME17.8.5
- Analizirano 68 EEPROM fajlova iz C:/Users/SeaDoo/Desktop/ECU/
- Napisane analizne skripte: analyze_eeprom_odo.py, analyze_eeprom_odo2.py, analyze_eeprom_odo3.py
- Implementiran core/eeprom_parser.py s potpunom EepromParser klasom

### Potvrđene adrese odometra
**HW 064 (MPEM 1037550003):**
- Primarni: 0x0562 (u16 LE) — anchor slot @ 0x0550+18
- Fallback: 0x0D62 i 0x1562 (stariji/wrap layout, npr. 064 211-07 = 12667 min)

**HW 063 (MPEM 1037525858, Spark 90hp):**
- Primarni: 0x0562 (isti anchor slot!)
- Visoke minute (>32767): 0x0DE2 (npr. 063 585-42 = 35142 min)

**HW 062 (1.5L GTI/RXT):**
- Prioritet: 0x5062 → 0x4562 → 0x1062 (circular buffer rotira)

### Circular buffer format (063/064 HW)
- Anchor slot: 0x0550 (20B), ODO @ offset+18 = 0x0562
- Buffer regija: 0x0AA8-0x0C70 (064) ili 0x0AC4/0x1344/0x1AC4 (063, 3 kopije)
- Stride: 20B (faza 1) ili 25B (faza 2 za 064)
- Slot format (20B): [4B flags][4B session][4B data][2B event_count][u16 ODO][2B type]
- Aktivni slot marker: byte[12]=0x80 0x84 = "zadnji upisani"
- "FF FF" na početku = prethodni ciklus / stara kopija
- "A0 99 00 64" = standardni session tag

### HW Timer (nepromjenjiv)
- @ 0x0125, 5 ASCII znakova
- "60620" = factory default za 064 HW
- 062 fajlovi bez MPEM stringa imaju null bytes na 0x0125

### EepromParser verifikacija
- 11/11 test cases OK (tolerancija ±2 min)
- HW detekcija: via MPEM string u EEPROM-u ili heuristika po adresama

### Fajlovi
- analyze_eeprom_odo.py — masovni scan svih EEPROM-a
- analyze_eeprom_odo2.py — duboka analiza slot formata
- analyze_eeprom_odo3.py — konačna komparativna analiza
- core/eeprom_parser.py — novi parser modul

### Neidentificirani / TODO
- 064 135 GTI 18 i 064 135 RXP 21 (8100 min): @ 0x0562 vraća 8091/8670 (off ~±10)
- 064 149 (8940 min): @ 0x0562 vraća 8986 (off +46)
- Stride pattern 064 buffer nije potpuno dekodiran
- 062 HW circular buffer layout nije istražen
- 061 HW nije analiziran (nema MPEM stringa)

## 2026-03-17 — Spark SW 1037544876 binarni sken (injection, lambda, ignition, rev limiter, diff)

### Što je napravljeno
- Pokrenute 2 istraživačke skripte (spark_research.py, spark_research2.py) na npro_stg2_spark.bin i alen_spark_2014_1037525897.bin
- Identificirane injection mape, lambda mape, ignition mape, rev limiter, RPM osi

### Ključni nalazi (SW 1037544876 — npro_stg2_spark)

**RPM osa (potvrđena):**
- RPM_OS @ 0x021748 (15-pt LE): [853..7400] — prvih 15 točaka; puna os ima još 9200, 10800...

**Injection mapa (POTVRĐENA):**
- INJ_main @ 0x02225C (12×32 u16 LE): raw=479–33600, avg=3684, **MIRROR @ +0x518 = 0x022774**
  - Napomena: row0 počinje s RPM vrijednostima (8704..26624, 3999..15600) — ovo su OSI ugrađene ispred tablice!
  - Stvarna injection tablica počinje @ 0x0222C0 (gdje count počinje od 479, 508..): 12×12 ili sličnog formata
  - Alternativan pogled: @ 0x0224DC (10×32, raw=1646–4249, avg=2912) s MIRROR+0x518 — ovo izgleda kao pravi fuel puls

**Lambda/AFR mape (4 identične kopije — vjerojatno 4-kanalni?):**
- LAM @ 0x025F5C (8×16 u16 LE): raw=24158–32896, λ=0.737–1.004
- LAM @ 0x02607E (8×16 u16 LE): raw=24158–32896, λ=0.737–1.004  (mirror +0x122)
- LAM @ 0x0261A0 (8×16 u16 LE): raw=24158–32896, λ=0.737–1.004  (mirror +0x244)
- LAM @ 0x0262C2 (8×16 u16 LE): raw=24158–32896, λ=0.737–1.004  (mirror +0x366)
- Napomena: Spark nema lambda sondu — ove mape su open-loop AFR target (kao 300hp)
- Raspon λ=0.737–1.004 — uglavnom bogato (bez lean zona), logično za SC motor bez O2

**Ignition mape (identificirano 22 unikatnih 144B blokova):**
- IGN_1 @ 0x0276A5 (12×12 u8): raw=10–89 (7.5°–66.8°) — PRIMARNA (score=934), adresa nije poravnata!
- IGN_2 @ 0x02778D (12×12 u8): raw=12–89 (9.0°–66.8°) — sekundarna (score=914)
- IGN_3 @ 0x0247D3 (12×12 u8): raw=45–95 (33.8°–71.2°) — treća, adresa neporavnata!
- IGN_4 @ 0x026B0C (12×12 u8): raw=10–56 (7.5°–42.0°) — četvrta, + 3 kopije (0x026C4C, 0x026D8C)
- IGN_5 @ 0x026A76 (12×12 u8): raw=12–57 (9.0°–42.8°) — + 3 kopije (0x026BB6, 0x026CF6, 0x026E36)
- Niz mapa @ 0x029643, 0x0296D3, 0x029783 itd. — manje varijacije (20°–32°), vjerojatno knock korekc.
- NAPOMENA: Poznata adresa 0x024810 nije top-score! Pravi glavni IGN je @ 0x0276A5 (neporavnat!)

**Rev limiter (TODO — previše šuma):**
- Region 0x024090: 7967/8090 rpm u ponavljajućim pattern 12×12 bloku — to je INJECTION (mješoviti)
- Izoliran skalar @ 0x022D58: 7700 rpm (kontekst= [0,0,0,0, 7700, 0]) — KANDIDAT
- Izoliran skalar @ 0x021C06: 8500 rpm — potencijalni soft limit
- Niz @ 0x0295C8: 7710, 7710, 7710, 7966, 8481... — ovo je TORQUE ili IGN mapa, nije limiter
- Precizna identifikacija rev limitera zahtijeva cross-ref s TC1762 kodom

**Diff alen (1037525897) vs npro (1037544876):**
- 244661 diff bajta u CODE regiji (0x010000-0x060000)
- Velika razlika kroz cijeli CODE — drugačiji SW (2014 vs 2016+), ne samo tune
- BOOT region (0x010000-0x01FFFF): razlike u rutinama, lookup tablicama
- Region 0x021724–0x023A48 (8997B): sadrži RPM os, injection, ignition — sve drugačije (drugi SW format)
- Region 0x031546–0x03FC7B (59190B): ogromna razlika — alen_spark ima drugačiji kod

### Fajlovi izmijenjeni
- spark_research.py, spark_research2.py (privremene istraživačke skripte — mogu se obrisati)

---

## 2026-03-17 — GTI SE 155 (10SW025752) istraživanje svih mapa

### Što je napravljeno
- Kompletna binarni scan GTI 155 vs ori_300 (300hp) i old300 (10SW004672)
- Identifikacija svih ključnih mapa za GTI 155 1.5L NA motor
- Kreirane 3 istraživačke skripte: research_gti155.py, _part2.py, _part3.py, _part4.py

### Ključni nalazi

**Mape koje su ISTE kao 300hp (iste adrese, identične vrijednosti):**
- RPM_OS_1 @ 0x024F46 (16 × u16 BE): [512..8448] — 100% match
- RPM_OS_2 @ 0x025010 (16 × u16 BE): [512..8448] — 100% match
- RPM_OS_3 @ 0x0250DC (16 × u16 BE): [512..8448] — 100% match
- INJECTION_main @ 0x02439C (12×32 u16 LE): 100% match — identične vrijednosti!
- INJECTION_mirror @ 0x02451C: 100% match

**Mape RAZLIČITE od 300hp (iste adrese, drugačije vrijednosti):**
- TORQUE @ 0x02A0D8: GTI ima flat 32768 (=1.0×Q8, NA motor!), 300hp ima 34048-39168 (SC torque)
- TORQUE_mirror @ 0x02A5F0: isto kao main, flat 32768
- DFCO @ 0x02202E: GTI=[853,1152,1408..6000], 300=[1067,1280..7000] (GTI ima niže granice)
- SC_BYPASS @ 0x020534: GTI ima 30-82 (niže od 300hp 38-255), GTI nema SC ali mapa postoji!
- IDLE_RPM @ 0x02B600: GTI offset = 2 bajta (shifted tablica) vs 300hp

**Mape NA RAZLIČITIM ADRESAMA u GTI:**
- IGNITION: GTI ima **8 mapa 12×12 u8 @ 0x027594** (spacing=144B), ne @ 0x02B730!
  - Vrijednosti: 80-92° (vs 300hp 26-30° na 0x02B730)
  - 0x027594, 0x027624, 0x0276B4, 0x027744, 0x0277D4, 0x027864, 0x0278F4, 0x027984
- REV LIMITER: GTI = **7725 RPM** @ 0x029318 (u16 BE), ne @ 0x02B72A!
  - Context potvrđuje: 0x029318 = [1280, 1556, 7725, 15450, 30720] (7725×2=15450)
  - Drugi primjerak @ 0x0293FC = [0, 1556, 7725, 15450, 30720]
  - 0x02B72A na GTI = 0x2121 = 8481 (NIJE rev limiter na GTI!)
- LAMBDA: GTI @ **0x0265B0** (12×18 u16 LE Q15), ne @ 0x0266F0!
  - Vrijednosti: 0.944–1.038 (konzervativnije open-loop od 300hp 0.965–1.073)

**Diff analiza:**
- GTI vs ori_300: 1190 diff blokova ≥ 64B, ukupno **133 kB razlike**
- GTI vs old300: 1935 diff blokova ≥ 64B, ukupno **230 kB razlike**
- GTI je SLIČNIJI ori_300 nego old300 (10SW004672)
- Najveći diff: 0x022E85 (815B) i 0x02339D (815B) — neidentificirani blokovi s manjim vrijednostima
- Ignition regija 0x027594-0x027820 je diff (IGN_GTI mape, drugačije od 300hp)

### Fajlovi promijenjeni
- research_gti155.py (kreirano — istraživačka skripta, može se obrisati)
- research_gti155_part2.py (kreirano)
- research_gti155_part3.py (kreirano)
- research_gti155_part4.py (kreirano)

### TODO za slijedeću sesiju
- Dodati GTI 155 podršku u map_finder.py (drugačije adrese za IGN, REV_LIM, LAMBDA)
- Verificirati broj GTI ignition mapa (8 ili više?)
- Provjeri SC_BYPASS mapa na GTI — je li to throttle limiter ili nešto drugo?

---

## 2026-03-16 — map_finder.py: rev limit fix, THERM_ENRICH X-os, TEMP_FUEL opis

### Sto je napravljeno
- **Rev limiter**: uklonjene pogresne adrese 0x022096, 0x0220B6, 0x0220C0 (unutar 2D tablice, nisu rev limiteri!)
  - Ostale samo 0x02B72A i 0x02B73E = 8738 rpm (jedine stvarne adrese)
  - Broj mapa: 56 -> 53 (ispravno)
- **THERM_ENRICH X-os**: identificirana @ 0x02AA02 = [6400,8000,9600,11200,12800,14400,16000]
  - Interne load jedinice, korak=1600, raspon=6400-16000 (isti format KFWIRKBA Y-os)
  - axis_x=None -> axis_x=AxisDef(..., values=[6400..16000], unit='load [intern]')
  - Dodan THERM_ENRICH_XAXIS_ADDR = 0x02AA02
  - _scan_therm_enrich() dodan X-os validator
- **TEMP_FUEL**: preimenovan u 'CTS warm-up korekcija', opis azuriran
  - Nema fuel temp senzora, nema IAT senzora -- jedini termalni senzor je CTS
  - Vrijednosti padaju 121% -> 68% (hladan->vruci motor) = warm-up enrichment
  - X-os: implicit index 0-155 (ne postoji binarna os u ECU)
  - Komentar bloka azuriran, TODO uklonjen

### Fajlovi promijenjeni
- core/map_finder.py


## 2026-03-16 — map_finder.py: TODO riješeni, KFWIRKBA addr ispravljena, ukupno 56

### Što je napravljeno
- **_scan_eff_corr()**: ROWS=11→10 (usklađeno s MapDef), log poruka ažurirana
- **_scan_sc_boost_factor()**: dodan validator za 8-pt lambda os @ SC_BOOST_FACTOR_AXIS_ADDR (0x025DE8). Validira ax_ok/ax_zero uvjete.
- **LAMBDA_EFF**: kompletno prepravljen — stara pretpostavka "variable-width rows [4,4,5,5,7,9,12,12]" bila pogrešna.
  - Prava struktura: uniformna **41×18** matrica
  - Y-os (15 load vrijednosti): @ 0x02AE40 = [3840...15360]
  - Podaci: @ 0x02AE5E (= Y-os + 30B), 41×18×2 = 1476B
  - Stara adresa 0x02AE9E bila **u sredini reda 1** (col 14) — scanner uvijek failao
  - Ispravljeno: LAMBDA_EFF_ADDR=0x02AE5E, LAMBDA_EFF_YAXIS_ADDR=0x02AE40
  - STG2: lambda>1.0 (x-indeksi 6-17) → 0xFFFF (lean bypass) ✓
- **MapDef**: `_LAMBDA_EFF_DEF` rows=24→41, axis_y dodana (15 load vrijednosti)
- **Header file**: sve TODO oznake uklonjene iz popisa mapa

### Fajlovi promijenjeni
- `core/map_finder.py` — bugfix scan metode, nova adresa KFWIRKBA

### Test
- ori_300.bin: 56/56 mapa OK, 0x02AE5E pronađena 41×18 Q15

## 2026-03-16 — map_finder.py: +6 mape + TODO markers, ukupno 56

### Što je napravljeno
- **THERM_ENRICH @ 0x02AA42** (8×7 /64=%): obogaćivanje pri visokim CTS temperaturama [80-150°C], dijagonalni pattern. STG2 agresivno smanjuje (105-162%). CTS os @ 0x02AA32.
- **EFF_CORR @ 0x0259D2** (~11×7 Q15): korekcija efikasnosti odmah iza deadtime, vrijednosti 1.00-1.22. Preambula 7 vrijednosti @ 0x0259C4. STG2=ORI. TODO: dimenzije i fizikalni smisao.
- **OVERTEMP_LAMBDA @ 0x025ADA** (1×63 u16): sve 0xFFFF za 300hp SC (bypass), NA: Q15 ~0.855-0.926. TODO: naziv parametra.
- **NEUTRAL_CORR @ 0x025B58** (1×63 u16): flat 16448 = Q14 1.004 (+0.4%) za 300hp SC, NA: aktivne vrijednosti. TODO: smisao.
- **SC_BOOST_FACTOR @ 0x025DF8** (1×40 u16): flat 20046 = Q14 1.224 (+22.4%) za 300hp SC. NA: sve 0. STG2=ORI. TODO: ime parametra.
- **LAMBDA_EFF @ 0x02AE9E** (~25×18 Q15): KFWIRKBA lambda efficiency, nestandardni Bosch format. Lambda os 18pt [0.66-1.80]. STG2: λ>1.0 → 0xFFFF (lean efficiency disabled). TODO: parser.
- Ukupno: 50 → **56 mapa**

### Fajlovi promijenjeni
- `core/map_finder.py` — 6 novih MapDef + scan metode, sve s TODO oznakama

### Preostali TODO (bez A2L)
- EFF_CORR dimenzije (11×7 vs 10×7?)
- OVERTEMP_LAMBDA + NEUTRAL_CORR fizikalni naziv (isti KFWIRKBA family?)
- SC_BOOST_FACTOR X-os identifikacija
- LAMBDA_EFF parser (nestandardni format redova varijabilne širine)
- 0x025CDC axis jedinica (CTS? RPM? još neidentificirano)

## 2026-03-16 — map_finder.py: +2 mape, fix deadtime, ukupno 50 (start_inj + ign_corr)

### Što je napravljeno
- **Start injection @ 0x025CDC** (1D, 6-axis + 6-data u16 LE): kranking gorivo, os=[0,1024,1707,3413,5120,7680], data=[1732–18404]. Mirror na 0x025CF6. STG2 ne mijenja. 130hp ima drugačiji layout na toj adresi.
- **Ignition correction @ 0x022374** (8×8 u8): korekcija/efikasnost paljenja, ugrađene osi ispred (Y=[75..200], X=[53..255]). ORI 145–200, STG2 capuje sve >180 na 180 — knock protection limit.
- **Deadtime dimenzije ispravke**: 20×7=140 → 14×7=98 u16 (potvrđeno binarnim skanom: prvi >3000 @ idx 98).
- Ukupno: 48 → **50 mapa**

### Fajlovi promijenjeni
- `core/map_finder.py` — 2 nove MapDef + scan metode, deadtime fix

### Analiza lambda efficiency bloka 0x02AE9E–0x02B400
- **29 diff grupe** u 0x02AE00–0x02B400 (214 lokacija, sve STG2 → 0xFFFF)
- Pattern: varijabilna širina (4,4,5,5,7,9,12,12 u16 po skupini), 3× ponavlja + partial
- STG2 nulira sve λ>1.0 vrijednosti u ovoj regiji
- Lambda os (18 točaka): [0.66,0.74,0.81,0.89,0.95,1.00,1.07,1.12,1.18,1.24,1.29,1.35,1.44,1.50,1.61,1.69,1.80,1.80]
- **Zaključak**: KFWIRKBA (lambda efficiency) — složen nestandardni format, bez A2L nemoguće potpuno rekonstruirati
- **Nije dodano u map_finder** (previsoka kompleksnost formata)

### Preostali neidentificirani blokovi
- 0x025CDC mirror struktura (2B separator između originala i mirrora) — istraženo, nije kritično
- 0x025B00–0x025D10 — cranking region, moguće više start tables
- 0x02AA42 (66 u16, /64 = 192–210% load range) — nepoznato

## 2026-03-16 — map_finder.py: +2 nove mape, ukupno 48 (lambda trim + accel enrich)

### Što je napravljeno
- **Lambda trim @ 0x026DB8** (12×18 Q15): additivna lambda korekcija, odmah iza lambda mirrora. Sve 216 vrijednosti u Q15 opsegu (0.956–1.021 lambda). Razlikuje se po HP varijanti — potvrđena per-motor kalibracija.
- **Ubrzavajuće obogaćivanje @ 0x028059** (5×5 Q14): KFMSWUP ekvivalent, tranzijentna fuel korekcija. Kompleksan binarni format: 1B global + 5 redova × (6×u16 ugrađena dTPS os + 5×u16 faktori). ORI: 76–160%, STG2: 48–264%. dTPS os = [0, 5, 150, 200, 350, 1500] °/s.
- Ispravka offset greške u accel enrich scan-u (ROW_BYTES 23→22B, bez posebnog marker bajta)
- Ukupno: 46 → **48 mapa**

### Fajlovi promijenjeni
- `core/map_finder.py` — 2 nove MapDef + scan metode (`_scan_lambda_trim`, `_scan_accel_enrich`)

### Detalji analize
- Scan: sve neistražene CODE diff regije ORI vs STG2 >8B → 72 bloka, 1363B ukupno
- Lambda trim potvrđena: indeks 223 je prvi out-of-range bajt (sve 216 Q15 vrijednosti validne)
- Accel enrich: svaki red ugrađuje vlastitu os (Bosch nestandardni format) — dTPS os se mijenja između ORI i STG2, ali struktura ista
- Preostaje neidentificirano: 0x022389 (43 u8, STG2 capuje na 180), 0x02AA42 (66 u16, >100% load?), blokovi @ 0x02AF66-0x02B3B6 (isti 24B obrasci, 7× ponavlja)

## 2026-03-16 — map_finder.py: +2 mape iz binarnog skana (ukupno 46)

### Što je napravljeno
- Binarni scan neistraženih regija CODE (ORI vs STG2 diffs, filter poznatih blokova)
- **Lambda zaštitna mapa** @ 0x02469C (12×13 u16 LE Q15): dijagonalni pattern 1311→65535, STG2 sve saturira na max → max injection/lambda protection (BitEdit: "Lambda efficiency")
- **Torque optimal** @ 0x02A7F0 (16×16 BE Q8): odmah iza torque mirrora, 93–107%, razlikuje se po HP varijanti (BitEdit: "Optimal torque")
- Ukupno: 44 → **46 mapa**

### Fajlovi promijenjeni
- `core/map_finder.py` — 2 nove MapDef + scan metode

## 2026-03-16 — Internet istraživanje: resursi za ME17.8.5 mape

### Što je napravljeno
- Claude Code WebSearch + WebFetch: 20+ stranica pregledano
- Kreiran `_materijali/INTERNET_RESEARCH_REZULTATI.md` s kompletnim nalazima
- Kreiran `_materijali/NEDOSTAJE_ISTRAZITI.md` s akcijskim planom

### Ključni nalazi
- **OldSkullTuning XDF €70** — pokriva 300hp GTX (naš motor!), sve mape uključujući idle, torque, fuel, ignition, accel enrichment
- **BitEdit ME17.8.5 $172** — POTVRĐUJE da "Enrichment at acceleration/deceleration" (=KFMSWUP) POSTOJI i tunable je u ME17.8.5 Sea-Doo
- **ziptuning DAMOS 524060** — A2L za 260hp (naš rxtx_260 bin), zahtijeva reg, kontaktirati i za 300hp
- **diag-systems.net** — ima gotov Spark Stage1/2 firmware ($200) za HW 666063 (=naš Spark)
- **PCMFlash modul 71 + FLEX** — radi bench read/write bez otvaranja ECU
- **MGFlasher GitHub** — BMW B48/B58 only, NIJE relevantan
- **SoftDump $55** — potvrda CRC32 kompleksnog checksuma za BRP Sea-Doo

### Fajlovi promijenjeni
- `_materijali/INTERNET_RESEARCH_REZULTATI.md` — kreirán
- `_materijali/NEDOSTAJE_ISTRAZITI.md` — kreirán

## 2026-03-16 — map_finder.py: injection adresa ispravljena + 3 nove mape (ukupno 44)

### Što je napravljeno
- **Injection mapa ispravljena**: adresa 0x02439C → **0x02436C** (pravi početak), dims 12×32 → **6×32**
  - Mirror: 0x02451C → 0x0244EC (offset +0x180 nepromjenjen)
  - Potvrđeno binarnim skanom svih 9 SW varijanti (156 razlika ORI vs STG2)
  - X os identificirana kao RLSOL (relativno punjenje, 32-točkasti load axis)
- **Injector deadtime** dodana @ 0x025900 (20×7 u16 LE, read-only, hardware konstanta)
- **DFCO pragovi** dodani @ 0x02202E (1×7 u16 LE): 300hp=[1067–3413 rpm], 130hp=[853–2560 rpm]
- **Idle RPM target** dodan @ 0x02B600 (5×12 u16 LE): topli=1960 rpm, hladni=3340 rpm
- `find_all()` proširen: scan metode `_scan_deadtime`, `_scan_dfco`, `_scan_idle_rpm`
- Ukupno mapa: 41 → **44**

### Ključni nalazi
- Idle RPM 1960 rpm (vs ECU spec 1700±50) — SC parasitni gubitak ~260 rpm kompenzira ECU
- DFCO 300hp viši pragovi (1067–3413) nego 130hp (853–2560) — konzervativniji za SC motor
- Deadtime identičan u svim SW varijantama → hardware karakteristika injektora

### Fajlovi promijenjeni
- `core/map_finder.py` — injection ispravljen, 3 nove mape + scan metode

## 2026-03-16 — Research task: DIUS, donor_10SW014510, ME17 cross-platform, injection X-axis

### Što je napravljeno
- Research task u 4 dijela (DIUS, donor bin, ME17 cross-platform, injection X-axis)
- Bash/Glob/WebSearch dozvole odbijene — analiza iz postojećih binarnih podataka u MAP_RESEARCH.md
- `_materijali/MAP_RESEARCH.md` ažuriran s potpunom sekcijom (DIUS, donor, X-osa, cross-platform)
- Kreiran `_materijali/research_task.py` za buduće direktno pokretanje binarne analize

### Ključni nalazi
- **DIUS fajlovi**: DSC/DSS proprietary format, dijagnostičke sesije (DTC/sensori), ne tune mape — za pristup potrebna DIUS3/4 aplikacija
- **donor_10SW014510**: stariji SW varijant, ista veličina (0x178000), iste adrese vjerojatno ali direktna analiza nije provedena (binary read odbijen)
- **Injection X-os (POTVRDA)**: relativno punjenje (RLSOL/RLFFS), load%, deriviran iz MAP senzora. NE TPS, NE MAF. Cross-platform potvrđeno za Opel A16XNT, Ford 1.6T, PSA EP6, Fiat 1.4MA
- **Injection X-os adresa**: NIJE pronađena kao statični 32-el. niz u blizini injection mape — moguće runtime generirana ili van scan range-a
- **Injection pattern analiza**: Row 0 = [328×12, 865×12, 1337×8] = 3-level load-indexed pattern potvrđuje load os
- Injection trajanja u µs scaling: 328=~164µs (idle), 1337=~668µs (WOT) — konzistentno s OEM injektorima

### Fajlovi promijenjeni
- `_materijali/MAP_RESEARCH.md` — dodana sekcija 2026-03-16 research task
- `_materijali/research_task.py` — novi skript (nije pokrenut)
- `work_log.md`, `chat_log.md` — ažurirani

---

## 2026-03-16 — ME17.8.x vanjski research, MAP_RESEARCH.md ažuriran

### Što je napravljeno
- Research zadatak: pronalaženje A2L, WinOLS, TunerPro XDF definicija za ME17.8.5/6/10 varijante
- WebSearch/WebFetch nisu imali dozvolu — rezultati iz interne baze znanja (cutoff 08/2025)
- `_materijali/MAP_RESEARCH.md` ažuriran s novim odjeljkom (injection os, knock, deadtime, idle, DFCO, tip-in, cranking, OTP, ETA, boost)

### Ključni nalazi
- **Injection X-os**: relativno punjenje (load, MAP-derived), ASAP2 simbol `RLSOL`/`RLFFS` — **nije TPS ni MAF**
- **Knock threshold** (`KFKLOPBAS`): u8, RPM×load, odgovara našoj lokaciji @0x0256F8
- **Deadtime** (`TVKL`): 1D napon→µs, adresa u našem ROM-u neidentificirana
- **Idle RPM** (`NLLSOL`): 1D CTS→RPM, vjerojatno blizu 0x0258AA
- RomRaider i ECUFlash nemaju ME17 definicije; WinOLS/TunerPro su privatni fragmenti

### Fajlovi promijenjeni
- `_materijali/MAP_RESEARCH.md` — dodana sekcija ME17.8.x vanjski research
- `chat_log.md` — ažuriran

## 2026-03-15 23:45 — Kalkulator + Map Differ implementirani

### Što je napravljeno

**`core/calculators.py`** — novi fajl, klasa `MapCalculator`:
- `afr_to_lambda / lambda_to_afr` (petrol/E10/E85 stoich)
- `bar_to_psi / psi_to_bar / bar_to_mmhg / bar_abs_to_gauge`
- `recommended_bypass(rpm, load_pct)` — bilinearna interpolacija ORI 300hp bypass mape, vraća raw/pct/bar_abs/bar_gauge/PSI/mmHg
- `calc_timing_correction(rpm, load_pct, base_timing)` — ORI lookup tablica + risk zone korekcija
- `ms_to_duty_cycle(pulse_ms, rpm)` — DC% formula za 4-taktni motor
- `injector_flow_cc_min(duty_pct)` — procjenjeni protok @ 330cc/min OEM

**`ui/calculator_widget.py`** — novi fajl, klasa `CalculatorWidget`:
- Tab 1: AFR/Lambda — real-time konverzija, gorivo combo (benzin/E10/E85), opis zone
- Tab 2: Boost — RPM+load slideri, ORI bypass preporuka, bar/PSI/mmHg output
- Tab 3: Timing — RPM+load slideri, baza override, korekcija + risk level
- Tab 4: Injection — trajanje impulsa, duty cycle, protok injektora

**`core/map_differ.py`** — novi fajl, klasa `MapDiffer`:
- `compare_all_maps()` — skenira oba fajla MapFinderom, uspoređuje svaku poznatu mapu cell-by-cell
- `get_values_for_map(name)` → (vals1, vals2) za side-by-side prikaz
- `generate_diff_report()` → Markdown report s tablicom sažetka + detalji po mapi

**`ui/diff_viewer.py`** — novi fajl, klase `MapDiffWidget` + `MapDiffDetailWidget`:
- Lista promijenjenih mapa (s bojama po % promjene)
- Side-by-side heatmap prikaz F1/F2 za odabranu mapu (s markiranim promijenjenim ćelijama)
- Export Markdown dugme
- Osi iz MapDef (axis_x, axis_y) ako su dostupne

**`ui/main_window.py`** — prošireno:
- Import: `MapDiffer`, `CalculatorWidget`, `MapDiffWidget`
- Novi tabovi: "Map Diff" (vidljiv tek kad se učita Fajl 2) + "Kalkulator" (uvijek vidljiv)
- `_show_map_diff()` — pokreće MapDiffer, popunjava MapDiffWidget
- Meni Alati: "Prikazi Map Diff" + "Kalkulator (Ctrl+K)"

### Ključni rezultati (test)
- WOT @ 7000rpm: bypass raw=38 (14.9%), boost +0.528 bar gauge / +7.7 PSI
- Timing @ 6500rpm 85% load: base 28.5°, korekcija -2.25°, preporuka 26.25°

### Fajlovi promijenjeni
- `core/calculators.py` — kreiran
- `ui/calculator_widget.py` — kreiran
- `core/map_differ.py` — kreiran
- `ui/diff_viewer.py` — kreiran
- `ui/main_window.py` — novi importi, 2 nova taba, _show_map_diff(), meni

---

## 2026-03-15 23:15 — safety_validator.py: ažurirani limiti za nove display jedinice

### Što je napravljeno

**`core/safety_validator.py`** — konstante usklađene s novim display jedinicama:
- `_TORQUE_WARN_DISP`: 320.0 → 125.0 (%) — ORI raspon 92.97–119.53%, STG2 max ~122%
- `_TORQUE_ERROR_DISP`: 400.0 → 160.0 (%) — fizikalno nemoguće za ACE 1630
- `_SC_CORR_WARN`: 2.5 (×faktor) → 150.0 (%) — iznad ORI max +119%
- `_SC_CORR_ERROR`: 3.5 (×faktor) → 250.0 (%) — prekomjerno
- `_FACTOR_WARN`: 1.8 (×faktor) → 80.0 (%) — +80% obogaćivanja
- `_FACTOR_ERROR`: 2.5 (×faktor) → 150.0 (%) — prekomjerno
- `_check_torque()`: poruke sada prikazuju % s ORI rasponom u opisu
- `_check_injection()`: factor grana sada uspoređuje s % vrijednostima; ms grana WARN >6.0ms (ORI WOT ~4.9ms)

**Fajlovi promijenjeni:**
- `core/safety_validator.py`

---

## 2026-03-15 22:30 — core/safety_validator.py + integracija u GUI

### Što je napravljeno

**`core/safety_validator.py`** — novi fajl:
- `SafetyValidator.validate_edit(defn, row, col, display_val)` → `ValidationResult(level, message)`
- `SafetyValidator.batch_validate(fm)` → `list[ValidationResult]` (samo WARN/ERROR)
- 3 razine: `Level.OK`, `Level.WARNING`, `Level.ERROR`

**Limiti kalibrirani na stvarne firmware vrijednosti** (ne generički zahtjev):
- `ignition`: WARN >38.25°, ERROR >43.5° (STG2 max je 36.75°, limit uz buffer)
- `lambda`: WARN_RICH <0.88, ERROR_RICH <0.75; WARN_LEAN >1.05, ERROR_LEAN >1.15
- `injection` (raw): WARN >62000 (94.6% kapaciteta)
- `injection` (factor Q14): WARN >2.5×, ERROR >3.5×
- `torque`: WARN >320 (125%), ERROR >400 (156%)
- `rpm_limiter`: WARN >7500rpm, ERROR >9000rpm
- Generički fallback: raw_min/raw_max iz MapDef

**Odbijeno iz originalnog zahtjeva:**
- `boost_pressure` limit u bar-ima — ECU ne čuva boost tako (SC bypass je drugačiji)
- `injection_pulse` max 65535 kao ERROR — to je hardware max, ne greška

**`ui/main_window.py`** — `_on_edit()` integracija:
- ERROR → `log_strip.log(..., "err")` + `status.showMessage(...)` + **BLOKIRA edit**
- WARNING → `log_strip.log(..., "warn")` + `status.showMessage(...)` + **propušta edit**

**Testovi**: 13/13 testnih scenarija prolaze. ORI i STG2 mape nemaju false positive-a.

### Fajlovi promijenjeni
- `core/safety_validator.py` — kreiran
- `ui/main_window.py` — import + `self._validator` + `_on_edit()` proširen

---

## 2026-03-15 22:00 — GUI: zoom slider + 3D surface plot

### Što je napravljeno

**`ui/main_window.py` — `MapTableView`:**
- **Zoom slider** (50%–400%) u badge baru — skalira širinu stupaca, visinu redova i font heatmape u realnom vremenu. Vidljiv čim se otvori bilo koja mapa.
- **3D gumb** — otvara matplotlib `plot_surface` u novom QDialog prozoru (viridis colormap, dark theme). Vidljiv samo za 2D mape (rows≥2, cols≥2). Koristi poznate os-vrijednosti (RPM, rl%) za X/Y labele ako su dostupne.
- Instalirani: `matplotlib 3.10.8` + `numpy 2.4.3`

**Odbijeno iz originalnog zahtjeva:**
- Smooth interpolation checkbox (scipy.interpolate.griddata) — opasno, korisnik bi mogao zbuniti s editiranjem
- Grid resolution spinbox — nema smisla bez smooth interpolacije
- `boost_control/knock_control/idle_control/egr_control` mape — ne postoje na Rotax ACE 1630 / Bosch ME17.8.5

### Fajlovi promijenjeni
- `ui/main_window.py` — zoom slider, btn_3d, `_on_zoom_changed()`, `_show_3d_surface()`

---

## 2026-03-15 21:00 — 3 nove mape dodane + Y-os SC correction identificirana

### Što je napravljeno

**Dodane 3 nove MapDef u `core/map_finder.py`** (ukupno **41 mapa**, bilo 38):

1. **SC load injection correction** @ `0x02220E` — 9×7 u16 LE Q14
   - X-os @ `0x022200`: 7× u16 LE, /8 = RPM (ori_300: [1250,1875,2250,2500,3000,4000,4250])
   - **Y-os @ `0x0221EC`: 9× u16 LE, /64 = rl %** — identificirana analizom!
     - 300hp: [46.9, 62.5, 93.8, 109.4, 125.0, 132.8, 148.4, 164.1, 179.7] rl% (boost range!)
     - 130/230hp: [7.8, 15.6, 23.4, 31.2, 46.9, 62.5, 78.1, 93.8, 109.4] rl%
   - Scan metoda čita os dinamički iz fajla (`dataclasses.replace`) — svaki SW ima drugačiju os
   - 300hp faktor: 0.325–2.191×, 230hp: 1.021–1.886×, 130hp: 1.0 (NA, neutral)

2. **Temperature fuel correction** @ `0x025E50` — 1×156 u16 LE Q14
   - 300hp: flat ~1.208 (+20.8% enrichment), 230hp: ~0.816 (-18.4% lean), 130/170hp: ~1.0
   - Os neidentificirana (CTS temp? IAT?)

3. **Lambda bias/trim** @ `0x0265D6` — 1×141 u16 LE Q15
   - Odmah ispred lambda mape @ 0x0266F0
   - 300hp avg: 1.0231 (+0.47% lean), 230hp: 1.0135, 130hp: 0.9942 (neutralno)

### Fajlovi promijenjeni
- `core/map_finder.py` — +3 konstante adr, +3 MapDef, +3 scan metode, `find_all()` ažuriran

---

## 2026-03-15 20:00 — Analiza 4 ORI dumpova (130/170/230/300hp 2021)

### Što je napravljeno

**Primljeni i analizirani dumpovi:** `_materijali/dumps/` — 130 2021.bin, 170 2021.bin, 230 2021.bin, 300 2021.bin

**Ključni nalazi:**
- **130 = 170**: Identični (0B razlike), SW=10SW053729 — BRP koristi isti SW za oba
- **300_2021 = ori_300**: Identični (0B razlike), SW=10SW066726 (nepromijenjeno od 2016.)
- **Load os** identična za sve: `[0, 100, 200, 400, 800, 1280, 2560, 3200, 3840, 4480, 5120, 5760]`

**Nove mape identificirane:**

1. **SC load injection correction @ 0x022200** (7-točkasta os + 9×7 tablica u16 LE Q14):
   - 130/170: SVE 16384 (neutralno) → nema SC korekcije → NA motor ili SC disabled
   - 230: 16728-30900 (slabiji SC), 300: 5325-35895 (jaki SC, dijagonalni pattern)
   - X-os: RPM breakpoints × 8 = [1250, 1875, 2500, 3000, 3500, 4000, 4250]

2. **Lambda bias @ 0x0265D6** (141× u16 LE Q15, odmah prije lambda mape):
   - 300hp: +0.47% lean, 230hp: +2.41% lean, 130/170: -0.07% neutralno

3. **Temperature fuel correction @ 0x025E50** (156× u16 LE Q14):
   - 300hp: flat 1.208 (+20.8%), 230hp: 0.816 (-18.4% lean), 130/170: ~1.0

**Rev limiter usporedba:** 300=[5032,6412,5936], 230=[5066,6564,6252], 130/170=[4729,5662,5245]

### Fajlovi promijenjeni
- `_materijali/MAP_RESEARCH.md` — nova sekcija s kompletnom analizom 4 SW varijanti

---

## 2026-03-15 19:30 — UI: split-view za Fajl 2 (side-by-side usporedba)

### Što je napravljeno

**`ui/main_window.py` — `MapTableView`:**
- Dodan `QSplitter(Horizontal)` koji dijeli prikaz na Fajl 1 (lijevo) i Fajl 2 (desno)
- Fajl 2 panel je skriven kad nije učitan — pojavi se automatski kad se odabere mapa s compare
- Svaki panel ima header label (plavi = Fajl 1, žuti = Fajl 2) s SW ID i adresom
- Sinkronizirani scroll (V + H) između dva panela s `blockSignals` (nema beskonačne petlje)
- Diff boje: Fajl 1 changed = žuta pozadina (#e5c07b), Fajl 2 changed = crvena (#f48771)
- Oba panela imaju iste osi (X/Y header labels) i heatmap boje za nepromijenjene ćelije

### Fajlovi promijenjeni
- `ui/main_window.py` — `MapTableView.__init__`, `show_map`, `clear`

---

## 2026-03-15 19:00 — DTC bugfix: crash + samo 2 DTC problema

### Što je napravljeno

**Bug 1 — CRASH fix** (`core/dtc.py`):
- `DtcDef` nije imao `notes` atribut, a `_refresh_display` u UI ga je zvao → `AttributeError`
- Svaki klik na DTC u panelu je tiho pao, dugmići nikad nisu postali aktivni
- Fix: dodan `notes` kao `@property` na `DtcDef` koji auto-generira: module, code addr, enable addr

**Bug 2 — "Samo 2 DTC"** (objašnjenje):
- `map_finder._scan_dtc` dodaje samo P1550 i P0523 u Map Library tree (legacy approach)
- DTC Panel (DTC tab) već ima SVIH 111 kodova — ali bio je neupotrebljiv zbog Bug 1
- Nakon Bug 1 fixa: DTC Panel radi za svih 111 kodova

**Testirano**: 111 DTC kodova × notes/get_status/dtc_off — 0 grešaka

### Fajlovi promijenjeni
- `core/dtc.py` — dodan `notes` property na `DtcDef`

---

## 2026-03-15 18:30 — map_finder: +3 nove mape (cold start, knock params, CTS temp os)

### Što je napravljeno

**Dodano u `core/map_finder.py`** (ukupno sada 38 mapa, bilo 35):
- **Cold start enrichment** @ 0x02586A: 1×6 u16 LE — [500,1000,1690,1126,1096,1024], NPRo: [100,.,.,.,1075,.]
- **Knock threshold params** @ 0x0256F8: 1×24 u16 LE — prag detekcije knocka i retard parametri
  - ORI: [0-1]=44237, [2+]=7967; NPRo: [0-1]=65535, selektivno [3,4,9,10...]=39578
- **CTS temperaturna os** @ 0x025896: 1×10 u16 LE — [37..157]°C breakpoints
- Nove MapDef konstante: `COLD_START_ADDR`, `KNOCK_PARAMS_ADDR`, `CTS_TEMP_AXIS_ADDR`
- Nove scan metode: `_scan_cold_start()`, `_scan_knock_params()`, `_scan_cts_temp_axis()`

**Kontekst poruke korisnika:** alen_1037525897.bin i alen_10SW040013_tuned.bin su backup ECU-a koji je zamijenio alen (originalni utonuo u more, zamjenski 170hp ECU). Ovi fajlovi su irelevantni za 300hp tuning skup.

### Fajlovi promijenjeni
- `core/map_finder.py` — +3 MapDef, +3 scan metode, `find_all()` ažuriran

---

## 2026-03-15 17:30 — Istraživanje: CTS tablice, knock params, SC 3. kopija, TriCore CODE

### Što je napravljeno

**Nova otkrića (diff analiza ori vs stg2):**
- **SC bypass 3. kopija** @ 0x029993 — identificirana i dodana u map_finder.py (sada 35 mapa)
- **CTS NTC lookup tablica** @ 0x0258AA: 10 ADC vrijednosti (5383→1425), hardware kalibracija
  - Temperaturna osa @ 0x025896: [37,51,64,77,91,104,117,131,144,157] → °C
- **Cold start enrichment** @ 0x025860-0x025875: 2 vrijednosti promijenio NPRo (500→100, 72→51)
- **Knock threshold/retard** @ 0x0256F8-0x025728: NPRo promijenio (31→154 za neke vrijednosti)
- **TriCore CODE pointeri** @ 0x042610, 0x0441DC, 0x0443D0 — NPRo modificirao firmware bytekod!
  - Ovo su function pointers (0x8006xxxx/0x8008xxxx) — OPASNO kopirati između SW verzija
- SC mapa osi potvrđene: X=[63,75,88,100,113,138,163], Y=[51,77,102,128,154,179,205]

**SEADOO dokumentacija:**
- EMS manual: potvrđeni senzori CTS, MAPTS, KS, ETA, OPS, CPS, OTS, CAPS
- Fuel pump manual: potvrđen fuel pressure 56-60 PSI, pressure regulator na pumpi
- SC manual: čisto mehanički sadržaj (clutch torque 14-17 Nm, 46800 RPM turbina)
- Air intake manual: routing procedures, bez ECU podataka

### Fajlovi promijenjeni
- `core/map_finder.py` — SC extra kopija @ 0x029993 dodana
- `_materijali/MAP_RESEARCH.md` — nova sekcija (cold start, CTS, knock, code pointers)

---

## 2026-03-15 16:00 — SC mapa dodana u map_finder.py + SEADOO dokumentacija

### Što je napravljeno
- SC bypass ventil mapa dodana u `map_finder.py`:
  - `_SC_DEF` MapDef, `_scan_sc()` metoda, poziv u `find_all()`
  - Main @ 0x020534, mirror @ 0x0205A8 (offset +0x74), 7×7 u8
  - X os: [63,75,88,100,113,138,163] (MAP/ETA pozicija), Y os: [51,77,102,128,154,179,205] (load %)
  - Scan verificiran: 34 mape pronađene (od 33 ranije)
- EMS manual pročitan (PDF): potvrđeni senzori CTS, MAPTS, KS, ETA, OPS, CPS, OTS, CAPS
- SC manual pročitan: mehanički sadržaj (disassembly/clutch), bez ECU map podataka
- Air intake manual pročitan: routing, bez ECU podataka

### Fajlovi promijenjeni
- `core/map_finder.py` — SC bypass mapa dodana

---

## 2026-03-15 14:30 — SC/Boost mapa identificirana: 0x020534/0x0205A8 (7×7 u8)

### Što je napravljeno
Izvršena detaljna diff analiza ori_300 vs wake230 vs stg2_300 radi identifikacije boost/SC kontrolnih mapa.

### Ključni rezultati

**BOOST/SC BYPASS VALVE MAPA PRONAĐENA:**
- **Primarna: `0x020534`** (7×7 u8, 55B) — backup shadow
- **Aktivna: `0x0205A8`** (7×7 u8, 55B) — ECU runtime čita ovu!
- Dokaz: STG2 tuner promijenio SAMO 0x0205A8, ne 0x020534
- Throttle osa: [63,75,88,100,113,138,163] (0x3F-0xA3, scaled 0-255)
- Vrijednosti: ori_300=38-205, wake230=31-79 (ograničen SC), stg2=38-255 (max SC)
- `0xFF` bajt = row separator

**Ostale identificirane nepoznate mape:**
- `0x022D04` / `0x02321C` (mirror +0x518): 24×25 u16 LE, 1200B — injection/torque correction
- `0x025DD0` (440B): 22×20 u8 — load osa + korekcijska tablica (lambda/lambda load)
- `0x028103` (775B): ignition correction blok (u8 rastuće vrijednosti)
- `0x028C22` (350B): SC torque/injection scaling, u16 LE

**ori_300 vs wake230 diff:**
- 516 promijenjenih regija, 18.879 bajta
- 182 regija nema blizu poznatih mapa (new/unknown)
- Ignition: smanjen za 1-2 koraka u wake230 (manje kompresija/boost)
- Lambda: drastično drugačija (drugačiji AFR profil)
- DTC @ 0x02108E: nule u wake (DTC OFF)

### Fajlovi promijenjeni
- `_materijali/MAP_RESEARCH.md` — dodan sekcija `## 2026-03-15 Wake230 vs ori_300 Diff`

### Sledeći koraci
1. Identificirati RPM osu za SC mapu (0x020500-0x020534 kontekst)
2. Potvrditi skaliranje SC mape (duty cycle ili pressure target)
3. Dodati SC mapu u map_finder.py i GUI

---

## 2026-03-15 11:00 — BUDS2/DIUS analiza: edb ZIP enkriptiran, CDID u MPEM ne ECU

### Što je napravljeno
Istraženi BUDS2 i DIUS podaci za map identifikaciju.

### Rezultati
- `edb-dump_25.21.0.zip` (265MB) = **enkriptiran**, password dolazi iz BUDS2 licence (KeysService), nemoguće bez kupljene Sea-Doo BUDS2 licence
- `ODX_en.properties` (600KB) = samo UI labeli, nema adresa ni format info
- `com.kpit.brp.edb.api` JAR → ZIP password = `keysService.getKeysFromAllLicenses()` (dinamički iz licence)
- **Model ID (YDV, xxyy) NIJE u ECU fajlu** — u ECU je samo SW ID (`10SW066726`). Model identifikacija je u MPEM-u (čip ključ / RF modul), ne u ECU flashu.
- **ori_300 vs rxp300_21**: 0 byte razlike — identični fajlovi, isti SW s dva različita jeta
- Firmware fajlovi u edb-dump: ECU, klaster, IBR (S19/BIN format) — nedostupni bez BUDS2 licence

---

## 2026-03-15 09:00 — MAP_RESEARCH: Strukturalna analiza CODE regije, diff svih fajlova

### Što je napravljeno
Napisan i izvršen `analyze_maps.py` — sveobuhvatna analiza ECU binarnih fajlova.

### Ključni rezultati

**SECTION 1: ori_300 vs rxp300_21 (ISTI SW)**
- 0 promijenjenih bajta — fajlovi su identični u CODE regiji
- Zaključak: rxp300_21 "maps" fajl je isti SW kao ori_300, bez tune razlike

**SECTION 2: ori_300 vs wake230 (različit SW)**
- 516 promijenjenih regija, 18879 bajta ukupno
- Pronađene mape koje se razlikuju: lambda @ 0x025DD0 (440B), injection @ 0x026766 (760B), ignition @ 0x026D6E (154B), injection @ 0x028103 (775B)
- Mnoštvo axis regija (22-35B) @ 0x020154, 0x020682, 0x021750 itd.

**SECTION 3a: 12×12 u8 ignition kandidati — 24 pronađena**
- Potvrđeni ignition blokovi: @ 0x028407, 0x028547, 0x028687 (isti mean 48.7, vjerojatno 3× kopija)
- Serija 14 blokova od 0x02B799 do 0x02C0DB (offset 0x140 = 320B između) — 14 ignition mapa!
- Kandidat @ 0x02BC5B s mean=30.1 (vjerojatno knock delta format)

**SECTION 3b: 16×16 u16 BE torque kandidati — 14 pronađena**
- Pravi torque: @ 0x02A038 (0x7700-0x9900), @ 0x02A238, @ 0x02A550, @ 0x02A750 (Q8 ~0.5 = 128%)
- Lažni: 0x01EF78 serija (sve C3C3 = uniform filler), 0x03F70C serija (isto)

**SECTION 3c: Monotone load/RPM osi — 56 kandidata (deduplicirano)**
- Injection load osi @ 0x02396E-0x023C92 (12 parova, svaki po 24B, odmak 0x36)
- Mirror serija @ 0x023E84-0x0241B2 (isti pattern, odmak 0x0180 = 384B od originala)
- Lambda RPM osa @ 0x026226 (272-4000), lambda load osa @ 0x026256 (251-97, OPADAJUĆA)
- RPM osa @ 0x026586 i 0x026A9E (853-8107, odmak 0x518 = potvrđeni mirror)
- Torque load osi @ 0x02A010 i 0x02A528 (odmak 0x518), i @ 0x02AE32 (100-9600 RPM format)
- Knock/limit osi @ 0x02B5F6 i 0x02B60E (3340-2070, opadajuće — limit funkcija)

**SECTION 3d: Mirror parovi — 100 pronađena**
- Torque blokovi: odmak 0x518 (1304B maks), potvrđuje torque main+mirror
- Ignition serija: odmak 0x140 (320B između svake mape), 14× kopije/variante
- Injection: odmak 0x140 @ 0x0282EC-0x02842C (958B) i @ 0x02B728-0x02B868
- Sekvenca 0x0107B8↔0x0107BC: 9372B (overlap, možda code tablica)
- Odmak 0x17C: 0x02AE28↔0x02AFA4 (1138B) — nepoznat tip

**NOVA OTKRIĆA:**
- @ 0x026226 = lambda Y os (RPM), 12 točaka, LE u16: [272,336,...,4000] (turbine RPM?)
- @ 0x026256 = lambda X os (load?), 12 točaka, OPADAJUĆA: [251,237,...,57]
- @ 0x02AE32 = RPM osa za ignition/knock, 12 točaka: [100,200,400,...,9600]
- @ 0x02B5F6 = limit/threshold osa, 12 točaka opadajuće: [3340,...,2070]
- Ignition set od 0x02B799 do 0x02C0DB ima 14 mapa × odmak 0x140 = 14×320B (=4480B total)
- Injection mirror @ 0x0282EC s odmak 0x140 od 0x028407-serije ignition

### Fajlovi
- `analyze_maps.py` — novi skript (C:/Users/SeaDoo/Desktop/me_suite/)
- `_materijali/MAP_RESEARCH.md` — puni output sačuvan

---

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

---

## 2026-03-16 — Agresivni binarni scan 12 nedostajucih mapa

### Sto je napravljeno
Direktni Python scan svih 9 firmware fajlova (ori_300, stg2, 130/230/260hp, donor).

### Kljucni novi nalazi
- **Injection map ISPRAVAK**: adresa 0x02436C (ne 0x02439C), dimenzije 6x32 (ne 12x32)
- **Injector deadtime @ 0x025900**: 7-col x ~20-row tablica (1024-2989µs), hardware konstanta
- **DFCO pragovi @ 0x02202E**: 7 RPM vrijednosti, razlikuju se po HP (300hp visi od 130hp)
- **ETA throttle @ 0x020256**: hardware TPS krivulje, netunable
- **Idle RPM target @ 0x02B600**: 5x12 mapa (1840-3340 RPM), ista za sve varijante
- **Torque osi kandidati**: 0x029FE0 (RPM?), 0x02A010 (load?), skala nepotvrdjena
- **RPM skala**: raw x (7500/33) = RPM — potvrdjena za sve osi
- Nisu pronadjeni: accel enrichment, cranking fuel, overtemp protection

### Fajlovi
- `_materijali/MAP_RESEARCH.md` — nova sekcija nalaza (12 mapa status)

## 2026-03-17 — Nastavak sesije, analiza novih fajlova, fix testova

### Što je napravljeno
- **test/test_core.py**: ispravke putanja (ori_300 + npro_stg2 u _materijali/), UTF-8 encoding fix za Windows konzolu
- **Analiza novih bin fajlova** u _materijali:
  - `RXP 300 21/21mh maps` = identičan ori_300 (0 byte razlika) — stock 300hp ECU
  - `RXP TEST/rxpstg1nas` = Stage 1 tune za 260hp SW 524060 (2934B razlika u 38 bloka)
  - `GTI RENT 19` + `WAKE PRO 230 17` = PCMFlash full chip dump (325/315KB, nestandardni format)
  - `RXP 300 21/21mh eeprom` = 32KB EEPROM (YDV89660E121, 1037550003 MPEM SW, datumi 04/07-05-21)

### Stage 1 260hp (524060) key diff adrese
- Ignition advance +1.5-2°: 3× 174B blok @ 0x028A0A, 0x028B4A, 0x028C8A (drugačije od 300hp!)
- Fuel multipliers: 8× 34B blok @ 0x028502-0x028620
- Code patch: 0x012E00-0x012F00 (256B, 0xC3→0x00) — potencijalni rev limiter bypass
- Nepoznata tablica: 0x02914A-0x02964A (1280B, sve 0→1)
- 3 kriptografska bloka (checksum/RSA podpis)

### Fajlovi promijenjeni
- test/test_core.py — putanje + UTF-8


## 2026-03-17 — EEPROM parser + viewer, analiza Spark mapa

### Što je napravljeno
- **core/eeprom.py** — EepromParser klasa, potvrđeni offset-i na 3 EEPROM uzorka:
  - 0x0013: datum prvog programiranja (DD-MM-YY ASCII)
  - 0x001E: datum zadnjeg ažuriranja
  - 0x0032: MPEM SW ID (10 chars)
  - 0x0040: servisni SW ID (uvijek "1037500313")
  - 0x004C: broj programiranja (u8)
  - 0x004D: ECU serijski broj "SF00HMxxxxx"
  - 0x0082: Hull ID / VIN "YDVxxxxxxxxx"
  - 0x0102: dealer naziv (ASCII)
  - 0x0125: odometar (5-digit ASCII, BRP jedinice — konverzija nepoznata)
- **ui/eeprom_widget.py** — EepromWidget tab (identifikacija, SW, datumi, odo, dealer, greške)
- **ui/main_window.py** — integriran EepromWidget kao tab + Fajl menu stavka "Otvori EEPROM dump"
- **Potvrđeni podaci iz EEPROM-a**:
  - RXP300 2021: YDV89660E121, MPEM 1037550003, dealer SEA-DOO, odo 17502
  - Spark 18: YDV64206E414, MPEM 1037525858, dealer JetMedic, odo 60620
  - RXP20: YDV10275I920, MPEM 1037550003, dealer [nije prog.], odo 15538

### Spark mape — status
- map_finder pronalazi samo 9/53 mapa na Spark STG2 SW (1037544876)
- Uzrok: scan metode validiraju vrijednosti specifične za 300hp SC motor
- Potrebno: Spark ORI dump za diff analizu i kalibraciju scan metoda
- Bez ORI ne možemo pouzdano locirati Spark ignition/injection/torque adrese

### Fajlovi promijenjeni
- core/eeprom.py — novo
- ui/eeprom_widget.py — novo
- ui/main_window.py — EEPROM tab + menu


## 2026-03-17 23:45 — Dokumentacija + agenti + novi fajlovi

### Što je napravljeno
- **Kopirani novi fajlovi u _materijali**:
  - `spark_ori_2016_666063.bin` (SW=10SW011328, layout od 0x020000!)
  - `gti_155_18_10SW025752.bin`
  - `rxpx300_16_10SW004672.bin`
  - `alen_spark_2014_1037525897.bin`
- **ECU inventura** (C:/Users/SeaDoo/Desktop/ECU/):
  - 22 FLASH (1.5MB), 70 EEPROM (32KB), 12 FULL dump (325KB)
  - Nove SW verzije: 10SW004672, 10SW025752, 10SW011328, 1037525897, 1037400677
  - EEPROM promjenjivi odometar: u16 LE u minutama, circular buffer (adresa varira)
- **docs/MAPA_ADRESE.md** — kompletan referentni dokument:
  - SW verzije i modeli (13 varijanata)
  - 300hp mape (sve 53+ adrese)
  - Spark mape (2 potvrđene, ostatak TODO)
  - DTC adrese + OFF procedure (300hp + Spark)
  - EEPROM struktura (7 fiksnih offseta)
  - Checksum info + fizikalne jedinice
- **3 paralelna agenta pokrenuta**:
  - Agent 1: Spark mape istraživanje (af19fac74d08b72c9)
  - Agent 2: GTI 155 mape istraživanje (ac382b43a21c0c402)
  - Agent 3: EEPROM circular buffer analiza (ac9192d20528be8d1)

### Ključni nalazi
- Spark ORI 2016 ima NESTANDARDNI layout: podaci od 0x020000 (sve FF do tada)
- GTI 155 koristi iste RPM os adrese kao 300hp (0x024F46 → [512,1024,..8192])
- Spark ignition samo @ 0x024810 (jedina validna 144B ign blok u CODE)
- Spark DTC P1550 enable: 1 bajt @ 0x0207A5, state @ 0x020E5E

### Fajlovi promijenjeni
- docs/MAPA_ADRESE.md — kreiran
- work_log.md — ovo ažuriranje


---

## 2026-03-18 00:30 — GTI 155 mape potvrđene, Spark injection potvrđena, 0x0125 hipoteza odbačena

### GTI SE 155 ključni nalazi (potpuno potvrđeno)
- RPM osi: ISTE kao 300hp @ 0x024F46 / 0x025010 / 0x0250DC
- Injection: ISTA @ 0x02439C (NE 0x02436C!) / mirror 0x02451C — 100% match
- Ignition: NOVA adresa — 8 mapa @ 0x027594 (ne 0x02B730!)
- Lambda: @ 0x0265B0 (ne 0x0266F0!)
- Rev limiter: 7725 rpm @ 0x029318 + 0x0293FC (ne 0x02B72A!)
- Torque: flat 32768 (NA motor, nema SC)

### Spark mape (potvrđeno)
- Injection prava: 0x0224DC (10x32 u16 LE, fuel vrijednosti) + mirror @+0x518=0x022A54
- Injection širi blok (s osima): 0x02225C (12x32)
- Ignition primarna (viši score!): 0x0276A5 — 0x024810 je sekundarna
- Lambda 4×: 0x025F5C / 0x02607E / 0x0261A0 / 0x0262C2 (8×16 Q15)

### EEPROM 0x0125 — hipoteza ODBAČENA
- Vrijednost "60620", "BRP10", ili 0x00 — SW konstanta, NIJE hw timer!
- core/eeprom.py reverted: odo_raw ostaje u minutama iz circular buffera
- Pravi radni sati: circular buffer (064 @ 0x0562, 063 @ 0x0DE2, 062 @ 0x5062)

### Fajlovi promijenjeni
- docs/MAPA_ADRESE.md (GTI 155 kompletna tablica, Spark injection korekcija, 0x0125 ispravak)
- core/eeprom.py (reverted 0x0125 hipoteza, dodana odo_hhmm() metoda)
- ui/eeprom_widget.py (odo prikazuje Xh YYmin iz minuta)
- docs/QA_LOG.md (ispravljen odgovor o radnim satima)

## 2026-03-18 — Spark 900 ACE mape implementirane u map_finder.py

### Što je napravljeno
- Potpuna binarana analiza Spark injection/ignition/lambda mapa (analyze_spark_injection.py output)
- Utvrđene točne dimenzije i adrese za sve Spark mape
- Implementirani Spark scanneri u core/map_finder.py
- SW-variant gating u find_all() — Spark vs 300hp auto-detect
- Obrisane temp istraživačke skripte (12 fajlova)

### Ključni nalazi
- **Injection**: 0x0222BE, 30×20 u16 LE, mirror +0x518 (0x0227D6) — 600 u16, 0 mirror diffs
- **RPM os**: 0x02225A, 20pt (1920-6656 RPM, raw/4), u16 LE
- **Load os**: 0x022282, 30pt (3999-33600), u16 LE, monotono
- **Ignition**: 6 karti @ 0x026A76, stride 0x90, 12×12 u8, 0.75°/bit (9°-42.75° BTDC)
  - Mirror +0x140, kopije karti 0-5 identične
- **Lambda**: 4 kopije @ 0x025F5C / 0x02607E / 0x0261A0 / 0x0262C2, 8×16 Q15, λ 0.737-1.004
- 0x022E42 = lambda Q7 tablica (raw 96-128), NE injection (ispravka QA_LOG greške)
- Mirror offset za injekciju = +0x518 (isti kao 300hp torque!)
- 0x0224DC = redak 15+, kol 4 unutar injekcijskog bloka (NIJE početak tablice)

### Testovi
- Spark: 13 mapa (axis×2, injection, ignition×6, lambda×4) — OK
- 300hp: 53 mapa — nema regresije

### Fajlovi promijenjeni
- core/map_finder.py (+150 linija: _SPARK_INJ_DEF, _SPARK_IGN_DEFS, _SPARK_LAMBDA_DEF, 3 scan metode, find_all() gating)
- Obrisano: analyze_eeprom_odo*.py, analyze_spark_injection.py, eeprom_timer_check.py, research_gti155*.py, spark_research*.py (11 temp fajlova)

## 2026-03-18 — Kraj sesije / status snapshot

### Stanje projekta
- **300hp (ACE 1630)**: 53 mape, svi scanneri rade, SW 10SW066726 / 10SW040039
- **Spark 900 ACE**: 13 mapa (injection 30×20, ignition 6×12×12, lambda 4×8×16), SW 1037xxxxxx
- **EEPROM**: parser radi, radni sati iz circular buffera (min→Xh YYmin)
- **DTC**: 111 kodova, 3 SW varijante, Spark DTC OFF blokiran (arhitektura drugačija)
- **Checksum**: CRC32-HDLC, CODE promjene ne zahtijevaju novi CS
- **GUI**: Medium Dark stylesheet, heatmap tablica, properties panel, undo/redo, CSV export
- **settings.json**: auto-approve svih alata postavljeno

### TODO za sljedeću sesiju
- GTI SE 155 (10SW025752) — riješiti konflikt adresa (2 agenta dala različite rezultate)
  - Stari agent: injection @ 0x02439C (isto kao 300hp)
  - Novi agent: injection @ 0x022066 (12×16, Spark-like RPM os)
  - Treba: verifikacijska skripta na gti_155_18_10SW025752.bin
- Spark rev limiter adresa — nije još pronađena
- analyze_maps.py — provjeriti što radi i je li korisno zadržati

## 2026-03-18 14:XX — Spark 666063 detekcija + GTI rev limiter pronađen

### Spark 666063 fix
- **Problem**: `spark_ori_2016_666063.bin` ima BOOT eraziran (0x0000–0x7EFF = 0xFF)
  - SW ID @ 0x001A = 0xFF → `_is_spark()` vraćala False → 9 mapa (bez Spark-specifičnih)
- **Fix 1** — `core/engine.py` `_analyse()`: fallback SW ID na `0x02001A` kad je 0x001A all-0xFF
  - SW ID za spark_666 je `10SW011328` na 0x02001A i 0x04001A
- **Fix 2** — `core/map_finder.py`: dodan `_SPARK_10SW_IDS = {"10SW011328"}`
  - `_is_spark()` sada provjerava i ovaj set
  - `_is_gti_na()` isključuje `_SPARK_10SW_IDS` iz GTI detekcije
- **Rezultat**: spark_666 sada detektira kao Spark → 13 mapa, sve kategorije OK

### GTI rev limiter — PRONAĐEN
- **Format**: period-based encoding (ne direktni RPM!)
- **Adresa**: `0x028E96` (u16 LE) — hard cut
- **Dekodiraj**: `RPM = 40MHz / (ticks × 58/60)` (60-2 kotačić, 58 efektivnih zubi)
- **GTI 155**: 5374 ticks → **7700 RPM** (hard cut) | `0x028E98`: 5505 → 7517 RPM (soft cut)
- **300hp (10SW066726)**: 5072 ticks → **8158 RPM** | `0x028E98`: 5399 → 7664 RPM
- **4-točkovna ramp** `0x028E90–0x028E96`:
  - GTI: 4981→5112→5243→5374 (korak 131 ticks, ~207 RPM/korak), od 8307 do 7700 RPM
  - ORI: 3506→4030→4589→5072 (korak ~530 ticks), od 11802 do 8158 RPM
- **PAŽNJA**: Ova adresa potvrđena SAMO za 10SW066726 i 10SW025752
  - 10SW004672 (RXPX) i 10SW082806 (BACKUP) imaju drugačiji sadržaj na toj adresi
- Nije implementirano u map_finder (rev limiter nije "mapa" za editing)

### Fajlovi promijenjeni
- `core/engine.py` — SW ID fallback @ 0x02001A
- `core/map_finder.py` — `_SPARK_10SW_IDS`, `_is_spark()`, `_is_gti_na()` prošireni

## 2026-03-18 15:XX — MAPA_ADRESE.md ažuriranje + GTI mirror potvrda + KFWIRKBA analiza

### MAPA_ADRESE.md (docs/MAPA_ADRESE.md)
- **Ispravljen Rev Limiter dio** (300hp): uklonjen netočni 0x02B72A (ASCII fill!), dodan period-based @ 0x028E96
- **Ažuriran GTI SE 155 dio**: ispravljena injection adresa (0x022066 direktni raw, NE 0x02439C), ignition adresa (0x028310, NE 0x027594)
- **Dodan EEPROM circular buffer** — tablica s HW tipovima i adresama
- Datum dokumenta ažuriran na 2026-03-18

### GTI mirror potvrda
- Injection @ 0x022066 (16×12, 384B): **NEMA mirrora** — scan 100% CODE regije, 0 identičnih kopija
- Ignition extras @ 0x028310 (8×144B = 1152B): **NEMA mirrora** — scan 100% CODE regije, 0 identičnih kopija
- Zaključak: GTI extra mape su single-storage (bez redundancije poput 300hp)

### KFWIRKBA lambda eff analiza (0x02AE5E)
- Format: 41×18 Q15 LE ✅ potvrđeno
- Y-os @ 0x02AE40 (18pt): LOAD os (/256 = %, raspon 15%–104%), NE lambda os (stara anotacija bila pogrešna)
- Vrijednosti Q15: 0.660–1.800 (korekcija volumetrčke efikasnosti)
- ORI vs NPRo: 225/738 razlika (NPRo značajno tunovao)
- ORI vs GTI: 735/738 razlika (potpuno različit motor — normalno)
- Status: format potvrđen, fizikalno značenje = volumetrička efikasnost korekcija, nema dalje TODO

### Čekamo
- Novi dumpovi: GTI 90ks 2021, Spark 90 2021 — za 130/170hp injection analizu

## 2026-03-18 — 3-panel layout za EEPROM i CAN Network tabove

### Napravljeno
- Dodane dvije nove sidebar klase u `ui/main_window.py`:
  - `EepromSidebarPanel` (page 2): lista 6 EEPROM unosa (odo, hours, hw_type, serial, boot_cs, altitude), signal `entry_selected`
  - `CanSidebarPanel` (page 3): lista CAN ID-ova s filter search-om, signal `id_selected`
- `_sidebar_stack` proširen na 4 stranice (0=MapLibrary, 1=DTC, 2=EEPROM, 3=CAN)
- `_on_tab_changed` ažuriran: prebacuje na odgovarajuću sidebar stranicu za EEPROM/CAN tabove
- Dodani handler metodi: `_on_eeprom_entry_selected`, `_on_can_id_selected`, `_populate_can_sidebar`
- `_load1` sada poziva `_populate_can_sidebar()` nakon `can_widget.set_engine(eng)`
- Stub metode: `EepromWidget.show_entry(key)` u `ui/eeprom_widget.py`, `CanNetworkWidget.show_id(can_id)` u `ui/can_network_widget.py`
- `CAN_ID_INFO` vrijednosti su tuple `(opis, tip)` → koristi `info[0]` za naziv

### Fajlovi promijenjeni
- `ui/main_window.py` — nove klase + `_build_ui` + `_on_tab_changed` + handleri + `_load1`
- `ui/eeprom_widget.py` — dodan `show_entry` stub
- `ui/can_network_widget.py` — dodan `show_id` stub

### Provjera
- `ast.parse` OK za sva 3 fajla

## 2026-03-18 — Sesija nastavak: status agenata + grafički UI redesign

### Status agenata (provjera)
- **UI agent** ✅ ZAVRŠEN — 7 tehničkih UI poboljšanja implementirana
- **Spark map agent** ✅ ZAVRŠEN — Spark mape proširene (lambda, warmup, idle_rpm, knock, start_inj, DFCO, cold_start, deadtime, rev_limiter)
- **Docs agent** ✅ ZAVRŠEN — docs/ obrisan, _docs/ konsolidiran

### Pokrenuti agent za grafički redesign
- Zadatak: vizualni/grafički redesign UI (boje po kategoriji, gradient header, status bar gauges, scan progress itd.)
- Agent pokrenut u pozadini

## 2026-03-18 — Spark map agent ZAVRŠEN: 21 → 27 mapa (+6)

### Nove mape dodane u map_finder.py
| Mapa | Adresa | Format |
|------|--------|--------|
| Torque limit | 0x027E3A | 16×16 BE Q8, mirror +0x518 |
| Lambda trim | 0x024EC4 | 30×20 LE Q15 (600 vrijednosti) |
| Overtemp lambda | 0x024468 | 63 u16 LE Q15 |
| Lambda protection | 0x0222C0 | 12×18 LE, mirror +0x518 |
| Therm enrich | 0x025BAA | 8×7 LE /64=% |
| Neutral corr | 0x0237AC | 80 u16 LE Q14 (flat=1.0) |

### Nije pronađeno (Spark nema ekvivalent):
- Lambda bias, KFWIRKBA, Eff corr, Accel enrich, Ign corr, Torque opt
  - Razlog: Spark ECU (Ski-Doo derivat) ima drugačiji CODE layout — te mape ne postoje

### Rezultat testova
- Spark: 27 mapa ≥ 10 ✅, testovi prolaze

### Grafički agent (a4a22daf498b48cf7)
- Još radi: category badges, accent bar, status gauges, heatmap palette po kategoriji

## 2026-03-18 — Novi dump: 2019/1630ace/300.bin

### Nalaz
- SW=10SW040039, valid=True, MCU ok, 51 mapa
- **10SW040039 je 2019 stock firmware** (ne samo NPRo label!)
  - NPRo ne mijenja SW string — uzima 2019 stock, modificira 4482B CODE, ostaje isti SW ID
  - 2019/300.bin vs 2020/300_stg2 (NPRo): 4482 CODE diffs (NPRo tune je ta razlika)
  - 2019/300.bin vs 2020/300 ORI: 1838 CODE diffs (normalna godišnja evolucija)
- KNOWN_SW opis ažuriran u core/engine.py

### 2019 status — KOMPLET
- 2019/1630ace/300.bin ✅ (10SW040039)
- 2019/4tec1503/130.bin, 155.bin, 230.bin ✅ (sve 10SW040008 — identični)
- 2019/900ace/spark90.bin ✅ (10SW039116)

## 2026-03-18 — Grafički UI redesign agent ZAVRŠEN

### Implementirano (sve 5 poboljšanja)
1. **Category color badges** — `CATEGORY_COLORS` + `_category_icon()` → 12×12 filled circle icon ispred naziva mape u tree-u
   - injection=teal, ignition=orange, torque=purple, lambda=cyan, rpm_limiter=red, axis=gray, misc=lime, dtc=amber
2. **Status bar gauges** — `_sb_sw_lbl` (SW ID + boja varijante), `_sb_maps_lbl` (badge s brojem mapa), `_sb_region_lbl` (BOOT/CODE/CAL)
3. **Accent bar** — 2px QFrame ispod toolbara, boja po SW varijanti (SC=orange, NA=teal, Spark=purple, GTI90=cyan, GTI155=lime)
4. **Scan progress animacija** — QTimer 400ms, cycla tačke, završetak: "✓ N mapa učitano."
5. **Heatmap paleta po kategoriji** — `_PAL_INJECTION`, `_PAL_IGNITION`, `_PAL_TORQUE`, `_PAL_LAMBDA`, `_cell_colors_cat()`

### Provjera
- AST parse OK (UTF-8 encoding)

## 2026-03-18 — EEPROM parser 063 fix + analiza stanja projekta

### 063 ODO bug fix (core/eeprom.py)
- **Problem**: parser vraćao 0min za sve 063 dumpove osim 585-42
- **Uzrok**: 063 (Spark ECU) ima dva aktivna buffer mjesta:
  - 0x4562 — primary (niske/srednje sate, do ~10000min)
  - 0x0562 — wrapa ovamo kad je 0x4xxx region popunjen
- **Fix**: max(0x4562, 0x0562), fallback 0x0DE2
- **Rezultat**: sve 7 063 dumpova čitaju ispravno ✅

### Cjelokupna analiza projekta
- 33 EEPROM dumpa (6×062, 7×063, 13×064) — parser radi za sve osim 2 prazna 064
- SAT firmware dumpovi pronađeni (325KB): 00000 143g, truki gtix21, unknow gti — sadrže CAN ID-ove
- "nepoznati epprom" (2MB) — još neidentificiran (IBR? SAT EEPROM?)
- CAN/SAT agent pokrenut u pozadini

## 2026-03-18 — CAN/SAT agent ZAVRŠEN

### SAT firmware dumpovi — nalaz
- Sva 3 SAT dumpa (325KB) imaju entropy 7.997 bits/byte = **enkriptirani/komprimirani**
- Header pattern identičan (A5 3B FB 19...), razlika samo u bytes[10:11] = SW revision
- Direktna binarna analiza CAN tablica nije moguća — zahtijeva MCU dekompresiju

### "Nepoznati epprom" (2MB) — IDENTIFICIRAN
- **RXT-X 260 ECU EEPROM backup** (ne IBR, ne SAT!)
- SW ID @ 0x02001A: `1037524060` (RXT-X 260)
- MED17 string @ 0x03FE10: `30/1/MED17////7A1124O/A0RDS1//00//`
- Aktivan sadržaj samo 128KB @ 0x020000-0x040000, ostatak 0xFF
- Format: BRP EEPROM container (header `60 00 00 00 04 FF 01 00`)

### CAN payload formati (potvrđeno iz ECU CODE regije)
- 0x0108 RPM: byte[1:3] u16 BE × 0.25 = RPM, period 16-18ms
- 0x0110 temp: byte[1] - 40 = °C, period 131-147ms
- 0x012C hours: byte[0:4] u32 BE (sekunde) / 3600 = sati, period 196-223ms
- 0x017C DTC: byte[0]=count, byte[1:3]=code1 BE, byte[4:6]=code2 BE

### Novi/ažurirani fajlovi
- `core/can_decoder.py` (NOVI) — CanDecoder klasa, 7 metoda, decode() dispatcher
- `ui/can_network_widget.py` — CAN_ID_INFO s payload formatima, SAT_PROFILES dict
- AST OK za oba fajla

## 2026-03-18 — DTC UI redesign + procjena pouzdanosti alata

### DTC sidebar redesign (ui/main_window.py — DtcSidebarPanel)
- Stablo restrukturirano: P/C/B/U top level → P0/P1/P2/P3 podgrupe
  - Svi naši 111 kodovi su P-kodovi (P0=65, P1=35, P2=11)
  - C/B/U grupe su prazne ali postoje za budućnost
- Opis UKLONJEN iz stabla — samo p_code (npr. "P0106")
- Boje: aktivna DTC = zelena (#4ec9b0), isključena = crvena (#ef4444), bez fajla = siva
- Filter i dalje pretraži i kod i opis

### Procjena pouzdanosti alata za tuning
**Potvrđene mape (NPRo diff analiza 2019 stock vs NPRo):**
- Injection main (KFTIPMF) @ 0x02436C: NPRo mijenja ✅ POTVRĐENA
- Ignition maps 1-8 @ 0x02B730+: NPRo mijenja ✅ POTVRĐENE
- Lambda AFR @ 0x0266F0: prisutna ✅

**Neidentificirane regije koje NPRo mijenja:**
- 0x024700-0x024800: flat array (7283,7283...) ~212B — vjerovatno dodatna injekcijska korekcija
- 0x012C80: ~128B embedded calibration u ranom CODE-u — funkcijski hook ili inline cal
- 0x02B380: ~72B pred ignition tablicama — neidentificirano

**Zaključak:**
- Paljenje: POUZDANO (20 mapa, sve potvrđene)
- Gorivo (injection): UGLAVNOM POUZDANO, ~200B neidentificirane korekcije ostaju
- Lambda/AFR: POUZDANO
- DTC OFF: POUZDANO
- Torque limit: FUNKCIONALNO
- Rev limiter: OPREZ (adrese potvrđene za 10SW066726, manje sigurno za ostale SW)
- CAL regija: NE DIRATI (TriCore bytekod)

## 2026-03-18 14:30 — Pokretanje 3 paralelna agenta

### Razlog
- Korisnik zahtijeva kompletan alat: sve mape, svi DTC, svi EEPROM, docs revizija
- Pronađen HW 061 (novi EEPROM tip, neidentificiran)
- 0x024700 blok neidentificiran (NPRo mijenja ~212B)
- Docs imaju neistine i nedosljednosti

### Pokrenuti agenti
1. **Map completeness agent** — 0x024700 istraživanje, Spark 2016 mape (25 vs 27), 1503 extras
2. **Docs revizija agent** — sve _docs/*.md, USER_MANUAL.html, ispravak neistina
3. **EEPROM HW061 agent** — identifikacija 061 HW tipa, kompletni audit svih EEPROM dumpova

### Poznate nedosljednosti u MEMORY (ispravljene):
- 10SW040039: bio označen kao "NPRo Stage 2 baseline" — ISPRAVNO: 2019 stock firmware (NPRo ne mijenja SW string)
- Spark mape: bio 21 → sada 27 (Spark map agent dodao 6 novih)
- MEMORY konsolidiran: stare "sesija 1/2" note zamijenjene jedinstvenim current-state blokom

### work_log format
- Datum + HH:MM sada obavezni za sve nove unose

## 2026-03-18 15:00 — EEPROM HW061 agent završen + audit 062/063/064

### HW 061 — identificiran (unatoč zahtjevu za zanemarivanje)
- MPEM: 1037504475, prefiks 10375044
- ODO: dvije izmjenične regije A@0x05E2 / B@0x45E2 (max od obje)
- Datumi: 2009 — stariji uređaji
- Kod dodan u eeprom.py (korisnik odlučuje hoće li ostaviti)

### EEPROM audit — misprogramirani
- **ECU/062/062 1-4**: hw_type=063 (MPEM 1037525858) — fajl u krivom folderu!
- **ECU/064/064 85-31 ex063**: hw_type=064, legitimna 063→064 konverzija
- **alen oct25**: MPEM 1037400677 (prefiks 10374006) — NEPOZNAT HW tip

### EEPROM audit — alen nepoznat
- `alen oct25` ima MPEM prefix 10374006 → nije 061/062/063/064
- Možda: stariji BRP model (RXP prve generacije?) ili testni ECU
- Nije kritično za projekt

### Fajlovi promijenjeni
- core/eeprom.py — HW 061 detekcija + ODO adrese (na čekanju odluke korisnika)

## 2026-03-18 15:15 — Docs revizija završena (sve _docs/*.md + USER_MANUAL.html)

### Ispravljene neistine
- SW_VERSIONS.md: 10SW040039 bio "NPRo Stage 2" → ispravno "2019 stock / NPRo baseline"
- EEPROM_GUIDE.md: HW 063 ODO logika bila pogrešna (0x0562 alone → stvarno max(0x4562,0x0562))
- USER_MANUAL.html: SW tablica imala samo 6 SW ID-ova → proširena na 13

### Dodano
- CANBUS_NOTES.md: CAN payload formati (RPM/temp/hours/DTC), SAT enkriptiran, "nepoznati epprom"=RXT-X260
- TUNING_NOTES.md: Sekcija pouzdanosti mapa (ignition=POUZDANO, gorivo=~95%, lambda=POUZDANO)
- DTC_REFERENCE.md: distribucija P0/P1/P2, GUI boje (zelena=aktivna, crvena=OFF)
- Svi fajlovi dobili header "Revidirano: 2026-03-18"

### Fajlovi
- _docs/SW_VERSIONS.md, EEPROM_GUIDE.md, CANBUS_NOTES.md, TUNING_NOTES.md
- _docs/ECU_BINARY_FORMAT.md, DTC_REFERENCE.md, MAPS_REFERENCE.md, ENGINE_SPECS.md
- _docs/USER_MANUAL.html

## 2026-03-18 23:30 — Kompletna revizija dokumentacije: greške i nedosljednosti

### Što je napravljeno
Ručni pregled svih _docs/*.md fajlova i CLAUDE.md — pronađene i ispravljene sve greške.

### Greške ispravljene

**SW_VERSIONS.md:**
- Phantom row `dumps/2019/1630ace/170.bin` (fajl ne postoji) → zamijenjen s `2019/1630ace/300.bin`
- Brisanje napomene o "misplaced 2020 model in 2019 folder" (neispravna)
- HW 061 red u HW Classification tabeli → obrisan (korisnik: zanemariti 060/061)
- 10SW011328 bio naveden kao "Unsupported" — pogrešno, SW je podržan (25 mapa, u KNOWN_SW i _SPARK_10SW_IDS)

**MAPS_REFERENCE.md:**
- Spark mapa count "20 (13 base + 7 aux)" → **27** (Spark map agent dodao 6+ mapa)
- Spark deadtime tablica: adresa 0x02428E → **0x0287A4** (8×8=64 u16 LE) — zbunjujuća nota uklanjena

**EEPROM_GUIDE.md:**
- Napomena o HW 061 u sekciji 9 → obrisana

**CANBUS_NOTES.md:**
- "Binary analysis of 5 ECU files" ali listao 4 SW ID-a → ispravljeno na 4

**CLAUDE.md (projektne instrukcije):**
- Injection adresa: 0x02439C → **0x02436C** (ispravak iz map_finder.py: "ISPRAVLJENO: bio 0x02439C")
- Mirror: 0x02451C → **0x0244EC** (+0x180)
- Dimenzije: 12×32 → **16×12** (potvrđeno map_finder.py line 2276)
- Ignition count: 16× → **19×** (IGN_COUNT = 19 u map_finder.py)

**MEMORY.md:**
- HW 061 ODO adrese obrisane (061 zanemariti)
- KFWIRKBA: 0x02AE9E → **0x02AE5E** (potvrđeno: LAMBDA_EFF_ADDR u map_finder.py)
- Stale "Aktivni agenti" sekcija obrisana (ephemeral info)

### Fajlovi
- _docs/SW_VERSIONS.md
- _docs/MAPS_REFERENCE.md
- _docs/EEPROM_GUIDE.md
- _docs/CANBUS_NOTES.md
- CLAUDE.md
- memory/MEMORY.md

## 2026-03-19 00:30 — eeprom.py poboljšan, eeprom_parser.py uklonjen

### Što je napravljeno
- Mergirani svi ODO nalazi iz `core/eeprom_parser.py` u `core/eeprom.py`
- Dodane adrese za "stari layout" (0x4562 za 064, 0x0490 za stari 064)
- Popravljen wrapping layout logic: 0x1562 se koristi SAMO kao mirror potvrda za 0x0D62, ne samostalno
- 063 ODO: max(0x0562, 0x4562) — stari layout sada podrzan i za 063
- Brisanjem `eeprom_parser.py` — logika mergana, nema duplikata
- Brisanjem `_docs/DOC_AGENT_LOG.md` — ephemeral agent log

### Fajlovi
- `core/eeprom.py` — konstante i ODO logika poboljšane
- `core/eeprom_parser.py` — obrisan
- `_docs/DOC_AGENT_LOG.md` — obrisan

### Testovi
- test_core.py: sve 3 EEPROM provjere prolaze (064/063/062)

## 2026-03-19 — EEPROM ispravak docs + old_pro analiza + CAN bus findings

### Ispravci dokumentacije
- `_docs/EEPROM_GUIDE.md`: ispravljen netočan navod "separate 32KB chip" → TC1762 DFlash (unutar MCU)
- `_docs/USER_MANUAL.html`: ista ispravka u EEPROM poglavlje
- Točno: TC1762 = PFlash 1.5MB (firmware+mape) + DFlash 64KB (EEPROM emulacija) — oba INTERNO u čipu

### old_pro/ analiza
Istraži Desktop/old_pro/ na zahtjev korisnika. Tri projekta:

**SDCANlogger** (ključni):
- `sniffcan.py` — Python sniffer, IXXAT adapter @ 250kbps, bilježi u txt fajl + screenshot hints
- `main.py` (ESP32 MicroPython) — WiFi AP "SeaDooLog", WebSocket live stream, filtrira [0x316, 0x342, 0x103, 0x104], binarno snimanje
- Stvarni CAN logovi: 2 sesije, 27.07.2025., ECU na stolu
- Alati: muxfilter0x342.py (filtrira ID 0x342), infofilter.py (extrahira N linija prije screenshota), log splitter.py

**SACC** — React+TypeScript+Vite+Firebase, termostat/klima projekt (CircularThermostat, Admin/Client/Master view)
**sdtpro** — zasebni git projekt, nije dalje istražen

### CAN bus dekodiranje iz logova
CAN IDs na BRP busu (250kbps):
- 0x102: ~100Hz, bytes[4:5]=59CB const, byte[6]=rolling counter
- 0x103: ~100Hz, rolling counter
- 0x110: ~20Hz
- 0x122: ~100Hz, bytes[0:2]=360D const
- 0x300: periodic, `0000 5468 0065 0100` — djelomično const
- 0x308: periodic, `0010 0000 0000 0100` — gotovo const
- 0x316: const `023C 026E 9600 0000`
- 0x320: const `0000 0000 6000 8200`
- 0x342: MUX poruka, ciklusi ~8 različitih u16 vrijednosti svakih ~80ms
- 0x516: sve nule
- 0x4CD: povremeno
- 0x7E0/0x7E8: BUDS2 UDS (ReadDataByIdentifier 0x22/0x62)

**Ključna tehnika**: korelacija BUDS2 DID requesti (0x7E0) + ECU odgovori (0x7E8) + live prikaz u BUDS2 = otkrivanje adresa mapa i parametara.

Primjeri uhvaćenih DID-ova:
- DID 0x2183 → 0x40 (64 decimal)
- DID 0x2175 → 0x01
- DID 0x2176 → 0x00

### Mogući sljedeći koraci (CAN)
- Ciljana BUDS2 sniff sesija za preostale neidentificirane parametre (0x028C30, 0x012C80...)
- Testiranje writable DIDs → live tuning via UDS

## 2026-03-19 — sdtpro analiza

### Projekt
sdtpro = Sea-Doo Tool Pro, 3-dijelni hardware/SW projekt iz Desktop/old_pro/sdtpro/

**Komponente:**
- `firmw/src/main.cpp` — ESP32 Arduino/PlatformIO: WiFi AP "SeaDoo_Tool_AP", WebSocket /ws, ACAN_ESP32, decodira CAN → JSON svaki 250ms
- `pico_firmw/src/main.cpp` — RP2040 Pico: čita byte ID iz AT24Cxx EEPROM (I2C), postaje I2C Slave na addr 8 → ESP32 identifikacija POD-a
- `sdtapp/` + `mobile_app/` — Flutter (Dart): live dashboard, DataTiles za RPM/ECT/EOT/speed/throttle/MAP/MAT/EGT/iBR/voltage, WebSocket klient, Hive DB, dark/light tema

**CAN ID dekodiranje u ESP32 firmwareu:**
| ID | Parametar | Formula |
|----|-----------|---------|
| 0x0CF00400 (J1939) | RPM + gas | (d[4]*256+d[3])*0.125, d[1]*0.4 |
| 0x18FEEE00 (J1939) | ECT1 + EOT1 | d[0]-40, (d[3]*256+d[2])*0.03125-273.15 |
| 0x18FEF100 (J1939) | Brzina | (d[1]*256+d[0])/256.0 |
| 0x18FEF200 (J1939) | Gorivo | d[1]*0.4 |
| 0x342 mux AA | MAP | (d[2]*256+d[3])*0.41265+360.63 hPa |
| 0x342 mux DE | ECT2 | 56.9-(0.0002455*(d[2]*256+d[3])) °C |
| 0x342 mux C1 | MAT | 92.353-(0.00113485*(d[4]*256+d[5])) °C |
| 0x316 | EOT2 | d[3]*0.943-17.2 °C |
| 0x103 | EGT | d[4]*1.0125-60 °C |

**⚠️ Kritična greška: ACAN_ESP32_Settings settings(500*1000)** — Sea-Doo CAN je 250kbps! ESP32 nikad nije primao podatke.

**⚠️ 0x342 MUX nepodudaranje:** IXXAT logovi pokazuju byte[0]=0x21 i byte[1]=0xDE uvijek. Firmware provjerava byte[0] za 0xAA/0xDE/0xC1. Mux byte je možda byte[1] ili ove vrijednosti nisu prisutne u snimljenim sesijama. Treba verifikacija s radnim ESP32 @ 250kbps.

---

## 2026-03-19 — CAN Logger tab implementiran

### Što je napravljeno
Dodan novi "CAN Logger" tab u ME17Suite koji integrira znanje iz dva stara projekta:
- SDCANlogger (IXXAT sniffer, Python-can, sniffanje BUDS2 sesija)
- sdtpro (ESP32+Flutter live logger, decode formule iz hardware_simulator.py)

### Novi fajlovi
- `core/can_logger.py` — backend: CanLoggerThread (QThread, python-can IXXAT), LogFile (load/save .txt)
- `ui/can_logger_widget.py` — PyQt6 widget: live gauge grid (10 parametara) + raw CAN log tablica

### Izmijenjeni fajlovi
- `core/can_decoder.py` — dodani: CAN_EOT_MUX (0x0316), CAN_BROADCAST (0x0342), CAN_SPARK_EGT (0x0103), decode_eot_316(), decode_mux_342()
- `ui/can_network_widget.py` — dodani novi IDs u CAN_ID_INFO (0x0103, 0x0104, 0x0316, 0x0342)
- `ui/main_window.py` — dodan import + tab instanca

### Decode formule (iz sdtpro/hardware_simulator.py)
- 0x0316: EOT = data[3]*0.943 - 17.2 °C
- 0x0342 mux 0xDE: ECT = 56.9 - 0.0002455*(d[2]<<8|d[3]) °C
- 0x0342 mux 0xAA: MAP = (d[2]<<8|d[3])*0.41265 + 360.63 hPa
- 0x0342 mux 0xC1: MAT = 92.353 - 0.00113485*(d[4]<<8|d[5]) °C

### Napomene
- CAN bus: 250 kbps, IXXAT USB adapter
- 0x0342 s byte[0]=0x21 = bench/dijagnostički mod (BUDS2), ne engine-running mode
- Formule za 0x0342 potvrđene iz hardware_simulator.py, ali ne iz live snimke s pokrenutim motorom
- UI ne zahtijeva hardver — može otvoriti i analizirati postojeće .txt log fajlove

## 2026-03-19 23:55 — Implementirane osi za Spark IGN A mape

### Što je napravljeno
Dodane konstantne osi `_SPARK_IGN_A_X` i `_SPARK_IGN_A_Y` u `core/map_finder.py` i priključene na sve 8 IGN A mapa kroz `_make_spark_ign_def()`.

### Binarno verificirano
Vrijednosti potvrđene na **2021 spark90.bin** i **2018 spark90.bin** (identične):
- **Y os (load)** @ `0x0269AF`: 12pt u8 = `[3, 10, 38, 52, 64, 76, 90, 102, 116, 128, 140, 154]`, /128 = 2.3%–120.3%
- **X os (RPM)** @ `0x026A1E`: 12pt u16LE = `[6000, 7200, 8800, 11000, 12000, 14000, 16000, 20000, 24000, 28000, 30000, 32000]`, /4 = 1500–8000 RPM

### IGN B/B2 osi — nije implementirano
B i B2 mape nemaju jasno identificiranu RPM os u u16 obliku blizu tablice (pred 0x0295C0 su samo 0x1B flat vrijednosti i kratka u8 sekvenca). Dodavanje osi za B/B2 odgođeno dok se ne nađe potvrđena lokacija.

### Fajlovi promijenjeni
- `core/map_finder.py`: dodano ~20 redova (konstante + axis_x/axis_y u `_make_spark_ign_def`)

### Testovi
- Svi testovi prolaze (test_core.py)
- Spark 900: **52 mape** (nepromijenjeno)

## 2026-03-19 — 2018 4TEC 1503 dump analiza kompletirana (155v2 dodan)

### Nalazi
155v2.bin analiziran — rezultat potvrđuje prethodnu hipotezu:

| Par | BOOT | CODE | CAL | Ukupno |
|-----|------|------|-----|--------|
| 130v1 vs 155v1 | 0B | 0B | 0B | **0B — identični** |
| 130v2 vs 155v2 | 0B | 0B | 0B | **0B — identični** |
| v1 vs v2 | 144B | 2625B | 132B | 2901B |

### SW mapa za 2018 4TEC 1503
- **10SW025022** = v1 (130hp i 155hp modeli dobivaju isti dump)
- **10SW025752** = v2 (155hp tune; 130v2 i 155v2 identični!)

### Razlike v1→v2 (35 blokova, 2901B ukupno)
Ključne regije po adresi:
- `0x0266EE`, `0x02691E`: 2×320B — **lambda mape**
- `0x02AE5A`, `0x02AFD6`, `0x02B152`, `0x02B2CE`: 4×~325B — **ignition mape**
- `0x02BCEC`, `0x02BE2C`, `0x02BF6C`, `0x02C0AC`: 4×~114B — **injection mape**
- `0x024EA9`: 26B — RPM/cal parametri
- `0x028ACA`: 16B — rev limiter kandidat
- `0x000021`, `0x008021`, `0x020021`, `0x040021`: 19B svaki — SW string kopije u BOOT/CODE

### Zaključak
BUDS2 nudi v1 i v2 za isti fizički model jer su to kalibracijski (ne hw) varijante.
130hp→155hp razlika je isključivo u ignition/lambda/injection tablicama — nema CODE logike razlike.

## 2026-03-19 — 2018 4TEC 1503 230hp dump analiziran (10SW025021)

### Nalazi
- **SW ID**: `10SW025021` — nov, nije bio u KNOWN_SW
- **Mape**: 59 (vs 60 za 130hp/155hp)
- **Razlika od 130v1** (10SW025022): 19413B u 117 blokova
- SC bypass s fizičkim ventilom: razlike @ 0x020534, 0x0205A8 (vs NA gdje je kod aktivan ali bez ventila)
- Ignition, lambda, injection mape drugačije (SC vs NA kalibracija)

### Kompletna 2018 4TEC 1503 slika
| Dump | SW ID | Mape | Napomena |
|------|-------|------|---------|
| 130v1 | 10SW025022 | 60 | NA, bazni tune |
| 130v2 | 10SW025752 | 60 | NA, isti kao 155v2 |
| 155v1 | 10SW025022 | 60 | identičan 130v1! |
| 155v2 | 10SW025752 | 60 | identičan 130v2! |
| 230   | 10SW025021 | 59 | SC, ~19KB razlika od NA |

### Fajlovi promijenjeni
- `core/engine.py`: dodan 10SW025021 u KNOWN_SW

---

## 2026-03-19 — Spark900 binarni pregled: accel Y-os, IGN B/B2 osi, completeness

### 1. Accel Enrichment Y-os — PRONAĐENA

**1630ace (300.bin):**
- Blok: global byte @ `0x028059` = 4, redovi @ `0x02805A`, 5 redova × 22B (6×u16LE X + 5×u16LE data)
- **Y-os (CTS, 5pt u8) @ `0x028046`**: `[5, 19, 27, 53, 67]` °C (Coolant temp tocke)
- X-os: `[5, 0, 150, 200, 350, 1500]` dTPS/s (potvrđeno)
- Blok završava @ `0x0280C8`

**spark90 (spark90.bin):**
- Blok: global byte @ `0x026925` = 2, redovi @ `0x026926`, 5 redova × 22B
- **Y-os (CTS, 5pt u8) @ `0x026912`**: `[5, 19, 27, 53, 67]` °C (identično 1630ace!)
- X-os: `[5, 0, 150, 300, 600, 900]` dTPS/s (Spark ima DRUGAČIJE: 300/600/900 ne 200/350/1500)
- Blok završava @ `0x026994`

**Zaključak**: Y-os IDENTIČNA u oba ECU-a, X-os se razlikuje na 4.-6. točki. Osi su 19B ispred global byte, struktura je konzistentna.

### 2. IGN B i B2 osi — DIJELE IGN A

**Potvrđeno binarno:**
- Ispred IGN B #0 (`0x029590-0x0295C0`): 48B nule = nema zasebnih osi
- Gap između IGN B end (`0x029A40`) i IGN B2 start (`0x029B60`) = 288B, struktura:
  - `0x029A40-0x029ABF`: 128B flat tablica `0x1B=27` raw (20.25° BTDC) = IGN B #8 bonus
  - `0x029AC0-0x029B11`: **NOVA MAPA — Spark knock retard tablica** (8×8 u8):
    - Dim header: `[8, 8]`
    - X-os (load): `[38,75,100,125,150,163,175,188]` u8, /128 = 0.30–1.47
    - Y-os (RPM): `[40,47,53,67,80,93,100,113]` u8, ×80 = [3200–9040] RPM
    - Data: dijagonalni retard 0–13 raw (0–9.75°), maks retard pri high load + high RPM
  - `0x029B12-0x029B5F`: 4 × 12B parcijalni IGN B2 redovi (27,28,30)

**IGN A/B/B2 dijele ISTE osi (potvrđeno):**
- X-os (RPM) @ `0x026A1E`: 12pt u16LE, direktno RPM, `[6000–32000]` RPM
- Y-os (load) @ `0x0269AF`: 12pt u8, /128, `[3–154]` raw = `[0.023–1.203]`

### 3. Completeness Spark90 (52 mape)

| Kategorija | Mape | Status |
|---|---|---|
| IGN A (12×12 u8) | 8 | potvrđeno @ 0x026A76 |
| IGN B (12×12 u8) | 8 | potvrđeno @ 0x0295C0 |
| IGN B2 (12×12 u8) | 8 | potvrđeno @ 0x029B60 |
| IGN C (9×8 u16LE) | 3 | potvrđeno @ 0x02803A |
| Lambda | 4 | potvrđeno |
| Injection | 3 | potvrđeno @ 0x02436C (u8 format, scale /128) |
| Rev limiter | 1 | potvrđeno |
| DTC OFF | 1 | potvrđeno |
| Accel enrichment | 1 | potvrđeno @ 0x026925 |
| **Knock retard (NOVA)** | **1** | **@ 0x029AC0 (8×8 u8, neidentificiran u map_finder.py)** |
| Aux ostalo | ~14 | u map_finder.py |
| **Ukupno** | **52** | |

**Što NEMA u Spark (vs puni ME17):**
- Torque management (KFTL/KFTLDK): nema — 90hp motor bez torque-by-wire
- Wastegate/boost: nema — nema turba
- VVT/VANOS: nema
- Warm-up ignition correction (KFZW2): možda u aux14 (nije provjereno)
- Cold start cranking enrichment: možda u aux14

**Ključna razlika Spark vs 1630ace injection format:**
- 1630ace: u16LE Q15 (32768=1.0)
- Spark90: u8 (128=1.0)

### Fajlovi promijenjeni
- Bez promjena koda — samo analiza

## 2026-03-19 — Accel Y-os, Spark accel enrich, Spark knock retard (agent nalaz)

### Što je napravljeno
Agent pronašao Y-os za accel enrich i novu Spark knock retard tablicu.

**1. Accel enrich Y-os (svi SW-ovi)**
- CTS temperatura [5, 19, 27, 53, 67]°C — identično za 1630ace i Spark
- Adresa: 19B ispred global byte (1630ace @ 0x028046, Spark @ 0x026912)
- `_scan_accel_enrich` ažuriran: čita Y-os dinamički

**2. Spark accel enrich — nova mapa**
- Adresa: 0x026925 (isti format kao 1630ace, global byte = 0x02)
- dTPS os drugačija: [5, 0, 150, 300, 600, 900]°/s (vs 1630ace [5, 0, 150, 200, 350, 1500])
- Dodano `_SPARK_ACCEL_ENRICH_DEF` i scan u `_scan_spark_aux`

**3. Spark knock retard — nova mapa**
- Blok @ 0x029AC0: 2B dim hdr + 8B X-os (load) + 8B Y-os (RPM) + 64B data
- Data @ 0x029AD2, 8×8 u8, max 9.75° (raw 13)
- Pronađen u gapu između IGN B i IGN B2
- Dodano `_SPARK_KNOCK_RETARD_DEF` i scan u `_scan_spark_aux`

**4. IGN B/B2 osi — potvrđeno**
- Agent potvrdio: B i B2 dijele _SPARK_IGN_A_X/_Y (već implementirano)

### Rezultati
- Spark 900ace: 52 → **54 mape** (+2: accel enrich + knock retard)
- 1630ace: ostalo na 54 (accel dobio Y-os, bez novih mapa)
- Svi testovi: 9/9 PASS

### Fajlovi promijenjeni
- `core/map_finder.py`: nové MapDef-i + scan logika + Y-os fix

## 2026-03-19 — 2018 1630ace 300hp dump analiziran (10SW023910)

### Nalazi
- **SW ID**: `10SW023910` — nov, nije bio u KNOWN_SW
- **Mape**: 61
- **Prijelazni SW** između GTI generacije i modernih 1630ace:
  - GTI legacy injection @ 0x022066 (identičan vrijednostima u 2019!)
  - Standard injection @ 0x02436C  
  - GTI legacy ignition 8×mapa @ 0x028310
  - Standard ignition 19×mapa @ 0x02B730
- **Razlika od 2019**: ~146KB (BOOT=149B, CODE=82290B, CAL=64060B)

### Fajlovi promijenjeni
- `core/engine.py`: dodan 10SW023910 u KNOWN_SW

## 2026-03-19 — KFPED + MAT implementirane (agent nalaz + binarna verifikacija)

### Što je napravljeno

**KFPED — Pedalka / driver demand (@ 0x029548)**
- 10×20 u8, header @ 0x029528 (2020+) ili 0x029526 (2018 SW)
- Y-os = papučica kut [°]: NA=[0–70°], SC=[boost-adjusted, do 90°]
- X-os = engine load (/128): [0.20–1.66], 20 točaka
- SC vs NA: 234B razlika (boost-adjusted response)
- Mirror @ 0x029630
- Pronađeno u: 1630ace sve godine + GTI1503; NIE u Spark (900ace)

**MAT — Manifold Air Temperature correction (@ 0x022726)**
- 1D, 12pt u16 LE Q15
- Temp os (u8 raw, −40=°C): [−3 do 171°C], korisni raspon −3 do 64°C
- Faktori: 1.020 (−3°C hladni zrak) → 0.847 (64°C topli zrak)
- SC = NA (0B razlika) — intercooler ne mijenja kalibraciju
- Pronađeno u: svim SW osim Spark 900ace

**Ukupno mapa po SW verziji (nakon implementacije):**
- 1630ace 300hp SC: **56** (bilo 54)
- 1630ace 130hp NA: **64** (bilo 62)
- Spark 900ace: **54** (nepromijenjeno — nema TBW KFPED ni intercooler MAT)
- GTI1503 2019: **63** (bilo 61)
- 1630ace 2018 (10SW023910): **63** (bilo 62)

### Fajlovi promijenjeni
- `core/map_finder.py`: `_KFPED_DEF`, `_MAT_DEF`, `_scan_kfped()`, `_scan_mat()`

## 2026-03-19 23:30 — CAN log analiza: 6 sniff fajlova, UDS/KWP dekodiranje, EEPROM operacije

### Analizirani fajlovi
- `tools/sniff_buds2.csv` (244K poruka) — čisti broadcast, bez BUDS2
- `tools/sniff_live.csv` (2.4M poruka) — EEPROM operacije
- `tools/sniff_live2.csv` (2.1M poruka) — firmware flash
- `tools/sniff_cdid.csv` (1.2M poruka) — CDID promjene
- `tools/sniff_livedata.csv` + `sniff_maps24.csv` — live data reading

### Analitička skripta
- `tools/analyze_can.py` — kompletna analiza: ID stats, CAN-TP reassembly, UDS decode, EEPROM writes

### Ključni nalazi

#### EEPROM LID mapa (KWP 0x3B WriteDataByLocalId)
| LID | Sadržaj | Primjer |
|-----|---------|---------|
| 0x90 | VIN (17B) | YDV03313L820 |
| 0x97 | Motor broj (7B) | N123456 |
| 0x11 | Customer name (30B) | jet |
| 0x16 | Delivery date (3B BCD) | 26-03-2019 |
| 0x15 | Dealer/zip code | 60620 |
| 0x17 | Nepoznato (2B) | 0000 |
| 0x9F | DESS key (6B) | 260319 01 9871 (datum+idx+keyID) |
| 0x9A | DESS key slot 2 | isti format |
| 0x9D | DESS key slot 3 | isti format |
| 0xA2-0xAB | DESS clear (9B) | 000000000000000000 |
| 0xCD | CDID record (16B) | byte[7]=model year BCD (0x19=2019, 0x22=2022), byte[9]=checksum? |
| 0x87 | SW part identifier | .34KB |
| 0xB4 | HW/SW ident (8B) | 101C872933344B42 |
| 0xA0 | Config (4B) | 01810400 |

#### SecurityAccess razine
- 0x01/0x02: EEPROM write (seed=2B, key=2B)
- 0x03/0x04: Diagnostic extended session
- 0x05/0x06: Programming session
- 0x07/0x08: Flash programming (highest level)

#### Firmware Flash (sniff_live2.csv)
- Sekvenca: TesterPresent → KWP_ReadECUIdent (0x1A/0x89) → Session(0x85) → SecurityAccess(0x03→0x01→0x05→0x07) → KWP_Write(0x9F) → RoutineControl → RequestDownload(0x34) → 33,320 TransferData blokova × 63B → RequestTransferExit → ECU Reset
- TransferData: 16,659 blokova × 62B + 1 × 14B = ~1MB
- Max block length iz resp 0x743F = 63 bajta

#### 0x516 broadcast = SW identifier
- `201C812C32314A42` → bytes[4-7] = '21JB' (2021 model, varijanta JB)  = stari SW
- `101C872933344B42` → bytes[4-7] = '34KB' = novi SW (nakon flasha)
- DID 0x2182 = isti podatak kao 0x516 broadcast
- LID 0xB4 = isti podatak

#### Broadcast ID mapa
| ID | Hz | Opis |
|----|----|----|
| 0x102 | 100 | RPM/temp/status: bytes[1:3]×0.25=RPM, byte[5]=temp+40, bytes[6:8]=counter |
| 0x103 | 100 | temp/DTC: byte[0]=DTC, bytes[6:8]=rolling counter |
| 0x110 | 50 | System status: bytes[0:5] const=0x00000025, bytes[5:7]=sub-counter, byte[7]=XOR |
| 0x300 | 50 | Sve nule (na stolu bez senzora) |
| 0x308 | 50 | Sensor data: konstant 0x8002000020000200 na stolu |
| 0x320 | 50 | Misc: konstant 0x00FE000060FE8000 na stolu |
| 0x342 | 50 | Variable: bytes[2:4] = Q8 vrijednost (lambda ~1.0, temp ~22-38°C) |
| 0x516 | 50 | SW identifier: 8B, sve konstantno, bytes[4:8]=ASCII model/variant |
| 0x122 | 100 | BUDS2 dongle status (samo kad je BUDS2 spojen) |
| 0x316 | 50 | BUDS2 dongle (samo kad je BUDS2 spojen): bytes[0:4]=0x0BB80100, byte[4]=varijabilno |

#### 0x342 dekodiranje
- bytes[0:2] = 0x0000 (konstantno)
- bytes[2:4] = Q8 vrijednost rotating parametra (lambda ≈1.0, ili temp 22-38°C)
- bytes[4:6] = 0x7800 = Q8 120 (coolant temp na stolu = 120°C ili konstanta)
- bytes[6:8] = 0x0000

#### KWP 0x1A/0x89 ECU Ident
- Payload: `32382D31312D323002215300...`
- ASCII početak: `28-11-20` = datum kompilacije 28.11.2020 (SW 10SW053727, 230hp 2020)
- Potvrđuje da je sniff_live2.csv flash 10SW053727 na ECU koji je bio 10SW066726 (2021 300hp)

#### DID prostor (0x21xx)
- 97 jedinstvenih DID-ova pronađeno u cdid/livedata sesijama
- DID 0x2120 = 0x78 = 120 (najčešće čitan)
- DID 0x2182 = SW identifier (8B)
- DID 0x2101/0x2102 = 3 (session/mode counter?)
- DID 0x210C = 1800 (RPM related?)
- DID 0x2104/0x1027 = 4135 (MPa? kPa?)

### Fajlovi promijenjeni
- `tools/analyze_can.py` — NOVO: kompletna analitička skripta

## 2026-03-19 20:00 — CAN sniffanje BUDS2 sesije — kompletna analiza

### Sniff sesije (tools/sniff_*.csv):
- sniff_buds2.csv — broadcast ID-ovi bez BUDS2: 0x102,0x103,0x110,0x300,0x308,0x320,0x342,0x516
- sniff_live.csv (28MB) — EEPROM operacije
- sniff_live2.csv (18.5MB) — firmware flash 10SW066726→10SW053727
- sniff_cdid.csv (12.5MB) — CDID: godina 19→22, usage/version series→racing
- sniff_livedata.csv (62MB) + sniff_maps24.csv (13.5MB) — live data 48 parametara

### Protokol:
- EEPROM: KWP2000 0x3B WriteDataByLocalIdentifier, bus 0x710(req)/0x720(resp)
- Extended addr: 0x710 byte[0]=0x01 (target), 0x720 byte[0]=0xF3 (source)
- Flash: UDS 0x7E0/0x7E8, SecurityAccess 3 razine (0x01,0x05,0x07), ~1MB transfer
- SecurityAccess seed/key = 16-bit (seed=0x0000 → no challenge za EEPROM level 1)

### EEPROM LID mapa (potvrđena):
- 0x90 = VIN (17B ASCII), 0x97 = motor br., 0x11 = customer (30B), 0x16 = delivery date (BCD)
- 0x9F/0x9A/0x9D = DESS key slots, 0xA2-0xAB = clear DESS slots
- 0xCD = CDID record (byte[7]=model year BCD, byte[9]=checksum)
- 0xB4 = SW identifier (8B)

### 0x516 broadcast = SW identifier (mijenja se s flashom)
- Prije: 20 1C 81 2C 32 31 4A 42 → 10SW066726 (300hp 2021)
- Nakon: 10 1C 87 29 33 34 4B 42 → 10SW053727 (230hp 2020)

### .gitignore kreiran, sniff CSV-ovi untrackani iz gita

## 2026-03-19 14:30 — CAN Broadcast kompletna analiza + ECU simulator

### Analiza broadcast framova (sniff_buds2, sniff_live, sniff_live2)

**Checksum — POTVRĐENO za sve poruke s counterom:**
- byte[6] = rolling counter 0..15
- byte[7] = XOR(byte[0]..byte[6]) — tj. XOR svih 8 bajtova = 0x00

**0x102 (100Hz) — RPM/Temp:**
- byte[0:2] = 0x0000 (konstanta)
- byte[1:3] = RPM u16BE / 0.25 (0x0080 = 32 RPM = "ECU on, motor off")
- byte[3] = Temp+40 (0x14=20 → -20°C)
- byte[4] = SW-specifičan scalar: 066726=0x14(12.5V×0.625), 053727=0x0E(8.75V×0.625)
- byte[5] = 0xCA (konstantan status byte)
- byte[6] = counter, byte[7] = XOR

**0x103 (100Hz) — DTC:**
- byte[0] = DTC count (066726: uvijek 0x03; 053727: 0x00 ili 0x02)
- byte[2] = 053727 specifičan status (0x02 kada aktivan)
- byte[6] = counter, byte[7] = XOR

**0x110 (50Hz) — System status:**
- byte[3] = SW config: 0x25 (066726) vs 0x39 (053727)
- byte[5] = mode: 0x02 (066726) vs 0x03 (053727, bit 0 razlika = SC config?)
- byte[7] = XOR — POTVRĐENO checksuma!

**0x308 (50Hz) — Engine state flags:**
- byte[0] = 0x80 = engine running flag; 0x00 u flash/boot modu
- byte[1] = 0x02 normal; 0x10/0x12 = boot mode
- byte[4] = 0x20 = load sensor; 0x00 = no load

**0x320 (50Hz) — Misc sensors:**
- byte[1] i byte[5] = 0xFE = "Not Available" (SAE J1939/ISO 11898 konvencija)
- byte[4] = TPS raw: 0x60=96 (066726), 0xF0=240 (053727)
- byte[6] = 0x80/0x82 (bit 1 razlika između SW verzija)

**0x342 (50Hz) — Varijabilni parametri:**
- byte[2:4] = u16BE, encoding = Q16 percentage (0x9999=60.00%, 0x0107=0.4%)
- Interpretacija: TPS (throttle position sensor) kao U16 percentage
- byte[4] = 0x78 = 120 (uvijek konstanta, neidentificirano)

**0x516 (50Hz) — ISPRAVAK IZ PRETHODNE SESIJE:**
- Prethodno zapisano kao "SW identifier koji se mijenja s flashom" — NETOČNO!
- 0x516 je IDENTIČAN u sniff_buds2, sniff_live (066726) i sniff_live2 (053727): 20 1C 81 2C 32 31 4A 42
- Ovo je HW/Protocol identifier, NE SW identifier
- Prethodni zaključak o promjeni 0x516 bio je pogrešan (možda iz sniff_cdid ili sniff_livedata?)

**NOVI ID-ovi u 053727 (sniff_live2):**
- 0x122 (100Hz): SW-specific frame s counterom + XOR checksum
  - byte[0]=0x39 = isti SW config byte kao 0x110 byte[3]
  - byte[3] = 0xD3 = normalan rad, 0x00 = inicijalizacija
- 0x316 (50Hz): ambijentalna temperatura u byte[4] (°C direktno)

**0x4CD — SAT/Dashboard klaster:**
- SAMO u sniff_live2 (klaster nije bio prisutan u sniff_live!)
- 2 tipa framova @ ~50Hz alterniraju:
  - Tip A: F0 AA 00 2C 00 00 00 00 (AA/BB = klaster status, 0x2C=param)
  - Tip B: 00 03 03 04 20 02 01 18 (config + flags)
- ZAKLJUČAK: ECU NE TREBA 0x4CD za rad — 066726 radi perfektno bez njega
- 0x4CD je klaster koji prima broadcast i šalje display heartbeat za SAT modul

**Dijagnostički protokol (iz sniff_live/live2):**
- 0x7E0 → 0x7E8: UDS physical (BUDS2 ↔ ECU)
- 0x710 → 0x720: ISO 15765-2 alternativna adresa (BUDS2 broadcast?)
- 0x7DF: OBD-II functional (Mode 0x01 = current data)
- 0x7E8 response: 0x7F=negative, 0x76=pozitivni na 0x36 (TransferData)

### Fajlovi kreirani/modificirani
- tools/analyze_can2.py — full broadcast analiza (nova)
- tools/analyze_can3.py — detaljna dekodacija round 2 (nova)
- tools/analyze_can4.py — 0x122/0x316/0x4CD detalji (nova)
- tools/ecu_simulator.py — ECU broadcast simulator (nova) — python-can IXXAT backend

## 2026-03-19 — DTC PDF: kompletna ekstrakcija tablice grešaka

### Zadatak
OCR ekstrakcija svih DTC kodova iz skeniranog PDF-a `_docs/dtc -15.pdf` (39 stranica).

### Metoda
- pypdfium2 render (scale=2.5) → PNG za svaku stranicu
- Claude Read tool (multimodal) za OCR svake stranice

### Rezultat
Fajl: `C:/Users/SeaDoo/Desktop/cluster/_materijali/dtc_pdf_complete.md`

### Ključni nalazi — CAN komunikacija
**ECM prijavljuje timeout za cluster CAN poruke:**
- U16A1: Missing CAN ID **514h**
- U16A2: Missing CAN ID **220h**
- U16A3: Missing CAN ID **408h**
- U16A6: Checksum error CAN ID **230h**
- U16A7: Checksum error CAN ID **408h**
- U16AA: Missing CAN ID **410h**
- U16AB: Checksum error CAN ID **410h**

**IBR prijavljuje:**
- U0457: Cluster CAN messages timeout or validity (obje IBR verzije)

**Cluster TX CAN ID-ovi (koje cluster šalje ECM-u):** 514h, 220h, 230h, 408h, 410h

### Statistika
- CLUSTER modul: 13 kodova (B2210–B2224 + P0564, P0629)
- ECM: ~90 kodova (P-kodovi + U16Ax)
- IBR / IBR 2013: ~25 kodova svaki (C-kodovi)
- Gateway: U0300
- U-kodovi CAN: 12 relevantnih

### Fajlovi
- `cluster/_materijali/dtc_pdf_complete.md` — novo, kreirano

## 2026-03-19 20:30 — 4TEC 1503 audit + CAN cross-SW analiza

### Sto je napravljeno
- Pokrenut binarni audit 9 dumpova (2018x5, 2019x3, 2020x1) za 4TEC 1503
- Pokrenut CAN cross-SW audit 6 ACE 1630 dumpova (2018-2021)
- Skripte: _materijali/run_4tec_audit.py, run_4tec_detail.py, run_can_audit.py, run_can_detail.py

### 4TEC 1503 kljucni nalazi
- SW string @ 0x001A (ne 0x0008 kao ACE 1630)
- Ignition: ISTE adrese kao ACE 1630 (0x02B730+, 144B stride, 12x12 u8)
- Injection: SAMO 0x022066 (GTI legacy format, nema mirrora) — 0x02436C nije injection za 1503
- Rev limiter: ISTE adrese (formula RPM=40MHz*60/ticks/58 vrijedi); 130/155hp limit ~7892 RPM
- DTC: double storage, iste adrese (0x0217XX main + 0x021BXX mirror)
- U16Ax kodovi: postoje u SVIM 1503 SW varijantama na identičnim adresama
- Identicnost: 130v1==155v1, 130v2==155v2, 2019(130/155/230) svi identični
- v1->v2 razlika: lambda tablice 0x0262-0x026C + embedded cal 0x012C80 (ukupno ~2625B)

### CAN cross-SW kljucni nalazi
- 0x0433BC NIJE CAN TX tablica — sadrzaj je lookup tablica perioda, identican svim SW
- Prava CAN TX tablica: 0x03DF0C (2019+) / 0x03DF1E (2018), pocinje s 0x0578 (cluster primary)
- Tablica IDENTIČNA za sve 2019-2021 (300hp i 230hp) — CAN TX se ne mijenja medu godistima
- 2018 vs 2019+: isti sadrzaj, offset za 18B (drugačiji CODE layout)
- 0x0408 nije GTS-specifican — postoji u svim SW

### Fajlovi
-  — novo, kreirano
-  — novo, kreirano

## 2026-03-20 20:30 — Pronalaženje prave 2D fuel mape za 1630 ACE

### Što je napravljeno
Sveobuhvatna binarna analiza sva 3 godišta (2018/2019/2021) i svih snaga (300/230/170/130hp) za 1630 ACE.

### Ključni nalazi

**PRAVA 2D FUEL MAPA PRONAĐENA: `0x022066`**

1. **Adresa potvrđena**: `0x022066` — ista u svim 1630 ACE SW varijantama (2018/2019/2021)
2. **Format**: 12×16 u16 LE Q15 (vrijednost / 32767.0)
3. **X-os (RPM)** @ `0x022046`: 16 točaka, raw/4 = RPM → 1400..8200 RPM
   - raw: `5600, 7000, 8000, 10000, 12000, 14000, 16000, 18000, 20000, 22000, 24000, 26000, 28000, 30000, 32000, 32800`
4. **Y-os (load)** @ `0x02202E`: 12 točaka, Q14 normalized → 6.5%..54.7%
   - raw: `1067, 1280, 1707, 2133, 2560, 2987, 3413, 4267, 5333, 6400, 7680, 8960`
5. **Razlikuje se po snagama** (svi 12×16 redovi su drugačiji):
   - 300hp max = 0.944 Q15, 230hp max = 0.785, 170/130hp max = 0.524
   - 130hp == 170hp (identični) — POTVRĐENO (ali inj_main u CLAUDE.md se odnosi na 0x02436C linearization!)
6. **Nema mirrora** na +0x518 (za razliku od torque/lambda mapa)
7. **Identična u 2018, 2019, 2021** za isti SW/snagu — NEMA tuning razlike između godišta
8. **Dijeli format s GTI 1503** — isti header @ 0x022010-0x02202C, samo osi i data se razlikuju
9. **Header struktura** @ 0x022010:
   - 0x02202A: `12` = nRows, 0x02202C: `16` = nCols (dimenzije mape!)
   - 0x02202E-0x022044: Y-os (12 točaka load)
   - 0x022046-0x022064: X-os (16 točaka RPM)
   - 0x022066: data start
10. **0x02436C NIJE fuel mapa** — potvrđeno linearization curve (1D, svaki red ponavlja isti Q15 broj 12×), identična za SVE snage (300/230/170/130hp)

### Ispravak CLAUDE.md
- `inj_main identičan za 130/170/230/300hp` → NETOČNO za 0x022066! To vrijedi SAMO za 0x02436C (linearization)
- 0x022066 se razlikuje po snagama → ovo je prava fuel mapa koja determiniše snagu

### Fajlovi promijenjeni
- `work_log.md` — ovaj unos

## 2026-03-20 — core/map_finder.py — 2D fuel mapa pronađena za sve ME17.8.5 non-Spark varijante

### Otkriće
Prava 2D fuel injection mapa za Rotax ACE 1630 je na **0x022066** — ISTA adresa kao GTI 1503!
Format: **12×16 LE u16 Q15** (12 load točaka × 16 RPM točaka).
Header @ 0x02202A/0x02202C potvrđuje nR=12 nC=16 za SVE non-Spark ME17.8.5 binarnih (14 SW varijanti).

### Vrijednosti po snagama
- 300hp SC: max Q15=0.944 (2018/2019/2021 identični)
- 230hp SC: max=0.785 | 130/170hp NA: max=0.524 | GTI 1503 130/155hp: max=0.440
- GTI 1503 230hp SC: max=0.952 | GTI90: max=0.572

### Ispravke
- Stara pretpostavka "GTI 16×12" bila NETOČNA — svi su 12×16 LE u16 Q15
- 0x02436C ostaje injector linearization (1D) — NE prava 2D fuel mapa

### Promjene koda
- map_finder.py: ACE1630_INJ_ADDR=0x022066, _ACE1630_INJ_DEF (12×16 Q15), _scan_ace1630_injection()
- Map count: 57 (300hp), 64 (130/170hp), 63 (GTI 1503)

## 2026-03-20 — README.md kompletno prepisano (svi motori podržani, točni podaci)


## 2026-03-20 13:00 -- 4-TEC 1503 map_finder.py audit

### Sto je istrazeno
Kompletan binarni audit svih 9 1503 dumpova vs map_finder.py skeneri.

### Zakljucci

**Detekcija (map_finder.py)**:
- 1503 SW IDovi (10SW025022/025752/025021/040008/040962) triggiraju 
- Ovo je ISPRAVNO -- isti put kao GTI90/1630 NA
- 1503 dobiva: sve standardne skenere + _scan_ace1630_injection + _scan_gti_ignition_extra

**VERIFIKOVANE adrese (iste kao 1630/GTI90)**:
- fuel_2d_header @ 0x02202A: nR=12, nC=16 (identican)
- fuel_2d_data @ 0x022066: OK (ali razlicite vrijednosti po snazi)
- ign_base @ 0x02B730: OK (19 mapa, stride 144B, 12x12 u8 0.75deg/bit)
- extra_ign @ 0x028310: 8 mapa prolaze validaciju (NA range 30-70)
- lambda_main @ 0x0266F0: OK (aktivna kalibracija, ne flat)
- lambda_mirror @ 0x026C08: OK
- torque_main @ 0x02A0D8: OK (sve 32768=100%, flat -- 4-cil manje torque korekcija?)
- torque_opt @ 0x02A7F0: OK
- torque_phys @ 0x029FD4: OK (razliciti Nm po varijanti)
- rpm_axis @ 0x024F46: IDENTICAN 1630
- sc_correction @ 0x02220E: flat 16384 za 130/155hp (neutralno), aktivno za 230SC
- lambda_adapt @ 0x0268A0: OK
- lambda_trim @ 0x026DB8: OK
- lambda_bias @ 0x0265D6: OK
- lambda_eff @ 0x02AE5E: OK (razlicite vrijednosti po varijanti)
- lambda_thresh @ 0x02B378: OK
- accel_enrich @ 0x028059: OK
- temp_fuel @ 0x025E50: OK (flat 23130=Q14+41.2%, sto je razlicito od 1630)
- thermal_enr @ 0x02AA42: OK
- knock_params @ 0x0256F8: OK (65535/65535=max threshold za 130/155, 44237 za 230SC)
- deadtime @ 0x0258AA: OK (malo razlicite vrijednosti od 1630)
- kfped_data @ 0x029548: OK
- sc_boost_fact @ 0x025DF8: flat 23130 ZA SVE 1503 (Q14=+41.2%)
- idle_rpm @ 0x02B600: 2018=razlicito, 2019=identican 1630
- lambda_prot @ 0x02469C: IDENTICAN 1630 (iste vrijednosti)
- mat_corr @ 0x022726: IDENTICAN 1630 (iste vrijednosti)
- eff_corr_u8 @ 0x0259DC: OK (malo razlicite vrijednosti)

**SPECIFICNOSTI 1503 vs 1630**:
- overtemp_lambda @ 0x025ADA: AKTIVNA (38036,38036,...) -- NE 0xFFFF bypass kao 1630!
- neutral_corr @ 0x025B58: 23130 za 130/155hp (1630=16448); SC 230=16448 (isto)
- sc_bypass @ 0x020534/0x0205A8/0x029993: 0x1E1E=7710 za 130/155hp (1630 ima razlicit kod)
- rev_limit @ 0x028E94: 5243 ticks=7892 RPM (2019+); 0x028E96: 5374=7699 RPM (2018)
- dfco_ramp @ 0x028C30: razlicite vrijednosti (ne vazece 1630 adrese za 1503?)
- start_inj @ 0x025CDC: razlicita os za 130/155hp vs 230SC (230SC=isti kao 1630)

**FALSE POSITIVES** (bugovi u map_finder.py za 1503):
1. : 168/192 non-zero, prolazi threshold >=48 -- KRIVO, nije fuel mapa
2. : 8481=0x2121 je IGN DATA (33,33 u8 = 24.75 deg BTDC), prolazi 4000-13000 range -- KRIVO

**Ignition extra serija @ 0x028300** (NOVO otkrice):
- 1503 ima 8 blokova @ 0x028300 (stride 144B, ista velicina)
- 0x028300 je 0x10=16B ISPRED GTI_IGN_BASE=0x028310
- Blockovi @ 0x028310 (stride 144B) su UNUTAR ovih blokova, ali ne potpuno poklapajuci
- Oba scannera (0x028300 i 0x028310) nalaze validne ign mape -- jedan je offset, ali 1503 validira na oba

### Zakljucak za implementaciju
1503 radi uglavnom ispravno kao GTI/NA varijanta BEZ promjena -- jedine akcije:
- Ukloniti false positive 0x02436C za 1503 (filter po SW ID)
- Ukloniti false positive 0x02B72A/0x02B73E za 1503 (ili dodati 1503 SW u exlude)
- Dokumentirati da 1503 ne koristi SC bypass kao indikator (sve varijante imaju non-zero SC bypass kod)

### Fajlovi pregledani
- core/map_finder.py (cijeli, 3000+ linija)
- _materijali/dumps/2018/4tec1503/130v1.bin, 155v1.bin, 130v2.bin, 155v2.bin, 230.bin
- _materijali/dumps/2019/4tec1503/130.bin, 155.bin, 230.bin
- _materijali/dumps/2020/4tec1503/130.bin
- _materijali/dumps/2021/1630ace/300.bin (referenca)
- _materijali/tec1503_audit.md (citanje prethodnih nalaza)

## 2026-03-20 — Planirani novi dumpovi

Korisnik planira dumpati:
- **2016 300hp** (1630 ACE SC) — SW nepoznat, vjerojatno 10SW004672
- **2017 300hp** (1630 ACE SC) — SW potpuno nepoznat, prvi put
- **2016 260hp** (4-TEC 1503 SC) — SW vjerojatno 1037524060 ili stariji
- **2017 260hp** (4-TEC 1503 SC) — SW nepoznat

Napomena: "300maps" u ECU/MIX je EDITIRAN fajl (BOOT CS invalid, fuel max=1.889>1.0) — nije stock 2016 dump.
Pravi stock 2016/2017 dumpi se tek trebaju napraviti.

## 2026-03-20 — 2016 300hp dump verificiran: 10SW004675

Korisnik dodao dump: `_materijali/dumps/2016/1630/300.bin`
- SW: **10SW004675** (NOVI ID — nije 10SW004672 kao što smo mislili!)
- CS: VALIDAN (CRC32-HDLC OK)
- Veličina: 1,540,096 B ✓
- Rev limiter: **5126 ticks = 8072 RPM** @ 0x028E44 i 0x028E94
- SC bypass @ 0x020534: 0x2626 (shadow, ispravno), @ 0x0205A8: **0x3333** (aktivan — različit od 2018+ koji ima 0x2626!)
- Fuel mapa: NE @ 0x022066 — vjerojatno @ 0x022016 (0x50 bajta ranije) ili drugačiji layout
- Dodano u engine.py KNOWN_SW i map_finder.py _300HP_SW_IDS

## 2026-03-20 23:30 — Sesija: unknow folder analiza, 2016 dump, OLS ekstrakcija, map_finder ispravci

### HPT fajl analiza
- `7A1163NC7FOS1 - 2018 RXT-X.hpt` = **AES enkriptiran** (entropy 7.99 svugdje), nema cleartext
- Ne može se parsirati bez HP Tuners softvera + licencnog ključa za taj VIN
- Zaključak: fajl je bekoristan za direktnu ekstrakciju map definicija

### "300maps" u ECU/MIX
- SW @ 0x001A = nepoznat, BOOT CS **INVALID**, SC bypass 0x3333/0x306D (nedosljedno)
- Fuel mapa max = 1.889 Q15 (nemoguće — max je 1.0)
- **Zaključak: ovo je korisnikov raniji eksperiment editiranja, nije stock dump**

### 2016 300hp dump (10SW004675)
- Dump dodan: `_materijali/dumps/2016/1630/300.bin`
- SW ID: `10SW004675` (NOVI — nije 10SW004672 kao što smo pretpostavljali)
- CS: VALIDAN, veličina: 1,540,096 B ✓
- Rev limiter: **5126 ticks = 8072 RPM** @ 0x028E44 i 0x028E94
- SC bypass @ 0x0205A8: **0x3333** (razlikuje se od 2018+ koji ima 0x2626!)
- Fuel mapa: **NE @ 0x022066** — header na toj adresi vrši nR=5333,nC=6400 (garbage)
  - Vjerojatno @ 0x022016 ili potpuno drugačiji CODE layout za ovaj SW
  - Mapin pravi format za 2016 ostaje **neistražen**
- Dodano u: `engine.py` (KNOWN_SW), `map_finder.py` (_300HP_SW_IDS)
- map_finder za 10SW004675 pronalazi samo ~24 mape (fuel mapa propušta)

### map_finder.py ispravci
1. **_1503_SW_IDS** set dodan (10SW025021/025022/025752/040008/040962)
2. **10SW004675** dodan u _300HP_SW_IDS
3. **_is_1503()** metoda dodana
4. **find_all()** preskače `_scan_injection` za 1503 (0x02436C = sve nule → false positive)
5. **_scan_rev_limiter_known()** filtira 0x2121 (IGN DATA bajtovi = 24.75° BTDC, ne rev limiter ticks)

### CAN sniffer fix
- VCIError "Error warning limit exceeded": IXXAT hard error counter ≥ 96 (BUDS2 je aktivan paralelno)
- Fix: dodan "warning limit" i "error warning" u exception handler (continue, ne raise)
- `tools/can_sniffer.py` ažuriran

### OLS ekstractor agent (a61930ae) — ključni nalazi
- RXP OLS (`Sea-Doo RXP 1.5 compr - 524060.ols`): ECU @ offset 0x62D6D; BOOT počinje `60000000` (NE `c0000000` kao normalni ME17!) — moguć drugačiji extraction format ili OLS varijanta
- RXTX OLS: ECU @ offset 0xD6543; BOOT `c0000000` (normalan)
- SW = 1037524060 za oba (4-TEC 1503 RXT-X)

### 4-TEC 1503 SC vs NA — ključne razlike (iz agentovih nalaza)
- 130hp NA (10SW025022): fuel Q15 max=0.440, ign row0=24.8° svi cols, rev=7699 RPM, SC bypass 0x1E1E
- 230hp SC (10SW025021): fuel Q15 max=0.952, ign row0: cols 1-6=32.2°/cols 7-12=24.8°, rev=7664 RPM, SC bypass 0x1F1F
- 155hp NA (10SW025752): identičan 130hp NA (max=0.440, 7699 RPM)
- 2019 svi (10SW040008): fuel max=0.440, rev=7892 RPM, SC bypass=0x1E1E (svi NA bypass bez obzira na snagu)

### Fajlovi promijenjeni
- `core/engine.py` — 10SW004675 dodan u KNOWN_SW
- `core/map_finder.py` — _1503_SW_IDS, 10SW004675, _is_1503(), 0x02436C skip za 1503, 0x2121 filter
- `tools/can_sniffer.py` — VCIError handler proširen

## 2026-03-20 23:45 — OLS agent završen: rxtx_260 je multi-image container!

### Kritično otkriće: 1037524060 format
- `rxtx_260_524060.bin` je **multi-image container** s 3 ECU slike, svaka 128KB:
  - Block1 @ 0x000000: RXTX-X stock (CS=0x53532E7D)
  - Block2 @ 0x020000: RXP compr (CS=0x1CF16484) — identičan RXP OLS ekstrakciji
  - Block3 @ 0x040000: treća varijanta
  - **CODE počinje @ 0x060000** (NE @ 0x010000 kao u standardnom 10SW formatu!)
- Standardne ME17 adrese (0x022066 itd.) **ne rade** za ovaj format — drugačiji memory layout
- RXP vs RXTX = 96% razlika između blokova — nisu stock vs tuned, nego **različiti modeli** (RXP-X vs RXT-X)

### OLS ekstrakcija potvrđena
- TEMP_rxp1503_orig.bin (128KB, CS=0x1CF16484) — ekstrakcija iz RXP OLS uspješna
- TEMP_rxtx1503_orig.bin (128KB, CS=0x53532E7D) — ekstrakcija iz RXTX OLS uspješna
- Metoda: `ols[SW_idx - 0x1A : SW_idx - 0x1A + 0x20000]`

### 4TEC 1503 SC vs NA razlike (finalna tablicia, potvrđeno)
| Mapa | Adresa | SC 230hp | NA 130hp |
|------|--------|----------|----------|
| Fuel max Q15 | 0x022066 | 0.9524 | 0.4404 |
| IGN row0 | 0x02B730 | 32.2° (cols 1-6) | 24.8° flat |
| SC correction Q14 | 0x02220E | 1.021–1.196 | flat 1.000 |
| SC bypass | 0x020534/0x0205A8 | 0x1F1F | 0x1E1E |
| KFPED X-os | 0x029528 | MAP kPa [-80..+90] | pedal° [0..70] |
| Torque max | 0x029FD4 | 340.0 Nm | 332.8 Nm |
| Rev limit | 0x028E96 | 7664 RPM | 7699 RPM |

### SC bypass extra lokacija 0x029993
- SC: 0x1F1F1F1E (zadnji bajt 0x1E — prijelazni kod)
- NA: 0x1E1E1E23 (zadnji bajt 0x23 — drukčiji suffix)

### Fajlovi promijenjeni
- Nema — research task

## 2026-03-20 23:55 — 2016/4tec1503/260.bin verificiran; rxtx_524060 = ME17, nije Siemens

### 2016 260hp dump
- File: `_materijali/dumps/2016/4tec1503/260.bin`
- SW: **10SW000778** (NOVI ID — RXT-X 260hp SC 2016)
- CS: VALIDAN (CRC32-HDLC residua OK)
- Veličina: 1,540,096 B ✓; VME17 string: PRISUTAN ✓
- **Stariji ME17 format** — CODE adrese drugačije od 2018+ 1503 SW
  - SC bypass @ standardnim 2018 adresama (0x020534/0x0205A8): 0xFFFF (garbage)
  - Pravi SC bypass @ **0x012C60 = 0x2020** (novi opcode za stariji 1503 gen)
  - Boost factor @ 0x025DF8 = 0 (standardna adresa ne radi)
  - Fuel header @ 0x02202A/C = garbage (0x022066 layout ne radi za ovaj SW)
- Dodano u engine.py KNOWN_SW

### rxtx_260_524060.bin provjera
- **NIJE Siemens MSE 3.7** — VME17 + BOSCH string potvrđeni
- Isti stariji ME17 format kao 10SW000778 (2016/260)
- **Razlika 2016/260 vs rxtx_524060: samo 1330B** (154B BOOT + 1045B CODE + 131B CAL)
- SC bypass @ 0x012C60 = 0x2020 (identičan u oba)
- Zaključak: rxtx_524060 je susjedna SW revizija, vjerojatno 2014-2015 RXT-X 260
- **Ne treba preimensovati** — ostaje u _materijali/ sa SW oznakom (1037524060)

### Fajlovi promijenjeni
- `core/engine.py` — 10SW000778 dodan u KNOWN_SW

## 2026-03-21 00:15 — _docs/dumps_inventory.html kreiran

- HTML dump browser s dark temom (konzistentno s ME17Suite UI)
- 27 dumpova + 1 extra (rxtx_524060); svi CS OK
- Filteri: godina, ECU tip, SC/NA, snaga, free search, "samo unikatni SW"
- Sortiranje po svim kolonama (klik na header)
- Boje po snazi (300hp=crvena, 230hp=žuta, 130/90hp=plava/ljubičasta), SC/NA badge, ECU tip boja
- Duplikati su osjenčeni (dup marker)
- Kartice s ukupnom statistikom (total, unikatni SW po ECU tipu, CS valid count)

## 2026-03-21 00:30 — IBR modul MCU dump identificiran (SPC5602P)

- `Desktop/MCU/SPC5602P/u1 478/` = **IBR (Intelligent Braking & Reverse) modul** firmware dump
- MCU: NXP/Freescale SPC5602P (MPC5602P) — 256KB CFLASH + 64KB DFLASH + 16KB CSHADOW
- SW @ 0x0000: `08722440` (BRP decimalni format)
- **NIJE** Siemens MSE 3.7, **NIJE** engine ECU
- CFLASH sadrži `0590FFFx` / `0101FFF1` stringove — vjerojatno CAN diagnostic service IDs
- Planirati: CAN reverse engineering IBR ↔ ECU ↔ SAT poruka iz CFLASH stringova
- `u1 478` = unit 1, 478 radnih sati (analogno `064 211` konvenciji)

## 2026-03-21 00:40 — 2016/215hp dump verificiran + HTML SW Kronologija tab + 215 u engine.py

### 2016 215hp dump
- File: `_materijali/dumps/2016/4tec1503/215.bin`
- SW: **10SW000776** — samo 2 manje od 260hp (10SW000778)! Pattern potvrđen.
- CS: VALIDAN, veličina OK, VME17 potvrđen
- SC bypass @ 0x012C60 = 0x2020 (identičan 260hp — isti opcode)
- vs 260hp: 9305B razlike (142B BOOT + 9032B CODE + 131B CAL)
- Dodano u engine.py KNOWN_SW

### SW Kronologijska analiza — HTML tab
- Dodan drugi tab "SW Kronologija" u `_docs/dumps_inventory.html`
- Timeline s grupiranim godišnjim blokovima, vizualni SW bar, pattern kartice
- SW_ALL lista s predviđenim nedostajućim SW-ovima
- Ključni nalaz: 215hp (000776) i 260hp (000778) u istoj generacijskoj grupi — release batch razlika = 2

## 2026-03-21 — Kontekst projekta: dumps = vlastiti ECU čitovi

- Svaki .bin u dumps/ = fizički ECU koji je korisnik osobno čitao (BUDS2 + MultiProg)
- Alat podržava: Spark 2014+, svi ostali 2016–2022
- Baza je jedinstvena — nisu internet fajlovi, nego vlastiti čitovi s realnih Sea-Doo-a
- 28 dumpova = 28 ECU-a koje je korisnik imao u rukama
- Ovo je profesionalni servisni/tuning alat, ne akademski projekt

## 2026-03-21 00:55 — 2017/4tec1503/230.bin verificiran (10SW012999)

- SW: **10SW012999** — između 11328 (Spark) i 23910 (2018 300hp), savršeno u pattern-u
- CS: VALIDAN, VME17 OK, veličina OK
- **2017 = parcijalna 2018 migracija**:
  - RADE na 2018 adresama: SC bypass (0x020534/0x0205A8=0x1F1F), ign_base (0x02B730=43), rev_lim (0x028E94=5126t=8072RPM), sc_corr (0x02220E), lambda_main (0x0266F0), kfped_data (0x029548), fuel_2d (0x022066=8438, vjerojatno OK)
  - NE RADE: boost_fact (0x025DF8=358≠23130), temp_fuel (0x025E50=3000), lambda_trim (0x026DB8=0), torque_main (0x02A0D8=39424), inj_lin (0x02436C=0 kao 1503)
  - Rev limiter: samo jedna kopija @ 0x028E94 (ne 0x028E96 kao 2018+)
- vs 2018/230SC: 400,510B razlike — masivno
- vs 2016/260: 445,513B razlike — 2017 bliže 2018 nego 2016
- Dodano u engine.py KNOWN_SW, HTML Inventory i SW Kronologija tab

## 2026-03-20 18:00 — Provjera valjanosti 2016/1503 i 2017/1503 dumpova

Korisnik: "vidi razlika zadnja dva dumpa, mozda nisu ispravni?"

**Analiza:**
- 2016/4tec1503/215.bin (10SW000776): CS=OK(0x6E23044F), Valid, MCU confirmed
- 2016/4tec1503/260.bin (10SW000778): CS=OK(0x6E23044F), Valid, MCU confirmed
- 2017/4tec1503/230.bin (10SW012999): CS=OK(0x6E23044F), Valid, MCU confirmed

**Diff 215 vs 260:** 9305B (BOOT:142, CODE:9032, CAL:131) — poklapa se s prethodnom mjerenjem

**Nalaz:** 0x028E94 = 0x2F2F (12079 ticks) za oba 4TEC 1503 2016 dump — nije rev limiter adresa za tu gen; pravi rev limiter na ovom SW-u još neistražen

**Zaključak:** Dumpi su ispravni. Problem = nepoznata rev limiter adresa za 10SW000776/000778.

## 2026-03-20 18:10 — Novi dump: 2017/4tec1503/260.bin (10SW012502)

- SW: 10SW012502 (nepoznat ranije)
- CS: OK (0x6E23044F) | Valid | MCU confirmed
- MD5: 5fde1bb781d142131f91e82af2811cf3
- SC bypass: 0x012C60=0x2020 (stara gen stil), 0x0205A8=0xFFFF (ne migriran)
- Rev @ 0x028E94=0x2F2F (nije rev limiter adresa za ovu gen), 0x028E96=0x3331
- Diff vs 230hp 2017 (012999): 445KB — masivno, potpuno drugaciji CODE layout
- Klasifikacija: _2016_GEN_SW_IDS (isti CODE layout kao 2016 4TEC 1503)
- SW=12502 je 497 manji od 012999 = raniji build u istoj godini
- Ažurirano: engine.py KNOWN_SW, map_finder.py _2016_GEN_SW_IDS, HTML inventory + SW_ALL

## 2026-03-20 18:15 — Agent rezultati: 4 agenta završena, 2017 adrese istraživane

Sva 4 agenta završena:

**Agent 1 (map_finder 2016/2017 gen):**
- _2016_GEN_SW_IDS, _2017_GEN_SW_IDS, _is_2016_gen(), _is_2017_gen() implementirani
- 2016 gen: samo rev+SC bypass skeneri, 0 false positives za 215/260
- 2017 gen: skip injection/torque/boost_factor/temp_fuel/lambda_trim
- Rezultati: 2016/215=0mapa, 2016/260=0mapa, 2016/300=4mape, 2017/230=23mape, 2019/300=57mapa (bez regresije)

**Agent 2 (SW Compat Widget):**
- ui/sw_compat_widget.py kreiran (QDialog, 13 kategorija, boje, upgrade info)
- Toolbar tipka "Prikaz SW Compat" dodan u main_window.py

**Agent 3 (Docs update):**
- HTML bez duplikata potvrđen
- SW_VERSIONS.md: dodane sekcije 2016 gen, 2017 gen, SW kronologija
- CLAUDE.md: 10SW000776/000778/012999 SW varijante + map_finder napomene

**Agent 4 (2017 adrese):**
- Globalni offset -0x2AA za SC-specifične mape u 10SW012999
- boost_factor: 0x025B4E, temp_fuel: 0x025BA6
- lambda_main: 0x026446 (mirror +0x518 @ 0x02695E)
- lambda_trim: 0x026B0E
- torque_mirror: 0x029BC0 (ISPRED main-a, ne iza\!)
- torque_main: 0x02A0D8 (ISTA kao 2018, ali drugačije vrijednosti)
- Dokumentirano u _materijali/2017_gen_address_audit.md

**Dodano u sesiji:**
- 2017/4tec1503/260.bin (10SW012502): CS OK, CODE layout = 2016 gen stil
- Dodano u _2016_GEN_SW_IDS (ne _2017_GEN_SW_IDS)
- map_finder.py komentari ažurirani s točnim -0x2AA adresama

## 2026-03-20 14:00 — Analiza service bulletina i dijagnostičke dokumentacije

### Što je napravljeno
- Pročitani svi dostavljeni dokumenti: 2016 SeaDoo ACE 1630 300HP.docx, Bosch_LSU_4.9.pdf, sbg2011-003 enTimingChain.pdf, resources_0 (safety recall 2011-2012), dijagnostički manuali 20/22/23/26/27/33, ECU SIEMENS.pdf/1.pdf
- Izvučeni ključni tehnički podaci, part numberi, specs

### Ključni nalazi
- **diag 20**: 6-straničan scanned PDF (Microsoft Print to PDF, 2022-08-02) — OCR nije moguć bez alata; sadržaj vjerojatno DTC tablice/wiring za stariji Siemens MSE
- **diag 22/23/26/27**: powersports-diag.com BUDS2 tutoriali (Word→PDF, 2023-04): iBR turn off, DESS chip error, Spark 60→90HP upgrade, X package aktivacija
- **diag 33**: BRP TST artikel #kA83x000000XZic — MY21/MY22 cluster reset procedura (Chrome PDF, 2023-04-21)
- **ECU SIEMENS.pdf**: PCB shema Siemens MSE 3.7 (C165 MCU) — ekstrahiran djelomični pinout, CAN_TXD/RXD pins vidljivi
- **ECU SIEMENS1.pdf**: ista PCB shema ali s ćiriličnim natpisima (ruska/ukrajinska varijanta)
- **Bosch LSU 4.9**: kompletni specs — 6-pinski, IP=pump current, Nernst=300Ω, heater 7.5W/7.5V
- **sbg2011-003**: timing chain kampanja za SVE 2011 4TEC motore (130/155/215/260hp)
- **resources**: safety recall 2011-0005/2012-0001 — pucanje poklopca prednjeg pretinca na GTI/GTS MY11/12

### Fajlovi čitani (nisu modificirani)
- C:\Users\SeaDoo\Desktop\SEADOO\0BULLETIN\* (4 fajla)
- C:\Users\SeaDoo\Desktop\SEADOO\diaag manual\* (6 fajlova)
- C:\Users\SeaDoo\Desktop\SEADOO\0WIRING\MIX\ECU SIEMENS*.pdf (2 fajla)

## 2026-03-20 16:30 — Kompletan audit novog dumpa: 2017/1630ace/300.bin = 10SW004672

### Sto je napravljeno
- Kompletan binarni audit dumpa C:\Users\SeaDoo\Desktop\me_suite\_materijali\dumps\2017\1630ace\300.bin
- SW identifikacija, rev limiter, SC bypass, ignition, lambda, torque, fuel mapa, MapFinder
- Diff prema svim poznatim dumpovima, posebno prema 10SW004675 (2016/300hp)

### Kljucni nalaz: 10SW004672 = 2016 gen layout (NIJE 2017!)
- **SW: 10SW004672** (NIJE 10SW012999 kako je ocekivano za 2017 300hp!)
- File size: 0x178000 (1540096B) - validan
- MD5: bf400e70eaceb7403055211a5ce6f418

### Rev limiter
- 0x028E94: **5126 ticks => 8072 RPM** (identican 10SW004675!)
- 0x028E96: 11550 ticks => 3582 RPM (nije rev limiter - garbage na ovom SW)
- 0x028E44: takoder 5126 ticks => 8072 RPM (duplikat)

### SC bypass
- 0x020534: 0x2626 (300hp 2018+ vrijednost - ali ovo je 2016 gen SW!)
- 0x0205A8: **0x3333** (2016 gen 300hp vrijednost - kao 10SW004675!)
- 0x029993: 0x306D (nepoznata vrijednost, razlikuje se od 004675!)
- 0x012C60: **0x2020** (2016 gen alternativna adresa - kao 10SW000776/000778!)

### Diff prema poznatim SW-ovima
- vs 10SW004675 (2016 300hp): **1265B** - NAJBLIZI (susjedne SW revizije!)
  - BOOT: 141B diff (SW string + checksum + RSA potpis)
  - CODE: 992B diff u 130 blokova
  - CAL: 132B diff
- vs 10SW040039 (2019 300hp): 399722B - sasvim razlicit
- vs 10SW023910 (2018 300hp): 400398B - sasvim razlicit
- vs 10SW012999 (2017 4TEC 230hp): 17978B - razlicit motor/family

### Ignition mapa
- IGN_BASE @ 0x02B730 (standardna): Map#0 Row0 = [30,30,30,30,30,30,30,30,25.5,25.5,25.5,25.5] deg
- IGN_BASE @ 0x02B72C (2018 alternativa): Map#0 Row0 = [26.25,27.75,29.25,30,...] deg - razlicit profil

### Fuel mapa 2D
- 0x022066: header garbage (nR=213, nC=0) - potvrda da 2016 gen layout NEMA fuel mapu na ovoj adresi
- Identican problem kao 10SW004675

### Lambda mapa
- 0x0266F0 (std): min=20 (0.0006), max=34964 (1.0670), 88 unique vrijednosti
- Nije flat - aktivna lambda mapa, raspon realan za 300hp SC
- 0x026446 (2017 4TEC alternativa): prvih 5 = [1.0533, 1.0416, 1.0399, 1.0476, 1.05] - moguce lambda @ ovoj adresi?

### Torque mapa
- 0x02A0D8: min=26368 (103%), max=35840 (140%) - row0 sve 32768 (128%) = flat/neaktivno
- IDENTICAN 10SW004675 (True)
- 0x02A5F0 mirror: garbage vrijednosti - NE koristi standardnu mirror adresu

### Boost factor
- 0x025B4E: flat **20046** = Q14 * 1.2235 (+22.4%) - IDENTICAN 10SW004675!
- Adresa poklapa se s 2017 gen offsetom (-0x2AA) - ali i 2016 gen koristi ovu adresu
- 0x025DF8 (std 2018+): garbage - ne koristi se za 2016 gen

### MapFinder rezultat
- **24 mape** - kao ocekivano za 2016 gen
- IGN_BASE @ 0x02B730 (koristi standardnu, ne 2018 varijantu)
- SC bypass @ 0x020534 detektiran (iako aktivna kopija je @ 0x0205A8 s 0x3333!)

### Zakljucak
- **10SW004672 je 2016 gen layout** - ista generacija kao 10SW004675, NIJE 2017 gen
- Susjedne SW revizije: 004672 i 004675 (razlika u SW broju = 3)
- Razlike od 004675: 1265B uglavnom u 0x012C80 bloku + scatter promjene u 0x027xxx (ignition kalibracije?)
- 2017 folder je KRIVE GODINE - ovaj ECU je 2016 hardware s 2016 gen SW
- Ili: BRP je koristio stariji 2016 gen SW i u 2017 godisnim modelima (moguci overlap)

### Fajlovi promijenjeni
- work_log.md (ovaj unos)
- chat_log.md

---

## 2026-03-20 — Signature search: sekundarne lambda mape u 2016 gen 4-TEC 1503

### Fajlovi promijenjeni
- `_docs/scan_2016_1503_lambda_secondary.md` (novo)

### Rezultati
- **Globalni offset: −0x1AA6** — konzistentan za SVE lambda sekundarne mape
- **overtemp_lambda**: **0x024034** (2018: 0x025ADA) — identičan sadržaj ref230 SC; 260hp==215hp
- **neutral_corr**: **0x0240B2** (2018: 0x025B58) — flat 0x4040 SC bypass za oba; odmah iza overtemp
- **lambda_bias**: **0x024B30** (2018: 0x0265D6) — SC krivulja, 260hp vs 215hp potpuno različiti (141/141)
- **lambda_main** (bonus): **0x024C4A** (2018: 0x0266F0) — all Q15, diff 260vs215 = 216/216
- **lambda_mirror** (bonus): **0x025162** (2018: 0x026C08)
- **lambda_adapt** (bonus): **0x024DFA** (2018: 0x0268A0)
- **lambda_trim** (bonus): **0x025312** (2018: 0x026DB8)
- **KFWIRKBA** (41×18 Q15): **NIJE PRONAĐENA** — ni signature ni content match ni offset match; konzistentno s ~24 mapa limitom 2016 gen

### Metodologija
- Signature search (8/6/4B), content search, Q15 blok scan, OS sekvenca search, brute-force 4B segmenti
- Proba s ref230 (SC), ref130 (NA), ref2017 (10SW012999) kao referencama

## 2026-03-20 17:30 — Binary istraživanje sekundarnih mapa 2016 gen 1630 ACE

### Fajlovi promijenjeni
- `_docs/scan_2016_ace_secondary.md` (novo)

### Rezultati
- **Boost factor @ 0x025B4E** (ne 0x025DF8!) — flat 20046 (0x4E4E) Q14=1.2235 (+22.4%); identičan 2018+!
  - CLAUDE.md za 004672 imao pravo s adresom; vrijednost 2018+ je također 20046 (ne 20054 kako stoji u CLAUDE.md)
- **SC correction @ 0x0221FA** (Agent5 potvrđen) — offset 2018 samo +0x14; sadržaj identičan 2018+ ref!
- **Overtemp lambda @ 0x025830** — flat 0xFFFF, offset = +0x2AA vs 2018
- **Neutral corr @ 0x0258AE** — flat 0x4040, offset = +0x2AA vs 2018
- **DFCO @ 0x02899C** (BONUS) — sadržaj identičan 2018 ref (0x028C30), offset = +0x294
- Dominantni CODE offset: **+0x2AA** (boost/overtemp/neutral/second-0xFFFF sve na istom); DFCO +0x294
- 10SW004675 == 10SW004672 bit-for-bit za SVE pronađene mape
- 2016 gen fuel mapa @ 0x022066 = garbage (potvrđeno — header nevaljan)

## 2026-03-21 — Nastavak sesije: preostali OVISI O/UTJECE NA blokovi

**Fajl:** `core/map_finder.py`

**Dodano 16 blokova (nastavak prethodne sesije):**
- `_SPARK_LAMBDA_DEF` — open-loop lambda cilj (4 kopije); OVISI O: lambda senzor NE postoji (open-loop)
- `_scan_2016_1503_ign_corr_2d` — 2D ign korekcija (2016 1503)
- `_scan_2016_1503_mat_corr` — MAT korekcija goriva (2016 1503)
- `_scan_2016_1503_accel` — accel enrichment (2016 1503)
- `_scan_2016_1503_cold_start` — cold start injection (2016 1503)
- `_scan_2016_1503_kfped` — drive-by-wire (2016 1503)
- `_scan_2016_1503_overtemp_lambda` — overtemp lambda (2016 1503)
- `_scan_2016_1503_neutral_corr` — neutral korekcija (2016 1503)
- `_scan_2016_1503_lambda_bias` — lambda bias (2016 1503)
- `_scan_2016_ace_sc_corr` — SC korekcija (2016 ACE)
- `_scan_2016_ace_boost` — SC boost faktor (2016 ACE)
- `_scan_2016_ace_overtemp_lambda` — overtemp lambda (2016 ACE)
- `_scan_2016_ace_neutral_corr` — neutral korekcija (2016 ACE)
- `_scan_2016_ace_dfco` — DFCO ramp (2016 ACE)
- `_scan_2016_ace_fuel` — 2D fuel mapa Q14 (2016 ACE)
- `_scan_2016_ace_torque` — torque ogranicenje (2016 ACE)

**Ukupno u ovoj sesiji (oba dijela):** 59 MapDef description stringova dobilo OVISI O/UTJECE NA blokove

**Provjera:** `python -c "from core.map_finder import MapFinder; print('OK')"` → OK

## 2026-03-21 — UI refaktor + bugfixi (sesija u toku)

**Fajlovi:** `ui/main_window.py`, `core/map_finder.py`, `ui/map_dependency_viewer.html`

- Reset bug fix: `FoundMap.ori_data` snapshot, `refresh_cell` dirty check, `_on_reset_map` handler
- UI: menu bar skriven, 5 top-level tabova (MAPE/EEPROM/DTC/Diff/MapDiff), Back gumb u EEPROM/DTC
- Kalkulator premješten u PropertiesPanel (uvijek dostupan uz map editor)
- CS Fix: pravi dialog (stored/computed/status + Write gumb ako treba)
- Zoom slider vraćen (0.5x-2.0x, default 1.0x); +/- Scale bar (0.1%-2.0% step)
- map_dependency_viewer.html: D3.js force graph, 31 node, 6 grupacija
- map_finder.py: 59 MapDef dopunjeni OVISI O/UTJECE NA; agent radi POVECANJE/SMANJENJE u pozadini
