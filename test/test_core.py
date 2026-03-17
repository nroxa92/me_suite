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


ROOT = os.path.join(os.path.dirname(__file__), '..')
ORI_PATH  = os.path.join(ROOT, "_materijali", "ori_300.bin")
STG2_PATH = os.path.join(ROOT, "_materijali", "npro_stg2_300.bin")


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
    eng = ME17Engine()
    info = eng.load(STG2_PATH)
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


if __name__ == "__main__":
    print("ME17Suite - Test runner")
    print("=" * 50)

    ori  = test_load_ori()
    stg2 = test_load_stg2()
    test_read_primitives(ori)
    test_diff(ori, stg2)
    test_map_finder_ori(ori)
    test_map_finder_stg2(stg2)
    test_changed_regions(ori, stg2)
    test_checksum(ori)
    test_write_safety()

    print("\n" + "=" * 50)
    print("Svi testovi zavrseni.")