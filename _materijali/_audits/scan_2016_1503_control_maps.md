# 2016 gen 1503 — Control mape — scan rezultati
Datum: 2026-03-21

Referentni fajlovi: 2018/4tec1503/230.bin (10SW025021), 2018/4tec1503/130v1.bin (10SW025022)
Ciljni fajlovi: 2016/4tec1503/260.bin (10SW000778), 2016/4tec1503/215.bin (10SW000776)

---

## KFPED throttle (10×20 u8)

- **2018+ adresa**: 0x029528 (header, 32B) + 0x029548 (data, 200B), mirror +0xE8 @ 0x029630
- **2016 gen adresa**: **0x026F4C** (header, 32B) + **0x026F6C** (data, 200B), mirror +0xE6 @ **0x027052**
- **Offset vs 2018**: -0x25DC (header i data)
- **Verifikacija**: 8B pre-sig match iz ref230; header struktura podudaranje potvrđeno
  - 260.bin header @ 0x026F4C: `00 03 04 0A 14 1E 28 32 3C 46 26 2C 32 3F 4B 58 ...`
  - vs ref230 @ 0x029528: `B0 D8 EC 00 0A 1E 28 32 46 5A 26 2C 32 3F 4B 58 ...`
  - Zajednički sadržaj od bajta 3 nadalje (Y-os vrijednosti identične)
- **Napomena**: 260 vs 215 RAZLIČITI podaci (198/200B razlika) — 260hp SC ima veće vrijednosti od 215hp SC, logično
- **Mirror offset**: 0xE6 (ne 0xE8 kao u 2018+)

## Accel enrichment (5×5 Q14, kompleksni format)

- **2018+ adresa**: 0x028059
- **2016 gen adresa**: **0x026223**
- **Offset vs 2018**: -0x1E36
- **Verifikacija**: 8B pre-sig `5D 5F 61 63 07 00 00 00` match u oba 2016 fajla (260 i 215)
  - Podaci identični u 2018 ref i 2016 ciljnim fajlovima za isti blok (SC varijanta)
  - 260 vs 215: identično (250B) — accel enrichment nije diferenciran po snazi
- **Pouzdanost**: VISOKA (8B signature, oba 2016 fajla potvrđena)

## Cold start injection (1×6 u16 LE)

- **2018+ adresa**: 0x025CDC (data, 12B), axis @ 0x025CD0 (12B)
- **2016 gen adresa**: **0x024236** (data, 12B), axis @ **0x02422A** (12B)
- **Offset vs 2018**: -0x1AA6
- **Verifikacija**: 6B pre-sig iz ref130 + 8B post-sig iz ref230
  - 260 cold data @ 0x024236: `[0, 1024, 1707, 3413, 5120, 7680]` Q15 = `[0.000, 0.031, 0.052, 0.104, 0.156, 0.234]`
  - Identično s ref230 (isti injektori u svim 1503 varijantama)
  - 260 vs 215: identično (12B)
  - 260 axis @ 0x02422A: `[32, 85, 65494, 10, 20, 6]` — axis[2]=65494=0xFFD6 (negativan, -42 kao i8 → -42°C temp)
- **Pouzdanost**: VISOKA (8B post-sig match potvrđen)

## Knock params (52×u16 LE = 104B)

- **2018+ adresa**: 0x0256F8, format: [ACCD ACCD | 1F1F × 50]
- **2016 gen adresa**: **0x024268**, format: DRUGAČIJA STRUKTURA
- **Offset vs 2018**: -0x1490
- **Verifikacija**: 2016 gen knock blok potvrđen pozicijom i sadržajem:
  - @ 0x024268: 9× 0x4040, 9× 0x1F1F, zatim tail data (09 1F 33 40 4D 5B 75 90 AB BF ...)
  - 2018 referenca: počinje s 0xACCD 0xACCD (SC=44237), ref130 s 0xFFFF 0xFFFF (NA=65535)
  - 2016 počinje s 0x4040 (16448) — drugačija kalibracija prvog parametra
  - **Napomena**: 2016 gen knock blok ima DRUGAČIJU internu strukturu od 2018+:
    - 2018: 2 "threshold" u16 + 50× 0x1F1F = uniformna
    - 2016: 9× 0x4040 + 9× 0x1F1F + promjenljivi tail (09 1F 33 40...) + FF blokovi
    - Potencijalno drugačiji broj knock parametara ili drug(ačiji format bloka
  - 260 vs 215: **identično** (104B pri ovoj adresi)
- **Pouzdanost**: SREDNJA — adresa potvrđena, ali format se razlikuje od 2018+; moguće da je ovo širi params blok

---

## Pregled offseta (2016 gen vs 2018+)

| Mapa            | 2016 gen   | 2018+      | Offset       |
|-----------------|------------|------------|--------------|
| cold_start data | 0x024236   | 0x025CDC   | -0x1AA6      |
| knock params    | 0x024268   | 0x0256F8   | -0x1490      |
| accel enrich    | 0x026223   | 0x028059   | -0x1E36      |
| rev_limit       | 0x026E1E   | 0x028E94   | -0x2076      |
| KFPED header    | 0x026F4C   | 0x029528   | -0x25DC      |
| KFPED data      | 0x026F6C   | 0x029548   | -0x25DC      |

**Zaključak**: 2016 gen 1503 nema uniformni CODE offset — offset varira od -0x1490 do -0x25DC ovisno o mapi.
KFPED i rev_limit imaju slične offsete (-0x25DC vs -0x2076), ali cold/accel su značajno bliže 2018+ adresi.
