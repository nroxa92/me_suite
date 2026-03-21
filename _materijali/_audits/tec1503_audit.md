# 4TEC 1503 Audit — ME17.8.5

**Datum**: 2026-03-19
**Dumps**: 9 binarija (2018×5, 2019×3, 2020×1)

---

## 1. SW Strings i Identifikacija

SW string @ 0x00001A (ASCII, 10 znakova):

| Dump | SW String | HW string |
|------|-----------|-----------|
| 2018/130v1.bin | **10SW025022** | 1037550003 |
| 2018/155v1.bin | **10SW025022** | 1037550003 |
| 2018/130v2.bin | **10SW025752** | 1037550003 |
| 2018/155v2.bin | **10SW025752** | 1037550003 |
| 2018/230.bin   | **10SW025021** | 1037550003 |
| 2019/130.bin   | **10SW040008** | 1037550003 |
| 2019/155.bin   | **10SW040008** | 1037550003 |
| 2019/230.bin   | **10SW040008** | 1037550003 |
| 2020/130.bin   | **10SW040962** | 1037550003 |

**Potvrđeno**: SW string je na offsetu 0x001A (ne 0x0008). HW = 1037550003 (isti kao ACE 1630!).

### Ključni zaključci o identičnosti SW:
- `130v1 == 155v1` (10SW025022) — **binarno identični, 0 razlika**
- `130v2 == 155v2` (10SW025752) — **binarno identični, 0 razlika**
- `2019/130 == 2019/155 == 2019/230` (10SW040008) — **svi identični, 0 razlika**
- `2020/130` = 10SW040962 (poseban SW)

---

## 2. File Layout

Svi dumpi: **1.540.096 B (0x178000)** — isti kao ACE 1630.
Header @ 0x0000: `C0 00 00 00 04 7F 00 00 00 00 02 80 00 7F 00 80` — identičan svim 1503 dumpovima.

---

## 3. Ignition Mape — POTVRĐENO ISTE ADRESE KAO 1630

Ignition mape su na **identičnim adresama** kao ACE 1630 (0x02B730+, stride 144B, 12×12 u8):

| Map # | Adresa | 2018 130/155 | 2018 230 | 2019 sve |
|-------|--------|-------------|----------|----------|
| #00 | 0x02B730 | min=33 max=43 | min=33 max=43 | min=33 max=43 |
| #01 | 0x02B7C0 | min=33 max=45 | min=35 max=47 | min=33 max=45 |
| #02 | 0x02B850 | min=33 max=43 | min=33 max=43 | min=33 max=45 |
| #03 | 0x02B8E0 | min=33 max=43 | min=35 max=43 | min=33 max=43 |
| #04 | 0x02B970 | min=33 max=45 | min=33 max=47 | min=33 max=45 |
| #05 | 0x02BA00 | min=33 max=43 | min=35 max=43 | min=33 max=43 |
| #06 | 0x02BA90 | min=33 max=40 | min=33 max=47 | min=33 max=40 |
| #07 | 0x02BB20 | min=33 max=43 | min=35 max=43 | min=33 max=43 |
| #08 | 0x02BBB0 | min=0 max=175 | min=0 max=200 | min=0 max=175 |
| #09 | 0x02BC40 | min=0 max=43  | min=0 max=43  | min=0 max=43 |

**230hp razlike** (2018_230 vs 130/155): mape #01, #03, #05, #06, #07, #08 su drugačije — više advance.

---

## 4. Injection Mape

### Što postoji na 1630 adresama:
- **0x02436C** (ACE 1630 main inj): min=0x0 max=0xFFFF, q15_count=72/192 — **NIJE injection mapa**, mješovit sadržaj
- **0x0244EC** (ACE 1630 mirror): isto — **NIJE**
- **0x022066** (GTI legacy injection): **JEST injection mapa** — q15_count=182/192

### Injection @ 0x022066 (confirmed):
- 2018 130/155: min=0x0C79, max=0x3860 — manje vrijednosti
- 2018 230 (SC): min=0x0C70, max=0x79E8 — **znatno viši raspon** (SC ima vise goriva)
- 2019 130/155/230: min=0x0C79, max=0x3860 — isti kao 2018 130/155

**Zaključak za injection**: 1503 koristi SAMO adresu 0x022066 (GTI legacy format). Nema mirrora. Potvrđuje prethodnu napomenu "GTI injection @ 0x022066: NEMA mirrora".

---

## 5. Rev Limiter

### Provjera na 1630 adresama (formula RPM = 40MHz×60/(ticks×58)):

| Adresa | Sve 130/155 (v1+v2) | 2019+ 130/155/230 | 2018 230 SC |
|--------|---------------------|-------------------|-------------|
| 0x022096 | 4619 tick → **8958 RPM** | 4619 → **8958 RPM** | 5416 → 7640 RPM |
| 0x0220B6 | 5535 → 7475 RPM | 5535 → 7475 RPM | 6927 → 5973 RPM |
| 0x0220C0 | 5240 → **7896 RPM** | 5240 → **7896 RPM** | 5771 → 7170 RPM |
| 0x028E96 | **5374 → 7699 RPM** | **5243 → 7892 RPM** | 5399 → 7664 RPM |

