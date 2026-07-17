---
date: 2026-07-14
updated: 2026-07-17
topic: kaardikihid-ja-legend
---

# Kaardikihtide ja legendi ümberkujundus

## Summary

Terrapoint säilitab rahuliku, ametlikele allikatele toetuva kaardi ning lisab tulemuste lehele faktipõhised kiirvastused, õigesti nimetatud andmeajastuse ja selged arhiivikihi olekud. Kasutaja saab lehel juba nähtava fakti kohta kohese vastuse ilma AI-analüüsi ootamata ning näeb, millise aja, allika ja tõlgenduspiiriga number kehtib.

---

## Problem Frame

Praegune kaart kuvab suure hulga eri allikatest pärinevaid kihte ühe pika lülitite loendina. Omanik peab ise teadma, milline kiht vastab tema küsimusele, kuidas sarnaseid piiranguallikaid omavahel tõlgendada ja kas kaardil puuduv objekt tähendab tegelikku puudumist või ajutiselt kättesaamatut allikat.

Kahel eraldi legendil on erinev loogika. Eraldiste värvid nimetavad raieliike, kuigi värv tuleneb peamiselt puistu vanusest ja raievanusest, ning metsateatis ei tõenda töö teostamist. See võib muuta registriandmetel põhineva hinnangu näiliselt kindlamaks ja tegevussoovituse konkreetsemaks, kui alusandmed lubavad.

Mobiilis võtavad eraldi juhtpaneelid ja legendid piiratud kaardipinnast ebaproportsionaalselt palju ruumi. Samal ajal laetakse kinnistu avamisel ka valikuliste kihtide andmeid, kuigi kasutaja ei pruugi neid vaadata ja mõne välise allika tõrge ei peaks põhivaadet takistama.

Tulemuste lehel kuvatakse mitu konkreetset registrifakti, kuid nende ajakontekst ei ole ühtlane. Maa maksustamishinna juures puudub hindamismudeli aasta ja väärtuse kehtivuse algus; päringu või Terrapointi kontrolli aega ei tohi esitada andmete enda kuupäevana.

AI-nõustaja saadab ka lehel juba nähtava numbri küsimuse pika mudelianalüüsi kaudu. Näiteks maa maksustamishinna kordamine ei vaja uut järeldust, kuid kasutaja näeb vastust oodates sama „Mõtleb” olekut nagu keerulise metsandussoovituse puhul.

Ajaloolise lageraie nähtav olek „Ei kattu kihiga” ei ütle, millist perioodi kontrolliti, ning võib praegu varjata ka allika tõrget. Kontaktlingi tavaline ankrukerimine jätab väikese kontaktiploki vaate ülaserva, kuigi selle keskne paigutus oleks loetavam.

---

## Actors

- A1. Metsaomanik: hindab kinnistu olukorda, piiranguid, riske ja järgmisi võimalikke samme ilma GIS-alase eelteadmiseta.
- A2. Metsandusnõustaja või haldaja: kasutab sama kaarti otsuse selgitamiseks ning peab nägema andmeallikat, ajakohasust ja tõlgenduspiiri.

---

## Key Flows

- F1. Kinnistu esmane ülevaade
  - **Trigger:** A1 valib kinnistu otsingu või kaardikliki kaudu.
  - **Actors:** A1
  - **Steps:** Eelmise kinnistu ruumiandmed eemaldatakse; kaart avab „Ülevaate”; kaart näitab ametlikku ortofotot, kinnistu piiri, eraldisi ja kinnistuga kattuvaid olulisi piiranguid; üks legend selgitab nähtavaid sümboleid ja andmete staatust; kasutaja saab eraldise või piirangu kohta lisainfot avada.
  - **Outcome:** A1 saab ilma kihte seadistamata aru, kus kinnistu ja eraldised asuvad ning millised olulised asjaolud vajavad tähelepanu.
  - **Covered by:** R1, R2, R3, R7, R8, R9, R13, R14

- F2. Otsusepõhise vaate valimine
  - **Trigger:** A1 või A2 soovib uurida teostatavust, piiranguid, riske, toetusi või ajalugu.
  - **Actors:** A1, A2
  - **Steps:** Kasutaja valib sobiva vaate; kaart aktiveerib selle küsimuse jaoks määratud teemad; kasutaja võib teemasid lisada või eemaldada; muudetud vaade säilitab lähtevaate nime ja tähistatakse kohandatuna; lähtevaate või „Ülevaate” saab ühe selge toiminguga taastada.
  - **Outcome:** Kaardil on korraga nähtav otsuse jaoks vajalik, mitte kogu saadaolev ruumiinfo.
  - **Covered by:** R4, R5, R6, R14

