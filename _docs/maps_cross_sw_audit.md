# Cross-SW Audit — 1630 ACE Kalibracijske Mape

Datum: 2026-03-19  |  Referenca: 2021/300hp (10SW066726)

## Legenda

| Status | Opis |
|--------|------|
| **SAME** | Identicno referenci (bit-za-bit) |
| **NEAR** | >=99% identicno (<=1% razlike) |
| **DIFF** | 50-99% identicno |
| **DIFF!** | <50% identicno (potpuno razlicito) |
| **MISSING** | Nije pronadeno / sve 0xFF/0x00 |
| **REF** | Ovo je referencni dump |

---

## SW Verzije dumpova

SW string lokacija: `0x001A` (10 ASCII znakova, format `10SWxxxxxx`)

| Dump | SW ID (iz fajla @ 0x001A) | Tip | Napomena |
|------|--------------------------|-----|---------|
| 2018/300hp | `10SW023910` | SC 300hp | Prijelazni SW — GTI legacy injection @ 0x022066 aktivan |
| 2019/300hp | `10SW040039` | SC 300hp | |
| 2020/300hp | `10SW054296` | SC 300hp | |
| 2020/230hp | `10SW053727` | SC 230hp | |
| 2020/170hp | `10SW053729` | NA 170hp | ISTI SW kao 130hp |
| 2020/130hp | `10SW053729` | NA 130hp | ISTI SW kao 170hp |
| 2021/300hp | `10SW066726` | SC 300hp | **REFERENCA** |
| 2021/230hp | `10SW053727` | SC 230hp | ISTI SW string kao 2020/230hp (80B razlike u CODE 0x017F02-0x017F73) |
| 2021/170hp | `10SW053729` | NA 170hp | ISTI SW string kao 2020/170hp (80B razlike u CODE 0x017F02-0x017F73) |
| 2021/130hp | `10SW053729` | NA 130hp | ISTI SW string kao 2020/130hp (80B razlike u CODE 0x017F02-0x017F73) |

**Kljucni nalaz:** 2021/230hp, 170hp i 130hp dijele isti SW string s 2020 verzijama — razlika je samo 80B u CODE regiji @ 0x017F02-0x017F73 (embedded kalibracije u ranom CODE-u, slicno 0x012C80 bloku koji NPRo mijenja). Ovo znaci da su "2021 NA/230" fajlovi zapravo malo izmijenjene 2020 kalibracije, ne novi SW release.

**2020/300 vs 2021/300:** 3173B razlike — pravi novi SW release (drugaciji BOOT + CODE).

---

## Tablica mapa — status po SW verziji

