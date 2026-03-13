"""
ME17Suite — Checksum Engine
Bosch ME17.8.5 / TC1762

Status istrage (2026-03-13):
  BOOT diff ORI vs STG2 ima 140 bajtova u 3 bloka:
    0x00001F  5B  -- SW ID promjena ("66726" -> "40039")  [POTVRDJENO]
    0x000030  4B  -- E505BC0B -> 9FC76FAD                 [CHECKSUM LOKACIJA!]
    0x007E7C  132B -- veci blok, vjerovatno SW-specifican  [NEISTRAZENO]

  Checksum @ 0x30 je 4-bajtna vrijednost (u32, big-endian pretpostavka).
  Algoritam NIJE identifikovan:
    - Bosch CRC32 (poly 0x04C11DB7) nad CODE: ne poklapa se
    - Standard zlib CRC32 nad CODE: ne poklapa se
    - Simple sum32 nad raznim regijama: ne poklapa se
    - Testirane regije: BOOT, CODE, BOOT+CODE, podnizovi, s/bez 0x30 patchom

  TODO: reverse eng checksum rutine iz TC1762 firmware koda @ BOOT

Algoritam (pretpostavka):
  CRC32(Bosch poly) over CODE region (0x010000-0x05FFFF)
  Rezultat pohranjen u BOOT header (trazimo tocnu adresu)
"""

from __future__ import annotations
import struct
from .engine import ME17Engine, BOOT_START, BOOT_END, CODE_START, CODE_END


# ─── CRC32 Bosch ──────────────────────────────────────────────────────────────

CRC32_POLY = 0x04C11DB7
CRC32_INIT = 0xFFFFFFFF
CRC32_XOR  = 0xFFFFFFFF


def _crc32_table() -> list[int]:
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            crc = ((crc << 1) & 0xFFFFFFFF) ^ CRC32_POLY if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return table


_CRC_TABLE = _crc32_table()


def crc32_bosch(data: bytes, init: int = CRC32_INIT) -> int:
    """CRC32 s Bosch polynomom (big-endian bit order)."""
    crc = init
    for b in data:
        idx = ((crc >> 24) ^ b) & 0xFF
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[idx]
    return crc ^ CRC32_XOR


def crc32_std(data: bytes) -> int:
    """Standardni Python CRC32 (za usporedbu)."""
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF


def simple_sum16(data: bytes) -> int:
    """16-bit suma svih u16 BE."""
    return sum((data[i] << 8) | data[i+1] for i in range(0, len(data)-1, 2)) & 0xFFFF


def simple_sum32(data: bytes) -> int:
    """32-bit suma svih u32 BE."""
    return sum(struct.unpack_from(">I", data, i)[0] for i in range(0, len(data)-3, 4)) & 0xFFFFFFFF


# ─── ChecksumEngine ───────────────────────────────────────────────────────────

