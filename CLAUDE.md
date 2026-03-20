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
- Rev limiter (stvarni, period-encoded LE u16): 0x028E96 (1630 SC/NA), 0x028E94 (2018 SW, 2B ranije)
  - 300hp SC=8223 RPM, 230hp SC=8168 RPM, 130/170hp NA=8750 RPM (NA viši jer bez SC tlaka)
  - Spark 900 @ 0x028E34 = 5120t = 8081 RPM; GTI90 @ 0x028E7C = 5875t = 7043 RPM
  - **UPOZORENJE**: 0x02B72A/0x02B73E su IGN DATA (u8 bajtovi, 0x22=25.5°BTDC), NISU rev limiteri!
- Ignition (1630 ACE): IGN_BASE=0x02B730, stride=144B, 19 mapa, 12×12 u8, scale=0.75°/bit
  - #00-#07 osnovna; #08-#09 knock trim; #10-#15 aux A/B/SC; #16-#17 extended (NPRo); #18 uvjetna/fallback
  - **2018 SW (10SW023910)**: IGN_BASE=0x02B72C (4B ranije!), 2× ignition set (drugačiji layout)
- Ignition (Spark 900 ACE): base ≈0x026A50, stride 144B, 12×12 u8 — **NIJE 0x02B730!**
  - IGN A @ 0x026A76, X-os RPM @ 0x026A1E, Y-os load @ 0x0269AF; B/B2 dijele iste osi
  - IGN C (3×9×8 u16LE): RPM X-os @ 0x027C7C, load Y-os @ 0x027D36
- Injection (1630 ACE): 0x02436C = **injector linearization curve** (1D kao 16×12 blok, svaki red = ista Q15 vrijednost ponavljana 12×)
  - Vrijednosti (Q15): [0..2.0] — duty breakpoints od idle do max open; **SC==NA** (isti injektori)
  - "Mirror" @ 0x0244EC je DRUGAČIJA tablica (2 zasebne karakteristike, ne identična kopija)
  - **NEMA prave 2D fuel mape na 0x02436C** — to je LINEARIZATION (1D lookup, svaki red ponavlja Q15)
  - **0x02436C identičan za 130/170/230/300hp** — snaga injektora se ne razlikuje kroz ovu krivulju
  - **Prava 2D fuel mapa @ 0x022066** (12×16 Q15) — RAZLICITA po snagama! (potvrđeno 2026-03-20)
- Injection (1630 ACE 2019+): **0x022066 = prava 2D fuel mapa** (12×16 u16 LE Q15) — POTVRĐENO 2026-03-20
  - X-os @ 0x022046 (16pt RPM, raw/4 = RPM, 1400–8200): 5600,7000,8000,...,32800
  - Y-os @ 0x02202E (12pt load, Q14 normalized): 1067,1280,...,8960 (6.5%–54.7%)
  - Header: 0x02202A=nRows(12), 0x02202C=nCols(16), zatim Y-os, X-os, data
  - Razlikuje se po snagama: 300hp max=0.944, 230hp=0.785, 130/170hp=0.524 Q15
  - 130hp==170hp identični; **NEMA mirrora** (za razliku od torque/lambda)
  - Identična u 2018/2019/2021 za isti SW — nema tuning razlike između godišta
- Injection (GTI 1503 + GTI90 2020-21): 0x022066 = isti format i adresa, SC vs NA razlikuju
  - 1503 i GTI90 NEMAJU 0x02436C layout! 2018/1630 ACE (10SW023910) ima OBJE @ 0x022066 + 0x02436C
- Injection (Spark 900 ACE): 30×20 @ 0x0222BE, X-os load @ 0x02225A, Y-os RPM @ 0x022282, mirror +0x518
- Torque (1630 ACE): main 0x02A0D8 + mirror 0x02A5F0 (+0x518) — 16×16 u16 BE Q8
  - Fizička krivulja momenta @ 0x029FD4: 30pt u16LE /100=Nm; SC max=340Nm, NA max=332Nm
- Torque (Spark 900 ACE): 30×20 @ 0x027D9A, mirror 0x0282B2 (+0x518), BE Q8
- Lambda (1630 ACE): main 0x0266F0 + mirror 0x026C08 (+0x518) — 12×18 u16 LE Q15
  - GTI90: main @ 0x0266F0 = flat 0.984 (pasivna), mirror @ 0x026C08 = aktivna (0.90–1.02)
