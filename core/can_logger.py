"""
CAN logger backend for ME17Suite.

Handles live CAN bus acquisition via IXXAT USB adapter (python-can) and
reading/writing of SDCANlogger-compatible log files.

Log file format:
    # START_TIME_WALL_CLOCK: 2025-07-27 15:43:37.367694
    3845.540628;0x7E8;05622106AB100000
    3845.541595;0x102;0000145A59CB0DD1

Each data line: timestamp_seconds;0xCANID;HEXDATA (hex without spaces, 8 bytes).

Hardware: IXXAT USB-to-CAN, BRP Sea-Doo CAN bus at 250 kbps.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    import can as _can_type


# ─── CanLoggerThread ──────────────────────────────────────────────────────────

class CanLoggerThread(QThread):
    """
    QThread that acquires CAN messages from the IXXAT USB adapter in real-time.

    Emits:
        message_received(float, int, bytes):
            Relative timestamp in seconds (float), CAN ID (int), 8-byte payload.
        connection_status(bool, str):
            True when bus opened successfully; False with error description.
    """

    message_received = pyqtSignal(float, int, bytes)   # (rel_timestamp_s, can_id, data_8bytes)
    connection_status = pyqtSignal(bool, str)           # (connected, message)

    def __init__(self, channel: int = 0, bitrate: int = 250_000) -> None:
        super().__init__()
        self._channel: int = channel
        self._bitrate: int = bitrate
        self._bus: "_can_type.BusABC | None" = None
        self._stop_event: threading.Event = threading.Event()
        self._start_time: float = 0.0

    # ── Public interface ───────────────────────────────────────────────────────

    def connect_bus(self) -> bool:
        """
        Open the IXXAT CAN bus.

        Returns True on success and emits connection_status(True, ...).
        Returns False on failure and emits connection_status(False, reason).
        """
        try:
            import can
        except ImportError:
            self.connection_status.emit(False, "python-can nije instaliran")
            return False

        try:
            self._bus = can.Bus(
                interface="ixxat",
                channel=self._channel,
                bitrate=self._bitrate,
            )
            self._start_time = time.monotonic()
            self.connection_status.emit(
                True,
                f"IXXAT kanal {self._channel} otvoren @ {self._bitrate // 1000} kbps",
            )
            return True
        except Exception as e:  # noqa: BLE001
            self._bus = None
            self.connection_status.emit(False, f"IXXAT greška: {e}")
            return False

    def disconnect_bus(self) -> None:
        """Close the CAN bus if open."""
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:  # noqa: BLE001
                pass
            self._bus = None

    def stop(self) -> None:
        """Signal the run loop to stop and wait for the thread to finish."""
        self._stop_event.set()
        self.wait()

    # ── QThread run ───────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Main thread loop.  Reads CAN messages and emits message_received.

        Exits when stop() is called or a bus error occurs.
        Data bytes are zero-padded to exactly 8 bytes before emission.
        """
        self._stop_event.clear()

        if self._bus is None:
            # Attempt to open the bus from within the thread context if caller
            # did not call connect_bus() beforehand.
            if not self.connect_bus():
                return

        try:
            while not self._stop_event.is_set():
                try:
                    msg = self._bus.recv(timeout=0.1)  # type: ignore[union-attr]
                except Exception as e:  # noqa: BLE001
                    self.connection_status.emit(False, f"IXXAT greška: {e}")
                    break

                if msg is None:
                    # recv() timed out — check stop event and continue
                    continue

                rel_ts: float = time.monotonic() - self._start_time
                data: bytes = bytes(msg.data).ljust(8, b"\x00")[:8]
                self.message_received.emit(rel_ts, msg.arbitration_id, data)

        finally:
            self.disconnect_bus()


# ─── LogFile ──────────────────────────────────────────────────────────────────

class LogFile:
    """
    Read and write SDCANlogger-compatible CAN log files.

    File format (text, UTF-8):
        # START_TIME_WALL_CLOCK: 2025-07-27 15:43:37.367694
        3845.540628;0x7E8;05622106AB100000
        3845.541595;0x102;0000145A59CB0DD1

    Lines starting with '#' are comments / metadata and are ignored when loading.
    """

    @staticmethod
    def load(path: str) -> list[tuple[float, int, bytes]]:
        """
        Load a CAN log file.

        Args:
            path: Absolute path to the .txt log file.

        Returns:
            List of (timestamp_s, can_id, data_8bytes) tuples.
            Data is always exactly 8 bytes (zero-padded if shorter in file).

        Raises:
            OSError: if the file cannot be opened.
            ValueError: if a non-comment line cannot be parsed (skipped with warning).
        """
        messages: list[tuple[float, int, bytes]] = []

        with open(path, "r", encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(";")
                if len(parts) < 3:
                    # Malformed line — skip silently
                    continue

                try:
                    timestamp = float(parts[0])
                    can_id = int(parts[1], 16)
                    hex_str = parts[2].strip()
                    raw_bytes = bytes.fromhex(hex_str)
                    # Pad or truncate to 8 bytes
                    data = raw_bytes.ljust(8, b"\x00")[:8]
                    messages.append((timestamp, can_id, data))
                except (ValueError, IndexError):
                    # Skip unparseable lines without crashing
                    continue

        return messages

    @staticmethod
    def save(
        path: str,
        messages: list[tuple[float, int, bytes]],
        start_time: str = "",
    ) -> None:
        """
        Save CAN messages to a log file.

        Args:
            path:       Absolute path to write (created or overwritten).
            messages:   List of (timestamp_s, can_id, data_8bytes) tuples.
            start_time: Optional wall-clock string for the header comment.
                        If non-empty, written as the first line:
                        "# START_TIME_WALL_CLOCK: {start_time}"

        Raises:
            OSError: if the file cannot be written.
        """
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            if start_time:
                fh.write(f"# START_TIME_WALL_CLOCK: {start_time}\n")

            for timestamp, can_id, data in messages:
                # Ensure data is exactly 8 bytes
                data_8 = bytes(data).ljust(8, b"\x00")[:8]
                hex_data = data_8.hex().upper()
                fh.write(f"{timestamp:.6f};0x{can_id:03X};{hex_data}\n")
