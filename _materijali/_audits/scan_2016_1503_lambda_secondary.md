# 2016 gen 4-TEC 1503 — Sekundarne lambda mape — scan rezultati
Datum: 2026-03-20

## Metodologija
- Signature search (8/6/4B pre/post) + content-based matching + offset analiza
- Referentni: 2018/4tec1503/230.bin (10SW025021, 230hp SC) + 2018/4tec1503/130v1.bin (10SW025022, 130hp NA)
- Ciljni: 2016/4tec1503/260.bin (10SW000778, 260hp SC) + 2016/4tec1503/215.bin (10SW000776, 215hp SC)
- **Globalni offset: 0x1AA6** — svi pronađeni sekundarni lambda pointeri su 2018_adresa - 0x1AA6

---

## Lambda bias (1×141 u16 LE Q15)
- 2018+ adresa: 0x0265D6
- **2016 gen adresa: 0x024B30**
- Offset: 0x0265D6 - 0x024B30 = **0x1AA6** (konzistentno s ostalim mapama)
- Verifikacija tgt260 (260hp SC): min=0x81C2 max=0x8A60 unique=17 — SC krivulja (>1.0 Q15)
- Verifikacija tgt215 (215hp SC): min=0x8240 max=0x8AAC unique=28 — SC krivulja
- Diff 260 vs 215: 141/141 vrijednosti različite → prava tunabilna mapa
- Napomena: adresa 0x024FA8 (signature hit od ref130 NA) je lažni hit —
  tamo je dio lambda_adapt ili sekundarne zone, ne prava lambda_bias za SC varijante

---

## Overtemp lambda (1×63 u16 LE Q15)
- 2018+ adresa: 0x025ADA
- **2016 gen adresa: 0x024034**
- Offset: 0x025ADA - 0x024034 = **0x1AA6**
- Verifikacija tgt260 == ref230 (SC): identično (byte-po-byte match, unique=17)
- Verifikacija tgt215 == tgt260: identično (215hp i 260hp SC = isti sadržaj)
- Sadržaj: min=0x0D0D max=0x8080, bez 0xFFFF bypass (2016 gen nema SC bypass u ovoj tablici)
- Potvrđena granica: 8B ispred = `4040404040404000` (identično ref230), iza = `4040404040...` (neutral_corr)

---

## Neutral correction (1×63 u16 LE Q14)
- 2018+ adresa: 0x025B58
- **2016 gen adresa: 0x0240B2**
- Offset: 0x025B58 - 0x0240B2 = **0x1AA6**
- Verifikacija tgt260: flat 0x4040 (=16448, Q14×1.004) × 63 — identičan ref230 SC
- Verifikacija tgt215: flat 0x4040 × 63 — identičan tgt260
- Mapa odmah slijedi iza overtemp lambda (0x024034 + 126B = 0x0240B2)

---

## KFWIRKBA Lambda efficiency (41×18 u16 LE Q15, 1476B)
- 2018+ adresa: 0x02AE5E
- **2016 gen adresa: NIJE PRONAĐENA**
- Metodologija: signature search (8/6/4B), content search (16B/8B/4B segmenti), Q15 blok scan, OS sekvenca search, brute-force 10 random 4B segmenata — sve bez hita
- Proba s offset 0x1AA6: 0x02AE5E - 0x1AA6 = 0x0293B8 → sadržaj je nekompatibilan (in_Q15=52/738, first vals 0x0404 = mali osi podaci, ne lambda)
- Zaključak: KFWIRKBA (41×18 lambda efficiency) vjerojatno **ne postoji** u 2016 gen 1503 SW-u (10SW000776/000778) — konzistentno s poznatim ~24 mapa (ograničen ME17 format za tu generaciju)

---

## Primarni lambda rezultati (bonus — potvrđeni istim offsetom)

### Lambda main (12×18 u16 LE Q15)
- 2018+ adresa: 0x0266F0
- **2016 gen adresa: 0x024C4A** (0x0266F0 - 0x1AA6)
- tgt260: all Q15, min=0x7E84 max=0x8662 unique=31
- tgt215: all Q15, min=0x7EFC max=0x8824 unique=25
- Diff 260 vs 215: 216/216 (potpuno različiti po snagi)

### Lambda mirror (12×18 u16 LE Q15)
- 2018+ adresa: 0x026C08
- **2016 gen adresa: 0x025162** (0x026C08 - 0x1AA6)
- tgt260: all Q15, min=0x7901 max=0x845B unique=25
- tgt215: all Q15, min=0x77B5 max=0x80D2 unique=13

### Lambda adapt (12×18 u16 LE Q15)
- 2018+ adresa: 0x0268A0
- **2016 gen adresa: 0x024DFA** (0x0268A0 - 0x1AA6)

### Lambda trim (12×18 u16 LE Q15)
- 2018+ adresa: 0x026DB8
- **2016 gen adresa: 0x025312** (0x026DB8 - 0x1AA6)

---

## Globalni offset — 2016 gen 1503 vs 2018

Konzistentni offset **−0x1AA6** za sve sekundarne lambda mape:

| Mapa | 2018+ adresa | 2016 gen adresa | Offset | Status |
|------|-------------|-----------------|--------|--------|
| overtemp_lambda | 0x025ADA | **0x024034** | −0x1AA6 | POTVRĐENO |
| neutral_corr | 0x025B58 | **0x0240B2** | −0x1AA6 | POTVRĐENO |
| lambda_bias | 0x0265D6 | **0x024B30** | −0x1AA6 | POTVRĐENO |
| lambda_main | 0x0266F0 | **0x024C4A** | −0x1AA6 | POTVRĐENO |
| lambda_mirror | 0x026C08 | **0x025162** | −0x1AA6 | POTVRĐENO |
| lambda_adapt | 0x0268A0 | **0x024DFA** | −0x1AA6 | POTVRĐENO |
| lambda_trim | 0x026DB8 | **0x025312** | −0x1AA6 | POTVRĐENO |
| kfwirkba | 0x02AE5E | N/A | — | NIJE PRONAĐENA |

**Napomena o offsetima**: Poznato je da rev limiter u 2016 gen 1503 ima offset −0x2076 (vs 1630 ACE 2019+). Ovaj scan pokazuje da lambda zone imaju offset −0x1AA6 vs 2018 4-TEC 1503. Radi se o različitim referentnim SW-ovima (2016 vs 2018 za isti motor).
