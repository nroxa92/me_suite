# DTC Cross-SW Audit — 1630 ACE

**Datum:** 2026-03-19
**Autor:** automatska analiza (dtc_cross_sw_audit.py)
**Referenca:** 10SW066726 (2021/300hp)

---

## Metodologija i nalazi — potvrđeni mehanizam

### DTC enable arhitektura (potvrđeno za sve analizirane dumpove)

| Parametar | Vrijednost | Napomena |
|-----------|------------|---------|
| DTC storage base | 0x021700 | u16 LE kodovi, non-zero = aktivan |
| Enable tablica | 0x021080–0x0210BD | 62 bajta (slot 0–61), u8 vrijednosti 0-6 |
| Mapping tablica | 0x0239B4 (za 300hp SW) | u8 array: idx=(code_addr-0x021700)/2 → slot |
| Formula | en_addr = 0x021080 + map[idx] | |
| P0231 stvarna adresa | 0x0217BC (idx=94) | DTC kod 0x0231 potvrđen u storage |

**VAŽNO:** Zadatak je specificirao P0231 @ 0x021786 (idx=67), ali u stvarnom binarnom P0231 (0x0231) pohranjen je @ **0x0217BC** (idx=94). Koriste se ispravne adrese iz direktne analize.

---

## 1. Enable tablica — identična kroz sve SW verzije

Enable tablica na 0x021080 je **bajt-za-bajt identična** u svim 10 analiziranih dumpova:

```
Slot  0: 0x00  Slot  1: 0x00  Slot  2: 0x00  Slot  3: 0x00
Slot  4: 0x06  Slot  5: 0x06  ...
Slot 57: 0x06  (P0231 slot u 300hp SW)
Slot  3: 0x00  (U16A4/A7/A9/AA slot u 300hp SW)
```

Ovo je **kritično**: ne ovisi o tome koji SW je na ECU-u — enable vrijednosti su uvijek iste na istim slotovima.

---

## 2. Mapping tablica — analiza po SW verziji

| Dump | SW | Map table offset | Status | Napomena |
|------|----|-----------------|--------|---------|
| 2018/300hp | 10SW023910 | **0x0239B4** | Potvrđen | Isti kao ref |
| 2019/300hp | 10SW040039 | **0x0239B4** | Potvrđen | Isti kao ref |
| 2020/300hp | 10SW054296 | **0x0239B4** | Potvrđen | Isti kao ref |
| 2021/300hp | 10SW066726 | **0x0239B4** | Potvrđen | Referenca |
| 2020/230hp | 10SW053727 | N/A | Nije pronađena | Drugačiji SW layout |
| 2021/230hp | 10SW053727 | N/A | Nije pronađena | Isti SW kao 2020/230 |
| 2020/170hp | 10SW053729 | N/A | Nije pronađena | 170=130 identičan dump |
| 2020/130hp | 10SW053729 | N/A | Nije pronađena | 170=130 identičan dump |
| 2021/170hp | 10SW053729 | N/A | Nije pronađena | |
| 2021/130hp | 10SW053729 | N/A | Nije pronađena | |

**Napomena za 10SW053727/053729:** Mapping tablica nije u u8 formatu na 0x0239B4. DTC storage adrese i enable tablica su identični s 300hp SW-om, ali indexing mehanizam za 230/170/130hp nije identificiran ovom metodom.

---

## 3. U16Ax enable mapping — potvrđeno za sve 300hp SW verzije

### 10SW066726 (2021/300hp) — identično za 10SW023910, 10SW040039, 10SW054296

P0231: slot=**57** | en_addr=**0x0210B9** | en_val=**0x06** (enabled)

| Kod | code_addr | idx | Slot | En addr | En val | Dijeli slot s P0231? |
|-----|-----------|-----|------|---------|--------|----------------------|
| U16A8 | 0x0217C4 | 98 | **57** | 0x0210B9 | 0x06 | **DA** |
| U16A9 | 0x0217C6 | 99 | 3 | 0x021083 | 0x00 | NE |
| U16A2 | 0x0217C8 | 100 | **57** | 0x0210B9 | 0x06 | **DA** |
| U16A7 | 0x0217CA | 101 | 3 | 0x021083 | 0x00 | NE |
| U16AB | 0x0217CC | 102 | **57** | 0x0210B9 | 0x06 | **DA** |
| U16A4 | 0x0217CE | 103 | 3 | 0x021083 | 0x00 | NE |
| U16A5 | 0x0217D0 | 104 | **57** | 0x0210B9 | 0x06 | **DA** |
| U16A3 | 0x0217D4 | 106 | **57** | 0x0210B9 | 0x06 | **DA** |
| U16AA | 0x0217D6 | 107 | 3 | 0x021083 | 0x00 | NE |
| U16A1 | 0x0217D8 | 108 | **57** | 0x0210B9 | 0x06 | **DA** |
| P0232 | 0x0217BE | 95 | 3 | 0x021083 | 0x00 | NE |

