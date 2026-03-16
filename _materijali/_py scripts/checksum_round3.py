"""
ME17Suite - Checksum Round 3
Novi pristup na osnovu hex analize:
  - 0x40: FADEFACE/CAFEFAFE magic (Bosch segment descriptor)
  - 0x7E7C: 128B blok + DEADBEEF = vjerovatno RSA/hash potpis
  - Pitanje: sto tocno pokriva checksum @ 0x30?
"""

import struct
import zlib
import sys

ORI_PATH  = "ori_300.bin"
STG2_PATH = "npro_stg2_300.bin"

CS_OFF  = 0x000030
CS_ORI_BE  = 0xE505BC0B
CS_STG2_BE = 0x9FC76FAD
CS_ORI_LE  = 0x0BBC05E5   # ako je LE
CS_STG2_LE = 0xAD6FC79F

with open(ORI_PATH,  "rb") as f: ori  = bytearray(f.read())
with open(STG2_PATH, "rb") as f: stg2 = bytearray(f.read())

hits = []

def check(label, v1, v2):
    """Provjeri obje interpretacije (BE i LE)."""
    if v1 == CS_ORI_BE and v2 == CS_STG2_BE:
        hits.append(f"[POGODAK BE!] {label} ORI=0x{v1:08X} STG2=0x{v2:08X}")
        print(f"  *** BE POGODAK: {label}")
    if v1 == CS_ORI_LE and v2 == CS_STG2_LE:
        hits.append(f"[POGODAK LE!] {label} ORI=0x{v1:08X} STG2=0x{v2:08X}")
        print(f"  *** LE POGODAK: {label}")


# ─── CRC32 helper ─────────────────────────────────────────────────────────────

def make_tbl(poly, refin):
    t = []
    for i in range(256):
        if refin:
            c = i
            for _ in range(8):
                c = (c >> 1) ^ (poly if c & 1 else 0)
        else:
            c = i << 24
            for _ in range(8):
                c = ((c << 1) ^ poly if c & 0x80000000 else c << 1) & 0xFFFFFFFF
        t.append(c & 0xFFFFFFFF)
    return t

def crc(data, tbl, init, xorout, refin):
    c = init & 0xFFFFFFFF
    if refin:
        for b in data:
            c = (c >> 8) ^ tbl[(c ^ b) & 0xFF]
    else:
        for b in data:
            c = ((c << 8) & 0xFFFFFFFF) ^ tbl[((c >> 24) ^ b) & 0xFF]
    return (c ^ xorout) & 0xFFFFFFFF

# Pripremi tablice
TBL_BOSCH = make_tbl(0x04C11DB7, False)
TBL_ZLIB  = make_tbl(0xEDB88320, True)

def crc32_bosch(data, init=0xFFFFFFFF, xorout=0xFFFFFFFF):
    return crc(data, TBL_BOSCH, init, xorout, False)

def crc32_std(data, init=0xFFFFFFFF, xorout=0xFFFFFFFF):
    return crc(data, TBL_ZLIB, init, xorout, True)


# ─── 1. Checksum pokriva 0x7E7C blok? ────────────────────────────────────────
print("=" * 70)
print("TEST 1: CS @ 0x30 pokriva blok @ 0x7E7C?")

for end in [0x7EF8, 0x7EFC, 0x7F00, 0x7F04, 0x8000]:
    for start in [0x7E7C, 0x7E80, 0x0040]:
        chunk1 = bytes(ori[start:end])
        chunk2 = bytes(stg2[start:end])
        for name, fn in [("crc32_bosch", crc32_bosch), ("crc32_std", crc32_std)]:
            for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
                v1 = fn(chunk1, init, xo)
                v2 = fn(chunk2, init, xo)
                check(f"{name}(0x{start:05X}-0x{end:05X}) init={init:08X} xo={xo:08X}", v1, v2)
        # suma
        s1 = sum(struct.unpack_from(">I", chunk1, i)[0] for i in range(0, len(chunk1)-3, 4)) & 0xFFFFFFFF
        s2 = sum(struct.unpack_from(">I", chunk2, i)[0] for i in range(0, len(chunk2)-3, 4)) & 0xFFFFFFFF
        check(f"sum_u32_be(0x{start:05X}-0x{end:05X})", s1, s2)
        s1l = sum(struct.unpack_from("<I", chunk1, i)[0] for i in range(0, len(chunk1)-3, 4)) & 0xFFFFFFFF
        s2l = sum(struct.unpack_from("<I", chunk2, i)[0] for i in range(0, len(chunk2)-3, 4)) & 0xFFFFFFFF
        check(f"sum_u32_le(0x{start:05X}-0x{end:05X})", s1l, s2l)


