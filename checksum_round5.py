"""
ME17Suite - Checksum Round 5
Kljucni nalaz: BOOT = 0x0000-0x7EFF (ne 0xFFFF!)
  - 0x38: STADD = 0x80000000 -> file 0x0000
  - 0x3C: ENDADD = 0x80007EFF -> file 0x7EFF
  - Signature blok @ 0x7E7C je unutar BOOT-a
  - Sto je u prostoru 0x7F00-0xFFFF?

Novi testovi:
  - CRC nad tocnim BOOT (0x0000-0x7EFF)
  - Hashlib: MD5, SHA1, SHA256 nad CODE/BOOT
  - Analiza 0x7F00-0xFFFF gap regije
  - Pokusaj s veeelikim brojem specificnih regija
"""

import struct
import zlib
import hashlib

ORI_PATH  = "ori_300.bin"
STG2_PATH = "npro_stg2_300.bin"

CS_OFF  = 0x000030
CS_ORI_BE  = 0xE505BC0B
CS_STG2_BE = 0x9FC76FAD
CS_ORI_LE  = 0x0BBC05E5
CS_STG2_LE = 0xAD6FC79F

with open(ORI_PATH,  "rb") as f: ori  = bytearray(f.read())
with open(STG2_PATH, "rb") as f: stg2 = bytearray(f.read())

hits = []

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

def crc_calc(data, tbl, init, xorout, refin):
    c = init & 0xFFFFFFFF
    if refin:
        for b in data:
            c = (c >> 8) ^ tbl[(c ^ b) & 0xFF]
    else:
        for b in data:
            c = ((c << 8) & 0xFFFFFFFF) ^ tbl[((c >> 24) ^ b) & 0xFF]
    return (c ^ xorout) & 0xFFFFFFFF

TBL_BOSCH = make_tbl(0x04C11DB7, False)
TBL_ZLIB  = make_tbl(0xEDB88320, True)

def bosch(data, init=0xFFFFFFFF, xo=0xFFFFFFFF):
    return crc_calc(data, TBL_BOSCH, init, xo, False)

def cstd(data, init=0xFFFFFFFF, xo=0xFFFFFFFF):
    return crc_calc(data, TBL_ZLIB, init, xo, True)

def check(label, v1, v2, suppress=False):
    if v1 == CS_ORI_BE and v2 == CS_STG2_BE:
        hits.append(f"[POGODAK BE!] {label}")
        print(f"  *** POGODAK BE: {label}")
        return True
    if v1 == CS_ORI_LE and v2 == CS_STG2_LE:
        hits.append(f"[POGODAK LE!] {label}")
        print(f"  *** POGODAK LE: {label}")
        return True
    return False


# ─── 1. Analiza gap regije 0x7F00-0xFFFF ─────────────────────────────────────
print("=" * 70)
print("1. Analiza gap regije 0x7F00-0xFFFF:")

gap_ori  = bytes(ori[0x7F00:0x10000])
gap_stg2 = bytes(stg2[0x7F00:0x10000])
unique_vals = set(gap_ori)
print(f"   Velicina gap-a: {len(gap_ori):,} B (0x{len(gap_ori):X})")
print(f"   ORI  unique bajtovi: {sorted(unique_vals)[:16]} ...")
print(f"   Razlika ORI vs STG2: {sum(1 for a,b in zip(gap_ori,gap_stg2) if a!=b)} B")
print(f"   ORI [0x7F00:0x7F10]: {gap_ori[:16].hex().upper()}")
print(f"   ORI [0xFF00:0xFF10]: {bytes(ori[0xFF00:0xFF10]).hex().upper()}")
print(f"   ORI [0xFFF0:0x10000]: {bytes(ori[0xFFF0:0x10000]).hex().upper()}")


# ─── 2. CRC nad tocnim BOOT (0x0000-0x7EFF) ──────────────────────────────────
print("\n" + "=" * 70)
print("2. CRC nad tocnim BOOT (0x0000-0x7EFF, 0x7F00 B):")

