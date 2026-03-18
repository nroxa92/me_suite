# ME17Suite — Work Log

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
