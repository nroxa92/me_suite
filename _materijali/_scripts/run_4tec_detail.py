#!/usr/bin/env python3
"""4TEC 1503 detalji: SW string, rev limiter, injection"""
import struct, os

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

# SW string - pokusaj razlicite offsete
def find_sw_string(data):
    """Trazi SW string 10SWxxxxxx u binariju"""
    target = b"10SW"
    results = []
    pos = 0
    while True:
        idx = data.find(target, pos)
        if idx == -1:
            break
        s = data[idx:idx+12].decode("ascii", "replace")
        results.append((idx, s))
        pos = idx + 1
    return results

def find_sw_1037(data):
    """Trazi SW string 1037xxxxxx"""
    target = b"1037"
    results = []
    pos = 0
    while True:
        idx = data.find(target, pos)
        if idx == -1:
            break
        s = data[idx:idx+12].decode("ascii", "replace")
        results.append((idx, s))
        pos = idx + 1
    return results[:5]

print("=" * 70)
print("SW STRINGS")
print("=" * 70)

dumps_data = {}
for rel, label in DUMPS:
    dumps_data[label] = load(rel)
    d = dumps_data[label]
    sw1 = find_sw_string(d)
    sw2 = find_sw_1037(d)
    print(f"\n[{label}]")
    if sw1:
        for addr, s in sw1[:3]:
            print(f"  10SW @ 0x{addr:06X}: {s!r}")
    if sw2:
        for addr, s in sw2[:3]:
            print(f"  1037 @ 0x{addr:06X}: {s!r}")
    if not sw1 and not sw2:
        # Hex dump od 0x0008
        raw8 = d[0x0008:0x0028]
        print(f"  @ 0x0008 (hex): {raw8.hex(' ')}")
        print(f"  @ 0x0008 (ascii): {raw8.decode('ascii','replace')!r}")

print("\n" + "=" * 70)
print("REV LIMITER - broad scan 1503")
print("=" * 70)

# Za 1503 (4cil, korak/nema info o broju cilindra) - pokusaj razne formule
# Ako je 4-cil i 60-2 kotacic: RPM = 40e6*60 / (ticks * N * cyl_factor)
# Standardni ME17 1630 formula: RPM = 40MHz*60/(ticks*58) gdje 58=60-2 zubi * 3cil / 3cil = nesto
# Za 4-cil: ticks se racunaju drugacije
# Pokusamo: RPM = 40e6*60/(ticks*58) i RPM = 40e6*60/(ticks*29) itd.

for label, d in dumps_data.items():
    print(f"\n[{label}] Ticks u CODE regiji (5000-8000 range):")
    hits = {}
    for addr in range(0x010000, min(0x060000, len(d)-2), 2):
        ticks = struct.unpack_from("<H", d, addr)[0]
        if 4800 <= ticks <= 9000:
            # Formula 1: kao 1630 (58)
            rpm_58 = int(40e6 * 60 / (ticks * 58))
            # Formula 2: 4cil 60-2 = 58 zubi, ali drugaci period
            rpm_29 = int(40e6 * 60 / (ticks * 29))
            # Formula 3: 116 (2x)
            rpm_116 = int(40e6 * 60 / (ticks * 116))
            if 6000 <= rpm_58 <= 9000:
                hits[addr] = (ticks, rpm_58, rpm_29, rpm_116)
    # Filter: trazi grupe od 2-4 bliskih adresa
    sorted_hits = sorted(hits.items())
    groups = []
    if sorted_hits:
        grp = [sorted_hits[0]]
        for i in range(1, len(sorted_hits)):
            if sorted_hits[i][0] - grp[-1][0] <= 16:
                grp.append(sorted_hits[i])
            else:
                if len(grp) >= 2:
                    groups.append(grp)
                grp = [sorted_hits[i]]
        if len(grp) >= 2:
            groups.append(grp)

    print(f"  Grupe (2+ bliski ticks):")
    for grp in groups[:10]:
        for addr, (t, r58, r29, r116) in grp:
            print(f"    0x{addr:06X}: {t} ticks → rpm_58={r58}, rpm_29={r29}, rpm_116={r116}")

