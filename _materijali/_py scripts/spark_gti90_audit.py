#!/usr/bin/env python3
"""
Spark 900 ACE + GTI90 — kompletan binarni audit
Čitanje samo, nema pisanja u dumpove.
"""
import struct, hashlib, os, sys, io
from pathlib import Path
from collections import Counter

# Force UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DUMPS = {
    "spark_2018": Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2018/900ace/spark90.bin"),
    "spark_2019": Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2019/900ace/spark90.bin"),
    "spark_2020": Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2020/900ace/spark90.bin"),
    "spark_2021": Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2021/900ace/spark90.bin"),
    "gti90_2020": Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2020/900ace/gti90.bin"),
    "gti90_2021": Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2021/900ace/gti90.bin"),
}

REF_1630 = Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps/2019/1630ace/300.bin")

out = []
def log(s=""):
    out.append(s)
    print(s)

# ─────────────────────────────────────────────────────────────────────────────
# Pomoćne funkcije
# ─────────────────────────────────────────────────────────────────────────────

def read_bin(path):
    with open(path, "rb") as f:
        return f.read()

def sw_string(data):
    """SW string @ 0x0008, 20 bajta ASCII"""
    raw = data[0x0008:0x0028]
    return raw.decode("ascii", errors="replace").rstrip('\x00').strip()

def header(data):
    return data[0x0000:0x0010].hex(" ")

def md5(data):
    return hashlib.md5(data).hexdigest()

def u16le(data, offset):
    return struct.unpack_from("<H", data, offset)[0]

def u16be(data, offset):
    return struct.unpack_from(">H", data, offset)[0]

def scan_for_u16le(data, target, start=0x010000, end=0x060000, window=2):
    """Skeniraj za LE u16 vrijednost"""
    hits = []
    for off in range(start, min(end, len(data)-1), window):
        v = u16le(data, off)
        if v == target:
            hits.append(off)
    return hits

def scan_range_u16le(data, lo, hi, start=0x010000, end=0x060000, step=2):
    """Vrati sve offsete gdje je LE u16 u rasponu [lo, hi]"""
    hits = []
    for off in range(start, min(end, len(data)-1), step):
        v = u16le(data, off)
        if lo <= v <= hi:
            hits.append((off, v))
    return hits

def diff_bins(d1, d2):
    """Vrati broj različitih bajtova i prvih 20 razlika"""
    if len(d1) != len(d2):
        return None, f"RAZLIČITA VELIČINA: {len(d1)} vs {len(d2)}"
    diffs = [(i, d1[i], d2[i]) for i in range(len(d1)) if d1[i] != d2[i]]
    return len(diffs), diffs[:20]

def extract_block(data, offset, rows, cols, dtype="u8"):
    """Izvuci blok podataka"""
    result = []
    if dtype == "u8":
        for r in range(rows):
            row = []
            for c in range(cols):
                row.append(data[offset + r*cols + c])
            result.append(row)
    elif dtype == "u16le":
        for r in range(rows):
            row = []
            for c in range(cols):
                o = offset + (r*cols + c)*2
                row.append(u16le(data, o))
            result.append(row)
    return result

def print_block(block, name, fmt="{:3d}"):
    log(f"  {name}:")
    for row in block:
        log("    " + " ".join(fmt.format(v) for v in row))

def entropy_region(data, start, length):
    """Shannonova entropija za region"""
    region = data[start:start+length]
    if not region:
        return 0.0
    counts = Counter(region)
    total = len(region)
    import math
    return -sum((c/total)*math.log2(c/total) for c in counts.values())

def scan_ign_pattern(data, start=0x010000, end=0x060000):
    """
    Traži blokove koji izgledaju kao ignition mape:
    - 8×8=64 bajta ili 12×12=144 bajta blokovi
    - vrijednosti 0-80 (°/bit 0.75, max ~60°)
    - relativno uniformna distribucija
    Vraća kandidate (offset, score)
    """
    candidates = []
    # Tražimo 12×12=144 bajta blokove
    BLOCK = 144
    for off in range(start, min(end, len(data)-BLOCK), 4):
        block = data[off:off+BLOCK]
        vmax = max(block)
        vmin = min(block)
        vmean = sum(block)/len(block)
        # ignition: 0-80, tipično 20-60
        if 15 <= vmean <= 65 and vmax <= 90 and vmin >= 0:
            # nema previše nula (nije prazna tablica)
            nz = sum(1 for b in block if b > 5)
            if nz >= 60:
                candidates.append((off, vmean, vmax, vmin))
    return candidates

