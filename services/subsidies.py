SUBSIDY_PROGRAMS = [
    # === KIK / Erametsakeskus programs ===
    {
        "name": "Looduskaitse toetus",
        "condition": lambda d: d.get("kaitseala") or d.get("natura_2000"),
        "reject_reason": lambda d: "Krundil puuduvad looduskaitselised piirangud (Natura 2000 või kaitseala)" if not d.get("kaitseala") and not d.get("natura_2000") else None,
        "amount": "60-160 €/ha",
        "asutus": "KIK",
        "voor": "Apr 4–30",
        "url": "https://www.eramets.ee/toetused/natura-metsa-toetus/",
        "description": "Looduskaitseliste piirangute hüvitamine Natura 2000 ja kaitsealadel. 160 €/ha metsaelupaigaga tsoonis.",
    },
    {
        "name": "Vääriselupaiga hooldus",
        "condition": lambda d: d.get("vaariselupaik"),
        "reject_reason": lambda d: "Vääriselupaika ei tuvastatud" if not d.get("vaariselupaik") else None,
        "amount": "20a leping",
        "asutus": "KIK",
        "voor": "Aastaringselt",
        "url": "https://www.eramets.ee/toetused/vaariselupaiga-kaitseks-lepingu-solmimine/",
        "description": "Vääriselupaiga kaitseks 20-aastase lepingu sõlmimine, hüvitis arvutatakse individuaalselt",
    },

    # === PRIA / Metsameede programs ===
    {
        "name": "Metsa hooldamise toetus",
        "condition": lambda d: 10 <= d.get("keskm_vanus", 0) <= 60 and d.get("mets_pindala", 0) >= 0.1,
        "amount": "kuni 200 €/ha",
        "asutus": "PRIA",
        "voor": "Metsameede",
        "url": "https://www.eramets.ee/toetused/metsameede/",
        "description": "Hooldusraie ja harvendusraie toetus 10-60a metsas",
        "reject_reason": "Metsa vanus peab olema 10-60 aastat",
    },
    {
        "name": "Kliimakindla metsa kujundamine",
        "condition": lambda d: 11 <= d.get("keskm_vanus", 0) <= 30 and d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: "Metsa vanus peab olema 11-30 aastat (praegu " + str(d.get("keskm_vanus", 0)) + "a)" if not (11 <= d.get("keskm_vanus", 0) <= 30) else "Metsa pindala peab olema vähemalt 0.1 ha" if d.get("mets_pindala", 0) < 0.1 else None,
        "amount": "356 €/ha",
        "asutus": "PRIA",
        "voor": "Apr 7–23",
        "url": "https://www.eramets.ee/metsa-kujundamine/",
        "description": "Hooldusraie toetus 11-30a metsas, mitmeliigilise ja struktuuririkka metsa kujundamine",
    },
    {
        "name": "Metsastamise toetus",
        "condition": lambda d: d.get("mets_pindala", 0) == 0 and d.get("siht1") != "ELAMUMAA" and d.get("pindala_ha", 0) >= 0.3,
        "reject_reason": lambda d: "Krundil on juba metsa" if d.get("mets_pindala", 0) > 0 else "Krunt on elamumaa" if d.get("siht1") == "ELAMUMAA" else "Krundi pindala peab olema vähemalt 0.3 ha" if d.get("pindala_ha", 0) < 0.3 else None,
        "amount": "kuni 1420 €/ha",
        "asutus": "PRIA",
        "voor": "Apr 16 – May 7",
        "url": "https://www.eramets.ee/metsastamine/",
        "description": "Uue metsa rajamine, kuni 30 ha omaniku kohta. Sisaldab istutamist ja hooldust",
    },
    {
        "name": "Metsa uuendamise toetus",
        "condition": lambda d: d.get("keskm_vanus", 0) >= d.get("keskm_raievanus", 999) and d.get("mets_pindala", 0) >= 0.1,
        "reject_reason": lambda d: "Mets ei ole veel raievanuses (vanus " + str(d.get("keskm_vanus", 0)) + "a, raievanus " + str(d.get("keskm_raievanus", "?")) + "a)" if d.get("keskm_vanus", 0) < d.get("keskm_raievanus", 999) else "Metsa pindala peab olema vähemalt 0.1 ha" if d.get("mets_pindala", 0) < 0.1 else None,
        "amount": "kuni 646 €/ha",
        "asutus": "PRIA",
        "voor": "Jun 16 – Jul 2",
        "url": "https://www.eramets.ee/toetused/metsa-uuendamise-toetus/",
        "description": "Metsa uuendamine pärast raievanuse saabumist. Sisaldab mullapinna ettevalmistust, istutamist ja hooldust",
    },
    {
        "name": "Kooreüraski tõrje",
        "condition": lambda d: d.get("has_kuusk") and d.get("max_kuusk_vanus", 0) > 30,
        "reject_reason": lambda d: "Krundil ei ole üle 30a kuuski" if not d.get("has_kuusk") or d.get("max_kuusk_vanus", 0) <= 30 else None,
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
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0.1 ha" if d.get("mets_pindala", 0) < 0.1 else None,
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
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0.1 ha" if d.get("mets_pindala", 0) < 0.1 else None,
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
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0.1 ha" if d.get("mets_pindala", 0) < 0.1 else None,
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
        "reject_reason": lambda d: "Metsa pindala peab olema vähemalt 0.1 ha" if d.get("mets_pindala", 0) < 0.1 else None,
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
        "reject_reason": lambda d: "Ainult jahipiirkonna kasutusõigust omavatele isikutele",
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
        pohjus = None
        if not eligible and "reject_reason" in prog:
            try:
                pohjus = prog["reject_reason"](data)
            except Exception:
                pohjus = None
        results.append({
            "nimi": prog["name"],
            "sobib": eligible,
            "summa": prog["amount"],
            "asutus": prog["asutus"],
            "taotlusvoor": prog.get("voor"),
            "url": prog.get("url"),
            "kirjeldus": prog.get("description"),
            "pohjus": pohjus,
        })
    return results
