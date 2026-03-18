#!/usr/bin/env python3
"""
EEPROM Odometar Circular Buffer — Konačna analiza i EepromParser
Otkrića:
  - Primarni slot je UVIJEK @ 0x0550+16 = 0x0560 za 064 HW (zadnji "pre-header" slot)
  - Circular buffer počinje @ 0x0AA0 sa stride-om 20
  - Slot format = 20B: [4B meta] [8B session data] [4B counters] [u16 ODO LE] [2B type]
  - Aktivni slot = zadnji s [12]=0x80 0x84 ili zadnji koji se razlikuje
  - 064 211-07 je poseben — drugi layout (stariji buffer)
"""

import sys, struct, re
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
    if off+2 > len(data): return 0
    return struct.unpack_from("<H", data, off)[0]

def u16be(data, off):
    if off+2 > len(data): return 0
    return struct.unpack_from(">H", data, off)[0]

def hexb(data, off, n=20):
    return ' '.join(f'{data[i]:02X}' for i in range(off, min(len(data), off+n)))


# =============================================================================
# Opservacije iz podataka:
#
# 064 HW — ANCHOR SLOT @ 0x0550:
#   Svaki 064 fajl (osim 211-07) ima odometar na poziciji 0x0562 (= 0x0550 + 18)
#   ili 0x0560 (= 0x0550 + 16)
#   Konkretno gledano, 0x0562 je pozicija nalaza, što znači da je ODO @ offset+16
#   od slot start-a 0x0552 ili @ offset+18 od 0x0550
#
#   ALI: gledajući dump za 064 9-5 @ 0x0550:
#     39 02 3B 01 35 02 7C 01 10 02 EB 00 00 00 00 00 00 00 21 02
#     [+0..+17 = pre-data][+18 = 0x21 02 = 545 LE]
#   Za 064 86-31 @ 0x0550:
#     A5 00 9F 00 83 00 A2 01 0A 02 90 01 00 00 00 00 00 00 47 14
#     [+18 = 0x47 14 = 5191 LE]
#   Za 064 99-50 @ 0x0550:
#     DC 00 5C 01 4E 01 7C 01 9E 01 4B 02 00 00 00 00 00 00 66 17
#     [+18 = 0x66 17 = 5990 LE]
#   Za 064 163 @ 0x0550:
#     08 00 A8 00 27 02 B3 01 D4 01 A8 01 12 01 00 00 CC 00 35 26
#     [+18 = 0x35 26 = 9781 ≈ 9780 +1? NE, 0x2635 = 9781 ne 9780]
#     Hmm, 0x35 0x26 LE = 0x2635 = 9781 ... Ime je "064 163" = 163*60 = 9780
#     Razlika 1 min? Ili zaokruživanje?
#
#   ZAKLJUČAK: ODO je @ 0x0562 = slot @ 0x0550, offset +18 (ne +16!)
#
# Circular buffer (064 HW) @ 0x0AA0-0x0C70 approx:
#   Stride = 20 (u fazi punjenja prve petlje), 25 (u fazi 2)
#   Format slota unutar buffer-a: [4B tag] [10B session] [2B flags] [2B ODO LE] [2B type]
#   Aktivni slot = zadnji koji je napisan (ili s 0x80 0x84 markerom)
#
# =============================================================================

