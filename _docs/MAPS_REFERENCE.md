# Maps Reference — Bosch ME17.8.5 / Rotax ECU

> *Revidirano: 2026-03-19*

**Last updated:** 2026-03-19
**Source:** `core/map_finder.py` (complete), binary analysis
**Coverage:** All confirmed maps in CODE region 0x010000–0x05FFFF

---

## Quick Summary by Variant

| Variant | SW ID | Maps found |
|---------|-------|-----------|
| 300hp SC | 10SW066726 | **53** |
| 300hp SC STG2 | 10SW040039 | **53** |
| 230hp SC | 10SW053727 | **52** |
| 130/170hp NA | 10SW053729 | **61** |
| GTI SE 90 | 10SW053774 | **59** |
| Spark 90 (2019+) | 10SW039116 | **52** (27 ign A/B/B2/C + 4λ + 3 inj + 14 aux) |
| GTI SE 155 | 10SW025752 | 9 GTI-specific + shared |
| GTI/GTS 130/155/230hp 1503 2019 | 10SW040008 | GTI layout (injection+8 ign mapa) |
| GTI/GTS 130hp 1503 2020 | 10SW040962 | GTI layout (injection+8 ign mapa) |

> **Napomena:** Brojevi su rezultat stvarnog testa `python test/test_core.py` — 2026-03-19.

> **2026-03-18**: +2 nove mape (Lambda adapt 0x0268A0, Decel RPM ramp 0x028C30); knock params ispravljen 24→52 u16.
> **2026-03-19 (a)**: SC boost fuel Y-os potvrđena load%; Thermal enrichment X-os potvrđena load%; Lambda Prot. X-os=lambda skala (dijagonalna mapa, bez standardne osi); Deadtime dimenzije finalne (14×7, skala 0.5µs/raw); Ign Corr. osi identificirane (Y=RPM raw×40, X=load% raw/2.55); Lambda Adapt confidence 85→90%; Decel RPM Ramp confidence 75→80%, Spark negativno potvrđen; KFWIRKBA 2D sub: STG2=ORI (0/70), varijanta-specifično.
> **2026-03-19 (b)**: 4tec1503 kompletna analiza — 130/155/230hp 2019 identični binariji (0 razlika, potvrđeno "isti SW za sve snage"); 2020 vs 2019: 536B CODE razlika (25 blokova, bez promjene u mapama); rev limiter 7892 RPM @ 0x028E96 (isti kao 1630 130hp NA); SC boost factor = +41.2% (flat 23130, anomalija u 1503); GTI injection @ 0x022066 aktivno i razlikuje se od 1630; 8 extra ignition mapa @ 0x028310 prisutne i aktivne.

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
| **#10** | **0x02BCD0** | **Aux A1 — Operating Cond. timing** | 12×12 u8 | ×0.75°/bit | ANALYSED 2026-03-18: absolute timing 25.5–30°, all 144 cells active, NPRo +2.25–+6.75° |
| **#11** | **0x02BD60** | **Aux B1 — Knock/decel dip (R07)** | 12×12 u8 | ×0.75°/bit | ANALYSED: absolute 24–33.75°; R07 dips to 24° (retard zone); R04-R06 == #18.R00-R02; NPRo +2.25–+9.0° |
| **#12** | **0x02BDF0** | **Aux A2 — Operating Cond. timing** | 12×12 u8 | ×0.75°/bit | ANALYSED: absolute 25.5–30°, all active, NPRo +2.25–+6.75° |
| **#13** | **0x02BE80** | **Aux B2 — Knock/decel dip (R09)** | 12×12 u8 | ×0.75°/bit | ANALYSED: absolute 24–33.75°; R09 dips to 24° (retard zone); NPRo +2.25–+9.0° |
| **#14** | **0x02BF10** | **Aux A3 — Operating Cond. timing** | 12×12 u8 | ×0.75°/bit | ANALYSED: absolute 25.5–30°, all active, NPRo +2.25–+6.75° |
| **#15** | **0x02BFA0** | **Aux B3/SC — SC/boost-specific timing** | 12×12 u8 | ×0.75°/bit | ANALYSED: 300hp avg 29.8°; 130hp NA avg only 26.5° (flat rows) → SC-conditional; NPRo +2.25–+9.0° |
| **#16** | **0x02C030** | **Extended 1** | 12×12 u8 | ×0.75°/bit | CONFIRMED: NPRo STG2 modifies |
| **#17** | **0x02C0C0** | **Extended 2** | 12×12 u8 | ×0.75°/bit | CONFIRMED: NPRo STG2 modifies |
| **#18** | **0x02C150** | **Conditional/Fallback (partial)** | 12×12 u8 | ×0.75°/bit | ANALYSED: only 40 active cells (R00–R02); R00-R02 == #11.R04-R06; 130hp = constant 25.5° (safe min) |

