"""
CAN payload decoder — BRP Sea-Doo ME17.8.5 ECU
Potvrđeno analizom binarnih fajlova + bench sniff + SDCANlogger sesija (2026-03)

=== DVA ODVOJENA CAN BUSA ===

  Diagnostic bus  (500 kbps, OBD konektor / IXXAT bench):
    IDs: 0x0102, 0x0103, 0x0110, 0x0122, 0x0300, 0x0308, 0x0316, 0x0320, 0x0342, 0x0516, 0x04CD
    XOR checksum na svim broadcast porukama: byte[7] = XOR(byte[0..6])
    Rolling counter: byte[6] = 0x00-0x0F (4-bit, inkrement svaki frejm)

  Cluster bus (250 kbps, Delphi 20-pin J1 pin2/3):
    ECU→SAT IDs: 0x0578 (267-300ms, svi modeli), 0x0400 (311-344ms, GTX/GTI)
                 0x0408 (267ms, prisutan u svim SW varijantama, nije samo GTS)
    SAT→ECU IDs: 0x0186-0x019B, 0x01CD (GTX/GTI), 0x04CD (DESS relay)
    ECU CAN TX table @ 0x03DF0C (2019-2021) / 0x03DF1E (2018):
      Počinje s 78 05 = LE16 0x0578 (cluster primary ID)
      ISPRAVKA: 0x0433BC je tablica perioda (LE16 ms vrijednosti), NE CAN IDs!

=== CHECKSUM PROTOKOL (potvrđeno sniffom + XOR verifikacijom) ===

  byte[7] = XOR(byte[0] ^ byte[1] ^ byte[2] ^ byte[3] ^ byte[4] ^ byte[5] ^ byte[6])
  byte[6] = rolling counter 0x00-0x0F (inkrementira svaki frejm, wrapa na 0 od 15)

=== CONFIRMED DECODE FORMULE (ECU binary + bench sniff 2026-03) ===

  0x0102:  bytes[1:3] u16 BE × 0.25 = RPM  |  byte[3]-40 = coolant °C  |  byte[4]=SW scalar
  0x0110:  byte[1]-40 = coolant °C  |  byte[2]-40 = IAT °C  |  byte[3]-40 = oil °C
  0x0342:  byte[0]=mux key — 0xDE→ECT, 0xAA→MAP hPa, 0xC1→MAT  (sdtpro potvrđeno)
  0x0316:  byte[3]*0.943-17.2 = EOT °C  (sdtpro potvrđeno)
  0x012C:  u32 BE bytes[0:4] / 3600 = engine hours
  0x017C:  byte[0] = DTC count  |  bytes[1:3]+bytes[4:6] = 2× DTC code u16 BE
"""

from __future__ import annotations
import struct


# ─── CAN ID tablice ───────────────────────────────────────────────────────────

# Diagnostic bus (500 kbps, bench sniff potvrđeno)
DIAG_RPM          = 0x0102   # RPM + coolant + SW scalar  @ 100 Hz
DIAG_DTC_STATUS   = 0x0103   # DTC + engine status        @ 100 Hz
DIAG_TEMP         = 0x0110   # Coolant + IAT + oil temps  @  50 Hz
DIAG_GTI_SC       = 0x0122   # GTI/SC specific            @  50 Hz (10SW053727)
DIAG_MISC_A       = 0x0300   # Misc broadcast A           @  50 Hz
DIAG_MISC_B       = 0x0308   # Misc broadcast B           @  50 Hz
DIAG_EOT          = 0x0316   # Engine oil temp MUX        @  50 Hz (10SW053727)
DIAG_MISC_C       = 0x0320   # Misc broadcast C           @  50 Hz
DIAG_MUX          = 0x0342   # ECT/MAP/MAT mux            @  50 Hz
DIAG_HW_ID        = 0x0516   # HW/Protocol identifier     (constant)
DIAG_DESS         = 0x04CD   # DESS relay / cluster hb    @   1 Hz

