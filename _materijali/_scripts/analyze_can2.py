#!/usr/bin/env python3
"""
ME17Suite — CAN Broadcast Analiza
Analizira sniff_buds2.csv, sniff_live.csv, sniff_live2.csv
"""
import sys
import csv
import collections
import statistics
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

TOOLS_DIR = Path(__file__).parent
FILES = {
    'buds2': TOOLS_DIR / 'sniff_buds2.csv',
    'live':  TOOLS_DIR / 'sniff_live.csv',
    'live2': TOOLS_DIR / 'sniff_live2.csv',
}

BROADCAST_IDS = [0x102, 0x103, 0x110, 0x300, 0x308, 0x320, 0x342, 0x516]
TARGET_IDS = set(BROADCAST_IDS) | {0x4CD, 0x7E0, 0x7E8}

# --- Učitavanje ---
def load_csv(path, max_rows=None, id_filter=None):
    """Učitaj CSV, vrati {id_hex: [list of data_hex strings]}"""
    data = collections.defaultdict(list)
    ts_data = collections.defaultdict(list)
    count = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                id_val = int(row['id_hex'], 16)
            except:
                continue
            if id_filter and id_val not in id_filter:
                continue
            raw = row['data_hex'].strip()
            ts = float(row['timestamp'])
            data[id_val].append(raw)
            ts_data[id_val].append(ts)
            count += 1
            if max_rows and count >= max_rows:
                break
    return data, ts_data

def parse_bytes(hex_str):
    return [int(x, 16) for x in hex_str.split()]

def xor_all(b):
    r = 0
    for x in b:
        r ^= x
    return r

def add_all(b):
    return sum(b) & 0xFF

# --- Analiza jednog ID-a ---
def analyze_id(id_val, samples, ts_list=None, label=''):
    if not samples:
        print(f"  [NEMA PODATAKA]")
        return

    parsed = [parse_bytes(s) for s in samples[:500]]
    dlc = len(parsed[0])

    # Koji bajtovi se mijenjaju?
    const_bytes = {}
    varying_bytes = {}
    for bi in range(dlc):
        vals = [p[bi] for p in parsed if len(p) > bi]
        unique = set(vals)
        if len(unique) == 1:
            const_bytes[bi] = vals[0]
        else:
            varying_bytes[bi] = sorted(unique)

    print(f"  DLC={dlc}, Uzoraka={len(samples)}")
    print(f"  Konstantni bajtovi: { {k: f'0x{v:02X}' for k,v in const_bytes.items()} }")
    print(f"  Varijabilni bajtovi: { {k: f'{len(v)} uniq, min=0x{min(v):02X} max=0x{max(v):02X}' for k,v in varying_bytes.items()} }")

    # Timing analiza
    if ts_list and len(ts_list) > 2:
        ts = ts_list[:len(parsed)]
        diffs = [ts[i+1]-ts[i] for i in range(len(ts)-1) if ts[i+1]-ts[i] < 0.5]
        if diffs:
            avg_ms = statistics.mean(diffs) * 1000
            print(f"  Timing: avg={avg_ms:.1f}ms (~{1000/avg_ms:.0f}Hz)")

    # Checksum provjera za svaki varijabilni bajt
    if len(varying_bytes) >= 1:
        for cs_bi in varying_bytes:
            # provjeri je li XOR ostalih
            hits_xor = 0
            hits_add = 0
            for p in parsed[:100]:
                others = [p[i] for i in range(dlc) if i != cs_bi]
                if xor_all(others) == p[cs_bi]:
                    hits_xor += 1
                if add_all(others) == p[cs_bi]:
                    hits_add += 1
            if hits_xor > 90:
                print(f"  CHECKSUM: byte[{cs_bi}] = XOR(ostali) ({hits_xor}/100)")
            elif hits_add > 90:
                print(f"  CHECKSUM: byte[{cs_bi}] = ADD(ostali) ({hits_add}/100)")

    # Counter detekcija
    for bi in varying_bytes:
        vals = [p[bi] for p in parsed[:100] if len(p) > bi]
        diffs_c = [(vals[i+1] - vals[i]) % 256 for i in range(len(vals)-1)]
        if diffs_c and all(d == diffs_c[0] for d in diffs_c[:20]):
            if diffs_c[0] in (1, 2, 4, 16):
                print(f"  COUNTER: byte[{bi}] inkrement={diffs_c[0]}, range 0x{min(vals):02X}..0x{max(vals):02X}")

    # Primjeri prvih 8 uzoraka
    print(f"  Primjeri (prvih 8):")
    for s in samples[:8]:
        print(f"    {s}")

