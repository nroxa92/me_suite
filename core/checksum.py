"""
ME17Suite — Checksum Engine
Bosch ME17.8.5 / TC1762

=== ALGORITAM PRONADEN (2026-03-14) ===

Algoritam: CRC32-HDLC (ISO-HDLC / zlib / "standard CRC32")
  Poly:    0xEDB88320 (reflected 0x04C11DB7)
  Init:    0xFFFFFFFF
  XorOut:  0xFFFFFFFF
  Regija:  0x0000-0x7EFF (0x7F00 bajta = BOOT region)
  Tip:     CLOSED-FORM -- CS @ 0x30 je UKLJUCEN u izracun (ne nulirati)
  Residua: 0x6E23044F (fiksna, verificirano na 4 razlicita ECU fajla)

  Verificirani fajlovi:
    ori_300     CS=0xE505BC0B  CRC(BOOT)=0x6E23044F OK
    stg2_300    CS=0x9FC76FAD  CRC(BOOT)=0x6E23044F OK
    rxtx_260    CS=0x53532E7D  CRC(BOOT)=0x6E23044F OK
    rxt_514362  CS=0xE5D7955F  CRC(BOOT)=0x6E23044F OK

  KLJUCNO: Promjena CODE mapa (0x10000-0x5FFFF) NE zahtijeva promjenu CS!
  CS se mijenja samo ako se mijenja BOOT region (0x0000-0x7EFF):
    - SW verzija (0x1C-0x23)
    - Sam CS (0x30-0x33)
    - RSA potpis (0x7E7C-0x7EFF, 132B) -- treba Bosch privatni kljuc

  Za novi CS (ako BOOT promjene ne ukljucuju RSA potpis):
    compute_new_cs() koristi meet-in-the-middle inverzni CRC.

=== ARHITEKTURA (potvrdjeno analizom) ===

  BOOT:   0x0000-0x7EFF (32 511 B)
    Header:     0x0000-0x003F
    CS @ 0x30:  4 bajta (BE u32), closed-form CRC32-HDLC
    BOOT kod:   0x0040-0x7E7B
    RSA potpis: 0x7E7C-0x7EFF (132 B, Bosch privatni kljuc)

  Gap:    0x7F00-0xFFFF
    0x7F00: DEADBEEF terminator
    0xFF00: TC1762 BROM startup kod

  CODE:   0x10000-0x5FFFF  (tuning mape)
  CAL:    0x60000-0x177FFF (TriCore bytekod -- READ-ONLY)
"""

from __future__ import annotations
import struct
from .engine import ME17Engine, BOOT_START, BOOT_END, CODE_START, CODE_END


# ─── CRC32-HDLC (ISO-HDLC / zlib standard) ────────────────────────────────────

_HDLC_POLY = 0xEDB88320
_HDLC_INIT = 0xFFFFFFFF
_HDLC_XOR  = 0xFFFFFFFF

# Pozicija CS u fajlu
CS_OFFSET = 0x30
CS_SIZE   = 4

# BOOT region za checksum
BOOT_CS_START = 0x0000
BOOT_CS_END   = 0x7F00   # ekskluzivno (0x0000-0x7EFF ukljucivo = 0x7F00 bajta)

# Ocekivana CRC residua (closed-form)
BOOT_CRC_RESIDUE = 0x6E23044F


def _build_hdlc_table() -> list[int]:
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (_HDLC_POLY if c & 1 else 0)
        t.append(c)
    return t


_HDLC_TABLE = _build_hdlc_table()


def crc32_hdlc(data: bytes, init: int = _HDLC_INIT, xorout: int = _HDLC_XOR) -> int:
    """CRC32-HDLC (standardni zlib CRC32). Poly=0xEDB88320, reflected."""
    c = init & 0xFFFFFFFF
    for b in data:
        c = (c >> 8) ^ _HDLC_TABLE[(c ^ b) & 0xFF]
    return (c ^ xorout) & 0xFFFFFFFF


def _crc_step_no_xor(state: int, b: int) -> int:
    """Jedan CRC32-HDLC korak bez finalnog XOR-a."""
    return (state >> 8) ^ _HDLC_TABLE[(state ^ b) & 0xFF]


