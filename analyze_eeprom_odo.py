#!/usr/bin/env python3
"""
EEPROM Odometar Circular Buffer Analiza
Autor: automatska analiza za me_suite projekt
Datum: 2026-03-17

Traži u16 LE vrijednosti odometra (minute) u EEPROM fajlovima
čija imena sadrže informaciju o satima i minutama.
"""

import os
import re
import struct
import sys
from pathlib import Path
from collections import defaultdict

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ─────────────────────────────────────────────────────────────────────────────
# Konfiguracija
# ─────────────────────────────────────────────────────────────────────────────
ECU_ROOT = Path("C:/Users/SeaDoo/Desktop/ECU")

# Kategorije direktorija po HW tipu
HW_DIRS = {
    "062": ECU_ROOT / "062",
    "063": ECU_ROOT / "063",
    "064": ECU_ROOT / "064",
    "alen": ECU_ROOT / "alen",
    "BACKUP": ECU_ROOT / "BACKUP",
    "MIX": ECU_ROOT / "MIX",
    "061": ECU_ROOT / "061",
}

EEPROM_SIZE = 0x8000  # 32KB

# Regex za parsiranje vremena iz imena fajla
# Podržava: "064 211-07", "063 585-42", "062 143-21", "062 848-33"
# i samo sate: "064 163", "063 167", "064 58"
TIME_PATTERN = re.compile(
    r'(\d{3})\s+(\d+)-(\d+)',   # NNN HHH-MM  (npr. "064 211-07")
    re.IGNORECASE
)
TIME_HOURS_ONLY = re.compile(
    r'(\d{3})\s+(\d+)(?![-\d])',  # NNN HHH (samo sati, bez minuta)
    re.IGNORECASE
)

# Poznate "magic" default vrijednosti
MAGIC_DEFAULTS = {60620, 0xFFFF, 0x0000, 0xEDED}

# ─────────────────────────────────────────────────────────────────────────────
# Pomoćne funkcije
# ─────────────────────────────────────────────────────────────────────────────

def parse_time_from_name(name: str):
    """Izvuci (sati, minute) iz imena fajla/direktorija."""
    m = TIME_PATTERN.search(name)
    if m:
        hw = m.group(1)
        hours = int(m.group(2))
        minutes = int(m.group(3))
        return hw, hours, minutes

    # Pokušaj samo-sati format
    m2 = TIME_HOURS_ONLY.search(name)
    if m2:
        hw = m2.group(1)
        hours = int(m2.group(2))
        return hw, hours, 0

    return None, None, None


