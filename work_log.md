# ME17Suite — Work Log

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
