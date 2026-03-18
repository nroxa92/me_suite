#!/usr/bin/env python3
"""
GTI SE 155 (1.5L, SW 10SW025752) ECU mape istraživanje
Usporedba s 300hp reference (ori_300.bin, rxpx300_16_10SW004672.bin)
"""
import struct
import os

# Putanje do fajlova
BASE = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali"
GTI   = os.path.join(BASE, "gti_155_18_10SW025752.bin")
R300  = os.path.join(BASE, "ori_300.bin")
STG2  = os.path.join(BASE, "npro_stg2_300.bin")
OLD300 = r"C:\Users\SeaDoo\Desktop\ECU\MIX\300maps"  # bin fajl

def load(path):
    with open(path, "rb") as f:
        return bytearray(f.read())

def u16be(data, off): return struct.unpack_from(">H", data, off)[0]
def u16le(data, off): return struct.unpack_from("<H", data, off)[0]
def u32be(data, off): return struct.unpack_from(">I", data, off)[0]

def read_u16be_arr(data, off, n):
    return [u16be(data, off + i*2) for i in range(n)]

def read_u16le_arr(data, off, n):
    return [u16le(data, off + i*2) for i in range(n)]

def hex_block(data, off, n):
    return " ".join(f"{data[off+i]:02X}" for i in range(min(n, len(data)-off)))

def diff_regions(d1, d2, min_block=16):
    """Nađi najveće diff blokove između dva bin fajla."""
    size = min(len(d1), len(d2))
    diffs = []
    in_diff = False
    start = 0
    for i in range(size):
        if d1[i] != d2[i]:
            if not in_diff:
                in_diff = True
                start = i
        else:
            if in_diff:
                in_diff = False
                length = i - start
                if length >= min_block:
                    diffs.append((start, length))
    if in_diff:
        length = size - start
        if length >= min_block:
            diffs.append((start, length))
    return diffs

def match_score(d1, d2, off, n):
    """Koliko % bajtova se poklapa na istoj adresi."""
    total = 0
    match = 0
    for i in range(n):
        a = off + i
        if a < len(d1) and a < len(d2):
            total += 1
            if d1[a] == d2[a]:
                match += 1
    return (match/total*100) if total else 0

print("="*70)
print("GTI SE 155 (10SW025752) — ECU MAP RESEARCH")
print("="*70)

gti  = load(GTI)
r300 = load(R300)
old300 = load(OLD300)

print(f"\nGTI 155 size:  0x{len(gti):06X} ({len(gti)} bajta)")
print(f"ori_300 size:  0x{len(r300):06X} ({len(r300)} bajta)")
print(f"old300 size:   0x{len(old300):06X} ({len(old300)} bajta)")

# SW verzija info (tipično u BOOT header-u)
print("\n--- SW info (0x00–0x30) ---")
print(f"GTI[0x00..0x20]: {hex_block(gti, 0, 32)}")
print(f"300[0x00..0x20]: {hex_block(r300, 0, 32)}")
# Pokušaj naći SW string
for off in range(0, 0x100, 4):
    chunk = gti[off:off+12]
    try:
        s = chunk.decode("ascii")
        if any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
            print(f"  GTI ASCII @ 0x{off:04X}: {s!r}")
    except:
        pass

# ============================================================
# TOČKA 1+2: RPM OSE
# ============================================================
print("\n" + "="*70)
print("1+2. RPM OSE")
print("="*70)

rpm_300_addrs = [0x024F46, 0x025010, 0x0250DC]
for addr in rpm_300_addrs:
    vals_300 = read_u16be_arr(r300, addr, 16)
    vals_gti  = read_u16be_arr(gti, addr, 16)
    score = match_score(gti, r300, addr, 32)
    print(f"\nRPM_OS @ 0x{addr:06X} (16 x u16 BE):")
    print(f"  300hp:  {vals_300}")
    print(f"  GTI155: {vals_gti}")
    print(f"  Podudaranje: {score:.1f}%")

