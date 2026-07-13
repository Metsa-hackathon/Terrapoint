from datetime import datetime, date


def _today() -> date:
    """Dynaamiline kuupäev — uueneb iga kutsungiga, mitte fikseeritud laadimisel."""
    return date.today()


def _parse_date(d: str) -> date:
    """Parse 'DD.MM.YYYY' or 'DD.MM' (assumes current year) to date."""
    parts = d.strip().split(".")
    day, month = int(parts[0]), int(parts[1])
    year = int(parts[2]) if len(parts) > 2 else _today().year
    return date(year, month, day)


def _voor_status(voor: str) -> str:
    """Return 'open', 'closed', or 'upcoming' based on date ranges in voor string."""
    if not voor or voor in ("Aastaringselt", "Täpsustamisel"):
        return "open" if voor == "Aastaringselt" else "unknown"
    import re
    ranges = re.findall(r"(\d{2}\.\d{2}(?:\.\d{4})?)\s*[-–]\s*(\d{2}\.\d{2}(?:\.\d{4})?)", voor)
    if not ranges:
        return "unknown"
    today = _today()
    for start_s, end_s in ranges:
        start = _parse_date(start_s)
        end = _parse_date(end_s)
        if start <= today <= end:
            return "open"
        if today < start:
            return "upcoming"
    return "closed"


def _voor_badge(voor: str) -> str:
    """Return a human-readable status badge for the application window."""
    status = _voor_status(voor)
    if status == "open":
        return "Taotlusvoor avatud"
    elif status == "upcoming":
        return "Tulemas"
    elif status == "closed":
        return "Tähtaeg möödunud"
    return ""


