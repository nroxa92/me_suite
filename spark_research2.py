#!/usr/bin/env python3
"""
Spark ECU istraživanje — fokusirano na konkretne nalaze
SW 1037544876 (npro_stg2_spark) vs SW 1037525897 (alen_spark)
"""
import sys
import struct
import os
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

BASE = r"C:\Users\SeaDoo\Desktop\me_suite\_materijali"

files = {
    "npro_spark": os.path.join(BASE, "npro_stg2_spark.bin"),
    "alen_spark": os.path.join(BASE, "alen_spark_2014_1037525897.bin"),
    "spark_ori":  os.path.join(BASE, "spark_ori_2016_666063.bin"),
}

data = {}
for k, path in files.items():
    if os.path.exists(path):
        with open(path, "rb") as f:
            data[k] = f.read()
        print(f"[OK] {k}: {len(data[k])} bajta")
    else:
        print(f"[NEMA] {k}")

CODE_START = 0x010000
CODE_END   = 0x060000

def u16le(d, a): return struct.unpack_from("<H", d, a)[0]
def u16be(d, a): return struct.unpack_from(">H", d, a)[0]
def arr16le(d, a, n): return list(struct.unpack_from(f"<{n}H", d, a))
def arr16be(d, a, n): return list(struct.unpack_from(f">{n}H", d, a))


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("A. RPM OSI — puna NPRo osa @ 0x021748 + proširenje")
print("═"*70)

d = data["npro_spark"]
# Pročitaj punu RPM os uključujući sve što slijedi uzlazno
addr = 0x021748
all_vals = arr16le(d, addr, 20)
print(f"  NPRo @ 0x{addr:06X}: {all_vals}")

# alen_spark ima drugačiju adresu — skeniraj
d2 = data["alen_spark"]
# Traži sekvencu sličnu RPM osi (uzlazno, >10 točaka, 1000–8000)
print("\n  Alen spark RPM osi (skeniranje):")
for a in range(CODE_START, 0x030000, 2):
    v = arr16le(d2, a, 12)
    if (400 <= v[0] <= 2000 and
        all(v[i] < v[i+1] for i in range(11)) and
        v[11] > 5000 and v[11] < 9000):
        # Proširi
        full = v[:]
        ea = a + 24
        while ea + 2 < CODE_END:
            nv = u16le(d2, ea)
            if full[-1] < nv < 12000:
                full.append(nv)
                ea += 2
            else:
                break
        print(f"    @ 0x{a:06X} ({len(full)} točaka): {full}")


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("B. REV LIMITER — traži izolirane skalare u 7400–9000 range")
print("═"*70)

# Poznato: RPM osa ima 7400, 9200, 10800 na kraju — to su os, ne limiter
# Traži jedinstven skalar s preciznim vrijednostima 7800–8800

def find_rev_scalars(d, name):
    # Skeniraj samo 0x020000-0x030000 (parametarski region)
    candidates = []
    for a in range(0x020000, 0x030000, 2):
        v = u16le(d, a)
        if not (7400 <= v <= 8800):
            continue
        # Kontekst: provjeri da okruženje nije niz sličnih vrijednosti
        ctx = arr16le(d, max(a-8, 0), 8)
        # Susjedni ne smiju biti u istom range (nije niz)
        before = [u16le(d, a-2)] if a >= 2 else [0]
        after = [u16le(d, a+2)] if a+4 < len(d) else [0]

        before_in_range = any(7000 <= x <= 10000 for x in before)
        after_in_range = any(7000 <= x <= 10000 for x in after)

        # Dodaj ako je skalar (ne unutar niza RPM vrijednosti)
        candidates.append((a, v, ctx, before_in_range, after_in_range))

    return candidates

print("\n  NPRo spark kandidati za rev limiter:")
cands = find_rev_scalars(data["npro_spark"], "npro_spark")
# Grupiraj bliže adrese
prev = -1000
for a, v, ctx, b_in, a_in in cands:
    if a - prev < 4:
        prev = a
        continue
    in_series = b_in or a_in
    marker = "" if in_series else "  <-- SKALAR KANDIDAT"
    print(f"    0x{a:06X}: {v} rpm  ctx={ctx}{marker}")
    prev = a


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("C. IGNITION MAPE — 144B blokovi, u8 uzlazno")
print("═"*70)