def _crc_inverse_step(state_new: int, b: int) -> int:
    """
    Inverzni CRC32-HDLC korak.

    Za reflected CRC32: state_new = (state >> 8) ^ T[(state ^ b) & 0xFF]
    Inverzno: pronaci state takav da forward(state, b) = state_new.

    Matematika:
      Neka k = (state & 0xFF) ^ b (indeks tablice).
      state_new >> 24 = T[k] >> 24  (jer (state>>8) ima gornji bajt = 0)
      => k je odreden gornjim bajtom state_new.
      state = ((state_new ^ T[k]) << 8) | (k ^ b)
    """
    target_hi = state_new >> 24
    for k in range(256):
        if (_HDLC_TABLE[k] >> 24) == target_hi:
            state = (((state_new ^ _HDLC_TABLE[k]) << 8) & 0xFFFFFFFF) | (k ^ b)
            # Verifikacija
            if _crc_step_no_xor(state, b) == state_new:
                return state
    raise ValueError(f"Inverzni CRC: nema rjesenja za state_new=0x{state_new:08X}, b=0x{b:02X}")


def verify_boot_crc(data: bytes | bytearray) -> tuple[bool, int]:
    """
    Provjeri BOOT CRC (closed-form).

    Uzima 0x7F00 bajta od 0x0000, racuna CRC32-HDLC
    (CS @ 0x30 je UKLJUCEN, ne nulirati).
    Ispravan fajl daje residuu 0x6E23044F.

    Returns:
        (ok: bool, actual_crc: int)
    """
    region = bytes(data[BOOT_CS_START:BOOT_CS_END])
    crc = crc32_hdlc(region)
    return crc == BOOT_CRC_RESIDUE, crc


def read_stored_cs(data: bytes | bytearray) -> int:
    """Citaj pohranjeni CS @ 0x30 kao BE u32."""
    return struct.unpack_from(">I", data, CS_OFFSET)[0]


def compute_new_cs(data: bytes | bytearray) -> int:
    """
    Izracunaj ispravni CS za modificirani BOOT (bez promjene RSA potpisa).

    Princip closed-form CRC:
      CRC32-HDLC(head || X || tail) = RESIDUE
    gdje X = 4 bajta CS @ 0x30.

    Algoritam (meet-in-the-middle):
      1. Naprijed: CRC stanje nakon head [0x0000, 0x0030)
      2. Unatrag: invertirati CRC od RESIDUE kroz tail [0x0034, 0x7F00)
      3. Pronaci 4 bajta X koji premostuju state1 -> state2

    Note: Ako RSA potpis (0x7E7C-0x7EFF) ostaje nepromijenjen, X je
    jedinstven i ECU ce prihvatiti novi fajl.

    Returns:
        Novi CS (u32) koji treba pohraniti na 0x30 kao BE.
    """
    data = bytes(data)

    # Korak 1: CRC stanje (bez finalnog XOR) nakon head [0x0000, 0x0030)
    head = data[BOOT_CS_START:CS_OFFSET]
    state_after_head = _HDLC_INIT
    for b in head:
        state_after_head = _crc_step_no_xor(state_after_head, b)

    # Korak 2: Invertirati od ciljnog finalnog stanja kroz tail [0x0034, 0x7F00)
    # Ciljno finalno stanje: RESIDUE = final_state ^ XOR => final_state = RESIDUE ^ XOR
    target_state = BOOT_CRC_RESIDUE ^ _HDLC_XOR
    tail = data[CS_OFFSET + CS_SIZE:BOOT_CS_END]
    state_before_tail = target_state
    for b in reversed(tail):
        state_before_tail = _crc_inverse_step(state_before_tail, b)

    # Korak 3: Pronaci 4 bajta X takva da:
    #   forward(X, state_after_head) = state_before_tail
    # Meet-in-the-middle: 2 bajta naprijed + 2 bajta unatrag
    x_bytes = _solve_4bytes_mitm(state_after_head, state_before_tail)

    # x_bytes su bajtovi koji se "citaju" LE (jer je CRC reflected = LE byte order)
    # Pohranjuju se na 0x30 u memorijskom redoslijedu (= LE u fajlu = BE citanje)
    # Provjeri koji je format: spremi kao bajtove i provjeri verify_boot_crc
    return struct.unpack(">I", x_bytes)[0]