- Lambda adapt baza: 0x0268A0 — 12×18 u16 LE Q15 (85% conf.)
- Lambda trim: 0x026DB8 — 12×18 u16 LE Q15
- Lambda bias: 0x0265D6 — 1×141 u16 LE Q15
- SC correction: 0x02220E — 9×7 u16 LE Q14 (NA=flat 16384=1.0, SC aktivno)
- SC boost factor: 0x025DF8 — 1×40 u16 LE Q14 (=1.224, +22%)
- SC bypass: 3 kopije @ 0x020534 (shadow), 0x0205A8 (active), 0x029993 (extra)
  - NPRo mijenja samo 0x0205A8 i 0x029993; opcodes: 300hp=0x2626, 230hp=0x1F1F, 170/130hp=0x1E1E
- Temp fuel correction: 0x025E50 — 1×156 u16 LE Q14
- Thermal enrichment: 0x02AA42 — 8×7 u16 LE /64=% (CTS 80–150°C)
- Eff correction (KFWIRKBA sub): 0x0259DC — **14×10 u8 /128=1.0** (NE 7×10 u16 Q15!)
  - Y-os 14pt lambda @ 0x0259C4, X-os 10pt lambda @ 0x0259D2 (oba u8/100)
- Lambda eff (KFWIRKBA): 0x02AE5E — 41×18 u16 LE Q15; GTI90 aktivan (0.51–0.71), SC bypass (sve iste vrijednosti)
- Overtemp lambda: 0x025ADA — 1×63 u16 LE Q15 (0xFFFF=SC bypass)
- Neutral corr: 0x025B58 — 1×63 u16 LE Q14
- Ign correction 2D: 0x022374 — 8×8 u8
- Accel enrichment: 0x028059 — 5×5 u16 LE Q14 (kompleksan format: 1B global + 5 sub-tablica)
- Start injection: 0x025CDC — 1×6 u16 LE + 6-pt osa
- Deadtime: 0x0258AA (ne 0x025900!) — 10×14 u16 LE; X-os trajanje, Y-os temp °C (read-only)
- Decel RPM ramp (DFCO): 0x028C30 — 16×11 u16 LE (stride 22B, 80% conf.)
- Knock params: 0x0256F8 — 52 u16 (104B); ispravak s prijašnjih 24
- KFPED (drive-by-wire): header 0x029528, data 0x029548 — 10×20 u8; mirror 0x029630
  - SC X-os = MAP kPa gauge (signed u8, boost/vakuum); NA X-os = pedal° [0..70]
- 0x02B380: 36×u16 lookup tablica koja skalira po snazi — NE tunabilna mapa
- 0x012C80: 96B embedded konstante s 0xDEADBEEF markerom — READ-ONLY
- CAL regija 0x060000–0x15FFFF = TriCore bytekod — NE PISATI!

## SW Varijante — ključne razlike
- **10SW023910** (2018 300hp): IGN_BASE=0x02B72C, rev limiter @0x028E94, 2× injection set (GTI 0x022066 + std 0x02436C), 2× ignition set; CAN TX @0x03DF1E
- **10SW040039** (2019 300hp = NPRo base): NPRo NE mijenja SW string; diff: BOOT=140B, CODE=7087B, CAL=169912B (4482B CODE, 83 bloka)
- **10SW053729**: 130hp == 170hp (0 razlika, isti SW); **0x02436C (linearization) identičan 300hp; 0x022066 fuel mapa RAZLICITA!**
- **10SW053774** (GTI90): ign=0x02B730 (=1630!), inj=0x022066 (GTI format), DTC @0x0217EE, rev=7043RPM
- **10SW039116** (Spark 900): ign≈0x026A50, inj=0x0222BE (30×20), DTC NIJE na 0x0217EE, rev=8081RPM; 2019=2020=2021 MD5 identični
- **10SW011328** (Spark 2016/2018): iste mape adrese kao 2019+, samo drugačija kalibracija

## Komande
- Pokreni: `python main.py` (iz me_suite foldera)
- Testovi: `python test/test_core.py`

