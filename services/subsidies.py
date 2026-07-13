import re
from datetime import date


VERIFIED_AT = "2026-07-13"
CATALOG_VALID_THROUGH = date(2026, 12, 31)

LIKELY = "Tõenäoliselt sobib"
CHECK = "Vajab kontrolli"
INELIGIBLE = "Ei sobi teadaolevate andmete põhjal"


def _today() -> date:
    return date.today()


def _parse_date(value: str) -> date:
    """Parse only complete DD.MM.YYYY dates; incomplete dates are not evidence."""
    match = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", value.strip())
    if not match:
        raise ValueError("Taotluskuupäeval peab olema aasta")
    day, month, year = (int(part) for part in match.groups())
    return date(year, month, day)


def _application_status(application) -> str:
    """Return open/upcoming/closed/year_round/awaiting_dates.

    Legacy display strings are accepted only when every parsed date includes a
    year. This prevents historical or yearless dates becoming a current round.
    """
    if isinstance(application, str):
        value = application.strip()
        if value == "Aastaringselt":
            return "year_round"
        if not value or "täpsustamisel" in value.lower():
            return "awaiting_dates"
        ranges = re.findall(
            r"(\d{2}\.\d{2}(?:\.\d{4})?)\s*[–-]\s*(\d{2}\.\d{2}(?:\.\d{4})?)",
            value,
        )
        if not ranges or any(len(start.split(".")) != 3 or len(end.split(".")) != 3 for start, end in ranges):
            return "awaiting_dates"
        periods = [{"start": start, "end": end} for start, end in ranges]
    else:
        kind = application.get("type")
        if kind == "year_round":
            return "year_round"
        if kind == "awaiting_dates":
            return "awaiting_dates"
        periods = application.get("periods", [])

    if not periods:
        return "awaiting_dates"

    today = _today()
    parsed = [(_parse_date(period["start"]), _parse_date(period["end"])) for period in periods]
    if any(start <= today <= end for start, end in parsed):
        return "open"
    if any(today < start for start, _ in parsed):
        return "upcoming"
    return "closed"


def _application_badge(status: str) -> str:
    return {
        "open": "Taotlus avatud",
        "upcoming": "Taotlusvoor tulemas",
        "closed": "Taotlusvoor lõppenud",
        "year_round": "Aastaringselt",
        "awaiting_dates": "Kuupäevad selgumisel",
    }[status]


def _application_period_label(application: dict) -> str:
    kind = application.get("type")
    if kind == "year_round":
        return "Aastaringselt"
    if kind == "awaiting_dates":
        return "2026. aasta kuupäevad avaldamata"

    labels = []
    periods = application.get("periods", [])
    for index, period in enumerate(periods, start=1):
        start = period["start"].rsplit(".", 1)[0]
        end = period["end"]
        label = f"{start}–{end}"
        if len(periods) > 1:
            label = f"{'I' * index} voor {label}"
        labels.append(label)
    return "; ".join(labels) if labels else "2026. aasta kuupäevad avaldamata"


def _assessment(status, reason, matches=None, match_scope="none", limited=False):
    return {
        "status": status,
        "reason": reason,
        "matches": matches or [],
        "match_scope": match_scope,
        "limited": limited,
    }


def _match(stand, reason, *facts):
    return {"stand": stand, "reason": reason, "facts": facts}


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _forest_or_stand_data_missing(data):
    return not data.get("forest_data_complete", False) or not data.get("stand_data_complete", False)


def _assess_protection(data):
    if data.get("natura_2000") or data.get("kaitseala"):
        return _assessment(
            LIKELY,
            "Kinnistul on ametliku kihi järgi looduskaitse või Natura 2000 ruumiline kattuvus. Täpne toetusmäär sõltub piirangu liigist.",
            match_scope="property",
        )
    if not data.get("protection_data_complete", False):
        return _assessment(
            CHECK,
            "Looduskaitse- ja Natura ruumiandmed puuduvad või on osalised.",
            match_scope="property",
            limited=True,
        )
    return _assessment(
        INELIGIBLE,
        "Ametlikes ruumikihtides ei tuvastatud kinnistul selle meetme kaitseala kattuvust.",
        match_scope="property",
    )


