# DTC Reference — Bosch ME17.8.5 / Sea-Doo

**Last updated:** 2026-03-18
**Source:** `core/dtc.py` (111 ECM codes), binary analysis
**Coverage:** ori_300 (10SW066726) as primary reference

---

## 1. DTC Architecture

### Standard (300hp / 230hp — ori_300 layout)

```
Code storage — two locations (main + mirror):
  Main range:   0x021700–0x0218FF  (u16 LE per code)
  Mirror range: 0x021A66–0x021C65  (u16 LE per code)
  Mirror offset: main_addr + 0x0366  (verified for all 111 codes)

Enable table @ 0x021080+ (min. 253 bytes, slots 0–252):
  Each byte = enable flag for one DTC monitoring channel:
    0x06 = active monitoring (fault triggers)
    0x05 = partial monitoring
    0x04 = warning only (no limp mode)
    0x00 = disabled
  Mapping table @ 0x0239B4: index = (code_addr - 0x021700) / 2 → enable_slot
```

### DTC OFF procedure (standard layout):
1. Zero the enable byte at `en_addr` (1 byte → 0x00)
2. Zero main code storage: write 0x0000 at `code_addr` (u16 LE)
3. Zero mirror code storage: write 0x0000 at `code_addr + 0x0366`
4. **Checksum NOT required** (only CODE region changes)

### SW variant differences:

| SW variant | Mirror offset | DTC base | Notes |
|------------|-------------|----------|-------|
| ori_300 (10SW066726) | 0x0366 | 0x0217B6 | Primary reference, 111 codes |
| rxpx300_17 (~10SW040039) | 0x0362 | ~0x021700 | Slightly different offset |
| spark_90 (10SW039116/011328) | different | ~0x021258 | **Single-storage, dtc_off BLOCKED** |
| rxtx_260 (524060) | n/a | ~0x020F80 | Single-storage, unsupported |

### Spark ECU architecture (DIFFERENT — do not apply standard procedure):
- Enable: 1 byte @ 0x0207A5 (P1550: 0x06 = enabled → 0x00 = off)
- State: @ 0x020E5E → write 0xFFFF to disable
- `dtc_off()` is **BLOCKED** for Spark in code (`single_storage=True`)

---

## 2. DTC Code List (111 ECM codes, ori_300)

### MAP Sensor (Intake Manifold Pressure)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0106 | MAP Sensor Out of Range | 0x0217EE | 0x021082 |
| P0107 | MAP Sensor Short to Ground | 0x0217EC | — |
| P0108 | MAP Sensor Open/Short to Battery | 0x0217EA | 0x021082 |

### IAT Sensor (Intake Air Temperature)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0112 | IAT Sensor Short to Ground | 0x0218BA | 0x021085 |
| P0113 | IAT Sensor Open/Short to Battery | 0x0218BC | 0x0210C6 |

### Coolant Temperature (CTS)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0116 | Coolant Temp Signal Not Plausible | 0x0218C6 | 0x021085 |
| P0117 | Coolant Temp Short to Ground | 0x0218C2 | 0x021085 |
| P0118 | Coolant Temp Open/Disconnected | 0x0218C4 | 0x0210C6 |
| P0217 | Coolant Temp High Detected | 0x0218C0 | 0x0210C6 |

### TPS (Throttle Position Sensor)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0122 | TPS1 Short Circuit to GND | 0x021894 | 0x0210A4 |
| P0123 | TPS1 Short Circuit to Battery | 0x021890 | 0x02108E |
| P0222 | TPS2 Short Circuit to GND | 0x021896 | 0x021084 |
| P0223 | TPS2 Short Circuit to Battery | 0x021892 | 0x021084 |
| P212C | TPS2 Electrical Lower-Range | 0x0217E4 | 0x02116A |
| P212D | TPS2 Electrical Upper-Range | 0x0217E2 | 0x021081 |
| P2620 | TPS Value Not Plausible | 0x0217E6 | 0x021081 |
| P2621 | TPS Electrical Lower-Range | 0x0217E0 | — |
| P2622 | TPS Electrical Upper-Range | 0x0217DE | 0x021081 |
| P2159 | TAS Synchronization Error | 0x021828 | — |
| P1120 | TOPS Violation TPS2 | 0x0217DC | — |

### Intake Air / Pressure

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0127 | Intake Air Temp Sensor Fault | 0x0218B8 | 0x0210C6 |
| P2279 | Air Intake Manifold Leak | 0x0217E8 | 0x02108A |
| P1106 | Altitude Correction Not Plausible | 0x0218E6 | 0x021083 |

### Lambda / O2 Sensor

