#!/usr/bin/env python3
"""
Spark ECU istraživačka skripta — SW 1037544876 vs 1037525897
Tražimo: injection mapu, lambda/AFR, rev limiter, RPM osi, ignition sekundarne mape
"""
import sys
import struct
import os

sys.stdout.reconfigure(encoding='utf-8')

# ─── Učitaj fajlove ──────────────────────────────────────────────────────────

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
        print(f"[OK] {k}: {len(data[k])} bajta ({len(data[k]):#010x})")
    else:
        print(f"[NEMA] {k}: {path}")

CODE_START = 0x010000
CODE_END   = 0x060000

print()

# ─── Helper funkcije ─────────────────────────────────────────────────────────

def read_u16_le(d, addr):
    return struct.unpack_from("<H", d, addr)[0]

def read_u16_be(d, addr):
    return struct.unpack_from(">H", d, addr)[0]

def read_u16_arr_le(d, addr, count):
    return list(struct.unpack_from(f"<{count}H", d, addr))

def read_u16_arr_be(d, addr, count):
    return list(struct.unpack_from(f">{count}H", d, addr))

def read_u8_arr(d, addr, count):
    return list(d[addr:addr+count])


# ─── 1. POZNATA RPM OS @ 0x021748 ────────────────────────────────────────────

print("=" * 70)
print("1. POZNATA RPM OS @ 0x021748 (provjera)")
print("=" * 70)

SPARK_RPM_ADDR = 0x021748
SPARK_RPM_COUNT = 15

for name, d in data.items():
    if not d or len(d) < SPARK_RPM_ADDR + SPARK_RPM_COUNT*2:
        continue
    vals = read_u16_arr_le(d, SPARK_RPM_ADDR, SPARK_RPM_COUNT)
    print(f"  {name} @ 0x{SPARK_RPM_ADDR:06X}: {vals}")

print()

# ─── 2. TRAŽI SVE RPM OSE (u16 LE, uzlazno sortiran, razumne RPM vrijednosti) ─

print("=" * 70)
print("2. SKENIRANJE RPM OSI (u16 LE, uzlazno, 500–9000 rpm, min 8 točaka)")
print("=" * 70)

def scan_rpm_axes(d, name):
    found = []
    for addr in range(CODE_START, CODE_END - 30, 2):
        # Čitaj 10 uzastopnih u16 LE
        vals = []
        ok = True
        prev = 0
        for i in range(10):
            v = read_u16_le(d, addr + i*2)
            if v < 400 or v > 10000:
                ok = False
                break
            if v <= prev:
                ok = False
                break
            prev = v
            vals.append(v)
        if not ok:
            continue
        # Provjeri da je opseg razuman (min < 2000, max > 4000)
        if vals[0] < 2000 and vals[-1] > 4000:
            # Proširi do kraja uzlaznog niza
            full = vals[:]
            ext_addr = addr + len(full)*2
            while ext_addr + 2 <= CODE_END:
                v = read_u16_le(d, ext_addr)
                if v > full[-1] and v < 12000:
                    full.append(v)
                    ext_addr += 2
                else:
                    break
            if len(full) >= 8:
                found.append((addr, full))
    return found

for name in ["npro_spark", "alen_spark"]:
    d = data.get(name)
    if not d:
        continue
    print(f"\n  [{name}]")
    results = scan_rpm_axes(d, name)
    # Dedupliciraj (čuvaj samo prvu pojavu istog niza)
    seen = {}
    for addr, vals in results:
        key = tuple(vals)
        if key not in seen:
            seen[key] = addr
    for key, addr in seen.items():
        print(f"    RPM OS @ 0x{addr:06X} ({len(key)} točaka): {list(key)}")

print()

# ─── 3. TRAŽI REV LIMITER ────────────────────────────────────────────────────

print("=" * 70)
print("3. SKENIRANJE REV LIMITERA (u16 LE/BE, 7000–9500 rpm)")
print("=" * 70)

REV_MIN = 7000
REV_MAX = 9500