- F3. Andmeusalduse kontroll
  - **Trigger:** A1 või A2 vaatab aktiivse teema tähendust või märkab, et oodatud objekte ei kuvata.
  - **Actors:** A1, A2
  - **Steps:** Ühine legend näitab teema allikaid, ajaseisu ja tõlgenduspiiri; täielik nulltulemus, osaline tulemus, allika tõrge ja kärbitud tulemus on üksteisest eristatavad; valikulise allika tõrge ei takista ülejäänud kaardi kasutamist.
  - **Outcome:** Kasutaja ei tõlgenda tehnilist puudujääki ekslikult piirangu, riski või ajaloolise sündmuse puudumisena.
  - **Covered by:** R7, R8, R10, R11, R12, R13

- F4. Lehel nähtava fakti küsimine
  - **Trigger:** A1 küsib AI-nõustajalt üheselt vastatavat kinnistufakti, mis on otsingutulemuses juba olemas.
  - **Actors:** A1
  - **Steps:** Terrapoint tunneb ära toetatud faktiküsimuse; vastab samast laaditud kinnistuandmest ilma mudelianalüüsita; näitab vastuse päritolu, ühikut ja olulist tõlgenduspiiri; säilitab küsimuse vestluse ajaloos.
  - **Outcome:** A1 saab kontrollitava vastuse praktiliselt kohe ja eristab selle AI koostatud analüüsist.
  - **Covered by:** R19, R20, R21, R22

- F5. Ajaloolise lageraie tulemuse tõlgendamine
  - **Trigger:** A1 vaatab tulemuste lehel ajaloolise lageraie kontrolli.
  - **Actors:** A1, A2
  - **Steps:** Terrapoint näitab kontrollitud perioodi; eristab leitud vaste, täieliku nulltulemuse, osalise kontrolli ja allika tõrke; selgitab, et arhiivikiht ei tõenda lageraie puudumist muul ajal ega tänast metsaseisundit.
  - **Outcome:** A1 ei tõlgenda piiratud arhiivikihti täieliku raieajaloo ega allikatõrget nulltulemusena.
  - **Covered by:** R23, R24

- F6. Kontaktini liikumine
  - **Trigger:** A1 valib päise või mobiilimenüü kontaktlingi.
  - **Actors:** A1
  - **Steps:** Menüü sulgub vajadusel; leht kerib kontaktiploki nähtava vaate keskossa, arvestades kleepuvat päist ja kasutaja vähendatud liikumise eelistust.
  - **Outcome:** Kontaktiploki pealkiri, selgitus ja e-posti link on korraga nähtavad.
  - **Covered by:** R25

---

## Product Model

| Mõiste | Tähendus kasutajale |
|---|---|
| Vaade | Nimega teemakomplekt. Vaated on „Ülevaade” ning viis otsusepõhist vaadet: „Teostatavus”, „Piirangud”, „Riskid”, „Toetused” ja „Ajalugu”. |
| Teema | Kasutaja lülitatav tähenduslik kaardiülekate, näiteks „Vesi ja kaldapiirangud”. Iga aktiivne teema saab legendirea; „Ülevaate” veel kinnitamata piirangukontrollid võivad olla koondatud ühisele kontrollireale. |
| Allikas | Üks või mitu ametlikku andmestikku, millest teema koosneb. Allikas on legendi detail, mitte eraldi põhijuhtimine. |
| Püsikontekst | Valitud kinnistu piir ja metsaeraldised. Need ei ole kasutaja lülitatavad teemad ning neil on legendis eraldi read ja eraldi andmeolekud. |
| Kohandatud vaade | Vaade, mille teemakomplekti kasutaja muutis. Nimi säilitab lähtevaate, näiteks „Ajalugu · kohandatud”. |

Eri õigusliku või praktilise tähendusega kattuvused jäävad eraldi teemadeks. Üheks teemaks võib koondada ainult sama asjaolu dubleerivad allikad; allikate lahknevus või puudulik katvus jääb teema detailis nähtavaks.

---

## Requirements

**Vaikeseis ja vaated**

- R1. Kinnistu avamisel peab kaart kasutama rahulikku „Ülevaate” vaikeseisu: ametlik Maa- ja Ruumiameti ortofoto, valitud kinnistu piir, ametlikud metsaeraldised ning ainult kinnistuga kattuvad olulised piirangud.
- R2. Aluskaart peab olema ülekatetest eraldi valitav. Ametlik ortofoto on vaikimisi aluskaart; olemasolevad alternatiivsed aluskaardid võivad jääda valikusse ainult selgelt nimetatud pakkuja ja ajaseisuga. Aluskaardi vahetamine ei muuda vaadet kohandatuks.
- R3. Vaikeseisus on piirang „oluline”, kui see kattub valitud kinnistu või eraldisega ja võib muuta tegevuse lubatavust, ajastust, viisi, väärtust või toetuse võimalikkust. Sama asjaolu dubleerivad allikad tuleb kasutajale koondada üheks arusaadavaks kokkuvõtteks.
- R4. Kaart peab pakkuma „Ülevaadet” ja viit otsusepõhist vaadet alloleva teemakomplektiga. „Teostatavus” on üldine eelsõel asjaoludest, mis võivad metsatöid mõjutada, mitte konkreetse töö õiguslik hinnang.

