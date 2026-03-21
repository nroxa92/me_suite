#!/usr/bin/env python3
"""
ME17Suite — CAN Detaljna analiza (round 2)
Fokus: 0x342, 0x320, 0x102 dekodacija, 0x4CD, 0x516, checksum relacije
"""
import sys
import csv
import collections
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

TOOLS_DIR = Path(__file__).parent

def load_id(path, target_id, max_rows=None):
    rows = []
    ts_list = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                id_val = int(row['id_hex'], 16)
            except:
                continue
            if id_val != target_id:
                continue
            raw = row['data_hex'].strip()
            rows.append([int(x,16) for x in raw.split()])
            ts_list.append(float(row['timestamp']))
            if max_rows and len(rows) >= max_rows:
                break
    return rows, ts_list

def xor_all(b):
    r = 0
    for x in b: r ^= x
    return r

# ============================================================
# 0x102: dekodacija RPM, Temp, Voltage, Counter
# ============================================================
print("="*70)
print("0x102 DETALJNA DEKODACIJA")
print("="*70)

# Format koji vidimo: 00 00 80 14 14 CA XX YY
# byte[0:2] = uvijek 0x00 0x00
# byte[2] = 0x80 (možda high RPM nibble?)
# byte[3] = 0x14 = 20 (temp offset?)
# byte[4] = 0x14 ili 0x0E (SW razlika!)
# byte[5] = 0xCA = 202
# byte[6] = counter 0..F
# byte[7] = varijabilno

# Provjera: RPM = (byte[1]<<8 | byte[2]) * 0.25
# 0x0080 * 0.25 = 32 RPM — ima smisla za ECU na stolu (idle-off cranking)

print("\nformat analiza za live (066726) 10 uzoraka:")
data_live, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x102, 50)
for p in data_live[:10]:
    rpm = ((p[1]<<8)|p[2]) * 0.25
    temp = p[3] - 40
    # byte[4] — možda napon? 0x14=20 -> 20*0.5=10V? ili 20*0.6=12V?
    v14 = p[4] * 0.5   # 20*0.5 = 10.0V
    v14b = p[4] * 0.6  # 20*0.6 = 12.0V
    v14c = p[4] * 0.625 # 20*0.625 = 12.5V
    # byte[5] 0xCA=202 -> 202*0.1=20.2? ili temperatura? 202-40=162°C? nope
    # možda napon*10? 202*0.1=20.2V nope. ili kombinacija?
    print(f"  {' '.join(f'{b:02X}' for b in p)} | RPM={rpm:.1f} Temp={temp}°C b4*0.5={v14:.1f}V b4*0.625={v14c:.1f}V b5=0x{p[5]:02X}({p[5]})")

print("\nformat analiza za live2 (053727) 10 uzoraka:")
data_l2, _ = load_id(TOOLS_DIR/'sniff_live2.csv', 0x102, 50)
for p in data_l2[:10]:
    rpm = ((p[1]<<8)|p[2]) * 0.25
    temp = p[3] - 40
    v14c = p[4] * 0.625
    print(f"  {' '.join(f'{b:02X}' for b in p)} | RPM={rpm:.1f} Temp={temp}°C b4*0.625={v14c:.1f}V b5=0x{p[5]:02X}({p[5]})")

# Checksum analiza za byte[7] kad se zna šta su ostali
print("\n0x102 checksum analiza byte[7]:")
for p in data_live[:10]:
    xor6 = xor_all(p[:6])
    xor7 = xor_all(p[:7])
    b6 = p[6]
    b7 = p[7]
    print(f"  byte[6..7]={b6:02X} {b7:02X} | XOR(0:6)={xor6:02X} | XOR(0:7)={xor7:02X} | b6^b7={b6^b7:02X}")

# ============================================================
# 0x342 detaljna analiza — što je u byte[2:4]?
# ============================================================
print("\n" + "="*70)
print("0x342 DETALJNA DEKODACIJA — byte[2:4]")
print("="*70)
# Format: 00 00 XX YY 78 00 00 00
# byte[4] = 0x78 = 120 uvijek (u live i live2)
# byte[2:4] = varijabilni, 16-bit BE value?

data_342, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x342, 300)
print("\nlive (066726) prvih 30 uzoraka s dekodacijom:")
vals_16 = []
for p in data_342[:30]:
    val_be = (p[2]<<8)|p[3]
    val_le = (p[3]<<8)|p[2]
    # Možda temperature*256? ili napon?
    # 0x2620 = 9760 BE
    # Tražimo smislene vrijednosti
    as_temp = val_be / 256.0 - 40  # Q8 temp encoding
    as_volt = val_be / 4096.0 * 5  # ADC 12bit → 5V
    as_volt2 = val_be * 0.001  # mV → V (npr 9.76V ako je 9760)
    vals_16.append(val_be)
    print(f"  {' '.join(f'{b:02X}' for b in p)} | u16BE={val_be} u16LE={val_le} | /256-40={as_temp:.1f} | *0.001={as_volt2:.3f}")