for name in ["npro_spark", "alen_spark"]:
    d = data.get(name)
    if not d:
        continue
    print(f"\n  [{name}]")
    found_le = []
    found_be = []
    for addr in range(CODE_START, CODE_END - 2, 2):
        v_le = read_u16_le(d, addr)
        v_be = read_u16_be(d, addr)
        if REV_MIN <= v_le <= REV_MAX:
            found_le.append((addr, v_le))
        if REV_MIN <= v_be <= REV_MAX and v_be != v_le:
            found_be.append((addr, v_be))

    # Filtriraj — prikaži samo izoliranog (susjedni bajtovi nisu slični)
    def is_isolated(d, addr, val):
        """Provjeri da nije unutar uzlaznog niza (osa)"""
        if addr >= 2:
            prev = read_u16_le(d, addr - 2)
            if 200 < prev < val and prev < 9500:
                return False  # vjerovatno unutar ose
        if addr + 4 <= len(d):
            nxt = read_u16_le(d, addr + 2)
            if val < nxt < 9500 and nxt > 200:
                return False
        return True

    print(f"    LE kandidati ({len(found_le)}):")
    for addr, v in found_le:
        isolated = is_isolated(d, addr, v)
        marker = "  <-- SKALAR" if isolated else ""
        # Prikaži kontekst
        ctx = read_u16_arr_le(d, max(addr-8, 0), 6)
        print(f"      0x{addr:06X}: {v} rpm | kontekst LE: {ctx}{marker}")

print()

# ─── 4. TRAŽI INJECTION MAPU ─────────────────────────────────────────────────

print("=" * 70)
print("4. TRAŽI INJECTION MAPU (2D u16 LE, fuel vrijednosti ~500–30000)")
print("=" * 70)

def looks_like_injection_row(vals):
    """Provjeri da red izgleda kao fuel row: uzlazno ili blago, razumni range"""
    if len(vals) < 8:
        return False
    non_zero = [v for v in vals if v > 0]
    if len(non_zero) < 4:
        return False
    mn, mx = min(non_zero), max(non_zero)
    if mn < 100 or mx > 60000:
        return False
    if mx / max(mn, 1) < 1.2:  # premalo varijacije — vjerovatno nije mapa
        return False
    # Većinom monotono uzlazno
    mono = sum(1 for a, b in zip(vals, vals[1:]) if b >= a)
    return mono >= len(vals) // 2

def scan_injection(d, name, rows_hint=None, cols_hint=None):
    """Skeniraj za injection-like 2D tablice"""
    results = []

    # Traži 2D tablice s dimenzijama koje su razumne za injection
    candidate_dims = [
        (6, 16), (6, 18), (6, 20), (6, 24), (6, 32),
        (8, 16), (8, 18), (8, 20), (8, 24),
        (10, 16), (10, 18), (10, 20),
        (12, 16), (12, 18), (12, 20),
        (16, 16), (16, 18),
    ]

    if rows_hint and cols_hint:
        candidate_dims = [(rows_hint, cols_hint)]

    seen_addr = set()

    for rows, cols in candidate_dims:
        size = rows * cols * 2
        for addr in range(CODE_START, CODE_END - size, 2):
            if addr in seen_addr:
                continue
            vals_flat = read_u16_arr_le(d, addr, rows * cols)

            # Provjera: sve vrijednosti u opsegu 50–60000
            non_zero = [v for v in vals_flat if v > 0]
            if len(non_zero) < rows * cols // 3:
                continue
            mn, mx = min(non_zero), max(non_zero)
            if mn < 50 or mx > 60000:
                continue
            if mx - mn < 500:  # premalo varijacije
                continue

            # Provjera redova: barem polovina redova izgleda uzlazno
            good_rows = 0
            for r in range(rows):
                row = vals_flat[r*cols:(r+1)*cols]
                if looks_like_injection_row(row):
                    good_rows += 1

            if good_rows < rows // 2:
                continue

            # Izračunaj prosječne vrijednosti
            avg = sum(non_zero) / len(non_zero)

            results.append({
                'addr': addr,
                'rows': rows,
                'cols': cols,
                'min': mn,
                'max': mx,
                'avg': avg,
                'good_rows': good_rows,
                'vals': vals_flat,
            })
            seen_addr.add(addr)

    return results

