# Lambda Verify — 2016 gen 4-TEC 1503

**Datum:** 2026-03-20
**Fajlovi:**
- `_materijali/dumps/2016/4tec1503/260.bin` (10SW000778, 260hp SC)
- `_materijali/dumps/2016/4tec1503/215.bin` (10SW000776, 215hp SC)
- `_materijali/dumps/2018/4tec1503/230.bin` (10SW025021, 230hp SC — referentni)

---

## 1. 2018 ref @ 0x0268A0 (lambda_adapt, 12x18 Q15)

| Parametar | Vrijednost |
|-----------|-----------|
| raw min   | 0x7C45 (31813) |
| raw max   | 0x8C11 (35857) |
| Q15 min   | 0.9709 |
| Q15 max   | 1.0943 |
| Q15 avg   | 1.0251 |
| unique vals | 140 |

Karakteristika: veliki plateau u donjim redovima (~1.033-1.058), tipično za ECU koji je skupljao adaptaciju tokom vožnje. Raspon prelazi 1.0 u oba smjera.

---

## 2. Kandidati u 2016 gen 260.bin

### Map A @ 0x024A90 (12x18 Q15)

| Parametar | 260.bin | 215.bin |
|-----------|---------|---------|
| Q15 min   | 1.0137  | 1.0176  |
| Q15 max   | 1.0811  | 1.0834  |
| Q15 avg   | 1.0267  | 1.0443  |
| unique approx | 19 | 30 |

**260 vs 215 razlika:** 216/216 ćelija razlikuju se (max_diff=0.0696 Q15, avg_diff=0.022 Q15)

Karakteristika: **sve vrijednosti >1.0** (lean bias). Redovi 0-2 su flat 1.019 u 260.bin (flat 1.044 u 215.bin) — različit default za svaki SW. Raspon uzan, sve pozitivne korekcije.

```
260.bin @ 0x024A90 (prvih 6 redova):
  row00: 1.019 1.019 1.019 1.019 1.019 1.019 1.019 1.019 ... (svi 1.019)
  row01: 1.019 1.019 1.019 1.019 1.019 1.019 ... (svi 1.019)
  row02: 1.019 1.019 1.019 1.019 1.019 1.019 ... (svi 1.019)
  row03: 1.019 1.019 1.019 1.019 1.019 1.019 1.019 1.019 1.039 1.049 1.049 1.039 1.029 ...
  row04: 1.019 ... 1.029 1.029 1.050 1.081 1.070 1.060 1.060 ...
  row05: 1.029 ... 1.014 1.014 1.014 ...
```

### Map B @ 0x024C40 (12x18 Q15)

| Parametar | 260.bin | 215.bin |
|-----------|---------|---------|
| Q15 min   | 0.9884  | 0.9921  |
| Q15 max   | 1.0499  | 1.0636  |
| Q15 avg   | 1.0197  | 1.0285  |
| unique approx | 30 | 26 |

**260 vs 215 razlika:** 216/216 ćelija razlikuju se (max_diff=0.0578 Q15, avg_diff=0.020 Q15)

Karakteristika: **raspon prelazi 1.0 u oba smjera** (0.988-1.050). Uključuje vrijednosti i ispod i iznad 1.0. Više varijacije po ćeliji. Bliže profilu lambda_main 2018 ref.

### Map C @ 0x024DF0 (12x18 — NEVAŽEĆI)

Repovi mape C (redovi 9-11) sadrže non-Q15 vrijednosti (0.0006-1.054, Q15 avg=0.875). Radi se o "tail corruption" — region u koji se preliva prethodna tablica s osima/podacima koji nisu lambda. **Ova adresa nije upotrebljiva kao lambda mapa.**

### Session B kandidat @ 0x024DFA — POGREŠAN

0x024DFA = 0x024DF0 + 0x0A = **10 bajta (5 u16) unutar Map C**. Nije na granici 12x18 bloka. Ista garbage statistika kao 0x024DF0. **Odbaciti.**

---

## 3. Koji bolje odgovara lambda_adapt ulozi?

**Odgovor: Ni jedan od ta dva nije lambda_adapt.**

Analiza:

| Kriterij | 2018 lambda_adapt | 260 @ 0x024A90 | 260 @ 0x024C40 |
|----------|------------------|----------------|----------------|
| Raspon Q15 | 0.971–1.094 | 1.014–1.081 | 0.988–1.050 |
| Prelazi <1.0 | Da | **Ne** | Da |
| avg | 1.025 | 1.027 | 1.020 |
| 260 vs 215 razlika | N/A | 216/216 | 216/216 |
| Shape dist. vs 2018_main | — | 0.104 | 0.138 |
| Shape dist. vs 2018_adapt | — | 0.123 | 0.225 |