## Struktura
- `core/engine.py` — load/save, read/write primitivi (u8/u16 BE/LE/i16); FILE_SIZE=0x178000; BOOT=0x0000–0x7EFF, CODE=0x010000–0x05FFFF, CAL=0x060000–0x15FFFF; SW @ 0x001A (10B), MCU string @ 0x01FE00
- `core/map_finder.py` — MapFinder.find_all() s detekcijom ECU tipa:
  - 300hp SC (10SWxxxxxx): 33 skenera → **56 mapa** (ne 54! — ispravak 2026-03-20)
  - GTI/NA varijanta: +2 skenera (_scan_gti_injection + _scan_gti_ignition_extra)
  - Spark 900 ACE (1037xxx / 10SW011328 / 10SW039116): 4 skenera, **52 mape** (2 false positive uklonjeni)
  - GTI90 (10SW053774): **60 mapa**; 1503 GTI: **59–62 mapa** (ovisno o SW)
- `core/map_editor.py` — MapEditor: read_map/read_raw, write_cell/write_map (auto-mirror sync), backup/restore; validacija raw_min/raw_max; write_rev_limit_scalar/write_rev_limit_row
- `core/dtc.py` — DTC_REGISTRY: **121 kod** (111 P-kodova ECM + 10 U16Ax CAN timeout); Enable tablica @ 0x021080–0x0210BD (slot 0–61); Mapping tablica @ 0x0239B4; Mirror offset=0x0366 (ori_300); DtcScanner dinamički detektira offset; DtcEngine: dtc_off / dtc_on / dtc_off_all / disable_all_monitoring; DTC OFF blokiran za Spark/rxtx_260 (single-storage arhitektura)
- `core/checksum.py` — CRC32-HDLC (poly=0xEDB88320, reflected); BOOT [0x0000–0x7EFF] = 0x7F00 bajta; CS @ 0x30 (BE u32) uključen u izračun (closed-form); residua=0x6E23044F; CODE promjene NE zahtijevaju CS promjenu; compute_new_cs() = MITM inverzni CRC
- `core/can_decoder.py` — CanDecoder; diagnostic bus 500kbps IDs: 0x0102 (RPM×0.25+coolant), 0x0103 (DTC+state), 0x0110 (temp), 0x0316 (EOT), 0x0342 (MUX: ECT/MAP/MAT), 0x0516 (HW ID), 0x04CD (DESS); cluster bus 250kbps: CAN_CLUSTER_PRI=0x0578 (ECU→SAT 267ms), CAN_CLUSTER_SEC=0x0400 (311ms), CAN_CLUSTER_GTS=0x0408 (267ms, svi SW); CAN_SAT_HEARTBEAT=0x0186, CAN_SAT_CRITICAL=0x01CD, CAN_SAT_DESS=0x04CD; XOR checksum byte[7]=XOR(byte[0..6]); rolling counter byte[6]=0x00–0x0F
- `core/eeprom.py` — EepromParser/EepromEditor: EEPROM_SIZE=32768; HW 064 (MPEM 10375500xx): ODO @ 0x0562, backup 0x0D62/0x1562; HW 063 (MPEM 10375258xx): max(0x0562, 0x4562); HW 062 (MPEM 10375091/92xx): rotacija 0x5062→0x4562→0x1062; Hull ID @ 0x0082, ECU serial @ 0x004D, MPEM SW @ 0x0032, prog count @ 0x004C; ODO u minutama (u16 LE); set_odo_raw() piše u sve relevantne ODO adrese
- `tools/can_sniffer.py` — IXXAT VCI4 USB-to-CAN, interface='ixxat', monitor=True (pasivni, listen-only); default 500kbps, --bitrate 250000 za cluster; CSV log; statistika po ID-u (freq, checksum errors, rolling counter jumps); koristi CanDecoder.decode()
- `tools/did_map.py` — UDS SID 0x22 (ReadDataByIdentifier) + KWP SID 0x21 (ReadDataByLocalId); 34 DID-a u livedata ciklusu; 5 vraća NRC 0x12; temp: raw/2-40=°C; lambda: raw/128; pressure: raw×0.5=kPa
- `ui/main_window.py` — PyQt6 trostupičasti layout: Map Library | Map Table + Hex + Log | Tab panel; dark theme #111113, accent #4FC3F7
  - Tabovi: Map Editor | DTC Off | Diff | Map Diff | Kalkulator | EEPROM | CAN Network | CAN Logger | CAN Live | Vizualizacija | Mape
  - Novi UI widgeti (importirani, dijelom integrirani):
