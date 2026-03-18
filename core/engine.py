"""
ME17Suite — Core Binary Engine
Bosch ME17.8.5 by Rotax (Sea-Doo 300)
MCU: Infineon TC1762 (TriCore)

Supported SW versions:
  10SW066726  (ORI baseline)
  10SW040039  (NPRo tuning baseline)
"""

import struct
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# ─── Constants ───────────────────────────────────────────────────────────────

FILE_SIZE       = 0x178000          # 1,540,096 bytes — jedina validna veličina
FILL_BYTE_CODE  = 0xC3              # TriCore NOP — fill u nekorištenim flash regijama
FILL_BYTE_CAL   = 0x00              # fill na kraju fajla

# Memory layout
BOOT_START      = 0x000000
BOOT_END        = 0x00FFFF
CODE_START      = 0x010000
CODE_END        = 0x05FFFF
CAL_START       = 0x060000
CAL_END         = 0x15FFFF
EMPTY_START     = 0x160000

# Poznati SW stringovi (na adresi 0x001A, 10 bajtova)
KNOWN_SW = {
    b"10SW066726": "ORI baseline (Sea-Doo 300hp SC, stock)",
    b"10SW040039": "NPRo Stage 2 baseline (300hp SC)",
    b"10SW004672": "RXP/RXT 300hp SC (2016)",
    b"10SW082806": "300hp SC variant (backup_flash)",
    b"10SW025752": "GTI SE 155 2018 (NA, 10SW025752)",
    b"10SW053774": "GTI SE 90 2020-2021 (NA, Rotax 900 HO ACE — isti SW, 2020 vs 2021 = 80B razlika u hash bloku @ 0x017F02)",
    b"10SW053729": "GTI SE 130/170 2020-2021 (NA, Rotax 1630 NA — isti SW, 2020 vs 2021 = 80B razlika samo u hash bloku)",
    b"10SW053727": "GTI SE 230 / Wake Pro 230 2021 (SC, Rotax 1630 SC)",
    b"10SW011328": "Spark 90 2016 (NA, HW063, Rotax 900 ACE)",
}

# String koji identificira ECU/MCU platformu (na 0x01FE50)
MCU_STRING      = b"VME17 SB_V05.01.02"
PLATFORM_STRING = b"PLATFORM VM_CB.04.80.00"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class BinInfo:
    sw_id: str
    sw_desc: str
    file_size: int
    mcu_confirmed: bool
    platform_confirmed: bool
    is_valid: bool
    errors: list


# ─── Engine ──────────────────────────────────────────────────────────────────

