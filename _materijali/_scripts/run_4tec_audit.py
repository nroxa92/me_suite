#!/usr/bin/env python3
"""4TEC 1503 audit skriptica"""
import struct, os, collections

BASE = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali\dumps"

DUMPS = [
    (r"2018\4tec1503\130v1.bin", "2018_130v1"),
    (r"2018\4tec1503\130v2.bin", "2018_130v2"),
    (r"2018\4tec1503\155v1.bin", "2018_155v1"),
    (r"2018\4tec1503\155v2.bin", "2018_155v2"),
    (r"2018\4tec1503\230.bin",   "2018_230"),
    (r"2019\4tec1503\130.bin",   "2019_130"),
    (r"2019\4tec1503\155.bin",   "2019_155"),
    (r"2019\4tec1503\230.bin",   "2019_230"),
    (r"2020\4tec1503\130.bin",   "2020_130"),
]

def load(rel):
    with open(os.path.join(BASE, rel), "rb") as f:
        return f.read()

def sw_string(data):
    raw = data[0x0008:0x0018]
    return raw.decode("ascii","replace").rstrip("\x00").rstrip()

def file_header(data):
    return data[0:16].hex(" ")

def find_ignition_maps(data, label):
    """Traži 12×12 u8 blokove koji izgledaju kao ignition mape (vrijednosti 0-200 tipično)"""
    results = []
    # Skeniraj CODE regiju 0x010000-0x05FFFF
    start = 0x010000
    end   = min(0x060000, len(data) - 144)

    for addr in range(start, end - 144, 4):
        block = data[addr:addr+144]
        vals = list(block)
        mn, mx = min(vals), max(vals)
        # Ignition: tipično 0-200 range, nije sve nule, nije sve iste
        if mn >= 0 and mx <= 200 and mx - mn > 10 and mn < 50:
            # Provjeri da nije nasumičan — majority treba biti u 0-150
            in_range = sum(1 for v in vals if 0 <= v <= 150)
            if in_range >= 120:
                results.append((addr, mn, mx))
    return results

def find_ignition_maps_8x8(data):
    """Traži 8×8=64 byte blokove"""
    results = []
    start = 0x010000
    end   = min(0x060000, len(data) - 64)
    for addr in range(start, end - 64, 4):
        block = data[addr:addr+64]
        vals = list(block)
        mn, mx = min(vals), max(vals)
        if mn >= 0 and mx <= 200 and mx - mn > 10 and mn < 50:
            in_range = sum(1 for v in vals if 0 <= v <= 150)
            if in_range >= 56:
                results.append((addr, mn, mx))
    return results

def find_injection_maps(data, rows=16, cols=12):
    """Traži LE u16 Q15 blokove (injection: tipično 0x0000-0x7FFF)"""
    results = []
    size = rows * cols * 2
    start = 0x010000
    end   = min(0x060000, len(data) - size)

    for addr in range(start, end - size, 2):
        block = data[addr:addr+size]
        vals = [struct.unpack_from("<H", block, i*2)[0] for i in range(rows*cols)]
        mn, mx = min(vals), max(vals)
        # Q15: 0x4000=0.5, 0x7FFF=1.0 tipično za injection
        if 0x1000 < mn and mx <= 0x7FFF and mx - mn > 0x0500:
            nonzero = sum(1 for v in vals if v > 0x0100)
            if nonzero >= rows * cols - 4:
                results.append((addr, hex(mn), hex(mx)))
    return results

def find_injection_8x8(data):
    """16×8 ili 8×8 injekcija"""
    results = []
    for rows, cols in [(16,8),(8,8),(12,12),(16,10)]:
        size = rows * cols * 2
        start = 0x010000
        end   = min(0x060000, len(data) - size)
        for addr in range(start, end - size, 2):
            block = data[addr:addr+size]
            vals = [struct.unpack_from("<H", block, i*2)[0] for i in range(rows*cols)]
            mn, mx = min(vals), max(vals)
            if 0x1000 < mn and mx <= 0x7FFF and mx - mn > 0x0500:
                nonzero = sum(1 for v in vals if v > 0x0100)
                if nonzero >= rows * cols - 4:
                    results.append((addr, f"{rows}x{cols}", hex(mn), hex(mx)))
    return results