def score_ign_block(d, addr):
    if addr + 144 > len(d): return 0
    b = list(d[addr:addr+144])
    nz = [v for v in b if v > 0]
    if len(nz) < 100: return 0
    mn, mx = min(nz), max(nz)
    if mx < 25 or mn < 10 or mx > 120 or mx - mn < 5: return 0
    cnt = Counter(b)
    mc_cnt = cnt.most_common(1)[0][1]
    if mc_cnt > 60: return 0  # uniformno
    return (mx - mn) * 10 + len(nz)

d = data["npro_spark"]
print("\n  NPRo spark — sken svakih 1B (CODE regija):")
ign_results = []
for addr in range(CODE_START, CODE_END - 144):
    sc = score_ign_block(d, addr)
    if sc > 0:
        ign_results.append((sc, addr))

# Sortiraj i dedupliciraj
ign_results.sort(key=lambda x: -x[0])
seen = []
final_ign = []
for sc, addr in ign_results:
    if any(abs(addr - s) < 144 for s in seen):
        continue
    seen.append(addr)
    b = list(d[addr:addr+144])
    nz = [v for v in b if v > 0]
    mn, mx = min(nz), max(nz)
    row0 = b[:12]
    final_ign.append((sc, addr, mn, mx, row0, b))

print(f"  Ukupno unikátnih IGN blokova: {len(final_ign)}")
print()
for sc, addr, mn, mx, row0, b in final_ign[:25]:
    known = " <-- POZNATA" if abs(addr - 0x024810) < 10 else ""
    print(f"  IGN @ 0x{addr:06X}: raw={mn}–{mx} ({mn*0.75:.1f}°–{mx*0.75:.1f}°), "
          f"score={sc}{known}")
    print(f"         row0={row0}")

# Provjeri alen_spark na istim adresama
print("\n  Alen spark @ istim adresama:")
d2 = data["alen_spark"]
for sc, addr, mn, mx, row0, b in final_ign[:10]:
    if addr + 144 > len(d2): continue
    b2 = list(d2[addr:addr+144])
    nz2 = [v for v in b2 if v > 0]
    if not nz2: continue
    mn2, mx2 = min(nz2), max(nz2)
    same = (b == b2)
    print(f"  @ 0x{addr:06X}: raw={mn2}–{mx2}, {'ISTO' if same else 'RAZLIČITO'}")


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("D. INJECTION MAPA — 2D u16 LE, fuel vrijednosti")
print("═"*70)

# Strategija: tražimo blok veličine N×M u16 LE gdje:
# - vrijednosti su u rasponu 200–40000 (fuel pulse width ili sl.)
# - ima uzlazni trend po redovima (više opterećenja = više goriva)
# - postoji mirror kopija (±0x180 ili neka druga)

def analyze_block_as_injection(d, addr, rows, cols):
    """Analiziraj blok kao injection mapu, vrati score ili 0"""
    size = rows * cols * 2
    if addr + size > len(d): return 0, []
    vals = arr16le(d, addr, rows * cols)
    nz = [v for v in vals if v > 0]
    if len(nz) < rows * cols // 2: return 0, vals
    mn, mx = min(nz), max(nz)
    if mn < 100 or mx > 50000 or mx - mn < 200: return 0, vals

    # Provjeri uzlaznost po redovima i stupcima
    row_mono = 0
    for r in range(rows):
        row = vals[r*cols:(r+1)*cols]
        nz_row = [v for v in row if v > 0]
        if len(nz_row) >= 3:
            m = sum(1 for a, b in zip(nz_row, nz_row[1:]) if b >= a)
            if m >= len(nz_row) // 2: row_mono += 1

    col_mono = 0
    for c in range(cols):
        col = [vals[r*cols+c] for r in range(rows)]
        nz_col = [v for v in col if v > 0]
        if len(nz_col) >= 3:
            m = sum(1 for a, b in zip(nz_col, nz_col[1:]) if b >= a)
            if m >= len(nz_col) // 2: col_mono += 1

    score = row_mono + col_mono
    return score, vals

d = data["npro_spark"]
d2 = data["alen_spark"]

# Fokusiraj se na 0x020000-0x030000 (parametarski region gdje su ignition mape)
# i provjeri uobičajene injection dimenzije
print()
best_inj = []
for rows, cols in [(6,16),(8,16),(10,16),(12,16),(6,18),(8,18),(10,18),(12,18),
                   (6,20),(8,20),(6,32),(8,32),(10,32),(12,32),(16,16),(16,18)]:
    size = rows * cols * 2
    for addr in range(0x020000, 0x030000 - size, 4):
        sc, vals = analyze_block_as_injection(d, addr, rows, cols)
        min_good = rows + cols - 2
        if sc >= min_good:
            nz = [v for v in vals if v > 0]
            mn, mx = min(nz), max(nz)
            best_inj.append((sc, addr, rows, cols, mn, mx, vals))