# Cluster bus (250 kbps, ECU CAN TX table @ 0x03DF0C)
# ECU→SAT (potvrđeno iz SAT watchdog tablice @ GTX 0x05280):
CAN_CLUSTER_PRI   = 0x0578   # ECU primarna poruka za SAT @ 267-300ms
CAN_CLUSTER_SEC   = 0x0400   # ECU sekundarna poruka      @ 311-344ms
CAN_CLUSTER_GTS   = 0x0408   # GTS/dodatna (svi SW)       @ 267ms
# SAT→ECU (potvrđeno iz SAT firmware init tablice):
CAN_SAT_HEARTBEAT = 0x0186   # Primarni SAT heartbeat     @ ~100ms
CAN_SAT_CRITICAL  = 0x01CD   # KRITIČNI heartbeat GTX/GTI @ ~50ms
CAN_SAT_DESS      = 0x04CD   # DESS relay                 @ ~1Hz
CAN_DTC           = 0x017C   # DTC / fault codes          (event)

# SW-specific scalars u byte[4] od DIAG_RPM (0x0102)
SW_SCALAR = {
    0x14: "10SW066726 (300hp 2020/2021)",
    0x0E: "10SW053727 (230hp 2020/2021)",
    0x12: "10SW053729 (130/170hp 2020/2021)",
}


# ─── Checksum utiliti ─────────────────────────────────────────────────────────

def validate_checksum(data: bytes) -> bool:
    """
    Provjeri BRP XOR checksum.
    byte[7] = XOR(byte[0..6])  — potvrđeno bench sniffom.
    """
    if len(data) < 8:
        return False
    xor = 0
    for b in data[:7]:
        xor ^= b
    return xor == data[7]


def extract_rolling_counter(data: bytes) -> int:
    """
    Izvuci rolling counter iz byte[6].
    Vrijednost 0x00-0x0F, inkrement svaki frejm.
    """
    if len(data) < 7:
        return -1
    return data[6] & 0x0F


def calc_checksum(data: bytes) -> int:
    """Izračunaj XOR checksum za prvih 7 bajta."""
    xor = 0
    for b in (data[:7] if len(data) >= 7 else data):
        xor ^= b
    return xor


# ─── Payload dekoderi ─────────────────────────────────────────────────────────

def _pad(payload: bytes, length: int = 8) -> bytes:
    if len(payload) >= length:
        return payload[:length]
    return payload + bytes(length - len(payload))


