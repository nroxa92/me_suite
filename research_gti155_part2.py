#!/usr/bin/env python3
"""
GTI SE 155 - Part 2: Ignition, Rev Limiter, Lambda detaljnija analiza
"""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r'C:\Users\SeaDoo\Desktop\me_suite\_materijali'
GTI = BASE + r'\gti_155_18_10SW025752.bin'
R300 = BASE + r'\ori_300.bin'

with open(GTI, 'rb') as f: gti = bytearray(f.read())
with open(R300, 'rb') as f: r300 = bytearray(f.read())

def u16be(d, o): return struct.unpack_from('>H', d, o)[0]
def u16le(d, o): return struct.unpack_from('<H', d, o)[0]
def hex_block(d, o, n): return ' '.join(f'{d[o+i]:02X}' for i in range(min(n, len(d)-o)))

# ==== 1. REV LIMITER kontekst ====
print('=== REV LIMITER @ 0x02B72A ===')
print('GTI 0x02B710..0x02B760:')
print('  ', hex_block(gti, 0x02B710, 80))
print('300 0x02B710..0x02B760:')
print('  ', hex_block(r300, 0x02B710, 80))

# ==== 2. INJECTION potpuna mapa ====
print()
print('=== INJECTION @ 0x02439C (12 redova × 32 stupca = 384 u16 LE) ===')
# Prikazi kao 12 redaka po 8 vrijednosti radi preglednosti
for row in range(12):
    vals = [u16le(gti, 0x02439C + (row*32 + col)*2) for col in range(32)]
    print(f'  Red {row:2d}: {vals[:16]}')
    print(f'         {vals[16:]}')

# Usporedba: koja su različita
diff_inj = 0
for i in range(384):
    if u16le(gti, 0x02439C + i*2) != u16le(r300, 0x02439C + i*2):
        diff_inj += 1
print(f'  Diff bajtova injection main: {diff_inj}/384 ({diff_inj/384*100:.1f}%)')

# ==== 3. IGNITION — serije 12x12 s timing vrijednostima ====
print()
print('=== IGNITION skeniranje — serije 12x12 u8 (val 20-90, gradijent) ===')
ign_series = []
prev = -9999
for off in range(0x020000, 0x050000, 2):
    if off + 144 > len(gti): break
    block = bytes(gti[off:off+144])
    avg = sum(block)/144
    mn, mx = min(block), max(block)
    if 20 <= mn and mx <= 100 and 25 <= avg <= 80:
        var = sum((b-avg)**2 for b in block)/144
        if var > 50:
            if off - prev > 200:
                ign_series.append([off])
            else:
                ign_series[-1].append(off)
            prev = off

print(f'Nadjeno {len(ign_series)} ignition serija:')
for s in ign_series[:20]:
    base = s[0]
    cnt = len(s)
    f16 = list(gti[base:base+16])
    last = s[-1]
    # Provjeri spacing: je li to 144B serija
    if cnt > 1:
        spacing = (s[1] - s[0]) if len(s) > 1 else 0
    else:
        spacing = 0
    print(f'  0x{base:06X}-0x{last:06X} ({cnt} blok, spacing={spacing}): {f16}')

# ==== 4. LAMBDA skeniranje ====
print()
print('=== LAMBDA skeniranje (Q15 LE blokovi 0x7D00-0x8500, 18+ vrijednosti) ===')
found_lambda = []
for off in range(0x020000, 0x050000, 2):
    if off + 72 > len(gti): break
    vals = [u16le(gti, off + i*2) for i in range(18)]
    avg = sum(vals) / 18
    mn, mx = min(vals), max(vals)
    if 0x7C00 <= int(avg) <= 0x8500 and mx - mn > 200:
        found_lambda.append((off, int(avg), mn, mx))

# Grupiraj bliske
prev = -9999
lseries = []
cur = []
for off, avg, mn, mx in found_lambda:
    if off - prev > 300:
        if cur: lseries.append(cur)
        cur = [(off, avg, mn, mx)]
    else:
        cur.append((off, avg, mn, mx))
    prev = off
if cur: lseries.append(cur)

print(f'Nadjeno {len(lseries)} lambda serija:')
for s in lseries[:15]:
    base = s[0][0]
    cnt = len(s)
    vals = [u16le(gti, base + i*2) for i in range(12)]
    print(f'  0x{base:06X} ({cnt} cand): first12={[hex(v) for v in vals]}')

