"""Terrapointi sisulehed: tekst, metaandmed ja struktuurne info ühes kohas.

Need lehed on **serveripoolselt renderdatud** HTML: nii näevad otsingumootorid
ja AI-kraalerid (mis sageli JavaScripti ei käivita) sisu ilma rakenduse
laadimiseta. Iga leht kannab oma pealkirja, kirjeldust, kanoonilist URL-i,
breadcrumb'i, avaldamis- ja uuendamiskuupäeva ning allikaid.

Sisu hoidmine Pythonis (mitte kuues eraldi HTML-failis) tähendab, et
`sitemap.xml`, `<head>` metaandmed ja sisulehtede tekst tulevad ühest
allikast ega lähe omavahel lahku.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SITE_NAME = "Terrapoint"
SITE_URL = "https://terrapoint.ee"
SITE_TAGLINE = "Eesti metsa- ja kinnistuandmed ühe otsinguga"
CONTACT_EMAIL = "arle.reidma@gmail.com"
# Lehtede sisu ajatempel: uuenda, kui teksti või arvutusi sisuliselt muudad.
CONTENT_UPDATED = "2026-11-04"


@dataclass(frozen=True)
class Section:
    """Üks sisuosa: pealkiri + lõigud, valikuliselt tabel või loend."""

    heading: str
    paragraphs: tuple[str, ...] = ()
    bullets: tuple[str, ...] = ()
    table_head: tuple[str, ...] = ()
    table_rows: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class Source:
    label: str
    url: str
    note: str = ""


@dataclass(frozen=True)
class FaqItem:
    question: str
    answer: str


@dataclass(frozen=True)
class SeoPage:
    slug: str
    title: str          # <60 tähemärki, kujul "Teema | Terrapoint"
    description: str    # 50–160 tähemärki
    h1: str
    lede: str           # vastus esimese 40–60 sõnaga (GEO: tsitaadikõlblik)
    summary: str        # lühike vastus "Lühivastus" plokis
    sections: tuple[Section, ...]
    faq: tuple[FaqItem, ...] = ()
    sources: tuple[Source, ...] = ()
    related: tuple[tuple[str, str], ...] = ()   # (slug, ankru tekst)
    updated: str = CONTENT_UPDATED
    published: str = "2026-11-04"
    og_image: str = "/static/og-image.png"
    keywords: tuple[str, ...] = ()


PAGES: tuple[SeoPage, ...] = (
    SeoPage(
        slug="metsaandmed-katastritunnuse-jargi",
        title="Metsaandmed katastritunnuse järgi | Terrapoint",
        description=(
            "Sisesta katastritunnus ja näe ühe otsinguga metsaeraldisi, tagavara, "
            "puidu hinnavahemikku, süsinikuvaru, kitsendusi ja toetusi koos "
            "allikate ajaseisuga."
        ),
        h1="Metsaandmed katastritunnuse järgi",
        lede=(
            "Terrapoint koondab ühe katastritunnuse alt Metsaregistri eraldised, "
            "Maa- ja Ruumiameti katastriandmed, EELISe kaitsealad ja metsateatised "
            "ühte vaatesse. Sisesta katastritunnus või aadress ja näed metsamaa "
            "pindala, tagavara, puuliike, vanust, hinnavahemikku, süsinikuvaru, "
            "piiranguid ja toetusi — iga näitaja juures on allikas ja ajaseis."
        ),
        summary=(
            "Metsaandmed katastritunnuse järgi saab kätte ühe päringuga: Terrapoint "
            "pärib otsingu hetkel Metsaregistrist eraldised ning sidusregistritest "
            "kitsendused, teatised ja toetused. Tulemus näitab nii andmeid kui ka "
            "seda, kui värsked need on ja millest arvutus ei räägi."
        ),
        sections=(
            Section(
                heading="Mida üks otsing tagastab?",
                paragraphs=(
                    "Otsing vastab küsimusele „mis sellel kinnistul tegelikult kirjas on?”. "
                    "Tulemus koosneb üheksast plokist: katastriüksus, metsaeraldised, "
                    "süsinikuvaru, metsa vara, tervisesignaal, EUDR-i eelsõel, "
                    "kitsendused, metsateatised ja toetused.",
                    "Iga plokk näitab lähteandmeid, mitte ainult lõppnumbrit: eraldiste "
                    "inventuuri kuupäevi, tagavara päritolu, hinnavahemiku alust ja "
                    "puuduvate andmete osakaalu. Kui mõne allika vastus puudub, ütleb "
                    "kaart seda välja, selle asemel et näidata vaikselt vana või "
                    "oletuslikku arvu.",
                ),
                bullets=(
                    "Katastritunnus, pindala, metsamaa pindala, sihtotstarve ja aadress",
                    "Eraldiste arv, peapuuliik, keskmine vanus, tagavara ja boniteet",
                    "Puidu ja maa indikatiivne hinnavahemik koos katvusega",
                    "Süsinikuvaru ja elusa biomassi hinnang",
                    "Kaitsealad, piiranguvööndid, vee- ja ranna piirangud, mälestised",
                    "Metsateatised (kehtivad ja arhiivitud) ning toetusmeetmed",
                ),
            ),
            Section(
                heading="Kust andmed tulevad?",
                paragraphs=(
                    "Päringud tehakse otsingu hetkel avalikest registritest: Maa- ja "
                    "Ruumiamet (kataster, ortofoto, kitsenduste kaart), Metsaregister "
                    "(eraldised, teatised, Natura 2000), EELIS ja Keskkonnaagentuuri "
                    "ruumikihid (kaitsealad, piirangud, sood), Kultuurimälestiste register, "
                    "EstHubi Sentinel-2 päevapilt ning avaldatud puiduhinnad.",
                    "Terrapoint ei ole register ega asenda ametlikku väljavõtet. Ta on "
                    "vaade, mis toob registrid ühte kohta ja märgib iga näitaja juurde, "
                    "kust see pärineb ning kui värske see on.",
                ),
            ),
            Section(
                heading="Mis on tulemuse piirid?",
                paragraphs=(
                    "Registriandmed võivad olla puudulikud või aegunud. Kui osa eraldistest "
                    "ei ole inventeeritud, näitab Terrapoint katvust (näiteks „Andmed "
                    "katavad 5,38 ha 6,34 ha-st”) ja loetleb puuduvaderaldised, mitte ei "
                    "esita osalist arvutust täielikuna.",
                    "Hinnavahemik on arvutuslik, mitte turuväärtus ega tehinguhinna "
                    "prognoos. Metsateatis näitab kavandatud raiet, mitte tehtud raiet. "
                    "Piirangute loetelu on kaardikihtide kattuvus, mitte õiguslik otsus.",
                ),
            ),
        ),
        faq=(
            FaqItem(
                "Kas Terrapoint töötab kogu Eesti kohta?",
                "Jah, iga katastriüksuse kohta, mille andmed on riiklikes registrites "
                "olemas. Kui mõni allikas ei vasta, märgib Terrapoint selle välja.",
            ),
            FaqItem(
                "Kas ma pean sisestama katastritunnuse?",
                "Katastritunnus on kõige täpsem võti. Aadressi või koha nime järgi "
                "otsides leiab Terrapoint sobiva katastriüksuse.",
            ),
            FaqItem(
                "Kas tulemus on ametlik dokument?",
                "Ei. Terrapoint koondab avalikke andmeid ja näitab nende päritolu; "
                "ametlikuks tõendiks on registri väljavõte.",
            ),
        ),
        sources=(
            Source("Maa- ja Ruumiamet — kataster ja kitsenduste kaart", "https://www.maaamet.ee/"),
            Source("Metsaregister", "https://register.metsad.ee/"),
            Source("EELIS (Eesti Looduse Infosüsteem)", "https://eelis.ee/"),
            Source("Kultuurimälestiste register", "https://register.muinas.ee/"),
        ),
        related=(
            ("metsa-hind", "Metsa hind ja väärtus"),
            ("metsatoetused", "Metsatoetused ja hüvitised"),
            ("andmeallikad", "Andmeallikad ja metoodika"),
            ("kkk", "Korduma kippuvad küsimused"),
        ),
        keywords=("metsaandmed", "katastritunnus", "metsaregister", "eraldised"),
    ),
    SeoPage(
        slug="metsa-hind",
        title="Metsa hind ja väärtus — kuidas see kujuneb | Terrapoint",
        description=(
            "Metsa hind ja väärtus Eestis: tagavara, puuliigid, hinnavahemik ja maa "
            "referents. Terrapoint näitab arvutuskäiku, kasutatud hindu ja katvust."
        ),
        h1="Metsa hind ja väärtus: kuidas hinnang kujuneb",
        lede=(
            "Metsa väärtus ei ole register, vaid arvutus: elus puistutagavara korrutatakse "
            "puuliigi hinnavahemikuga ja liidetakse maa referents. Terrapoint näitab "
            "tulemust vahemikuna koos katvuse, kasutatud hinnainfo ja puuduvate "
            "eraldiste loeteluga, sest osaline arvutus ei tohi näida täielikuna."
        ),
        summary=(
            "Metsa väärtust hinnatakse Eestis tavaliselt tagavara ja puidu hindade kaudu. "
            "Terrapoint kasutab Eesti Erametsaliidu avaldatud hinnainfot, arvestab iga "
            "eraldise tagavara ja pindala ning näitab tulemust vahemikuna koos maa "
            "maksustamishinnaga."
        ),
        sections=(
            Section(
                heading="Millest hinnang koosneb?",
                paragraphs=(
                    "Hinnangul on kaks osa: kasvav puit ja maa referents. Puiduosa lähtub "
                    "eraldiste elusast tagavarast (m³/ha) ja pindalast; maaosa kasutab "
                    "katastri maksustamishinda. Kogu kinnistu vahemik liidab need kaks osa.",
                ),
                table_head=("Näitaja", "Kust see tuleb", "Mida see ei ole"),
                table_rows=(
                    ("Elus puistutagavara", "Metsaregister, eraldiste inventuur",
                     "Surnud või lamapuit ei kuulu müüdava puidu hulka"),
                    ("Puidu hinnavahemik", "Avaldatud kännuraha hinnad",
                     "Ei ole konkreetse ostja pakkumine"),
                    ("Maa referents", "Katastri maksustamishind",
                     "Ei ole tehinguhind ega turuväärtus"),
                    ("Kogu kinnistu vahemik", "Puit + maa referents",
                     "Ei asenda hindamisakti"),
                ),
            ),
            Section(
                heading="Miks on tulemus vahemik, mitte üks number?",
                paragraphs=(
                    "Sama tagavara eest on erinevates tingimustes erinev hind: sortiment, "
                    "raievalmidus, ligipääs, kivid ja märg ala mõjutavad lõpptulemust. "
                    "Terrapoint ei asenda neid oletusi, vaid näitab vahemikku ja seda, "
                    "millised sisendid on puudu.",
                    "Kui osa eraldistest ei ole tagavaraandmetega kaetud, kahaneb "
                    "usaldusväärsus ja Terrapoint ütleb seda otse. See on oluline, sest "
                    "näiteks 10-hektarilisest kinnistust 90% katvus ei ole sama asi kui "
                    "täielik katvus.",
                ),
            ),
            Section(
                heading="Kuidas seda praktikas kasutada?",
                bullets=(
                    "Võrdle vahemikku, mitte keskpunkti: keskpunkt on aritmeetiline, mitte ootus.",
                    "Kontrolli, kas eraldised on inventeeritud 10 aasta jooksul (Metsaseadus).",
                    "Vaata metsateatisi: kavandatud raie ja tehtud raie on eri asjad.",
                    "Vaata kitsendusi: kaitseala või veekaitsevöönd piirab raiet.",
                    "Küsi ametlik väljavõte ja hinnapakkumine, kui tehing on tõsine.",
                ),
            ),
        ),
        faq=(
            FaqItem(
                "Kas Terrapointi hinnang on lõplik turuväärtus?",
                "Ei. See on arvutuslik vahemik avalikest andmetest, mis aitab suurusjärku "
                "mõista; tehinguhinna annab turg.",
            ),
            FaqItem(
                "Milliseid hindu kasutatakse?",
                "Hinnavahemik põhineb Eesti Erametsaliidu avaldatud hinnainfol; iga "
                "näitaja juures on viidatud allikas ja periood.",
            ),
            FaqItem(
                "Kas puuduvad eraldised jäetakse summast välja?",
                "Jah. Puuduvate andmetega eraldised jäävad summast välja ja Terrapoint "
                "näitab, kui suur osa pindalast on kaetud.",
            ),
        ),
        sources=(
            Source("Eesti Erametsaliit — puidu hinnainfo", "https://www.erametsaliit.ee/"),
            Source("Metsaregister — eraldiste andmed", "https://register.metsad.ee/"),
            Source("Metsaseadus", "https://www.riigiteataja.ee/akt/116012017002"),
        ),
        related=(
            ("metsaandmed-katastritunnuse-jargi", "Metsaandmed katastritunnuse järgi"),
            ("metsa-hind", "Metsa hind ja väärtus"),
            ("kkk", "Korduma kippuvad küsimused"),
        ),
        keywords=("metsa hind", "metsa väärtus", "metsa hindamine", "puidu hind", "kännuraha"),
    ),
    SeoPage(
        slug="metsatoetused",
        title="Metsatoetused ja hüvitised 2026 | Terrapoint",
        description=(
            "Millised metsatoetused on 2026. aastal avatud, millised lõppenud ja mida "
            "peab enne taotlemist kontrollima. Terrapoint seob meetmed kinnistu andmetega."
        ),
        h1="Metsatoetused ja hüvitised",
        lede=(
            "Toetusmeetmed muutuvad iga vooruga: see, mis oli avatud eelmisel aastal, "
            "võib olla suletud. Terrapoint seob avalikud meetmed kinnistu andmetega ja "
            "ütleb iga meetme juures, kas see puudutab seda kinnistut, kas voor on "
            "avatud ning millist tingimust tuleb ametlikust allikast kontrollida."
        ),
        summary=(
            "Metsatoetusi antakse Keskkonnaameti ja KIK-i kaudu ning need sõltuvad "
            "kinnistu asukohast, kaitse staatusest ja metsa seisundist. Terrapoint "
            "näitab, millised meetmed on kinnistuga seotud ja millised on lõppenud, "
            "kuid lõplik otsus sünnib alati taotlusvooru tingimustest."
        ),
        sections=(
            Section(
                heading="Kuidas Terrapoint meetmeid käsitleb?",
                paragraphs=(
                    "Iga meede on kolmes grupis: kinnistuga seotud avatud või aastaringne "
                    "meede, vooru avanemist jälgiv meede ning „muud meetmed ja lõppenud "
                    "voorud”. Grupp näitab, kui tõenäoline on, et meede sellele kinnistule "
                    "kohaldub — mitte seda, et taotlus õnnestub.",
                ),
                bullets=(
                    "Sobivus: kas kinnistu asukoht ja kaitse staatus vastavad meetme alale",
                    "Vooru staatus: avatud, aastaringne, tulev või lõppenud",
                    "Kontrollitavad tingimused: mida peab enne taotlemist ametlikust allikast vaatama",
                ),
            ),
            Section(
                heading="Mida peab enne taotlemist kontrollima?",
                paragraphs=(
                    "Toetuse saamist ei saa mingi automaatne süsteem ette lubada. Enne "
                    "taotlemist kontrolli meetme tingimusi, taotlusvooru kuupäevi, "
                    "kinnistu piiranguid ning seda, kas metsateatis on vajalik ja "
                    "heaks kiidetud.",
                    "Kui kinnistu asub kaitsealal või piiranguvööndis, võib tööde tegemine "
                    "vajada Keskkonnaameti nõusolekut. Terrapoint näitab kitsendusi, aga "
                    "ei asenda ametlikku menetlust.",
                ),
            ),
        ),
        faq=(
            FaqItem(
                "Kas Terrapoint ütleb, millele mul on õigus?",
                "Ei. Ta näitab, millised meetmed on avalike andmete põhjal kinnistuga "
                "seotud, ja suunab ametliku tingimuse juurde.",
            ),
            FaqItem(
                "Miks on osa meetmeid „lõppenud voorudes”?",
                "Sest nende taotlusvoor on suletud või lõppenud. Need kuvatakse "
                "taustainfona, et uus voor oleks äratuntav.",
            ),
        ),
        sources=(
            Source("Keskkonnaamet — toetused", "https://keskkonnaamet.ee/"),
            Source("Keskkonnainvesteeringute Keskus (KIK)", "https://kik.ee/"),
            Source("Metsaregister — metsateatis", "https://register.metsad.ee/"),
        ),
        related=(
            ("metsaandmed-katastritunnuse-jargi", "Metsaandmed katastritunnuse järgi"),
            ("andmeallikad", "Andmeallikad ja metoodika"),
            ("kkk", "Korduma kippuvad küsimused"),
        ),
        keywords=("metsatoetused", "toetus 2026", "KIK", "Keskkonnaamet"),
    ),
    SeoPage(
        slug="eudr-geolokatsioon",
        title="EUDR geolokatsioon metsakinnistule | Terrapoint",
        description=(
            "EUDR-i geolokatsiooni lähtefail Eesti katastriüksuse kohta: ametlik "
            "geomeetria, registri eelsõel ja selgitus, mida see fail tõendab ning "
            "mida mitte."
        ),
        h1="EUDR geolokatsioon Eesti metsakinnistule",
        lede=(
            "EUDR (määrus (EL) 2023/1115) nõuab puittoodete tarneahelas geolokatsiooni "
            "andmeid selle maa kohta, kust puit pärineb. Terrapoint valmistab Eesti "
            "katastriüksuse kohta GeoJSON-faili ametliku kinnistugeomeetriaga ja "
            "registri eelsõeluga — see on lähteandmete pakett, mitte vastavustõend."
        ),
        summary=(
            "EUDR geolokatsioon on GeoJSON, mis sisaldab katastriüksuse ametlikku "
            "geomeetriat ning Terrapointi registri eelsõela tulemust. Ettevõtja peab "
            "eraldi tõendama raadamisvabaduse pärast 31.12.2020, tootmise seaduslikkuse "
            "ja tarneahela."
        ),
        sections=(
            Section(
                heading="Mida fail sisaldab?",
                bullets=(
                    "Katastriüksuse ametlik geomeetria (GeoJSON Polygon)",
                    "Katastritunnus, pindala ja sihtotstarve",
                    "Reprezentatiivsed koordinaadid (geomeetriast tuletatud, mitte tippude keskmine)",
                    "Registri eelsõel: kaitseala, Natura 2000, sood",
                    "Faili koostamise aeg ja andmeallikate loetelu",
                ),
            ),
            Section(
                heading="Mida see fail ei tõenda?",
                paragraphs=(
                    "Geolokatsioonifail ei ole hoolsuskohustuse deklaratsioon (DDS) ega "
                    "vastavustõend. See ei kinnita, et maa-ala oli 31.12.2020 seisuga "
                    "raadamata, ega seda, et toode on seaduslikult toodetud. Need "
                    "tõendid peab ettevõtja ise koguma ja riskihindamise tegema.",
                    "Terrapoint näitab registrite eelsõela tulemust nii, nagu registrid "
                    "seda parasjagu võimaldavad, ja märgib puuduliku allika korral, et "
                    "kontroll jäi osaliseks.",
                ),
            ),
            Section(
                heading="Mis on EUDR-i geolokatsiooni mõte?",
                paragraphs=(
                    "Määruse eesmärk on tagada, et Euroopa Liidu turule jõudev puit ei "
                    "oleks seotud metsaraiega, mis toimus pärast 31.12.2020. Selleks "
                    "peab ettevõtja teadma, millisele maa-alale tooraine jälg välja "
                    "viib, ja suutma seda tõendada ka siis, kui tarneahel on pikk.",
                    "Geolokatsioon on selle ahela esimene lüli: kinnistu piir "
                    "koordinaatidena, mille vastu saab hiljem kontrollida nii "
                    "raadamisandmeid kui ka kaitsealade kattuvust. Eesti kontekstis "
                    "on katastriüksus kõige täpsem avalik võti, sest metsaeraldised "
                    "ja inventuuriandmed on seotud just selle piiriga.",
                    "Seetõttu teeb Terrapoint faili katastriüksuse ametlikust "
                    "geomeetriast, mitte käsitsi joonistatud ristkülikust ega "
                    "kaardi tippude keskmisest.",
                ),
            ),
            Section(
                heading="Kuidas faili kasutada?",
                bullets=(
                    "Laadi GeoJSON alla katastriüksuse otsingu tulemusest (EUDR plokk).",
                    "Kontrolli, et geomeetria vastab sellele maa-alale, millelt puit pärineb.",
                    "Lisa fail oma hoolsuskohustuse toimikusse koos tarneahela andmetega.",
                    "Tee riskihindamine ja vajadusel riskimaandamine eraldi menetlusena.",
                ),
            ),
        ),
        faq=(
            FaqItem(
                "Kas EUDR kehtib ka väikeomanikule?",
                "Määrus kohaldub ettevõtjatele, kes puittooteid turule lasevad või ekspordivad. "
                "Metsaomanik puutub sellega kokku eeskätt ostja andmenõuete kaudu.",
            ),
            FaqItem(
                "Kas Terrapoint saab DDS-i koostada?",
                "Ei. Terrapoint annab lähteandmed; deklaratsiooni esitab ettevõtja ise.",
            ),
        ),
        sources=(
            Source("Määrus (EL) 2023/1115 (EUDR)", "https://eur-lex.europa.eu/eli/reg/2023/1115/oj"),
            Source("Euroopa Komisjon — metsaraie määrus", "https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en"),
            Source("Maa- ja Ruumiamet — kataster", "https://www.maaamet.ee/"),
        ),
        related=(
            ("metsaandmed-katastritunnuse-jargi", "Metsaandmed katastritunnuse järgi"),
            ("andmeallikad", "Andmeallikad ja metoodika"),
            ("kkk", "Korduma kippuvad küsimused"),
        ),
        keywords=("EUDR", "geolokatsioon", "metsaraie määrus", "GeoJSON"),
    ),
    SeoPage(
        slug="andmeallikad",
        title="Andmeallikad ja metoodika | Terrapoint",
        description=(
            "Milliseid registreid Terrapoint pärib, kui sageli need uuenevad ja kuidas "
            "arvutused (tagavara, süsinik, hinnavahemik) tehtud on. Metoodika ja piirid."
        ),
        h1="Andmeallikad ja metoodika",
        lede=(
            "Terrapoint ei kogu oma andmeid: iga näitaja pärineb avalikust registrist "
            "või avaldatud hinnainfost. See leht loetleb allikad, nende uuenemise ja "
            "arvutuste reeglid, et iga numbri taga oleks jälgitav tee."
        ),
        summary=(
            "Allikad: Maa- ja Ruumiamet (kataster, ortofoto, kitsenduste kaart), "
            "Metsaregister (eraldised, teatised, Natura 2000), EELIS ja Keskkonnaagentuur "
            "(kaitsealad, piirangud, sood), Kultuurimälestiste register, EstHubi "
            "Sentinel-2 päevapilt ning Eesti Erametsaliidu puiduhinnad."
        ),
        sections=(
            Section(
                heading="Allikad ja nende uuenemine",
                table_head=("Allikas", "Mida see annab", "Uueneb"),
                table_rows=(
                    ("Maa- ja Ruumiamet", "Kataster, piirid, ortofoto, kitsendused", "Kataster perioodiliselt"),
                    ("Metsaregister", "Eraldised, tagavara, teatised, Natura 2000", "Inventuuri ja teatiste kaupa"),
                    ("EELIS / Keskkonnaagentuur", "Kaitsealad, piirangud, sood", "Allika järgi"),
                    ("EstHubi Sentinel-2", "Päevapilt (viimane selge päev)", "Iga päev"),
                    ("Eesti Erametsaliit", "Puidu hinnainfo", "Kord kvartalis"),
                ),
            ),
            Section(
                heading="Arvutuste reeglid",
                paragraphs=(
                    "Tagavara ja süsinik arvutatakse ainult nende eraldiste põhjal, mille "
                    "kohta andmed on olemas. Terrapoint ei asenda turvavälja oletusega: "
                    "kui tagavara puudub, ei arvata seda nulliks, vaid jäetakse summast "
                    "välja ja näidatakse katvus.",
                    "Süsinik lähtub elusast maapealsest ja juurebiomassist IPCC tegurite "
                    "järgi; muld, surnud puit ja varis ei ole arvutuses. Tulemus on varu "
                    "(tCO₂), mitte aastane sidumine ega süsinikukrediit.",
                ),
            ),
            Section(
                heading="Mida Terrapoint ei tee",
                bullets=(
                    "Ei anna ametlikku väljavõtet ega hinnangut",
                    "Ei prognoosi tehinguhinda",
                    "Ei asenda metsateatist ega kaitseala nõusolekut",
                    "Ei koosta EUDR-i hoolsuskohustuse deklaratsiooni",
                    "Ei kasuta kinnistu andmeid ilma päringuta (vahemällu salvestatakse lühidalt)",
                ),
            ),
        ),
        faq=(
            FaqItem(
                "Kas andmeid salvestatakse?",
                "Päringud tehakse otsingu hetkel ja tulemus püsib lühiajalises vahemälus, "
                "et sama päringut korrata saaks. Isikuandmeid ei koguta.",
            ),
            FaqItem(
                "Miks võib sama kinnistu näidata erinevat numbrit?",
                "Registrid uuenevad eri aegadel. Terrapoint näitab iga näitaja juures "
                "allika seisukorda ja seda, millal seda kontrolliti.",
            ),
        ),
        sources=(
            Source("Maa- ja Ruumiamet", "https://www.maaamet.ee/"),
            Source("Metsaregister", "https://register.metsad.ee/"),
            Source("EELIS", "https://eelis.ee/"),
            Source("EstHub — Sentinel-2 päevamosaiik", "https://esthub.maaruum.ee/est/satiladu-p1.html"),
            Source("Eesti Erametsaliit", "https://www.erametsaliit.ee/"),
        ),
        related=(
            ("metsaandmed-katastritunnuse-jargi", "Metsaandmed katastritunnuse järgi"),
            ("metsa-hind", "Metsa hind ja väärtus"),
            ("eudr-geolokatsioon", "EUDR geolokatsioon"),
            ("kkk", "Korduma kippuvad küsimused"),
        ),
        keywords=("andmeallikad", "metoodika", "metsaregister", "maa-amet"),
    ),
    SeoPage(
        slug="kkk",
        title="Korduma kippuvad küsimused | Terrapoint",
        description=(
            "Vastused levinumatele küsimustele Terrapointi, metsaandmete, hinnangute, "
            "toetuste ja EUDR-i kohta — lühidalt ja allikate viidetega."
        ),
        h1="Korduma kippuvad küsimused",
        lede=(
            "Siia on koondatud küsimused, mida Terrapointi kohta kõige sagedamini "
            "küsitakse: kust andmed tulevad, mida hinnang tähendab, miks osa andmeid "
            "vahel puudub ja mida saab EUDR-i ja toetuste kohta teada."
        ),
        summary=(
            "Terrapoint on tasuta veebirakendus, mis koondab Eesti avalikest registritest "
            "metsa- ja kinnistuandmed ühte otsingusse ning näitab iga näitaja päritolu, "
            "ajaseisu ja piiranguid. Ta ei anna ametlikke otsuseid ega hinnanguid."
        ),
        sections=(
            Section(
                heading="Üldised küsimused",
                paragraphs=(
                    "Terrapointi eesmärk on teha nähtavaks see, mida registrid juba "
                    "ütlevad, ja see, mida nad ei ütle. Seetõttu näeb iga tulemus välja "
                    "nii: number, selle allikas, ajaseis ja piirang.",
                ),
            ),
            Section(
                heading="Metsa ja hinnangu kohta",
                paragraphs=(
                    "Tagavara, vanus ja puuliigid tulevad Metsaregistrist. Hinnavahemik on "
                    "Terrapointi arvutus avaldatud puiduhindadest, mitte ostja pakkumine. "
                    "Kui osa eraldistest puudub, näitab Terrapoint katvust.",
                ),
            ),
            Section(
                heading="Toetuste ja piirangute kohta",
                paragraphs=(
                    "Toetusmeetmed ja kitsendused sõltuvad kinnistu asukohast ja staatusest. "
                    "Terrapoint näitab, millised meetmed ja piirangud on andmete põhjal "
                    "seotud, ning suunab ametliku allika juurde, kust tuleb lõplik tingimus.",
                ),
            ),
        ),
        faq=(
            FaqItem("Mis on Terrapoint?", "Tasuta veebirakendus Eesti metsa- ja kinnistuandmete analüüsiks."),
            FaqItem("Kas see on tasuta?", "Jah, kasutamine on tasuta."),
            FaqItem("Kust andmed tulevad?", "Maa- ja Ruumiametist, Metsaregistrist, EELISest, Kultuurimälestiste registrist ja avaldatud hinnainfost."),
            FaqItem(
                "Miks mõni väli on tühi?",
                "Sest register ei sisalda seda andet. Terrapoint ei asenda puuduvat välja "
                "oletusega, vaid näitab puudujääki ja katvust.",
            ),
            FaqItem(
                "Kas Terrapoint asendab metsateatist?",
                "Ei. Teatise esitab metsaomanik Metsaregistris; Terrapoint näitab "
                "registrisse jõudnud teatisi.",
            ),
            FaqItem(
                "Kust saan abi või annan tagasisidet?",
                "Kirjuta aadressile arle.reidma@gmail.com.",
            ),
            FaqItem(
                "Kas Terrapoint kogub isikuandmeid?",
                "Ei kogu isikuandmeid ega küsi sisselogimist.",
            ),
        ),
        sources=(
            Source("Metsaregister", "https://register.metsad.ee/"),
            Source("Maa- ja Ruumiamet", "https://www.maaamet.ee/"),
            Source("EELIS", "https://eelis.ee/"),
        ),
        related=(
            ("metsaandmed-katastritunnuse-jargi", "Metsaandmed katastritunnuse järgi"),
            ("metsa-hind", "Metsa hind ja väärtus"),
            ("metsatoetused", "Metsatoetused ja hüvitised"),
            ("eudr-geolokatsioon", "EUDR geolokatsioon"),
        ),
        keywords=("terrapoint", "kkk", "metsaandmed", "EUDR"),
    ),
)

PAGES_BY_SLUG: dict[str, SeoPage] = {page.slug: page for page in PAGES}


def page_for_slug(slug: str) -> SeoPage | None:
    return PAGES_BY_SLUG.get(slug)
