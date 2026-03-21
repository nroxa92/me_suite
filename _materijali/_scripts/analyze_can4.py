#!/usr/bin/env python3
"""
ME17Suite — CAN Analiza Round 3
Fokus: 0x122, 0x316 (novi IDs), counter struktura, 0x342 dekodacija, 0x4CD checksum
"""
import sys
import csv
import collections
import math
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
TOOLS_DIR = Path(__file__).parent

def load_id(path, target_id, max_rows=2000):
    rows, ts = [], []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                if int(row['id_hex'], 16) != target_id:
                    continue
            except:
                continue
            rows.append([int(x,16) for x in row['data_hex'].strip().split()])
            ts.append(float(row['timestamp']))
            if len(rows) >= max_rows:
                break
    return rows, ts

def xor_all(b):
    r = 0
    for x in b: r ^= x
    return r

# ============================================================
# 0x122 — NOVO u live2! Nije u live (066726)!
# ============================================================
print("="*70)
print("0x122 — NOVI ID u live2 (053727) — KLASTER/SAT PORUKA?")
print("="*70)

data_122, ts_122 = load_id(TOOLS_DIR/'sniff_live2.csv', 0x122, 500)
print(f"Uzoraka: {len(data_122)}")
if data_122:
    import statistics
    if len(ts_122) > 2:
        diffs = [ts_122[i+1]-ts_122[i] for i in range(len(ts_122)-1) if 0 < ts_122[i+1]-ts_122[i] < 0.5]
        if diffs:
            avg_ms = statistics.mean(diffs)*1000
            print(f"Timing: {avg_ms:.1f}ms (~{1000/avg_ms:.0f}Hz)")

    # Varijabilnost
    parsed = data_122[:200]
    dlc = len(parsed[0])
    print(f"DLC: {dlc}")
    for bi in range(dlc):
        vals = [p[bi] for p in parsed if len(p) > bi]
        unique = sorted(set(vals))
        if len(unique) == 1:
            print(f"  byte[{bi}]: CONST 0x{unique[0]:02X} ({unique[0]})")
        else:
            print(f"  byte[{bi}]: {len(unique)} uniq, min=0x{min(unique):02X} max=0x{max(unique):02X}")

    print("\nPrvih 20 uzoraka:")
    for p in parsed[:20]:
        print(f"  {' '.join(f'{b:02X}' for b in p)}")

    # RPM dekodacija pokušaj
    print("\nDekodacija (prvih 10):")
    for p in parsed[:10]:
        # byte[0:2] i byte[4:6] su varijabilni
        rpm_0 = ((p[0]<<8)|p[1]) * 0.25
        rpm_4 = ((p[4]<<8)|p[5]) * 0.25
        # byte[2:4] i byte[6:8]
        v23 = (p[2]<<8)|p[3]
        v67 = (p[6]<<8)|p[7]
        xor_check = xor_all(p[:7])
        print(f"  {' '.join(f'{b:02X}' for b in p)} | rpmA={rpm_0:.1f} rpmB={rpm_4:.1f} v23={v23} v67={v67} XOR7={xor_check:02X}")

# ============================================================
# 0x316 — NOVO u live2!
# ============================================================
print("\n" + "="*70)
print("0x316 — NOVI ID u live2 (053727)")
print("="*70)

data_316, ts_316 = load_id(TOOLS_DIR/'sniff_live2.csv', 0x316, 500)
print(f"Uzoraka: {len(data_316)}")
if data_316:
    if len(ts_316) > 2:
        diffs = [ts_316[i+1]-ts_316[i] for i in range(len(ts_316)-1) if 0 < ts_316[i+1]-ts_316[i] < 0.5]
        if diffs:
            avg_ms = statistics.mean(diffs)*1000
            print(f"Timing: {avg_ms:.1f}ms (~{1000/avg_ms:.0f}Hz)")

    parsed = data_316[:200]
    dlc = len(parsed[0])
    print(f"DLC: {dlc}")
    for bi in range(dlc):
        vals = [p[bi] for p in parsed if len(p) > bi]
        unique = sorted(set(vals))
        if len(unique) == 1:
            print(f"  byte[{bi}]: CONST 0x{unique[0]:02X} ({unique[0]})")
        else:
            print(f"  byte[{bi}]: {len(unique)} uniq, min=0x{min(unique):02X} max=0x{max(unique):02X}")

    print("\nPrvih 20 uzoraka:")
    for p in parsed[:20]:
        v01 = (p[0]<<8)|p[1]
        v23 = (p[2]<<8)|p[3]
        v45 = (p[4]<<8)|p[5]
        v67 = (p[6]<<8)|p[7]
        rpm_01 = v01 * 0.25
        print(f"  {' '.join(f'{b:02X}' for b in p)} | v01={v01}({rpm_01:.1f}RPM?) v23={v23} v45={v45} v67={v67}")

