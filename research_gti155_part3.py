#!/usr/bin/env python3
"""
GTI SE 155 - Part 3: Ignition mapa lokacija + Rev Limiter precizno
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

# ===========================================================================
# IGNITION @ 0x0282EA - velika serija nađena u Part2
# 0x0282EA-0x028756, 502 blokova, spacing=2
# To je skeniranje svakih 2 bajta, dakle NIJE serija 144B blokova!
# Proba: prikazati kao 12x12 blok od 0x028000
# ===========================================================================
print('=== IGNITION detaljno @ 0x028000 region ===')
print()
# Provjeri je li 0x028000 ignition mapa
for test_addr in [0x027400, 0x027500, 0x027594, 0x027700, 0x027800, 0x027843, 0x027A00, 0x027B00,
                  0x027C00, 0x027D00, 0x027E00, 0x027F00, 0x028000, 0x028100, 0x028200, 0x0282EA]:
    block = bytes(gti[test_addr:test_addr+144])
    if len(block) < 144: continue
    avg = sum(block)/144
    mn, mx = min(block), max(block)
    var = sum((b-avg)**2 for b in block)/144
    # Prikazi kao 12x12
    rows = [list(block[r*12:(r+1)*12]) for r in range(12)]
    tag = ''
    # Ignition karakteristike: timing vrijednosti 20-90, gradijent
    if 20 <= mn and mx <= 90 and 25 <= avg <= 75 and var > 30:
        tag = '  *** MOGUCI IGNITION ***'
    print(f'@ 0x{test_addr:06X}: avg={avg:.1f} min={mn} max={mx} var={var:.1f}{tag}')
    for row in rows:
        deg = [f'{v*0.75:.2f}' for v in row]
        print(f'  {row}  => {deg}°')
    print()

# ===========================================================================
# Napomenuto: GTI diff @ 0x027594-0x027843 je velik diff s 300hp
# GTI: 6B 7B 7B 7B 7B 78 73 6F  = 107 123 123 123 123 120 115 111
# x 0.75 = 80, 92, 92, 92, 92, 90, 86, 83 deg
# To su realne ignition vrijednosti!
# Provjeri te adrese
print('=== IGNITION @ 0x027594 (diff region iz Part1) ===')
block = bytes(gti[0x027594:0x027594+144])
avg = sum(block)/144
mn, mx = min(block), max(block)
print(f'avg={avg:.1f} min={mn}({mn*0.75:.1f}deg) max={mx}({mx*0.75:.1f}deg)')
for r in range(12):
    row = list(block[r*12:(r+1)*12])
    deg = [round(v*0.75, 2) for v in row]
    print(f'  R{r}: {row} => {deg}')

# Provjeri ima li serija od 0x027594 (144B spacing)
print()
print('Provjera serije od 0x027594 (144B spacing):')
for i in range(20):
    addr = 0x027594 + i * 144
    if addr + 144 > len(gti): break
    block = bytes(gti[addr:addr+144])
    avg = sum(block)/144
    mn, mx = min(block), max(block)
    print(f'  [{i}] @ 0x{addr:06X}: avg={avg:.1f} min={mn} max={mx}  first8={list(block[:8])}')

# ===========================================================================
# GTI Rev Limiter - najvjerojatniji kandidati
# Iz skeniranja: 0x02930A ima seriju [1280,1280,...,1556,7725]
# Provjeri kontekst
print()
print('=== REV LIMITER kontekst @ 0x02930A ===')
print('GTI 0x029300..0x029340:')
print('  ', hex_block(gti, 0x029300, 64))
print('300 0x029300..0x029340:')
print('  ', hex_block(r300, 0x029300, 64))
vals_gti = [u16le(gti, 0x029300 + i*2) for i in range(16)]
vals_300 = [u16le(r300, 0x029300 + i*2) for i in range(16)]
print(f'GTI LE: {vals_gti}')
print(f'300 LE: {vals_300}')

# 0x0291C4: [1280, 1280, 1280, 1280, 1536, 2048, 5120, 7680]
print()
print('=== REV LIMITER kontekst @ 0x0291C4 ===')
print('GTI 0x0291B0..0x0291F0:')
print('  ', hex_block(gti, 0x0291B0, 64))
vals_gti = [u16le(gti, 0x0291B0 + i*2) for i in range(16)]
print(f'GTI LE: {vals_gti}')

# Trazimo precizno: rev limiter u GTI koji = 7750 rpm
# GTI servis manual: Rotax 1503 4-TEC = 7700 rpm max (ogranicen SW)
# ACE 1630 = 8600 rpm (mechanicall max)
# GTI 155 = 7750 rpm SW limit

# Provjeri 0x0238D6 i 0x023DEC koji imaju 7937 (blisko 8000?)
print()
print('=== Rastuci RPM niz @ 0x0238D6 ===')
print('GTI 0x0238C0..0x023910:')
print('  ', hex_block(gti, 0x0238C0, 80))
vals_gti = [u16be(gti, 0x0238C0 + i*2) for i in range(20)]
vals_300 = [u16be(r300, 0x0238C0 + i*2) for i in range(20)]
print(f'GTI BE: {vals_gti}')
print(f'300 BE: {vals_300}')

# 7750 = 0x1E46 - direktno trazenje u GTI u16 BE
print()
print('=== DIREKTNO TRAZENJE 7750 (0x1E46) u GTI u16 BE ===')
target = struct.pack('>H', 7750)
off = 0
found = []
while True:
    idx = gti.find(target, off)
    if idx == -1: break
    found.append(idx)
    off = idx + 1
print(f'Nađeno {len(found)} pojavljivanja 7750 u cijelom GTI binu:')
for idx in found:
    region = 'BOOT' if idx < 0x10000 else 'CODE' if idx < 0x60000 else 'CAL'
    ctx = [u16be(gti, idx + i*2) for i in range(-2, 4)]
    print(f'  0x{idx:06X} [{region}]: ctx={ctx}')

# 7725 = 0x1E2D
print()
print('=== DIREKTNO TRAZENJE 7725 (0x1E2D) u GTI ===')
target = struct.pack('>H', 7725)
off = 0
while True:
    idx = gti.find(target, off)
    if idx == -1: break
    region = 'BOOT' if idx < 0x10000 else 'CODE' if idx < 0x60000 else 'CAL'
    ctx = [u16be(gti, idx + i*2) for i in range(-2, 4)]
    print(f'  0x{idx:06X} [{region}]: ctx={ctx}')
    off = idx + 1

# ===========================================================================
# Lambda: 300hp lambda mapa = 12x18 Q15 LE
# Na GTI adresi 0x0266F0 i 0x026C08 imamo razlicite vrijednosti
# Pokusaj naci pravu GTI lambda mapu
# Lambda Q15: 1.0 = 0x8000 (32768), lambda 0.9 ~ 0x7333, 1.1 ~ 0x8CCD
# Trazimo 12×18 = 216 u16 LE blok s vrijednostima oko 0x7000-0x9000
print()
print('=== LAMBDA precizno trazenje (216 u16 LE, Q15, 0x6800-0x9800) ===')
for off in range(0x020000, 0x04A000, 4):
    if off + 432 > len(gti): break
    vals = [u16le(gti, off + i*2) for i in range(216)]
    mn, mx = min(vals), max(vals)
    avg = sum(vals)/216
    if 0x6800 <= mn and mx <= 0x9800 and mx - mn > 0x0200:
        var = sum((v-avg)**2 for v in vals)/216
        if var > 0x10000:
            print(f'  Lambda cand @ 0x{off:06X}: avg=0x{int(avg):04X} min=0x{mn:04X} max=0x{mx:04X} var={var:.0f}')
            first12 = [f'{v/32768:.4f}' for v in vals[:12]]
            print(f'    first12 as lambda: {first12}')

print()
print('[GOTOVO PART3]')
