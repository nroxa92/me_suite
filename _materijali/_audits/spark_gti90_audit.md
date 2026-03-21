# Spark 900 ACE + GTI90 — Binarni Audit
**Datum**: 2026-03-19
**Autor**: automatski audit (spark_gti90_audit.py)

---

## DIO 1: SW Identifikacija

| Dump | SW String | Veličina | MD5 |
|------|-----------|----------|-----|
| spark_2018 | 10SW011328 | 1,540,096 B (1504 KB) | 2d57971afdf5364e74ba336be1ed2dad |
| spark_2019 | 10SW039116 | 1,540,096 B (1504 KB) | b12b30c7c8b3798799569bb857b85f8f |
| spark_2020 | 10SW039116 | 1,540,096 B (1504 KB) | b12b30c7c8b3798799569bb857b85f8f |
| spark_2021 | 10SW039116 | 1,540,096 B (1504 KB) | b12b30c7c8b3798799569bb857b85f8f |
| gti90_2020 | 10SW053774 | 1,540,096 B (1504 KB) | f659da3507db1543559547c4d6b82bf0 |
| gti90_2021 | 10SW053774 | 1,540,096 B (1504 KB) | ce47c3ba90a0936d82c22d974e9d800f |

**Header (svi)**: `c0 00 00 00 04 7f 00 00 00 00 02 80 00 7f 00 80` — identičan za sve!

**Zaključak SW identifikacije:**
- Svi dumpovi su iste veličine kao 1630 (1504 KB)
- spark_2019 = spark_2020 = spark_2021 (MD5 identičan — isti binarni fajl!)
- gti90_2020 ≠ gti90_2021 (80 razlika — samo kalibracija/patch)
- spark_2018 (10SW011328) ≠ spark_2019+ (10SW039116) — 3792 razlike

---

## DIO 2: Binarna Usporedba

### Spark međusobno
| Usporedba | Razlike | Napomena |
|-----------|---------|----------|
| spark_2018 vs spark_2019 | 3,792 B | SW string + checksum + calibracija |
| spark_2018 vs spark_2020 | 3,792 B | identično kao 2018 vs 2019 |
| spark_2018 vs spark_2021 | 3,792 B | identično kao 2018 vs 2019 |
| spark_2019 vs spark_2020 | **0 B** | IDENTIČNI (isti binarni fajl) |
| spark_2019 vs spark_2021 | **0 B** | IDENTIČNI (isti binarni fajl) |

**Prvih razlika spark_2018 vs spark_2019:**
- `0x00001F`-`0x000023`: SW string (11328 → 39116)
- `0x000030`-`0x000033`: Checksum bajti
- `0x007E7C`: Boot region (BOOT CS)

### GTI90 međusobno
- gti90_2020 vs gti90_2021: **80 razlika** sve u regiji `0x017F02`-`0x017F15`
  - To je područje unutar CAL regije (0x060000+)... ali adrese su niže, u CODE regiji 0x017F00 — potencijalni patch

### Spark vs GTI90 (2020)
- spark_2020 vs gti90_2020: **450,182 razlika** — kompletno različit SW

### Spark vs 1630 ACE
- spark_2018 vs ref_1630 (2019/300hp): **450,148 razlika** — kompletno drugačiji SW

---

## DIO 3: Rev Limiter

### Potvrđene adrese:
| ECU | Adresa | Ticks | RPM |
|-----|--------|-------|-----|
| Spark 900 (sve god.) | **0x028E34** | 5120 | **8081 RPM** |
| GTI90 (2020/2021) | **0x028E7C** | 5875 | **7043 RPM** |

### Raspored adresa:
- `0x028E34` = Spark rev limiter (potvrđeno)
- `0x028E7C` = GTI90 rev limiter (potvrđeno — procjena ≈7040 RPM bila točna!)
- `0x028E96` = 1630 ACE rev limiter (odvojeno)

**Napomena**: Rev limiter adresi su iste za sve godišnje Spark dumpove — nije promijenjen između 2018 i 2019+.

---

## DIO 4: Ignition Mape

