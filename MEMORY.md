# ME17Suite — Memorija projekta

## Sljedeća sesija
- Running engine CAN log strategija: kratki WOT pulsevi u plivajućem dock-u, IXXAT na 250k (Delphi J1!), bilježiti DIDs u vodi
- UI + grafika + CAN prikazi — pro level polish — vidjeti project_next_session.md
- ~~Lambda adapt 2016 gen 1503~~ — **ne postoji** (potvrdeno 2026-03-21)
- ~~2017 gen 012999~~ — **riješeno**: 28 mapa

## Cluster projekt — ključni nalaz (2026-03-21)
- **JEDNA CAN mreza** @ 250kbps na Delphi J1 pin2/3 (ne dvije odvojene!)
- BUDS2 MPI VCI + IXXAT sniffer + ECU + SAT = SVI na istom 250kbps busu
- OBD konektor 500kbps = nije korišten u ovom projektu
- ESP32 firmware: **CAN_BITRATE = 250kbps** obavezno
- VP230 (WCMCU-230): Rs=10kΩ→GND (slope control, TX aktivan), ne Rs=VCC bug
- TX/RX spajanje za CAN: **NE križa se** (MCU_TX→modul_TX direktno)

## Korisničke preference i napomene
- BRP manuals: Tech Specs su **zadnjih 20% stranica** — vidjeti feedback_manual_search.md

## Korisničke preference
- Jezik: **isključivo Hrvatski** — nikada srpski ni bosanski. Koristiti hrvatska jezična rješenja (npr. "pronađen" ne "pronašao se", "nije" ne "nema", itd.)
- Dozvole: **Sve dopušteno** — ne pitati za dozvole, raditi autonomno u me_suite folderu i šire
- Permission dialozi: korisnik ne želi NIKAKVE approve/deny dialoge — vidjeti feedback_permissions.md
- GitHub: **NIKADA ne commitati niti pushati** — to radi isključivo korisnik
- Stil: koncizan, tehnički, bez nepotrebnog objašnjavanja
- work_log.md: **obavezno datum + HH:MM** uz svaki unos

## Projekt
- Lokacija: `C:\Users\SeaDoo\Desktop\me_suite`
- ECU: Bosch ME17.8.5, MCU: Infineon TC1762 (TriCore, Little Endian)
- Stack: Python 3.14 + PyQt6
- **Kontekst**: Profesionalni servisni/tuning alat. Svaki .bin u dumps/ = fizički ECU koji je korisnik osobno čitao (BUDS2 + MultiProg). Baza je 100% vlastita, nisu internet fajlovi.
- **FOKUS ALATA: samo 10SW format** (2016–2022+). Decimal (1037xxxxxx) i Siemens MSE 3.7 = samo dokumentacija. Ionako svi stariji motori rade s novijim 10SW ECU SW-om.
- **BUDS**: 2016 = oba BUDS; BUDS2 nema backup za pre-2016; 2017+ = BUDS2; stariji dostupni kroz DIUS4 (nije prioritet)
- **ECU kronologija**: Siemens MSE 3.7 (2002–2011) → Bosch ME17.8.5 (2008–2022+, 10SW format od 2016) → **BRP "XCU"** (2024+ za 130/170hp NA; Spark/230hp/300hp SC ostaju ME17.8.5 u 2024!)
- **XCU** = novi ECU BRP naziva, 3-cifreni pin format (101–256), ~48 pinova, fizički nekompatibilan harness; **325hp SC**: ECM relay u dijagramu ali XCU fuse box — dvosmisleno, ME17 adrese vjerojatno ne rade
- **XCU/325hp scope:** izvan ME17Suite — čeka se xhorse protokol za read/write
- **2016 gen (10SW0007xx/004675)**: stariji CODE layout, neke adrese rade, neke ne — ograničena podrška, označiti u UI-u
- **2017 gen (10SW012999)**: parcijalna migracija — SC bypass/ign/rev/lambda rade na 2018 adresama; boost/temp_fuel/lambda_trim na drugačijim adresama
- **Korisnik je praktičar** — radi servis i tuning na realnim strojevima, ne akademski projekt