def scan_inj_pattern(data, start=0x010000, end=0x060000):
    """
    Traži injection mape: LE u16 Q15 blokovi
    - 16×12 = 192 u16 = 384 bajta ili 16×16=512 bajta
    - vrijednosti 0x3000-0x8000 (0.375-1.0 u Q15)
    """
    candidates = []
    BLOCK = 16 * 12 * 2  # 384 bajta
    for off in range(start, min(end, len(data)-BLOCK), 2):
        vals = [u16le(data, off+i*2) for i in range(16*12)]
        vmin = min(vals)
        vmax = max(vals)
        vmean = sum(vals)/len(vals)
        if 0x2000 <= vmean <= 0xA000 and vmin >= 0x0800 and vmax <= 0xFFFF:
            nv = sum(1 for v in vals if 0x2000 <= v <= 0xC000)
            if nv >= 150:
                candidates.append((off, vmean, vmax, vmin))
    return candidates

def scan_lambda_pattern(data, start=0x010000, end=0x060000):
    """
    Traži lambda mape: LE u16 Q15
    - 12×18=216 u16 = 432 bajta
    - vrijednosti blizu 0x7FFF (≈1.0 AFR)
    """
    candidates = []
    BLOCK = 12 * 18 * 2
    for off in range(start, min(end, len(data)-BLOCK), 2):
        vals = [u16le(data, off+i*2) for i in range(12*18)]
        vmean = sum(vals)/len(vals)
        vmax = max(vals)
        vmin = min(vals)
        if 0x6000 <= vmean <= 0x9000 and vmin >= 0x4000 and vmax <= 0xBFFF:
            candidates.append((off, vmean, vmax, vmin))
    return candidates

def scan_dtc_region(data, start=0x010000, end=0x060000):
    """
    Traži DTC enable tablicu: P-kod blokovi
    - P0xxx = 0x0000-0x0FFF u LE16
    - Traži guste regije s vrednostima 0x0100-0x0FFF
    """
    # Skeniraj za tipične P-kodove
    p_codes_known = [
        0x0601,  # P0601 MAP
        0x0351,  # P0351 Ign Coil A
        0x0352,  # P0352 Ign Coil B
        0x0201,  # P0201 Injector
        0x0335,  # P0335 CKP
        0x0115,  # P0115 ECT
        0x0110,  # P0110 IAT
        0x0234,  # P0234 Turbo Overboost
        0x0562,  # P0562 System Voltage Low
        0x0563,  # P0563 System Voltage High
    ]
    hits_by_code = {}
    for code in p_codes_known:
        hits = scan_for_u16le(data, code, start, end, 2)
        if hits:
            hits_by_code[f"P{code:04X}"] = hits
    return hits_by_code

def scan_can_table(data, start=0x040000, end=0x060000):
    """
    Traži CAN frame tablicu:
    - LE u16 CAN IDs u rasponu 0x0100-0x07FF
    - grupirani zajedno
    - tipično 8-16B per frame entry
    """
    # Traži regije s gustim skupinama validnih CAN ID-ova
    can_range_hits = scan_range_u16le(data, 0x0100, 0x07FF, start, end, 2)

    # Grupiraj konsekutivne hitove
    groups = []
    if can_range_hits:
        grp_start = can_range_hits[0][0]
        grp = [can_range_hits[0]]
        for i in range(1, len(can_range_hits)):
            off, val = can_range_hits[i]
            prev_off = can_range_hits[i-1][0]
            if off - prev_off <= 32:  # unutar 32 bajta = isti entry
                grp.append((off, val))
            else:
                if len(grp) >= 3:
                    groups.append(grp)
                grp = [(off, val)]
        if len(grp) >= 3:
            groups.append(grp)
    return groups