for name in ["npro_spark", "alen_spark"]:
    d = data.get(name)
    if not d:
        continue
    print(f"\n  [{name}]")
    results = scan_injection(d, name)

    # Sortiraj po broju dobrih redova
    results.sort(key=lambda x: (-x['good_rows'], x['addr']))

    # Prikaži top 20
    for r in results[:20]:
        print(f"    INJ kandidat @ 0x{r['addr']:06X} ({r['rows']}×{r['cols']} u16 LE): "
              f"raw={r['min']}–{r['max']}, avg={r['avg']:.0f}, "
              f"dobrih_redova={r['good_rows']}/{r['rows']}")

    if len(results) > 20:
        print(f"    ... i još {len(results)-20} kandidata")

print()

# ─── 5. TRAŽI LAMBDA/AFR MAPU ────────────────────────────────────────────────

print("=" * 70)
print("5. TRAŽI LAMBDA/AFR MAPU (u16 LE, Q15, raw ~27853–39321)")
print("=" * 70)

# Q15: 1.0 = 32768
# lambda 0.85 = 27853, lambda 1.0 = 32768, lambda 1.20 = 39322
LAMBDA_MIN_RAW = 24000  # ~0.73 lambda (bogato)
LAMBDA_MAX_RAW = 42000  # ~1.28 lambda (siromašno)
LAMBDA_TARGET_MIN = 26000
LAMBDA_TARGET_MAX = 40000

def looks_like_lambda(vals):
    non_zero = [v for v in vals if v > 0]
    if len(non_zero) < 6:
        return False
    mn, mx = min(non_zero), max(non_zero)
    if mn < LAMBDA_MIN_RAW or mx > LAMBDA_MAX_RAW:
        return False
    # Mora biti blizu 32768 (lambda=1.0)
    near_one = sum(1 for v in non_zero if 29000 < v < 37000)
    if near_one < len(non_zero) // 3:
        return False
    return True

def scan_lambda(d, name):
    results = []
    candidate_dims = [
        (12, 18), (12, 16), (12, 20),
        (8, 18), (8, 16), (8, 20), (8, 24),
        (10, 18), (10, 16),
        (16, 18), (16, 16),
        (6, 18), (6, 16),
    ]
    seen_addr = set()

    for rows, cols in candidate_dims:
        size = rows * cols * 2
        for addr in range(CODE_START, CODE_END - size, 2):
            if addr in seen_addr:
                continue
            vals = read_u16_arr_le(d, addr, rows * cols)
            if looks_like_lambda(vals):
                non_zero = [v for v in vals if v > 0]
                mn, mx = min(non_zero), max(non_zero)
                results.append((addr, rows, cols, mn, mx, sum(non_zero)/len(non_zero)))
                seen_addr.add(addr)

    return results

for name in ["npro_spark", "alen_spark"]:
    d = data.get(name)
    if not d:
        continue
    print(f"\n  [{name}]")
    results = scan_lambda(d, name)
    results.sort(key=lambda x: x[0])
    for addr, rows, cols, mn, mx, avg in results[:30]:
        lambda_min = mn / 32768.0
        lambda_max = mx / 32768.0
        lambda_avg = avg / 32768.0
        print(f"    LAMBDA kandidat @ 0x{addr:06X} ({rows}×{cols} u16 LE): "
              f"raw={mn}–{mx}, λ={lambda_min:.3f}–{lambda_max:.3f}, avg λ={lambda_avg:.3f}")

print()

# ─── 6. TRAŽI IGNITION SEKUNDARNE MAPE (144B blokovi) ────────────────────────

print("=" * 70)
print("6. TRAŽI IGNITION MAPE (144B blokovi, u8, raspon 25–75, varijacija >=4)")
print("=" * 70)

SPARK_IGN_ADDR = 0x024810  # poznata ignition mapa

def score_ignition_block(d, addr):
    """Vrati score za 144B blok kao potencijalnu ignition mapu (u8, 12×12)"""
    if addr + 144 > len(d):
        return 0, []
    block = list(d[addr:addr+144])

    non_zero = [v for v in block if v > 0]
    if len(non_zero) < 80:
        return 0, block

    mn, mx = min(non_zero), max(non_zero)

    # Ignition bi trebao biti u opsegu 20–120 (raw, 0.75°/bit => 15°–90°)
    if mn < 15 or mx > 130:
        return 0, block

    # Varijacija mora biti >= 4 (0.75° * 4 = 3°)
    if mx - mn < 4:
        return 0, block

    # Provjeri da nije uniform noise
    from collections import Counter
    cnt = Counter(block)
    # Ako jedna vrijednost dominira (>50%), nije mapa
    most_common_count = max(cnt.values())
    if most_common_count > len(block) * 0.5:
        return 0, block

    score = (mx - mn) * len(non_zero)
    return score, block