def _assess_vep(data):
    if data.get("vaariselupaik"):
        return _assessment(
            LIKELY,
            "Kinnistul on tuvastatud EELISesse kantud vääriselupaik; lepingu võimalikkuse kinnitab Keskkonnaamet.",
            match_scope="property",
        )
    if data.get("vep_data_complete", False):
        return _assessment(
            INELIGIBLE,
            "Kontrollitud EELIS andmetes ei tuvastatud kinnistul vääriselupaika.",
            match_scope="property",
        )
    return _assessment(
        CHECK,
        "Terrapointi vastus ei sisalda autoriteetset vääriselupaiga kontrolli; küsi kinnitust Keskkonnaametilt.",
        match_scope="property",
        limited=True,
    )


def _assess_climate_shaping(data):
    if _forest_or_stand_data_missing(data):
        return _assessment(CHECK, "Metsaeraldiste vanuse- või pindalaandmed puuduvad või on osalised.", limited=True)
    matches = []
    partial_stands = False
    for stand in data.get("eraldised", []):
        age = _number(stand.get("vanus"))
        area = _number(stand.get("pindala_ha"))
        if stand.get("eraldis_nr") is None or age is None or area is None or area <= 0:
            partial_stands = True
            continue
        if 11 <= age <= 30:
            display_age = int(age) if age.is_integer() else age
            matches.append(_match(
                stand,
                f"Eraldise vanus {display_age} a jääb toetuse 11–30 aasta vahemikku.",
                "vanus",
            ))
    hectares = sum(_number(item["stand"].get("pindala_ha")) or 0 for item in matches)
    if hectares >= 1:
        return _assessment(
            LIKELY,
            f"Vanuse järgi sobivaid eraldisi on {hectares:.2f} ha; ametlik miinimum on 1 ha.",
            matches,
            "compartment",
        )
    if partial_stands:
        return _assessment(
            CHECK,
            "Vähemalt ühe eraldise number, vanus või pindala puudub või on vigane; 1 ha ja vanuse tingimust ei saa kindlalt kontrollida.",
            matches,
            "compartment" if matches else "none",
            limited=True,
        )
    if matches:
        return _assessment(
            INELIGIBLE,
            f"11–30-aastaseid eraldisi on {hectares:.2f} ha, mis jääb alla 1 ha miinimumi.",
            matches,
            "compartment",
        )
    return _assessment(
        INELIGIBLE,
        "Teadaolevate eraldiste hulgas ei ole 11–30-aastast puistut.",
        match_scope="compartment",
    )


def _assess_establishment(data):
    if not data.get("forest_data_complete", False):
        return _assessment(CHECK, "Metsamaa andmed puuduvad või on osalised.", limited=True)
    return _assessment(
        CHECK,
        "Terrapoint ei tea tehtud uuendustöid, kasutatud taimi ega metsaühistu kaudu taotlemise võimalust.",
    )


def _assess_afforestation(data):
    if not data.get("forest_data_complete", False) or not data.get("pindala_ha"):
        return _assessment(CHECK, "Kinnistu pindala- või metsamaa andmed puuduvad või on osalised.", limited=True)
    return _assessment(
        CHECK,
        "Sobivus sõltub ametlikust metsastatava maa kaardist ja metsaühistu kaudu taotlemisest; neid andmeid Terrapoint ei tuvasta.",
    )


def _assess_beetle(data):
    if _forest_or_stand_data_missing(data) or not data.get("spruce_data_complete", False):
        return _assessment(
            CHECK,
            "Kuuse osakaalu või vanuse detail on puudulik; üraskikahjustuse ennetamise vajadus tuleb kohapeal kontrollida.",
            limited=True,
        )
    matches = []
    partial_stands = False
    for stand in data.get("eraldised", []):
        raw_spruce_age = stand.get("kuuse_vanus_max") or (stand.get("vanus") if stand.get("puuliik_kood") == "KU" else 0)
        spruce_age = _number(raw_spruce_age)
        area = _number(stand.get("pindala_ha"))
        if stand.get("eraldis_nr") is None or area is None or area <= 0 or spruce_age is None:
            partial_stands = True
            continue
        if (stand.get("sisaldab_kuuske") or stand.get("puuliik_kood") == "KU") and spruce_age > 30:
            display_age = int(spruce_age) if spruce_age.is_integer() else spruce_age
            matches.append(_match(
                stand,
                f"Eraldis sisaldab kuuske, mille teadaolev suurim vanus on {display_age} a (>30 a).",
                "puuliik",
                "puuliik_kood",
                "vanus",
            ))
    if matches:
        return _assessment(
            LIKELY,
            "Leiti üle 30-aastast kuuske sisaldavaid eraldisi; toetatav töö ja kahjustuse värskus vajavad eraldi tõendamist.",
            matches,
            "compartment",
        )
    if partial_stands:
        return _assessment(
            CHECK,
            "Vähemalt ühe eraldise kuuse-, vanuse- või pindalaandmed on puudulikud; toetatavaid tegevusi ei saa välistada.",
            limited=True,
        )
    return _assessment(
        CHECK,
        "Üle 30-aastast kuuske ei leitud, kuid värske tormikahjustuse likvideerimise toetatavust ei saa nende andmete põhjal välistada.",
        limited=True,
    )