def rpm_from_ticks(ticks, teeth=58, cylinders=3, freq_mhz=40):
    """Pretvori period ticks u RPM"""
    if ticks == 0:
        return 0
    return int(freq_mhz * 1e6 * 60 / (ticks * teeth))

# ─────────────────────────────────────────────────────────────────────────────
# DIO 1: SW identifikacija
# ─────────────────────────────────────────────────────────────────────────────

log("=" * 80)
log("DIO 1: SW IDENTIFIKACIJA")
log("=" * 80)

bins = {}
for name, path in DUMPS.items():
    if not path.exists():
        log(f"  {name}: NIJE PRONAĐEN — {path}")
        continue
    data = read_bin(path)
    bins[name] = data
    sw = sw_string(data)
    hdr = header(data)
    size = len(data)
    m = md5(data)
    log(f"\n{name}:")
    log(f"  Putanja : {path}")
    log(f"  Veličina: {size:,} B ({size/1024:.1f} KB)")
    log(f"  SW string: '{sw}'")
    log(f"  Header   : {hdr}")
    log(f"  MD5      : {m}")

    # Rev limiter na poznatim adresama
    for lbl, off in [("rev_spark", 0x028E34), ("rev_gti90", 0x028E7C), ("rev_1630", 0x028E96)]:
        if off + 2 <= len(data):
            t = u16le(data, off)
            rpm = rpm_from_ticks(t) if t > 0 else 0
            log(f"  {lbl} @ 0x{off:06X}: {t} ticks → {rpm} RPM")

# Referentni 1630
if REF_1630.exists():
    bins["ref_1630"] = read_bin(REF_1630)
    log(f"\nref_1630 (2019/300): {sw_string(bins['ref_1630'])}, {len(bins['ref_1630']):,}B")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 2: Binarna usporedba Spark dumpova
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 2: BINARNA USPOREDBA")
log("=" * 80)

spark_keys = [k for k in bins if k.startswith("spark")]
gti_keys   = [k for k in bins if k.startswith("gti")]

# Spark međusobno
log("\n--- Spark međusobna usporedba ---")
base_spark = spark_keys[0] if spark_keys else None
for k in spark_keys[1:]:
    if base_spark and k in bins and base_spark in bins:
        cnt, diffs = diff_bins(bins[base_spark], bins[k])
        if cnt is None:
            log(f"  {base_spark} vs {k}: {diffs}")
        elif cnt == 0:
            log(f"  {base_spark} vs {k}: IDENTIČNI (0 razlika)")
        else:
            log(f"  {base_spark} vs {k}: {cnt} različitih bajta")
            log(f"    Prvih razlika: {[(f'0x{d[0]:06X}', hex(d[1]), hex(d[2])) for d in diffs[:10]]}")

# GTI90 međusobno
log("\n--- GTI90 međusobna usporedba ---")
if len(gti_keys) >= 2 and all(k in bins for k in gti_keys[:2]):
    cnt, diffs = diff_bins(bins[gti_keys[0]], bins[gti_keys[1]])
    if cnt is None:
        log(f"  {gti_keys[0]} vs {gti_keys[1]}: {diffs}")
    elif cnt == 0:
        log(f"  {gti_keys[0]} vs {gti_keys[1]}: IDENTIČNI")
    else:
        log(f"  {gti_keys[0]} vs {gti_keys[1]}: {cnt} različitih bajta")
        log(f"    Prvih razlika: {[(f'0x{d[0]:06X}', hex(d[1]), hex(d[2])) for d in diffs[:10]]}")

# Spark vs GTI90 (iste godine ako postoje)
log("\n--- Spark vs GTI90 (2020) ---")
if "spark_2020" in bins and "gti90_2020" in bins:
    d1, d2 = bins["spark_2020"], bins["gti90_2020"]
    if len(d1) == len(d2):
        cnt, diffs = diff_bins(d1, d2)
        log(f"  spark_2020 vs gti90_2020: {cnt} različitih bajta")
        log(f"    Prvih razlika: {[(f'0x{d[0]:06X}', hex(d[1]), hex(d[2])) for d in diffs[:10]]}")
    else:
        log(f"  spark_2020 ({len(d1):,}B) vs gti90_2020 ({len(d2):,}B): RAZLIČITA VELIČINA")

