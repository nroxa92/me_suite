"""
Research task script — runs analysis on binary files and DIUS directory.
Results printed to stdout.
Run from me_suite root: python _materijali/research_task.py
"""

import os
import sys
import struct

BASE = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali"
DIUS_DIR = r"C:\Users\SeaDoo\Desktop\dius"

# ─── helpers ──────────────────────────────────────────────────────────────────

def hexdump(data, base_addr=0, width=16):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {base_addr+i:06X}  {hex_part:<{width*3}}  {asc_part}")
    return "\n".join(lines)

def read_u16_le_arr(data, offset, count):
    return [struct.unpack_from("<H", data, offset + i*2)[0] for i in range(count)]

def read_u16_be_arr(data, offset, count):
    return [struct.unpack_from(">H", data, offset + i*2)[0] for i in range(count)]

def read_u8_arr(data, offset, count):
    return list(data[offset:offset+count])

def extract_strings(data, min_len=8):
    """Extract printable ASCII runs of min_len+ chars."""
    results = []
    current = []
    start = 0
    for i, b in enumerate(data):
        if 0x20 <= b < 0x7F:
            if not current:
                start = i
            current.append(chr(b))
        else:
            if len(current) >= min_len:
                results.append((start, "".join(current)))
            current = []
    if len(current) >= min_len:
        results.append((start, "".join(current)))
    return results

def is_monotone(arr, allow_equal=True):
    for i in range(1, len(arr)):
        if allow_equal:
            if arr[i] < arr[i-1]:
                return False
        else:
            if arr[i] <= arr[i-1]:
                return False
    return True

def find_32col_axis(data, base_offset=0x023700, end_offset=0x024500):
    """Search for 32-value monotonically increasing u16 LE array."""
    candidates = []
    for off in range(base_offset, min(end_offset, len(data)-64), 2):
        arr = read_u16_le_arr(data, off, 32)
        if arr[0] > 0 and arr[-1] < 65000 and is_monotone(arr, allow_equal=False):
            candidates.append((off, arr))
    return candidates

# ─── Part 1: DIUS directory ───────────────────────────────────────────────────

print("="*80)
print("PART 1: DIUS DIRECTORY ANALYSIS")
print("="*80)

if not os.path.exists(DIUS_DIR):
    print(f"  DIUS directory NOT FOUND: {DIUS_DIR}")
else:
    print(f"  DIUS directory found: {DIUS_DIR}")
    for root, dirs, files in os.walk(DIUS_DIR):
        for f in files:
            fpath = os.path.join(root, f)
            fsize = os.path.getsize(fpath)
            print(f"\n  FILE: {fpath}  ({fsize:,} bytes)")
            try:
                with open(fpath, "rb") as fh:
                    raw = fh.read(min(fsize, 65536))

                # Header (first 64 bytes)
                print(f"  Header (first 64 bytes):")
                print(hexdump(raw[:64], base_addr=0))

                # Strings
                strings = extract_strings(raw)
                print(f"\n  Strings (ASCII 8+, first 60):")
                keywords = ["injection","ignition","lambda","knock","throttle","idle",
                            "torque","fuel","boost","map","rpm","table","calibr","axis",
                            "0x0","addr","inje","ign","inj","lam","kno","thr","boo"]
                shown = 0
                for soff, s in strings[:200]:
                    print(f"    {soff:06X}: {s[:120]}")
                    shown += 1
                    if shown >= 60:
                        break

                # Check for XML/JSON header
                text_prefix = raw[:100].decode("utf-8", errors="ignore").strip()
                if text_prefix.startswith("<?xml") or text_prefix.startswith("<"):
                    print(f"\n  *** XML FORMAT DETECTED ***")
                elif text_prefix.startswith("{") or text_prefix.startswith("["):
                    print(f"\n  *** JSON FORMAT DETECTED ***")

                # Known map keywords in strings
                all_text = " ".join(s for _, s in strings).lower()
                found_keywords = [kw for kw in keywords if kw in all_text]
                if found_keywords:
                    print(f"\n  ECU keywords found: {found_keywords}")

                # Look for 0x0XXXXX address patterns
                addr_strings = [(o, s) for o, s in strings
                                if any(c in s for c in ["0x02", "0x01", "0x03", "0x04"])
                                and len(s) >= 6]
                if addr_strings:
                    print(f"\n  Address-like strings:")
                    for o, s in addr_strings[:20]:
                        print(f"    {o:06X}: {s}")

            except Exception as e:
                print(f"  ERROR reading file: {e}")