### Rev limiter interpretacija:
- **0x028E96** = SC bypass/rev limit lokacija (iste kao ACE 1630)
  - 2018 v1/v2: 5374 ticks = **~7700 RPM** (nizi limit)
  - 2019+: 5243 ticks = **~7892 RPM** (isti kao 1630 130/170hp)
- **0x0220C0** = soft-cut @ ~7896 RPM — konzistentno za 1503
- **0x022096** = 4619 ticks = **~8958 RPM** — ovaj je previsok za RL, vjerojatno nesto drugo (overcrank protection?)
- 2018 230 (SC) ima potpuno drugačije vrijednosti

### Formula za 1503:
Formula `RPM = 40MHz×60/(ticks×58)` radi za 1503 isto kao za 1630 — isti ECU, isti hardware timer. Potvrđuje da je kotačić 60-2 i 3-cil equivalent (ili da 1503 s 4cil koristi istu formula s drugačijim kotačićem).

**Napomena**: ticks s BOOT regiona (0x010000-0x014XXX) su u rangu 5000-8000 → RPM 6000-8100, što odgovara mapi RPM osi, a NE rev limiteru direktno. Rev limiter su specifični u CODE kod ~0x022096 i 0x028E96.

---

## 6. DTC Analiza

### U16Ax kodovi (0xD6A1-0xD6AB):
**PRONAĐENI u svim 1503 dumpovima** — iste adrese kao ACE 1630:
- U16A1 (0xD6A1) LE @ 0x0217D8 — identično kao ori_300 (10SW066726)
- U16A2 (0xD6A2) LE @ 0x0217C8, 0x0217D2
- Double storage: LE @ 0x0217XX i 0x021B3X — **potvrđuje DOUBLE storage**

### DTC storage type:
- **Double storage** (main + mirror) — iste adrese kao ACE 1630
- 0x0217XX = main storage, 0x021B3X = mirror storage
- Isti pattern u svim 1503 SW verzijama

### Sequential P-code sequences:
Isti pattern u svim 1503: @ 0x01422C, 0x014D42, 0x01520E, 0x01603C, 0x016D9C — ovo su CODE adrese (bytekod TriCore), ne DTC tablice.

---

## 7. Usporedba Dump-ova

### 2018: v1 vs v2 (10SW025022 vs 10SW025752)
- **31 diff chunkova (~2625B razlika)**
- Glavne diff regije:
  - `0x012C00-0x012CFF` (132B) — embedded cal (kalibracija @ 0x012C80 region)
  - `0x020021-0x020022` — SW string bajtovi (025022→025752 potvrđeno: `30 32` → `37 35`)
  - `0x026200-0x026C00` (673B) — **lambda/AFR tablice** — ovo je glavna promjena v1→v2
  - `0x024E00` (5B) — manje korekcije (RPM os?)
- **Zaključak**: v1→v2 razlika je uglavnom u lambda mapama (0x0262-0x026C = lambda+inj area), ostalo je minimalno

### 2018 vs 2019 (10SW025752 vs 10SW040008)
- **523 diff chunkova (~81.727B)** — potpuno novi SW
- Promjene kroz cijeli CODE, ne samo kalibracija

### 2018_230 vs 2019_230 (10SW025021 vs 10SW040008)
- **608 diff chunkova (~96.121B)** — još veća razlika

### 2019 vs 2020 (10SW040008 vs 10SW040962)
- **14 diff chunkova (~472B)** — mala razlika (zakrpa)
- Diff @ 0x012C00 (132B), 0x020000 (15B), 0x029400/0x029C00 — firmware + kalibracija

### Identičnost unutar iste SW generacije:
| Par | Razlika |
|-----|---------|
| 130v1 = 155v1 | **0B** (identični) |
| 130v2 = 155v2 | **0B** (identični) |
| 2019/130 = 2019/155 = 2019/230 | **0B** (svi identični) |

---

## 8. Ključni Zaključci

1. **Ignition**: Iste adrese kao ACE 1630 (0x02B730+, 144B stride, 12×12 u8, 0.75°/bit)
2. **Injection**: SAMO 0x022066 (GTI legacy format, nema mirrora) — ne 0x02436C
3. **Rev limiter**: Iste adrese kao ACE 1630; formula identična. 1503 130/155hp limit ~7892 RPM, 2018v1 ~7700 RPM
4. **DTC**: Double storage (main 0x0217XX + mirror 0x021BXX) — iste adrese kao ACE 1630
5. **U16Ax**: Postoje u svim 1503 SW varijantama na identičnim adresama kao ACE 1630
6. **HP razlike**: 130/155hp IDENTIČNI binarno. 230hp (SC) ima različite ign+inj mape
7. **2019 sve HP identične**: 10SW040008 je jedan SW za sve snage — logika razlike u cal (EEPROM?)
8. **v1→v2 razlika**: Lambda tablice @ 0x0262-0x026C + embedded cal 0x012C80

---

## 9. Neistraženo / TODO

- Tražiti pravu injection mapu za 1503 (ne na 0x02436C — tamo je nešto drugo za 1503)
- 0x022066 dimenzija: vjerojatno nije 16×12; trebalo bi provjeriti 8×12 ili 12×8
- SC bypass za 1503_230: postoji li @ 0x020534 kao u ACE 1630 SC?
- Lambda mapa za 1503: gdje je? Ne na 0x0266F0 (to je ACE 1630 adresa)
- Rev limiter formula za 4-cil: trebalo bi potvrditi točan RPM limit s tehničkim manualima