- `core/safety_validator.py` — ValidationResult (OK/WARNING/ERROR); limiti: ign <43.5°, lambda >0.75, torque <160%, rev <9000rpm
- `core/map_differ.py` — MapDiffer.compare_all_maps(); CellDiff/MapDiff; diff report je stub
- `ui/map_visualizer.py` — MapHeatWidget (JET paleta, RPM/Load headeri, klik signal); MapDeltaWidget (delta A vs B); MapMiniPreview (thumbnail 100×60)
- `ui/map_editor_widget.py` — MapEditorWidget: UndoStack (deque, max 20), inline edit, paste TSV/Excel, validacija; **importiran ali nije instanciran u main_window.py!**
- `ui/can_live_widget.py` — CanLivePanel: CanWorker(QThread) + dashboard (RPM/coolant/hours/DTC) + CAN ID tablica + hex log; IXXAT VCI4 500kbps
- `ui/calculator_widget.py` — AFR↔lambda, boost, timing, injection kalkulatori; nema live link s otvorenom mapom
- `ui/diff_viewer.py` — MapDiffWidget: heat table delta; sorting/filter stub; tab skriven dok nije aktivna usporedba
- `ui/eeprom_widget.py` — EepromWidget: read svih polja + write hull_id/dealer; ODO set NIJE spojen (postoji u core)
- `ui/can_network_widget.py` — CAN bus topologija (statična); nema live animacije
- `ui/can_logger_widget.py` — CSV logging (timestamp/ID/data_hex/decoded); gauge refresh spor

## DTC
- DTC_REGISTRY: 121 kod — 111 P-kodova (ECM) + 10 U16Ax (CAN timeout 0xD6A1–0xD6AB)
- Code storage: main 0x021700–0x0218FF + mirror (main+0x0366), LE u16
- Enable tablica @ 0x021080 (slot 0–61, 0x06=aktivan, 0x05=djelomičan, 0x04=upozorenje, 0x00=isključen)
- Mapping @ 0x0239B4: (code_addr - 0x021700) / 2 → enable_slot; P0231 stvarna adresa: 0x0217BC (idx=94)
- U16Ax (0xD6A1/A2/A3/A5/A8/AB): dijele en_addr 0x0210B9 (slot 57) s P0231 (fuel pump)
- U16A4/A7/A9/AA: en_addr 0x021083 (slot 3) — već disabled (0x00)
- GTI90 DTC storage @ 0x0217EE; Spark 900 DTC NIJE na ovoj adresi (drugačija arhitektura)
- Blokiran za Spark (single-storage) i rxtx_260

## CAN
- Diagnostic bus: 500kbps, OBD konektor / IXXAT bench — IDs: 0x0102, 0x0103, 0x0110, 0x0316, 0x0342, 0x0516, 0x04CD
- Cluster bus: 250kbps, Delphi 20-pin J1 — ECU→SAT: 0x0578 (267ms), 0x0400 (311ms), 0x0408; SAT→ECU: 0x0186, 0x01CD
- **CAN TX tablica @ 0x03DF0C (2019+) / 0x03DF1E (2018)** — ISPRAVKA: 0x0433BC je period tablica (LE16 ms vrijednosti), NE TX ID tablica!
- SAT TX IDs (iz SAT firmware init tablice): 0x0186–0x019B, 0x01CD (GTX/GTI), 0x4CD (DESS keepalive 1Hz)
- SW scalar u byte[4] od 0x0102: 0x14=300hp (10SW066726), 0x0E=230hp (10SW053727), 0x12=130/170hp (10SW053729)
- RIDING_MODES: 0x01=SPORT, 0x02=ECO, 0x03=CRUISE, 0x06=SKI, 0x07=SLOW SPEED, 0x08=DOCK, 0x0F=LIMP HOME, 0x14=KEY MODE
- XOR checksum byte[7]=XOR(byte[0..6]) vrijedi za 0x102/0x103/0x110/0x122/0x516; ostali nemaju CS

## EEPROM
- HW 064 (1037550003): 130/170/230/300hp ACE 1630 + GTI90; ODO prim @ 0x0562, backup 0x0D62, mirror 0x1562, stari 0x4562, old-064 0x0490
- HW 063 (1037525858): Spark 90; ODO = max(0x0562, 0x4562), fallback 0x0DE2
- HW 062 (1037509210): 4TEC 1503 130/155/230/260hp; ODO rotacija 0x5062→0x4562→0x1062
- Detekcija HW tipa iz MPEM SW @ 0x0032 (prefiks 10375500/10375258/10375091-92)
- NEMA checksuma — direktne izmjene; sigurna polja: hull_id, dealer_name, datumi, prog_count
- Audit: `062/062 1-4` = stvarno HW 063 (u krivom folderu); `064 85-31 ex063` = legitimna 063→064 konverzija

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
