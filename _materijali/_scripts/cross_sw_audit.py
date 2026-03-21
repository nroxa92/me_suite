#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-SW audit kalibracijskih mapa za Bosch ME17.8.5 (Sea-Doo 1630 ACE).
Cita binarne dumpove, usporeduje mape s referencnim dumpom (2021/300.bin).
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import struct
from pathlib import Path

BASE = Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/dumps")

DUMPS = [
    ("2018", "300",  "10SW023910", BASE / "2018/1630ace/300.bin"),
    ("2019", "300",  "10SW040039", BASE / "2019/1630ace/300.bin"),
    ("2020", "300",  "10SW054296", BASE / "2020/1630ace/300.bin"),
    ("2020", "230",  "10SW053727", BASE / "2020/1630ace/230.bin"),
    ("2020", "170",  "10SW053729", BASE / "2020/1630ace/170.bin"),
    ("2020", "130",  "10SW053729", BASE / "2020/1630ace/130.bin"),
    ("2021", "300",  "10SW066726", BASE / "2021/1630ace/300.bin"),  # REF
    ("2021", "230",  "?",          BASE / "2021/1630ace/230.bin"),
    ("2021", "170",  "?",          BASE / "2021/1630ace/170.bin"),
    ("2021", "130",  "?",          BASE / "2021/1630ace/130.bin"),
]

REF_IDX = 6  # 2021/300.bin

MAPS_REF = {
    "rpm_axis_1":     (0x024F46, 32),
    "rpm_axis_2":     (0x025010, 32),
    "rpm_axis_3":     (0x0250DC, 32),
    "rev_lim_1":      (0x02B72A, 2),
    "rev_lim_2":      (0x02B73E, 2),
    "rev_lim_sc":     (0x022096, 2),
    "rev_lim_sc2":    (0x0220B6, 2),
    "rev_lim_sc3":    (0x0220C0, 2),
    "ign_base":       (0x02B730, 144*19),
    "inj_main":       (0x02436C, 16*12*2),
    "inj_mirror":     (0x0244EC, 16*12*2),
    "inj_gti":        (0x022066, 16*12*2),
    "sc_corr":        (0x02220E, 9*7*2),
    "torque_main":    (0x02A0D8, 16*16*2),
    "torque_mirror":  (0x02A5F0, 16*16*2),
    "lambda_main":    (0x0266F0, 12*18*2),
    "lambda_mirror":  (0x026C08, 12*18*2),
    "lambda_bias":    (0x0265D6, 141*2),
    "lambda_adapt":   (0x0268A0, 12*18*2),
    "lambda_trim":    (0x026DB8, 12*18*2),
    "accel_enrich":   (0x028059, 5*5*2),
    "temp_fuel_corr": (0x025E50, 156*2),
    "start_inj":      (0x025CDC, 6*2),
    "ign_corr_2d":    (0x022374, 8*8),
    "thermal_enrich": (0x02AA42, 8*7*2),
    "eff_corr":       (0x0259D2, 10*7*2),
    "overtemp_lam":   (0x025ADA, 63*2),
    "neutral_corr":   (0x025B58, 63*2),
    "sc_boost":       (0x025DF8, 40*2),
    "lambda_eff":     (0x02AE5E, 41*18*2),
    "sc_bypass_1":    (0x020534, 2),
    "sc_bypass_2":    (0x0205A8, 2),
    "sc_bypass_3":    (0x029993, 2),
    "knock_params":   (0x0256F8, 104),
    "decel_ramp":     (0x028C30, 16*11*2),
    "lambda_adapt2":  (0x0268A0, 12*18*2),
}

# SC-only mape (NA varijante neće ih imati valjano)
SC_ONLY = {"rev_lim_sc", "rev_lim_sc2", "rev_lim_sc3", "sc_corr", "sc_boost",
           "sc_bypass_1", "sc_bypass_2", "sc_bypass_3", "ign_corr_2d"}

