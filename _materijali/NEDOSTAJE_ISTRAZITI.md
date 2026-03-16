# ME17Suite — Što nedostaje i što treba istražiti

**Datum zadnje ažuriranja:** 2026-03-16
**Status projekta:** 44 mape potvrđene, ~8-10 mapa još ne pronađene/definirane

---

## 1. MAPE KOJE NE MOŽEMO PRONAĆI U BINARNOM FAJLU

### 1.1 Acceleration Enrichment (KFMSWUP / WDKBA)
**Bosch ASAP2 naziv:** `KFMSWUP` ili `WDKBA` (Mehrfachanreicherung / Beschleunigungsanreicherung)
**Fizikalni smisao:** Kratko bogaćenje goriva pri naglom gazu (tip-in enrichment)
**Zašto bitno:** Određuje kako motor reagira na nagli gas. Premalo = hesitacija, previše = crni dim.
**Format (ME17 standard):** 2D mapa, RPM × dTPS (promjena pozicije zaklopke), u8 ili u16 Q14
**Procjenjena veličina:** 8×8 do 12×12 celija
**Gdje tražiti:** Između 0x026000–0x028000 (nismo skenirali ovaj rozsah)
**Što tražimo:** Niz s patternom koji raste od dole-lijevo prema gore-desno (veći gas = više obogaćenja)

### 1.2 Cranking / Warm-Up Injection (KFSTARTMS)
**Bosch ASAP2 naziv:** `KFSTARTMS` (Kraftstoffmenge Start)
**Fizikalni smisao:** Količina goriva pri startanju i prvih sekundama zagrijavanja
**Zašto bitno:** Loš hladan start = nedovoljno goriva ili previše. Kritično za morski motor (vlaga).
**Format (ME17 standard):** 1D ili 2D mapa indexirana CTS temperaturom, u16 LE, Q14
**Procjenjena veličina:** 1×10 do 1×16 celija
**Gdje tražiti:** Blizu cold_start_enrichment @ 0x025860 (već imamo region 0x025800–0x026000)
**Što tražimo:** Rastuće vrijednosti kako temperatura pada (hladniji start = više goriva)

### 1.3 Overtemperature Protection
**Bosch ASAP2 naziv:** `KFTEMPCORR` ili `MLHFM_TMP`
**Fizikalni smisao:** ECU smanjuje snagu/ubrizgavanje kad CTS prelazi prag (~97°C za 300hp)
**Zašto bitno:** Limp mode aktivacija — važno za tuning (ne smije se deaktivirati, ali može pomaknuti prag).
**Format:** Skalarna vrijednost praga ili 1D mapa smanjenja po temperaturi
**Gdje tražiti:** Blizu CTS NTC tablice @ 0x0258AA i thermal mape @ 0x025E50
**Napomena:** Može biti u obliku skalara u BOOT regiji (0x0000–0x7EFF)

### 1.4 Injection X-Axis (RLSOL — 32 točke)
**Bosch ASAP2 naziv:** `RLSOL` (Relative Load Sollwert)
**Fizikalni smisao:** X-os injection mape — 32-točkasti raspon relativnog punjenja (0–200% load)
**Zašto bitno:** Bez poznate X-osi ne možemo točno interpretirati injection mapu!
**Format:** 32× u16 LE ili BE, rastuće, vjerojatno 0–8320 (0–130% rl)
**Gdje tražiti:** Neposredno ispred injection mape @ 0x02436C (možda 0x02434C ili 0x024300)
**Napomena:** Možda nije statički pohranjena — ME17 može generirati runtime iz parametara

### 1.5 Torque Axis Scale Konfirmacija
**Problem:** Pronašli smo kandidate za torque osi ali nisu potvrđene skaliranjem.
**Kandidat RPM os:** @ 0x029FE0 (16× u16, skala ×0.25?)
**Kandidat Load os:** @ 0x02A010 (16× u16)
**Zašto bitno:** Prikaz torque mape trenutno koristi globalnu RPM os — možda je pogrešno.
**Potvrda:** Trebamo A2L ili dump fajl s poznatim torque vrijednostima