# Tražimo GTI RPM uzorke — 16 točaka, korak ~256 ili 512
# Tipičan RPM niz: 0, 512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 4608, 5120, 5632, 6144, 6656, 7168, 7750 (max ~7750 rpm GTI)
# u16 BE = big-endian
# 7750 rpm = 0x1E46
# Tražimo uzorak koji počinje s 0 ili 512 i raste

print("\n--- Traženje GTI RPM osi (skeniranje CODE regije 0x010000-0x05FFFF) ---")
candidates = []
for off in range(0x010000, 0x058000, 2):
    if off + 32 > len(gti):
        break
    v0 = u16be(gti, off)
    v1 = u16be(gti, off+2)
    v2 = u16be(gti, off+4)
    v15 = u16be(gti, off+30)
    # Uzorak: počinje <= 512, raste, završi 7000-8500
    if v0 <= 512 and v1 > v0 and v2 > v1 and 6500 <= v15 <= 8500:
        # Provjeri da li je monotono rastuće
        vals = read_u16be_arr(gti, off, 16)
        mono = all(vals[i] < vals[i+1] for i in range(15))
        if mono:
            candidates.append((off, vals))

print(f"Nađeno {len(candidates)} RPM-os kandidata:")
for off, vals in candidates[:15]:
    match_300 = "DA" if any(abs(off - a) < 4 for a in rpm_300_addrs) else "NOVO"
    print(f"  @ 0x{off:06X}: {vals} [{match_300}]")

# ============================================================
# TOČKA 3: IGNITION MAPE
# ============================================================
print("\n" + "="*70)
print("3. IGNITION MAPE")
print("="*70)

ign_base_300 = 0x02B730
ign_size = 144  # 12×12 u8
n_ign_300 = 19

print(f"\n300hp Ignition base: 0x{ign_base_300:06X}, {n_ign_300} mapa × {ign_size}B")

# Provjeri GTI na istoj adresi
for i in range(min(n_ign_300, 5)):
    addr = ign_base_300 + i * ign_size
    vals_300 = list(r300[addr:addr+16])
    vals_gti  = list(gti[addr:addr+16]) if addr + 16 <= len(gti) else []
    score = match_score(gti, r300, addr, ign_size)
    print(f"\n  IGN[{i}] @ 0x{addr:06X}: 300hp first16={vals_300}")
    print(f"         GTI155 first16={vals_gti}  match={score:.1f}%")

# Tražimo ignition uzorke u GTI
# Ignition vrijednosti: 0.75°/bit, tipično 0–200 raspon, 12×12=144 bajtova
# Tražimo blokove s vrijednostima u rasponu 20-250 (tipično kutovi paljenja × 0.75)
print("\n--- Traženje GTI Ignition blokova (12×12 u8, scan) ---")
ign_candidates = []
for off in range(0x020000, 0x050000, 2):
    if off + 144 > len(gti):
        break
    block = gti[off:off+144]
    # Karakteristike ignition mape: prosječna vrijednost ~60-160, min>5, max<250, gradijent
    avg = sum(block) / 144
    mn = min(block)
    mx = max(block)
    if 40 <= avg <= 180 and mn >= 4 and mx <= 252:
        # Provjeri da li ima smislenu strukturu (nije flat)
        variance = sum((b - avg)**2 for b in block) / 144
        if variance > 100:
            ign_candidates.append((off, avg, mn, mx, variance))

print(f"Nađeno {len(ign_candidates)} ignition kandidata (avg 40-180, variance>100):")
# Grupiraj bliske (serije)
prev_off = -9999
series = []
current_series = []
for off, avg, mn, mx, var in ign_candidates:
    if off - prev_off <= 144 + 4:
        current_series.append(off)
    else:
        if current_series:
            series.append(current_series)
        current_series = [off]
    prev_off = off
