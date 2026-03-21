#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ME17Suite — CAN Log Analysis
Analizira sve sniff_*.csv fajlove i generira kompletni izvještaj.
"""

import csv
import sys
import os
import re
from collections import defaultdict, Counter, OrderedDict

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

BASE = r"C:\Users\SeaDoo\Desktop\me_suite\tools"

FILES = {
    "sniff_buds2.csv":    "Prva kratka sesija — identifikacija ID-ova",
    "sniff_live.csv":     "EEPROM operacije (VIN, motor, DESS, ...)",
    "sniff_live2.csv":    "Firmware flash kompletna sekvenca",
    "sniff_cdid.csv":     "CDID promjene (model year, usage, version series)",
    "sniff_livedata.csv": "Live data reading — prva serija 24 parametra",
    "sniff_maps24.csv":   "Live data reading — druga serija 24 parametra",
}

# ─────────────────────────────────────────────────────────────────────────────
# UDS/KWP Service names
# ─────────────────────────────────────────────────────────────────────────────
UDS_SERVICES = {
    0x10: "DiagnosticSessionControl",
    0x11: "EcuReset",
    0x14: "ClearDiagnosticInfo",
    0x19: "ReadDTCInformation",
    0x1A: "KWP_ReadECUIdent",
    0x20: "ReturnToNormalMode (KWP)",
    0x21: "KWP_ReadDataByLocalId",
    0x22: "ReadDataByIdentifier",
    0x23: "ReadMemoryByAddress",
    0x27: "SecurityAccess",
    0x28: "CommunicationControl",
    0x2C: "DynamicallyDefineDataId",
    0x2E: "WriteDataByIdentifier",
    0x2F: "InputOutputControl",
    0x31: "RoutineControl",
    0x34: "RequestDownload",
    0x35: "RequestUpload",
    0x36: "TransferData",
    0x37: "RequestTransferExit",
    0x38: "RequestFileTransfer",
    0x3B: "KWP_WriteDataByLocalId",
    0x3D: "WriteMemoryByAddress",
    0x3E: "TesterPresent",
    0x85: "ControlDTCSetting",
    0x86: "ResponseOnEvent",
    0x87: "LinkControl",
}

SESSION_TYPES = {0x01: "Default", 0x02: "Programming", 0x03: "Extended"}
ROUTINE_IDS = {
    0x0202: "CheckProgrammingDependencies",
    0x0203: "EraseMemory",
    0x0206: "CheckMemoryIntegrity",
    0xFF00: "EraseFlash",
    0xFF01: "CheckSum",
    0x0205: "BackgroundInit",
    0x0201: "StartSoftware",
    0x0101: "EraseDependencies",
}

# ─────────────────────────────────────────────────────────────────────────────
# ISO 15765-2 CAN-TP reassembler
# ─────────────────────────────────────────────────────────────────────────────
class CANTP:
    """Simple ISO 15765-2 reassembler (single channel)."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.buf = bytearray()
        self.expected = 0
        self.sn = 0
        self.active = False

    def feed(self, data_bytes):
        """Feed a CAN frame, returns (complete_payload, frame_type) or (None, type)."""
        if not data_bytes:
            return None, "empty"

        b0 = data_bytes[0]
        frame_type = (b0 >> 4) & 0xF

        if frame_type == 0:  # Single Frame
            length = b0 & 0x0F
            if length == 0 and len(data_bytes) > 1:
                # Extended SF (CAN FD style)
                length = data_bytes[1]
                payload = bytes(data_bytes[2:2+length])
            else:
                payload = bytes(data_bytes[1:1+length])
            self.reset()
            return payload, "SF"

        elif frame_type == 1:  # First Frame
            length = ((b0 & 0x0F) << 8) | data_bytes[1]
            self.buf = bytearray(data_bytes[2:])
            self.expected = length
            self.sn = 1
            self.active = True
            return None, "FF"

        elif frame_type == 2:  # Consecutive Frame
            if not self.active:
                return None, "CF_orphan"
            sn = b0 & 0x0F
            self.buf.extend(data_bytes[1:])
            self.sn = (self.sn + 1) & 0x0F
            if len(self.buf) >= self.expected:
                result = bytes(self.buf[:self.expected])
                self.reset()
                return result, "CF_done"
            return None, "CF"

        elif frame_type == 3:  # Flow Control
            return None, "FC"

        return None, f"UNK_{frame_type}"


# ─────────────────────────────────────────────────────────────────────────────
# Extended addressing handler (0x710 / 0x720)
# ─────────────────────────────────────────────────────────────────────────────
class ExtAddrCANTP:
    """CAN-TP with extended (2-byte) addressing — first byte is address."""
    def __init__(self, addr_byte):
        self.addr_byte = addr_byte
        self.tp = CANTP()

    def feed(self, data_bytes):
        if not data_bytes or data_bytes[0] != self.addr_byte:
            return None, "wrong_addr"
        return self.tp.feed(data_bytes[1:])