### 1.6 Knock Threshold 2D Struktura
**Problem:** Imamo blok @ 0x0256F8 ali ne znamo dimenzije (1D ili 2D?).
**Trenutno:** Tretiramo kao 1×24 flat array
**Bosch standard:** Knock threshold je RPM×load 2D mapa (KFKLOPBAS)
**Procjenjena struktura:** 6×4 ili 8×3 (24 ćelija ukupno = naša procjena)
**Potvrda treba:** A2L ili WinOLS XDF

---

## 2. ŠTO SMO HTJELI ISTRAŽITI NA INTERNETU

### 2.1 Bosch ME17.8.5 A2L / ASAP2 Kalibracijski Fajlovi
**Što je A2L:** XML-like fajl koji opisuje SVE mape u ECU-u — naziv, adresa, skala, osi, limiti
**Vrijednost:** Jednim A2L fajlom riješavamo SVE nepoznanice (injection X-os, torque osi, knock dims, accel enrichment...)
**Gdje tražiti:**
- GitHub repozitoriji: pretražiti "ME17 A2L" ili "ME17.8.5 a2l"
- ECU tuning forumi: EcuTalk, RomRaider, TunerPro forums
- EcuFlash/RomRaider definicije za Subaru (dijele ME17.8.x s Boschom)
- Opel/Vauxhall forums: Corsa OPC, Astra OPC (1.6T, ME17.8.6 — slično)
- VCDS/Ross-Tech forumi za golf R / A3 8V varijantu (ME17.5 slično)

**Ključna napomena:** A2L fajlovi su vlasničke Bosch datoteke ali se pojavljuju na internetu za auto-ECU ME17 varijantu jer je tuning zajednica veća.

### 2.2 WinOLS Definicije (OLS fajlovi) za ME17
**Što je OLS:** WinOLS projekt fajl s predefiniranim mapama za specifični ECU
**Vrijednost:** Gotove definicije mapa s osi — možemo direktno usporediti s Sea-Doo adresama
**Gdje tražiti:**
- EcuTalk.co.uk — WinOLS OLS razmjena (forum thread "ME17 definitions")
- Nefmoto.com — tuning resursi za ME17 varijante
- German tuning forumi: Corsa-D, Vectra-C (1.6T ECOTEC, ME17.8.6)
- MyCorsa.co.uk ili Golfmk6.com (A14NET / A16XNT varijante)
**Napomena:** Sea-Doo nema online zajednice za ECU tuning — tražimo auto ECU s istim Bosch čipom.

### 2.3 TunerPro XDF za ME17.8.x
**Što je XDF:** TunerPro definicija mapa — slično WinOLS OLS-u
**Gdje tražiti:**
- TunerPro XDF Archive (tunerpro.net downloads)
- GitHub: pretražiti "tuner pro xdf ME17" ili "ME17 XDF"
- Corsa forums: "TunerPro Corsa OPC" (A16XNT motor, ME17.8.6)

### 2.4 EcuFlash / RomRaider XML Definicije
**Vrijednost:** Open-source ECU definicije koje pokrivaju neke ME17 varijante
**Gdje tražiti:**
- github.com/RomRaider/RomRaider/tree/master/src/main/resources/org/romraider/maps
- ECUFlash definicije za Subaru (ME7/ME17 Bosch srodnici)

### 2.5 Sea-Doo Specifični Resursi
**Gdje tražiti:**
- SeaDooForum.com — thread "RXP-X ECU tuning" ili "Bosch ME17 Sea-Doo"
- Performance Watercraft (PWCPerformance.com) — tuning diskusija
- BRP servisni partneri koji možda imaju BUDS2 diagnostic data export
- Rotax community forumi (kros-referenca s Rotax E-TEC za slični Bosch ECU)
- Yamaha SuperJet forumi (Yamaha YXZ ima srodne Bosch sisteme)

---

## 3. KOJE ECU DUMP-OVE TRAŽITI

### 3.1 Prioritet 1 — Direktno korisni (isti motor, različite godine)