**Layout:** Base address 0x02B730, stride 144B (12×12×1 byte), 19 maps total.

**Axes (shared, not embedded):**
- X (RPM, 12 points): 512–6400 RPM — global RPM axis @ 0x024F46
- Y (load, 12 points): rl% 0–90% — @ 0x02AFAC

**Knock correction maps (#08, #09):**
- Represent retard delta applied when knock is detected
- Negative/small values = less timing retard allowed
- ORI: 0–40 raw, STG2: caps at 40

**Auxiliary maps #10–#15 (analysed 2026-03-18):**
- All are ABSOLUTE timing maps (same range/format as base maps #00–#07)
- Two structural groups:
  - **Group A** (#10, #12, #14): narrow range 25.5–30° BTDC; all 144 cells active; NPRo adds +2.25–+6.75°
  - **Group B** (#11, #13, #15): wider range 24–33.75° BTDC; NPRo adds up to +9.0°
- #11 and #13 have "dip rows" (timing drops to 24.0–24.75°) — knock/decel retard zone
- #15 is SC/boost-specific: 130hp NA has drastically lower advance (26.5° avg) with flat rows
- NPRo STG2 modifies ALL 6 maps (consistent with advancing all timing tables)
- Exact operating condition names unknown without A2L/decompilation

**Conditional/fallback map #18:**
- Partial map: only R00–R03 contain data (40/144 active cells), R04–R11 = zero
- R00–R02 are IDENTICAL to #11.R04–R06 (exact byte match)
- 130hp NA version = constant 34 raw (25.5°) across all active rows — safe minimum
- 300hp version: 31.5–33.75° active range (higher than 130hp)
- STG2 modifies R00–R03 (+2.25–+9.0°), zero rows unchanged

### Ignition Correction (2D u8)

| Address | Name | Format | Scale | Notes |
|---------|------|--------|-------|-------|
| **0x022374** | Ignition correction / efficiency | 8×8 u8 | raw | **Y-axis (RPM) @ 0x022364**: raw×40=RPM; 300hp=[3000–8000], 130hp=[2520–8000]; **X-axis (load%) @ 0x02236C**: raw/2.55=%; 300hp=[20.8–100%], 130hp max=127=100% (normirano). VARIJANTA-SPECIFIČNO — osi se razlikuju! ORI: 145–200; STG2 caps >180→180. Confidence 70%. |

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
| **0x02220E** | SC boost fuel correction | u16 LE Q14 | 9×7 | ×100/16384-100% | none | **X-axis (RPM) @ 0x022200**: [1250,1875,2250,2500,3000,4000,4250] RPM (raw/8); **Y-axis (load%) @ 0x0221EC**: raw/64=%; 300hp=[46.9–179.7%], 130hp=[7.8–109.4%] — osi VARIJANTA-SPECIFIČNE! 130/170hp = all 0% (NA, no SC boost). |
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
> NOTE GTI90: Lambda main @ 0x0266F0 = flat 0.984 (only 5 unique values, effectively neutral). Lambda mirror @ 0x026C08 = ACTIVE calibration (0.90–1.02, 127 unique values). GTI90 uses mirror as primary lambda map.

### Rotax 1630 (all SC/NA variants)

| Address | Name | Format | Dims | Scale | Mirror | Notes |
|---------|------|--------|------|-------|--------|-------|
| **0x0266F0** | Lambda — target AFR (open-loop) | u16 LE Q15 | 12×18 | ÷32768 = λ | +0x518 → 0x026C08 | ORI: 0.965–1.073 λ; STG2: 0.984–1.080 λ |
| **0x026C08** | Lambda — mirror | u16 LE Q15 | 12×18 | ÷32768 = λ | | Mirror (+0x518) |
| **0x0265D6** | Lambda bias (global AFR trim) | u16 LE Q15 | 1×141 | ×100/32768-100% | none | 300hp: +0.47% lean; 230hp: +2.41%; 130/170hp: −0.07% |
| **0x0268A0** | Lambda adaptation base (STF base) | u16 LE Q15 | 12×18 | ÷32768 = λ | none | +0x1B0 from lambda main. Per-HP: **300hp λ0.966–1.039** (112 unique), **230hp λ1.009–1.059** (9u), **130hp λ0.999–1.025** (8u), **GTI90 λ0.984–1.014** (5u). STG2 changes 105/216. 2020 vs 2021 300hp: 105/216 razlika (drugačiji SW). Confidence **90%**. A2L nepoznat (KFLAMBAS?). |
| **0x026DB8** | Lambda trim (RPM×load) | u16 LE Q15 | 12×18 | ×100/32768-100% | none | Per-variant calibration; 300hp: 0.965–1.001 |
| **0x02469C** | Lambda protection (max injection) | u16 LE Q15 | 12×13 | ÷32768 = λ | none | ORI: diagonal 0.04–1.80; STG2: all 65535 (max freedom). **X-os: nije pronađena kao standardni vektor** — mapa je dijagonalna (R×C lambda pragovi), obje dimenzije kodiraju lambda vrijednosti direktno. 300hp=130hp IDENTIČNO u ORI. Y-os = load 12-pt @ 0x02AFAC. |
| **0x025ADA** | Lambda overtemp protection (sub-A) | u16 LE Q15 | 1×63 | ÷32768 | none | 300hp SC: all 0xFFFF (bypass); 130hp NA: 0.855–0.926 |
| **0x025B58** | Lambda neutral correction (sub-B) | u16 LE Q14 | 1×63 | ÷16384 | none | 300hp SC: flat 16448 = Q14 1.004 (+0.4%, neutral bypass); 130hp NA: active 0.855–0.933 |
| **0x0259D2** | Lambda efficiency sub-table (KFWIRKBA 2D sub) | u16 LE Q15 | 10×7 | ÷32768 | none | col[0] = embedded Y-axis (lambda Q15, NELINEARNO: [0.40,1.10,1.00,1.15,...]); X-axis @ 0x0259C4: λ 0.40–1.34. **STG2=ORI (0/70 razlika)**. 300hp vs 130hp: 41/70 razlika, vs GTI90: 39/70 razlika — varijanta-specifično. Confidence ~65%. |
| **0x02AE5E** | Lambda efficiency (KFWIRKBA) 41×18 | u16 LE Q15 | 41×18 | ÷32768 | none | X-axis: λ 0.66–1.80 (18 pts, embedded in row 0); Y-axis @ 0x02AE40: [3840..15360] SC / [3840..12800] GTI90; 300hp SC: bypass (rows=X-os); GTI90: active 0.51–0.71; STG2: lean side 0xFFFF |

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
| **0x02AA42** | Thermal enrichment (high CTS) | u16 LE | 8×7 | /64 = %; **Y-axis (CTS) @ 0x02AA32**: [80,90,100,110,120,130,140,150]°C; **X-axis (load) @ 0x02AA02**: [6400,8000,9600,11200,12800,14400,16000] — IDENTIČNO za sve varijante (300hp=130hp=230hp=GTI90). ORI: 168–210%; STG2: 105–208%. Mapa je IDENTIČNA za 300hp i 130hp — toplinska zaštita je ista bez obzira na SC! |

---

## 9. Other Maps

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| **0x02B600** | Idle RPM target | u16 LE | 5×12 | Direct RPM; 1840–3340 rpm; identical across all SC/NA variants; 5 conditions × 12 temp/time steps |
| **0x02202E** | DFCO RPM thresholds | u16 LE | 1×7 | 130/170hp: [853–2560]; 300hp: [1067–3413 rpm] |
| **0x028C30** | Decel/DFCO RPM ramp table | u16 LE | 16×11 (stride 22B) | 16 entries × 22B = 352B. Entry: 3× RPM ticks + 8× load values. **300hp**: col[2]=10670t=3878 RPM (const), col[0]=4791–5877 RPM; **130hp**: col[0]=10731–11129 RPM (drastično viši!), col[2]=8649 RPM; **GTI90**: col[0]=9255 RPM; **Spark 900**: nema validnih vrijednosti — nije aplicabilno. STG2 snižava RPM limite. Confidence **80%** (Spark negativno potvrđen). |
| **0x0256F8** | Knock threshold parameters | u16 LE | 1×**52** | **CORRECTED 2026-03-18: was 1×24, actual 1×52 (104B, 0x0256F8–0x02575F).** ORI: [0-1]=44237, rest=7967; STG2: [0-1]=65535, selective cells=39578 or 8090. 230hp: all remain 7967. Repeating groups of 7967/39578/8090. |
| **0x025900** | Injector deadtime (TVKL) | u16 LE | 14×7 | Hardware constant — DO NOT MODIFY. **Skala: ×0.5µs/raw** (R0[0]=2594→1297µs). Kraj @ 0x0259C4 (=EFF_CORR X-os, POTVRĐENO). X-os (napon baterije) nije embeddana — interio u ECU CODE. 300hp vs 130hp: praktički identični (isti HW injektori). |

---

## 10. Spark-Specific Aux Maps (10SW039116)

| Address | Name | Format | Dims | Notes |
|---------|------|--------|------|-------|
| 0x021748 | Spark DFCO RPM thresholds | u16 LE | 1×7 | Spark DFCO |
| 0x0241F8 | Spark cold start enrichment | u16 LE | 1×6 | Same as GTI90 |
| **0x0287A4** | Spark deadtime | u16 LE | 8×8 = 64 | Period-encoded ticks 9632–13440; potvrđeno binarnim skanom 2026-03-18 |
| 0x02408C | Spark knock thresholds | u16 LE | 1×24 | Same as GTI90 |
| 0x024676 | Spark start injection | u16 LE | 1×6 | Spark-specific |
| 0x024786 | Spark warm-up enrichment | u16 LE Q14 | 1×156 | |
| 0x0224A0 | Spark idle RPM target | u16 LE | 5×12 | |

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

| Map | 300hp SC | 230hp SC | 130/170hp NA | GTI90 NA | 1503 GTI | Spark 900 |
|-----|----------|----------|-------------|----------|----------|-----------|
| Ignition 19× (0x02B730) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (diff. addr) |
| GTI IGN 8× (0x028310) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Injection main (0x02436C) | ✅ | ✅ | ✅ | ✅ | ✅ (same as GTI90) | ❌ (diff. addr) |
| GTI injection (0x022066) | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Lambda main (0x0266F0) | ✅ | ✅ | ✅ | ✅ | ✅ (diff. values) | ❌ (diff. addr) |
| Torque (0x02A0D8) | ✅ | ✅ | ✅ | ✅ flat | ✅ (100–110%) | ❌ |
| SC bypass (0x020534/A8/9993) | ✅ active | ✅ active | ✅ present/low | ✅ present/low | ✅ present/low | ❌ |
| SC boost factor (0x025DF8) | ✅ +22.4% | ✅ | ✅ variable | ✅ −18.4% | ✅ **+41.2%** (flat 23130) | ❌ |
| Thermal enrichment (0x02AA42) | ✅ | ✅ | ✅ (diff. values) | ✅ | ✅ | ❌ |
| KFWIRKBA (0x02AE5E) | ✅ bypass | ✅ bypass | ✅ bypass | ✅ **ACTIVE** | ✅ bypass | ❌ |
| Lambda main flat (GTI90) | — | — | — | ✅ flat 0.984 | — | — |
| Lambda mirror active (GTI90) | — | — | — | ✅ active 0.90–1.02 | — | — |
| Rev limiter (0x028E96) | ✅ 8158 RPM | ✅ 8158 RPM | ✅ 7892 RPM | ❌ diff. addr | ✅ **7892 RPM** | ❌ diff. addr |

---

## 13. Rotax 1503 (4tec1503) — Kompletna analiza 2026-03-19

### 130hp vs 155hp vs 230hp (svi 10SW040008, 2019)

**POTVRĐENO: 130.bin == 155.bin == 230.bin — identični binariji, 0 razlika!**

- Sve tri datoteke su byte-for-byte identične (ukupno i u BOOT, CODE i CAL regijama)
- Razlika u snazi je isključivo mehanička (različit impeler ili opterećenje pogona)
- Isto ponašanje kao 1630 130hp vs 170hp (isti SW 10SW053729)

### 1503 vs 1630 NA — razlike u mapama

| Mapa | Adresa | 1503 vs 1630 | Napomena |
|------|--------|--------------|---------|
| RPM osa | 0x024F46 | IDENTIČNO | Isti globalni RPM niz |
| Rev limiter | 0x028E96 | IDENTIČNO | Obje = 5243 ticks = 7892 RPM |
| GTI injection | 0x022066 | RAZLIČITO (301/384B) | 1503 nešto niže vrijednosti pri visokom load |
| Q15 injection | 0x02436C | IDENTIČNO | Zajednička sekundarna tablica |
| Lambda main | 0x0266F0 | RAZLIČITO (409/432B) | 1503: λ 0.961–1.042, 1630: λ 0.984–1.026 (1503 lean/bogatije pri niskom load) |
| Torque | 0x02A0D8 | RAZLIČITO (211/512B) | 1503: 100–110% (MSB 128–141), 1630: 100–117% (MSB 128–150) |
| Ignition #00 | 0x02B730 | RAZLIČITO (100/144B) | Specifično za motor |
| GTI IGN #00–#07 | 0x028310+ | RAZLIČITO (136–143/144B) | Sve 8 mapa različite, ali isti raspon (40–67 raw) |
| Idle RPM | 0x02B600 | IDENTIČNO | Iste idle postavke |
| SC bypass shadow | 0x020534 | RAZLIČITO (4/49B) | Neznatna razlika |
| SC bypass active | 0x0205A8 | RAZLIČITO (15/49B) | Različite kalibracije, ali oba NA (niske vrijednosti) |
| SC boost factor | 0x025DF8 | RAZLIČITO (40/40) | **1503: flat 23130 (+41.2%) vs 1630 NA: varijabilno** |
| Lambda overtemp | 0x025ADA | RAZLIČITO (60/63B) | 1503: 0.157–1.161, 1630: flat 1.004 — 1503 ima puno aktivniju zaštitu |
| Knock thresholds | 0x0256F8 | RAZLIČITO (4/104B) | Neznatna razlika |
| Embedded cal | 0x012C7C | RAZLIČITO (132/132B) | Motor-specifična kalibracija |

### Rev limiter za sve 1503 varijante

| Varijanta | Adresa | Ticks | RPM | Status |
|-----------|--------|-------|-----|--------|
| 10SW040008 (130/155/230hp 2019) | 0x028E96 | 5243 | **7892 RPM** | POTVRĐENO |
| 10SW040962 (130hp 2020) | 0x028E96 | 5243 | **7892 RPM** | POTVRĐENO |

> **Napomena:** Rev limiter 7892 RPM je ISTI kao na 1630 130hp/170hp NA (10SW053729).
> Prethodna napomena u dokumentaciji "7700 RPM za GTI 155" odnosila se na stariju verziju 10SW025752 (2018).
> Novije verzije 10SW040008/10SW040962 (2019/2020) koriste 7892 RPM = isti limit kao 1630 NA.

### 2019 (10SW040008) vs 2020 (10SW040962) razlike

| Region | Adresa | Veličina | Napomena |
|--------|--------|---------|---------|
| Embedded cal | 0x012C7C | 132B | Motor-specifična kalibracija |
| Kalibracija ID | 0x02CD74 | 2B | Build ID razlika ('PI0' → 'PG0') |
| Mapa @ 0x029C58 | 0x029C58 | 64B | **NOVA u 2020**: aktivna 8×8 u8 tablica (7–48°, timing raspon) — u 2019 = sve nule |
| Parametri | 0x029492 | 20B | Konfiguracija promjena |
| Razno | ostalo | ~300B | Mali parametarski popravci |

- **KLJUČNI NALAZ**: Sve poznate mape (injection, lambda, torque, ignition, rev limiter) su IDENTIČNE između 2019 i 2020 verzije. Razlika je samo u kalibracijskim parametrima i jednoj novoj 8×8 tablici @ 0x029C58.

### SC bypass — NA vs SC analiza

1503 (sve varijante): SC bypass mapa **prisutna ali s niskim vrijednostima** (30–255 raw)
- Vrijednosti 30–36 pri punoj gazu = SC skoro potpuno otvoren = nema boost
- Isto ponašanje kao 1630 130hp NA — obje varijante NA imaju isti obrazac
- 1630 300hp SC: vrijednosti 38–131 = SC djelomično zatvoren = aktivni boost

### SC boost factor anomalija (@0x025DF8)

| Varijanta | Vrijednost | Q14 faktor | Napomena |
|-----------|-----------|-----------|---------|
| 300hp SC | 20046 (flat) | +22.4% | SC enrichment |
| 1630 130hp NA | 16191–20303 | +0.99–1.24 | Varijabilno |
| **1503 sve varijante** | **23130 (flat)** | **+41.2%** | **Anomalija — neočekivano visoko** |
| GTI90 NA | 13364 (flat) | −18.4% | Negativna korekcija |

> **UPOZORENJE**: 1503 SC boost factor (+41.2%) je viši od 300hp SC (+22.4%) unatoč tome što je NA motor. Fizikalni razlog nepoznat bez A2L dekompostiranja. Moguće da ECU koristi ovu tablicu drugačije na 1503 platformi ili da je bug u kalibraciji.

---

## 14. Spark 900 ACE — Kompletna mapa lista

### Ignition mape (27 ukupno — 4 serije)

Spark 900 ACE ima 4 serije ignition mapa, sve s bazom 0.75°/bit (osim serije C).

#### Serija A — osnovna timing mapa (8 mapa @ 0x026A76, stride 0x90)

| Index | Adresa | Naziv | Format | Raspon | Notes |
|-------|--------|-------|--------|--------|-------|
| A#00 | 0x026A76 | base_low_load | 12×12 u8 | 9°–42.75° | STG2 mijenja |
| A#01 | 0x026B06 | base_mid_load | 12×12 u8 | 9°–42.75° | |
| A#02 | 0x026B96 | base_high_load | 12×12 u8 | 9°–42.75° | |
| A#03 | 0x026C26 | boost_low | 12×12 u8 | 9°–42.75° | |
| A#04 | 0x026CB6 | boost_mid | 12×12 u8 | 9°–42.75° | |
| A#05 | 0x026D46 | idle | 12×12 u8 | 9°–42.75° | |
| A#06 | 0x026DD6 | (aux) | 12×12 u8 | 9°–42.75° | Prethodno propuštena |
| A#07 | 0x026E66 | (aux) | 12×12 u8 | 9°–42.75° | Prethodno propuštena |

Mirror kopija: +0x140 od base svake mape.

#### Serija B — uski raspon, knock/decel (8 mapa @ 0x0295C0, stride 0x90)

| Index | Adresa | Format | Raspon | Notes |
|-------|--------|--------|--------|-------|
| B#00–B#04 | 0x0295C0–0x029930 | 12×12 u8 | 20.25–27° | STG2 mijenja (+2–7°) |
| B#05–B#07 | 0x029940–0x0299C0 | 12×12 u8 | flat 20.25° | Sigurna rezervna mapa, STG2 ne mijenja |

#### Serija B2 — warm-up/adaptation (8 mapa @ 0x029B60, stride 0x90)

| Index | Adresa | Format | Raspon | Notes |
|-------|--------|--------|--------|-------|
| B2#00–B2#07 | 0x029B60–0x029F40 | 12×12 u8 | 20.25–27° | Svi modificirani STG2 (+2–7°) |

#### Serija C — u16 format (3 mape @ 0x02803A, stride 0x90)

| Index | Adresa | Format | Raspon | Notes |
|-------|--------|--------|--------|-------|
| C#00 | 0x02803A | 9×8 u16 LE | 110–125 raw × 0.25° = 27.5–31.25° | MSB uvijek 0, STG2 mijenja +0.5–1.0° |
| C#01 | 0x0280CA | 9×8 u16 LE | 27.5–31.25° | |
| C#02 | 0x02815A | 9×8 u16 LE | 27.5–31.25° | |

### Spark aux mape (14 ukupno)

| Adresa | Naziv | Format | Dims | Notes |
|--------|-------|--------|------|-------|
| **0x028E34** | Rev limiter | u16 LE | 1×1 | 5120 ticks = 8081 RPM (identično 2018/2021/STG2) |
| **0x027E3A** | Torque limit | u16 BE Q8 | 16×16 | Mirror +0x518; ×100/128 = % |
| **0x024EC4** | Lambda trim | u16 LE Q15 | 30×20 | STG2 izravnava na λ1.004 |
| **0x024468** | Overtemp lambda | u16 LE Q15 | 1×63 | Termalna zaštita (Q15) |
| **0x0222C0** | Lambda protection | u16 LE Q15 | 12×18 | Dijagonalna struktura, mirror +0x518 |
| **0x025BAA** | Thermal enrichment | u16 LE /64 | 8×7 | STG2 mijenja ~112B |
| **0x0237AC** | Neutral correction | u16 LE Q14 | 1×80 | Flat = 16384 (neutral, nema korekcije) |
| **0x021748** | DFCO RPM thresholds | u16 LE | 1×7 | Identično GTI90 @ 0x02202E |
| **0x0241F8** | Cold start enrichment | u16 LE | 1×6 | Identično GTI90 @ 0x02586A |
| **0x0287A4** | Injector deadtime | u16 LE | 8×8 | Period-encoded; 9632–13440 ticks |
| **0x02408C** | Knock thresholds | u16 LE | 1×24 | Identično GTI90 |
| **0x024676** | Start injection | u16 LE | 1×6 | Spark-specific |
| **0x024786** | Warm-up enrichment | u16 LE Q14 | 1×156 | STG2 povećava ~1.83× |
| **0x0224A0** | Idle RPM target | u16 LE | 5×12 | Identično GTI90 (isti idle) |

---

## 15. Spark 900 ACE — STG2 vs ORI diff summary

Spark ORI 2019 == Spark ORI 2021: **0 razlika** (identični binariji, isti SW 10SW039116).

| Region | Adresa | Veličina | Promjena |
|--------|--------|---------|---------|
| Lambda trim | 0x024EC4 | 1200B (30×20) | STG2 izravnava na 1.004 (lean bias uklonjen) |
| Lambda copies 1–2 | 0x025F5C–0x02617F | 2×256B | STG2 mijenja AFR cilj (bogaće pri WOT, lean na idle) |
| Warm-up enrichment | 0x024786 | 156×2B | STG2 povećava ~1.83× (više goriva pri zagrijavanju) |
| Lambda os (X-os) | 0x024775 | 16B | STG2 proširuje raspon lambda osi |
| Ignition timing | 0x027EBA–0x028760 | ~320B | STG2 povećava timing |
| Thermal enrichment | 0x025BAA | 112B | STG2 mijenja korekciju |

> Spark 2019 i 2021 su **identični** — isti SW, nema razlike u binariju.
