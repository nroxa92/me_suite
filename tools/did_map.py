#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ME17Suite — BUDS2 Live Data DID/LID Map
Bosch ME17.8.5 ECU — Rotax ACE 1630 (Sea-Doo 300)

Identifikacija: analiza CAN logova sniff_livedata.csv + sniff_maps24.csv
Protokol: UDS SID 0x22 (ReadDataByIdentifier) + KWP SID 0x21 (ReadDataByLocalId)
CAN IDs: 0x7E0 (request), 0x7E8 (response)

Metodologija:
  - Sesija "livedata": 24 korisničkih parametara, kratki ciklus (34 itema)
  - Sesija "maps24": 24 korisničkih parametara, puni ciklus (89 itema = background)
  - ECU na stolu (motor hladni/topli, nije u radu)
  - Pozicijsko mapiranje + fizikalna provjera vrijednosti
  - Temp format: T_C = raw / 2 - 40  (1-byte, Bosch standard)
  - Lambda format: normalized = raw / 128  (Q7, 128 = 1.000)
  - Pritisak: P_kPa = raw / 2  (1-byte, 0x2136=202 -> 101.0 kPa verificirano)

Pouzdanost:
  ✓ Verificirano fizikalnom vrijednošću (definitivan match)
  ~ Visoka vjerovatnoća (logična pozicija + vrijednost)
  ? Nepoznato / nesigurno