class CanDecoder:
    """
    Dekoder BRP Sea-Doo ME17.8.5 CAN payloada.
    Sve metode prihvaćaju bytes payload (DLC=8).
    Kraći payloadi se dopunjavaju nulama.
    """

    _TEMP_OFFSET   = 40     # raw - 40 = °C
    _RPM_SCALE     = 0.25   # raw × 0.25 = RPM
    _HOURS_DIV     = 3600   # raw seconds / 3600 = hours

    # ── Diagnostic bus 0x0102 — RPM + Coolant ─────────────────────────────────

    @staticmethod
    def decode_0102(payload: bytes) -> dict:
        """
        Diagnostic bus RPM broadcast (100 Hz).

        Layout:
          [0]   Status flags
          [1:3] RPM u16 BE × 0.25
          [3]   Coolant temp: raw - 40 = °C
          [4]   SW scalar (0x14=300hp, 0x0E=230hp, 0x12=130/170hp)
          [5]   Unknown
          [6]   Rolling counter 0x00-0x0F
          [7]   XOR checksum = XOR(byte[0..6])
        """
        p = _pad(payload)
        rpm_raw = (p[1] << 8) | p[2]
        return {
            "rpm":            round(rpm_raw * 0.25, 0),
            "coolant_c":      p[3] - 40,
            "sw_scalar":      f"0x{p[4]:02X}",
            "sw_hint":        SW_SCALAR.get(p[4], "nepoznat SW"),
            "status":         f"0x{p[0]:02X}",
            "rolling_ctr":    p[6] & 0x0F,
            "checksum_ok":    validate_checksum(p),
        }

    @staticmethod
    def decode_rpm(payload: bytes) -> int:
        """Brzi RPM iz 0x0102 ili 0x0108 payloada."""
        p = _pad(payload)
        return int(((p[1] << 8) | p[2]) * 0.25)

    # ── Diagnostic bus 0x0103 — DTC + Engine status ───────────────────────────

    @staticmethod
    def decode_0103(payload: bytes) -> dict:
        """
        Diagnostic bus DTC + status (100 Hz).

        Layout (djelomično poznat):
          [0]   DTC count (aktivnih gresaka)
          [1]   Engine run state: 0=off, 1=cranking, 2=running, 3=limp
          [2]   MIL / fault flags (bit0=MIL, bit1=service, bit2=limp)
          [3]   Unknown
          [4]   Unknown
          [5]   Unknown
          [6]   Rolling counter
          [7]   XOR checksum
        """
        p = _pad(payload)
        state_map = {0: "off", 1: "cranking", 2: "running", 3: "limp"}
        return {
            "dtc_count":    p[0] & 0x3F,
            "engine_state": state_map.get(p[1] & 0x03, f"0x{p[1]:02X}"),
            "mil_on":       bool(p[2] & 0x01),
            "service_due":  bool(p[2] & 0x02),
            "limp_mode":    bool(p[2] & 0x04),
            "rolling_ctr":  p[6] & 0x0F,
            "checksum_ok":  validate_checksum(p),
        }

    # ── Diagnostic/Cluster 0x0110 — Temperature ───────────────────────────────

    @staticmethod
    def decode_0110(payload: bytes) -> dict:
        """
        Temperature broadcast — isti ID na oba busa.

        Layout:
          [0]   Status flags
          [1]   Coolant temp: raw - 40 = °C
          [2]   IAT (intake air temp): raw - 40 = °C
          [3]   Oil temp: raw - 40 = °C (0xFF = senzor ne postoji)
          [4:6] Reserved
          [6]   Rolling counter
          [7]   XOR checksum
        """
        p = _pad(payload)
        oil = (p[3] - 40) if p[3] != 0xFF else None
        return {
            "coolant_c":    p[1] - 40,
            "iat_c":        p[2] - 40,
            "oil_c":        oil,
            "status":       f"0x{p[0]:02X}",
            "rolling_ctr":  p[6] & 0x0F,
            "checksum_ok":  validate_checksum(p),
        }

    @staticmethod
    def decode_coolant_temp(payload: bytes) -> float:
        p = _pad(payload)
        return float(p[1] - 40)

    @staticmethod
    def decode_iat(payload: bytes) -> float:
        p = _pad(payload)
        return float(p[2] - 40)

    # ── Diagnostic bus 0x0316 — Engine oil temp (MUX) ─────────────────────────

    @staticmethod
    def decode_0316(payload: bytes) -> dict:
        """
        EOT broadcast (sdtpro potvrđeno, 10SW053727 model-specific).

        Formula: byte[3] × 0.943 - 17.2 = °C
        """
        p = _pad(payload)
        eot = round(p[3] * 0.943 - 17.2, 1)
        return {
            "eot_c":        eot,
            "raw_byte3":    p[3],
            "rolling_ctr":  p[6] & 0x0F,
            "checksum_ok":  validate_checksum(p),
        }

    @staticmethod
    def decode_eot_316(payload: bytes) -> float:
        p = _pad(payload)
        return round(p[3] * 0.943 - 17.2, 1)

    # ── Diagnostic bus 0x0342 — MUX broadcast (ECT/MAP/MAT/TPS) ──────────────

    @staticmethod
    def decode_0342(payload: bytes) -> dict:
        """
        Multiplexed broadcast (sdtpro potvrđeno).

        MUX key u byte[0]:
          0xDE → ECT (coolant):  56.9 - 0.0002455 × u16BE(byte[2:4]) °C
          0xAA → MAP:            u16BE(byte[2:4]) × 0.41265 + 360.63  hPa
          0xC1 → MAT:            92.353 - 0.00113485 × u16BE(byte[4:6]) °C
          0x21 → Diagnostic/bench mode (ECU bez SAT)
          Ostalo → TPS/load Q16: u16BE(byte[2:4]) / 65536 × 100 = %

        Rolling counter + XOR checksum standardni.
        """
        p = _pad(payload)
        mux = p[0]
        val_23 = (p[2] << 8) | p[3]
        val_45 = (p[4] << 8) | p[5]

        result: dict = {
            "mux_key":      f"0x{mux:02X}",
            "rolling_ctr":  p[6] & 0x0F,
            "checksum_ok":  validate_checksum(p),
        }

        if mux == 0xDE:
            result["ect_c"]   = round(56.9 - 0.0002455 * val_23, 1)
        elif mux == 0xAA:
            result["map_hpa"] = round(val_23 * 0.41265 + 360.63, 1)
        elif mux == 0xC1:
            result["mat_c"]   = round(92.353 - 0.00113485 * val_45, 1)
        else:
            # TPS/load Q16 (bench potvrđeno: 0x9999 = 60.00%)
            result["load_pct"] = round(val_23 / 65536.0 * 100.0, 2)

        return result

    @staticmethod
    def decode_mux_342(payload: bytes) -> dict:
        """Alias za decode_0342 (kompatibilnost)."""
        return CanDecoder.decode_0342(payload)

    # ── Diagnostic bus 0x0516 — HW/Protocol identifier ────────────────────────

    @staticmethod
    def decode_0516(payload: bytes) -> dict:
        """
        HW/Protocol identifier (konstantan za isti HW).
        Nije SW-specifičan — mijenja se samo s promjenom hardwarea.

        Sadržaj je Bosch/BRP proprietary; korisno za identifikaciju HW varijante.
        """
        p = _pad(payload)
        return {
            "hw_id_hex":  p[:8].hex(' ').upper(),
            "hw_id_raw":  list(p[:8]),
        }

    # ── Diagnostic bus 0x04CD — DESS relay / Cluster heartbeat ───────────────

    @staticmethod
    def decode_04CD(payload: bytes) -> dict:
        """
        DESS transponder relay + cluster keepalive (1 Hz, 8 bytes).

        SAT čita iCODE transponder s DESS ključa i prosljeđuje podatke ECU-u.
        Alternira između dva frejmа (alive toggle):
          Frame A: 00 0B 03 04 20 02 01 21  (init/request)
          Frame B: F0 AA 00 2D 00 04 00 00  (0xAA = alive byte)

        Bez valjanog DESS odgovora ECU ne dozvoljava start.
        Ako je DESS disabled u ECU (BUDS2 opcija), ovaj ID možda nije potreban.

        IDR0=0x99, IDR1=0xA0 → CAN ID = (0x99 << 3) | (0xA0 >> 5) = 0x4CD
        """
        p = _pad(payload)
        frame_type = "B_alive" if p[1] == 0xAA else "A_request"
        return {
            "frame_type":  frame_type,
            "alive_byte":  f"0x{p[1]:02X}",
            "raw":         p[:8].hex(' ').upper(),
        }

    # ── Cluster bus 0x0108 — RPM (cluster protocol) ───────────────────────────

    @staticmethod
    def decode_0108(payload: bytes) -> dict:
        """
        RPM na cluster busu (250 kbps, ECU→SAT).

        Layout (iz ECU binary CAN TX table @ 0x0433BC):
          [0]   Status flags
          [1:3] RPM u16 BE × 0.25
          [3]   TPS % (1%/bit)
          [4]   MAP kPa
          [5]   Mode/gear
          [6:8] Reserved
        """
        p = _pad(payload)
        rpm_raw = (p[1] << 8) | p[2]
        return {
            "rpm":          int(rpm_raw * 0.25),
            "tps_pct":      round(p[3] * 100.0 / 255.0, 1),
            "map_kpa":      p[4],
            "status":       f"0x{p[0]:02X}",
        }

    # ── Cluster bus 0x012C — Engine hours ─────────────────────────────────────

    @staticmethod
    def decode_0012C(payload: bytes) -> dict:
        """
        Engine hours + service interval (cluster bus).

        Layout:
          [0:4] Engine runtime u32 BE (sekunde)
          [4:6] Service countdown u16 BE (0.1h/bit)
          [6:8] Reserved/flags
        """
        p = _pad(payload)
        seconds = struct.unpack_from(">I", p, 0)[0]
        service_raw = struct.unpack_from(">H", p, 4)[0]
        return {
            "engine_hours":           round(seconds / 3600.0, 2),
            "engine_seconds":         seconds,
            "service_hours_remain":   round(service_raw * 0.1, 1),
        }

    @staticmethod
    def decode_engine_hours(payload: bytes) -> float:
        p = _pad(payload)
        seconds = struct.unpack_from(">I", p, 0)[0]
        return round(seconds / 3600.0, 2)

    @staticmethod
    def decode_service_hours_remaining(payload: bytes) -> float:
        p = _pad(payload)
        raw = struct.unpack_from(">H", p, 4)[0]
        return round(raw * 0.1, 1)

    # ── Cluster bus 0x017C — DTC codes ────────────────────────────────────────

    @staticmethod
    def decode_017C(payload: bytes) -> dict:
        """
        DTC fault codes (cluster bus, event-driven).

        Layout:
          [0]   DTC count (lower nibble, max 2 per frame)
          [1:3] DTC code #1 u16 BE (BRP internal)
          [3]   Status byte DTC #1
          [4:6] DTC code #2 u16 BE
          [6]   Status byte DTC #2
          [7]   Frame counter
        """
        p = _pad(payload)
        count = min(p[0] & 0x0F, 2)
        codes = []
        for i in range(count):
            off = 1 + i * 3
            code = (p[off] << 8) | p[off + 1]
            if code:
                codes.append(f"P{code:04X}")
        return {
            "dtc_count":  p[0] & 0x0F,
            "dtc_codes":  codes,
            "frame_ctr":  p[7],
        }

    @staticmethod
    def decode_dtc(payload: bytes) -> list[int]:
        p = _pad(payload)
        count = min(p[0] & 0x0F, 2)
        codes = []
        for i in range(count):
            off = 1 + i * 3
            code = (p[off] << 8) | p[off + 1]
            if code:
                codes.append(code)
        return codes

    # ── Cluster bus 0x013C — Engine status flags ──────────────────────────────

    @staticmethod
    def decode_013C(payload: bytes) -> dict:
        """
        Engine status + riding mode flags.

        Layout:
          [0]   Engine run state: 0=off, 1=cranking, 2=running, 3=limp
          [1]   MIL: bit0=MIL, bit1=service due, bit2=limp mode
          [2]   Rev limit: bit0=soft cut, bit1=hard cut
          [3]   Mode: bit0=neutral, bit1=sport, bit2=eco, bit3=cruise
          [4:8] Extended (model-specific)
        """
        p = _pad(payload)
        state_map = {0: "off", 1: "cranking", 2: "running", 3: "limp"}
        return {
            "engine_state": state_map.get(p[0] & 0x03, f"0x{p[0]:02X}"),
            "mil_on":       bool(p[1] & 0x01),
            "service_due":  bool(p[1] & 0x02),
            "limp_mode":    bool(p[1] & 0x04),
            "rev_soft_cut": bool(p[2] & 0x01),
            "rev_hard_cut": bool(p[2] & 0x02),
            "neutral":      bool(p[3] & 0x01),
            "sport_mode":   bool(p[3] & 0x02),
            "eco_mode":     bool(p[3] & 0x04),
            "cruise_mode":  bool(p[3] & 0x08),
        }

    @staticmethod
    def decode_engine_status(payload: bytes) -> dict:
        return CanDecoder.decode_013C(payload)

    # ── Spark 900 HO specifično ───────────────────────────────────────────────

    @staticmethod
    def decode_spark_egt(payload: bytes) -> float:
        """EGT iz Spark 0x0103: byte[4] × 1.0125 - 60 = °C (sdtpro)."""
        p = _pad(payload)
        return round(p[4] * 1.0125 - 60, 1)

    @staticmethod
    def decode_spark_tps_103(payload: bytes) -> float:
        """TPS iz Spark 0x0103: (byte[6:8] u16 BE) × 0.04907 - 25.12 = %."""
        p = _pad(payload)
        raw = (p[6] << 8) | p[7]
        return round(raw * 0.04907 - 25.12, 1)

    @staticmethod
    def decode_spark_throttle_body(payload: bytes) -> float:
        """Throttle body iz Spark 0x0104: byte[0:2] / 100."""
        p = _pad(payload)
        return round(((p[0] << 8) | p[1]) / 100.0, 2)

    # ── Universalni dispatcher ────────────────────────────────────────────────

    @staticmethod
    def decode(can_id: int, payload: bytes) -> dict:
        """
        Dekodiraj bilo koji podržan CAN ID.

        Returns:
            dict s 'decoded': True ako je ID poznat, False inače.
            Uvijek uključuje 'can_id' i 'raw'.
            Za broadcast IDs sa checksumom uključuje 'rolling_ctr' i 'checksum_ok'.
        """
        p = _pad(payload)
        base = {
            "can_id": f"0x{can_id:04X}",
            "raw":    p.hex(' ').upper(),
        }

        dispatch = {
            DIAG_RPM:         CanDecoder.decode_0102,
            DIAG_DTC_STATUS:  CanDecoder.decode_0103,
            DIAG_TEMP:        CanDecoder.decode_0110,
            DIAG_EOT:         CanDecoder.decode_0316,
            DIAG_MUX:         CanDecoder.decode_0342,
            DIAG_HW_ID:       CanDecoder.decode_0516,
            DIAG_DESS:        CanDecoder.decode_04CD,
            CAN_RPM:          CanDecoder.decode_0108,
            CAN_ENGINE_HOURS: CanDecoder.decode_0012C,
            CAN_DTC:          CanDecoder.decode_017C,
            CAN_ENGINE_FLAGS: CanDecoder.decode_013C,
            # 0x0103 Spark variants
            0x0103: CanDecoder.decode_0103,
            0x0104: lambda pl: {
                "throttle_body": CanDecoder.decode_spark_throttle_body(pl),
            },
        }

        fn = dispatch.get(can_id)
        if fn:
            result = fn(p)
            return base | result | {"decoded": True}

        # Nepoznat ID — samo raw
        return base | {
            "decoded":      False,
            "rolling_ctr":  p[6] & 0x0F if len(p) >= 7 else -1,
            "checksum_ok":  validate_checksum(p),
        }


