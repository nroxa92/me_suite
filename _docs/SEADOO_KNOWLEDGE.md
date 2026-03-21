# Sea-Doo / Rotax — Master Knowledge Base

> Sintetizira sve PDF shop manual analize (2014–2022) + binary audit nalazi.
> Posljednje ažuriranje: 2026-03-21 (dodana sekcija 13: XCU platforma)

---

## SADRZAJ

1. [Motori — pregled po varijanti](#1-motori)
2. [Sensor specifikacije](#2-sensor-specifikacije)
3. [ECU hardware — konektori i pinovi](#3-ecu-hardware)
4. [CAN bus](#4-can-bus)
5. [Gorivo i injekcija](#5-gorivo-i-injekcija)
6. [RPM limiteri](#6-rpm-limiteri)
7. [Supercharger](#7-supercharger)
8. [Svjećice i paljenje](#8-svjecice-i-paljenje)
9. [SW verzije — brzi pregled](#9-sw-verzije)
10. [Razlike po godištu](#10-razlike-po-godistu)
11. [Limp home i zaštite](#11-limp-home)
12. [Impeller / jet pump](#12-impeller)
13. [XCU platforma (2024+)](#13-xcu-platforma-2024)

---

## 1. MOTORI

### Rotax 1630 ACE (3-cil, SOHC)

| Parametar | 300hp SC | 230hp SC | 170hp NA | 130hp NA |
|-----------|----------|----------|----------|----------|
| Zapremina | 1630.5cc | 1630.5cc | 1630.5cc | 1630.5cc |
| Bore × Stroke | 100×69.2mm | 100×69.2mm | 100×69.2mm | 100×69.2mm |
| Kompresija | 8.4:1 | 8.3:1 | 11:1 | 11:1 |
| Ventili | 12 (4/cil) | 12 (4/cil) | 12 (4/cil) | 12 (4/cil) |
| Ventil lifteri | Hydraulic | Hydraulic | Hydraulic | Hydraulic |
| Throttle body | **62mm** ETA | **62mm** ETA | **62mm** ETA | **62mm** ETA |
| Idle RPM (spec) | 1700±50 | 1700±50 | 1700±50 | 1700±50 |
| Max HP RPM | ~8000 | ~8000 | ~8000 | ~8000 |
| Svjećice | NGK KR9E-G | NGK KR9E-G | NGK DCPR8E | NGK DCPR8E |
| Svjećica gap | 0.7–0.8mm | 0.7–0.8mm | 0.8–0.9mm | 0.8–0.9mm |
| Gorivo tlak | 386–414 kPa | 386–414 kPa | 386–414 kPa | 386–414 kPa |

**Napomene:**
- 130hp i 170hp = identičan motor + isti SW (10SW053729) — razlika samo u impelleru/opterećenju
- ECU idle setpoint ~1840 RPM (ne 1700) jer SC parazitni moment traži kompenzaciju
- 2022 koristi iste motore kao 2021 — nema novog ME17 ECU-a u 2022

### Rotax 1503 4-TEC (3-cil, SOHC — stariji motor)

> **NAPOMENA**: 230hp postoji i na 1503 (GTI SC) i na 1630 ACE — to su RAZLIČITI motori s različitim SW-om i mapama!

| Parametar | **230hp SC** | 260/215hp SC | 155hp NA | 130hp NA |
|-----------|--------------|--------------|----------|----------|
| Zapremina | 1493.8cc | 1493.8cc | 1493.8cc | 1493.8cc |
| Bore × Stroke | 100×63.4mm | 100×63.4mm | 100×63.4mm | 100×63.4mm |
| Kompresija | **8.4:1** | **8.4:1** | **10.6:1** | **10.6:1** |
| Ventili | 12 (4/cil) | 12 (4/cil) | 12 (4/cil) | 12 (4/cil) |
| Throttle body | **62mm** | **62mm** | **62mm** | **62mm** |
| Idle RPM (spec) | **1800±50** | **1800±50** | **1800±50** | **1800±50** |
| Max HP RPM | 8000 (SC) | 8000 (SC) | 7300 (155hp) | — |
| Injektor boja | plava | plava | plava | plava |
| Injektor otpor | 11.4–12.6 Ω | 11.4–12.6 Ω | 11.4–12.6 Ω | 11.4–12.6 Ω |
| Svjećice | NGK DCPR8E | NGK DCPR8E | NGK DCPR8E | NGK DCPR8E |
| Svjećica gap | 0.7–0.8mm | 0.7–0.8mm | 0.7–0.8mm | 0.7–0.8mm |
| Gorivo tlak | 386–414 kPa | 386–414 kPa | 386–414 kPa | 386–414 kPa |
| Magneto | 360W@6000RPM | 360W@6000RPM | 360W@6000RPM | 360W@6000RPM |
| SW (2018) | 10SW025021 | 10SW000776 | 10SW025752 | 10SW025022 |
| SW (2019) | 10SW040008 | — | 10SW040008 | 10SW040008 |

*Napomena: 1503 koristi 62mm throttle body (ne 60mm!). Idle 1800 RPM (ne 1700 — to je 1630). 230hp 1503 ≠ 230hp 1630 ACE — drugačiji motori, drugačiji SW, drugačije mape!*

### Rotax 900 ACE (3-cil, DOHC)

| Parametar | 900 ACE (60hp) | 900 HO ACE (90hp) |
|-----------|----------------|-------------------|
| Zapremina | 899.31cc | 899.31cc |
| Bore × Stroke | 74×69.7mm | 74×69.7mm |
| Kompresija | 11:1 | 11:1 |
| Ventili | 12 (4/cil) | 12 (4/cil) |
| Throttle body | 46mm Dell'Orto (heated) | 46mm Dell'Orto (heated) |
| Idle RPM | 1400±100 (u vodi) | 1450 RPM (vehicle spec) |
| Max HP RPM | 7000 RPM (60hp) | 8000 RPM (90hp) |
| Gorivo tlak | 386–414 kPa | 386–414 kPa |
| Svjećice | NGK CR8EB | NGK CR8EB |
| Svjećica gap | 0.70–0.80mm | 0.70–0.80mm |

**Ključna razlika 60hp vs 90hp:**
**ISKLJUČIVO kalibracija ECM-a** — isti hardware, isti senzori, ista throttle body, isti injektor. BUDS2 mijenja samo model number, ne SW.

---

## 2. SENSOR SPECIFIKACIJE

### CPS — Crankshaft Position Sensor

| Motor | Otpor @ 20°C | Output voltage (okretanje) | ECM pin (1630) |
|-------|-------------|---------------------------|----------------|
| 1630 ACE | 775–950 Ω | ~3.7 Vac | — |
| 1503 NA | 775–950 Ω | ~3.7 Vac | — |
| 900 ACE | 775–950 Ω | ~3.7 Vac | H1-K2 |

Trigger wheel: 60-2 (58 zuba aktivna) — osnova za RPM period formula.

### CTS — Coolant Temperature Sensor

| Motor | Overheat threshold |
|-------|--------------------|
| 1630 ACE | 110°C |
| 1503 NA | 110°C |
| 900 ACE | 100°C |

Karakteristika otpora (NTC, iz 2016 1630 ACE shop manuala):

| Temp °C | Otpor MIN Ω | Otpor MAX Ω |
|---------|------------|------------|
| -40 | 38 457 | 52 630 |
| -10 | 8 208 | 10 656 |
| +20 | 2 233 | 2 780 |
| +80 | 297 | 349 |
| +120 | 105 | 122 |

### MAPTS — Manifold Abs. Pressure + Temp Sensor (temp dio)

Ista klasa NTC termistora kao CTS:

| Temp °C | Otpor MIN Ω | Otpor MAX Ω |
|---------|------------|------------|
| -40 | 40 528 | 56 935 |
| -10 | 8 103 | 10 919 |
| +20 | 2 193 | 2 863 |
| +80 | 294 | 368 |
| +120 | 98 | 122 |

Pressure funkcija: napajanje 5V na pin 3, signal na pin 4.

### OTS — Oil Temperature Sensor (i EGTS — identična krivulja)

| Temp °C | Otpor MIN Ω | Otpor MAX Ω |
|---------|------------|------------|
| -30 | 11 800 | 13 400 |
| +20 | 2 200 | 2 800 |
| +80 | 280 | 370 |
| +120 | 100 | 125 |

### OPS — Oil Pressure Switch

| Stanje | Otpor |
|--------|-------|
| Motor ugašen (bez tlaka) | ~0 Ω (normally-closed) |
| Motor radi (tlak > 180–220 kPa) | ∞ (open circuit) |

### EGTS — Exhaust Gas Temperature Sensor

| Motor | Overheat threshold |
|-------|--------------------|
| 1630 ACE | 110°C |
| 1503 NA | 110°C |
| 900 ACE | 95°C |

*OTS/EGTS dijele identičnu otpornosnu krivulju (NTC termistori iste klase).*

### Knock Sensor (KS)

| Motor | Otpor @ 20°C | Test threshold |
|-------|-------------|----------------|
| Svi (1630/1503/900) | ~5 MΩ | >5000 RPM |
| ECM pin (900 ACE) | A-C3 / A-G2 | — |

### Ignition Coil

| Motor | Primary Ω | Secondary kΩ |
|-------|-----------|--------------|
| 1630 ACE | 0.80–0.97 Ω | N/A |
| 1503 4-TEC | **0.85–1.15 Ω** | **9.5–13.5 kΩ** |
| 900 ACE | 0.85–1.15 Ω | 9.5–13.5 kΩ |

### Magneto / Stator

| Motor | Output | Winding otpor (faza-faza) | Insulation |
|-------|--------|--------------------------|------------|
| 1630 ACE | 420W @ 6000 RPM | 0.1–1.0 Ω | ∞ prema masi |
| 1503 4-TEC | 360W @ 6000 RPM | 0.1–1.0 Ω | ∞ prema masi |

### Injektori

| Motor | Otpor @ 20°C | Boja |
|-------|-------------|------|
| 1630 ACE | 11.4–12.6 Ω | Žuto-zelena |
| 1503 NA | 11.4–12.6 Ω | Plava |
| 900 ACE | 11.4–12.6 Ω | — |

Svi motori iste resistance klase — isti tip Bosch direktnih injektora.

### Lambda sonda (LSU 4.9)

Wideband — Bosch LSU 4.9 na svim ME17.8.5 motorima (1630/1503/900 ACE).
Otpor grijača: ~6–9 Ω (hladna), operativna temp >700°C.

---

## 3. ECU HARDWARE

### Bosch ME17.8.5

- MCU: Infineon TC1762 (TriCore, Little Endian, 32-bit)
- ECM referentna fotografija: `smr2009-027-005` (isti hardware za sve ME17.8.5 motore)
- ECU P/N: naveden samo na fizičkoj naljepnici modula (nije u tekstu manuala)
- EEPROM P/N prefiks: 10375500xx (HW 064) — 1630 ACE + GTI90
- EEPROM: 32KB eksterna
- Flash size: 0x178000 (1,540,096 B)
- Memory layout: BOOT=0x0000–0x7EFF, CODE=0x010000–0x05FFFF, CAL=0x060000–0x15FFFF
- Checksum: CRC32-HDLC, BOOT regija (0x0000–0x7EFF), CS @ 0x30
- Montažni torque: **5.5 Nm ±0.6 Nm + Loctite 243** (ECM na intake manifoldu)
- Zamjena zahtijeva BUDS2: unos serial number, VIN, customer data

### Fuse tablica (1630/1503 — 2016+)

| Fuse | A | Namjena |
|------|---|---------|
| F13 | 10A | Injektor + Paljenje cil 1 (rear) |
| F14 | 10A | Injektor + Paljenje cil 2 |
| F15 | 10A | Injektor + Paljenje cil 3 |
| F18 | 10A | Fuel pump |
| F19 | 15A | ECM napajanje |
| F3  | 3A | START/STOP switch |

### Konektori — 1630 ACE HO

ECM ima 3 konektora (A, B, H). CAN pinovi: Connector B, pin C1 (CAN HI), pin C2 (CAN LO).

### CAN wire boje po godištu

| Godište | CAN HI | CAN LO |
|---------|--------|--------|
| 2016 (1630/1503) | WHITE/RED | WHITE/BLACK |
| 2017–2021 | WHITE/BLACK | WHITE/BEIGE |

*Uvijek vjerovati wire colour na stvarnom konektoru — BRP je mijenjao standard između generacija.*

---

## 4. CAN BUS

### Topologija

```
ECU (ME17.8.5)
   ├── Diagnostic bus: 500 kbps (OBD konektor / IXXAT bench)
   │   IDs: 0x0102, 0x0103, 0x0110, 0x0316, 0x0342, 0x0516, 0x04CD
   │
   └── Cluster bus: 250 kbps (Delphi 20-pin J1)
       ECU→SAT: 0x0578 (267ms), 0x0400 (311ms), 0x0408 (267ms)
       SAT→ECU: 0x0186 (heartbeat), 0x01CD (critical), 0x04CD (DESS 1Hz)
```

### Diagnostic bus IDs (500kbps)

| ID | Sadržaj | Period |
|----|---------|--------|
| 0x0102 | RPM (×0.25), coolant temp (byte[1]-40°C), SW scalar byte[4] | ~20ms |
| 0x0103 | DTC count, engine state | ~20ms |
| 0x0110 | Temperature mux | ~100ms |
| 0x0316 | EOT (Engine Oil Temp) | ~100ms |
| 0x0342 | MUX: ECT/MAP/MAT | ~100ms |
| 0x0516 | Hardware ID | ~1000ms |
| 0x04CD | DESS keepalive | ~1000ms |

### SW scalar (0x0102 byte[4])

| Vrijednost | SW / model |
|------------|------------|
| 0x14 (20) | 300hp (10SW066726) |
| 0x0E (14) | 230hp (10SW053727) |
| 0x12 (18) | 130/170hp (10SW053729) |

### CAN checksum i rolling counter

- XOR checksum: byte[7] = XOR(byte[0..6]) — vrijedi za 0x102/0x103/0x110/0x122/0x516
- Rolling counter: byte[6] = 0x00–0x0F (inkrementira svaki paket)

### Moduli po modelu

| Model | Broj CAN modula |
|-------|-----------------|
| Spark bez iBR | 2 (ECM + Gauge) |
| Spark s iBR | 3 (ECM + iBR + Gauge) |
| GTI/GTX/RXP/RXT | 3+ (ECM + SAT + iBR + ...) |

---

## 5. GORIVO I INJEKCIJA

### Tlak goriva

Svi motori (1630/1503/900 ACE): **386–414 kPa (56–60 PSI)**
Regulacija je u fuel pump modulu — nije odvojeni regulator.

### Injektor karakteristika (binary analiza)

- `0x02436C`: injector **linearization curve** (1D, 16 breakpointa × Q15)
  IDENTIČNA za 130/170/230/300hp — samo injektor deadtime se razlikuje
- `0x022066`: **prava 2D fuel mapa** (12×16 u16 LE Q15)
  RAZLICITA po snagama — ovo je primarna tuning mapa

### 2D fuel mapa Q15 max vrijednosti (0x022066)

> **230hp ≠ 230hp**: 230hp SC na 1630 ACE i 230hp SC na 1503 su RAZLIČITI motori s RAZLIČITIM mapama i SW-om!

| SW / model | Max Q15 vrijednost | Max duty |
|------------|-------------------|----------|
| 300hp SC (1630 ACE) | 0.944 | ~94% |
| **230hp SC (1630 ACE, 10SW053727)** | **0.785** | **~78.5%** |
| **230hp SC (1503, 10SW025021)** | **0.952** | **~95.2%** |
| 170hp NA | 0.524 | ~52.4% |
| 130hp NA | 0.524 | ~52.4% (=170hp) |
| GTI 130/155hp (1503) | 0.440 | ~44% |
| GTI90 (900 HO ACE) | 0.572 | ~57.2% |

---

## 6. RPM LIMITERI

### Period encoding formula

```
RPM = (40_000_000 × 60) / (ticks × 58)
```
*(40MHz kristal, 60 sekundi, 60-2 kotačić = 58 aktivnih zuba)*

### Izmjereni limiteri (binary) — stvarni ECU cut

> **NAPOMENA**: Ovo su stvarni ECU rev limiter vrijednosti izmjerene iz binarnih fajlova (sve potvrđeno).
> 130hp i 170hp NA dijele ISTI SW (10SW053729) → isti ECU limit = 7892 RPM.
> 230hp SC 1630 (10SW053727) potvrđen binarno 2026-03-21 — identičan 300hp SC (5072t = 8158 RPM).

| SW / model | Adresa | Ticks | RPM (ECU limit) |
|------------|--------|-------|-----------------|
| 300hp SC (2019+) | 0x028E96 | 5072 | **8158** |
| 230hp SC (1630, 10SW053727) | 0x028E96 | 5072 | **8158** *(=300hp, potvrđeno 2020+2021)* |
| 170hp NA (1630) | 0x028E96 | 5243 | **7892** (= 130hp, isti SW) |
| 130hp NA (1630) | 0x028E96 | 5243 | **7892** |
| GTI90 (900 HO ACE) | 0x028E7C | 5875 | **7043** |
| Spark 900 ACE | 0x028E34 | 5120 | **8082** |
| 300hp SC (2018) | 0x028E94 | 5072 | **8158** |
| 230hp SC (2018, 1503, 10SW025021) | 0x028E96 | 5399 | **7664** |
| 230hp SC (2019, 1503, 10SW040008) | 0x028E96 | 5243 | **7892** |
| 230hp SC (2017, 1503, 10SW012999) | 0x028E94 | 5126 | **8072** |
| 260hp SC (2017, 1503, 10SW012502) | **0x026E1E** | 5126 | **8072** *(2016 gen adresa!)* |
| 260hp SC (2016, 1503, 10SW000778) | **0x026E1E** | 5126 | **8072** |
| 215hp SC (2016, 1503, 10SW000776) | **0x026E1E** | 5126 | **8072** *(=260hp, isti limit)* |
| 300hp SC (2016, 1630) | 0x028E94/0x028E44 | 5126 | **8072** |

**Napomena (2016 gen 1503 adrese):**
- `0x026E1E` = main rev limiter u 2016 gen 1503 (i 2017 gen 260hp!)
- Mirror @ `0x026D82` (156B = 0x9C ranije)
- Offset vs 1630 ACE ekvivalenta (0x028E94): −0x2076 bytes
- 215hp i 260hp imaju **isti rev limit** (8072 RPM) — razlika je samo u kalibraciji snage
- `0x026E1E` NE radi za 2017 gen 230hp (10SW012999) — taj SW koristi 0x028E94

### RPM iz shop manuala — dijagnostički operativni RPM

> **VAŽNO**: Manual RPM ≠ ECU rev limiter!
> Manual RPM = očekivani WOT RPM u vodi (impeller pod opterećenjem).
> Ispod = nedovoljno gorivo/zrak; iznad = jet je u bypass.
> Bez opterećenja (van vode) svi motori vrte VIŠE od manual specifikacije.

| Motor | Manual WOT RPM (u vodi) |
|-------|-------------------------|
| 1630 ACE 300/230hp SC | ~8000–8200 RPM |
| 1630 ACE 170hp NA | ~8000–8400 RPM |
| 1630 ACE 130hp NA | ~7800–8100 RPM |
| 1503 NA (130/155hp) | ~7500–8000 RPM |
| 900 ACE HO (90hp) | ~7500–8000 RPM |
| 900 ACE (60hp) | ~6500–7000 RPM |
| Spark u vodi (stock) | ~7900 RPM (propeler-limitirano) |

*Razlika spec vs binary: binary mjeri soft-cut (ignition cut početak), spec je hard-cut (fuel+ign cut).*

---

## 7. SUPERCHARGER

### Ključna činjenica — isti SC hardware za sve modele

> **230hp 1503, 260hp 1503, 230hp 1630 i 300hp 1630 — SVI KORISTE ISTI fizički SC kompresor.**
> Razlika u snazi dolazi isključivo od:
> 1. **SC bypass ventil** (software: opcode 0x2626/0x1F1F/0x2020 — više bypass = manje boosta)
> 2. **Motor displacement** (1503cc vs 1630cc)
> 3. **Fuel/ignition kalibracija**
> Hardware SC kompresor je identičan — **ne postoji "slabiji" ili "jači" fizički SC za različite snage.**

### 1630 ACE SC — servisni podaci

| Model | Max SC RPM | Clutch slip (novi) | Clutch slip (min) |
|-------|-----------|--------------------|--------------------|
| 300hp | 46800 RPM | 14–17 N·m | 11 N·m |
| 230hp | 45000 RPM | 9–14 N·m | 7 N·m |

**Napomena:** SC je "maintenance free" od 2019+ generacije — nema periodičnog servisa SC-a.

### SC bypass opcode

| SW / model | Opcode | Adresa |
|------------|--------|--------|
| 300hp SC (2020+) | 0x2626 | 0x0205A8 |
| 230hp SC (2020+, 1630) | 0x1F1F | 0x0205A8 |
| 130/170hp NA (2020+) | 0x1E1E | 0x0205A8 |
| GTI90 (900 HO ACE) | 0x1C1B | 0x0205A8 |
| 300hp SC (2016) | 0x3333 | 0x0205A8 |
| 300hp SC (2018–2019) | **0x3333** @ active; 0x2626 @ shadow | 0x0205A8 / 0x020534 |
| 215/260hp SC (2016, 1503) | 0x2020 | 0x012C60 (!!) |
| 230hp SC (2017, 1503) | 0x1F1F | 0x0205A8 |

**Napomena (bypass shadow vs active):**
- `0x020534` = shadow kopija, `0x0205A8` = active kopija, `0x029993` = extra kopija
- NPRo mijenja samo `0x0205A8` i `0x029993` — shadow ostaje nepromjenjen
- **2018/2019 ORI**: shadow (0x020534) = 0x2626, ali active (0x0205A8) = **0x3333** (nije 0x2626!)
- **2020+ ORI**: obje adrese = 0x2626 — usklađene

### SC boost factor

| Motor | Adresa | Vrijednost | Q14 | Efekt |
|-------|--------|-----------|-----|-------|
| 1630 ACE | 0x025DF8 | 20038 | 1.224 | +22.4% |
| 4-TEC 1503 (svi, 2018+) | 0x025DF8 | 23130 | 1.412 | +41.2% |
| 4-TEC 1503 (2017 SC) | 0x025B4E | 23130 | 1.412 | +41.2% |

*1503: isti boost factor za SC i NA varijante — boost kompenzacija hardcoded u kalibraciji.*

---

## 8. SVJECICE I PALJENJE

### Svjećice

| Motor | Tip | Gap |
|-------|-----|-----|
| 1630 ACE 300hp | NGK KR9E-G | 0.7–0.8mm |
| 1630 ACE 230hp | NGK KR9E-G | 0.7–0.8mm |
| 1630 ACE 130/170hp | NGK DCPR8E | 0.8–0.9mm |
| 1503 NA | NGK DCPR8E (pretpostavka) | 0.8–0.9mm |
| 900 ACE | NGK CR8EB | 0.70–0.80mm |

### Ignition mape (binary, 1630 ACE)

- Base: IGN_BASE = 0x02B730 (2019+), 0x02B72C (2018 10SW023910)
- Format: 12×12 u8, scale = 0.75°/bit
- Stride: 144B (svaka mapa)
- Ukupno 19 mapa: #00-#07 base, #08-#09 knock trim, #10-#15 aux, #16-#17 extended, #18 fallback

---

## 9. SW VERZIJE — BRZI PREGLED

### Generacijski pregled

| Generacija | SW range | Layout | Podrška |
|------------|----------|--------|---------|
| 2016 gen | 10SW0007xx, 10SW004675 | Stariji ME17, drugačije adrese | ~24 mape (ograničena) |
| 2017 gen | 10SW012999 | Parcijalna 2018 migracija (-0x2AA offset za neke mape) | ~57 mapa |
| 2018+ | 10SW023910+ | Standardni layout | 56–64 mape |

### Kompletna tablica verificiranih SW-ova

| SW ID | Motor | HP | Godište | Mapa count | Ključna napomena |
|-------|-------|----|---------|-----------:|------------------|
| 10SW000776 | 1503 | 215 SC | 2016 | ~24 | SC bypass @ 0x012C60 = 0x2020 |
| 10SW000778 | 1503 | 260 SC | 2016 | ~24 | Referentni 2016 1503 dump |
| 1037524060 | 1503 | 260 SC | ~2015 | ~24 | Decimalni format, 1330B razlika |
| 10SW004675 | 1630 | 300 SC | 2016 | ~24 | SC bypass = 0x3333 (ne 0x2626!) |
| 10SW012999 | 1503 | 230 SC | 2017 | ~57 | -0x2AA offset za SC mape |
| 10SW023910 | 1630 | 300 SC | 2018 | 63 | 2× injekcija + 2× paljenje |
| 10SW025021 | 1503 | 230 SC | 2018 | 59 | Fizički SC ventil @ 0x020534 |
| 10SW025022 | 1503 | 130 NA | 2018 v1 | 60 | =155hp v1 identičan |
| 10SW025752 | 1503 | 155 NA | 2018 v2 | 60 | =130hp v2 identičan |
| 10SW040008 | 1503 | 130/155/230 | 2019 | 59 | ISTI SW za SVE snage! |
| 10SW040039 | 1630 | 300 SC | 2019 | 57 | NPRo base; NPRo ne mijenja SW string |
| 10SW039116 | 900 | 90 HO | 2019–21 | 54 | MD5 identičan sve 3 godine! |
| 10SW011328 | 900 | 90 HO | 2016/18 | ~54 | Iste adrese, drukčija kalibracija |
| 10SW040962 | 1503 | 130 NA | 2020 | 59 | — |
| 10SW053727 | 1630 | 230 SC | 2020–21 | 56 | — |
| 10SW053729 | 1630 | 130/170 NA | 2020–21 | 64 | Isti SW za 130 i 170hp! |
| 10SW053774 | 900 HO | GTI90 | 2020–21 | 62 | DTC @ 0x0217EE; IGN = 1630 adresa! |
| 10SW054296 | 1630 | 300 SC | 2020 | 57 | — |
| 10SW066726 | 1630 | 300 SC | 2021 | 57 | Primarni referentni dump |

---

## 10. RAZLIKE PO GODISTU

### 2016 → 2017

- 1630 ACE: SW 10SW004675 → 10SW004672 (1265B razlika — minimalna)
- 1503: kompletno novi SW (10SW012999 — parcijalna CODE migracija)
- 2016 SC bypass = 0x3333, 2018+ = 0x2626 (različita vrijednost!)
- 2016: BUDS + BUDS2; 2017+: SAMO BUDS2

### 2017 → 2018

- 1630 SC: 2018 (10SW023910) dobiva **2× injection set** (0x022066 + 0x02436C) i **2× ignition set**
- 1503: CODE refaktor — offset +0x2AA za SC mape; lambda/boost adrese migriraju
- CAN TX tablica premješta se: 0x03DF0C (2019+) vs 0x03DF1E (2018)

### 2018 → 2019

- 10SW040039 (2019 300hp): CODE diff vs 2021 = 7087B (4482B CODE, 83 bloka)
- GTI 1503: 10SW040008 unificira sve snage (130/155/230hp = isti SW!)
- Spark 900: 10SW039116 = identičan MD5 za 2019/2020/2021

### 2019 → 2020+

- 1630 NA: 10SW053729 uvodi 170hp varijant (isti SW kao 130hp, razlika = impeller)
- GTI90: poseban SW (10SW053774) za 900 ACE HO u GTI karosiriji

### 2022 — Tranzicijska platforma (zadnji ME17.8.5)

- Isti Rotax 1630/900 ACE motori — nema novog motora u 2022
- ECU: ME17.8.5 — ali s **potpuno novim CODE layoutom** (priprema za 2023)
- **10SW082806 VERIFICIRAN 2026-03-21** — čisti ORI dump (`dumps/2022/300.bin`)
- **CODE arhitektura refaktorirana — sve adrese pomjerene vs 2021:**
  - CODE diff vs 2021 (10SW066726): **236,401B** (vs 2,891B za 2020→2021!)
  - Rev limiter NIJE na 0x028E96 — adresa se promijenila
  - Fuel mapa NIJE na 0x022066 — header na 0x022066 = garbage za 2022
  - IGN NIJE na 0x02B730 — sadrži drugačiji tip podataka (u16 LE faktori, ne u8 kutovi)
  - SC bypass shadow (0x020534) i active (0x0205A8) = 0x2626 — **isti kao 2021** (jedine potvrđene adrese)
  - MapFinder 2021 adresama: samo 14/57 mapa — ostale promijenjene
- **2022 je priprema za 2023 platformu** — BRP je 2022 refaktorirao CODE za:
  - E-kontrolirani tlak goriva (novi podsustav)
  - Blow-off ventil (novi aktuator)
  - Novi SC arhitekturu (325hp, 2023)
- **Status: adrese neistražene** — MapFinder treba kompletni redizajn za 2022 SW

### 2023+ — Bosch MG1 platforma (XCU)

- **BRP naziv:** XCU (eXtended Control Unit)
- **Hardware:** Bosch **MG1** — ista generacija kao aktualni Audi/BMW high-perf aplikacije
- **MCU:** Infineon **TC3xx** TriCore (novija generacija od TC1762 u ME17.8.5)
- **Debijutirao:** RXP-X 325hp 2023 (ekskluzivno prvi)
- **Novi podsustavi:** 325hp SC, blow-off ventil, elektronski regulirani tlak goriva
- **Mix po modelima 2023+:** vjerojatno samo RXP-X 325 na MG1 inicijalno; GTI/GTX/Spark možda ostaju ME17 još godinu-dvije
- **ME17Suite scope:** samo ME17.8.5 (do 2022) — MG1/XCU je zasebna platforma
- **Tuning tool podrška:** čeka se xhorse protokol za Bosch MG1 — bez toga nema read/write
- **Binary format:** potpuno drugačiji od ME17.8.5 (MG1 ima drugačiji flash layout, enkriptiran bootloader u nekim aplikacijama)
- 2022 ME17.8.5 CODE refaktor = BRP gradio infrastrukturu za MG1 tranziciju dok je još na starom hardwareu

---

## 11. LIMP HOME I ZASTITE

### 1630 ACE

| Uvjet | Efekat |
|-------|--------|
| CTS > 110°C | Overheat mode |
| ETA u limp home | ~8° otvorenost (min throttle) |

### 900 ACE (Spark)

| Uvjet | RPM limit |
|-------|-----------|
| High temp / high EGTS | 3800 RPM |
| Low oil pressure | 4500 RPM |
| ECM default limp | 3800 RPM |

### 1503 4-TEC

| Uvjet | Temperatura |
|-------|------------|
| CTS overheat | 110°C |
| OTS limp home | >95°C |

---

## 12. IMPELLER / JET PUMP

| Model | Impeller promjer | Pitch |
|-------|-----------------|-------|
| GTI 90 (900 ACE) | 150mm | — |
| GTI 130/170 (1630 NA) | 155.5mm | — |
| GTR 230 (1630 SC) | 161mm | — |
| RXP-X 300 / GTX LTD 300 | 161mm | 13.5°/24° |

---

## 13. XCU PLATFORMA (2024+)

> Izvor: Wiring dijagrami 2021/2022/2024 (pdfplumber analiza 2026-03-21)
> Dokument ID 2024: `WD21Y24S10` (219101111)

### Terminologija: ECM vs XCU

BRP koristi dva naziva u 2024 wiring dijagramima:
- **ECM** = stari Bosch ME17.8.5 (isti hardware kao 2018–2023)
- **XCU** = novi ECU (nova generacija, 2024 uvedena)

**Fajl `WD21Y24S10`** = "S10" = specifičan model set. Dokument pokriva sve 2024 PWC modele.

---

### Koji modeli imaju što (2024)

| Dijagram stranica | Modeli | ECU tip | Motor |
|-------------------|--------|---------|-------|
| Str 1 | Spark Series | **ECM** | 900 ACE 60/90hp |
| Str 2 | 230 / 300 ENGINES — All Engines | **ECM** | 1630 ACE 230/300hp SC |
| Str 3 | 130 / 170 ENGINES — All Engines | **XCU** | 1630 ACE 130/170hp NA |
| Str 4 | 325 ENGINES — All Engines | **ECM** | 1630 ACE 325hp SC |

**Zaključak:**
- **XCU je uveden samo na 130/170hp NA varijantama u 2024**
- **Spark, 230hp, 300hp i 325hp** — ostaju na starom **ECM (ME17.8.5)** i dalje
- XCU je u 2024 bio u fazi uvođenja, ne globalni prelaz

---

### XCU — Konektor i pin format

XCU koristi **potpuno drugačiji pin format** od starog ECM-a:

| ECU tip | Pin format | Primjer | Ukupno pinova |
|---------|-----------|---------|---------------|
| Stari ECM (ME17.8.5) | Alfanumerički A/B matrica | `A-K3`, `B-M2` | 38 pinova (2×connector) |
| XCU (2024, 130/170) | 3-cifreni decimalni | `101`, `127`, `212`, `256` | ~48+ pinova (1×connector?) |
| 325 ECM (2024) | Numerički matrica | `13-xx`, `4-xx` | 56+ pinova (2×connector) |

**Stari ECM format** (2018–2024 za Spark/230/300):
- Connector A: `A-A1` do `A-M4` (matrica rows A-M, cols 1-4)
- Connector B: `B-H2`, `B-L1`, `B-M1`, `B-M2`, `B-M3`
- **Identičan pinout od 2021 do 2024** za 230/300hp modele (nulta razlika)

**XCU pin format** (2024, 130/170hp):
- Jedinstven 3-cifreni identifikator: `101`, `102`, `107`, `108`, `120`, `127`, `130`, `132`, `149`, `150`, `151`, `170`, `201`–`256`
- Raspon: ~101–256 (2 grupe: 1xx i 2xx — vjerojatno 2 konektora ili 2 reda)
- **Novi konektor — fizički nekompatibilan s ME17.8.5 harnessom**

---

### 325hp ECM (2024) — novi ECM, nije XCU

325hp motor (RXP-X 325, GTX 325) koristi **ECM** (ne XCU), ali sa **novim pin formatom**:
- Pin format: `13-xx` (max 56) i `4-xx` — numerički matrica, ne alfanumerički
- **Nije isti ME17.8.5 konektor** kao 230/300hp!
- Ima **FUEL PUMP RELAY (FPR)** — zasebni relay za fuel pump (ME17 nema ovaj relay, FP je direktno napajan)
- Ima **O2 SENSOR** (lambda sonda) — u wiring dijagramu vidljiva kao `02 SENSOR` s 6-pinskim konektorom (wiring mirrored tekst)
- Ima `LEVEL PRESSURE` (fuel pressure measurement) — zasebni senzor
- `TOPS` sensor — isti kao kod NA, ostaje
- **Fuse box oznaka: `XCU -127-`** — 325hp FUSE BOX poziva XCU fuse! To znači da je 325hp ECM BRP interno klasificiran kao XCU platforma, ali na 325 dijagramu ima RELAY natpis "ECM", a fuse poziva "XCU"

> **Napomena**: 325hp dijagram ima dualnu terminologiju — relay poziva `ECM`, fuse box poziva `XCU -127-`. Ovo sugerira da je BRP u tranziciji, i da je 325hp ECM mogući XCU hardver koji je etiketiran kao "ECM" u relay dijagramu. Ova nejasnoća zahtijeva fizičku provjeru P/N-a.

---

### 325hp novi sustavi (nije bilo na 300hp)

Uspoređujući str 4 (325hp) vs str 2 (300hp) u istom 2024 wiring dokumentu:

| Sustav | 300hp (2024) | 325hp (2024) |
|--------|-------------|-------------|
| Fuel pump relay (FPR) | NE (direktna napajanja) | **DA** (FPR = 6-pin relay) |
| O2/Lambda sonda | NE (lambda ECM-interni) | **DA** (`02 SENSOR`, 6-pin) |
| Fuel pressure sensor | NE (samo MAPTS) | **DA** (`LEVEL PRESSURE`) |
| ECU relay naziv | ECM | ECM (ali fuse = XCU) |
| Pin format | `A-xx`/`B-xx` | `13-xx`/`4-xx` (numericko) |
| Konektor tip | ME17.8.5 2×connector | Novi konektor |
| EGTS (exh. temp) | DA | DA |
| MAPTS (MAP+temp) | DA | DA |
| Knock sensor | DA | DA |

---

### Spark 2024 — ostaje na ME17.8.5

Spark Series 2024:
- Dijagram str 1 — jasno oznacen "ECM RELAY"
- Pin format identičan kao 2021/2022 Spark (`A-xx`/`B-xx`)
- 900 ACE motor — bez promjena
- **Bez XCU u 2024 Spark dijagramu**

---

### Kronologija uvođenja XCU

| Godište | Modeli s XCU | Modeli s ECM |
|---------|-------------|-------------|
| ≤ 2022 | Nema | Sve (Spark/GTI/GTX/RXT/RXP) |
| 2023 | Nepoznato (nema wiring) | Pretpostavlja se iste kao 2022 |
| **2024** | **130/170hp NA (1630 ACE)** | Spark, 230hp, 300hp, 325hp |

**Kada točno**: Prema dostupnim wiring dijagramima, XCU je **potvrđen u 2024 godištu za 130/170hp NA modele** (GTI 130, GTI 170, GTR 230 možda ne — treba provjera). Ne postoji wiring dijagram za 2023 u kolekciji, pa uvođenje u 2023 nije potvrđeno niti isključeno.

---

### Implikacije za ME17Suite

- **ME17Suite ostaje relevantan** za sve modele do i uključujući:
  - Spark Series (sve do 2024 i dalje — ostaje ECM/ME17)
  - 230hp i 300hp SC (do 2024 potvrđeno — ostaje ME17)
  - 325hp SC (2024 novi ECM, ali SW format za dump/flash neistražen)
  - Sve verzije do 2022/2023 (sve ECM/ME17.8.5)
- **130/170hp NA 2024+**: XCU — ME17Suite NIJE kompatibilan (drugačiji ECU)
- **325hp ECM**: Potencijalno novi ECU format — dumps nepoznatog formata, bin layout vjerojatno drugačiji od ME17.8.5
- **Preporuka**: Ako korisnik donese 2024 130/170hp ECU na BUDS2, dump će biti drugačijeg formata — ME17Suite ga neće prepoznati

---

## NAPOMENE I ZAMKE

### Česte greške pri radu sa SW-ovima

1. **1503 SC bypass adresa**: 2016 gen koristi `0x012C60`, ne `0x020534`!
2. **2017 gen (10SW012999)**: SC mape su na `-0x2AA` offsetu vs 2018 — boost/temp_fuel/lambda_trim na drugačijim adresama
3. **2018 300hp (10SW023910)**: IGN_BASE = `0x02B72C` (4B ranije od 2019+); rev limiter na `0x028E94`
4. **Spark IGN adresa**: `0x026A50` — NIJE `0x02B730` (to je 1630 ACE!)
5. **GTI90 DTC**: storage @ `0x0217EE`; za Spark `0x0217EE` su RPM ticks, ne DTC!
6. **0x02B72A/0x02B73E**: IGN DATA bajtovi (u8, 0x22=25.5°BTDC), NISU rev limiteri!
7. **0x02436C (linearization)**: identična za 130/170/230/300hp — NIJE za tuning; prava fuel mapa @ `0x022066`
8. **GTI injection mirror**: `0x022066` NEMA mirrora (za razliku od torque/lambda)
9. **10SW040008**: isti SW za 130/155/230hp 1503 — ne gledati snagu kao indikator SW verzije!
10. **NPRo**: ne mijenja SW string — 10SW040039 je i stock i NPRo base

### Adrese koje su IDENTIČNE za sve snage (ne tuning-relevantne za power)

- `0x02436C`: injector linearization — svi isti
- `0x012C80`: embedded cal konstante (~96B) — READ-ONLY
- `0x02B380`: 36×u16 lookup tablica — NE tunabilna