for fill in [b"\x00\x00\x00\x00", b"\xFF\xFF\xFF\xFF"]:
    d1 = bytearray(ori[0x0000:0x7F00])
    d2 = bytearray(stg2[0x0000:0x7F00])
    # Zamijeni CS lokaciju s fill
    d1[0x30:0x34] = fill
    d2[0x30:0x34] = fill
    fill_s = fill.hex().upper()

    for algo_name, fn in [("bosch", bosch), ("cstd", cstd)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
            v1 = fn(bytes(d1), init, xo)
            v2 = fn(bytes(d2), init, xo)
            check(f"CRC_{algo_name}(BOOT_0x7F00, fill={fill_s}) i={init:08X} xo={xo:08X}", v1, v2)

# BOOT bez signature bloka (0x0000-0x7E7C bez 0x7E7C-0x7F00)
for fill in [b"\x00\x00\x00\x00"]:
    d1 = bytearray(ori[0x0000:0x7E7C])
    d2 = bytearray(stg2[0x0000:0x7E7C])
    d1[0x30:0x34] = fill
    d2[0x30:0x34] = fill
    for algo_name, fn in [("bosch", bosch), ("cstd", cstd)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0)]:
            v1 = fn(bytes(d1), init, xo)
            v2 = fn(bytes(d2), init, xo)
            check(f"CRC_{algo_name}(BOOT_bez_sig_0x7E7C) i={init:08X}", v1, v2)

# BOOT samo do FADEFACE markera (0x0000-0x0040)
d1 = bytearray(ori[0x0000:0x0040])
d2 = bytearray(stg2[0x0000:0x0040])
d1[0x30:0x34] = b"\x00\x00\x00\x00"
d2[0x30:0x34] = b"\x00\x00\x00\x00"
for fn, name in [(bosch, "bosch"), (cstd, "cstd")]:
    v1 = fn(bytes(d1))
    v2 = fn(bytes(d2))
    check(f"CRC_{name}(hdr_0x40_zeroed)", v1, v2)


# ─── 3. Hashlib algoritmi (truncated) ─────────────────────────────────────────
print("\n" + "=" * 70)
print("3. Hash algoritmi (truncated na 4B):")

regions = {
    "BOOT_7F00":   (0x0000, 0x7F00),
    "BOOT_7E7C":   (0x0000, 0x7E7C),
    "CODE_full":   (0x10000, 0x60000),
    "CODE_CAL":    (0x10000, 0x160000),
    "BOOT_CODE":   (0x0000, 0x60000),
}

for reg_name, (start, end) in regions.items():
    d1 = bytearray(ori[start:end])
    d2 = bytearray(stg2[start:end])
    # Nuliranje CS ako je unutar regije
    if start <= CS_OFF < end - 3:
        d1[CS_OFF-start:CS_OFF-start+4] = b"\x00\x00\x00\x00"
        d2[CS_OFF-start:CS_OFF-start+4] = b"\x00\x00\x00\x00"

    for algo in ["md5", "sha1", "sha256"]:
        h1 = hashlib.new(algo, bytes(d1)).digest()
        h2 = hashlib.new(algo, bytes(d2)).digest()
        # Probaj prvih 4 bajta (BE i LE)
        for offset in range(0, min(len(h1), 32) - 3, 1):
            v1_be = struct.unpack_from(">I", h1, offset)[0]
            v1_le = struct.unpack_from("<I", h1, offset)[0]
            v2_be = struct.unpack_from(">I", h2, offset)[0]
            v2_le = struct.unpack_from("<I", h2, offset)[0]
            if v1_be == CS_ORI_BE and v2_be == CS_STG2_BE:
                hits.append(f"[POGODAK!] {algo}[{offset}:+4]_BE / {reg_name}")
                print(f"  *** POGODAK: {algo}[{offset}:+4] BE / {reg_name}")
            if v1_le == CS_ORI_BE and v2_le == CS_STG2_BE:
                hits.append(f"[POGODAK!] {algo}[{offset}:+4]_LE->BE / {reg_name}")
                print(f"  *** POGODAK: {algo}[{offset}:+4] LE->BE / {reg_name}")

    print(f"  {reg_name}:")
    for algo in ["md5", "sha1"]:
        h1 = hashlib.new(algo, bytes(d1)).hexdigest()
        print(f"    ORI  {algo}: {h1[:16]}...")