| Traženi dump | Motor | SW ID (pretpostavka) | Zašto koristan |
|---|---|---|---|
| Sea-Doo RXP-X 300 **2017** | Rotax ACE 1630, 300hp | 10SW066726 ili sličan | Prva godina s promjenama, diff vs 2016 |
| Sea-Doo RXP-X 300 **2019** | Rotax ACE 1630, 300hp | novi SW ID | Moguće promjene maps poslije 2018 recall |
| Sea-Doo RXT-X 300 **2022+** | Rotax ACE 1630, 300hp | nepoznat | Najnoviji SW — TOPS 2.0 promjene? |
| Sea-Doo GTX 300 **any year** | Rotax ACE 1630, 300hp | sličan RXP-X | Isti motor, različite performance karte? |
| Sea-Doo RXP-X 300 **RS edition** | Rotax ACE 1630, 300hp | nepoznat | RS verzija = agresivniji tune? |
| Sea-Doo Wake **230hp** dump | Rotax ACE 1630, 230hp | 10SW053727 | Već imamo, ali novija godišta |

### 3.2 Prioritet 2 — Srodne varijante (isti blok, drugačija primjena)

| Traženi dump | Motor | Platforma | Zašto koristan |
|---|---|---|---|
| Can-Am Maverick X3 Turbo | Rotax ACE 900T | Bosch ME17.8.5 ili srodan | Isti Bosch platforma, turbo vs SC |
| Can-Am Spyder F3 | Rotax ACE 1330 | Bosch ME17 | Srodna ACE arhitektura |
| Sea-Doo GTI 155 **2021+** | Rotax ACE 1503 | ME17 varijant | 155hp — između 130 i 230 |
| Sea-Doo Spark TRIXX | Rotax 900 ACE | ME17 lite? | 90hp referenca |

### 3.3 Prioritet 3 — Automobilski ME17.8.x (ASAP2/A2L referenca)

| ECU | Auto | Motor | Vrijednost |
|---|---|---|---|
| Bosch ME17.8.6 | Opel Astra J OPC / Corsa OPC | A16XNT 1.6T 207hp | Isti Bosch generation, A2L javno dostupan |
| Bosch ME17.8.5 | Ford Focus ST 2013-2018 | 2.0 EcoBoost 250hp | Isti SW family |
| Bosch ME17.8.6 | Chevrolet Sonic / Cruze | A14NET 140hp | Manji motor, ali iste mape struktura |
| Bosch ME17.9.7 | Opel Insignia B | B16DTH | Novija generacija — struktura mapa ista |
| Bosch ME17.8.5 | Alfa Romeo 1.4T | ME17 varijant | Fiat Group → isti Bosch chip |

**Zašto automobilske ECU?** Bosch standardizira ASAP2 nazive i map structure kroz cijelu ME17 familiju. Adreses se razlikuju ali: rows, cols, dtype, scale, axis structure — identični. A2L za Opel A16XNT je djelomično javno dostupan (WinOLS community) i direktno primjenjiv.

---

## 4. UPUTSTVO ZA BUDUĆE INTERNET ISTRAŽIVANJE

### 4.1 Ključne pretraživačke fraze

```
"ME17.8.5" A2L filetype:a2l
"ME17.8.5" XDF site:github.com
"ME17.8.6" WinOLS definitions download
"Bosch ME17" KFKLOPBAS (knock threshold map name)
"Bosch ME17" KFMSWUP (accel enrichment map name)
"ME17.8.5" "map definition" sea-doo OR rotax
bosch me17 a2l "relative load" "RLSOL"
site:ecutek.com OR site:optimum-power.com "ME17"
"sea-doo 300" ECU flash tune maps
RXP-X 300 ECU remap "map addresses"
```

### 4.2 Gdje tražiti A2L fajlove

1. **GitHub** — mnogi tuners dijele A2L iz projekata:
   `github.com search: "me17" language:ASAP2` ili `filename:*.a2l me17`

2. **EcuTalk** (ecuttalk.co.uk) — najveći EU ECU tuning forum, thread "Bosch ME17 mapping"

3. **Nefmoto.com** — američki tuning forum, ME17 thread za Ford Focus ST / Fiesta ST
   (Bosch ME17.8.5 na 2.0 EcoBoost — ista generacija kao Sea-Doo SW)

4. **HPTuners forum** (hptuners.com/forum) — GM/Ford tuning, neke ME17 definicije