def scan_ignition_blocks(d, name):
    results = []
    for addr in range(CODE_START, CODE_END - 144, 1):
        score, block = score_ignition_block(d, addr)
        if score > 0:
            mn = min(v for v in block if v > 0)
            mx = max(v for v in block if v > 0)
            results.append((score, addr, mn, mx, block))

    # Sortiraj po score descending
    results.sort(key=lambda x: -x[0])
    return results

for name in ["npro_spark"]:
    d = data.get(name)
    if not d:
        continue
    print(f"\n  [{name}]")
    results = scan_ignition_blocks(d, name)

    # Dedupliciraj: ukloni blokove koji se preklapaju s boljim
    seen_ranges = []
    deduped = []
    for score, addr, mn, mx, block in results:
        overlap = any(abs(addr - a) < 144 for a in seen_ranges)
        if not overlap:
            seen_ranges.append(addr)
            deduped.append((score, addr, mn, mx, block))

    print(f"    Ukupno kandidata (deduplicirano): {len(deduped)}")
    for score, addr, mn, mx, block in deduped[:20]:
        deg_min = mn * 0.75
        deg_max = mx * 0.75
        is_known = abs(addr - SPARK_IGN_ADDR) < 144
        marker = " <-- POZNATA" if is_known else ""
        # First row preview
        row0 = block[:12]
        print(f"    IGN @ 0x{addr:06X} (score={score}): raw={mn}–{mx} "
              f"({deg_min:.1f}°–{deg_max:.1f}°), row0={row0}{marker}")

print()

# ─── 7. DIFF: npro_spark vs alen_spark ───────────────────────────────────────

print("=" * 70)
print("7. DIFF: npro_spark (1037544876) vs alen_spark (1037525897)")
print("=" * 70)

d1 = data.get("npro_spark")
d2 = data.get("alen_spark")

if d1 and d2:
    min_len = min(len(d1), len(d2))

    # Nađi promijenjene regije
    in_diff = False
    diff_start = 0
    diff_regions = []

    for i in range(min_len):
        if d1[i] != d2[i]:
            if not in_diff:
                diff_start = i
                in_diff = True
        else:
            if in_diff:
                diff_regions.append((diff_start, i - 1, i - diff_start))
                in_diff = False
    if in_diff:
        diff_regions.append((diff_start, min_len - 1, min_len - diff_start))

    print(f"  npro_spark vs alen_spark: {len(diff_regions)} diff regija u prvih {min_len:#010x} B")
    print(f"  Veličina fajlova: npro={len(d1):#010x}, alen={len(d2):#010x}")
    print()

    # Spoji bliske regije (gap < 16B) za pregled
    merged = []
    for start, end, size in diff_regions:
        if merged and start - merged[-1][1] < 32:
            merged[-1] = (merged[-1][0], end, end - merged[-1][0] + 1)
        else:
            merged.append((start, end, size))

    print(f"  Spojene diff regije ({len(merged)}):")
    for start, end, size in merged:
        in_code = CODE_START <= start < CODE_END
        region_tag = "CODE" if in_code else ("BOOT" if start < 0x10000 else "CAL")

        # Prikaži vrijednosti
        print(f"    0x{start:06X}–0x{end:06X} ({size:4d} B) [{region_tag}]")
        if size <= 64:
            v1 = list(d1[start:end+1])
            v2 = list(d2[start:end+1])
            print(f"      npro: {[f'{x:02X}' for x in v1]}")
            print(f"      alen: {[f'{x:02X}' for x in v2]}")

print()

# ─── 8. SPECIFIČNA PROVJERA INJECTION ZA SPARK ───────────────────────────────

print("=" * 70)
print("8. SPECIFIČNA PROVJERA POZNATIH INJECTION ADRESA (analogija s 300hp)")
print("=" * 70)

# 300hp injection je @ 0x02439C (12×32 u16 LE)
# Spark je manji motor, injection bi mogao biti manji
# Provjeri u blizini ignition mape (0x024810)