### Spark 900 ACE — ignition lokacija

**Ignition mape NISU na 0x02B730** (1630 adresa):
- @ `0x02B730`: mean=83.1, max=255 — NOK (nije ign)

**Pronađen ignition niz @ `0x026A50`** (stride 144B):
- 8 uzastopnih mapa (12×12, u8, ×0.75°/bit)
- Vrijednosti: mean 29°-41°, max do 57°, min od 5°
- Format: isti 12×12 kao 1630!

**Spark ignition mapa #0 @ 0x026A50** (prvih 4 retka):
```
40  36  34  28  25  21  19  15  14  13  11  10
 8   7   6   5   5   5  53  49  45  37  32  29
28  26  23  21  19  17  15  13  12  11  10   9
 9   8  57  55  49  43  39  36  33  30  29  26
```
**NAPOMENA**: Vrijednosti >47 (npr. 53, 55, 57) su "wrap-around" artefakti skeniranja — skener ne prepoznaje granice tablice ispravno jer ign mape nisu poravnate kao niz od istog početka. Potrebna dodatna analiza za točan offset prvog bajta prvog rekorda.

**Spark ign statistike (8 pronađenih mapa, stride 144B od 0x026A50):**
```
#00: mean=29.2°  max=57°  min=5°
#01: mean=40.6°  max=56°  min=21°
#02: mean=32.1°  max=57°  min=5°
#03: mean=37.7°  max=54°  min=21°
#04: mean=35.1°  max=57°  min=5°
#05: mean=35.8°  max=54°  min=19°
#06: mean=38.2°  max=57°  min=5°
#07: mean=32.7°  max=57°  min=12°
```
- Skener detektira samo 8 uzastopnih (traži stride 144B); Spark ima 27 mapa ali u drugačijem rasoredu (A×8+B×8+B2×8+C×3) pa stride između setova nije 144B

**GTI90 ignition — lokacija:**
- @ `0x02B730`: **OK** (mean=29.0°, max=33°) — GTI90 KORISTI ISTU ADRESU KAO 1630!
- Pronađen niz @ `0x0282EC`: 8 mapa, stride 144B
- GTI90 ign vrijednosti su više i ravnomjernije od Spark (mean 35°-42° vs Spark 29°-41°)

**GTI90 ign mapa #0 @ 0x0282EC** (gore-lijevo kut):
```
42  35  31  28  23  20  18  17
22  25  30  33  35  35  52  48
```
→ Puno glađi profil, manje agresivan timing u niskim RPM nego Spark

---

## DIO 5: Injection Mape

### Spark 900 ACE

| Adresa | Mean | Max | Min | Valid/192 | Napomena |
|--------|------|-----|-----|-----------|---------|
| 0x02436C | 0x55CD | 0xC5AB | 0x0000 | 127 | **Kandidat** (ali neke nule) |
| 0x0244EC | 0x2C20 | 0xFFAB | 0x0006 | 103 | Slabiji kandidat |
| 0x022066 | 0x0000 | 0x0000 | 0x0000 | 0 | NEMA (za razliku od 1630!) |

**Spark injection kandidati (skeniranje):**
- `0x0174B8`: mean=0x6DD8 — visoko u CAL/CODE graničnoj regiji
- `0x021752`: mean=0x43B8 — CODE, razumna vrijednost
- `0x02475C`: mean=0x47F1 — CODE, razumna vrijednost
- `0x024EAA`: mean=0x7855 — visoko, kandidat za lambda-zaštitu
- `0x0253C2`: mean=0x7660 — kandidat

**Spark @ 0x02436C nije čista injekcijska tablica** — 127/192 valid, max=0xC5AB (>1.0 u Q15). Vjerojatno overlapping s drugom strukturom. Potrebna ručna analiza.

### GTI90 injection

| Adresa | Valid/192 | Napomena |
|--------|-----------|---------|
| 0x02436C | 48 | NIJE (samo 25% valjanih) |
| 0x0244EC | 48 | NIJE |
| 0x022066 | **110** | **GTI injection AKTIVNA ovdje!** |