# ─── Part 2: donor_10SW014510.bin analysis ────────────────────────────────────

print("\n" + "="*80)
print("PART 2: donor_10SW014510.bin ANALYSIS")
print("="*80)

donor_path = os.path.join(BASE, "donor_10SW014510.bin")
ori_path   = os.path.join(BASE, "ori_300.bin")

if not os.path.exists(donor_path):
    print(f"  FILE NOT FOUND: {donor_path}")
else:
    with open(donor_path, "rb") as f:
        donor = f.read()
    print(f"  Donor size: {len(donor):,} bytes (0x{len(donor):X})")

    # SW ID @ 0x001A
    sw_raw = donor[0x001A:0x0024]
    sw_id = sw_raw.rstrip(b"\x00").decode("ascii", errors="replace")
    print(f"\n  SW ID @ 0x001A: '{sw_id}'")

    # Header region 0x0040-0x0100
    print(f"\n  Header region 0x0040-0x0100:")
    print(hexdump(donor[0x40:0x100], base_addr=0x40))

    # Strings in 0x0000-0x1000
    print(f"\n  Strings in boot region (0x0000-0x1000):")
    boot_strings = extract_strings(donor[:0x1000])
    for off, s in boot_strings[:30]:
        print(f"    {off:06X}: {s}")

    # Check map locations
    checks = [
        ("Injection map",  0x02439C, "u16LE", 32, "first row"),
        ("Injection mirror", 0x02451C, "u16LE", 32, "first row"),
        ("Ignition #0",    0x02B730, "u8",    12, "first row"),
        ("Knock thresh",   0x0256F8, "u8",    32, "sequence"),
        ("Cold start",     0x025860, "u16LE", 12, "sequence"),
        ("RPM axis 1",     0x024F46, "u16BE", 16, "RPM axis"),
        ("Load axis",      0x02AFAC, "u16LE", 12, "load axis"),
        ("Rev lim soft",   0x022096, "u16LE",  1, "scalar"),
        ("Rev lim hard",   0x0220B6, "u16LE",  1, "scalar"),
        ("SC bypass",      0x020534, "u8",     7, "first row"),
    ]

    print(f"\n  MAP LOCATION CHECK (donor vs ori_300):")
    if os.path.exists(ori_path):
        with open(ori_path, "rb") as f:
            ori = f.read()
        print(f"  {'Map':<22} {'Addr':>8}  {'donor values':<50} {'match?'}")
        print(f"  {'-'*22} {'-'*8}  {'-'*50} {'-'*6}")
        for name, addr, dtype, count, label in checks:
            if addr + count*2 > len(donor):
                print(f"  {name:<22} {addr:08X}  OUT OF RANGE")
                continue
            if dtype == "u16LE":
                d_vals = read_u16_le_arr(donor, addr, count)
                o_vals = read_u16_le_arr(ori, addr, count) if addr + count*2 <= len(ori) else []
            elif dtype == "u16BE":
                d_vals = read_u16_be_arr(donor, addr, count)
                o_vals = read_u16_be_arr(ori, addr, count) if addr + count*2 <= len(ori) else []
            else:
                d_vals = read_u8_arr(donor, addr, count)
                o_vals = read_u8_arr(ori, addr, count) if addr + count <= len(ori) else []
            match = "SAME" if d_vals == o_vals else "DIFF"
            print(f"  {name:<22} {addr:08X}  {str(d_vals[:8]):<50} {match}")
    else:
        print("  ori_300.bin not found for comparison")

    # Detailed 0x025600-0x025A00
    print(f"\n  REGION 0x025600-0x025A00 hexdump (256B sample):")
    if 0x025A00 <= len(donor):
        print(hexdump(donor[0x025600:0x025700], base_addr=0x025600))
        print(f"\n  0x025700-0x025800:")
        print(hexdump(donor[0x025700:0x025800], base_addr=0x025700))
        print(f"\n  0x025800-0x025900:")
        print(hexdump(donor[0x025800:0x025900], base_addr=0x025800))
        print(f"\n  0x025900-0x025A00:")
        print(hexdump(donor[0x025900:0x025A00], base_addr=0x025900))

    # Knock threshold detailed comparison
    print(f"\n  KNOCK THRESHOLD @ 0x0256F8 (64 bytes):")
    if 0x0256F8 + 64 <= len(donor):
        d_knock = donor[0x0256F8:0x025738]
        print(f"  donor:  {list(d_knock)}")
        if os.path.exists(ori_path):
            o_knock = ori[0x0256F8:0x025738]
            print(f"  ori300: {list(o_knock)}")
            diffs = [(i, d_knock[i], o_knock[i]) for i in range(64) if d_knock[i] != o_knock[i]]
            print(f"  diffs:  {diffs}")

    # Diff summary vs ori_300
    if os.path.exists(ori_path) and len(donor) == len(ori):
        print(f"\n  DIFF SUMMARY (donor vs ori_300):")
        diffs = [(i, donor[i], ori[i]) for i in range(len(donor)) if donor[i] != ori[i]]
        print(f"  Total changed bytes: {len(diffs)}")
        # By region
        BOOT_END = 0x00FFFF
        CODE_S = 0x010000; CODE_E = 0x05FFFF
        CAL_S  = 0x060000
        boot_d = [d for d in diffs if d[0] <= BOOT_END]
        code_d = [d for d in diffs if CODE_S <= d[0] <= CODE_E]
        cal_d  = [d for d in diffs if d[0] >= CAL_S]
        print(f"  BOOT region: {len(boot_d)} bytes changed")
        print(f"  CODE region: {len(code_d)} bytes changed")
        print(f"  CAL region:  {len(cal_d)} bytes changed")

        if code_d:
            # Group into contiguous regions
            regions = []
            cur_start = code_d[0][0]
            cur_end = code_d[0][0]
            for _, (off, dv, ov) in enumerate(code_d[1:], 1):
                if off <= cur_end + 16:
                    cur_end = off
                else:
                    regions.append((cur_start, cur_end, cur_end - cur_start + 1))
                    cur_start = off
                    cur_end = off
            regions.append((cur_start, cur_end, cur_end - cur_start + 1))
            print(f"  CODE changed regions: {len(regions)}")
            print(f"  {'Start':>8}  {'End':>8}  {'Size':>6}")
            for rs, re, rsz in sorted(regions, key=lambda x: -x[2])[:30]:
                print(f"  {rs:08X}  {re:08X}  {rsz:6d}")

