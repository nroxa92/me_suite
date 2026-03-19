# EEPROM Guide — BRP/Bosch ME17 Sea-Doo

> *Revidirano: 2026-03-18*

**Last updated:** 2026-03-18
**Source:** `core/eeprom.py`, binary analysis (3 samples: RXP 300 2021, Spark 18, RXP 20)

---

## 1. Overview

The EEPROM je **Data Flash (DFlash) unutar Infineon TC1762 MCU** — nije zasebni čip. TC1762 ima interno: 1.5MB Program Flash (PFlash, firmware + mape) i 64KB Data Flash (EEPROM emulacija). Oba se čitaju/pišu kroz isti MCU (BDM/BSL interface). EEPROM (DFlash) pohranjuje:
- Vehicle identification (Hull ID / VIN)
- Programming history (dates, count)
- Odometer / operating hours (circular buffer)
- Dealer information

**File size:** 32,768 bytes (32KB) exactly.

**Programmer tool:** BUDS2 (BRP's dealer software) reads and writes EEPROM via K-Line/CAN.

---

## 2. Fixed Offsets (verified on 3 samples)

| Offset | Field | Format | Length | Example |
|--------|-------|--------|--------|---------|
| 0x0013 | First programming date | ASCII | 8B | `04-05-21` (DD-MM-YY) |
| 0x001E | Last update date | ASCII | 8B | `07-05-21` (DD-MM-YY) |
| 0x0032 | MPEM SW ID | ASCII | 10B | `1037550003` |
| 0x0040 | Service SW ID | ASCII | 10B | `1037500313` (always this value) |
| 0x004C | Programming count | u8 | 1B | 1 or 2 |
| 0x004D | ECU serial number | ASCII | 11B | `SF00HM00196` |
| 0x0082 | Hull ID / VIN | ASCII | 12B | `YDV89660E121` |
| 0x0102 | Dealer name | ASCII | 16B | `SEA-DOO` |
| 0x0125 | **NOT hw timer** — SW constant | ASCII | 5B | `60620`, `BRP10`, or 0x00 |

> **Warning about 0x0125:** This field was initially suspected to be working hours, but it contains a software constant (`60620`, `BRP10`, or null). Real operating hours are in the circular buffer — see section 4.

---

## 3. HW Type Detection

HW type is derived from the MPEM SW ID prefix:

| MPEM SW prefix | HW Type | Vehicles |
|---------------|---------|---------|
| `10375500xxx` | **064** | 300hp SC, 230hp SC (Rotax 1630 SC/turbo) |
| `10375258xx` | **063** | Spark 90/115hp, some GTI SE 155 (1.5L) |
| `10375091xx` or `10375092xx` | **062** | GTI 130/155 older (2015–16) |
| Other | (unknown) | Older or unrecognized |

```python
# Detection logic from core/eeprom.py:
if mpem.startswith("10375500"):
    hw_type = "064"
elif mpem.startswith("10375258"):
    hw_type = "063"
elif mpem.startswith("10375091") or mpem.startswith("10375092"):
    hw_type = "062"
```

HW type affects the ODO circular buffer addresses (see section 4).

---

## 4. Odometer — Circular Buffer

The odometer (operating hours) is stored as **minutes** in a u16 LE circular buffer. The active slot rotates as the buffer fills.

### HW 064 (300hp / GTI SE 230hp)

| Address | Role |
|---------|------|
| **0x0562** | Primary — read this first |
| 0x0D62 | Backup (older layout / high minutes) |
| 0x1562 | Backup mirror |

### HW 063 (Spark 90, some GTI 155)

Spark ECU ima dva aktivna buffer mjesta — uzima se veća (novija) vrijednost:

| Address | Role |
|---------|------|
| **0x4562** | Primary Spark ODO buffer |
| **0x0562** | Fallback — kada buffer wrapa (počne ispunjavati od početka) |
| 0x0DE2 | High minutes overflow (>~30,000 minutes) |

> Stvarna logika: `best = max(val_at_0x4562, val_at_0x0562)` — koristi se viša vrijednost iz ova dva mjesta. Ako obje nisu valjane, fallback je 0x0DE2.

### HW 062 (GTI 130/155, older RXT 260)

Rotational scheme — newest value is in the highest numbered slot:

| Address | Priority | Notes |
|---------|----------|-------|
| **0x5062** | Newest (try first) | |
| **0x4562** | Second | |
| **0x1062** | Oldest | |

### Reading logic (iz core/eeprom.py):
```python
def _u16le(off):
    return int.from_bytes(data[off:off+2], 'little')

if hw_type == "062":
    # Rotacijski buffer — probaj od najnovijeg prema najstarijem
    for addr in (0x5062, 0x4562, 0x1062):
        v = _u16le(addr)
        if 1 <= v <= 65000:
            odo_raw = v; break
elif hw_type == "063":
    # Spark: uzmi max od dva aktivna mjesta
    v_a = _u16le(0x4562)  # primary (niske/srednje sate)
    v_b = _u16le(0x0562)  # fallback (kada buffer wrapa)
    best = max(v if 1 <= v <= 65000 else 0 for v in (v_a, v_b))
    if best:
        odo_raw = best
    else:
        v = _u16le(0x0DE2)  # visoke minute >~30000
        if 1 <= v <= 65000:
            odo_raw = v
else:
    # 064 / nepoznat HW
    v = _u16le(0x0562)
    if 1 <= v <= 65000:
        odo_raw = v
    else:
        for addr in (0x0D62, 0x1562):
            v = _u16le(addr)
            if 1 <= v <= 65000:
                odo_raw = v; break
```

### Converting minutes to hours:
```python
hours   = odo_raw // 60
minutes = odo_raw % 60
display = f"{hours}h {minutes:02d}min"
```

---

## 5. Hull ID / VIN Format

Format: `YDVxxxxxxxxx` (12 characters)

| Position | Meaning |
|----------|---------|
| 0–2 | Manufacturer code (YDV = BRP Sea-Doo) |
| 3–8 | Vehicle descriptor (model/engine) |
| 9 | Model year code (letter, A=1980, K=2019, L=2020, M=2021...) |
| 10 | Plant/manufacturing code |
| 11 | Production sequence digit |

Example: `YDV89660E121` → position 9 = `E` (likely 2014?), position 11 = `1`

---

## 6. ECU Serial Number Format

Format: `SF00HMxxxxx` (11 characters)

- `SF00` = Bosch ECU family prefix
- `HM` = hardware model
- `xxxxx` = 5-digit serial

---

## 7. MPEM Model Identification

| MPEM SW prefix | Probable model |
|---------------|----------------|
| `10375500` | 300hp (RXP-X 300 / GTX 300 / RXT-X 300) |
| `10375258` | Spark (90/110hp) |
| `10375091` or `10375092` | 260hp (RXT-X 260 / RXP-X 260) |
| `1037` (other) | BRP / Sea-Doo (generic) |

---

## 8. Using EepromParser

```python
from core.eeprom import EepromParser

parser = EepromParser()
info = parser.parse("path/to/eeprom.bin")

print(info.is_valid)         # True if hull_id or mpem_sw found
print(info.hull_id)          # e.g. "YDV89660E121"
print(info.serial_ecu)       # e.g. "SF00HM00196"
print(info.mpem_sw)          # e.g. "1037550003"
print(info.hw_type)          # "064", "063", "062", or ""
print(info.prog_count)       # number of times programmed
print(info.date_first_prog)  # "04-05-21"
print(info.odo_raw)          # raw minutes (u16)
print(info.odo_hhmm())       # "145h 23min"
print(info.mpem_model_guess()) # "300hp (RXP-X / GTX 300 / RXT-X 300)"
```

---

## 9. Notes

- EEPROM size must be exactly 32,768 bytes; parser continues with warnings if different
- EEPROM (DFlash) i firmware (PFlash) su oba unutar TC1762 — čitaju se zasebno jer su različite memorijske banke, ali kroz isti fizički čip
- The dealer name field (0x0102) can be up to 16 ASCII characters
- Service SW ID (0x0040) is always `1037500313` across all known samples — hardcoded by BUDS2
- **RXT-X 260 "nepoznati epprom"**: 2MB container dump, aktivan sadržaj 128KB @ offset 0x020000. SW=1037524060, Bosch part `7A1124OA0RDS1`. Nije standard 32KB format — EepromParser nije kompatibilan.
