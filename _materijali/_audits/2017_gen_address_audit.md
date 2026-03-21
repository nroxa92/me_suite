# 2017 Gen 4TEC 1503 — Address Audit

**Datum:** 2026-03-20
**Referentni SW:** 10SW012999 (2017/230hp SC 4TEC 1503)
**Referenca 2018:** 10SW025021 (2018/230hp SC 4TEC 1503)
**Metodologija:** Python binary scan + structural analysis + cross-dump verification

---

## Ključni nalaz

SW 10SW012999 ima **globalni CODE offset od -0x2AA (-682B)** za SC-specifične mape u odnosu na 2018 gen (10SW025021). Sve lambda/boost/fuel mape su uniformno pomaknute.

**Torque mape**: na ISTIM adresama kao 2018, ali mirror je ispred main-a (negativan offset).

---

## Potvrđene adrese

| Mapa | 2017 adresa | 2018 adresa | Delta | Napomena |
|------|-------------|-------------|-------|----------|
| `boost_factor` | **0x025B4E** | 0x025DF8 | -0x2AA | 40× u16LE flat 23130 (Q14=1.412) |
| `temp_fuel` | **0x025BA6** | 0x025E50 | -0x2AA | 156× u16LE Q14, varijabilna (12850–23130) |
| `lambda_main` | **0x026446** | 0x0266F0 | -0x2AA | 12×18 u16LE Q15, 0.986–1.033 |
| `lambda_main mirror` | **0x02695E** | 0x026C08 | -0x2AA | offset +0x518 od main |
| `lambda_trim` | **0x026B0E** | 0x026DB8 | -0x2AA | 12×18 u16LE Q15, 0.955–1.044 |
| `torque_main` | **0x02A0D8** | 0x02A0D8 | **0** | ISTA adresa! 16×16 u16BE Q8 |
| `torque mirror` | **0x029BC0** | 0x02A5F0 | -0xA38 | Ispred main-a (offset = -0x518) |

---

## Rev limiter

- **2017/230hp @ 0x028E94**: 5126 ticks = **8072 RPM**
- Napomena: adresa je 0x028E94 (2B ispred 2018 standardne 0x028E96)
- Isti pattern kao 2016 gen (10SW004675 ima isti offset!)
- 2018/230hp (10SW025021) @ 0x028E96 = 5399 ticks = 7664 RPM

---

## Detalji verifikacije

### boost_factor @ 0x025B4E
```
2017: [23130, 23130, 23130, 23130, ...] × 40 elem  ← TOCNO
2018: [23130, 23130, ...] × 40 elem @ 0x025DF8
```
Flat 23130 = Q14 × 1.412 = +41.2% SC boost korekcija.

### temp_fuel @ 0x025BA6
```
2017: [20817, 20817, ..., 23130, 21335, 19275, ...] varijabilna × 156 elem  ← TOCNO
2018: flat 23130 × 156 elem (nema temp korekcije)
```
2017 ima aktivnu temperature fuel correction (za razliku od flat 2018).

### lambda_main @ 0x026446
```
2017: 12×18 Q15 grid, range 0.986–1.033, 115 unikatnih vrijednosti  ← TOCNO
2018: 12×18 Q15 @ 0x0266F0, range 0.983–1.073
```
Mirror @ 0x02695E (= 0x026446 + 0x518), range 0.984–1.000.

### lambda_trim @ 0x026B0E
```
2017: 12×18 Q15, range 0.955–1.044  ← TOCNO
2018: 12×18 Q15 @ 0x026DB8, range 0.942–1.025
```

### torque_main @ 0x02A0D8
```
2017: 16×16 u16BE Q8, vrijednosti 128–154 (100–120%)  ← ISTA ADRESA
2018: 16×16 u16BE Q8, flat 128 (100%)
```
2017 ima aktivni torque map (nije flat). Mirror na 0x029BC0 = 0x02A0D8 - 0x518.
**Pažnja**: u 2017 mirror je ISPRED main-a (- offset), za razliku od 2018 gdje je iza (+ offset).

---

## Napomene za ostale 2017 gen SW-ove

- **10SW012502** (2017/260hp): DRUGAČIJI layout, boost @ 0x02437A, lambda main nije na 0x026446
- **10SW000776/778** (2016 gen): SASVIM DRUGAČIJI layout, adrese 0x025DF8–0x025E50 su prazne (nule)
- Offset -0x2AA je **specifičan za 10SW012999** — ne primjenjivati na druge SW varijante

---

## Ostale mape (nisu testirane)

Mape koje nisu bile problematične (vjerojatno na istim adresama kao 2018):
- `fuel_main` @ 0x022066 — nije testirana
- `ignition` @ 0x02B730 — nije testirana
- `lambda_adapt` @ 0x0268A0 — nije testirana (vjerovatno -0x2AA?)
- `sc_bypass` @ 0x0205A8 — nije testirana

**Preporuka**: za kompletnu analizu koristiti diff 2017 vs 2018 dump i primjeniti -0x2AA offset na sve adrese u regionu 0x025000–0x027000.