- GTI90 koristi `0x022066` za injection (kao i 1630 GTI legacy format!)
- Mean=0x257A → ≈0.29 u Q15 → relativno niske vrijednosti vs Spark

**GTI90 injection kandidati:**
- `0x025DCE`, `0x026594`, `0x026AAC`, `0x027484` — dodatne injection/lambda tablice
- `0x0282D6`: mean=0x26FE — mali kandidat
- `0x043F3E`, `0x044302` — u 0x040000+ regiji (CAN/cal area?)

---

## DIO 6: Lambda Mape

### Spark 900 ACE

| Adresa | Mean | Uniq | Napomena |
|--------|------|------|---------|
| 0x0266F0 | 0x1350 | 66 | NOK — prenisko (trebalo bi ~0x7FFF) |
| 0x026C08 | 0x23EE | 101 | NOK — prenisko |
| 0x0268A0 | 0x47EB | 132 | Kandidat ali ispod Q15 lambda range |

**Spark lambda skeniranje:**
- `0x024EC4`: mean=0x802D, max=0x8087, min=0x7E02 — **JAKO DOBAR KANDIDAT!**
  - Gotovo sve vrijednosti blizu 0x7E02-0x8087 (lambda ≈ 1.0)
  - 2019 dump: mean=0x7EC9 (malo drugačije od 2018)
- `0x0253DC`: mean=0x7E02 — flat tablica (pasivna/zaštita?)

**Zaključak**: Spark lambda main nije na 0x0266F0! Prava adresa je vjerojatno **0x024EC4** ili blizu.

### GTI90 lambda

| Adresa | Mean | Uniq | Napomena |
|--------|------|------|---------|
| 0x0266F0 | **0x7FC6** | 5 | **FLAT** (pasivna, ≈1.0) |
| 0x026C08 | **0x7E1F** | **127** | **AKTIVNA** (varijabilna) |
| 0x0268A0 | **0x8095** | 5 | Flat |

- GTI90 lambda layout **potvrđuje memorijsku napomenu**: 0x0266F0=flat(pasivna), 0x026C08=aktivna (127 unikatnih vrijednosti)
- GTI90 skeniranje: `0x0265AE` i `0x026AC6` kao dodatni kandidati

---

## DIO 7: DTC Analiza

### Spark vs GTI90 @ 0x0217EE

**Spark @ 0x0217EE** (nije DTC tablica):
```
ec 37 c8 35 1f 2f fb 2e 9a 2b ee 2b 58 2b 6d 2c ...
```
→ Izgledaju kao period ticks (LE u16: 0x37EC=14316, 0x35C8=13768 ...) — vjerojatno RPM kalibracija ili krivulja

**GTI90 @ 0x0217EE** (DTC enable tablica!):
```
06 01 10 16 11 16 12 16 13 16 14 16 15 16 16 16 ...
```
→ `06 01` = P0601 (LE), `10 16` = P1610, `11 16` = P1611 ... — **POTVRĐENO: ovo je GTI90 DTC tablica**

### Najgušće DTC regije

| Dump | Najgušće područje | P-kod kandidata |
|------|-------------------|-----------------|
| spark_2018/2019 | 0x022800-0x022A00 | 256 |
| spark_2018/2019 | 0x023000-0x023200 | 247 |
| spark_2018/2019 | 0x021000-0x021200 | 239 |
| gti90_2020 | 0x023A00-0x023C00 | 248 |
| gti90_2020 | 0x023200-0x023400 | 242 |

### P-kod hitovi (potvrđeni offseti)

**Spark** (2018=2019):
- P0601: `0x02073C`, `0x020768`, `0x021CD0`, `0x025954`, `0x04377E`
- P0335: `0x020F28`, `0x021290`
- P0562: `0x020FE8`, `0x021350`
- P0563: `0x020FE6`, `0x02134E`

**GTI90**:
- P0601: `0x021028`, `0x0253CE`, `0x0270B4`, `0x041EC4`, `0x043D54`
- P0335: `0x021814`, `0x021B7A`, `0x023B28`, `0x02403E`
- P0562: `0x0218DC`, `0x021C42`

