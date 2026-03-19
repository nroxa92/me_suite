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
  0x0125–0x0129  NIJE hw timer — SW konstanta ("60620", "BRP10") ili nula
                 Pravi radni sati su u circular bufferu (vidi ODO adrese po HW tipu)

Circular buffer — radni sati u minutama (potvrdjeno 2026-03-18):
  HW 064 (1037550003): primarno @ 0x0562 (u16 LE), backup: 0x0D62, 0x1562
  HW 063 (1037525858): max(0x4562, 0x0562), fallback: 0x0DE2
  HW 062 (1037509210): rotacija 0x5062 -> 0x4562 -> 0x1062
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

    # Odometar / radni sati (circular buffer, u minutama)
    odo_raw: int = 0            # Vrijednost iz circular buffera (u16 LE, minute)
    hw_type: str = ""           # HW tip: "062", "063", "064", ili ""

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
    """Cita i parsira BRP ME17 EEPROM dump fajl."""

    DATE_OFFSET_1  = 0x0013  # Datum prvog programiranja
    DATE_OFFSET_2  = 0x001E  # Datum zadnjeg azuriranja
    MPEM_SW_OFFSET = 0x0032  # MPEM SW ID (10B)
    SVC_SW_OFFSET  = 0x0040  # Servisni SW (10B)
    PROG_CNT_OFF   = 0x004C  # Broj programiranja (u8)
    ECU_SER_OFFSET = 0x004D  # ECU serial "SF00HM..." (11B)
    HULL_OFFSET    = 0x0082  # Hull ID / VIN (12B)
    DEALER_OFFSET  = 0x0102  # Dealer naziv (max 16B ASCII)
    # ODO_OFFSET  = 0x0125  # NE koristiti! SW konstanta, ne odometar

    # Circular buffer ODO adrese po HW tipu (istraživanje 2026-03-18/19)
    # Potvrđeno na 35 EEPROM dumpova — sve adrese verificirane

    # 063/064 standardni layout (MPEM kopija @ 0x05B0):
    _ODO_STANDARD     = 0x0562   # anchor slot @ 0x0550 + 18 — svi 063/064 novi firmware
    # 063/064 stari layout (MPEM samo u headeru @ 0x0032, anchor pomaknut +0x4000):
    _ODO_STARI_LAYOUT = 0x4562   # potvrđeno: 063 0-55, 063 77-16, 063 121-55, 063 167, 064 13
    # 064 wrapping layout (višestruki buffer wrap, mirror potvrda):
    _ODO_WRAP_PRIM    = 0x0D62   # potvrđeno: 064 211-07 (12667 min)
    _ODO_WRAP_MIRROR  = 0x1562   # mirror za 0x0D62 — SAMO za potvrdu, ne samostalno
    # 064 još stariji layout (anchor @ 0x047E + 18):
    _ODO_OLD_064      = 0x0490   # potvrđeno: 064 58 (3503 min), 064 211.bin (12667 min)
    # 063 visoke minute:
    _ODO_063_HIGH     = 0x0DE2   # potvrđeno: 063 585-42 (35142 min)
    # 062 rotacijski buffer (od najnovijeg prema najstarijem):
    _ODO_062_HIGH_B   = 0x5062   # najnoviji
    _ODO_062_HIGH_A   = 0x4562   # drugi
    _ODO_062_LOW      = 0x1062   # najstariji

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

        # ── HW tip detekcija iz MPEM SW prefiksa ─────────────────────────────
        mpem = info.mpem_sw
        if mpem.startswith("10375500"):
            info.hw_type = "064"
        elif mpem.startswith("10375258"):
            info.hw_type = "063"
        elif mpem.startswith("10375091") or mpem.startswith("10375092"):
            info.hw_type = "062"
        else:
            info.hw_type = ""

        # ── Circular buffer ODO (radni sati u minutama) ───────────────────
        def _u16le(off: int) -> int:
            if off + 2 > len(data): return 0
            return int.from_bytes(data[off:off+2], 'little')

        if info.hw_type == "062":
            # Rotacijski buffer — od najnovijeg prema najstarijem
            for addr in (self._ODO_062_HIGH_B, self._ODO_062_HIGH_A, self._ODO_062_LOW):
                v = _u16le(addr)
                if 1 <= v <= 65000:
                    info.odo_raw = v; break
        elif info.hw_type == "063":
            # Spark ECU: uzimamo max od standardnog i stari-layout mjesta
            v_std  = _u16le(self._ODO_STANDARD)      # 0x0562 (kada buffer wrapa)
            v_star = _u16le(self._ODO_STARI_LAYOUT)  # 0x4562 (stariji firmware)
            best = max(v if 1 <= v <= 65000 else 0 for v in (v_std, v_star))
            if best:
                info.odo_raw = best
            else:
                # 063 visoke minute (>~30000 min, npr. 063 585-42)
                v = _u16le(self._ODO_063_HIGH)
                if 1 <= v <= 65000:
                    info.odo_raw = v
        else:
            # 064 / nepoznat HW — višeslojna detekcija
            # 1. Standardni anchor (novi firmware)
            v = _u16le(self._ODO_STANDARD)
            if 1 <= v <= 65000:
                info.odo_raw = v
            else:
                # 2. Stari layout (anchor pomaknut +0x4000)
                v = _u16le(self._ODO_STARI_LAYOUT)
                if 1 <= v <= 65000:
                    info.odo_raw = v
                else:
                    # 3. Wrapping layout (potvrdi mirror-om)
                    v_wrap = _u16le(self._ODO_WRAP_PRIM)
                    if 1 <= v_wrap <= 65000:
                        v_mir = _u16le(self._ODO_WRAP_MIRROR)
                        if 1 <= v_mir <= 65000 and abs(v_mir - v_wrap) <= 100:
                            info.odo_raw = max(v_wrap, v_mir)
                        else:
                            info.odo_raw = v_wrap
                    else:
                        # 4. Još stariji 064 anchor (064 58, 064 211.bin)
                        v = _u16le(self._ODO_OLD_064)
                        if 1 <= v <= 65000:
                            info.odo_raw = v

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


