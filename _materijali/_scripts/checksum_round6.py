"""
ME17Suite - Checksum Round 6
Fokus: byte-swap varijante, word-swapped CRC, i analiza gap koda @ 0xFF00

Kljucna hipoteza: TC1762 je LE, pa mozda CRC procesira u32 rijeci
obrnutog byte-reda (svaki 4-bajtni chunk reversed prije CRC-a).
"""

import struct, zlib, hashlib

ORI_PATH  = "ori_300.bin"
STG2_PATH = "npro_stg2_300.bin"
CS_OFF    = 0x000030
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

def check(label, v1, v2):
    if v1 == CS_ORI_BE and v2 == CS_STG2_BE:
        hits.append(f"[POGODAK BE!] {label}")
        print(f"  *** POGODAK BE: {label}")
        return True
    if v1 == CS_ORI_LE and v2 == CS_STG2_LE:
        hits.append(f"[POGODAK LE!] {label}")
        print(f"  *** POGODAK LE: {label}")
        return True
    return False


# ─── Helper: byte-swap varijante ──────────────────────────────────────────────

def swap_u32(data: bytes) -> bytes:
    """Svaki u32 LE chunk reversed: [A B C D] -> [D C B A]"""
    out = bytearray()
    for i in range(0, len(data)-3, 4):
        out.extend(data[i:i+4][::-1])
    if len(data) % 4:
        out.extend(data[-(len(data)%4):])
    return bytes(out)

def swap_u16(data: bytes) -> bytes:
    """Svaki u16 reversed: [A B] -> [B A]"""
    out = bytearray()
    for i in range(0, len(data)-1, 2):
        out.extend(data[i:i+2][::-1])
    if len(data) % 2:
        out.extend(data[-1:])
    return bytes(out)


# ─── Pripremi regije (s nuliranim CS) ─────────────────────────────────────────

def region(data, start, end):
    d = bytearray(data[start:end])
    if start <= CS_OFF < end - 3:
        d[CS_OFF-start:CS_OFF-start+4] = b"\x00\x00\x00\x00"
    return bytes(d)


# ─── 1. Byte-swap CRC ─────────────────────────────────────────────────────────
print("=" * 70)
print("1. Byte-swapped CRC (u32 reversed, u16 reversed):")

regions_list = [
    ("CODE_full",   0x10000, 0x60000),
    ("CODE_CAL",    0x10000, 0x160000),
    ("BOOT_7F00",   0x0000,  0x7F00),
    ("BOOT_CODE",   0x0000,  0x60000),
]

for reg_name, start, end in regions_list:
    r1 = region(ori,  start, end)
    r2 = region(stg2, start, end)
    sw32_1 = swap_u32(r1)
    sw32_2 = swap_u32(r2)
    sw16_1 = swap_u16(r1)
    sw16_2 = swap_u16(r2)

    for algo_name, fn in [("bosch", bosch), ("cstd", cstd)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0)]:
            # Normal
            check(f"CRC_{algo_name}({reg_name}) i={init:08X}", fn(r1,init,xo), fn(r2,init,xo))
            # u32 byte-swapped
            check(f"CRC_{algo_name}({reg_name}_sw32) i={init:08X}", fn(sw32_1,init,xo), fn(sw32_2,init,xo))
            # u16 byte-swapped
            check(f"CRC_{algo_name}({reg_name}_sw16) i={init:08X}", fn(sw16_1,init,xo), fn(sw16_2,init,xo))


# ─── 2. Word-by-word CRC (razni nacini unosa 4B rijeci) ───────────────────────
print("\n" + "=" * 70)
print("2. Word-by-word CRC varijante:")

def crc_word_be(data: bytes, init: int, xo: int) -> int:
    """CRC32 Bosch: procesira 4B u32 BE word-by-word."""
    c = init & 0xFFFFFFFF
    for i in range(0, len(data)-3, 4):
        word = struct.unpack_from(">I", data, i)[0]
        for _ in range(32):
            if (c ^ (word & 0x80000000)) & 0x80000000:
                c = ((c << 1) & 0xFFFFFFFF) ^ 0x04C11DB7
            else:
                c = (c << 1) & 0xFFFFFFFF
            word = (word << 1) & 0xFFFFFFFF
    return (c ^ xo) & 0xFFFFFFFF

def crc_word_le(data: bytes, init: int, xo: int) -> int:
    """CRC32 Bosch: procesira 4B u32 LE word-by-word."""
    c = init & 0xFFFFFFFF
    for i in range(0, len(data)-3, 4):
        word = struct.unpack_from("<I", data, i)[0]
        for _ in range(32):
            if (c ^ (word & 0x80000000)) & 0x80000000:
                c = ((c << 1) & 0xFFFFFFFF) ^ 0x04C11DB7
            else:
                c = (c << 1) & 0xFFFFFFFF
            word = (word << 1) & 0xFFFFFFFF
    return (c ^ xo) & 0xFFFFFFFF

for reg_name, start, end in regions_list:
    r1 = region(ori,  start, end)
    r2 = region(stg2, start, end)
    for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
        v1 = crc_word_be(r1, init, xo)
        v2 = crc_word_be(r2, init, xo)
        check(f"crc_word_BE({reg_name}) i={init:08X} xo={xo:08X}", v1, v2)
        v1 = crc_word_le(r1, init, xo)
        v2 = crc_word_le(r2, init, xo)
        check(f"crc_word_LE({reg_name}) i={init:08X} xo={xo:08X}", v1, v2)