def _solve_4bytes_mitm(state_start: int, state_end: int) -> bytes:
    """
    Pronadi 4 bajta X takva da forward(X, state_start) = state_end.
    Koristi meet-in-the-middle: 2 bajta naprijed, 2 bajta unatrag.

    Returns: 4 bajta kao bytes objekt (u redoslijedu kakvom se zapisuju u fajl).
    """
    # Naprijed tablica: {state_after_2_bytes: (b0, b1)}
    fwd = {}
    for b0 in range(256):
        s1 = _crc_step_no_xor(state_start, b0)
        for b1 in range(256):
            s2 = _crc_step_no_xor(s1, b1)
            if s2 not in fwd:
                fwd[s2] = (b0, b1)

    # Unatrag: za svaki par (b3, b2), invertirati od state_end
    for b3 in range(256):
        s3 = _crc_inverse_step(state_end, b3)
        for b2 in range(256):
            s2_target = _crc_inverse_step(s3, b2)
            if s2_target in fwd:
                b0, b1 = fwd[s2_target]
                return bytes([b0, b1, b2, b3])

    raise ValueError("MITM: nema rjesenja za 4-bajtni CS!")


# ─── Legacy Bosch CRC (za referencu) ──────────────────────────────────────────

def crc32_bosch(data: bytes, init: int = 0xFFFFFFFF) -> int:
    """CRC32 s Bosch polynomom (big-endian bit order). Za referencu."""
    poly = 0x04C11DB7
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            crc = ((crc << 1) & 0xFFFFFFFF) ^ poly if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    crc = init
    for b in data:
        idx = ((crc >> 24) ^ b) & 0xFF
        crc = ((crc << 8) & 0xFFFFFFFF) ^ table[idx]
    return crc ^ 0xFFFFFFFF


# ─── ChecksumEngine ───────────────────────────────────────────────────────────

class ChecksumEngine:
    """
    Checksum verifikacija i korekcija za ME17.8.5 / TC1762.

    Algoritam (pronaden 2026-03-14):
      CRC32-HDLC, closed-form, BOOT region [0x0000, 0x7F00)
      Residua: 0x6E23044F

    VAZNO: Promjena CODE mapa NE zahtijeva promjenu checksuma!
    CS se mijenja samo ako se mijenja BOOT (SW verzija, kod, ili potpis).
    """

    def __init__(self, engine: ME17Engine):
        self.eng = engine

    def verify(self) -> dict:
        """Provjeri integritet fajla (CS + struktura)."""
        data = self.eng.get_bytes()
        results = {}

        ok, actual = verify_boot_crc(data)
        stored = read_stored_cs(data)
        results["boot_crc"] = {
            "stored":    f"0x{stored:08X}",
            "computed":  f"0x{actual:08X}",
            "residue":   f"0x{BOOT_CRC_RESIDUE:08X}",
            "status":    "OK" if ok else f"FAIL (got 0x{actual:08X})",
            "algorithm": "CRC32-HDLC closed-form, BOOT [0x0000-0x7EFF]",
        }

        sw = data[0x001A:0x0024].rstrip(b"\x00").decode("ascii", errors="replace")
        results["sw_id"] = {
            "value":  sw,
            "status": "OK" if (sw.startswith("10SW") or sw.startswith("10375")) else "WARN",
        }

        cal = data[0x060000:0x160000]
        non_zero = sum(1 for b in cal if b != 0)
        results["cal_integrity"] = {
            "non_zero_bytes": non_zero,
            "status": "OK" if non_zero > 10000 else "WARN -- CAL prazna?",
        }

        return results

    def needs_update(self) -> bool:
        data = self.eng.get_bytes()
        ok, _ = verify_boot_crc(data)
        return not ok

    def update_all(self) -> dict:
        """
        Azuriraj CS @ 0x30 ako je BOOT region promijenjen.

        Za CODE-only promjene: CS ostaje nepromijenjen (nije potrebno).
        Za BOOT promjene (SW verzija, kod): izracuna novi CS.
        RSA potpis (0x7E7C-0x7EFF) mora ostati nepromijenjen.
        """
        data = self.eng.get_bytes()
        ok, actual = verify_boot_crc(data)

        if ok:
            return {
                "status": "OK",
                "message": "Checksum je ispravan.",
                "crc": f"0x{actual:08X}",
            }

        try:
            new_cs = compute_new_cs(data)
            data_copy = bytearray(data)
            data_copy[CS_OFFSET:CS_OFFSET + CS_SIZE] = struct.pack(">I", new_cs)
            ok2, crc2 = verify_boot_crc(data_copy)

            if ok2:
                self.eng.write_bytes(CS_OFFSET, struct.pack(">I", new_cs))
                return {
                    "status": "UPDATED",
                    "old_cs": f"0x{read_stored_cs(data):08X}",
                    "new_cs": f"0x{new_cs:08X}",
                }
            else:
                return {
                    "status": "ERROR",
                    "message": f"Izracunati CS nije pravi: CRC=0x{crc2:08X}",
                    "computed_cs": f"0x{new_cs:08X}",
                }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
