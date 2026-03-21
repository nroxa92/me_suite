#!/usr/bin/env python3
"""
ME17Suite — ECU CAN Broadcast Simulator
Replikira Bosch ME17.8.5 CAN broadcast za Rotax ACE 1630 (Sea-Doo 300)
Bus: 500kbps, IXXAT USB-to-CAN

Broadcast ID-ovi (ECU → CAN bus):
  0x102  100Hz  RPM + Temp + Napon + Counter
  0x103  100Hz  DTC count + Status + Counter
  0x110   50Hz  System status + SW flags (XOR checksum)
  0x300   50Hz  Sve nule (keep-alive placeholder)
  0x308   50Hz  Sensor flags (engine state bitmap)
  0x316   50Hz  Temperatura/sensor data (MW053727 specifično)
  0x320   50Hz  Misc sensors (0xFE=N/A kada motor nije upaljen)
  0x342   50Hz  Varijabilni parametri (sensor readings)
  0x516   50Hz  HW/Protocol identifier (konstantan: 20 1C 81 2C 32 31 4A 42)

Heartbeat koji klaster šalje (0x4CD → ECU):
  Tip A: F0 AA 00 XX 00 00 00 00  (XX=napon×10 ili sensor)
  Tip B: 00 YY YY 04 ZZ 02 01 CS  (status/config frame)

Napomena: sniff_live.csv (066726) NEMA 0x4CD — klaster nije bio na busu!
          sniff_live2.csv (053727) IMA 0x4CD — klaster je bio na busu.
          0x4CD se alternira između Tip A i Tip B framova @ ~50Hz.
"""
import sys
import time
import struct
import threading
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False
    print("UPOZORENJE: python-can nije instaliran. Simulator radi u 'dry run' modu.")


def xor_bytes(data: bytes | list) -> int:
    """XOR svih bajtova."""
    r = 0
    for b in data:
        r ^= b
    return r