# ─── Part 4: Injection X-axis binary analysis ─────────────────────────────────

print("\n" + "="*80)
print("PART 4: INJECTION X-AXIS BINARY ANALYSIS (ori_300.bin)")
print("="*80)

if os.path.exists(ori_path):
    with open(ori_path, "rb") as f:
        ori = f.read()

    INJ_START = 0x02439C
    INJ_ROWS  = 12
    INJ_COLS  = 32
    INJ_END   = INJ_START + INJ_ROWS * INJ_COLS * 2  # 0x02461C

    # Region before injection map: 0x02430C - 0x02439C (0x90 = 144 bytes before)
    print(f"\n  REGION BEFORE INJECTION MAP (0x024300 - 0x02439C):")
    print(hexdump(ori[0x024300:INJ_START], base_addr=0x024300))

    # First row of injection map for reference
    first_row = read_u16_le_arr(ori, INJ_START, 32)
    print(f"\n  Injection map first row (0x02439C, 32×u16LE):")
    print(f"  {first_row}")

    # Region after injection map: 0x02461C - 0x024700
    print(f"\n  REGION AFTER INJECTION MAP (0x02461C - 0x024700):")
    print(hexdump(ori[INJ_END:0x024700], base_addr=INJ_END))

    # Region 0x024700-0x024800
    print(f"\n  REGION 0x024700-0x024800:")
    print(hexdump(ori[0x024700:0x024800], base_addr=0x024700))

    # Search for 32-value axis near injection map
    print(f"\n  SEARCH FOR 32-VALUE MONOTONE AXIS (u16LE) IN 0x023500-0x024500:")
    cands = find_32col_axis(ori, 0x023500, 0x024500)
    if cands:
        for off, arr in cands:
            print(f"  {off:06X}: {arr}")
    else:
        print("  None found in range 0x023500-0x024500")

    # Wider search
    print(f"\n  WIDER SEARCH 0x020000-0x026000:")
    cands2 = find_32col_axis(ori, 0x020000, 0x026000)
    if cands2:
        for off, arr in cands2:
            print(f"  {off:06X}: {arr}")
    else:
        print("  None found")

    # Look around 0x024E00-0x024F46
    print(f"\n  REGION 0x024D00-0x025000:")
    print(hexdump(ori[0x024D00:0x025000], base_addr=0x024D00))

    # Check if injection map has identical columns (would imply X-axis is not RPM)
    print(f"\n  INJECTION MAP COLUMN ANALYSIS:")
    inj_data = []
    for row in range(INJ_ROWS):
        row_data = read_u16_le_arr(ori, INJ_START + row * INJ_COLS * 2, INJ_COLS)
        inj_data.append(row_data)
        print(f"  Row {row:2d}: {row_data}")

    # Check if columns are identical (Alpha-N / load-only map = all cols same)
    col0 = [inj_data[r][0] for r in range(INJ_ROWS)]
    col31 = [inj_data[r][31] for r in range(INJ_ROWS)]
    row0_unique = len(set(inj_data[0]))
    print(f"\n  Row 0 unique values: {row0_unique} (32 if all different, 1 if all same)")
    print(f"  Col 0:  {col0}")
    print(f"  Col 31: {col31}")

    # Check structure between injection map and RPM axis (0x024F46)
    print(f"\n  REGION 0x02461C-0x024F46 (before RPM axis):")
    print(hexdump(ori[INJ_END:0x024F46], base_addr=INJ_END))

    # Look for load axis signature near injection
    LOAD_12 = [0, 100, 200, 400, 800, 1280, 2560, 3200, 3840, 4480, 5120, 5760]
    load_bytes = b"".join(struct.pack("<H", v) for v in LOAD_12)
    idx = 0
    occurrences = []
    while True:
        pos = ori.find(load_bytes, idx)
        if pos == -1:
            break
        occurrences.append(pos)
        idx = pos + 1
    print(f"\n  Load axis signature (12×u16LE) found at: {[hex(p) for p in occurrences]}")

    # Look for any 32-value sequence in the gap between inj and RPM axis
    gap_start = INJ_END
    gap_end   = 0x024F46
    print(f"\n  SEARCH 32-VAL AXIS IN GAP (0x{gap_start:X}-0x{gap_end:X}):")
    cands3 = find_32col_axis(ori, gap_start, gap_end)
    if cands3:
        for off, arr in cands3:
            print(f"  {off:06X}: {arr}")
    else:
        print("  None found in gap")

    # Check what's at 0x024F46-64 (before RPM axis 1)
    print(f"\n  Bytes just before RPM axis 1 @ 0x024F46 (0x024F00-0x024F46):")
    print(hexdump(ori[0x024F00:0x024F46], base_addr=0x024F00))

    # Also: injection map column 0 values — are they RPM-like?
    row_col0 = [inj_data[r][0] for r in range(12)]
    print(f"\n  Column 0 values (all rows): {row_col0}")
    print(f"  Are col values different across a row? Row 0 min={min(inj_data[0])}, max={max(inj_data[0])}")

    # Check if injection data has any axis embedded at beginning/end of block
    # Mirror at 0x02451C
    INJ_MIRROR = 0x02451C
    mirror_row0 = read_u16_le_arr(ori, INJ_MIRROR, 32)
    print(f"\n  Mirror injection @ 0x02451C first row: {mirror_row0}")

    # Additional: second injection map @ 0x02469C
    INJ2 = 0x02469C
    inj2_row0 = read_u16_le_arr(ori, INJ2, 32)
    print(f"\n  Third injection @ 0x02469C first row:  {inj2_row0}")

    # Bytes at 0x02437C - 0x02439C (just before injection)
    print(f"\n  32 bytes immediately before injection @ 0x02437C:")
    print(hexdump(ori[0x02437C:INJ_START], base_addr=0x02437C))

    # Check region from 0x023700 to injection start for 32-element sequences
    print(f"\n  SEARCH 32-VAL AXIS IN 0x023700-0x02439C:")
    cands4 = find_32col_axis(ori, 0x023700, INJ_START)
    if cands4:
        for off, arr in cands4:
            print(f"  {off:06X}: {arr}")
    else:
        print("  None found")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