# Spark vs 1630
log("\n--- Spark vs 1630 ACE ---")
if base_spark and base_spark in bins and "ref_1630" in bins:
    d1, d2 = bins[base_spark], bins["ref_1630"]
    if len(d1) == len(d2):
        cnt, diffs = diff_bins(d1, d2)
        log(f"  {base_spark} vs ref_1630: {cnt} različitih bajta")
    else:
        log(f"  {base_spark} ({len(d1):,}B) vs ref_1630 ({len(d2):,}B): RAZLIČITA VELIČINA")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 3: Ignition mape — skeniranje
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 3: IGNITION MAPE — SKENIRANJE")
log("=" * 80)

# Za Spark: poznata adresa iz memory = 0x02B730 (isto kao 1630?)
# Provjeri na toj adresi i skeniraj okolinu

def check_ign_at(data, offset, label=""):
    """Provjeri da li blok @ offset liči na ignition mapu"""
    if offset + 144 > len(data):
        return False, "VAN GRANICA"
    block = data[offset:offset+144]
    vmax = max(block)
    vmin = min(block)
    vmean = sum(block)/len(block)
    nz = sum(1 for b in block if b > 5)
    ok = 10 <= vmean <= 70 and vmax <= 100 and nz >= 50
    return ok, f"mean={vmean:.1f} max={vmax} min={vmin} nz={nz}"

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — ignition kandidati:")

    # 1. Provjeri poznate adrese
    for lbl, off in [
        ("ign@0x02B730 (1630 baza)", 0x02B730),
        ("ign@0x02B700", 0x02B700),
        ("ign@0x02B600", 0x02B600),
        ("ign@0x029A00", 0x029A00),
        ("ign@0x02A000", 0x02A000),
    ]:
        ok, info = check_ign_at(data, off, lbl)
        marker = "OK" if ok else "ne"
        log(f"  {marker}  {lbl}: {info}")

    # 2. Skeniraj CODE za kandidate
    log(f"  Skeniranje 0x010000-0x060000 za 12×12 ign blokove...")
    cands = scan_ign_pattern(data, 0x010000, 0x060000)
    if cands:
        log(f"  Nađeno {len(cands)} kandidata, prvih 20:")
        # Grupiraj bliske kandidate
        prev = -9999
        shown = 0
        for (off, mean, mx, mn) in cands:
            if off - prev >= 100:  # novi cluster
                log(f"    0x{off:06X}: mean={mean:.1f} max={mx} min={mn}")
                shown += 1
                if shown >= 20:
                    break
            prev = off
    else:
        log("  Nema kandidata!")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 4: Rev limiter — detaljno
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 4: REV LIMITER — SKENIRANJE")
log("=" * 80)

# Tražimo ticks u rasponu 4500-6000 (7000-10000 RPM)
# Formula: RPM = 40e6 * 60 / (ticks * 58)
# 10000 RPM → ticks = 40e6*60/(10000*58) ≈ 4138
# 7000 RPM → ticks = 40e6*60/(7000*58) ≈ 5914
# 8081 RPM → ticks = 5120 (potvrđeno za Spark)
# 7040 RPM → ticks ≈ 5884

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — rev limiter scan (ticks 4000-6500):")

    # Skeniraj CODE regiju
    hits = []
    for off in range(0x020000, min(0x050000, len(data)-1), 2):
        v = u16le(data, off)
        if 4000 <= v <= 6500:
            rpm = rpm_from_ticks(v)
            hits.append((off, v, rpm))

    if hits:
        # Grupiraj bliske
        log(f"  Nađeno {len(hits)} kandidata u 0x020000-0x050000")
        prev_off = -999
        shown = 0
        for (off, t, rpm) in hits:
            if off - prev_off > 16:
                log(f"    0x{off:06X}: {t} ticks → {rpm} RPM")
                shown += 1
                if shown >= 30:
                    log("    ... (prikazano 30)")
                    break
            prev_off = off

    # Posebno: provjeri poznate adrese
    for lbl, off in [("0x028E34", 0x028E34), ("0x028E7C", 0x028E7C), ("0x028E96", 0x028E96)]:
        if off + 2 <= len(data):
            v = u16le(data, off)
            rpm = rpm_from_ticks(v)
            log(f"  {lbl}: {v} ticks → {rpm} RPM")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 5: Injection mape
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 5: INJECTION MAPE — SKENIRANJE")
log("=" * 80)