d = data.get("npro_spark")
if d:
    # Provjeri region oko poznate ignition mape
    print("\n  Regija oko 0x024000–0x025000:")
    check_addrs = [
        0x023000, 0x023200, 0x023400, 0x023600, 0x023800, 0x023A00,
        0x023C00, 0x023E00, 0x024000, 0x024200, 0x024400, 0x024600,
        0x025000, 0x025200, 0x025400, 0x025600, 0x025800, 0x025A00,
        0x026000, 0x026200, 0x026400, 0x026600,
    ]

    # Za svaku adresu, pokušaj čitati 8×16, 6×16, 10×16 u16 LE i procijeni
    for addr in check_addrs:
        for rows, cols in [(8, 16), (6, 16), (10, 16), (8, 18), (6, 18), (12, 16)]:
            size = rows * cols * 2
            if addr + size > len(d):
                continue
            vals = read_u16_arr_le(d, addr, rows * cols)
            non_zero = [v for v in vals if v > 0]
            if len(non_zero) < rows * cols // 2:
                continue
            mn, mx = min(non_zero), max(non_zero)
            if 100 <= mn and mx <= 60000 and mx - mn > 300:
                # Provjeri monotoniju redova
                good = 0
                for r in range(rows):
                    row = vals[r*cols:(r+1)*cols]
                    nz = [v for v in row if v > 0]
                    if len(nz) >= cols // 2:
                        mono = sum(1 for a, b in zip(nz, nz[1:]) if b >= a)
                        if mono >= len(nz) // 2:
                            good += 1
                if good >= rows // 2:
                    print(f"    INJ? @ 0x{addr:06X} ({rows}×{cols}): raw={mn}–{mx}, dobrih_redova={good}")

print()

# ─── 9. DETALJNI PREGLED POZNATOG IGNITION BLOKA ─────────────────────────────

print("=" * 70)
print("9. DETALJNI PREGLED POZNATE IGNITION MAPE @ 0x024810")
print("=" * 70)

d = data.get("npro_spark")
if d:
    addr = 0x024810
    block = list(d[addr:addr+144])
    print(f"  Raw vrijednosti (12×12 u8):")
    for r in range(12):
        row = block[r*12:(r+1)*12]
        deg = [f"{v*0.75:.1f}" for v in row]
        print(f"    Redak {r+1:2d}: raw={row} => °={deg}")

    # Provjeri susjedne blokove
    print(f"\n  Susjedni 144B blokovi:")
    for offset in [-288, -144, 144, 288, 432, 576]:
        check_addr = addr + offset
        if check_addr < CODE_START or check_addr + 144 > CODE_END:
            continue
        block2 = list(d[check_addr:check_addr+144])
        non_zero = [v for v in block2 if v > 0]
        if not non_zero:
            print(f"    @ 0x{check_addr:06X} (offset={offset:+d}): SVE NULE")
            continue
        mn, mx = min(non_zero), max(non_zero)
        from collections import Counter
        cnt = Counter(block2)
        mc = cnt.most_common(1)[0]
        print(f"    @ 0x{check_addr:06X} (offset={offset:+d}): raw={mn}–{mx}, "
              f"nenula={len(non_zero)}, najčešće={mc[0]}×{mc[1]}")

print()

# ─── 10. SCAN SEKVENCIONALNIH 144B IGN BLOKOVA ───────────────────────────────

print("=" * 70)
print("10. SCAN SEKVENCIJALNIH IGN BLOKOVA OD 0x024810")
print("=" * 70)

d = data.get("npro_spark")
if d:
    start = 0x024810
    print(f"  Sken od 0x{start:06X}, stride=144B, do 30 blokova:")
    for i in range(30):
        addr = start + i * 144
        if addr + 144 > len(d):
            break
        block = list(d[addr:addr+144])
        non_zero = [v for v in block if v > 0]
        if not non_zero:
            print(f"  Blok {i:2d} @ 0x{addr:06X}: SVE NULE")
            continue
        mn, mx = min(non_zero), max(non_zero)
        from collections import Counter
        cnt = Counter(block)
        mc_val, mc_cnt = cnt.most_common(1)[0]
        row0 = block[:12]
        print(f"  Blok {i:2d} @ 0x{addr:06X}: raw={mn:3d}–{mx:3d} ({mn*0.75:.1f}°–{mx*0.75:.1f}°), "
              f"nenula={len(non_zero)}/144, dom={mc_val}×{mc_cnt}, row0={row0}")

print()

