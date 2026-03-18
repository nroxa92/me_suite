# ME17Suite — Q&A Log

Kratki odgovori na specifična pitanja. Format: pitanje → odgovor (2-3 rečenice max).

---

**[2026-03-18]**
👤 Zašto nemamo definicije radnih sati u EEPROM?
🤖 Radni sati SU u EEPROM circular bufferu (iste adrese kao odometar: 064/063 @ 0x0562, 062 @ 0x5062), u minutama (u16 LE). Offset 0x0125 se ispostavilo da NIJE hw timer — sadrži SW konstantu ("60620", "BRP10", ili 0x00). UI sada prikazuje radne sate kao "Xh YYmin" pretvoreno iz minuta. Pravi non-changeable hw timer vjerojatno je u posebnom registru čipa, ne u EEPROM-u.

---

**[2026-03-17]**
👤 Folder 063 (Spark) vs 064 (1.6L) — ima puno edita, zašto?
🤖 063 i 064 su potpuno različiti motori (900cc 3-cil vs 1630cc 3-cil SC), pa i SW je drugačiji — drugačiji mapping tablica, DTC arhitektura, RPM osi, sve. Editi u 063 folderima su vjerojatno aftermarket tuni ili SW upgradei između HW revizija (npr. 063→064 konverzija za uništeni motor). Svaka konverzija mijenja firmware i HW tip u EEPROM.

---

**[2026-03-17]**
👤 Agent za 155hp mapu — da li je to analizirano?
🤖 Agent je pokrenut u prošloj sesiji ali rezultati nisu pročitani do kraja. U MAPA_ADRESE.md stoji "analizira agent" za GTI 155 adrese — pokrenut novi agent (GTI155 agent) u ovoj sesiji da kompletira analizu. Rezultati će biti dodani u doc kad budu gotovi.

---

**[2026-03-17]**
👤 Spark injection mapa — gdje je?
🤖 Binarni sken pokazuje beste kandidate @ 0x022E42 (16×16 u16 LE, raw=96-654) + mirror @ 0x023358 (offset +0x516, gotovo isti kao 300hp +0x518). Lambda/AFR mapa (open-loop, bez sondi): 4 kopije @ 0x025F5C / 0x02607E / 0x0261A0 / 0x0262C2 (8×16 u16 LE Q15, λ=0.737–1.004). Potvrda adresa je TODO — agent pokrenut.

---