def find_rev_limiter(data):
    """Traži rev limiter (LE u16 ticks): RPM = 40e6*60/(ticks*58)"""
    results = []
    # Tipično za 7000-8500 RPM
    # ticks = 40e6*60/(RPM*58)
    # @ 7000: ~5882, @ 8500: ~4839
    for addr in range(0x010000, min(0x060000, len(data)-2), 2):
        ticks = struct.unpack_from("<H", data, addr)[0]
        if 4500 <= ticks <= 6500:
            rpm = int(40e6 * 60 / (ticks * 58))
            results.append((addr, ticks, rpm))
    return results

def find_dtc_p_codes(data):
    """Traži P-kodove u LE16 formatu"""
    # P-kodovi za 1503: tipično P0xxx i P1xxx
    # LE16: P0100 = 0x0064, P0300 = 0x012C
    # Traži pattern: sekvencijalni P-kodovi u tablici
    found_seqs = []
    for addr in range(0x010000, min(0x060000, len(data)-4), 2):
        v = struct.unpack_from("<H", data, addr)[0]
        # P0xxx = 0x0000-0x3FFF ish... ali Bosch enkodira DTC kao SAE raw
        # Stvarni DTC: 0x0000-0xFFFF, P0xxx MSN=0, P1xxx MSN=1 u SAE
        # Traži sekvence gdje 3+ uzastopnih LE16 vrijednosti su rastuće P-kodovi
        if 0x0010 < v < 0x4000:
            # provjeri sljedeće
            v2 = struct.unpack_from("<H", data, addr+2)[0]
            v3 = struct.unpack_from("<H", data, addr+4)[0]
            if v < v2 < v3 and v2 - v < 0x100 and v3 - v2 < 0x100:
                found_seqs.append((addr, v, v2, v3))
    return found_seqs[:20]

def find_u16ax_codes(data, label):
    """Traži U16Ax DTC kodove: 0xD6A1-0xD6AB u LE16"""
    results = []
    for code in range(0xD6A1, 0xD6AC):
        lo = code & 0xFF
        hi = (code >> 8) & 0xFF
        pattern = bytes([lo, hi])
        pos = 0
        while True:
            idx = data.find(pattern, pos, 0x060000)
            if idx == -1:
                break
            if idx >= 0x010000:
                results.append((idx, hex(code)))
            pos = idx + 1
    return results

def find_specific_dtc_tables(data):
    """
    Traži DTC storage: za 1630 je double (main+mirror).
    Za 1503 provjeri je li single ili double.
    Sekvencijalni DTC u LE16.
    """
    # Uobičajeni P0xxx kodovi koje znamo za 1630:
    known_1630 = [0x0031, 0x0032, 0x0053, 0x0054, 0x0068, 0x006E, 0x0072, 0x0087, 0x0088]

    results = []
    for addr in range(0x010000, min(0x060000, len(data)-20), 2):
        v = struct.unpack_from("<H", data, addr)[0]
        if v == known_1630[0]:
            # Provjeri je li cijela sekvenca tu
            match = 0
            for i, expected in enumerate(known_1630):
                got = struct.unpack_from("<H", data, addr + i*2)[0]
                if got == expected:
                    match += 1
            if match >= 5:
                results.append((addr, match, "possible DTC table"))
    return results

def scan_ign_addresses_1630_style(data):
    """Provjeri rade li iste adrese kao 1630: 0x02B730+ (19× mapa, svakih 144B)"""
    results = []
    base = 0x02B730
    for i in range(25):
        addr = base + i * 144
        if addr + 144 > len(data):
            break
        block = data[addr:addr+144]
        vals = list(block)
        mn, mx = min(vals), max(vals)
        if mx - mn > 5:
            results.append((addr, i, mn, mx))
    return results

