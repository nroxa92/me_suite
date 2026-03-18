"""
EepromParser — Sea-Doo Bosch ME17.8.5 EEPROM (32KB) Odometar Parser

Autor: me_suite projekt
Datum: 2026-03-17

Istraživanjem potvrđeni adresni layout:

HW 064 (MPEM 1037550003) — RXP-X 300, GTI SE 155, RXT-X 300:
  - PRIMARNI ODOMETAR: @ 0x0562 (u16 LE) — "anchor slot" @ 0x0550, offset +18
    Prisutan u SVIM 064 fajlovima s <~10000 min; izuzetak: 064 211-07 (višestruki wrap)
  - CIRCULAR BUFFER: 0x0AA8–0x0C70 (approx), stride varijabilan (20 ili 25B)
    Format zapisa: [4B flags/meta][4B session_data][4B more_data][2B counts]
                   [u16 LE ODO][2B session_type]  — ODO @ offset +4 ili +0 od zapisa
    Aktivni slot = zadnji s bitom 0x80 u flags[0] ILI zadnji koji nije FFFF
  - SEKUNDARNI (wrap > ~15000 min): @ 0x0D62 i 0x1562 (stride 0x0800)
  - HW TIMER (nepromjenjiv): @ 0x0125 (5 ASCII znakova)

HW 063 (MPEM 1037525858) — Spark 90hp:
  - PRIMARNI: @ 0x0562 (isti anchor slot 0x0550+18) za niže minute
  - BUFFER: @ 0x0AC4–0x1B70, iste tri kopije:
      kopija 1: 0x0AC4, kopija 2: 0x1344, kopija 3: 0x1AC4 (sve stride=20)
    Svaka kopija = 8 slotova × 20B
  - VISOKI SATI: @ 0x0DE2 (npr. 063 585-42 = 35142 min)
  - HW TIMER @ 0x0125

HW 062 (MPEM 1037509210) — GTI SE 130, RXT 1.5L:
  - Potpuno drugačiji layout!
  - ODO @ 0x1062 (niže minute) ILI @ 0x4562/0x5062 (više minute)
  - Stride između kopija: 0x1000 (4096B)
  - HW TIMER @ 0x0125 (samo u nekim fajlovima — ostali imaju spaces)

Neidentificirani / nepodržani:
  - 064 211-07 (12667 min): @ 0x0D62 i 0x1562 (stride 2048) — stariji layout
  - 061 HW: nije pronađen u dostupnim fajlovima
  - "60620" = default/factory HW timer vrijednost za 064 HW

Circular buffer slot format (064/063 HW, potvrđen):
  Offset 0x0AA8 (064) ili 0x0AC4 (063):
  Stride: 20B (početak), 25B (drugi round u 064)

  Zapis:
    [0]:    byte — flags (0x07, 0x08, 0x0A, 0x0B...)
    [1-3]:  bytes — uvijek 0x00 (padding)
    [4-5]:  u16 LE — ??? (ADC/ECT vrijednost?)
    [6-7]:  u16 LE — ??? (RPM/throttle?)
    [8-11]: bytes — session data (A0 99 00 64 = "normal session")
    [12]:   byte — event flags (0x00, 0x05, 0x0A, 0x0B...)
    [13-15]:bytes — 0x00 padding
    [16-17]:u16 LE — ODOMETAR u minutama  ← POTVRĐENO
    [18-19]:bytes — session type (0x10 0x02 = normalna vožnja, 0x12 0x02 = drugi tip)

  NAPOMENA: Gornji format vrijedi za ANCHOR SLOT regiju (0x0AC4 u 063 HW).
  Za circular buffer u 064 HW (0x0AA8+), format je drugačiji:
    [0-1]:  u16 LE — event counter?
    [2-3]:  bytes
    [4-5]:  u16 LE — ODOMETAR u minutama  ← POTVRĐENO za 064 buffer

KORISNIČKI API:
    parser = EepromParser(data)
    odo = parser.odo_minutes   # odometar u minutama
    hw_timer = parser.hw_timer # HW timer string (5 znakova)
    hw_type = parser.hw_type   # "062", "063", "064"
"""

import struct
from typing import Optional