## SW verzije i motori

| SW ID | Motor / Model | Mape | Napomena |
|-------|--------------|------|---------|
| 10SW082806 | **300hp SC 2022 ORI** | **14** | VERIFICIRAN 2026-03-21; **ČISTI ORI** (korisnik potvrdio); CODE layout potpuno novi — 236KB diff vs 2021; sve mape na novim adresama; SC bypass shadow/active = 0x2626 jedine potvrđene adrese; **PRIJELAZNA platforma za 2023** (novi ECU, 325hp, blow-off, E-fuel pressure); MapFinder treba redizajn za 2022 |
| 10SW066726 | 300hp SC 2021 ORI | **57** | +1 mapa: 2D fuel @ 0x022066 (2026-03-20) |
| 10SW054296 | 300hp SC 2020 ORI | 57 | isti layout kao 2021 |
| 10SW023910 | **300hp SC 2018 ORI** | **63** | 2× injection (0x022066 + 0x02436C) + 2× ignition seti |
| 10SW040039 | **2019 stock + NPRo base** | **57** | NPRo NE mijenja SW string! |
| 10SW053727 | 230hp SC 2020-2021 | **56** | fuel @ 0x022066 max Q15=0.785 |
| 10SW053729 | 130/170hp NA 2020-2021 | **64** | ISTI SW, fuel @ 0x022066 max Q15=0.524 |
| 10SW053774 | GTI 90 2020-2021 | **62** | fuel @ 0x022066 max Q15=0.572 |
| 10SW039116 | Spark 90 2019-2021 | **54** | MD5 identičan 2019=2020=2021! Ign @ 0x026A50 (NE 0x02B730!), lambda @ 0x024EC4 |
| 10SW011328 | Spark 90 2016/2018 | ~54 | drugačije kalibracije ali iste adrese kao 2019+ |
| 1037544876 | NPRo Spark STG2 | ~52 | decimalni SW format |
| 10SW025021 | GTI **230hp** 1503 **2018 SC** | **59** | NOVI — SC s fizičkim ventilom @ 0x020534; ~19KB razlika od NA (10SW025022) |
| 10SW025022 | GTI 130hp 1503 **2018 v1** | **60** | SC bypass kod aktivan (bez fizičkog ventila); 130v1=155v1 identični |
| 10SW025752 | GTI 130/155hp 1503 **2018 v2** | **60** | 155hp tune; 130v2=155v2 identični; razlika v1→v2: 2901B (ign+lambda+inj) |
| 10SW040008 | GTI 130/155/230hp 1503 2019 | 59 | ISTI SW za sve snage! |
| 10SW040962 | GTI 130hp 1503 2020 | 59 | |
| 10SW012999 | GTI **230hp SC 2017** 4TEC 1503 | **28** | RIJEŠENO 2026-03-21; -0x2AA offset SC mape implementirane: lambda(0x026446), adapt(0x0265F6), trim(0x026B0E), boost(0x025B4E), temp_fuel(0x025BA6), torque mirror(0x029BC0=main-0x518) |
| 10SW000778 | **RXT-X 260hp SC 2016** | ~24 | VERIFICIRAN 2026-03-20; stariji ME17 format (CODE adrese drugačije od 2018+); SC bypass **0x2020** @ 0x012C60; 1330B razlike od 1037524060 |
| 1037524060 | RXT-X 260hp SC ~2015 | ~24 | Decimal SW format; isti stariji ME17 format kao 10SW000778; 1330B razlike (susjedne SW revizije); **nije Siemens MSE 3.7** (VME17+BOSCH potvrđen) |
| 10SW004675 | **300hp SC 2016 ORI** | ~24 | VERIFICIRAN 2026-03-20; fuel NIJE @ 0x022066 (2016 drugačiji CODE layout!); rev=8072RPM; SC bypass=**0x3333** (ne 0x2626!) |
| 10SW004672 | **300hp SC 2016/17** | ~24 | VERIFICIRAN 2026-03-20; **2016 gen layout**, 1265B razlika od 004675 (susjedne revizije!); rev=8072RPM; SC bypass 0x3333 @ 0x0205A8; 0x2020 @ 0x012C60; boost @ 0x025B4E=20046; fuel garbage @ 0x022066; torque identičan 004675; u dumps/2017/ ali 2016 gen SW |