# --- 0x102 RPM/TEMP detaljna analiza ---
def analyze_0x102(samples, label):
    print(f"\n  === 0x102 Detaljna dekodacija ({label}) ===")
    parsed = [parse_bytes(s) for s in samples[:200]]
    rpm_vals = []
    temp_vals = []
    for p in parsed:
        if len(p) < 8:
            continue
        # RPM: byte[1:3] * 0.25 (big endian u16)
        rpm_raw = (p[1] << 8) | p[2]
        rpm = rpm_raw * 0.25
        # Temp: byte[3] - 40
        temp = p[3] - 40
        # Napon: byte[4] * 0.1 ili 0.0625?
        v_raw = p[4]
        v1 = v_raw * 0.1
        v2 = v_raw * 0.0625
        rpm_vals.append(rpm)
        temp_vals.append(temp)
        if len(rpm_vals) <= 5:
            print(f"    {' '.join(f'{b:02X}' for b in p)} → RPM={rpm:.1f}, Temp={temp}°C, byte4=0x{v_raw:02X}({v_raw}), byte5=0x{p[5]:02X}, byte6=0x{p[6]:02X}, byte7=0x{p[7]:02X}")

    if rpm_vals:
        print(f"  RPM range: {min(rpm_vals):.1f}..{max(rpm_vals):.1f}")
        print(f"  Temp range: {min(temp_vals)}..{max(temp_vals)}°C")

# --- 0x103 DTC analiza ---
def analyze_0x103(samples, label):
    print(f"\n  === 0x103 DTC/Status ({label}) ===")
    parsed = [parse_bytes(s) for s in samples[:200]]
    for p in parsed[:8]:
        dtc_count = p[0]
        print(f"    {' '.join(f'{b:02X}' for b in p)} → DTC_count={dtc_count}, byte[6]=0x{p[6]:02X}, byte[7]=0x{p[7]:02X}")

# --- 0x110 XOR checksum analiza ---
def analyze_0x110(samples, label):
    print(f"\n  === 0x110 System Status ({label}) ===")
    parsed = [parse_bytes(s) for s in samples[:200]]
    xor_ok = 0
    for p in parsed[:100]:
        if len(p) < 8:
            continue
        cs = xor_all(p[:7])
        if cs == p[7]:
            xor_ok += 1
    print(f"  XOR(byte[0:7]) == byte[7]: {xor_ok}/100")

    # Konstantni prikaz
    for p in parsed[:5]:
        print(f"    {' '.join(f'{b:02X}' for b in p)}")

# --- 0x516 SW identifier analiza ---
def analyze_0x516(samples_buds2, samples_live, samples_live2):
    print(f"\n  === 0x516 SW Identifier ===")

    def mode_bytes(samples):
        if not samples:
            return None
        parsed = [parse_bytes(s) for s in samples[:50]]
        result = []
        for bi in range(8):
            vals = [p[bi] for p in parsed if len(p) > bi]
            if vals:
                # najčešća vrijednost
                c = collections.Counter(vals)
                result.append(c.most_common(1)[0][0])
        return result

    b2 = mode_bytes(samples_buds2)
    lv = mode_bytes(samples_live)
    l2 = mode_bytes(samples_live2)

    print(f"  buds2 (ECU OFF): {' '.join(f'{b:02X}' for b in b2) if b2 else 'N/A'}")
    print(f"  live (066726):   {' '.join(f'{b:02X}' for b in lv) if lv else 'N/A'}")
    print(f"  live2 (053727):  {' '.join(f'{b:02X}' for b in l2) if l2 else 'N/A'}")

    if lv and l2:
        print(f"  Razlike (bit po bit):")
        for bi in range(min(len(lv), len(l2))):
            if lv[bi] != l2[bi]:
                print(f"    byte[{bi}]: 0x{lv[bi]:02X}→0x{l2[bi]:02X}  (066726→053727)")
            else:
                print(f"    byte[{bi}]: 0x{lv[bi]:02X} (isto)")

    # Pokušaj ASCII dekodacije
    if lv:
        ascii_live = ''.join(chr(b) if 32 <= b < 127 else '.' for b in lv)
        print(f"  live ASCII: '{ascii_live}'")
    if l2:
        ascii_l2 = ''.join(chr(b) if 32 <= b < 127 else '.' for b in l2)
        print(f"  live2 ASCII: '{ascii_l2}'")