# ─── 11. ALEN SPARK — IGN I INJECTION ADRESE ─────────────────────────────────

print("=" * 70)
print("11. ALEN SPARK (1037525897) — IGN PREGLED @ 0x024810 i okolina")
print("=" * 70)

d = data.get("alen_spark")
if d:
    # Provjeri da li alen_spark ima isti ign blok
    addr = 0x024810
    if len(d) > addr + 144:
        block = list(d[addr:addr+144])
        non_zero = [v for v in block if v > 0]
        if non_zero:
            mn, mx = min(non_zero), max(non_zero)
            row0 = block[:12]
            print(f"  alen_spark IGN @ 0x{addr:06X}: raw={mn}–{mx}, row0={row0}")

    # RPM os u alen_spark
    ALEN_RPM_ADDR = 0x021748
    if len(d) > ALEN_RPM_ADDR + 30:
        vals = read_u16_arr_le(d, ALEN_RPM_ADDR, 15)
        print(f"  alen_spark RPM os @ 0x{ALEN_RPM_ADDR:06X}: {vals}")

    # Tražimo blokove koji su različiti između npro i alen u CODE regiji
    d1 = data.get("npro_spark")
    if d1:
        diffs_in_code = []
        for i in range(CODE_START, min(CODE_END, len(d), len(d1)), 2):
            if d[i] != d1[i] or (i+1 < len(d) and i+1 < len(d1) and d[i+1] != d1[i+1]):
                diffs_in_code.append(i)

        # Grupišemo
        if diffs_in_code:
            groups = []
            g_start = diffs_in_code[0]
            g_end = diffs_in_code[0]
            for a in diffs_in_code[1:]:
                if a - g_end <= 4:
                    g_end = a
                else:
                    groups.append((g_start, g_end))
                    g_start = a
                    g_end = a
            groups.append((g_start, g_end))

            print(f"\n  CODE diff regije alen vs npro: {len(groups)} bloka")
            for g_start, g_end in groups:
                sz = g_end - g_start + 2
                print(f"    0x{g_start:06X}–0x{g_end+1:06X} ({sz} B)")
                if sz <= 128:
                    v_npro = list(d1[g_start:g_end+2])
                    v_alen = list(d[g_start:g_end+2])
                    print(f"      npro: {[f'{x:02X}' for x in v_npro]}")
                    print(f"      alen: {[f'{x:02X}' for x in v_alen]}")

print()

# ─── 12. FINALNA PROVJERA: TRAŽENJE IGN PO PRVOM REDU ─────────────────────────

print("=" * 70)
print("12. TRAŽENJE REGIONA S UZLAZNIM u8 (ignition-like, 12 uzastopnih)")
print("=" * 70)

d = data.get("npro_spark")
if d:
    found_ign = []
    for addr in range(CODE_START, CODE_END - 144, 1):
        row = list(d[addr:addr+12])
        # Provjeri uzlaznost prvog reda
        if row[0] < 20:
            continue
        if row[-1] > 130:
            continue
        if max(row) - min(row) < 5:
            continue
        # Uzlazno tendencija
        mono = sum(1 for a, b in zip(row, row[1:]) if b >= a)
        if mono < 8:
            continue

        # Provjeri i ostale redove (144B ukupno)
        block = list(d[addr:addr+144])
        good_rows = 0
        for r in range(12):
            rr = block[r*12:(r+1)*12]
            if min(rr) >= 15 and max(rr) <= 130 and max(rr) - min(rr) >= 3:
                good_rows += 1

        if good_rows >= 8:
            found_ign.append((addr, block))

    # Dedupliciraj
    deduped = []
    last_addr = -1000
    for addr, block in found_ign:
        if addr - last_addr >= 144:
            deduped.append((addr, block))
            last_addr = addr

    print(f"  Nađeno {len(deduped)} kandidata:")
    for addr, block in deduped[:30]:
        mn = min(v for r in range(12) for v in block[r*12:(r+1)*12])
        mx = max(v for r in range(12) for v in block[r*12:(r+1)*12])
        row0 = block[:12]
        print(f"  IGN_SIG @ 0x{addr:06X}: raw={mn}–{mx} ({mn*0.75:.1f}°–{mx*0.75:.1f}°), row0={row0}")

print()
print("=" * 70)
print("KRAJ SKENIRANJA")
print("=" * 70)