if current_series:
    series.append(current_series)

for s in series[:10]:
    base = s[0]
    count = len(s)
    vals_first16 = list(gti[base:base+16])
    match_300 = "DA" if abs(base - ign_base_300) < 10 else "NOVO"
    print(f"  Series @ 0x{base:06X}–0x{s[-1]:06X} ({count} blokova): first16={vals_first16} [{match_300}]")

# ============================================================
# TOČKA 4: INJECTION MAPA
# ============================================================
print("\n" + "="*70)
print("4. INJECTION MAPA")
print("="*70)

inj_addr_300 = 0x02436C  # 6×32 u16 LE iz memorije
inj_addr_300b = 0x02439C  # iz CLAUDE.md
inj_mirror_300 = 0x02451C

for addr, name in [(inj_addr_300, "inj_300_v1"), (inj_addr_300b, "inj_300_v2"), (inj_mirror_300, "inj_mirror")]:
    vals_300 = read_u16le_arr(r300, addr, 16) if addr + 32 <= len(r300) else []
    vals_gti  = read_u16le_arr(gti, addr, 16) if addr + 32 <= len(gti) else []
    score = match_score(gti, r300, addr, 64)
    print(f"\n{name} @ 0x{addr:06X}:")
    print(f"  300hp:  {vals_300}")
    print(f"  GTI155: {vals_gti}")
    print(f"  Match: {score:.1f}%")

# Skeniranje za injection uzorke (12×32 u16 LE, vrijednosti tipično 0–65000)
# Injection: gorivo ms/trims, tipično 200–5000 za ECU u16 LE
print("\n--- Traženje GTI Injection blokova (12×32=384 u16 LE, scan) ---")
inj_candidates = []
for off in range(0x020000, 0x050000, 2):
    if off + 384*2 > len(gti):
        break
    vals = read_u16le_arr(gti, off, 16)
    avg = sum(vals) / 16
    mn = min(vals)
    mx = max(vals)
    # Injection: tipično 100–15000, ima gradijent
    if 500 <= avg <= 12000 and mn >= 50 and mx <= 50000:
        variance = sum((v - avg)**2 for v in vals) / 16
        if variance > 50000:
            inj_candidates.append((off, avg, mn, mx))

print(f"Nađeno {len(inj_candidates)} injection kandidata:")
for off, avg, mn, mx in inj_candidates[:15]:
    vals = read_u16le_arr(gti, off, 8)
    match_300 = "DA" if abs(off - inj_addr_300b) < 8 else ""
    print(f"  @ 0x{off:06X}: avg={avg:.0f} min={mn} max={mx} first8={vals} {match_300}")

# ============================================================
# TOČKA 5: REV LIMITER
# ============================================================
print("\n" + "="*70)
print("5. REV LIMITER")
print("="*70)

rl_addrs_300 = [0x02B72A, 0x02B73E, 0x022096, 0x0220B6, 0x0220C0]
rl_val_300 = 8738  # 300hp rev limiter

for addr in rl_addrs_300:
    val_300 = u16be(r300, addr) if addr + 2 <= len(r300) else None
    val_gti  = u16be(gti, addr) if addr + 2 <= len(gti) else None
    print(f"  REV_LIM @ 0x{addr:06X}: 300hp={val_300} RPM, GTI155={val_gti} RPM")

# Tražimo 7750 rpm (= 0x1E46 u16 BE) ili blizu toga
# GTI 155 max ~7750 rpm
target_rpms = [7750, 7800, 7500, 8000, 7600]
print(f"\n--- Skeniranje za rev limiter vrijednosti (GTI spec ~7750 RPM) ---")
found_rl = []
for target in target_rpms:
    tb = struct.pack(">H", target)
    off = 0
    while True:
        idx = gti.find(tb, off, 0x060000)
        if idx == -1:
            break
        found_rl.append((idx, target, "BE"))
        off = idx + 1
    # Also LE
    tb_le = struct.pack("<H", target)
    off = 0
    while True:
        idx = gti.find(tb_le, off, 0x060000)
        if idx == -1:
            break
        if (idx, target, "BE") not in found_rl:
            found_rl.append((idx, target, "LE"))
        off = idx + 1

