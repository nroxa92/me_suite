"""
ME17Suite — Checksum Deep Analysis (Round 2)
Fokus: hex analiza BOOT headera, segment table, Adler/Fletcher,
       complement-sum, block @ 0x7E7C, proširene regije.
"""

import struct
import zlib
import sys

ORI_PATH  = "ori_300.bin"
STG2_PATH = "npro_stg2_300.bin"

CS_OFF  = 0x000030
CS_ORI  = 0xE505BC0B
CS_STG2 = 0x9FC76FAD

with open(ORI_PATH,  "rb") as f: ori  = bytearray(f.read())
with open(STG2_PATH, "rb") as f: stg2 = bytearray(f.read())

hits = []

# ─── 1. Hex dump BOOT headera ─────────────────────────────────────────────────
def hexdump(data, offset=0, rows=16):
    for r in range(rows):
        addr = offset + r*16
        if addr >= len(data): break
        chunk = data[addr:addr+16]
        h = " ".join(f"{b:02X}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"  {addr:06X}:  {h:<47}  {a}")

print("=" * 70)
print("BOOT header ORI (0x000-0x080):")
hexdump(ori, 0, 8)
print()
print("BOOT header STG2 (0x000-0x080):")
hexdump(stg2, 0, 8)

print()
print("Block @ 0x7E7C ORI (132B):")
hexdump(ori, 0x7E7C, 9)
print()
print("Block @ 0x7E7C STG2 (132B):")
hexdump(stg2, 0x7E7C, 9)


# ─── 2. Complement-sum analiza ────────────────────────────────────────────────
# Ideja: CS = sum(region) → stored directly OR negated OR XOR s konst.
print("\n" + "=" * 70)
print("COMPLEMENT-SUM analiza:")

def complement_sum_u32_be(data: bytes) -> int:
    """Vrijednost koja doda 0x00000000 na ukupni sum."""
    s = sum(struct.unpack_from(">I", data, i)[0]
            for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF
    return (-s) & 0xFFFFFFFF

def complement_sum_u32_le(data: bytes) -> int:
    s = sum(struct.unpack_from("<I", data, i)[0]
            for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF
    return (-s) & 0xFFFFFFFF

regions_with_cs = {
    "CODE_full":    (0x010000, 0x060000),
    "BOOT_full":    (0x000000, 0x010000),
    "BOOT_CODE":    (0x000000, 0x060000),
    "BOOT_excl_cs": None,  # posebno
}

for label, bounds in regions_with_cs.items():
    if bounds:
        start, end = bounds
        chunk1 = bytes(ori[start:end])
        chunk2 = bytes(stg2[start:end])
    else:
        # BOOT s checksumom izrezanim
        chunk1 = bytes(ori[0:CS_OFF]) + b"\x00\x00\x00\x00" + bytes(ori[CS_OFF+4:0x010000])
        chunk2 = bytes(stg2[0:CS_OFF]) + b"\x00\x00\x00\x00" + bytes(stg2[CS_OFF+4:0x010000])

    # Provjeri: je li sum(region + CS) = 0 ili 0xFFFFFFFF?
    def total_sum_u32_be(data: bytes) -> int:
        return sum(struct.unpack_from(">I", data, i)[0]
                   for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF
    def total_sum_u32_le(data: bytes) -> int:
        return sum(struct.unpack_from("<I", data, i)[0]
                   for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF

    s1_be = total_sum_u32_be(chunk1)
    s1_le = total_sum_u32_le(chunk1)
    print(f"  {label}: sum_u32_be=0x{s1_be:08X}  sum_u32_le=0x{s1_le:08X}")

    neg_be = (-s1_be) & 0xFFFFFFFF
    neg_le = (-s1_le) & 0xFFFFFFFF
    print(f"    complement_be=0x{neg_be:08X}  complement_le=0x{neg_le:08X}")

    if neg_be == CS_ORI:
        s2 = (-total_sum_u32_be(chunk2)) & 0xFFFFFFFF
        if s2 == CS_STG2:
            hits.append(f"[POGODAK!] complement_sum_u32_be / {label}")
        print(f"    *** ORI match complement_be! STG2={s2:08X} (trazimo {CS_STG2:08X})")
    if neg_le == CS_ORI:
        s2 = (-total_sum_u32_le(chunk2)) & 0xFFFFFFFF
        if s2 == CS_STG2:
            hits.append(f"[POGODAK!] complement_sum_u32_le / {label}")
        print(f"    *** ORI match complement_le! STG2={s2:08X} (trazimo {CS_STG2:08X})")


# ─── 3. Adler-32 i Fletcher-32 ────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ADLER-32 / FLETCHER-32:")

def adler32(data: bytes) -> int:
    MOD = 65521
    a, b = 1, 0
    for byte in data:
        a = (a + byte) % MOD
        b = (b + a) % MOD
    return ((b << 16) | a) & 0xFFFFFFFF

def fletcher32(data: bytes) -> int:
    # Fletcher-32: radi s 16-bit blocovima
    d = data + (b"\x00" if len(data) % 2 else b"")
    a, b = 0, 0
    for i in range(0, len(d), 2):
        word = (d[i] << 8) | d[i+1]
        a = (a + word) % 0xFFFF
        b = (b + a) % 0xFFFF
    return ((b << 16) | a) & 0xFFFFFFFF

for label, start, end in [
    ("BOOT_full", 0, 0x10000),
    ("CODE_full", 0x10000, 0x60000),
    ("BOOT_CODE", 0, 0x60000),
]:
    c1 = bytes(ori[start:end])
    c2 = bytes(stg2[start:end])

    for algo_name, fn in [("Adler-32", adler32), ("Fletcher-32", fletcher32)]:
        v1 = fn(c1)
        v2 = fn(c2)
        print(f"  {algo_name}/{label}: ORI=0x{v1:08X} STG2=0x{v2:08X}")
        if v1 == CS_ORI and v2 == CS_STG2:
            hits.append(f"[POGODAK!] {algo_name} / {label}")


# ─── 4. Bosch-specifični: CRC32 s checksum poljem = 0xFFFFFFFF ────────────────
print("\n" + "=" * 70)
print("CRC32 Bosch s checksum poljem = 0xFF / 0x00:")

def make_crc_table_be(poly):
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            crc = ((crc << 1) & 0xFFFFFFFF) ^ poly if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return table

def crc32_be(data: bytes, poly=0x04C11DB7, init=0xFFFFFFFF, xorout=0xFFFFFFFF) -> int:
    table = make_crc_table_be(poly)
    crc = init
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ table[((crc >> 24) ^ b) & 0xFF]
    return (crc ^ xorout) & 0xFFFFFFFF

for fill in [b"\x00\x00\x00\x00", b"\xFF\xFF\xFF\xFF"]:
    fill_hex = fill.hex().upper()
    for label, start, end in [
        ("BOOT_full",    0x0000, 0x10000),
        ("CODE_full",    0x10000, 0x60000),
        ("BOOT_CODE",    0x0000, 0x60000),
    ]:
        d1 = bytearray(ori[start:end])
        d2 = bytearray(stg2[start:end])
        # Zamijeni checksum lokaciju s fill
        cs_in_region = CS_OFF - start
        if 0 <= cs_in_region < len(d1) - 3:
            d1[cs_in_region:cs_in_region+4] = fill
            d2[cs_in_region:cs_in_region+4] = fill

        for init, xorout in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
            v1 = crc32_be(bytes(d1), init=init, xorout=xorout)
            if v1 == CS_ORI:
                v2 = crc32_be(bytes(d2), init=init, xorout=xorout)
                print(f"  *** ORI MATCH: Bosch CRC32 fill={fill_hex} {label} init={init:08X} xorout={xorout:08X}")
                print(f"      ORI=0x{v1:08X} STG2=0x{v2:08X} (trazimo {CS_STG2:08X})")
                if v2 == CS_STG2:
                    hits.append(f"[POGODAK!] Bosch CRC32 fill={fill_hex} {label} init={init:08X} xorout={xorout:08X}")


# ─── 5. Analiza: ima li CS_ORI ikakvog odnosa s podacima? ─────────────────────
print("\n" + "=" * 70)
print("ANALIZA RAZLIKE:")
print(f"  CS_ORI  = 0x{CS_ORI:08X}  = {CS_ORI:,}")
print(f"  CS_STG2 = 0x{CS_STG2:08X}  = {CS_STG2:,}")
print(f"  XOR diff = 0x{CS_ORI ^ CS_STG2:08X}")
print(f"  SUM diff = 0x{(CS_ORI + CS_STG2) & 0xFFFFFFFF:08X}")
print(f"  SUB diff = 0x{(CS_ORI - CS_STG2) & 0xFFFFFFFF:08X}")

# Provjeri: u32 LE vs BE u originalnom fajlu
v_be = struct.unpack_from(">I", ori, CS_OFF)[0]
v_le = struct.unpack_from("<I", ori, CS_OFF)[0]
print(f"\n  @ 0x30 ORI:  BE=0x{v_be:08X}  LE=0x{v_le:08X}")
v_be2 = struct.unpack_from(">I", stg2, CS_OFF)[0]
v_le2 = struct.unpack_from("<I", stg2, CS_OFF)[0]
print(f"  @ 0x30 STG2: BE=0x{v_be2:08X}  LE=0x{v_le2:08X}")

# ─── 6. Pokušaj: u32 LE interpretacija checksuma ──────────────────────────────
CS_ORI_LE  = struct.unpack_from("<I", ori,  CS_OFF)[0]
CS_STG2_LE = struct.unpack_from("<I", stg2, CS_OFF)[0]
print(f"\n  Ako je LE: ORI=0x{CS_ORI_LE:08X}  STG2=0x{CS_STG2_LE:08X}")

# Testiraj LE interpretaciju s istim algoritmima
for label, start, end in [("BOOT_full", 0, 0x10000), ("CODE_full", 0x10000, 0x60000)]:
    c1_z = bytearray(ori[start:end])
    c2_z = bytearray(stg2[start:end])
    cs_in = CS_OFF - start
    if 0 <= cs_in < len(c1_z)-3:
        c1_z[cs_in:cs_in+4] = b"\x00\x00\x00\x00"
        c2_z[cs_in:cs_in+4] = b"\x00\x00\x00\x00"

    # sum_u32_le complement
    def total_le(data):
        return sum(struct.unpack_from("<I", data, i)[0]
                   for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF
    s1 = total_le(bytes(c1_z))
    s2 = total_le(bytes(c2_z))
    neg1 = (-s1) & 0xFFFFFFFF
    neg2 = (-s2) & 0xFFFFFFFF
    print(f"  complement_le_zeroed/{label}: ORI=0x{neg1:08X} STG2=0x{neg2:08X}")
    if neg1 == CS_ORI_LE and neg2 == CS_STG2_LE:
        hits.append(f"[POGODAK! LE] complement_sum_u32_le (LE checksum) / {label}")

# ─── 7. Zlib s initialnim CRC iz prethodnog segmenta (chained) ────────────────
print("\n" + "=" * 70)
print("CHAINED CRC32:")
# Bosch često radi: crc(segment2, init=crc(segment1))
# Probaj: crc(BOOT excl CS, init=0xFFFF) zatim crc(CODE, init=result_from_boot)
for init_val in [0, 0xFFFFFFFF]:
    boot_data = bytes(ori[0:CS_OFF]) + b"\x00\x00\x00\x00" + bytes(ori[CS_OFF+4:0x10000])
    crc_boot = zlib.crc32(boot_data, init_val) & 0xFFFFFFFF
    crc_final = zlib.crc32(bytes(ori[0x10000:0x60000]), crc_boot) & 0xFFFFFFFF
    print(f"  zlib chained(BOOT_z→CODE) init={init_val:08X}: boot_crc=0x{crc_boot:08X} final=0x{crc_final:08X}")
    if crc_final == CS_ORI:
        b2 = bytes(stg2[0:CS_OFF]) + b"\x00\x00\x00\x00" + bytes(stg2[CS_OFF+4:0x10000])
        c2_b = zlib.crc32(b2, init_val) & 0xFFFFFFFF
        c2_f = zlib.crc32(bytes(stg2[0x10000:0x60000]), c2_b) & 0xFFFFFFFF
        print(f"  *** ORI MATCH chained! STG2=0x{c2_f:08X}")
        if c2_f == CS_STG2:
            hits.append(f"[POGODAK!] zlib chained BOOT→CODE init={init_val:08X}")

# Reverse chain: CODE pa BOOT
for init_val in [0, 0xFFFFFFFF]:
    crc_code = zlib.crc32(bytes(ori[0x10000:0x60000]), init_val) & 0xFFFFFFFF
    boot_data = bytes(ori[0:CS_OFF]) + b"\x00\x00\x00\x00" + bytes(ori[CS_OFF+4:0x10000])
    crc_final = zlib.crc32(boot_data, crc_code) & 0xFFFFFFFF
    print(f"  zlib chained(CODE→BOOT_z) init={init_val:08X}: code_crc=0x{crc_code:08X} final=0x{crc_final:08X}")
    if crc_final == CS_ORI:
        c2_c = zlib.crc32(bytes(stg2[0x10000:0x60000]), init_val) & 0xFFFFFFFF
        b2 = bytes(stg2[0:CS_OFF]) + b"\x00\x00\x00\x00" + bytes(stg2[CS_OFF+4:0x10000])
        c2_f = zlib.crc32(b2, c2_c) & 0xFFFFFFFF
        if c2_f == CS_STG2:
            hits.append(f"[POGODAK!] zlib chained CODE→BOOT init={init_val:08X}")


# ─── Finalni rezultati ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"UKUPNO POGODAKA: {len(hits)}")
if hits:
    for h in hits:
        print(f"  {h}")
else:
    print("  Nema pogodaka — algoritam je nestandardan ili region nije standardan.")
    print("  Sljedeci korak: disassembly BOOT koda (TC1762 TriCore ASM)")
print("=" * 70)