| Mapa | Offset | Velicina | 2018/300hp | 2019/300hp | 2020/300hp | 2020/230hp | 2020/170hp | 2020/130hp | 2021/300hp | 2021/230hp | 2021/170hp | 2021/130hp |
|------|--------|----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **RPM osi** | | | | | | | | | | | | |
| `rpm_axis_1` | `0x024F46` | 32B | SAME | SAME | SAME | SAME | SAME | SAME | **REF** | SAME | SAME | SAME |
| `rpm_axis_2` | `0x025010` | 32B | SAME | SAME | SAME | SAME | SAME | SAME | **REF** | SAME | SAME | SAME |
| `rpm_axis_3` | `0x0250DC` | 32B | SAME | SAME | SAME | SAME | SAME | SAME | **REF** | SAME | SAME | SAME |
| **Rev limiter** | | | | | | | | | | | | |
| `rev_lim_1` | `0x02B72A` | 2B | **DIFF!** (0%) | SAME | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `rev_lim_2` | `0x02B73E` | 2B | **DIFF!** (0%) | SAME | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `rev_lim_sc` | `0x022096` | 2B | SAME | SAME | SAME | **DIFF** (50%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF** (50%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `rev_lim_sc2` | `0x0220B6` | 2B | SAME | SAME | SAME | **DIFF** (50%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF** (50%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `rev_lim_sc3` | `0x0220C0` | 2B | SAME | SAME | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| **Ignition** | | | | | | | | | | | | |
| `ign_base` | `0x02B730` | 2736B | **DIFF** (52.2%) | SAME | SAME | **DIFF!** (38%) | **DIFF!** (11.3%) | **DIFF!** (11.3%) | **REF** | **DIFF!** (38%) | **DIFF!** (11.3%) | **DIFF!** (11.3%) |
| `ign_corr_2d` | `0x022374` | 64B | SAME | SAME | SAME | **DIFF!** (3.1%) | **DIFF!** (3.1%) | **DIFF!** (3.1%) | **REF** | **DIFF!** (3.1%) | **DIFF!** (3.1%) | **DIFF!** (3.1%) |
| **Injection** | | | | | | | | | | | | |
| `inj_main` | `0x02436C` | 384B | SAME | SAME | SAME | SAME | SAME | SAME | **REF** | SAME | SAME | SAME |
| `inj_mirror` | `0x0244EC` | 384B | SAME | SAME | SAME | SAME | SAME | SAME | **REF** | SAME | SAME | SAME |
| `inj_gti` | `0x022066` | 384B | SAME | SAME | SAME | **DIFF!** (6%) | **DIFF!** (0.5%) | **DIFF!** (0.5%) | **REF** | **DIFF!** (6%) | **DIFF!** (0.5%) | **DIFF!** (0.5%) |
| **SC korekcija** | | | | | | | | | | | | |
| `sc_corr` | `0x02220E` | 126B | SAME | SAME | SAME | **DIFF!** (2.4%) | **DIFF!** (0.8%) | **DIFF!** (0.8%) | **REF** | **DIFF!** (2.4%) | **DIFF!** (0.8%) | **DIFF!** (0.8%) |
| `sc_boost` | `0x025DF8` | 80B | SAME | SAME | SAME | **DIFF!** (0%) | **DIFF!** (5%) | **DIFF!** (5%) | **REF** | **DIFF!** (0%) | **DIFF!** (5%) | **DIFF!** (5%) |
| `sc_bypass_1` | `0x020534` | 2B | SAME | SAME | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `sc_bypass_2` | `0x0205A8` | 2B | **DIFF!** (0%) | **DIFF!** (0%) | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `sc_bypass_3` | `0x029993` | 2B | **DIFF!** (0%) | **DIFF!** (0%) | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| **Torque** | | | | | | | | | | | | |
| `torque_main` | `0x02A0D8` | 512B | **DIFF** (63.1%) | **DIFF** (64.1%) | **DIFF** (64.1%) | **DIFF** (71.3%) | **DIFF** (54.3%) | **DIFF** (54.3%) | **REF** | **DIFF** (71.3%) | **DIFF** (54.3%) | **DIFF** (54.3%) |
| `torque_mirror` | `0x02A5F0` | 512B | **DIFF** (63.1%) | **DIFF** (64.1%) | **DIFF** (64.1%) | **DIFF** (71.3%) | **DIFF** (54.3%) | **DIFF** (54.3%) | **REF** | **DIFF** (71.3%) | **DIFF** (54.3%) | **DIFF** (54.3%) |
| **Lambda** | | | | | | | | | | | | |
| `lambda_main` | `0x0266F0` | 432B | **DIFF!** (33.8%) | **DIFF!** (33.8%) | **DIFF!** (33.8%) | **DIFF!** (13.9%) | **DIFF!** (7.9%) | **DIFF!** (7.9%) | **REF** | **DIFF!** (13.9%) | **DIFF!** (7.9%) | **DIFF!** (7.9%) |
| `lambda_mirror` | `0x026C08` | 432B | **DIFF!** (35.4%) | **DIFF!** (35.4%) | **DIFF!** (35.4%) | **DIFF!** (33.1%) | **DIFF!** (35.2%) | **DIFF!** (35.2%) | **REF** | **DIFF!** (33.1%) | **DIFF!** (35.2%) | **DIFF!** (35.2%) |
| `lambda_bias` | `0x0265D6` | 282B | **DIFF** (68.4%) | **DIFF** (68.4%) | **DIFF** (68.4%) | **DIFF!** (0.4%) | **DIFF!** (5.7%) | **DIFF!** (5.7%) | **REF** | **DIFF!** (0.4%) | **DIFF!** (5.7%) | **DIFF!** (5.7%) |
| `lambda_adapt` | `0x0268A0` | 432B | **DIFF** (53%) | **DIFF** (53%) | **DIFF** (53%) | **DIFF!** (14.8%) | **DIFF!** (7.4%) | **DIFF!** (7.4%) | **REF** | **DIFF!** (14.8%) | **DIFF!** (7.4%) | **DIFF!** (7.4%) |
| `lambda_trim` | `0x026DB8` | 432B | **DIFF** (53.2%) | **DIFF** (53.2%) | **DIFF** (53.2%) | **DIFF!** (9.3%) | **DIFF!** (34.3%) | **DIFF!** (34.3%) | **REF** | **DIFF!** (9.3%) | **DIFF!** (34.3%) | **DIFF!** (34.3%) |
| `lambda_eff` | `0x02AE5E` | 1476B | **DIFF!** (3%) | SAME | SAME | **DIFF!** (10.5%) | **DIFF!** (10.4%) | **DIFF!** (10.4%) | **REF** | **DIFF!** (10.5%) | **DIFF!** (10.4%) | **DIFF!** (10.4%) |
| **Gorivo misc** | | | | | | | | | | | | |
| `accel_enrich` | `0x028059` | 50B | **DIFF!** (38%) | **DIFF!** (36%) | SAME | **DIFF** (64%) | **DIFF** (60%) | **DIFF** (60%) | **REF** | **DIFF** (64%) | **DIFF** (60%) | **DIFF** (60%) |
| `temp_fuel_corr` | `0x025E50` | 312B | SAME | SAME | SAME | **DIFF!** (0%) | **DIFF!** (3.8%) | **DIFF!** (3.8%) | **REF** | **DIFF!** (0%) | **DIFF!** (3.8%) | **DIFF!** (3.8%) |
| `start_inj` | `0x025CDC` | 12B | SAME | SAME | SAME | SAME | **DIFF!** (8.3%) | **DIFF!** (8.3%) | **REF** | SAME | **DIFF!** (8.3%) | **DIFF!** (8.3%) |
| `thermal_enrich` | `0x02AA42` | 112B | **DIFF!** (25%) | **DIFF!** (6.2%) | **DIFF!** (6.2%) | SAME | SAME | SAME | **REF** | SAME | SAME | SAME |
| `eff_corr` | `0x0259D2` | 140B | SAME | SAME | SAME | **DIFF** (69.3%) | **DIFF!** (45%) | **DIFF!** (45%) | **REF** | **DIFF** (69.3%) | **DIFF!** (45%) | **DIFF!** (45%) |
| `overtemp_lam` | `0x025ADA` | 126B | **DIFF!** (9.5%) | **DIFF!** (9.5%) | **DIFF!** (9.5%) | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | **DIFF!** (0%) | **DIFF!** (0%) | **DIFF!** (0%) |
| `neutral_corr` | `0x025B58` | 126B | SAME | SAME | SAME | SAME | **DIFF!** (0%) | **DIFF!** (0%) | **REF** | SAME | **DIFF!** (0%) | **DIFF!** (0%) |
| **Knock/Decel** | | | | | | | | | | | | |
| `knock_params` | `0x0256F8` | 104B | SAME | SAME | SAME | SAME | **DIFF** (96.2%) | **DIFF** (96.2%) | **REF** | SAME | **DIFF** (96.2%) | **DIFF** (96.2%) |
| `decel_ramp` | `0x028C30` | 352B | **DIFF!** (2%) | SAME | SAME | **DIFF!** (16.2%) | **DIFF!** (13.4%) | **DIFF!** (13.4%) | **REF** | **DIFF!** (16.2%) | **DIFF!** (13.4%) | **DIFF!** (13.4%) |

---

## Invarijantne mape (identicne u SVIM SW verzijama)

- `rpm_axis_1` @ 0x024F46 (32B) — RPM os 1: [512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 4608, 5120, 5632, 6400, 6912, 7424, 7936, 8448]
- `rpm_axis_2` @ 0x025010 (32B) — RPM os 2: identican sadrzaj
- `rpm_axis_3` @ 0x0250DC (32B) — RPM os 3: identican sadrzaj
- `inj_main` @ 0x02436C (384B) — Injection main: 16x12 Q15, isti u svim SW verzijama i snagama
- `inj_mirror` @ 0x0244EC (384B) — Injection mirror: isto

**Zakljucak:** Injection tablice su ISTE za sve snage (130/170/230/300hp). Snaga se razlikuje kroz ignition, lambda, torque i rev-limiter kalibracije, NE kroz bazne injection vrijednosti.

**Napomena o inj_main:** Mapa ima 12 u16 vrijednosti = 0xFFFF (gornji kraj) — to je dizajnirano, ne padding. Ostale vrijednosti su u rasponu 0x0148-0xBFFF (Q15 koeficijenti, 0.01 do 0.75).

---

## Tuning razlike po kategorijama

### Kategorija A: 300hp vs svi ostali (SC razlike)

Ove mape imaju razlicite vrijednosti specificno za 300hp naspram 230hp:

| Mapa | 300hp (ref) | 230hp (sim%) | 170/130hp (sim%) |
|------|------------|--------------|-----------------|
| `ign_base` | REF | 38% | 11.3% |
| `lambda_main` | REF | 13.9% | 7.9% |
| `torque_main` | REF | 71.3% | 54.3% |
| `decel_ramp` | REF | 16.2% | 13.4% |
| `rev_lim_sc` | 5032t→8223RPM | 5066t→8168RPM | 4729t→8750RPM |

### Kategorija B: SC vs NA (bypass patching)

SC bypass patch kodira razlicite TriCore instrukcije za ukljucivanje/iskljucivanje SC:

| Mapa | 300hp | 230hp | 170/130hp (NA) |
|------|-------|-------|---------------|
| `sc_bypass_1` @ 0x020534 | `2626` | `1f1f` | `1e1e` |
| `sc_bypass_2` @ 0x0205A8 | `2626` | `1f1f` | `1e1e` |
| `sc_bypass_3` @ 0x029993 | `2626` | `1f1f` | `1e1e` |

**Interpretacija:** Svaka snaga ima drugaciji bypass opcode. 0x26=JNZ?, 0x1f/0x1e=drugacije instrukcije. Ovo potvrdjuje da BRP programira iste ECU fizicki, ali s razlicitim SW patchiima po modelu.

**Posebno: 2018 i 2019 imaju razlicite bypass vrijednosti:**
- sc_bypass_2 @ 0x0205A8: 2018=`3333`, 2019=`3333`, 2020+=`2626`
- sc_bypass_3 @ 0x029993: 2018=`3854`, 2019=`3333`, 2020+=`2626`

### Kategorija C: 2018 SW (10SW023910) — prijelazni SW

2018 je poseban slucaj s nekoliko razlika od svih ostalih:

| Mapa | Status vs 2021/300 | Objasnjenje |
|------|-------------------|-------------|
| `ign_base` | DIFF 52.2% | Isti set kao 2019-2020 300hp, ali 2021 je revidiran |
| `lambda_eff` | DIFF! 3% | Jako razlicito — 2018 ima stariji lambda model |
| `decel_ramp` | DIFF! 2% | Gotovo potpuno razlicito |
| `thermal_enrich` | DIFF! 25% | Razlicita obogacivanja pri hladnom startu |
| `overtemp_lam` | DIFF! 9.5% | Razlicite lambda korekcije pri prekotemperaturi |
| `accel_enrich` | DIFF! 38% | Razlicita ubrzavacka obogacivanja |
| `sc_bypass_2/3` | DIFF! | Stariji bypass opcode (0x33, 0x38 naspram 0x26) |
| `inj_gti` @ 0x022066 | SAME kao 2019/2020 300hp | GTI legacy tablica aktivna u 2018/2019 SW |

### Kategorija D: Lambda razlike po snazi

Lambda mape su NAJVARIJABILNIJI set kalibracija:

| SW | lambda_main min | lambda_main max | lambda_main mean |
|----|-----------------|-----------------|------------------|
| 2018/300 | 0.9844 | 1.0798 | 1.0202 |
| 2019/300 | 0.9844 | 1.0798 | 1.0202 |
| 2020/300 | 0.9844 | 1.0798 | 1.0202 |
| 2020/230 | 0.9844 | 1.0307 | 1.0052 |
| 2020/170 | 0.9844 | 1.0258 | 1.0021 |
| 2020/130 | 0.9844 | 1.0258 | 1.0021 |
| **2021/300** | **0.9655** | **1.0730** | **1.0112** |
| 2021/230 | 0.9844 | 1.0307 | 1.0052 |
| 2021/170 | 0.9844 | 1.0258 | 1.0021 |
| 2021/130 | 0.9844 | 1.0258 | 1.0021 |

**Kljucni nalaz:** 2021/300hp ima NIZI minimum lambda (0.9655 vs 0.9844) — agresivniji bogati uvjeti pod opterecenjem.

---

## RPM osi — vrijednosti (zajednicke svim SW verzijama)

Sve tri RPM osi su identicne kroz sve SW verzije:

`[512, 1024, 1536, 2048, 2560, 3072, 3584, 4096, 4608, 5120, 5632, 6400, 6912, 7424, 7936, 8448]`

Korak nije ravnomjeran — gustiji u niskoRPM (512 RPM korak) i rjedi gore, s paukom na 5632→6400 (768 RPM skok).

---

## Rev limiter vrijednosti (ticks → RPM)

Formula: `RPM = 40MHz × 60 / (ticks × 58)`

| Mapa | 300hp (SC) | 230hp (SC) | 170/130hp (NA) | 2018/300 |
|------|-----------|-----------|----------------|---------|
| `rev_lim_sc` @ 0x022096 | 5032t → **8223 RPM** | 5066t → 8168 RPM | 4729t → 8750 RPM | 5032t → 8223 RPM |
| `rev_lim_sc2` @ 0x0220B6 | 6412t → 6453 RPM | 6564t → 6304 RPM | 5662t → 7308 RPM | 6412t → 6453 RPM |
| `rev_lim_sc3` @ 0x0220C0 | 5936t → 6971 RPM | 6252t → 6619 RPM | 5245t → 7889 RPM | 5936t → 6971 RPM |
| `rev_lim_1` @ 0x02B72A | 8738t → 4736 RPM | 8993t → 4601 RPM | 8481t → 4879 RPM | 9764t → 4238 RPM |
| `rev_lim_2` @ 0x02B73E | 8738t → 4736 RPM | 8993t → 4601 RPM | 8481t → 4879 RPM | 9764t → 4238 RPM |

**Napomena:** rev_lim_1 i rev_lim_2 (~4600-4900 RPM) su ocito ne maksimalne vrijednosti — vjerojatno su to prijelazni RPM ili startni limiti, ne hard-cut. Pravi hard-cut je u rev_lim_sc bloku (~8000+ RPM).

**Paradoks NA:** NA varijante (170/130hp) imaju VISI RPM limit u nekim scalerima (8750 RPM naspram 8223 za 300hp SC). Ovo je konzistentno s dokumentacijom da NA nema SC tlak koji bi ugrozio motor na visokim RPM, pa ima visi limit.

---

## SC bypass vrijednosti

| Mapa | Offset | 300hp (SC) | 230hp (SC) | 170/130hp (NA) | 2018/300 | 2019/300 |
|------|--------|-----------|-----------|----------------|---------|---------|
| `sc_bypass_1` | `0x020534` | `2626` | `1f1f` | `1e1e` | `2626` | `2626` |
| `sc_bypass_2` | `0x0205A8` | `2626` | `1f1f` | `1e1e` | `3333` | `3333` |
| `sc_bypass_3` | `0x029993` | `2626` | `1f1f` | `1e1e` | `3854` | `3333` |

**Interpretacija sc_bypass_1 razlike 2018→2019:** sc_bypass_1 je SAME za sve 300hp (0x2626), ali sc_bypass_2 i sc_bypass_3 su razliciti u 2018 i 2019. Ovo sugerira da Bosch/BRP mijenja vise bypass lokacija pri SW update-ima, a jedna kopija ostaje "legacy".

---

## Torque mapa — min/max (BE u16 Q8)

| SW verzija | min (Q8) | max (Q8) | mean (Q8) | min Nm | max Nm |
|-----------|---------|---------|---------|--------|--------|
| 2018/300hp | 27904 | 35840 | 32642 | ~109 | ~140 |
| 2019/300hp | 27904 | 35840 | 32637 | ~109 | ~140 |
| 2020/300hp | 27904 | 35840 | 32637 | ~109 | ~140 |
| 2020/230hp | 31232 | 36864 | 33785 | ~122 | ~144 |
| 2020/170hp | 32768 | 38400 | 34850 | ~128 | ~150 |
| 2020/130hp | 32768 | 38400 | 34850 | ~128 | ~150 |
| **2021/300hp** | **30464** | **39168** | **33109** | **~119** | **~153** |
| 2021/230hp | 31232 | 36864 | 33785 | ~122 | ~144 |
| 2021/170hp | 32768 | 38400 | 34850 | ~128 | ~150 |
| 2021/130hp | 32768 | 38400 | 34850 | ~128 | ~150 |

*Nm procjena: Q8 val / 256. Ovo je relativni koeficijent, ne apsolutne vrijednosti u Nm.*

**Nalaz:** 2021/300hp ima NAJSIRI raspon torque mape (min 30464, max 39168 — najveci max od svih). Ovo je konzistentno s performansnim poboljsanjima 2021 godista.

**Paradoks NA torque:** NA varijante imaju VISI minimum torque koeficijenta od SC! Ovo se objasnjava time da NA motori rade na stoichiometrijskom lambda (bez bogatenja za SC hladjenje), pa je torque mapa kalibirana visoko-ravnomjerno kroz cijeli RPM opseg. SC modeli imaju nizi minimum jer SC bogatenje pri niskim RPM smanjuje iskoristivost.

---

## Injection main (inj_main) — detaljna analiza

**Status: SAME svugdje — ova mapa je INVARIJANTNA.**

Matrica 16x12 (LE u16 Q15), korak prikaza po stupcima (16 RPM tacaka x 12 load tacaka):

```
row00 (lowest load): 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000
row01:               0000...0000 0148 0148 0148 0148 0148 0148 0148 0148
row02:               0148 0148 0148 0148 0361 0361 0361 0361 0361 0361 0361 0361 0361 0361 0361 0361
...
row10:               7d70...7d70 bfff bfff bfff bfff bfff bfff bfff bfff
row11 (max load):    bfff...bfff ffff ffff ffff ffff ffff ffff ffff ffff
```

Zakljucak: Injection main je baza — jednaka za sve snage. Stvarna kolicina goriva ovisi o torque limitu, lambda tablicama i SC korekcijama.

---

## Napomene i interpretacije

1. **Injection je bazna mapa** — `inj_main` i `inj_mirror` su IDENTIČNI za sve snage od 2018 do 2021. Razlika snage realizira se kroz torque, lambda i SC korekcijske mape.

2. **SC bypass kodiranje:** Svaki power level ima drugaciji 2-bajtni opcode: 300hp=`2626`, 230hp=`1f1f`, 170/130hp=`1e1e`. U 2018 je kodiran drugacije (`3354`/`3854`), sto sugerira da je Bosch promijenio pristup SC bypass implementaciji.

3. **GTI legacy (inj_gti @ 0x022066):** Aktivni sadrzaj u 2018/2019/2020/2021 300hp SW — ali sadrzaj u 230/170/130hp je potpuno razlicit (0.5-6% slicnost). Potvrduje da nije aktivna tablica u tim SW verzijama.

4. **2021 NA dumpovi nisu novi SW** — 2021/230, 170 i 130 koriste isti SW string kao 2020 varijante, s razlikom od samo 80B u CODE regiji @ 0x017F02-0x017F73. Ovo je moguce kalibracijsko podrucje ugradjeno u strojni kod (slicno 0x012C80 bloku).

5. **Torque mapa je kljucna tuning varijabla** — razlikuje se i po snazi i po godisnjoj verziji. 2021/300hp ima najsiri torque raspon. Tablica je BE u16 (ne LE kao injection).

6. **Lambda najvariabilnija** — sve lambda mape imaju <40% slicnost izmedju 300hp i NA varijanti. 2021/300 jedini ima lambda min ispod 0.9844 (bogatiji uvjeti).

7. **CAL regija nije pregledavana** — sve adrese su u CODE regiji (0x010000-0x05FFFF). CAL regija je TriCore bytekod, ne kalibracija.

---

## Preporuke za tuning

| Mapa | Prioritet za tune | Razlog |
|------|------------------|--------|
| `ign_base` | VISOK | Najveca razlika po snazi (11-52%), direktan utjecaj na performanse |
| `lambda_main` | VISOK | Kljucna za AFR ciljeve po RPM/loadu, jako razlicita izmedju modela |
| `torque_main` | SREDNJI | Limitira maksimalnu snagu ECU izlaza |
| `rev_lim_sc` | SREDNJI | Direktno postavlja RPM granicu |
| `lambda_bias` | NIZAK | Korekcija baze, manje kriticna |
| `decel_ramp` | NIZAK | Samo DFCO ponasanje |
| `inj_main` | NE MIJENJATI | Invarijantan, nije tuning varijabla u ovom ECU |

---

*Generirano: cross_sw_audit.py | Samo citanje binarnih fajlova, bez modifikacija.*
