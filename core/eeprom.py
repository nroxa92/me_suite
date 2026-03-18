"""
ME17Suite — EEPROM Parser
Parsira BRP/Bosch ME17 EEPROM (32KB) za Sea-Doo / Ski-Doo / Can-Am.

Potvrđena struktura (3 uzorka: RXP 300 2021, Spark 18, RXP 20):
  0x0000        Header/checksum blok (FF 00 ...)
  0x0013–0x001A  Datum prvog programiranja (DD-MM-YY, ASCII)
  0x001E–0x0025  Datum zadnjeg ažuriranja (DD-MM-YY, ASCII)
  0x0032–0x003B  MPEM SW ID (10 ASCII)
  0x0040–0x0049  Servisni SW ID (10 ASCII, uvijek "1037500313")
  0x004C         Broj programiranja (u8 counter)
  0x004D–0x0057  ECU serijski broj (11 ASCII "SF00HMxxxxx")
  0x0082–0x008D  Hull ID / VIN (12 ASCII "YDVxxxxxxxxx")
  0x0102–0x0112  Dealer naziv (ASCII, max 16 chars)
  0x0125–0x0129  Odometar (5-digit ASCII string, BRP unutarnje jedinice)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

EEPROM_SIZE = 32_768  # 32KB

# ─── EEPROM offset 0x0125 — neidentificirano polje ───────────────────────────
# Vrijednost: 5-digit ASCII string. Ponavljaju se "60620", "BRP10", ili 0x00.
# NIJE hw timer ni radni sati — hipoteza HHHM odbačena (nije konzistentno).
# Pravi radni sati su u circular bufferu (isti mehanizam kao odometar):
#   064/063 HW: @ 0x0562 (u16 LE, minute), backup: 0x0D62 / 0x1562
#   062 HW: @ 0x5062 → 0x4562 → 0x1062 (rotacija)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EepromInfo:
    """Parsirani podaci iz EEPROM dumpa."""
    is_valid: bool = False
    errors: list = field(default_factory=list)

    # Identifikacija
    hull_id: str = ""           # VIN / Hull ID (YDVxxxxxxxxx)
    serial_ecu: str = ""        # ECU serijski broj (SF00HMxxxxx)
    mpem_sw: str = ""           # MPEM SW verzija (1037xxxxxx)
    service_sw: str = ""        # Servisni SW ID (uvijek 1037500313)

    # Datumi
    date_first_prog: str = ""   # Datum prvog programiranja (DD-MM-YY)
    date_last_update: str = ""  # Datum zadnjeg ažuriranja (DD-MM-YY)
    prog_count: int = 0         # Broj programiranja

    # Vlasnik / dealer
    dealer_name: str = ""       # Dealer naziv (iz BUDS2)

    # Odometar (circular buffer, u minutama)
    odo_raw: int = 0            # Vrijednost iz circular buffera (u16 LE, minute); adresa ovisi o HW tipu

    # Meta
    file_size: int = 0
    source_path: str = ""

    def odo_hhmm(self) -> str:
        """Formatira odometar (minute) kao HHHh MMmin."""
        if self.odo_raw <= 0:
            return "—"
        hours = self.odo_raw // 60
        minutes = self.odo_raw % 60
        return f"{hours}h {minutes:02d}min"

    def model_year_guess(self) -> Optional[str]:
        """Pokušaj ekstrakcije godine iz hull ID (YDV89660E121 → E=2014? 1=2021?)."""
        if len(self.hull_id) >= 12:
            year_char = self.hull_id[9]   # 10. znak = model year code
            year_digit = self.hull_id[11] # 12. znak = god. fab.
            return f"{year_char}{year_digit}"
        return None

    def mpem_model_guess(self) -> str:
        """Grubo određivanje modela prema MPEM SW prefiksu."""
        mpem = self.mpem_sw
        if mpem.startswith("10375500"):
            return "300hp (RXP-X / GTX 300 / RXT-X 300)"
        elif mpem.startswith("10375258"):
            return "Spark (90/110hp)"
        elif mpem.startswith("10375091") or mpem.startswith("10375092"):
            return "260hp (RXT-X 260 / RXP-X 260)"
        elif mpem.startswith("1037"):
            return f"BRP / Sea-Doo ({mpem})"
        return "Nepoznat model"


class EepromParser:
    """Čita i parsira BRP ME17 EEPROM dump fajl."""

    DATE_OFFSET_1  = 0x0013  # Datum prvog programiranja
    DATE_OFFSET_2  = 0x001E  # Datum zadnjeg ažuriranja
    MPEM_SW_OFFSET = 0x0032  # MPEM SW ID (10B)
    SVC_SW_OFFSET  = 0x0040  # Servisni SW (10B)
    PROG_CNT_OFF   = 0x004C  # Broj programiranja (u8)
    ECU_SER_OFFSET = 0x004D  # ECU serial "SF00HM..." (11B)
    HULL_OFFSET    = 0x0082  # Hull ID / VIN (12B)
    DEALER_OFFSET  = 0x0102  # Dealer naziv (max 16B ASCII)
    ODO_OFFSET     = 0x0125  # Odometar (5-digit ASCII)

    def parse(self, path: str) -> EepromInfo:
        info = EepromInfo(source_path=str(path))
        try:
            data = Path(path).read_bytes()
        except Exception as e:
            info.errors.append(f"Greška čitanja: {e}")
            return info

        info.file_size = len(data)

        if len(data) < 0x200:
            info.errors.append(f"Fajl premali ({len(data)}B), očekivano min 512B")
            return info

        if len(data) != EEPROM_SIZE:
            info.errors.append(f"Veličina {len(data):,}B != {EEPROM_SIZE:,}B (32KB)")
            # ne vraćamo — pokušaj parsirati i dalje

        def _str(offset: int, length: int) -> str:
            raw = data[offset:offset + length]
            return raw.split(b'\x00')[0].rstrip(b' ').decode('ascii', errors='replace')

        info.date_first_prog = _str(self.DATE_OFFSET_1, 8)
        info.date_last_update = _str(self.DATE_OFFSET_2, 8)
        info.mpem_sw = _str(self.MPEM_SW_OFFSET, 10)
        info.service_sw = _str(self.SVC_SW_OFFSET, 10)
        info.prog_count = data[self.PROG_CNT_OFF] if len(data) > self.PROG_CNT_OFF else 0
        info.serial_ecu = _str(self.ECU_SER_OFFSET, 11)
        info.hull_id = _str(self.HULL_OFFSET, 12)
        info.dealer_name = _str(self.DEALER_OFFSET, 16).strip()

        odo_str = _str(self.ODO_OFFSET, 5).strip()
        try:
            info.odo_raw = int(odo_str)
        except ValueError:
            info.odo_raw = 0
            if odo_str:
                info.errors.append(f"Odometar: ne može se parsirati '{odo_str}'")

        # Provjera valjanosti
        if info.hull_id.startswith("YDV") and len(info.mpem_sw) >= 6:
            info.is_valid = True
        elif info.hull_id or info.mpem_sw:
            info.is_valid = True
            info.errors.append("Nepotpuni podaci (moguće drugačiji format)")
        else:
            info.errors.append("Nisu pronađeni Hull ID ni MPEM SW — nije validan EEPROM?")

        return info

    def parse_bytes(self, data: bytes, source: str = "<bytes>") -> EepromInfo:
        """Parsira iz već učitanog byte buffera."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
        try:
            tmp.write(data)
            tmp.close()
            result = self.parse(tmp.name)
            result.source_path = source
            return result
        finally:
            os.unlink(tmp.name)
