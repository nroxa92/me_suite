"""
CAN payload decoder for BRP Sea-Doo ME17.8.5 ECU.

Decoded from binary analysis of:
  - 300hp ECU flash (10SW066726) @ dumps/2021/1630ace/300.bin
  - Spark 90hp ECU flash (10SW053774) @ dumps/2021/900ace/spark90.bin

CAN bus parameters: 250 kbps, standard 11-bit frames, BRP proprietary protocol.

CAN TX table locations in ECU flash:
  - GTI/SC 1630:  0x0433BC (12 IDs, 0x0000 terminated)
  - Spark 900 HO: 0x042EC4 (12 IDs, 0x0000 terminated)

CAN TX timing (period ms) — from ECU binary table preceding CAN ID list:
  0x015B → 8ms   | 0x015C → 16ms  | 0x0148 → 22ms  | 0x013C → 22ms
  0x015C → 22ms  | 0x0138 → 22ms  | 0x0108 → 16-18ms | 0x0214 → 132-148ms
  0x012C → 196-223ms | 0x0110 → 131-147ms | 0x017C → (event-driven)
"""

from __future__ import annotations


# ─── CAN ID constants ─────────────────────────────────────────────────────────

CAN_RPM          = 0x0108   # Engine speed + TPS + MAP
CAN_TEMP         = 0x0110   # Coolant + IAT temperatures
CAN_ENGINE_HOURS = 0x012C   # Engine time / service info
CAN_THROTTLE     = 0x0138   # Throttle / speed status
CAN_ENGINE_FLAGS = 0x013C   # Engine status flags
CAN_MAIN_ECU     = 0x015B   # Main ECU broadcast A
CAN_SEC_ECU      = 0x015C   # Main ECU broadcast B
CAN_GTI_SC       = 0x0148   # GTI/SC 1630 specific
CAN_SPARK_A      = 0x0134   # Spark specific A
CAN_SPARK_B      = 0x0154   # Spark specific B
CAN_DTC          = 0x017C   # DTC / fault status
CAN_DIAG_EXT     = 0x0214   # Extended diagnostics


# ─── CAN Decoder ──────────────────────────────────────────────────────────────

