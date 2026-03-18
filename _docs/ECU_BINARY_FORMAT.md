# ECU Binary Format — Bosch ME17.8.5 / TC1762

> *Revidirano: 2026-03-18*

**Last updated:** 2026-03-18
**Source:** `core/engine.py`, `core/checksum.py`, `_docs/_BRIEFING.md`, binary analysis

---

## 1. File Overview

| Parameter | Value |
|-----------|-------|
| File size | **1,540,096 bytes** (0x178000) — only valid size |
| MCU | Infineon TC1762 (TriCore, Little Endian) |
| Platform | Bosch ME17.8.5 |
| Flash base address | 0x80000000 (all TriCore pointers offset by this) |
| Fill byte (CODE unused) | 0xC3 (TriCore NOP instruction) |
| Fill byte (CAL/EMPTY) | 0x00 |

---

## 2. Memory Layout

```
Offset       Size         Region   Contents
─────────────────────────────────────────────────────────────────────────
0x000000   64KB (0x10000) BOOT     Bootloader, SW identifiers, checksum,
                                   security mechanisms.
                                   Sub-layout:
                                     0x0000–0x003F  Header (40B)
                                     0x0030–0x0033  CRC32 checksum (u32 BE)
                                     0x0040–0x7E7B  Boot code
                                     0x7E7C–0x7EFF  RSA-1024 signature (132B)
                                   Gap 0x7F00–0xFFFF:
                                     0x7F00:  DEADBEEF terminator
                                     0xFF00:  TC1762 BROM startup code

0x010000  320KB (0x50000) CODE     TriCore firmware + ALL TUNING MAPS.
                                   All calibration tables are here.
                                   Fill: 0xC3 (TriCore NOP) in unused areas.

0x060000    1MB (0x100000) CAL     *** WARNING: LOOKS LIKE CALIBRATION
                                   BUT IS TRICORE BYTECODE! ***
                                   Bosch AUTOSAR/ASCET compiled code with
                                   embedded parameters. READ-ONLY — do not
                                   write without deep understanding.
                                   754 LE pointers in CODE point here
                                   (bytecode, not map data).

0x160000   96KB (0x18000)  EMPTY   0x00 fill, unused flash space.
```

> **BOOT region stvarna granica:** BOOT završava na 0x7EFF (ne 0xFFFF!). Gap 0x7F00–0xFFFF sadrži DEADBEEF terminator i TC1762 BROM startup kod. Checksum pokriva samo 0x0000–0x7EFF.

### Python constants (core/engine.py):
```python
BOOT_START  = 0x000000
BOOT_END    = 0x00FFFF   # konstantna granica regije u kodu
CODE_START  = 0x010000
CODE_END    = 0x05FFFF
CAL_START   = 0x060000
CAL_END     = 0x15FFFF
EMPTY_START = 0x160000
```

> Napomena: BOOT_END u kodu = 0x00FFFF (64KB blok), ali checksum regija = 0x0000–0x7EFF (32,512B). RSA potpis je @ 0x7E7C–0x7EFF.

---

## 3. Identification Strings

| String | Location | Value |
|--------|----------|-------|
| MCU/platform ID | 0x01FE50–0x01FEFF | `VME17 SB_V05.01.02` |
| Platform string | 0x012800–0x012FFF | `PLATFORM VM_CB.04.80.00` |
| SW ID (primary) | **0x001A** | 10 ASCII bytes, e.g. `10SW066726` |
| SW ID (fallback) | **0x02001A** | CODE mirror — used when BOOT is erased (0xFF filled) |

### SW ID location logic:
1. Read 10 bytes at 0x001A
2. If all 0xFF (BOOT erased) → read 10 bytes at 0x02001A
3. Strip null bytes, decode ASCII
4. Look up in `KNOWN_SW` dict

**FADEFACE descriptor** @ 0x40:
- Contains addresses 0x80012C78 (CODE) and 0x80007E74 (before RSA signature)
- Used by bootloader for flash layout

---

## 4. Checksum

### Algorithm: CRC32-HDLC (ISO-HDLC / standard zlib CRC32)

