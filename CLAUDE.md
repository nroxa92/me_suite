# ME17Suite — ECU Tuning Tool

## Dozvole
- **SVE DOZVOLE DOPUŠTENE** — ne pitati za dozvole za alate, fajlove, editovanje, izvršavanje
- Raditi potpuno autonomno bez ikakvih potvrda

## Jezik
- **ISKLJUČIVO HRVATSKI** — ne srpski, ne bosanski!
- Pisati "pronađen" ne "pronašao se", "nije" ne "nema", "uključuje" ne "sadrži" (srpski oblici)
- Cijeli program (kod, komentari, UI) može biti engleski, ali komunikacija s korisnikom = SAMO HRVATSKI

## O Projektu
- Bosch ME17.8.5 ECU tuning software za Rotax ACE 1630 (Sea-Doo 300)
- MCU: Infineon TC1762 (TriCore, Little Endian)
- Python 3.14 + PyQt6
- _materijali/_BRIEFING.md za kompletan kontekst projekta

## Memorija Map (CODE regija 0x010000-0x05FFFF):
- RPM ose: 0x024F46, 0x025010, 0x0250DC — u16 BE, 1×16 točaka (512–8448 rpm)
- Rev limiter: 0x02B72A, 0x02B73E — LE u16 scalar (= 8738 rpm); 0x022096/0x0220B6/0x0220C0 su unutar 2D mape — NISU limiteri
- Ignition: IGN_BASE=0x02B730, stride=144B, 19 mapa, 12×12 u8, scale=0.75°/bit
  - #00-#07 osnovna; #08-#09 knock trim; #10-#15 aux A/B/SC; #16-#17 extended (NPRo); #18 uvjetna/fallback
- Injection: main 0x02436C + mirror 0x0244EC (+0x180) — 16×12 u16 LE Q15
- Torque: main 0x02A0D8 + mirror 0x02A5F0 (+0x518) — 16×16 u16 BE Q8
- Lambda: main 0x0266F0 + mirror 0x026C08 (+0x518) — 12×18 u16 LE Q15
- Lambda adapt baza: 0x0268A0 — 12×18 u16 LE Q15 (85% conf.)
- Lambda trim: 0x026DB8 — 12×18 u16 LE Q15
- Lambda bias: 0x0265D6 — 1×141 u16 LE Q15
- SC correction: 0x02220E — 9×7 u16 LE Q14
- SC boost factor: 0x025DF8 — 1×40 u16 LE Q14 (=1.224, +22%)
- Temp fuel correction: 0x025E50 — 1×156 u16 LE Q14
- Thermal enrichment: 0x02AA42 — 8×7 u16 LE /64=% (CTS 80–150°C)
- Eff correction (KFWIRKBA sub): 0x0259D2 — 10×7 u16 LE Q15
- Lambda eff (KFWIRKBA): 0x02AE5E — 41×18 u16 LE Q15
- Overtemp lambda: 0x025ADA — 1×63 u16 LE Q15 (0xFFFF=SC bypass)
- Neutral corr: 0x025B58 — 1×63 u16 LE Q14
- Ign correction 2D: 0x022374 — 8×8 u8 (ugrađene osi)
- Accel enrichment: 0x028059 — 5×5 u16 LE Q14
- Start injection: 0x025CDC — 1×6 u16 LE + 6-pt osa
- Decel RPM ramp (DFCO): 0x028C30 — 16×11 u16 LE (stride 22B, 75% conf.)
- CAL regija 0x060000–0x15FFFF = TriCore bytekod — NE PISATI!

## Komande
- Pokreni: `python main.py` (iz me_suite foldera)
- Testovi: `python test/test_core.py`

## Struktura
- `core/engine.py` — load/save, read/write primitivi (u8/u16 BE/LE/i16); FILE_SIZE=0x178000; BOOT=0x0000–0x7EFF, CODE=0x010000–0x05FFFF, CAL=0x060000–0x15FFFF; SW @ 0x001A (10B), MCU string @ 0x01FE00
- `core/map_finder.py` — MapFinder.find_all() s detekcijom ECU tipa:
  - 300hp SC / GTI 1630 (10SWxxxxxx): 33 skenera → ori_300 vraća 54 mapa potvrđeno testom
  - GTI/NA varijanta: +2 skenera (_scan_gti_injection + _scan_gti_ignition_extra)
  - Spark 900 ACE (1037xxx / 10SW011328 / 10SW039116): 4 skenera, 52 mape