class CanDecoder:
    """
    Decodes BRP Sea-Doo ME17 CAN payloads.

    All methods accept a `bytes` payload of exactly 8 bytes (DLC=8).
    Shorter payloads are zero-padded internally; longer payloads are truncated.

    Payload formats determined by binary analysis of ECU CODE region.
    """

    # Temperature offset: raw - 40 = °C  (range: -40..+215 °C)
    _TEMP_OFFSET: int = 40

    # RPM scaling: raw / 4 = RPM  (or RPM * 4 = raw)
    _RPM_SCALE: float = 0.25

    # Engine hours: raw seconds / 3600 = hours
    _SECONDS_PER_HOUR: int = 3600

    # Service interval default (hours)
    _SERVICE_INTERVAL_H: int = 100

    @staticmethod
    def _pad(payload: bytes, length: int = 8) -> bytes:
        """Zero-pad or truncate payload to exactly `length` bytes."""
        if len(payload) >= length:
            return payload[:length]
        return payload + bytes(length - len(payload))

    # ── 0x0108 — RPM ──────────────────────────────────────────────────────────

    @staticmethod
    def decode_rpm(payload: bytes) -> int:
        """
        Decode engine speed from CAN 0x0108.

        Payload layout (DLC=8):
          [0]   Status / engine state flags
          [1:3] Engine speed (u16 BE, 0.25 RPM/bit)  →  RPM = raw * 0.25
          [3]   TPS / throttle position (%, 1 %/bit)
          [4]   MAP (kPa, 1 kPa/bit)
          [5]   Mode / gear indicator
          [6:8] Reserved

        Returns: RPM as integer (0–16383).
        """
        p = CanDecoder._pad(payload)
        raw = (p[1] << 8) | p[2]
        return int(raw * CanDecoder._RPM_SCALE)

    @staticmethod
    def decode_throttle_from_rpm_msg(payload: bytes) -> float:
        """
        Decode TPS % from CAN 0x0108 payload byte[3].

        Returns: throttle position 0.0–100.0 %.
        """
        p = CanDecoder._pad(payload)
        return round(p[3] * 100.0 / 255.0, 1)

    @staticmethod
    def decode_map_from_rpm_msg(payload: bytes) -> int:
        """
        Decode manifold absolute pressure from CAN 0x0108 payload byte[4].

        Returns: MAP in kPa (0–255).
        """
        p = CanDecoder._pad(payload)
        return p[4]

    # ── 0x0110 — Temperature ──────────────────────────────────────────────────

    @staticmethod
    def decode_coolant_temp(payload: bytes) -> float:
        """
        Decode coolant temperature from CAN 0x0110.

        Payload layout (DLC=8):
          [0]   Sensor status flags
          [1]   Coolant temp (raw − 40 = °C,  range −40..+215 °C)
          [2]   IAT — intake air temp (raw − 40 = °C)
          [3]   Aux sensor / oil temp (raw − 40 = °C, 0xFF = not present)
          [4:8] Reserved

        Returns: coolant temperature in °C (float).
        """
        p = CanDecoder._pad(payload)
        return float(p[1] - CanDecoder._TEMP_OFFSET)

    @staticmethod
    def decode_iat(payload: bytes) -> float:
        """
        Decode intake air temperature from CAN 0x0110 payload byte[2].

        Returns: IAT in °C (float).
        """
        p = CanDecoder._pad(payload)
        return float(p[2] - CanDecoder._TEMP_OFFSET)

    # ── 0x012C — Engine hours ─────────────────────────────────────────────────

    @staticmethod
    def decode_engine_hours(payload: bytes) -> float:
        """
        Decode engine hours from CAN 0x012C.

        Payload layout (DLC=8):
          [0:4] Engine run time (u32 BE, seconds)  →  hours = seconds / 3600
          [4:6] Service interval countdown (u16 BE, hours remaining, 0.1 h/bit)
          [6:8] Reserved / flags

        Returns: total engine hours as float (e.g. 123.4 h).
        """
        p = CanDecoder._pad(payload)
        seconds = (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]
        return round(seconds / CanDecoder._SECONDS_PER_HOUR, 2)

    @staticmethod
    def decode_service_hours_remaining(payload: bytes) -> float:
        """
        Decode service interval hours remaining from CAN 0x012C payload [4:6].

        Returns: hours until next service (float, 0.1 h resolution).
        """
        p = CanDecoder._pad(payload)
        raw = (p[4] << 8) | p[5]
        return round(raw * 0.1, 1)

    # ── 0x017C — DTC ──────────────────────────────────────────────────────────

    @staticmethod
    def decode_dtc(payload: bytes) -> list[int]:
        """
        Decode DTC fault codes from CAN 0x017C.

        Payload layout (DLC=8) — BRP proprietary format:
          [0]   Number of active DTCs in this frame (0–3)
          [1:3] DTC code #1 (u16 BE, BRP internal code, 0x0000 = empty)
          [3]   Status byte for DTC #1 (confirmed/pending flags)
          [4:6] DTC code #2 (u16 BE)
          [6]   Status byte for DTC #2
          [7]   Sequence / frame counter

        Note: BRP DTC codes differ from SAE J2012 PIDs.
        Use core.dtc module to translate to SAE P-codes.

        Returns: list of active DTC codes (integers, up to 2 per frame).
        """
        p = CanDecoder._pad(payload)
        count = min(p[0] & 0x0F, 2)   # clamp to 2 codes per frame
        codes: list[int] = []
        for i in range(count):
            offset = 1 + i * 3
            code = (p[offset] << 8) | p[offset + 1]
            if code != 0x0000:
                codes.append(code)
        return codes

    # ── 0x013C — Engine status flags ─────────────────────────────────────────

    @staticmethod
    def decode_engine_status(payload: bytes) -> dict:
        """
        Decode engine status flags from CAN 0x013C.

        Payload layout (DLC=8):
          [0]   Engine run state: 0=off, 1=cranking, 2=running, 3=limp mode
          [1]   MIL / fault lamp: bit0=MIL on, bit1=service, bit2=limp
          [2]   Rev limit flags: bit0=soft cut active, bit1=hard cut active
          [3]   Launch / mode: bit0=neutral, bit1=sport mode, bit2=eco mode
          [4:8] Extended status (model-specific)

        Returns: dict with decoded fields.
        """
        p = CanDecoder._pad(payload)
        state_map = {0: "off", 1: "cranking", 2: "running", 3: "limp"}
        return {
            "state":        state_map.get(p[0] & 0x03, f"unknown({p[0]})"),
            "mil_on":       bool(p[1] & 0x01),
            "service_due":  bool(p[1] & 0x02),
            "limp_mode":    bool(p[1] & 0x04),
            "rev_soft_cut": bool(p[2] & 0x01),
            "rev_hard_cut": bool(p[2] & 0x02),
            "neutral":      bool(p[3] & 0x01),
            "sport_mode":   bool(p[3] & 0x02),
            "eco_mode":     bool(p[3] & 0x04),
        }

    # ── 0x0214 — Extended diagnostics ────────────────────────────────────────

    @staticmethod
    def decode_extended_diag(payload: bytes) -> dict:
        """
        Decode extended diagnostics from CAN 0x0214 (DLC=8).

        Content is Bosch ME17 / BRP proprietary. Format partially known:
          [0]   Diag request type / session
          [1:3] Response data (mode-dependent)
          [3:8] Extended data

        Returns: raw dict with hex strings for manual inspection.
        """
        p = CanDecoder._pad(payload)
        return {
            "session":  p[0],
            "data_hex": p[1:].hex(' '),
        }

    # ── Universal dispatcher ──────────────────────────────────────────────────

    @staticmethod
    def decode(can_id: int, payload: bytes) -> dict:
        """
        Decode any supported CAN message by ID.

        Returns a dict with all decoded fields.
        Unknown CAN IDs return {'can_id': hex_str, 'raw': hex_str, 'decoded': False}.

        Example:
            >>> CanDecoder.decode(0x0108, bytes([0x00, 0x6D, 0x60, 0x64, 0x65, 0x00, 0x00, 0x00]))
            {'can_id': '0x0108', 'rpm': 7000, 'throttle_pct': 39.2, 'map_kpa': 101, ...}
        """
        p = CanDecoder._pad(payload)
        base = {"can_id": f"0x{can_id:04X}"}

        if can_id == CAN_RPM:
            return base | {
                "rpm":          CanDecoder.decode_rpm(p),
                "throttle_pct": CanDecoder.decode_throttle_from_rpm_msg(p),
                "map_kpa":      CanDecoder.decode_map_from_rpm_msg(p),
                "status_byte":  p[0],
                "raw":          p.hex(' '),
                "decoded":      True,
            }

        if can_id == CAN_TEMP:
            return base | {
                "coolant_temp_c": CanDecoder.decode_coolant_temp(p),
                "iat_c":          CanDecoder.decode_iat(p),
                "status_byte":    p[0],
                "raw":            p.hex(' '),
                "decoded":        True,
            }

        if can_id == CAN_ENGINE_HOURS:
            return base | {
                "engine_hours":           CanDecoder.decode_engine_hours(p),
                "service_hours_remaining": CanDecoder.decode_service_hours_remaining(p),
                "raw":                    p.hex(' '),
                "decoded":                True,
            }

        if can_id == CAN_DTC:
            return base | {
                "dtc_count":   p[0] & 0x0F,
                "dtc_codes":   CanDecoder.decode_dtc(p),
                "raw":         p.hex(' '),
                "decoded":     True,
            }

        if can_id == CAN_ENGINE_FLAGS:
            return base | CanDecoder.decode_engine_status(p) | {
                "raw":     p.hex(' '),
                "decoded": True,
            }

        if can_id == CAN_DIAG_EXT:
            return base | CanDecoder.decode_extended_diag(p) | {
                "raw":     p.hex(' '),
                "decoded": True,
            }

        # Unknown or broadcast IDs — return raw
        return base | {
            "raw":     p.hex(' '),
            "decoded": False,
        }