def find_u16_le(data: bytes, value: int):
    """Pronađi sve pozicije u16 LE vrijednosti u binarnom nizu."""
    packed = struct.pack("<H", value)
    positions = []
    start = 0
    while True:
        pos = data.find(packed, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
    return positions


def find_u16_be(data: bytes, value: int):
    """Pronađi sve pozicije u16 BE vrijednosti u binarnom nizu."""
    packed = struct.pack(">H", value)
    positions = []
    start = 0
    while True:
        pos = data.find(packed, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
    return positions


def read_u16_le(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        return None
    return struct.unpack_from("<H", data, offset)[0]


def read_u16_be(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        return None
    return struct.unpack_from(">H", data, offset)[0]


def hex_context(data: bytes, offset: int, before: int = 8, after: int = 16) -> str:
    """Vrati hex dump okoline offset-a."""
    start = max(0, offset - before)
    end = min(len(data), offset + after)
    chunk = data[start:end]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    # Označi target
    marker_start = offset - start
    return f"[0x{start:04X}] {hex_str}  (marker@+{marker_start})"


def is_eeprom_file(path: Path) -> bool:
    """Provjeri je li fajl vjerojatno EEPROM (32KB ± tolerancija)."""
    try:
        size = path.stat().st_size
        # EEPROM može biti 32KB (0x8000) ili varirati malo
        return 0x7000 <= size <= 0x9000 and path.is_file()
    except:
        return False


def load_eeprom(path: Path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        return data
    except Exception as e:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Analiza jednog EEPROM fajla
# ─────────────────────────────────────────────────────────────────────────────

def analyze_eeprom(path: Path, expected_minutes: int = None, hw_type: str = "???"):
    """Kompletna analiza jednog EEPROM fajla."""
    data = load_eeprom(path)
    if data is None:
        return None

    result = {
        "path": str(path),
        "name": path.name,
        "size": len(data),
        "hw": hw_type,
        "expected_minutes": expected_minutes,
        "found_le": [],
        "found_be": [],
        "hw_timer_ascii": None,
        "magic_hits": [],
        "all_u16_candidates": [],
    }

    # HW timer @ 0x0125 (5-digit ASCII)
    try:
        hw_str = data[0x0125:0x012A].decode('ascii', errors='replace')
        result["hw_timer_ascii"] = hw_str.strip()
    except:
        pass

    # Traži expected_minutes ako je poznat
    if expected_minutes is not None and expected_minutes > 0:
        le_hits = find_u16_le(data, expected_minutes)
        be_hits = find_u16_be(data, expected_minutes)
        result["found_le"] = le_hits
        result["found_be"] = be_hits

    # Traži magic defaults
    for magic in MAGIC_DEFAULTS:
        hits = find_u16_le(data, magic)
        if hits:
            result["magic_hits"].append((magic, hits[:5]))  # max 5

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Sakupljanje svih EEPROM fajlova
# ─────────────────────────────────────────────────────────────────────────────

def collect_all_eeproms():
    """Sakupi sve EEPROM fajlove iz ECU direktorija."""
    eeproms = []

    for hw_type, base_dir in HW_DIRS.items():
        if not base_dir.exists():
            continue

        # Traži EEPROM fajlove rekurzivno
        for item in base_dir.rglob("*"):
            if not item.is_file():
                continue

            # Provjeri veličinu
            try:
                size = item.stat().st_size
            except:
                continue

            if not (0x6000 <= size <= 0xA000):
                continue

            # Pokušaj parsirati vrijeme iz roditeljskog direktorija ili samog imena
            # Provjeri sve dijelove putanje
            name_to_parse = item.name
            parent_name = item.parent.name

            hw, hours, minutes = parse_time_from_name(parent_name)
            if hw is None:
                hw, hours, minutes = parse_time_from_name(name_to_parse)

            total_minutes = None
            if hours is not None:
                total_minutes = hours * 60 + (minutes or 0)

            eeproms.append({
                "path": item,
                "hw_type": hw_type,
                "hw_digits": hw,
                "hours": hours,
                "minutes": minutes,
                "total_minutes": total_minutes,
                "size": size,
            })

    return eeproms


# ─────────────────────────────────────────────────────────────────────────────
# Circular buffer pattern analiza
# ─────────────────────────────────────────────────────────────────────────────

def analyze_circular_buffer_pattern(all_results):
    """
    Iz skupa rezultata izvuci pattern circular buffera:
    - raspon adresa
    - stride (korak)
    - kako prepoznati aktivni slot
    """
    print("\n" + "="*70)
    print("CIRCULAR BUFFER PATTERN ANALIZA")
    print("="*70)

    # Grupiraj po HW tipu
    by_hw = defaultdict(list)
    for r in all_results:
        if r and r["found_le"]:
            by_hw[r["hw"]].append(r)

    for hw, results in sorted(by_hw.items()):
        print(f"\n--- HW {hw} ---")
        all_addrs = []
        for r in results:
            mins = r["expected_minutes"]
            addrs = r["found_le"]
            print(f"  {r['name']}: {mins} min → LE @ {[hex(a) for a in addrs]}")
            all_addrs.extend(addrs)

        if all_addrs:
            print(f"  Sve adrese: {sorted(set(hex(a) for a in all_addrs))}")
            sorted_addrs = sorted(set(all_addrs))
            if len(sorted_addrs) >= 2:
                strides = [sorted_addrs[i+1] - sorted_addrs[i]
                           for i in range(len(sorted_addrs)-1)]
                print(f"  Strides između adresa: {strides}")
                # Mod za stride
                stride_counts = defaultdict(int)
                for s in strides:
                    stride_counts[s] += 1
                print(f"  Stride distribution: {dict(stride_counts)}")


# ─────────────────────────────────────────────────────────────────────────────
# Analiza svih EEPROM fajlova zajedno — cross-file pattern
# ─────────────────────────────────────────────────────────────────────────────

def deep_circular_analysis(eeproms_with_data):
    """
    Dublja analiza: za svaki EEPROM s poznatim minutama, analiziraj
    kontekst oko svake pronađene adrese da otkrijemo buffer strukturu.
    """
    print("\n" + "="*70)
    print("DEEP CONTEXT ANALIZA")
    print("="*70)

    for entry in eeproms_with_data:
        r = entry["result"]
        data = entry["data"]
        if not r or not r["found_le"] or r["expected_minutes"] is None:
            continue

        mins = r["expected_minutes"]
        print(f"\n{'─'*60}")
        print(f"Fajl: {r['name']} (HW: {r['hw']}, {mins} min)")
        print(f"Veličina: 0x{r['size']:04X} ({r['size']} B)")
        print(f"HW Timer @ 0x0125: '{r['hw_timer_ascii']}'")

        for addr in r["found_le"]:
            ctx = hex_context(data, addr, before=16, after=24)
            print(f"  [LE] @ 0x{addr:04X}: {ctx}")

            # Provjeri je li ovo dio regularnog patternu (svaki n-ti bajt)
            # Gledaj +-128 bajta okolo za druge u16 vrijednosti
            region_start = max(0, addr - 128)
            region_end = min(len(data), addr + 128)
            region = data[region_start:region_end]

            # Nađi sve u16 LE u regiji koji su "razumni" odometar (1-100000 min)
            candidates = []
            for i in range(0, len(region)-1, 2):
                v = struct.unpack_from("<H", region, i)[0]
                if 100 <= v <= 100000:
                    candidates.append((region_start + i, v,
                                       f"{v//60}h{v%60}m"))
            if candidates:
                print(f"    Susjedni kandidati (100-100000 min u ±128B):")
                for ca, cv, ct in candidates[:10]:
                    marker = " ◄ TARGET" if ca == addr else ""
                    print(f"      0x{ca:04X}: {cv} ({ct}){marker}")

        if r["found_be"]:
            for addr in r["found_be"]:
                print(f"  [BE] @ 0x{addr:04X}: {hex_context(data, addr)}")


# ─────────────────────────────────────────────────────────────────────────────
# Traži indeks/counter za aktivni slot
# ─────────────────────────────────────────────────────────────────────────────

def find_active_slot_index(eeproms_with_data):
    """
    Pokušaj pronaći counter/index koji pokazuje na aktivni slot.
    Strategija: za više fajlova s različitim vrijednostima,
    nađi adresu gdje se vrijednost mijenja proporcionalno.
    """
    print("\n" + "="*70)
    print("TRAŽENJE AKTIVNOG SLOT INDEXA")
    print("="*70)

    # Skupi fajlove po HW tipu koji imaju poznate adrese
    by_hw = defaultdict(list)
    for entry in eeproms_with_data:
        r = entry["result"]
        data = entry["data"]
        if r and r["found_le"] and r["expected_minutes"]:
            by_hw[r["hw"]].append({
                "name": r["name"],
                "minutes": r["expected_minutes"],
                "addrs": r["found_le"],
                "data": data,
            })

    for hw, entries in sorted(by_hw.items()):
        if len(entries) < 2:
            continue

        print(f"\n--- HW {hw} (n={len(entries)} fajlova) ---")

        # Za svaku poznatu adresu, provjeri koje adrese se mijenjaju između fajlova
        # Uzmi par fajlova i usporedi bajt po bajt na regijama blizu odometar adresa

        # Odaberi max 3 fajla za usporedbu
        sample = entries[:3]
        print(f"  Uspoređujem: {[e['name'] for e in sample]}")

        # Nađi zajednički set adresa
        common_addrs = set(sample[0]["addrs"])
        for e in sample[1:]:
            common_addrs &= set(e["addrs"])

        if not common_addrs:
            print(f"  Nema zajedničkih adresa — svaki fajl ima različite adrese")
            # Analiziraj raspon
            for e in sample:
                print(f"  {e['name']}: {e['minutes']} min @ {[hex(a) for a in e['addrs']]}")
        else:
            print(f"  Zajedničke adrese: {[hex(a) for a in sorted(common_addrs)]}")


# ─────────────────────────────────────────────────────────────────────────────
# Scan za circular buffer pattern u jednom fajlu
# ─────────────────────────────────────────────────────────────────────────────

def scan_eeprom_regions(data: bytes, hw_type: str = "???"):
    """
    Scan EEPROM i identificiraj regije s repeating patterns
    koje izgledaju kao circular buffer (isti stride, sličan sadržaj).
    """
    results = {}

    # Strategija 1: Nađi sve u16 LE u rasponu 100-100000 (razumne minute)
    candidates = []
    for i in range(0, len(data)-1, 2):
        v = struct.unpack_from("<H", data, i)[0]
        if 100 <= v <= 100000:
            candidates.append((i, v))

    results["u16_odo_candidates"] = candidates[:50]

    # Strategija 2: Nađi repeating patterns (stride analiza)
    # Uzmi par uzastopnih "razumnih" vrijednosti i provjeri stride
    if len(candidates) >= 4:
        addr_list = [c[0] for c in candidates[:20]]
        strides = [addr_list[i+1] - addr_list[i] for i in range(len(addr_list)-1)]
        results["stride_analysis"] = strides

    return results


# ─────────────────────────────────────────────────────────────────────────────
# EepromParser stub
# ─────────────────────────────────────────────────────────────────────────────

def generate_eeprom_parser(findings):
    """Na osnovu nalaza generiraj EepromParser.find_odo_minutes() implementaciju."""

    template = '''
class EepromParser:
    """
    Parser za Sea-Doo Bosch ME17.8.5 EEPROM (32KB).
    Identificira odometar (minute) iz circular buffer-a.

    HW tipovi:
      062 = MPEM 1037509210 / 1037525858 (GTI, RXT 1.5L)
      063 = MPEM 1037525858 (Spark 90hp)
      064 = MPEM 1037550003 (RXP-X 300, GTI SE 155)
    """

    EEPROM_SIZE = 0x8000  # 32KB

    # Circular buffer parametri po HW tipu
    # NAPOMENA: ažurirati nakon analize!
    BUFFER_CONFIG = {
        "062": {
            "start": 0x0500,    # TODO: verificirati
            "end":   0x1600,    # TODO: verificirati
            "stride": 0x80,     # TODO: verificirati
            "slots": 34,        # TODO: verificirati
        },
        "063": {
            "start": 0x0B00,    # TODO: verificirati
            "end":   0x0C00,    # Spark ima manji buffer?
            "stride": 0x14,     # TODO: verificirati
            "slots": 8,         # TODO: verificirati
        },
        "064": {
            "start": 0x0500,    # Poznato: 0x0562, 0x0D62, 0x0DE2, 0x1562
            "end":   0x1600,
            "stride": 0x80,     # TODO: verificirati (0x0D62-0x0562=0x800 / 16 slotova?)
            "slots": 34,        # TODO: verificirati
        },
    }

    # HW timer lokacija (nepromjenjiva)
    HW_TIMER_OFFSET = 0x0125
    HW_TIMER_LEN = 5  # 5 ASCII znakova

    @classmethod
    def detect_hw_type(cls, data: bytes) -> str:
        """
        Detektiraj HW tip iz EEPROM-a.
        TODO: implementirati na osnovu MPEM ID-a ili karakterističnih
        magic bajtova u EEPROM-u.
        """
        # Placeholder — treba identificirati MPEM ID lokaciju
        return "064"  # default

    @classmethod
    def find_odo_minutes(cls, data: bytes, hw_type: str = None) -> int | None:
        """
        Pronađi odometar u minutama iz circular buffera.

        Returns:
            int: odometar u minutama, ili None ako nije pronađen
        """
        if len(data) < cls.EEPROM_SIZE:
            return None

        if hw_type is None:
            hw_type = cls.detect_hw_type(data)

        cfg = cls.BUFFER_CONFIG.get(hw_type)
        if cfg is None:
            return None

        # Scan circular buffer regije
        best_addr = None
        best_val = None
        best_counter = -1

        stride = cfg["stride"]
        start = cfg["start"]
        end = cfg["end"]

        # Strategija: pronađi slot s najvećim "counter" vrijednošću
        # ili zadnji napisani slot (wraparound detekcija)
        # TODO: implementirati pravi algoritam nakon identifikacije counter-a

        # Trenutna fallback strategija: scan sve u16 LE u regiji
        import struct
        candidates = []
        for offset in range(start, min(end, len(data)-1), 2):
            val = struct.unpack_from("<H", data, offset)[0]
            if 1 <= val <= 100000:  # razumne minute (max ~1666h)
                candidates.append((offset, val))

        if not candidates:
            return None

        # Vrati najveću vrijednost (pretpostavljamo rast odometra)
        # TODO: zamijeniti s pravim counter-based detekcijom
        return max(v for _, v in candidates)

    @classmethod
    def get_hw_timer(cls, data: bytes) -> str | None:
        """Čitaj nepromjenjivi hardware timer (5-digit ASCII @ 0x0125)."""
        try:
            return data[cls.HW_TIMER_OFFSET:cls.HW_TIMER_OFFSET + cls.HW_TIMER_LEN].decode("ascii")
        except Exception:
            return None
'''
    return template


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("ME17Suite — EEPROM Odometar Circular Buffer Analiza")
    print("Datum: 2026-03-17")
    print("="*70)

    # Sakupi sve EEPROM fajlove
    print("\nTražim EEPROM fajlove...")
    eeproms = collect_all_eeproms()
    print(f"Pronađeno {len(eeproms)} potencijalnih EEPROM fajlova")

    # Ispiši sve pronađene fajlove s parsiranim vremenom
    print("\n--- SVE PRONAĐENE DATOTEKE ---")
    for e in sorted(eeproms, key=lambda x: (x["hw_type"], x["path"].name)):
        mins_str = f"{e['total_minutes']} min ({e['hours']}h{e['minutes']}m)" if e["total_minutes"] else "nepoznato"
        print(f"  [{e['hw_type']}] {e['path'].name:40s} {e['size']:6d}B  {mins_str}")

    # Analiziraj svaki fajl
    print("\n--- ANALIZA PO FAJLU ---")
    all_results = []
    eeproms_with_data = []

    for e in eeproms:
        data = load_eeprom(e["path"])
        if data is None:
            print(f"  GREŠKA čitanja: {e['path']}")
            continue

        r = analyze_eeprom(e["path"], e["total_minutes"], e["hw_type"])
        all_results.append(r)
        eeproms_with_data.append({"result": r, "data": data, "entry": e})

        if r["expected_minutes"] is not None:
            found_str = f"LE @ {[hex(a) for a in r['found_le']]}" if r["found_le"] else "NIJE PRONAĐENO"
            be_str = f", BE @ {[hex(a) for a in r['found_be']]}" if r["found_be"] else ""
            print(f"  [{e['hw_type']}] {e['path'].name:40s} {r['expected_minutes']:6d} min  → {found_str}{be_str}")
        else:
            print(f"  [{e['hw_type']}] {e['path'].name:40s} (bez poznatih sati u imenu)")

    # Pattern analiza
    analyze_circular_buffer_pattern(all_results)

    # Deep context analiza
    deep_circular_analysis(eeproms_with_data)

    # Traženje aktivnog slot indexa
    find_active_slot_index(eeproms_with_data)

    # Rezime "neočekivanih" fajlova
    print("\n" + "="*70)
    print("NEOČEKIVANE VRIJEDNOSTI")
    print("="*70)
    for entry in eeproms_with_data:
        r = entry["result"]
        if r["expected_minutes"] and not r["found_le"] and not r["found_be"]:
            print(f"  NIJE PRONAĐENO: {r['name']} ({r['expected_minutes']} min)")
        if r["magic_hits"]:
            for magic, hits in r["magic_hits"]:
                print(f"  MAGIC 0x{magic:04X} u {r['name']}: @ {[hex(h) for h in hits]}")

    # Prijedlog EepromParser-a
    print("\n" + "="*70)
    print("EEPROMPARSER PRIJEDLOG")
    print("="*70)
    parser_code = generate_eeprom_parser({})
    print(parser_code)

    print("\n=== ANALIZA ZAVRŠENA ===")


if __name__ == "__main__":
    main()