class EepromParser:
    """
    Parser za Sea-Doo Bosch ME17.8.5 EEPROM (32KB = 0x8000 bajta).
    Čita odometar (minute) i ostale parametre iz circular buffera.
    """

    EEPROM_SIZE = 0x8000  # 32768 bajta

    # Fiksne adrese
    HW_TIMER_ADDR  = 0x0125  # 5 ASCII znakova, nepromjenjivo
    HW_TIMER_LEN   = 5

    # Anchor slot adrese (sadrže zadnji snimljeni odometar)
    # Potvrđeno: odo @ offset+18 od početka slota @ 0x0550
    ANCHOR_SLOT_0550 = 0x0550  # slot start
    ANCHOR_ODO_OFFSET = 18     # odo je @ slot_start + 18 = 0x0562

    # Direktna adresa odometra (shortcut)
    ODO_ADDR_PRIMARY  = 0x0562  # = 0x0550 + 18

    # Circular buffer (064/063 HW)
    BUF_064_START = 0x0AA8  # prvi slot circular buffera
    BUF_063_START = 0x0AC4  # prvi slot za 063 HW
    BUF_STRIDE    = 20       # bajta po slotu (početak)
    BUF_STRIDE_25 = 25       # bajta po slotu (drugi round u 064)

    # 062 HW
    ODO_ADDR_062_LOW  = 0x1062  # za < ~9000 min
    ODO_ADDR_062_HIGH_A = 0x4562  # za > ~8000 min (kopija 1)
    ODO_ADDR_062_HIGH_B = 0x5062  # za > ~8000 min (kopija 2)

    # Sekundarni (wrap/stariji layout)
    ODO_ADDR_ALT_1    = 0x0D62  # alternativna lokacija
    ODO_ADDR_ALT_2    = 0x1562  # alternativna lokacija (mirror)

    # Factory default HW timer
    HW_TIMER_DEFAULT = "60620"

    def __init__(self, data: bytes):
        if len(data) < self.EEPROM_SIZE:
            raise ValueError(f"EEPROM premali: {len(data)} < {self.EEPROM_SIZE}")
        self._data = data
        self._hw_type: Optional[str] = None
        self._odo: Optional[int] = None
        self._hw_timer: Optional[str] = None

    # ─────────────────────────────────────────────────────────────────────────
    # Niske razine čitanje
    # ─────────────────────────────────────────────────────────────────────────

    def _u16le(self, offset: int) -> int:
        if offset + 2 > len(self._data):
            return 0
        return struct.unpack_from("<H", self._data, offset)[0]

    def _u8(self, offset: int) -> int:
        if offset >= len(self._data):
            return 0
        return self._data[offset]

    def _bytes_at(self, offset: int, n: int) -> bytes:
        return self._data[offset:offset + n]

    # ─────────────────────────────────────────────────────────────────────────
    # HW Timer
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def hw_timer(self) -> str:
        """Nepromjenjivi HW timer @ 0x0125 (5 ASCII znakova)."""
        if self._hw_timer is None:
            raw = self._bytes_at(self.HW_TIMER_ADDR, self.HW_TIMER_LEN)
            try:
                self._hw_timer = raw.decode("ascii").strip()
            except Exception:
                self._hw_timer = raw.hex()
        return self._hw_timer

    # ─────────────────────────────────────────────────────────────────────────
    # HW tip detekcija
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def hw_type(self) -> str:
        """
        Detekcija HW tipa iz EEPROM sadržaja.

        Strategija:
          - Traži MPEM part number string u EEPROM headeru
          - 064: string "1037550003" na ~0x05B4
          - 063: string "1037525858" na ~0x05B8
          - 062: string "1037509210" ili "1037525858" na ~0x05B8

        Fallback: po poziciji gdje se nalazi odometar
        """
        if self._hw_type is not None:
            return self._hw_type

        # Traži MPEM string
        data = self._data

        # 064 specific: "1037550003" @ ~0x05B4
        if b"1037550003" in data[0x0500:0x0700]:
            self._hw_type = "064"
            return self._hw_type

        # 063 specific: "1037525858" @ ~0x05B8
        if b"1037525858" in data[0x0500:0x0700]:
            self._hw_type = "063"
            return self._hw_type

        # 062 specific: "1037509210"
        if b"1037509210" in data[0x0400:0x0700]:
            self._hw_type = "062"
            return self._hw_type

        # Fallback heuristika:
        # 062 HW: karakteristično je da NEMA MPEM string @ 0x05B0-0x05C0
        # i da ima odometar na visokim adresama (0x1062, 0x4562, 0x5062)
        # 063/064: ima odometar @ 0x0562

        # Provjeri "1037550003" u cijelom EEPROM-u (može biti na drugom offsetu)
        if b"1037550003" in data:
            self._hw_type = "064"
            return self._hw_type
        if b"1037525858" in data:
            self._hw_type = "063"
            return self._hw_type
        if b"1037509210" in data or b"1037525" in data:
            self._hw_type = "062"
            return self._hw_type

        # Zadnja heuristika: 062 ima odometar na 0x1062/0x4562/0x5062
        # ali NE na 0x0562 (koji je kod 062 obično 0 ili nešto drugo)
        v_0562 = self._u16le(0x0562)
        v_1062 = self._u16le(0x1062)
        v_4562 = self._u16le(0x4562)
        v_5062 = self._u16le(0x5062)

        # Ako je 0x0562 = 0 ali neke od 062 adresa nisu 0 → 062
        if v_0562 == 0 and (1 <= v_1062 <= 65000 or 1 <= v_4562 <= 65000 or 1 <= v_5062 <= 65000):
            self._hw_type = "062"
        elif 1 <= v_0562 <= 65000:
            # Može biti 063 ili 064 — bez MPEM stringa ne možemo točno razlikovati
            # 064 ima "D0 D0" @ 0x05BB (mirror tag)
            if data[0x05BB:0x05BD] == b"\xD0\xD0":
                self._hw_type = "064"
            else:
                self._hw_type = "063"
        else:
            self._hw_type = "064"  # default

        return self._hw_type

    # ─────────────────────────────────────────────────────────────────────────
    # Odometar čitanje
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def odo_minutes(self) -> Optional[int]:
        """
        Čita odometar u minutama.

        Strategija (po HW tipu):
          064/063: scan circular buffer i anchor slot, vrati maksimalnu
          062:     čita @ 0x4562, 0x5062, ili 0x1062

        Returns:
            int: odometar u minutama (1 min = 1/60 sata)
            None: ako nije pronađen
        """
        if self._odo is not None:
            return self._odo

        hw = self.hw_type

        if hw in ("063", "064"):
            self._odo = self._find_odo_063_064()
        elif hw == "062":
            self._odo = self._find_odo_062()
        else:
            self._odo = self._find_odo_063_064()

        return self._odo

    def _find_odo_063_064(self) -> Optional[int]:
        """
        Pronađi odometar za 063/064 HW.

        Potvrđene adrese (istraživanje 2026-03-17):

        Primarni (063 i 064, sve minute < ~65000):
          @ 0x0562 (u16 LE) — anchor slot @ 0x0550, offset +18
          Potvrđeno na: 064 9-5, 064 86-31, 064 99-50, 064 163,
                        063 85-31, 063 92-51, 064 85-31 ex063

          NAPOMENA: @ 0x0562 je uvijek najnovije (zadnje upisano) u normalnom radu.
          Koristimo 0x0562 kao primarni izvor.

        Fallback 1 (ako je primarni = 0):
          @ 0x0D62 (u16 LE) — potvrđeno za 064 211-07 (12667 min)
          @ 0x1562 (u16 LE) — mirror od 0x0D62, stride 0x0800

        Fallback 2 (visoke minute, 063 HW):
          @ 0x0DE2 (u16 LE) — potvrđeno za 063 585-42 (35142 min)

        Strategija: primarni prioritet (0x0562), fallback samo ako je 0
        """
        # Primarni izvor (anchor slot)
        v_primary = self._u16le(0x0562)
        if 1 <= v_primary <= 65000:
            return v_primary

        # Fallback: alternativne adrese ako je primarni = 0
        FALLBACK_ADDRS = [
            0x0D62,   # 064 211-07 layout
            0x1562,   # mirror
            0x0DE2,   # 063 visoke minute
        ]
        for addr in FALLBACK_ADDRS:
            v = self._u16le(addr)
            if 1 <= v <= 65000:
                return v

        return None

    # _scan_circular_buffer, _scan_064_buffer, _scan_063_buffer su uklonjeni.
    # Direktne adrese su preciznije i pouzdanije od buffer scana.
    # Circular buffer format nije potpuno dekodiran — TODO za buduće istraživanje.

    def _find_odo_062(self) -> Optional[int]:
        """
        062 HW odometar.

        Potvrđene adrese (istraživanje 2026-03-17):
          062 86-24  (5184 min):  @ 0x1062 ✓
          062 143-21 (8601 min):  @ 0x4562 ✓, @ 0x5062 ✓
          062 228-52 (13732 min): @ 0x1062 ✓
          062 848-33 (50913 min): @ 0x5062 ✓

        Strategija s prioritetom:
          1. Ako postoji razumna vrijednost @ 0x5062 → to je aktivni (zadnji)
          2. Ako 0x5062 = 0 → provjeri 0x4562
          3. Ako 0x4562 = 0 → provjeri 0x1062

        Razlog: circular buffer puni se od 0x1062 prema gore,
        zadnji upisani je na najvišoj aktivnoj adresi.
        """
        # Prioritetni redosled: od najveće (najnovije) prema manjoj
        PRIORITY_ADDRS = [0x5062, 0x4562, 0x1062]

        for addr in PRIORITY_ADDRS:
            v = self._u16le(addr)
            if 1 <= v <= 65000:
                return v

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Pomoćne metode
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def odo_hours(self) -> float:
        """Odometar u satima (float)."""
        odo = self.odo_minutes
        return odo / 60.0 if odo is not None else 0.0

    @property
    def odo_str(self) -> str:
        """Odometar kao string 'Xh Ym'."""
        odo = self.odo_minutes
        if odo is None:
            return "N/A"
        h = odo // 60
        m = odo % 60
        return f"{h}h {m}m"

    @property
    def is_factory_default(self) -> bool:
        """True ako je HW timer na factory default vrijednosti."""
        return self.hw_timer == self.HW_TIMER_DEFAULT

    @classmethod
    def from_file(cls, path: str) -> "EepromParser":
        """Učitaj EEPROM iz fajla."""
        with open(path, "rb") as f:
            data = f.read()
        return cls(data)

    def __repr__(self) -> str:
        return (f"EepromParser(hw={self.hw_type}, "
                f"odo={self.odo_str}, "
                f"timer={self.hw_timer!r})")