### U16Ax (0xD6xx) kodovi
- Spark 2018: 126 kandidata (incl. `0x012CB8: 0xD6D3` koji nedostaje u 2019!)
- Spark 2019+: 126 kandidata (bez `0x012CB8`)
- GTI90: 102 kandidata
- Svi imaju zajedničke adrese: `0x014C1A`, `0x015FD4`, `0x016006` (`0xD640`)

---

## DIO 8: CAN Tablice

### Spark CAN tablica @ 0x0433BC

```
b9 00 bd 00 bf 00 c4 00 c9 00 ce 00 d0 00 d2 00
d4 00 d6 00 d8 00 da 00 dc 00 e0 00 e4 00 e8 00 ...
```
Valid CAN IDs: `0x00B9`, `0x00BD`, `0x00BF`, `0x00C4`, `0x00C9`, `0x00CE`, `0x00D0`, `0x00D2`, `0x00D4`, `0x00D6`, `0x00D8`, `0x00DA`, `0x00DC`, `0x00E0`, `0x00E4`, `0x00E8`, `0x00EC`, `0x00EE`, `0x00F0`, `0x00F2`, `0x00F4`, `0x00F9`, `0x00FE`, `0x0103`, `0x0108`, `0x010C`, `0x010E`, `0x0110`, `0x0112`, `0x0114`, `0x0116`, `0x0118`

**→ Spark koristi niže CAN ID-ove (0x00B9-0x0118) nego GTI90 (0x015x-0x0214)**

### GTI90 CAN tablica @ 0x0433BC

```
01 5b 01 5c 01 48 01 3c 01 5c 01 38 01 08 02 14
01 2c 01 10 01 08 01 7c 00 00 01 00 02 00 03 00 ...
```
Valid CAN IDs: Nema direktno validnih u prvom bloku (vrijednosti > 0x0100 ali čitaju se kao 0x5B01 itd. u BE) — ovo je vjerojatno **timing/period tablica**, ne CAN ID lista!

**GTI90 CAN IDs pronađeni skeniranjem (0x040000+):**
- `0x0587`, `0x0797`, `0x069A`, `0x069D`, `0x069F`
- `0x0180`, `0x0182`, `0x05DE`, `0x0546`
- `0x0544`, `0x03DA`, `0x01B6`
- `0x05D4`, `0x055C`, `0x05C0`, `0x0580`, `0x055E`, `0x05C4`, `0x058E`, `0x021A`
- `0x0186` (CAN ID za GTI) nađen @ `0x04240C`

### Spark specifični CAN ID-ovi (skeniranje):
- `0x0578` nađen @ `0x020880`, `0x022464`, `0x02297C`, `0x03BDF0`
- `0x0280` nađen @ `0x015BA0`, `0x015C16`, `0x015C50`
- `0x03E8` nađen @ `0x0203F0`, `0x0214E6`, `0x021730`, `0x021AA6`

---

## DIO 9: Torque + SC Bypass

### Torque mape

| Dump | 0x02A0D8 (main) | 0x02A5F0 (mirror) |
|------|-----------------|-------------------|
| spark_2018 | mean=0x0000 (NEMA!) | mean=0x0EA1 (djelomično?) |
| spark_2019 | mean=0x0000 (NEMA!) | mean=0x0EA1 |
| gti90_2020 | mean=0x0075 (OK) | mean=0x0075 (OK) |

- Spark nema torque tablicu na 1630 adresi!
- GTI90 ima torque tablicu na obje 1630 adrese (mean ≈ 0x75 = 117 u Q8)

### SC Bypass

| Adresa | Spark | GTI90 |
|--------|-------|-------|
| 0x020534 | `64 7d a3 ff` | `1b 1c 1f 2e` |
| 0x0205A8 | `08 08 00 1a` | `1b 1c 1f 2e` |
| 0x029993 | `1b 1b 1b 1b` | `1b 1c 1f 2e` |

- GTI90 ima iste vrijednosti na sve 3 lokacije → bez SC-a (consistent)
- Spark ima drugačije vrijednosti → drugačija logika (nema kompresora)

