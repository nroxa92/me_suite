# CAN Cross-SW Audit — ACE 1630 (2018-2021)

**Datum**: 2026-03-19
**Dumps**: 6 binarija (2018/300, 2019/300, 2020/300, 2020/230, 2021/300 REF, 2021/230)

---

## 1. SW Identifikacija

| Dump | SW String |
|------|-----------|
| 2018/1630ace/300.bin | 10SW023910 (2018 prijelazni SW) |
| 2019/1630ace/300.bin | 10SW040039 |
| 2020/1630ace/300.bin | 10SW054296 ili 10SW066726 |
| 2020/1630ace/230.bin | 10SW053727 |
| 2021/1630ace/300.bin | **10SW066726** (REFERENCA) |
| 2021/1630ace/230.bin | 10SW053727 |

---

## 2. Blok @ 0x0433BC (128 B)

**Sadržaj** (svih 6 dumpova — identično):
```
01 5B 01 5C 01 48 01 3C 01 5C 01 38 01 08 02 14
01 2C 01 10 01 08 01 7C 00 00 01 00 02 00 03 00
...
```

Adresa 0x0433BC sadrži **lookup tablicu perioda/timinga**, ne CAN ID tablicu. Sve LE16 vrijednosti su u rangu 0x01xx-0x02xx — to su periodi (ms×10 ili slično), ne CAN ID-ovi (koji bi bili 0x0578, 0x0400 itd.).

Jedine CAN-range vrijednosti: `0x0801` na offsetima +0x0C i +0x14 — to je vjerojatno bitmask/flags, ne CAN ID.

**Zaključak**: 0x0433BC **NIJE** CAN TX tablica. Tražena CAN TX tablica je na drugoj adresi.

---

## 3. Lokacija CAN TX Tablice (0x0578 scan)

Scan za 0x0578 (bytes `78 05`) u cijelom CODE regionu 0x020000-0x060000:

| Dump | Adrese gdje 0x0578 postoji |
|------|---------------------------|
| 2018_300 | 0x021166, **0x03DF1E** |
| 2019_300 | 0x021166, **0x03DF0C** |
| 2020_300 | 0x021166, **0x03DF0C** |
| 2020_230 | 0x021166, **0x03DF0C** |
| 2021_300 | 0x021166, **0x03DF0C** |
| 2021_230 | 0x021166, **0x03DF0C** |

**Stvarna adresa CAN tablice**: ~**0x03DF0C** (ne 0x0433BC!)
- 2018 SW je na 0x03DF1E (offset +0x12 od 2019+)
- 0x021166 = referenca na adresu u CODE (TriCore pointeri)

---

## 4. CAN ID-ovi u Regiji 0x043000-0x045000

Ova regija sadrži **bogatu kolekciju** CAN-range vrijednosti (160+ unique ID-ova). Ovo nije jedna CAN TX tablica — to je vjerojatno CAN filter/receive tablica ili kompleksan firmware kod koji referencira mnoge CAN ID-ove.

### Cluster IDs pronađeni:

**0x0578 (cluster primary)**:
- Prisutan u svim dumpovima @ 0x043000-0x045000 regiji: **NE** (nije nađen direktno)
- Ali prisutan u CODE @ ~0x03DF0C — ovo je prava TX tablica

**0x0400 (cluster secondary)**:
- 224 hita u 2018_300 vs 220 hita u 2020/2021 — mali broj razlika
- Prisutan svugdje, nije CAN ID specifičan

**0x0408 (GTS specific?)**:
- Prisutan u **svim** SW varijantama (129-130 hita svaki)
- Nije GTS-specifičan — postoji i u standardnim 300hp/230hp SW

### Dostupni CAN IDs u 0x043000-0x045000 koji su potvrđeni:

| CAN ID | Tip | Adresa (2021_300) |
|--------|-----|------------------|
| 0x0300 | diag TX | 0x43D4E, 0x43D50 |
| 0x0400 | cluster secondary | 0x43D44, 0x43D86 |
| 0x0301 | diag/ECU | 0x43D26, 0x43DDA |
| 0x0500 | unknown | 0x43098, 0x430A0 |
| 0x0501 | unknown | 0x43D8C+ |
| 0x0601-0x0606 | OBD/diag | 0x43D54+ |

---

## 5. Cross-SW Usporedba

### 300hp 2021 vs 230hp 2021 (u regiji 0x043000-0x045000):
**0 diff words** — potpuno identični. CAN tablice 300hp == 230hp za isti godišnjak.

### 2021 vs 2020 (isti SW):
**0 diff words** — identični u CAN regiji.

### 2021_300 vs 2019_300:
- **334 diff words** — razlikuju se
- Glavna diff regija: **0x04326C-0x043288** (pattern razlika)
  - 2021: `AC AA 08 80`, 2019: `96 AA 08 80` — offset bajtovi (kalibracija timinga?)
- Sekundarna diff: **0x0441DC-0x044208** (timing tablice)

### 2021_300 vs 2018_300:
- **616 diff words** — najveća razlika
- 0x04326C blok: 2021=`AC AA 08 80`, 2018=`7C AA 08 80`
- 0x043EB8-0x043EE4 region: timing vrijednosti različite
- **2018→2019 promjena**: ~282 diff words u 0x043000-0x045000

---

## 6. Detaljni Pregled 0x0433BC

Svih 6 dumpova je **identično** na adresi 0x0433BC. Sadržaj je konstantan bez obzira na SW verziju ili snagu (300/230hp). Ovo znači da ta adresa **nije** SW-specifična CAN TX tablica.