def _assess_metsameede(data):
    return _assessment(
        CHECK,
        "2026. aasta taotlusvooru kuupäevi ei ole ametlikult avaldatud ning sobivus sõltub kavandatud tegevusest.",
    )


def _assess_inventory(data):
    if not data.get("forest_data_complete", False):
        return _assessment(CHECK, "Metsaeraldiste andmed puuduvad või on osalised.", limited=True)
    stands = [
        _match(stand, "Metsaregistris olev eraldis võib kuuluda inventeeritava ala hulka.")
        for stand in data.get("eraldised", [])
    ]
    if not stands:
        return _assessment(
            CHECK,
            "Metsaregistris ei ole eraldisi, kuid metsamaa ja inventeerimise vajadus tuleb eraldi kontrollida.",
            limited=True,
        )
    return _assessment(
        CHECK,
        "Metsaeraldised on olemas, kuid taotleda saab metsaühistu ning kontrollida tuleb seitsme aasta piirangut ja inventuuri kehtivust.",
        stands,
        "compartment",
    )


def _assess_heritage(data):
    return _assessment(
        CHECK,
        "Terrapoint ei tuvasta toetuse ametlikku nimekirja kantud pärandkultuuri objekti ega kavandatud töid.",
    )


def _assess_drainage(data):
    if _forest_or_stand_data_missing(data):
        return _assessment(CHECK, "Metsaeraldiste andmed puuduvad või on osalised.", limited=True)
    matches = [
        _match(stand, "Eraldise andmetes on kuivenduse tunnus; süsteemi registrikanne ja tööde vajadus tuleb kontrollida.")
        for stand in data.get("eraldised", [])
        if stand.get("kuivendatud")
    ]
    return _assessment(
        CHECK,
        "2026. aasta taotluskuupäevi ei ole avaldatud; toetada saab üksnes registrisse kantud olemasoleva maaparandussüsteemi töid.",
        matches,
        "compartment" if matches else "none",
    )


def _assess_association(data):
    return _assessment(
        CHECK,
        "Meede on mõeldud metsaühistule, mitte metsaomaniku otsetaotluseks; uuri oma ühistult, kas tegevus hõlmab sind.",
    )