# ==== 5. REV LIMITER pravi kandidati ====
print()
print('=== REV LIMITER kandidati (7500-8100 RPM, u16 BE, CODE regija) ===')
targets = list(range(7500, 8150, 50))
found_rl = {}
for t in targets:
    tb = struct.pack('>H', t)
    off = 0x010000
    while True:
        idx = gti.find(tb, off, 0x060000)
        if idx == -1: break
        found_rl[idx] = t
        off = idx + 1

for idx in sorted(found_rl)[:30]:
    val = u16be(gti, idx)
    val300 = u16be(r300, idx)
    ctx_before = [u16be(gti, idx - 4), u16be(gti, idx - 2)]
    ctx_after = [u16be(gti, idx + 2), u16be(gti, idx + 4)]
    same = '=300' if val == val300 else f'!={val300}'
    print(f'  0x{idx:06X}: GTI={val} ({same})  ctx=[{ctx_before[0]},{ctx_before[1]},*{val}*,{ctx_after[0]},{ctx_after[1]}]')

# ==== 6. GTI SC_BYPASS mapa (0x020534) - je li nešto korisno tu? ====
print()
print('=== SC_BYPASS @ 0x020534 (GTI nema SC - sto je tu?) ===')
print('GTI 0x020520..0x020600:')
for row in range(4):
    base = 0x020520 + row*32
    print(f'  0x{base:06X}: {hex_block(gti, base, 32)}')

# Provjeri 0x020534 kao potencijalnu throttle/ETA korekciju ili ogranicenje
# GTI ima 0x1E, 0x1E itd = 30 dec
print()
print('GTI mapa @ 0x020534 (7x7 u8 = 49 bajtova):')
for row in range(7):
    vals = list(gti[0x020534 + row*7 : 0x020534 + row*7 + 7])
    vals_300 = list(r300[0x020534 + row*7 : 0x020534 + row*7 + 7])
    print(f'  GTI R{row}: {vals}  300: {vals_300}')

# ==== 7. TORQUE detalji ====
print()
print('=== TORQUE @ 0x02A0D8 (16x16 u16 BE Q8) ===')
print('GTI vs 300hp - prvi 4 retka:')
for row in range(4):
    gti_row = [u16be(gti, 0x02A0D8 + (row*16+col)*2) for col in range(16)]
    r300_row = [u16be(r300, 0x02A0D8 + (row*16+col)*2) for col in range(16)]
    print(f'  GTI R{row}: {gti_row}')
    print(f'  300 R{row}: {r300_row}')

# ==== 8. DFCO GTI ====
print()
print('=== DFCO @ 0x02202E (GTI) ===')
# 300hp: 7 vrijednosti (u16 LE)
# Provjeri kontekst 0x022000-0x022100
print('GTI 0x022000..0x022080:')
for row in range(4):
    base = 0x022000 + row*32
    print(f'  0x{base:06X}: {hex_block(gti, base, 32)}')

# GTI DFCO kao u16 LE vrijednosti
dfco_gti = [u16le(gti, 0x02202E + i*2) for i in range(14)]
dfco_300 = [u16le(r300, 0x02202E + i*2) for i in range(14)]
print(f'GTI DFCO @ 0x02202E (14 u16 LE): {dfco_gti}')
print(f'300 DFCO @ 0x02202E (14 u16 LE): {dfco_300}')

# ==== 9. IDLE RPM GTI ====
print()
print('=== IDLE RPM @ 0x02B600 ===')
print('GTI 0x02B5F0..0x02B640:')
print('  ', hex_block(gti, 0x02B5F0, 80))
print('300 0x02B5F0..0x02B640:')
print('  ', hex_block(r300, 0x02B5F0, 80))

idle_gti = [u16le(gti, 0x02B600 + i*2) for i in range(12)]
idle_300 = [u16le(r300, 0x02B600 + i*2) for i in range(12)]
print(f'GTI IDLE (12 u16 LE): {idle_gti}')
print(f'300 IDLE (12 u16 LE): {idle_300}')

# ==== 10. TRAZENJE GTI specifičnog rev limiter ====
print()
print('=== TRAZENJE GTI rev limiter (7750 rpm region, scan 0x020000-0x030000) ===')
# GTI spec max rpm = 7750
# Tražimo kontekst gdje ima serija RPM vrijednosti koje završavaju oko 7750
for off in range(0x020000, 0x030000, 2):
    if off + 16 > len(gti): break
    v = [u16be(gti, off + i*2) for i in range(8)]
    # Tražimo rastuću sekvencu koja završi između 7500-8000
    if v[-1] in range(7500, 8100) and v[0] < v[-1]:
        mono = all(v[i] <= v[i+1] for i in range(7))
        if mono and v[0] >= 1000:
            print(f'  0x{off:06X}: {v}')

print()
print('[GOTOVO PART2]')