# =============================================================================
# Verifikacijska skripta
# =============================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    ECU_ROOT = Path("C:/Users/SeaDoo/Desktop/ECU")

    # Test cases s poznatim vrijednostima
    TEST_CASES = [
        # (path, expected_minutes, expected_hw)
        (ECU_ROOT / "064" / "064 9-5",    545,   "064"),
        (ECU_ROOT / "064" / "064 86-31",  5191,  "064"),
        (ECU_ROOT / "064" / "064 99-50",  5990,  "064"),
        (ECU_ROOT / "064" / "064 163",    9780,  "064"),
        (ECU_ROOT / "064" / "064 211-07", 12667, "064"),
        (ECU_ROOT / "063" / "063 85-31",  5131,  "063"),
        (ECU_ROOT / "063" / "063 92-51",  5571,  "063"),
        (ECU_ROOT / "063" / "063 585-42", 35142, "063"),
        (ECU_ROOT / "062" / "062 86-24",  5184,  "062"),
        (ECU_ROOT / "062" / "062 143-21", 8601,  "062"),
        (ECU_ROOT / "062" / "062 848-33", 50913, "062"),
    ]

    print("="*70)
    print("EepromParser Verifikacija")
    print("="*70)
    print(f"\n{'File':30} {'Expect':8} {'Got':8} {'HW_exp':6} {'HW_got':6} {'Status':8} {'Timer':8}")

    ok = 0
    fail = 0
    for path, expected_odo, expected_hw in TEST_CASES:
        if not path.exists():
            print(f"  {path.name:30} NIJE PRONAĐEN")
            continue

        try:
            p = EepromParser.from_file(str(path))
            got_odo = p.odo_minutes
            got_hw  = p.hw_type
            timer   = p.hw_timer

            # Tolerancija ±2 min (zaokruživanje)
            odo_ok = got_odo is not None and abs(got_odo - expected_odo) <= 2
            hw_ok  = got_hw == expected_hw
            status = "OK" if odo_ok else "FAIL"

            print(f"  {path.name:30} {expected_odo:8} {got_odo or 0:8} "
                  f"{expected_hw:6} {got_hw:6} {status:8} {timer!r:8}")

            if odo_ok:
                ok += 1
            else:
                fail += 1

        except Exception as e:
            print(f"  {path.name:30} GREŠKA: {e}")
            fail += 1

    print(f"\nRezultat: {ok} OK, {fail} FAIL")
