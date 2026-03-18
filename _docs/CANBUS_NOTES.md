# CAN Bus Notes — Bosch ME17.8.5 / Sea-Doo

> *Revidirano: 2026-03-18*

**Last updated:** 2026-03-18
**Source:** `docs/CAN_SAT_PORUKE.md` (consolidated), binary analysis of 5 ECU files

---

## 1. Protocol Overview

BRP Sea-Doo uses a **proprietary CAN protocol**:
- Speed: **250 kbps**
- Frame format: Standard 11-bit IDs
- ECU: Bosch ME17.8.5 (TC1762 TriCore)
- Display/Gauge: SAT (Systeme d'Affichage et de Tableau bord = instrument cluster/dashboard)

**Confirmed compatibility:** 300hp Sea-Doo ECU works with Spark SAT — the protocol is hardware-compatible across models. Minor CAN ID differences exist but do not prevent basic functionality.

---

## 2. CAN ID Tables in Binary

CAN message ID tables found in CODE region (Big-Endian u16 array, null-terminated):

| ECU variant | Address in binary |
|-------------|------------------|
| Spark (10SW039116) | 0x042EC4 |
| GTI / 230hp / 300hp | 0x0433BC |

---

## 3. CAN Message IDs by ECU Type

### Spark ECU (10SW039116):
```
0x015B  0x0154  0x0134  0x013C  0x015C  0x0138
0x0108  0x0214  0x012C  0x0110  0x0108  0x017C
```

### GTI / 230hp / 300hp ECU (10SW053774 / 10SW053727 / 10SW066726):
```
0x015B  0x015C  0x0148  0x013C  0x015C  0x0138
0x0108  0x0214  0x012C  0x0110  0x0108  0x017C
```

> GTI90 / 230hp / 300hp are IDENTICAL in this table.

---

## 4. CAN ID Differences: Spark vs GTI/230/300hp

### IDs present ONLY in Spark:
| CAN ID | Decimal | Notes |
|--------|---------|-------|
| `0x0134` | 308 | Spark-specific signal |
| `0x0154` | 340 | Spark-specific signal |

### IDs present ONLY in GTI/230/300hp:
| CAN ID | Decimal | Notes |
|--------|---------|-------|
| `0x0148` | 328 | GTI/230/300-specific signal |

### Common IDs (present in BOTH):
| CAN ID | Decimal |
|--------|---------|
| `0x0108` | 264 |
| `0x0110` | 272 |
| `0x012C` | 300 |
| `0x0138` | 312 |
| `0x013C` | 316 |
| `0x015B` | 347 |
| `0x015C` | 348 |
| `0x017C` | 380 |
| `0x0214` | 532 |

---

## 5. Extra CAN Messages (GTI/230/300 Only)

Found in config table @ `0x010470` (GTI/230/300 ECU) — 3 extra 4-byte entries not in Spark:

| Bytes 0–1 (CAN ID LE) | CAN ID | Byte 2 | Byte 3 | Notes |
|----------------------|--------|--------|--------|-------|
| `CD 00` | 0x00CD (205) | 0x01 | 0xFF | GTI/230/300 only |
| `DC 00` | 0x00DC (220) | 0x01 | 0xFF | GTI/230/300 only |
| `BF 00` | 0x00BF (191) | 0x01 | 0xFF | GTI/230/300 only |

> Byte 2 = likely DLC or signal count (value 1)
> Byte 3 = 0xFF likely means "enabled/active"

### Shared table (present in both Spark AND GTI):
| Format | Likely CAN ID (BE) | Byte 2 | Notes |
|--------|-------------------|--------|-------|
| `02 1F 06 00` | 0x021F (543) | 6 | Shared message |
| `02 25 06 00` | 0x0225 (549) | 6 | Shared message |
| `02 2B 06 00` | 0x022B (555) | 6 | Shared message |

---

## 6. Spark SAT on 230/260hp — Compatibility Analysis

### What works without modification:
- All **9 common CAN IDs** (0x108–0x214) are identical — these display RPM, temperature, operating hours, etc.
- 300hp ECU + Spark SAT = confirmed working → 230hp uses **same CAN ID set** as 300hp → **should work**

### Potential issues:
- Spark SAT may send/receive on 0x0134 and 0x0154 — these IDs **do not exist** in 230hp ECU
  → Corresponding displays may show 0 or blank on Spark SAT
- 230hp ECU sends on 0x0148 and has 3 extra messages (0xBF/0xCD/0xDC) — Spark SAT ignores unknown IDs without errors

### Recommendation:
1. **Plug-and-play test:** Directly connect Spark SAT to 230hp/260hp (same CAN pin-out on Sea-Doo)
2. If something doesn't display, identify which CAN ID is missing with a CAN sniffer (SavvyCAN, etc.)
3. Possible ECU patch: change 0x0148→0x0134 and 0x015C→0x0154 (2-byte swap in CODE table) — **not recommended without testing**

---

## 7. Quick Reference — CAN IDs by ECU Type

```
Spark ECU:      108 110 12C 138 13C 15B 15C 17C 214  +  134 154
GTI/230/300:    108 110 12C 138 13C 15B 15C 17C 214  +  148 (2×15C)
                                                          +  BF  CD  DC
```

---

## 8. Analysis Methodology

- Binary analysis of 5 ECU files: 10SW039116, 10SW053774, 10SW053727, 10SW066726
- CAN ID table found in CODE region (Big-Endian u16 array, null-terminator)
- Cross-referenced Spark vs non-Spark binaries
- **Note:** TX/RX direction is not explicitly encoded in the table — assumption that these are ECU→SAT messages based on 300hp+Spark SAT working without ECU adaptation
- **For 100% confirmation:** CAN sniffing on live vehicle (250 kbps, standard 11-bit)

---

## 9. CAN Payload Formats (potvrđeno iz ECU CODE)

Payload formati verifirani binarnom analizom ECU flash-a (CODE region). Implementirano u `core/can_decoder.py`.

| CAN ID | Signal | Payload format | Period (GTI/300hp) | Period (Spark) |
|--------|--------|----------------|-------------------|----------------|
| **0x0108** | RPM | byte[1:3] u16 BE × 0.25 = RPM | 16–18 ms | 16 ms |
| **0x0110** | Coolant temp | byte[1] − 40 = °C | 131–147 ms | 131 ms |
| **0x012C** | Engine hours | byte[0:4] u32 BE (seconds) ÷ 3600 = hours | 196–223 ms | 196 ms |
| **0x017C** | DTC | byte[0] = active DTC count | — | — |
| **0x013C** | Engine status flags | byte[0] bitmask | — | — |

### CAN descriptor structure (@ CODE 0x0173C0):
```
5A <opcode> <idx> <CAN_ID BE u16> <0xFFFF> <checksum>
```

### Timing tables in binary:
- GTI/300hp: `(table_addr − 14)` → LE u16 ms periods per ID position
- Spark: similar layout, ~2ms faster periods

---

## 10. SAT Firmware Analysis

**SAT dumpovi** (Spark SAT, GTI-X SAT, GTI SAT variant):
- Veličine: Spark + GTI = 325,696B, GTI-X = 324,672B
- **Entropy: ~7.997 bits/byte** → firmware je enkriptiran (ili komprimiran)
- Header pattern identičan u sva 3 dumpa — bytes[10:11] se razlikuju (vjerojatno SW revision)
- Spark SAT i GTI SAT imaju identičan kraj (isti base firmware) — GTI-X je drugačiji

> **Zaključak: SAT firmware je enkriptiran. Direktna binarna analiza CAN ID-ova iz SAT dumpa NIJE MOGUĆA.**

---

## 11. "Nepoznati epprom" — Identifikacija

Taj fajl (2MB) je **ECU EEPROM backup za RXT-X 260**:
- SW ID @ 0x02001A: `1037524060` (RXT-X 260)
- MED17 string @ 0x03FE10: `30/1/MED17////7A1124O/A0RDS1//00//`
- Bosch part @ 0x029D13: `7A1124OA0RDS1`
- Aktivan sadržaj: 128KB u regiji 0x020000–0x040000 (sve ostalo = 0xFF)
- Header @ 0x020000: `60 00 00 00 04 FF 01 00` — BRP EEPROM container format
- Nije standardni 32KB EEPROM format — `EepromParser` nije kompatibilan

---

## 12. ME17Suite CAN Network Tab

The GUI includes a **CAN Network** tab (teal) that displays:
- ECU CAN message IDs read from the loaded binary
- SAT compatibility assessment (SAT_PROFILES per model year)
- Comparison between Spark and GTI/300hp ID sets
- Payload format info per CAN ID (via `core/can_decoder.py`)
- Timing information (period in ms per ID)

Source: `ui/can_network_widget.py`, `core/can_decoder.py`