> NOTE: Rotax ACE 1630 and 900 HO do NOT have a physical lambda sensor. These codes exist in firmware but never trigger.

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0130 | O2 Sensor Downstream | 0x021858 | 0x02113C |
| P0131 | O2 Sensor Signal Low | 0x021856 | 0x021081 |
| P0132 | O2 Sensor Signal High | 0x021854 | — |
| P0133 | O2 Sensor Slow Response | 0x02184E | 0x021083 |
| P0135 | O2 Sensor Heater Fault | 0x02182C | 0x021168 |
| P1030 | Lambda Heater Power Stage | 0x021834 | 0x021177 |
| P1130 | Lambda Sensor Upstream Catalyst | 0x02185A | 0x021081 |

### Mixture Adaptation

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0171 | Mixture Adaptation Lean (upper) | 0x021844 | 0x021177 |
| P0172 | Mixture Adaptation Rich (lower) | 0x021846 | 0x021083 |
| P1171 | Additive Mixture Trim Lean | 0x021848 | 0x021177 |
| P1172 | Additive Mixture Trim Rich | 0x02184A | 0x021083 |

### Oil Temperature

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0197 | Oil Temp Sensor Low | 0x0218CA | 0x021085 |
| P0198 | Oil Temp Sensor High | 0x0218C8 | 0x0210C6 |

### Injectors

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0201 | Injector 1 Power Stage Open | 0x021826 | 0x021083 |
| P0202 | Injector 2 Power Stage Open | 0x02181A | 0x021083 |
| P0203 | Injector 3 Power Stage Open | 0x021820 | — |
| P0261 | Injector 1 Open/Short to GND | 0x021824 | — |
| P0262 | Injector 1 Short to Battery | 0x021822 | 0x021083 |
| P0264 | Injector 2 Open/Short to GND | 0x021818 | — |
| P0265 | Injector 2 Short to Battery | 0x021816 | 0x021083 |
| P0267 | Injector 3 Open/Short to GND | 0x02181E | 0x021083 |
| P0268 | Injector 3 Short to Battery | 0x02181C | — |

### Fuel Pump

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0231 | Fuel Pump Open/Short to Ground | 0x0217BC | 0x0210B9 |
| P0232 | Fuel Pump Short to Battery | 0x0217BE | 0x021083 |

### Misfire

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0300 | Multiple Misfire Detected | 0x02185C | 0x021088 |
| P0301 | Misfire Cylinder 1 | 0x021862 | 0x021082 |
| P0302 | Misfire Cylinder 2 | 0x02185E | 0x021082 |
| P0303 | Misfire Cylinder 3 | 0x021860 | 0x0210AB |

### Knock Sensor

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0325 | Knock Sensor Fault | 0x021842 | 0x021083 |

### Crank / Cam Sensors

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0335 | Crankshaft Signal Error | 0x021814 | — |
| P0340 | Camshaft Signal Error | 0x021812 | 0x021083 |

### Ignition Coils / Power Stage

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0357 | Ignition Coil 1 Short to Y+ | 0x02183A | 0x021083 |
| P0358 | Ignition Coil 2 Short to Y+ | 0x021836 | 0x021083 |
| P0359 | Ignition Coil 3 Short to Y+ | 0x021838 | 0x021177 |
| P0360 | Ignition PS Max Error Cyl3 | 0x021840 | 0x021177 |
| P0361 | Ignition PS Max Error Cyl1 | 0x02183C | 0x021177 |
| P0362 | Ignition PS Max Error Cyl2 | 0x02183E | 0x021083 |

### Speed Sensor

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0500 | Vehicle Speed Sensor Open | 0x0218E2 | 0x021083 |
| P0501 | Vehicle Speed Sensor Fault | 0x0218E0 | 0x02108D |

### Starter / DESS

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0512 | Starter Motor Stage Fault | 0x0218A0 | 0x0210B1 |
| P0513 | Invalid DESS Key | 0x021882 | 0x021083 |

### Oil Pressure

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0520 | Oil Pressure Switch Functional Problem | 0x02188E | 0x021084 |
| **P0523** | **Oil Pressure Sensor Fault** | **0x02188C** | **0x02108E** |
| P0524 | Low Oil Pressure Condition | 0x02188A | 0x021084 |
| P0298 | Oil Pressure Derived Fault | 0x0218D6 | 0x021082 |

### EGT (Exhaust Gas Temperature)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0544 | EGT Sensor Open/Short to Battery | 0x0218B6 | 0x021085 |
| P0545 | EGT Sensor Short to Ground | 0x0218B2 | 0x021085 |
| P0546 | EGT Sensor Short to Battery | 0x0218B4 | 0x0210C6 |
| P2080 | EGT Sensor B Low | 0x0218B0 | 0x0210C6 |
| P2081 | EGT Sensor B High | 0x0218AE | 0x021085 |
| P2428 | High EGT Detected | 0x0218AC | 0x021087 |

