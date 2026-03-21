#!/usr/bin/env python3
"""CAN cross-SW audit za 1630 ACE dumps"""
import struct, os, collections

BASE = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali\dumps"

DUMPS_1630 = [
    (r"2018\1630ace\300.bin",  "2018_300"),
    (r"2019\1630ace\300.bin",  "2019_300"),
    (r"2020\1630ace\300.bin",  "2020_300"),
    (r"2020\1630ace\230.bin",  "2020_230"),
    (r"2021\1630ace\300.bin",  "2021_300"),  # REFERENCA
    (r"2021\1630ace\230.bin",  "2021_230"),
]

CAN_REF_ADDR = 0x0433BC  # referentna adresa za 2021_300
CAN_SCAN_START = 0x043000
CAN_SCAN_END   = 0x045000

# Poznati CAN IDs (ref 2021_300)
KNOWN_CAN_IDS = {
    0x0578: "cluster primary (267ms)",
    0x0400: "cluster secondary (311ms)",
    0x0102: "diag TX",
    0x0103: "diag TX",
    0x0110: "diag TX",
    0x0122: "diag TX",
    0x0300: "diag TX",
    0x0308: "diag TX",
    0x0408: "GTS specific?",
}

def load(rel):
    path = os.path.join(BASE, rel)
    with open(path, "rb") as f:
        return f.read()

def sw_string(data):
    raw = data[0x0008:0x0018]
    return raw.decode("ascii","replace").rstrip("\x00").rstrip()

def read_128b(data, addr):
    if addr + 128 > len(data):
        return None
    return data[addr:addr+128]

def find_can_ids_in_region(data, start, end):
    """Pronađi sve LE16 vrijednosti u 0x0100-0x07FF u regiji"""
    found = collections.defaultdict(list)
    end = min(end, len(data)-2)
    for addr in range(start, end, 2):
        v = struct.unpack_from("<H", data, addr)[0]
        if 0x0100 <= v <= 0x07FF:
            found[v].append(addr)
    return found

def search_can_id_bytes(data, can_id, center, radius=2048):
    """Traži LE bytes za can_id u ±radius od center"""
    lo = can_id & 0xFF
    hi = (can_id >> 8) & 0xFF
    pattern = bytes([lo, hi])
    results = []
    search_start = max(0, center - radius)
    search_end   = min(len(data), center + radius)
    pos = search_start
    while True:
        idx = data.find(pattern, pos, search_end)
        if idx == -1:
            break
        results.append(idx)
        pos = idx + 2
    return results

def find_can_table_offset(data, ref_id=0x0578):
    """Pronađi offset CAN tablice skeniranjem cijelog CODE regiona"""
    lo = ref_id & 0xFF
    hi = (ref_id >> 8) & 0xFF
    pattern = bytes([lo, hi])
    results = []
    for addr in range(0x020000, 0x060000, 2):
        if data[addr:addr+2] == pattern:
            results.append(addr)
    return results

def diff_128b(data_a, data_b, addr):
    """Usporedi 128B na zadanoj adresi"""
    a = data_a[addr:addr+128]
    b = data_b[addr:addr+128]
    if a == b:
        return 0, []
    diffs = [(i, a[i], b[i]) for i in range(min(len(a),len(b))) if a[i] != b[i]]
    return len(diffs), diffs

# ===== MAIN =====
print("=" * 70)
print("CAN CROSS-SW AUDIT — 1630 ACE")
print("=" * 70)

dumps_data = {}
for rel, label in DUMPS_1630:
    path = os.path.join(BASE, rel)
    if os.path.exists(path):
        dumps_data[label] = load(rel)
        d = dumps_data[label]
        sw = sw_string(d)
        print(f"[{label}] SW={sw!r} size={len(d):#x}")
    else:
        print(f"[{label}] MISSING")

ref_label = "2021_300"
if ref_label not in dumps_data:
    print("REFERENCA 2021_300 nije dostupna!")
    exit(1)

ref_data = dumps_data[ref_label]

# ===== 1. Čitaj 128B @ 0x0433BC =====
print("\n\n" + "="*70)
print(f"1. 128B @ 0x{CAN_REF_ADDR:06X} po dumpovima")
print("="*70)

ref_block = read_128b(ref_data, CAN_REF_ADDR)
print(f"\n[{ref_label}] @ 0x{CAN_REF_ADDR:06X}:")
if ref_block:
    # Prikaži kao LE16 vrijednosti
    vals = [struct.unpack_from("<H", ref_block, i*2)[0] for i in range(64)]
    can_vals = [(i*2, hex(v), KNOWN_CAN_IDS.get(v,"")) for i,v in enumerate(vals) if 0x0080 <= v <= 0x0FFF]
    print(f"  hex: {ref_block[:32].hex(' ')}")
    print(f"  CAN-range LE16 vrijednosti:")
    for off, v, note in can_vals:
        print(f"    +0x{off:02X}: {v}  {note}")
else:
    print("  NEMA podataka (addr izvan fajla)")

