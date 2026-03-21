"""
ME17Suite - Checksum Round 4
Fokus: TC1762 Boot Mode Header (BMHD) struktura verificacija
  BMHD0 @ 0x00:
    STAD    @ 0x00 = LE: 0x000000C0
    ENDADD  @ 0x04 = LE: 0x00007F04
    CRCRANGE@ 0x08 = LE: 0x80020000  <- provjeri!
    CRCBMHD @ 0x0C = LE: 0x80007F00  <- provjeri!
  Checksum @ 0x30: pripada drugom BMHD ili drugoj provjeri
"""

import struct
import zlib

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

def std(data, init=0xFFFFFFFF, xo=0xFFFFFFFF):
    return crc_calc(data, TBL_ZLIB, init, xo, True)


def check_both(label, v1, v2):
    if v1 == CS_ORI_BE and v2 == CS_STG2_BE:
        hits.append(f"[POGODAK BE!] {label}")
        print(f"  *** POGODAK BE: {label}")
    if v1 == CS_ORI_LE and v2 == CS_STG2_LE:
        hits.append(f"[POGODAK LE!] {label}")
        print(f"  *** POGODAK LE: {label}")


# ─── 1. Verificiraj BMHD0 strukturu ──────────────────────────────────────────
print("=" * 70)
print("BMHD0 verificacija (da li razumijemo header format):")

# BMHD0: STAD=0xC0, ENDADD=0x7F04
# CRCRANGE @ 0x08 = 0x80020000 (LE) - treba biti CRC od [STAD..ENDADD]
# Pokusavamo razne interpretacije ENDADD
STAD = 0x000000C0
for endadd in [0x00007F04, 0x00007F03, 0x00007F05, 0x00007EFF, 0x00007F00]:
    chunk = bytes(ori[STAD:endadd+1])
    for algo_name, fn in [("bosch", bosch), ("std", std)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
            v = fn(chunk, init, xo)
            if v == 0x80020000:
                print(f"  BMHD0 CRCRANGE MATCH: {algo_name}(0x{STAD:X}..0x{endadd:X}) init={init:08X} xo={xo:08X} = 0x{v:08X}")
            # Ako ne matchira direktno, probaj LE: 0x00000280
            if v == 0x00000280:
                print(f"  BMHD0 LE match: {algo_name}(0x{STAD:X}..0x{endadd:X}) = 0x{v:08X}")

# CRCBMHD @ 0x0C = 0x80007F00 (LE) - treba biti CRC od BMHD[0:12]
bmhd_bytes = bytes(ori[0x00:0x0C])
print(f"\n  BMHD0 bytes [0:12]: {bmhd_bytes.hex().upper()}")
for algo_name, fn in [("bosch", bosch), ("std", std)]:
    for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
        v = fn(bmhd_bytes, init, xo)
        if v == 0x80007F00:
            print(f"  BMHD0 CRCBMHD MATCH: {algo_name} init={init:08X} xo={xo:08X} = 0x{v:08X}")
        if v == 0x00007F80:  # LE interpretacija
            print(f"  BMHD0 CRCBMHD LE match: {algo_name} = 0x{v:08X}")

# Pokusaj inverznu - mozda je CRCBMHD inverzija CRC-a
for algo_name, fn in [("bosch", bosch), ("std", std)]:
    v = fn(bmhd_bytes)
    inv_v = (~v) & 0xFFFFFFFF
    print(f"  ~CRC_BMHD0({algo_name}) = 0x{inv_v:08X} (CRCBMHD treba biti 0x80007F00)")


# ─── 2. BMHD1 ili drugi descriptor koji ima CS @ 0x30 ─────────────────────────
print("\n" + "=" * 70)
print("Trazenje BMHD koji pokriva CS @ 0x30:")
print("Header oko 0x28-0x3F:")
for off in range(0x20, 0x44, 4):
    v_le = struct.unpack_from("<I", ori, off)[0]
    v_be = struct.unpack_from(">I", ori, off)[0]
    print(f"  0x{off:04X}: LE=0x{v_le:08X}  BE=0x{v_be:08X}")

# Ako je drugi BMHD na 0x10:
# BMHD1: STAD @ 0x10=0, ENDADD @ 0x14=0, CRCRANGE @ 0x18=0, CRCBMHD @ 0x1C=0
# sve nule - nema smisla

# Pokusaj: BMHD na 0x28
# STAD @ 0x28 = AF AF AF AF = 0xAFAFAFAF (nevalidna adresa, preskoci)
# Pokusaj: BMHD na 0x2C
# STAD @ 0x2C = 01 00 00 00 = LE: 0x00000001 = file 0x01?
# ENDADD @ 0x30 = CS = LE: 0x0BBC05E5 -- NE, to je checksum
# Pokusaj drugacije: STAD @ 0x2C, SIZE @ 0x30 = CHECKSUM kao SIZE?

# Najvjerovatnije: kod 0x30 je CRCRANGE za BMHD koji pocinje na 0x28 ili 0x2C
# A CRCBMHD za taj isti BMHD je na 0x34 = LE: 0x000204C0
# Sto bi STAD mogao biti? Provjeri region od 0xC0 nadalje ali s razlicitim ENDADD

print("\nPokusaj: CRCRANGE @ 0x30 = CRC([STAD, ENDADD])")
print("Probam razne STAD+ENDADD kombinacije iz headerskih vrijednosti:")

# Adrese koje se pojavljuju u headeru
addrs = [0x000000C0, 0x00007F04, 0x80020000, 0x80007F00,
         0x000204C0, 0x80000000, 0x80007EFF,
         0x80012C78, 0x80007E74, 0x00001000]

# Probaj sve parove (start, end) gdje su oba unutar fajla
file_size = len(ori)
candidate_pairs = [
    (0x0000C0, 0x7F04),
    (0x0000C0, 0x7EFF),
    (0x0000C0, 0x7F00),
    (0x000000, 0x7F04),
    (0x000000, 0x7EFF),
    (0x0000C0, 0x010000),
    (0x000034, 0x7F04),
    (0x000034, 0x7EFF),
    (0x000034, 0x010000),
    (0x001000, 0x7F04),   # STAD=0x1000 (iz 0x50)
    (0x001000, 0x7EFF),
    (0x001000, 0x010000),
    (0x001000, 0x012C78),  # do adrese iz 0x48
    (0x007E74, 0x012C78),  # od adrese 0x4C do 0x48
    (0x000000, 0x012C78),
    (0x0000C0, 0x012C78),
]

for start, end in candidate_pairs:
    if end >= len(ori): continue
    chunk1 = bytes(ori[start:end+1])
    chunk2 = bytes(stg2[start:end+1])
    for algo_name, fn in [("bosch", bosch), ("std", std)]:
        for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
            v1 = fn(chunk1, init, xo)
            v2 = fn(chunk2, init, xo)
            check_both(f"crc_{algo_name}(0x{start:06X}..0x{end:06X}) i={init:08X} xo={xo:08X}", v1, v2)


# ─── 3. Svi blokovi iz BOOT s nuliranim CS ────────────────────────────────────
print("\n" + "=" * 70)
print("Prosireniji scan s nuliranim CS (sve kombinacije offset-a u BOOT):")

# Probaj sve razumne regije u BOOT sa CS nuliranim
d1_z = bytearray(ori)
d2_z = bytearray(stg2)
d1_z[0x30:0x34] = b"\x00\x00\x00\x00"
d2_z[0x30:0x34] = b"\x00\x00\x00\x00"

step = 0x100
for start in range(0, 0x1000, step):
    for end in [0x7EFF, 0x7F00, 0x7FC0, 0x7FFF, 0x10000, 0x60000]:
        if end <= start: continue
        chunk1 = bytes(d1_z[start:end])
        chunk2 = bytes(d2_z[start:end])
        for algo_name, fn in [("bosch", bosch), ("std", std)]:
            for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0)]:
                v1 = fn(chunk1, init, xo)
                v2 = fn(chunk2, init, xo)
                check_both(f"zeroed_cs/{algo_name}(0x{start:05X}..0x{end:05X}) i={init:08X}", v1, v2)