# ─── 2. Header descriptor analiza (Bosch segment table) ──────────────────────
print("\n" + "=" * 70)
print("TEST 2: Bosch segment descriptor @ 0x40 (FADEFACE/CAFEFAFE)")

# Parsiraj adrese iz headera
print("\nHeader adrese (LE):")
for off in range(0x30, 0x60, 4):
    v = struct.unpack_from("<I", ori, off)[0]
    print(f"  0x{off:04X}: 0x{v:08X}  ({v:,})")

# Pretpostavi: TC1762 PFLASH baza = 0x80000000
# File offset = TC1762_addr - 0x80000000
# Provjeri koje adrese daju smislene file offset-e
print("\nAdrese kao TC1762 file offset-i (base=0x80000000):")
for off in range(0x30, 0x80, 4):
    v = struct.unpack_from("<I", ori, off)[0]
    if 0x80000000 <= v < 0x80200000:
        file_off = v - 0x80000000
        print(f"  0x{off:04X}: TC=0x{v:08X} -> file=0x{file_off:06X}")


# ─── 3. Prosireniji raspon CODE regije ────────────────────────────────────────
print("\n" + "=" * 70)
print("TEST 3: Prosireni CODE raspon")

# Mozda CODE nije 0x010000-0x05FFFF, nego nesto drugo
test_ranges = [
    (0x010000, 0x04FFFF),   # manji CODE
    (0x010000, 0x07FFFF),   # veci CODE
    (0x010000, 0x0FFFFF),   # jos veci
    (0x010000, 0x160000),   # CODE + CAL
    (0x000040, 0x010000),   # BOOT bez headera
    (0x000040, 0x060000),   # BOOT (bez headera) + CODE
    (0x000040, 0x160000),   # sve bez headera
    (0x000100, 0x060000),   # BOOT bez prvih 256B + CODE
    (0x000080, 0x060000),   # BOOT bez prvih 128B + CODE
    (0x000034, 0x010000),   # BOOT od 0x34 (preskoci CS)
    (0x000034, 0x060000),   # BOOT od 0x34 + CODE
    (0x007E7C, 0x160000),   # od 0x7E7C do kraja
]

for start, end in test_ranges:
    chunk1 = bytes(ori[start:end+1])
    chunk2 = bytes(stg2[start:end+1])
    for name, fn in [("bosch", crc32_bosch), ("std", crc32_std)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0)]:
            v1 = fn(chunk1, init, xo)
            v2 = fn(chunk2, init, xo)
            check(f"crc32_{name}(0x{start:06X}-0x{end:06X}) i={init:08X}", v1, v2)


# ─── 4. Checksum je mozda samo sume SW ID polja? ──────────────────────────────
print("\n" + "=" * 70)
print("TEST 4: Checksum SW ID / malih regija")

small_regions = [
    ("SW_ID_bytes",  0x001A, 0x0024),   # SW ID bytes
    ("hdr_0_to_30",  0x0000, 0x0030),   # header do checksuma
    ("hdr_34_to_40", 0x0034, 0x0040),   # header iza checksuma
    ("hdr_0_to_40_z", None, None),      # header s CS = 0
    ("hdr_10_to_30", 0x0010, 0x0030),
    ("hdr_0_to_30_and_34_to_80", None, None),   # posebno
]

# 0x0 do 0x30, CS nuliran, nastavak 0x34-0x80
d1_z = bytearray(ori[:0x80])
d2_z = bytearray(stg2[:0x80])
d1_z[0x30:0x34] = b"\x00\x00\x00\x00"
d2_z[0x30:0x34] = b"\x00\x00\x00\x00"