def analyze_anchor_slot():
    """
    Provjeri 0x0550 anchor slot za sve 064 fajlove.
    ODO je @ +18 (ili +16?), treba verificirati.
    """
    print("="*70)
    print("ANCHOR SLOT @ 0x0550 ANALIZA (064 HW)")
    print("="*70)

    files_064 = []
    base = ECU_ROOT / "064"
    for p in sorted(base.iterdir()):
        if p.is_file() and 0x7000 <= p.stat().st_size <= 0x9000:
            m = re.search(r'(\d+)-(\d+)', p.name)
            if m:
                odo = int(m.group(1)) * 60 + int(m.group(2))
            else:
                m2 = re.search(r' (\d+)$', p.name)
                odo = int(m2.group(1)) * 60 if m2 else None
            files_064.append((p, odo))

    print(f"\n{'File':30} {'ODO_expect':10} {'@+16':10} {'@+18':10} {'match@16':8} {'match@18':8}")
    for path, odo_expected in files_064:
        if odo_expected is None or odo_expected == 0:
            continue
        data = load(path)
        v16 = u16le(data, 0x0550 + 16)
        v18 = u16le(data, 0x0550 + 18)
        m16 = "OK" if v16 == odo_expected else f"off={v16-odo_expected}"
        m18 = "OK" if v18 == odo_expected else f"off={v18-odo_expected}"
        hex_str = hexb(data, 0x0550, 20)
        print(f"  {path.name:30} {odo_expected:10} {v16:10} {v18:10} {m16:8} {m18:8}")
        print(f"    0x0550: {hex_str}")


def analyze_buffer_for_all():
    """
    Za svaki 064 fajl, skenira circular buffer i traži zadnji napisani slot.
    Strategija: ODO pri +0 ili +2 poziciji u okviru zapisa u buffer-u.
    """
    print("\n" + "="*70)
    print("CIRCULAR BUFFER SCAN — SVE 064 DATOTEKE")
    print("="*70)

    files_064 = []
    base = ECU_ROOT / "064"
    for p in sorted(base.iterdir()):
        if p.is_file() and 0x7000 <= p.stat().st_size <= 0x9000:
            m = re.search(r'(\d+)-(\d+)', p.name)
            if m:
                odo = int(m.group(1)) * 60 + int(m.group(2))
            else:
                m2 = re.search(r' (\d+)$', p.name)
                odo = int(m2.group(1)) * 60 if m2 else None
            files_064.append((p, odo))

    print(f"\nUsporing: scan buffer 0x0A00-0x0D00")
    for path, odo_expected in files_064:
        if odo_expected is None or odo_expected == 0:
            continue
        data = load(path)
        print(f"\n--- {path.name} (odo={odo_expected}) ---")

        # Traži sve pozicije u buffer regiji
        hits = []
        for off in range(0x0A00, 0x0D00):
            if u16le(data, off) == odo_expected:
                hits.append(off)

        if not hits:
            print(f"  NIJE pronađen u 0x0A00-0x0D00!")
            continue

        print(f"  Pronađeno @ {[hex(h) for h in hits]}")

        # Analiziraj kontekst svakog hita
        for h in hits[:5]:
            # Pokušaj identificirati slot granicu (multiple of 20)
            # Offset 0x0A9C je hit za 064 9-5 — koji je to slot od 0x0AA0?
            for slot_off in [0, 2, 4, 14, 16, 18]:
                ss = h - slot_off
                if ss < 0: continue
                # Provjeri je li slot_start na aligned offset
                raw = hexb(data, ss, 20)
                print(f"  h=0x{h:04X} slot_start=0x{ss:04X} [off=+{slot_off}]: {raw}")
            print()


def identify_slot_boundaries_064():
    """
    Identificiraj precizne slot granice za 064 HW.
    Koristimo 064 9-5 (odo=545) kao primjer.
    Znamo da je odo @ 0x0A9C, 0x0AB0... stride ~20.
    Ako je stride 20 i hit @ 0x0A9C, onda slot start = 0x0A9C - 0 = 0x0A9C (ODO @ +0)
    ili slot start = 0x0A9C - 16 = 0x0A8C (ODO @ +16)
    """
    print("\n" + "="*70)
    print("SLOT GRANICE — 064 9-5 DETALJ")
    print("="*70)

    path = ECU_ROOT / "064" / "064 9-5"
    data = load(path)
    odo = 545

    print(f"\nFajl: 064 9-5 (odo={odo} = 0x{odo:04X})")
    print(f"\nHex dump 0x0A80-0x0C00:")
    for off in range(0x0A80, 0x0C00, 20):
        raw = hexb(data, off, 20)
        has_odo = " <ODO" if any(u16le(data, off+j) == odo for j in range(0, 19)) else ""
        print(f"  0x{off:04X}: {raw}{has_odo}")

    # Isti za 064 99-50 (ima puno hitova)
    path2 = ECU_ROOT / "064" / "064 99-50"
    if path2.exists():
        d2 = load(path2)
        odo2 = 5990
        print(f"\nFajl: 064 99-50 (odo={odo2})")
        print(f"Hex dump 0x0A80-0x0C80:")
        for off in range(0x0A80, 0x0C80, 20):
            raw = hexb(d2, off, 20)
            has_odo = " <ODO" if any(u16le(d2, off+j) == odo2 for j in range(0, 19)) else ""
            print(f"  0x{off:04X}: {raw}{has_odo}")


