# 2016 gen 1503 — SC mape — scan rezultati
Datum: 2026-03-21

## SC correction

- 2018+ adresa: 0x02220E (ref: 10SW025021)
- **2016 gen adresa: 0x023478** — PRONAĐENO (8B signature hit)
- Vrijedi za: 10SW000778 (2016 260hp), 10SW000776 (2016 215hp), 10SW012502 (2017 260hp)
- 2017/230 (10SW012999): 0x0221FA (−14B od 2018, u skladu s −0x2AA offset za tu SW)
- Verifikacija: min=16771 (Q14=1.024), max=30900 (Q14=1.886) — u smislenom SC rasponu
- Razlika vs 2018 ref (24/63 elem): kalibracijska razlika, format identičan (9×7 u16 LE Q14)
- **215hp == 260hp == 2017/260**: identične vrijednosti (0/63 razlika)
- Razlika adrese vs 2018: +0x126A = +4714B

### Offset tablica SC correction

| SW | Model | Adresa | Offset vs 2018 |
|----|-------|--------|----------------|
| 10SW025021 | 2018 230hp SC | 0x02220E | ref |
| 10SW012999 | 2017 230hp SC | 0x0221FA | −14B |
| 10SW000778 | 2016 260hp SC | 0x023478 | +4714B |
| 10SW000776 | 2016 215hp SC | 0x023478 | +4714B |
| 10SW012502 | 2017 260hp SC | 0x023478 | +4714B (2016 gen layout!) |

---

## SC boost factor

- 2018+ adresa: 0x025DF8 (ref: 10SW025021), flat 23130 = Q14×1.412 (+41.2%)
- 2017/230 adresa: 0x025B4E — POTVRĐENO (10SW012999, −0x2AA od 2018)
- **2016 gen adresa: 0x02619C — NEPOTVRDENO (jedini kandidat)**
  - Flat vrijednost: 23130 (Q14=1.412, +41.2%) — isti kao 2018/2017
  - 44 elementa umjesto 40 (format razlika vs 2018+)
  - Pre-kontekst: lambda/Q14 vrijednosti (~0.80–0.96), NE rastuci X-os niz
  - X-os boost iz 2018 (50 57 5d 64 6b 71 78 7f 85 8c 93 99 a0 a7 ad bb) **nije pronaden** u 2016 gen
  - Razlika adrese vs 2018: +0x03A4 = +932B
- Vrijedi za: 10SW000778, 10SW000776, 10SW012502 (svi imaju flat 5a5a na 0x02619C, 44 elem)

### Status: NEPOUZDANO

Flat 5a5a @ 0x02619C je jedini 23130-flat niz u CODE regiji 2016 gen binarija.
Kontekst ispred nije standardni X-os (nije rastuci kPa niz kao u 2018+).
Moguće interpretacije:
1. SC boost_factor postoji ali s drugačijim X-osijem i 44 elementima (2016 gen specifičan format)
2. Flat 5a5a je dio neke druge tablice koja slučajno ima iste vrijednosti
3. 2016 gen nema odvojenu 1D boost_factor tablicu (boost hardkodiran drugačije)

Bez poznatog X-osi strukturom, pisanje na 0x02619C nije preporučljivo.

---

## Metoda

### SC correction
- Signature (8B pre): `c05d606d007dd084` → jedinstven hit u 2016 gen
- Referentni fajl: 10SW025021 (2018/4tec1503/230.bin)
- Hit adresa: 0x023470 → mapa @ 0x023470+8 = 0x023478
- Verifikacija: Q14 raspon [1.024–1.886] konzistentan s SC correction formatom

### SC boost factor
- Signature (8B pre): `9399a0a7adbb5a5a` → NUL hit u 2016 gen (X-os razlicita)
- Flat-5a5a scan: jedini blok ≥38 elemenata u CODE regiji je @ 0x02619C (44 elem)
- Referentni fajl: 10SW025021 (2018) i 10SW012999 (2017/230) za usporedbu

---

## Napomene za implementaciju

- `sc_corr` u map_finder.py: za 2016 gen koristiti 0x023478 (ne 0x02220E)
- `boost_factor` za 2016 gen: treba dodatno istraživanje — ne implementirati bez potvrde
- 10SW012502 (2017 260hp) = 2016 gen layout, adrese identične 2016 gen (ne 2018!)
- 10SW012999 (2017 230hp) = hibridni layout: SC corr na 0x0221FA (≈2018), boost na 0x025B4E (−0x2AA)
