# CAN SAT Poruke — ME17.8.5 ECU ↔ SAT Komunikacija

**Datum analize:** 2026-03-18
**Cilj:** Utvrditi koje CAN poruke ECU razmjenjuje sa SAT (Systeme d'Affichage et de Tableau bord = instrument ploča/gauge cluster) — za projekt Spark SAT na 230/260hp modelu.

---

## 1. Pregled

BRP Sea-Doo koristi **proprietarni CAN protokol** (250 kbps, standard 11-bit frames).
ECU ME17.8.5 (TC1762 TriCore) razmjenjuje podatke sa SAT-om putem fiksnih CAN message ID-ova.

**Potvrđena kompatibilnost:** Korisnik je potvrdio da 300hp Sea-Doo radi sa Spark SAT-om — dakle protokol je kompatibilan na razini hardvera. Razlike koje postoje između Spark ECU i 300hp/230hp ECU ne sprječavaju osnovnu funkcionalnost.

---

## 2. Analiza binarnih fajlova

### SW verzije analizirane:
| Naziv | SW ID | Model | Motor |
|-------|--------|-------|-------|
| spark90_21 | 10SW039116 | Spark 90 2021 | Rotax 900 ACE |
| gti90_21   | 10SW053774 | GTI SE 90 2021 | Rotax 900 HO |
| sw230_21   | 10SW053727 | GTI SE 230 / Wake 230 2021 | Rotax 1630 SC |
| sw300_21   | 10SW066726 | RXP/RXT/GTX 300 2021 | Rotax 1630 SC |
| ori_300    | 10SW066726 | RXP/RXT/GTX 300 (2016–2021) | Rotax 1630 SC |

---

## 3. CAN Message ID tablica (iz ECU binarnog fajla)

Pronađena u CODE regiji svih ECU-a (u16 Big-Endian niz, nul-terminiran):
- **Spark ECU** @ fizička adresa `0x042EC4`
- **GTI/230/300 ECU** @ fizička adresa `0x0433BC`

### Spark ECU (10SW039116):
```
0x015B  0x0154  0x0134  0x013C  0x015C  0x0138
0x0108  0x0214  0x012C  0x0110  0x0108  0x017C
```

### GTI/230hp/300hp ECU (10SW053774 / 10SW053727 / 10SW066726):
```
0x015B  0x015C  0x0148  0x013C  0x015C  0x0138
0x0108  0x0214  0x012C  0x0110  0x0108  0x017C
```
> **Napomena:** GTI/230/300hp su IDENTIČNI u ovoj tablici.

---

## 4. Razlike Spark vs GTI/230/300hp

### 4a. CAN IDs samo u Spark ECU-u:
| CAN ID | Decimal | Primjedba |
|--------|---------|-----------|
| `0x0134` | 308 | Spark-specifičan (nema u GTI/230/300) |
| `0x0154` | 340 | Spark-specifičan (nema u GTI/230/300) |

### 4b. CAN IDs samo u GTI/230/300hp ECU-u:
| CAN ID | Decimal | Primjedba |
|--------|---------|-----------|
| `0x0148` | 328 | GTI/230/300-specifičan (nema u Spark) |

### 4c. Zajednički CAN IDs (prisutni u OBA):
| CAN ID | Decimal |
|--------|---------|
| `0x0108` | 264 |
| `0x0110` | 272 |
| `0x012C` | 300 |
| `0x0138` | 312 |
| `0x013C` | 316 |
| `0x015B` | 347 |
| `0x015C` | 348 |
| `0x017C` | 380 |
| `0x0214` | 532 |

---

## 5. Dodatne poruke u GTI/230/300hp ECU (nema u Spark)

U config tablici @ `0x010470` (GTI/230/300), pronađene su 3 ekstra 4-byte entryja kojih Spark nema:

| Byte 0-1 (CAN ID LE) | CAN ID | Byte 2 | Byte 3 | Napomena |
|----------------------|--------|--------|--------|---------|
| `CD 00` | 0x00CD (205) | 0x01 | 0xFF | Prisutan samo u GTI/230/300 ECU |
| `DC 00` | 0x00DC (220) | 0x01 | 0xFF | Prisutan samo u GTI/230/300 ECU |
| `BF 00` | 0x00BF (191) | 0x01 | 0xFF | Prisutan samo u GTI/230/300 ECU |

> Byte 2 = vjerojatno DLC ili signal count (vrijednost 1)
> Byte 3 = 0xFF vjerojatno znači "enabled/active"

### Zajednička tablica (prisutna u OBA, Spark i GTI):
| Format | Moguće CAN ID (BE) | Byte 2 | Napomena |
|--------|-------------------|--------|---------|
| `02 1F 06 00` | 0x021F (543) | 6 | Shared poruka |
| `02 25 06 00` | 0x0225 (549) | 6 | Shared poruka |
| `02 2B 06 00` | 0x022B (555) | 6 | Shared poruka |

---

## 6. Zaključak za projekt Spark SAT na 230/260hp

### Što radi bez izmjena:
- **Svih 9 zajedničkih CAN ID-ova** (0x108–0x214) je identično — ovi prikazuju RPM, temperaturu, sate rada i sl.
- 300hp ECU + Spark SAT = potvrđeno radi → 230hp ECU koristi **isti CAN ID set** kao 300hp → **ide raditi**

### Potencijalni problemi:
- Spark SAT šalje/prima na 0x0134 i 0x0154 — ovi ID-ovi **ne postoje** u 230hp ECU-u
  → Odgovarajući prikaz (signal koji koristi ta 2 ID-a) može biti prazan/0 na Spark SAT-u
- 230hp ECU šalje na 0x0148 i ima 3 extra poruke (0xBF/0xCD/0xDC) — Spark SAT ignorira nepoznate ID-ove bez grešaka

### Preporuka:
1. **Plug-and-play test:** Direktno spoji Spark SAT na 230hp/260hp (isti CAN pin-out na Sea-Doo-u)
2. Ako nešto ne prikazuje, identifikuj koji CAN ID nedostaje CAN snifferom (SavvyCAN ili slično)
3. Moguća korekcija: ECU flash koji mijenja 0x0148→0x0134 i 0x015C→0x0154 (zamjena 2 bajta u tablici) — **nije preporučeno bez testiranja!**

---

## 7. Metodologija analize

- Binarna analiza 5 ECU fajlova (10SW039116, 10SW053774, 10SW053727, 10SW066726)
- Pronalazak CAN ID tablice u CODE regiji (Big-Endian u16 niz, nul-terminator)
- Cross-referenca između Spark i ne-Spark binara
- **Napomena:** Smjer (TX/RX) nije eksplicitno kodiran u tablici — pretpostavka da su ovo ECU→SAT poruke bazirana na tome da 300hp+Spark SAT radi bez ECU prilagodbe
- **Za 100% potvrdu:** CAN sniffanje na živom vozilu (250 kbps, standard 11-bit)

---

## 8. Brza referenca — CAN ID-ovi po tipu ECU

```
Spark ECU:      108 110 12C 138 13C 15B 15C 17C 214  +  134 154
GTI/230/300:    108 110 12C 138 13C 15B 15C 17C 214  +  148 (x2×15C)
                                                          +  BF  CD  DC
```
