SUBSIDY_PROGRAMS = [
    # === KIK / Erametsakeskus programs ===
    {
        "name": "Looduskaitseliste piirangute hüvitamine (Natura 2000)",
        "condition": lambda d: d.get("natura_2000"),
        "amount": "60-160 €/ha",
        "asutus": "KIK",
        "voor": "Apr 4–30",
        "url": "https://www.eramets.ee/toetused/natura-metsa-toetus/",
        "description": "Hüvitis looduskaitseliste piirangute tõttu saamata jääva tulu eest Natura 2000 alal",
    },
    {
        "name": "Looduskaitseliste piirangute hüvitamine (väljaspool Natura 2000)",
        "condition": lambda d: d.get("kaitseala") and not d.get("natura_2000"),
        "amount": "kuni 60 €/ha",
        "asutus": "KIK",
        "voor": "Apr 4–30",
        "url": "https://www.eramets.ee/toetused/natura-metsa-toetus/",
        "description": "Hüvitis piirangute tõttu saamata jääva tulu eest kaitsealadel väljaspool Natura 2000",
    },
    {
        "name": "Vääriselupaiga hooldus",
        "condition": lambda d: d.get("vaariselupaik"),
        "amount": "20a leping",
        "asutus": "KIK",
        "voor": "Aastaringselt",
        "url": "https://www.eramets.ee/toetused/vaariselupaiga-kaitseks-lepingu-solmimine/",
        "description": "Vääriselupaiga kaitseks 20-aastase lepingu sõlmimine, hüvitis arvutatakse individuaalselt",
    },

    # === PRIA / Metsameede programs ===
    {
        "name": "Kliimakindla metsa kujundamine",
        "condition": lambda d: 11 <= d.get("keskm_vanus", 0) <= 30 and d.get("mets_pindala", 0) >= 0.1,
        "amount": "356 €/ha",
        "asutus": "PRIA",
        "voor": "Apr 7–23",
        "url": "https://www.eramets.ee/metsa-kujundamine/",
        "description": "Hooldusraie toetus 11-30a metsas, mitmeliigilise ja struktuuririkka metsa kujundamine",
    },
    {
        "name": "Metsastamise toetus",
        "condition": lambda d: d.get("mets_pindala", 0) == 0 and d.get("siht1") != "ELAMUMAA" and d.get("pindala_ha", 0) >= 0.3,
        "amount": "kuni 1420 €/ha",
        "asutus": "PRIA",
        "voor": "Apr 16 – May 7",
        "url": "https://www.eramets.ee/metsastamine/",
        "description": "Uue metsa rajamine, kuni 30 ha omaniku kohta. Sisaldab istutamist ja hooldust",
    },
    {
        "name": "Metsa uuendamise toetus",
        "condition": lambda d: d.get("keskm_vanus", 0) >= d.get("keskm_raievanus", 999) and d.get("mets_pindala", 0) >= 0.1,
        "amount": "kuni 646 €/ha",
        "asutus": "PRIA",
        "voor": "Jun 16 – Jul 2",
        "url": "https://www.eramets.ee/toetused/metsa-uuendamise-toetus/",
        "description": "Metsa uuendamine pärast raievanuse saabumist. Sisaldab mullapinna ettevalmistust, istutamist ja hooldust",
    },
    {
        "name": "Kooreüraski tõrje",
        "condition": lambda d: d.get("has_kuusk") and d.get("max_kuusk_vanus", 0) > 30,
        "amount": "kuni 500 €/ühik",
        "asutus": "PRIA",
        "voor": "Sep 1–15",
        "url": "https://www.eramets.ee/uraskikahjustuste-ennetamine/",
        "description": "Püünispuude kasutamine, feromoonpüüniste paigaldamine, tormikahjustuste likvideerimine",
    },

    # === KIK / Metsainventeerimine ===
    {
        "name": "Metsa inventeerimise toetus",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "amount": "kuni 10 €/ha",
        "asutus": "KIK",
        "voor": "Täpsustamisel",
        "url": "https://www.eramets.ee/toetused/metsa-inventeerimise-toetus/",
        "description": "Metsa inventeerimisandmete koostamise toetus, makstakse üks kord 7 aasta jooksul",
    },

    # === KIK / Maaparandus ===
    {
        "name": "Maaparandussüsteemi korrastamine",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "amount": "kuni 10 000 €",
        "asutus": "KIK",
        "voor": "Täpsustamisel",
        "url": "https://www.eramets.ee/toetused/metsamaaparandustoode-toetus/",
        "description": "Drenaažisüsteemide korrastamine, truupide vahetus, kraavide puhastamine",
    },

    # === KIK / Pärandkultuur ===
    {
        "name": "Pärandkultuuri säilitamine",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "amount": "kuni 2000 €/objekt",
        "asutus": "KIK",
        "voor": "Jun 16 – Jul 2",
        "url": "https://www.eramets.ee/toetused/parandkultuuri-sailitamise-toetus/",
        "description": "Pärandkultuuri objektide taastamine, hooldamine, tähistamine ja avalikuks kasutamiseks kohandamine",
    },

    # === Metsaühistu toetus ===
    {
        "name": "Metsaühistu toetus",
        "condition": lambda d: d.get("mets_pindala", 0) >= 0.1,
        "amount": "kuni 30 000 €",
        "asutus": "PRIA",
        "voor": "Täpsustamisel",
        "url": "https://www.eramets.ee/toetused/uhistutoetus/",
        "description": "Metsaühistute tegevuse toetamine, liikmetele teenuste osutamine",
    },

    # === Metssigade küttimine ===
    {
        "name": "Metssigade küttimise toetus",
        "condition": lambda d: False,  # Only for hunting area holders
        "amount": "65 €/metssiga",
        "asutus": "KIK",
        "voor": "Oct 27–31",
        "url": "https://www.eramets.ee/metssigade-kuttimise-toetus/",
        "description": "Aafrika seakatku tõkestamiseks metssigade küttimise toetus. Ainult jahipiirkonna kasutajatele",
    },
]


def check_subsidies(data: dict) -> list[dict]:
    results = []
    for prog in SUBSIDY_PROGRAMS:
        try:
            eligible = prog["condition"](data)
        except Exception:
            eligible = False
        results.append({
            "nimi": prog["name"],
            "sobib": eligible,
            "summa": prog["amount"],
            "asutus": prog["asutus"],
            "taotlusvoor": prog.get("voor"),
            "url": prog.get("url"),
            "kirjeldus": prog.get("description"),
        })
    return results