# Poznate adrese za 1630: 0x02436C, mirror 0x0244EC
INJ_ADDRS_1630 = [0x02436C, 0x0244EC]

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — injection:")

    # Provjeri 1630 adrese
    for off in INJ_ADDRS_1630:
        if off + 384 <= len(data):
            vals = [u16le(data, off + i*2) for i in range(16*12)]
            vmean = sum(vals)/len(vals)
            vmax = max(vals)
            vmin = min(vals)
            nv = sum(1 for v in vals if 0x2000 <= v <= 0xC000)
            log(f"  0x{off:06X}: mean=0x{int(vmean):04X} max=0x{vmax:04X} min=0x{vmin:04X} valid={nv}/192")

    # Posebna provjera za GTI legacy adresu
    if off := 0x022066:
        if off + 384 <= len(data):
            vals = [u16le(data, off + i*2) for i in range(16*12)]
            vmean = sum(vals)/len(vals)
            vmax = max(vals)
            vmin = min(vals)
            nv = sum(1 for v in vals if 0x2000 <= v <= 0xC000)
            log(f"  GTI_legacy 0x022066: mean=0x{int(vmean):04X} max=0x{vmax:04X} min=0x{vmin:04X} valid={nv}/192")

    # Skeniraj za inje kandidate
    log(f"  Skeniranje za inj blokove (sporo)...")
    cands = scan_inj_pattern(data, 0x010000, 0x060000)
    if cands:
        prev = -9999
        cnt = 0
        for (off, mean, mx, mn) in cands:
            if off - prev >= 300:
                log(f"    0x{off:06X}: mean=0x{int(mean):04X} max=0x{mx:04X} min=0x{mn:04X}")
                cnt += 1
                if cnt >= 15:
                    break
            prev = off
    else:
        log("  Nema inj kandidata!")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 6: Lambda mape
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 6: LAMBDA MAPE — SKENIRANJE")
log("=" * 80)

LAMBDA_ADDRS = [0x0266F0, 0x026C08, 0x0268A0]

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — lambda:")

    for off in LAMBDA_ADDRS:
        if off + 432 <= len(data):
            vals = [u16le(data, off + i*2) for i in range(12*18)]
            vmean = sum(vals)/len(vals)
            vmax = max(vals)
            vmin = min(vals)
            uniq = len(set(vals))
            log(f"  0x{off:06X}: mean=0x{int(vmean):04X} max=0x{vmax:04X} min=0x{vmin:04X} uniq={uniq}")

    # Skeniraj
    log(f"  Skeniranje za lambda blokove...")
    cands = scan_lambda_pattern(data, 0x010000, 0x060000)
    if cands:
        prev = -9999
        cnt = 0
        for (off, mean, mx, mn) in cands:
            if off - prev >= 400:
                log(f"    0x{off:06X}: mean=0x{int(mean):04X} max=0x{mx:04X} min=0x{mn:04X}")
                cnt += 1
                if cnt >= 15:
                    break
            prev = off
    else:
        log("  Nema lambda kandidata!")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 7: DTC analiza
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 7: DTC ANALIZA")
log("=" * 80)

# Poznato za 1630: DTC enable regija ~ 0x0217EE
DTC_1630_OFFSET = 0x0217EE