# Filtriraj samo CODE regiju
found_rl_code = [(off, val, fmt) for off, val, fmt in found_rl if 0x010000 <= off < 0x060000]
found_rl_code.sort()
print(f"Nađeno {len(found_rl_code)} pogodaka u CODE regiji:")
for off, val, fmt in found_rl_code[:30]:
    ctx = read_u16be_arr(gti, max(0, off-4), 6) if fmt == "BE" else read_u16le_arr(gti, max(0, off-4), 6)
    also_300 = any(abs(off - a) < 4 for a in rl_addrs_300)
    tag = " [=300hp addr]" if also_300 else ""
    print(f"  0x{off:06X}: {val} RPM ({fmt}){tag}  ctx={ctx}")

# ============================================================
# TOČKA 6: DIFF ANALIZA
# ============================================================
print("\n" + "="*70)
print("6. DIFF ANALIZA: GTI 155 vs ori_300")
print("="*70)

diffs = diff_regions(gti, r300, min_block=64)
diffs.sort(key=lambda x: -x[1])
print(f"Ukupno diff blokova >= 64B: {len(diffs)}")
print("\nTop 30 najvećih diff blokova:")
for start, length in diffs[:30]:
    # Provjeri je li to poznata mapa
    tags = []
    if abs(start - 0x02B730) < 300: tags.append("IGNITION")
    if abs(start - 0x02439C) < 200: tags.append("INJECTION")
    if abs(start - 0x02A0D8) < 300: tags.append("TORQUE")
    if abs(start - 0x0266F0) < 300: tags.append("LAMBDA")
    if abs(start - 0x024F46) < 100: tags.append("RPM_OS")
    if abs(start - 0x020534) < 100: tags.append("SC_BYPASS")
    if abs(start - 0x02B72A) < 50:  tags.append("REV_LIM")
    gti_first = hex_block(gti, start, min(16, length))
    r300_first = hex_block(r300, start, min(16, length))
    tag_str = " [" + ",".join(tags) + "]" if tags else ""
    print(f"  0x{start:06X}–0x{start+length-1:06X} ({length:5d}B){tag_str}")
    print(f"    GTI: {gti_first}")
    print(f"    300: {r300_first}")

# Broji ukupne razlike
total_diff = sum(l for _, l in diffs)
print(f"\nUkupno različitih bajtova (u blokovima >= 64B): {total_diff}")

# ============================================================
# TOČKA 7: GTI 155 vs OLD300 (10SW004672)
# ============================================================
print("\n" + "="*70)
print("7. GTI 155 vs OLD300 (10SW004672 = rxpx300_16)")
print("="*70)

diffs_old = diff_regions(gti, old300, min_block=64)
diffs_old.sort(key=lambda x: -x[1])
total_diff_old = sum(l for _, l in diffs_old)
print(f"GTI vs old300: {len(diffs_old)} diff blokova >= 64B, ukupno {total_diff_old} B različito")

diffs_300s = diff_regions(gti, r300, min_block=64)
total_diff_300 = sum(l for _, l in diffs_300s)
print(f"GTI vs ori_300: {len(diffs_300s)} diff blokova >= 64B, ukupno {total_diff_300} B različito")

if total_diff_old < total_diff_300:
    print(f"  => GTI je SLIČNIJI old300 ({total_diff_old} vs {total_diff_300} B razlike)")
else:
    print(f"  => GTI je SLIČNIJI ori_300 ({total_diff_300} vs {total_diff_old} B razlike)")

