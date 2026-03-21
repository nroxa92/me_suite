#!/usr/bin/env python3
"""Detaljan dump CAN TX tablice @ 0x03DF0C"""
import struct, os

BASE = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali\dumps"
DUMPS = [
    (r"2018\1630ace\300.bin", "2018_300", 0x03DF1E),
    (r"2019\1630ace\300.bin", "2019_300", 0x03DF0C),
    (r"2020\1630ace\300.bin", "2020_300", 0x03DF0C),
    (r"2020\1630ace\230.bin", "2020_230", 0x03DF0C),
    (r"2021\1630ace\300.bin", "2021_300", 0x03DF0C),
    (r"2021\1630ace\230.bin", "2021_230", 0x03DF0C),
]

KNOWN_CAN_IDS = {
    0x0578: "cluster primary (267ms)",
    0x0400: "cluster secondary (311ms)",
    0x0102: "diag TX",
    0x0103: "diag TX",
    0x0110: "diag TX",
    0x0122: "diag TX",
    0x0300: "diag TX",
    0x0308: "diag TX",
}

def load(rel):
    with open(os.path.join(BASE, rel), "rb") as f:
        return f.read()

print("=" * 70)
print("CAN TX TABLE DETAIL @ 0x03DF0C")
print("=" * 70)

for rel, label, addr in DUMPS:
    d = load(rel)
    print(f"\n[{label}] @ 0x{addr:06X} (256 bytes):")
    block = d[addr:addr+256]
    print(f"  Hex: {block[:32].hex(' ')}")
    print(f"       {block[32:64].hex(' ')}")
    print(f"       {block[64:96].hex(' ')}")
    print(f"       {block[96:128].hex(' ')}")

    # Trazi LE16 CAN IDs u bloku
    print(f"  CAN-like LE16 values (0x0100-0x07FF):")
    for i in range(0, min(256, len(block)-1), 2):
        v = struct.unpack_from("<H", block, i)[0]
        if 0x0100 <= v <= 0x07FF:
            note = KNOWN_CAN_IDS.get(v, "")
            print(f"    +0x{i:02X}: {hex(v)}  {note}")

    # Kontekstualni: pokazi sve u +/-16B od pronalaska 0x0578
    idx_578 = block.find(bytes([0x78, 0x05]))
    if idx_578 >= 0:
        print(f"  0x0578 pronaden @ +0x{idx_578:02X}, kontekst +-8B:")
        start = max(0, idx_578-8)
        end = min(len(block), idx_578+10)
        ctx = block[start:end]
        print(f"    {ctx.hex(' ')}")

# Usporedi 2018 i 2021 raw
print("\n\n" + "=" * 70)
print("Usporedba 2018 (0x03DF1E) vs 2021 (0x03DF0C) — 64 bytes")
print("=" * 70)
d18 = load(r"2018\1630ace\300.bin")
d21 = load(r"2021\1630ace\300.bin")
b18 = d18[0x03DF1E:0x03DF1E+64]
b21 = d21[0x03DF0C:0x03DF0C+64]
print(f"2018: {b18[:32].hex(' ')}")
print(f"2021: {b21[:32].hex(' ')}")
diffs = [(i, b18[i], b21[i]) for i in range(min(len(b18),len(b21))) if b18[i] != b21[i]]
print(f"Razlike: {len(diffs)}")
for off, va, vb in diffs[:20]:
    print(f"  +0x{off:02X}: 2018={va:02X} 2021={vb:02X}")

# Trazi sto je iznad 0x03DF0C - moze biti pocetna adresa tablice
print("\n\n" + "=" * 70)
print("Trazim pocetnu adresu CAN tablice (scan unazad od 0x03DF0C)")
print("=" * 70)
d = load(r"2021\1630ace\300.bin")
# Trazi niz koji pocinje s validnim CAN IDs (0x0100-0x07FF LE16)
for base in range(0x03DF0C, 0x03DC00, -2):
    v = struct.unpack_from("<H", d, base)[0]
    if not (0x0080 <= v <= 0x0FFF):
        # Nije CAN-like vrijednost
        prev = struct.unpack_from("<H", d, base+2)[0]
        if 0x0080 <= prev <= 0x0FFF:
            print(f"Moguca pocetak tablice @ 0x{base+2:06X}")
            # Ispisi 32B od te adrese
            blk = d[base+2:base+2+64]
            print(f"  {blk[:32].hex(' ')}")
        break

print("\nDONE.")