class EepromEditor:
    """
    Editor za BRP/Bosch ME17 EEPROM dump (32KB).

    EEPROM nema checksum — izmjene se direktno upisuju.
    Sigurna polja za edit: hull_id, dealer_name, datumi, prog_count.
    NE mijenjati: serial_ecu, mpem_sw, service_sw, odo (circular buffer).

    Primjer:
        editor = EepromEditor("path/to/eeprom.bin")
        editor.set_hull_id("YDV89660M123")
        editor.set_dealer_name("MY SHOP")
        editor.set_date_first_prog("01-01-24")
        editor.set_date_last_update("01-01-24")
        editor.set_prog_count(1)
        editor.save("path/to/eeprom_modified.bin")
    """

    # Offseti (isti kao EepromParser)
    DATE_OFFSET_1  = EepromParser.DATE_OFFSET_1   # 0x0013
    DATE_OFFSET_2  = EepromParser.DATE_OFFSET_2   # 0x001E
    MPEM_SW_OFFSET = EepromParser.MPEM_SW_OFFSET  # 0x0032
    SVC_SW_OFFSET  = EepromParser.SVC_SW_OFFSET   # 0x0040
    PROG_CNT_OFF   = EepromParser.PROG_CNT_OFF    # 0x004C
    ECU_SER_OFFSET = EepromParser.ECU_SER_OFFSET  # 0x004D
    HULL_OFFSET    = EepromParser.HULL_OFFSET      # 0x0082
    DEALER_OFFSET  = EepromParser.DEALER_OFFSET    # 0x0102

    def __init__(self, path: str):
        self._path = str(path)
        data = Path(path).read_bytes()
        if len(data) != EEPROM_SIZE:
            raise ValueError(f"EEPROM veličina {len(data)}B != {EEPROM_SIZE}B (32KB)")
        self._data = bytearray(data)

    @classmethod
    def from_bytes(cls, data: bytes, source: str = "<bytes>") -> "EepromEditor":
        """Kreira editor iz byte buffera (bez čitanja fajla)."""
        obj = object.__new__(cls)
        obj._path = source
        if len(data) != EEPROM_SIZE:
            raise ValueError(f"EEPROM veličina {len(data)}B != {EEPROM_SIZE}B")
        obj._data = bytearray(data)
        return obj

    def _write_ascii(self, offset: int, length: int, value: str) -> None:
        """Upisuje ASCII string na offset, padira s 0x00."""
        encoded = value.encode('ascii', errors='replace')[:length]
        self._data[offset:offset + length] = encoded.ljust(length, b'\x00')

    # ── Javne metode za editiranje ────────────────────────────────────────────

    def set_hull_id(self, hull_id: str) -> None:
        """Upisuje Hull ID / VIN (max 12 ASCII znakova, format YDVxxxxxxxxx)."""
        if len(hull_id) > 12:
            raise ValueError(f"Hull ID max 12 znakova (dobiveno: {len(hull_id)})")
        self._write_ascii(self.HULL_OFFSET, 12, hull_id)

    def set_dealer_name(self, name: str) -> None:
        """Upisuje dealer naziv (max 16 ASCII znakova)."""
        if len(name) > 16:
            raise ValueError(f"Dealer naziv max 16 znakova (dobiveno: {len(name)})")
        self._write_ascii(self.DEALER_OFFSET, 16, name)

    def set_date_first_prog(self, date: str) -> None:
        """Upisuje datum prvog programiranja (format DD-MM-YY, npr. '01-01-24')."""
        if len(date) > 8:
            raise ValueError(f"Datum max 8 znakova DD-MM-YY (dobiveno: '{date}')")
        self._write_ascii(self.DATE_OFFSET_1, 8, date)

    def set_date_last_update(self, date: str) -> None:
        """Upisuje datum zadnjeg ažuriranja (format DD-MM-YY)."""
        if len(date) > 8:
            raise ValueError(f"Datum max 8 znakova DD-MM-YY (dobiveno: '{date}')")
        self._write_ascii(self.DATE_OFFSET_2, 8, date)

    def set_prog_count(self, count: int) -> None:
        """Upisuje broj programiranja (u8, 0–255)."""
        if not 0 <= count <= 255:
            raise ValueError(f"Broj programiranja mora biti 0–255 (dobiveno: {count})")
        self._data[self.PROG_CNT_OFF] = count

    def get_bytes(self) -> bytes:
        """Vraća modificirani EEPROM kao bytes."""
        return bytes(self._data)

    def save(self, path: str) -> None:
        """Sprema modificirani EEPROM na disk."""
        Path(path).write_bytes(self._data)

    def get_info(self) -> "EepromInfo":
        """Parsira trenutno stanje i vraća EepromInfo."""
        parser = EepromParser()
        return parser.parse_bytes(self.get_bytes(), source=self._path)
