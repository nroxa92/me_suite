"""
ME17Suite — DTC Manager
Bosch ME17.8.5 / TC1762

Upravljanje DTC (Diagnostic Trouble Code) fault kodovima.
Analizirano iz profesionalnih DTC OFF primjera (_materijali/DTC OFF/).

=== STRUKTURA DTC U ME17.8.5 ===

  Enable tablica @ ~0x021080 (CODE regija):
    Svaki bajt = enable flag jednog DTC kanala:
      0x06 = aktivno praćenje (fault se pali)
      0x05 = djelomično praćenje
      0x04 = samo upozorenje (nema limp mode)
      0x00 = isključeno

  DTC code storage (2 mjesta — main + mirror):
    LE u16, npr. P1550 = 0x1550, zapisano kao bytes [0x50, 0x15]

  DTC OFF = nuliranje enable bajti + nuliranje code bajti na oba mjesta
  Checksum se NE mijenja za DTC OFF (promjene su isključivo u CODE regiji)

=== POTVRĐENE ADRESE (ori_300, SW 10SW066726) ===
  Verificirano diff analizom rxpx300_17 P1550 i wakepro_230 P0523 fajlova.

=== TODO (Faza 6) ===
  - Mapirati sve DTC-ove u enable tablici (0x021080–0x0210FF)
  - Adrese ovise o SW verziji — dodati per-SW mapiranje
  - Dodati P0089, P1659, P0562, P0563 i ostale relevantne za Sea-Doo 300
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import Optional


# ─── DTC definicija ───────────────────────────────────────────────────────────

@dataclass
class DtcDef:
    """Definicija jednog DTC fault koda za ME17.8.5."""
    code:         int           # P-code kao int, npr. 0x1550 = P1550
    name:         str           # Kratki opis, npr. "Boost Pressure Sensor"
    enable_addr:  int           # Adresa prvog enable bajta
    enable_size:  int           # Broj enable bajti
    code_addr:    int           # Adresa main code storage (LE u16)
    mirror_addr:  int           # Adresa mirror code storage (LE u16)
    notes:        str = ""      # Napomene

    @property
    def p_code(self) -> str:
        return f"P{self.code:04X}"

    @property
    def code_bytes_le(self) -> bytes:
        """Bajti DTC koda u LE redoslijedu."""
        return struct.pack("<H", self.code)


# ─── Poznate DTC definicije (ori_300, SW 10SW066726) ─────────────────────────

DTC_REGISTRY: dict[int, DtcDef] = {

    # P1550 — senzor tlaka punjenja (boost pressure sensor)
    # Diff potvrđen: rxpx300_17 (bad vs off), 14 razlika
    0x1550: DtcDef(
        code        = 0x1550,
        name        = "Boost Pressure Sensor",
        enable_addr = 0x02108A,
        enable_size = 10,
        code_addr   = 0x021888,
        mirror_addr = 0x021BEE,
        notes       = "P1550 — prekoračenje tlaka punjenja. "
                      "Enable @ 0x02108A (10B), code @ 0x021888/0x021BEE.",
    ),

    # P0523 — senzor tlaka ulja (oil pressure sensor)
    # Diff potvrđen: wakepro_230 (bad vs off), 34 razlika
    0x0523: DtcDef(
        code        = 0x0523,
        name        = "Oil Pressure Sensor",
        enable_addr = 0x02108E,
        enable_size = 11,
        code_addr   = 0x02188C,
        mirror_addr = 0x021BF2,
        notes       = "P0523 — nizak tlak ulja. "
                      "Enable @ 0x02108E (11B), code @ 0x02188C/0x021BF2.",
    ),

    # TODO: dodati ostale DTC-ove nakon analize enable tablice
    # Kandidati za Sea-Doo 300: P0089 (fuel pressure), P1659 (EVAP),
    #   P0562/P0563 (battery voltage), P0217 (coolant temp high),
    #   P0300-P0303 (misfire), P0335/P0340 (crank/cam sensor)

}


# ─── DTC status ───────────────────────────────────────────────────────────────

@dataclass
class DtcStatus:
    defn:          DtcDef
    enable_values: list[int]    # trenutne vrijednosti enable bajti
    code_main:     int          # trenutni main code (LE u16)
    code_mirror:   int          # trenutni mirror code (LE u16)

    @property
    def is_active(self) -> bool:
        """True ako je DTC praćenje aktivno (bilo koji enable != 0x00)."""
        return any(b != 0x00 for b in self.enable_values)

    @property
    def is_off(self) -> bool:
        return not self.is_active and self.code_main == 0 and self.code_mirror == 0

    @property
    def status_str(self) -> str:
        if self.is_off:
            return "OFF"
        active_count = sum(1 for b in self.enable_values if b != 0)
        return f"AKTIVAN ({active_count}/{len(self.enable_values)} kanala)"


# ─── DTC Engine ───────────────────────────────────────────────────────────────

class DtcEngine:
    """
    DTC provjera i isključivanje za ME17.8.5.

    Checksum se NE mijenja za DTC OFF (samo CODE promjene).
    """

    def __init__(self, engine):
        """
        Args:
            engine: ME17Engine instanca
        """
        self.eng = engine

    def get_status(self, dtc_code: int) -> Optional[DtcStatus]:
        """Vrati status jednog DTC-a. Vrati None ako DTC nije poznat."""
        defn = DTC_REGISTRY.get(dtc_code)
        if not defn:
            return None
        data = self.eng.get_bytes()
        enable_vals = [data[defn.enable_addr + i] for i in range(defn.enable_size)]
        code_main   = struct.unpack_from("<H", data, defn.code_addr)[0]
        code_mirror = struct.unpack_from("<H", data, defn.mirror_addr)[0]
        return DtcStatus(defn, enable_vals, code_main, code_mirror)

    def get_all_status(self) -> list[DtcStatus]:
        """Vrati status svih poznatih DTC-ova."""
        return [s for code in DTC_REGISTRY if (s := self.get_status(code))]

    def dtc_off(self, dtc_code: int) -> dict:
        """
        Isključi DTC praćenje.

        Nulira:
          1. Sve enable bajte na 0x00
          2. Main code storage na 0x0000
          3. Mirror code storage na 0x0000

        Checksum se NE mijenja (promjene su u CODE regiji).

        Returns:
            {"status": "OK"|"ERROR", "message": str, ...}
        """
        defn = DTC_REGISTRY.get(dtc_code)
        if not defn:
            return {"status": "ERROR", "message": f"Nepoznati DTC: P{dtc_code:04X}"}

        data = self.eng.get_bytes()
        status_before = self.get_status(dtc_code)

        if status_before.is_off:
            return {
                "status":  "ALREADY_OFF",
                "message": f"{defn.p_code} je već isključen.",
            }

        # Nuliranje enable bajti
        for i in range(defn.enable_size):
            self.eng.write_u8(defn.enable_addr + i, 0x00)

        # Nuliranje code storage (main + mirror)
        self.eng.write_u16_le(defn.code_addr,   0x0000)
        self.eng.write_u16_le(defn.mirror_addr, 0x0000)

        return {
            "status":         "OK",
            "message":        f"{defn.p_code} ({defn.name}) — isključen.",
            "enable_before":  [hex(b) for b in status_before.enable_values],
            "code_before":    f"0x{status_before.code_main:04X}",
            "bytes_changed":  defn.enable_size + 4,
        }

    def dtc_on(self, dtc_code: int, enable_value: int = 0x06) -> dict:
        """
        Vrati DTC praćenje na zadanu vrijednost (default 0x06 = aktivno).

        NAPOMENA: ovo vraća enable bajte ali ne može znati originalnu
        konfiguraciju — pišemo isti enable_value na sve kanale.
        Za točan restore koristiti originalnu bin datoteku.

        Returns:
            {"status": "OK"|"ERROR", "message": str}
        """
        defn = DTC_REGISTRY.get(dtc_code)
        if not defn:
            return {"status": "ERROR", "message": f"Nepoznati DTC: P{dtc_code:04X}"}

        if enable_value not in (0x04, 0x05, 0x06):
            return {"status": "ERROR", "message": f"Nevažeća enable vrijednost: 0x{enable_value:02X}"}

        # Postavi enable bajte
        for i in range(defn.enable_size):
            self.eng.write_u8(defn.enable_addr + i, enable_value)

        # Postavi code storage
        self.eng.write_u16_le(defn.code_addr,   defn.code)
        self.eng.write_u16_le(defn.mirror_addr, defn.code)

        return {
            "status":  "OK",
            "message": f"{defn.p_code} ({defn.name}) — uključen (enable=0x{enable_value:02X}).",
        }

    def dtc_off_all(self) -> dict:
        """Isključi sve poznate DTC-ove odjednom."""
        results = {}
        for code in DTC_REGISTRY:
            results[f"P{code:04X}"] = self.dtc_off(code)
        ok = sum(1 for r in results.values() if r["status"] in ("OK", "ALREADY_OFF"))
        return {
            "status":  "OK" if ok == len(results) else "PARTIAL",
            "results": results,
            "total":   len(results),
            "changed": sum(1 for r in results.values() if r["status"] == "OK"),
        }