# ============================================================
# 0x342 — Q15 dekodacija pokušaj
# ============================================================
print("\n" + "="*70)
print("0x342 — Q15/Q8 DEKODACIJA POKUŠAJ")
print("="*70)
# Vrijednosti: 0x9999=39321, 0x2620=9760, 0x0107=263
# 0x9999 / 32768 = 1.2 (Q15? možda lambda/AFR)
# 0x2620 / 32768 = 0.298
# 0x0107 / 32768 = 0.008
#
# Ili kao percentage: 0x9999 = 60% (hex frakcija?)
# 0x99 = 9.9 * 10 = 99? BCD?
#
# Integer rPM? 0x2620=9760/4=2440 RPM? engine off = ne
#
# Throttle position? 0x9999/0xFFFF = 60%? Da, 0x9999 = ~60%
# 0x2620/0xFFFF = ~14.8%
# 0x0107/0xFFFF = ~0.4%
# 0xD6AA (max seen) / 0xFFFF = ~84%?

vals_342 = [0x0107, 0x0122, 0x0222, 0x1550, 0x1619, 0x1621, 0x2620, 0xC129, 0x9999, 0x99AA]
print("Pokušaji dekodacije 0x342 byte[2:4] (u16BE):")
print(f"{'Value':<10} {'Q15/32768':<12} {'%/65535':<12} {'/10':<8} {'/100':<8} {'sqrt':<10}")
for v in vals_342:
    q15 = v / 32768.0
    pct = v / 65535.0 * 100
    div10 = v / 10.0
    div100 = v / 100.0
    sqrtv = math.sqrt(v)
    print(f"0x{v:04X}={v:<5} {q15:<12.4f} {pct:<12.2f}% {div10:<8.1f} {div100:<8.2f} {sqrtv:<10.2f}")

# Nota: 0x9999 = 39321 -> jako blizu 0x8000*1.2 = Q15 signed = -0.8?
# Ili UNSIGNED Q15: 39321/32768 = 1.2 (nije moguće za Q15)
# 0x9999 kao signed i16: -26215 / 32768 = -0.8
# 0x9999 kao BCD: 9 9 9 9 -> 99.99?
print("\n0x9999 analiza:")
print(f"  0x9999 = {0x9999} decimal")
print(f"  kao signed i16: {0x9999 - 0x10000 if 0x9999 > 0x7FFF else 0x9999}")
print(f"  BCD: {(0x9999>>12)&0xF}{(0x9999>>8)&0xF}.{(0x9999>>4)&0xF}{0x9999&0xF}")
print(f"  % od 0xFFFF: {0x9999/0xFFFF*100:.2f}%")
print(f"  / 256 (Q8): {0x9999/256.0:.2f}")

# ============================================================
# 0x4CD — checksum analiza detaljno
# ============================================================
print("\n" + "="*70)
print("0x4CD — CHECKSUM ANALIZA")
print("="*70)
# Unikátni frami:
# F0 AA 00 2C 00 00 00 00
# F0 AA 00 29 00 00 00 00
# F0 BB 00 29 00 00 00 00
# 00 03 03 04 20 02 01 18
# 00 02 02 04 02 02 01 19
# 00 02 02 04 02 02 01 22

# Tip 1: F0 XX 00 YY 00 00 00 00
# F0 = ?; XX = 0xAA ili 0xBB; YY = 0x2C ili 0x29
# Tip 2: 00 ZZ ZZ 04 WW 02 01 SUM
# Za tip 2:
frames = [
    [0x00, 0x03, 0x03, 0x04, 0x20, 0x02, 0x01, 0x18],
    [0x00, 0x02, 0x02, 0x04, 0x02, 0x02, 0x01, 0x19],
    [0x00, 0x02, 0x02, 0x04, 0x02, 0x02, 0x01, 0x22],
]
print("Tip 2 frami (00 XX XX 04 YY 02 01 CS?):")
for f in frames:
    xor7 = xor_all(f[:7])
    add7 = sum(f[:7]) & 0xFF
    add7_inv = (~sum(f[:7])) & 0xFF
    cs = f[7]
    print(f"  {' '.join(f'{b:02X}' for b in f)} | XOR(0:7)={xor7:02X} ADD(0:7)={add7:02X} ~ADD={add7_inv:02X} | CS={cs:02X}")
    # Provjeri više kombinacija
    for mask in range(8):
        included = [f[i] for i in range(8) if (mask >> i) & 1 == 0 or i == 7]
    # Razlika između framova
    print(f"    byte[4]=0x{f[4]:02X}, byte[7]=0x{f[7]:02X}")

