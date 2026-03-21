"""
ME17Suite — Checksum Brute-Force
Traži algoritam koji producira:
  ORI  @ 0x30 = 0xE505BC0B
  STG2 @ 0x30 = 0x9FC76FAD
"""

import struct
import zlib
import sys

ORI_PATH  = "ori_300.bin"
STG2_PATH = "npro_stg2_300.bin"

CS_OFFSET = 0x000030  # lokacija checksuma (4B)
CS_ORI    = 0xE505BC0B
CS_STG2   = 0x9FC76FAD

# ─── Učitavanje ───────────────────────────────────────────────────────────────

with open(ORI_PATH,  "rb") as f: ori  = bytearray(f.read())
with open(STG2_PATH, "rb") as f: stg2 = bytearray(f.read())
print(f"ORI:  {len(ori):,} B")
print(f"STG2: {len(stg2):,} B")

# ─── CRC32 engine (parametriziran) ────────────────────────────────────────────

def make_crc_table(poly: int, reflect: bool) -> list:
    table = []
    for i in range(256):
        if reflect:
            crc = i
            for _ in range(8):
                crc = (crc >> 1) ^ (poly if crc & 1 else 0)
        else:
            crc = i << 24
            for _ in range(8):
                crc = ((crc << 1) ^ poly if crc & 0x80000000 else crc << 1) & 0xFFFFFFFF
        table.append(crc & 0xFFFFFFFF)
    return table


def crc32_param(data: bytes, table: list, init: int, xorout: int,
                refin: bool, refout: bool) -> int:
    crc = init & 0xFFFFFFFF
    if refin:
        for b in data:
            crc = (crc >> 8) ^ table[(crc ^ b) & 0xFF]
    else:
        for b in data:
            crc = ((crc << 8) & 0xFFFFFFFF) ^ table[((crc >> 24) ^ b) & 0xFF]
    if refout and not refin:
        crc = int(f"{crc:032b}"[::-1], 2)
    return (crc ^ xorout) & 0xFFFFFFFF


# ─── Aditivne sume ────────────────────────────────────────────────────────────

def sum_u8(data: bytes) -> int:
    return sum(data) & 0xFFFFFFFF

def sum_u16_be(data: bytes) -> int:
    return sum(struct.unpack_from(">H", data, i)[0]
               for i in range(0, len(data)-1, 2)) & 0xFFFFFFFF

def sum_u16_le(data: bytes) -> int:
    return sum(struct.unpack_from("<H", data, i)[0]
               for i in range(0, len(data)-1, 2)) & 0xFFFFFFFF