# ─── CAN TX timing tablice (iz ECU binary) ───────────────────────────────────

#: Cluster bus timing (ms) za GTI/SC 1630 (10SWxxxxxx)
GTI_SC_CAN_TIMING: dict[int, int] = {
    0x015B:  8,
    0x015C: 16,
    0x0148: 22,
    0x013C: 22,
    0x0138: 22,
    0x0108: 18,
    0x0214: 148,
    0x012C: 223,
    0x0110: 147,
    0x017C:   0,    # event-driven (DTC)
}

#: Cluster bus timing (ms) za Spark 900 HO (10SW011328 / 1037xxxxxx)
SPARK_CAN_TIMING: dict[int, int] = {
    0x015B:  8,
    0x0154: 16,
    0x0134: 20,
    0x013C: 20,
    0x015C: 20,
    0x0138: 20,
    0x0108: 16,
    0x0214: 132,
    0x012C: 196,
    0x0110: 131,
    0x017C:   0,
}

#: Diagnostic bus frekvencija (Hz) — bench sniff potvrđeno
DIAG_FREQ: dict[int, int] = {
    DIAG_RPM:        100,
    DIAG_DTC_STATUS: 100,
    DIAG_TEMP:        50,
    DIAG_GTI_SC:      50,
    DIAG_MISC_A:      50,
    DIAG_MISC_B:      50,
    DIAG_EOT:         50,
    DIAG_MISC_C:      50,
    DIAG_MUX:         50,
    DIAG_HW_ID:        0,   # sporadično
    DIAG_DESS:         1,
}