SUBSIDY_PROGRAMS = [
    # === Conservation (KIK) ===
    {
        "name": "Looduskaitseliste piirangute hüvitamine",
        "condition": lambda d: d.get("kaitseala") or d.get("natura_2000"),
        "reject_reason": lambda d: "Krundil puuduvad looduskaitselised piirangud (Natura 2000 või kaitseala)",
        "amount": "60–160 €/ha",
        "asutus": "KIK",
        "voor": "04.04–30.04.2026",
        "url": "https://www.eramets.ee/toetused/natura-metsa-toetus/",
        "voor_url": "https://www.eramets.ee/toetuste_tahtajad/",
        "description": "Natura 2000 alal kuni 160 €/ha, mujal kaitsealadel 60 €/ha. Hüvitab looduskaitseliste piirangute tõttu saamata jäänud tulu. Taotlus esitada igal aastal uuesti e-PRIAs. Min 0,3 ha.",
        "category": "looduskaitse",
        # Hõlmab kõiki kinnistu eraldisi kaitsealal/Natura 2000 alal
        "eraldised_filter": lambda d: d.get("eraldised", []) if (d.get("kaitseala") or d.get("natura_2000")) else [],
        "eraldised_filter_label": "Kõik kinnistu eraldised kaitsealal või Natura 2000 alal",
    },
    {
        "name": "Vääriselupaiga hooldus",
        "condition": lambda d: d.get("vaariselupaik"),
        "reject_reason": lambda d: "Krundil ei tuvastatud vääriselupaika (EELIS andmetel)",
        "amount": "20a leping, hüvitis arvutatakse individuaalselt",
        "asutus": "KIK",
        "voor": "Aastaringselt",
        "url": "https://www.eramets.ee/toetused/vaariselupaiga-kaitseks-lepingu-solmimine/",
        "description": "Vääriselupaiga kaitseks 20-aastase lepingu sõlmimine. Sisaldab kaitse-eeskirja koostamist ja hoolduskava. Taotlemine aastaringselt.",
        "category": "looduskaitse",
        "eraldised_filter": lambda d: d.get("eraldised", []) if d.get("vaariselupaik") else [],
        "eraldised_filter_label": "Vääriselupaiga eraldised (tuvastatakse EELIS andmetest)",
    },
    {
        "name": "Metsakasutuse kitsendustest hüvitis",
        "condition": lambda d: d.get("kaitseala") or d.get("natura_2000") or d.get("natura_elupaik"),
        "reject_reason": lambda d: "Krundil puuduvad metsakasutuse kitsendused (kaitseala, Natura 2000 või Natura elupaik)",
        "amount": "hüvitis arvutatakse kahjude ja kulude alusel",
        "asutus": "KIK",
        "voor": "Täpsustamisel",
        "url": "https://www.kik.ee/et/toetatavad-tegevused",
        "description": "Metsakasutuse kitsendustest põhjustatud kahjude ja kulude hüvitamine erametsaomanikele. Erinevalt looduskaitse hüvitisest (saamata jäänud tulu), kompenseerib tegelikud kahjud ja kulud.",
        "category": "looduskaitse",
        "eraldised_filter": lambda d: d.get("eraldised", []) if (d.get("kaitseala") or d.get("natura_2000") or d.get("natura_elupaik")) else [],
        "eraldised_filter_label": "Kõik eraldised kitsendustega alal",
    },

    # === Metsameede (PRIA/KIK) ===
    {
        "name": "Metsameede",
        "condition": lambda d: 10 <= d.get("keskm_vanus", 0) <= 60 and d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: (
            "Metsa vanus peab olema 10–60 aastat (praegu " + str(d.get("keskm_vanus", 0)) + "a)"
            if not (10 <= d.get("keskm_vanus", 0) <= 60)
            else "Metsa pindala peab olema vähemalt 0,1 ha (praegu " + str(round(d.get("mets_pindala", 0), 2)) + " ha)"
        ),
        "amount": "kuni 200 €/ha",
        "asutus": "KIK",
        "voor": "Täpsustamisel (2025: 16.09–07.10)",
        "url": "https://www.eramets.ee/toetused/metsameede/",
        "description": "Hooldusraie kuni 10a puistus, metsakahjustuste ennetamine (männikärsakas, juurepess), loodusõnnetuses kahjustada saanud metsa uuendamine. Elurikkuse nõuded: säilikpuud ja lamapuit.",
        "category": "metsahooldus",
        "eraldised_filter": lambda d: [
            e for e in d.get("eraldised", [])
            if 10 <= (e.get("vanus") or 0) <= 60
        ],
        "eraldised_filter_label": "Eraldised vanusega 10–60 aastat",
    },
    {
        "name": "Kliimakindla metsa kujundamine",
        "condition": lambda d: 11 <= d.get("keskm_vanus", 0) <= 30 and d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: (
            "Metsa vanus peab olema 11–30 aastat (praegu " + str(d.get("keskm_vanus", 0)) + "a)"
            if not (11 <= d.get("keskm_vanus", 0) <= 30)
            else "Metsa pindala peab olema vähemalt 0,1 ha"
        ),
        "amount": "356 €/ha (eraisik) / 297 €/ha (juriidiline)",
        "asutus": "KIK",
        "voor": "07.04–23.04.2026",
        "url": "https://www.eramets.ee/metsa-kujundamine/",
        "voor_url": "https://www.eramets.ee/toetuste_tahtajad/",
        "description": "Hooldusraie 11–30a metsas. Mitmeliigilise ja struktuuririkka metsa kujundamine. Min 1 ha aastas, max 30 ha. Ainult e-PRIA kaudu. Eelarve 1,6M €.",
        "category": "metsahooldus",
        "eraldised_filter": lambda d: [
            e for e in d.get("eraldised", [])
            if 11 <= (e.get("vanus") or 0) <= 30
        ],
        "eraldised_filter_label": "Eraldised vanusega 11–30 aastat",
    },

    # === Metsastamine (KIK) ===
    {
        "name": "Metsastamise toetus",
        "condition": lambda d: d.get("mets_pindala", 0) == 0 and d.get("siht1") != "ELAMUMAA" and d.get("pindala_ha", 0) >= 0.3,
        "reject_reason": lambda d: (
            "Krundil on juba metsa (" + str(round(d.get("mets_pindala", 0), 1)) + " ha)"
            if d.get("mets_pindala", 0) > 0
            else "Krunt on elamumaa"
            if d.get("siht1") == "ELAMUMAA"
            else "Krundi pindala peab olema vähemalt 0,3 ha (praegu " + str(round(d.get("pindala_ha", 0), 2)) + " ha)"
        ),
        "amount": "1420 €/ha (rajamine) + 260 €/ha/aasta (hooldus)",
        "asutus": "KIK",
        "voor": "16.04–07.05.2026",
        "url": "https://www.eramets.ee/metsastamine/",
        "voor_url": "https://www.eramets.ee/toetuste_tahtajad/",
        "description": "Uue metsa rajamine. Min 0,3 ha, laius vähemalt 15m, max 30 ha omaniku kohta. Ainult metsaühistu kaudu (min 200 liiget). Eelarve 840 000 €.",
        "category": "metsastamine",
        # Metsastamise toetus: kinnistul ei tohi olla metsa, seega eraldisi pole
        "eraldised_filter": lambda d: [],
        "eraldised_filter_label": "Metsastatavale alale (eraldisi hetkel ei ole)",
    },

    # === Metsa uuendamine (KIK) ===
    {
        "name": "Metsa uuendamise toetus",
        "condition": lambda d: d.get("keskm_vanus", 0) >= d.get("keskm_raievanus", 999) and d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: (
            "Mets ei ole veel raievanuses (vanus " + str(d.get("keskm_vanus", 0)) + "a, raievanus " + str(d.get("keskm_raievanus", "?")) + "a)"
            if d.get("keskm_vanus", 0) < d.get("keskm_raievanus", 999)
            else "Metsa pindala peab olema vähemalt 0,1 ha"
        ),
        "amount": "kuni 646 €/ha",
        "asutus": "KIK",
        "voor": "I voor 16.06–02.07.2026, II voor 17.11–01.12.2026",
        "url": "https://www.eramets.ee/toetused/metsa-uuendamise-toetus/",
        "voor_url": "https://www.eramets.ee/toetuste_tahtajad/metsa-uuendamine/",
        "description": "Metsa uuendamine pärast raievanust või metsa hukkumist. Ainult metsaühistu kaudu (min 200 liiget). Taimede soetamine, istutamine, maapinna ettevalmistus, hooldus. Eelarve 622 000 €.",
        "category": "metsastamine",
        "eraldised_filter": lambda d: [
            e for e in d.get("eraldised", [])
            if (e.get("vanus") or 0) >= (e.get("raievanus") or 999)
        ],
        "eraldised_filter_label": "Raieküpsed eraldised (vanus ≥ raievanus)",
    },

    # === Kooreürask (KIK) ===
    {
        "name": "Kooreüraski tõrje",
        "condition": lambda d: d.get("has_kuusk") and d.get("max_kuusk_vanus", 0) > 30,
        "reject_reason": lambda d: (
            "Liigiline detail on osaline; teisese kuuse olemasolu vajab kontrolli"
            if not d.get("spruce_data_complete", True)
            else "Krundil ei ole üle 30a kuuski"
        ),
        "amount": "püünispuud 500 €/üksus, feromoonpüünised 40 €/komplekt, tormikahjustus 500 €/üksus",
        "asutus": "KIK",
        "voor": "01.09–15.09.2026",
        "url": "https://www.eramets.ee/uraskikahjustuste-ennetamine/",
        "voor_url": "https://www.eramets.ee/toetuste_tahtajad/uraskikahjustuste-ennetamise-toetus/",
        "description": "Püünispuud, feromoonpüünised ja tormikahjustuste likvideerimine. Kehtivad inventeerimisandmed nõutud. Konsulendi kinnitus tööde kohta vajalik. Eelarve 30 000 €.",
        "category": "kahjuritõrje",
        "requires_spruce_details": True,
        "eraldised_filter": lambda d: [
            e for e in d.get("eraldised", [])
            if (e.get("sisaldab_kuuske") or (e.get("puuliik_kood") or "") == "KU")
            and (e.get("kuuse_vanus_max") or e.get("vanus") or 0) > 30
        ],
        "eraldised_filter_label": "Üle 30a vanused kuuse eraldised",
    },

    # === KIK / Inventeerimine ===
    {
        "name": "Metsa inventeerimise toetus",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0,1 ha",
        "amount": "kuni 10 €/ha",
        "asutus": "KIK",
        "voor": "Täpsustamisel",
        "url": "https://www.eramets.ee/toetused/metsa-inventeerimise-toetus/",
        "description": "Metsa inventeerimisandmete koostamise toetus. Makstakse üks kord 7 aasta jooksul. Sisaldab metsakava koostamist.",
        "category": "inventeerimine",
        "eraldised_filter": lambda d: d.get("eraldised", []),
        "eraldised_filter_label": "Kõik kinnistu metsaeraldised",
    },

    # === KIK / Maaparandus ===
    {
        "name": "Maaparandussüsteemi korrastamine",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0,1 ha",
        "amount": "kuni 10 000 €",
        "asutus": "KIK",
        "voor": "Täpsustamisel",
        "url": "https://www.eramets.ee/toetused/metsamaaparandustoode-toetus/",
        "description": "Drenaažisüsteemide korrastamine, truupide vahetus, kraavide puhastamine. Eesmärk on parandada metsamaa veerežiimi.",
        "category": "maaparandus",
        "eraldised_filter": lambda d: [e for e in d.get("eraldised", []) if e.get("kuivendatud")],
        "eraldised_filter_label": "Kuivendatud eraldised",
    },

    # === KIK / Pärandkultuur ===
    {
        "name": "Pärandkultuuri säilitamine",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0,1 ha",
        "amount": "kuni 2000 €/objekt",
        "asutus": "KIK",
        "voor": "16.06–02.07.2026",
        "url": "https://www.eramets.ee/toetused/parandkultuuri-sailitamise-toetus/",
        "voor_url": "https://www.eramets.ee/toetuste_tahtajad/parandkultuuri-sailitamise-ja-eksponeerimise-toetus/",
        "description": "Pärandkultuuri objektide (kiviaiad, vanad puud, ajaloolised paigad) taastamine, hooldamine ja avalikuks kasutamiseks kohandamine. Eelarve 10 000 €.",
        "category": "kultuur",
        "eraldised_filter": lambda d: d.get("eraldised", []),
        "eraldised_filter_label": "Kõik metsaeraldised (pärandkultuuri objektid valitakse eraldi)",
    },

    # === PRIA / Metsaühistu ===
    {
        "name": "Metsaühistu toetus",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0,1 ha",
        "amount": "kuni 30 000 €",
        "asutus": "PRIA",
        "voor": "Täpsustamisel",
        "url": "https://www.eramets.ee/toetused/uhistutoetus/",
        "description": "Metsaühistute tegevuse toetamine. Sisaldab liikmetele teenuste osutamist, koolituste korraldamist ja ühiseid metsamajandamise tegevusi.",
        "category": "ühistu",
        "eraldised_filter": lambda d: d.get("eraldised", []),
        "eraldised_filter_label": "Kõik metsaühistu liikme metsaeraldised",
    },

    # === KIK / Metssigad ===
    {
        "name": "Metssigade küttimise toetus",
        "condition": lambda d: False,  # Only for hunting area holders
        "reject_reason": lambda d: "Ainult jahipiirkonna kasutusõigust omavatele isikutele (andmed puuduvad)",
        "amount": "65 €/metssiga",
        "asutus": "KIK",
        "voor": "27.10–31.10.2026",
        "url": "https://www.eramets.ee/metssigade-kuttimise-toetus/",
        "description": "Aafrika seakatku tõkestamiseks metssigade küttimise toetus. Ainult jahipiirkonna kasutajatele.",
        "category": "kahjuritõrje",
        "eraldised_filter": lambda d: [],
        "eraldised_filter_label": "Metssigade küttimise toetus ei ole seotud eraldistega",
    },
]


