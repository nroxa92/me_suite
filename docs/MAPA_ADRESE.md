# ME17Suite — Mapa Adresa i Definicija
> Generiran: 2026-03-17 | Automatski ažurirati pri svakoj potvrđenoj promjeni

---

## Sadržaj
1. [SW verzije i modeli](#sw-verzije)
2. [300hp mape (10SW066726)](#300hp-mape)
3. [Spark mape (1037544876)](#spark-mape)
4. [GTI SE 155 mape (10SW025752)](#gti-155-mape)
5. [DTC adrese i OFF procedure](#dtc-adrese)
6. [EEPROM struktura](#eeprom-struktura)
7. [Checksum](#checksum)

---

## SW verzije i modeli {#sw-verzije}

| SW ID | Model | Motor | Konjske snage | Godina | HW prefix | Napomena |
|-------|-------|-------|--------------|--------|-----------|----------|
| 10SW066726 | RXP-X 300 / GTX 300 / RXT-X 300 | Rotax 1630 SC | 300hp | 2016–2021 | 064 | **Primarna referenca** |
| 10SW082806 | RXP-X 300 (noviji) | Rotax 1630 SC | 300hp | 2022+ | 064 | backup_flash_082806.bin |
| 10SW040039 | NPRo Stage 2 300hp | Rotax 1630 SC | 300hp | 2020+ | 064 | Tuned SW |
| 10SW004672 | RXP-X 300 (stariji) | Rotax 1630 SC | 300hp | 2016–17 | 064 | rxpx300_16 |
| **10SW053727** | **GTI SE 230 / Wake Pro 230 2021** | **Rotax 1630 SC (1.6L)** | **230hp** | **2021** | 064 | SC motor, hard cut ~8158 rpm |
| **10SW053729** | **GTI SE 130 / GTI SE 170 2021** | **Rotax 1630 NA (1.6L)** | **130/170hp** | **2021** | 064 | NA motor, isti SW (0 binarnih razlika!), razlika = mehanička |
| **10SW053774** | **GTI SE 90 2021** | **Rotax 900 HO ACE** | **90hp** | **2021** | — | NA motor, hard cut ~7040 rpm |
| 10SW040013 | RXT 230 (2018) | Rotax 1630 SC | 230hp | 2018 | 064 | alen_flash_2026 |
| 10SW025752 | GTI SE 155 2018 | Rotax 1503 NA (1.5L) | 155hp | 2018 | 062 | NA motor, hard cut 7700 rpm |
| 1037544876 | Spark STG2 (NPRo) | Rotax 900 ACE | 90hp | 2018 | 063 | Samo DTC OFF, mape=ORI |
| 1037524060 | RXT-X 260 / RXP-X 260 | Rotax 1503 SC | 260hp | pre-2016 | — | 1.5L SC, drugačiji layout |
| 1037525897 | Spark/GTI (stariji) | Rotax 900 ACE | 90–130hp | 2014 | 062/063 | alen_spark_2014 |
| 1037525858 | Spark ORI / GTI SE 155 | Rotax 900/1503 | 90–155hp | 2017+ | 062/063 | MPEM ID |
| 1037509210 | GTI 130/155 (stariji) | Rotax 1503 NA | 130–155hp | 2015–16 | 062 | donor_10SW014510 |
| 10SW011328 | Spark ORI 2016 | Rotax 900 ACE | 90hp | 2016 | — | BOOT eraziran, fallback @ 0x02001A |

---

## 300hp mape (10SW066726) {#300hp-mape}
> Referentni fajl: `_materijali/ori_300.bin`
> CODE regija: 0x010000–0x05FFFF | CAL regija: 0x060000+ (read-only!)

### RPM Osi
| Adresa | Opis | Dimenzije | Format | Vrijednosti |
|--------|------|-----------|--------|-------------|
| 0x024F46 | RPM os 1 (globalna) | 1×16 | u16 BE | [512, 1024, ... 8192] korak 512 |
| 0x025010 | RPM os 2 (globalna) | 1×16 | u16 BE | [512, 1024, ... 8192] korak 512 |
| 0x0250DC | RPM os 3 (globalna) | 1×16 | u16 BE | [512, 1024, ... 8192] korak 512 |

### Paljenje (Ignition)
| Adresa | Naziv | Dimenzije | Format | Raspon | Napomena |
|--------|-------|-----------|--------|--------|----------|
| 0x02B730 | Paljenje — Osnovna 1 | 12×12 | u8 | 34–40 raw | ×0.75°/bit |
| 0x02B7C0 | Paljenje — Osnovna 2 | 12×12 | u8 | 34–45 raw | offset +0x90 |
| 0x02B850 | Paljenje — Osnovna 3 | 12×12 | u8 | 32–45 raw | |
| 0x02B8E0 | Paljenje — Osnovna 4 | 12×12 | u8 | 34–42 raw | |
| 0x02B970 | Paljenje — Osnovna 5 | 12×12 | u8 | 32–45 raw | |
| 0x02BA00 | Paljenje — Osnovna 6 | 12×12 | u8 | 34–40 raw | |
| 0x02BA90 | Paljenje — Osnovna 7 | 12×12 | u8 | 32–45 raw | |
| 0x02BB20 | Paljenje — Osnovna 8 | 12×12 | u8 | 34–40 raw | |
| 0x02BBB0 | Paljenje — Knock korekcija 1 | 12×12 | u8 | 0–227 raw | Delta format |
| 0x02BC40 | Paljenje — Knock korekcija 2 | 12×12 | u8 | 0–40 raw | Delta format |
| 0x02BCD0 | Paljenje — Pomoćna 1 | 12×12 | u8 | 34–40 raw | |
| 0x02BD60 | Paljenje — Pomoćna 2 | 12×12 | u8 | 32–45 raw | |
| 0x02BDF0 | Paljenje — Pomoćna 3 | 12×12 | u8 | 34–40 raw | |
| 0x02BE80 | Paljenje — Pomoćna 4 | 12×12 | u8 | 32–45 raw | |
| 0x02BF10 | Paljenje — Pomoćna 5 | 12×12 | u8 | 34–40 raw | |
| 0x02BFA0 | Paljenje — Pomoćna 6 | 12×12 | u8 | 34–45 raw | |
| 0x02C030 | Paljenje — Proširena 1 | 12×12 | u8 | 32–41 raw | |
| 0x02C0C0 | Paljenje — Proširena 2 | 12×12 | u8 | 34–44 raw | |
| 0x02C150 | Paljenje — Uvjetna | 12×12 | u8 | 0–45 raw | |
| 0x022374 | Paljenje — korekcija/efikasnost | 8×8 | u8 | 145–200 raw | STG2 cap=180 |

### Ubrizgavanje (Injection)
| Adresa | Naziv | Dimenzije | Format | Napomena |
|--------|-------|-----------|--------|----------|
| 0x02436C | Ubrizgavanje — rel. masa goriva (rk) | 6×32 | u16 LE Q15 | Osnovna mapa |
| 0x0244EC | Ubrizgavanje — mirror | 6×32 | u16 LE Q15 | Mirror = +0x180 |
| 0x025CDC | Start — gorivo pri pokretanju | 1×6 | u16 LE | os=[0,1024...7680] |
| 0x025CF6 | Start injection mirror | 1×6 | u16 LE | +0x1A offset |
| 0x028059 | Ubrzanje — tranzijentno obogaćivanje | 5×5 | Q14 | dTPS os ugrađena |

### Moment (Torque)
| Adresa | Naziv | Dimenzije | Format | Raspon |
|--------|-------|-----------|--------|--------|
| 0x02A0D8 | Moment — ograničenje | 16×16 | u16 BE Q8 | 119–153 MSB |
| 0x02A5F0 | Moment — ograničenje mirror | 16×16 | u16 BE Q8 | Mirror = +0x518 |
| 0x02A7F0 | Torque optimal / driver demand | 16×16 | u16 BE Q8 | 111–138 MSB |

### Lambda / AFR
| Adresa | Naziv | Dimenzije | Format | Raspon |
|--------|-------|-----------|--------|--------|
| 0x0266F0 | Lambda — ciljni AFR (open-loop) | 12×18 | u16 LE Q15 | 0.965–1.073 λ |
| 0x026C08 | Lambda mirror | 12×18 | u16 LE Q15 | Mirror = +0x518 |
| 0x02469C | Lambda zaštita — max ubrizgavanje | 12×13 | u16 LE Q15 | 0.040–1.800 |
| 0x026DB8 | Lambda trim — korekcija po RPM×load | 12×18 | u16 LE Q15 | 0.956–1.021 λ |
| 0x02AE5E | Lambda efikasnost (KFWIRKBA) | 41×18 | u16 LE Q15 | 0.000–1.997 |
| 0x0265D6 | Lambda bias — AFR korekcija | 1×141 | u16 LE Q15 | avg λ=1.023 |

### SC Bypass (samo 300hp / SC modeli)
| Adresa | Naziv | Dimenzije | Format | Napomena |
|--------|-------|-----------|--------|----------|
| 0x020534 | SC bypass ventil — shadow kopija | 7×7 | u8 | NPRo NE mijenja! |
| 0x0205A8 | SC bypass ventil — aktivna | 7×7 | u8 | NPRo mijenja (38–255) |
| 0x029993 | SC bypass ventil — extra | 7×7 | u8 | NPRo mijenja drugačije |
| 0x025DF8 | SC bazno obogaćivanje po λ | 1×40 | u16 LE Q14 | +22.4% default |

### Temperaturne korekcije
| Adresa | Naziv | Dimenzije | Format | Raspon |
|--------|-------|-----------|--------|--------|
| 0x02586A | Cold start — bogaćenje | 1×6 | u16 LE | 500–1690 raw |
| 0x025E50 | CTS warm-up korekcija | 1×156 | u16 LE Q14 | 72–121% |
| 0x02AA42 | Toplinsko obogaćivanje (visoka CTS temp) | 8×7 | u16 LE Q6 | 168–210% |
| 0x02AA02 | Therm enrich X-os | 1×7 | u16 LE | [6400..16000] load |
| 0x025900 | Injektori — deadtime | 14×7 | u16 LE | 1024–2989 raw (read-only) |

### Rev Limiter
| Adresa | Naziv | Format | 300/230hp | 130/170hp 2021 | GTI 155 2018 | Napomena |
|--------|-------|--------|-----------|----------------|--------------|----------|
| 0x028E90–0x028E94 | Rev cut ramp [0–2] | u16 LE period | 3506–4589 | 4915–5112 | 4981–5243 | Ramp-down periodi |
| **0x028E96** | **Rev limiter — hard cut** | u16 LE period | **5072 = 8158 rpm** | **5243 = 7892 rpm** | **5374 = 7700 rpm** | ✅ Potvrđeno |
| 0x028E98 | Rev limiter — soft cut | u16 LE period | 5399 = 7664 rpm | 5374 = 7700 rpm | 5505 = 7517 rpm | Resume threshold |

> **Formula dekodiraj**: `RPM = 40,000,000 / (ticks × 58/60)` — 60-2 kotačić (58 eff. zubi), 3-cil. Rotax
> ✅ Potvrđeno za: **10SW066726** (8158), **10SW053727/053729** (7892/8158), **10SW025752** (7700)
> ⚠️ **10SW053774 (GTI 90)** ima drugačiju strukturu — hard cut je na **0x028E7C** (5875 = 7043 rpm)!
> ❌ **0x02B72A** (stara dokumentacija) je ASCII filler (0x2222 = `""`, 0x2121 = `!!`) — NIJE rev limiter!

### Ostale mape
| Adresa | Naziv | Dimenzije | Format | Raspon |
|--------|-------|-----------|--------|--------|
| 0x02220E | SC boost — korekcija goriva | 9×7 | u16 LE Q14 | 32–219% |
| 0x02202E | DFCO — pragovi isključivanja goriva | 1×7 | u16 LE | 1067–3413 rpm |
| 0x02B600 | Ralanti — ciljni RPM | 5×12 | u16 LE | 1960–3340 rpm |
| 0x0256F8 | Knock — parametri praga detekcije | 1×24 | u16 LE | razni |
| 0x025896 | CTS — temperaturna os | 1×10 | i16 LE | 37–157°C |
| 0x025ADA | Overtemp lambda (SC bypass) | 1×63 | u16 LE | 0xFFFF (SC bypass) |
| 0x025B58 | Neutral korekcija | 1×63 | u16 LE Q14 | 1.004 flat |
| 0x0259D2 | Lambda efikasnost — Q15 2D | 10×7 | u16 LE Q15 | TODO fizikalni smisao |

---

## Spark mape (1037544876) {#spark-mape}
> Referentni fajl: `_materijali/npro_stg2_spark.bin` (mape = ORI, samo DTC promijenjen)
> Motor: 900 ACE, 3 cilindra, bez SC, max ~8500 rpm

| Adresa | Naziv | Dimenzije | Format | Raspon | Status |
|--------|-------|-----------|--------|--------|--------|
| 0x021748 | RPM os 1 | 1×15 | u16 LE | [853..7400] rpm | ✅ Potvrđeno |
| 0x0276A5 | Paljenje — Primarna (PRAVI!) | 12×12 | u8 | 10–89 raw (7.5°–66.8°) | ✅ Potvrđeno (neporavnata adr.!) |
| 0x02778D | Paljenje — Sekundarna 2 | 12×12 | u8 | 12–89 raw (9.0°–66.8°) | ✅ +0xE8 od primarne |
| 0x0247D3 | Paljenje — Treća | 12×12 | u8 | 45–95 raw (33.8°–71.2°) | ✅ Neporavnata adresa |
| 0x024810 | Paljenje — Četvrta | 12×12 | u8 | 45–68 raw (33.8°–51.0°) | ✅ Bila smatrana primarnom |
| 0x029643 | Paljenje — Knock korekcija | 12×12 | u8 | 27–43 raw (20°–32°) | ✅ +3 kopije (+0x90 stride) |
| 0x0224DC | Injection — osnovna mapa | 10×32 | u16 LE | raw=1646–4249, avg=2912 | ✅ Potvrđeno (čiste fuel vrijednosti) |
| 0x022A54 | Injection — mirror | 10×32 | u16 LE | raw=1646–4249, avg=2912 | ✅ Mirror (+0x518) |
| 0x02225C | Injection — širi blok (s osima) | 12×32 | u16 LE | raw=479–33600 | 🔍 Uključuje RPM osi |
| 0x025F5C | Lambda/AFR — kopija 1 | 8×16 | u16 LE Q15 | λ=0.737–1.004 | 🔍 Kandidat |
| 0x02607E | Lambda/AFR — kopija 2 | 8×16 | u16 LE Q15 | λ=0.737–1.004 | 🔍 Mirror (+0x122) |
| 0x0261A0 | Lambda/AFR — kopija 3 | 8×16 | u16 LE Q15 | λ=0.737–1.004 | 🔍 Mirror (+0x244) |
| 0x0262C2 | Lambda/AFR — kopija 4 | 8×16 | u16 LE Q15 | λ=0.737–1.004 | 🔍 Mirror (+0x366) |
| 0x022D58 | Rev limiter kandidat | skalar | u16 LE | 7700 rpm | 🔍 Kandidat (izolirani skalar) |
| 0x021C06 | Rev limiter soft limit | skalar | u16 LE | 8500 rpm | 🔍 Kandidat |
| — | Torque | — | — | — | 🔍 TODO |

---

## GTI SE 155 mape (10SW025752) {#gti-155-mape}
> Referentni fajl: `_materijali/gti_155_18_10SW025752.bin`
> Motor: Rotax 1503/1504 1.5L, atmosferski, 155hp, **hard cut @ 7700 RPM**

### GTI-specifične mape (DRUGAČIJE od 300hp)
| Adresa | Naziv | Dimenzije | Format | Napomena |
|--------|-------|-----------|--------|----------|
| **0x022066** | **GTI — ubrizgavanje (direktno)** | **16×12** | u16 LE raw | ✅ Direktne vrijednosti, NE Q15! Range ~3193–14432 |
| 0x028310 | GTI Paljenje — OS 1 (low load) | 12×12 | u8 | ✅ Stride 0x90 (144B) od ove adrese |
| 0x0283A0 | GTI Paljenje — OS 2 (mid load) | 12×12 | u8 | ✅ |
| 0x028430 | GTI Paljenje — OS 3 (high load) | 12×12 | u8 | ✅ |
| 0x0284C0 | GTI Paljenje — OS 4 | 12×12 | u8 | ✅ |
| 0x028550 | GTI Paljenje — OS 5 | 12×12 | u8 | ✅ |
| 0x0285E0 | GTI Paljenje — OS 6 | 12×12 | u8 | ✅ |
| 0x028670 | GTI Paljenje — OS 7 | 12×12 | u8 | ✅ |
| 0x028700 | GTI Paljenje — OS 8 | 12×12 | u8 | ✅ (ukupno 8 GTI-specifičnih mapa) |

### GTI mape dijeljene s 300hp (iste adrese, drugačije vrijednosti)
| Adresa | Naziv | Dimenzije | Format | Napomena |
|--------|-------|-----------|--------|----------|
| 0x024F46 | RPM os 1 | 1×16 | u16 BE | ✅ Identično 300hp ([512..8448]) |
| 0x025010 | RPM os 2 | 1×16 | u16 BE | ✅ Identično 300hp |
| 0x0250DC | RPM os 3 | 1×16 | u16 BE | ✅ Identično 300hp |
| 0x02436C | Ubrizgavanje — rel. masa goriva (rk) | 6×32 | u16 LE Q15 | Dijeli se s 300hp, ali GTI ima vlastiti @ 0x022066 |
| 0x0266F0 | Lambda — ciljni AFR | 12×18 | u16 LE Q15 | Iste adrese, vrijednosti skalirane za 1.5L |
| 0x02A0D8 | Moment — ograničenje | 16×16 | u16 BE Q8 | ✅ GTI = flat 32768 (1.0×, NA motor, nema SC!) |
| 0x02B730 | Paljenje — Osnovna 1 (dijeljeno) | 12×12 | u8 | Prisutno u GTI, ali GTI koristi 0x028310 seriju |
| 0x02202E | DFCO limit | 1×7 | u16 LE | GTI max = 6000 rpm (vs 300hp 7000) |

### GTI Rev Limiter
| Adresa | Format | GTI vrijednost | Dekodirana RPM |
|--------|--------|----------------|----------------|
| **0x028E96** | u16 LE period | **5374** | **7700 RPM** (hard cut) |
| 0x028E98 | u16 LE period | 5505 | 7517 RPM (soft cut / resume) |

> ⚠️ GTI injection je na **0x022066** (16×12 direktni raw), NE identično 300hp @ 0x02436C!
> ⚠️ GTI extra ignition mape su na **0x028310** (8 mapa, stride 144B), a adresa 0x02B730 (dijeljena s 300hp) je **fill vrijednost** specifično za GTI high-load range
> ⚠️ GTI 155 je **NA motor** (nema SC) — SC bypass mape (0x020534, 0x029993) prisutne ali neaktivne
> ⚠️ **Iste adrese vrijede za GTI SE 90 2021 (10SW053774)** — isti GTI/NA format, drugačiji tune

---

## GTI SE 90 2021 mape (10SW053774) {#gti90-mape}
> Referentni fajl: `_materijali/dumps/2021/gti 90 2021.bin`
> Motor: Rotax 900 HO ACE, 3 cilindra, NA (bez SC), ~90hp

### GTI 90 — ključne razlike od GTI 155 (10SW025752)
| Adresa | Naziv | GTI 90 vrijednost | GTI 155 vrijednost | Napomena |
|--------|-------|-------------------|---------------------|----------|
| 0x022066 | Injection — primarni | [5284, 5124, 4780...] | [6351, 5768, 5348...] | 16×12 raw, GTI format |
| 0x028310–0x028700 | Ignition (8 mapa) | prisutne | prisutne | isti format 12×12 u8 |
| 0x025DF8 | SC boost factor | 13364 (−18.4%) | 20046 (+22.4%) | NA motor = negativna vrijednost |

### GTI 90 Rev Limiter
| Adresa | Format | Vrijednost | Dekodirana RPM | Status |
|--------|--------|------------|----------------|--------|
| **0x028E68** | u16 LE period | **5883** | **~7034 RPM** | Probable hard cut (blok A) |
| **0x028E7C** | u16 LE period | **5875** | **~7043 RPM** | Probable hard cut (blok B) |

> ⚠️ GTI 90 ima **drugačiji rev limiter raspored** od GTI 155/300hp!
> Adresa 0x028E96 za GTI 90 = 3277 ticks (~12627 rpm) — potpuno pogrešna za rev limiter.
> Dva bloka s gotovo identičnim završnim peridom (~5880 ≈ 7040 RPM) pronađena na 0x028E60 i 0x028E70.
> Hard cut ~7040 RPM je **procjena** — nije potvrđeno live testom ili tune usporedbom.

---

## DTC adrese i OFF procedure {#dtc-adrese}

### 300hp (SW 10SW066726 = ori_300) i (SW 10SW040039 = rxpx300_17)

```
Enable tablica:  @ 0x021080 (62 bajta)
DTC base:        @ 0x0217B6 (111 kodova × 2B)
Mirror offset:   0x0366 (DTC base mirror = 0x0217B6 + 0x0366 = 0x021B1C)
```

**P1550** (Oil Pressure Sensor):
- Enable bytes @ 0x02108A (slots 10–19, 10 bajta, sve 0x06 = enabled)
- **OFF**: nulirati sve 10 bajta na 0x00

**P0523** (Oil Pressure Switch):
- Enable bytes @ 0x02108E (slots 14–24, 11 bajta, razne vrijednosti)
- **OFF**: nulirati sve 11 bajta na 0x00

### Spark (SW 1037544876)

```
Arhitektura DRUGAČIJA od 300hp — single-storage, bez mirrora
P1550 enable:    @ 0x0207A5 (1 bajt, 0x06 = enabled → 0x00 = OFF)
P1550 state:     @ 0x020E5E (u16 LE, 0x0000 → 0xFFFF za OFF)
```

⚠️ **UPOZORENJE**: `dtc_off()` je blokiran za Spark u kodu (single_storage=True) — ne koristiti!

### RXT 230 / Wake Pro 230 (SW 10SW053727)

```
P0523 enable:    provjeri DTC scanner — SW detektira automatski
```

### DTC Kodovi (111 ukupno za 300hp)
Kompletna lista u `core/dtc.py` — DTC_REGISTRY dict, 111 P-kodova.

Ključni za tuning:
- **P1550** — Oil Pressure Sensor Circuit Low (najčešće isključivan)
- **P0523** — Oil Pressure Sensor Circuit High
- **P0116** — Engine Coolant Temperature Sensor Range
- **P0562** — System Voltage Low

---

## EEPROM struktura {#eeprom-struktura}
> Veličina: 32KB (32,768 bajta) | Parser: `core/eeprom.py`

### Fiksni offseti (potvrđeno na 3 uzorka)

| Offset | Naziv | Format | Primjer |
|--------|-------|--------|---------|
| 0x0013 | Datum prvog programiranja | ASCII 8B "DD-MM-YY" | "04-05-21" |
| 0x001E | Datum zadnjeg ažuriranja | ASCII 8B "DD-MM-YY" | "07-05-21" |
| 0x0032 | MPEM SW ID | ASCII 10B | "1037550003" |
| 0x0040 | Servisni SW ID | ASCII 10B | "1037500313" (uvijek) |
| 0x004C | Broj programiranja | u8 | 1 ili 2 |
| 0x004D | ECU serijski broj | ASCII 11B | "SF00HM00196" |
| 0x0082 | Hull ID / VIN | ASCII 12B | "YDV89660E121" |
| 0x0102 | Dealer naziv | ASCII 16B | "SEA-DOO" |
| 0x0125 | Neidentificirano (SW konstanta?) | ASCII 5B | "60620"/"BRP10"/0x00 — NIJE hw timer! |

### Promjenjivi odometar (circular buffer, BUDS2 promjenjiv)
- Format: u16 LE, vrijednost u **minutama** od prvog pokretanja
- Adresa: varijabilna (circular buffer s anchor slotom @ 0x0550)
- Slot format: 20B, ODO vrijednost @ slot_start+16 i slot_start+18 (u16 LE)

| HW tip | Primarna adresa | Fallback 1 | Fallback 2 | Napomena |
|--------|-----------------|------------|------------|----------|
| **064** (300hp, GTI SE, 230hp) | **0x0562** | 0x0D62 | 0x1562 | 064 = MPEM "1037550003" |
| **063** (Spark 90/115hp) | **0x0562** | 0x0DE2 | — | 063 = MPEM "1037525858" |
| **062** (GTI 130/155, RXT 1.5L stari) | **0x5062** | 0x4562 | 0x1062 | 062 = MPEM "1037509210" |

> Implementirano u `core/eeprom.py` — `EepromParser.parse()` automatski detektira HW tip iz MPEM SW prefiksa.
> EEPROM widget u GUI prikazuje hw_type i preračunate HH:MM radne sate.

### MPEM ID → HW tip
| MPEM SW | HW folder | Motor |
|---------|-----------|-------|
| 1037550003 | 064 | 300hp / 230hp (1.6L SC i turbo) |
| 1037525858 | 063/062 | Spark 90hp / GTI SE 155 (1.5L) |
| 1037509210 | 062 | GTI 130/155 stariji (2015-16) |
| 1037525897 | 062/063 | Spark/GTI stariji (2014) |
| 1037504475 | 061 | Nepoznat (2013?) |

---

## Checksum {#checksum}

```
Algoritam:  CRC32-HDLC (poly=0xEDB88320 reflected, init=0xFFFFFFFF, xorout=0xFFFFFFFF)
Regija:     BOOT [0x0000, 0x7F00) = 0x7F00 bajta
Lokacija:   @ 0x0030 (u32 LE, uključen u izračun)
Residua:    0x6E23044F (fiksna za sve validne fajlove)

ori_300 CS:    0xE505BC0B
STG2 CS:       0x9FC76FAD
```

**Važno**: Promjena mapa u CODE regiji (0x010000–0x05FFFF) **NE zahtijeva** promjenu checksuma!
Checksum se mijenja samo ako se mijenja BOOT kod (0x0000–0x7EFF).

---

## Fizikalne jedinice i konverzije

| Format | Konverzija | Primjer |
|--------|-----------|---------|
| u8 ignition | × 0.75° = °BTDC | raw=40 → 30.0° BTDC |
| u16 BE Q8 | ÷ 256 = % (torque) | 38400 = 150% |
| u16 LE Q14 | ÷ 16384 = faktor | 16384 = 1.000 (100%) |
| u16 LE Q15 | ÷ 32768 = faktor | 32768 = 1.000 (λ=1.000) |
| RPM os | raw = RPM | 8192 = 8192 rpm |
| CTS temp | raw = °C (signed i16) | 80 = 80°C |

---

*Posljednje ažuriranje: 2026-03-18*
*Generiran automatski iz core/map_finder.py i binarnih analiza*