"""

# ─────────────────────────────────────────────────────────────────────────────
# POLLING CIKLUS — kratki (user-selected only, prvih 2-3 ciklusa u sesiji)
# ─────────────────────────────────────────────────────────────────────────────
# 34 itema = 24 user-selected parametara + 10 background (uvijek prisutni)
# 5 od 24 vraća NRC 0x12 (ECU ne podržava na Rotax ACE 1630)
#
# Redoslijed poliranja (tablični prikaz 8x3, redak po redak):
LIVEDATA_POLL_CYCLE = [
    # (SID, DID/LID, tip, ime)
    (0x22, 0x211A, "user",       "Manifold Pressure With Altitude Correction"),
    (0x22, 0x216C, "user",       "Charge Based O2 Target"),
    (0x22, 0x2102, "background", "?"),
    (0x22, 0x2120, "user",       "Intake Temperature"),
    (0x22, 0x213F, "user",       "Relative Air Charge"),
    (0x22, 0x212E, "user",       "Fuel Cut-Off Factor"),
    (0x22, 0x212D, "user",       "Engine Friction Torque"),
    (0x22, 0x2126, "user",       "Desired O2"),
    (0x22, 0x2101, "background", "?"),
    (0x22, 0x2104, "user",       "Idle Reference Speed"),
    (0x22, 0x2103, "user",       "Desired Indicated Engine Torque"),
    (0x22, 0x2145, "user",       "Engine Speed Limitation Active"),
    (0x21, 0x1E,   "background", "? (KWP LID)"),
    (0x22, 0x2168, "user_nrc",   "? (NRC 0x12 — unsupported on this ECU)"),
    (0x22, 0x2188, "user",       "Exhaust Water Temperature"),
    (0x22, 0x212C, "user",       "Multiplicative Adaptive O2 Correction (Fra_w)"),
    (0x22, 0x2140, "user",       "Throttle Opening"),
    (0x22, 0x210E, "user",       "Engine Speed"),
    (0x22, 0x2136, "user",       "Ambient Pressure"),
    (0x22, 0x216D, "user_nrc",   "? (NRC 0x12 — unsupported on this ECU)"),
    (0x22, 0x210C, "background", "? (variable 1544-2056)"),
    (0x22, 0x210A, "user",       "Indicated Resultant Torque"),
    (0x22, 0x2146, "user_nrc",   "? (NRC 0x12 — unsupported on this ECU)"),
    (0x22, 0x2142, "user",       "Desired Ignition Angle After Torque Intervention"),
    (0x22, 0x2167, "user_nrc",   "? (NRC 0x12 — unsupported on this ECU)"),
    (0x22, 0x2125, "user",       "O2 Correction From Controller (Fr_w)"),
    (0x22, 0x212F, "user",       "O2 Full Load Correction"),
    (0x22, 0x212A, "user",       "Additive Adaptive O2 Correction (rka_w)"),
    (0x22, 0x2169, "user_nrc",   "? (NRC 0x12 — unsupported on this ECU)"),
    (0x22, 0x212B, "user",       "Intake Air Pressure"),
    (0x22, 0x2121, "user",       "Engine Coolant Temperature"),
    (0x22, 0x2105, "user",       "Mass Fuel Flow Injected"),
    (0x22, 0x213B, "user",       "Driver's Desire Throttle Angle"),
    (0x22, 0x213D, "background", "?"),
]

# ─────────────────────────────────────────────────────────────────────────────
# DID MAP — UDS SID 0x22 (ReadDataByIdentifier)
# ─────────────────────────────────────────────────────────────────────────────
# Format entry:
#   "name":     ime parametra iz BUDS2
#   "unit":     fizikalna jedinica
#   "scale":    multiplikator (physical = raw * scale + offset)
#   "offset":   offset (physical = raw * scale + offset)
#   "nbytes":   broj bajtova podataka
#   "signed":   da li je signed integer
#   "endian":   "big" ili "little"
#   "bench":    vrijednost na stolu (hex string)
#   "notes":    napomene i pouzdanost
#
UDS_DID_MAP = {

    # ── LAMBDA / O2 parametri ──────────────────────────────────────────────
    # Lambda Q7 format: normalized = raw / 128 (1B: 128=1.000, 2B: 0x0080=1.000)
    # Sve lambda vrijednosti na stolu = 1.000 (stoichiometric, motor ne radi)

    0x2105: {
        "name": "Mass Fuel Flow Injected",
        "unit": "mg/stroke",
        "scale": 1.0 / 32768,  # Q15 signed: -21744/32768 = -0.664 (motor stoji = neg?)
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "AB 10",
        "bench_phys": -0.664,
        "notes": "Q15 signed, s16=-21744, bench=-0.664 — livedata pos32 ~",
    },

    0x216C: {
        "name": "Charge Based O2 Target",
        "unit": "lambda",
        "scale": 1.0 / 128,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "00 80",
        "bench_phys": 1.000,
        "notes": "Q7 (2B): 0x0080=128/128=1.000, livedata pos2 ~",
    },

    0x2126: {
        "name": "Desired O2",
        "unit": "lambda",
        "scale": 1.0 / 128,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "00 80",
        "bench_phys": 1.000,
        "notes": "Q7 (2B): 128/128=1.000, livedata pos8 ~",
    },

    0x212A: {
        "name": "Additive Adaptive O2 Correction (rka_w)",
        "unit": "lambda_add",
        "scale": 1.0 / 128,
        "offset": 0,
        "nbytes": 1,
        "signed": True,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0.0,
        "notes": "Additive correction = 0 na stolu (motorno ulje, bez adaptacije) livedata pos28 ~",
    },

    0x212C: {
        "name": "Multiplicative Adaptive O2 Correction (Fra_w)",
        "unit": "lambda",
        "scale": 1.0 / 128,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "00 80",
        "bench_phys": 1.000,
        "notes": "Q7 (2B): 128/128=1.000 na stolu, livedata pos16 ~",
    },

    0x2125: {
        "name": "O2 Correction From Controller (Fr_w)",
        "unit": "lambda",
        "scale": 1.0 / 128,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "80",
        "bench_phys": 1.000,
        "notes": "Q7 (1B): 128/128=1.000 na stolu, livedata pos26 ~",
    },

    0x212F: {
        "name": "O2 Full Load Correction",
        "unit": "lambda",
        "scale": 1.0 / 128,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "80",
        "bench_phys": 1.000,
        "notes": "Q7 (1B): 128/128=1.000 na stolu, livedata pos27 ~",
    },

    # ── AIR CHARGE / PRESSURE ─────────────────────────────────────────────

    0x213F: {
        "name": "Relative Air Charge",
        "unit": "%",
        "scale": 100.0 / 32768,  # Q15: 0x0040=64, LE=16384/32768=0.5=50%
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "00 40",
        "bench_phys": 0.195,  # 64*100/32768 = 0.195%? Or LE=16384/32768*100=50%
        "notes": "BE=64 (0.195%) OR LE=16384/32768=50% — endian uncertain, livedata pos5 ~",
    },

    0x212B: {
        "name": "Intake Air Pressure",
        "unit": "kPa",
        "scale": 0.5,  # similar to ambient pressure
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "00 00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu (bez vakuuma), livedata pos30 ?",
    },

    0x211A: {
        "name": "Manifold Pressure With Altitude Correction",
        "unit": "kPa",
        "scale": None,  # Q15 signed, formula unknown
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "D7 D3",
        "bench_phys": None,
        "notes": "s16=-10285, Q15=-0.314 — formula nepoznata, livedata pos1 ~",
    },

    0x2136: {
        "name": "Ambient Pressure",
        "unit": "kPa",
        "scale": 0.5,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "CA",
        "bench_phys": 101.0,
        "notes": "VERIFICIRANO: 0xCA=202, 202*0.5=101.0 kPa (standardni atmosferski tlak) livedata pos19 ✓",
    },

    # ── THROTTLE ──────────────────────────────────────────────────────────

    0x2140: {
        "name": "Throttle Opening",
        "unit": "%",
        "scale": None,  # LE=50 (0.5% or 50%?)
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "little",  # LE interpretation: 0x3200 -> 0x0032 = 50
        "bench_hex": "32 00",
        "bench_phys": 50.0,  # LE=50, scale?
        "notes": "LE=50 na stolu (0% ili 50% s nekim scaleom), livedata pos17 ~",
    },

    0x213B: {
        "name": "Driver's Desire Throttle Angle",
        "unit": "%",
        "scale": 100.0 / 255,  # u8 percentage?
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu (gas nije pritisnut), livedata pos33 ~",
    },

    # ── TORQUE ────────────────────────────────────────────────────────────

    0x2103: {
        "name": "Desired Indicated Engine Torque",
        "unit": "Nm",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "00 00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu, livedata pos11 ~",
    },

    0x210A: {
        "name": "Indicated Resultant Torque",
        "unit": "Nm",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "00 00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu, livedata pos22 ~",
    },

    0x212D: {
        "name": "Engine Friction Torque",
        "unit": "Nm",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "00 00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu, livedata pos7 ~",
    },

    # ── IGNITION ──────────────────────────────────────────────────────────

    0x2142: {
        "name": "Desired Ignition Angle After Torque Intervention",
        "unit": "deg BTDC",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "00 00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu (bez paljenja), livedata pos24 ~",
    },

    # ── ENGINE SPEED ─────────────────────────────────────────────────────

    0x210E: {
        "name": "Engine Speed",
        "unit": "RPM",
        "scale": None,  # LE=984 RPM? But engine off should be 0
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "little",  # 0xD803 -> LE = 0x03D8 = 984
        "bench_hex": "D8 03",
        "bench_phys": 984.0,  # LE=984, motor ne radi — možda radi dok se snima?
        "notes": "LE=984 RPM (motor moguće radio pri snimanju), livedata pos18 ~",
    },

    0x2104: {
        "name": "Idle Reference Speed",
        "unit": "RPM",
        "scale": 0.25,  # BE: 4135 * 0.25 = 1034 RPM (idle ~800-1100 RPM)
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "10 27",
        "bench_phys": 1033.75,  # 4135 * 0.25 = 1033.75 RPM
        "notes": "BE=4135, *0.25=1034 RPM (idle ref), livedata pos10 ~",
    },

    # ── TEMPERATURE ───────────────────────────────────────────────────────
    # Format: T_C = raw / 2 - 40  (Bosch standard 1-byte temp encoding)

    0x2121: {
        "name": "Engine Coolant Temperature",
        "unit": "degC",
        "scale": 0.5,
        "offset": -40,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "B8",
        "bench_phys": 52.0,  # 184/2-40 = 52°C (topao motor na stolu)
        "notes": "0xB8=184, 184*0.5-40=52.0°C (topao motor), livedata pos31 ~",
    },

    0x2120: {
        "name": "Intake Temperature",
        "unit": "degC",
        "scale": 0.5,
        "offset": -40,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "78",
        "bench_phys": 20.0,  # 120/2-40 = 20°C (sobna temperatura)
        "notes": "0x78=120, 120*0.5-40=20.0°C (sobna temperatura), livedata pos4 ✓",
    },

    0x2188: {
        "name": "Exhaust Water Temperature",
        "unit": "degC",
        "scale": 0.5,
        "offset": -40,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "6E",
        "bench_phys": 15.0,  # 110/2-40 = 15°C (ispod sobne = rashladna voda)
        "notes": "0x6E=110, 110*0.5-40=15.0°C, livedata pos15 ~",
    },

    # ── FUEL / LAMBDA FLAGS ───────────────────────────────────────────────

    0x212E: {
        "name": "Fuel Cut-Off Factor",
        "unit": "",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0.0,
        "notes": "= 0 na stolu, livedata pos6 ~",
    },

    0x2145: {
        "name": "Engine Speed Limitation Active",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0.0,
        "notes": "Boolean 0=inactive, livedata pos12 ~",
    },

    # ── UNSUPPORTED ON ROTAX ACE 1630 (NRC 0x12) ─────────────────────────
    # Ovi DID-ovi postoje u BUDS2 ali ECU vraća subFunctionNotSupported
    # Vjerovatno parametri specifični za druge motore (GTI 90, Spark, 4TEC)

    0x2168: {
        "name": "? (unsupported — NRC 0x12)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "signed": None,
        "endian": None,
        "bench_hex": "7F 22 12",
        "bench_phys": None,
        "notes": "ECU ne podržava (NRC subFunctionNotSupported), livedata pos14",
    },

    0x216D: {
        "name": "? (unsupported — NRC 0x12)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "signed": None,
        "endian": None,
        "bench_hex": "7F 22 12",
        "bench_phys": None,
        "notes": "ECU ne podržava (NRC subFunctionNotSupported), livedata pos20",
    },

    0x2146: {
        "name": "? (unsupported — NRC 0x12)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "signed": None,
        "endian": None,
        "bench_hex": "7F 22 12",
        "bench_phys": None,
        "notes": "ECU ne podržava (NRC subFunctionNotSupported), livedata pos23",
    },

    0x2167: {
        "name": "? (unsupported — NRC 0x12)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "signed": None,
        "endian": None,
        "bench_hex": "7F 22 12",
        "bench_phys": None,
        "notes": "ECU ne podržava (NRC subFunctionNotSupported), livedata pos25",
    },

    0x2169: {
        "name": "? (unsupported — NRC 0x12)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "signed": None,
        "endian": None,
        "bench_hex": "7F 22 12",
        "bench_phys": None,
        "notes": "ECU ne podržava (NRC subFunctionNotSupported), livedata pos29",
    },

    # ── BACKGROUND DIDs (uvijek pollovani, ne user-selected) ─────────────
    # Identificirani kao "background" jer nisu u user-selected listi ali uvijek prisutni

    0x2101: {
        "name": "? (background)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "03",
        "bench_phys": 3,
        "notes": "background, val=3 (flags?), livedata pos9",
    },

    0x2102: {
        "name": "? (background)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "03",
        "bench_phys": 3,
        "notes": "background, val=3 (flags?), livedata pos3",
    },

    0x210C: {
        "name": "? (background — dynamic)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "07 08",
        "bench_phys": 1800,
        "notes": "background, variable 1544-2056, livedata pos21",
    },

    0x213D: {
        "name": "? (background)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background, val=0, livedata pos34",
    },

    # ── MAPS24 SESSION parametri (nova lista — druga sesija) ──────────────
    # maps24: 24 parametara poredani u ciklusu 73 UDS + 16 KWP

    0x213C: {
        "name": "Control Active B_lr (kandidat)",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0,
        "notes": "val=0 na bench (motor stoji) — kandidat za 'Control Active (B_lr)' iz BUDS2. "
                 "B_lr = lambda closed-loop control active (0=off bench, 1=running). maps24",
    },

    0x2108: {
        "name": "? (maps24 — val=36106 LE=2701)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "8D 0A",
        "bench_phys": None,
        "notes": "BE=36106 LE=2701, maps24 background",
    },

    0x2124: {
        "name": "? (background — Engine Speed candidate)",
        "unit": "RPM",
        "scale": None,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0.0,
        "notes": "val=0 na stolu — kandidat za Engine Speed (0 = motor stoji)",
    },

    # ── OSTALI PODRŽANI DIDs (iz sniff_cdid.csv scan) ────────────────────

    0x2107: {
        "name": "Lambda zaštita — prag (bench=0xFFFF=disabled)",
        "unit": "lambda Q15",
        "scale": 1.0 / 32768,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "FF FF",
        "bench_phys": 65535,
        "notes": "0xFFFF na bench = lambda protection threshold 'disabled' (off bench). "
                 "NPRo STG2 = uvijek 0xFFFF (bypass). Map @ 0x02B378 (79×u16 Q15). 95% conf.",
    },

    0x2158: {
        "name": "Lambda zaštita — prag 2 (bench=0xFFFF=disabled)",
        "unit": "lambda Q15",
        "scale": 1.0 / 32768,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "FF FF",
        "bench_phys": 65535,
        "notes": "0xFFFF na bench = lambda protection threshold 'disabled' (off bench). "
                 "NPRo STG2 = uvijek 0xFFFF (bypass). Map @ 0x02B378 (79×u16 Q15). 95% conf.",
    },

    0x2134: {
        "name": "? (val=0xC293 = 49811)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "C2 93",
        "bench_phys": None,
        "notes": "s16=-15725, LE=37826, Q15=-0.480",
    },

    0x2119: {
        "name": "? (isti kao 0x211A — manifold pressure?)",
        "unit": "kPa",
        "scale": None,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "D7 D3",
        "bench_phys": None,
        "notes": "Identična vrijednost kao 0x211A, vjerojatno isti parametar (primary/secondary sensor?)",
    },

    0x211B: {
        "name": "? (val=4479, 2B)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "11 7F",
        "bench_phys": None,
        "notes": "BE=4479, LE=32529",
    },

    0x211E: {
        "name": "? (val=4479 = isti kao 0x211B)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "11 7F",
        "bench_phys": None,
        "notes": "Identična vrijednost kao 0x211B — par parametara",
    },

    0x2183: {
        "name": "VTS Position (kandidat)",
        "unit": "%",
        "scale": 100.0 / 255,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "40",
        "bench_phys": 25.1,  # 64/255*100 = 25.1% (VTS default/rest position)
        "notes": "0x40=64 = 25% od 255, kandidat za 'VTS Position' (BUDS2 lista). "
                 "VTS rest position na bench ≈25% — konzistentno. maps24 background",
    },

    0x214F: {
        "name": "? (val=1 boolean)",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "01",
        "bench_phys": 1,
        "notes": "boolean 1=true na stolu",
    },

    0x214C: {
        "name": "? (val=1 boolean)",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "01",
        "bench_phys": 1,
        "notes": "boolean 1=true na stolu",
    },

    0x2187: {
        "name": "? (val=1 boolean)",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "01",
        "bench_phys": 1,
        "notes": "boolean 1=true na stolu, maps24 background",
    },

    0x2175: {
        "name": "? (val=1 boolean)",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "01",
        "bench_phys": 1,
        "notes": "boolean 1=true na stolu, maps24 background",
    },

    0x2139: {
        "name": "? (val=1 boolean)",
        "unit": "bool",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "01",
        "bench_phys": 1,
        "notes": "boolean 1=true na stolu, maps24 background",
    },

    0x2106: {
        "name": "Indicated Basic Torque (kandidat)",
        "unit": "Nm",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "AB 10",
        "bench_phys": None,
        "notes": "Identična vrijednost kao 0x2105 (AB 10) — nije mirror (Mass Fuel ne =-21744Nm). "
                 "Kandidat za 'Indicated Basic Torque' (BUDS2 lista). Format nejasan. maps24",
    },

    0x210F: {
        "name": "Throttle Opening Requirement For Idle Speed (kandidat)",
        "unit": "%",
        "scale": 1.0,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "little",
        "bench_hex": "52 00",
        "bench_phys": 82.0,  # LE=82 (direktan % ili raw?)
        "notes": "LE=82 na bench — kandidat za 'Throttle Opening Requirement For Idle Speed' "
                 "(BUDS2 lista). 82 = idle throttle setpoint (raw ili %). maps24 background",
    },

    0x2110: {
        "name": "Flow Model Based Temperature Correction (kandidat)",
        "unit": "corr",
        "scale": 1.0 / 32768,
        "offset": 0,
        "nbytes": 2,
        "signed": True,
        "endian": "big",
        "bench_hex": "F2 99",
        "bench_phys": -0.105,  # s16=-3431/32768=-0.105
        "notes": "s16=-3431, Q15=-0.105 (negativna korekcija) — kandidat za "
                 "'Flow Model Based Temperature Correction' ili "
                 "'Combustion Chamber Temperature Correction' (BUDS2 lista). maps24",
    },

    0x216A: {
        "name": "? (val=0 boolean/enum)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "00",
        "bench_phys": 0,
        "notes": "maps24 background",
    },

    0x2135: {
        "name": "Lake Water Temperature (kandidat)",
        "unit": "degC",
        "scale": 0.5,
        "offset": -40,
        "nbytes": 1,
        "signed": False,
        "endian": "big",
        "bench_hex": "85",
        "bench_phys": 26.5,
        "notes": "0x85=133, 133*0.5-40=26.5°C — sobna temperatura na bench, "
                 "kandidat za 'Lake Water Temperature' (BUDS2 lista). "
                 "Na bench bez rashladne vode = sobna temp (OK). maps24 background",
    },

    0x2144: {
        "name": "Optimum Indicated Torque (kandidat)",
        "unit": "% Q15",
        "scale": 100.0 / 32768,
        "offset": 0,
        "nbytes": 2,
        "signed": False,
        "endian": "big",
        "bench_hex": "80 27",
        "bench_phys": 100.1,  # 32807/32768*100 = 100.1% (idle bench, normalizirani torque)
        "notes": "BE=32807/32768=1.001 (≈100.1%) — blizu 1.0 na bench, "
                 "kandidat za 'Optimum Indicated Torque' iz BUDS2 liste. "
                 "Moguce i 'Desired Indicated Torque Before Slope Limitation'. maps24 background",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# KWP LID MAP — SID 0x21 (ReadDataByLocalId)
# ─────────────────────────────────────────────────────────────────────────────
KWP_LID_MAP = {

    0x1E: {
        "name": "? (KWP — 4 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 4,
        "bench_hex": "00 00 00 00",
        "bench_phys": 0,
        "notes": "Uvijek prisutan u ciklusu (background), livedata pos13",
    },

    0x11: {
        "name": "? (KWP — background)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x17: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x20: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x21: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x22: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x23: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x24: {
        "name": "? (KWP — 4 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 4,
        "bench_hex": "00 00 00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x25: {
        "name": "? (KWP — 4 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 4,
        "bench_hex": "00 00 00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x54: {
        "name": "? (KWP — 1 byte, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 1,
        "bench_hex": "00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x56: {
        "name": "? (KWP — 1 byte, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 1,
        "bench_hex": "00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x57: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0x58: {
        "name": "? (KWP — 3 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 3,
        "bench_hex": "00 00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0xB4: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0xB6: {
        "name": "? (KWP — 2 bytes, val=0)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 2,
        "bench_hex": "00 00",
        "bench_phys": 0,
        "notes": "background",
    },

    0xB7: {
        "name": "? (KWP — 3 bytes = 0x0BB801)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": 3,
        "bench_hex": "0B B8 01",
        "bench_phys": None,
        "notes": "background, val=[0x0B, 0xB8, 0x01] — moguci engine hours?",
    },

    0xB9: {
        "name": "? (KWP — livedata only)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "bench_hex": None,
        "bench_phys": None,
        "notes": "samo u livedata sesiji, extended scan (~5min interval)",
    },

    0xBA: {
        "name": "? (KWP — livedata only)",
        "unit": None,
        "scale": None,
        "offset": None,
        "nbytes": None,
        "bench_hex": None,
        "bench_phys": None,
        "notes": "samo u livedata sesiji, extended scan (~5min interval)",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# BUDS2 LIVEVIEW — kompletna lista parametara (iz BUDS2 UI screenshotova)
# Izvor: _materijali/live data info/Screenshot_1-7.png
# Snimano: 2026-03-22, vozilo: GTX/RXT Dolphin, iBR=True, NA varijanta
# Ukupno: 129 parametara dostupnih u BUDS2 Liveview dropdownu
# ─────────────────────────────────────────────────────────────────────────────
BUDS2_PARAMETER_LIST = [
    # ── Adaptacijske vrijednosti ────────────────────────────────────────────
    "Adaptive Value Of Integral Idle Speed",
    "Additive Adaptive O2 Correction (rka_w)",        # DID 0x212A
    "Additive Adjustment of Calc. Air Mass Flow",
    "Multiplicative Adaptive O2 Correction (Fra_w)",  # DID 0x212C
    "Multiplicative Adjustment Of Calc. Air Mass Flow",

    # ── Senzori / okolina ────────────────────────────────────────────────
    "Ambient Pressure",                               # DID 0x2136 ✓
    "Battery Voltage",
    "Boat Speed",
    "Engine Coolant Temperature",                     # DID 0x2121
    "Engine Speed",                                   # DID 0x210E
    "Engine Total Hour",
    "Exhaust Water Temperature",                      # DID 0x2188
    "Intake Air Pressure",                            # DID 0x212B
    "Intake Temperature",                             # DID 0x2120
    "Lake Water Temperature",                         # DID 0x2135 (kandidat)
    "Oil Pressure Switch",
    "Oil Temperature",
    "Throttle Actuator Sensor",
    "Voltage PWG Potentiometer 1",
    "Voltage PWG Potentiometer 2",
    "VTS Position",                                   # DID 0x2183 (kandidat)

    # ── Lambda / O2 ──────────────────────────────────────────────────────
    "Charge Based O2 Target",                         # DID 0x216C
    "Desired O2",                                     # DID 0x2126
    "O2 Correction From Controller (Fr_w)",           # DID 0x2125
    "O2 Full Load Correction",                        # DID 0x212F
    "O2 Sensor Heating",
    "STFT (Bank 1)",

    # ── Punjenje zraka ───────────────────────────────────────────────────
    "Desired Relative Air Charge",
    "Desired Relative Air Charge After Torque Coordination",
    "Desired Throttle Angle",
    "Manifold Pressure With Altitude Correction",     # DID 0x211A
    "Relative Air Charge",                            # DID 0x213F
    "Relative Air Charge Based Primary Sensor",
    "Throttle Body Air Mass Flow",
    "Throttle Opening",                               # DID 0x2140
    "Throttle Opening Requirement For Idle Speed",    # DID 0x210F (kandidat)

    # ── Moment / torque ──────────────────────────────────────────────────
    "Coordinated Torque Effective Upon Cylinder Charging",
    "Desired Indicated Engine Torque",                # DID 0x2103
    "Desired Indicated Torque Before Slope Limitation",
    "Driver's Desire Throttle Angle",                 # DID 0x213B
    "Engine Friction Torque",                         # DID 0x212D
    "Indicated Basic Torque",                         # DID 0x2106 (kandidat)
    "Indicated Resultant Torque",                     # DID 0x210A
    "Optimum Indicated Torque",                       # DID 0x2144 (kandidat)

    # ── Paljenje ─────────────────────────────────────────────────────────
    "Desired Ignition Angle After Torque Intervention",  # DID 0x2142

    # ── Gorivo / injection ───────────────────────────────────────────────
    "Fuel Cut-Off Factor",                            # DID 0x212E
    "Fuel Pump",
    "Mass Fuel Flow Injected",                        # DID 0x2105
    "Purge Valve Correction",

    # ── Brzinsko ograničenje ─────────────────────────────────────────────
    "Engine Speed Limitation Active",                 # DID 0x2145
    "Engine Speed Limitation Set Point",
    "Vehicle Speed",
    "Vehicle Speed Limitation Set Point",

    # ── Idle / pokretanje ────────────────────────────────────────────────
    "Idle Reference Speed",                           # DID 0x2104
    "Idle Speed Control Active",

    # ── Temperatura korekcije ────────────────────────────────────────────
    "Combustion Chamber Temperature Correction",
    "Flow Model Based Temperature Correction",        # DID 0x2110 (kandidat)

    # ── Servisni / dijagnostički ─────────────────────────────────────────
    "Check Engine Lamp",
    "Customer Name",
    "Distance Counter For Check Engine ON",
    "Distance Counter For Limp Home ON",
    "Error (B_maxflsv || B_minflsv || B_sigflsv || B_nplflsv)",
    "Exchange Security Invalid",
    "Flooded Engine",
    "Last Service Hour",
    "Learn Duration Time Counter For One Learnstep",
    "Limp Home Lamp",
    "Logistic Programming 3 Raw",
    "Maintenance Interval",
    "MoF_bSrgDiffErr",
    "Number Of Maintenance Calls Up To Now",
    "Odometer Backup",
    "OTAS Switch State Not Plausible",
    "OTAS Switch State Valid",
    "Starter Solenoid",
    "Start Switch",
    "State Of DESS",
    "State Of Tip Over Switch",
    "Stop Switch",
    "Time Spent In Learning Key",
    "Time Spent In Limp Home",
    "Time Spent In Normal Key",
    "Time Spent In Rental Key",
    "TPS Learning Successful",
    "Transmission Position",
    "Vehicle Hour Counter",

    # ── B_ boolean zastavice (Bosch Merkmal) ─────────────────────────────
    "B_accessdenied (Vehicle Access Is Denied)",
    "B_brems (Condition: Brake Operated)",
    "B_ccon (Cruise Control Is Active)",
    "B_fembgact (Torque Limitation In FEM Active)",  # FEM = Fahrerwunsch! Potvrđuje FWM mapu
    "B_keypresent (Plugged Key Was Detected By The Vehicle)",
    "B_klpedd (Enhanced Throttle Mode Active)",      # sport/enhanced throttle mode
    "B_ll (Idle Speed From Driver's Side)",
    "B_mil (Lamp - Check Engine)",
    "B_nachlauf (ECU Control For ECU Switch Off Delay)",
    "B_nmot (Engine Speed Greater NMIN)",
    "B_poelmn (Oil Pressure Too Low)",
    "B_skion (Ski Mode Status)",
    "B_stendes (End Of Start Also For Injection)",
    "B_ugd (Throttle Angle Near Max. Possible Air Charge)",  # blizu WOT
    "B_upsddwn (Vehicle Is Upside Down)",
    "Brake Switch",
    "Clutch Switch",
    "Control Active (B_lr)",                         # DID 0x213C (kandidat) = lambda CL active
    "Heating Active (B_hsve)",
    "Init(B_lsvklt)",
    "Key Switch Input",

    # ── Byte konfiguracija (vehicle config word) ─────────────────────────
    "Byte 0 Vehicle",          # = "Dolphin" (GTX/RXT codename)
    "Byte 1 Bit 0 Supercharger Fit",     # False = NA, True = SC
    "Byte 1 Bit 1 iS Fit",               # intelligent Suspension
    "Byte 1 Bit 2 iBR fit",              # intelligent Brake & Reverse
    "Byte 1 Bit 3 C/U or Inter (Inter = 1)",  # Intercooler
    "Byte 1 Bit 4 Fuel tank config bit 1",
    "Byte 1 Bit 5 Fuel tank config bit 2",
    "Byte 1 Bit 6 SBOAT BALLAST",
    "Byte 1 Bit 7",
    "Byte 2 Engine",
    "Byte 3 Bit 0 CRUISE + SLOW SPEED CRUISE",
    "Byte 3 Bit 1 SKI MODE",
    "Byte 3 Bit 2 Fuel Autonomy",
    "Byte 3 Bit 3 Top/Avr Spd/RPM, LAP,Engine Temp",
    "Byte 3 Bit 4 Altitude",
    "Byte 3 Bit 5 VTS Switch",
    "Byte 3 Bit 6",
    "Byte 3 Bit 7",
    "Byte 4", "Byte 5", "Byte 6", "Byte 7",
]

# ─────────────────────────────────────────────────────────────────────────────
# BUDS2 RUNNING ENGINE — prioritetni parametri za running engine CAN sesiju
# Strategija: kratki WOT pulsevi u plivajućem dock-u, IXXAT 500kbps
# Cilj: potvrditi mape FWM/KFZW2/Lambda/DFCO u stvarnom radu
# ─────────────────────────────────────────────────────────────────────────────
BUDS2_RUNNING_ENGINE_PRIORITY = [
    # Format: (BUDS2_naziv, DID, cilj_verifikacije)
    # ── FWM (vozačev zahtjev momenta) @ 0x02A7F0 ──
    ("Driver's Desire Throttle Angle",         0x213B, "FWM ulaz — prati gas pedal"),
    ("Desired Indicated Engine Torque",        0x2103, "FWM izlaz — SC<100% / NA>100%"),
    ("Desired Indicated Torque Before Slope Limitation", None, "FWM raw (prije ramp filter)"),
    ("Optimum Indicated Torque",               0x2144, "alt FWM kandidat"),
    ("B_fembgact (Torque Limitation In FEM Active)", None, "FEM=FWM aktivan (bool)"),

    # ── KFZW2 (paljenje za moment) @ 0x022374 ──
    ("Desired Ignition Angle After Torque Intervention", 0x2142, "KFZW2 izlaz — stupnjevi BTDC"),

    # ── Lambda lanac ──
    ("O2 Correction From Controller (Fr_w)",   0x2125, "lambda CL korekcija (aktivna u radu)"),
    ("Control Active (B_lr)",                  0x213C, "lambda CL status (0=bench, 1=running)"),
    ("STFT (Bank 1)",                          None,   "kratkoročna lambda trim"),
    ("Additive Adaptive O2 Correction (rka_w)", 0x212A, "dugoročna lambda adapt (additive)"),
    ("Multiplicative Adaptive O2 Correction (Fra_w)", 0x212C, "dugoročna lambda adapt (mult)"),

    # ── DFCO (decel fuel cut) @ 0x028C30 ──
    ("Fuel Cut-Off Factor",                    0x212E, "DFCO aktivan (1=cut, 0=normal)"),
    ("Engine Speed",                           0x210E, "RPM pri DFCO aktivaciji"),

    # ── Boost / punjenje ──
    ("Relative Air Charge",                    0x213F, "punjenje cilindra %"),
    ("Desired Relative Air Charge",            None,   "željeno punjenje (torque coordination)"),
    ("Manifold Pressure With Altitude Correction", 0x211A, "MAP kPa (boost/vakuum)"),

    # ── Termalni parametri ──
    ("Engine Coolant Temperature",             0x2121, "CTS za thermal mape"),
    ("Lake Water Temperature",                 0x2135, "rashladna voda temperature"),
    ("Exhaust Water Temperature",              0x2188, "EWT (overtemp zaštita)"),
]

# ─────────────────────────────────────────────────────────────────────────────
# POLLING STATISTIKE iz sniff logova
# ─────────────────────────────────────────────────────────────────────────────
POLLING_STATS = {
    "livedata": {
        "file": "sniff_livedata.csv",
        "duration_s": 1955.9,
        "total_uds22_requests": 31092,
        "unique_uds22_dids": 95,
        "total_kwp21_requests": 6564,
        "unique_kwp21_lids": 18,
        "short_cycle_items": 34,   # user-selected (prvih 2 ciklusa)
        "full_cycle_items": 89,    # user + full background (od 4. ciklusa)
        "cycle_period_s": 0.7,
    },
    "maps24": {
        "file": "sniff_maps24.csv",
        "duration_s": 140.7,
        "total_uds22_requests": 3341,
        "unique_uds22_dids": 78,
        "total_kwp21_requests": 649,
        "unique_kwp21_lids": 16,
        "short_cycle_items": None,  # nema kratkih ciklusa — snimanje počelo kad smo vec u full ciklusu
        "full_cycle_items": 89,
        "cycle_period_s": 1.5,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# KORISNE FUNKCIJE
# ─────────────────────────────────────────────────────────────────────────────

def decode_uds_value(did: int, raw_bytes: bytes) -> float | None:
    """
    Dekodira raw bytes za dani DID u fizikalnu vrijednost.
    Vraca None ako DID nije poznat ili formula nije dostupna.
    """
    info = UDS_DID_MAP.get(did)
    if info is None:
        return None
    if info.get("scale") is None or info.get("offset") is None:
        return None

    endian = info.get("endian", "big")
    signed = info.get("signed", False)

    try:
        raw_int = int.from_bytes(raw_bytes, endian, signed=signed)
        return raw_int * info["scale"] + info["offset"]
    except Exception:
        return None


def decode_uds_value_with_unit(did: int, raw_bytes: bytes) -> tuple[float | None, str]:
    """
    Vraca (value, unit_string) par.
    """
    val = decode_uds_value(did, raw_bytes)
    info = UDS_DID_MAP.get(did, {})
    unit = info.get("unit", "")
    return val, unit


def get_did_name(did: int) -> str:
    """Vraca ime parametra za dani DID."""
    info = UDS_DID_MAP.get(did, {})
    return info.get("name", f"Unknown DID 0x{did:04X}")


def get_lid_name(lid: int) -> str:
    """Vraca ime parametra za dani KWP LID."""
    info = KWP_LID_MAP.get(lid, {})
    return info.get("name", f"Unknown LID 0x{lid:02X}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — ispis kompletne tablice
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 80)
    print("ME17Suite — BUDS2 DID/LID Map")
    print("Bosch ME17.8.5 / Rotax ACE 1630 / Sea-Doo 300")
    print("=" * 80)
    print()

    print("UDS SID 0x22 — ReadDataByIdentifier:")
    print("-" * 80)
    print(f"  {'DID':8} {'Naziv':45} {'Jedinica':12} {'Bench':10}")
    print("-" * 80)
    for did, info in sorted(UDS_DID_MAP.items()):
        name = info.get("name", "?")[:44]
        unit = info.get("unit") or "-"
        bench = info.get("bench_hex") or "-"
        print(f"  0x{did:04X}   {name:45} {unit:12} {bench}")

    print()
    print("KWP SID 0x21 — ReadDataByLocalId:")
    print("-" * 80)
    print(f"  {'LID':8} {'Naziv':45} {'Bench':10}")
    print("-" * 80)
    for lid, info in sorted(KWP_LID_MAP.items()):
        name = info.get("name", "?")[:44]
        bench = info.get("bench_hex") or "-"
        print(f"  0x{lid:02X}     {name:45} {bench}")

    print()
    print("Livedata poll cycle (34 items = 24 user-selected + 10 background):")
    print("-" * 80)
    for pos, (sid, did, typ, name) in enumerate(LIVEDATA_POLL_CYCLE, 1):
        if sid == 0x22:
            did_str = f"UDS 0x{did:04X}"
        else:
            did_str = f"KWP 0x{did:02X}  "
        flag = "[NRC]" if typ == "user_nrc" else ("[ bg]" if typ == "background" else "[usr]")
        print(f"  [{pos:2d}] {flag} {did_str}  {name}")