# ─── 3. Analiza gap koda @ 0xFF00-0xFFFF ─────────────────────────────────────
print("\n" + "=" * 70)
print("3. Hex dump gap koda @ 0xFF00-0xFFFF (potencijalni BOOT kod):")

def hexdump(data, offset, rows=16):
    for r in range(rows):
        addr = offset + r*16
        if addr >= len(data): break
        chunk = data[addr:addr+16]
        h = " ".join(f"{b:02X}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"  {addr:06X}:  {h:<47}  {a}")

hexdump(ori, 0xFF00, 16)

# Provjeri je li ORI == STG2 u cijeloj gap regiji
diff_count = sum(1 for a,b in zip(ori[0x7F00:0x10000], stg2[0x7F00:0x10000]) if a!=b)
print(f"\n  Gap 0x7F00-0xFFFF: {diff_count} razlika ORI vs STG2 (ocekujemo 0)")


# ─── 4. Specijalni Bosch ME17 INIT/SEED vrijednosti ───────────────────────────
print("\n" + "=" * 70)
print("4. Specijalni init vrijednosti iz Bosch ME17 dokumentacije:")

# Poznate Bosch init vrijednosti iz KWP2000/seed-key algoritama
special_inits = [
    0xE505BC0B,   # ORI checksum kao init? (samo-referentno)
    0x9FC76FAD,   # STG2 checksum kao init
    0xFADECAFE,
    0xCAFEAFFE,
    0xDEADBEEF,
    0x00000001,
    0x00000080,
    0x80000000,
]

for reg_name, start, end in [("CODE_full", 0x10000, 0x60000)]:
    r1 = region(ori,  start, end)
    r2 = region(stg2, start, end)
    for init in special_inits:
        for xo in [0xFFFFFFFF, 0, init]:
            for algo_name, fn in [("bosch", bosch), ("cstd", cstd)]:
                v1 = fn(r1, init, xo)
                v2 = fn(r2, init, xo)
                check(f"CRC_{algo_name}({reg_name}) i=0x{init:08X} xo=0x{xo:08X}", v1, v2)


# ─── 5. Potpuno drugacije: je li 0x30 = f(SW_ID)? ────────────────────────────
print("\n" + "=" * 70)
print("5. Je li CS deriviran iz SW ID-a?")

# SW IDs
sw_ori  = b"10SW066726"
sw_stg2 = b"10SW040039"
# Proba svih jednostavnih transformacija
for sw, cs_target in [(sw_ori, CS_ORI_BE), (sw_stg2, CS_STG2_BE)]:
    for algo_name, fn in [("bosch", bosch), ("cstd", cstd)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0)]:
            v = fn(sw, init, xo)
            if v == cs_target:
                print(f"  SW_ID match: {algo_name}('{sw.decode()}') i={init:08X} = 0x{v:08X}")

# Suma ASCII vrijednosti
s = sum(sw_ori) & 0xFFFFFFFF
print(f"  sum_ascii(ORI SW_ID)  = 0x{s:08X} (trazimo 0x{CS_ORI_BE:08X})")
s2 = sum(sw_stg2) & 0xFFFFFFFF
print(f"  sum_ascii(STG2 SW_ID) = 0x{s2:08X} (trazimo 0x{CS_STG2_BE:08X})")


# ─── 6. Rekurzivna CRC (CRC CRC-a) ───────────────────────────────────────────
print("\n" + "=" * 70)
print("6. CRC svake CODE rijeci zasebno (rolling CRC tablice):")

# Alternativa: Bosch ponekad radi sum-of-crcs po chunk-ovima
def sum_of_crc_chunks(data, chunk_size=4):
    """Suma CRC32 za svaki chunk posebno."""
    total = 0
    for i in range(0, len(data)-chunk_size+1, chunk_size):
        chunk = data[i:i+chunk_size]
        total ^= bosch(chunk)
    return total & 0xFFFFFFFF

for reg_name, start, end in [("CODE_full", 0x10000, 0x60000)]:
    r1 = region(ori,  start, end)
    r2 = region(stg2, start, end)
    v1 = sum_of_crc_chunks(r1, 4)
    v2 = sum_of_crc_chunks(r2, 4)
    check(f"sum_of_crc_u32({reg_name})", v1, v2)
    v1 = sum_of_crc_chunks(r1, 2)
    v2 = sum_of_crc_chunks(r2, 2)
    check(f"sum_of_crc_u16({reg_name})", v1, v2)


# ─── Finalni zakljucak ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"UKUPNO POGODAKA: {len(hits)}")
for h in hits:
    print(f"  {h}")
if not hits:
    print("  0 pogodaka.")
    print()
    print("  ZAKLJUCAK ISTRAGE:")
    print("  Nijedan standardni nor nestandardni CRC/suma algoritam ne")
    print("  generira vrijednost na 0x30.")
    print()
    print("  Moguce objasnjenje:")
    print("  A) Kriptografski potpis (RSA/ECDSA) - ne mozemo replicirat")
    print("  B) Proprietary Bosch algoritam u BOOT kodu (treba disassembly)")
    print("  C) Vrijednost na 0x30 nije integrity checksum vec nesto drugo")
    print("     (npr. security seed, verzijska konstanta)")
    print()
    print("  Prakticni zakljucak:")
    print("  Ako ECU prihvata fajlove bez ispravnog checksuma,")
    print("  mozemo privremeno preskociti i fokusirati se na tuning.")
    print("  Trajno rjesenje: disassembly BOOT koda s IDA/Ghidra + TriCore plugin.")
print("=" * 70)
