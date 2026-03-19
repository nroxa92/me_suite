"""
ME17Suite — CAN Sniffer
Pasivno snifanje BRP CAN busa (IXAAT VCI4 USB-to-CAN V2).

Pokretanje:
    python tools/can_sniffer.py
    python tools/can_sniffer.py --bitrate 500000 --output sniff_buds2.csv
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from collections import defaultdict

try:
    import can
except ImportError:
    print("GREŠKA: pip install python-can")
    sys.exit(1)


# ─── BRP payload dekoderi ──────────────────────────────────────────────────────
# Potvrđeno iz ECU CODE analize (me_suite sessions 2026-03)

def _try_decode(msg_id: int, data: bytes) -> dict | None:
    """
    Pokušaj dekodirati poznate BRP CAN payloade.
    Returns dict s dekodiranin vrijednostima ili None ako ID nije poznat.
    """
    if len(data) < 2:
        return None

    result = {}

    # RPM: byte[1:3] × 0.25  (potvrđeno iz ECU CODE)
    if len(data) >= 3:
        rpm_raw = (data[1] << 8) | data[2]
        rpm = rpm_raw * 0.25
        if 0 < rpm < 12000:
            result['rpm'] = round(rpm, 1)

    # Temp: byte[1] - 40  (potvrđeno iz ECU CODE)
    if len(data) >= 2:
        temp = data[1] - 40
        if -40 <= temp <= 150:
            result['temp_c'] = temp

    # DTC count: byte[0] direktno
    dtc = data[0]
    if dtc < 50:
        result['dtc_count'] = dtc

    return result if result else None


# ─── Statistika po ID-u ───────────────────────────────────────────────────────

class IdStats:
    def __init__(self):
        self.count = 0
        self.first_ts = None
        self.last_ts = None
        self.last_data = None
        self.dlc = None
        self.changes = 0
        self._prev_data = None

    def update(self, ts: float, data: bytes):
        self.count += 1
        if self.first_ts is None:
            self.first_ts = ts
        self.last_ts = ts
        self.dlc = len(data)
        if self._prev_data is not None and data != self._prev_data:
            self.changes += 1
        self._prev_data = bytes(data)
        self.last_data = bytes(data)

    @property
    def freq_hz(self) -> float:
        if self.count < 2 or self.last_ts == self.first_ts:
            return 0.0
        return (self.count - 1) / (self.last_ts - self.first_ts)


# ─── Glavni sniffer ───────────────────────────────────────────────────────────

def run_sniffer(bitrate: int, channel: int, output: str | None, duration: float | None):
    print(f"\n{'='*60}")
    print(f"  ME17Suite CAN Sniffer")
    print(f"  IXAAT VCI4 USB-to-CAN | {bitrate//1000}kbps | listen-only")
    print(f"  {'Snima u: ' + output if output else 'Bez logiranja'}")
    print(f"{'='*60}\n")

    # Otvori IXAAT u listen-only modu
    try:
        bus = can.Bus(
            interface='ixxat',
            channel=channel,
            bitrate=bitrate,
            receive_own_messages=False,
            monitor=True,   # pasivni monitor mod — ne šalje ACK, radi paralelno s BUDS2/MiniMon
        )
        print(f"  [OK] IXAAT otvoren ch{channel} @ {bitrate//1000}kbps  [MONITOR MODE]\n")
    except Exception as e:
        print(f"  [GREŠKA] Ne mogu otvoriti IXAAT: {e}")
        print("  Provjeri: IXAAT driver (VCI), kabl, terminator")
        sys.exit(1)

    stats: dict[int, IdStats] = defaultdict(IdStats)
    csv_writer = None
    csv_file = None

    if output:
        csv_file = open(output, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['timestamp', 'id_hex', 'dlc', 'data_hex', 'decoded'])

    start_time = time.monotonic()
    last_print = start_time
    msg_count = 0
    PRINT_INTERVAL = 2.0  # sekunde između ispisa statistike

    print("  Snifam... (Ctrl+C za stop)\n")

    try:
        while True:
            elapsed = time.monotonic() - start_time
            if duration and elapsed >= duration:
                break

            try:
                msg = bus.recv(timeout=0.1)
            except Exception as e:
                if "overrun" in str(e).lower():
                    print(f"  [WARN] Buffer overrun — preskacam ({e})")
                    continue
                raise
            if msg is None:
                continue

            msg_count += 1
            ts = msg.timestamp or time.time()
            mid = msg.arbitration_id
            data = bytes(msg.data)

            stats[mid].update(ts, data)

            decoded = _try_decode(mid, data) or {}
            dec_str = str(decoded) if decoded else ""

            if csv_writer:
                csv_writer.writerow([
                    f"{ts:.6f}",
                    f"0x{mid:03X}",
                    msg.dlc,
                    data.hex(' ').upper(),
                    dec_str,
                ])

            # Live print svake PRINT_INTERVAL sekunde
            now = time.monotonic()
            if now - last_print >= PRINT_INTERVAL:
                last_print = now
                _print_stats(stats, elapsed, msg_count)

    except KeyboardInterrupt:
        print("\n\n  [STOP] Ctrl+C")
    finally:
        elapsed = time.monotonic() - start_time
        bus.shutdown()
        if csv_file:
            csv_file.close()
            print(f"  Log snimljen: {output}")

    print(f"\n  Ukupno: {msg_count} poruka u {elapsed:.1f}s")
    print(f"  Unikatnih CAN ID-ova: {len(stats)}\n")
    _print_stats(stats, elapsed, msg_count, final=True)


def _print_stats(stats: dict, elapsed: float, total: int, final: bool = False):
    if not stats:
        return

    label = "== FINALNA STATISTIKA" if final else f"== {elapsed:.0f}s"
    print(f"\n  {label} ({total} msg, {len(stats)} ID-ova) {'-'*30}")
    print(f"  {'ID':>6}  {'DLC':>3}  {'Hz':>7}  {'Promjena':>9}  {'Zadnji bajti':>30}  Dekod")
    print(f"  {'-'*6}  {'-'*3}  {'-'*7}  {'-'*9}  {'-'*30}  {'-'*20}")

    for mid in sorted(stats.keys()):
        s = stats[mid]
        data_str = s.last_data.hex(' ').upper() if s.last_data else ""
        dec = _try_decode(mid, s.last_data) if s.last_data else {}
        dec_str = str(dec)[:20] if dec else ""
        print(f"  0x{mid:03X}  {s.dlc:>3}  {s.freq_hz:>6.1f}  {s.changes:>9}  {data_str:>30}  {dec_str}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="ME17Suite CAN Sniffer (IXAAT)")
    p.add_argument('--bitrate',  type=int, default=500000,   help="Bitrate (default 500kbps)")
    p.add_argument('--channel',  type=int, default=0,        help="IXAAT kanal (default 0)")
    p.add_argument('--output',   type=str, default=None,     help="CSV log fajl (opcija)")
    p.add_argument('--duration', type=float, default=None,   help="Sekunde snifanja (default=beskonačno)")
    args = p.parse_args()

    run_sniffer(args.bitrate, args.channel, args.output, args.duration)