# ─── 4. Provjeri: je li CRC na 0x08 ispravno izracunat? ──────────────────────
print("\n" + "=" * 70)
print("Kriz-provjera: vrijednost @ 0x08 (CRCRANGE za STAD=0xC0..ENDADD):")
CRCRANGE_ORI = struct.unpack_from("<I", ori, 0x08)[0]
print(f"  CRCRANGE @ 0x08 (LE) = 0x{CRCRANGE_ORI:08X}")
print(f"  CRCRANGE @ 0x08 (BE) = 0x{struct.unpack_from('>I', ori, 0x08)[0]:08X}")

# CRC od raznih regija treba matchirati 0x80020000 ili 0x00000280
TARGET = 0x80020000
TARGET_LE = 0x00000280

for start_off in [0xC0, 0x00, 0x10, 0x40]:
    for end_off in [0x7F04, 0x7F05, 0x7F03, 0x7EFF, 0x7F00, 0x7F80, 0x8000, 0x10000]:
        if end_off <= start_off: continue
        chunk = bytes(ori[start_off:end_off])
        for algo_name, fn in [("bosch", bosch), ("std", std)]:
            for init, xo in [(0xFFFFFFFF, 0xFFFFFFFF), (0, 0), (0xFFFFFFFF, 0), (0, 0xFFFFFFFF)]:
                v = fn(chunk, init, xo)
                if v == TARGET or v == TARGET_LE:
                    print(f"  KRIZ-PROVJERA MATCH! {algo_name}(0x{start_off:04X}..0x{end_off:04X}) "
                          f"i={init:08X} xo={xo:08X} = 0x{v:08X} "
                          f"({'TARGET' if v==TARGET else 'TARGET_LE'})")


# ─── Finalno ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"UKUPNO POGODAKA za CS@0x30: {len(hits)}")
for h in hits:
    print(f"  {h}")
if not hits:
    print("  Nema pogodaka za 0x30.")
print("=" * 70)