for label, d in dumps_data.items():
    if label == ref_label:
        continue
    block = read_128b(d, CAN_REF_ADDR)
    if block is None:
        print(f"\n[{label}] OUT OF RANGE")
        continue
    if block == ref_block:
        print(f"\n[{label}] @ 0x{CAN_REF_ADDR:06X}: IDENTIČAN referenci")
    else:
        n, diffs = diff_128b(ref_data, d, CAN_REF_ADDR)
        print(f"\n[{label}] @ 0x{CAN_REF_ADDR:06X}: {n} razlika od ref:")
        for off, va, vb in diffs[:20]:
            print(f"    +0x{off:02X}: ref={va:02X} this={vb:02X}")
        # Prikazi CAN IDs u ovom bloku
        vals = [struct.unpack_from("<H", block, i*2)[0] for i in range(64)]
        can_vals = [(i*2, hex(v), KNOWN_CAN_IDS.get(v,"")) for i,v in enumerate(vals) if 0x0080 <= v <= 0x0FFF]
        if can_vals:
            print(f"  CAN IDs u ovom bloku:")
            for off, v, note in can_vals:
                print(f"    +0x{off:02X}: {v}  {note}")

# ===== 2. Search 0x0578 u ±1KB =====
print("\n\n" + "="*70)
print(f"2. Scan za 0x0578 (bytes 78 05) u ±1KB od 0x{CAN_REF_ADDR:06X}")
print("="*70)

for label, d in dumps_data.items():
    hits = search_can_id_bytes(d, 0x0578, CAN_REF_ADDR, 1024)
    print(f"[{label}] 0x0578 found at: {[hex(h) for h in hits]}")

# ===== 3. CAN IDs u 0x043000-0x045000 =====
print("\n\n" + "="*70)
print(f"3. Sve CAN ID vrijednosti (0x0100-0x07FF) u regiji 0x{CAN_SCAN_START:06X}-0x{CAN_SCAN_END:06X}")
print("="*70)

for label, d in dumps_data.items():
    found = find_can_ids_in_region(d, CAN_SCAN_START, CAN_SCAN_END)
    print(f"\n[{label}] CAN IDs pronađeni ({len(found)} unique values):")
    for can_id in sorted(found.keys()):
        addrs = found[can_id]
        note = KNOWN_CAN_IDS.get(can_id, "")
        print(f"  {hex(can_id):8s} @ {[hex(a) for a in addrs[:5]]}  {note}")

# ===== 4. Specifično: 0x0578 i 0x0400 =====
print("\n\n" + "="*70)
print("4. Cluster IDs: 0x0578 i 0x0400 — prisutnost po SW")
print("="*70)

for target_id, name in [(0x0578, "cluster primary"), (0x0400, "cluster secondary"), (0x0408, "GTS?")]:
    print(f"\n{name} (0x{target_id:04X}):")
    for label, d in dumps_data.items():
        # Scan cijeli CODE region
        hits_code = search_can_id_bytes(d, target_id, 0x040000, 0x020000)  # ±20KB od 0x040000
        print(f"  [{label}]: {len(hits_code)} hits @ {[hex(h) for h in hits_code[:8]]}")

# ===== 5. Find actual CAN table offset =====
print("\n\n" + "="*70)
print("5. Tražim CAN tablicu (0x0578 LE16) u cijelom CODE region 0x020000-0x060000")
print("="*70)

for label, d in dumps_data.items():
    hits = find_can_table_offset(d, 0x0578)
    print(f"[{label}] 0x0578 u CODE: {[hex(h) for h in hits[:10]]}")

# ===== 6. Cross-SW diff za CAN region =====
print("\n\n" + "="*70)
print("6. Diff CAN regije (0x043000-0x045000) između SW varijanti")
print("="*70)

pairs = [
    ("2021_300","2021_230","300hp vs 230hp 2021"),
    ("2021_300","2020_300","2021_300 vs 2020_300"),
    ("2021_300","2019_300","2021_300 vs 2019_300"),
    ("2021_300","2018_300","2021_300 vs 2018_300"),
    ("2020_300","2020_230","2020: 300 vs 230"),
]

for la, lb, desc in pairs:
    if la not in dumps_data or lb not in dumps_data:
        continue
    da = dumps_data[la]
    db = dumps_data[lb]
    # Diff 0x043000-0x045000
    start = CAN_SCAN_START
    end_  = min(CAN_SCAN_END, len(da), len(db))
    diff_addrs = []
    for addr in range(start, end_, 4):
        if da[addr:addr+4] != db[addr:addr+4]:
            diff_addrs.append(addr)

    print(f"\n[{desc}]: {len(diff_addrs)} diff words u CAN regiji")
    if diff_addrs:
        for addr in diff_addrs[:20]:
            va = da[addr:addr+4].hex()
            vb = db[addr:addr+4].hex()
            va16 = struct.unpack_from("<H",da,addr)[0]
            vb16 = struct.unpack_from("<H",db,addr)[0]
            note_a = KNOWN_CAN_IDS.get(va16,"")
            note_b = KNOWN_CAN_IDS.get(vb16,"")
            print(f"  0x{addr:06X}: {va} vs {vb}  ({note_a} | {note_b})")

# ===== 7. Provjeri oko 0x0433BC za sve =====
print("\n\n" + "="*70)
print("7. Byte dump 0x0433BC-0x043440 za svaki dump (64 bytes)")
print("="*70)

for label, d in dumps_data.items():
    if CAN_REF_ADDR + 64 <= len(d):
        block = d[CAN_REF_ADDR:CAN_REF_ADDR+64]
        vals_le16 = [struct.unpack_from("<H", block, i*2)[0] for i in range(32)]
        can_like = [(i, hex(v)) for i,v in enumerate(vals_le16) if 0x0080 <= v <= 0x0FFF]
        print(f"[{label}] 0x{CAN_REF_ADDR:06X}: {block[:16].hex(' ')} ...")
        print(f"  CAN-like LE16: {can_like[:10]}")

print("\n\nDONE.")