best_inj.sort(key=lambda x: -x[0])

# Dedupliciraj
seen_inj = []
final_inj = []
for sc, addr, rows, cols, mn, mx, vals in best_inj:
    size = rows * cols * 2
    if any(abs(addr - s) < size for s in seen_inj):
        continue
    seen_inj.append(addr)
    final_inj.append((sc, addr, rows, cols, mn, mx, vals))

print(f"  Injection kandidati (0x020000-0x030000): {len(final_inj)}")
for sc, addr, rows, cols, mn, mx, vals in final_inj[:20]:
    # Provjeri mirror na +0x180
    mirror_ok = False
    mirror_addr = 0
    for offset in [0x180, 0x200, 0x300, 0x3C0, 0x400, 0x500, 0x518]:
        ma = addr + offset
        if ma + rows*cols*2 > len(d): continue
        mv = arr16le(d, ma, rows*cols)
        if mv == vals:
            mirror_ok = True
            mirror_addr = offset
            break

    mirror_str = f"  MIRROR+0x{mirror_addr:X}" if mirror_ok else ""
    avg = sum(vals)/len(vals)
    print(f"  INJ @ 0x{addr:06X} ({rows}×{cols} u16LE): raw={mn}–{mx}, avg={avg:.0f}, "
          f"score={sc}{mirror_str}")
    # Prikaži prvu i zadnju vrstu
    row0 = vals[:cols]
    rowlast = vals[(rows-1)*cols:]
    print(f"         row0={row0}")
    if rows > 1: print(f"         row{rows-1}={rowlast}")


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("E. LAMBDA MAPA — u16 LE, Q15 format (32768=1.0)")
print("═"*70)

def analyze_lambda(d, addr, rows, cols):
    size = rows * cols * 2
    if addr + size > len(d): return 0, []
    vals = arr16le(d, addr, rows * cols)
    nz = [v for v in vals if v > 0]
    if len(nz) < rows * cols // 2: return 0, vals
    mn, mx = min(nz), max(nz)
    # Q15 lambda: 0.75–1.30 = 24576–42598
    if mn < 22000 or mx > 44000: return 0, vals
    if mx - mn < 1000: return 0, vals
    # Mora imati vrijednosti blizu 32768 (lambda=1.0)
    near_1 = sum(1 for v in nz if 29000 < v < 36000)
    if near_1 < len(nz) // 4: return 0, vals
    return near_1, vals

print()
best_lam = []
for rows, cols in [(12,18),(12,16),(8,18),(8,16),(16,18),(16,16),
                   (10,18),(10,16),(6,18),(6,16),(12,20),(8,20)]:
    size = rows * cols * 2
    for addr in range(0x020000, 0x030000 - size, 2):
        sc, vals = analyze_lambda(d, addr, rows, cols)
        if sc > 0:
            nz = [v for v in vals if v > 0]
            mn, mx = min(nz), max(nz)
            best_lam.append((sc, addr, rows, cols, mn, mx))

best_lam.sort(key=lambda x: -x[0])
seen_lam = []
final_lam = []
for sc, addr, rows, cols, mn, mx in best_lam:
    size = rows * cols * 2
    if any(abs(addr - s) < size for s in seen_lam):
        continue
    seen_lam.append(addr)
    final_lam.append((sc, addr, rows, cols, mn, mx))

print(f"  Lambda kandidati: {len(final_lam)}")
for sc, addr, rows, cols, mn, mx in final_lam[:15]:
    lam_min = mn / 32768.0
    lam_max = mx / 32768.0
    print(f"  LAM @ 0x{addr:06X} ({rows}×{cols} u16LE): "
          f"raw={mn}–{mx}, λ={lam_min:.3f}–{lam_max:.3f}, score={sc}")


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("F. DIFF: alen_spark vs npro_spark — CODE regija 0x010000–0x060000")
print("═"*70)

d1 = data["npro_spark"]
d2 = data["alen_spark"]

diff_bytes = []
for i in range(CODE_START, min(CODE_END, len(d1), len(d2))):
    if d1[i] != d2[i]:
        diff_bytes.append(i)