# P-kodovi koje tražimo
DTC_CHECK = {
    "P0106": 0x0601,
    "P0351": 0x0351,
    "P0201": 0x0201,
    "P0335": 0x0335,
    "P0115": 0x0115,
    "P0562": 0x0562,
    "P0480": 0x0480,
    "P0532": 0x0532,
}

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — DTC analiza:")

    # Provjeri 1630 DTC region
    log(f"  Provjera 1630 DTC offset 0x{DTC_1630_OFFSET:06X}:")
    if DTC_1630_OFFSET + 40 <= len(data):
        region = data[DTC_1630_OFFSET:DTC_1630_OFFSET+40]
        log(f"    Hex: {region.hex(' ')}")

    # Scan za DTC P-kodove
    hits_by_code = scan_dtc_region(data, 0x010000, 0x060000)
    if hits_by_code:
        log(f"  P-kod hitovi (LE u16):")
        for code, offsets in hits_by_code.items():
            log(f"    {code}: {[f'0x{o:06X}' for o in offsets[:8]]}")
    else:
        log("  Nema P-kod hitova!")

    # Traži U16Ax DTC kodove (Bosch-specifični)
    # U16Ax: 0xD6xx range u LE16 → 0xxD6 kao high byte
    log(f"  Scan za U16Ax kodove (0xD6xx range):")
    u16ax_hits = []
    for off in range(0x010000, min(0x060000, len(data)-1), 2):
        v = u16le(data, off)
        if (v & 0xFF00) == 0xD600 or (v >> 8) == 0xD6:
            u16ax_hits.append((off, v))
    if u16ax_hits:
        log(f"  Nađeno {len(u16ax_hits)} U16Ax kandidata, prvih 10:")
        for off, v in u16ax_hits[:10]:
            log(f"    0x{off:06X}: 0x{v:04X}")
    else:
        log("  Nema U16Ax kodova")

    # Traži DTC blok: gusta regija s kodovima 0x0100-0x0FFF
    log(f"  Traži DTC tablicu (gusta P-kod regija):")
    p_hits_all = []
    for off in range(0x010000, min(0x060000, len(data)-1), 2):
        v = u16le(data, off)
        if 0x0100 <= v <= 0x0FFF:
            # Provjeri je li "P-kod like" — visoka nibble 0-9, nema X
            hi = (v >> 8)
            lo = (v & 0xFF)
            if hi <= 0x09 and lo > 0:
                p_hits_all.append((off, v))

    # Nađi regije s visokom gustoćom
    if p_hits_all:
        # Grupiraj po 512B windowu
        window = 512
        density = {}
        for off, v in p_hits_all:
            bucket = (off // window) * window
            density[bucket] = density.get(bucket, 0) + 1

        sorted_buckets = sorted(density.items(), key=lambda x: -x[1])
        log(f"  Najgušće DTC regije (top 5):")
        for bucket, count in sorted_buckets[:5]:
            log(f"    0x{bucket:06X}-0x{bucket+window:06X}: {count} P-kod kandidata")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 8: CAN tablica
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 8: CAN TABLICA — SKENIRANJE")
log("=" * 80)

# 1630 CAN TX tablica @ 0x0433BC
CAN_1630_OFFSET = 0x0433BC

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — CAN tablice:")

    # Provjeri 1630 adresu
    if CAN_1630_OFFSET + 64 <= len(data):
        log(f"  @ 1630 CAN offset 0x{CAN_1630_OFFSET:06X}:")
        region = data[CAN_1630_OFFSET:CAN_1630_OFFSET+64]
        log(f"    Hex: {region.hex(' ')}")
        # Izvuci CAN IDs (LE u16)
        ids = [u16le(region, i*2) for i in range(32)]
        valid_ids = [x for x in ids if 0x0100 <= x <= 0x07FF]
        log(f"    Valid CAN IDs: {[f'0x{x:04X}' for x in valid_ids]}")

    # Skeniraj za CAN tablice
    log(f"  Skeniranje 0x040000-0x060000 za CAN tablice...")
    groups = scan_can_table(data, 0x040000, 0x060000)
    if groups:
        log(f"  Nađeno {len(groups)} grupa CAN ID-ova:")
        for i, grp in enumerate(groups[:10]):
            off = grp[0][0]
            ids = [v for _, v in grp]
            log(f"    Grupa {i+1} @ 0x{off:06X}: IDs={[f'0x{v:04X}' for v in ids[:8]]}")
    else:
        log("  Nema CAN tablica!")

    # Traži specifične Spark CAN IDs
    log(f"  Scan za specifične CAN IDs:")
    for cid_name, cid_val in [("0x0186", 0x0186), ("0x0578", 0x0578),
                               ("0x0280", 0x0280), ("0x03E8", 0x03E8),
                               ("0x0201", 0x0201), ("0x0400", 0x0400)]:
        hits = scan_for_u16le(data, cid_val, 0x010000, 0x060000, 2)
        if hits:
            log(f"    {cid_name}: {[f'0x{o:06X}' for o in hits[:5]]}")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 9: Torque i ostale mape
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 9: TORQUE + OSTALE MAPE")
log("=" * 80)

TORQUE_ADDRS = [0x02A0D8, 0x02A5F0]
KNOCK_ADDR   = 0x0256F8
SC_BYPASS    = [0x020534, 0x0205A8, 0x029993]

for name in ["spark_2018", "spark_2019", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name}:")

    # Torque (Q8, 16×16)
    for off in TORQUE_ADDRS:
        if off + 512 <= len(data):
            vals = [u16le(data, off+i*2) for i in range(16*16)]
            vmean = sum(vals)/len(vals)
            log(f"  Torque 0x{off:06X}: mean=0x{int(vmean):04X} max=0x{max(vals):04X} min=0x{min(vals):04X}")

    # Knock params
    if KNOCK_ADDR + 104 <= len(data):
        vals = [u16le(data, KNOCK_ADDR+i*2) for i in range(52)]
        log(f"  Knock 0x{KNOCK_ADDR:06X}: [{' '.join(f'0x{v:04X}' for v in vals[:8])}...]")

    # SC bypass
    for off in SC_BYPASS:
        if off + 4 <= len(data):
            b = data[off:off+4]
            log(f"  SC bypass 0x{off:06X}: {b.hex(' ')}")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 10: Ignition detalji — prvih N mapa ako nađemo start
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 10: IGNITION MAPE — DETALJNA ANALIZA")
log("=" * 80)

def find_ign_start(data, search_start=0x020000, search_end=0x050000):
    """
    Traži početak niza ignition mapa:
    - Traži seriju od 3+ konsekutivnih 144B blokova koji svi izgledaju kao ign mape
    - Stride: točno 144B između mapa
    """
    candidates = []
    BLOCK = 144

    for off in range(search_start, search_end - BLOCK*5, 4):
        # Provjeri je li to početak niza od 5+ mapa
        ok_count = 0
        for i in range(27):  # Spark ima 27 mapa
            b_off = off + i * BLOCK
            if b_off + BLOCK > len(data):
                break
            ok, _ = check_ign_at(data, b_off)
            if ok:
                ok_count += 1
            else:
                break
        if ok_count >= 5:
            candidates.append((off, ok_count))
    return candidates

for name in ["spark_2018", "gti90_2020"]:
    if name not in bins:
        continue
    data = bins[name]
    log(f"\n{name} — tražim ignition niz:")

    starts = find_ign_start(data, 0x020000, 0x050000)
    if starts:
        for off, cnt in starts[:3]:
            log(f"  Ignition niz @ 0x{off:06X}: {cnt} uzastopnih mapa (stride 144B)")
            # Prikaži prvu mapu
            block = data[off:off+144]
            rows = [block[r*12:(r+1)*12] for r in range(12)]
            log(f"  Mapa #0 (12×12, u8, ×0.75°):")
            for row in rows:
                log(f"    {' '.join(f'{b:3d}' for b in row)}")
            # Prikaži statistike svih nađenih mapa
            log(f"  Statistike {cnt} mapa:")
            for i in range(cnt):
                b = data[off+i*144:off+i*144+144]
                log(f"    Mapa #{i:02d}: mean={sum(b)/144:.1f}° max={max(b)}° min={min(b)}°")
    else:
        log("  Nema ignition niza!")
        # Pokušaj s alternativnim stride vrijednostima
        for stride in [128, 160, 192, 256]:
            ok_count = 0
            best_off = None
            for off in range(0x020000, 0x050000, 4):
                cnt = 0
                for i in range(10):
                    b_off = off + i * stride
                    if b_off + 64 > len(data):
                        break
                    # Provjeri 8×8 blok
                    block = data[b_off:b_off+64]
                    vmean = sum(block)/64
                    if 10 <= vmean <= 70 and max(block) <= 100:
                        cnt += 1
                    else:
                        break
                if cnt >= 5 and cnt > ok_count:
                    ok_count = cnt
                    best_off = off
            if best_off:
                log(f"  Alt stride {stride}B: {ok_count} mapa @ 0x{best_off:06X}")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 11: Usporedba Spark 2018 vs 1630 na ključnim adresama
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 11: SPARK 2018 vs 1630 — ADRESNA USPOREDBA")
log("=" * 80)

KEY_ADDRESSES = {
    "Header": (0x0000, 32),
    "SW string": (0x0008, 32),
    "Checksum region": (0x0028, 16),
    "Boot end": (0x7EF0, 32),
    "CODE start": (0x010000, 32),
    "Rev @ 0x028E34": (0x028E34, 8),
    "Rev @ 0x028E7C": (0x028E7C, 8),
    "Rev @ 0x028E96": (0x028E96, 8),
    "IGN base": (0x02B730, 16),
    "INJ main": (0x02436C, 16),
    "Lambda main": (0x0266F0, 16),
    "Torque main": (0x02A0D8, 16),
    "SC bypass 1": (0x020534, 8),
    "DTC @ 0x0217EE": (0x0217EE, 32),
    "CAN @ 0x0433BC": (0x0433BC, 32),
}

if "spark_2018" in bins and "ref_1630" in bins:
    d_spark = bins["spark_2018"]
    d_1630  = bins["ref_1630"]
    log(f"\nspark_2018 vs ref_1630:")
    for lbl, (off, sz) in KEY_ADDRESSES.items():
        if off + sz > min(len(d_spark), len(d_1630)):
            log(f"  {lbl:25s}: VAN GRANICA")
            continue
        b1 = d_spark[off:off+sz]
        b2 = d_1630[off:off+sz]
        same = "ISTO" if b1 == b2 else "RAZLIČITO"
        log(f"  {lbl:25s}: {same}")
        if b1 != b2:
            log(f"    Spark: {b1.hex(' ')}")
            log(f"    1630 : {b2.hex(' ')}")

# ─────────────────────────────────────────────────────────────────────────────
# DIO 12: Sažetak i zaključci
# ─────────────────────────────────────────────────────────────────────────────

log("\n" + "=" * 80)
log("DIO 12: SAŽETAK")
log("=" * 80)

for name in bins:
    if name == "ref_1630":
        continue
    data = bins[name]
    log(f"\n{name} ({sw_string(data)}, {len(data):,}B):")

    # Filesize kategorija
    sz = len(data)
    if sz < 0x100000:
        log(f"  Veličina: {sz/1024:.0f}KB — Manji od 1630!")
    else:
        log(f"  Veličina: {sz/1024:.0f}KB")

    # Rev limiter
    for off, lbl in [(0x028E34, "Spark"), (0x028E7C, "GTI90")]:
        if off + 2 <= len(data):
            t = u16le(data, off)
            if 4000 <= t <= 7000:
                rpm = rpm_from_ticks(t)
                log(f"  Rev ({lbl}) @ 0x{off:06X}: {t} ticks = {rpm} RPM")

log("\n")
log("AUDIT ZAVRŠEN.")

# ─────────────────────────────────────────────────────────────────────────────
# Spremi rezultate
# ─────────────────────────────────────────────────────────────────────────────

output_path = Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/spark_gti90_audit.md")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("# Spark 900 ACE + GTI90 — Binarni Audit\n")
    f.write(f"**Datum**: 2026-03-19\n\n")
    f.write("```\n")
    f.write("\n".join(out))
    f.write("\n```\n")

print(f"\nRezultati spremljeni u: {output_path}")
