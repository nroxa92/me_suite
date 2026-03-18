"""
Binarna analiza Spark 900 ACE ECU - traženje mapa koje nedostaju
Uspoređuje GTI90 (poznate adrese) vs Spark90 (traži ekvivalente)
"""
import sys, os
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Učitaj binarne podatke direktno (bez ME17Engine dependency)
def load_bin(path):
    with open(path, 'rb') as f:
        return f.read()

spark21_path = '_materijali/dumps/2021/900ace/spark90.bin'
spark18_path = '_materijali/dumps/2018/900ace/spark90.bin'
gti21_path   = '_materijali/dumps/2021/900ace/gti90.bin'
stg2_path    = '_materijali/dumps/2018/900ace/spark_stg2'

d_spark21 = load_bin(spark21_path)
d_gti21   = load_bin(gti21_path)
print(f"Spark21: {len(d_spark21):,}B = 0x{len(d_spark21):X}")
print(f"GTI21:   {len(d_gti21):,}B = 0x{len(d_gti21):X}")

try:
    d_spark18 = load_bin(spark18_path)
    print(f"Spark18: {len(d_spark18):,}B = 0x{len(d_spark18):X}")
except:
    d_spark18 = None
    print("Spark18: nije dostupan")

try:
    d_stg2 = load_bin(stg2_path)
    print(f"SparkSTG2: {len(d_stg2):,}B = 0x{len(d_stg2):X}")
except:
    d_stg2 = None
    print("SparkSTG2: nije dostupan")

def u16le(d, a): return int.from_bytes(d[a:a+2], 'little')
def u16be(d, a): return int.from_bytes(d[a:a+2], 'big')
def read_n_le(d, a, n): return [u16le(d, a+i*2) for i in range(n)]
def read_n_be(d, a, n): return [u16be(d, a+i*2) for i in range(n)]
def read_bytes(d, a, n): return list(d[a:a+n])

CODE_START = 0x010000
CODE_END   = 0x060000

print("\n" + "="*70)
print("ANALIZA MAPA KOJE NEDOSTAJU ZA SPARK 900 ACE")
print("="*70)

# ─────────────────────────────────────────────────────────────────
# 1. TORQUE MAPE
# GTI90 @ 0x02A0D8 (16×16 Q8 BE) i 0x02A7F0 (mirror)
# ─────────────────────────────────────────────────────────────────
print("\n--- 1. TORQUE MAPE ---")
gti_torq_addr = 0x02A0D8
n = 16 * 16
gti_torq = read_n_be(d_gti21, gti_torq_addr, n)
print(f"GTI torque @ 0x{gti_torq_addr:06X}: min={min(gti_torq)}, max={max(gti_torq)}, n={n}")
print(f"  Prvih 8 BE: {gti_torq[:8]}")
print(f"  Q8 (/ 256): {[v/256 for v in gti_torq[:8]]}")