class ME17ECUSimulator:
    """
    Simulira ECU broadcast za Bosch ME17.8.5 / Rotax ACE 1630.

    Parametri:
        rpm     : float  — RPM motora (0 = ugašen)
        temp_c  : int    — temperatura rashladne tekućine (°C), min -40
        voltage : float  — napon napajanja (V)
        dtc_count: int   — broj aktivnih DTC kodova
        sw_066726: bool  — True = 10SW066726 (300hp 2021), False = 10SW053727 (230hp 2020)

    Checksum shema (verificirano iz logova):
        0x102 : byte[6] = counter 0..F; byte[7] = XOR(byte[0:6]) XOR byte[6]
                (ekvivalentno: byte[7] = XOR(byte[0:7]), tj. counter je DIO checksuma)
        0x103 : isti mehanizam — byte[6]=counter, byte[7]=XOR(0:7)
        0x110 : byte[6]=counter, byte[7]=XOR(byte[0:7])
        0x122 : byte[6]=counter, byte[7]=XOR(byte[0:7])
        Sve ostalo: nema CAN checksum (sadržaj je konstan ili sensor vrijednost)

    SW razlike (10SW066726 vs 10SW053727):
        0x102 byte[4]: 0x14(20) → 0x0E(14)  — sensor/napon scalar razlika
        0x103 byte[0]: uvijek 0x03 (066726) → 0 ili 2 (053727)
        0x110 byte[3]: 0x25 → 0x39  — system config flags
        0x110 byte[5]: 0x02 → 0x03  — bit 0 razlika
        0x308 byte[0]: 0x80 → 0x00; byte[1]: 0x02 → 0x12; byte[4]: 0x20 → 0x00
        0x316 : POSTOJI samo u 053727, nema u 066726!
        0x320 byte[1]: 0xFE → 0x00; byte[5]: 0xFE → 0x00; byte[6]: 0x80 → 0x82
        0x4CD : klaster heartbeat (samo u live2/053727 logu)
    """

    # Konstantni HW/Protocol identifier (isti za SVE SW verzije!)
    SW_IDENTIFIER = bytes([0x20, 0x1C, 0x81, 0x2C, 0x32, 0x31, 0x4A, 0x42])
    # ASCII: " ..,21JB" — vjerovatno HW revision + protocol version

    def __init__(
        self,
        rpm: float = 0.0,
        temp_c: int = -20,
        voltage: float = 12.5,
        dtc_count: int = 0,
        sw_066726: bool = True,
        channel: int = 0,
        bitrate: int = 500000,
        dry_run: bool = False
    ):
        self.rpm = rpm
        self.temp_c = temp_c
        self.voltage = voltage
        self.dtc_count = dtc_count
        self.sw_066726 = sw_066726
        self.channel = channel
        self.bitrate = bitrate
        self.dry_run = dry_run or not CAN_AVAILABLE

        # Counter za 100Hz poruke (0..15, inkrement svaki frame)
        self._counter_100hz = 0
        # Counter za 50Hz poruke (0..15)
        self._counter_50hz = 0

        self._bus: Optional[object] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Klaster heartbeat state
        self._cluster_tip_toggle = False  # alternira između Tip A i Tip B

    # ----------------------------------------------------------------
    # Bus inicijalizacija
    # ----------------------------------------------------------------
    def connect(self):
        if self.dry_run:
            print("[DRY RUN] Bus nije inicijaliziran.")
            return
        try:
            self._bus = can.interface.Bus(
                interface='ixxat',
                channel=self.channel,
                bitrate=self.bitrate,
                monitor=False  # TX mod (ne monitoring)
            )
            print(f"[CAN] Spojen na IXXAT channel={self.channel} @ {self.bitrate}bps")
        except Exception as e:
            print(f"[CAN] Greška pri spajanju: {e}")
            self._bus = None

    def disconnect(self):
        if self._bus:
            self._bus.shutdown()
            self._bus = None
            print("[CAN] Odspojeno.")

    # ----------------------------------------------------------------
    # Frame graditeljske metode
    # ----------------------------------------------------------------
    def _build_0x102(self) -> bytes:
        """
        RPM/Temp frame @ 100Hz.
        byte[0:2] = 0x00 0x00
        byte[1:3] = RPM u16BE / 0.25 (tj. RPM*4 u 16-bit)
        byte[3]   = Temp+40 (offset encoding, -40°C = 0)
        byte[4]   = napon scalar (SW-specifičan: 066726=0x14, 053727=0x0E)
                    0x14=20 → 20*0.625=12.5V; 0x0E=14 → 14*0.625=8.75V (ECU na stolu = ~5V bench?)
                    Napomena: oba snima su "ECU na stolu" bez punjaća, razlika SW-a
        byte[5]   = 0xCA=202 (konstanta, vjerojatno sensor ID ili status)
        byte[6]   = counter 0..F
        byte[7]   = XOR(byte[0:7])
        """
        rpm_raw = min(int(self.rpm / 0.25), 0xFFFF)
        temp_raw = max(0, min(255, self.temp_c + 40))

        # Napon scalar — SW specifičan
        if self.sw_066726:
            voltage_raw = 0x14  # 20 * 0.625 = 12.5V
        else:
            voltage_raw = 0x0E  # 14 * 0.625 = 8.75V
        # Ako korisnik želi pravi napon: voltage_raw = int(self.voltage / 0.625)

        b = [
            0x00,
            (rpm_raw >> 8) & 0xFF,
            rpm_raw & 0xFF,
            temp_raw,
            voltage_raw,
            0xCA,           # Konstantan status byte
            self._counter_100hz,
            0x00            # Checksum placeholder
        ]
        b[7] = xor_bytes(b[:7])
        return bytes(b)

    def _build_0x103(self) -> bytes:
        """
        DTC/Status frame @ 100Hz.
        byte[0]   = DTC count (raw) ili status flags
                    066726: uvijek 0x03 (3 DTC aktivna u sniff)
                    053727: 0x00 ili 0x02 (razlika!)
        byte[1:6] = 0x00 (rezervirano)
        byte[2]   = 053727 specifičan: 0x02 kad je aktivan
        byte[6]   = counter 0..F
        byte[7]   = XOR(byte[0:7])

        Napomena: byte[0]=3 u 066726 jer su 3 DTC aktivna na tom sniffu.
                  byte[0] = broj DTC kodova u memoriji.
        """
        if self.sw_066726:
            status_b2 = 0x00
            dtc_raw = self.dtc_count & 0xFF
        else:
            # 053727: byte[0]=0, byte[2]=0x02 (drugačija encoding)
            status_b2 = 0x02 if self.dtc_count > 0 else 0x00
            dtc_raw = 0x00  # DTC count ide negdje drugdje

        b = [
            dtc_raw if self.sw_066726 else 0x00,
            0x00,
            status_b2,
            0x00, 0x00, 0x00,
            self._counter_100hz,
            0x00
        ]
        b[7] = xor_bytes(b[:7])
        return bytes(b)

    def _build_0x110(self) -> bytes:
        """
        System status @ 50Hz.
        byte[0:3] = 0x00 0x00 0x00
        byte[3]   = System config (SW-specifičan!):
                    066726: 0x25 (0b00100101)
                    053727: 0x39 (0b00111001)
                    Razlika bita: 1,3,4 su drugačiji → vjerovatno engine/SC config bits
        byte[4]   = 0x01 (init done flag?)
        byte[5]   = protocol/mode:
                    066726: 0x02
                    053727: 0x03 (bit 0 razlika = možda SC aktivan?)
        byte[6]   = counter 0..F
        byte[7]   = XOR(byte[0:7])  ← POTVRĐENO checksuma!
        """
        sys_cfg = 0x25 if self.sw_066726 else 0x39
        mode = 0x02 if self.sw_066726 else 0x03

        b = [
            0x00, 0x00, 0x00,
            sys_cfg,
            0x01,
            mode,
            self._counter_50hz,
            0x00
        ]
        b[7] = xor_bytes(b[:7])
        return bytes(b)

    def _build_0x300(self) -> bytes:
        """Keep-alive / placeholder @ 50Hz. Uvijek sve nule."""
        return bytes(8)

    def _build_0x308(self) -> bytes:
        """
        Sensor/Engine state flags @ 50Hz.
        066726 (živ):  80 02 00 00 20 00 02 00
        053727 (flash): 00 12 00 00 00 00 02 00  (početak)
                        00 10 00 00 00 00 02 00  (alternira)
        buds2 (off):   80 00 00 00 00 00 02 00  (initial)
                       80 02 00 00 20 00 02 00  (normalan)

        Analiza:
          byte[0]: 0x80 = engine running flag? (bit 7)
                   0x00 u 053727 = engine nije u normalnom stanju (flash!)
          byte[1]: 0x02 = running normal; 0x10/0x12 = boot/flash mode
          byte[4]: 0x20 = load sensor reading? (normalan rad)
                   0x00 = nema opterećenja / boot mode
          byte[6]: 0x02 = uvijek konstanta (protocol ID?)
        """
        if self.sw_066726:
            b0 = 0x80
            b1 = 0x02
            b4 = 0x20
        else:
            b0 = 0x00
            b1 = 0x10
            b4 = 0x00
        return bytes([b0, b1, 0x00, 0x00, b4, 0x00, 0x02, 0x00])

    def _build_0x316(self) -> bytes:
        """
        Sensor data @ 50Hz. POSTOJI SAMO u 053727!
        066726 ga ne šalje.

        Format: 0B B8 01 00 XX 00 00 00
          byte[0:2] = 0x0BB8 = 3000 decimal
                      → 3000 * 0.25 = 750 RPM? NE, motor nije upaljen.
                      → 3000 može biti sensor kalibracijska vrijednost
          byte[2]   = 0x01
          byte[3]   = 0x00
          byte[4]   = varijabilno (0x19..0x85) — sensor reading (temp? pressure?)
                      0x19=25, 0x85=133 → možda °C (25°C ambient = 0x19)
          byte[5:8] = 0x00

        Dekodacija byte[4] = ambijentalna/ulazna temperatura:
          0x19=25, 0x20=32, 0x26=38, 0x2B=43, 0x85=133
          25°C je realna ambijentalna temperatura!
        """
        # byte[4] = ambijentalna temperatura (°C)
        temp_raw = max(0, min(0x85, int(self.temp_c)))
        return bytes([0x0B, 0xB8, 0x01, 0x00, temp_raw, 0x00, 0x00, 0x00])

    def _build_0x320(self) -> bytes:
        """
        Misc sensors @ 50Hz.
        066726: 00 FE 00 00 60 FE 80 00
        053727: 00 00 00 00 F0 00 82 00

        0xFE = "Not Available" / sensor N/A u SAE J1939 / ISO 11898
        066726 ima 2x 0xFE → dva sensora bez odgovora
        053727 nema 0xFE → senzori "dostupni" ali s drugačijim vrijednostima

        byte[1]: 0xFE (N/A) u 066726, 0x00 u 053727
        byte[4]: 0x60=96 (066726), 0xF0=240 ili 0xD0 (053727)
                 Possible: throttle position (0x60=37.5%, 0xF0=94%)
                 ili sensor voltage raw (0x60/255*5V=1.18V)
        byte[5]: 0xFE (N/A) u 066726, 0x00 u 053727
        byte[6]: 0x80 u 066726, 0x82 u 053727 (bit 1 razlika)
        """
        if self.sw_066726:
            b1 = 0xFE
            b4 = 0x60
            b5 = 0xFE
            b6 = 0x80
        else:
            b1 = 0x00
            b4 = 0xF0
            b5 = 0x00
            b6 = 0x82
        return bytes([0x00, b1, 0x00, 0x00, b4, b5, b6, 0x00])

    def _build_0x342(self) -> bytes:
        """
        Varijabilni parametri @ 50Hz.
        byte[0:2] = 0x00 0x00
        byte[2:4] = u16BE sensor reading (varijabilno, poseban encoding)
        byte[4]   = 0x78 = 120 (UVIJEK konstanta u oba SW!)
        byte[5:8] = 0x00

        0x342 byte[2:4] vrijednosti:
          0x0107 = 263  → IDLE/low load
          0x1619 = 5657 → normalan rad
          0x2620 = 9760 → viši load
          0x9999 = 39321 → 39321/65535 = 60.00% TOČNO (Q16 percentage!)
          0xC129 = 49449 → 49449/65535 = 75.44%
          0x99AA = 60.03%

        Zaključak: byte[2:4] je UNSIGNED Q16 percentage (0..65535 = 0..100%)
        Možda: TPS (throttle position sensor) u Q16?
          Motor ugašen/idle → ~0.4% (0x0107)
          Normalan rad     → ~8-15% (0x1619, 0x2620)
          Pun gas          → 60-75% (0x9999, 0xC129)

        byte[4]=0x78=120 → neidentificirano, uvijek konstanta
        """
        # Throttle position 0..100% enkodiran kao Q16 (0..65535)
        # Koristimo RPM kao proxy za throttle (gruba aproksimacija)
        throttle_pct = min(100.0, max(0.0, self.rpm / 80.0))  # 0..8000 RPM → 0..100%
        tps_q16 = int(throttle_pct / 100.0 * 65535)
        b2 = (tps_q16 >> 8) & 0xFF
        b3 = tps_q16 & 0xFF
        return bytes([0x00, 0x00, b2, b3, 0x78, 0x00, 0x00, 0x00])

    def _build_0x516(self) -> bytes:
        """
        HW/Protocol identifier @ 50Hz.
        IDENTIČAN za sve SW verzije (066726, 053727, buds2)!
        → Nije SW identifier, nego HW ili protocol version identifier.
        0x20 0x1C 0x81 0x2C 0x32 0x31 0x4A 0x42
        ASCII: " ..,21JB"
        """
        return self.SW_IDENTIFIER

    def _build_0x122(self) -> bytes:
        """
        SAMO u 053727 (230hp 2020).
        Format: 39 18 00 XX 0B 5E CC CS
          byte[0] = 0x39 = 57 — SW config (isti kao 0x110 byte[3] za 053727!)
          byte[1] = 0x18 = 24
          byte[2] = 0x00
          byte[3] = varijabilno (0x00 ili 0xD3=211) — status/error flag?
                    0x00 = inicijalizacija, 0xD3 = normalan rad
          byte[4] = 0x0B = 11
          byte[5] = 0x5E = 94
          byte[6] = counter 0..F (100Hz)
          byte[7] = XOR(byte[0:7]) ← POTVRĐENO!

        Napomena: byte[0]=0x39 = 0x110 byte[3] u 053727 — sigurno SW-config byte!
        """
        status = 0xD3 if self.rpm > 0 or True else 0x00  # 0xD3 = normalan rad
        b = [
            0x39,    # SW config byte (053727-specific)
            0x18,
            0x00,
            status,
            0x0B,
            0x5E,
            self._counter_100hz,
            0x00
        ]
        b[7] = xor_bytes(b[:7])
        return bytes(b)

    # ----------------------------------------------------------------
    # Klaster heartbeat (0x4CD) — SAT/Dashboard → ECU
    # ----------------------------------------------------------------
    def build_cluster_heartbeat(self) -> bytes:
        """
        Klaster (dashboard) šalje 0x4CD @ ~50Hz (alternira između 2 tipa).

        Tip A: F0 AA 00 XX 00 00 00 00
          byte[0] = 0xF0 — tip marker
          byte[1] = 0xAA ili 0xBB — klaster status
                    0xAA = normalan, 0xBB = možda upozorenje/alarm
          byte[3] = 0x2C(44) ili 0x29(41) — napon/parametar
                    44 * 0.1 = 4.4V? (interni supply) ili 44 = signal

        Tip B: 00 YY YY 04 ZZ 02 01 CS
          byte[0] = 0x00 — tip marker
          byte[1] = byte[2] = 0x03 ili 0x02 (config pair)
          byte[3] = 0x04 (konstanta)
          byte[4] = 0x20 ili 0x02 — status flags
                    0x20 = normalan, 0x02 = degradiran?
          byte[5] = 0x02, byte[6] = 0x01 (konstante)
          byte[7] = checksum

        KRITIČNO ZA KLASTER SRETNOST:
          ECU sa sniff_live2 prima 0x4CD redovito.
          Bez 0x4CD, ECU možda prijavi DTC ili uđe u limp mode.
          Ali: sniff_live (066726) NEMA 0x4CD i ECU radi normalno!
          → 0x4CD je klaster → CAN, NE heartbeat koji ECU čeka.
          → Klaster prikazuje podatke, ECU ih ne treba za rad.
          → 0x4CD je vjerovatno klaster koji REAGIRA na ECU broadcast
            (pita za status ili šalje display heartbeat za SAT).

        Za simulaciju ECU bez klastera: 0x4CD NIJE potreban.
        """
        self._cluster_tip_toggle = not self._cluster_tip_toggle

        if self._cluster_tip_toggle:
            # Tip A
            volt_raw = int(self.voltage * 10)  # npr. 12.5V → 125, ali vidimo 44 i 41
            # Ispravak: 0x2C=44, 0x29=41 — možda temperatura ili signal koji KLASTER šalje ECU-u
            # Ne znamo pravi encoding; koristimo 0x2C kao default (normalan rad)
            status = 0xAA  # normalan
            param = 0x2C   # default parameter
            return bytes([0xF0, status, 0x00, param, 0x00, 0x00, 0x00, 0x00])
        else:
            # Tip B
            config = 0x03  # normalan status
            flags = 0x20   # normalan flags
            payload = [0x00, config, config, 0x04, flags, 0x02, 0x01, 0x00]
            # Checksum: ne XOR (ne odgovara). Možda counter ili slobodan?
            # 0x18 za {03,03,04,20,02,01}, 0x19 za {02,02,04,02,02,01}
            # ADD(1:7) = 3+3+4+32+2+1 = 45 = 0x2D? nope (0x18=24)
            # XOR(1:7) = 3^3^4^32^2^1 = 27 = 0x1B? nope (0x18=24)
            # Hipoteza: byte[7] = running counter (mijenja se s klastera interne stanje)
            # Za simulaciju: hardcode 0x18
            payload[7] = 0x18
            return bytes(payload)

    # ----------------------------------------------------------------
    # Slanje
    # ----------------------------------------------------------------
    def _send(self, can_id: int, data: bytes):
        if self.dry_run or self._bus is None:
            return
        msg = can.Message(
            arbitration_id=can_id,
            data=data,
            is_extended_id=False
        )
        try:
            self._bus.send(msg)
        except Exception as e:
            pass  # Ignoriraj greške slanja u produkci

    def _send_verbose(self, can_id: int, data: bytes, label: str = ""):
        """Verbose verzija za debug/dry run."""
        hex_data = ' '.join(f'{b:02X}' for b in data)
        print(f"  TX 0x{can_id:03X} [{label}]: {hex_data}")

    # ----------------------------------------------------------------
    # Broadcast cycle
    # ----------------------------------------------------------------
    def broadcast_cycle_100hz(self):
        """Šalje 100Hz poruke (0x102, 0x103). Pozivati svakih 10ms."""
        data_102 = self._build_0x102()
        data_103 = self._build_0x103()

        self._send(0x102, data_102)
        self._send(0x103, data_103)

        if not self.sw_066726:
            data_122 = self._build_0x122()
            self._send(0x122, data_122)

        # Inkrementiraj counter (0..15)
        self._counter_100hz = (self._counter_100hz + 1) & 0x0F

    def broadcast_cycle_50hz(self):
        """Šalje 50Hz poruke. Pozivati svakih 20ms."""
        self._send(0x110, self._build_0x110())
        self._send(0x300, self._build_0x300())
        self._send(0x308, self._build_0x308())
        self._send(0x320, self._build_0x320())
        self._send(0x342, self._build_0x342())
        self._send(0x516, self._build_0x516())

        if not self.sw_066726:
            self._send(0x316, self._build_0x316())

        self._counter_50hz = (self._counter_50hz + 1) & 0x0F

    def send_cluster_heartbeat(self):
        """Šalje klaster heartbeat (0x4CD) — koristiti ako se simulira i klaster."""
        data = self.build_cluster_heartbeat()
        self._send(0x4CD, data)

    # ----------------------------------------------------------------
    # Kontinuirani broadcast (thread)
    # ----------------------------------------------------------------
    def _run_loop(self):
        """Glavni broadcast loop. Radi u pozadinskom threadu."""
        interval_100hz = 0.010  # 10ms
        interval_50hz  = 0.020  # 20ms

        last_50hz = time.monotonic()
        last_100hz = time.monotonic()

        while self._running:
            now = time.monotonic()

            if now - last_100hz >= interval_100hz:
                self.broadcast_cycle_100hz()
                last_100hz = now

            if now - last_50hz >= interval_50hz:
                self.broadcast_cycle_50hz()
                last_50hz = now

            # Sleep da ne bude busy loop
            time.sleep(0.001)

    def start(self):
        """Pokreće broadcast u pozadinskom threadu."""
        if not self.dry_run:
            self.connect()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Simulator] Broadcast pokrenut.")

    def stop(self):
        """Zaustavlja broadcast."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.disconnect()
        print("[Simulator] Broadcast zaustavljen.")

    # ----------------------------------------------------------------
    # Verbose demo (dry run)
    # ----------------------------------------------------------------
    def demo_print(self, cycles: int = 3):
        """Ispiši primjer broadcast ciklusa bez stvarnog slanja."""
        print(f"\n{'='*60}")
        print(f"ECU Simulator Demo — {'066726 (300hp 2021)' if self.sw_066726 else '053727 (230hp 2020)'}")
        print(f"RPM={self.rpm:.0f}, Temp={self.temp_c}°C, V={self.voltage:.1f}V, DTC={self.dtc_count}")
        print(f"{'='*60}")

        for cycle in range(cycles):
            print(f"\n--- Ciklus {cycle+1} (t={cycle*10}ms) ---")
            print("100Hz poruke:")
            self._send_verbose(0x102, self._build_0x102(), "RPM/Temp")
            self._send_verbose(0x103, self._build_0x103(), "DTC/Status")
            if not self.sw_066726:
                self._send_verbose(0x122, self._build_0x122(), "SW053-extra")

            if cycle % 2 == 0:
                print("50Hz poruke (svaki 2. 100Hz ciklus):")
                self._send_verbose(0x110, self._build_0x110(), "System status")
                self._send_verbose(0x300, self._build_0x300(), "Keep-alive")
                self._send_verbose(0x308, self._build_0x308(), "Sensor flags")
                self._send_verbose(0x320, self._build_0x320(), "Misc sensors")
                self._send_verbose(0x342, self._build_0x342(), "Var params")
                self._send_verbose(0x516, self._build_0x516(), "HW/Protocol ID")
                if not self.sw_066726:
                    self._send_verbose(0x316, self._build_0x316(), "Temp sensor")

            self._counter_100hz = (self._counter_100hz + 1) & 0x0F
            if cycle % 2 == 0:
                self._counter_50hz = (self._counter_50hz + 1) & 0x0F

        print(f"\n--- Klaster heartbeat (0x4CD) ---")
        self._send_verbose(0x4CD, self.build_cluster_heartbeat(), "Cluster Tip A")
        self._send_verbose(0x4CD, self.build_cluster_heartbeat(), "Cluster Tip B")


# ----------------------------------------------------------------
# CLI / Demo
# ----------------------------------------------------------------
if __name__ == '__main__':
    print("ME17Suite — ECU Simulator Demo")
    print("="*60)

    # Demo 1: 300hp 2021 (10SW066726), ECU na stolu, motor ugašen
    print("\n[SCENARIO 1] 10SW066726 (300hp 2021) — ECU na stolu, motor OFF")
    sim1 = ME17ECUSimulator(
        rpm=32,        # "32 RPM" = ECU idle, motor nije startao
        temp_c=-20,    # -20°C = hladna radna temperatura
        voltage=12.5,
        dtc_count=3,   # 3 DTC (kao u sniff_live)
        sw_066726=True,
        dry_run=True
    )
    sim1.demo_print(cycles=4)

    # Demo 2: 230hp 2020 (10SW053727), motor ugašen, klaster aktivan
    print("\n\n[SCENARIO 2] 10SW053727 (230hp 2020) — motor OFF, klaster aktivan")
    sim2 = ME17ECUSimulator(
        rpm=32,
        temp_c=-20,
        voltage=12.5,
        dtc_count=0,
        sw_066726=False,
        dry_run=True
    )
    sim2.demo_print(cycles=4)

    print("\n\n" + "="*60)
    print("SUMMARY — CAN Broadcast Format")
    print("="*60)
    print("""