def analyze_slot_format_definitive():
    """
    Definirajmo slot format gledajući niz koji se MIJENJA između fajlova.
    Fokus: 064 9-5 vs 064 86-31 — oba imaju slotove @ 0x0AA0 regiji.
    """
    print("\n" + "="*70)
    print("DEFINITIVAN FORMAT SLOTA — USPOREDBA DVA FAJLA")
    print("="*70)

    path_a = ECU_ROOT / "064" / "064 9-5"
    path_b = ECU_ROOT / "064" / "064 86-31"

    if not (path_a.exists() and path_b.exists()):
        return

    da = load(path_a)
    db = load(path_b)
    odo_a = 545
    odo_b = 5191

    print(f"\n064 9-5 ({odo_a} min) vs 064 86-31 ({odo_b} min)")
    print(f"\nRegija 0x0A80-0x0B80:")
    print(f"\n{'Adresa':8} {'--- 064 9-5 ---':43} {'--- 064 86-31 ---':43}")
    for off in range(0x0A80, 0x0B80, 20):
        raw_a = hexb(da, off, 20)
        raw_b = hexb(db, off, 20)
        odo_a_here = any(u16le(da, off+j) == odo_a for j in range(0, 19))
        odo_b_here = any(u16le(db, off+j) == odo_b for j in range(0, 19))
        ma = " <A" if odo_a_here else "   "
        mb = " <B" if odo_b_here else "   "
        print(f"  0x{off:04X}: {raw_a}{ma}  |  {raw_b}{mb}")


def find_odo_slot_offset():
    """
    Traži koji je TOČNI offset unutar slota za ODO vrijednost.
    Koristimo sve 064 fajlove i gledamo koji offset (0-18) uvijek poklapa.
    """
    print("\n" + "="*70)
    print("TRAŽENJE TOČNOG ODO OFFSETA UNUTAR SLOTA")
    print("="*70)

    files = []
    base = ECU_ROOT / "064"
    for p in sorted(base.iterdir()):
        if p.is_file() and 0x7000 <= p.stat().st_size <= 0x9000:
            m = re.search(r'(\d+)-(\d+)', p.name)
            odo = int(m.group(1))*60 + int(m.group(2)) if m else None
            if odo and odo > 0:
                files.append((p, odo))

    # Za svaki fajl, nađi prvu poziciju u 0x0A00-0x0C80
    # i odredi offset unutar slota (pretpostavka: slotovi poravnati na stride 20)

    # Referentni slot start: koristimo 0x0AA0 kao base (vidjeli smo da 064 9-5 ima hit @ 0x0A9C)
    # 0x0A9C - 0x0AA0 = -4, što nije valid
    # Probajmo s 0x0A9C kao slot start

    print(f"\nTestiranje slot start = 0x0A9C (koji je vidljiv u 064 9-5):")
    slot_base = 0x0A9C

    for path, odo in files:
        data = load(path)
        print(f"\n  {path.name} (odo={odo}):")

        # Nađi nearest hit >= slot_base
        hits = [i for i in range(slot_base, slot_base + 500)
                if u16le(data, i) == odo]

        for h in hits[:3]:
            off_within = h - slot_base
            # Koji slot (stride 20)?
            slot_idx = off_within // 20
            within_slot = off_within % 20
            actual_slot_start = slot_base + slot_idx * 20
            print(f"    hit @ 0x{h:04X}, slot#{slot_idx} start=0x{actual_slot_start:04X}, off_within_slot={within_slot}")