# --- 0x4CD SAT/Dashboard analiza ---
def analyze_4CD(samples_live, samples_live2):
    print(f"\n  === 0x4CD SAT/Dashboard ===")
    if not samples_live and not samples_live2:
        print("  [NEMA 0x4CD PODATAKA]")
        return

    for label, samples in [('live', samples_live), ('live2', samples_live2)]:
        if not samples:
            print(f"  [{label}]: nema podataka")
            continue
        parsed = [parse_bytes(s) for s in samples[:100]]
        print(f"  [{label}]: {len(samples)} uzoraka")
        for p in parsed[:5]:
            print(f"    {' '.join(f'{b:02X}' for b in p)}")

        # Provjeri varijabilnost
        dlc = len(parsed[0])
        for bi in range(dlc):
            vals = set(p[bi] for p in parsed if len(p) > bi)
            if len(vals) > 1:
                print(f"    byte[{bi}] varijabilno: {len(vals)} uniq vrijednosti")

# --- SW usporedba ---
def sw_compare(data_live, data_live2):
    print("\n" + "="*70)
    print("SW USPOREDBA: 10SW066726 vs 10SW053727")
    print("="*70)

    all_ids = sorted(set(list(data_live.keys()) + list(data_live2.keys())))
    for id_val in all_ids:
        if id_val not in BROADCAST_IDS and id_val != 0x4CD:
            continue
        s1 = data_live.get(id_val, [])
        s2 = data_live2.get(id_val, [])
        if not s1 or not s2:
            print(f"\n0x{id_val:03X}: samo u {'live' if s1 else 'live2'} ({len(s1) or len(s2)} uzoraka)")
            continue

        p1 = [parse_bytes(s) for s in s1[:200]]
        p2 = [parse_bytes(s) for s in s2[:200]]

        dlc = min(len(p1[0]), len(p2[0]))
        print(f"\n0x{id_val:03X}:")

        for bi in range(dlc):
            v1 = collections.Counter(p[bi] for p in p1 if len(p) > bi)
            v2 = collections.Counter(p[bi] for p in p2 if len(p) > bi)
            m1 = v1.most_common(1)[0][0]
            m2 = v2.most_common(1)[0][0]
            if m1 != m2:
                print(f"  byte[{bi}]: 0x{m1:02X}({m1}) → 0x{m2:02X}({m2})  *** RAZLIKA ***")
            else:
                # provjeri raspon
                u1 = len(v1)
                u2 = len(v2)
                if abs(u1-u2) > 5:
                    print(f"  byte[{bi}]: uniq_live={u1} uniq_live2={u2} (rasponi se razlikuju)")

# --- Klaster heartbeat identifikacija ---
def identify_cluster_frames(data_live, data_live2, ts_live, ts_live2):
    print("\n" + "="*70)
    print("KLASTER HEARTBEAT IDENTIFIKACIJA")
    print("="*70)

    known_ecu = set(BROADCAST_IDS)
    known_diag = {0x7E0, 0x7E8}

    print("\nSvi ID-ovi u sniff_live.csv (osim broadcast+diag):")
    for id_val in sorted(data_live.keys()):
        if id_val in known_ecu or id_val in known_diag:
            continue
        samples = data_live[id_val]
        p = parse_bytes(samples[0])
        print(f"  0x{id_val:03X}: {len(samples)} uzoraka | primjer: {' '.join(f'{b:02X}' for b in p)}")

    print("\nSvi ID-ovi u sniff_live2.csv (osim broadcast+diag):")
    for id_val in sorted(data_live2.keys()):
        if id_val in known_ecu or id_val in known_diag:
            continue
        samples = data_live2[id_val]
        p = parse_bytes(samples[0])
        print(f"  0x{id_val:03X}: {len(samples)} uzoraka | primjer: {' '.join(f'{b:02X}' for b in p)}")

