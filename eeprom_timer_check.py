# EEPROM hw timer format provjera.
import struct
from pathlib import Path

ecu_root = Path("C:/Users/SeaDoo/Desktop/ECU")

def read_file(fpath):
    """Čita binarne podatke iz fajla."""
    return fpath.read_bytes()

def hex_dump(data, offset, length=16):
    """Vraća hex dump određene regije."""
    chunk = data[offset:offset+length]
    hex_part = ' '.join(f'{b:02X}' for b in chunk)
    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    return f"{hex_part:<48}  |{ascii_part}|"

print("=" * 80)
print("EEPROM HW TIMER FORMAT ANALIZA")
print("=" * 80)

# Skupi sve fajlove iz 062, 063, 064
all_files = []
for hw_folder in ["061", "062", "063", "064"]:
    folder = ecu_root / hw_folder
    if not folder.exists():
        print(f"  Folder {hw_folder} ne postoji")
        continue
    files = list(folder.iterdir())
    files = [f for f in files if f.is_file() and not f.name.startswith('.') and 'desktop.ini' not in f.name]
    for f in sorted(files):
        all_files.append((hw_folder, f))

print(f"\nPronađeno {len(all_files)} fajlova ukupno.\n")

results = []

for hw_folder, fpath in all_files:
    try:
        data = read_file(fpath)
        if len(data) < 0x200:
            print(f"[{hw_folder}] {fpath.name}: premali fajl ({len(data)}B)")
            continue

        fname = fpath.stem

        # --- Čitaj hw timer @ 0x0125 (5B ASCII) ---
        hw_raw = data[0x0125:0x012A]
        hw_str = hw_raw.split(b'\x00')[0].decode('ascii', errors='replace').strip()

        # --- Hex dump regije oko 0x0125 ---
        dump_0x110 = hex_dump(data, 0x0110, 32)
        dump_0x125 = hex_dump(data, 0x0125, 10)

        # --- Pokušaj alternativnih adresa ---
        # Provjeri 0x0130 i 0x013A (5B ASCII)
        hw_alt1 = data[0x0130:0x0135].decode('ascii', errors='replace').strip('\x00').strip()
        hw_alt2 = data[0x013A:0x013F].decode('ascii', errors='replace').strip('\x00').strip()

        # --- Provjeri datume @ 0x0013 i 0x001B ---
        date1 = data[0x0013:0x001B].split(b'\x00')[0].decode('ascii', errors='replace')
        date2 = data[0x001B:0x0023].split(b'\x00')[0].decode('ascii', errors='replace')

        # --- MPEM SW @ 0x0032 ---
        mpem = data[0x0032:0x003C].split(b'\x00')[0].decode('ascii', errors='replace')

        # --- HW type iz fajla (negdje u headeru) ---
        hw_type_raw = data[0x0030:0x0036].decode('ascii', errors='replace')

        # Parsiranje filename-a (različiti formati): "HHH-MM", "HHH", "NNN h MMmin"
        fn_hours = None
        fn_mins = None
        fn_info = fname

        if '-' in fname:
            # Format: "064 HHH-MM" ili "HHH-MM"
            parts = fname.replace('064', '').replace('063', '').replace('062', '').replace('061', '').strip().split('-')
            if len(parts) == 2:
                try:
                    fn_hours = int(parts[0].strip())
                    fn_mins = int(parts[1].strip())
                    fn_info = f"{fn_hours}h {fn_mins}min"
                except ValueError:
                    pass
        elif fname.split()[-1].isdigit():
            # Format: "064 HHH" — samo sati
            try:
                fn_hours = int(fname.split()[-1])
                fn_mins = 0
                fn_info = f"{fn_hours}h"
            except ValueError:
                pass

        # Usporedi s hw_str ako je parsiran
        match_str = "?"
        hw_hours_parsed = None
        hw_mins_parsed = None
        if fn_hours is not None and hw_str.isdigit() and len(hw_str) == 5:
            hw_int = int(hw_str)
            hw_hours_parsed = hw_int // 100
            hw_mins_parsed = hw_int % 100
            if hw_hours_parsed == fn_hours and hw_mins_parsed == fn_mins:
                match_str = "OK HHHM"
            else:
                # Provjeri alternativni format: MMMMM (ukupne minute)?
                total_min = fn_hours * 60 + fn_mins
                if hw_int == total_min:
                    match_str = "OK MIN"
                    hw_hours_parsed = hw_int // 60
                    hw_mins_parsed = hw_int % 60
                else:
                    match_str = f"NO (parsed={hw_hours_parsed}h {hw_mins_parsed}min if HHHM)"

        results.append({
            'hw': hw_folder, 'file': fname, 'hw_str': hw_str,
            'hw_hours': hw_hours_parsed, 'hw_mins': hw_mins_parsed,
            'fn_hours': fn_hours, 'fn_mins': fn_mins,
            'match': match_str, 'mpem': mpem, 'date1': date1, 'date2': date2,
            'data': data, 'fpath': fpath
        })

        print(f"[{hw_folder}] {fname}")
        print(f"  @ 0x0125: raw={hw_raw.hex()} str='{hw_str}'  alt@0x130='{hw_alt1}' alt@0x13A='{hw_alt2}'")
        print(f"  filename: {fn_info}  | match: {match_str}")
        print(f"  date1={date1} date2={date2} SW={mpem}")
        print()

    except Exception as e:
        import traceback
        print(f"[{hw_folder}] {fpath.name}: ERROR {e}")
        traceback.print_exc()

# --- Detaljni hex dump za prvih nekoliko fajlova ---
print("\n" + "=" * 80)
print("DETALJNI HEX DUMP REGIJE 0x0100-0x0160")
print("=" * 80)
for r in results[:6]:
    data = r['data']
    print(f"\n[{r['hw']}] {r['file']} (SW={r['mpem']}):")
    for off in range(0x0100, 0x0160, 16):
        line = hex_dump(data, off, 16)
        # Označi 0x0125
        marker = " <-- @ 0x0125" if off <= 0x0125 < off + 16 else ""
        print(f"  {off:04X}: {line}{marker}")

# --- Circular buffer provjera ---
print("\n" + "=" * 80)
print("CIRCULAR BUFFER PROVJERA")
print("=" * 80)
hw_addrs = {
    "062": [0x5062, 0x4562, 0x1062, 0x5060, 0x4560],
    "063": [0x0DE2, 0x05E2, 0x15E2, 0x0DE0, 0x05E0],
    "064": [0x0562, 0x0D62, 0x1562, 0x0560, 0x0D60],
}
for r in results:
    hw = r['hw']
    if hw not in hw_addrs:
        continue
    data = r['data']
    fname = r['file']
    fn_hours = r['fn_hours']
    fn_mins = r['fn_mins']
    if fn_hours is None:
        continue
    expected_min = fn_hours * 60 + (fn_mins or 0)
    print(f"\n[{hw}] {fname} (filename={fn_hours}h {fn_mins or 0}min = {expected_min}min total):")
    for addr in hw_addrs[hw]:
        if addr + 2 <= len(data):
            val_le = struct.unpack_from("<H", data, addr)[0]
            val_be = struct.unpack_from(">H", data, addr)[0]
            match_le = "OK!" if val_le == expected_min else ""
            match_be = "OK!" if val_be == expected_min else ""
            print(f"  @ 0x{addr:04X}: LE={val_le} ({val_le//60}h {val_le%60}min) {match_le}  BE={val_be} ({val_be//60}h {val_be%60}min) {match_be}")

print("\n\nANALIZA DOVRSENA.")