class ME17Engine:
    """
    Temeljni engine za čitanje i pisanje ME17.8.5 binarnih fajlova.
    Sve operacije su non-destructive: radi na kopiji podataka.
    """

    def __init__(self):
        self._data: Optional[bytearray] = None
        self._path: Optional[Path] = None
        self._info: Optional[BinInfo] = None
        self._dirty: bool = False

    # ── Load / Save ──────────────────────────────────────────────────────────

    def load(self, path: str | Path) -> BinInfo:
        path = Path(path)
        raw = path.read_bytes()
        self._data = bytearray(raw)
        self._path = path
        self._dirty = False
        self._info = self._analyse()
        return self._info

    def save(self, path: str | Path | None = None) -> None:
        if self._data is None:
            raise RuntimeError("Nema učitanog fajla")
        target = Path(path) if path else self._path
        target.write_bytes(self._data)
        if target == self._path:
            self._dirty = False

    def get_bytes(self) -> bytes:
        """Vrati trenutni sadržaj kao bytes (za preview / checksum)."""
        return bytes(self._data)

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def info(self) -> Optional[BinInfo]:
        return self._info

    @property
    def loaded(self) -> bool:
        return self._data is not None

    # ── Validation ───────────────────────────────────────────────────────────

    def _analyse(self) -> BinInfo:
        errors = []
        d = self._data

        # Veličina
        if len(d) != FILE_SIZE:
            errors.append(f"Pogrešna veličina: {len(d):,} B (očekivano {FILE_SIZE:,} B)")

        # SW ID @ 0x001A, fallback na CODE mirror 0x02001A ako je BOOT eraziran (0xFF fill)
        sw_raw = bytes(d[0x001A:0x0024])
        if all(b == 0xFF for b in sw_raw) and len(d) > 0x02001A + 10:
            sw_raw = bytes(d[0x02001A:0x02001A + 10])
        sw_id = sw_raw.rstrip(b"\x00").decode("ascii", errors="replace")
        sw_desc = KNOWN_SW.get(sw_raw.rstrip(b"\x00"), f"Nepoznati SW: {sw_id}")

        # MCU string provjera
        mcu_ok = MCU_STRING in bytes(d[0x01FE00:0x01FF00])
        platform_ok = PLATFORM_STRING in bytes(d[0x012800:0x013000])

        if not mcu_ok:
            errors.append("MCU identifikacijski string nije pronađen — možda pogrešan ECU tip")

        return BinInfo(
            sw_id=sw_id,
            sw_desc=sw_desc,
            file_size=len(d),
            mcu_confirmed=mcu_ok,
            platform_confirmed=platform_ok,
            is_valid=len(errors) == 0,
            errors=errors,
        )

    # ── Read primitives ───────────────────────────────────────────────────────

    def _check_bounds(self, offset: int, size: int):
        if self._data is None:
            raise RuntimeError("Fajl nije učitan")
        if offset < 0 or offset + size > len(self._data):
            raise ValueError(f"Out of bounds: 0x{offset:06X} + {size}")

    def read_u8(self, offset: int) -> int:
        self._check_bounds(offset, 1)
        return self._data[offset]

    def read_u16_be(self, offset: int) -> int:
        self._check_bounds(offset, 2)
        return (self._data[offset] << 8) | self._data[offset + 1]

    def read_i16_be(self, offset: int) -> int:
        v = self.read_u16_be(offset)
        return v - 65536 if v >= 0x8000 else v

    def read_u16_le(self, offset: int) -> int:
        self._check_bounds(offset, 2)
        return self._data[offset] | (self._data[offset + 1] << 8)

    def read_i16_le(self, offset: int) -> int:
        v = self.read_u16_le(offset)
        return v - 65536 if v >= 0x8000 else v

    def read_u32_be(self, offset: int) -> int:
        self._check_bounds(offset, 4)
        return struct.unpack_from(">I", self._data, offset)[0]

    def read_u32_le(self, offset: int) -> int:
        self._check_bounds(offset, 4)
        return struct.unpack_from("<I", self._data, offset)[0]

    def read_bytes(self, offset: int, size: int) -> bytes:
        self._check_bounds(offset, size)
        return bytes(self._data[offset: offset + size])

    def read_array_u16_be(self, offset: int, count: int) -> list[int]:
        return [self.read_u16_be(offset + i * 2) for i in range(count)]

    def read_array_i16_be(self, offset: int, count: int) -> list[int]:
        return [self.read_i16_be(offset + i * 2) for i in range(count)]

    def read_array_u16_le(self, offset: int, count: int) -> list[int]:
        return [self.read_u16_le(offset + i * 2) for i in range(count)]

    # ── Write primitives ─────────────────────────────────────────────────────

    def write_u8(self, offset: int, value: int):
        self._check_bounds(offset, 1)
        value = max(0, min(255, int(value)))
        if self._data[offset] != value:
            self._data[offset] = value
            self._dirty = True

    def write_u16_be(self, offset: int, value: int):
        self._check_bounds(offset, 2)
        value = max(0, min(0xFFFF, int(value)))
        b = value.to_bytes(2, "big")
        if self._data[offset:offset+2] != bytearray(b):
            self._data[offset:offset+2] = b
            self._dirty = True

    def write_i16_be(self, offset: int, value: int):
        value = max(-32768, min(32767, int(value)))
        raw = value if value >= 0 else value + 65536
        self.write_u16_be(offset, raw)

    def write_u16_le(self, offset: int, value: int):
        self._check_bounds(offset, 2)
        value = max(0, min(0xFFFF, int(value)))
        b = value.to_bytes(2, "little")
        if self._data[offset:offset+2] != bytearray(b):
            self._data[offset:offset+2] = b
            self._dirty = True

    def write_i16_le(self, offset: int, value: int):
        value = max(-32768, min(32767, int(value)))
        raw = value if value >= 0 else value + 65536
        self.write_u16_le(offset, raw)

    def write_array_u16_be(self, offset: int, values: list[int]):
        for i, v in enumerate(values):
            self.write_u16_be(offset + i * 2, v)

    def write_array_u16_le(self, offset: int, values: list[int]):
        for i, v in enumerate(values):
            self.write_u16_le(offset + i * 2, v)

    # ── Region helpers ───────────────────────────────────────────────────────

    def in_cal(self, offset: int) -> bool:
        return CAL_START <= offset <= CAL_END

    def in_code(self, offset: int) -> bool:
        return CODE_START <= offset <= CODE_END

    def in_boot(self, offset: int) -> bool:
        return BOOT_START <= offset <= BOOT_END

    def get_cal_slice(self, offset: int, size: int) -> bytes:
        """Sigurno čitanje iz CAL regije."""
        if not (CAL_START <= offset < CAL_START + size + (CAL_END - CAL_START)):
            raise ValueError(f"Adresa 0x{offset:06X} nije u CAL regiji")
        return self.read_bytes(offset, size)

    def patch_cal(self, offset: int, data: bytes):
        """Sigurno pisanje u CAL regiju."""
        if not self.in_cal(offset):
            raise ValueError(f"Adresa 0x{offset:06X} nije u CAL regiji — odbijeno")
        self._check_bounds(offset, len(data))
        old = self._data[offset:offset+len(data)]
        if old != bytearray(data):
            self._data[offset:offset+len(data)] = data
            self._dirty = True

    # ── Diff ─────────────────────────────────────────────────────────────────

    def diff(self, other: "ME17Engine") -> list[tuple[int, int, int]]:
        """
        Usporedi ovaj fajl sa drugim.
        Returns: lista (offset, self_byte, other_byte)
        """
        if len(self._data) != len(other._data):
            raise ValueError("Fajlovi su različitih veličina")
        return [
            (i, self._data[i], other._data[i])
            for i in range(len(self._data))
            if self._data[i] != other._data[i]
        ]

    def diff_summary(self, other: "ME17Engine") -> dict:
        diffs = self.diff(other)
        regions = {
            "BOOT":  [d for d in diffs if BOOT_START <= d[0] <= BOOT_END],
            "CODE":  [d for d in diffs if CODE_START <= d[0] <= CODE_END],
            "CAL":   [d for d in diffs if CAL_START  <= d[0] <= CAL_END],
            "OTHER": [d for d in diffs if d[0] > CAL_END],
        }
        return {k: len(v) for k, v in regions.items()}