ID     Hz  Format (SW066726 primjer)
------ --- --------------------------------------------------
0x102  100 00 00 [RPM_HI] [RPM_LO] [TEMP+40] [V_RAW] [CA] [CNT] [XOR]
             RPM = byte[1:3]*0.25, Temp = byte[3]-40°C
0x103  100 [DTC] 00 00 00 00 00 [CNT] [XOR]
             DTC count u byte[0]
0x110   50 00 00 00 [SYS_CFG] 01 [MODE] [CNT] [XOR]
             SYS_CFG: 0x25=066726, 0x39=053727
0x300   50 00 00 00 00 00 00 00 00  (keep-alive)
0x308   50 [ENG] [STATE] 00 00 [LOAD] 00 02 00
             066726: 80 02 00 00 20 00 02 00
0x316   50 0B B8 01 00 [AMB_TEMP] 00 00 00  (053727 only!)
0x320   50 00 [SEN1] 00 00 [TPS] [SEN2] [CFG] 00
             0xFE = sensor N/A
0x342   50 00 00 [TPS_HI] [TPS_LO] 78 00 00 00
             TPS Q16: 0x9999=60%, 0x0107=0.4%
0x516   50 20 1C 81 2C 32 31 4A 42  (HW/Protocol ID, KONSTANTAN!)
0x122  100 39 18 00 [STATUS] 0B 5E [CNT] [XOR]  (053727 only!)

KLASTER → ECU (0x4CD @ 50Hz, alternira 2 tipa):
  Tip A: F0 [AA/BB] 00 [PARAM] 00 00 00 00
  Tip B: 00 [CFG] [CFG] 04 [FLAGS] 02 01 [CS]
  → ECU ne treba 0x4CD za rad (066726 radi bez njega)

CHECKSUM FORMULA (svi frami koji imaju CS):
  byte[6] = counter (0..15, inkrementira se svaki frame)
  byte[7] = XOR(byte[0], byte[1], ..., byte[6])
  Tj. XOR svih 8 bajtova = 0x00 (self-consistent)
""")
