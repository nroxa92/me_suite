# 2016 gen 1503 — Correction mape — scan rezultati
Datum: 2026-03-21

Referentni binariji: 2018/4tec1503/230.bin (10SW025021), 2018/4tec1503/130v1.bin (10SW025022)
Ciljni binariji: 2016/4tec1503/260.bin (10SW000778), 2016/4tec1503/215.bin (10SW000776)
Metoda: signature search (8B pre + 8B post), cross-verifikacija s oba ciljana binarija

---

## Thermal enrichment (8×7 u16 LE /64=%)
- 2018+ adresa: 0x02AA42
- **2016 gen adresa: 0x028004** (obje varijante 260hp i 215hp)
- Offset vs 2018: -0x2A3E
- Verifikacija: vrijednosti identične 2018 (isti postotak npr. 194.5%, 197.5%, 100.0% na kraju)
- Potvrda: dvostruki hit (pre + post signatura neovisno potvrdile istu adresu)

## Deadtime (10×14 u16 LE, 280B)
- 2018+ adresa: 0x0258AA
- **2016 gen adresa: 0x023E04** (obje varijante)
- Offset vs 2018: -0x1AA6
- Verifikacija: logične vrijednosti (5710→5013→4323... padajući niz = trajanja pulsa), 2016 ima nešto drugačije kalibracije ali isti format
- Napomena: X-osa (trajanje, u8) ispred podataka @ 0x023DF4 (pre-data), vidljivo kao `2500330040004d005b006800750083009000ab00`

## Eff correction / KFWIRKBA sub (14×10 u8 /128=1.0, 140B)
- 2018+ adresa: 0x0259DC
- **2016 gen adresa: 0x023F36** (obje varijante)
- Offset vs 2018: -0x1AA6 (isti kao deadtime — leže u istom bloku)
- Verifikacija: raspon 128–159 (/128 = 1.00–1.24), isti pattern ponavlja se po redovima (14-pt Y-osa)
- Napomena: deadtime i eff_correction su susjedni u 2016 gen (kao i u 2018+)

## Ignition correction 2D (8×8 u8, 64B)
- 2018+ adresa: 0x022374
- **2016 gen adresa: 0x02169A** (obje varijante)
- Offset vs 2018: -0xCDA
- Verifikacija: logične u8 vrijednosti (113–188 raw = 84.75°–141° pri scale 0.75°/bit)
- Napomena: post-signatura `0500050004000a00` potvrđena s obje strane; 230hp i 130hp ref daju isti hit

## MAT air temp correction (12pt u16 LE Q15)
- 2018+ adresa (osa): 0x0275E2, data: 0x0275EE
- **2016 gen adresa (osa): 0x025A92, data: 0x025A9E** (obje varijante — isti podaci 260==215!)
- Offset vs 2018: -0x1B50
- Format: 12pt uzlazna u8 osa (temp, npr. [100,113,120,125,145,150,158,162,169,175,188,200]) + 12×u16 LE Q15
- Vrijednosti 2016 260hp: [30416,30326,30838,31611,31608,30328,29555,26222,30310,30326,30838,31611]
- Vrijednosti 2016 215hp: [30416,30326,30838,31611,31611,30328,29555,26222,30310,30326,30838,31611] (~iste)
- Kopije: 2 kopije s stride=0x122 (290B) — oba u CODE regiji: 0x025A92 i 0x025BB4
- Napomena: u 2018+ postoje 4 kopije (0x0275E2/0x027704/0x027826/0x027948), isti stride 0x122

## DFCO decel RPM ramp (16×11 u16 LE, 352B)
- 2018+ adresa: 0x028C30
- **2016 gen: NIJE PRONAĐENA u ekvivalentnom formatu**
- Status: Stub/placeholder @ 0x026CAC — samo `[100, 150, 0xFFFF×20]` (2-točkasta osa, sve ostalo 0xFFFF)
- Napomena: 0x028C30 u 2016 gen sadrži IGN mapu (12×12 u8, vrijednosti 0x28=30.0°BTDC) — adresa je rekoristena
- Napomena: 2017 gen (10SW012999) ima isti stub @ 0x028C30 — potvrđuje da je 16×11 DFCO tablica tek uvedena s 2018 gen
- Zaključak: DFCO ramp 16×11 nije implementirana u 2016/2017 gen 1503

---

## Sažetak offseta za 2016 gen 1503

| Mapa | 2018+ adresa | 2016 gen adresa | Offset |
|------|-------------|-----------------|--------|
| thermal_enrichment | 0x02AA42 | 0x028004 | -0x2A3E |
| deadtime | 0x0258AA | 0x023E04 | -0x1AA6 |
| eff_correction | 0x0259DC | 0x023F36 | -0x1AA6 |
| ign_correction_2d | 0x022374 | 0x02169A | -0x0CDA |
| MAT correction (osa) | 0x0275E2 | 0x025A92 | -0x1B50 |
| MAT correction (data) | 0x0275EE | 0x025A9E | -0x1B50 |
| dfco_ramp | 0x028C30 | NIJE PRONAĐENA | — |

Za usporedbu: rev limiter offset = -0x2076 (poznato), što je blisko ali ne jednako thermal offsetu (-0x2A3E).

## Pouzdanost
- thermal_enrichment: **VISOKA** (dvostruki hit, identični podaci)
- deadtime: **VISOKA** (post-sig hit, logični podaci)
- eff_correction: **VISOKA** (post-sig hit, logični Q15-ish podaci)
- ign_correction_2d: **VISOKA** (dvostruki hit)
- MAT correction: **SREDNJA** (pattern scan, 2 kopije neovisno potvrđene, logični Q15 podaci)
- dfco_ramp: **N/A** — nije prisutna u 2016/2017 gen (different CODE layout)
