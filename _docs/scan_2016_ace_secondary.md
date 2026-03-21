# Sekundarne mape — 2016 gen 1630 ACE (10SW004675 / 10SW004672)

**Datum**: 2026-03-20
**Referentni binariji**:
- 2016: `_materijali/dumps/2016/1630ace/300.bin` (10SW004675)
- 2017: `_materijali/dumps/2017/1630ace/300.bin` (10SW004672) — 2016 gen layout
- 2018+ ref: `_materijali/dumps/2019/1630ace/300.bin` (10SW040039)

**Metoda**: binary/signature search u CODE regiji (0x010000–0x05FFFF)

---

## 1. Boost Factor

**2018+ adresa**: 0x025DF8 (1×40 u16 LE Q14, flat)
**2016 gen adresa**: **0x025B4E** (potvrđeno binarno)
**Offset**: 2018 − 2016 = **0x2AA** (682 bajta)

| SW | Adresa | Vrijednost | Q14 | SC boost |
|----|--------|-----------|-----|---------|
| 10SW004675 (2016) | 0x025B4E | 0x4E4E = 20046 | 1.2235 | +22.4% |
| 10SW004672 (2017) | 0x025B4E | 0x4E4E = 20046 | 1.2235 | +22.4% |
| 10SW040039 (2019) | 0x025DF8 | 0x4E4E = 20046 | 1.2235 | +22.4% |

**004675 == 004672**: DA (identični)
**Napomena**: Svi imaju **20046** (0x4E4E), ne 20054 (0x4E56). SC boost identičan kroz 2016–2019+ za 1630 ACE.
CLAUDE.md za 004672 navodi 20046 — potvrđeno. 2018 ref vrijednost iz CLAUDE.md (20054) je netočna — stvarna 2018+ vrijednost je također 20046.

---

## 2. SC Correction

**2018+ adresa**: 0x02220E (9×7 = 63 u16 LE Q14)
**2016 gen adresa**: **0x0221FA** (potvrđeno — Agent5 bio u pravu)
**Offset**: 2018 − 2016 = **0x14** (20 bajta)

Vrijednosti (9×7 grid Q14) — **identične** u 2016 gen i 2018+:

```
row0: [1.003, 1.083, 1.188, 1.275, 1.335, 1.480, 1.803]
row1: [1.883, 0.990, 1.086, 1.197, 1.294, 1.359, 1.513]
row2: [1.880, 1.990, 0.956, 1.080, 1.202, 1.294, 1.367]
row3: [1.529, 1.922, 2.064, 0.820, 1.017, 1.191, 1.296]
row4: [1.370, 1.545, 1.994, 2.136, 0.715, 0.937, 1.150]
row5: [1.285, 1.370, 1.544, 2.012, 2.158, 0.580, 0.837]
row6: [1.093, 1.249, 1.355, 1.540, 2.032, 2.179, 0.501]
row7: [0.771, 1.040, 1.212, 1.338, 1.541, 2.030, 2.191]
row8: [0.325, 0.616, 0.917, 1.123, 1.274, 1.523, 2.031]
```

**004675 == 004672**: DA
**004675@0x0221FA == 040039@0x02220E**: DA (identični sadržaj!)
Dijagonalne vrijednosti < 1.0 = nadopuna (eficiency correction), van dijagonale = SC correction faktori.

---

## 3. Overtemp Lambda

**2018+ adresa**: 0x025ADA (1×63 u16 LE Q15, flat 0xFFFF = SC bypass)
**2016 gen adresa**: **0x025830** (pronađeno flat 0xFFFF search)
**Offset**: 2018 − 2016 = **0x2AA** (682 bajta — konzistentno s boost/neutral)

| SW | Adresa | Sadržaj |
|----|--------|---------|
| 10SW004675 | 0x025830 | 63 × 0xFFFF (SC bypass) |
| 10SW004672 | 0x025830 | 63 × 0xFFFF (SC bypass) — identičan |
| 10SW040039 | 0x025ADA | 63 × 0xFFFF (SC bypass) |

**004675 == 004672**: DA
**Napomena**: Svi SC varianiti imaju flat 0xFFFF (bypass). Format = identičan, samo adresa drugačija.

**Bonus — druga flat 0xFFFF tablica** (64 elementa, nepoznata namjena):

