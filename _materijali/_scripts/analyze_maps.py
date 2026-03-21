import sys
import io
import struct
import os
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================
# FILE PATHS
# ============================================================
FILES = {
    'ori_300':    r'C:/Users/SeaDoo/Desktop/me_suite/_materijali/ori_300.bin',
    'rxp300_21':  r'C:/Users/SeaDoo/Desktop/ECU/BACKUP/RXP 300 21/21mh maps',
    'stg2_300':   r'C:/Users/SeaDoo/Desktop/me_suite/_materijali/npro_stg2_300.bin',
    'wake230':    r'C:/Users/SeaDoo/Desktop/ECU/DTC OFF/P0523/wakepro 230 20 p0523 ops off',
    'gti155':     r'C:/Users/SeaDoo/Desktop/ECU/BACKUP/GTI SE 155 18/30jd maps',
    'alen_flash': r'C:/Users/SeaDoo/Desktop/ECU/alen/SEA_DOO_ME17.8.5_INT FLASH_20260114144854.bin',
    'npro_spark': r'C:/Users/SeaDoo/Desktop/ECU/BACKUP/0NPRO/spark 18 STGII/maps',
}

CODE_START = 0x010000
CODE_END   = 0x060000

output_lines = []

def pr(*args, **kwargs):
    line = ' '.join(str(a) for a in args)
    print(line, **kwargs)
    output_lines.append(line)

def load_file(path):
    with open(path, 'rb') as f:
        return bytearray(f.read())

pr("=" * 80)
pr("ME17Suite — MAP RESEARCH ANALYSIS")
pr("=" * 80)

# Load all files
data = {}
for name, path in FILES.items():
    try:
        data[name] = load_file(path)
        pr(f"  [{name}] loaded: {len(data[name])} bytes (0x{len(data[name]):X})")
    except Exception as e:
        pr(f"  [{name}] FAILED: {e}")

pr()

# ============================================================
# HELPER: diff two byte arrays in CODE region
# ============================================================
def diff_code_regions(a, b, gap_tol=4):
    """Return list of (start, end) tuples of changed regions."""
    length = min(len(a), len(b), CODE_END)
    regions = []
    in_region = False
    reg_start = 0
    last_diff = -99

    for i in range(CODE_START, length):
        if a[i] != b[i]:
            if not in_region:
                in_region = True
                reg_start = i
            last_diff = i
        else:
            if in_region and (i - last_diff) > gap_tol:
                regions.append((reg_start, last_diff + 1))
                in_region = False
    if in_region:
        regions.append((reg_start, last_diff + 1))
    return regions


def guess_map_type(size):
    hints = []
    if 135 <= size <= 155:   hints.append("ignition 12x12 u8 (144B)")
    if 500 <= size <= 530:   hints.append("torque 16x16 u16 (512B)")
    if 755 <= size <= 780:   hints.append("injection 12x32 u16 (768B)")
    if 425 <= size <= 445:   hints.append("lambda 12x18 u16 (432B)")
    if 28 <= size <= 36:     hints.append("RPM axis 16×u16 (32B)")
    if 20 <= size <= 28:     hints.append("axis 12×u16 (24B)")
    return ', '.join(hints) if hints else ""


# ============================================================
# SECTION 1: ori_300 vs rxp300_21 DIFF (SAME SW)
# ============================================================
pr("=" * 80)
pr("SECTION 1: ori_300 vs rxp300_21 — SAME SW DIFF (CODE region)")
pr("=" * 80)

