"""
Analiza Spark injection mape — jednom pokreni iz me_suite foldera:
  python analyze_spark_injection.py
"""
import struct

SPARK = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali\npro_stg2_spark.bin"
ORI300 = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali\ori_300.bin"

with open(SPARK, "rb") as f:
    spark = f.read()
with open(ORI300, "rb") as f:
    ori300 = f.read()

print(f"Spark:  0x{len(spark):X} B")
print(f"ORI300: 0x{len(ori300):X} B")

def u16le(data, offset):
    return struct.unpack_from("<H", data, offset)[0]

def grid_u16le(data, offset, rows, cols):
    flat = [u16le(data, offset + i*2) for i in range(rows * cols)]
    return [flat[r*cols:(r+1)*cols] for r in range(rows)]

# ============================================================
# 1. ORI300 injection referenca
# ============================================================
print("\n" + "="*60)
print("ORI300 INJECTION @ 0x02439C (12x32 u16 LE)")
print("="*60)
g300 = grid_u16le(ori300, 0x02439C, 12, 32)
for i, row in enumerate(g300):
    print(f"  row{i:02d}: {row}")

# ============================================================
# 2. RPM os @ 0x02225C — koliko točaka?
# ============================================================
print("\n" + "="*60)
print("RPM OS @ 0x02225C")
print("="*60)
rpm_start = 0x02225C
for n in [12, 14, 16, 20, 24, 32]:
    rpms = [u16le(spark, rpm_start + i*2) for i in range(n)]
    # Provjeri monotono rastuće (RPM os mora biti sortirana)
    mono = all(rpms[i] < rpms[i+1] for i in range(n-1))
    if mono and rpms[0] > 500 and rpms[-1] < 20000:
        end = rpm_start + n*2
        print(f"  {n} točaka (mono=OK): {rpms}")
        print(f"  → Os završava @ 0x{end:06X}, podaci počinju @ 0x{end:06X}")

# ============================================================
# 3. Analiza podataka iza RPM osi (za 16-točku os → 0x02227C)
# ============================================================
print("\n" + "="*60)
print("PODACI IZA 16-TOČKE RPM OSI (@ 0x02227C)")
print("="*60)
data_start = 0x02227C
for rows, cols in [(12,16), (12,20), (16,16), (16,20), (20,16), (12,24), (20,20)]:
    g = grid_u16le(spark, data_start, rows, cols)
    flat = [v for row in g for v in row]
    mn, mx, avg = min(flat), max(flat), sum(flat)//len(flat)
    end = data_start + rows*cols*2
    if mn >= 100 and mx < 60000 and (mx-mn) > 500:
        print(f"\n  OK ({rows}x{cols}): raw={mn}-{mx}, avg={avg}, end=0x{end:06X}")
        for i, row in enumerate(g):
            print(f"    row{i:02d}: {row}")

# ============================================================
# 4. Direktna analiza 0x02225C (ako row0 = os)
# ============================================================
print("\n" + "="*60)
print("PODACI @ 0x02225C (ako je row0 os — provjeri)")
print("="*60)
for rows, cols in [(12,16), (12,20), (16,16), (16,20), (20,16), (12,24)]:
    g = grid_u16le(spark, 0x02225C, rows, cols)
    flat = [v for row in g for v in row]
    mn, mx, avg = min(flat), max(flat), sum(flat)//len(flat)
    if mn >= 100 and mx < 60000 and (mx-mn) > 500:
        print(f"  OK ({rows}x{cols}): raw={mn}-{mx}, avg={avg}")
        print(f"    row0: {g[0]}")
        print(f"    row-1: {g[-1]}")

# ============================================================
# 5. Kandidat 0x0224DC — detaljna analiza
# ============================================================
print("\n" + "="*60)
print("KANDIDAT @ 0x0224DC")
print("="*60)
for rows, cols in [(12,16), (12,20), (16,16), (16,20), (20,16), (12,24), (20,20)]:
    g = grid_u16le(spark, 0x0224DC, rows, cols)
    flat = [v for row in g for v in row]
    mn, mx, avg = min(flat), max(flat), sum(flat)//len(flat)
    end = 0x0224DC + rows*cols*2
    if mn >= 200 and mx < 60000 and (mx-mn) > 300:
        print(f"\n  OK ({rows}x{cols}): raw={mn}-{mx}, avg={avg}, end=0x{end:06X}")
        for i, row in enumerate(g):
            print(f"    row{i:02d}: {row}")

# ============================================================
# 6. Mirror provjera: 0x022E42 vs 0x023358 (offset=+0x516)
# ============================================================
print("\n" + "="*60)
print("MIRROR PROVJERA 0x022E42 vs 0x023358 (offset=+0x516)")
print("="*60)
A = 0x022E42
B = 0x023358
size = 0x516  # pretpostavljeni mirror offset = veličina bloka?
# Pokušaj s manjim veličinama
for n in [128, 256, 512, 640, 768, 1024]:
    blokA = spark[A:A+n]
    blokB = spark[B:B+n]
    razlike = sum(1 for x, y in zip(blokA, blokB) if x != y)
    print(f"  n={n}: razlike={razlike}/{n} ({100*razlike/n:.1f}%)")

# ============================================================
# 7. Hex dump oko 0x022E42 i 0x023358
# ============================================================
print("\n" + "="*60)
print("HEX DUMP 0x022E00-0x022F00")
print("="*60)
for addr in range(0x022E00, 0x022F00, 0x10):
    raw = spark[addr:addr+16]
    vals = [u16le(raw, i*2) for i in range(8)]
    hex_str = ' '.join(f'{b:02X}' for b in raw)
    if any(100 <= v < 60000 for v in vals):
        print(f"  0x{addr:06X}: {hex_str} | {vals}")

print("\n" + "="*60)
print("HEX DUMP 0x023300-0x023400")
print("="*60)
for addr in range(0x023300, 0x023400, 0x10):
    raw = spark[addr:addr+16]
    vals = [u16le(raw, i*2) for i in range(8)]
    hex_str = ' '.join(f'{b:02X}' for b in raw)
    if any(100 <= v < 60000 for v in vals):
        print(f"  0x{addr:06X}: {hex_str} | {vals}")

# ============================================================
# 8. Širi scan od 0x022000-0x026000 za injection-like blokove
# ============================================================
print("\n" + "="*60)
print("ŠIRI SCAN 0x022000-0x026000 (injection-like, 12x20 u16 LE)")
print("="*60)
for addr in range(0x022000, 0x026000, 2):
    try:
        g = grid_u16le(spark, addr, 12, 20)
        flat = [v for row in g for v in row]
        mn, mx, avg = min(flat), max(flat), sum(flat)//len(flat)
        # Injection: min >= 200, max <= 35000, avg 800-10000, monotono u prvom redu
        row0_mono = all(g[0][i] < g[0][i+1] for i in range(19))
        if mn >= 200 and mx <= 35000 and 500 <= avg <= 12000 and (mx-mn) > 1000 and row0_mono:
            print(f"  @ 0x{addr:06X}: {mn}-{mx}, avg={avg}, row0={g[0]}")
    except:
        pass

print("\nDONE.")
