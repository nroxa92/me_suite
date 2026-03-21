# 2016 gen 4-TEC 1503 — Lambda Bias / MAT / Overtemp verifikacija

**Datum:** 2026-03-20
**Fajlovi:**
- 260.bin = 10SW000778 (RXT-X 260hp SC 2016)
- 215.bin = 10SW000776 (215hp SC 2016)
- 230.bin = 10SW025021 (2018 SC ref)
- 130v1.bin = 10SW025022 (2018 NA ref)

---

## 1. Lambda Bias

### Adresa 2016 gen: `0x024B30`

Potvrda adrese: `0x024B30 + 141*2 = 0x024C4A` = lambda main start (poklapa se s lambda main candidatom na -0x1AA6 od 2018 adrese `0x0266F0`).

Offset formula: **2016 gen = 2018 adresa - 0x1AA6** (vrijedi za lambda bias i lambda main).

| SW | Adresa | raw min..max | Q15 min..max | avg Q15 |
|---|---|---|---|---|
| 260 (10SW000778) | 0x024B30 | 33218..35424 | 1.0137..1.0811 | 1.0300 |
| 215 (10SW000776) | 0x024B30 | 33344..35500 | 1.0176..1.0834 | 1.0461 |
| 230_2018 (10SW025021) | 0x0265D6 | 32414..36947 | 0.9892..1.1275 | 1.0237 |
| 130v1_2018 (10SW025022) | 0x0265D6 | 30059..34000 | 0.9173..1.0376 | 0.9753 |

### 260 vs 215 razlika

**141/141 vrijednosti su razlicite** — Agent 2 je bio u pravu.
260 i 215 imaju potpuno razlicite kalibracije lambda bias (kao sto imaju razlicite fuel mape).

### Shape usporedba (krivulja profil)

Kljucne tocke Q15 po poziciji [0] / [20] / [40] / [70] / [100] / [140]:

| SW | [0] | [20] | [40] | [70] | [100] | [140] |
|---|---|---|---|---|---|---|
| 260 | 1.0292 | 1.0137 | 1.0292 | 1.0189 | 1.0238 | 1.0292 |
| 215 | 1.0441 | 1.0600 | 1.0547 | 1.0495 | 1.0441 | 1.0183 |
| 230_2018 | 1.0002 | 1.0002 | 1.0292 | 1.0650 | 1.0042 | 1.0022 |
| 130v1_2018 | 0.9844 | 0.9648 | 0.9648 | 0.9648 | 1.0062 | 0.9899 |

**Zakljucak shape-a:**
- 260 i 230_2018 dijele 16/141 identicnih vrijednosti (sve na Q15=1.0292) — zajednicki "anchor"
- Shape-ovi su razliciti: 260 ima relativno uzak raspon (1.0137–1.0811), 2016 gen 215 ima visi range (1.0176–1.0834), 230_2018 ima siri raspon (0.9892–1.1275), 130v1_2018 je pretezno ispod 1.0
- 2016 gen 260 i 215 oba su potpuno iznad 1.0 (sve vrijednosti >= 1.0137) — karakteristicno za SC motore s aktivnom lambda zastitom
- 2018 NA (130v1) pretezno ispod 1.0 (0.9173 min), SC (230_2018) krivulja crossover oko 1.0

### Kontekst bloka u memoriji (2016 gen)

Struktura kod 0x024A70:
- `0x024A70..0x024A8E` (16 vrijednosti): axis ramp 0.0456..0.2018 — os za neku prethodnu tablicu
- `0x024A90..0x024B2E` (80 vrijednosti, Q15 ~1.02–1.07, unique=4): kraj prethodne tablice (lambda_trim ili adapt)
- **`0x024B30..0x024C49` (141 vrijednosti): lambda bias** — POTVRDJENO
- `0x024C4A` i dalje: lambda main (12x18 = 216 vrijednosti, sve u lambda opsegu)

---

## 2. MAT Correction

### Adrese

| SW | Axis (u8 x12) | Data (u16LE x12) |
|---|---|---|
| 260, 215 | 0x025A92 | 0x025A9E |
| 230_2018, 130v1_2018 | 0x0275E2 | 0x0275EE |

Offset: 0x0275E2 - 0x025A92 = **0x1B50** (razlicit od lambda bias offset -0x1AA6, dakle MAT ima drugaciji CODE pomak)

### Vrijednosti

**260 (10SW000778):**
- axis: `[100, 113, 120, 125, 145, 150, 158, 162, 169, 175, 188, 200]`
- data: `[30416, 30326, 30838, 31611, 31608, 30328, 29555, 26222, 30310, 30326, 30838, 31611]`
- Q15: [0.8002..0.9647], avg=0.9257

**215 (10SW000776):**
- axis: `[100, 113, 120, 125, 145, 150, 155, 160, 169, 175, 188, 200]`
- data: `[30416, 30326, 30838, 31611, 31611, 30328, 29555, 26222, 30310, 30326, 30838, 31611]`
- Q15: [0.8002..0.9647], avg=0.9257

**230_2018 (10SW025021) SC:**
- axis: `[100, 113, 120, 125, 145, 150, 156, 162, 169, 175, 188, 200]`
- data: `[29648, 29555, 29555, 29555, 29555, 29555, 29041, 26990, 29543, 29555, 29555, 29555]`
- Q15: [0.8237..0.9048], avg=0.8943