## Dumps inventar
- `_materijali/dumps/YYYY/{1630ace,900ace,4tec1503}/` — 22 dump, svi valid
  - **2016**: 1630ace/300(10SW004675) + 4tec1503/260(10SW000778) — oba VERIFICIRANA; stariji ME17 format (drugačije CODE adrese)
  - **2017**: 1630ace/300(10SW004672) + 4tec1503/230(10SW012999) + 4tec1503/260(10SW012502); 004672 je 2016 gen layout (1265B razlika od 004675)
  - 2018: 1630ace/300(10SW023910), spark90(10SW011328), spark_stg2(1037544876), 1503×5(130v1+v2+155v1+v2+230)
  - 2019: 300(10SW040039), spark90(10SW039116), 1503×3(10SW040008)
  - 2020: 1630ace×5+stg2, 900ace×2, 1503×1(10SW040962)
  - 2021: 1630ace×4, 900ace×2
  - **2022**: 1630ace/300(10SW082806) — **ČISTI ORI** (korisnik potvrdio); CODE layout promijenjen vs 2021; MapFinder: 14 mapa
- **NEMA**: 2018/1630ace — to godište nije u dumps/
- **Planirani**: 2017 300hp, 2016 260hp, 2017 260hp, **2022 ORI 300hp** — još nisu dumpani
- 2018/4tec1503: 130v1=155v1=10SW025022, 130v2=155v2=10SW025752, 230=10SW025021 (SC)
- **unknow folder**: WinOLS KP(10974)=Spark900 mape, KP(Rxp260)=Bosch param baza (bez ECU adresa), 2×OLS(SW=1037524060), HPT(AES-enkr, neupotrebljiv)

## EEPROM (32KB)
- HW 064 (1037550003): 130/170/230/300hp ACE 1630 + GTI90 2016-2022+
- HW 063 (1037525858): Spark 90 2014-2019
- HW 062 (1037509210): 130/155/230/260hp 4TEC 1503 2012-2015
- ODO primary adrese: 064=0x0562, 063=max(0x4562,0x0562), 062=rotacija(0x5062→0x4562→0x1062)
- Upozorenje: "NEKI 063 SU NEKIM NABADANJEM ZAVRŠILI KAO 064!" — detekcija: hw_type≠folder_prefix
- Folder format: `06x HHH-MM` gdje HHH=sati, MM=minute motora
- **Audit 2026-03-18**: `062/062 1-4` je zapravo HW 063 (u krivom folderu); `064 85-31 ex063` je legitimna 063→064 konverzija; `alen oct25` = nepoznat prefiks `10374006`

## Mape — pouzdanost za tuning
- **Ignition** (19 mapa, sve identificirane): POUZDANO — #00-#07 base, #08-#09 knock, #10-#15 aux (A/B/SC), #16-#17 extended, #18 conditional/fallback
- **Injection/gorivo** (~95%): main @ 0x02436C potvrđen, 0x024700 = dio lambda zaštite @ 0x02469C (riješeno)
- **Lambda/AFR** (10 mapa): POUZDANO — +lambda adapt @0x0268A0 (+85%), +KFWIRKBA TODO uklonjen (GTI90 aktivan 0.51-0.71, SC bypass)
- **DTC OFF**: POUZDANO — **121 kodova** (111 P + 10 U16Ax), 3 SW varijante; U16Ax dijele slot s P0231
- **CAL regija (0x060000+)**: TriCore bytekod — NE PISATI!
- **CODE mape**: promjene NE zahtijevaju promjenu checksuma
- **FWM (vozačev zahtjev momenta)** @ 0x02A7F0: **95% conf.** — DID 0x213B→mapa→DID 0x2103 potvrđeno; SC 300hp=75-98% (limiting), NA 130hp=100-116% (boost)
- **KFWIRKBA tranzijentni (4 uvjeta)** @ 0x0275FD: **80% conf.** — 4 kopije stride 290B; NPRo mijenja C0/C1 → agresivniji throttle odaziv (korisnik potvrdio)
- **Lambda zaštita — pragovi** @ 0x02B378: **95% conf.** — DID 0x2107/0x2158=0xFFFF bench; NPRo STG2=sve 0xFFFF (bypass)
- **KFZW2 (paljenje za moment)** @ 0x022374: **80% conf.** — DID 0x2142 "Desired Ignition Angle After Torque Intervention" potvrđuje lanac