| Parameter | Value |
|-----------|-------|
| Polynomial | 0xEDB88320 (reflected 0x04C11DB7) |
| Init | 0xFFFFFFFF |
| XorOut | 0xFFFFFFFF |
| Region | 0x0000–0x7EFF (0x7F00 bytes = BOOT region) |
| Type | Closed-form (CS @ 0x30 is INCLUDED in calculation) |
| Storage | @ **0x0030** as u32 Big-Endian |
| Fixed residue | **0x6E23044F** (verified on 4 different ECU files) |

### Verified checksums:
| File | Stored CS | CRC of BOOT | Status |
|------|-----------|-------------|--------|
| ori_300 (10SW066726) | 0xE505BC0B | 0x6E23044F | OK |
| stg2_300 (10SW040039) | 0x9FC76FAD | 0x6E23044F | OK |
| rxtx_260 (524060) | 0x53532E7D | 0x6E23044F | OK |
| rxt_514362 | 0xE5D7955F | 0x6E23044F | OK |

### CRITICAL RULE:
**Changing CODE maps (0x010000–0x05FFFF) does NOT require changing the checksum!**

CS must change only if the BOOT region changes:
- SW version bytes (0x001C–0x0023)
- The CS itself (0x0030–0x0033)
- RSA signature (0x7E7C–0x7EFF, 132B) — requires Bosch private key

### RSA Signature:
- Location: 0x7E7C–0x7EFF (132 bytes)
- Type: RSA-1024 (suspected, cannot replicate without Bosch key)
- This block cannot be modified — changing it causes ECU to reject the flash
- `compute_new_cs()` in `core/checksum.py` calculates new CS via meet-in-the-middle inverse CRC (works only if RSA signature unchanged)

### Verification code (core/checksum.py):
```python
# Verify: CRC32-HDLC of data[0x0000:0x7F00] should equal 0x6E23044F
from core.checksum import verify_boot_crc
ok, actual = verify_boot_crc(data)  # True if checksum is valid
```

---

## 5. Data Format Reference

| Format | Description | Decoder |
|--------|-------------|---------|
| u8 | 1 byte unsigned | `data[addr]` |
| u16 BE | 2 bytes Big-Endian | `(d[a]<<8) \| d[a+1]` |
| u16 LE | 2 bytes Little-Endian | `d[a] \| (d[a+1]<<8)` |
| u32 BE | 4 bytes Big-Endian | `struct.unpack_from(">I", data, addr)` |
| Q8 | u16 BE, data in MSB only | `MSB / 128 × 100 = %` |
| Q14 | u16 LE fixed-point | `val / 16384 = factor` (16384 = 1.000) |
| Q15 | u16 LE fixed-point | `val / 32768 = factor` (32768 = 1.000 = λ 1.0) |
| Q15 % | u16 LE Q15 as percentage | `val × 100 / 32768 - 100 = %` |

### RPM encoding (period-based, rev limiter):
```
RPM = 40,000,000 / (ticks × 58/60)
```
- 40 MHz = TC1762 timer clock
- 58/60 = 60-2 tooth reluctor wheel (60 teeth, 2 missing), 3-cylinder Rotax
- Example: 5072 ticks → 40e6 / (5072 × 58/60) = **8158 RPM**

---

## 6. Pointer Analysis

- 754 Little-Endian pointers found in CODE region pointing to CAL
- All start with 0x80006... or 0x80008... (CAL base = 0x80060000)
- These are bytecode function pointers — NOT map data pointers
- CAL region is TriCore AUTOSAR bytecode — do not write

---

## 7. Notable Binary Signatures

| Signature | Address | Meaning |
|-----------|---------|---------|
| `FADEFACE` | 0x0040 | Flash descriptor |
| `DEADBEEF` | 0x7F00 | BOOT region terminator |
| `VME17 SB_V05.01.02` | 0x01FE50 | MCU/platform ID string |
| `PLATFORM VM_CB.04.80.00` | 0x012800 | Platform string |
| `10SW066726` | 0x001A | SW ID (varies by variant) |

---

## 8. Reading a Binary File

```python
from core.engine import ME17Engine

eng = ME17Engine()
info = eng.load("dumps/2021/1630ace/300.bin")

print(info.sw_id)          # "10SW066726"
print(info.mcu_confirmed)  # True
print(info.is_valid)       # True
print(info.errors)         # [] if all OK

# Read a u16 LE value at address 0x028E96 (rev limiter):
ticks = eng.read_u16_le(0x028E96)  # 5072
rpm = 40e6 / (ticks * 58/60)      # 8158 RPM
```