# Grupiraj
groups = []
if diff_bytes:
    gs = diff_bytes[0]
    ge = diff_bytes[0]
    for i in diff_bytes[1:]:
        if i - ge <= 8:
            ge = i
        else:
            groups.append((gs, ge))
            gs = i
            ge = i
    groups.append((gs, ge))

print(f"\n  Ukupno diff bajtova: {len(diff_bytes)}, spojenih regija: {len(groups)}")
print()

# Prikaži regije s analizom
for gs, ge in groups:
    size = ge - gs + 1
    v1 = list(d1[gs:ge+1])
    v2 = list(d2[gs:ge+1])
    print(f"  DIFF @ 0x{gs:06X}–0x{ge:06X} ({size} B):")

    if size <= 32:
        print(f"    npro: {[f'{x:02X}' for x in v1]}")
        print(f"    alen: {[f'{x:02X}' for x in v2]}")
    else:
        # Pokušaj interpretirati kao u16 LE
        n16 = size // 2
        try:
            vals1 = arr16le(d1, gs, n16)
            vals2 = arr16le(d2, gs, n16)
            mn1, mx1 = min(vals1), max(vals1)
            mn2, mx2 = min(vals2), max(vals2)
            print(f"    npro u16LE: min={mn1}, max={mx1}, primjer={vals1[:8]}...")
            print(f"    alen u16LE: min={mn2}, max={mx2}, primjer={vals2[:8]}...")
        except:
            print(f"    (preveliko za ispis)")

    # Provjeri da li izgleda kao ignition blok
    if 130 <= size <= 160:
        b1 = list(d1[gs:gs+144]) if gs+144 <= len(d1) else []
        if b1:
            nz = [v for v in b1 if v > 0]
            if nz:
                mn, mx = min(nz), max(nz)
                if 15 <= mn and mx <= 130 and mx - mn > 5:
                    print(f"    >>> POTENCIJALNA IGNITION MAPA: raw={mn}–{mx}")


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("G. DETALJNI PREGLED POZNATIH I OKOLNIH ADRESA")
print("═"*70)

d = data["npro_spark"]

# Provjerimo region oko RPM osi @ 0x021748
# i čitajmo što je ispred/iza kao potencijalne mape

print("\n  Region 0x021700–0x022500 (u blizini RPM osi i DTC tablice):")
print("  (interpretirajmo kao u16 LE, prikažimo regije sa 'razumnim' vrijednostima)")

for start in range(0x021700, 0x022600, 0x20):
    vals = arr16le(d, start, 16)
    nz = [v for v in vals if v > 0]
    if not nz: continue
    mn, mx = min(nz), max(nz)
    # Interesantno: nije sve 0xFFFF ili sume, ima varijacije, razuman range
    all_ff = all(v == 0xFFFF for v in vals)
    if all_ff: continue
    if mx < 100 and mn < 100: continue  # mali scalari/flags
    if mx > 60000: continue  # vjerovatno adrese/bytekod
    uniq = len(set(vals))
    if uniq < 3: continue
    print(f"  0x{start:06X}: {vals}  (mn={mn}, mx={mx}, uniq={uniq})")

# Pogledajmo šire oko ignition @ 0x024810
print("\n  Region 0x023000–0x026000 (šira okolina ignition):")
print("  (prikaz samo blokova koji izgledaju kao mapa)")

for start in range(0x023000, 0x026100, 0x20):
    vals = arr16le(d, start, 16)
    nz = [v for v in vals if v > 0]
    if not nz: continue
    mn, mx = min(nz), max(nz)
    if all(v == 0xFFFF for v in vals): continue
    if mx > 60000: continue
    if mx - mn < 200: continue
    if len(set(vals)) < 5: continue

    # Provjeri da li izgleda kao injection ili lambda
    inj_like = 200 <= mn and mx <= 40000
    lam_like = 22000 <= mn and mx <= 44000 and 28000 <= sum(nz)/len(nz) <= 37000

    tag = ""
    if lam_like: tag = "  [LAMBDA?]"
    elif inj_like: tag = "  [INJECTION?]"

    print(f"  0x{start:06X}: {vals[:8]}... (mn={mn}, mx={mx}){tag}")


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("H. REV LIMITER — focused scan @ poznate lokacije i okolina")
print("═"*70)

d = data["npro_spark"]

# 300hp ima rev limiter @ 0x02B72A, 0x02B73E
# Spark je drugačija layout — pokušajmo pronaći analoge