# GTI legacy - samo 2018 SW
GTI_LEGACY = {"inj_gti"}

SEARCH_RANGE = 2048  # +-2KB za signature search


def read_sw(data: bytes) -> str:
    try:
        raw = data[0x0008:0x0018]
        s = raw.decode("ascii", errors="replace").rstrip("\x00 ")
        return s
    except Exception:
        return "?"


def is_valid_data(data: bytes) -> bool:
    """Provjera je li blok razuman (nije sve 0xFF ili sve 0x00)."""
    if len(data) == 0:
        return False
    if len(data) <= 4:
        return True  # scalari su uvijek OK
    all_ff = all(b == 0xFF for b in data)
    all_00 = all(b == 0x00 for b in data)
    return not all_ff and not all_00


def signature_search(haystack: bytes, needle: bytes, ref_offset: int, search_range: int = SEARCH_RANGE) -> int | None:
    """Traži prvih 8B needle-a u +-search_range od ref_offset. Vraća novi offset ili None."""
    if len(needle) < 8:
        return None
    sig = needle[:8]
    lo = max(0, ref_offset - search_range)
    hi = min(len(haystack) - len(sig), ref_offset + search_range)
    idx = haystack.find(sig, lo, hi + len(sig))
    if idx == -1:
        return None
    return idx


def diff_bytes(a: bytes, b: bytes) -> tuple[int, float]:
    """Vraća (broj različitih bajtova, % sličnosti)."""
    if len(a) != len(b):
        l = min(len(a), len(b))
        a, b = a[:l], b[:l]
    diffs = sum(x != y for x, y in zip(a, b))
    pct = 100.0 * (len(a) - diffs) / len(a) if len(a) > 0 else 100.0
    return diffs, pct


def decode_rpm_axis(data: bytes) -> list[int]:
    """Dekodira RPM os: 16× u16 BE."""
    if len(data) < 32:
        return []
    return [struct.unpack_from(">H", data, i*2)[0] for i in range(16)]


def decode_u16le_scalar(data: bytes) -> int:
    if len(data) >= 2:
        return struct.unpack_from("<H", data)[0]
    return 0


def rpm_from_ticks(ticks: int) -> float:
    """RPM = 40MHz × 60 / (ticks × 58)"""
    if ticks == 0:
        return 0.0
    return 40_000_000 * 60 / (ticks * 58)