**130v1_2018 (10SW025022) NA:**
- axis: `[75, 88, 100, 113, 125, 131, 138, 143, 150, 156, 163, 175]`
- data: `[30396, 30326, 30582, 31611, 31611, 31611, 31099, 29560, 30323, 30326, 30582, 31611]`
- Q15: [0.9021..0.9647], avg=0.9400

### Usporedba 260 vs 215

**Nisu identicni** — 3 razlike:

| idx | 260 | 215 | Razlika |
|---|---|---|---|
| axis[6] | 158 | 155 | +3 (temperaturni breakpoint) |
| axis[7] | 162 | 160 | +2 (temperaturni breakpoint) |
| data[4] | 31608 (0.9647) | 31611 (0.9647) | raw razlika 3, Q15 zaokruzeno jednako |

**Zakljucak:** 260 i 215 MAT korekcija je **prakticno identicna** — data[4] razlika je samo +3 raw (~0.00009 Q15, zanemarivo), a axis razlike su u breakpointima [6] i [7] koji su pomaknuti za 3 i 2 stupnja (158 vs 155, 162 vs 160).

### 2016 gen vs 2018 ref

260 vs 230_2018: **ni axis ni data nisu identicni**
- 2016 gen axis raspon: 100–200°C (bez niskih temperaturnih tocaka)
- 2018 NA (130v1) axis raspon: 75–175°C (pocinje ranije, nize temperature)
- 2016 gen SC (260/215) i 2018 SC (230) imaju slicne axis strukture (100–200) ali razlicite data vrijednosti
- 2016 gen ima vise vrijednosti blize 1.0 (max 0.9647), 2018 SC ima nize vrijednosti (max 0.9048) — veca MAT korekcija u 2018

---

## 3. Overtemp Lambda

### Adresa: `0x024034` (1×63 u16 LE Q15)

| SW | raw min..max | Q15 min..max | avg Q15 | 0xFFFF count | unique vals |
|---|---|---|---|---|---|
| 260 (10SW000778) | 3341..32896 | 0.1020..1.0039 | 0.5405 | 0 | 17 |
| 215 (10SW000776) | 3341..32896 | 0.1020..1.0039 | 0.5405 | 0 | 17 |

**260 i 215 su IDENTICNI** — 0/63 razlika.

### Karakter krivulje

Max vrijednost = 32896 (Q15=1.0039) — **NIJE 0xFFFF** => ovo je aktivna overtemp lambda zastita, ne SC bypass.
Minimum = 3341 (Q15=0.1020) — dramaticno bogatenje pri pregrijavanju.

Puna krivulja Q15 (260 = 215):
```
[1.004, 1.004, 0.746, 1.002, 1.004, 0.871, 0.628, 1.004, 1.004, 0.746,
 1.002, 1.004, 0.871, 0.628, 0.784, 0.784, 0.620, 0.283, 0.282, 0.251,
 0.251, 0.102, 0.102, 0.102, 0.102, 0.102, 0.102, 0.102, 0.102, 0.102,
 0.102, 1.000, 1.004, 0.871, 0.628, 1.004, 1.004, 0.746, 1.002, 1.004,
 0.871, 0.628, 1.004, 1.004, 0.746, 0.784, 0.784, 0.683, 0.557, 0.282,
 0.282, 0.251, 0.103, 0.102, 0.102, 0.102, 0.102, 0.102, 0.102, 0.102,
 0.102, 0.102, 0.102]
```

**Napomena:** Krivulja ima cudnu strukturu (vrijednosti osciliraju umjesto da budu monotone) — moguce da 0x024034 nije stvarna overtemp tablica ili da je format drugaciji od 1630 ACE equivalenta (0x025ADA). Potrebna daljnja provjera konteksta.

---

## Sazetak nalaza

| Parametar | 260 vs 215 | 2016 gen vs 2018 | Status |
|---|---|---|---|
| Lambda bias adresa | ISTA (0x024B30) | -0x1AA6 od 2018 | POTVRDJENO |
| Lambda bias vrijednosti | 141/141 RAZLICITI | Shape razlicit | RAZLICITE kalibracije |
| MAT adresa | ISTA (0x025A92/9E) | -0x1B50 od 2018 | POTVRDJENO |
| MAT vrijednosti | ~identicni (3 minor diff) | Razlicite vrijednosti | 260=215 prakticno |
| Overtemp lambda | IDENTICNI (0/63) | - | 260==215 potvrdjeno |

### Kljucni zakljucci

1. **Lambda bias adresa 0x024B30 je tocna za 2016 gen 4-TEC 1503** — aligment potvrden (bias_end = main_start = 0x024C4A)
2. **260 i 215 imaju razlicite lambda bias kalibracije** (141/141 razlika) — kao sto je Agent 2 utvrdio; istu struk. ali razlicite vrijednosti
3. **MAT korekcija 260 vs 215 je prakticno identicna** (3 minor razlike, zanemarivo)
4. **Overtemp lambda** 260 == 215 (identicni) — oba motora dijele istu overtemp zastitu
5. Offset za lambda u 2016 gen vs 2018: -0x1AA6 (bias i main), -0x1B50 (MAT) — nije uniformni globalni offset