# ─────────────────────────────────────────────────────────────────────────────
# UDS decoder
# ─────────────────────────────────────────────────────────────────────────────
def decode_uds(payload, direction="REQ"):
    """Decode a complete UDS payload. Returns dict."""
    if not payload:
        return {}
    result = {"raw": payload.hex().upper()}
    sid = payload[0]

    # Handle positive response (SID + 0x40)
    is_resp = False
    if sid >= 0x40:
        actual_sid = sid - 0x40
        if actual_sid in UDS_SERVICES:
            is_resp = True
            result["type"] = "RESP"
            result["service"] = UDS_SERVICES[actual_sid]
            result["sid"] = actual_sid
        else:
            result["type"] = "UNK_RESP"
    elif sid == 0x7F:
        result["type"] = "NEG_RESP"
        result["requested_sid"] = payload[1] if len(payload) > 1 else 0
        result["nrc"] = payload[2] if len(payload) > 2 else 0
        nrc_names = {
            0x10: "GeneralReject", 0x11: "ServiceNotSupported",
            0x12: "SubFuncNotSupported", 0x13: "IncorrectLength",
            0x14: "ResponseTooLong", 0x21: "BusyRepeatRequest",
            0x22: "ConditionsNotCorrect", 0x24: "RequestSequenceError",
            0x25: "NoResponseFromSubnet", 0x26: "FailurePreventsExecution",
            0x31: "RequestOutOfRange", 0x33: "SecurityAccessDenied",
            0x35: "InvalidKey", 0x36: "ExceededAttempts",
            0x37: "RequiredTimeDelayNotExpired", 0x70: "UploadDownloadNotAccepted",
            0x71: "TransferDataSuspended", 0x72: "GeneralProgrammingFailure",
            0x73: "WrongBlockSequenceCounter", 0x78: "RequestCorrectlyReceivedRespPending",
            0x7E: "SubFuncNotSupportedInSession", 0x7F: "ServiceNotSupportedInSession",
        }
        result["nrc_name"] = nrc_names.get(result["nrc"], f"0x{result['nrc']:02X}")
        return result
    else:
        result["type"] = "REQ"
        result["service"] = UDS_SERVICES.get(sid, f"UNK_0x{sid:02X}")
        result["sid"] = sid

    # Decode per service
    if not is_resp:
        if sid == 0x10 and len(payload) >= 2:
            st = payload[1]
            result["session_type"] = SESSION_TYPES.get(st, f"0x{st:02X}")
        elif sid == 0x27 and len(payload) >= 2:
            level = payload[1]
            result["access_level"] = f"0x{level:02X}"
            result["subfunction"] = "requestSeed" if level % 2 == 1 else "sendKey"
            if len(payload) > 2:
                result["seed_or_key"] = payload[2:].hex().upper()
        elif sid == 0x22 and len(payload) >= 3:
            did = (payload[1] << 8) | payload[2]
            result["DID"] = f"0x{did:04X}"
        elif sid == 0x2E and len(payload) >= 3:
            did = (payload[1] << 8) | payload[2]
            result["DID"] = f"0x{did:04X}"
            result["data"] = payload[3:].hex().upper()
        elif sid == 0x21 and len(payload) >= 2:
            result["LID"] = f"0x{payload[1]:02X}"
        elif sid == 0x3B and len(payload) >= 2:
            result["LID"] = f"0x{payload[1]:02X}"
            raw = payload[2:]
            result["data_hex"] = raw.hex().upper()
            # Try ASCII decode
            try:
                ascii_str = raw.decode('ascii', errors='replace')
                printable = ''.join(c if 32 <= ord(c) < 127 else '.' for c in ascii_str)
                result["data_ascii"] = printable
            except:
                pass
        elif sid == 0x34 and len(payload) >= 3:
            comp = payload[1]
            addr_len = (payload[2] >> 4) & 0xF
            size_len = payload[2] & 0xF
            off = 3
            if len(payload) >= off + addr_len:
                addr = int.from_bytes(payload[off:off+addr_len], 'big')
                result["address"] = f"0x{addr:08X}"
                off += addr_len
            if len(payload) >= off + size_len:
                size = int.from_bytes(payload[off:off+size_len], 'big')
                result["size"] = f"0x{size:X} ({size} bytes)"
            result["compression"] = f"0x{comp:02X}"
        elif sid == 0x36 and len(payload) >= 2:
            result["block_seq"] = payload[1]
            result["block_data_len"] = len(payload) - 2
        elif sid == 0x31 and len(payload) >= 4:
            subf = payload[1]
            routine = (payload[2] << 8) | payload[3]
            subf_names = {0x01: "startRoutine", 0x02: "stopRoutine", 0x03: "requestResults"}
            result["subfunction"] = subf_names.get(subf, f"0x{subf:02X}")
            result["routine_id"] = f"0x{routine:04X}"
            result["routine_name"] = ROUTINE_IDS.get(routine, "unknown")
            if len(payload) > 4:
                result["option_record"] = payload[4:].hex().upper()
        elif sid == 0x3E:
            result["subfunction"] = f"0x{payload[1]:02X}" if len(payload) > 1 else "0x00"
        elif sid == 0x85 and len(payload) >= 2:
            result["dtc_setting"] = "on" if payload[1] == 0x01 else "off"
    else:
        actual_sid = sid - 0x40
        if actual_sid == 0x22 and len(payload) >= 3:
            did = (payload[1] << 8) | payload[2]
            result["DID"] = f"0x{did:04X}"
            result["data"] = payload[3:]
            result["data_hex"] = payload[3:].hex().upper()
        elif actual_sid == 0x27 and len(payload) >= 2:
            level = payload[1]
            result["access_level"] = f"0x{level:02X}"
            if len(payload) > 2:
                result["seed_or_key"] = payload[2:].hex().upper()
        elif actual_sid == 0x34 and len(payload) >= 3:
            max_block = (payload[1] & 0xF0) >> 4
            block_len_bytes = payload[1] & 0x0F
            if block_len_bytes and len(payload) >= 2 + block_len_bytes:
                blen = int.from_bytes(payload[2:2+block_len_bytes], 'big')
                result["max_block_len"] = f"0x{blen:X} ({blen} bytes)"
        elif actual_sid == 0x3B and len(payload) >= 2:
            result["LID"] = f"0x{payload[1]:02X}"
        elif actual_sid == 0x10 and len(payload) >= 2:
            st = payload[1]
            result["session_type"] = SESSION_TYPES.get(st, f"0x{st:02X}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CSV loader
# ─────────────────────────────────────────────────────────────────────────────
def load_csv(fname, max_rows=None):
    """Load CSV, return list of dicts."""
    path = os.path.join(BASE, fname)
    rows = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_rows and i >= max_rows:
                break
            rows.append(row)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Analysis functions
# ─────────────────────────────────────────────────────────────────────────────
def analyze_id_stats(rows):
    """Count messages per CAN ID."""
    counts = Counter()
    for r in rows:
        counts[r['id_hex']] += 1
    return counts


def extract_uds_messages(rows, diag_ids=None):
    """
    Extract and reassemble UDS messages.
    Returns list of (timestamp, can_id, direction, payload_bytes, decoded).
    """
    if diag_ids is None:
        # Standard UDS + extended addressing
        diag_ids = {'0x7e0', '0x7e8', '0x710', '0x720',
                    '0x7E0', '0x7E8', '0x710', '0x720'}

    # TP instances per channel
    tp_map = {
        '0x7e0': CANTP(), '0x7E0': CANTP(),
        '0x7e8': CANTP(), '0x7E8': CANTP(),
    }
    # Extended addressing
    tp_710 = ExtAddrCANTP(0x01)
    tp_720 = ExtAddrCANTP(0xF3)

    results = []

    for r in rows:
        cid = r['id_hex'].lower()
        if cid not in {x.lower() for x in diag_ids}:
            continue

        ts = float(r['timestamp'])
        data_str = r['data_hex'].strip()
        try:
            data_bytes = bytes(int(x, 16) for x in data_str.split())
        except:
            continue

        payload = None
        frame_type = None

        if cid in ('0x7e0', '0x710'):
            direction = "REQ"
        else:
            direction = "RESP"

        if cid == '0x7e0':
            payload, frame_type = tp_map['0x7e0'].feed(data_bytes)
        elif cid == '0x7e8':
            payload, frame_type = tp_map['0x7e8'].feed(data_bytes)
        elif cid == '0x710':
            payload, frame_type = tp_710.feed(data_bytes)
        elif cid == '0x720':
            payload, frame_type = tp_720.feed(data_bytes)

        if payload is not None:
            decoded = decode_uds(payload, direction)
            results.append({
                'ts': ts,
                'can_id': r['id_hex'],
                'direction': direction,
                'payload': payload,
                'frame_type': frame_type,
                'decoded': decoded,
            })

    return results


def analyze_broadcast(rows, broadcast_ids=None):
    """Analyze broadcast frames."""
    if broadcast_ids is None:
        broadcast_ids = ['0x102', '0x103', '0x110', '0x300',
                         '0x308', '0x320', '0x342', '0x516']

    stats = {}
    for bid in broadcast_ids:
        frames = [r for r in rows if r['id_hex'].lower() == bid.lower()]
        if not frames:
            continue

        # Sample data values
        samples = []
        for f in frames[:200]:
            try:
                b = bytes(int(x, 16) for x in f['data_hex'].split())
                samples.append(b)
            except:
                pass

        # Find constant vs variable bytes
        if samples:
            const_mask = []
            for i in range(8):
                vals = set(s[i] for s in samples if i < len(s))
                const_mask.append(len(vals) == 1)

            # Compute timing
            if len(frames) > 1:
                ts_list = [float(f['timestamp']) for f in frames[:500]]
                intervals = [ts_list[i+1]-ts_list[i] for i in range(len(ts_list)-1)]
                avg_interval = sum(intervals)/len(intervals) if intervals else 0
                freq_hz = 1/avg_interval if avg_interval > 0 else 0
            else:
                freq_hz = 0

        stats[bid] = {
            'count': len(frames),
            'dlc': frames[0]['dlc'] if frames else 0,
            'freq_hz': freq_hz,
            'const_bytes': const_mask,
            'sample': samples[0].hex().upper() if samples else "",
            'samples': samples[:20],
        }

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# PRINT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
SEP = "=" * 80
SEP2 = "-" * 60

def print_section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def print_subsection(title):
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_file_basic(fname, desc):
    """Section 1: ID statistics for a file."""
    print_section(f"{fname} — {desc}")

    rows = load_csv(fname)
    print(f"  Ukupno poruka: {len(rows):,}")

    counts = analyze_id_stats(rows)
    print(f"\n  CAN ID statistika ({len(counts)} jedinstvenih ID-ova):")
    print(f"  {'ID':<12} {'Count':>10}  {'%':>6}  DLC  Opis")
    print(f"  {'-'*12} {'-'*10}  {'-'*6}  ---  ----")

    total = len(rows)
    id_descs = {
        '0x102': 'Broadcast — RPM/temp/status',
        '0x103': 'Broadcast — temp/DTC',
        '0x110': 'Broadcast — system status',
        '0x300': 'Broadcast — general data',
        '0x308': 'Broadcast — sensor data',
        '0x320': 'Broadcast — misc',
        '0x342': 'Broadcast — variable data',
        '0x516': 'Broadcast — constant/SW info',
        '0x7e0': 'UDS Request (tester→ECU)',
        '0x7e8': 'UDS Response (ECU→tester)',
        '0x710': 'UDS Ext.Addr Request (0x01)',
        '0x720': 'UDS Ext.Addr Response (0xF3)',
    }

    # Get DLC samples
    dlc_map = {}
    for r in rows:
        cid = r['id_hex']
        if cid not in dlc_map:
            dlc_map[cid] = r['dlc']

    for cid, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        pct = 100*cnt/total
        desc_str = id_descs.get(cid.lower(), id_descs.get(cid, ''))
        dlc = dlc_map.get(cid, '?')
        print(f"  {cid:<12} {cnt:>10,}  {pct:>5.1f}%  {dlc:>3}  {desc_str}")

    return rows, counts


def analyze_uds_section(fname, rows, title="UDS/KWP2000 analiza"):
    """Section 2: UDS service analysis."""
    print_subsection(title)

    msgs = extract_uds_messages(rows)
    if not msgs:
        print("  Nema UDS poruka.")
        return msgs

    print(f"  Ukupno UDS payloada: {len(msgs)}")

    # Count by service
    svc_counts = Counter()
    for m in msgs:
        d = m['decoded']
        svc = d.get('service', d.get('type', 'UNK'))
        svc_counts[svc] += 1

    print(f"\n  Servisi (po broju poziva):")
    for svc, cnt in sorted(svc_counts.items(), key=lambda x: -x[1]):
        print(f"    {svc:<45} {cnt:>6}")

    return msgs


def analyze_eeprom_writes(fname):
    """Section 3: EEPROM write analysis (sniff_live.csv)."""
    print_subsection("EEPROM Write analiza — KWP 0x3B WriteDataByLocalId")

    rows = load_csv(fname)
    msgs = extract_uds_messages(rows)

    writes = [m for m in msgs if m['decoded'].get('sid') == 0x3B]
    write_resps = [m for m in msgs if m['decoded'].get('sid') == 0x7B - 0x40 + 0x40
                   or (m['decoded'].get('type') == 'RESP' and m['decoded'].get('sid') == 0x3B)]

    # Also get SecurityAccess
    sec_access = [m for m in msgs if m['decoded'].get('sid') == 0x27]

    print(f"  KWP 0x3B Write requestovi: {len(writes)}")
    print(f"  SecurityAccess (0x27) razmjena: {len(sec_access)}")

    # Print SecurityAccess sequence
    if sec_access:
        print(f"\n  SecurityAccess sekvenca:")
        for m in sec_access[:20]:
            d = m['decoded']
            lvl = d.get('access_level', '?')
            subfn = d.get('subfunction', '?')
            sk = d.get('seed_or_key', '')
            print(f"    {m['can_id']:<8} lvl={lvl} {subfn:<15} {sk}")

    # Print all writes
    print(f"\n  KWP 0x3B WriteDataByLocalId — sve operacije:")
    print(f"  {'LID':<6} {'Hex Data':<40} ASCII")
    print(f"  {'-'*6} {'-'*40} -----")

    for m in writes:
        d = m['decoded']
        lid = d.get('LID', '??')
        dhex = d.get('data_hex', '')
        dasc = d.get('data_ascii', '')
        # Truncate for readability
        if len(dhex) > 38:
            dhex_disp = dhex[:38] + ".."
        else:
            dhex_disp = dhex
        print(f"  {lid:<6} {dhex_disp:<40} {dasc}")

    # Group by LID
    lid_groups = defaultdict(list)
    for m in writes:
        d = m['decoded']
        lid = d.get('LID', '??')
        lid_groups[lid].append(d)

    print(f"\n  Grupiranje po LID:")
    for lid, items in sorted(lid_groups.items()):
        print(f"\n  LID {lid} — {len(items)} pisanje(a):")
        for d in items:
            dhex = d.get('data_hex', '')
            dasc = d.get('data_ascii', '')
            print(f"    HEX: {dhex}")
            if dasc.strip('.'):
                print(f"    ASC: {dasc}")

    return msgs


def analyze_rdbi(fname, desc):
    """Section 4: ReadDataByIdentifier analysis."""
    print_subsection(f"ReadDataByIdentifier (0x22) — {fname}")

    rows = load_csv(fname)
    msgs = extract_uds_messages(rows)

    # Collect all DID reads in order
    reqs = [m for m in msgs if m['decoded'].get('sid') == 0x22]
    resps = [m for m in msgs if m['decoded'].get('type') == 'RESP'
             and m['decoded'].get('sid') == 0x22]

    # Also check 0x21 (KWP ReadDataByLocalId)
    reqs_kwp = [m for m in msgs if m['decoded'].get('sid') == 0x21]

    print(f"  0x22 ReadDataByIdentifier requestovi: {len(reqs)}")
    print(f"  0x22 Responsi: {len(resps)}")
    print(f"  0x21 KWP ReadDataByLocalId: {len(reqs_kwp)}")

    # Build DID table — ordered by first appearance
    did_order = []
    did_seen = set()
    for m in reqs:
        did = m['decoded'].get('DID', '?')
        if did not in did_seen:
            did_order.append(did)
            did_seen.add(did)

    # Match requests to responses (by timestamp proximity)
    # Build dict: DID -> response data
    did_resp = {}
    resp_idx = 0
    for m in reqs:
        did = m['decoded'].get('DID', '?')
        # Find matching response
        for rm in resps[resp_idx:resp_idx+5]:
            if rm['decoded'].get('DID') == did:
                did_resp[did] = rm['decoded'].get('data_hex', '')
                break

    print(f"\n  DID tablica (redoslijed BUDS2 upita):")
    print(f"  {'#':<4} {'DID':<8} {'Response HEX':<40} Napomena")
    print(f"  {'-'*4} {'-'*8} {'-'*40} -------")

    for i, did in enumerate(did_order):
        resp_hex = did_resp.get(did, '')
        # Try to find response from actual messages
        for m in resps:
            if m['decoded'].get('DID') == did:
                resp_hex = m['decoded'].get('data_hex', '')
                break
        if len(resp_hex) > 38:
            resp_hex_d = resp_hex[:38] + ".."
        else:
            resp_hex_d = resp_hex
        print(f"  {i+1:<4} {did:<8} {resp_hex_d:<40}")

    # KWP LIDs
    if reqs_kwp:
        lid_order = []
        lid_seen = set()
        for m in reqs_kwp:
            lid = m['decoded'].get('LID', '?')
            if lid not in lid_seen:
                lid_order.append(lid)
                lid_seen.add(lid)

        print(f"\n  KWP 0x21 LID tablica:")
        resps_kwp = [m for m in msgs if m['decoded'].get('type') == 'RESP'
                     and m['decoded'].get('sid') == 0x21]
        lid_resp = {}
        for m in resps_kwp:
            lid = m['decoded'].get('LID', '?')
            lid_resp[lid] = m['decoded'].get('data_hex', '')

        for i, lid in enumerate(lid_order):
            resp_hex = lid_resp.get(lid, '')
            if len(resp_hex) > 38:
                resp_hex_d = resp_hex[:38] + ".."
            else:
                resp_hex_d = resp_hex
            print(f"  {i+1:<4} {lid:<8} {resp_hex_d:<40}")

    return msgs


def analyze_flash(fname):
    """Section 5: Firmware flash sequence."""
    print_subsection("Firmware Flash sekvenca — sniff_live2.csv")

    rows = load_csv(fname)
    msgs = extract_uds_messages(rows)

    print(f"  Ukupno UDS poruka: {len(msgs)}")

    # Print full sequence in order
    session_changes = [m for m in msgs if m['decoded'].get('sid') == 0x10]
    sec_access = [m for m in msgs if m['decoded'].get('sid') == 0x27]
    downloads = [m for m in msgs if m['decoded'].get('sid') == 0x34]
    transfers = [m for m in msgs if m['decoded'].get('sid') == 0x36]
    exits = [m for m in msgs if m['decoded'].get('sid') == 0x37]
    routines = [m for m in msgs if m['decoded'].get('sid') == 0x31]
    dtc_ctrl = [m for m in msgs if m['decoded'].get('sid') == 0x85]
    comm_ctrl = [m for m in msgs if m['decoded'].get('sid') == 0x28]
    ecu_reset = [m for m in msgs if m['decoded'].get('sid') == 0x11]

    print(f"\n  === Session Control (0x10) ===")
    for m in session_changes:
        d = m['decoded']
        st = d.get('session_type', '?')
        t = d.get('type', '?')
        print(f"    {m['can_id']:<8} {t:<6} SessionType={st}")

    print(f"\n  === SecurityAccess (0x27) ===")
    print(f"  Razina   Smjer    Subfunction      Seed/Key")
    for m in sec_access:
        d = m['decoded']
        lvl = d.get('access_level', '?')
        subfn = d.get('subfunction', '?')
        sk = d.get('seed_or_key', '')[:32]
        t = d.get('type', '?')
        print(f"  {lvl:<8} {m['can_id']:<8} {subfn:<18} {sk}")

    print(f"\n  === ControlDTCSetting (0x85) ===")
    for m in dtc_ctrl:
        d = m['decoded']
        print(f"    {m['can_id']:<8} DTC={d.get('dtc_setting','?')}")

    print(f"\n  === CommunicationControl (0x28) ===")
    for m in comm_ctrl:
        d = m['decoded']
        print(f"    {m['can_id']:<8} raw={d.get('raw','')}")

    print(f"\n  === RequestDownload (0x34) ===")
    for m in downloads:
        d = m['decoded']
        t = d.get('type', '?')
        if t == 'REQ':
            addr = d.get('address', '?')
            size = d.get('size', '?')
            comp = d.get('compression', '?')
            print(f"    REQ  addr={addr}  size={size}  compression={comp}")
        else:
            mbl = d.get('max_block_len', '?')
            print(f"    RESP max_block_len={mbl}")

    print(f"\n  === TransferData (0x36) ===")
    print(f"  Ukupno blokova: {len(transfers)}")
    # Show first/last few
    show_transfers = list(transfers[:5]) + (list(transfers[-5:]) if len(transfers) > 10 else [])
    for m in show_transfers:
        d = m['decoded']
        t = d.get('type', '?')
        seq = d.get('block_seq', '?')
        blen = d.get('block_data_len', '?')
        print(f"    {t:<6} seq={seq}  data_len={blen}")
    if len(transfers) > 10:
        print(f"    ... ({len(transfers)-10} blokova između) ...")

    print(f"\n  === RequestTransferExit (0x37) ===")
    for m in exits:
        d = m['decoded']
        print(f"    {m['can_id']:<8} {d.get('type','?')} raw={d.get('raw','')[:20]}")

    print(f"\n  === RoutineControl (0x31) ===")
    for m in routines:
        d = m['decoded']
        t = d.get('type', '?')
        subfn = d.get('subfunction', '?')
        rid = d.get('routine_id', '?')
        rname = d.get('routine_name', '?')
        opt = d.get('option_record', '')
        print(f"    {m['can_id']:<8} {t:<6} {subfn:<18} {rid} ({rname}) opt={opt}")

    print(f"\n  === ECU Reset (0x11) ===")
    for m in ecu_reset:
        d = m['decoded']
        print(f"    {m['can_id']:<8} {d.get('type','?')} raw={d.get('raw','')}")

    # Compressed kronological summary — skip transfer data spam
    print(f"\n  === Kronološka sekvenca (bez TransferData) ===")
    transfer_block_start = None
    transfer_count = 0
    for m in msgs:
        d = m['decoded']
        sid = d.get('sid')
        t = d.get('type', '?')
        # Skip transfer data noise
        if sid == 0x36 or (t == 'RESP' and d.get('service') == 'TransferData'):
            transfer_count += 1
            if transfer_block_start is None:
                transfer_block_start = m['ts']
            continue
        else:
            if transfer_count > 0:
                print(f"    [... {transfer_count} TransferData blokova ...]")
                transfer_count = 0
                transfer_block_start = None

        if t == 'NEG_RESP':
            svc_name = UDS_SERVICES.get(d.get('requested_sid', 0), '?')
            print(f"    {m['can_id']:<8} NEG_RESP  svc={svc_name} NRC={d.get('nrc_name','?')}")
        elif t in ('REQ', 'RESP'):
            svc = d.get('service', f"0x{sid:02X}" if sid else '?')
            extra = ""
            if 'session_type' in d:
                extra = f" session={d['session_type']}"
            elif 'DID' in d:
                extra = f" DID={d['DID']}"
            elif 'LID' in d:
                extra = f" LID={d['LID']}"
            elif 'address' in d:
                extra = f" addr={d['address']} size={d.get('size','?')}"
            elif 'block_seq' in d:
                extra = f" seq={d['block_seq']}"
            elif 'routine_id' in d:
                extra = f" routine={d['routine_id']} ({d.get('routine_name','?')})"
            elif 'access_level' in d:
                extra = f" lvl={d['access_level']} {d.get('subfunction','')}"
            print(f"    {m['can_id']:<8} {t:<6} {svc:<35}{extra}")
    if transfer_count > 0:
        print(f"    [... {transfer_count} TransferData blokova ...]")

    return msgs


def analyze_broadcast_detail(rows, fname):
    """Section 6: Broadcast parameter analysis."""
    print_subsection(f"Broadcast parametri — {fname}")

    stats = analyze_broadcast(rows)

    for bid, s in sorted(stats.items()):
        print(f"\n  ID {bid}:")
        print(f"    Poruka: {s['count']:,}  DLC: {s['dlc']}  Freq: {s['freq_hz']:.1f} Hz")
        print(f"    Uzorak: {s['sample']}")

        if s['samples']:
            # Show byte variability
            const = s['const_bytes']
            line = "    Bajt:   "
            for i in range(8):
                line += f"[{i}]  "
            print(line)

            line = "    Konst:  "
            for c in const:
                line += "DA   " if c else "NE   "
            print(line)

            # For 0x516 — it's constant, decode fields
            if bid == '0x516' and s['samples']:
                samp = s['samples'][0]
                print(f"\n    0x516 dekodirani bajtovi:")
                print(f"    Hex: {samp.hex().upper()}")
                print(f"    ASCII: {''.join(chr(b) if 32 <= b < 127 else '.' for b in samp)}")
                # Bytes 4-7 look like ASCII
                print(f"    Bytes[4-7] ASCII: {''.join(chr(samp[i]) if 32<=samp[i]<127 else '.' for i in range(4,8))}")
                print(f"    Byte[0]: 0x{samp[0]:02X} = {samp[0]}")
                print(f"    Byte[1]: 0x{samp[1]:02X} = {samp[1]}")
                print(f"    Byte[2]: 0x{samp[2]:02X} = {samp[2]}")
                print(f"    Byte[3]: 0x{samp[3]:02X} = {samp[3]}")

                # Check all samples
                all_same = all(s2 == samp for s2 in s['samples'])
                print(f"    Svi uzorci identični: {'DA' if all_same else 'NE'}")

                # Unique values per byte
                print(f"\n    Unique vrijednosti po bajtu (iz 20 uzoraka):")
                for i in range(min(8, len(samp))):
                    vals = sorted(set(s2[i] for s2 in s['samples'] if i < len(s2)))
                    ascii_vals = [f"'{chr(v)}'" if 32<=v<127 else f"0x{v:02X}" for v in vals]
                    print(f"    Bajt[{i}]: {ascii_vals}")

            # For 0x342 — variable, analyze
            elif bid == '0x342':
                print(f"\n    0x342 varijabilna analiza (20 uzoraka):")
                for i, samp in enumerate(s['samples'][:10]):
                    b = samp
                    # Possible: bytes 0-1 = some u16, 2-3 = another u16, etc.
                    val01_be = (b[0] << 8 | b[1]) if len(b) >= 2 else 0
                    val23_be = (b[2] << 8 | b[3]) if len(b) >= 4 else 0
                    val45_be = (b[4] << 8 | b[5]) if len(b) >= 6 else 0
                    val67_be = (b[6] << 8 | b[7]) if len(b) >= 8 else 0
                    print(f"    [{i:02d}] {b.hex().upper()}  "
                          f"w01={val01_be:5d}  w23={val23_be:5d}  "
                          f"w45={val45_be:5d}  w67={val67_be:5d}")

            # For 0x110
            elif bid == '0x110' and s['samples']:
                print(f"\n    0x110 analiza (10 uzoraka):")
                for i, samp in enumerate(s['samples'][:10]):
                    print(f"    [{i:02d}] {samp.hex().upper()}")

            # For 0x102 — RPM/temp
            elif bid == '0x102' and s['samples']:
                print(f"\n    0x102 analiza (RPM=bytes[1:3]*0.25, temp=byte[5]-40):")
                for i, samp in enumerate(s['samples'][:10]):
                    if len(samp) >= 8:
                        rpm = ((samp[1] << 8) | samp[2]) * 0.25
                        temp = samp[5] - 40
                        ctr = (samp[6] << 8) | samp[7]
                        print(f"    [{i:02d}] {samp.hex().upper()}  RPM={rpm:.1f}  temp={temp}°C  ctr={ctr}")

            # For 0x308
            elif bid == '0x308' and s['samples']:
                print(f"\n    0x308 analiza (10 uzoraka):")
                for i, samp in enumerate(s['samples'][:10]):
                    print(f"    [{i:02d}] {samp.hex().upper()}")


def analyze_cdid(fname):
    """Analyze CDID changes."""
    print_subsection("CDID promjene — sniff_cdid.csv")

    rows = load_csv(fname)
    msgs = extract_uds_messages(rows)

    writes_2e = [m for m in msgs if m['decoded'].get('sid') == 0x2E]
    writes_3b = [m for m in msgs if m['decoded'].get('sid') == 0x3B]
    reads_22 = [m for m in msgs if m['decoded'].get('sid') == 0x22]
    reads_22_r = [m for m in msgs if m['decoded'].get('type') == 'RESP'
                  and m['decoded'].get('sid') == 0x22]

    print(f"  0x2E WriteDataByIdentifier: {len(writes_2e)}")
    print(f"  0x3B KWP WriteDataByLocalId: {len(writes_3b)}")
    print(f"  0x22 ReadDataByIdentifier (req): {len(reads_22)}")

    if writes_2e:
        print(f"\n  WriteDataByIdentifier (0x2E) operacije:")
        for m in writes_2e:
            d = m['decoded']
            did = d.get('DID', '?')
            data_hex = d.get('data', '')
            if isinstance(data_hex, bytes):
                data_hex = data_hex.hex().upper()
            ascii_repr = ''
            if isinstance(d.get('data'), bytes):
                ascii_repr = ''.join(chr(b) if 32<=b<127 else '.' for b in d['data'])
            print(f"    DID={did}  data={data_hex[:60]}  ascii='{ascii_repr}'")

    if writes_3b:
        print(f"\n  KWP WriteDataByLocalId (0x3B) operacije:")
        for m in writes_3b:
            d = m['decoded']
            lid = d.get('LID', '?')
            dhex = d.get('data_hex', '')
            dasc = d.get('data_ascii', '')
            print(f"    LID={lid}  data={dhex[:60]}  ascii='{dasc}'")

    # Show read-before-write and write-after sequences
    print(f"\n  Kronološka sekvenca zapisa:")
    for m in msgs:
        d = m['decoded']
        sid = d.get('sid')
        t = d.get('type', '?')
        if t not in ('REQ', 'RESP', 'NEG_RESP'):
            continue
        svc = d.get('service', '?')
        extra = ''
        if sid in (0x22, 0x62):
            did = d.get('DID', '')
            resp = d.get('data_hex', '')[:40]
            extra = f" DID={did} data={resp}"
        elif sid in (0x2E, 0x6E):
            did = d.get('DID', '')
            data = d.get('data', '')
            if isinstance(data, bytes):
                asc = ''.join(chr(b) if 32<=b<127 else '.' for b in data)
                extra = f" DID={did} ascii='{asc}'"
            else:
                extra = f" DID={did} data={str(data)[:40]}"
        elif sid in (0x3B, 0x7B):
            lid = d.get('LID', '')
            dasc = d.get('data_ascii', '')
            extra = f" LID={lid} ascii='{dasc}'"
        elif t == 'NEG_RESP':
            extra = f" NRC={d.get('nrc_name','?')}"
        elif 'session_type' in d:
            extra = f" session={d['session_type']}"
        elif 'access_level' in d:
            extra = f" lvl={d['access_level']} {d.get('subfunction','')}"
        print(f"    {m['can_id']:<8} {t:<6} {svc:<35}{extra}")

    return msgs


# ─────────────────────────────────────────────────────────────────────────────
# DEEP ANALYSIS for sniff_live.csv — find DESS, VIN, motor, customer
# ─────────────────────────────────────────────────────────────────────────────
def analyze_live_deep(fname):
    """Deep analysis of sniff_live.csv for specific EEPROM operations."""
    print_subsection("EEPROM Deep Analysis — VIN, motor, customer, DESS, service reset")

    rows = load_csv(fname)
    msgs = extract_uds_messages(rows)

    # All writes (both KWP and UDS)
    all_writes = [m for m in msgs if m['decoded'].get('sid') in (0x3B, 0x2E)]
    print(f"  Ukupno write operacija: {len(all_writes)}")

    # Show all with more detail
    print(f"\n  Sve EEPROM write operacije (detalj):")
    print(f"  {'#':<4} {'SID':<6} {'ID/DID':<8} {'Hex Data'}")
    print(f"  {'-'*4} {'-'*6} {'-'*8} {'-'*60}")

    for i, m in enumerate(all_writes):
        d = m['decoded']
        sid_str = f"0x{d.get('sid', 0):02X}"
        identifier = d.get('LID', d.get('DID', '?'))
        dhex = d.get('data_hex', '')
        dasc = d.get('data_ascii', '')
        if isinstance(d.get('data'), bytes):
            dhex = d['data'].hex().upper()
            dasc = ''.join(chr(b) if 32<=b<127 else '.' for b in d['data'])
        print(f"  {i+1:<4} {sid_str:<6} {identifier:<8} {dhex[:60]}")
        if dasc and any(32 <= ord(c) < 127 for c in dasc):
            print(f"  {'':4} {'':6} {'':8} ASCII: '{dasc}'")

    # Security Access analysis
    print(f"\n  SecurityAccess (0x27) — Seed/Key razmjena:")
    for m in msgs:
        d = m['decoded']
        if d.get('sid') == 0x27:
            lvl = d.get('access_level', '?')
            subfn = d.get('subfunction', '?')
            sk = d.get('seed_or_key', '')
            print(f"    {m['can_id']:<8} {subfn:<20} level={lvl}  value={sk}")

    # Session control
    print(f"\n  Session Control (0x10):")
    for m in msgs:
        d = m['decoded']
        if d.get('sid') == 0x10:
            t = d.get('type', '?')
            st = d.get('session_type', '?')
            print(f"    {m['can_id']:<8} {t:<6} session={st}")

    # Routine Control
    print(f"\n  RoutineControl (0x31):")
    for m in msgs:
        d = m['decoded']
        if d.get('sid') == 0x31:
            subfn = d.get('subfunction', '?')
            rid = d.get('routine_id', '?')
            rname = d.get('routine_name', '?')
            opt = d.get('option_record', '')[:20]
            t = d.get('type', '?')
            print(f"    {m['can_id']:<8} {t:<6} {subfn:<18} {rid} ({rname}) opt={opt}")

    # Check for specific patterns
    print(f"\n  Pretraga ASCII podataka (motor, VIN, customer):")
    for m in all_writes:
        d = m['decoded']
        raw_data = None
        if isinstance(d.get('data'), bytes):
            raw_data = d['data']
        elif d.get('data_hex'):
            try:
                raw_data = bytes.fromhex(d['data_hex'].replace(' ', ''))
            except:
                pass

        if raw_data:
            ascii_str = ''.join(chr(b) if 32<=b<127 else '.' for b in raw_data)
            # Look for patterns
            if any(c.isalnum() and c != '.' for c in ascii_str.replace('.', '')):
                identifier = d.get('LID', d.get('DID', '?'))
                print(f"    LID/DID={identifier}: '{ascii_str}'")


# ─────────────────────────────────────────────────────────────────────────────
# LIVEDATA DID mapping with response values
# ─────────────────────────────────────────────────────────────────────────────
def analyze_livedata_full(fname, desc):
    """Full livedata analysis with req/resp pairing."""
    print_subsection(f"LiveData DID mapiranje — {fname}")

    rows = load_csv(fname)
    msgs = extract_uds_messages(rows)

    print(f"  Ukupno UDS poruka: {len(msgs)}")

    # Pair requests with responses
    # Build ordered list of DID queries
    pairs = []
    i = 0
    while i < len(msgs):
        m = msgs[i]
        d = m['decoded']
        if d.get('type') == 'REQ' and d.get('sid') == 0x22:
            did = d.get('DID', '?')
            # Look for response
            resp_data = None
            for j in range(i+1, min(i+10, len(msgs))):
                rd = msgs[j]['decoded']
                if rd.get('type') == 'RESP' and rd.get('DID') == did:
                    resp_data = rd.get('data')
                    if isinstance(resp_data, bytes):
                        pass
                    else:
                        resp_data = None
                    resp_hex = rd.get('data_hex', '')
                    break
            else:
                resp_hex = ''
                resp_data = None
            pairs.append((did, resp_hex, resp_data))
        elif d.get('type') == 'REQ' and d.get('sid') == 0x21:
            lid = d.get('LID', '?')
            # Look for KWP response
            resp_hex = ''
            for j in range(i+1, min(i+10, len(msgs))):
                rd = msgs[j]['decoded']
                if rd.get('type') == 'RESP' and rd.get('sid') == 0x21:
                    resp_hex = rd.get('data_hex', '')
                    break
            pairs.append((f"KWP_{lid}", resp_hex, None))
        i += 1

    # Deduplicate preserving order but show repeat count
    seen_dids = OrderedDict()
    for did, resp_hex, resp_data in pairs:
        if did not in seen_dids:
            seen_dids[did] = {'resp_hex': resp_hex, 'resp_data': resp_data, 'count': 1}
        else:
            seen_dids[did]['count'] += 1
            if resp_hex:
                seen_dids[did]['resp_hex'] = resp_hex
                seen_dids[did]['resp_data'] = resp_data

    print(f"  Jedinstveni DID-ovi: {len(seen_dids)}")
    print(f"  Ukupni upiti: {len(pairs)}")

    print(f"\n  {'#':<4} {'DID':<10} {'Cnt':>5}  {'Response HEX':<50} Dekodirana vrijednost")
    print(f"  {'-'*4} {'-'*10} {'-'*5}  {'-'*50} -------------------")

    known_dids = {
        # Common UDS DIDs
        '0xF186': 'Active Diagnostic Session',
        '0xF187': 'VehicleManufacturerSparePartNumber',
        '0xF188': 'VehicleManufacturerECUSoftwareNumber',
        '0xF189': 'VehicleManufacturerECUSoftwareVersionNumber',
        '0xF18A': 'SystemSupplierIdentifier',
        '0xF18B': 'ECU Manufacturing Date',
        '0xF18C': 'ECU Serial Number',
        '0xF18E': 'SupportedFunctionalUnits',
        '0xF190': 'VIN',
        '0xF191': 'VehicleManufacturerECUHardwareNumber',
        '0xF192': 'SystemSupplierECUHardwareNumber',
        '0xF193': 'SystemSupplierECUHardwareVersionNumber',
        '0xF194': 'SystemSupplierECUSoftwareNumber',
        '0xF195': 'SystemSupplierECUSoftwareVersionNumber',
        '0xF197': 'VehicleManufacturerSystemName',
        '0xF19E': 'AUTOSAR Platform Description',
        '0xF1A0': 'ECU Platform',
        '0x0100': 'DTC Count / Status',
        '0xFD00': 'ODO',
        '0xFD01': 'Engine Hours',
        '0xFD02': 'Coolant Temp',
        '0xFD03': 'RPM',
        '0xFD04': 'TPS',
        '0xFD05': 'MAP Sensor',
        '0xFD06': 'MAF Sensor',
        '0xFD07': 'Injector PW',
        '0xFD08': 'Ignition Advance',
        '0xFD09': 'Lambda',
        '0xFD0A': 'Battery Voltage',
        '0xFD0B': 'Air Temp',
        '0xFD0C': 'Fuel Pressure',
        '0xFD0D': 'Knock Count',
        '0xFD10': 'Throttle Position Raw',
        '0xFD20': 'Torque Request',
        '0xFD21': 'Torque Actual',
        '0xFD22': 'Torque Limit',
        '0xFD30': 'Air Charge',
        '0xFD31': 'Volumetric Efficiency',
        '0xFD40': 'Pedal Position',
        '0xFD50': 'Fuel Trim ST',
        '0xFD51': 'Fuel Trim LT',
        '0xFD60': 'SC Boost Pressure',
        '0xFD61': 'SC Bypass Valve',
        '0x2201': 'Correction Factor',
        '0x2202': 'Fuel Map Correction',
    }

    for i, (did, info) in enumerate(seen_dids.items()):
        resp_hex = info['resp_hex']
        cnt = info['count']
        resp_data = info['resp_data']

        # Decode response
        decoded_val = ''
        if resp_data and isinstance(resp_data, bytes) and len(resp_data) > 0:
            # Try various decodings
            if len(resp_data) == 1:
                decoded_val = f"u8={resp_data[0]}"
            elif len(resp_data) == 2:
                u16be = (resp_data[0] << 8) | resp_data[1]
                i16be = u16be if u16be < 32768 else u16be - 65536
                decoded_val = f"u16={u16be} (i16={i16be})"
            elif len(resp_data) == 4:
                u32 = int.from_bytes(resp_data, 'big')
                decoded_val = f"u32={u32}"
            else:
                # Try ASCII
                try:
                    ascii_v = resp_data.decode('ascii', errors='replace')
                    printable = ''.join(c if 32<=ord(c)<127 else '.' for c in ascii_v)
                    if any(c.isalnum() for c in printable):
                        decoded_val = f"ascii='{printable}'"
                except:
                    pass

        name = known_dids.get(did, '')
        disp_hex = (resp_hex[:48] + '..') if len(resp_hex) > 50 else resp_hex
        print(f"  {i+1:<4} {did:<10} {cnt:>5}  {disp_hex:<50} {decoded_val}")
        if name:
            print(f"  {'':4} {'':10} {'':5}  {'':50} [{name}]")

    return msgs, seen_dids


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("  ME17Suite — CAN Log Analiza")
    print("  Datum: 2026-03-19")
    print("=" * 80)

    # ── 1. sniff_buds2.csv ──────────────────────────────────────────────────
    rows_buds2, counts_buds2 = analyze_file_basic("sniff_buds2.csv",
        "Prva kratka sesija — identifikacija CAN ID-ova")
    analyze_uds_section("sniff_buds2.csv", rows_buds2, "UDS/KWP analiza — sniff_buds2.csv")
    analyze_broadcast_detail(rows_buds2, "sniff_buds2.csv")

    # ── 2. sniff_live.csv ───────────────────────────────────────────────────
    rows_live, counts_live = analyze_file_basic("sniff_live.csv",
        "EEPROM operacije (VIN, motor, DESS, ...)")
    analyze_uds_section("sniff_live.csv", rows_live, "UDS/KWP analiza — sniff_live.csv")
    analyze_live_deep("sniff_live.csv")
    analyze_broadcast_detail(rows_live, "sniff_live.csv")

    # ── 3. sniff_live2.csv ──────────────────────────────────────────────────
    rows_live2, counts_live2 = analyze_file_basic("sniff_live2.csv",
        "Firmware flash kompletna sekvenca")
    analyze_flash("sniff_live2.csv")
    analyze_broadcast_detail(rows_live2, "sniff_live2.csv")

    # ── 4. sniff_cdid.csv ───────────────────────────────────────────────────
    rows_cdid, counts_cdid = analyze_file_basic("sniff_cdid.csv",
        "CDID promjene (model year, usage, version series)")
    analyze_cdid("sniff_cdid.csv")
    analyze_broadcast_detail(rows_cdid, "sniff_cdid.csv")

    # ── 5. sniff_livedata.csv ───────────────────────────────────────────────
    rows_ld, counts_ld = analyze_file_basic("sniff_livedata.csv",
        "Live data reading — prva serija 24 parametra")
    msgs_ld, dids_ld = analyze_livedata_full("sniff_livedata.csv",
        "sniff_livedata.csv — prva serija")
    analyze_broadcast_detail(rows_ld, "sniff_livedata.csv")

    # ── 6. sniff_maps24.csv ─────────────────────────────────────────────────
    rows_m24, counts_m24 = analyze_file_basic("sniff_maps24.csv",
        "Live data reading — druga serija 24 parametra")
    msgs_m24, dids_m24 = analyze_livedata_full("sniff_maps24.csv",
        "sniff_maps24.csv — druga serija")
    analyze_broadcast_detail(rows_m24, "sniff_maps24.csv")

    # ── FINAL SUMMARY ────────────────────────────────────────────────────────
    print_section("FINALNI SAŽETAK")

    print("\n  Fajlovi analizirani:")
    sizes = {}
    for fname in FILES:
        path = os.path.join(BASE, fname)
        size = os.path.getsize(path)
        sizes[fname] = size
        print(f"    {fname:<30} {size/1024/1024:.1f} MB")

    # All unique DIDs seen
    all_dids = set(list(dids_ld.keys()) + list(dids_m24.keys()))
    print(f"\n  Ukupno jedinstvenih DID-ova u live data: {len(all_dids)}")
    for did in sorted(all_dids):
        cnt_ld = dids_ld.get(did, {}).get('count', 0)
        cnt_m24 = dids_m24.get(did, {}).get('count', 0)
        print(f"    {did:<10} livedata={cnt_ld:>4}  maps24={cnt_m24:>4}")

    print(f"\n{SEP}")
    print("  Analiza završena.")
    print(SEP)


if __name__ == '__main__':
    main()
