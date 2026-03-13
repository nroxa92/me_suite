"""
ME17Suite — Map Editor

Cita i pise kalibracijske mape u binary fajl.
Svaki write automatski updateuje mirror kopiju (ako postoji).
Validira vrijednosti prije pisanja.
Podrzava: u8, u16 BE/LE, i16 BE/LE
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .engine import ME17Engine, CAL_START, CAL_END, CODE_START, CODE_END
from .map_finder import FoundMap, MapDef


@dataclass
class EditResult:
    ok:            bool
    cells_changed: int
    message:       str


class MapEditor:
    """
    Wrapper oko ME17Engine za sigurno editovanje mapa.
    - Validira display vrijednosti i konvertuje u raw
    - Auto-sinkronizira mirror kopiju
    - Podrzava u8, u16 BE/LE, i16 BE/LE formate
    """

    def __init__(self, engine: ME17Engine):
        self.eng = engine

    # ── Read ─────────────────────────────────────────────────────────────────

    def read_map(self, found: FoundMap) -> list[list[float]]:
        """Vrati 2D display-scaled vrijednosti (rows × cols)."""
        defn = found.defn
        n    = defn.rows * defn.cols
        raw  = self._read_raw(found.address, n, defn)
        flat = [v * defn.scale + defn.offset_val for v in raw]
        return [flat[r * defn.cols:(r+1) * defn.cols] for r in range(defn.rows)]

    def read_raw(self, found: FoundMap) -> list[list[int]]:
        """Vrati sirove (nekonvertovane) vrijednosti."""
        defn = found.defn
        n    = defn.rows * defn.cols
        raw  = self._read_raw(found.address, n, defn)
        return [raw[r * defn.cols:(r+1) * defn.cols] for r in range(defn.rows)]

    # ── Write ─────────────────────────────────────────────────────────────────

    def write_cell(self, found: FoundMap, row: int, col: int,
                   display_value: float) -> EditResult:
        """
        Upisi jednu celiju mape.
        Automatski sinkronizira mirror kopiju.
        """
        defn = found.defn

        if defn.scale == 0.0:
            return EditResult(False, 0, "Scale faktor nije poznat — editovanje blokirano")

        raw = round((display_value - defn.offset_val) / defn.scale)

        # Validacija
        raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max
        raw_min = defn.raw_min
        if not (raw_min <= raw <= raw_max):
            disp_min = raw_min * defn.scale + defn.offset_val
            disp_max = raw_max * defn.scale + defn.offset_val
            return EditResult(
                False, 0,
                f"Vrijednost {display_value:.3f} izvan opsega "
                f"[{disp_min:.3f}–{disp_max:.3f}] {defn.unit}"
            )

        cell_idx = row * defn.cols + col
        addr     = found.address + cell_idx * defn.cell_bytes

        if not (self.eng.in_cal(addr) or self.eng.in_code(addr)):
            return EditResult(False, 0, f"Adresa 0x{addr:06X} nije u CAL ili CODE regiji")

        # Citaj staru vrijednost
        old = self._read_one(addr, defn)

        # Pisi
        self._write_one(addr, raw, defn)
        changed = 1 if old != raw else 0

        # Mirror sync
        if defn.mirror_offset and changed:
            mirror_addr = found.address + defn.mirror_offset + cell_idx * defn.cell_bytes
            if self.eng.in_cal(mirror_addr) or self.eng.in_code(mirror_addr):
                self._write_one(mirror_addr, raw, defn)

        return EditResult(True, changed, f"OK: 0x{addr:06X}  raw {old} -> {raw}")

    def write_map(self, found: FoundMap, values_2d: list[list[float]]) -> EditResult:
        """
        Upisi cijelu mapu odjednom.
        values_2d: lista redova, svaki red je lista display vrijednosti.
        """
        defn = found.defn

        if defn.scale == 0.0:
            return EditResult(False, 0, "Scale faktor nije poznat — editovanje blokirano")

        flat = [v for row in values_2d for v in row]

        if len(flat) != defn.rows * defn.cols:
            return EditResult(False, 0,
                f"Pogresan broj vrijednosti: {len(flat)} (ocekivano {defn.rows * defn.cols})")

        raw_max = 0xFF if defn.dtype == "u8" else defn.raw_max

        raw_vals = []
        for v in flat:
            raw = round((v - defn.offset_val) / defn.scale)
            if not (defn.raw_min <= raw <= raw_max):
                return EditResult(False, 0,
                    f"Vrijednost {v:.3f} izvan opsega "
                    f"[{defn.raw_min * defn.scale:.3f}–{raw_max * defn.scale:.3f}] {defn.unit}")
            raw_vals.append(raw)

        # Batch write — main
        for i, raw in enumerate(raw_vals):
            addr = found.address + i * defn.cell_bytes
            self._write_one(addr, raw, defn)

        # Mirror sync
        if defn.mirror_offset:
            for i, raw in enumerate(raw_vals):
                mirror_addr = found.address + defn.mirror_offset + i * defn.cell_bytes
                if self.eng.in_cal(mirror_addr) or self.eng.in_code(mirror_addr):
                    self._write_one(mirror_addr, raw, defn)

        return EditResult(True, len(raw_vals), f"Zapisano {len(raw_vals)} celija")

    # ── Rev limiter shortcut ──────────────────────────────────────────────────

    def write_rev_limit_scalar(self, found: FoundMap, rpm: int) -> EditResult:
        """
        Pisi scalar rev limiter vrijednost (1×1 mapa).
        """
        if not (4000 <= rpm <= 13000):
            return EditResult(False, 0, f"RPM {rpm} izvan [4000–13000]")

        old = self._read_one(found.address, found.defn)
        self.eng.write_u16_le(found.address, rpm)
        return EditResult(True, 1 if old != rpm else 0,
                          f"Rev limiter @ 0x{found.address:06X}: {old} → {rpm} rpm")

    def write_rev_limit_row(self, found: FoundMap, row_idx: int,
                            soft_rpm: int, mid_rpm: int, hard_rpm: int) -> EditResult:
        """
        Pisi stride-0x18 rev limiter tabelu.
        Validira: soft < mid < hard.
        """
        if not (4000 <= soft_rpm <= 12000):
            return EditResult(False, 0, f"Soft limit {soft_rpm} izvan [4000–12000]")
        if not (soft_rpm < mid_rpm < hard_rpm):
            return EditResult(False, 0, "Mora biti: soft < mid < hard")
        if hard_rpm > 12000:
            return EditResult(False, 0, f"Hard limit {hard_rpm} previsok (max 12000)")

        STRIDE = 0x18
        base   = found.address + row_idx * STRIDE

        for addr, rpm in [(base, soft_rpm), (base + STRIDE, mid_rpm), (base + STRIDE*2, hard_rpm)]:
            self.eng.write_u16_le(addr, rpm)

        return EditResult(True, 3,
            f"Rev limiter row {row_idx}: {soft_rpm}/{mid_rpm}/{hard_rpm} rpm")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _read_raw(self, base: int, count: int, defn: MapDef) -> list[int]:
        """Citaj 'count' vrijednosti od 'base', koristeci format iz MapDef."""
        result = []
        data   = self.eng.get_bytes()
        size   = defn.cell_bytes
        bo     = "big" if defn.byte_order == "BE" else "little"
        signed = defn.dtype.startswith("i")

        for i in range(count):
            off = base + i * size
            if off + size > len(data):
                result.append(0)
                continue
            raw = int.from_bytes(data[off:off + size], bo)
            if signed and size == 2 and raw >= 0x8000:
                raw -= 65536
            result.append(raw)
        return result

    def _read_one(self, addr: int, defn: MapDef) -> int:
        data   = self.eng.get_bytes()
        size   = defn.cell_bytes
        bo     = "big" if defn.byte_order == "BE" else "little"
        if addr + size > len(data):
            return 0
        raw = int.from_bytes(data[addr:addr + size], bo)
        if defn.dtype.startswith("i") and size == 2 and raw >= 0x8000:
            raw -= 65536
        return raw

    def _write_one(self, addr: int, raw: int, defn: MapDef) -> None:
        """Pisi jednu vrijednost na adresu, koristeci format iz MapDef."""
        if defn.dtype == "u8":
            self.eng.write_u8(addr, max(0, min(0xFF, raw)))
        elif defn.dtype == "u16":
            if defn.byte_order == "BE":
                self.eng.write_u16_be(addr, max(0, min(0xFFFF, raw)))
            else:
                self.eng.write_u16_le(addr, max(0, min(0xFFFF, raw)))
        elif defn.dtype == "i16":
            if defn.byte_order == "BE":
                self.eng.write_i16_be(addr, max(-32768, min(32767, raw)))
            else:
                self.eng.write_i16_le(addr, max(-32768, min(32767, raw)))