def _eraldised_to_summary(eraldised: list[dict]) -> list[dict]:
    """Convert full eraldis records to lightweight summaries for the API response.

    Each summary has: eraldis_nr, puuliik, puuliik_kood, vanus, pindala_ha.
    Tulemus sorditakse eraldis_nr järgi numbriliselt (tõusev), et UI-s
    kuvatakse eraldiste numbrid alati järjest: 1, 2, 5, 6, ... mitte 1, 10, 11, 2.
    Toetab nii int/float kui ka string-kujul numbreid (nt "901").
    """
    out = []
    for e in eraldised or []:
        nr = e.get("eraldis_nr")
        if nr is None:
            continue
        out.append({
            "eraldis_nr": nr,
            "puuliik": e.get("puuliik") or e.get("puuliik_kood") or "?",
            "puuliik_kood": e.get("puuliik_kood") or "",
            "vanus": e.get("vanus") or 0,
            "pindala_ha": e.get("pindala_ha") or 0,
        })

    def _sort_key(item: dict):
        n = item["eraldis_nr"]
        if isinstance(n, (int, float)):
            return (0, float(n))
        # String, mis on parsitav numbrina — käsitle numbrina
        try:
            return (0, float(str(n)))
        except (ValueError, TypeError):
            return (1, str(n))

    out.sort(key=_sort_key)
    return out


