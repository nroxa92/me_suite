"""
ME17Suite — DTC opisi i mogući uzroci
Bosch ME17.8.5 / Sea-Doo Rotax ACE 1630 + 900

Format:
  DTC_INFO[code] = (description: str, causes: list[str])
  - description: kratki tehnički opis greške (EN)
  - causes:      mogući uzroci, od najvjerojatnijeg prema manje vjerojatnom (HR)

Svi kodovi su ECM (Engine Control Module) osim gdje je naznačeno.
"""

# (description, [uzrok1, uzrok2, ...])
_T = tuple[str, list[str]]

DTC_INFO: dict[int, _T] = {

    # ── MAP senzor (Manifold Absolute Pressure) ───────────────────────────────
    0x0106: (
        "MAP sensor signal out of plausible range — vrijednost postoji ali je van očekivanog opsega.",
        [
            "Vakuumska cijev na MAP senzoru raspukla, probijena ili slabo pritegnuta",
            "MAP senzor prljav ili kondenz blokira otvor",
            "Propuštanje kolektora (intake manifold leak) — lažni zrak",
            "MAP senzor defektan (zamjeniti PN 420856714)",
            "Konektor MAP senzora korodiran ili slabo spojen",
        ]
    ),
    0x0107: (
        "MAP sensor short circuit to ground — signal žica kratko spojena prema masi.",
        [
            "Oštećena izolacija signalnog kabela (trenje o motor, pregrijavanje)",
            "Defektan MAP senzor — unutarnji kratki spoj",
            "Konektor vlažan, korozija između pinova 2 i 3",
            "ECM pin oštećen",
        ]
    ),
    0x0108: (
        "MAP sensor open circuit or short to battery voltage — signal žica prekinuta ili kratko na +12V.",
        [
            "Konektor MAP senzora odspojen ili pin isklizao",
            "Prekinut signalni kabel (prignječen, prekinut)",
            "Defektan MAP senzor",
            "Kratki spoj signalne žice prema +12V (oštećena izolacija)",
        ]
    ),

    # ── IAT senzor (Intake Air Temperature) ──────────────────────────────────
    0x0112: (
        "IAT sensor short to ground — temperatura usisnog zraka signal kratko na masu.",
        [
            "Konektor IAT senzora kratko prema masi (vlaga, korozija)",
            "Defektan IAT senzor (u većini slučajeva integriran u MAP senzor)",
            "Signalni kabel oštećen, dodiruje šasiju",
        ]
    ),
    0x0113: (
        "IAT sensor open circuit or short to battery — temperatura usisnog zraka signal prekinut ili na +12V.",
        [
            "Konektor IAT senzora odspojen",
            "Prekinut signalni kabel",
            "Defektan IAT/MAP senzor (kombinovani senzor)",
            "ECM pin korodiran",
        ]
    ),

    # ── Coolant temperatura ───────────────────────────────────────────────────
    0x0116: (
        "Coolant temp sensor signal not plausible — temperatura ne prati očekivani obrazac (prebrzo grijanje/hlađenje).",
        [
            "Defektan CTS senzor (drift, nelinearna karakteristika)",
            "Loš termički kontakt senzora s kućištem (slabo pritegnut)",
            "Propuštanje rashladne tekućine u okolini senzora (mjehurići zraka)",
            "Konektor CTS senzora korodiran",
        ]
    ),
    0x0117: (
        "Coolant temp sensor short to ground — signal kratko na masu, ECM čita previsoku temperaturu.",
        [
            "Defektan CTS senzor — unutarnji kratki spoj",
            "Signalni kabel CTS senzora dodiruje masu (oštećena izolacija)",
            "Konektor vlažan ili korodiran",
        ]
    ),
    0x0118: (
        "Coolant temp sensor open circuit — signal prekinut, ECM čita prenisko temperaturu ili grešku.",
        [
            "Konektor CTS senzora odspojen ili pin isklizao",
            "Prekinut signalni kabel",
            "Defektan CTS senzor (otvorena veza)",
        ]
    ),
    0x0217: (
        "Coolant temperature too high detected — prekoračena temperatura rashladne tekućine.",
        [
            "Nedovoljno rashladne tekućine (water box, hladnjak, pumpa)",
            "Začepljen hladnjak ili filtar vode",
            "Defektna pumpa rashladne tekućine",
            "Termostat zaglavljen u zatvorenom položaju",
            "CTS senzor daje lažno visoke vrijednosti (provjeri P0117 zajedno)",
            "Preopterećenje motora (blokiran jet pump, previsoka ambijentalna temp)",
        ]
    ),

    # ── TPS (Throttle Position Sensor) ────────────────────────────────────────
    0x0122: (
        "TPS1 (primary throttle position sensor) signal short to ground.",
        [
            "Konektor TPS odspojen ili korodiran pin",
            "Signalni kabel TPS1 kratko na masu",
            "Defektan TPS sklop (u ETB aktuatoru)",
            "ECM pin oštećen",
        ]
    ),
    0x0123: (
        "TPS1 signal short to battery voltage — signal na +5V referenci ili +12V.",
        [
            "Kratki spoj TPS1 signalne žice prema Vref (+5V) ili +12V",
            "Defektan TPS sklop",
            "Kratki između signalnih žica u konektoru",
        ]
    ),
    0x0127: (
        "Intake air temperature too high — temperature usisnog zraka prešla granicu.",
        [
            "Blokiran dovod zraka (filter, usisna cijev)",
            "Pregrijani motor ili motorski prostor",
            "Defektan IAT senzor (lažno visoke vrijednosti)",
            "Provjeri i P0112/P0113",
        ]
    ),

    # ── Lambda / O2 senzor ────────────────────────────────────────────────────
    0x0130: (
        "Downstream O2 sensor general fault — lambda senzor iza katalizatora (ukoliko postoji) ne radi ispravno.",
        [
            "Defektan lambda senzor (starost, trovanje olovom ili silikonom)",
            "Provjeri žice senzora (kratki, prekidi)",
            "Propuštanje ispušnog sustava ispred senzora (lažni zrak)",
        ]
    ),
    0x0131: (
        "O2 sensor signal too low — lambda senzor pokazuje trajno bogatu mješavinu ili je signal pre nizak.",
        [
            "Defektan ili star lambda senzor",
            "Zagađenje senzora (ulje, antifriz u ispuhu)",
            "Propuštanje ispušnog sustava (lažno visok O2)",
            "Ubrizgivač propušta (fuel injector leaking)",
        ]
    ),
    0x0132: (
        "O2 sensor signal too high — lambda senzor pokazuje trajno siromašnu mješavinu ili signal pre visok.",
        [
            "Defektan lambda senzor",
            "Propuštanje gorivo (bogata mješavina uzrokuje visok napon senzora)",
            "Kratki spoj signalnog kabela prema Vref",
        ]
    ),
    0x0133: (
        "O2 sensor slow response — lambda senzor reagira presporo (zastarjeli senzor).",
        [
            "Star/istrošen lambda senzor (zamijeniti)",
            "Zagađenje senzora (silikonski preparati, ulje u gorivu)",
            "Oštećena grijana nit senzora (sporije zagrijavanje)",
        ]
    ),
    0x0135: (
        "O2 sensor heater circuit fault — grijač lambda senzora ne funkcionira.",
        [
            "Prekinuta ili kratko spojena žica grijača senzora",
            "Defektan lambda senzor (grijač otvoren)",
            "Konektor lambda senzora odspojen",
            "Istrošen relej napajanja grijača",
        ]
    ),

    # ── Adaptacija mješavine ──────────────────────────────────────────────────
    0x0171: (
        "Fuel mixture adaptation at upper lean limit — dugotrajna adaptacija dostigla gornju (lean) granicu.",
        [
            "Propuštanje zraka (intake manifold, crankcase vent, vakuumske cijevi)",
            "Začepljeni ili dotrajali injektori (mala količina ubrizgavanja)",
            "Defektan MAP ili MAF senzor (lažno niske vrijednosti)",
            "Propuštanje goriva prema naprijed (fuel pressure regulator, return line)",
            "Propuštanje ispušnog sustava ispred lambda senzora",
        ]
    ),
    0x0172: (
        "Fuel mixture adaptation at lower rich limit — dugotrajna adaptacija dostigla donju (rich) granicu.",
        [
            "Ubrizgivač propušta (leaking injector) — motor se gasi s bogatom mješavinom",
            "Preveliki tlak goriva (fuel pressure regulator defektan)",
            "Defektan lambda senzor (pokazuje lean, ECM dodaje gorivo)",
            "Propuštanje ulja u usisni kolektor (worn rings/valve seals)",
            "Aktivni ugljeni filter (kanister) propušta gorivo u usisni sustav",
        ]
    ),

    # ── Temperatura ulja ──────────────────────────────────────────────────────
    0x0197: (
        "Oil temperature sensor signal too low — senzor temperature ulja čita prenizku vrijednost ili signal kratak prema masi.",
        [
            "Defektan OTS senzor",
            "Kratki spoj signalnog kabela prema masi",
            "Konektor odspojen ili korodiran",
        ]
    ),
    0x0198: (
        "Oil temperature sensor signal too high — senzor temperature ulja čita previsoku vrijednost ili je signal prekinut.",
        [
            "Provjeri razinu i kvalitetu motornog ulja",
            "Defektan OTS senzor",
            "Otvoreni signalni kabel",
            "Stvarno pregrijanje ulja — provjeri rashladni sustav",
        ]
    ),

    # ── Injektori — napajanje ─────────────────────────────────────────────────
    0x0201: (
        "Injector 1 power stage open circuit — struja ubrizgivača 1 ne teče (prekid strujnog kruga).",
        [
            "Konektor injektora 1 odspojen ili pin isklizao",
            "Prekinuta žica injektora (vibracije, trenje)",
            "Defektan injektor 1 (otvorena zavojnica)",
            "ECM driver pin oštećen",
        ]
    ),
    0x0202: (
        "Injector 2 power stage open circuit — struja ubrizgivača 2 ne teče.",
        [
            "Konektor injektora 2 odspojen ili pin isklizao",
            "Prekinuta žica injektora",
            "Defektan injektor 2 (otvorena zavojnica)",
        ]
    ),
    0x0203: (
        "Injector 3 power stage open circuit — struja ubrizgivača 3 ne teče.",
        [
            "Konektor injektora 3 odspojen ili pin isklizao",
            "Prekinuta žica injektora",
            "Defektan injektor 3 (otvorena zavojnica)",
        ]
    ),

    # ── Gorivo pumpa ──────────────────────────────────────────────────────────
    0x0231: (
        "Fuel pump relay/driver open circuit or short to ground.",
        [
            "Defektan relej pumpe goriva",
            "Prekinuta žica upravljačkog signala pumpe",
            "Kratki spoj kabela pumpe prema masi",
            "Pumpa goriva defektna (unutarnji kratki)",
            "Konektor pumpe goriva korodiran (kabel u prtljažnom prostoru izložen vlazi)",
        ]
    ),
    0x0232: (
        "Fuel pump relay/driver short to battery voltage.",
        [
            "Kratki spoj kabela pumpe prema +12V",
            "Defektan relej pumpe (zalijepljeni kontakti)",
            "ECM driver pin oštećen",
        ]
    ),

    # ── Injektori — struja ────────────────────────────────────────────────────
    0x0261: (
        "Injector 1 open circuit or short to ground — niska strana injektora 1.",
        [
            "Prekinuta žica injektora 1 između ECM-a i injektora",
            "Kratki spoj žice prema masi",
            "Defektan injektor 1",
            "Konektor korodiran",
        ]
    ),
    0x0262: (
        "Injector 1 short to battery voltage — niska strana injektora 1 spojena na +12V.",
        [
            "Kratki spoj žice injektora 1 prema +12V",
            "Defektan ECM driver",
        ]
    ),
    0x0264: (
        "Injector 2 open circuit or short to ground.",
        [
            "Prekinuta žica injektora 2",
            "Kratki spoj prema masi",
            "Defektan injektor 2",
        ]
    ),
    0x0265: (
        "Injector 2 short to battery voltage.",
        [
            "Kratki spoj žice injektora 2 prema +12V",
            "Defektan ECM driver",
        ]
    ),
    0x0267: (
        "Injector 3 open circuit or short to ground.",
        [
            "Prekinuta žica injektora 3",
            "Kratki spoj prema masi",
            "Defektan injektor 3",
        ]
    ),
    0x0268: (
        "Injector 3 short to battery voltage.",
        [
            "Kratki spoj žice injektora 3 prema +12V",
            "Defektan ECM driver",
        ]
    ),

    # ── Tlak ulja ─────────────────────────────────────────────────────────────
    0x0298: (
        "Oil pressure derived fault — izračunati tlak ulja izvan prihvatljivog opsega (modelirani signal).",
        [
            "Niska razina motornog ulja — odmah provjeriti!",
            "Defektna pumpa ulja (istrošena)",
            "Začepljeni filtar ulja",
            "Propuštanje ulja (main seal, crankcase)",
            "Defektan tlačni prekidač/senzor ulja",
        ]
    ),

    # ── Misfire ───────────────────────────────────────────────────────────────
    0x0300: (
        "Multiple cylinder misfire detected — preskakanje paljenja detektirano na više cilindara.",
        [
            "Loše svjećice (istrošene, neispravan razmak)",
            "Defektne paljene zavojnice (coil pack)",
            "Zagađeni ili začepljeni injektori",
            "Propuštanje kompresije (worn rings/valves)",
            "Propuštanje usisnog kolektora (lean misfire)",
            "Loše gorivo (voda u gorivu, loš oktan)",
            "Defektan CKP senzor (krivi signal za sve cilindre)",
        ]
    ),
    0x0301: (
        "Cylinder 1 misfire detected — preskakanje paljenja na cilindru 1.",
        [
            "Svjećica cilindra 1 — istrošena ili kratko spojena",
            "Paljenja zavojnica cilindra 1 — defektna",
            "Injektor cilindra 1 — začepljen ili propušta",
            "Niska kompresija cilindra 1",
            "Provjeri kabl paljenja / konektor coila",
        ]
    ),
    0x0302: (
        "Cylinder 2 misfire detected — preskakanje paljenja na cilindru 2.",
        [
            "Svjećica cilindra 2",
            "Paljenja zavojnica cilindra 2",
            "Injektor cilindra 2",
            "Niska kompresija cilindra 2",
        ]
    ),
    0x0303: (
        "Cylinder 3 misfire detected — preskakanje paljenja na cilindru 3.",
        [
            "Svjećica cilindra 3",
            "Paljenja zavojnica cilindra 3",
            "Injektor cilindra 3",
            "Niska kompresija cilindra 3",
        ]
    ),

    # ── Knock senzor ─────────────────────────────────────────────────────────
    0x0325: (
        "Knock sensor fault — signal senzora detonacije izvan prihvatljivog opsega.",
        [
            "Defektan knock senzor (piezo element)",
            "Loše pritegnut knock senzor (moment: 20 Nm)",
            "Prekinut ili kratko spojen signalni kabel",
            "Jak mehanički šum motora maskira signal (istrošeni ležajevi)",
            "Loše gorivo (prenizak oktan, ECM retardira paljenje)",
        ]
    ),

    # ── CKP / CMP senzor ─────────────────────────────────────────────────────
    0x0335: (
        "Crankshaft position sensor (CKP) signal error — RPM signal nedostaje ili je neploziibilni.",
        [
            "Defektan CKP senzor",
            "Zazor CKP senzora preveć ili premalo (nominalno 0.5–1.5 mm)",
            "Oštećeni zubi na 60-2 kotaciću (trigger wheel)",
            "Prekinut ili kratko spojen kabel CKP senzora",
            "Konektor korodiran ili slabo spojen",
            "Jake EMI smetnje (oštećena paljenja zavojnica u blizini)",
        ]
    ),
    0x0340: (
        "Camshaft position sensor (CMP) signal error — signal bregaste osovine nedostaje ili je neplausibilan.",
        [
            "Defektan CMP senzor",
            "Oštećen trigger disk (rotor) na breg. osovini",
            "Prekinut kabel CMP senzora",
            "Prevelik zazor CMP senzora",
            "Rastegnutu lanac bregaste osovine (timing chain)",
        ]
    ),

    # ── Paljenje zavojnice ─────────────────────────────────────────────────────
    0x0357: (
        "Ignition coil 1 short to positive supply — niska strana coila 1 kratko na V+.",
        [
            "Kratki spoj žice prema +12V između ECM-a i coila 1",
            "Defektna paljenja zavojnica 1 (unutarnji kratki)",
            "ECM output driver oštećen",
        ]
    ),
    0x0358: (
        "Ignition coil 2 short to positive supply.",
        [
            "Kratki spoj žice prema +12V coila 2",
            "Defektna paljenja zavojnica 2",
        ]
    ),
    0x0359: (
        "Ignition coil 3 short to positive supply.",
        [
            "Kratki spoj žice prema +12V coila 3",
            "Defektna paljenja zavojnica 3",
        ]
    ),
    0x0360: (
        "Ignition power stage maximum error cylinder 3 — ECM ne može upravljati prim. strujom coila 3.",
        [
            "Defektna paljenja zavojnica 3 (unutarnji kratki/prekid)",
            "Kratki spoj ili prekid kabela paljenja cil. 3",
            "ECM output driver oštećen",
        ]
    ),
    0x0361: (
        "Ignition power stage maximum error cylinder 1.",
        [
            "Defektna paljenja zavojnica 1",
            "Kratki/prekid kabela cil. 1",
            "ECM driver oštećen",
        ]
    ),
    0x0362: (
        "Ignition power stage maximum error cylinder 2.",
        [
            "Defektna paljenja zavojnica 2",
            "Kratki/prekid kabela cil. 2",
            "ECM driver oštećen",
        ]
    ),

    # ── VSS (Vehicle Speed Sensor / brzina plovila) ───────────────────────────
    0x0500: (
        "Vehicle speed sensor open circuit — signal brzine nije primljen (otvoreni krug).",
        [
            "Konektor GPS/VSS modula odspojen",
            "Prekinut kabel VSS signala",
            "Defektan GPS/Hall senzor brzine",
        ]
    ),
    0x0501: (
        "Vehicle speed sensor signal fault — signal brzine van plausibilnog opsega ili neplausibilan u usporedbi s RPM.",
        [
            "Defektan senzor brzine (dPT/impeller speed sensor)",
            "Začepljen jet pump (propuštanje — nagle promjene brzine)",
            "Konektor labav ili korodiran",
            "Signalni kabel prolazi pokraj jakih EMI izvora",
        ]
    ),

    # ── Starter motor ─────────────────────────────────────────────────────────
    0x0512: (
        "Starter motor power stage fault — ECM ne može upravljati starterom ili detekcija greške u strujnom krugu.",
        [
            "Defektan relej startera",
            "Kratki spoj upravljačke žice startera",
            "Defektan starter motor",
            "Loša masa startera ili akumulatora",
        ]
    ),

    # ── DESS (Digital Encoded Security System) ────────────────────────────────
    0x0513: (
        "Invalid or unrecognized DESS key — ECM nije prepoznao DESS taster.",
        [
            "Neprogramiran DESS taster (potrebna programiranje kroz BUDS2)",
            "DESS taster nije taster koji pripada ovom plovilu",
            "Defektan DESS taster (pukao kontakt lanyard-a)",
            "DESS antenna (SAT/klaster) loša veza s ECM-om",
            "DESS modul na SAT-u defektan",
        ]
    ),

    # ── Tlak ulja — prekidač/senzor ───────────────────────────────────────────
    0x0520: (
        "Oil pressure switch functional problem — signal tlačnog prekidača ne odgovara očekivanom stanju.",
        [
            "Defektan prekidač tlaka ulja",
            "Niska razina ili tlak ulja (provjeri odmah!)",
            "Prekinuta ili kratko spojena žica prekidača",
            "Konektor korodiran",
        ]
    ),
    0x0523: (
        "Oil pressure sensor fault — signal senzora tlaka ulja izvan opsega.",
        [
            "Defektan senzor tlaka ulja",
            "Kratki spoj signalnog kabela",
            "Niska razina ulja — provjeri odmah",
            "Konektor odspojen",
        ]
    ),
    0x0524: (
        "Low oil pressure detected — stvarno niska razina/tlak ulja registriran.",
        [
            "ODMAH zaustaviti motor — niska razina ulja!",
            "Propuštanje ulja (seal, gasket, crankcase)",
            "Defektna pumpa ulja",
            "Začepljeni kanal za ulje ili filtar",
            "Pregrijanje (ulje previše rijetko)",
        ]
    ),

    # ── EGT senzor (Exhaust Gas Temperature) ─────────────────────────────────
    0x0544: (
        "EGT sensor open circuit or short to battery — senzor temperature ispušnih plinova isključen iz kruga.",
        [
            "Konektor EGT senzora odspojen",
            "Prekinuta žica senzora",
            "Kratki spoj signala prema +12V",
            "Defektan EGT senzor (K-type thermocouple ili NTC)",
        ]
    ),
    0x0545: (
        "EGT sensor short to ground — signal senzora EGT kratko na masu.",
        [
            "Signalni kabel EGT senzora kratko na masu",
            "Defektan EGT senzor",
            "Oštećena izolacija kabela (toplina ispušne cijevi)",
        ]
    ),
    0x0546: (
        "EGT sensor short to battery voltage.",
        [
            "Kratki spoj žice EGT senzora prema +12V",
            "Defektan EGT senzor",
        ]
    ),

    # ── Napon akumulatora ─────────────────────────────────────────────────────
    0x0560: (
        "Battery voltage not plausible — napon akumulatora nije u normalnom opsegu.",
        [
            "Defektan alternator/regulator napona",
            "Istrošen akumulator (visoka unutarnja otpornost)",
            "Loša masa (chassis ground) ili loša veza +'a",
            "Kratki spoj na nekom potrošaču",
        ]
    ),
    0x0562: (
        "Battery voltage too low — napon ispod minimalne granice (tipično <10.5V pri radu).",
        [
            "Istrošen akumulator",
            "Defektan alternator/punjač",
            "Loša veza masa kabela (visoka otpornost)",
            "Preoptrerećenje električne mreže (kratki spoj potrošača)",
        ]
    ),
    0x0563: (
        "Battery voltage too high — napon iznad maksimalne granice (tipično >15.5V).",
        [
            "Defektan regulator napona alternatora",
            "Alternator radi bez regulacije (puna pobuda)",
            "Loša masa alternatora (regulator misread napona)",
        ]
    ),

    # ── ECM interni ───────────────────────────────────────────────────────────
    0x0606: (
        "ECM ADC (Analog-Digital Converter) fault — interni ADC modul ECM-a daje greške.",
        [
            "Defektan ECM (hardverski ADC problem)",
            "Naponski skok koji je oštetio ECM",
            "Vibracije/vlaga koja uzrokuje intermitentan kontakt unutar ECM-a",
            "Ako se ponavlja — ECM treba zamjena ili reflash",
        ]
    ),
    0x0610: (
        "ECM variant coding fault — variantno kodiranje ECM-a nije ispravno.",
        [
            "ECM reflashiran s pogrešnom SW verzijom (mismatched variant)",
            "EEPROM kodiranje pogrešno (BUDS2 reprogramiranje potrebno)",
            "Defektan ECM EEPROM",
        ]
    ),
    0x062F: (
        "ECM EEPROM fault — greška pri čitanju/pisanju EEPROM memorije.",
        [
            "Defektan EEPROM čip unutar ECM-a",
            "Prekinuto napajanje tokom BUDS2 programiranja",
            "ECM je stariji i EEPROM je dostigao limit ciklusa pisanja",
        ]
    ),
    0x0650: (
        "ECM field ADC fault — ADC za mjerenje napona napajanja unutar ECM-a daje grešku.",
        [
            "Interni ADC problem u ECM-u",
            "Naponski skok oštetio ECM",
            "Uglavnom zahtijeva zamjenu ECM-a",
        ]
    ),

    # ── Lambda grijač ─────────────────────────────────────────────────────────
    0x1030: (
        "Lambda sensor heater power stage fault — ECM ne može upravljati grijačem lambda senzora.",
        [
            "Defektan lambda senzor (grijač otvorena veza)",
            "Prekinuta ili kratko spojena žica grijača senzora",
            "Defektan relej napajanja lambda grijača (ukoliko postoji)",
            "ECM driver pin za grijač oštećen",
        ]
    ),

    # ── Nadmorska visina / barometarski tlak ──────────────────────────────────
    0x1106: (
        "Altitude correction not plausible — barometarski tlak (BARO) nije konzistentan s MAP signalom.",
        [
            "Defektan MAP senzor (koristi se i za BARO mjerenje pri startu)",
            "Propuštanje usisnog kolektora (lažni MAP signal koji se uočava i kao BARO)",
            "ECM greška pri BARO kalibraciji (resetirati adaptacijske vrijednosti)",
        ]
    ),

    # ── TOPS (Tilt/Overturn Protection System) ────────────────────────────────
    0x1120: (
        "TOPS violation TPS2 — TPS2 signal izvan opsega pri TOPS nadzoru.",
        [
            "Defektan TPS sklop (TPS2 potenciometar)",
            "Kratki/prekid žice TPS2 signala",
            "ECM kalibracija TPS učena s greškom (potrebno re-učiti)",
        ]
    ),
    0x1130: (
        "Lambda sensor upstream catalyst fault — upstream lambda senzor (ispred kat.) ne funkcionira ispravno.",
        [
            "Defektan upstream lambda senzor",
            "Propuštanje ispušnog sustava ispred senzora",
            "Oštećena žica ili konektor senzora",
            "Trovanje senzora (silikonski aditivi u ulju)",
        ]
    ),
    0x1171: (
        "Additive mixture trim lean — aditivni trim lambda adaptacije dostigao lean granicu.",
        [
            "Propuštanje zraka (intake, crankcase vent)",
            "Začepljeni injektori",
            "Niski tlak goriva",
            "Provjeri zajedno s P0171",
        ]
    ),
    0x1172: (
        "Additive mixture trim rich — aditivni trim lambda adaptacije dostigao rich granicu.",
        [
            "Ubrizgivač propušta",
            "Previsok tlak goriva",
            "Defektan lambda senzor",
            "Provjeri zajedno s P0172",
        ]
    ),

    # ── TOPS prekidač ─────────────────────────────────────────────────────────
    0x1502: (
        "TOPS (tilt sensor) switch short to ground.",
        [
            "Defektan TOPS/G-senzor",
            "Kratki spoj signalnog kabela prema masi",
            "Konektor korodiran ili vlažan",
        ]
    ),
    0x1503: (
        "TOPS switch short to 12V.",
        [
            "Kratki spoj TOPS signalnog kabela prema +12V",
            "Defektan TOPS senzor",
        ]
    ),
    0x1504: (
        "TOPS switch open circuit — signal TOPS senzora nedostaje (otvoreni krug).",
        [
            "Konektor TOPS senzora odspojen",
            "Prekinut signalni kabel",
            "Defektan TOPS senzor",
        ]
    ),
    0x1505: (
        "TOPS switch active — plovilo detektirano prevrnuto ili u nagibu >45°.",
        [
            "Motor zaustavio normalno jer je plovilo prevrnjeno — nije greška",
            "Lažni alarm: vibracijski šok (skok, udar) aktivirao senzor",
            "Defektan TOPS senzor (zalijepljeni kontakti — uvijek prijavljuje aktivan)",
        ]
    ),
    0x1506: (
        "TOPS switch signal not plausible — signal TOPS senzora neplausibilan.",
        [
            "Defektan TOPS senzor",
            "Signalni kabel s intermitentnim kontaktom",
            "Korozija konektora",
        ]
    ),
    0x1509: (
        "TOPS functional fault — TOPS sustav ne može obaviti self-test pri pokretanju.",
        [
            "Defektan TOPS/G-senzor (akcel. čip ili elektronika)",
            "Provjeri napajanje i masu TOPS modula",
            "Konektor odspojen ili korodiran",
        ]
    ),

    # ── SC (Supercharger) tlak / senzor ───────────────────────────────────────
    0x1550: (
        "Boost/OLAS pressure sensor fault — senzor tlaka turbopunjača ili OLAS (On Lake Activation System) signal izvan opsega.",
        [
            "Defektan MAP/boost senzor (PN specifičan za SC motor)",
            "Vakuumska cijev na MAP senzoru raspukla ili odspojena",
            "Kratki spoj ili prekid kabela senzora",
            "Propuštanje SC intercoolera ili crijeva",
        ]
    ),

    # ── Elektronska leptirnica (ETB / e-Gas) ──────────────────────────────────
    0x1610: (
        "Throttle actuator power stage A fault — ECM ne može kontrolirati H-most fazu A ETB aktuatora.",
        [
            "Defektna elektronska leptirnica (ETB sklop)",
            "Kratki spoj ili prekid kabela faze A motora leptirnice",
            "ECM H-bridge driver oštećen",
            "Konektor ETB odspojen",
        ]
    ),
    0x1611: (
        "Throttle actuator power stage B fault — ECM ne može kontrolirati H-most fazu B ETB aktuatora.",
        [
            "Defektna elektronska leptirnica (ETB sklop)",
            "Kratki spoj ili prekid kabela faze B",
            "ECM H-bridge driver oštećen",
        ]
    ),
    0x1612: (
        "Throttle actuator return spring fault — ECM detektirao da opruga leptirnice ne zatvara leptir.",
        [
            "Istrošena ili puknuta opruga za povrat leptirnice",
            "Defektan ETB sklop (mehanički)",
            "Karbonski talog blokira kretanje leptirnice",
        ]
    ),
    0x1613: (
        "Throttle actuator default position fault — leptirnica se nije otvorila/zatvorila na zadanu poziciju.",
        [
            "Defektan ETB (motor ili mehanički dio)",
            "Karbonski talog blokira leptir",
            "TPS kalibracija potrebna (re-learn procedura)",
        ]
    ),
    0x1614: (
        "Throttle actuator position monitoring fault — razlika između TPS1 i TPS2 veća od dozvoljene.",
        [
            "Defektan TPS1 ili TPS2 (jedan od senzora daje krivu vrijednost)",
            "Labava TPS pločica (loose sensor rotor)",
            "Konektor TPS korodiran — intermitentni kontakt",
            "ECM TPS kalibracija pokvarena (resetirati i ponovo naučiti)",
        ]
    ),
    0x1615: (
        "Throttle actuator default check fault — self-test leptirnice pri pokretanju nije prošao.",
        [
            "Defektan ETB aktuator",
            "Karbonski talog ili mehanička prepreka",
            "Opruga za povrat slaba",
        ]
    ),
    0x1616: (
        "Throttle actuator learning fault — ECM nije mogao naučiti min/max poziciju leptirnice.",
        [
            "Mehanička prepreka u leptirnici",
            "Defektan ETB motor",
            "TPS kalibracija potrebna (BUDS2 Basic Setup)",
        ]
    ),
    0x1619: (
        "Throttle actuator upper limit fault — leptirnica ne može dostići gornju (otvorenu) granicu.",
        [
            "Mehanička prepreka (nečistoća, karbonski talog)",
            "Defektan ETB motor (slab)",
            "Pogrešno naučene granice — resetirati adaptacije",
        ]
    ),
    0x1620: (
        "Throttle actuator lower limit fault — leptirnica ne može dostići donju (zatvorenu) granicu.",
        [
            "Mehanička prepreka kod zatvorenog položaja",
            "Opruga previše čvrsta",
            "Defektan ETB",
        ]
    ),
    0x1621: (
        "Throttle actuator adaptation aborted — učenje pozicija leptirnice prekinuto.",
        [
            "Motor se ugasio tokom procedure učenja",
            "TPS signal intermitentni tokom učenja",
            "Defektan ETB",
        ]
    ),
    0x1622: (
        "Throttle actuator repeated adaptation abort — učenje leptirnice prekinuto više puta uzastopno.",
        [
            "Trajni mehanički problem ETB-a",
            "TPS kvar koji uzrokuje ponovljene prekide",
            "Zamjeniti ETB sklop",
        ]
    ),

    # ── DESS komunikacija ─────────────────────────────────────────────────────
    0x1647: (
        "DESS key communication fault A — greška u komunikacijskom protokolu DESS sustava (faza A).",
        [
            "Defektan DESS taster",
            "Korozija na DESS taster anteni (na ključu upravljača)",
            "Defektan DESS modul u SAT/klasteru",
            "CAN bus problem između ECM-a i DESS modula",
        ]
    ),
    0x1648: (
        "DESS key communication fault B.",
        [
            "Defektan DESS taster",
            "Antena DESS modula odspojena",
            "Defektan DESS modul",
        ]
    ),
    0x1649: (
        "DESS key communication fault C.",
        [
            "Defektan DESS taster (zamjeniti)",
            "Defektan DESS modul",
        ]
    ),
    0x1651: (
        "DESS key voltage too low — napon napajanja DESS modula ispod minimuma.",
        [
            "Slab akumulator (ispod 10.5V pri startu)",
            "Loša masa DESS modula",
            "Prekinut pozitivni kabel napajanja DESS modula",
        ]
    ),
    0x1652: (
        "DESS key voltage too high — napon napajanja DESS modula previsok.",
        [
            "Defektan regulator napona alternatora",
            "Provjeri P0563 zajedno",
        ]
    ),
    0x1654: (
        "DESS key signal out of range — signalni napon DESS tasterice van opsega.",
        [
            "Defektan DESS taster (istrošen kontakt lanyard konekcije)",
            "Korozija na DESS anteni/konektoru",
            "Defektan DESS modul",
        ]
    ),
    0x1657: (
        "DESS key signal fault A.",
        [
            "Defektan DESS taster",
            "Korozija ili vlaga u DESS anteni",
        ]
    ),
    0x1658: (
        "DESS key signal fault B.",
        [
            "Defektan DESS taster",
            "Defektan DESS antena/modul",
        ]
    ),

    # ── iBR (Intelligent Brake and Reverse) ───────────────────────────────────
    0x1661: (
        "iBR system malfunction — iBR modul (reverzno/kočno lopatica) prijavio grešku ECM-u.",
        [
            "Defektan iBR modul ili aktuator",
            "CAN komunikacija između ECM-a i iBR modula prekinuta",
            "iBR loptice/lopatice mehanički blokirane (nečistoća, kavitacija)",
            "Napajanje iBR modula — provjeri osigurač i relej",
        ]
    ),
    0x1662: (
        "iBR torque request not plausible — ECM primio torque request od iBR-a koji nije konzistentan s trenutnim stanjem.",
        [
            "Defektan iBR modul (kriva CAN poruka)",
            "CAN bus smetnje (kratki spoj CAN H/L žica)",
            "iBR modul treba software update (BUDS2)",
        ]
    ),

    # ── Glavni relej ──────────────────────────────────────────────────────────
    0x1679: (
        "Main relay sticking — ECM detektirao da se glavni relej nije otvorio nakon isključivanja.",
        [
            "Defektan glavni relej (zalijepljeni kontakti)",
            "Kratki spoj između napajanja relejnog izlaza i +12V",
            "Previsoka temperatura relejnog prostora",
        ]
    ),

    # ── EGT senzor B (alternativni senzor) ───────────────────────────────────
    0x2080: (
        "EGT sensor B signal too low — drugi EGT senzor (ukoliko postoji) čita prenizku vrijednost.",
        [
            "Kratki spoj signalnog kabela prema masi",
            "Defektan EGT senzor B",
            "Konektor korodiran",
        ]
    ),
    0x2081: (
        "EGT sensor B signal too high — drugi EGT senzor čita previsoku vrijednost ili signal prekinut.",
        [
            "Otvoreni krug EGT senzora B",
            "Defektan senzor B",
            "Previsoke temperature ispuha (lean mixture, misfire)",
        ]
    ),

    # ── TPS2 kratki spoj ─────────────────────────────────────────────────────
    0x0222: (
        "TPS2 (secondary throttle position sensor) short circuit to ground.",
        [
            "Kratki spoj TPS2 signalnog kabela prema masi",
            "Defektan TPS sklop (TPS2 potenciometar)",
            "Konektor TPS korodiran ili vlažan",
        ]
    ),
    0x0223: (
        "TPS2 short circuit to battery voltage — TPS2 signal spojen na +5V referencu ili +12V.",
        [
            "Kratki spoj TPS2 signalne žice prema Vref (+5V) ili +12V",
            "Defektan TPS2",
            "Kratki između signalnih pinova u konektoru",
        ]
    ),

    # ── TPS2 električni opseg ─────────────────────────────────────────────────
    0x212C: (
        "TPS2 electrical lower range fault — TPS2 signal ispod minimalne električne vrijednosti.",
        [
            "Kratki spoj TPS2 signala prema masi",
            "Defektan TPS2 (klizač)",
            "Konektor TPS korodiran",
        ]
    ),
    0x212D: (
        "TPS2 electrical upper range fault — TPS2 signal iznad maksimalne električne vrijednosti.",
        [
            "Kratki spoj TPS2 prema Vref (+5V)",
            "Defektan TPS2",
            "Konektor TPS s kratkim između pinova",
        ]
    ),

    # ── TAS (Throttle Angle Sensor) ───────────────────────────────────────────
    0x2159: (
        "TAS (Throttle Angle Sensor) synchronization error — razlika između TPS1 i TAS veća od dozvoljene.",
        [
            "Defektan TAS senzor (ručica gasa / handlebar)",
            "Labav kabel TAS senzora",
            "Korozija konektora TAS-a",
            "TPS kalibracija potrebna zajedno s TAS",
        ]
    ),

    # ── Propuštanje usisa ─────────────────────────────────────────────────────
    0x2279: (
        "Air intake manifold leak detected — ECM detektirao lažni zrak u usisnom kolektoru.",
        [
            "Pukla ili odspojena vakuumska cijev (PCV, EVAP, brake servo, MAP)",
            "Oštećena brtva usisnog kolektora",
            "Propuštanje EGR ventila (ukoliko postoji)",
            "Rastreseni vijci intake manifolda",
            "Oštećen TPS O-ring (gdje manifold prolazi kroz throttle body)",
        ]
    ),

    # ── Visoka temperatura ispuha ─────────────────────────────────────────────
    0x2428: (
        "High EGT (exhaust gas temperature) detected — temperatura ispušnih plinova prekoračila gornju granicu.",
        [
            "ODMAH smanjiti gas — moguće oštećenje motora",
            "Lean mješavina (propuštanje zraka, začepljeni injektori, niski tlak goriva)",
            "Preskakanje paljenja (misfire uzrokuje gorenje u ispuhu)",
            "Blokiran ispušni sustav",
            "Katalizator pregrijava ispuh (ako je start/stop vožnja)",
        ]
    ),

    # ── ECM RTC / satovnik ────────────────────────────────────────────────────
    0x2610: (
        "ECM RTC (Real Time Clock) fault — interni satovnik ECM-a ne funkcionira ispravno.",
        [
            "Istrošena backup baterija ECM-a (ukoliko postoji)",
            "Defektan RTC čip unutar ECM-a",
            "Ako se ponavlja — ECM treba zamjena",
        ]
    ),

    # ── TPS plausibilnost ─────────────────────────────────────────────────────
    0x2620: (
        "TPS value not plausible — TPS signal ne odgovara opterećenju motora i ostalim senzorima.",
        [
            "Defektan TPS sklop (nelinearna karakteristika)",
            "Karbonski talog na leptirnici (fizička pozicija ne odgovara TPS-u)",
            "Kalibracija TPS potrebna (BUDS2 Basic Setup)",
        ]
    ),
    0x2621: (
        "TPS electrical lower range fault — TPS1 signal ispod minimalne električne vrijednosti.",
        [
            "Kratki spoj TPS1 signala prema masi",
            "Defektan TPS1",
            "Konektor odspojen ili korodiran",
        ]
    ),
    0x2622: (
        "TPS electrical upper range fault — TPS1 signal iznad maksimalne električne vrijednosti.",
        [
            "Kratki spoj TPS1 prema Vref (+5V) ili +12V",
            "Defektan TPS1",
        ]
    ),
}