| Kaardielement | Ülevaade | Teostatavus | Piirangud | Riskid | Toetused | Ajalugu |
|---|---|---|---|---|---|---|
| Kinnistu piir (püsikontekst) | Alati | Alati | Alati | Alati | Alati | Alati |
| Metsaeraldised (püsikontekst) | Alati | Alati | Alati | Alati | Alati | Alati |
| Looduskaitse | Olulisel kattuvusel | Sees | Sees | Väljas | Sees | Väljas |
| Liigid ja elupaigad | Olulisel kattuvusel | Sees | Sees | Väljas | Sees | Väljas |
| Vesi ja kaldapiirangud | Olulisel kattuvusel | Sees | Sees | Väljas | Väljas | Väljas |
| Muinsuskaitse ja muud tegevuspiirangud | Olulisel kattuvusel | Sees | Sees | Väljas | Väljas | Väljas |
| Üleujutus ja märgalad | Väljas | Sees | Sees | Sees | Väljas | Väljas |
| Metsatervise riskid | Väljas | Väljas | Väljas | Sees | Väljas | Väljas |
| Võõrliigid | Väljas | Väljas | Väljas | Sees | Väljas | Väljas |
| Toetuse ruumilised indikaatorid | Väljas | Väljas | Väljas | Väljas | Sees | Väljas |
| Metsateatised | Väljas | Väljas | Väljas | Väljas | Väljas | Sees |
| Lageraietuvastus 2011–2016 | Väljas | Väljas | Väljas | Väljas | Väljas | Sees, arhiivina |

„Olulisel kattuvusel” tähendab, et „Ülevaade” kontrollib alati kõiki nii märgitud teemasid, kuid joonistab kaardile ainult kinnitatud kattuvused. Legendis on alati üks mitteeemaldatav koondrida „Piirangute kontroll”; kinnitatud ja nähtavad kattuvused saavad lisaks oma teemarea, täieliku nulltulemusega teemad jäävad koondrea detaili. Kuni mõni kontroll laadib, on koondolek „Laadib”; pärast kõigi kontrollide lõppu on see kas „Olulisi kattuvusi ei leitud”, „Leiti X olulist teemat” või mistahes puuduliku kontrolli korral „Piirangute kontroll osaline”. Mõjutatud teema ja selle korduskatse on koondrea detailis nähtavad. Ükski ebaõnnestunud kontroll ei tohi kaduda selle tõttu, et kattuvust ei suudetud kinnitada.

„Toetuse ruumilised indikaatorid” loeb vasteks ametliku toetuse sihtala kattuvuse või praeguse toetuste analüüsi reegli, mis seob kontrollimist vajava tingimuse konkreetse kinnistu või eraldisega. Ametlik geomeetria kuvatakse ülekattena, eraldisepõhine tuletis vastava eraldise juures ja ainult kinnistutasemel teada olev indikaator legendi detailis märkega „Kinnistu tasemel”; teadmata asukohale ei lisata oletuslikku kaardisümbolit. Teema kasutab silti „Indikaatorid leitud”, mitte toetuskõlblikkuse kinnitust. Terrapointi tuletatud sobivussignaal peab olema nii tähistatud ning muu toetuse info jääb tulemuste lehe toetuste osasse.

- R5. Vaate valimine taastab selle tabelis määratud teemakomplekti. Teema käsitsi lisamisel või eemaldamisel säilitab liides lähtevaate nime ja lisab „kohandatud” oleku; sama vaate uuesti valimine taastab selle algse komplekti. „Ülevaate” kohustuslik piirangukontroll ei ole eemaldatav: leitud teema väljalülitamine peidab selle ülekatte, kuid koondrida säilitab hoiatuse „X kattuvust peidetud”. „Taasta ülevaade” taastab „Ülevaate” nähtavad teemad, kuid ei muuda kasutaja valitud aluskaarti.
- R6. Kasutaja lülitab teemasid, mitte üksikuid tehnilisi allikaid. Järved, vooluveed ning vee- ja kaldakaitse asjaolud kuuluvad teemasse „Vesi ja kaldapiirangud”; sama kaitseala dubleerivad kirjed võib koondada, kuid eri tähendusega piiranguid ei tohi üksnes ruumilise kattuvuse tõttu üheks muuta. 2011–2016 lageraietuvastus on saadaval ainult „Ajaloo” lähtevaates, säilib olekus „Ajalugu · kohandatud”, eemaldub teise vaate valimisel ja peab olema tähistatud arhiiviandmena.

**Legend ja tähendus**

- R7. Kaardil peab olema üks ühine legend eraldi kinnistu piiri, metsaeraldiste ja aktiivsete teemade ridadega. Iga teemarida näitab vähemalt kaardisümbolit, inimkeelset nimetust, tulemi olekut ja tõlgenduspiiri; avatav detail näitab kõiki teema ametlikke allikaid, nende andmete ajaseisu või viimase kontrolli aega ning kattuvuse ulatust valitud kinnistu või eraldistega. Teema vasted ja olek käivad valitud kinnistu, mitte parajasti nähtava kaardiakna kohta; kaardi nihutamine ei laienda analüüsi ruumilist ulatust.
- R8. Aktiivne teema peab legendis säilima ka vaste puudumise või allikaprobleemi korral. Tulemi olek määratakse kogu teema allikate põhjal ja võib koos nähtavate vastetega näidata puudulikku katvust:

| Allikate tulemus | Kasutajale nähtav olek |
|---|---|
| Vähemalt üks vajalik allikas alles laadib ja varasemat kehtivat tulemust pole | Laadib |
| Korduskatse või värskendamine käib ja varasem kehtiv tulemus on olemas | Uuendab; varasemad vasted jäävad nähtavaks ja on märgitud eelmise tulemina |
| Kõik vajalikud allikad vastasid täielikult, vasteid pole | Vasteid ei leitud |
| Kõik vajalikud allikad vastasid täielikult, vasted on olemas | Vasted leitud |
| Vähemalt üks kasutatav vaste on olemas, kuid sama või teine vajalik allikas ebaõnnestus, sisaldas kasutuskõlbmatuid objekte või kärbiti | Vasted leitud · osaline |
| Vasteid pole, kuid vähemalt üks vajalik allikas andis kasutatava vastuse ja sama või teine vajalik allikas ebaõnnestus või kärbiti | Puudumist ei saa kinnitada · osaline |
| Ükski vajalik allikas ei andnud kasutatavat tulemust | Allikas ei vasta · proovi uuesti |

- R9. Eraldiste põhivärv peab kirjeldama Terrapointi tuletatud vanuse suhet arvutuslikku raievanusesse, mitte soovitatud raiemeetodit: „Noor” alla 50%, „Keskealine” vähemalt 50%, kuid alla 85%, „Valmiv” vähemalt 85%, kuid alla 100%, „Raievanus saavutatud” vähemalt 100% ning „Määramata”, kui vanus või raievanus puudub. Andmete ajakohasus või puudulikkus tuleb näidata eraldi tunnusena ning värvile peab alati lisanduma tekstiline või muu mittevärviline selgitus.
- R10. Metsateatis tuleb kirjeldada ametliku staatusega sündmusena, mitte tehtud raiet tõendava sündmusena; ainult lubava ja kehtiva staatusega teatist võib nimetada lubatud tööks ning muud staatused tuleb esitada nende ametliku tähenduse järgi. „Ajaloo” vaate kaardidetail seob teatise võimaluse korral eraldisega ja järjestab sündmused ametliku kuupäeva järgi; teadmata kuupäev või staatus jääb nähtavalt määramata. Kinnistuga seotud, kuid usaldusväärse geomeetria või eraldiseseoseta teatis loetakse teema vasteks ja kuvatakse „Asukoht kinnistul määramata” loendis, mitte kaardisümbolina. Lageraietuvastus 2011–2016 peab näitama vaatlusperioodi ja arhiivilisust ning jääma teatisest eraldi sündmuseliigiks.

**Andmeusaldus ja laadimine**

- R11. Kaardil tuleb eelistada ametlikke Eesti allikaid ja näidata eraldi kolme sõltumatut andmeomadust. Päritolu on „Ametlik andmekiht” otse allikast pärineva asjaolu või „Terrapointi tuletis” arvutatud klassi või koonduse puhul. Täielikkus järgib R8 olekuid. Ajakohasus näitab allika avaldatud andmekuupäeva või „Andmete ajaseis teadmata”; Terrapointi viimast edukat kontrolli näidatakse sellest eraldi. Eraldise vanuseklass võib olla arvutatud ka vanema inventuuri põhjal, kuid inventuuri kuupäev või selle puudumine peab sama eraldise juures nähtav olema.
- R12. Vaikekaardi kasutatavus ei tohi sõltuda kõigi valikuliste teemade edukast laadimisest. „Ülevaate” olulise kattuvuse kontrollid on aktiivsed ka enne vaste leidmist; muud mitteaktiivsed teemad laaditakse alles aktiveerimisel. Teema aktiveerimisel on nähtav laadimisolek ja tõrke järel korduskatse. Kinnistu või vaate vahetamisel eemaldatakse aegunud kinnistupõhine sisu kohe ning hilinenud vastus ei tohi muuta enam aktiivse kinnistu või teema olekut.
- R13. Valitud kinnistu geomeetria on kinnistupõhise vaate ainus blokeeriv eeldus. Kinnistu rida liigub olekust „Laadib” olekusse „Kinnistu leitud”; tõrke korral kuvatakse blokeeriv veateade ja korduskatse. Metsaeraldiste eraldi rida liigub olekust „Laadib” olekusse „Leiti X eraldist”, „Metsaeraldisi ei leitud” või „Metsaeraldiste allikas ei vasta · proovi uuesti”; selle tõrge ei takista kinnistutaseme piirangute kasutamist. Ortofoto tõrke korral jäävad kinnistuandmed kasutatavaks neutraalsel varualuskaardil ning piirangute või riskide osaline tõrge järgib R8 olekuid.