| SW | Adresa |
|----|--------|
| 10SW004675/004672 | 0x0260F2 (64 × 0xFFFF) |
| 10SW040039 | 0x02639E (64 × 0xFFFF) |

Offset iste: 0x02639E − 0x0260F2 = **0x2AC** (≈ 0x2AA, jednobajtna razlika).

---

## 4. Neutral Correction

**2018+ adresa**: 0x025B58 (1×63 u16 LE Q14, flat 0x4040)
**2016 gen adresa**: **0x0258AE** (pronađeno flat 0x4040 search)
**Offset**: 2018 − 2016 = **0x2AA** (682 bajta — konzistentno)

| SW | Adresa | Sadržaj |
|----|--------|---------|
| 10SW004675 | 0x0258AE | 63 × 0x4040 = Q14 1.004 |
| 10SW004672 | 0x0258AE | 63 × 0x4040 = Q14 1.004 — identičan |
| 10SW040039 | 0x025B58 | 63 × 0x4040 = Q14 1.004 |

**004675 == 004672**: DA
**Napomena**: Odmah ispred 0x0258AE je overtemp lambda (flat 0xFFFF), što je konzistentno s 2018+ layoutom.

**Bonus — druga flat 0x4040 tablica** (50 elementa):

| SW | Adresa |
|----|--------|
| 10SW004675/004672 | 0x025C7A (50 × 0x4040) |
| 10SW040039 | 0x025F24 (50 × 0x4040) |

Offset: 0x025F24 − 0x025C7A = **0x2AA**.

---

## 5. DFCO (Decel Fuel Cut-Off RPM Ramp) — BONUS NALAZ

**2018+ adresa**: 0x028C30 (16×11 u16 LE, stride 22B)
**2016 gen adresa**: **0x02899C** (pronađeno exact content match)
**Offset**: 2018 − 2016 = **0x294** (660 bajta)

| SW | Adresa | Sadržaj |
|----|--------|---------|
| 10SW004675 | 0x02899C | identičan sadržaju 040039@0x028C30 (redovi 0-14) |
| 10SW004672 | 0x02899C | identičan 004675 |
| 10SW040039 | 0x028C30 | referentni |

**004675 == 004672**: DA
**Sadržaj identičan 2018+**: DA (redovi 0–14 bit-for-bit isti; row15 = junk/padding u oba)

Uzorak row0 (RPM breakpoints za decel ramp):
```
[8636, 9653, 10670, 0, 1054, 1842, 2911, 4129, 5336, 6474, 7556]
```

---

## Offset Sažetak

| Mapa | 2018+ adresa | 2016 gen adresa | Offset (2018−2016) |
|------|-------------|----------------|-------------------|
| SC correction | 0x02220E | 0x0221FA | **+0x14** |
| Boost factor | 0x025DF8 | 0x025B4E | **+0x2AA** |
| Overtemp lambda | 0x025ADA | 0x025830 | **+0x2AA** |
| Neutral corr | 0x025B58 | 0x0258AE | **+0x2AA** |
| DFCO RPM ramp | 0x028C30 | 0x02899C | **+0x294** |

**Dominantni offset za 2016 gen 1630 ACE = +0x2AA** (isti kao boost/overtemp/neutral)
SC correction je iznimka (+0x14) — vjerojatno jer je ona u drugom područje CODE-a.
DFCO je +0x294 (blizak ali ne identičan dominantnom offsetu).

---

## Identičnost 004675 vs 004672

Sve pronađene mape: **004675 == 004672** (bit-for-bit identični za sve gore navedene tablice).
Ovo je konzistentno s prethodnim nalazom da su te dvije SW verzije susjedne revizije s minimalnim razlikama (1265B CODE diff, uglavnom ignition kalibracije).

---

## Fuel mapa @ 0x022066 — Potvrda nevaljanosti

Header @ 0x02202A/0x02202C za 2016 gen: `D5 14 ... 00 19` — garbage (ne 0x0C/0x10 kao 2018+).
Prvih 8 u16 @ 0x022066: `1D89 1E6F 1C4E 1F6A 1F77 1FD7 36D5 3721` — nisu Q15 fuel vrijednosti.
**Zaključak**: 2016 gen ACE nema fuel mapu na 0x022066 (kao što CLAUDE.md navodi). Adresa neistražena.