# ─── 4. Sume s tocnim BOOT granicama ─────────────────────────────────────────
print("\n" + "=" * 70)
print("4. Additive sume s tocnim granicama:")

from itertools import product

for start, end in [
    (0x0000, 0x7F00),   # tocni BOOT
    (0x0040, 0x7F00),   # BOOT bez headera
    (0x0040, 0x7E7C),   # BOOT bez headera i bez sig bloka
    (0x00C0, 0x7F00),   # BOOT od STAD
    (0x00C0, 0x7E7C),   # BOOT od STAD bez sig
    (0x0000, 0x7F00+0x10000),  # BOOT + CODE (s pravim BOOT krajem)
]:
    d1 = bytearray(ori[start:end])
    d2 = bytearray(stg2[start:end])
    if start <= CS_OFF < end:
        d1[CS_OFF-start:CS_OFF-start+4] = b"\x00\x00\x00\x00"
        d2[CS_OFF-start:CS_OFF-start+4] = b"\x00\x00\x00\x00"

    for word_size, endian in product([4], ['>', '<']):
        fmt = f"{endian}I"
        s1 = sum(struct.unpack_from(fmt, d1, i)[0] for i in range(0, len(d1)-3, 4)) & 0xFFFFFFFF
        s2 = sum(struct.unpack_from(fmt, d2, i)[0] for i in range(0, len(d2)-3, 4)) & 0xFFFFFFFF
        neg1 = (-s1) & 0xFFFFFFFF
        neg2 = (-s2) & 0xFFFFFFFF
        endian_s = "BE" if endian == ">" else "LE"
        check(f"sum_u32_{endian_s}(0x{start:05X}..0x{end:05X}) zeroed", s1, s2)
        check(f"~sum_u32_{endian_s}(0x{start:05X}..0x{end:05X}) zeroed", neg1, neg2)

    # 2-bajtne sume
    for endian in ['>', '<']:
        fmt = f"{endian}H"
        endian_s = "BE" if endian == ">" else "LE"
        s1 = sum(struct.unpack_from(fmt, d1, i)[0] for i in range(0, len(d1)-1, 2)) & 0xFFFFFFFF
        s2 = sum(struct.unpack_from(fmt, d2, i)[0] for i in range(0, len(d2)-1, 2)) & 0xFFFFFFFF
        neg1 = (-s1) & 0xFFFFFFFF
        neg2 = (-s2) & 0xFFFFFFFF
        check(f"sum_u16_{endian_s}(0x{start:05X}..0x{end:05X})", s1, s2)
        check(f"~sum_u16_{endian_s}(0x{start:05X}..0x{end:05X})", neg1, neg2)


# ─── 5. Hex dump oko 0x7E70 da vidimo sto je tocno na 0x7E74 ─────────────────
print("\n" + "=" * 70)
print("5. Hex dump 0x7E60-0x7F10:")

def hexdump(data, base_offset, rows=8):
    for r in range(rows):
        addr = base_offset + r*16
        if addr >= len(data): break
        chunk = data[addr:addr+16]
        h = " ".join(f"{b:02X}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"  {addr:06X}:  {h:<47}  {a}")

print("ORI:")
hexdump(ori, 0x7E60, 5)
print()
print("STG2:")
hexdump(stg2, 0x7E60, 5)


# ─── Finalno ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"UKUPNO POGODAKA: {len(hits)}")
for h in hits:
    print(f"  {h}")
if not hits:
    print("  Nema pogodaka.")
    print()
    print("  SLJEDECI KORAK: TriCore disassembly BOOT koda (0x50-0x7E7C)")
    print("  ili analiza flasher alata (KTAG/Flex protokol capture)")
print("=" * 70)