def scan_inj_addresses_1630_style(data):
    """Provjeri 1630 injection adrese: 0x02436C, 0x0244EC"""
    results = []
    for addr in [0x02436C, 0x0244EC, 0x022066]:
        if addr + 384 > len(data):
            results.append((addr, "OUT_OF_RANGE"))
            continue
        block = data[addr:addr+384]
        vals = [struct.unpack_from("<H", block, i*2)[0] for i in range(192)]
        mn, mx = min(vals), max(vals)
        results.append((addr, f"min={hex(mn)} max={hex(mx)} range={hex(mx-mn)}"))
    return results

def rev_near(data, centers):
    """Čitaj ticks u ±32B od poznatih 1630 rev limiter adresa"""
    results = []
    for c in centers:
        for off in range(-32, 33, 2):
            addr = c + off
            if 0 <= addr < len(data)-1:
                ticks = struct.unpack_from("<H", data, addr)[0]
                if 4500 <= ticks <= 7000:
                    rpm = int(40e6 * 60 / (ticks * 58))
                    results.append((addr, ticks, rpm, f"near 0x{c:06X}"))
    return results

def diff_blocks(data_a, data_b, region_start=0x010000, region_end=0x060000, chunk=256):
    """Pronađi chunks koji se razlikuju između dva dupa."""
    diffs = []
    end = min(region_end, len(data_a), len(data_b))
    for addr in range(region_start, end, chunk):
        a = data_a[addr:addr+chunk]
        b = data_b[addr:addr+chunk]
        if a != b:
            # Koliko bajtova je različito
            changed = sum(1 for x,y in zip(a,b) if x!=y)
            diffs.append((addr, changed))
    return diffs

# ===== MAIN =====
print("=" * 70)
print("4TEC 1503 AUDIT")
print("=" * 70)

dumps_data = {}
for rel, label in DUMPS:
    path = os.path.join(BASE, rel)
    if os.path.exists(path):
        dumps_data[label] = load(rel)
        d = dumps_data[label]
        sw = sw_string(d)
        hdr = file_header(d)
        print(f"\n{'='*60}")
        print(f"[{label}] SW={sw!r} size={len(d):#x} ({len(d)} B)")
        print(f"  header: {hdr}")
    else:
        print(f"[{label}] MISSING: {path}")

# --- Ignition scan ---
print("\n\n" + "="*70)
print("IGNITION MAPS SCAN (12×12 u8 @ CODE regija)")
print("="*70)

for label, d in dumps_data.items():
    # Provjeri 1630 adrese
    ign_1630 = scan_ign_addresses_1630_style(d)
    print(f"\n[{label}] 1630-style ign check (0x02B730+, svakih 144B):")
    if ign_1630:
        for addr, i, mn, mx in ign_1630[:10]:
            print(f"  #{i:02d} @ 0x{addr:06X}: min={mn} max={mx}")
    else:
        print("  NEMA sadržaja na 1630 adresama")

# --- Injection scan ---
print("\n\n" + "="*70)
print("INJECTION MAPS SCAN")
print("="*70)

for label, d in dumps_data.items():
    inj = scan_inj_addresses_1630_style(d)
    print(f"\n[{label}] 1630-style inj check:")
    for addr, info in inj:
        print(f"  0x{addr:06X}: {info}")

# --- Rev limiter ---
print("\n\n" + "="*70)
print("REV LIMITER SCAN")
print("="*70)

# 1630 poznate adrese
known_rl_1630 = [0x022096, 0x0220B6, 0x0220C0, 0x02B72A, 0x02B73E, 0x028E96]

for label, d in dumps_data.items():
    near = rev_near(d, known_rl_1630)
    print(f"\n[{label}] Rev limiter ticks (4500-7000 range = 8500-5300 RPM):")
    # Group by address proximity
    seen_addrs = set()
    for addr, ticks, rpm, note in near:
        if addr not in seen_addrs:
            print(f"  0x{addr:06X}: {ticks} ticks → {rpm} RPM  ({note})")
            seen_addrs.add(addr)
    if not near:
        # Broad scan
        broad = find_rev_limiter(d)
        print(f"  Broad scan: {len(broad)} hits, prvi: {broad[:5]}")