class ChecksumEngine:
    """
    Checksum analiza i (buduca) korekcija za ME17.8.5 / TC1762.

    Trenutno stanje:
      - verify()              — provjera SW ID + CAL integriteta
      - analyze_boot_diff()   — usporedba BOOT regija dva fajla (istrazivanje)
      - find_checksum_candidates() — heuristika za BOOT header kandidate
      - try_crc_match()       — pokusaj pronalaska CRC32 u BOOT-u
      - update_all()          — NOT_IMPLEMENTED (cekamo potvrdu lokacija)
    """

    def __init__(self, engine: ME17Engine):
        self.eng = engine

    # ── Verify ────────────────────────────────────────────────────────────────

    def verify(self) -> dict:
        data = self.eng.get_bytes()
        results = {}

        # BOOT CRC32 (za referencu, lokacija checksuma nepoznata)
        boot = data[0x0000:0x10000]
        results["boot_crc32_bosch"] = {
            "value":  f"0x{crc32_bosch(boot):08X}",
            "status": "UNKNOWN -- lokacija checksuma u BOOT-u nije identificirana",
        }

        # CODE CRC32 (ovo je vjerovatno sto se checksum-a)
        code = data[CODE_START:CODE_END+1]
        results["code_crc32_bosch"] = {
            "value":  f"0x{crc32_bosch(code):08X}",
            "status": "Izracunat -- trazi se gdje je pohranjen u BOOT-u",
        }

        # SW ID
        sw = data[0x001A:0x0024].rstrip(b"\x00").decode("ascii", errors="replace")
        results["sw_id"] = {
            "value":  sw,
            "status": "OK" if sw.startswith("10SW") else "WARN",
        }

        # CAL integrity
        cal = data[0x060000:0x160000]
        non_zero = sum(1 for b in cal if b != 0)
        results["cal_integrity"] = {
            "non_zero_bytes": non_zero,
            "status": "OK" if non_zero > 10000 else "WARN -- CAL prazna?",
        }

        return results

    # ── BOOT diff analiza (Faza 4 istrazivanje) ───────────────────────────────

    def analyze_boot_diff(self, other: "ME17Engine") -> dict:
        """
        Usporedi BOOT regije dva fajla (ORI vs STG2).
        Grupira razlike u blokove -- to su kandidati za checksum lokacije.

        Returns:
          {
            total_changed: int,
            changed_bytes: [(offset, val_self, val_other), ...],
            blocks: [{"offset", "size", "val_ori", "val_stg2"}, ...],
            crc_in_boot: {adresa: True/False}  -- je li CODE CRC u BOOT-u?
          }
        """
        d1 = self.eng.get_bytes()
        d2 = other.get_bytes()

        diffs = [(i, d1[i], d2[i]) for i in range(min(0x10000, len(d1), len(d2))) if d1[i] != d2[i]]

        # Grupisi u blokove (gap <= 2 bajta)
        blocks = []
        if diffs:
            start = prev = diffs[0][0]
            for off, v1, v2 in diffs[1:]:
                if off - prev > 2:
                    if prev - start >= 3:   # blok >= 4 bajta
                        size = prev - start + 1
                        chunk1 = d1[start:start+size]
                        chunk2 = d2[start:start+size]
                        blocks.append({
                            "offset":   start,
                            "size":     size,
                            "val_ori":  " ".join(f"{b:02X}" for b in chunk1[:8]),
                            "val_stg2": " ".join(f"{b:02X}" for b in chunk2[:8]),
                        })
                    start = off
                prev = off
            # Zadnji blok
            if prev - start >= 3:
                size = prev - start + 1
                blocks.append({
                    "offset":   start,
                    "size":     size,
                    "val_ori":  " ".join(f"{b:02X}" for b in d1[start:start+size][:8]),
                    "val_stg2": " ".join(f"{b:02X}" for b in d2[start:start+size][:8]),
                })

        # Pokusaj pronaci CODE CRC32 u BOOT-u
        code_crc1 = crc32_bosch(bytes(d1[CODE_START:CODE_END+1]))
        code_crc2 = crc32_bosch(bytes(d2[CODE_START:CODE_END+1]))
        crc_in_boot = self._find_u32_in_boot(d1, code_crc1)

        return {
            "total_changed": len(diffs),
            "changed_bytes": diffs[:20],   # prvih 20 za debug
            "blocks":        blocks,
            "code_crc_ori":  f"0x{code_crc1:08X}",
            "code_crc_stg2": f"0x{code_crc2:08X}",
            "crc_in_boot":   crc_in_boot,
        }

    def _find_u32_in_boot(self, data: bytes, value: int) -> dict:
        """Trazi u32 vrijednost (BE i LE) u BOOT regionu."""
        be = struct.pack(">I", value)
        le = struct.pack("<I", value)
        results = {}
        boot = data[:0x10000]
        for i in range(0, len(boot)-3):
            if boot[i:i+4] == be: results[f"0x{i:06X}"] = "BE"
            if boot[i:i+4] == le: results[f"0x{i:06X}"] = "LE"
        return results

    # ── CRC match pokusaj ─────────────────────────────────────────────────────

    def try_crc_match(self) -> list[dict]:
        """
        Pokusaj naci checksum pokusavanjem raznih regija i algoritama.
        Trazi rezultat u BOOT-u.

        Returns: lista potencijalnih pogodaka.
        """
        data = self.eng.get_bytes()
        boot = data[:0x10000]
        hits = []

        # Regije za testiranje
        regions = [
            ("CODE full",    CODE_START, CODE_END+1),
            ("CODE first8K", CODE_START, CODE_START+0x2000),
            ("CODE last8K",  CODE_END-0x2000, CODE_END+1),
            ("BOOT+CODE",    0, CODE_END+1),
        ]

        for name, start, end in regions:
            chunk = bytes(data[start:end])

            for algo, fn in [
                ("CRC32_Bosch", crc32_bosch),
                ("CRC32_std",   crc32_std),
                ("sum32_BE",    simple_sum32),
            ]:
                val = fn(chunk)
                found = self._find_u32_in_boot(data, val)
                if found:
                    hits.append({
                        "region": name,
                        "algo":   algo,
                        "value":  f"0x{val:08X}",
                        "found_at": found,
                    })

        return hits

    # ── Kandidati ─────────────────────────────────────────────────────────────

    def find_checksum_candidates(self) -> list[dict]:
        """Trazi ne-nul u32 vrijednosti u BOOT header-u (0x000-0x200)."""
        data = self.eng.get_bytes()
        cands = []
        for off in range(0, min(0x200, len(data)-3), 4):
            v = struct.unpack_from(">I", data, off)[0]
            if v not in (0, 0xFFFFFFFF, 0xC3C3C3C3):
                cands.append({
                    "offset": off,
                    "value":  f"0x{v:08X}",
                    "type":   "u32 BE candidate",
                })
        return cands

    # ── Update all ────────────────────────────────────────────────────────────

    def needs_update(self) -> bool:
        return self.eng.dirty

    def update_all(self) -> dict:
        """
        Update checksuma. NOT YET IMPLEMENTED.

        Sljedeci koraci:
          1. try_crc_match() na paru ORI+STG2 da pronadjemo lokaciju
          2. Kada potvrdimo lokaciju, implementirati pisanje
          3. Testirati na bench ECU-u
        """
        if not self.eng.dirty:
            return {"status": "OK", "message": "Nema izmjena, checksum nije potreban."}

        # Pokusaj auto-detekcije
        hits = self.try_crc_match()
        if hits:
            return {
                "status": "CANDIDATE_FOUND",
                "message": f"Potencijalni pogodak: {hits[0]}. Potrebna rucna verifikacija.",
                "hits": hits,
            }

        return {
            "status": "NOT_IMPLEMENTED",
            "message": (
                "Checksum update nije implementiran. "
                "Lokacije u BOOT-u su u istrazivanju. "
                "Koristite kompatibilan flash alat (KTAG, Flex, CMD Flash) "
                "koji automatski racuna checksum."
            ),
        }