**Kasutus eri seadmetel**

- R14. Vaated, käsitsi teemavalik ja ühine legend peavad jagama üht arusaadavat olekut. Enne kinnistu valimist on kasutatavad aluskaart ja senine kinnistuotsing, kuid kinnistupõhised vaated on selgitusega passiivsed. Uue kinnistu valimine taastab „Ülevaate” teemad, säilitades sama lehesessiooni jooksul valitud aluskaardi; lehe uuesti laadimine taastab ametliku ortofoto ja „Ülevaate”.
- R15. Juhtimine peab töötama klaviatuuri, puute ja hiirega. Mobiilis on vaatevalik ja legend vaikimisi kompaktsed ning suletavad, valitud kinnistu peab jääma jälgitavaks ja peamised puutealad olema vähemalt 44 × 44 CSS-pikslit. Avatud juhtpaneeli saab sulgeda paoklahviga, fookus naaseb avamisnupule ning värv ei tohi olla ainus tähenduse kandja; tekstipõhine kinnistuotsing on klaviatuuriga kasutatav alternatiiv kaardiklikile.
- R16. Ümberkujundus peab säilitama kinnistu kaardilt valimise, eraldiste numbrid, eraldiste detailvaate, kaardi suumimise ja olemasoleva tulemuste lehe ülejäänud funktsioonid. Vaated muudavad ainult kaardi ülekatteid, juhtimist ja legendi; need ei filtreeri ega kirjuta ümber lehe „Riskide”, „Toetuste”, „Metsateatiste”, väärtuse ega AI-nõustaja sisu.

**Faktide ajakontekst ja kiirvastused**

- R17. Iga tulemuses kuvatav ajamärge peab nimetama oma tegeliku tähenduse: allika avaldatud või inventeerimise kuupäev, hindamismudeli aasta, väärtuse kehtivuse algus, arvutamise aeg või Terrapointi kontrolli aeg. Neid ei tohi koondada üheks üldiseks „andmeaastaks”.
- R18. Maa maksustamishind peab võimaluse korral näitama ametlikust hindamisinfosüsteemist saadud hindamismudeli aastat ja väärtuse kehtivuse algust; detailis võib näidata arvutamise aega ning alust. Kui metaandmeid ei saa usaldusväärselt siduda kuvatava väärtusega, jääb ajaseis teadmata ja seda ei tuletata katastrikihi muutmis- ega päringuajast.
- R19. Kui kasutaja küsimus vastab toetatud, juba laaditud ja üheselt tõlgendatavale kinnistufaktile, peab Terrapoint vastama ilma generatiivset AI-mudelit käivitamata. Kiirtee hõlmab vähemalt maa maksustamishinda, kinnistu ja metsamaa pindala, peapuuliiki, metsa keskmist vanust, eraldiste arvu, elus puistutagavara ning olemasolevaid mahu- ja hinnavahemikke.
- R20. Kiirvastus peab sisaldama fakti inimkeelset nimetust, väärtust, ühikut, päritolu ning otsust mõjutavat piirangut. Maa maksustamishinna vastus peab ütlema, et see ei ole aastane maamaks ega turuväärtus, ning lisama R18 ajakonteksti, kui see on saadaval.
- R21. Mitmetähenduslik, arvutust nõudev, puuduva väärtusega või toetamata küsimus peab jätkama olemasolevasse AI-analüüsi voogu. Kiirtee ei tohi märksõna põhjal vastata aastase maamaksu summale ega muule faktile, mida otsingutulemus ei sisalda.
- R22. Kasutaja peab nägema, kas vastus pärineb otse kinnistuandmetest või AI-analüüsist. Kiirvastus lisatakse samasse vestlusesse ja säilib järgmiste küsimuste kontekstina, kuid ei käivita AI laadimisolekut ega kuluta AI päringupiirangut.

**Ajaloolise lageraie selgus**

- R23. Ajaloolise lageraie kontrollil peavad olema eraldi olekud „Arhiivivaste leitud”, „2011–2016 arhiivikihis vastet ei leitud”, „Vasted leitud · kontroll osaline”, „Kontroll osaline · puudumist ei saa kinnitada” ja „Kontroll ebaõnnestus · puudumist ei saa kinnitada”. Kärbitud või osaliselt kasutuskõlbmatu vastus peab olema eristatav allika tõrkest ning kummalgi juhul ei tohi näidata täielikku nulltulemust.
- R24. Ajaloolise lageraie selgitus peab nimetama Keskkonnaagentuuri Veeveebi 2011–2016 vaatlusperioodi ning ütlema, et nulltulemus ei välista raiet muul ajal ja tuvastus ei kinnita tänast metsaseisundit ega töö täpset aastat.

**Lehesisene navigeerimine**