# Traži sličnu tablicu u Spark
# Q8 vrijednosti za torque su tipično 50-300 (≈0.2-1.2 normalizovano)
print(f"\nTražim torque-like tablice u Spark (n=256, Q8 range 50-350)...")
hits = []
for base in range(CODE_START, CODE_END - n*2, 2):
    vals = read_n_be(d_spark21, base, n)
    if all(50 <= v <= 350 for v in vals) and (max(vals) - min(vals)) > 30:
        hits.append((base, min(vals), max(vals), vals[:4]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno (BE Q8, 256 vrijednosti)")

# Probaj LE
print(f"\nTražim torque LE u Spark...")
hits_le = []
for base in range(CODE_START, CODE_END - n*2, 2):
    vals = read_n_le(d_spark21, base, n)
    if all(50 <= v <= 350 for v in vals) and (max(vals) - min(vals)) > 30:
        hits_le.append((base, min(vals), max(vals), vals[:4]))
if hits_le:
    for h in hits_le[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno (LE, 256 vrijednosti)")

# Možda torque nije 16x16 u Spark - probaj 12x12
print(f"\nTražim 12×12 torque u Spark (BE, Q8 50-350)...")
n2 = 12*12
hits2 = []
for base in range(CODE_START, CODE_END - n2*2, 2):
    vals = read_n_be(d_spark21, base, n2)
    if all(50 <= v <= 350 for v in vals) and (max(vals) - min(vals)) > 30:
        hits2.append((base, min(vals), max(vals), vals[:4]))
if hits2:
    for h in hits2[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 2. LAMBDA TRIM (korekcija po RPM×load)
# GTI90 @ 0x026DB8 (12×18 Q15 LE)
# ─────────────────────────────────────────────────────────────────
print("\n--- 2. LAMBDA TRIM ---")
gti_ltrim_addr = 0x026DB8
n = 12 * 18  # = 216
gti_ltrim = read_n_le(d_gti21, gti_ltrim_addr, n)
print(f"GTI lambda trim @ 0x{gti_ltrim_addr:06X}: min={min(gti_ltrim)}, max={max(gti_ltrim)}")
print(f"  Q15 (/ 32768): min={min(gti_ltrim)/32768:.4f}, max={max(gti_ltrim)/32768:.4f}")
print(f"  Prvih 8: {gti_ltrim[:8]}")

# Traži u Sparku - 12×18 Q15 LE vrijednosti oko 32768 ± 2000
print(f"\nTražim lambda trim u Spark (n=216, LE, ~32768±4000)...")
hits = []
for base in range(CODE_START, CODE_END - n*2, 2):
    vals = read_n_le(d_spark21, base, n)
    if all(28000 <= v <= 36768 for v in vals) and (max(vals) - min(vals)) > 100:
        hits.append((base, min(vals), max(vals), vals[:4]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno (uski raspon ±4000)")

# Širi raspon
print(f"\nTražim lambda trim u Spark (širi raspon 24000-40000)...")
hits2 = []
for base in range(CODE_START, CODE_END - n*2, 2):
    vals = read_n_le(d_spark21, base, n)
    if all(24000 <= v <= 40000 for v in vals) and (max(vals) - min(vals)) > 200:
        hits2.append((base, min(vals), max(vals), vals[:4]))
if hits2:
    for h in hits2[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 3. LAMBDA BIAS (1×141 Q15 LE)
# GTI90 @ 0x0265D6
# ─────────────────────────────────────────────────────────────────
print("\n--- 3. LAMBDA BIAS ---")
gti_lbias_addr = 0x0265D6
n = 141
gti_lbias = read_n_le(d_gti21, gti_lbias_addr, n)
print(f"GTI lambda bias @ 0x{gti_lbias_addr:06X}: min={min(gti_lbias)}, max={max(gti_lbias)}")
print(f"  Prvih 8: {gti_lbias[:8]}")

# U Sparku ima 4 lambda kopije @ 0x025F5C-0x0262C2, pa tražimo bias negdje blizu
print(f"\nTražim lambda bias u Spark (n=141, LE Q15, ~24000-33000)...")
hits = []
for base in range(CODE_START, CODE_END - n*2, 2):
    vals = read_n_le(d_spark21, base, n)
    if all(24000 <= v <= 34000 for v in vals) and (max(vals) - min(vals)) > 200:
        hits.append((base, min(vals), max(vals), vals[:4]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 4. LAMBDA PROTECTION
# GTI90 @ 0x02469C
# ─────────────────────────────────────────────────────────────────
print("\n--- 4. LAMBDA PROTECTION ---")
gti_lprot_addr = 0x02469C
# Pročitaj 32 vrijednosti da vidimo strukturu
gti_lprot = read_n_le(d_gti21, gti_lprot_addr, 32)
print(f"GTI lambda prot @ 0x{gti_lprot_addr:06X}: {gti_lprot[:16]}")
print(f"  Q15: {[v/32768 for v in gti_lprot[:8]]}")

# Procijeni dimenzije: u300 scan kaže lambda_prot 12×18 Q15
# Traži sliku u Sparku
print(f"\nTražim lambda protection u Spark (n=216, LE, Q15 λ-range)...")
n = 12 * 18
hits = []
for base in range(CODE_START, CODE_END - n*2, 2):
    vals = read_n_le(d_spark21, base, n)
    if all(24000 <= v <= 34000 for v in vals) and (max(vals) - min(vals)) > 200:
        hits.append((base, min(vals), max(vals), vals[:4]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 5. LAMBDA EFF / KFWIRKBA
# GTI90 @ 0x02AE5E (41×18 Q15 LE)
# ─────────────────────────────────────────────────────────────────
print("\n--- 5. LAMBDA EFF (KFWIRKBA) ---")
gti_leff_addr = 0x02AE5E
n_leff = 41 * 18  # = 738
gti_leff = read_n_le(d_gti21, gti_leff_addr, n_leff)
print(f"GTI lambda eff @ 0x{gti_leff_addr:06X}: min={min(gti_leff)}, max={max(gti_leff)}, n={n_leff}")
print(f"  Prvih 8: {gti_leff[:8]}")

# Isti format u Sparku
print(f"\nTražim KFWIRKBA u Spark (n=738, LE Q15, ~30000-36000)...")
hits = []
for base in range(CODE_START, CODE_END - n_leff*2, 2):
    vals = read_n_le(d_spark21, base, n_leff)
    if all(28000 <= v <= 36000 for v in vals) and (max(vals) - min(vals)) > 100:
        hits.append((base, min(vals), max(vals), vals[:4]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno (strogi raspon)")

# Širi
print(f"\nTražim KFWIRKBA u Spark (širi: ~25000-37000)...")
hits2 = []
for base in range(CODE_START, CODE_END - n_leff*2, 2):
    vals = read_n_le(d_spark21, base, n_leff)
    if all(25000 <= v <= 37000 for v in vals) and (max(vals) - min(vals)) > 300:
        hits2.append((base, min(vals), max(vals), vals[:4]))
if hits2:
    for h in hits2[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 6. EFF CORR
# GTI90 @ 0x0259D2 (10×7 Q15 LE, ugrađene Y-osi)
# ─────────────────────────────────────────────────────────────────
print("\n--- 6. EFF CORR ---")
gti_eff_addr = 0x0259D2
n_eff = 10 * 7  # = 70
gti_eff = read_n_le(d_gti21, gti_eff_addr, n_eff)
print(f"GTI eff corr @ 0x{gti_eff_addr:06X}: min={min(gti_eff)}, max={max(gti_eff)}")
print(f"  Prvih 10: {gti_eff[:10]}")
print(f"  Q15: {[v/32768 for v in gti_eff[:8]]}")

# Traži u Sparku
print(f"\nTražim eff corr u Spark (n=70, LE Q15, ~30000-35000)...")
hits = []
for base in range(CODE_START, CODE_END - n_eff*2, 2):
    vals = read_n_le(d_spark21, base, n_eff)
    if all(28000 <= v <= 36000 for v in vals) and (max(vals) - min(vals)) > 100:
        hits.append((base, min(vals), max(vals), vals[:4]))
if hits:
    for h in hits[:15]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first4={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 7. ACCEL ENRICH
# GTI90 @ 0x028059 (5×5 Q14 LE)
# ─────────────────────────────────────────────────────────────────
print("\n--- 7. ACCEL ENRICH ---")
gti_accel_addr = 0x028059
n_accel = 5 * 5  # = 25
gti_accel = read_n_le(d_gti21, gti_accel_addr, n_accel)
print(f"GTI accel enrich @ 0x{gti_accel_addr:06X}: {gti_accel}")
print(f"  Q14 (/16384): {[v/16384 for v in gti_accel]}")

# Traži u Sparku - Q14 ~ 16384 base, enrich values > 16384
print(f"\nTražim accel enrich u Spark (n=25, LE Q14, 16000-30000)...")
hits = []
for base in range(CODE_START, CODE_END - n_accel*2, 2):
    vals = read_n_le(d_spark21, base, n_accel)
    if all(14000 <= v <= 35000 for v in vals) and max(vals) > 17000:
        hits.append((base, min(vals), max(vals), vals))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] vals={h[3]}")
else:
    print("  Nije pronađeno (strogi)")

# Siri raspon
print(f"\nTražim accel enrich u Spark (13000-40000, max>16500)...")
hits2 = []
for base in range(CODE_START, CODE_END - n_accel*2, 2):
    vals = read_n_le(d_spark21, base, n_accel)
    if all(12000 <= v <= 42000 for v in vals) and max(vals) > 16500:
        hits2.append((base, min(vals), max(vals), vals))
if hits2:
    for h in hits2[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] vals={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 8. IGN CORR (paljenje korekcija 2D)
# GTI90 @ 0x022374 (8×8 u8, range 0-180)
# ─────────────────────────────────────────────────────────────────
print("\n--- 8. IGN CORR ---")
gti_ign_corr_addr = 0x022374
n_ign_corr = 8 * 8  # = 64
gti_ign_corr = read_bytes(d_gti21, gti_ign_corr_addr, n_ign_corr)
print(f"GTI ign corr @ 0x{gti_ign_corr_addr:06X}: min={min(gti_ign_corr)}, max={max(gti_ign_corr)}")
print(f"  Prvih 16: {gti_ign_corr[:16]}")

# Traži u Sparku - 8×8 u8, malo je teže jer se preklapa s IGN mapama
# ign corr ima razlicite vrijednosti: uglavnom 0 ili fiksni offset (npr 20-50)
# GTI STG2 ih povisi na 180 za neke. Tražimo tablicu s uglavnom manjim vrijednostima
print(f"\nTražim ign corr u Spark (n=64 bytes, u8, 0-180)...")
hits = []
for base in range(CODE_START, CODE_END - n_ign_corr, 1):
    raw = list(d_spark21[base:base+n_ign_corr])
    # ign_corr: max nije 255, ima mix nula i pozitivnih
    if (all(0 <= v <= 180 for v in raw) and
        max(raw) >= 5 and max(raw) <= 180 and
        raw.count(0) < n_ign_corr // 2):  # nije prazna tablica
        hits.append((base, min(raw), max(raw), raw[:8]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first8={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 9. THERM ENRICH
# GTI90 @ 0x02AA42 (8×7 = 56 u16 LE, /64=%, CTS osa @ 0x02AA32)
# ─────────────────────────────────────────────────────────────────
print("\n--- 9. THERM ENRICH ---")
gti_therm_addr = 0x02AA42
n_therm = 8 * 7  # = 56
gti_therm = read_n_le(d_gti21, gti_therm_addr, n_therm)
print(f"GTI therm enrich @ 0x{gti_therm_addr:06X}: min={min(gti_therm)}, max={max(gti_therm)}")
print(f"  Prvih 8: {gti_therm[:8]}")
print(f"  /64 (%): {[v/64 for v in gti_therm[:8]]}")
# Pročitaj i Y-os (CTS axis)
gti_therm_yax = read_n_le(d_gti21, gti_therm_addr - 0x10, 8)  # 0x02AA32
print(f"  Y-os (CTS) @ 0x{gti_therm_addr-0x10:06X}: {gti_therm_yax}")

# Traži u Sparku - /64 enrich, values 64-1000 (1x = 64, 5x = 320, etc.)
print(f"\nTražim therm enrich u Spark (n=56, LE, 64-2000)...")
hits = []
for base in range(CODE_START, CODE_END - n_therm*2, 2):
    vals = read_n_le(d_spark21, base, n_therm)
    if all(64 <= v <= 2000 for v in vals) and max(vals) > 100:
        hits.append((base, min(vals), max(vals), vals[:6]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first6={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 10. OVERTEMP LAMBDA
# GTI90 @ 0x025ADA (1×63 u16 LE Q15, 0xFFFF=SC bypass)
# Za Spark koji je NA motor, neće biti 0xFFFF bypass
# ─────────────────────────────────────────────────────────────────
print("\n--- 10. OVERTEMP LAMBDA ---")
gti_ovt_addr = 0x025ADA
n_ovt = 63
gti_ovt = read_n_le(d_gti21, gti_ovt_addr, n_ovt)
print(f"GTI overtemp lambda @ 0x{gti_ovt_addr:06X}: min={min(gti_ovt)}, max={max(gti_ovt)}")
print(f"  Prvih 10: {gti_ovt[:10]}")
print(f"  Q15: {[v/32768 for v in gti_ovt[:5]]}")

print(f"\nTražim overtemp lambda u Spark (n=63, LE Q15, 0-33000)...")
hits = []
for base in range(CODE_START, CODE_END - n_ovt*2, 2):
    vals = read_n_le(d_spark21, base, n_ovt)
    if all(0 <= v <= 34000 for v in vals) and min(vals) == 0 and max(vals) > 30000:
        hits.append((base, min(vals), max(vals), vals[:8]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first8={h[3]}")
else:
    print("  Nije pronađeno (s min=0)")

# Možda spark nema 0 u overtemp lambda - traži flat array blizu 32768
print(f"\nTražim overtemp lambda u Spark (n=63, ~30000-34000, monotono ili flat)...")
hits2 = []
for base in range(CODE_START, CODE_END - n_ovt*2, 2):
    vals = read_n_le(d_spark21, base, n_ovt)
    if all(28000 <= v <= 34000 for v in vals):
        hits2.append((base, min(vals), max(vals), vals[:8]))
if hits2:
    for h in hits2[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first8={h[3]}")
else:
    print("  Nije pronađeno")

# ─────────────────────────────────────────────────────────────────
# 11. NEUTRAL CORR
# GTI90 @ 0x025B58 (1×63 u16 LE Q14≈1.004)
# ─────────────────────────────────────────────────────────────────
print("\n--- 11. NEUTRAL CORR ---")
gti_neut_addr = 0x025B58
n_neut = 63
gti_neut = read_n_le(d_gti21, gti_neut_addr, n_neut)
print(f"GTI neutral corr @ 0x{gti_neut_addr:06X}: min={min(gti_neut)}, max={max(gti_neut)}")
print(f"  Prvih 10: {gti_neut[:10]}")
print(f"  Q14 (/16384): {[v/16384 for v in gti_neut[:5]]}")

print(f"\nTražim neutral corr u Spark (n=63, LE Q14≈16500, flat)...")
hits = []
for base in range(CODE_START, CODE_END - n_neut*2, 2):
    vals = read_n_le(d_spark21, base, n_neut)
    if all(16200 <= v <= 16600 for v in vals):
        hits.append((base, min(vals), max(vals), vals[:5]))
if hits:
    for h in hits[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first5={h[3]}")
else:
    print("  Nije pronađeno (16200-16600)")

# Širi
print(f"\nTražim neutral corr u Spark (15000-17500, flat)...")
hits2 = []
for base in range(CODE_START, CODE_END - n_neut*2, 2):
    vals = read_n_le(d_spark21, base, n_neut)
    if all(15000 <= v <= 17500 for v in vals) and (max(vals) - min(vals)) < 200:
        hits2.append((base, min(vals), max(vals), vals[:5]))
if hits2:
    for h in hits2[:10]:
        print(f"  @ 0x{h[0]:06X}: [{h[1]}-{h[2]}] first5={h[3]}")
else:
    print("  Nije pronađeno")

print("\n--- DONE ---")