def sum_u32_be(data: bytes) -> int:
    return sum(struct.unpack_from(">I", data, i)[0]
               for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF

def sum_u32_le(data: bytes) -> int:
    return sum(struct.unpack_from("<I", data, i)[0]
               for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF

def xorsum_u32_be(data: bytes) -> int:
    v = 0
    for i in range(0, len(data)-3, 4):
        v ^= struct.unpack_from(">I", data, i)[0]
    return v

def xorsum_u32_le(data: bytes) -> int:
    v = 0
    for i in range(0, len(data)-3, 4):
        v ^= struct.unpack_from("<I", data, i)[0]
    return v


# ─── Regije za testiranje ─────────────────────────────────────────────────────

def get_regions(data: bytearray, zero_cs: bool = True) -> dict:
    d = bytearray(data)
    if zero_cs:
        d[CS_OFFSET:CS_OFFSET+4] = b"\x00\x00\x00\x00"

    BOOT_END  = 0x010000
    CODE_S    = 0x010000
    CODE_E    = 0x060000
    CAL_S     = 0x060000
    CAL_E     = 0x160000

    return {
        "BOOT_full":        bytes(d[0x0000:BOOT_END]),
        "BOOT_excl_hdr":    bytes(d[0x0040:BOOT_END]),   # preskoci header (0x00-0x3F)
        "BOOT_hdr_only":    bytes(d[0x0000:0x0040]),
        "BOOT_0_to_200":    bytes(d[0x0000:0x0200]),
        "CODE_full":        bytes(d[CODE_S:CODE_E]),
        "CODE_first8K":     bytes(d[CODE_S:CODE_S+0x2000]),
        "BOOT_CODE":        bytes(d[0x0000:CODE_E]),
        "BOOT_excl_CODE":   bytes(d[0x0040:CODE_E]),
        "BOOT_CODE_CAL":    bytes(d[0x0000:CAL_E]),
        "BOOT_no_cs_u32":   bytes(d[0x0000:0x0030]) + bytes(d[0x0034:BOOT_END]),
    }


# ─── CRC polinom kandidati ────────────────────────────────────────────────────

POLYS = [
    ("CRC32_BZIP2",   0x04C11DB7, False, False),   # ISO-HDLC (Bosch-style)
    ("CRC32_standard",0xEDB88320, True,  True),    # zlib / ISO 3309
    ("CRC32C",        0x82F63B78, True,  True),    # Castagnoli
    ("CRC32D",        0xD419CC15, True,  True),
    ("CRC32_JAMCRC",  0xEDB88320, True,  True),    # JAMCRC (xorout=0)
    ("CRC32_MPEG2",   0x04C11DB7, False, False),   # MPEG2
    ("CRC32_POSIX",   0x04C11DB7, False, False),   # POSIX cksum
    ("CRC32Q",        0x814141AB, False, False),
    ("CRC32_XFER",    0x000000AF, False, False),
    ("CRC32_Bosch_RL",0xEDB88320, True,  False),   # Bosch reflected
]

INIT_VALS = [0xFFFFFFFF, 0x00000000]
XOR_VALS  = [0xFFFFFFFF, 0x00000000]


hits = []

# ─── Scan: aditivne sume ──────────────────────────────────────────────────────
print("\n[1/3] Aditivne sume...")
for zero_cs in (True, False):
    tag = "zero_cs" if zero_cs else "raw"
    r1 = get_regions(ori,  zero_cs)
    r2 = get_regions(stg2, zero_cs)

    for reg_name in r1:
        for algo_name, fn in [
            ("sum_u8",      sum_u8),
            ("sum_u16_be",  sum_u16_be),
            ("sum_u16_le",  sum_u16_le),
            ("sum_u32_be",  sum_u32_be),
            ("sum_u32_le",  sum_u32_le),
            ("xor_u32_be",  xorsum_u32_be),
            ("xor_u32_le",  xorsum_u32_le),
        ]:
            v1 = fn(r1[reg_name])
            v2 = fn(r2[reg_name])
            if v1 == CS_ORI and v2 == CS_STG2:
                hits.append(f"[POGODAK!] {algo_name} / {reg_name} / {tag}"
                             f" => ORI=0x{v1:08X} STG2=0x{v2:08X}")
            # Provjeri negiranu vrijednost
            v1n = (~v1) & 0xFFFFFFFF
            v2n = (~v2) & 0xFFFFFFFF
            if v1n == CS_ORI and v2n == CS_STG2:
                hits.append(f"[POGODAK! NOT] ~{algo_name} / {reg_name} / {tag}"
                             f" => ORI=0x{v1n:08X} STG2=0x{v2n:08X}")

# ─── Scan: CRC32 varijante ────────────────────────────────────────────────────
print("[2/3] CRC32 varijante...")
total = len(POLYS) * len(INIT_VALS) * len(XOR_VALS) * 2 * 2  # approx
done = 0

for poly_name, poly_val, default_refin, default_refout in POLYS:
    for refin in (True, False):
        table = make_crc_table(
            poly_val if not refin else int(f"{poly_val:032b}"[::-1], 2),
            refin
        )
        for refout in (True, False):
            for init in INIT_VALS:
                for xorout in XOR_VALS:
                    for zero_cs in (True, False):
                        tag = "zero_cs" if zero_cs else "raw"
                        r1 = get_regions(ori,  zero_cs)
                        r2 = get_regions(stg2, zero_cs)

                        for reg_name in r1:
                            v1 = crc32_param(r1[reg_name], table, init, xorout, refin, refout)
                            if v1 != CS_ORI:
                                continue
                            # Polu-pogodak — provjeri i STG2
                            v2 = crc32_param(r2[reg_name], table, init, xorout, refin, refout)
                            if v2 == CS_STG2:
                                hits.append(
                                    f"[POGODAK!] CRC32 poly={poly_name}(0x{poly_val:08X})"
                                    f" refin={refin} refout={refout}"
                                    f" init=0x{init:08X} xorout=0x{xorout:08X}"
                                    f" / {reg_name} / {tag}"
                                    f" => ORI=0x{v1:08X} STG2=0x{v2:08X}"
                                )
    done += 1
    print(f"  {done}/{len(POLYS)} polinom-a...", end="\r")

# ─── Scan: zlib CRC32 ─────────────────────────────────────────────────────────
print("\n[3/3] zlib CRC32 s razlicitim init vrijednostima...")
for zero_cs in (True, False):
    tag = "zero_cs" if zero_cs else "raw"
    r1 = get_regions(ori,  zero_cs)
    r2 = get_regions(stg2, zero_cs)
    for reg_name in r1:
        for init in [0, 0xFFFFFFFF, CS_ORI, 0xDEADBEEF]:
            v1 = zlib.crc32(r1[reg_name], init) & 0xFFFFFFFF
            if v1 == CS_ORI:
                v2 = zlib.crc32(r2[reg_name], init) & 0xFFFFFFFF
                if v2 == CS_STG2:
                    hits.append(
                        f"[POGODAK!] zlib.crc32 init=0x{init:08X}"
                        f" / {reg_name} / {tag}"
                        f" => ORI=0x{v1:08X} STG2=0x{v2:08X}"
                    )

# ─── Rezultati ────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print(f"REZULTATI: {len(hits)} pogodak(a)")
print("="*70)
if hits:
    for h in hits:
        print(h)
else:
    print("Nema direktnih pogodaka.")
    print()
    print("Najbliži rezultati (samo ORI strana):")
    # Ispiši top 10 najbliže vrijednosti za CODE i BOOT
    r1 = get_regions(ori, True)
    for reg_name in ("BOOT_full", "CODE_full", "BOOT_CODE"):
        chunk = r1[reg_name]
        v_zlib = zlib.crc32(chunk) & 0xFFFFFFFF
        print(f"  zlib.crc32({reg_name})       = 0x{v_zlib:08X}  (tražimo 0x{CS_ORI:08X})")
        v_bosch = 0xFFFFFFFF
        tbl = make_crc_table(0x04C11DB7, False)
        v_bosch = crc32_param(chunk, tbl, 0xFFFFFFFF, 0xFFFFFFFF, False, False)
        print(f"  crc32_bosch({reg_name})      = 0x{v_bosch:08X}")
        v_su32 = sum_u32_be(chunk)
        print(f"  sum_u32_be({reg_name})       = 0x{v_su32:08X}")
        v_su32l = sum_u32_le(chunk)
        print(f"  sum_u32_le({reg_name})       = 0x{v_su32l:08X}")
        print()

print("="*70)