- R25. Kõik `#kontakt` lingid peavad viima sama kontaktiploki juurde nii, et ploki põhisisu paikneb võimalusel vaate keskosas; väikese vaate või vähendatud liikumise eelistuse korral peab kogu sisu jääma loetavaks ja kleepuv päis ei tohi seda katta.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R3.** Kui kasutaja valib kinnistu esimest korda, näeb ta ametlikul ortofotol kinnistu piiri, nummerdatud eraldisi ja ainult alaga kattuvaid olulisi piiranguid, ilma et ta peaks teemasid ise sisse lülitama.
- AE2. **Covers R4, R5, R14.** Kui kasutaja valib „Riskid” ja eemaldab seejärel „Võõrliigid”, kajastub muudatus kaardil ja legendis, vaate nimi on „Riskid · kohandatud”, „Riskide” uuesti valimine taastab selle tabelijärgse komplekti ning „Taasta ülevaade” ei muuda kasutaja aluskaarti.
- AE3. **Covers R3, R6, R7.** Kui sama kaitseala saabub kahest ametlikust teenusest, näeb kasutaja üht „Looduskaitse” teemat ja selle detailis mõlemat allikat. Kui samal alal kehtib eri tähendusega veekaitsepiirang, jääb see oma veeteemasse.
- AE4. **Covers R8, R12, R13.** Kui kõik veeteema allikad vastavad täielikult ja kinnistul vasteid pole, näitab legend „Vasteid ei leitud”. Kui üks vajalik allikas ei vasta, kuid teine andis kasutatava nulltulemuse, näitab legend „Puudumist ei saa kinnitada · osaline”. Kui ükski vajalik allikas ei andnud kasutatavat tulemust, näitab legend „Allikas ei vasta · proovi uuesti”; muude teemade tulemused jäävad mõlemal juhul nähtavaks.
- AE5. **Covers R8.** Kui väline teenus tagastab piirväärtuse jagu objekte ja tulemus võib olla kärbitud, säilitab kaart leitud vasted, kuid legend näitab „Vasted leitud · osaline” ega jäta muljet täielikust kattuvuste loendist.
- AE6. **Covers R9, R11.** Kui eraldise vanus on 84% arvutuslikust raievanusest, on klass „Keskealine”; 85% korral „Valmiv” ja 100% korral „Raievanus saavutatud”. Kõik on tähistatud „Terrapointi tuletisena” ning ükski klass ei nimeta ega soovita raiemeetodit.
- AE7. **Covers R10.** Kui kinnistul on kehtiv teatis otsusega „JAH”, arhiivitud teatis otsusega „JAH” ja teatis otsusega „EI”, näitab „Ajalugu” ainult esimest kehtiva lubatud tööna, teist arhiivitud sündmusena ja kolmandat eitava otsusena. Lageraietuvastus 2011–2016 kuvatakse neist eraldi arhiivse tuvastusena ning ühtegi sündmust ei märgita kinnitatud tehtud raiena.
- AE8. **Covers R15, R16.** Kui kasutaja avab 390 CSS-piksli laiuses vaates kaardijuhtimise, saab ta selle puute või paoklahviga sulgeda, fookus naaseb avamisnupule, valitud kinnistu jääb kaardil jälgitavaks ning eraldiste numbrid ja detailid on endiselt avatavad.
- AE9. **Covers R7, R11.** Kui ametlik allikas ei avalda andmestiku kuupäeva, näitab teema detail eraldi „Andmete ajaseis teadmata” ja „Terrapoint kontrollis viimati 14.07.2026”, mitte ei esita kontrolliaega andmete kuupäevana.
- AE10. **Covers R8, R12, R14.** Kui kasutaja proovib sama kinnistu ebaõnnestunud riskiallikat uuesti, jäävad varasemad kehtivad vasted nähtavaks olekuga „Uuendab”. Kui kasutaja vahetab laadimise ajal kinnistut, eemaldatakse vana kinnistu ülekatted kohe, uus kinnistu avaneb „Ülevaates” ja hilinenud vana vastus ei ilmu uuele kinnistule.
- AE11. **Covers R13.** Kui ortofoto ei lae, kuvatakse kinnistu neutraalsel varualuskaardil koos hoiatusega. Kui kinnistu geomeetria ei lae, ei näidata kinnistupõhist nulltulemust, vaid blokeerivat veateadet ja korduskatset. Kui kinnistu leiti, kuid eraldiste allikas ei vasta, näitab eraldiste eraldi rida korduskatset ja kinnistutaseme piirangukontroll jätkub.
- AE12. **Covers R14, R16.** Enne kinnistu valimist saab kasutaja otsida teksti või kaardiklikiga, kuid kinnistupõhised vaated selgitavad, et esmalt tuleb kinnistu valida; vaate vahetamine ei muuda tulemuste lehe kaarte ega AI-vastuseid.
- AE13. **Covers R7, R10.** Kui metsateatis kuulub kinnistule, kuid selle usaldusväärne geomeetria või eraldiseseos puudub, loendab „Ajalugu” selle vastena ja näitab detailis „Asukoht kinnistul määramata”, kuid ei lisa kaardile oletuslikku sümbolit ega muuda tulemuste lehe metsateatiste järjekorda.
- AE14. **Covers R4, R5, R8, R12.** Kui „Ülevaate” kontroll leiab looduskaitse kattuvuse, veeteema vastab täieliku nulliga ja muinsuskaitse allikas ei vasta, näitab kaart looduskaitse ülekatet ning koondrida „Piirangute kontroll osaline”. Muinsuskaitse tõrge on detailis uuesti proovitav; looduskaitse ülekatte peitmisel jääb koondreale „1 kattuvus peidetud”.
- AE15. **Covers R4, R7, R11, R16.** Kui toetuse signaal kehtib terve kinnistu kohta ilma täpse geomeetriata ja teine signaal on tuletatud ühe eraldise tunnustest, näitab „Toetused” esimest legendi detailis „Kinnistu tasemel” ning teist vastava eraldise juures „Terrapointi tuletisena”. Teema ütleb „Indikaatorid leitud”, ei kinnita toetuskõlblikkust ega muuda tulemuste lehe toetuste hinnanguid.
- AE16. **Covers R17, R18, R20.** Kui maksustamishind on 4200 eurot, ametlik hindamismudel on 2022 ja väärtus kehtib alates 17.12.2025, näitab Terrapoint neid eri tähendustega; ta ei nimeta 17.12.2025 päringu kuupäevaks ega kogu väärtust 2022. aasta andmeteks.
- AE17. **Covers R18.** Kui hindamise metaandmete allikas ei vasta või tagastab kuvatava maksustamishinnaga vastuolus oleva väärtuse, jääb 4200-eurone katastriväärtus nähtavaks, kuid selle juurde ei lisata kontrollimata hindamisaega.
- AE18. **Covers R19, R20, R22.** Kui kasutaja küsib „Mis hinna pealt maad maksustatakse?” ja laaditud maksustamishind on 4200 eurot, ilmub kuni ühe sekundi jooksul „Kinnistuandmetest” vastus 4200 euro, ajakonteksti ning maamaksu ja turuväärtuse piiranguga; AI mudelipäringut ei alustata.
- AE19. **Covers R21.** Kui kasutaja küsib „Kui palju ma aastas maamaksu maksan?”, ei esita kiirtee maksustamishinda aastase maksusummana, vaid küsimus jätkub AI voogu või selgitab vajalike maksumäära ja soodustuste puudumist.
- AE20. **Covers R23, R24.** Kui lageraie arhiivikiht vastab täielikult nulltulemusega, näeb kasutaja „2011–2016 arhiivikihis vastet ei leitud” ja selgitust perioodi piirangu kohta. Kui vastus on kärbitud või osaliselt kasutuskõlbmatu, näeb ta „Kontroll osaline · puudumist ei saa kinnitada”; kui sama allikas ei vasta, näeb ta „Kontroll ebaõnnestus · puudumist ei saa kinnitada”.
- AE21. **Covers R23, R24.** Kui arhiivikihist leitakse vaste, kuid osa allikatulemusest on kasutuskõlbmatu, jääb periood nähtavaks olekuga „Vasted leitud · kontroll osaline” ega muutu täielikuks kinnituseks.
- AE22. **Covers R25.** Kui kasutaja valib kontaktlingi laua- või mobiilivaates, on kerimise järel korraga nähtavad kontaktiploki pealkiri, selgitus ja e-posti link ning plokk ei jää kleepuva päise alla.

