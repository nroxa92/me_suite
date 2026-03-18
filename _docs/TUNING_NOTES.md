# Tuning Notes — ME17.8.5 / Rotax Sea-Doo

> *Revidirano: 2026-03-18*

**Last updated:** 2026-03-18
**Source:** Binary analysis (ORI vs NPRo STG2), work_log.md, service manuals

---

## 1. NPRo STG2 Tune — 300hp (10SW066726 → 10SW040039)

### Overview

| Metric | Value |
|--------|-------|
| CODE diff bytes | 7087B (ori_300 2021 vs STG2) |
| CODE diff bytes | 6038B (ori_300 2020 vs STG2) |
| Total changed regions | 11462 vs backup_flash_082806 |
| BOOT modified | Yes (SW ID changed) |
| CAL modified | Unknown (not analyzed) |

### Changes confirmed by binary diff:

#### Ignition Timing (+ advance)
- Maps #00–#07 (base timing 0x02B730+): increased timing advance
- ORI: 24–33.75° BTDC
- STG2: up to 36.75° BTDC (+3° to +6° advance throughout map)
- Maps #16–#17 (0x02C030, 0x02C0C0): extended timing maps — NPRo confirms active
- Ignition correction (0x022374): STG2 caps all values >180 to exactly 180 (knock protection)

#### Injection (fuel increase)
- Injection main @ 0x02436C: all values increased (more fuel = richer)
- ORI raw max: ~49151; STG2 raw max: 65535 (saturated = maximum)
- Scale: Q15 (32768 = 100% base fuel), STG2 aggressive enrichment

#### Cold Start Enrichment (0x02586A)
- ORI: [500, 1000, 1690, 1126, 1096, 1024]
- STG2: [100, 1000, 1690, 1126, 1075, 1024]
- NPRo **reduced** first value 500→100 (80% less enrichment at coldest condition)
- Also reduced index [4]: 1096→1075

#### Knock Threshold (0x0256F8)
- ORI: [0-1]=44237, rest=7967
- STG2: [0-1]=65535 (max — harder to trigger retard), selective cells=39578 (31→154 u8)
- Effect: ECU is less aggressive at pulling timing on knock events

#### Lambda Efficiency / KFWIRKBA (0x02AE5E)
- STG2: all lean-side values (λ>1.0, x-indices 6–17) → 0xFFFF
- Effect: ECU ignores lean-side efficiency correction = maximum power priority

#### SC Bypass Maps
- 0x020534 (shadow): NPRo does NOT modify
- 0x0205A8 (active): NPRo modifies (decreased bypass = more boost)
- 0x029993 (extra): NPRo modifies differently