print(f"\n  Sve unikátne u16BE vrijednosti (live):")
unique_342 = sorted(set(vals_16))
for v in unique_342:
    print(f"    0x{v:04X} = {v}  (Q8/256={v/256.0-40:.2f}°C?, /100={v/100.0:.2f}?, sqrt_ish)")

print("\nlive2 (053727) prvih 20 uzoraka:")
data_342_l2, _ = load_id(TOOLS_DIR/'sniff_live2.csv', 0x342, 200)
for p in data_342_l2[:20]:
    val_be = (p[2]<<8)|p[3]
    print(f"  {' '.join(f'{b:02X}' for b in p)} | u16BE={val_be}")

# ============================================================
# 0x320 detaljna analiza
# ============================================================
print("\n" + "="*70)
print("0x320 DETALJNA DEKODACIJA")
print("="*70)
# live:  00 FE 00 00 60 FE 80 00
# live2: 00 00 00 00 F0 00 82 00
# byte[1]=0xFE, byte[5]=0xFE u live — što znači 0xFE=254?
# 0xFE se često koristi kao "not available" / "sensor error" u CAN

print("live: 00 FE 00 00 60 FE 80 00")
print("  byte[1]=0xFE=254 — vjerovatno 'N/A' ili max sensor value")
print("  byte[4]=0x60=96")
print("  byte[5]=0xFE=254 — vjerovatno 'N/A'")
print("  byte[6]=0x80=128")

print("\nlive2: 00 00 00 00 F0 00 82 00")
print("  byte[4]=0xF0=240")
print("  byte[6]=0x82=130")

# Moguće dekodacije za byte[4]:
# 0x60=96: temp sensor? 96-40=56°C (ambient pred pokretanje?)
# 0xF0=240: 240-40=200°C? Nema smisla
# ili napon: 96*0.0625=6.0V? 96/10=9.6V? 96*0.15=14.4V?
# 0x60 * 0.15 = 14.4V (napon punjenja)? Ali off na stolu...
print("\nSpekulacija byte[4]:")
for v in [0x60, 0xF0]:
    print(f"  0x{v:02X}={v}: /10={v/10.0:.1f}V?, *0.0625={v*0.0625:.2f}?, -40={v-40}°C?, *0.15={v*0.15:.2f}V?")

# ============================================================
# 0x4CD — SAT/Dashboard analiza
# ============================================================
print("\n" + "="*70)
print("0x4CD SAT/DASHBOARD DETALJNA ANALIZA")
print("="*70)

data_4cd, ts_4cd = load_id(TOOLS_DIR/'sniff_live2.csv', 0x4CD, 500)
print(f"Ukupno {len(data_4cd)} uzoraka u live2")

if data_4cd:
    # Timing
    if len(ts_4cd) > 5:
        import statistics
        diffs = [ts_4cd[i+1]-ts_4cd[i] for i in range(len(ts_4cd)-1) if ts_4cd[i+1]-ts_4cd[i] < 2.0]
        if diffs:
            avg_ms = statistics.mean(diffs)*1000
            print(f"Timing: avg={avg_ms:.1f}ms (~{1000/avg_ms:.0f}Hz)")

    # Sve unikátne vrijednosti
    unique_4cd = list({tuple(p) for p in data_4cd})
    print(f"Unikátni frami ({len(unique_4cd)}):")
    for u in sorted(unique_4cd):
        print(f"  {' '.join(f'{b:02X}' for b in u)}")

    # Checksum provjera
    print("\nChecksum provjere:")
    for p in data_4cd[:20]:
        xors = [xor_all(p[:i]) for i in range(1,9)]
        adds = [sum(p[:i])&0xFF for i in range(1,9)]
        print(f"  {' '.join(f'{b:02X}' for b in p)}")

    # Analiza po tipu frema (alterniraju li se?)
    print("\nPrvih 20 uzoraka s indeksom:")
    for i, p in enumerate(data_4cd[:20]):
        print(f"  [{i:3d}] {' '.join(f'{b:02X}' for b in p)}")

    # Grupe po byte[0] (F0 vs 00)
    group_f0 = [p for p in data_4cd if p[0] == 0xF0]
    group_00 = [p for p in data_4cd if p[0] == 0x00]
    print(f"\nbyte[0]=0xF0: {len(group_f0)} uzoraka")
    print(f"byte[0]=0x00: {len(group_00)} uzoraka")
    if group_f0:
        print(f"  0xF0 primjer: {' '.join(f'{b:02X}' for b in group_f0[0])}")
    if group_00:
        print(f"  0x00 primjer: {' '.join(f'{b:02X}' for b in group_00[0])}")