# Specificno provjeri 1630 RL adrese u 1503
print("\n" + "=" * 70)
print("REV LIMITER - provjera 1630 poznatih adresa u 1503")
print("=" * 70)

# Poznate adrese za 1630: 0x022096, 0x0220B6, 0x0220C0, 0x02B72A, 0x02B73E, 0x028E96
rl_addrs_1630 = [0x022096, 0x0220B6, 0x0220C0, 0x02B72A, 0x02B73E, 0x028E96]

for label, d in dumps_data.items():
    print(f"\n[{label}]:")
    for addr in rl_addrs_1630:
        if addr + 2 <= len(d):
            ticks = struct.unpack_from("<H", d, addr)[0]
            rpm_58 = int(40e6 * 60 / ticks / 58) if ticks > 0 else 0
            print(f"  0x{addr:06X}: {ticks} (0x{ticks:04X}) → {rpm_58} RPM (formula 58)")

print("\n" + "=" * 70)
print("INJECTION MAPS - trazenje u 1503")
print("=" * 70)

# Za 1503: drugacija dimenzija? Probamo 16x12, 12x8, 8x12
inj_candidates_ref = [0x02436C, 0x0244EC, 0x022066]

for label, d in dumps_data.items():
    print(f"\n[{label}] Injection na 1630 adresama:")
    for addr in inj_candidates_ref:
        if addr + 384 > len(d):
            print(f"  0x{addr:06X}: OUT OF RANGE")
            continue
        # 16x12 u16 LE
        vals = [struct.unpack_from("<H", d, addr + i*2)[0] for i in range(192)]
        mn, mx = min(vals), max(vals)
        # Provjeri je li to Q15 injection (tipicno 0x2000-0x7FFF)
        q15_count = sum(1 for v in vals if 0x1000 <= v <= 0x7FFF)
        print(f"  0x{addr:06X}: min={hex(mn)} max={hex(mx)} q15_count={q15_count}/192")
        if q15_count > 100:
            # Ispisi prvih 12 vrijednosti
            row0 = [hex(vals[i]) for i in range(12)]
            print(f"    row0: {row0}")

print("\n" + "=" * 70)
print("U16Ax DTC SCAN u cijelom CODE + BOOT regionu")
print("=" * 70)

# Potpuniji scan - trazi D6 A1, D6 A2... itd.
for label, d in dumps_data.items():
    found = []
    for code in range(0xD6A1, 0xD6AC):
        lo = code & 0xFF
        hi = (code >> 8) & 0xFF
        # LE16: lo first
        pat_le = bytes([lo, hi])
        # BE16: hi first
        pat_be = bytes([hi, lo])
        pos = 0
        while True:
            idx = d.find(pat_le, pos, len(d))
            if idx == -1:
                break
            found.append((idx, hex(code), "LE"))
            pos = idx + 1
        pos = 0
        while True:
            idx = d.find(pat_be, pos, len(d))
            if idx == -1:
                break
            found.append((idx, hex(code), "BE"))
            pos = idx + 1
    if found:
        print(f"\n[{label}] U16Ax ({len(found)} hits):")
        for addr, code, enc in found[:10]:
            print(f"  {code} ({enc}) @ 0x{addr:06X}")
    else:
        print(f"\n[{label}] U16Ax: NEMA")

print("\n" + "=" * 70)
print("DIFF DETAIL: 2018v1 vs 2018v2 — koji tocno bajtovi se razlikuju")
print("=" * 70)

da = dumps_data["2018_130v1"]
db = dumps_data["2018_130v2"]
diff_regions = [
    (0x012C00, 0x012D00, "0x012C region"),
    (0x020000, 0x020200, "0x020000 region"),
    (0x024E00, 0x024F00, "0x024E region"),
    (0x026200, 0x026C00, "0x0262-026C region"),
]
for start, end, desc in diff_regions:
    a = da[start:end]
    b = db[start:end]
    if a != b:
        diffs = [(start+i, a[i], b[i]) for i in range(len(a)) if a[i] != b[i]]
        print(f"\n{desc}: {len(diffs)} razlika")
        for addr, va, vb in diffs[:20]:
            print(f"  0x{addr:06X}: {va:02X} -> {vb:02X}")
    else:
        print(f"\n{desc}: IDENTICAN")

print("\nDONE.")