# ─── CAN TX timing table (from ECU binary analysis) ───────────────────────────

#: CAN TX period in ms for GTI/SC 1630 ECU (SW: 10SWxxxxxx)
GTI_SC_CAN_TIMING: dict[int, int] = {
    0x015B: 8,
    0x015C: 16,
    0x0148: 22,
    0x013C: 22,
    0x0138: 22,
    0x0108: 18,
    0x0214: 148,
    0x012C: 223,
    0x0110: 147,
    0x017C: 0,     # event-driven (DTC), no fixed period
}

#: CAN TX period in ms for Spark 900 HO ECU (SW: 10SW011328 / 1037xxxxxx)
SPARK_CAN_TIMING: dict[int, int] = {
    0x015B: 8,
    0x0154: 16,
    0x0134: 20,
    0x013C: 20,
    0x015C: 20,
    0x0138: 20,
    0x0108: 16,
    0x0214: 132,
    0x012C: 196,
    0x0110: 131,
    0x017C: 0,     # event-driven
}


def get_timing(can_id: int, ecu_type: str = "gti300") -> int:
    """
    Return CAN TX period (ms) for given CAN ID and ECU type.

    Args:
        can_id:   CAN message ID.
        ecu_type: 'spark' or 'gti300' (default).

    Returns:
        Period in ms, or 0 if event-driven / unknown.
    """
    table = SPARK_CAN_TIMING if ecu_type == "spark" else GTI_SC_CAN_TIMING
    return table.get(can_id, 0)
