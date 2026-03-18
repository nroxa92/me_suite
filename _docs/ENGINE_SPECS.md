# Engine Specifications — Rotax Engines (Sea-Doo)

> *Revidirano: 2026-03-18*

**Last updated:** 2026-03-18
**Source:** 2021 BRP Service Manual (str. 185), Tech Spec PDFs, binary analysis

---

## 1. Rotax 1630 SC — 300hp / 230hp

### Base Specifications

| Parameter | 300hp | 230hp |
|-----------|-------|-------|
| Displacement | 1630.5cc | 1630.5cc |
| Configuration | SOHC, 3-cyl, inline | SOHC, 3-cyl, inline |
| Bore × Stroke | 100mm × 69.2mm | 100mm × 69.2mm |
| Valves | 12 (4 per cylinder) | 12 (4 per cylinder) |
| Valve lifters | Hydraulic (no adjustment) | Hydraulic (no adjustment) |
| Compression ratio | **8.4:1** | **8.3:1** |
| Supercharger slip (clutch) | 14–17 N·m | 9–14 N·m |
| Fuel pressure | 386–414 kPa (56–60 PSI) | 386–414 kPa (56–60 PSI) |
| Throttle body | 60mm single, ETA (Electronic Throttle Actuator) | 60mm single |
| Idle RPM (spec) | 1700 ±50 RPM | 1700 ±50 RPM |
| Idle RPM (ECU firmware) | ~1840 RPM | ~1840 RPM |
| ECU hard cut (from binary) | **8158 RPM** | **8158 RPM** |
| Max HP RPM (spec) | ~8000 RPM | ~8000 RPM |
| ECU SW | 10SW066726 (2021), 10SW054296 (2020) | 10SW053727 |

> Note: ECU idle setpoint is ~1840 RPM (not 1700) because the supercharger parasitic drag requires ~140 RPM compensation.

### Sparks / Ignition Plugs (300hp / 230hp)

| Part | NGK KR9E-G |
|------|------------|
| Gap | 0.7–0.8 mm |

### Camshaft Timing — 300hp

| | Exhaust | Intake |
|-|---------|--------|
| Open | 50° BBDC | 0° BTDC |
| Close | 0° ATDC | 50° ABDC |
| Lobe height (new) | 31.430–31.630 mm | 31.540–31.740 mm |

### Camshaft Timing — 230hp

| | Exhaust | Intake |
|-|---------|--------|
| Open | 48° BBDC | 2° ATDC |
| Close | 8° BTDC | 42° ABDC |
| Lobe height (new) | 30.630–30.830 mm | 30.513–30.713 mm |

### Piston Clearance
- 300hp: **0.044–0.076 mm**
- 230hp: **0.024–0.056 mm**

---

## 2. Rotax 1630 NA — 170hp / 130hp

### Base Specifications

| Parameter | 170hp | 130hp |
|-----------|-------|-------|
| Displacement | 1630.5cc | 1630.5cc |
| Configuration | SOHC, 3-cyl, inline | SOHC, 3-cyl, inline |
| Bore × Stroke | 100mm × 69.2mm | 100mm × 69.2mm |
| Compression ratio | **11:1** | **11:1** |
| Supercharger | None | None |
| Fuel pressure | 386–414 kPa (56–60 PSI) | 386–414 kPa (56–60 PSI) |
| Idle RPM (spec) | 1750 ±50 RPM | 1820 ±50 RPM |
| ECU hard cut (from binary) | **7892 RPM** | **7892 RPM** |
| ECU SW | 10SW053729 (same for both!) | 10SW053729 |

> **130hp vs 170hp paradox:** The ECU binary is **identical** (0 bytes difference). Identical valve timing. Power difference is likely due to different impeller or drivetrain loading — NOT the ECU.

### Sparks / Ignition Plugs (130hp / 170hp)

| Part | NGK DCPR8E |
|------|------------|
| Gap | 0.8–0.9 mm |

### Camshaft Timing — 130hp / 170hp NA

| | Exhaust | Intake |
|-|---------|--------|
| Open | 52° BBDC | 2° BTDC |
| Close | 3° ATDC | 55° ABDC |
| Lobe height (new) Exhaust | 31.720–31.920 mm | — |
| Lobe height (new) Intake | — | 31.710–31.910 mm |

### Piston Clearance
- 130hp / 170hp: **0.024–0.056 mm** (same as 230hp)

### Injectors (1630 series — all variants share)
- 300hp, 230hp, 170hp, 130hp: **same injectors**
- Deadtime table @ 0x025900: identical across 130–300hp
- Deadtime minor variations (±2 values) for 300hp vs 230hp but effectively same hardware

---

## 3. Rotax 1503 NA — GTI 155 / GTI 130

### Base Specifications

| Parameter | GTI 155 | GTI 130 |
|-----------|---------|---------|
| Displacement | ~1503cc | ~1503cc |
| Configuration | SOHC, 3-cyl, inline | SOHC, 3-cyl, inline |
| Stroke vs 1630 | Shorter (same bore, shorter stroke) | — |
| Supercharger | None | None |
| Idle RPM (spec) | ~1700 RPM | ~1700 RPM |
| ECU hard cut (from binary) | **7700 RPM** (GTI 155 2018) | — |
| ECU soft cut | 7517 RPM | — |
| ECU SW (GTI 155) | 10SW025752 | 10SW040008 / 10SW040962 |