def get_timing(can_id: int, ecu_type: str = "gti300") -> int:
    """
    Vrati CAN TX period (ms) za cluster bus.

    Args:
        can_id:   CAN ID.
        ecu_type: 'spark' ili 'gti300' (default).

    Returns:
        Period ms, 0 = event-driven ili nepoznat.
    """
    table = SPARK_CAN_TIMING if ecu_type == "spark" else GTI_SC_CAN_TIMING
    return table.get(can_id, 0)


def get_diag_freq(can_id: int) -> int:
    """Vrati očekivanu frekvenciju (Hz) za diagnostic bus ID. 0 = sporadično."""
    return DIAG_FREQ.get(can_id, 0)


# ─── Riding mode dekoder ─────────────────────────────────────────────────────

RIDING_MODES: dict[int, str] = {
    0x01: "SPORT",
    0x02: "ECO",
    0x03: "CRUISE",
    0x06: "SKI",
    0x07: "SLOW SPEED",
    0x08: "DOCK",
    0x0F: "LIMP HOME",
    0x14: "KEY MODE",
}


def decode_riding_mode(mode_byte: int) -> str:
    """Dekodira riding mode byte iz CAN 0x0141 (ECU→SAT) ili 0x019B (SAT→ECU)."""
    return RIDING_MODES.get(mode_byte, f"UNKNOWN(0x{mode_byte:02X})")
