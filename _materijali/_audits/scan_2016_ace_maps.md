# 2016 gen 1630 ACE — Map discovery — scan rezultati
Datum: 2026-03-21
SW: 10SW004675 (2016) i 10SW004672 (2017 folder, 2016 gen layout)
Referentni: 10SW054296 (2020 300hp SC), 10SW000778 (2016 4TEC 1503 260hp SC)

---

## Metodologija
Tri pristupa primijenjena paralelno:
1. **Signature search** od 2018+ ACE 1630 (ref20) prema 2016 ACE — pre/post kontekst 12B
2. **Signature search** od 2016 1503 (ref16) prema 2016 ACE — kontrolna provjera
3. **Direktna binarna verifikacija** — header bajtovi, osi, vrijednosti, mirror provjera

---

## Fuel 2D mapa

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x022052** |
| **Adresa (2018+)** | 0x022066 |
| **Offset razlika** | −0x0014 (−20B) |
| Format | 12×16 u16 LE |
| **SKALA** | **Q14** (ne Q15!) — sve vrijednosti 2× veće od 2018+ |
| Max vrijednost | 1.889 (Q14) = 0.944 Q15 (identično 2018+ 300hp SC!) |
| Osi | Identične: RPM 1400–8200 rpm (16pt), Load 6.5–54.7% (12pt) |
| Header @ | 0x022016 (nRows=12, nCols=16, Y-os, X-os) |
| 75 vs 72 razlika | 0/192 ćelija (isti SW sadržaj) |
| 75 vs ref20 razlika | 192/192 (faktor ×2 — drugačija skala) |

**Zaključak**: Fuel mapa je prisutna i identificirana. Iste fizičke vrijednosti goriva kao 2018+, samo s Q14 umjesto Q15 normalizacijom (bit shift razlika). Osi identične. MapFinder može koristiti adresu **0x022052** s napomenom o skaliranju.

---

