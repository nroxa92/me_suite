"""
ME17Suite — CAN Sniffer
Pasivno snifanje BRP CAN busa (IXAAT VCI4 USB-to-CAN V2).

Pokretanje:
    python tools/can_sniffer.py
    python tools/can_sniffer.py --bitrate 500000 --output sniff_buds2.csv
    python tools/can_sniffer.py --bitrate 250000 --output sniff_cluster_250k.csv
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

# Apsolutni import (me_suite root mora biti u sys.path)
try:
    from core.can_decoder import CanDecoder, validate_checksum, extract_rolling_counter
except ImportError:
    # Fallback ako se pokreće izvan me_suite roota
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.can_decoder import CanDecoder, validate_checksum, extract_rolling_counter


# ─── Statistika po ID-u ───────────────────────────────────────────────────────

class IdStats:
    def __init__(self):
        self.count = 0
        self.first_ts = None
        self.last_ts = None
        self.last_data = None
        self.dlc = None
        self.changes = 0
        self.checksum_errors = 0
        self.rolling_ctr_jumps = 0  # broj preskočenih rolling counter vrijednosti
        self._prev_data = None
        self._prev_rolling_ctr = None

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

        # XOR checksum provjera (samo za DLC=8)
        if len(data) == 8 and not validate_checksum(data):
            self.checksum_errors += 1

        # Rolling counter jump detekcija
        if len(data) >= 7:
            ctr = extract_rolling_counter(data)
            if self._prev_rolling_ctr is not None:
                expected = (self._prev_rolling_ctr + 1) & 0x0F
                if ctr != expected:
                    self.rolling_ctr_jumps += 1
            self._prev_rolling_ctr = ctr

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
        csv_file = open(output, 'w', newline='', encoding='utf-8')
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

            # ID-specifičan dekoder iz CanDecoder
            decoded = CanDecoder.decode(mid, data)
            dec_str = _format_decoded(decoded)

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


def _format_decoded(decoded: dict) -> str:
    """Formatiraj CanDecoder.decode() rezultat u kratki string za CSV/terminal."""
    if not decoded.get("decoded"):
        return ""
    # Izbaci meta polja, prikaži samo korisne vrijednosti
    skip = {"can_id", "raw", "decoded", "checksum_ok", "rolling_ctr"}
    parts = []
    for k, v in decoded.items():
        if k in skip:
            continue
        if isinstance(v, float):
            parts.append(f"{k}={v:.1f}")
        else:
            parts.append(f"{k}={v}")
    return " ".join(parts)


def _print_stats(stats: dict, elapsed: float, total: int, final: bool = False):
    if not stats:
        return

    label = "== FINALNA STATISTIKA" if final else f"== {elapsed:.0f}s"
    print(f"\n  {label} ({total} msg, {len(stats)} ID-ova) {'-'*25}")
    print(f"  {'ID':>6}  {'DLC':>3}  {'Hz':>7}  {'Promj':>5}  {'CSerr':>5}  {'RCjmp':>5}  {'Zadnji bajti':>23}  Dekod")
    print(f"  {'-'*6}  {'-'*3}  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*23}  {'-'*24}")

    for mid in sorted(stats.keys()):
        s = stats[mid]
        data_str = s.last_data.hex(' ').upper() if s.last_data else ""
        decoded = CanDecoder.decode(mid, s.last_data) if s.last_data else {}
        dec_str = _format_decoded(decoded)[:24]
        cs_flag = f"!{s.checksum_errors}" if s.checksum_errors else "  ok"
        rc_flag = f"!{s.rolling_ctr_jumps}" if s.rolling_ctr_jumps else "   0"
        print(
            f"  0x{mid:03X}  {s.dlc:>3}  {s.freq_hz:>6.1f}"
            f"  {s.changes:>5}  {cs_flag:>5}  {rc_flag:>5}"
            f"  {data_str:>23}  {dec_str}"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="ME17Suite CAN Sniffer (IXAAT)")
    p.add_argument('--bitrate',  type=int, default=500000,   help="Bitrate (default 500kbps=diagnostic, 250kbps=cluster)")
    p.add_argument('--channel',  type=int, default=0,        help="IXAAT kanal (default 0)")
    p.add_argument('--output',   type=str, default=None,     help="CSV log fajl (opcija)")
    p.add_argument('--duration', type=float, default=None,   help="Sekunde snifanja (default=beskonačno)")
    args = p.parse_args()

    run_sniffer(args.bitrate, args.channel, args.output, args.duration)