# --- Glavna analiza ---
def main():
    print("="*70)
    print("ME17Suite — CAN Broadcast Analiza")
    print("="*70)

    print("\nUčitavam sniff_buds2.csv...")
    data_b2, ts_b2 = load_csv(FILES['buds2'], id_filter=TARGET_IDS)
    print(f"  Učitano: {sum(len(v) for v in data_b2.values())} redova")

    print("Učitavam sniff_live.csv (prvih 300k redova)...")
    data_lv, ts_lv = load_csv(FILES['live'], max_rows=300000, id_filter=TARGET_IDS)
    print(f"  Učitano: {sum(len(v) for v in data_lv.values())} relevantnih redova")

    print("Učitavam sniff_live2.csv (prvih 300k redova)...")
    data_l2, ts_l2 = load_csv(FILES['live2'], max_rows=300000, id_filter=TARGET_IDS)
    print(f"  Učitano: {sum(len(v) for v in data_l2.values())} relevantnih redova")

    # --- SEKCIJA 1: sniff_buds2 analiza (ECU OFF, čisti broadcast) ---
    print("\n" + "="*70)
    print("SEKCIJA 1: sniff_buds2.csv — ECU OFF, čisti broadcast")
    print("="*70)

    for id_val in BROADCAST_IDS:
        samples = data_b2.get(id_val, [])
        ts = ts_b2.get(id_val, [])
        print(f"\n--- ID 0x{id_val:03X} ({len(samples)} uzoraka) ---")
        analyze_id(id_val, samples, ts, 'buds2')

    # Detaljna dekodacija
    analyze_0x102(data_b2.get(0x102, []), 'buds2')
    analyze_0x103(data_b2.get(0x103, []), 'buds2')
    analyze_0x110(data_b2.get(0x110, []), 'buds2')

    # --- SEKCIJA 2: sniff_live analiza ---
    print("\n" + "="*70)
    print("SEKCIJA 2: sniff_live.csv — ECU živ (10SW066726)")
    print("="*70)

    for id_val in BROADCAST_IDS:
        samples = data_lv.get(id_val, [])
        ts = ts_lv.get(id_val, [])
        print(f"\n--- ID 0x{id_val:03X} ({len(samples)} uzoraka) ---")
        analyze_id(id_val, samples, ts, 'live')

    analyze_0x102(data_lv.get(0x102, []), 'live')
    analyze_0x103(data_lv.get(0x103, []), 'live')
    analyze_0x110(data_lv.get(0x110, []), 'live')

    # --- SEKCIJA 3: sniff_live2 ---
    print("\n" + "="*70)
    print("SEKCIJA 3: sniff_live2.csv — ECU živ (10SW053727 / flash)")
    print("="*70)

    for id_val in BROADCAST_IDS:
        samples = data_l2.get(id_val, [])
        ts = ts_l2.get(id_val, [])
        print(f"\n--- ID 0x{id_val:03X} ({len(samples)} uzoraka) ---")
        analyze_id(id_val, samples, ts, 'live2')

    analyze_0x102(data_l2.get(0x102, []), 'live2')
    analyze_0x103(data_l2.get(0x103, []), 'live2')
    analyze_0x110(data_l2.get(0x110, []), 'live2')

    # --- SEKCIJA 4: 0x516 usporedba ---
    print("\n" + "="*70)
    print("SEKCIJA 4: 0x516 SW Identifier analiza")
    print("="*70)
    analyze_0x516(
        data_b2.get(0x516, []),
        data_lv.get(0x516, []),
        data_l2.get(0x516, [])
    )

    # --- SEKCIJA 5: 0x4CD SAT/Dashboard ---
    print("\n" + "="*70)
    print("SEKCIJA 5: 0x4CD SAT/Dashboard analiza")
    print("="*70)
    analyze_4CD(data_lv.get(0x4CD, []), data_l2.get(0x4CD, []))

    # --- SEKCIJA 6: SW usporedba ---
    sw_compare(data_lv, data_l2)

    # --- SEKCIJA 7: Klaster heartbeat identifikacija ---
    identify_cluster_frames(data_lv, data_l2, ts_lv, ts_l2)

    # --- SEKCIJA 8: 0x320 i 0x342 detaljna analiza ---
    print("\n" + "="*70)
    print("SEKCIJA 8: 0x320 i 0x342 detaljna analiza (live)")
    print("="*70)

    for id_val in [0x320, 0x342]:
        samples = data_lv.get(id_val, [])
        print(f"\n0x{id_val:03X} prvih 20 uzoraka (live):")
        for s in samples[:20]:
            print(f"  {s}")

    # --- SEKCIJA 9: 0x308 detaljna ---
    print("\n" + "="*70)
    print("SEKCIJA 9: 0x308 Sensor Flags (sve 3 datoteke)")
    print("="*70)
    for label, data in [('buds2', data_b2), ('live', data_lv), ('live2', data_l2)]:
        samples = data.get(0x308, [])
        if samples:
            parsed = [parse_bytes(s) for s in samples[:100]]
            print(f"\n{label}: {len(samples)} uzoraka")
            # Prikaži sve unikátne vrijednosti
            unique = set(tuple(p) for p in parsed)
            print(f"  Uniq frami: {len(unique)}")
            for u in sorted(unique)[:10]:
                print(f"    {' '.join(f'{b:02X}' for b in u)}")

if __name__ == '__main__':
    main()