def analyze_063_slot():
    """
    063 HW — različit buffer layout.
    063 85-31 ima hitove @ 0x0546, 0x0562 (anchor) i @ 0x0AC4+ (buffer).
    """
    print("\n" + "="*70)
    print("063 HW — SLOT ANALIZA")
    print("="*70)

    files_063 = [
        ("063 77-16",  ECU_ROOT / "063" / "063 77-16",  4636),
        ("063 85-31",  ECU_ROOT / "063" / "063 85-31",  5131),
        ("063 92-51",  ECU_ROOT / "063" / "063 92-51",  5571),
        ("063 121-55", ECU_ROOT / "063" / "063 121-55", 7315),
        ("063 585-42", ECU_ROOT / "063" / "063 585-42", 35142),
    ]

    print(f"\nAnchor slot @ 0x0550 (063 HW):")
    print(f"\n{'File':20} {'odo_exp':8} {'@+16':8} {'@+18':8} {'m16':8} {'m18':8}")
    for name, path, odo in files_063:
        if not path.exists():
            continue
        data = load(path)
        v16 = u16le(data, 0x0550 + 16)
        v18 = u16le(data, 0x0550 + 18)
        m16 = "OK" if v16 == odo else f"{v16}"
        m18 = "OK" if v18 == odo else f"{v18}"
        print(f"  {name:20} {odo:8} {v16:8} {v18:8} {m16:8} {m18:8}")

    # 063 85-31 detaljni dump
    path = ECU_ROOT / "063" / "063 85-31"
    if path.exists():
        data = load(path)
        odo = 5131
        print(f"\n063 85-31 (odo={odo}): dump 0x0540-0x0580:")
        for off in range(0x0530, 0x0590, 20):
            raw = hexb(data, off, 20)
            has_odo = " <ODO" if any(u16le(data, off+j) == odo for j in range(0, 19)) else ""
            v16 = u16le(data, off+16)
            v18 = u16le(data, off+18)
            print(f"  0x{off:04X}: {raw}  @+16={v16} @+18={v18}{has_odo}")


def finalni_pregled():
    """
    Finalni pregled: za sve fajlove s poznatim odo, čitaj @ 0x0562 i usporedi.
    Ili @ 0x0560?
    """
    print("\n" + "="*70)
    print("FINALNI PREGLED — ODO LOKACIJA PO HW TIPU")
    print("="*70)

    all_files = []
    for hw in ["062", "063", "064"]:
        base = ECU_ROOT / hw
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            if not p.is_file() or not (0x7000 <= p.stat().st_size <= 0x9000):
                continue
            m = re.search(r'(\d+)-(\d+)', p.name)
            odo = int(m.group(1))*60 + int(m.group(2)) if m else None
            if not odo:
                m2 = re.search(r' (\d+)\b', p.name)
                odo = int(m2.group(1))*60 if m2 else None
            if odo and odo > 0:
                all_files.append((hw, p, odo))

    CANDIDATE_ADDRS = [0x0546, 0x0560, 0x0562, 0x0564, 0x0DE2, 0x0D62, 0x1062, 0x1562, 0x4562, 0x5062]

    print(f"\n{'HW':4} {'File':30} {'odo':7}", end="")
    for a in CANDIDATE_ADDRS:
        print(f" 0x{a:04X}", end="")
    print()

    for hw, path, odo in all_files:
        data = load(path)
        print(f"  {hw:4} {path.name:30} {odo:7}", end="")
        for a in CANDIDATE_ADDRS:
            v = u16le(data, a)
            marker = "OK" if v == odo else f"{v}"
            print(f" {marker:7}", end="")
        print()


def main():
    print("="*70)
    print("ME17Suite — EEPROM Circular Buffer — Konacna Analiza v3")
    print("="*70)

    analyze_anchor_slot()
    analyze_063_slot()
    finalni_pregled()
    identify_slot_boundaries_064()
    analyze_slot_format_definitive()


if __name__ == "__main__":
    main()