5. **TunerPro** (tunerpro.net) — downloads sekcija, search "ME17" ili "Bosch 17"

6. **RomRaider** (romraider.com/forum) — open-source, neke Bosch definicije

### 4.3 Što točno pitati na forumima

> "I'm working on reverse-engineering a Bosch ME17.8.5 ECU (Rotax ACE 1630 engine in Sea-Doo PWC).
> I've confirmed injection map at 0x02436C (6×32, u16 LE), torque at 0x02A0D8 (16×16, Q8),
> lambda at 0x0266F0 (12×18, Q15). I need help identifying:
> 1. Acceleration enrichment (KFMSWUP) address
> 2. Cranking injection (KFSTARTMS) address
> 3. RLSOL X-axis for injection map (32 columns)
> Does anyone have an A2L or WinOLS OLS for ME17.8.5 / ME17.8.6 that might cross-reference?"

### 4.4 Koje baze podataka pretražiti

| Baza | URL | Sadržaj |
|---|---|---|
| ECUDB | ecudb.com | Dump upload/download zajednica |
| Openecu | openecu.org | Open-source ECU info |
| RomRaider maps | github.com/RomRaider | XML mapa definicije |
| Bosch Press | bosch-motorsport.com | Javni tehnički docs |
| SAE International | sae.org | ME17 tehničke publikacije |

---

## 5. NEDOSTAJE U DOKUMENTACIJI

### 5.1 Osi koje nisu definirane
| Mapa | Nepoznata os | Problem |
|---|---|---|
| Injection (6×32) | X os (32 cols) | RLSOL vrijednosti nepoznate |
| Knock threshold | Obje osi | 2D struktura nepoznata |
| Temp fuel (1×156) | X os | CTS? IAT? Nepoznato |
| Lambda bias (1×141) | X os | Uvjet indexiranja nepoznat |
| Deadtime (20×7) | Obje osi | Napon baterije? CTS? |
| Idle RPM (5×12) | Obje osi | Uvjeti (row) i stupnjevi (col) nepoznati |
| Cold start (1×6) | X os | Temperatura? Trajanje? |

### 5.2 Mape koje treba verificirati (procjene, ne potvrđeno)
- **SC bypass X os**: kPa ili ETA% — pretpostavljamo kPa, nije A2L potvrđeno
- **Injection scale**: 0.0001ms — procjena, možda µs ili mg/stroke
- **Knock threshold scale**: tretiramo kao raw u16, ali mogu biti mV ili dB

### 5.3 Mape koje postoje ali su van dosega
- **ETA throttle map** @ 0x020256 — pronađena, ali non-tunable (hardware TPS linearizacija)
- **NTC ADC lookup** @ 0x0258AA — pronađena, hardware konstanta (NE MIJENJATI)
- **Function pointers** @ 0x042xxx–0x044xxx — TriCore CODE, opasno kopirati

---

## 6. PRIORITETNI ZADACI (NEXT STEPS)

### Za sljedeću sesiju:
1. **Pronći RLSOL os**: Skenirati region 0x024300–0x024370 za 32-element rastuci niz
2. **Accel enrichment hunt**: Skenirati 0x026000–0x028000 za RPM×dTPS pattern
3. **Torque axis verifikacija**: Pročitati @ 0x029FE0 i 0x02A010, skale testirati
4. **Cranking injection**: Tražiti blizu cold_start @ 0x025860, pattern: pada s temperaturom

### Za BUDS2 sesiju (kad imaš pristup):
1. Snimiti dump sa **GTI 155** (novi HP nivo koji nemamo)
2. Snimiti dump sa **RXT-X 300 2022** (najnoviji SW)
3. Snimiti dump sa **Spark 90 2021+** (novija godišta za Spark)
4. Pokušati BUDS2 live data logging pri radu motora za identifikaciju RLSOL vrijednosti

### Za internet istraživanje:
1. GitHub search: `filename:*.a2l me17` i `bosch me17 definition`
2. Nefmoto.com search: "ME17.8.5 map"
3. EcuTalk search: "Bosch ME17 a2l download"
4. Kontaktirati Opel A16XNT tuners — ista Bosch generacija, veća zajednica