---

## DIO 10: Adresna Usporedba Spark vs 1630

| Region | Ista/Različita | Napomena |
|--------|----------------|---------|
| Header | **ISTA** (samo SW string razlika) | c0000000 047f0000... identično |
| Checksum | RAZLIČITA | različiti CRC32 |
| CODE start (0x010000) | **POTPUNO RAZLIČITA** | kompletno drugi SW |
| Rev @ 0x028E34 | RAZLIČITA | Spark: 5120 ticks, 1630: drugačije |
| IGN base @ 0x02B730 | RAZLIČITA | Spark nema ign ovdje |
| INJ @ 0x02436C | RAZLIČITA | Spark: `93 91 8f...`, 1630: nule |
| Lambda @ 0x0266F0 | RAZLIČITA | Spark: `01 01...`, 1630: aktivne vrijednosti |
| Torque @ 0x02A0D8 | RAZLIČITA | Spark: nule |
| DTC @ 0x0217EE | **POTPUNO RAZLIČITA** | Spark: ticks, GTI90/1630: P-kodovi |
| CAN @ 0x0433BC | RAZLIČITA | Spark: 0x00B9-0x0118 range |

---

## Zaključci i Nova Saznanja

### Potvrđeno

1. **spark_2019 = spark_2020 = spark_2021** (MD5 identičan) — BRP nije radio SW update između 2019-2021
2. **GTI90 rev limiter = 7043 RPM @ 0x028E7C** (5875 ticks) — procjena bila točna
3. **Spark rev limiter = 8081 RPM @ 0x028E34** (5120 ticks) — potvrđeno za sve godišnje
4. **GTI90 koristi iste lambda adrese kao 1630**: 0x0266F0=pasivna, 0x026C08=aktivna
5. **GTI90 DTC tablica = 0x0217EE** (isto kao 1630!) — Spark nema DTC tu!
6. **GTI90 ignition @ 0x02B730** (iste adrese kao 1630) — Spark je na drugačijoj lokaciji

### Novo / Nije Znano

7. **Spark ignition je na ~0x026A50** (stride 144B, 8+ mapa), NOT 0x02B730!
   - Puna mapa spark ignition treba dodatnu analizu (27 mapa u 3 grupe A/B/B2/C)
8. **Spark lambda main nije na 0x0266F0** — pravi kandidat je **0x024EC4** (mean ≈ 1.0)
9. **Spark injection kandidat @ 0x02436C** ima 127/192 valjanih vrijednosti — overlapping s drugom strukturom
10. **Spark CAN IDs su u nižem rasponu** (0x00B9-0x0118) vs GTI90/1630 (0x015x-0x07FF)
11. **0x0217EE u Sparku nije DTC** — to su period ticks (RPM kalibracija)
12. **DTC gusta regija za Spark**: 0x022800-0x022A00 i 0x023000-0x023200 (256/247 P-kod kandidata)
13. **GTI90 DTC gusta regija**: 0x023A00-0x023C00 (248 kandidata) — offset od 1630 (0x0217EE)
14. **gti90_2020 vs gti90_2021**: 80 razlika u regiji 0x017F02-0x017F15 (CODE, ne CAL)

### TODO — Daljnja Istraživanja

- [ ] Precizna lokacija Spark injection tablice (ručna analiza oko 0x02436C)
- [ ] Spark lambda main — verificirati 0x024EC4 (je li to stvarno AFR tablica?)
- [ ] Spark ignition — mapirati sve 27 mapa (A×8+B×8+B2×8+C×3) od 0x026A50
- [ ] GTI90 injection tablica — je li na 0x022066 ili drugdje?
- [ ] Spark DTC enable tablica — skenirati 0x022800 regiju ručno
- [ ] GTI90 2020 vs 2021 — što je promijenjeno u 0x017F02 regiji (80 bajta)?
- [ ] Spark CAN tablica — verificirati redoslijed u 0x0433BC bloku

---

*Generirano: 2026-03-19 | Skripte: _materijali/spark_gti90_audit.py*