## Ignition base

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x02B31E** |
| **Adresa (2018+)** | 0x02B730 |
| **Offset razlika** | −0x0412 (−1042B) |
| Format | 12×12 u8, stride 144B |
| **Broj mapa** | **19** (mape #00–#18, identično 2018+) |
| Sadržaj | **Identičan** s ref20 u svim 19 mapama (diff=0/144 za sve) |
| Map#00–#07 | Base ignition (34–45 range = ~25.5–33.75°BTDC) |
| Map#08–#09 | Knock trim (mješavine 0 i normalnih vrijednosti) |
| Map#10–#15 | Aux A/B/SC mape |
| Map#16–#17 | Extended (NPRo) |
| Map#18 | Conditional/fallback (40/144 u range, ostalo nule) |
| Drugi set | @ 0x02B870 (main+0x552) — identičan backup set (0/144 diff) |
| 75 vs 72 razlika | 0/144 za sve mape |

**Zaključak**: Ignition je u potpunosti identificiran. 19 mapa na stride 144B od baze **0x02B31E**. Sadržaj identičan 2018+, samo baza pomaknuta za −0x0412. MapFinder može koristiti IGN_BASE=**0x02B31E**.

---

## Lambda main

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x026444** |
| **Adresa (2018+)** | 0x0266F0 |
| **Offset razlika** | −0x02AC (−684B) |
| Format | 12×18 u16 LE Q15 |
| Q15 raspon | 0.984–1.080 (isti kao ref20) |
| Mirror | **NEMA identičnog mirrora** u cijelom CODE prostoru |
| Header context | Identičan s ref20 (64B pred tablicom = 0 razlike) |
| 75 vs 72 razlika | 0 (identično) |

**Napomena**: Lambda nema identičnog mirrora u 2016 gen 1630 ACE (za razliku od 2018+ koja ima mirror +0x518). Adresa **+0x518 od main = 0x02695C** sadrži lambda_trim (Q15=[0.955–1.063]), nije mirror. Ovo je konzistentno s 2016 gen arhitekturom.

---

## Lambda trim

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x026B0C** |
| **Adresa (2018+)** | 0x026DB8 |
| **Offset razlika** | −0x02AC (−684B) — isti offset kao lambda_main |
| Format | 12×18 u16 LE Q15 |
| Q15 raspon | 0.960–1.032 |
| Napomena | Identičan offset od main kao 2018+ (+0x6C8) |

---

## Lambda adapt

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x0265F4** |
| **Adresa (2018+)** | 0x0268A0 |
| **Offset razlika** | −0x02AC (−684B) — isti offset |
| Format | 12×18 u16 LE Q15 |
| Q15 raspon | 0.979–1.068 |
| Napomena | Identičan offset od main kao 2018+ (+0x1B0 od main) |

---

## Torque main

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x029B48** |
| **Adresa (2018+)** | 0x02A0D8 |
| **Offset razlika** | −0x0590 (−1424B) |
| Format | 16×16 u16 BE Q8 |
| Hi-byte raspon | 109–140 (= Nm/100 × Q8 scale) |
| Mirror | @ **0x02A060** = main + 0x518 (identičan mirror, OK) |
| Sadržaj vs ref20 | **Identičan** (0/256 diff) — 300hp SC torque nije mijenjan |
| 75 vs 72 razlika | 0/256 |

**Zaključak**: Torque je u potpunosti identificiran s ispravnim mirrorom. Torque krivulja (fizičke Nm vrijednosti) @ **0x029A44** = ref20 @ 0x029FD4, offset −0x590, identičan sadržaj.

---

## Torque mirror

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x02A060** |
| **Adresa (2018+)** | 0x02A5F0 |
| **Offset od main** | +0x518 (standardni mirror offset — potvrđen) |
| Sadržaj | Identičan torque_main (0/512B diff) |

---

## SC boost factor

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x025B4E** |
| **Adresa (2018+)** | 0x025DF8 |
| **Offset razlika** | −0x02AA (−682B) |
| Format | 1×40 u16 LE Q14 |
| Vrijednost | flat 20046 = Q14×1.2235 = +22.4% |
| Napomena | Identična vrijednost kao 2018+ (isti SC kompresori) |

---

## SC correction

| Parametar | Vrijednost |
|-----------|-----------|
| **Adresa (2016 ACE)** | **0x0221FA** |
| **Adresa (2018+)** | 0x02220E |
| **Offset razlika** | −0x0014 (−20B) — isti kao fuel_2d! |
| Format | 9×7 u16 LE Q14 |
| Q14 raspon | 0.325–2.191 |
| Sadržaj | **Identičan** s ref20 (iste vrijednosti) |

---

## Rev limiter (referentni podaci, potvrđeni ranije)

| Adresa | Opis | Vrijednost |
|--------|------|-----------|
| 0x028E44 | Primary | 5126 ticks = **8072 RPM** |
| 0x028E94 | Mirror | 5126 ticks = **8072 RPM** |

---

## SC bypass (potvrđeni podaci)

| Adresa | 10SW004675 | 10SW004672 | Napomena |
|--------|------------|------------|---------|
| 0x020534 | 0x2626 | 0x2626 | Shadow |
| 0x0205A8 | 0x3333 | 0x3333 | Active (razlikuje se od 2018+ koji ima 0x2626!) |
| 0x029993 | 0x306D | 0x306D | Extra |
| 0x012C60 | 0x2020 | 0x2020 | 2016 gen alternativna adresa |

---

## Zaključak — Offset tablice

Nema jedinstvenog globalnog CODE offseta. Svaka regija ima vlastiti pomak:

| Regija | Offset (2018+ - 2016) |
|--------|-----------------------|
| fuel_2d / sc_correction | +0x0014 |
| lambda_main / trim / adapt / boost_factor | ~+0x02AC |
| ign_base | +0x0412 |
| torque_main / mirror / curve | +0x0590 |

---

## MapFinder implementacija — preporuke

Za `_is_2016_gen()` provjeru dodati skenere:

```python
# 2016 gen 1630 ACE adrese
FUEL_2016_ACE    = 0x022052  # Q14 (2× Q15 vrijednosti!)
IGN_BASE_2016_ACE = 0x02B31E  # 19 mapa, stride 144B
LAMBDA_2016_ACE  = 0x026444  # NEMA mirrora
TORQUE_2016_ACE  = 0x029B48  # mirror @ +0x518 = 0x02A060
SC_BOOST_2016_ACE = 0x025B4E  # flat 20046 Q14
SC_CORR_2016_ACE = 0x0221FA  # 9x7 Q14
```

Estimirani broj mapa za 2016 gen 1630 ACE s ovim adresama: **~35–40 mapa**
(prethodnih ~24 bez fuel/ign/lambda/torque → sada kompletni set)

---

## Bilješke

- 10SW004675 i 10SW004672 imaju **0 razlika** u fuel/ign/lambda/torque mapama — iste kalibracije
- Ukupna razlika između ova dva SW je 1265B (130 blokova) uglavnom u ignition kalibracijama i 0x012C7C regiji, ali ne u mapama direktno
- Fuel mapa Q14 faktor: vrijedi samo za 2016 gen 1630 ACE; 2016 gen 1503 (10SW000778) ima fuel @ 0x0232D0 s drugačijim skaliranjem
- Lambda nema mirror u 2016 gen: za razliku od 2018+ (main=0x0266F0, mirror=0x026C08), 2016 gen ima samo jednu kopiju