- `core/map_editor.py` — MapEditor: read_map/read_raw, write_cell/write_map (auto-mirror sync), backup/restore; validacija raw_min/raw_max; write_rev_limit_scalar/write_rev_limit_row
- `core/dtc.py` — DTC_REGISTRY: **121 kod** (111 P-kodova ECM + 10 U16Ax CAN timeout); Enable tablica @ 0x021080–0x0210BD (slot 0–61); Mapping tablica @ 0x0239B4; Mirror offset=0x0366 (ori_300); DtcScanner dinamički detektira offset; DtcEngine: dtc_off / dtc_on / dtc_off_all / disable_all_monitoring; DTC OFF blokiran za Spark/rxtx_260 (single-storage arhitektura)
- `core/checksum.py` — CRC32-HDLC (poly=0xEDB88320, reflected); BOOT [0x0000–0x7EFF] = 0x7F00 bajta; CS @ 0x30 (BE u32) ukljucen u izracun (closed-form); residua=0x6E23044F; CODE promjene NE zahtijevaju CS promjenu; compute_new_cs() = MITM inverzni CRC
- `core/can_decoder.py` — CanDecoder; diagnostic bus 500kbps IDs: 0x0102 (RPM×0.25+coolant), 0x0103 (DTC+state), 0x0110 (temp), 0x0316 (EOT), 0x0342 (MUX: ECT/MAP/MAT), 0x0516 (HW ID), 0x04CD (DESS); cluster bus 250kbps: 0x0108 (RPM), 0x012C (engine hours), 0x017C (DTC), 0x013C (flags); XOR checksum byte[7]=XOR(byte[0..6]); rolling counter byte[6]=0x00–0x0F; CAN TX table @ 0x0433BC
- `core/eeprom.py` — EepromParser/EepromEditor: EEPROM_SIZE=32768; HW 064 (MPEM 10375500xx): ODO @ 0x0562, backup 0x0D62/0x1562; HW 063 (MPEM 10375258xx): max(0x0562, 0x4562); HW 062 (MPEM 10375091/92xx): rotacija 0x5062→0x4562→0x1062; Hull ID @ 0x0082, ECU serial @ 0x004D, MPEM SW @ 0x0032, prog count @ 0x004C; ODO u minutama (u16 LE)
- `tools/can_sniffer.py` — IXXAT VCI4 USB-to-CAN, interface='ixxat', monitor=True (pasivni, listen-only, radi paralelno s BUDS2); default 500kbps (diagnostic), --bitrate 250000 za cluster; CSV log; statistika po ID-u (freq, checksum errors, rolling counter jumps)
- `tools/did_map.py` — UDS SID 0x22 (ReadDataByIdentifier) + KWP SID 0x21 (ReadDataByLocalId); 34 DID-a u livedata ciklusu; 5 vraća NRC 0x12 (unsupported na Rotax ACE 1630); temp: raw/2-40=°C; lambda: raw/128=normalized; pressure: raw×0.5=kPa
- `ui/main_window.py` — PyQt6 trostupicastni layout: Map Library (stablo+search) | Map Table + Hex + Log | Tab panel [Cell/Map/ECU]; uvozi: core.dtc_descriptions, core.safety_validator, core.map_differ, ui.calculator_widget, ui.diff_viewer, ui.eeprom_widget, ui.can_network_widget, ui.can_logger_widget

## DTC
- DTC_REGISTRY: 121 kod — 111 P-kodova (ECM) + 10 U16Ax (CAN timeout 0xD6A1–0xD6AB)
- Code storage: main 0x021700–0x0218FF + mirror (main+0x0366), LE u16
- Enable tablica @ 0x021080 (slot 0–61, 0x06=aktivan, 0x05=djelomičan, 0x04=upozorenje, 0x00=isključen)
- Mapping @ 0x0239B4: (code_addr - 0x021700) / 2 → enable_slot
- U16Ax (0xD6A1/A2/A3/A5/A8/AB): dijele en_addr 0x0210B9 (slot 57) s P0231 (fuel pump)
- Blokiran za Spark (single-storage) i rxtx_260

## CAN
- Diagnostic bus: 500kbps, OBD konektor / IXXAT bench — IDs: 0x0102, 0x0103, 0x0110, 0x0316, 0x0342, 0x0516, 0x04CD
- Cluster bus: 250kbps, Delphi 20-pin J1 — ECU TX @ 0x0433BC: 0x015B/0x015C/0x0148/0x013C/0x0138/0x0108/0x0214/0x012C/0x0110/0x017C
- SW scalar u byte[4] od 0x0102: 0x14=300hp (10SW066726), 0x0E=230hp (10SW053727), 0x12=130/170hp (10SW053729)
- RIDING_MODES: 0x01=SPORT, 0x02=ECO, 0x03=CRUISE, 0x06=SKI, 0x07=SLOW SPEED, 0x08=DOCK, 0x0F=LIMP HOME, 0x14=KEY MODE

## EEPROM
- HW 064 (1037550003): 130/170/230/300hp ACE 1630 + GTI90; ODO prim @ 0x0562, backup 0x0D62, mirror 0x1562, stari 0x4562, old-064 0x0490
- HW 063 (1037525858): Spark 90; ODO = max(0x0562, 0x4562), fallback 0x0DE2
- HW 062 (1037509210): 4TEC 1503 130/155/230/260hp; ODO rotacija 0x5062→0x4562→0x1062
- Detekcija HW tipa iz MPEM SW @ 0x0032 (prefiks 10375500/10375258/10375091-92)
- NEMA checksuma — direktne izmjene; sigurna polja: hull_id, dealer_name, datumi, prog_count

## Pravila
- Svi importi su APSOLUTNI (from core.engine, ne from ..core.engine)
- Pokretati testove iz me_suite root foldera
- CAL regija je read-only — ne pisati tamo!
- **GitHub je backup — NIKADA ne commitati niti pushati na GitHub. To radi isključivo korisnik.**

## Work Log — OBAVEZNO
- **UVIJEK ažurirati `work_log.md` nakon svake bitne promjene ili otkrića!**
- Format unosa: `## YYYY-MM-DD HH:MM — Kratki opis`
- Uključiti: što je napravljeno, koji fajlovi promijenjeni, ključni rezultati
- Ažurirati i na početku sesije (što se nastavlja) i na kraju (što je dovršeno)

## Chat Log — OBAVEZNO
- **UVIJEK dodati unos u `chat_log.md` nakon SVAKE korisnikove poruke!**
- Format unosa:
```
---
**[datum i vrijeme]**
👤 [korisnikova poruka — doslovno, cijela]
🤖 [odgovor — MAKSIMALNO 2-3 rečenice, samo suština]

---
```
- Ne brisati stare unose, samo dodavati na kraj
- work_log = tehnički detalji promjena; chat_log = history razgovora i odluka
