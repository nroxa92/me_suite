# Maps Reference — Bosch ME17.8.5 / Rotax ECU

**Last updated:** 2026-03-18
**Source:** `core/map_finder.py` (complete), binary analysis
**Coverage:** All confirmed maps in CODE region 0x010000–0x05FFFF

---

## Quick Summary by Variant

| Variant | SW ID | Maps found |
|---------|-------|-----------|
| 300hp SC | 10SW066726 | 51 |
| 230hp SC | 10SW053727 | 51 |
| 130/170hp NA | 10SW053729 | 60 |
| GTI SE 90 | 10SW053774 | 58 |
| Spark 90 (2019+) | 10SW039116 | 20 (13 base + 7 aux) |
| GTI SE 155 | 10SW025752 | 9 GTI-specific + shared |

---

## Data Format Legend

| Symbol | Meaning |
|--------|---------|
| BE | Big-Endian byte order |
| LE | Little-Endian byte order |
| Q8 | 16-bit BE, only MSB carries data; MSB/128 = fraction |
| Q14 | 16-bit LE fixed-point; val/16384 = factor (16384 = 1.000) |
| Q15 | 16-bit LE fixed-point; val/32768 = factor (32768 = 1.000 = λ1.0) |
| u8 | 1-byte unsigned integer |
| u16 | 2-byte unsigned integer |
| rows×cols | row = Y axis (load), col = X axis (RPM) |

---

## 1. Axes (Global)

### RPM Axes — 3 mirrors @ 0x024F46 / 0x025010 / 0x0250DC

| Address | Format | Dimensions | Values (RPM) |
|---------|--------|-----------|--------------|
| 0x024F46 | u16 BE | 1×16 | 512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 4608, 5120, 5632, 6400, 6912, 7424, 7936, 8448 |
| 0x025010 | u16 BE | 1×16 | (identical mirror) |
| 0x0250DC | u16 BE | 1×16 | (identical mirror) |

- Used by: ignition (first 12 pts), torque (all 16 pts), lambda (first 12 pts)
- Variants: all 1630 SC/NA variants share these addresses; GTI90 and Spark have different RPM axes

### Load (Relative Air Charge) Axes

| Points | Values (raw/64 = rl %) | Used for |
|--------|----------------------|----------|
| 12-pt | 0, 100, 200, 400, 800, 1280, 2560, 3200, 3840, 4480, 5120, 5760 | ignition, injection, lambda (rows) |
| 16-pt | + 6400, 7040, 7680, 8320 | torque (rows) |
| 18-pt (lambda X) | 853, 1067, 1280, 1493, 1707, 1920, 2133, 2347, 2560, 2773, 2987, 3200, 3413, 3840, 4267, 4693, 5547, 6400 | lambda main map (columns) |

> Source: @ 0x02AFAC (LE u16, 12 points), @ 0x02AE30 (16 points)
> Scale: raw ÷ 64 = relative load %. >100% is normal with supercharger.

---

## 2. Ignition Maps

### Primary Ignition Block (19 maps)