SUBSIDY_PROGRAMS = [
    {
        "id": "looduskaitse-piirangute-huvitis",
        "name": "Looduskaitseliste piirangute hüvitamine",
        "category": "looduskaitse",
        "amount": "Natura sihtkaitsevööndis kuni 160 €/ha; muudes toetatavates piirangukategooriates kuni 60 €/ha",
        "application": {"type": "fixed", "periods": [{"start": "04.04.2026", "end": "30.04.2026"}]},
        "application_channel": "Vana e-PRIA (ligipääs e-PRIA kaudu)",
        "applicant_scope": "Erametsa omanik või nõuetele vastav kasutusvaldaja",
        "source_name": "PRIA: Natura 2000 erametsades elurikkuse soodustamise toetus 2026",
        "source_url": "https://www.pria.ee/toetused/natura-2000-erametsades-elurikkuse-soodustamise-toetus-2026",
        "source_as_of": "2026-04-04",
        "description": "Iga-aastane hüvitis Natura 2000 ja muude nõuetele vastavate looduskaitseliste piirangutega erametsale.",
        "verification_items": ["toetusõigusliku ala kaart ja piirangu kategooria", "vähemalt 0,3 ha nõue", "omandi- või kasutusvalduse õigus", "VEP lepingu puudumine samal alal"],
        "assess": _assess_protection,
        "match_label": "Kattuvus on teada kinnistu, mitte eraldise täpsusega",
    },
    {
        "id": "vep-kaitseleping",
        "name": "Vääriselupaiga kaitseks lepingu sõlmimine",
        "category": "looduskaitse",
        "amount": "Kasvava metsa väärtuse põhine hüvitis, makstakse 20 aasta jooksul võrdsete aastamaksetena",
        "application": {"type": "year_round"},
        "application_channel": "Esmalt Keskkonnaamet; lepingu ja maksed korraldab KIK",
        "applicant_scope": "Erametsa omanik",
        "source_name": "Keskkonnaamet: vääriselupaigad",
        "source_url": "https://www.keskkonnaamet.ee/elusloodus-looduskaitse/metsandus/vaariselupaigad",
        "source_as_of": "2025-02-17",
        "description": "Vabatahtlik 20-aastane notariaalne leping väljaspool kaitstavat loodusobjekti asuva EELISesse kantud VEP kaitseks.",
        "verification_items": ["VEP kanne EELISes", "ala paiknemine väljaspool kaitstavat loodusobjekti", "Keskkonnaameti hinnang", "notariaalse lepingu tingimused"],
        "assess": _assess_vep,
        "match_label": "VEP asukohta ei määrata Terrapointis eraldise täpsusega",
    },
    {
        "id": "kliimakindla-metsa-kujundamine",
        "name": "Mitmekesise ja kliimakindla metsa kujundamise toetus",
        "category": "metsahooldus",
        "amount": "356 €/ha füüsilise isiku või FIE maal; 297 €/ha juriidilise isiku või metsaühistu maal",
        "application": {"type": "fixed", "periods": [{"start": "07.04.2026", "end": "23.04.2026"}]},
        "application_channel": "e-PRIA",
        "applicant_scope": "Erametsa omanik või metsaühistu",
        "source_name": "Erametsakeskus: metsa kujundamine",
        "source_url": "https://www.eramets.ee/metsa-kujundamine/",
        "source_as_of": "2026-04-07",
        "description": "11–30-aastase puistu hooldusraie mitmeliigilise ja struktuuririkka metsa kujundamiseks.",
        "verification_items": ["kehtivad inventeerimisandmed", "vähemalt 1 ha ja kuni 30 ha omaniku kohta", "säilikpuude ja lamapuidu nõuded", "töö tegemise ja kulude tõendid"],
        "assess": _assess_climate_shaping,
        "match_label": "Eraldised vanusega 11–30 aastat",
    },
    {
        "id": "kliimakindla-metsa-rajamine",
        "name": "Mitmekesise ja kliimakindla metsa rajamise toetus",
        "category": "metsastamine",
        "amount": "Maapinna ettevalmistus 96 €/ha; taimed ja istutamine 400 €/ha; uuenduse hooldus 150 €/ha",
        "application": {"type": "fixed", "periods": [{"start": "16.06.2026", "end": "02.07.2026"}, {"start": "17.11.2026", "end": "01.12.2026"}]},
        "application_channel": "Uus e-PRIA, taotlejaks metsaühistu",
        "applicant_scope": "Metsaühistu oma liikme metsa kohta",
        "source_name": "Erametsakeskus: mitmekesise ja kliimakindla metsa rajamise toetus",
        "source_url": "https://www.eramets.ee/toetused/metsa-uuendamise-toetus/",
        "source_as_of": "2026-06-16",
        "description": "Metsa uuendamise tööde toetus, mida taotleb vähemalt 200 liikmega metsaühistu pärast tööde tegemist.",
        "verification_items": ["metsaühistu liikmesus ja taotlemine ühistu kaudu", "töö tegemise aeg ja tõendid", "taimede päritolu ja istutustihedus", "omaniku ettevõtte suuruse piirang"],
        "assess": _assess_establishment,
        "match_label": "Tehtud uuendustöid ei saa eraldiseandmetest tuvastada",
    },
    {
        "id": "metsastamine",
        "name": "Metsastamise toetus",
        "category": "metsastamine",
        "amount": "Uue metsa rajamine 1420 €/ha; taimede hooldus 260 €/ha aastas",
        "application": {"type": "fixed", "periods": [{"start": "16.04.2026", "end": "07.05.2026"}]},
        "application_channel": "e-PRIA, taotlejaks metsaühistu",
        "applicant_scope": "Metsaühistu liikme maal või omaniku volituse alusel",
        "source_name": "Riigi Teataja: metsastamise toetus",
        "source_url": "https://www.riigiteataja.ee/akt/124032026004",
        "source_as_of": "2026-03-24",
        "description": "Ametlikule kaardile kantud kasutusest väljas vähemalt 0,3 ha suuruse mittemetsamaa metsastamine.",
        "verification_items": ["ala kuulumine ametlikule toetatava maa kaardile", "vähemalt 0,3 ha ja 15 m laius", "kuni 30 ha omaniku kohta", "metsaühistu volitus"],
        "assess": _assess_afforestation,
        "match_label": "Meede puudutab mittemetsamaad, mitte olemasolevaid metsaeraldisi",
    },
    {
        "id": "uraskikahjustuste-ennetamine",
        "name": "Üraskikahjustuste ennetamise toetus",
        "category": "kahjuritõrje",
        "amount": "Püünispuud kuni 500 €/katastriüksus; feromoonpüünise komplekt 40 €; värske tormikahjustuse likvideerimine kuni 500 €/katastriüksus",
        "application": {"type": "fixed", "periods": [{"start": "01.09.2026", "end": "15.09.2026"}]},
        "application_channel": "E-post või post KIKile; püünispuude puhul taotleb metsaühistu",
        "applicant_scope": "Erametsa omanik või metsaühistu, tegevusest sõltuvalt",
        "source_name": "Erametsakeskus: üraskikahjustuste ennetamine",
        "source_url": "https://www.eramets.ee/uraskikahjustuste-ennetamine/",
        "source_as_of": "2026-07-13",
        "description": "Püünispuude, feromoonpüüniste ja värske tormikahjustuse likvideerimise toetus.",
        "verification_items": ["kehtivad inventeerimisandmed", "toetatava töö liik ja tähtajaks tegemine", "konsulendi kinnitus", "tormikahjustuse värskus või püüniste nõuded"],
        "assess": _assess_beetle,
        "match_label": "Üle 30-aastast kuuske sisaldavad eraldised",
    },
    {
        "id": "metsameede-monitoring",
        "name": "Erametsade kliimamuutustega kohanemise investeeringutoetus (Metsameede)",
        "category": "metsahooldus",
        "amount": "2026 määrad ja taotlusvoor vajavad ametlikku kinnitust",
        "application": {"type": "awaiting_dates"},
        "application_channel": "e-PRIA viimase ametliku vooru järgi",
        "applicant_scope": "Metsaomanik, metsaühistu, FIE või nõuetele vastav mikroettevõtja",
        "source_name": "KIK: Metsameede",
        "source_url": "https://www.kik.ee/et/toetatavad-tegevused/metsameede",
        "source_as_of": "2026-07-13",
        "description": "Jälgimiskanne: ametlikud lehed näitavad viimati 2025. aasta vooru, mitte kinnitatud 2026. aasta taotlusperioodi.",
        "verification_items": ["2026 taotlusvooru ametlik väljakuulutamine", "toetatav tegevus", "taotleja ja metsamaa nõuded", "tööde ajastus"],
        "assess": _assess_metsameede,
        "match_label": "Tegevus ja 2026 tingimused ei ole eraldise sobivuse määramiseks teada",
    },
    {
        "id": "metsa-inventeerimine",
        "name": "Metsa inventeerimise ja püsimetsanduse metsamajandamiskava koostamise toetus",
        "category": "inventeerimine",
        "amount": "20 €/ha inventeerimine; 25 €/ha inventeerimine koos püsimetsakavaga",
        "application": {"type": "fixed", "periods": [{"start": "01.12.2026", "end": "15.12.2026"}]},
        "application_channel": "Uus e-PRIA, taotlejaks metsaühistu",
        "applicant_scope": "Vähemalt 200 liikmega metsaühistu liikme metsa kohta",
        "source_name": "Riigi Teataja: erametsanduse toetuse andmise alused",
        "source_url": "https://www.riigiteataja.ee/akt/110032026007",
        "source_as_of": "2026-03-10",
        "description": "Inventeerimisandmete registrisse kandmise ning soovi korral lageraieta majandamist kirjeldava püsimetsakava toetus.",
        "verification_items": ["taotlemine metsaühistu kaudu", "inventeerimisandmete registrisse kandmine", "seitsme aasta piirang", "püsimetsakava nõuded 25 €/ha määra jaoks"],
        "assess": _assess_inventory,
        "match_label": "Metsaregistris olevad eraldised; lõpliku inventeeritava ala määrab ühistu",
    },
    {
        "id": "parandkultuuri-sailitamine",
        "name": "Pärandkultuuri säilitamise ja eksponeerimise toetus",
        "category": "kultuur",
        "amount": "Kuni 80% abikõlblikust kulust, kuni 2000 €/objekt aastas",
        "application": {"type": "fixed", "periods": [{"start": "16.06.2026", "end": "02.07.2026"}]},
        "application_channel": "E-post või post KIKile",
        "applicant_scope": "Erametsa omanik või metsaühistu",
        "source_name": "Erametsakeskus: pärandkultuuri säilitamise toetus",
        "source_url": "https://www.eramets.ee/toetused/parandkultuuri-sailitamise-toetus/",
        "source_as_of": "2026-06-16",
        "description": "Erametsamaal asuva ametlikku nimekirja kantud pärandkultuuri objekti säilitamine ja eksponeerimine.",
        "verification_items": ["objekti kanne ametlikus nimekirjas", "objekti paiknemine erametsamaal", "kavandatud tööde abikõlblikkus", "kuludokumendid ja oma töö arvestus"],
        "assess": _assess_heritage,
        "match_label": "Pärandkultuuri objekti asukohta ei saa metsaeraldiste põhjal määrata",
    },
    {
        "id": "maaparandussusteemi-korrastamine",
        "name": "Maaparandussüsteemi korrastamise toetus",
        "category": "maaparandus",
        "amount": "Kuni 10 000 € omaniku kohta; tegevustel ametlikud ühikumäärad",
        "application": {"type": "awaiting_dates"},
        "application_channel": "E-post, post või KIKi kontor viimase ametliku vooru järgi",
        "applicant_scope": "Erametsa omanik või metsaühistu",
        "source_name": "Erametsakeskus: metsamaaparandustööde toetus",
        "source_url": "https://www.eramets.ee/toetused/metsamaaparandustoode-toetus/",
        "source_as_of": "2025-11-03",
        "description": "Registrisse kantud olemasoleva metsakuivendussüsteemi kraavide, voolunõvade ja truupide korrastamine.",
        "verification_items": ["maaparandussüsteemi registrikanne", "tööde vastavus toetatavatele tegevustele", "omaniku nõusolekud ja projekt", "2026 taotlusvooru väljakuulutamine"],
        "assess": _assess_drainage,
        "match_label": "Kuivenduse tunnusega eraldised; registrikanne vajab kontrolli",
    },
    {
        "id": "vastutustundliku-metsanduse-edendamine",
        "name": "Vastutustundliku metsanduse edendamise toetus",
        "category": "ühistu",
        "amount": "Kuni 100 € nõustatud füüsilisest isikust või FIEst metsaomaniku kohta",
        "application": {"type": "fixed", "periods": [{"start": "03.03.2026", "end": "17.03.2026"}]},
        "application_channel": "Uus e-PRIA, taotlejaks metsaühistu",
        "applicant_scope": "Vähemalt 400 liikmega metsaühistu",
        "source_name": "Erametsakeskus: ühistutoetus",
        "source_url": "https://www.eramets.ee/toetused/uhistutoetus/",
        "source_as_of": "2026-03-03",
        "description": "Metsaühistu nõustamistegevuse toetus; metsaomanik ei esita otsetaotlust.",
        "verification_items": ["metsaühistu osalemine meetmes", "omaniku liikmesus või nõustamise tingimused", "nõustamistegevuse dokumenteerimine"],
        "assess": _assess_association,
        "match_label": "Ühistu tegevus ei ole seotud ühe konkreetse eraldisega",
    },
    {
        "id": "metsauhistu-toetus",
        "name": "Metsaühistu toetus",
        "category": "ühistu",
        "amount": "Kuni 30 € metsaühistu liikme kohta",
        "application": {"type": "fixed", "periods": [{"start": "03.03.2026", "end": "17.03.2026"}]},
        "application_channel": "E-post või post KIKile, taotlejaks metsaühistu",
        "applicant_scope": "Vähemalt 400 liikmega metsaühistu",
        "source_name": "Erametsakeskus: ühistutoetus",
        "source_url": "https://www.eramets.ee/toetused/uhistutoetus/",
        "source_as_of": "2026-03-03",
        "description": "Metsaühistu tegevuskulude toetus; metsaomanik ei esita otsetaotlust.",
        "verification_items": ["metsaühistu vastavus liikmete arvu nõudele", "omaniku liikmesus", "ühistu toetatavad tegevused"],
        "assess": _assess_association,
        "match_label": "Ühistu tegevus ei ole seotud ühe konkreetse eraldisega",
    },
]


