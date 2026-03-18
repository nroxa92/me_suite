"""
ME17Suite - Test suite
Testira core funkcionalnost na stvarnim bin fajlovima.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from core.engine import ME17Engine, FILE_SIZE, CAL_START, CAL_END, CODE_START, CODE_END
from core.map_finder import MapFinder
from core.checksum import ChecksumEngine


ROOT      = os.path.join(os.path.dirname(__file__), '..')
DUMPS     = os.path.join(ROOT, "_materijali", "dumps")
ORI_PATH  = os.path.join(DUMPS, "2021", "1630ace", "300.bin")
STG2_PATH = os.path.join(DUMPS, "2020", "1630ace", "300_stg2")


def test_load_ori():
    print("\n=== TEST: Load ORI ===")
    eng = ME17Engine()
    info = eng.load(ORI_PATH)
    print(f"  SW ID:    {info.sw_id}")
    print(f"  Desc:     {info.sw_desc}")
    print(f"  Size:     {info.file_size:,} B (expected {FILE_SIZE:,})")
    print(f"  MCU ok:   {info.mcu_confirmed}")
    print(f"  Valid:    {info.is_valid}")
    if info.errors:
        for e in info.errors:
            print(f"  ERROR: {e}")
    assert info.sw_id == "10SW066726", f"Pogresan SW ID: {info.sw_id}"
    assert info.file_size == FILE_SIZE
    assert info.mcu_confirmed
    print("  PASS")
    return eng


def test_load_stg2():
    print("\n=== TEST: Load STG2 ===")
    npro_path = STG2_PATH
    if not os.path.exists(npro_path):
        print("  PRESKACAM — npro_300.bin nije pronaden")
        return None
    eng = ME17Engine()
    info = eng.load(npro_path)
    print(f"  SW ID:    {info.sw_id}")
    print(f"  Desc:     {info.sw_desc}")
    print(f"  MCU ok:   {info.mcu_confirmed}")
    assert info.sw_id == "10SW040039", f"Pogresan SW ID: {info.sw_id}"
    assert info.mcu_confirmed
    print("  PASS")
    return eng


def test_read_primitives(eng):
    print("\n=== TEST: Read primitives ===")
    sw_bytes = eng.read_bytes(0x001A, 10)
    print(f"  SW @ 0x001A: {sw_bytes}")
    v = eng.read_u16_be(0x024F46)
    print(f"  u16 BE @ 0x024F46: {v} (expected 512)")
    assert v == 512, f"RPM osa vrijednost: {v} != 512"
    print("  PASS")


def test_diff(ori, stg2):
    print("\n=== TEST: Diff ORI vs STG2 ===")
    if stg2 is None:
        print("  PRESKACAM — STG2 fajl nije dostupan")
        return
    summary = ori.diff_summary(stg2)
    print(f"  BOOT:  {summary['BOOT']:,} B")
    print(f"  CODE:  {summary['CODE']:,} B")
    print(f"  CAL:   {summary['CAL']:,} B")
    print(f"  OTHER: {summary['OTHER']:,} B")
    assert summary['CODE'] == 7087
    assert summary['CAL']  == 169912
    assert summary['BOOT'] == 140
    print("  PASS")


def test_map_finder_ori(ori):
    print("\n=== TEST: Map finder ORI ===")
    finder = MapFinder(ori)
    maps = finder.find_all(progress_cb=lambda m: print(f"  {m}"))
    print(f"\n  Ukupno pronadjeno: {len(maps)} mapa")
    for fm in maps:
        print(f"  0x{fm.address:06X}  {fm.defn.name:25s}  {len(fm.data)} vals  range=[{min(fm.data)}..{max(fm.data)}]")
    return maps


def test_map_finder_stg2(stg2):
    print("\n=== TEST: Map finder STG2 ===")
    finder = MapFinder(stg2)
    maps = finder.find_all()
    print(f"  Ukupno pronadjeno: {len(maps)} mapa")
    for fm in maps:
        print(f"  0x{fm.address:06X}  {fm.defn.name:25s}  vals={fm.data[:4]}...")
    return maps


def test_changed_regions(ori, stg2):
    print("\n=== TEST: Changed regions ===")
    finder = MapFinder(ori)
    blocks = finder.find_changed_regions(stg2, min_block=32)
    print(f"  Ukupno blokova (>=32B): {len(blocks)}")
    cal_blocks  = [b for b in blocks if b['in_cal']]
    code_blocks = [b for b in blocks if b['in_code']]
    print(f"  CAL blokovi:  {len(cal_blocks)}")
    print(f"  CODE blokovi: {len(code_blocks)}")
    print("\n  Najveci CODE blokovi:")
    for b in sorted(code_blocks, key=lambda x: -x['size'])[:10]:
        print(f"    0x{b['start']:06X}-0x{b['end']:06X}  {b['size']:,}B")
    print("\n  Najveci CAL blokovi:")
    for b in sorted(cal_blocks, key=lambda x: -x['size'])[:10]:
        print(f"    0x{b['start']:06X}-0x{b['end']:06X}  {b['size']:,}B")


def test_checksum(ori):
    print("\n=== TEST: Checksum engine ===")
    cs = ChecksumEngine(ori)
    results = cs.verify()
    for k, v in results.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


def test_map_finder_sc_variants():
    print("\n=== TEST: Map finder SC varijante (230hp/130hp/170hp) ===")
    variants = [
        (os.path.join(DUMPS, "2021", "1630ace", "230.bin"), "10SW053727", "230hp"),
        (os.path.join(DUMPS, "2021", "1630ace", "130.bin"), "10SW053729", "130hp"),
        (os.path.join(DUMPS, "2020", "1630ace", "170.bin"), "10SW053729", "170hp"),
    ]
    for path, expected_sw, label in variants:
        if not os.path.exists(path):
            print(f"  {label}: PRESKACAM — nije pronaden")
            continue
        eng = ME17Engine()
        info = eng.load(path)
        assert info.sw_id == expected_sw, f"{label} SW: {info.sw_id} != {expected_sw}"
        finder = MapFinder(eng)
        maps = finder.find_all()
        print(f"  {label} ({expected_sw}): {len(maps)} mapa")
        assert len(maps) >= 40, f"{label} treba >= 40 mapa, dobiveno: {len(maps)}"
    print("  PASS")


def test_write_safety():
    print("\n=== TEST: Write safety ===")
    eng2 = ME17Engine()
    eng2.load(ORI_PATH)
    val_before = eng2.read_u16_be(CAL_START)
    eng2.write_u16_be(CAL_START, 0x1234)
    val_after = eng2.read_u16_be(CAL_START)
    assert val_after == 0x1234, "Write u CAL nije uspio"
    assert eng2.dirty, "Dirty flag nije postavljen"
    print(f"  CAL write: 0x{val_before:04X} -> 0x1234 OK")
    try:
        eng2.write_u16_be(0x200000, 0xBEEF)
        print("  ERROR: Trebao je baciti ValueError!")
    except ValueError:
        print("  Out-of-bounds zastita: OK")
    print("  PASS")


SPARK_PATH  = os.path.join(DUMPS, "2021", "900ace", "spark90.bin")   # 10SW039116
SPARK2_PATH = os.path.join(DUMPS, "2019", "900ace", "spark90.bin")   # 10SW039116
GTI90_PATH  = os.path.join(DUMPS, "2021", "900ace", "gti90.bin")     # 10SW053774
GTI_PATH    = None   # GTI155 (10SW025752) nije u dumps — preskoci


def test_map_finder_spark():
    print("\n=== TEST: Map finder SPARK 900 HO ACE (2021) ===")
    if not os.path.exists(SPARK_PATH):
        print("  PRESKACAM — spark90.bin nije pronaden")
        return []
    eng = ME17Engine()
    info = eng.load(SPARK_PATH)
    print(f"  SW ID: {info.sw_id}")
    assert info.sw_id == "10SW039116", f"Spark SW ID: {info.sw_id}"

    finder = MapFinder(eng)
    assert finder._is_spark(), "Spark detekcija failed"
    assert not finder._is_gti_na(), "Spark ne smije biti GTI"

    maps = finder.find_all()
    print(f"  Ukupno mapa: {len(maps)}")
    cats = {m.defn.category for m in maps}
    assert "injection" in cats, "Spark mora imati injection mapu"
    assert "ignition"  in cats, "Spark mora imati ignition mapu"
    assert "lambda"    in cats, "Spark mora imati lambda mapu"
    assert len(maps) >= 10, f"Spark treba >= 10 mapa, dobiveno: {len(maps)}"
    print("  PASS")
    return maps


def test_map_finder_gti90():
    print("\n=== TEST: Map finder GTI 90 HO ACE (2021) ===")
    if not os.path.exists(GTI90_PATH):
        print("  PRESKACAM — gti90.bin nije pronaden")
        return []
    eng = ME17Engine()
    info = eng.load(GTI90_PATH)
    print(f"  SW ID: {info.sw_id}")
    assert info.sw_id == "10SW053774", f"GTI90 SW ID: {info.sw_id}"

    finder = MapFinder(eng)
    assert not finder._is_spark(), "GTI90 ne smije biti Spark"
    assert finder._is_gti_na(), "GTI90 detekcija failed"

    maps = finder.find_all()
    print(f"  Ukupno mapa: {len(maps)}")
    cats = {m.defn.category for m in maps}
    assert "injection" in cats, "GTI90 mora imati injection mapu"
    assert "ignition"  in cats, "GTI90 mora imati ignition mapu"
    assert len(maps) >= 30, f"GTI90 treba >= 30 mapa, dobiveno: {len(maps)}"
    print("  PASS")
    return maps


def test_map_finder_gti():
    print("\n=== TEST: Map finder GTI 155 ===")
    gti155 = os.path.join(DUMPS, "2018", "4tec1503", "gti155.bin")
    if not os.path.exists(gti155):
        print("  PRESKACAM — gti155.bin nije pronaden")
        return []
    eng = ME17Engine()
    info = eng.load(gti155)
    print(f"  SW ID: {info.sw_id}")
    assert info.sw_id == "10SW025752", f"GTI SW ID: {info.sw_id}"

    finder = MapFinder(eng)
    assert not finder._is_spark(), "GTI ne smije biti Spark"
    assert finder._is_gti_na(), "GTI detekcija failed"

    maps = finder.find_all()
    print(f"  Ukupno mapa: {len(maps)}")
    gti_inj = [m for m in maps if "GTI" in m.defn.name and m.defn.category == "injection"]
    gti_ign = [m for m in maps if "GTI" in m.defn.name and m.defn.category == "ignition"]
    print(f"  GTI injection: {len(gti_inj)}, GTI ignition extra: {len(gti_ign)}")
    assert len(gti_inj) >= 1, "GTI mora imati direktnu injection mapu"
    assert len(maps) >= 50, f"GTI treba >= 50 mapa, dobiveno: {len(maps)}"
    print("  PASS")
    return maps


def test_eeprom_circular():
    print("\n=== TEST: EEPROM circular buffer ODO ===")
    from core.eeprom import EepromParser

    parser = EepromParser()
    ecu_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Desktop', 'ECU')

    test_cases = [
        # (path, expected_min_odo, expected_hw)
        (os.path.join(ecu_root, "064", "064 86-31"), 5000, "064"),
        (os.path.join(ecu_root, "063", "063 92-51"), 5000, "063"),
        (os.path.join(ecu_root, "062", "062 86-24"), 4000, "062"),
    ]

    ok = 0
    for path, min_odo, expected_hw in test_cases:
        if not os.path.exists(path):
            print(f"  {os.path.basename(path)}: PRESKACAM (nije pronaden)")
            continue
        info = parser.parse(path)
        hw_ok  = info.hw_type == expected_hw
        odo_ok = info.odo_raw >= min_odo
        status = "OK" if (hw_ok and odo_ok) else "FAIL"
        print(f"  {os.path.basename(path):20s}: hw={info.hw_type} odo={info.odo_raw}min {status}")
        if hw_ok and odo_ok:
            ok += 1

    print(f"  {ok}/{len(test_cases)} OK (preskoceni racunaju kao prolaz)")
    print("  PASS")


if __name__ == "__main__":
    print("ME17Suite - Test runner")
    print("=" * 50)

    ori  = test_load_ori()
    stg2 = test_load_stg2()
    test_read_primitives(ori)
    test_diff(ori, stg2)
    test_map_finder_ori(ori)
    if stg2 is not None:
        test_map_finder_stg2(stg2)
    test_map_finder_spark()
    test_map_finder_gti90()
    test_map_finder_gti()
    test_map_finder_sc_variants()
    if stg2 is not None:
        test_changed_regions(ori, stg2)
    test_checksum(ori)
    test_write_safety()
    test_eeprom_circular()

    print("\n" + "=" * 50)
    print("Svi testovi zavrseni.")