#!/usr/bin/env python3
"""
EEPROM Odometar Circular Buffer — Duboka analiza slota
Fokus: dekodiranje 20-bajtnog slot formata koji se ponavlja
"""

import sys
import struct
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ECU_ROOT = Path("C:/Users/SeaDoo/Desktop/ECU")


def load(path):
    with open(path, 'rb') as f:
        return f.read()


def u16le(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u16be(data, off):
    return struct.unpack_from(">H", data, off)[0]


def u32le(data, off):
    return struct.unpack_from("<I", data, off)[0]


def hexline(data, off, n=20):
    chunk = data[off:off+n]
    return ' '.join(f'{b:02X}' for b in chunk)


# ─────────────────────────────────────────────────────────────────────────────
# Analiza 20-bajtnog slot formata
# Pattern vidljiv iz 063 85-31:
#   @ 0x0AC4: FF FF 00 64 88 65 5E A0 65 00 00 00 05 00 00 00 0B 14 10 02
#   @ 0x0AD8: A0 99 00 64 88 66 5E A0 65 00 00 00 05 00 00 00 0B 14 10 02
#   @ 0x0AEC: A0 99 00 64 46 47 42 9E 65 00 00 00 0A 00 00 00 0B 14 10 02
#   Odometar (5131 min = 0x140B) je @ offset +16..+17 (LE)
# ─────────────────────────────────────────────────────────────────────────────

SLOT_SIZE = 20

def decode_slot(data, off):
    """Dekodira 20-bajtni slot na zadanoj adresi."""
    if off + SLOT_SIZE > len(data):
        return None
    raw = data[off:off+SLOT_SIZE]
    hex_str = hexline(data, off, SLOT_SIZE)

    # Pokušaj različite interpretacije odometra
    odo_at_0  = u16le(data, off + 0)   # offset 0
    odo_at_2  = u16le(data, off + 2)   # offset 2
    odo_at_16 = u16le(data, off + 16)  # offset 16 (0x10)
    odo_at_18 = u16le(data, off + 18)  # offset 18

    # Counter/index bytes
    b0 = raw[0]
    b1 = raw[1]
    b2 = raw[2]
    b3 = raw[3]

    return {
        "off": off,
        "hex": hex_str,
        "odo@0":  odo_at_0,
        "odo@2":  odo_at_2,
        "odo@16": odo_at_16,
        "odo@18": odo_at_18,
        "b[0]": b0,
        "b[1]": b1,
        "b[2]": b2,
        "b[3]": b3,
    }


def scan_buffer_region(data, start, end, stride, expected_odo):
    """
    Skeniraj buffer regiju s poznatim stride-om i dekodira slotove.
    Traži koji offset unutar slota sadrži expected_odo.
    """
    hits = []
    off = start
    while off + SLOT_SIZE <= end and off < len(data):
        slot = decode_slot(data, off)
        if slot is None:
            break
        # Provjeri sve u16 LE u slotu
        for field_off in range(0, SLOT_SIZE - 1, 1):
            v = u16le(data, off + field_off)
            if v == expected_odo:
                hits.append((off, field_off, v))
        off += stride
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# Analiza "proba" fajlova — usporedba s izvornim
# ─────────────────────────────────────────────────────────────────────────────

def compare_files(path_a, path_b, label_a, label_b, region_start=0x0400, region_end=0x2000):
    """Usporedi dvije datoteke u zadanoj regiji."""
    data_a = load(path_a)
    data_b = load(path_b)

    diffs = []
    for i in range(region_start, min(region_end, len(data_a), len(data_b))):
        if data_a[i] != data_b[i]:
            diffs.append(i)

    if not diffs:
        print(f"  Nema razlika u 0x{region_start:04X}-0x{region_end:04X}")
        return

    # Grupiraj uzastopne
    groups = []
    grp_start = diffs[0]
    prev = diffs[0]
    for d in diffs[1:]:
        if d == prev + 1:
            prev = d
        else:
            groups.append((grp_start, prev))
            grp_start = d
            prev = d
    groups.append((grp_start, prev))

    print(f"  Razlike ({len(diffs)} B u {len(groups)} blokova):")
    for (gs, ge) in groups[:30]:
        size = ge - gs + 1
        hex_a = ' '.join(f'{data_a[j]:02X}' for j in range(gs, ge+1))
        hex_b = ' '.join(f'{data_b[j]:02X}' for j in range(gs, ge+1))
        print(f"    0x{gs:04X}-0x{ge:04X} (+{size}B): {label_a}=[{hex_a}]  {label_b}=[{hex_b}]")


# ─────────────────────────────────────────────────────────────────────────────
# Identifikacija slot strukture za 064 fajlove
# Poznato: 064 86-31 = 5191 min, hit @ 0x0562 i 0x0B25, 0x0B39... (stride ~20)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_064_slot_structure():
    """Detaljna analiza slot strukture za 064 HW."""
    print("\n" + "="*70)
    print("064 HW — SLOT STRUKTURA ANALIZA")
    print("="*70)

    files_064 = [
        ("064 9-5",    ECU_ROOT / "064" / "064 9-5",    545,    ECU_ROOT / "064" / "064 9-5.bin"),
        ("064 86-31",  ECU_ROOT / "064" / "064 86-31",  5191,   ECU_ROOT / "064" / "064 86-31.bin"),
        ("064 99-50",  ECU_ROOT / "064" / "064 99-50",  5990,   None),
        ("064 163",    ECU_ROOT / "064" / "064 163",    9780,   None),
        ("064 211-07", ECU_ROOT / "064" / "064 211-07", 12667,  None),
    ]

    for name, path, expected_odo, path2 in files_064:
        if not path.exists():
            continue
        data = load(path)
        print(f"\n--- {name} (očekivano: {expected_odo} min = 0x{expected_odo:04X}) ---")
        print(f"  HW timer @ 0x0125: '{data[0x125:0x12A].decode('ascii','replace').strip()}'")

        # Skeniranje regije 0x0400-0x2000 svaki 1B za exact match
        found_at = []
        for i in range(0, len(data)-1):
            if u16le(data, i) == expected_odo:
                found_at.append(i)

        print(f"  Sve LE pozicije 0x{expected_odo:04X}: {[hex(x) for x in found_at[:30]]}")

        # Za svaku poziciju u regiji 0x0400-0x2000, prikaži kontekst
        low_hits = [x for x in found_at if 0x0400 <= x <= 0x2000]
        if low_hits:
            print(f"  Pozicije u regiji 0x0400-0x2000:")
            for h in low_hits[:20]:
                # Prikaži 20B context od -4 do +16 (ukupno 20)
                start_ctx = max(0, h - 4)
                raw = hexline(data, start_ctx, 32)
                # Identifikacija offset unutar potencijalnog slota
                # Ako je stride ~20, provjeri od kojeg ste u slotu
                b_before = ' '.join(f'{data[j]:02X}' for j in range(max(0, h-4), h))
                b_val = f'{data[h]:02X} {data[h+1]:02X}'
                b_after = ' '.join(f'{data[j]:02X}' for j in range(h+2, min(len(data), h+18)))
                print(f"    0x{h:04X}: ...{b_before} [{b_val}] {b_after}")

        # Analiza stride-a između susjednih hitova
        if len(low_hits) >= 2:
            strides_observed = [low_hits[i+1] - low_hits[i] for i in range(len(low_hits)-1)]
            print(f"  Strides: {strides_observed[:20]}")

            # Pokušaj identificirati konstantni stride
            stride_counts = defaultdict(int)
            for s in strides_observed:
                stride_counts[s] += 1
            print(f"  Stride distribucija: {dict(sorted(stride_counts.items(), key=lambda x: -x[1])[:5])}")

        # Analiziraj slot @ 0x0562 i okolinu — ovo je "anchor" slot
        print(f"\n  Anchor slot @ 0x0500-0x0600:")
        for off in range(0x0500, 0x0600, SLOT_SIZE):
            if off + SLOT_SIZE > len(data):
                break
            slot_hex = hexline(data, off, SLOT_SIZE)
            odo_val = u16le(data, off + 16)
            marker = " <<< AKTIVAN" if odo_val == expected_odo else ""
            has_odo = " [ODO]" if any(u16le(data, off+j) == expected_odo for j in range(0, SLOT_SIZE-1)) else ""
            print(f"    0x{off:04X}: {slot_hex}  odo@+16={odo_val}{marker}{has_odo}")

        # Prikaži što je na 0x04FE (magic constant 292 = 0x0124)
        print(f"\n  @ 0x04FC-0x0510:")
        print(f"    {hexline(data, 0x04FC, 20)}")


def analyze_064_buffer_regions():
    """
    Za 064 fajlove — analiziraj CIJELI buffer od 0x0500 do 0x1D00.
    Identificiraj blokove i stripe.
    """
    print("\n" + "="*70)
    print("064 HW — BUFFER REGIJA MAPA")
    print("="*70)

    # Koristimo 064 86-31 kao primarni fajl (5191 min)
    path = ECU_ROOT / "064" / "064 86-31"
    if not path.exists():
        print("Fajl nije pronađen!")
        return
    data = load(path)
    odo = 5191

    print(f"\nFajl: 064 86-31 ({odo} min = 0x{odo:04X})")
    print(f"\nBuffer scan 0x0500-0x1D00 (stride=20):")

    # Scan s stride=20
    print(f"\n{'Adresa':8} {'Hex (20B)':60} {'@+0':7} {'@+2':7} {'@+16':7} {'flag':4}")
    for off in range(0x0500, 0x1D00, SLOT_SIZE):
        if off + SLOT_SIZE > len(data):
            break
        slot_hex = hexline(data, off, SLOT_SIZE)
        v0  = u16le(data, off + 0)
        v2  = u16le(data, off + 2)
        v16 = u16le(data, off + 16)
        v18 = u16le(data, off + 18)
        b3  = data[off + 3]

        marker = ""
        if v0 == odo or v2 == odo or v16 == odo:
            marker = " <ODO"
        # Ignore empty/FF lines
        if all(b == 0xFF for b in data[off:off+SLOT_SIZE]):
            continue
        if all(b == 0x00 for b in data[off:off+SLOT_SIZE]):
            continue

        print(f"  0x{off:04X}: {slot_hex}  {v0:5} {v2:5} {v16:5}  {data[off]:02X}{marker}")

    # Sada pokušaj s različitim stride-om za 063 fajl
    print(f"\n\n--- 063 85-31 buffer scan ---")
    path063 = ECU_ROOT / "063" / "063 85-31"
    if path063.exists():
        d = load(path063)
        odo063 = 5131
        print(f"\nFajl: 063 85-31 ({odo063} min = 0x{odo063:04X})")
        print(f"Buffer scan 0x0400-0x2000 (stride=20):")
        print(f"\n{'Adresa':8} {'Hex (20B)':60} {'@+0':7} {'@+2':7} {'@+16':7} {'b[0]':4}")
        for off in range(0x0400, 0x2000, SLOT_SIZE):
            if off + SLOT_SIZE > len(d):
                break
            slot_hex = hexline(d, off, SLOT_SIZE)
            v0  = u16le(d, off + 0)
            v16 = u16le(d, off + 16)

            marker = ""
            if any(u16le(d, off+j) == odo063 for j in range(0, SLOT_SIZE-1)):
                marker = " <ODO"
            if all(b == 0xFF for b in d[off:off+SLOT_SIZE]):
                continue
            if all(b == 0x00 for b in d[off:off+SLOT_SIZE]):
                continue

            print(f"  0x{off:04X}: {slot_hex}  {v0:5} {v16:5}  {d[off]:02X}{marker}")


def analyze_064_slot_detail():
    """
    Fokus na 064 86-31 — detaljni prikaz buffer bloka 0x0A80-0x0C80
    koji sadrži main circular buffer (sa stridovima 20 i 25).
    """
    print("\n" + "="*70)
    print("064 HW — CIRCULAR BUFFER DETALJ (0x0A80-0x0C80)")
    print("="*70)

    path = ECU_ROOT / "064" / "064 86-31"
    if not path.exists():
        return
    data = load(path)
    odo = 5191

    # Skeniranje s potencijalnim stride-om = 20 i 25
    for stride in [20, 25]:
        print(f"\n--- stride={stride} ---")
        for start in [0x0A80, 0x0AA0, 0x0AB0]:
            print(f"\n  Start=0x{start:04X}:")
            for i, off in enumerate(range(start, 0x0D00, stride)):
                if off + 20 > len(data):
                    break
                raw = data[off:off+20]
                hex_str = ' '.join(f'{b:02X}' for b in raw)
                v16 = u16le(data, off + 16)
                v0  = u16le(data, off + 0)
                marker = " <ODO" if odo in [v0, v16, u16le(data, off+2), u16le(data, off+14)] else ""
                print(f"    [{i:3}] 0x{off:04X}: {hex_str}  v@+16={v16} v@+0={v0}{marker}")


def identify_active_slot_marker():
    """
    Identifikacija markera aktivnog slota.
    Pattern: FF FF na početku slota = "zauzeto/staro", A0 99 = "prazno/default"?
    Ili je to write-counter?
    """
    print("\n" + "="*70)
    print("AKTIVNI SLOT MARKER IDENTIFIKACIJA")
    print("="*70)

    # Analiziramo 063 85-31 koji ima mnogo slotova (25 hitova)
    # i 064 99-50 koji ima najviše hitova
    test_files = [
        ("063 85-31", ECU_ROOT / "063" / "063 85-31", 5131),
        ("064 99-50", ECU_ROOT / "064" / "064 99-50", 5990),
        ("064 86-31", ECU_ROOT / "064" / "064 86-31", 5191),
        ("064 9-5",   ECU_ROOT / "064" / "064 9-5",   545),
    ]

    for name, path, odo in test_files:
        if not path.exists():
            continue
        data = load(path)
        print(f"\n--- {name} ({odo} min) ---")

        # Pronađi sve pozicije s exact match
        all_hits = []
        for i in range(0, len(data)-1):
            if u16le(data, i) == odo:
                all_hits.append(i)

        # Filtriraj na odometar-buffer regiju (0x0400-0x2000)
        buf_hits = [h for h in all_hits if 0x0400 <= h <= 0x2000]
        print(f"  {len(buf_hits)} hitova u 0x0400-0x2000: {[hex(h) for h in buf_hits[:20]]}")

        # Za svaki hit, pogledaj što je na -(offset_within_slot) da nađemo slot start
        for h in buf_hits[:15]:
            # Probaj različite offset-e unutar slota
            for field_off in [0, 2, 4, 14, 16]:
                slot_start = h - field_off
                if slot_start < 0:
                    continue
                b0 = data[slot_start] if slot_start < len(data) else 0xFF
                b1 = data[slot_start+1] if slot_start+1 < len(data) else 0xFF
                b2 = data[slot_start+2] if slot_start+2 < len(data) else 0xFF
                b3 = data[slot_start+3] if slot_start+3 < len(data) else 0xFF
                # Specifičan pattern: FF FF 00 64 = stari zapis? A0 99 00 64 = normal?
                is_ff = (b0 == 0xFF and b1 == 0xFF)
                is_a099 = (b0 == 0xA0 and b1 == 0x99)
                if is_ff or is_a099:
                    tag = "FF_FF" if is_ff else "A0_99"
                    print(f"    hit@0x{h:04X}: field_off={field_off} slot_start=0x{slot_start:04X} [{b0:02X} {b1:02X} {b2:02X} {b3:02X}] → {tag}")
                    break


def analyze_header_region():
    """
    Analiza zaglavlja EEPROM-a (0x0000-0x0500) za index/counter.
    Tražimo fiksnu adresu koja se razlikuje između fajlova s različitim sati.
    """
    print("\n" + "="*70)
    print("HEADER REGION — TRAŽENJE INDEX/COUNTER-a")
    print("="*70)

    files = [
        ("064 9-5",    ECU_ROOT / "064" / "064 9-5",    545),
        ("064 86-31",  ECU_ROOT / "064" / "064 86-31",  5191),
        ("064 99-50",  ECU_ROOT / "064" / "064 99-50",  5990),
        ("064 163",    ECU_ROOT / "064" / "064 163",    9780),
        ("064 211-07", ECU_ROOT / "064" / "064 211-07", 12667),
    ]

    datasets = []
    for name, path, odo in files:
        if not path.exists():
            continue
        data = load(path)
        datasets.append((name, data, odo))

    if len(datasets) < 2:
        return

    print(f"\nUsporedba {len(datasets)} fajlova u regiji 0x0000-0x0500:")

    # Nađi adrese koje se RAZLIKUJU između fajlova
    n = len(datasets)
    diff_addrs = []
    ref_data = datasets[0][1]

    for addr in range(0, min(0x0500, len(ref_data))):
        vals = [d[addr] for _, d, _ in datasets]
        if len(set(vals)) > 1:  # razlikuju se
            diff_addrs.append(addr)

    print(f"  Adresen koje se razlikuju (0x0000-0x0500): {len(diff_addrs)}")

    # Grupiraj uzastopne
    if diff_addrs:
        groups = []
        gs = diff_addrs[0]
        prev = diff_addrs[0]
        for a in diff_addrs[1:]:
            if a == prev + 1:
                prev = a
            else:
                groups.append((gs, prev))
                gs = a
                prev = a
        groups.append((gs, prev))

        print(f"  Blokovi: {len(groups)}")
        for (gs, ge) in groups[:30]:
            print(f"    0x{gs:04X}-0x{ge:04X}:")
            for (name, data, odo) in datasets:
                vals = ' '.join(f'{data[j]:02X}' for j in range(gs, ge+1))
                print(f"      [{name:15s} {odo:5d}min]: [{vals}]")

    # Posebno pregledaj regiju 0x0400-0x0600 (odometar počinje @ 0x0562)
    print(f"\n  Regija 0x0400-0x0580 — razlike:")
    diff_addrs2 = []
    for addr in range(0x0400, 0x0580):
        vals = [d[addr] if addr < len(d) else 0 for _, d, _ in datasets]
        if len(set(vals)) > 1:
            diff_addrs2.append(addr)

    if diff_addrs2:
        groups2 = []
        gs = diff_addrs2[0]
        prev = diff_addrs2[0]
        for a in diff_addrs2[1:]:
            if a == prev + 1:
                prev = a
            else:
                groups2.append((gs, prev))
                gs = a
                prev = a
        groups2.append((gs, prev))

        for (gs, ge) in groups2[:20]:
            print(f"    0x{gs:04X}-0x{ge:04X}:")
            for (name, data, odo) in datasets:
                vals = ' '.join(f'{data[j]:02X}' for j in range(gs, ge+1) if j < len(data))
                u16v = u16le(data, gs) if gs+2 <= len(data) else 0
                print(f"      [{name:15s} {odo:5d}min]: [{vals}]  as u16LE={u16v}")


def analyze_slot20_structure():
    """
    Definiraj točan format 20-bajtnog slota na osnovu opservacija.

    Iz kontekst dump-a @ 063 85-31 (5131 min):
    FF FF 00 64 88 65 5E A0 65 00 00 00 05 00 00 00 0B 14 10 02
    A0 99 00 64 88 66 5E A0 65 00 00 00 05 00 00 00 0B 14 10 02
    A0 99 00 64 46 47 42 9E 65 00 00 00 0A 00 00 00 0B 14 10 02
    ...
    A0 99 00 64 45 47 42 98 65 00 00 00 08 80 84 00 00 E9 01 10  (ZADNJI — ima 80 84!)

    Byte offset analiza:
    [0-1]:  counter/flag (FF FF = invalid/wrap?, A0 99 = normal?)
    [2]:    00 = uvijek 0?
    [3]:    64 = uvijek 100?
    [4-7]:  4 bajta nešto
    [8-9]:  RPM ili nešto 2B
    [10-11]: uvijek 00 00?
    [12]:   event count? (05, 05, 0A, 0A, 08...)
    [13-15]: uvijek 00 00 00?
    [16-17]: ODOMETAR u16 LE!
    [18-19]: nešto (10 02, 12 02...)
    """
    print("\n" + "="*70)
    print("SLOT FORMAT ANALIZA")
    print("="*70)

    path = ECU_ROOT / "063" / "063 85-31"
    if not path.exists():
        return
    data = load(path)
    odo = 5131

    print(f"\n063 85-31 ({odo} min) — Buffer 0x0AC4 do 0x0B70 (stride=20):")
    print(f"\n{'Off':6} {'[0-1]':5} {'[2]':3} {'[3]':3} {'[4..7]':12} {'[8..11]':12} {'[12]':4} {'[13-15]':9} {'[16-17]=ODO':12} {'[18-19]':6}")

    for off in range(0x0AC4, 0x0B70, SLOT_SIZE):
        if off + SLOT_SIZE > len(data):
            break
        raw = data[off:off+SLOT_SIZE]
        flag = f"{raw[0]:02X}{raw[1]:02X}"
        b2   = f"{raw[2]:02X}"
        b3   = f"{raw[3]:02X}"
        b4_7 = ' '.join(f'{raw[i]:02X}' for i in range(4,8))
        b8_11= ' '.join(f'{raw[i]:02X}' for i in range(8,12))
        b12  = f"{raw[12]:02X}"
        b1315= ' '.join(f'{raw[i]:02X}' for i in range(13,16))
        odo_val = u16le(data, off+16)
        b1819= f"{raw[18]:02X} {raw[19]:02X}"
        marker = " ← ODO" if odo_val == odo else ""
        print(f"0x{off:04X}: {flag:5} {b2:3} {b3:3} {b4_7:11} {b8_11:11} {b12:4} {b1315:9} {odo_val:5} [{b1819}]{marker}")

    # Isti format za drugi blok koji se pojavljuje (0x1344-0x13D1)
    print(f"\n063 85-31 — Blok 0x1344 do 0x13F0 (stride=20):")
    print(f"\n{'Off':6} {'[0-1]':5} {'[16-17]=ODO':12} {'[18-19]':6}")
    for off in range(0x1344, 0x13F0, SLOT_SIZE):
        if off + SLOT_SIZE > len(data):
            break
        odo_val = u16le(data, off+16)
        flag = f"{data[off]:02X}{data[off+1]:02X}"
        b1819 = f"{data[off+18]:02X} {data[off+19]:02X}"
        marker = " ← ODO" if odo_val == odo else ""
        print(f"0x{off:04X}: {flag:5} {odo_val:5} [{b1819}]{marker}")

    # Treći blok (0x1AC4-0x1B70)
    print(f"\n063 85-31 — Blok 0x1AC4 do 0x1B70 (stride=20):")
    for off in range(0x1AC4, 0x1B70, SLOT_SIZE):
        if off + SLOT_SIZE > len(data):
            break
        odo_val = u16le(data, off+16)
        flag = f"{data[off]:02X}{data[off+1]:02X}"
        b1819 = f"{data[off+18]:02X} {data[off+19]:02X}"
        marker = " ← ODO" if odo_val == odo else ""
        print(f"0x{off:04X}: {flag:5} {odo_val:5} [{b1819}]{marker}")


def analyze_last_slot_marker():
    """
    Identificiraj marker zadnjeg slota.
    Primijećeno: zadnji slot ima "80 84 00 00" u oktet [12-15]
    dok ostali imaju "00 00 00 00" ili "00 [bla] 00 00".
    """
    print("\n" + "="*70)
    print("ZADNJI SLOT MARKER — 80 84 PATTERN")
    print("="*70)

    files_to_check = [
        ("063 85-31",  ECU_ROOT / "063" / "063 85-31",  5131),
        ("063 92-51",  ECU_ROOT / "063" / "063 92-51",  5571),
        ("064 86-31",  ECU_ROOT / "064" / "064 86-31",  5191),
        ("064 9-5",    ECU_ROOT / "064" / "064 9-5",    545),
        ("064 99-50",  ECU_ROOT / "064" / "064 99-50",  5990),
        ("064 163",    ECU_ROOT / "064" / "064 163",    9780),
        ("064 211-07", ECU_ROOT / "064" / "064 211-07", 12667),
    ]

    for name, path, odo in files_to_check:
        if not path.exists():
            continue
        data = load(path)

        # Traži "80 84" pattern
        hits_8084 = []
        for i in range(0x0400, 0x2000):
            if i+1 < len(data) and data[i] == 0x80 and data[i+1] == 0x84:
                hits_8084.append(i)

        if hits_8084:
            print(f"\n{name} ({odo} min): '80 84' @ {[hex(h) for h in hits_8084[:10]]}")
            for h in hits_8084[:5]:
                # Probaj poravnati na 20B slot
                for slot_start_offset in range(-20, 4):
                    ss = h + slot_start_offset
                    if ss < 0:
                        continue
                    v16 = u16le(data, ss + 16) if ss + 18 <= len(data) else 0
                    if v16 == odo:
                        print(f"  80 84 @ 0x{h:04X} → slot start @ 0x{ss:04X} (offset +{-slot_start_offset}), odo@+16={v16} = {odo} min")
                        # Print cijeli slot
                        slot_hex = hexline(data, ss, SLOT_SIZE)
                        print(f"  slot: {slot_hex}")
                        break
        else:
            print(f"\n{name} ({odo} min): '80 84' NIJE pronađen")


def analyze_062_structure():
    """062 HW — ima potpuno drugačiji layout (adrese 0x1062, 0x4562, 0x5062)."""
    print("\n" + "="*70)
    print("062 HW — LAYOUT ANALIZA")
    print("="*70)

    files_062 = [
        ("062 86-24",  ECU_ROOT / "062" / "062 86-24",  5184),
        ("062 143-21", ECU_ROOT / "062" / "062 143-21", 8601),
        ("062 228-52", ECU_ROOT / "062" / "062 228-52", 13732),
        ("062 848-33", ECU_ROOT / "062" / "062 848-33", 50913),
    ]

    for name, path, odo in files_062:
        if not path.exists():
            continue
        data = load(path)

        print(f"\n--- {name} ({odo} min = 0x{odo:04X}) ---")
        print(f"  HW timer @ 0x0125: '{data[0x125:0x12A].decode('ascii','replace').strip()}'")

        # Pronađi sve LE pozicije
        all_hits = [i for i in range(0, len(data)-1) if u16le(data, i) == odo]
        print(f"  LE pozicije: {[hex(h) for h in all_hits[:15]]}")

        # Za 062 86-24: pronađen @ 0x1062 (i 0x5062 za 848-33)
        # Analiziraj kontekst od -16 do +24 oko prve pozicije
        for h in all_hits[:5]:
            ctx_start = max(0, h-16)
            print(f"\n  Context @ 0x{h:04X} (od 0x{ctx_start:04X}):")
            for row_start in range(ctx_start, min(len(data), h+24), 16):
                row_hex = hexline(data, row_start, 16)
                marker = " ←" if row_start <= h < row_start + 16 else ""
                print(f"    0x{row_start:04X}: {row_hex}{marker}")

        # Skeniranje stride-a kod 062 143-21 (2 hita: 0x4562, 0x5062)
        if len(all_hits) == 2:
            stride = all_hits[1] - all_hits[0]
            print(f"\n  Stride između 2 hita: 0x{stride:04X} = {stride}")

            # 0x5062 - 0x4562 = 0x1000 = 4096
            # 0x5062 - 0x1062 = 0x4000 = 16384 (offset između 1. i 2. od 062 86-24/143-21)


def find_odo_in_all_eeproms():
    """
    Finalni scan: provjeri da li odo uvijek leži na offset +16 unutar 20B slota,
    i identificiraj slot start za svaki fajl.
    """
    print("\n" + "="*70)
    print("FINALNI SCAN — ODO @ SLOT+16 PROVJERA")
    print("="*70)

    all_eeproms = []
    for hw_dir in ["062", "063", "064"]:
        base = ECU_ROOT / hw_dir
        if not base.exists():
            continue
        for p in base.iterdir():
            if p.is_file() and 0x7000 <= p.stat().st_size <= 0x9000:
                # Parsiraj vrijeme
                import re
                m = re.search(r'(\d+)-(\d+)', p.name)
                if m:
                    h, mn = int(m.group(1)), int(m.group(2))
                    odo = h * 60 + mn
                    all_eeproms.append((hw_dir, p, odo))
                else:
                    m2 = re.search(r' (\d+)$', p.name)
                    if m2:
                        h = int(m2.group(1))
                        odo = h * 60
                        all_eeproms.append((hw_dir, p, odo))

    print(f"\n{'HW':4} {'File':30} {'ODO':7} {'SlotStart':10} {'Offset':7} {'Verifikirano':12}")
    for hw, path, odo in all_eeproms:
        if odo == 0:
            continue
        data = load(path)

        # Traži slot gdje odo leži @ offset+16
        found = False
        for i in range(0, len(data)-1):
            if u16le(data, i) == odo:
                # Provjeri: je li i = slot_start + 16?
                slot_start = i - 16
                if slot_start >= 0x0400 and slot_start < 0x2000:
                    # Provjeri je li slot start "razuman" (ne FF, ne 00)
                    b0 = data[slot_start]
                    b1 = data[slot_start+1]
                    # Možda slot marker?
                    found = True
                    print(f"  {hw:4} {path.name:30} {odo:6} min  slot@0x{slot_start:04X}  off=+16  [{b0:02X} {b1:02X}]")
                    break

        if not found:
            # Traži @ offset+0
            for i in range(0, len(data)-1):
                if u16le(data, i) == odo:
                    if 0x0400 <= i < 0x2000:
                        print(f"  {hw:4} {path.name:30} {odo:6} min  odo@0x{i:04X}  off=+0  [{data[i]:02X} {data[i+1]:02X}]")
                        break


def main():
    print("="*70)
    print("ME17Suite — EEPROM Circular Buffer Deep Analysis v2")
    print("="*70)

    analyze_slot20_structure()
    analyze_last_slot_marker()
    analyze_header_region()
    analyze_064_slot_structure()
    analyze_064_buffer_regions()
    analyze_062_structure()
    find_odo_in_all_eeproms()


if __name__ == "__main__":
    main()