for name, fn in [("bosch", crc32_bosch), ("std", crc32_std)]:
    for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
        v1 = fn(bytes(d1_z), init, xo)
        v2 = fn(bytes(d2_z), init, xo)
        check(f"crc32_{name}(hdr_0x80_zeroed_cs) i={init:08X} xo={xo:08X}", v1, v2)

for start, end in [(0x001A, 0x0024), (0x0000, 0x0030), (0x0034, 0x0040), (0x0010, 0x0030)]:
    c1 = bytes(ori[start:end])
    c2 = bytes(stg2[start:end])
    for name, fn in [("bosch", crc32_bosch), ("std", crc32_std)]:
        v1 = fn(c1, 0xFFFFFFFF, 0xFFFFFFFF)
        v2 = fn(c2, 0xFFFFFFFF, 0xFFFFFFFF)
        check(f"crc32_{name}(0x{start:04X}-0x{end:04X})", v1, v2)


# ─── 5. Kombinacija: CRC(header + CODE) razliciti nacini ─────────────────────
print("\n" + "=" * 70)
print("TEST 5: Header (zeroed CS) + CODE, chained CRC")

for init in [0, 0xFFFFFFFF]:
    for xo in [0, 0xFFFFFFFF]:
        # Chained: header pa CODE
        hdr_z = bytes(d1_z)  # 0x80 bajtova, CS nuliran
        code1 = bytes(ori[0x10000:0x60000])
        c_hdr = crc(hdr_z, TBL_BOSCH, init, 0, False)
        c_fin = crc(code1, TBL_BOSCH, c_hdr, xo, False)
        check(f"chained_bosch(hdr80_z->CODE) i={init:08X} xo={xo:08X}", c_fin,
              crc(bytes(stg2[0x10000:0x60000]), TBL_BOSCH,
                  crc(bytes(d2_z), TBL_BOSCH, init, 0, False), xo, False))

        # zlib chained
        c_hdr_z = zlib.crc32(bytes(d1_z), init) & 0xFFFFFFFF
        c_fin_z = zlib.crc32(code1, c_hdr_z) ^ xo & 0xFFFFFFFF
        c_hdr_z2 = zlib.crc32(bytes(d2_z), init) & 0xFFFFFFFF
        c_fin_z2 = zlib.crc32(bytes(stg2[0x10000:0x60000]), c_hdr_z2) ^ xo & 0xFFFFFFFF
        check(f"chained_zlib(hdr80_z->CODE) i={init:08X} xo={xo:08X}", c_fin_z, c_fin_z2)


# ─── 6. Sazeti ispis "blize" vrijednosti ─────────────────────────────────────
print("\n" + "=" * 70)
print("INFO: Referentne vrijednosti za debug")
print(f"  Ciljamo BE: ORI=0x{CS_ORI_BE:08X}  STG2=0x{CS_STG2_BE:08X}")
print(f"  Ciljamo LE: ORI=0x{CS_ORI_LE:08X}  STG2=0x{CS_STG2_LE:08X}")

# Ispiši CRC32 standardnih regija za referencu
for label, chunk in [
    ("BOOT[0:0x7E7C]",  ori[0:0x7E7C]),
    ("BOOT[0x40:0x7E7C]", ori[0x40:0x7E7C]),
    ("BOOT[0:0x7F00]",  ori[0:0x7F00]),
]:
    v_b = crc32_bosch(bytes(chunk))
    v_s = crc32_std(bytes(chunk))
    print(f"  bosch({label}) = 0x{v_b:08X}")
    print(f"  std  ({label}) = 0x{v_s:08X}")


# ─── Finalno ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"UKUPNO POGODAKA: {len(hits)}")
for h in hits:
    print(f"  {h}")
if not hits:
    print("  Nema pogodaka.")
    print("  ZAKLJUCAK: Algoritam je vjerojatno kriptografski (RSA/ECDSA)")
    print("  ili pokriven regijom koja nije standardna.")
    print("  Sljedeci korak: TriCore disassembly BOOT koda!")
print("=" * 70)