# Nota: 0x18+0x04+0x01+0x03+0x03+0x02 = 0x2B... nope
# 0x18 XOR raznih: provjeri
for f in frames:
    # Provjeri različite range checksume
    results = []
    for start in range(7):
        for end in range(start+1, 8):
            xor_r = xor_all(f[start:end])
            if xor_r == f[7]:
                results.append(f"XOR[{start}:{end}]")
            add_r = sum(f[start:end]) & 0xFF
            if add_r == f[7]:
                results.append(f"ADD[{start}:{end}]")
    if results:
        print(f"  Frame {' '.join(f'{b:02X}' for b in f)}: {results}")

# Tip 1 analiza
print("\nTip 1 frami (F0 XX 00 YY 00...):")
tip1 = [
    [0xF0, 0xAA, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00],
    [0xF0, 0xAA, 0x00, 0x29, 0x00, 0x00, 0x00, 0x00],
    [0xF0, 0xBB, 0x00, 0x29, 0x00, 0x00, 0x00, 0x00],
]
for f in tip1:
    xor_all_b = xor_all(f)
    xor_07 = xor_all(f[:7])
    print(f"  {' '.join(f'{b:02X}' for b in f)} | XOR(all)={xor_all_b:02X} XOR(0:7)={xor_07:02X}")
    print(f"    byte[1]: 0x{f[1]:02X} = {'AA (170)' if f[1]==0xAA else 'BB (187)'}")
    print(f"    byte[3]: 0x{f[3]:02X} = {f[3]} ({f[3]/10.0:.1f} ako *0.1?)")

# ============================================================
# Svi ID-ovi u sniff_live2.csv — je li 0x4CD klaster → ECU?
# ============================================================
print("\n" + "="*70)
print("TIMING ANALIZA 0x4CD vs broadcast (live2)")
print("="*70)

# Učitaj prvih 1000 redova da vidimo timing
with open(TOOLS_DIR/'sniff_live2.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    all_rows = []
    for i, row in enumerate(reader):
        if i >= 2000:
            break
        try:
            all_rows.append((float(row['timestamp']), int(row['id_hex'],16), row['data_hex'].strip()))
        except:
            pass

print("Prvih 30 CAN poruka (sve ID-ove):")
for ts, id_v, data in all_rows[:30]:
    tag = ""
    if id_v == 0x4CD:
        tag = " <<< KLASTER"
    print(f"  {ts:.6f} 0x{id_v:03X}: {data}{tag}")

# ============================================================
# 0x710 — BUDS2/dijagnostički heartbeat
# ============================================================
print("\n" + "="*70)
print("0x710 / 0x720 — DIJAGNOSTIČKI PROTOKOL")
print("="*70)

data_710_lv, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x710, 100)
data_720_lv, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x720, 100)
print(f"0x710 u live: {len(data_710_lv)} uzoraka")
if data_710_lv:
    for p in data_710_lv[:5]:
        print(f"  {' '.join(f'{b:02X}' for b in p)}")
print(f"0x720 u live: {len(data_720_lv)} uzoraka")
if data_720_lv:
    for p in data_720_lv[:5]:
        print(f"  {' '.join(f'{b:02X}' for b in p)}")

# 0x720 = F3 01 7E ... → 0x3E = TesterPresent response?
# 0x7E0 → 0x7E8 = ECU diagnostic (physical addressing)
# 0x7DF = functional addressing (broadcast request)
print("\n0x7DF analiza (functional addressing):")
data_7df, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x7DF, 50)
for p in data_7df[:10]:
    print(f"  {' '.join(f'{b:02X}' for b in p)}")

print("\n0x7E0 primjeri (BUDS2 → ECU):")
data_7e0, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x7E0, 100)
# Grupiraj po service ID
from collections import Counter
sids = Counter()
for p in data_7e0:
    if len(p) >= 2:
        sids[p[1]] += 1
print(f"  Service IDs: {dict(sids.most_common(10))}")
for p in data_7e0[:10]:
    print(f"  {' '.join(f'{b:02X}' for b in p)}")

print("\n0x7E8 primjeri (ECU → BUDS2):")
data_7e8, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x7E8, 100)
for p in data_7e8[:10]:
    print(f"  {' '.join(f'{b:02X}' for b in p)}")
