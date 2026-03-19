# SW Versions — Bosch ME17.8.5 Sea-Doo / Rotax

> *Revidirano: 2026-03-18*

**Last updated:** 2026-03-18
**Source:** `core/engine.py` (KNOWN_SW), `work_log.md`, binary analysis

---

## 1. Classification Overview

| Class | Engine | HP | SW IDs |
|-------|--------|----|--------|
| Rotax 1630 SC | 1630cc, 3-cyl, supercharged | 230 / 300 hp | 10SW066726, 10SW054296, 10SW053727, 10SW040039, 10SW082806, 10SW004672 |
| Rotax 1630 NA | 1630cc, 3-cyl, naturally aspirated | 130 / 170 hp | 10SW053729 |
| Rotax 1503 NA | 1503cc, 3-cyl, naturally aspirated | 155 / 130 hp | 10SW025752, 10SW040008, 10SW040962 |
| Rotax 900 HO ACE | 899cc, 3-cyl, naturally aspirated | 90 hp | 10SW053774 |
| Rotax 900 ACE | 899cc, 3-cyl, naturally aspirated | 90 hp | 10SW039116, 10SW011328, 1037544876 |

---

## 2. All Known SW Versions

### Rotax 1630 SC (Sea-Doo 300hp / 230hp)

| SW ID | Description | Vehicles | Notes |
|-------|-------------|----------|-------|
| **10SW066726** | ORI baseline 300hp SC (2016–2021) | RXP-X 300, RXT-X 300, GTX 300 | **Primary reference binary** |
| **10SW054296** | 300hp SC 2020 ORI | RXP/RXT/GTX 300, 2020 model | Confirmed: `dumps/2020/1630ace/300.bin` |
| **10SW082806** | 300hp SC variant (newer) | RXP-X 300 (2022+?) | `_materijali/backup_flash_082806.bin`, 11462 changed regions vs ori_300 |
| **10SW004672** | 300hp SC (2016) | RXP-X 300 / RXT-X 300 | Older variant |
| **10SW040039** | 2019 stock / NPRo baseline 300hp | RXP-X 300 (tuned) | SW string nije promijenjen u NPRo tunu — isti SW ID. CODE diff vs ori_300: 7087B (2021) / 6038B (2020) |
| **10SW053727** | GTI SE 230 / Wake Pro 230 (2021) | GTI SE 230, Wake Pro 230 | SC motor, hard cut ~8158 RPM |

### Rotax 1630 NA (Sea-Doo 130hp / 170hp)

| SW ID | Description | Vehicles | Notes |
|-------|-------------|----------|-------|
| **10SW053729** | GTI SE 130 / GTI SE 170 (2020–2021) | GTI SE 130hp, GTI SE 170hp | **SAME binary for both 130 and 170hp** — difference is mechanical (impeller/load) |

> **130hp vs 170hp paradox:** Identical ECU binary, identical valve timing — power difference likely from different impeller or drivetrain loading, not the ECU.

### Rotax 1503 NA (Sea-Doo GTI 155 / 130)

| SW ID | Description | Vehicles | Notes |
|-------|-------------|----------|-------|
| **10SW025752** | GTI SE 155 2018 | GTI SE 155 | Primary 1503 reference. Hard cut **7700 RPM** (5374 ticks) |
| **10SW040008** | GTI/GTS 130/155/230hp 1503 NA 2019 | GTI SE 130/155, GTS 130/230 | **IDENTIČNI BINARIJI za 130, 155 i 230hp (0 razlika!)** Hard cut **7892 RPM** |
| **10SW040962** | GTI/GTS 130hp 1503 NA 2020 | GTI SE 130 2020 | Hard cut **7892 RPM**. Iste mape kao 10SW040008, 536B razlika u parametrima |

> **2026-03-19**: Potvrđeno binarnim skanom da su 10SW040008 varijante (130/155/230hp) apsolutno identični binariji. Razlika u snazi je isključivo mehanička.

### Rotax 900 HO ACE (GTI SE 90)

| SW ID | Description | Vehicles | Notes |
|-------|-------------|----------|-------|
| **10SW053774** | GTI SE 90 2020–2021 | GTI SE 90, GTS 90 | Same SW for 2020 and 2021 (only 80B hash block differs) |

### Rotax 900 ACE (Spark 90)

| SW ID | Description | Vehicles | Notes |
|-------|-------------|----------|-------|
| **10SW039116** | Spark 90 2019–2021 | Sea-Doo Spark 90hp | **Same binary for 2019, 2020, 2021** |
| **10SW011328** | Spark 90 2016 | Sea-Doo Spark 90hp (2016) | **Completely different CODE layout** from 10SW039116 (622,954 bytes diff) |
| **1037544876** | NPRo Spark Stage 2 | Spark 90hp (tuned) | Decimal BUDS2 format SW ID. Based on 10SW039116 + 6145B CODE changes |

---

## 3. Dumps Available

### Directory structure: `dumps/YYYY/{1630ace,900ace,4tec1503}/`