def _eraldised_to_summary(matches):
    summaries = []
    for item in matches:
        stand = item["stand"]
        number = stand.get("eraldis_nr")
        if number is None:
            continue
        summary = {
            "eraldis_nr": number,
            "pindala_ha": _number(stand.get("pindala_ha")) or 0,
            "match_reason": item["reason"],
        }
        for fact in item.get("facts", ()):
            if stand.get(fact) is not None:
                summary[fact] = stand.get(fact)
        summaries.append(summary)

    def sort_key(summary):
        try:
            return (0, float(summary["eraldis_nr"]))
        except (TypeError, ValueError):
            return (1, str(summary["eraldis_nr"]))

    summaries.sort(key=sort_key)
    return summaries


def check_subsidies(data: dict) -> list[dict]:
    results = []
    catalog_expired = _today() > CATALOG_VALID_THROUGH
    for program in SUBSIDY_PROGRAMS:
        try:
            assessment = program["assess"](data)
        except (TypeError, ValueError, KeyError):
            assessment = _assessment(
                CHECK,
                "Sisendandmete kuju ei võimaldanud tingimusi usaldusväärselt kontrollida.",
                limited=True,
            )
        if catalog_expired:
            assessment = _assessment(
                CHECK,
                "2026. aasta toetuste kataloogi kehtivusaeg on möödunud; tingimused, määrad ja kuupäevad vajavad uut ametlikku kontrolli.",
                limited=True,
            )
        matches = _eraldised_to_summary(assessment["matches"])
        matched_ha = round(sum(item["pindala_ha"] for item in matches), 2)
        application_status = "awaiting_dates" if catalog_expired else _application_status(program["application"])
        application_period = _application_period_label(program["application"])
        periods = program["application"].get("periods", [])
        authority = "PRIA" if program["id"] == "looduskaitse-piirangute-huvitis" else "KIK / Keskkonnaamet" if program["id"] == "vep-kaitseleping" else "KIK"
        result = {
            "id": program["id"],
            "name": program["name"],
            "nimi": program["name"],
            "eligibility_status": assessment["status"],
            "eligibility_reason": assessment["reason"],
            "verification_items": program["verification_items"],
            "application_status": application_status,
            "application_period": application_period,
            "application_periods": periods,
            "application_channel": program["application_channel"],
            "amount": program["amount"],
            "applicant_scope": program["applicant_scope"],
            "source_name": program["source_name"],
            "source_url": program["source_url"],
            "source_as_of": program["source_as_of"],
            "verified_at": VERIFIED_AT,
            "authority": authority,
            "catalog_valid_through": CATALOG_VALID_THROUGH.isoformat(),
            "disclaimer": "Terrapointi hinnang on esmane sõelumine. Lõpliku otsuse teeb toetuse andja.",
            "description": program["description"],
            "category": program["category"],
            "match_scope": assessment["match_scope"],
            "eraldised_match": matches,
            "eraldised_match_count": len(matches),
            "eraldised_match_ha": matched_ha,
            "eraldised_filter_label": program["match_label"],
            "andmed_piiratud": assessment["limited"],
            # Legacy keys retained for the current API consumer.
            "sobib": assessment["status"] == LIKELY,
            "pohjus": assessment["reason"],
            "summa": program["amount"],
            "asutus": authority,
            "taotlusvoor": application_period,
            "voor_status": {"year_round": "open", "awaiting_dates": "unknown"}.get(application_status, application_status),
            "voor_badge": _application_badge(application_status),
            "url": program["source_url"],
            "voor_url": program["source_url"],
            "kirjeldus": program["description"],
        }
        results.append(result)

    eligibility_order = {LIKELY: 0, CHECK: 1, INELIGIBLE: 2}
    application_order = {"open": 0, "year_round": 1, "upcoming": 2, "awaiting_dates": 3, "closed": 4}
    results.sort(key=lambda item: (
        eligibility_order[item["eligibility_status"]],
        application_order[item["application_status"]],
        item["name"],
    ))
    return results