print("\nTop 15 diff blokova GTI vs old300:")
for start, length in diffs_old[:15]:
    gti_first = hex_block(gti, start, min(16, length))
    old_first = hex_block(old300, start, min(16, length))
    print(f"  0x{start:06X}–0x{start+length-1:06X} ({length:5d}B)")
    print(f"    GTI: {gti_first}")
    print(f"    OLD: {old_first}")

# ============================================================
# DETALJNIJA ANALIZA: torque, lambda, DFCO
# ============================================================
print("\n" + "="*70)
print("BONUS: TORQUE, LAMBDA, DFCO, IDLE RPM, SC/BOOST adrese")
print("="*70)

checks = [
    (0x02A0D8, "TORQUE_main",  16*2, "u16 BE Q8"),
    (0x02A5F0, "TORQUE_mirror",16*2, "u16 BE Q8"),
    (0x0266F0, "LAMBDA_main",  12*2, "u16 LE Q15"),
    (0x026C08, "LAMBDA_mirror",12*2, "u16 LE Q15"),
    (0x02202E, "DFCO",         7*2,  "u16 LE"),
    (0x02B600, "IDLE_RPM",     5*2,  "u16 LE"),
    (0x020534, "SC_BYPASS_sh", 7*7,  "u8"),
    (0x0205A8, "SC_BYPASS_act",7*7,  "u8"),
]

for addr, name, size, fmt in checks:
    vals_300 = list(r300[addr:addr+min(size,16)]) if addr+size <= len(r300) else []
    vals_gti  = list(gti[addr:addr+min(size,16)]) if addr+size <= len(gti) else []
    score = match_score(gti, r300, addr, size)
    match_tag = "DA" if score >= 80 else ("DJELOMIČNO" if score >= 40 else "NE")
    print(f"\n{name} @ 0x{addr:06X} ({fmt}):")
    print(f"  300hp:  {[hex(v) for v in vals_300]}")
    print(f"  GTI155: {[hex(v) for v in vals_gti]}")
    print(f"  Podudaranje: {score:.1f}% [{match_tag}]")

# ============================================================
# SUMARNA TABLICA
# ============================================================
print("\n" + "="*70)
print("SUMARNA TABLICA — GTI 155 adrese")
print("="*70)

def check_addr(data_gti, data_300, addr, n_bytes):
    score = match_score(data_gti, data_300, addr, n_bytes)
    if score >= 95: return "DA"
    if score >= 60: return "DJELOMIČNO"
    return "NE"

summary = [
    ("RPM_OS_1",    0x024F46, 32, "u16 BE, 16pt"),
    ("RPM_OS_2",    0x025010, 32, "u16 BE, 16pt"),
    ("RPM_OS_3",    0x0250DC, 32, "u16 BE, 16pt"),
    ("IGN_base",    0x02B730, 144,"12×12 u8"),
    ("INJECTION",   0x02439C, 192,"12×32? u16 LE"),
    ("TORQUE",      0x02A0D8, 512,"16×16 Q8"),
    ("LAMBDA",      0x0266F0, 432,"12×18 Q15 LE"),
    ("REV_LIM_1",   0x02B72A, 2,  "u16 BE"),
    ("REV_LIM_2",   0x02B73E, 2,  "u16 BE"),
    ("SC_BYPASS",   0x020534, 49, "7×7 u8"),
    ("DFCO",        0x02202E, 14, "u16 LE"),
    ("IDLE_RPM",    0x02B600, 120,"u16 LE"),
]

print(f"{'MAPA':<20} {'ADRESA':<10} {'DIMS':<18} {'GTI=300hp?':<15} {'GTI first 8B'}")
print("-"*80)
for name, addr, size, fmt in summary:
    tag = check_addr(gti, r300, addr, size)
    gti_hex = hex_block(gti, addr, 8) if addr + 8 <= len(gti) else "N/A"
    print(f"{name:<20} 0x{addr:06X}  {fmt:<18} {tag:<15} {gti_hex}")

print("\n[GOTOVO]")