> Note: GTI SE 155 uses SW 10SW025752. GTI SE 130/155 2019 use same SW 10SW040008.

### Key difference from 1630 series:
- Different injection map format: GTI uses direct raw values @ 0x022066 (not Q15)
- 8 additional ignition maps @ 0x028310 (stride 144B) — GTI-specific
- SC bypass maps present but inactive (NA motor)

---

## 4. Rotax 900 HO ACE — GTI SE 90

### Base Specifications

| Parameter | GTI SE 90 |
|-----------|-----------|
| Displacement | 899.3cc |
| Configuration | SOHC, 3-cyl, inline |
| Bore × Stroke | 74mm × 69.7mm |
| Compression ratio | 11.0:1 |
| Output | 66.19 kW @ 8000 RPM (90hp) |
| Supercharger | None |
| Idle RPM (spec) | 1400 ±100 RPM |
| ECU hard cut (estimated) | **~7040 RPM** (@ 0x028E7C = 5875 ticks — not live verified) |
| ECU SW | 10SW053774 |

> WARNING: GTI90 rev limiter is at a DIFFERENT address (0x028E7C / 0x028E68) compared to 1630 engines (0x028E96). The value at 0x028E96 for GTI90 = 3277 ticks (~12627 RPM) — completely wrong for rev limiter.

### Torque map:
- @ 0x02A0D8 = flat 32768 (100% = no restriction)
- No supercharger override needed

---

## 5. Rotax 900 ACE — Sea-Doo Spark 90

### Base Specifications

| Parameter | Spark 90 |
|-----------|----------|
| Displacement | 899.3cc |
| Configuration | SOHC, 3-cyl, inline |
| Bore × Stroke | 74mm × 69.7mm |
| Compression ratio | 11.0:1 |
| Supercharger | None |
| Idle RPM (spec) | 1400 ±100 RPM |
| ECU hard cut (from binary) | **8081 RPM** (5120 ticks @ 0x028E34) |
| ECU SW (2016) | 10SW011328 |
| ECU SW (2019–2021) | 10SW039116 |

### Rev limiter details (Spark):

| Type | Ticks | RPM | Source |
|------|-------|-----|--------|
| Hard cut (ECU binary) | 5120 | **8081 RPM** | Confirmed same in 2018/2021/STG2 |
| Engine speed limiter (Tech Spec) | — | **8300 RPM** | BRP service manual (engine-only, no load) |
| Max HP RPM (Tech Spec) | — | **8000 RPM** | Maximum power RPM |
| iBR/VEHICLE limit | — | **8000 RPM** | Vehicle/iBR-equipped Spark variant |
| Practical in-water RPM | — | ~7900 RPM | Impeller-limited |
| NPRo STG2 in-water RPM | — | ~8500 RPM | With modified impeller; ECU cut = 8081 |

> Binary value 8081 is between 8000 (max HP RPM) and 8300 (engine speed limiter). Hypothesis: 8300 = engine-only limit (no load), 8081 = actual ECU cut with load/impeller.

### Differences from GTI SE 90:
- Different CODE layout (different address for all maps)
- 10SW011328 (2016/2018) vs 10SW039116 (2019+): 622,954 bytes different — completely different layout
- 10SW039116 (2019/2020/2021): identical binaries across years

---

## 6. Fuel System (All Variants)

| Parameter | Value |
|-----------|-------|
| Fuel pressure | **386–414 kPa (56–60 PSI)** — same for all NA and SC variants |
| Injectors | Sequential, 3 total (1 per cylinder) |
| Fuel rail | Integrated with 60mm throttle body |
| Injector deadtime | @ 0x025900 (14×7 table, hardware constant — do not modify) |

---

## 7. CTS (Coolant Temperature Sensor) Resistance

| Temperature | Resistance range |
|-------------|-----------------|
| −40°C | 38k–53k Ω |
| −10°C | 8k–11k Ω |
| 20°C | 2.2k–2.8k Ω |
| 80°C | 297–349 Ω |
| 120°C | 105–122 Ω |

### CTS NTC ADC lookup table (hardware calibration — DO NOT MODIFY):
- Location: @ 0x0258AA (10 values: ADC 5383→1425)
- These are hardware-specific calibration values for the NTC thermistor

### Overtemperature thresholds:

| Variant | CTS limp mode trigger | OTS limp mode |
|---------|----------------------|----------------|
| 130hp / 170hp NA | >102°C | 115°C |
| 230hp / 300hp SC | >97°C | 97°C |

---

## 8. 1.5L vs 1.6L Comparison

| Feature | Rotax 1503 (1.5L) | Rotax 1630 (1.6L) |
|---------|-------------------|-------------------|
| Bore | Same | Same |
| Stroke | Shorter | Longer (→ larger displacement) |
| Architecture | Same block design | Same block design |
| Variants | 130/155/230/260hp | 130/170/230/300hp |
| Differences | Pistons, camshafts, injectors, ECU map | Pistons, camshafts, injectors, ECU map |

The 1.5L and 1.6L share the same block architecture — the 1.6L simply has a longer stroke (larger crankshaft throw) for additional displacement.