## Ključni tehnički nalazi

### Checksumi i memory layout
- Checksum: CRC32-HDLC, regija 0x0000-0x7EFF (BOOT), CS @ 0x30 uključen, residua=0x6E23044F
- BOOT = 0x0000–0x7EFF | CODE = 0x010000–0x05FFFF | CAL = 0x060000–0x15FFFF
- CODE promjene NE zahtijevaju promjenu CS; BOOT/SW promjena zahtijeva CS + RSA potpis (Bosch ključ)

### Rev limiter (period encoding)
- Formula: `RPM = 40MHz × 60 / (ticks × 58)` (60-2 kotačić, 3-cil)
- **Binarni ECU limiti** (NE manual WOT RPM): 300hp SC=5072t→8158, **230hp SC (1630)=5072t→8158 (=300hp!)**, 130/170hp NA=5243t→7892 (ISTI SW=ISTI limit!), Spark=5120t→**8082**, 1503 GTI: 2018=7664, 2019=7892, 2017=8072, GTI90=5875t→**7043** (potvrđeno binarno)
- **2016 gen 1503 rev limiter** (VERIFICIRANO 2026-03-21): `0x026E1E` = 5126t = **8072 RPM**; mirror @ `0x026D82` (−0x9C); vrijedi za 10SW000776/000778 i 10SW012502 (2017 260hp!); isti limit za 215hp i 260hp; offset vs 1630 ACE = −0x2076
- **GTI90 SC bypass = 0x1C1B** @ 0x0205A8 (nova potvrda 2026-03-21)
- **SC bypass discrepancy**: 2018/2019 ORI: shadow (0x020534)=0x2626 ali active (0x0205A8)=**0x3333**; 2020+ ORI: obje adrese=0x2626
- **Manual WOT RPM** (dijagnostički, u vodi) = viši od ECU cut; bez opterećenja svi vrte više
- Spark stock u vodi ≈7900 RPM (propeler-limitirano); NPRo diže snagu → 8150 RPM (isti ECU limit)
- **Throttle body**: 62mm na svim motorima 2012+ (1630 ACE, 1503, isto 62mm — potvrđeno korisnikom)

### Identificirane CODE regije (finalni status)
- 0x024700 = dio lambda zaštite @ 0x02469C (12×13 Q15) — **RIJEŠENO**
- 0x0268A0 = lambda adaptacijska baza (12×18 Q15) — **85% conf.**
- 0x028C30 = DFCO RPM ramp (16×11 u16 LE, stride 22B) — **90% conf.**
- 0x02A7F0 = FWM vozačev zahtjev momenta (16×16 BE Q8) — **95% conf.**
- 0x0275FD = KFWIRKBA tranzijentni (16×16 u8, 4 kopije) — **80% conf.**
- 0x02B378 = Lambda zaštita pragovi (79 u16 LE Q15) — **95% conf.**
- 0x022374 = KFZW2 paljenje za moment (8×8 u8) — **80% conf.**
- 0x012C80: ~128B embedded cal u ranom CODE-u (NPRo mijenja) — READ-ONLY
- 0x02B380: ~72B pred ignition tablicama — NE tunabilna