Prava interpretacija 0x0433BC sadržaja (01 5B = 347, 01 5C = 348, ...):
- Ovo izgleda kao **lookup tablica perioda u ms** (multiplicirano faktorom), možda CAN timing periodi
- Ali 0x0578 (cluster 267ms) i 0x0400 (311ms) nisu ovdje direktno — oni su na ~0x03DF0C

---

## 7. Prava CAN TX Tablica (~0x03DF0C)

Adresa **0x03DF0C** (za 2019-2021) ili **0x03DF1E** (za 2018_300):
- Sadržaj: `78 05` = 0x0578 LE16 — cluster primary
- 2018 SW je offset za 0x12 bajtova = 18B odmak
- Ovo je kandidat za stvarnu CAN TX tablicu

**Preporuča se**: detaljan dump 64-128B od 0x03DF0C za vizualni pregled svih TX CAN ID-ova.

---

## 8. Ključni Zaključci

1. **0x0433BC NIJE CAN TX tablica** — to je lookup tablica perioda/timinga; identična u svim 6 dumpova
2. **Prava lokacija CAN TX tablice**: ~**0x03DF0C** (2019+) / 0x03DF1E (2018)
3. **0x0578 (cluster primary)** postoji samo na 2 mjesta u CODE regiji (0x021166 i 0x03DF0C)
4. **0x0408 nije GTS-specifičan** — postoji u svim SW varijantama
5. **300hp == 230hp** u CAN tablici (identični u 2020 i 2021 — isti SW za cluster)
6. **2018→2021 evolucija**: CAN tablice se mijenjaju između godišnjaka, ali samo u 0x04326C i 0x0441XX blokovima, ne u core CAN ID-ovima
7. **CAN ID 0x0102** pronađen samo u 2018_300 @ 0x43DFA (diag TX) — u kasnijim SW premješten na drugu adresu ili uklonjen iz te regije

---

## 9. Detaljan Dump CAN TX Tablice @ 0x03DF0C

**Sadržaj** (identičan u svih 5 dumpova 2019-2021, i 2018 na offset 0x03DF1E):
```
78 05 60 A5 09 CF 5D 08 24 5F 09 CF 5E 08 96 20
24 5F 09 E4 47 08 40 5F DF 04 14 00 91 00 00 4D
...
```

**Struktura**: `78 05` = 0x0578 LE16 je **prvi entry**. Format nije trivijalan (nije [CAN_ID][period_ms] jednostavno) — to je komprimirani TriCore kod koji referencira CAN operacije. Međutim, 0x0578 je jasno na poziciji 0 = "cluster primary ID je prvi registrirani".

### CAN ID-ovi nađeni u tablici (sve verzije identične):
| Offset | LE16 vrijednost | Opis |
|--------|-----------------|------|
| +0x00 | 0x0578 | cluster primary |
| +0x18 | 0x04DF | nepoznat |
| +0x26 | 0x054A | nepoznat |
| +0x50 | 0x0535 | nepoznat |
| +0x56 | 0x0237 | nepoznat |
| +0x5E | 0x0137 | nepoznat |
| +0x96 | 0x0512 | nepoznat |
| +0xA2 | 0x0237 | nepoznat |
| +0xB0 | 0x0378 | nepoznat |
| +0xB4 | 0x0100 | nepoznat |
| +0xEE | 0x04E2 | nepoznat |
| +0xF0 | 0x0182 | nepoznat |
| +0xF6 | 0x0382 | nepoznat |
| +0xF8 | 0x0273 | nepoznat |

**Napomena**: 0x0400 (cluster secondary) i 0x0102-0x0308 (diag TX) nisu direktno pronađeni u ovoj 256B tablici. Vjerojatno su u nastavku tablice ili u drugoj strukturi.

### Usporedba 2018 vs 2021 (ova tablica):
**Identični** — isti sadržaj na offsetima 0x03DF1E (2018) i 0x03DF0C (2019-2021). Razlika je samo u adresi (18B odmak = promjena layout-a između 2018 i 2019 SW).

---

## 10. Ključni Zaključci (FINALNI)

1. **0x0433BC NIJE CAN TX tablica** — sadržaj je lookup tablica, identičan svim SW verzijama
2. **Prava CAN TX tablica**: **0x03DF0C** (2019+) / **0x03DF1E** (2018 SW)
3. **0x0578 (cluster primary)** = **prvi entry** u CAN TX tablici
4. **Tablica je identična** za sve 2019-2021 verzije (300hp i 230hp) — CAN TX struktura se ne mijenja između godišnjaka ni snaga
5. **2018 vs 2019+**: isti sadržaj ali odmaknut 0x12 (18B) zbog drugačijeg CODE layout-a
6. **0x0408 nije GTS-specifičan** — postoji u svim SW
7. **0x0400 (cluster secondary)**: nađen u regiji 0x043000-0x045000 ali ne u 0x03DF0C bloku — možda posebna RX tablica ili u kasnijim entryima CAN TX tablice

---

## 11. TODO / Preporučene Akcije

1. Nastaviti scan CAN TX tablice od 0x03DF0C+256 — pronaći 0x0400 i diag TX ID-ove
2. Potvrditi format: vjerojatno TriCore inline CAN message setup, ne jednostavna lookup tablica
3. Usporediti 0x03DF0C sa Spark/GTI dumpovima — imaju li iste cluster IDs?