---

## Success Criteria

- Esmakordne metsaomanik suudab vaikekaardilt 30 sekundi jooksul leida kinnistu piiri, eraldised, olulised kattuvad piirangud ja selgituse, mida eraldise värv tähendab.
- Kasutaja saab ühe valikuga liikuda teostatavuse, piirangute, riskide, toetuste ja ajaloo küsimuse juurde ning taastada sama selgelt „Ülevaate”.
- Ükski kaardivärv ega staatus ei esita vanusepõhist hinnangut raiemeetodina ega metsateatist tehtud tööna.
- Iga aktiivse teema puhul on eristatavad olemasolevad vasted, vastete puudumine, allika tõrge ja võimalik mittetäielikkus.
- Vaikekaart muutub kasutatavaks ka siis, kui mõni mitteaktiivne või valikuline allikas on aeglane või kättesaamatu.
- Laua- ja mobiilivaates ei kata juhtimine püsivalt kaardi otsustamiseks vajalikku ala ning kõik funktsioonid on kasutatavad ilma ainult värvile tuginemata.
- Planeerija saab sellest dokumendist tuletada deterministlikud kasutusvood ja kontrollstsenaariumid ilma toote käitumist või ulatust juurde leiutamata.
- Toetatud lihtsa faktiküsimuse vastus ilmub tavakasutuses kuni ühe sekundi jooksul ja selle jaoks ei tehta generatiivse AI teenuse päringut.
- Maa maksustamishinna juures on ametliku allika olemasolul nähtav hindamismudeli aasta ja kehtivuse algus, ilma et neid aetaks segamini andmete päringuajaga.
- Ajaloolise lageraie nulltulemus, osaline kontroll ja allikatõrge on eri tekstiga ning ükski tõrge ei paista kasutajale vaste puudumisena.
- Kontaktlink jätab kontaktiploki põhisisu laua- ja mobiilivaates loetavasse vaateossa.