| Index | Address | Name | Format | Scale | Notes |
|-------|---------|------|--------|-------|-------|
| #00 | 0x02B730 | Ignition — Base 1 | 12×12 u8 | ×0.75°/bit | ORI: 24–33.75° BTDC |
| #01 | 0x02B7C0 | Ignition — Base 2 | 12×12 u8 | ×0.75°/bit | STG2: up to 36.75° BTDC |
| #02 | 0x02B850 | Ignition — Base 3 | 12×12 u8 | ×0.75°/bit | |
| #03 | 0x02B8E0 | Ignition — Base 4 | 12×12 u8 | ×0.75°/bit | |
| #04 | 0x02B970 | Ignition — Base 5 | 12×12 u8 | ×0.75°/bit | |
| #05 | 0x02BA00 | Ignition — Base 6 | 12×12 u8 | ×0.75°/bit | |
| #06 | 0x02BA90 | Ignition — Base 7 | 12×12 u8 | ×0.75°/bit | |
| #07 | 0x02BB20 | Ignition — Base 8 | 12×12 u8 | ×0.75°/bit | |
| **#08** | **0x02BBB0** | **Knock correction 1** | 12×12 u8 | ×0.75° | CONFIRMED: negative delta/retard trim |
| **#09** | **0x02BC40** | **Knock correction 2** | 12×12 u8 | ×0.75° | CONFIRMED: knock delta/trim map |
| #10 | 0x02BCD0 | Auxiliary 1 | 12×12 u8 | ×0.75°/bit | unidentified |
| #11 | 0x02BD60 | Auxiliary 2 | 12×12 u8 | ×0.75°/bit | unidentified |
| #12 | 0x02BDF0 | Auxiliary 3 | 12×12 u8 | ×0.75°/bit | unidentified |
| #13 | 0x02BE80 | Auxiliary 4 | 12×12 u8 | ×0.75°/bit | unidentified |
| #14 | 0x02BF10 | Auxiliary 5 | 12×12 u8 | ×0.75°/bit | unidentified |
| #15 | 0x02BFA0 | Auxiliary 6 | 12×12 u8 | ×0.75°/bit | unidentified |
| **#16** | **0x02C030** | **Extended 1** | 12×12 u8 | ×0.75°/bit | CONFIRMED: NPRo STG2 modifies |
| **#17** | **0x02C0C0** | **Extended 2** | 12×12 u8 | ×0.75°/bit | CONFIRMED: NPRo STG2 modifies |
| #18 | 0x02C150 | Conditional | 12×12 u8 | ×0.75°/bit | first 3 rows active, rest zero |

**Layout:** Base address 0x02B730, stride 144B (12×12×1 byte), 19 maps total.

**Axes (shared, not embedded):**
- X (RPM, 12 points): 512–6400 RPM — global RPM axis @ 0x024F46
- Y (load, 12 points): rl% 0–90% — @ 0x02AFAC