# Traži parove scalara (soft/hard limit) u blizini
print("\nSken za izolirane RPM skalare 7200–8800 u 0x020000–0x025000:")
prev_a = -1000
for a in range(0x020000, 0x025000, 2):
    v = u16le(d, a)
    if not (7200 <= v <= 8800):
        continue
    if a - prev_a < 6:
        prev_a = a
        continue
    # Provjeri kontekst - ne smije biti unutar niza RPM vrijednosti
    ctx_before = [u16le(d, a - i*2) for i in range(1, 5) if a - i*2 >= 0]
    ctx_after = [u16le(d, a + i*2) for i in range(1, 5) if a + i*2 < len(d)]

    # Niz RPM bi imao uzlazne vrijednosti oko njega
    is_in_rpm_series = (
        any(200 < x < v for x in ctx_before[:2]) or
        any(v < x < 12000 for x in ctx_after[:2])
    )

    if is_in_rpm_series:
        prev_a = a
        continue

    all_ctx = ctx_before[:3] + ctx_after[:3]
    print(f"  0x{a:06X}: {v} rpm  before={ctx_before[:3]}, after={ctx_after[:3]}")
    prev_a = a


# ════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("I. SKENIRANJE U16 LE BLOKOVA — injection fokus (širi scan)")
print("═"*70)

# Pokušajmo s 12×12 (144 ćelije, 288B) — kao ignition ali u16
# ili 8×12, 6×12, 10×12 itd.
d = data["npro_spark"]
print("\nKandidati za 12×12 u16 LE injection (288 bajta):")
for addr in range(CODE_START, CODE_END - 288, 4):
    vals = arr16le(d, addr, 144)
    nz = [v for v in vals if v > 0]
    if len(nz) < 100: continue
    mn, mx = min(nz), max(nz)
    if mn < 100 or mx > 50000 or mx - mn < 500: continue
    # Ne smije biti RPM-like (previsoke vrijednosti dominantne)
    high_vals = sum(1 for v in nz if v > 8000)
    if high_vals > 40: continue

    row_ok = 0
    for r in range(12):
        row = vals[r*12:(r+1)*12]
        nz_r = [v for v in row if v > 0]
        if len(nz_r) >= 8:
            m = sum(1 for a, b in zip(nz_r, nz_r[1:]) if b >= a)
            if m >= 7: row_ok += 1

    if row_ok >= 6:
        print(f"  0x{addr:06X} (12×12 u16LE): raw={mn}–{mx}, dobrih_redova={row_ok}")
        print(f"    row0={vals[:12]}")

print("\nKandidati za 8×8 u16 LE injection (128 bajta):")
for addr in range(CODE_START, CODE_END - 128, 4):
    vals = arr16le(d, addr, 64)
    nz = [v for v in vals if v > 0]
    if len(nz) < 40: continue
    mn, mx = min(nz), max(nz)
    if mn < 100 or mx > 50000 or mx - mn < 300: continue
    high_vals = sum(1 for v in nz if v > 8000)
    if high_vals > 20: continue

    row_ok = 0
    for r in range(8):
        row = vals[r*8:(r+1)*8]
        nz_r = [v for v in row if v > 0]
        if len(nz_r) >= 5:
            m = sum(1 for a, b in zip(nz_r, nz_r[1:]) if b >= a)
            if m >= 4: row_ok += 1

    if row_ok >= 5:
        print(f"  0x{addr:06X} (8×8 u16LE): raw={mn}–{mx}, dobrih_redova={row_ok}")
        print(f"    row0={vals[:8]}")

print("\nKandidati za 6×16 u16 LE (192 bajta):")
for addr in range(CODE_START, CODE_END - 192, 4):
    vals = arr16le(d, addr, 96)
    nz = [v for v in vals if v > 0]
    if len(nz) < 60: continue
    mn, mx = min(nz), max(nz)
    if mn < 100 or mx > 50000 or mx - mn < 300: continue
    high_vals = sum(1 for v in nz if v > 8000)
    if high_vals > 20: continue

    row_ok = 0
    for r in range(6):
        row = vals[r*16:(r+1)*16]
        nz_r = [v for v in row if v > 0]
        if len(nz_r) >= 10:
            m = sum(1 for a, b in zip(nz_r, nz_r[1:]) if b >= a)
            if m >= 8: row_ok += 1

    if row_ok >= 4:
        print(f"  0x{addr:06X} (6×16 u16LE): raw={mn}–{mx}, dobrih_redova={row_ok}")
        print(f"    row0={vals[:16]}")

print("\n" + "═"*70)
print("KRAJ")
print("═"*70)