def check_subsidies(data: dict) -> list[dict]:
    results = []
    for prog in SUBSIDY_PROGRAMS:
        try:
            eligible = prog["condition"](data)
        except Exception:
            eligible = False

        pohjus = None
        if not eligible and "reject_reason" in prog:
            try:
                pohjus = prog["reject_reason"](data)
            except Exception:
                pohjus = "Tingimuste kontroll ebaõnnestus"

        # Eraldistega seotus: millistele konkreetsetele eraldistele toetus
        # kohaldub (või oleks kohaldatav, kui üldtingimused on täidetud).
        matched_eraldised = []
        if "eraldised_filter" in prog:
            try:
                matched_eraldised = prog["eraldised_filter"](data) or []
            except Exception:
                matched_eraldised = []
        matched_summary = _eraldised_to_summary(matched_eraldised)
        matched_ha = round(sum(e.get("pindala_ha", 0) for e in matched_summary), 2)

        voor = prog.get("voor", "")
        results.append({
            "nimi": prog["name"],
            "sobib": eligible,
            "summa": prog["amount"],
            "asutus": prog["asutus"],
            "taotlusvoor": voor,
            "voor_status": _voor_status(voor),
            "voor_badge": _voor_badge(voor),
            "url": prog.get("url"),
            "voor_url": prog.get("voor_url"),
            "kirjeldus": prog.get("description"),
            "pohjus": pohjus,
            "category": prog.get("category", ""),
            "eraldised_match": matched_summary,
            "eraldised_match_count": len(matched_summary),
            "eraldised_match_ha": matched_ha,
            "eraldised_filter_label": prog.get("eraldised_filter_label", ""),
            "andmed_piiratud": bool(prog.get("requires_spruce_details") and not data.get("spruce_data_complete", True)),
        })

    # Sort: eligible first (by voor_status: open > upcoming > other), then ineligible
    status_order = {"open": 0, "upcoming": 1, "unknown": 2, "closed": 3}
    results.sort(key=lambda r: (
        0 if r["sobib"] else 1,
        status_order.get(r["voor_status"], 2),
    ))
    return results