def main():
    # Učitaj sve dumpove
    binaries = []
    for year, hp, sw_id, path in DUMPS:
        if path.exists():
            data = path.read_bytes()
            sw_read = read_sw(data)
            binaries.append({
                "year": year, "hp": hp, "sw_id": sw_id,
                "sw_read": sw_read, "data": data, "path": path,
                "size": len(data)
            })
            print(f"Učitan: {year}/{hp}hp — SW iz fajla: {sw_read} — {len(data)//1024}KB")
        else:
            print(f"NEDOSTAJE: {path}")
            binaries.append(None)

    ref = binaries[REF_IDX]
    print(f"\nReferenca: {ref['year']}/{ref['hp']}hp — {ref['sw_id']}\n")

    # Za svaku mapu izvuci referentne podatke
    ref_data_map = {}
    for map_name, (offset, size) in MAPS_REF.items():
        if offset + size <= len(ref["data"]):
            ref_data_map[map_name] = ref["data"][offset:offset+size]
        else:
            ref_data_map[map_name] = b""

    # Analiza po dumpu
    results = {}  # map_name -> {dump_key -> status_dict}

    for b in binaries:
        if b is None:
            continue
        key = f"{b['year']}/{b['hp']}hp"
        for map_name, (ref_offset, size) in MAPS_REF.items():
            raw = b["data"][ref_offset:ref_offset+size] if ref_offset + size <= len(b["data"]) else b""
            ref_raw = ref_data_map.get(map_name, b"")

            valid = is_valid_data(raw)
            found_offset = ref_offset
            found_by_sig = False

            # Ako nije validan, pokušaj signature search
            if (not valid or len(raw) == 0) and len(ref_raw) >= 8:
                sig_offset = signature_search(b["data"], ref_raw, ref_offset)
                if sig_offset is not None:
                    raw = b["data"][sig_offset:sig_offset+size]
                    found_offset = sig_offset
                    found_by_sig = True
                    valid = is_valid_data(raw)

            if not valid:
                status = "MISSING"
                diff_n, sim_pct = 0, 0.0
            elif raw == ref_raw:
                status = "SAME"
                diff_n, sim_pct = 0, 100.0
            else:
                diff_n, sim_pct = diff_bytes(raw, ref_raw)
                if sim_pct >= 99.0:
                    status = "NEAR"
                elif sim_pct >= 50.0:
                    status = "DIFF"
                else:
                    status = "DIFF!"

            entry = {
                "status": status,
                "diff_n": diff_n,
                "sim_pct": sim_pct,
                "offset": found_offset,
                "found_by_sig": found_by_sig,
                "raw": raw,
                "valid": valid,
            }
            results.setdefault(map_name, {})[key] = entry

    # ---- Detaljna analiza RPM osi i Rev limitera ----
    print("\n=== RPM OSEDETALJI ===")
    for rmap in ["rpm_axis_1", "rpm_axis_2", "rpm_axis_3"]:
        offset, size = MAPS_REF[rmap]
        print(f"\n{rmap} @ 0x{offset:06X}:")
        for b in binaries:
            if b is None: continue
            raw = b["data"][offset:offset+size]
            rpms = decode_rpm_axis(raw)
            key = f"{b['year']}/{b['hp']}hp"
            print(f"  {key:20s}: {rpms}")

    print("\n=== REV LIMITER (ticks → RPM) ===")
    for rmap in ["rev_lim_1", "rev_lim_2", "rev_lim_sc", "rev_lim_sc2", "rev_lim_sc3"]:
        offset, _ = MAPS_REF[rmap]
        print(f"\n{rmap} @ 0x{offset:06X}:")
        for b in binaries:
            if b is None: continue
            raw = b["data"][offset:offset+2]
            ticks = decode_u16le_scalar(raw)
            rpm = rpm_from_ticks(ticks)
            key = f"{b['year']}/{b['hp']}hp"
            print(f"  {key:20s}: {ticks} ticks → {rpm:.0f} RPM  (raw: {raw.hex()})")

    print("\n=== SC BYPASS VALUES ===")
    for rmap in ["sc_bypass_1", "sc_bypass_2", "sc_bypass_3"]:
        offset, _ = MAPS_REF[rmap]
        print(f"\n{rmap} @ 0x{offset:06X}:")
        for b in binaries:
            if b is None: continue
            raw = b["data"][offset:offset+2]
            key = f"{b['year']}/{b['hp']}hp"
            print(f"  {key:20s}: {raw.hex()}")

    # ---- Injection main — statistike ----
    print("\n=== INJECTION MAIN — min/max po SW ===")
    for b in binaries:
        if b is None: continue
        offset, size = MAPS_REF["inj_main"]
        raw = b["data"][offset:offset+size]
        if len(raw) == size:
            vals = [struct.unpack_from("<H", raw, i*2)[0] for i in range(size//2)]
            print(f"  {b['year']}/{b['hp']}hp: min={min(vals)} max={max(vals)} mean={sum(vals)//len(vals)}")

    # ---- Torque main — statistike ----
    print("\n=== TORQUE MAIN — min/max po SW ===")
    for b in binaries:
        if b is None: continue
        offset, size = MAPS_REF["torque_main"]
        raw = b["data"][offset:offset+size]
        if len(raw) == size:
            vals = [struct.unpack_from(">H", raw, i*2)[0] for i in range(size//2)]
            print(f"  {b['year']}/{b['hp']}hp: min={min(vals)} max={max(vals)} mean={sum(vals)//len(vals)}")

    # ---- Lambda main — statistike ----
    print("\n=== LAMBDA MAIN — min/max po SW ===")
    for b in binaries:
        if b is None: continue
        offset, size = MAPS_REF["lambda_main"]
        raw = b["data"][offset:offset+size]
        if len(raw) == size:
            vals = [struct.unpack_from("<H", raw, i*2)[0] for i in range(size//2)]
            # Q15: val / 32768.0
            fvals = [v/32768.0 for v in vals]
            print(f"  {b['year']}/{b['hp']}hp: min={min(fvals):.4f} max={max(fvals):.4f} mean={sum(fvals)/len(fvals):.4f}")

    # ---- Identificiraj invarijantne vs. tuning mape ----
    print("\n=== INVARIJANTNOST ANALIZA ===")
    invariant_maps = []
    tuning_maps = []
    missing_maps = []

    for map_name in MAPS_REF:
        statuses = [v["status"] for v in results.get(map_name, {}).values()]
        all_same = all(s == "SAME" for s in statuses)
        any_missing = any(s == "MISSING" for s in statuses)
        any_diff = any(s in ("DIFF", "DIFF!") for s in statuses)

        if all_same:
            invariant_maps.append(map_name)
        elif any_missing and not any_diff:
            missing_maps.append(map_name)
        else:
            tuning_maps.append(map_name)

    print(f"Invarijantne (SAME svugdje): {invariant_maps}")
    print(f"Tuning razlike:              {tuning_maps}")
    print(f"Djelomično nedostajuće:      {missing_maps}")

    # ---- Generiraj Markdown izvještaj ----
    dump_keys = [f"{b['year']}/{b['hp']}hp" for b in binaries if b is not None]
    dump_sws  = [b['sw_id'] for b in binaries if b is not None]

    md_lines = []
    md_lines.append("# Cross-SW Audit — 1630 ACE Kalibracijske Mape")
    md_lines.append("")
    md_lines.append(f"Datum: 2026-03-19  |  Referenca: 2021/300hp (10SW066726)")
    md_lines.append("")
    md_lines.append("## Legenda")
    md_lines.append("| Status | Opis |")
    md_lines.append("|--------|------|")
    md_lines.append("| **SAME** | Identično referenci (bit-za-bit) |")
    md_lines.append("| **NEAR** | ≥99% identično (≤1% razlike) |")
    md_lines.append("| **DIFF** | 50–99% identično |")
    md_lines.append("| **DIFF!** | <50% identično (potpuno različito) |")
    md_lines.append("| **MISSING** | Nije pronađeno / sve 0xFF/0x00 |")
    md_lines.append("| **REF** | Ovo je referentni dump |")
    md_lines.append("")
    md_lines.append("## SW Verzije dumpova")
    md_lines.append("")
    for b in binaries:
        if b is None: continue
        sc_mark = " (SC)" if b['hp'] in ("300", "230") else " (NA)"
        md_lines.append(f"- **{b['year']}/{b['hp']}hp**: SW={b['sw_id']} | iz fajla: `{b['sw_read']}`{sc_mark} | veličina: {b['size']//1024}KB")
    md_lines.append("")

    # Headeri tablice
    md_lines.append("## Tablica mapa — status po SW verziji")
    md_lines.append("")

    header = "| Mapa | Offset | Veličina |"
    sep    = "|------|--------|---------|"
    for dk in dump_keys:
        header += f" {dk} |"
        sep    += "---------|"
    md_lines.append(header)
    md_lines.append(sep)

    # Grupiranje mapa po kategoriji
    categories = {
        "RPM osi": ["rpm_axis_1", "rpm_axis_2", "rpm_axis_3"],
        "Rev limiter": ["rev_lim_1", "rev_lim_2", "rev_lim_sc", "rev_lim_sc2", "rev_lim_sc3"],
        "Ignition": ["ign_base", "ign_corr_2d"],
        "Injection": ["inj_main", "inj_mirror", "inj_gti"],
        "SC korekcija": ["sc_corr", "sc_boost", "sc_bypass_1", "sc_bypass_2", "sc_bypass_3"],
        "Torque": ["torque_main", "torque_mirror"],
        "Lambda": ["lambda_main", "lambda_mirror", "lambda_bias", "lambda_adapt", "lambda_adapt2", "lambda_trim", "lambda_eff"],
        "Gorivo misc": ["accel_enrich", "temp_fuel_corr", "start_inj", "thermal_enrich", "eff_corr",
                        "overtemp_lam", "neutral_corr"],
        "Knock/Decel": ["knock_params", "decel_ramp"],
    }

    for cat_name, map_list in categories.items():
        md_lines.append(f"| **{cat_name}** | | | " + " | ".join([""] * len(dump_keys)) + " |")
        for map_name in map_list:
            if map_name not in MAPS_REF:
                continue
            offset, size = MAPS_REF[map_name]
            row = f"| `{map_name}` | `0x{offset:06X}` | {size}B |"
            for dk in dump_keys:
                entry = results.get(map_name, {}).get(dk)
                if entry is None:
                    row += " — |"
                    continue
                s = entry["status"]
                if dk == "2021/300hp":
                    row += " **REF** |"
                elif s == "SAME":
                    row += " SAME |"
                elif s == "NEAR":
                    row += f" NEAR ({entry['sim_pct']:.1f}%) |"
                elif s in ("DIFF", "DIFF!"):
                    row += f" **{s}** ({entry['sim_pct']:.1f}%) |"
                elif s == "MISSING":
                    row += " ~~MISSING~~ |"
                else:
                    row += f" {s} |"
            md_lines.append(row)

    md_lines.append("")
    md_lines.append("## Invarijantne mape (identične u svim SW verzijama)")
    md_lines.append("")
    if invariant_maps:
        for m in invariant_maps:
            offset, size = MAPS_REF[m]
            md_lines.append(f"- `{m}` @ 0x{offset:06X} ({size}B)")
    else:
        md_lines.append("*Nema potpuno invarijantnih mapa.*")
    md_lines.append("")

    md_lines.append("## Tuning razlike (razlikuju se između snaga/SW verzija)")
    md_lines.append("")
    if tuning_maps:
        for m in tuning_maps:
            offset, size = MAPS_REF[m]
            # Skupi statuse
            st_str = ", ".join(f"{k}:{v['status']} ({v['sim_pct']:.1f}%)"
                               for k, v in sorted(results.get(m, {}).items()) if k != "2021/300hp")
            md_lines.append(f"- `{m}` @ 0x{offset:06X}: {st_str}")
    md_lines.append("")

    md_lines.append("## RPM osi — vrijednosti")
    md_lines.append("")
    for rmap in ["rpm_axis_1", "rpm_axis_2", "rpm_axis_3"]:
        offset, size = MAPS_REF[rmap]
        md_lines.append(f"### {rmap} @ 0x{offset:06X}")
        md_lines.append("")
        md_lines.append("| SW verzija | RPM točke (16×) |")
        md_lines.append("|-----------|-----------------|")
        for b in binaries:
            if b is None: continue
            raw = b["data"][offset:offset+size]
            rpms = decode_rpm_axis(raw)
            key = f"{b['year']}/{b['hp']}hp"
            md_lines.append(f"| {key} | {rpms} |")
        md_lines.append("")

    md_lines.append("## Rev limiter vrijednosti")
    md_lines.append("")
    md_lines.append("| Mapa | Offset |" + "".join(f" {b['year']}/{b['hp']}hp |" for b in binaries if b is not None))
    md_lines.append("|------|--------|" + "--------|" * len(dump_keys))
    for rmap in ["rev_lim_1", "rev_lim_2", "rev_lim_sc", "rev_lim_sc2", "rev_lim_sc3"]:
        offset, _ = MAPS_REF[rmap]
        row = f"| `{rmap}` | `0x{offset:06X}` |"
        for b in binaries:
            if b is None: continue
            raw = b["data"][offset:offset+2]
            ticks = decode_u16le_scalar(raw)
            rpm = rpm_from_ticks(ticks)
            row += f" {ticks}t→{rpm:.0f}RPM |"
        md_lines.append(row)
    md_lines.append("")

    md_lines.append("## Injection main — min/max vrijednosti")
    md_lines.append("")
    md_lines.append("| SW verzija | min | max | mean |")
    md_lines.append("|-----------|-----|-----|------|")
    for b in binaries:
        if b is None: continue
        offset, size = MAPS_REF["inj_main"]
        raw = b["data"][offset:offset+size]
        if len(raw) == size:
            vals = [struct.unpack_from("<H", raw, i*2)[0] for i in range(size//2)]
            md_lines.append(f"| {b['year']}/{b['hp']}hp | {min(vals)} | {max(vals)} | {sum(vals)//len(vals)} |")
    md_lines.append("")

    md_lines.append("## Lambda main — min/max (Q15 → float)")
    md_lines.append("")
    md_lines.append("| SW verzija | min λ | max λ | mean λ |")
    md_lines.append("|-----------|-------|-------|--------|")
    for b in binaries:
        if b is None: continue
        offset, size = MAPS_REF["lambda_main"]
        raw = b["data"][offset:offset+size]
        if len(raw) == size:
            vals = [struct.unpack_from("<H", raw, i*2)[0]/32768.0 for i in range(size//2)]
            md_lines.append(f"| {b['year']}/{b['hp']}hp | {min(vals):.4f} | {max(vals):.4f} | {sum(vals)/len(vals):.4f} |")
    md_lines.append("")

    md_lines.append("## SC bypass vrijednosti")
    md_lines.append("")
    md_lines.append("| Mapa | Offset |" + "".join(f" {b['year']}/{b['hp']}hp |" for b in binaries if b is not None))
    md_lines.append("|------|--------|" + "--------|" * len(dump_keys))
    for rmap in ["sc_bypass_1", "sc_bypass_2", "sc_bypass_3"]:
        offset, _ = MAPS_REF[rmap]
        row = f"| `{rmap}` | `0x{offset:06X}` |"
        for b in binaries:
            if b is None: continue
            raw = b["data"][offset:offset+2]
            row += f" `{raw.hex()}` |"
        md_lines.append(row)
    md_lines.append("")

    md_lines.append("## Napomene")
    md_lines.append("")
    md_lines.append("- SC mape (sc_corr, sc_boost, sc_bypass_*) su prisutne u svim dumpovima jer ECU HW podržava SC")
    md_lines.append("- NA varijante (130/170hp) imaju SC bypass kod koji deaktivira SC funkciju")
    md_lines.append("- `inj_gti` @ 0x022066 je GTI legacy iz 2018 SW (10SW023910) — drugi SWovi imaju neaktivan/drugačiji sadržaj")
    md_lines.append("- lambda_adapt i lambda_adapt2 su iste adrese (0x0268A0) — duplikat u MAPS_REF, normalno")
    md_lines.append("- Offset 0x028059 (accel_enrich) je neparan — očekivano za u8/Q14 mješovite tablice")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("*Generirano: cross_sw_audit.py | Samo čitanje, bez modifikacija binarnih fajlova.*")

    out_path = Path("C:/Users/SeaDoo/Desktop/me_suite/_materijali/maps_cross_sw_audit.md")
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n✓ Markdown izvještaj spašen: {out_path}")


if __name__ == "__main__":
    main()