---

## Scope Boundaries

- Esimesse versiooni ei kuulu kõigi Eesti ruumiandmete täielik GIS-kataloog ega edasijõudnud kaardikihi haldus.
- Esimesse versiooni ei kuulu reaalajas Sentinel-seire, LiDAR-i töötlemine ega uus kaugseireanalüüs.
- Terrapoint ei kinnita kaardi põhjal töö õiguspärasust, toetuse lõplikku sobivust ega raietöö tegelikku teostamist.
- Ümberkujundus ei laiene kogu tulemuste lehe, väärtusarvutuse või AI-nõustaja visuaalsele ümbertegemisele.
- Esimesse versiooni ei kuulu kontopõhised salvestatud vaated ega vaadete jagamine.
- Ajaloolist 2011–2016 lageraietuvastust ei taastata silmapaistva põhikihi ega tänase metsaseisundi signaalina.
- Esimesse versiooni ei kuulu uus satelliidi- või ortofotopõhine lageraietuvastus ega 2011–2016 perioodist laiem ajalookatvus.
- Kiirvastused ei arvuta aastast maamaksu, turuväärtust ega muid puuduvaid fakte ning ei asenda keeruliste küsimuste AI-analüüsi.
- Muudatus ei kujunda AI-nõustaja ega tulemuste lehe visuaalset struktuuri tervikuna ümber.

---

## Key Decisions

- Otsusepõhised vaated allikapõhise kihiloendi asemel: omanik alustab oma küsimusest, mitte GIS-andmestiku nimest.
- Hõre ametlik vaikeseis: kaart näitab esmalt orientiire ja olulisi kattuvusi, detailid avanevad vajaduse järgi.
- Üks allikateadlik legend: sümbol, tähendus ja andmeusaldus kuuluvad samasse kohta.
- Raievanuse suhtarv ei ole raietsoovitus: puistu vanuseklass, metsateatis ja ajalooline tuvastus jäävad eraldi mõisteteks.
- Dubleerivate piiranguallikate koondamine: kasutaja näeb asjaolu tähendust, säilitades võimaluse kontrollida selle ametlikke allikaid.
- Faktipõhine kiirtee mudeli kiirendamise asemel: lehel juba olemasoleva numbri kordamine peab olema deterministlik, allikapõhine ja mudeli latentsusest sõltumatu.
- Semantiline ajakontekst üldise aasta asemel: „hindamismudel”, „kehtib alates”, „inventeeritud” ja „kontrollitud” jäävad eraldi mõisteteks.
- Olemasoleva lageraie arhiivkihi selgitamine uue tuvastuse asemel: esimene väärtus tuleb õigest tõlgendusest ja ausast allikaolekust.

---

## Dependencies / Assumptions

- Vajalikud ametlikud kaardi- ja registriteenused jäävad Terrapointile tehniliselt ning kasutustingimuste järgi kättesaadavaks.
- Valitud kinnistu geomeetria võimaldab määrata, kas piirang või riskisignaal alaga kattub; allika ruumiline täpsus võib siiski erineda.
- Kõik välised teenused ei avalda usaldusväärset andmestiku kuupäeva, mistõttu tuleb andmete ajaseis ja Terrapointi viimane kontroll selgelt lahus hoida.
- Kaardil kuvatav nulltulemus ei ole piisav tõend asjaolu puudumise kohta, kui allika kättesaadavus või tulemuse täielikkus pole kinnitatud.
- Maa- ja Ruumiameti hindamisinfosüsteem tagastab katastritunnuse kohta hindamismudeli aasta, arvutusaja ja kehtivusvahemiku ning jääb tootmiskasutuseks kättesaadavaks. Selle tõrge ei tohi blokeerida katastri põhiandmeid.
- Kiirvastuse tuvastus põhineb piiratud, kontrollitaval faktide ja küsimusvormide hulgal; kahtluse korral eelistatakse olemasolevat AI voogu vale faktivastuse asemel.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R3, R6][Technical] Millised kattuvad kaitse- ja piirangukihid saab nende atribuutide ning ruumilise katvuse põhjal ohutult üheks kasutajateemaks koondada?
- [Affects R2, R11, R13][Needs research] Milline Maa- ja Ruumiameti ametlik ortofototeenus, ajaseisu info, atribuutika ja neutraalne varualuskaart sobivad tootmiskasutuseks?
- [Affects R12, R13][Technical] Milline mõõdetav laadimis- ja interaktiivsuse eelarve on praeguse tootmistaseme põhjal realistlik ning millised allikad tuleb selle saavutamiseks laadida nõudmisel?