**Identično potvrđeno za: 10SW023910 (2018), 10SW040039 (2019), 10SW054296 (2020).**

---

## 4. Cross-SW komparacija (300hp SW)

| Parametar | 2018/300 | 2019/300 | 2020/300 | 2021/300 |
|-----------|----------|----------|----------|----------|
| SW | 10SW023910 | 10SW040039 | 10SW054296 | 10SW066726 |
| Map base | 0x0239B4 | 0x0239B4 | 0x0239B4 | 0x0239B4 |
| P0231 slot | 57 | 57 | 57 | 57 |
| P0231 en_addr | 0x0210B9 | 0x0210B9 | 0x0210B9 | 0x0210B9 |
| P0231 en_val | 0x06 | 0x06 | 0x06 | 0x06 |
| U16Ax @ P0231 slot | A1,A2,A3,A5,A8,AB | A1,A2,A3,A5,A8,AB | A1,A2,A3,A5,A8,AB | A1,A2,A3,A5,A8,AB |
| U16Ax @ slot 3 | A4,A7,A9,AA | A4,A7,A9,AA | A4,A7,A9,AA | A4,A7,A9,AA |

**Savršena konzistentnost kroz sve 300hp SW verzije (2018–2021).**

---

## 5. Enable slot grupacija — implikacija za DTC OFF

### Slot distribucija (300hp SW, identično za sve godine)

| Slot | En addr | En val | Kodovi pod tom kontrolom |
|------|---------|--------|--------------------------|
| **57** | **0x0210B9** | **0x06** (enabled) | **P0231, U16A1, U16A2, U16A3, U16A5, U16A8, U16AB** |
| **3** | **0x021083** | **0x00** (disabled) | P0232, U16A4, U16A7, U16A9, U16AA |

### Implikacije za DTC OFF

1. **Slot 57 (0x0210B9) je shared enable byte** za P0231 i 6 od 10 U16Ax kodova.
   Gašenje bajta na 0x0210B9 gasi **sve istovremeno**: P0231 + U16A1, U16A2, U16A3, U16A5, U16A8, U16AB.

2. **Slot 3 (0x021083) = 0x00** — P0232 i U16A4, U16A7, U16A9, U16AA su već **disabled** u originalnom 300hp binarnom.
   Za te kodove DTC OFF nije potreban.

3. Za **230hp (10SW053727)** i **170/130hp (10SW053729)**: enable tablica je identična, DTC storage adrese iste. Mapping nije potvrđen ovom metodom, ali struktura ECU-a je ista, pa se pretpostavlja isti šablon.

---

## 6. DTC storage potvrda — sve SW verzije

| Dump | P0231@0x0217BC | U16A1@0x0217D8 | U16A8@0x0217C4 | U16A4@0x0217CE |
|------|---------------|---------------|---------------|---------------|
| 2018/300 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2019/300 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2020/300 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2020/230 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2020/170 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2020/130 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2021/300 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2021/230 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2021/170 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |
| 2021/130 | 0x0231 OK | 0xD6A1 OK | 0xD6A8 OK | 0xD6A4 OK |

**DTC kodovi su na istim adresama u SVIM SW verzijama — 100% konzistentno.**

---

## Zaključak

### Pitanje iz audita: Dijele li U16Ax isti enable slot kao P0231?

**Za 300hp SW (10SW023910/040039/054296/066726): DA, djelomično.**

Dvije grupe:

| Grupa | Kodovi | Slot | En addr | En val | Dijele s P0231? |
|-------|--------|------|---------|--------|-----------------|
| A | P0231, U16A1, U16A2, U16A3, U16A5, U16A8, U16AB | 57 | 0x0210B9 | 0x06 | P0231 je referenca |
| B | P0232, U16A4, U16A7, U16A9, U16AA | 3 | 0x021083 | 0x00 | NE |

### Cross-SW konzistentnost

Sve 4 verzije 300hp SW (2018–2021) imaju **identično mapiranje**. Enable tablica je **identična bajt-za-bajt** u svim 10 analiziranih dumpova. DTC storage adrese su **identične** u svim SW verzijama.

### Preporuka za DTC OFF (300hp SW)

Za gasenje P0231: pisati **0x00 na adresu 0x0210B9** (slot 57).
**Kolateral**: ista adresa kontrolira i U16A1, U16A2, U16A3, U16A5, U16A8, U16AB — svi se gase zajedno.

P0232, U16A4, U16A7, U16A9, U16AA su vec **0x00** u originalnom binarnom — ne treba ih gasiti.

---

*Generirano automatski 2026-03-19 — samo čitanje, bez izmjena binarnih fajlova.*
*Skripte: `_materijali/dtc_cross_sw_audit.py`*