if 'ori_300' in data and 'rxp300_21' in data:
    ori = data['ori_300']
    rxp = data['rxp300_21']
    regions = diff_code_regions(ori, rxp, gap_tol=4)
    pr(f"  Total changed regions: {len(regions)}")
    total_changed = sum(e - s for s, e in regions)
    pr(f"  Total changed bytes: {total_changed}")
    pr()

    pr(f"  {'Address':>10}  {'Size':>6}  {'Type hint':<40}  First bytes (ori -> rxp)")
    pr(f"  {'-'*10}  {'-'*6}  {'-'*40}  {'-'*30}")

    interesting = []
    for (start, end) in sorted(regions):
        size = end - start
        hint = guess_map_type(size)
        ori_bytes = ' '.join(f'{b:02X}' for b in ori[start:start+8])
        rxp_bytes = ' '.join(f'{b:02X}' for b in rxp[start:start+8])
        pr(f"  0x{start:06X}    {size:>6}  {hint:<40}  {ori_bytes} -> {rxp_bytes}")
        if size > 10:
            interesting.append((start, end, size, hint))

    pr()
    pr(f"  Interesting regions (>10 bytes): {len(interesting)}")
    pr()

    # Detailed analysis of interesting regions
    pr("  --- Detailed analysis of interesting regions ---")
    for (start, end, size, hint) in interesting:
        pr()
        pr(f"  [0x{start:06X} - 0x{end:06X}] size={size} {hint}")
        # Print first 4 rows of ori and rxp as hex
        row_size = 16
        rows_to_show = min(4, (size + row_size - 1) // row_size)
        for r in range(rows_to_show):
            addr = start + r * row_size
            chunk_o = ori[addr:addr+row_size]
            chunk_x = rxp[addr:addr+row_size]
            pr(f"    ORI  0x{addr:06X}: {' '.join(f'{b:02X}' for b in chunk_o)}")
            pr(f"    RXP  0x{addr:06X}: {' '.join(f'{b:02X}' for b in chunk_x)}")

        # Check for axis-like u16 LE before region
        context_start = max(CODE_START, start - 64)
        pr(f"    Context [-64B before]: u16 LE values at 0x{context_start:06X}:")
        u16_vals = []
        for i in range(context_start, start, 2):
            v = struct.unpack_from('<H', ori, i)[0]
            u16_vals.append(v)
        pr(f"    {u16_vals[:16]}")

else:
    pr("  MISSING files for this comparison")

pr()

# ============================================================
# SECTION 2: ori_300 vs wake230 DIFF (DIFFERENT SW)
# ============================================================
pr("=" * 80)
pr("SECTION 2: ori_300 vs wake230 — DIFFERENT SW DIFF (CODE region)")
pr("=" * 80)

if 'ori_300' in data and 'wake230' in data:
    ori = data['ori_300']
    wake = data['wake230']
    regions_wake = diff_code_regions(ori, wake, gap_tol=4)
    pr(f"  Total changed regions: {len(regions_wake)}")
    total_changed_wake = sum(e - s for s, e in regions_wake)
    pr(f"  Total changed bytes: {total_changed_wake}")
    pr()

    pr(f"  {'Address':>10}  {'Size':>6}  {'Type hint':<40}")
    pr(f"  {'-'*10}  {'-'*6}  {'-'*40}")
    for (start, end) in sorted(regions_wake):
        size = end - start
        hint = guess_map_type(size)
        if hint:  # Only print ones with type hints
            pr(f"  0x{start:06X}    {size:>6}  {hint}")

    pr()
    # Show size distribution
    sizes = [e - s for s, e in regions_wake]
    size_buckets = defaultdict(int)
    for s in sizes:
        if s <= 4: size_buckets['1-4'] += 1
        elif s <= 16: size_buckets['5-16'] += 1
        elif s <= 64: size_buckets['17-64'] += 1
        elif s <= 200: size_buckets['65-200'] += 1
        elif s <= 600: size_buckets['201-600'] += 1
        else: size_buckets['>600'] += 1
    pr("  Size distribution:")
    for k, v in sorted(size_buckets.items()):
        pr(f"    {k:>10}: {v}")
else:
    pr("  MISSING files")

pr()

# ============================================================
# SECTION 3: STRUCTURAL SCAN of ori_300 CODE region
# ============================================================
pr("=" * 80)
pr("SECTION 3: STRUCTURAL SCAN of ori_300 CODE region")
pr("=" * 80)

if 'ori_300' not in data:
    pr("  ori_300 not loaded, skipping")
else:
    ori = data['ori_300']

    # ---- 3a: 12x12 u8 ignition candidates ----
    pr()
    pr("--- 3a: 12x12 u8 blocks (80%+ values in 16-58) — ignition candidates ---")
    ign_candidates = []
    stride = 1
    for addr in range(CODE_START, CODE_END - 144, stride):
        block = ori[addr:addr+144]
        in_range = sum(1 for b in block if 16 <= b <= 58)
        if in_range >= int(0.80 * 144):
            # Skip if overlaps last found
            if ign_candidates and addr < ign_candidates[-1][0] + 144:
                continue
            ign_candidates.append((addr, block))

    pr(f"  Found {len(ign_candidates)} candidates")
    for (addr, block) in ign_candidates[:40]:
        mean_val = sum(block) / len(block)
        vals_str = ' '.join(f'{b:02X}' for b in block[:12])
        pr(f"  0x{addr:06X}  mean={mean_val:.1f}  first_row: {vals_str}")

    # ---- 3b: 16x16 u16 BE torque candidates (Q8 0x5000-0xD000, even) ----
    pr()
    pr("--- 3b: 16x16 u16 BE blocks (all in 0x5000-0xD000, LSB patterns) — torque Q8 candidates ---")
    torque_candidates = []
    for addr in range(CODE_START, CODE_END - 512, 2):
        block = ori[addr:addr+512]
        vals = struct.unpack_from('>256H', block)
        if all(0x3000 <= v <= 0xF000 for v in vals):
            if torque_candidates and addr < torque_candidates[-1][0] + 512:
                continue
            torque_candidates.append((addr, vals))

    pr(f"  Found {len(torque_candidates)} candidates (Q8 relaxed: 0x3000-0xF000)")
    for (addr, vals) in torque_candidates[:20]:
        pr(f"  0x{addr:06X}  min=0x{min(vals):04X} max=0x{max(vals):04X}  first: {' '.join(f'{v:04X}' for v in vals[:8])}")

    # ---- 3c: 1D monotone u16 LE sequences (load axis candidates, len 12-18, range 100-9000) ----
    pr()
    pr("--- 3c: Monotone u16 LE sequences len=12-18, range 100-9000 — load/RPM axis candidates ---")
    axis_candidates = []
    for addr in range(CODE_START, CODE_END - 36, 2):
        for length in [12, 13, 14, 15, 16, 17, 18]:
            size = length * 2
            if addr + size > CODE_END:
                continue
            vals = list(struct.unpack_from(f'<{length}H', ori, addr))
            if not (100 <= vals[0] <= 9000 and 100 <= vals[-1] <= 9000):
                continue
            if vals != sorted(vals):
                continue
            # Must be strictly increasing
            if len(set(vals)) != len(vals):
                continue
            # Reasonable spacing (not too tight)
            diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
            if min(diffs) < 10:
                continue
            axis_candidates.append((addr, length, vals))
            break  # Don't double-count at same addr

    # Deduplicate overlapping
    deduped = []
    last_end = -1
    for (addr, length, vals) in sorted(axis_candidates):
        if addr >= last_end:
            deduped.append((addr, length, vals))
            last_end = addr + length * 2
    axis_candidates = deduped

    pr(f"  Found {len(axis_candidates)} candidates")
    for (addr, length, vals) in axis_candidates[:50]:
        pr(f"  0x{addr:06X}  len={length:2d}  {vals}")

    # ---- 3d: Mirror candidates (identical 200+ byte blocks) ----
    pr()
    pr("--- 3d: Mirror candidates (identical blocks >= 200 bytes) ---")
    MIN_MIRROR = 200
    mirror_candidates = []
    checked = set()

    # Build hash index of 200-byte blocks
    from hashlib import md5
    block_map = defaultdict(list)
    step = 4
    for addr in range(CODE_START, CODE_END - MIN_MIRROR, step):
        h = md5(ori[addr:addr+MIN_MIRROR]).digest()
        block_map[h].append(addr)

    # Find duplicates
    for h, addrs in block_map.items():
        if len(addrs) >= 2:
            # Expand the match
            a1, a2 = addrs[0], addrs[1]
            # Avoid already found pairs
            key = (a1 // 4, a2 // 4)
            if key in checked:
                continue
            checked.add(key)

            # Extend match
            ext = MIN_MIRROR
            while (a1 + ext < CODE_END and a2 + ext < CODE_END and
                   ori[a1 + ext] == ori[a2 + ext]):
                ext += 1

            mirror_candidates.append((a1, a2, ext))

    # Sort and deduplicate by start address
    mirror_candidates.sort()
    deduped_mirrors = []
    last_a1 = -9999
    last_a2 = -9999
    for (a1, a2, size) in mirror_candidates:
        if a1 - last_a1 < 50 and a2 - last_a2 < 50:
            continue
        deduped_mirrors.append((a1, a2, size))
        last_a1 = a1
        last_a2 = a2

    # Filter: size >= 200
    deduped_mirrors = [(a1, a2, s) for a1, a2, s in deduped_mirrors if s >= MIN_MIRROR]
    # Sort by size descending
    deduped_mirrors.sort(key=lambda x: -x[2])

    pr(f"  Found {len(deduped_mirrors)} mirror pairs (size >= {MIN_MIRROR}B)")
    pr(f"  {'Addr1':>10}  {'Addr2':>10}  {'Size':>8}  {'Offset':>8}  {'Type hint'}")
    pr(f"  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*8}  {'-'*30}")
    for (a1, a2, size) in deduped_mirrors[:40]:
        offset = a2 - a1
        hint = guess_map_type(size)
        pr(f"  0x{a1:06X}    0x{a2:06X}    {size:>8}  0x{offset:>6X}  {hint}")

    pr()

    # ---- EXTRA: Check known map addresses ----
    pr("--- KNOWN MAP VERIFICATION ---")
    known_maps = [
        (0x024F46, "RPM axis 1", 16, 'u16 BE'),
        (0x025010, "RPM axis 2", 16, 'u16 BE'),
        (0x0250DC, "RPM axis 3", 16, 'u16 BE'),
        (0x022096, "Rev limiter 1", 8, 'u16 BE'),
        (0x0220B6, "Rev limiter 2", 8, 'u16 BE'),
        (0x0220C0, "Rev limiter 3", 8, 'u16 BE'),
        (0x02B72A, "Rev limiter 4", 8, 'u16 BE'),
        (0x02B73E, "Rev limiter 5", 8, 'u16 BE'),
        (0x02B730, "Ignition map #0 start", 12, 'u8'),
        (0x02439C, "Injection map", 32, 'u16 LE'),
        (0x02451C, "Injection mirror", 32, 'u16 LE'),
        (0x02A0D8, "Torque map", 16, 'u16 BE'),
        (0x02A5F0, "Torque mirror", 16, 'u16 BE'),
        (0x0266F0, "Lambda map", 18, 'u16 LE'),
        (0x026C08, "Lambda mirror", 18, 'u16 LE'),
    ]
    for (addr, name, cols, fmt) in known_maps:
        if addr + cols * 2 <= len(ori):
            if fmt == 'u16 BE':
                vals = list(struct.unpack_from(f'>{cols}H', ori, addr))
            elif fmt == 'u16 LE':
                vals = list(struct.unpack_from(f'<{cols}H', ori, addr))
            else:
                vals = list(ori[addr:addr+cols])
            pr(f"  {name:<25} @ 0x{addr:06X}: {vals}")


# ============================================================
# SECTION 4: Cross-file comparison summary
# ============================================================
pr()
pr("=" * 80)
pr("SECTION 4: CROSS-FILE COMPARISON SUMMARY")
pr("=" * 80)

pairs = [
    ('ori_300', 'rxp300_21', 'SAME SW tune diff'),
    ('ori_300', 'stg2_300',  'ORI vs STG2 (diff SW)'),
    ('ori_300', 'wake230',   'ORI vs WAKE230 (diff SW)'),
    ('ori_300', 'gti155',    'ORI vs GTI155 (diff SW)'),
    ('ori_300', 'alen_flash','ORI vs ALEN FLASH (diff SW)'),
]

for (n1, n2, desc) in pairs:
    if n1 not in data or n2 not in data:
        pr(f"  [{n1} vs {n2}] SKIPPED (missing file)")
        continue
    d1 = data[n1]
    d2 = data[n2]
    regions = diff_code_regions(d1, d2, gap_tol=4)
    total = sum(e - s for s, e in regions)
    pr(f"  [{desc}]  regions={len(regions)}  changed_bytes={total}")

pr()

# ============================================================
# SECTION 5: Interesting u16 sequences near known map addresses
# ============================================================
pr("=" * 80)
pr("SECTION 5: U16 LE AXIS CANDIDATES — Near known injection/lambda/torque maps")
pr("=" * 80)

if 'ori_300' in data:
    ori = data['ori_300']
    SCAN_REGIONS = [
        (0x024000, 0x028000, "Around injection/lambda"),
        (0x02A000, 0x02C000, "Around torque/ignition"),
        (0x024F00, 0x025200, "Around RPM axes"),
    ]
    for (scan_s, scan_e, label) in SCAN_REGIONS:
        pr()
        pr(f"  --- {label} (0x{scan_s:06X} - 0x{scan_e:06X}) ---")
        for addr in range(scan_s, scan_e - 36, 2):
            for length in [12, 14, 16, 18, 32]:
                size = length * 2
                if addr + size > scan_e:
                    continue
                vals = list(struct.unpack_from(f'<{length}H', ori, addr))
                if not (50 <= vals[0] <= 10000 and 50 <= vals[-1] <= 10000):
                    continue
                if vals != sorted(vals) and vals != sorted(vals, reverse=True):
                    continue
                if len(set(vals)) != len(vals):
                    continue
                diffs = [abs(vals[i+1] - vals[i]) for i in range(len(vals)-1)]
                if min(diffs) < 5:
                    continue
                pr(f"    0x{addr:06X} len={length:2d}: {vals}")
                break

pr()
pr("=" * 80)
pr("ANALYSIS COMPLETE")
pr("=" * 80)

# ============================================================
# SAVE OUTPUT
# ============================================================
out_path = r'C:\Users\SeaDoo\Desktop\me_suite\_materijali\MAP_RESEARCH.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write("# MAP_RESEARCH — ME17Suite ECU Analysis\n\n")
    f.write("```\n")
    f.write('\n'.join(output_lines))
    f.write("\n```\n")

print(f"\nOutput saved to: {out_path}", file=sys.stdout)