# --- DTC scan ---
print("\n\n" + "="*70)
print("DTC SCAN — single vs double storage?")
print("="*70)

for label, d in dumps_data.items():
    u16ax = find_u16ax_codes(d, label)
    print(f"\n[{label}] U16Ax (0xD6A1-0xD6AB):")
    if u16ax:
        for addr, code in u16ax[:10]:
            print(f"  {code} @ 0x{addr:06X}")
    else:
        print("  NEMA U16Ax kodova")

# --- DTC table detection ---
print("\n\n" + "="*70)
print("DTC TABLE LOCATION SCAN")
print("="*70)

for label, d in dumps_data.items():
    dtc_seqs = find_specific_dtc_tables(d)
    print(f"\n[{label}] DTC table candidates:")
    if dtc_seqs:
        for addr, match, note in dtc_seqs:
            print(f"  0x{addr:06X}: {match}/9 matches — {note}")
    else:
        # Tražimo sekvencijalni P-kodove
        seqs = find_dtc_p_codes(d)
        if seqs:
            print(f"  Sequential P-code sequences ({len(seqs)} found):")
            for addr, v, v2, v3 in seqs[:5]:
                print(f"    0x{addr:06X}: {hex(v)},{hex(v2)},{hex(v3)}")
        else:
            print("  Nema prepoznatljive DTC tablice")

# --- Diff analysis ---
print("\n\n" + "="*70)
print("DIFF ANALYSIS — koji blokovi se razlikuju?")
print("="*70)

label_pairs = [
    ("2018_130v1","2018_155v1","130v1 vs 155v1 (isti SW?)"),
    ("2018_130v2","2018_155v2","130v2 vs 155v2 (isti SW?)"),
    ("2018_130v1","2018_130v2","2018_130: v1 vs v2"),
    ("2019_130","2019_155","2019: 130 vs 155"),
    ("2019_130","2020_130","2019_130 vs 2020_130"),
    ("2018_230","2019_230","2018_230 vs 2019_230"),
    ("2018_130v2","2019_130","2018v2_130 vs 2019_130"),
]

for la, lb, desc in label_pairs:
    if la in dumps_data and lb in dumps_data:
        da = dumps_data[la]
        db = dumps_data[lb]
        diffs = diff_blocks(da, db)
        total_diff = sum(c for _,c in diffs)
        print(f"\n[{desc}]")
        print(f"  Različitih 256B chunkova: {len(diffs)}")
        print(f"  Ukupno promijenjenih bajtova: ~{total_diff}")
        if len(diffs) <= 20:
            for addr, cnt in diffs:
                print(f"    0x{addr:06X}: {cnt}B")
        else:
            print(f"  Prvih 10 diff blokova:")
            for addr, cnt in diffs[:10]:
                print(f"    0x{addr:06X}: {cnt}B")

# --- Custom ign scan za 1503 ---
print("\n\n" + "="*70)
print("CUSTOM IGN SCAN (8×8 i 12×12 blokovi) — prvih 5 hittova")
print("="*70)

for label, d in dumps_data.items():
    hits_12 = find_ignition_maps(d, label)
    hits_8 = find_ignition_maps_8x8(d)
    print(f"\n[{label}] 12×12 candidates: {len(hits_12)}, 8×8 candidates: {len(hits_8)}")
    if hits_12:
        print(f"  12×12 prvih 5: {[(hex(a),mn,mx) for a,mn,mx in hits_12[:5]]}")
    if hits_8:
        # Samo oni koji nisu pokriveni 12×12
        addrs_12 = {a for a,_,_ in hits_12}
        unique_8 = [(a,mn,mx) for a,mn,mx in hits_8 if a not in addrs_12]
        print(f"  8×8 unique (nije u 12×12): {len(unique_8)}, prvih 5: {[(hex(a),mn,mx) for a,mn,mx in unique_8[:5]]}")

print("\n\nDONE.")
