#!/usr/bin/env python3
"""
GTI SE 155 - Part 4: Finalna analiza
- Ignition serija od 0x027594 (8 blokova, 144B spacing)
- Lambda @ 0x0265B0 region detaljno
- Rev limiter @ 0x029318 (7725 rpm) - provjera konteksta
- GTI vs 300hp SW razlike u tuning regiji 0x020000-0x030000
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
def match_score(d1, d2, off, n):
    t = m = 0
    for i in range(n):
        a = off+i
        if a < len(d1) and a < len(d2):
            t += 1
            if d1[a] == d2[a]: m += 1
    return (m/t*100) if t else 0

# ===========================================================================
# GTI IGNITION @ 0x027594: serija od 8 validnih blokova
# Provjeri jesmo li nasli pravi base (0x027594 je blizu diff regije 0x027594-0x02781D)
# GTI 155 = 3-cilindrični 1.5L DOHC (ACE 900 HO baza)
# Taj motor u Sea-Doo GTI SE 155 ima manji broj cilindara od ACE 1630
# Ignition mape: vjerojatno manje (manji number of load/rpm points)
# ===========================================================================
print('=== IGNITION SERIJA @ 0x027594 (GTI 155) ===')
print('Spacing=144B, 8 validnih blokova (blokovi 0-7):')
for i in range(8):
    addr = 0x027594 + i * 144
    block = bytes(gti[addr:addr+144])
    avg = sum(block)/144
    mn, mx = min(block), max(block)
    # Provjera: je li ovo pravi ignition
    rows = [list(block[r*12:(r+1)*12]) for r in range(12)]
    print(f'\n  IGN_GTI[{i}] @ 0x{addr:06X}: avg={avg:.1f} min={mn}({mn*0.75:.1f}deg) max={mx}({mx*0.75:.1f}deg)')
    for r, row in enumerate(rows):
        deg = [f'{v*0.75:.0f}' for v in row]
        print(f'    R{r:2d}: {row}  => [{", ".join(deg)}]°')

# Usporedba s 300hp ignition @ 0x02B730
print()
print('300hp IGN[0] @ 0x02B730 (reference):')
block_300 = bytes(r300[0x02B730:0x02B730+144])
for r in range(12):
    row = list(block_300[r*12:(r+1)*12])
    deg = [f'{v*0.75:.0f}' for v in row]
    print(f'  R{r:2d}: {row}  => [{", ".join(deg)}]°')

# ===========================================================================
# LAMBDA @ 0x0265B0
# Trazimo tocnu pocetnu adresu 12x18 bloka
# ===========================================================================
print()
print('=== LAMBDA GTI detaljno ===')
# 0x0265B0 candid - provjeri od 0x026500
for start in range(0x0265A0, 0x026700, 4):
    vals = [u16le(gti, start + i*2) for i in range(216)]
    mn, mx = min(vals), max(vals)
    avg = sum(vals)/216
    if 0x6800 <= mn and mx <= 0x9800 and mx - mn > 0x0400:
        as_lambda = [v/32768 for v in vals[:18]]
        # Provjeri je li ovo 12 redova x 18 stupaca
        print(f'Lambda @ 0x{start:06X}: avg={avg/32768:.4f} min={mn/32768:.4f} max={mx/32768:.4f}')
        for r in range(12):
            row = [u16le(gti, start + (r*18+c)*2) for c in range(18)]
            lam = [f'{v/32768:.3f}' for v in row]
            print(f'  R{r:2d}: [{", ".join(lam)}]')
        print()
        break

# Provjeri 300hp lambda na istoj adresi
print('300hp Lambda @ 0x0266F0:')
for r in range(12):
    row = [u16le(r300, 0x0266F0 + (r*18+c)*2) for c in range(18)]
    lam = [f'{v/32768:.3f}' for v in row]
    print(f'  R{r:2d}: [{", ".join(lam)}]')

# ===========================================================================
# REV LIMITER @ 0x029318 (7725 rpm kandidat)
# ctx=[1280, 1556, 7725, 15450, 30720, 0]
# 7725 * 2 = 15450 — podudaranje! To je TABLICA RPM threshold
# 1556 -> 1556? ne vidi se pattern
# ===========================================================================
print()
print('=== REV LIMITER @ 0x029318 i okolicina ===')
print('GTI 0x029300..0x029360:')
for row in range(3):
    base = 0x029300 + row*32
    hex_gti = hex_block(gti, base, 32)
    hex_300 = hex_block(r300, base, 32)
    print(f'  GTI 0x{base:06X}: {hex_gti}')
    print(f'  300 0x{base:06X}: {hex_300}')
    print()

# Provjeri u16 LE i BE na tom podrucju
vals_le = [u16le(gti, 0x029310 + i*2) for i in range(12)]
vals_be = [u16be(gti, 0x029310 + i*2) for i in range(12)]
print(f'GTI @ 0x029310 LE: {vals_le}')
print(f'GTI @ 0x029310 BE: {vals_be}')

# 0x029318: GTI LE = [7725, 15450, 30720, 0, ...]
# 0x0293FC: ctx=[0, 1556, 7725, 15450, 30720, 1280]
print()
print('=== REV LIMITER @ 0x0293FC ===')
vals = [u16le(gti, 0x0293F0 + i*2) for i in range(12)]
print(f'GTI 0x0293F0 LE: {vals}')
print('GTI 0x0293E0..0x029420:')
print('  ', hex_block(gti, 0x0293E0, 64))

# ===========================================================================
# SC_BYPASS mapa na GTI - sto znaci 0x020534 vrednosti?
# GTI nema SC ali ima tu mapu s vrijednostima 30-82 (x0.75 = 22-62 deg)
# Moze biti IGNITION korekcija ili ETA mapa
# ===========================================================================
print()
print('=== MAPA @ 0x020534 (GTI) - provjera contextua ===')
print('GTI 0x020500..0x020560:')
for row in range(4):
    print(f'  0x{0x020500+row*24:06X}: {hex_block(gti, 0x020500+row*24, 24)}')

print()
# Ose za 300hp SC mapa: X=[63,75,88,100,113,138,163] Y=[51,77,102,128,154,179,205]
# GTI mapa 7x7: vrijednosti 30,30,...,82 = 0x1E,0x1E,...
# Provjeri ose ispred ove mape (trebale bi biti u16 BE ili u8)
# Pogledaj 32B ispred mape @ 0x020534
print('Kontekst ispred 0x020534 (16B):')
print(f'  0x020524: {hex_block(gti, 0x020524, 16)}')
print(f'  300:      {hex_block(r300, 0x020524, 16)}')

# Iza mape (49B = 0x020534..0x020565):
print(f'  0x020565: {hex_block(gti, 0x020565, 16)}')

# ===========================================================================
# DFCO analiza: GTI ima drugacije vrijednosti
# GTI: [853, 1152, 1408, 1707, 2005, 2261, 2560, 2816, 3413, 3968, 4139, 4267, 5200, 6000]
# 300: [1067, 1280, 1707, 2133, 2560, 2987, 3413, 4267, 5333, 6400, 7680, 8960, 5600, 7000]
# GTI ide do 6000 rpm max = DFCO off threshold
# To znaci GTI DFCO max = 6000 rpm (engine max ~7750 rpm, cut fuel od 6000+)
print()
print('=== DFCO @ 0x02202E (GTI vs 300hp) ===')
dfco_gti = [u16le(gti, 0x02202E + i*2) for i in range(14)]
dfco_300 = [u16le(r300, 0x02202E + i*2) for i in range(14)]
print(f'GTI:  {dfco_gti}')
print(f'300:  {dfco_300}')
# Tumacenje: DFCO je vjerojatno (MAP_threshold, RPM1, RPM2, ...) ili (decel_rpm1, decel_rpm2, ...)
# GTI: 853, 1152... = male vrijednosti, moguce MAP/kPa * 100?
# 300hp: 1067, 1280... = vece vrijednosti
# Sve vrijednosti su LE

# ===========================================================================
# USPOREDBA GTI vs 300hp u TUNING REGIJI 0x020000-0x030000
# ===========================================================================
print()
print('=== TUNING REGIJA DIFF (0x020000-0x030000): GTI vs 300hp ===')
diffs = []
in_d = False
start = 0
for i in range(0x020000, 0x030000):
    if i >= len(gti) or i >= len(r300): break
    if gti[i] != r300[i]:
        if not in_d: in_d = True; start = i
    else:
        if in_d:
            in_d = False
            length = i - start
            if length >= 16:
                diffs.append((start, length))
if in_d:
    diffs.append((start, 0x030000 - start))
diffs.sort(key=lambda x: -x[1])
print(f'Ukupno {len(diffs)} diff blokova >= 16B u 0x020000-0x030000:')
for s, l in diffs[:40]:
    tags = []
    if 0x024F40 <= s <= 0x025100: tags.append('RPM_OS')
    if 0x02439C <= s <= 0x024520: tags.append('INJECTION')
    if 0x02A0D8 <= s <= 0x02A700: tags.append('TORQUE')
    if 0x0266F0 <= s <= 0x026D00: tags.append('LAMBDA')
    if 0x02B720 <= s <= 0x02BDC0: tags.append('IGN/REV_LIM')
    if 0x020534 <= s <= 0x020600: tags.append('SC_MAP')
    if 0x02202E <= s <= 0x022100: tags.append('DFCO/IDLE')
    if 0x027594 <= s <= 0x027820: tags.append('IGN_GTI?')
    gv = hex_block(gti, s, min(16, l))
    rv = hex_block(r300, s, min(16, l))
    t = ' ['+','.join(tags)+']' if tags else ''
    print(f'  0x{s:06X}-0x{s+l-1:06X} ({l:4d}B){t}')
    print(f'    GTI: {gv}')
    print(f'    300: {rv}')

print()
print('[GOTOVO PART4]')
