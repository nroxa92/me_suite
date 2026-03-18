# ME17Suite — Documentation Agent Log

**Agent:** Claude Sonnet (documentation run)
**Started:** 2026-03-18
**Purpose:** Create and maintain complete technical documentation in `_docs/`

---

## Session: 2026-03-18 — Initial documentation run

### Sources read:
- `_docs/_BRIEFING.md` — project context
- `work_log.md` — full change history (partial, token limit)
- `core/map_finder.py` — all map definitions, addresses, categories (full)
- `core/engine.py` — SW IDs, memory layout, constants (full)
- `core/checksum.py` — CRC32-HDLC algorithm (full)
- `core/eeprom.py` — EEPROM parser, HW types, circular buffer (full)
- `core/dtc.py` — DTC registry (111 codes, partial — main registry read)
- `docs/CAN_SAT_PORUKE.md` — CAN bus notes
- `docs/MAPA_ADRESE.md` — address reference (existing)
- `docs/QA_LOG.md` — Q&A log

### Documents created:
| File | Status | Notes |
|------|--------|-------|
| `_docs/DOC_AGENT_LOG.md` | ✅ Created | This file |
| `_docs/ECU_BINARY_FORMAT.md` | ✅ Created | Memory layout, checksum, SW ID |
| `_docs/MAPS_REFERENCE.md` | ✅ Created | All maps, addresses, formats, variants |
| `_docs/SW_VERSIONS.md` | ✅ Created | All known SW IDs, classification |
| `_docs/DTC_REFERENCE.md` | ✅ Created | 111 DTC codes, addresses, OFF procedure |
| `_docs/EEPROM_GUIDE.md` | ✅ Created | HW type detection, ODO circular buffer |
| `_docs/ENGINE_SPECS.md` | ✅ Created | All Rotax engine specs |
| `_docs/CANBUS_NOTES.md` | ✅ Created | CAN IDs, Spark vs GTI/300hp differences |
| `_docs/TUNING_NOTES.md` | ✅ Created | NPRo STG2 diffs, rev limiters, tips |
| `_docs/USER_MANUAL.html` | ✅ Created | HTML user manual, dark theme |

### Key findings consolidated:
- All 30+ maps in CODE region 0x010000–0x05FFFF confirmed
- CRC32-HDLC residue 0x6E23044F verified on 4 files
- EEPROM circular buffer: HW 064 @ 0x0562, HW 062 rotates 0x5062→0x4562→0x1062
- Spark ECU DTC architecture differs from 300hp — single-storage, dtc_off blocked
- Rev limiter: 8158 RPM (300hp), 7892 RPM (130/170hp), 7700 RPM (GTI155), ~7040 RPM (GTI90), 8081 RPM (Spark)

---