### Battery Voltage

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0560 | Battery Voltage Not Plausible | 0x0218DE | 0x021082 |
| P0562 | Battery Voltage Too Low | 0x0218DC | — |
| P0563 | Battery Voltage Too High | 0x0218DA | 0x021082 |

### ECM Self-Diagnostics

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P0606 | ECM ADC Fault | 0x0217B6 | 0x021083 |
| P0610 | ECM Variant Coding Fault | 0x0218E4 | — |
| P062F | ECM EEPROM Fault | 0x0217DA | 0x021083 |
| P0650 | ECM Field ADC Fault | 0x021868 | — |
| P2610 | ECM RTC Fault | 0x02186A | 0x021082 |

### TOPS (Throttle Override Protection System)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P1502 | TOPS Switch Short to GND | 0x0218D2 | 0x021081 |
| P1503 | TOPS Switch Short to 12V | 0x0218CC | — |
| P1504 | TOPS Switch Open Circuit | 0x0218CE | 0x021081 |
| P1505 | TOPS Switch Active | 0x0218D0 | — |
| P1506 | TOPS Switch Fault Non-Plausible | 0x0218D4 | 0x0210A4 |
| P1509 | TOPS Functional Fault | 0x0218D8 | — |

### Boost / Olas Pressure Sensor

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| **P1550** | **Boost/Olas Pressure Sensor Fault** | **0x021888** | **0x02108A** |

### Throttle Actuator (DBW)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P1610 | Throttle Actuator Power Stage A | 0x0217F0 | — |
| P1611 | Throttle Actuator Power Stage B | 0x0217F2 | 0x021082 |
| P1612 | Throttle Actuator Return Spring | 0x0217F4 | — |
| P1613 | Throttle Actuator Default Position | 0x0217F6 | 0x021082 |
| P1614 | Throttle Actuator Pos Monitoring | 0x0217F8 | — |
| P1615 | Throttle Actuator Default Check | 0x0217FA | 0x021082 |
| P1616 | Throttle Actuator Learning Fault | 0x0217FC | 0x02117C |
| P1619 | Throttle Actuator Upper Limit | 0x021802 | 0x021083 |
| P1620 | Throttle Actuator Lower Limit | 0x021804 | 0x0210A0 |
| P1621 | Throttle Actuator Abort Adapt | 0x021808 | 0x0210BC |
| P1622 | Throttle Actuator Repeated Abort | 0x021806 | 0x021083 |

### DESS Key

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P1647 | DESS Key Communication A | 0x0218A6 | 0x021084 |
| P1648 | DESS Key Communication B | 0x0218A4 | — |
| P1649 | DESS Key Communication C | 0x0218A2 | 0x021084 |
| P1651 | DESS Key Voltage Low | 0x021866 | 0x021082 |
| P1652 | DESS Key Voltage High | 0x021864 | — |
| P1654 | DESS Key Out of Range | 0x02184C | 0x021177 |
| P1657 | DESS Key Signal A | 0x021852 | 0x021083 |
| P1658 | DESS Key Signal B | 0x021850 | 0x021177 |

### iBR (Intelligent Brake and Reverse)

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P1661 | iBR Malfunction | 0x02189A | 0x021084 |
| P1662 | iBR Torque Request Not Plausible | 0x02189C | — |

### Main Relay

| Code | Name | code_addr | enable_addr |
|------|------|-----------|-------------|
| P1679 | Main Relay Sticking | 0x0218A8 | — |

---

## 3. Most Commonly Disabled DTCs

| Code | Reason for disabling |
|------|---------------------|
| **P1550** | Boost/Olas sensor fault — commonly disabled on tuned/modified craft |
| **P0523** | Oil pressure sensor — disabled when sensor is removed/bypassed |
| **P0116** | Coolant temp range — disabled on overheating builds |
| **P0562** | Battery voltage low — disabled on high-draw builds |

---

## 4. DTC Scanner (Runtime Detection)

`DtcScanner.scan(data)` in `core/dtc.py` automatically detects the SW variant and addresses:

1. Scans for DTC code storage table signature
2. Determines mirror offset (0x0366, 0x0362, or single-storage)
3. Returns `DtcScanResult` with:
   - `mirror_offset`: confirmed offset
   - `addrs`: dict {dtc_code: main_addr}
   - `sw_hint`: detected SW variant string
   - `single_storage`: True = dtc_off is NOT safe (Spark, rxtx_260)

---

## 5. DTC OFF in GUI

Access via **DTC Off** tab in ME17Suite:

1. Load binary file (File → Open)
2. Switch to **DTC Off** tab
3. Select DTC from sidebar list (grouped by P0xxx / P1xxx)
4. Click **Disable** button (or use "Disable All" in Advanced dropdown)
5. Save the modified binary

> The "Svi DTC OFF" (Disable All) option is in the **▾ Advanced** dropdown menu.
> Spark ECU shows a warning — dtc_off is blocked for single-storage SW.