#### SC Boost Factor (0x025DF8)
- STG2 = ORI (identical, tuneri don't touch base SC enrichment)

#### Accel Enrichment (0x028059)
- dTPS axis changed: ORI=[0,5,150,200,350,1500], STG2=[0,5,150,300,600,900]
- Q14 values dramatically increased: ORI 76–160%, STG2 48–264%
- Much more aggressive transient enrichment

#### Thermal Enrichment (0x02AA42)
- STG2 aggressively reduces SC thermal protection:
  - Row 0 (80°C): ORI 195.2% → STG2 105.0%
  - Row 7 (150°C): ORI 188.5% → STG2 162.0%
- Effect: Less fuel enrichment at high coolant temps = more aggressive performance tune

#### Rev Limiter
- STG2 does NOT change rev limiter (0x028E96 = 5072 = 8158 RPM — identical to ORI)

#### Torque Map
- ORI: 93–119.5%; STG2: 92.2–122.7% (slightly expanded range)

---

## 2. NPRo STG2 — Spark 900 ACE (10SW011328 / 10SW039116 → 1037544876)

### Overview

| Metric | Value |
|--------|-------|
| CODE diff bytes | 3065B (2018 Spark ORI vs STG2) |
| SW ID format | Decimal: `1037544876` (BUDS2 format) |

### Changes confirmed:
- Injection: changes around 0x024EEC (different values)
- Ignition: changes @ 0x027EBA–0x028760 (u8 pairs — ignition trim maps)
- Timing advance: estimated +2.25° (based on u8 delta × 0.75°/bit)
- Torque: changes @ ~0x0295EE
- Lambda: changes @ ~0x025F57
- Rev limiter: **NOT CHANGED** — same 5120 ticks = 8081 RPM in ORI, STG2, 2018 and 2021

### NPRo Spark practical RPM:
- Stock in water: ~7900 RPM (impeller-limited)
- NPRo STG2 + modified impeller: up to 8500–8550 RPM in field reports
- ECU hard cut: 8081 RPM (unchanged by NPRo)

---

## 3. Rev Limiter Reference — All Variants

| Variant | SW ID | Address | Ticks | RPM | Status |
|---------|-------|---------|-------|-----|--------|
| 300hp SC | 10SW066726 | **0x028E96** | 5072 | **8158** | Confirmed |
| 230hp SC | 10SW053727 | **0x028E96** | 5072 | **8158** | Confirmed |
| 170hp NA | 10SW053729 | **0x028E96** | 5243 | **7892** | Confirmed |
| 130hp NA | 10SW053729 | **0x028E96** | 5243 | **7892** | Confirmed (same SW) |
| GTI155 NA | 10SW025752 | **0x028E96** | 5374 | **7700** | Confirmed |
| GTI90 NA | 10SW053774 | **0x028E7C** | 5875 | **~7043** | Estimated (different address!) |
| Spark 900 | 10SW039116 | **0x028E34** | 5120 | **8081** | Confirmed |
| Spark 900 (manual) | — | — | — | **8300** | BRP Tech Spec (engine-only, no load) |

### RPM Formula:
```
RPM = 40,000,000 / (ticks × 58/60)
```
- 40 MHz = TC1762 timer
- 58/60 = 60-2 tooth reluctor wheel (60 teeth minus 2 gap teeth = 58 effective)
- 3-cylinder Rotax

### Soft cut thresholds (0x028E98, 1630 series):
| Variant | Ticks | RPM |
|---------|-------|-----|
| 300/230hp | 5399 | 7664 RPM |
| 130/170hp | 5374 | 7700 RPM |
| GTI155 | 5505 | 7517 RPM |

---

## 4. Variant Comparison — Key Map Values

### Injection (rk Q15) differences:
| Variant | Typical range | Notes |
|---------|-------------|-------|
| 300hp ORI | up to 49151 | Base fuel, open SC |
| 300hp STG2 | up to 65535 | Saturated enrichment |
| 130/170hp | lower values | NA motor, less fuel needed |
| 230hp | between 130 and 300 | Weaker SC than 300hp |

### Lambda target map (0x0266F0):
| Variant | Lambda range | AFR range |
|---------|------------|---------|
| 300hp ORI | 0.965–1.073 | AFR 14.2–15.8 |
| 300hp STG2 | 0.984–1.080 | AFR 14.5–15.9 |
| 130/170hp | slightly leaner | NA motor |

### Lambda trim (0x026DB8):
| Variant | Range |
|---------|-------|
| 300hp ORI | 0.965–1.001 (mild lean bias at high load) |
| 300hp STG2 | 0.984–0.999 (equalized — NPRo unified trim) |
| 130hp | 0.984–1.001 (higher load slightly richer) |
| 230hp | 0.970–1.014 (wider variation — SC compensation?) |

---

## 5. What is Safe to Tune

### Safe to modify:
- Ignition timing maps (#00–#07) — advance by 1–3° with caution; monitor for knock
- Lambda target map (0x0266F0) — enriching at WOT/high load is safe
- Cold start enrichment (0x02586A) — reducing is generally fine (NPRo did it)
- Accel enrichment (0x028059) — increasing for better throttle response
- Torque map (0x02A0D8) — can increase limit, but TOPS uses this for protection
- DFCO thresholds (0x02202E) — affects engine braking character
- Idle RPM (0x02B600) — minor adjustments possible
- Lambda bias (0x0265D6) — global AFR trim

### Caution:
- Knock threshold (0x0256F8) — increasing means ECU will allow more detonation before reacting
- Thermal enrichment (0x02AA42) — reducing SC thermal protection risks component damage
- SC bypass (0x020534 / 0x0205A8) — only modify 0x0205A8 (active copy), not 0x020534 (shadow)
- Lambda efficiency KFWIRKBA (0x02AE5E) — setting lean-side to 0xFFFF removes correction safety

### DO NOT modify:
- Injector deadtime @ 0x025900 — hardware constant, not a tuning parameter
- CTS NTC lookup @ 0x0258AA — hardware calibration, changing causes wrong temp readings
- CAL region (0x060000+) — TriCore bytecode, NOT calibration data
- RSA signature @ 0x7E7C — Bosch private key required, cannot replicate

---

## 6. Code Region Caution — NPRo TC1762 Bytecode Edits

In the NPRo STG2 binary (`backup_flash_082806.bin`), it was found that:
- Function pointers @ 0x042xxx–0x044xxx were modified
- These are TC1762 machine code pointers (0x8006xxxx / 0x8008xxxx format)
- **DANGEROUS to copy** — directly copying NPRo's bytecode changes between SW versions will likely corrupt ECU or cause undefined behavior

NPRo's STG2 tune appears to include both map changes AND code modifications — the code changes are NOT safe to replicate manually.

---

## 7. Mirror Write Rule

All maps with a mirror MUST be written to both locations simultaneously:

| Map | Main | Mirror |
|-----|------|--------|
| Torque | 0x02A0D8 | 0x02A5F0 (+0x518) |
| Lambda | 0x0266F0 | 0x026C08 (+0x518) |
| Injection | 0x02436C | 0x0244EC (+0x180) |
| SC bypass (active) | 0x0205A8 | — (0x020534 is shadow, write separately if needed) |

The `map_editor.py` handles mirror writes automatically when `mirror_offset > 0`.

---

## 8. Checksum — When to Update

**MAP CHANGES IN CODE REGION (0x010000–0x05FFFF) = NO CHECKSUM UPDATE NEEDED**

Only update checksum if you change BOOT region (0x0000–0x7EFF):
- SW version string at 0x001A
- Bootloader code
- Note: RSA signature (0x7E7C–0x7EFF) must remain unchanged

```python
from core.checksum import ChecksumEngine
cs = ChecksumEngine(engine)
result = cs.update_all()  # Only updates if BOOT was changed
print(result["status"])   # "OK" (no change needed) or "UPDATED"
```

---

## 9. Procjena pouzdanosti mapa (Tool Confidence Assessment)

Koliko je svaka kategorija mapa pouzdano identificirana, bazirano na NPRo diff verifikaciji i binarnoj analizi:

| Kategorija | Pouzdanost | Osnova |
|------------|-----------|--------|
| **Paljenje (ignition)** | POUZDANA | 20 mapa potvrđeno NPRo difom — adrese, dimenzije i skaliranje 100% verificirani |
| **Gorivo (injection main)** | ~95% | KFTIPMF @ 0x02436C potvrđen, ~200B regija @ 0x024700 još neidentificirana |
| **Lambda/AFR** | POUZDANA | Potvrđeno: target map, trim, bias, KFWIRKBA — sve Q15 LE adrese verificirane |
| **Moment (torque)** | POUZDANA | 0x02A0D8 + mirror Q8 BE — potvrđeno NA vs SC razlika |
| **Rev limiter** | POUZDANA | Period encoding formula verificirana, adrese po variantama potvrđene |
| **SC bypass** | POUZDANA | 3 kopije identificirane, NPRo potvrđuje shadow vs active razliku |
| **GTI injection (0x022066)** | POUZDANA | GTI-specifična direktna tablica, NEMA mirrora — potvrđeno full CODE scan-om |
| **Thermal enrichment** | ~85% | 0x02AA42 identificiran NPRo difom, OS adrese potvrđene; fizikalni smisao logičan |
| **KFWIRKBA (0x02AE5E)** | ~80% | Format identificiran, ali parser markiran TODO — lambda os i dimenzije još se verifikuju |
| **Eff. corr. (0x0259D2)** | ~60% | Adresa identificirana, dimenzije confirmirane (~10×7), ali fizikalni smisao nije potvrđen |

> **KRITIČNO: CAL regija (0x060000+) = NE DIRATI**
> Izgleda kao kalibracija, ali je TriCore AUTOSAR/ASCET kompajlirani bytekod. 754 pokazivača u CODE regiji upućuju na CAL. Pisanje u CAL = korupcija firmware-a.