**Zaključak za Session A (0x024C40 = lambda_adapt):** POGREŠAN naziv.
0x024C40 je **lambda_main** — raspon prelazi 1.0 u oba smjera, shape distance bliža 2018_main nego 2018_adapt, a adapt bi trebao biti bliže "neutarlan" u factory-fresh ECU-u.

**Zaključak za Session B (0x024DFA = lambda_adapt):** POGREŠAN offset.
Misaligned (5 u16 unutar Map C), garbage vrijednosti.

---

## 4. Je li 0x024A90 zaista lambda_main?

**Odgovor: Vjerojatno je lambda_TRIM ili lambda_BIAS (sekundarna tablica), ne main.**

Ključni razlozi:
- Sve vrijednosti >1.0 (1.014-1.081) — lambda_main koji kontrolira AFR treba imati i <1.0 vrijednosti za WOT bogatu smjesu
- 2018 lambda_main ima min 0.983, 0x024A90 ima min 1.014 — fizikalno nije main ako ne može ciljati lambda <1.0
- Profil podsjeća na adaptiranu tablicu s lean biasom (ECU koji nije odradio reset adapcije)
- Može biti lambda_trim koji koristi ECU za statičnu korekciju gornje razine

**Moguće interpretacije 0x024A90:**
1. **lambda_trim** (statična kalibracija, lean side correction) — najvjerovatnije
2. **lambda_adapt** koji je bio factory pre-loaded s lean biasom (ne standardni default=1.0)

---

## 5. Triplet struktura 2016 gen 1503

Tri uzastopne 12x18 mape s razmakom +0x1B0 = 432B (= 12*18*2B, tj. direktno jedna za drugom, BEZ razmaka između):

| Uloga | Adresa | Q15 min | Q15 max | Napomena |
|-------|--------|---------|---------|---------|
| **lambda sekundarna/trim** | **0x024A90** | 1.0137 | 1.0811 | sve >1.0, lean bias |
| **lambda_main** | **0x024C40** | 0.9884 | 1.0499 | raspon ±1.0, primarni AFR target |
| ~~lambda_adapt~~ | ~~0x024DF0~~ | — | — | NEVALJANA: tail corruption |

Mirror set (+0x518 od svake):

| Uloga | Adresa | Q15 min | Q15 max |
|-------|--------|---------|---------|
| mirror sekundarne | 0x024FA8 | 0.9697 | 1.0515 |
| **mirror lambda_main** | **0x025158** | 0.9453 | 1.0340 |

Za usporedbu 2018 gen (10SW025021, 230hp SC):

| Uloga | Adresa | Q15 min | Q15 max |
|-------|--------|---------|---------|
| lambda_main | 0x0266F0 | 0.9831 | 1.0727 |
| lambda_adapt | 0x0268A0 | 0.9709 | 1.0943 |
| lambda_trim | 0x026DB8 | 0.9421 | 1.0253 |
| mirror_main | 0x026C08 | diff 216/216 | — |

---

## Razlika 2016 vs 2018 strukture

- **2018:** main (432B) + **48B gap** + adapt (432B) + **0x16A8 gap** + trim
- **2016:** A (432B) + **bez razmaka** + B (432B) + **bez razmaka** + C-corrupted

Odsutnost razmaka u 2016 gen sugerira da su osi pohranene negdje drugdje (ili su shared s prethodnom tablicom). Potvrđeno: osi za ovaj blok su na 0x024A44 (18pt RPM, raw/4 = 4100-8500 RPM) i 0x024A68 (18pt load Q14, 640-6613 raw = 3.9-40.4%).

---

## Konačna preporuka

| Varijabla | Ispravna adresa | Stara (Session A) |
|-----------|----------------|-------------------|
| `lambda_main_2016_1503` | **0x024C40** | bila označena kao adapt |
| `lambda_trim_2016_1503` | **0x024A90** | bila označena kao main |
| `lambda_main_mirror_2016_1503` | **0x025158** | — |
| `lambda_adapt_2016_1503` | **NEPOZNATA** (nije od ta 3) | 0x024C40 (pogrešno) |

**Session B adresa 0x024DFA — odbaciti, misaligned.**

Prava lambda_adapt za 2016 gen 1503 ostaje **neidentificirana** iz ove sesije. Potrebna je nova pretraga u bloku koji slijedi iza 0x025308 (Mirror C kraj) ili u nekom drugom dijelu CODE regije.