# ============================================================
# 0x516 dekodacija — što znači 20 1C 81 2C 32 31 4A 42?
# ============================================================
print("\n" + "="*70)
print("0x516 SW IDENTIFIER DEKODACIJA")
print("="*70)
# 20 1C 81 2C 32 31 4A 42
# ASCII: 0x32='2', 0x31='1', 0x4A='J', 0x42='B'
# 32 31 = "21" — ovo je 2021 model year?
# 4A 42 = "JB" — Bosch? ili "JumpBrp"?
# 20 = 32 decimal
# 1C = 28 decimal
# 81 = 129
# 2C = 44
# Ili BCD dekodacija?
val = [0x20, 0x1C, 0x81, 0x2C, 0x32, 0x31, 0x4A, 0x42]
print(f"Raw: {' '.join(f'{b:02X}' for b in val)}")
print(f"Decimal: {val}")
print(f"ASCII (printable): {''.join(chr(b) if 32<=b<127 else '.' for b in val)}")
print(f"BCD decode: {''.join(f'{(b>>4)}{b&0xF}' for b in val)}")
print(f"uint32[0]: 0x{(val[0]<<24|val[1]<<16|val[2]<<8|val[3]):08X} = {val[0]<<24|val[1]<<16|val[2]<<8|val[3]}")
print(f"uint32[1]: 0x{(val[4]<<24|val[5]<<16|val[6]<<8|val[7]):08X} = {val[4]<<24|val[5]<<16|val[6]<<8|val[7]}")
# 10SW066726 u SW string
print(f"SW 10SW066726 u binarnom: 10={10:#04x} SW={'SW'.encode().hex()}")
# Usporedi s 10SW053727 koji je u live2 — ali 0x516 je ISTI?!
print("NOTE: 0x516 je ISTI za obje SW verzije! To nije SW version string.")
print("  Možda je HW identifier ili protocol version?")

# ============================================================
# 0x103 counter i DTC analiza
# ============================================================
print("\n" + "="*70)
print("0x103 COUNTER ANALIZA")
print("="*70)
data_103_live, _ = load_id(TOOLS_DIR/'sniff_live.csv', 0x103, 100)
# byte[6] i byte[7] su counter i nešto
# byte[6] = 0..F (counter mod 16)
# byte[7]: u live je XOR(ostali), ali kakva relacija s byte[6]?
print("live: prvih 20")
for p in data_103_live[:20]:
    b6 = p[6]
    b7 = p[7]
    xor_0_5 = xor_all(p[:6])
    xor_0_6 = xor_all(p[:7])
    print(f"  {' '.join(f'{b:02X}' for b in p)} | XOR(0:6)={xor_0_5:02X} -> b6={b6:02X}? | XOR(0:7)={xor_0_6:02X} -> b7={b7:02X}?")

# ============================================================
# Svi IDs koji postoje u live fajlovima
# ============================================================
print("\n" + "="*70)
print("SVI CAN ID-ovi u sniff_live.csv (prvih 500k redova)")
print("="*70)
id_counts = collections.Counter()
id_samples = {}
try:
    with open(TOOLS_DIR/'sniff_live.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 500000:
                break
            try:
                id_val = int(row['id_hex'], 16)
                id_counts[id_val] += 1
                if id_val not in id_samples:
                    id_samples[id_val] = row['data_hex'].strip()
            except:
                pass
except:
    pass

for id_val, count in sorted(id_counts.items()):
    sample = id_samples.get(id_val, '')
    print(f"  0x{id_val:03X}: {count:7d} uzoraka | {sample}")

print("\n" + "="*70)
print("SVI CAN ID-ovi u sniff_live2.csv (prvih 500k redova)")
print("="*70)
id_counts2 = collections.Counter()
id_samples2 = {}
try:
    with open(TOOLS_DIR/'sniff_live2.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 500000:
                break
            try:
                id_val = int(row['id_hex'], 16)
                id_counts2[id_val] += 1
                if id_val not in id_samples2:
                    id_samples2[id_val] = row['data_hex'].strip()
            except:
                pass
except:
    pass

for id_val, count in sorted(id_counts2.items()):
    sample = id_samples2.get(id_val, '')
    print(f"  0x{id_val:03X}: {count:7d} uzoraka | {sample}")

# ============================================================
# 0x110 byte[3:5] analiza — što znači 0x25 0x01 vs 0x39 0x01?
# ============================================================
print("\n" + "="*70)
print("0x110 byte[3:5] ANALIZA — SW-specifični parametri")
print("="*70)
# live:  byte[3]=0x25=37, byte[4]=0x01=1, byte[5]=0x02=2
# live2: byte[3]=0x39=57, byte[4]=0x01=1 (ili 0), byte[5]=0x03=3
print("live (066726):  byte[3]=0x25(37), byte[4]=0x01, byte[5]=0x02")
print("live2 (053727): byte[3]=0x39(57), byte[4]=0x01, byte[5]=0x03")
print("Razlika byte[3]: 0x39-0x25 = 0x14 = 20")
print("Hipoteza: byte[3] = system state flags ili SW-dependent config")
print("  0x25 = 0b00100101, 0x39 = 0b00111001")
print(f"  bits 0x25: {0x25:08b}")
print(f"  bits 0x39: {0x39:08b}")
print(f"  XOR: {0x25^0x39:08b} = 0x{0x25^0x39:02X}")
# bit 1,4,5 se razlikuju
# byte[5]: 0x02 vs 0x03 (bit 0 razlika)
print(f"  byte[5] razlika: 0x02={0x02:08b} vs 0x03={0x03:08b} — samo bit 0!")
