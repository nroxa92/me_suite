# ME17Suite — ECU Tuning Tool

## O Projektu
- Bosch ME17.8.5 ECU tuning software za Rotax ACE 1630 (Sea-Doo 300)
- MCU: Infineon TC1762 (TriCore, Little Endian)
- Python 3.14 + PyQt6
- _materijal/_BRIEFING.md za kompletan kontekst projekta

## Memorija Map (sve su u CODE regiji 0x010000-0x05FFFF):
- RPM ose: 0x024F46, 0x025010, 0x0250DC (u16 BE, 16 tačaka)
- Rev limiter: 0x022096, 0x0220B6, 0x0220C0, 0x02B72A, 0x02B73E
- Ignition: 16× mapa od 0x02B730, svakih 144B, 12×12 u8, 0.75°/bit
- Injection: 0x02439C + mirror 0x02451C (12×32 u16 LE)
- Torque: 0x02A0D8 + mirror 0x02A5F0 (16×16 Q8)
- Lambda: 0x0266F0 + mirror 0x026C08 (12×18 Q15 LE)
- CAL regija (0x060000+) je TriCore BYTEKOD, ne kalibracija!

## Komande
- Pokreni: `python main.py` (iz me_suite foldera)
- Testovi: `python test/test_core.py`

## Struktura
- core/engine.py — load/save, read/write primitivi
- core/map_finder.py — 30 potvrđenih mapa, skeniranje
- core/map_editor.py — editovanje sa zaštitom
- core/checksum.py — CRC32 (checksum lokacije nepoznate)
- ui/main_window.py — PyQt6 GUI

## Pravila
- Svi importi su APSOLUTNI (from core.engine, ne from ..core.engine)
- Pokretati testove iz me_suite root foldera
- CAL regija je read-only — ne pisati tamo!
```

Sa ovim fajlom, Claude zna SVE o projektu od prve poruke — nema potrebe da svaki put objašnjavaš kontekst.

---

## 7. KLJUČNE KOMANDE U SESIJI

| Komanda | Opis |
|---|---|
| `/help` | Lista svih komandi |
| `/clear` | Nova sesija (resetuj kontekst) |
| `/compact` | Sažmi dugačku sesiju |
| `/config` | Podešavanja |
| `/bug` | Prijavi bug Anthropicu |
| `Ctrl+C` | Prekini trenutnu akciju |

---

## 8. PERMISSIONS — KAKO FUNKCIONIŠE

Kad Claude želi nešto napraviti, pitat će te:
```
Claude wants to edit: core/map_finder.py
Allow? [yes-always]