| Path | SW ID | Description |
|------|-------|-------------|
| `dumps/2021/1630ace/300.bin` | 10SW066726 | 300hp ORI 2021 |
| `dumps/2021/1630ace/230.bin` | 10SW053727 | 230hp ORI 2021 |
| `dumps/2021/1630ace/170.bin` | 10SW053729 | 170hp ORI 2021 |
| `dumps/2021/1630ace/130.bin` | 10SW053729 | 130hp ORI 2021 (identical binary to 170hp) |
| `dumps/2021/900ace/gti90.bin` | 10SW053774 | GTI SE 90 ORI 2021 |
| `dumps/2021/900ace/spark90.bin` | 10SW039116 | Spark 90 ORI 2021 |
| `dumps/2020/1630ace/300.bin` | 10SW054296 | 300hp ORI 2020 |
| `dumps/2020/1630ace/300_stg2` | 10SW040039 | NPRo STG2 (no extension, data file) |
| `dumps/2020/1630ace/130.bin` | 10SW053729 | 130hp ORI 2020 |
| `dumps/2020/900ace/gti90.bin` | 10SW053774 | GTI SE 90 ORI 2020 |
| `dumps/2020/900ace/spark90.bin` | 10SW039116 | Spark 90 ORI 2020 (identical to 2021) |
| `dumps/2019/1630ace/300.bin` | 10SW040039 | 300hp ORI 2019 |
| `dumps/2019/900ace/spark90.bin` | 10SW039116 | Spark 90 ORI 2019 (identical to 2020/2021) |
| `dumps/2018/900ace/spark90.bin` | 10SW011328 | Spark 90 2018 ORI (different layout from 2019+) |
| `dumps/2018/900ace/spark_stg2` | 1037544876 | NPRo Spark STG2 |

---

## 4. Confirmed ORI/STG2 Pairs

| ORI file | ORI SW | STG2 file | STG2 SW | CODE diff |
|----------|--------|-----------|---------|-----------|
| `dumps/2021/1630ace/300.bin` | 10SW066726 | `dumps/2020/1630ace/300_stg2` | 10SW040039 | **7087B** |
| `dumps/2020/1630ace/300.bin` | 10SW054296 | `dumps/2020/1630ace/300_stg2` | 10SW040039 | **6038B** |
| `dumps/2018/900ace/spark90.bin` | 10SW011328 | `dumps/2018/900ace/spark_stg2` | 1037544876 | **3065B** |

---

## 5. Binary Differences Between Years

### 230hp: 2020 vs 2021
- SW ID: same (10SW053727)
- CODE diff: ~80B on 2 blocks (0x017F02–0x017F48 and 0x017F5C–0x017F74)
- Maps: **100% identical** — only likely difference is build timestamp
- Practically: 2020 and 2021 230hp are interchangeable for tuning purposes

### GTI SE 90: 2020 vs 2021
- SW ID: same (10SW053774)
- CODE diff: ~80B in hash block @ 0x017F02
- Maps: 100% identical

### Spark 90: 2018 vs 2019/2020/2021
- 2018 (10SW011328) vs 2019+ (10SW039116): **622,954 bytes different** — completely different CODE layout
- All maps at different addresses
- 2019/2020/2021 are truly identical binaries

---

## 6. HW Type Classification

| HW Type | MPEM SW Prefix | Vehicles |
|---------|---------------|----------|
| **064** | 10375500xxx | 300hp SC, 230hp SC (Rotax 1630 SC) |
| **063** | 10375258xx | Spark 90/115hp, GTI SE 155 (1.5L NA) |
| **062** | 10375091xx / 10375092xx | GTI 130/155 older (2015–16), RXT-X 260 |

> **Napomena:** HW 063 = i Spark i GTI SE 155 koriste ISTI MPEM prefiks, ali imaju RAZLIČITU DTC arhitekturu (Spark = single-storage, GTI155 = main+mirror).

HW type affects:
1. EEPROM ODO circular buffer addresses (see EEPROM_GUIDE.md)
2. DTC architecture (064 = main+mirror, 063 = single-storage in Spark variants)
3. Ignition map layout (GTI155 has 8 extra maps @ 0x028310)

---

## 7. Unsupported SW Versions

| SW / MPEM | Engine | Reason |
|-----------|--------|--------|
| 1037524060 (rxtx_260) | Rotax 1503/1504 SC 260hp | Pre-2016, different CODE layout, DTC single-storage |
| 1037504475 | Unknown (2013?) | Not analyzed |
| Rotax 1504 SC 260hp | 1.5L SC | Pre-2016, completely different binary structure |

> **Napomena o 10SW011328 (Spark 2016/2018):** Ovaj SW JE podržan u map_finder.py i prisutan u KNOWN_SW. Ima drugačiji CODE layout od 10SW039116 (2019+) — 622,954B razlika — ali adrese mapa su mapirane za oba layout-a.

---

## 8. SW Gating in map_finder.py

```python
# 300hp SC variants (map addresses for Rotax 1630 SC layout):
_300HP_SW_IDS = {"10SW066726", "10SW054296", "10SW082806", "10SW040039",
                 "10SW004672", "10SW053727"}

# GTI/NA variants (1630 NA, 900 HO, 1503 NA):
_GTI_NA_SW_IDS = {"10SW053774", "10SW053729", "10SW025752",
                  "10SW040008", "10SW040962"}

# Spark (900 ACE) — different addresses from 2019+:
_SPARK_10SW_IDS = {"10SW039116", "1037544876", "10SW011328"}
```

Maps are selected based on detected SW ID — wrong SW = wrong addresses = corrupted data.