### CAN bus
- **CAN ID 0x122**: 10ms period, XOR checksum, bytes[4:6]=engine hours (0x0B5E=2910h bench) — **IBR modul hipoteza**
- Payload potvrđen iz ECU CODE: RPM=byte[1:3]×0.25 | temp=byte[1]-40°C | hours=u32/3600 | DTC byte[0]=count
- SAT firmware (325KB ×3): enkriptiran (entropy ~8), nije direktno čitljiv
- "Nepoznati epprom" (2MB) = RXT-X 260 ECU EEPROM backup (BRP container, SW=1037524060)
- `core/can_decoder.py` — CanDecoder klasa
- **ECU→SAT cluster bus IDs**: 0x0578 (267ms, svi), 0x0400 (311ms, GTX/GTI), 0x0408 (267ms, svi SW!)
- **ECU CAN TX tablica**: @ 0x03DF0C (2019-2021), @ 0x03DF1E (2018) — ISPRAVKA: 0x0433BC je period tablica!
- **SW string offset**: @ 0x001A (ne 0x0008!) — potvrđeno cross-SW auditom
- **inj_main (0x02436C) identičan** za 130/170/230/300hp — ovo je injector linearization (1D), NE 2D fuel mapa!
- **PRAVA 2D FUEL MAPA** @ 0x022066 (12×16 LE u16 Q15) — za SVE non-Spark ME17.8.5 varijante! Potvrđeno 2026-03-20.
  - Header @ 0x02202A/0x02202C: nR=12, nC=16 za sve varijante (GTI 1503 stara "16×12" pretpostavka bila NETOČNA)
  - RPM X-os @ 0x022046 (16pt, raw/4=RPM, 1400-8200); Load Y-os @ 0x02202E (12pt Q14, 6.5-54.7%)
  - Vrijednosti: 300hp max=0.944, 230hp=0.785, 130/170hp=0.524, GTI 1503=0.440, GTI90=0.572, GTI 1503 SC=0.952
  - 2018=2019=2021 identični za isti model; NEMA mirrora
- **Spark ignition**: @ 0x026A50 (ne 0x02B730 — to je 1630 ACE adresa!)
- **GTI90 DTC** @ 0x0217EE (potvrđeno); **Spark DTC** na drugom offsetu (0x0217EE su RPM ticks za Spark)
- **0x0408 nije samo GTS** — potvrđen u svim 1630 ACE SW varijantama

### Ostalo
- SC bypass: 3 kopije @ 0x020534/0x0205A8/0x029993 — NPRo mijenja samo 0x0205A8 i 0x029993
- **2016 SC bypass = 0x3333** (@ 0x0205A8), 2018+ = 0x2626 — razlikuju se!
- GTI injection @ 0x022066: NEMA mirrora (potvrđeno full CODE scan)
- GTI90 lambda: main @ 0x0266F0 = flat 0.984 (pasivna), mirror @ 0x026C08 = AKTIVNA (0.90-1.02, 127 unikátnih val)
- Knock params @ 0x0256F8: 52 u16 (ispravak s 24 — pravo područje je 104B)
- `_materijali/unknow/`: WinOLS .ols i .kp fajlovi + HPT tune fajl (RXT-X)
- **4-TEC 1503 SC boost factor** @ 0x025DF8: flat 23130 = Q14×1.412 (+41.2%) ZA SVE varijante (SC i NA identični!)
- **OLS BOOT razlika**: RXP tune OLS ima BOOT koji počinje `60000000` (ne `c0000000` kao normalni ME17); razlog neistražen
- **HPT fajl** = AES enkriptiran (entropy 7.99), neupotrebljiv bez HP Tuners softvera + VIN licencnog ključa
- **IBR modul MCU**: `Desktop/MCU/SPC5602P/u1 478/` = SPC5602P firmware; CFLASH=256KB, DFLASH=64KB; SW=08722440; CAN IDs za istraživanje u CAN sesiji (`0590FFFx`, `0101FFF1` stringovi)
- **rxtx_260_524060.bin** = multi-image container (3×128KB ECU slike); CODE @ 0x060000 (NE 0x010000!); standardne 10SW adrese ne rade; Block1=RXTX stock, Block2=RXP compr, Block3=treća varijanta; RXP vs RXTX = 96% razlika (različiti modeli, ne tune razlika)