**Knock correction maps (#08, #09):**
- Represent retard delta applied when knock is detected
- Negative/small values = less timing retard allowed
- ORI: 0–40 raw, STG2: caps at 40

### Ignition Correction (2D u8)

| Address | Name | Format | Scale | Notes |
|---------|------|--------|-------|-------|
| **0x022374** | Ignition correction / efficiency | 8×8 u8 | raw | Y-axis @ 0x022364: [75,100,150,163,175,181,188,200]; X-axis: [53,80,107,120,147,187,227,255]; ORI: 145–200; STG2 caps all >180 |

---

## 3. Injection Maps

### Rotax 1630 (300hp / 230hp / 130hp / 170hp / GTI 155)

| Address | Name | Format | Dims | Scale | Mirror | Notes |
|---------|------|--------|------|-------|--------|-------|
| **0x02436C** | Injection — rel. fuel mass (rk) | u16 LE Q15 | 16×12 | ÷32768 | +0x180 → 0x0244EC | Main fuel map. Q15: 32768=1.0 (100% base fuel) |
| **0x0244EC** | Injection — mirror | u16 LE Q15 | 16×12 | ÷32768 | | Mirror of main (+0x180) |
| **0x025CDC** | Start injection (cranking) | u16 LE | 1×6 | raw | +0x1A → 0x025CF6 | 6-pt RPM axis embedded: [0,1024,1707,3413,5120,7680] rpm |
| **0x025CF6** | Start injection — mirror | u16 LE | 1×6 | raw | | Mirror (+0x1A from main) |
| **0x028059** | Accel enrichment (transient) | u16 LE Q14 | 5×5 | ×100/16384-100% | none | dTPS axis [°/s] embedded per-row; ORI: 76–160%, STG2: 48–264% |
| **0x02220E** | SC boost fuel correction | u16 LE Q14 | 9×7 | ×100/16384-100% | none | X-axis (RPM) @ 0x022200, Y-axis (load) @ 0x0221EC; 130/170hp = all 0% (NA, no SC) |
| **0x025E50** | CTS warm-up correction | u16 LE Q14 | 1×156 | ×100/16384-100% | none | 300hp: flat +20.8%; 230hp: −18.4%; 130/170hp: ~0% |
| **0x025DF8** | SC base fuel factor | u16 LE Q14 | 1×40 | ÷16384-1 | none | 300hp SC: flat +22.4% (raw=20046); 130hp NA: 0; lambda axis (8pt) @ 0x025DE8 |

### GTI SE 155 / GTI SE 90 Specific

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x022066** | GTI injection (direct) | u16 LE raw | 16×12 | GTI-specific, not Q15. Range 3193–14432. No mirror confirmed. |

### Spark 900 ACE (10SW039116)

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x0222BE** | Spark injection | u16 LE | 30×20 | 30 load × 20 RPM, range 479–4443 µs |
| **0x022282** | Spark load axis (30pt) | u16 LE | 1×30 | range 3999–33600 |
| **0x02225A** | Spark RPM axis (20pt) | u16 LE | 1×20 | raw/4 = RPM, range 1920–6656 |

---

## 4. Lambda / AFR Maps

> NOTE: Rotax ACE 1630 and 900 HO have NO physical lambda sensor. These maps are open-loop AFR targets.

### Rotax 1630 (all SC/NA variants)

| Address | Name | Format | Dims | Scale | Mirror | Notes |
|---------|------|--------|------|-------|--------|-------|
| **0x0266F0** | Lambda — target AFR (open-loop) | u16 LE Q15 | 12×18 | ÷32768 = λ | +0x518 → 0x026C08 | ORI: 0.965–1.073 λ; STG2: 0.984–1.080 λ |
| **0x026C08** | Lambda — mirror | u16 LE Q15 | 12×18 | ÷32768 = λ | | Mirror (+0x518) |
| **0x0265D6** | Lambda bias (global AFR trim) | u16 LE Q15 | 1×141 | ×100/32768-100% | none | 300hp: +0.47% lean; 230hp: +2.41%; 130/170hp: −0.07% |
| **0x026DB8** | Lambda trim (RPM×load) | u16 LE Q15 | 12×18 | ×100/32768-100% | none | Per-variant calibration; 300hp: 0.965–1.001 |
| **0x02469C** | Lambda protection (max injection) | u16 LE Q15 | 12×13 | ÷32768 = λ | none | ORI: diagonal 0.04–1.80; STG2: all 65535 (max freedom) |
| **0x025ADA** | Lambda overtemp protection (sub-A) | u16 LE Q15 | 1×63 | ÷32768 | none | 300hp SC: all 0xFFFF (bypass); 130hp NA: 0.855–0.926 |
| **0x025B58** | Lambda neutral correction (sub-B) | u16 LE Q14 | 1×63 | ÷16384 | none | 300hp SC: flat 16448 = Q14 1.004 (+0.4%, neutral bypass); 130hp NA: active 0.855–0.933 |
| **0x0259D2** | Lambda efficiency correction (2D) | u16 LE Q15 | 10×7 | ÷32768 | none | col[0] = embedded Y-axis (lambda); X-axis @ 0x0259C4: λ 0.40–1.34; KFWIRKBA sub-table (TODO confirm) |
| **0x02AE5E** | Lambda efficiency (KFWIRKBA) 41×18 | u16 LE Q15 | 41×18 | ÷32768 | none | X-axis: λ 0.66–1.80 (18 pts); Y-axis (15 load pts) @ 0x02AE40: [3840..15360]; STG2: lean side (λ>1.0) all 0xFFFF |

### Spark 900 ACE

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x025F5C** | Spark lambda copy 1 | u16 LE Q15 | 8×16 | λ 0.737–1.004 |
| **0x02607E** | Spark lambda copy 2 | u16 LE Q15 | 8×16 | +0x122 from copy 1 |
| **0x0261A0** | Spark lambda copy 3 | u16 LE Q15 | 8×16 | +0x244 from copy 1 |
| **0x0262C2** | Spark lambda copy 4 | u16 LE Q15 | 8×16 | +0x366 from copy 1 |

---

## 5. Torque Maps

| Address | Name | Format | Dims | Scale | Mirror | Notes |
|---------|------|--------|------|-------|--------|-------|
| **0x02A0D8** | Torque — limit [%] | u16 BE Q8 | 16×16 | MSB×100/128 = % | +0x518 → 0x02A5F0 | ORI: 93–120%; STG2: 93–123%; LSB always 0x00 |
| **0x02A5F0** | Torque — mirror | u16 BE Q8 | 16×16 | MSB×100/128 = % | | Mirror (+0x518) |
| **0x02A7F0** | Torque optimal / driver demand | u16 BE Q8 | 16×16 | ×100/32768 = % | none | 300hp: 93–107%; 230hp: 90–108%; 130hp: 92–108%; immediately after mirror |

**Axes:** X = RPM 16-pt (512–8448), Y = load 16-pt (0–130%)

> GTI SE 90 NA (10SW053774): torque map @ 0x02A0D8 = flat 32768 (100% = no restriction; NA motor, no SC override)

---

## 6. Rev Limiter

### Rotax 1630 SC/NA (300hp, 230hp, 130hp, 170hp, GTI155)

| Address | Name | Format | 300hp/230hp | 130/170hp | GTI155 |
|---------|------|--------|-------------|-----------|--------|
| **0x028E96** | Hard cut RPM | u16 LE period | **5072 = 8158 RPM** | **5243 = 7892 RPM** | **5374 = 7700 RPM** |
| **0x028E98** | Soft cut / resume | u16 LE period | 5399 = 7664 RPM | 5374 = 7700 RPM | 5505 = 7517 RPM |
| 0x028E90–0x028E94 | Ramp-down [0–2] | u16 LE period | 3506–4589 | 4915–5112 | 4981–5243 |

### GTI SE 90 (10SW053774)

> Different structure! Rev limiter is NOT at 0x028E96 for this variant.

| Address | Ticks | Est. RPM | Status |
|---------|-------|----------|--------|
| **0x028E68** | 5883 | ~7034 RPM | Probable hard cut (block A) |
| **0x028E7C** | 5875 | ~7043 RPM | Probable hard cut (block B) |

### Spark 900 ACE (10SW039116 / 10SW011328)

| Address | Ticks | RPM | Notes |
|---------|-------|-----|-------|
| **0x028E34** | 5120 | **8081 RPM** | Hard cut — confirmed identical in 2018/2021/STG2 |
| 0x028E2E | 3200–13763 | ramp table | Soft-cut ramp table (16 values) |

**RPM formula (all variants):**
```
RPM = 40,000,000 / (ticks × 58/60)
```
- 40 MHz timer, 60-2 tooth reluctor wheel (58 effective teeth), 3-cylinder

---

## 7. SC (Supercharger) Bypass Maps

Only relevant for SC variants (300hp, 230hp). Present but inactive on NA motors.

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x020534** | SC bypass — shadow copy | u8 | 7×7 | NPRo does NOT modify this copy |
| **0x0205A8** | SC bypass — active copy | u8 | 7×7 | NPRo modifies (38–255 raw); this is the effective map |
| **0x029993** | SC bypass — extra copy | u8 | 7×7 | NPRo modifies differently from 0x0205A8 |

**Encoding:** 0 = bypass closed = MAX boost; 255 = bypass fully open = zero boost
**Scale:** raw × 100/255 = % bypass open

**Axes:**
- X (MAP pressure, 7 pts) @ 0x020509: [63,75,88,100,113,138,163] = [0.63–1.63 bar abs.]
- Y (load %, 7 pts) @ 0x020524: [51,77,102,128,154,179,205] = [39.8–160.2 %] (128 = 100%)

---

## 8. Temperature Corrections

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x02586A** | Cold start enrichment | u16 LE | 1×6 | ORI: [500,1000,1690,1126,1096,1024]; STG2: [100,1000,1690,1126,1075,1024] |
| **0x025896** | CTS temperature axis | u16 LE | 1×10 | [37,51,64,77,91,104,117,131,144,157] °C |
| **0x0258AA** | NTC ADC lookup | u16 LE | 1×10 | [5383..1425] hardware calibration — DO NOT MODIFY |
| **0x02AA42** | Thermal enrichment (high CTS) | u16 LE | 8×7 | /64 = %; Y-axis (CTS) @ 0x02AA32: [80..150]°C; X-axis (load) @ 0x02AA02: [6400..16000]; ORI: 168–210%; STG2: 105–208% |

---

## 9. Other Maps

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x02B600** | Idle RPM target | u16 LE | 5×12 | Direct RPM; 1840–3340 rpm; identical across all SC/NA variants; 5 conditions × 12 temp/time steps |
| **0x02202E** | DFCO RPM thresholds | u16 LE | 1×7 | 130/170hp: [853–2560]; 300hp: [1067–3413 rpm] |
| **0x0256F8** | Knock threshold parameters | u16 LE | 1×24 | ORI: [0-1]=44237, rest=7967; STG2: [0-1]=65535, selective cells=39578 |
| **0x025900** | Injector deadtime (TVKL) | u16 LE | 14×7 | Hardware constant — DO NOT MODIFY; identical across all SW variants; X-axis = battery voltage |

---

## 10. Spark-Specific Aux Maps (10SW039116)

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| 0x021748 | Spark DFCO RPM thresholds | u16 LE | 1×7 | Spark DFCO |
| 0x0241F8 | Spark cold start enrichment | u16 LE | 1×6 | Same as GTI90 |
| 0x02428E | Spark deadtime | u16 LE | 14×7 | Same as GTI90 |
| 0x02408C | Spark knock thresholds | u16 LE | 1×24 | Same as GTI90 |
| 0x024676 | Spark start injection | u16 LE | 1×6 | Spark-specific |
| 0x024786 | Spark warm-up enrichment | u16 LE Q14 | 1×156 | |
| 0x0224A0 | Spark idle RPM target | u16 LE | 5×12 | |

> Note: Spark deadtime corrected to 0x0287A4 in later work (8×8=64 u16 LE, period-encoded 9632–13440 ticks)

---

## 11. Mirror Offsets Summary

| Map | Main | Mirror | Offset |
|-----|------|--------|--------|
| Torque | 0x02A0D8 | 0x02A5F0 | +0x518 |
| Lambda | 0x0266F0 | 0x026C08 | +0x518 |
| Injection 1630 | 0x02436C | 0x0244EC | +0x180 |
| SC bypass | 0x020534 | 0x0205A8 | +0x74 |
| Start injection | 0x025CDC | 0x025CF6 | +0x1A |
| GTI injection | 0x022066 | none | mirror_offset=0 |

**Always write both main and mirror when editing a map that has one!**

---

## 12. Variant Availability Matrix

| Map | 300hp SC | 230hp SC | 130/170hp NA | GTI90 NA | Spark 900 |
|-----|----------|----------|-------------|----------|-----------|
| Ignition 19× (0x02B730) | ✅ | ✅ | ✅ | ✅ | ❌ (diff. addr) |
| Injection main (0x02436C) | ✅ | ✅ | ✅ | ✅ | ❌ (diff. addr) |
| GTI injection (0x022066) | ❌ | ❌ | ❌ | ✅ | ❌ |
| Lambda main (0x0266F0) | ✅ | ✅ | ✅ | ✅ | ❌ (diff. addr) |
| Torque (0x02A0D8) | ✅ | ✅ | ✅ | ✅ flat | ❌ |
| SC bypass (0x020534/A8/9993) | ✅ active | ✅ active | ❌ present/inactive | ❌ present/inactive | ❌ |
| SC boost factor (0x025DF8) | ✅ +22.4% | ✅ | ✅ 0 (NA) | ✅ −18.4% | ❌ |
| Thermal enrichment (0x02AA42) | ✅ | ✅ | ✅ (diff. values) | ✅ | ❌ |
| KFWIRKBA (0x02AE5E) | ✅ | ✅ | ✅ | ✅ | ❌ |
| Rev limiter (0x028E96) | ✅ | ✅ | ✅ | ❌ diff. addr | ❌ diff. addr |
