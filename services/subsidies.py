SUBSIDY_PROGRAMS = [
    {"name": "Natura 2000 metsatoetus", "condition": lambda d: d.get("natura_2000"), "amount": "60-160 €/ha", "asutus": "KIK", "voor": "Apr 4–30"},
    {"name": "Kliimakindla metsa kujundamine", "condition": lambda d: 11 <= d.get("keskm_vanus", 0) <= 30, "amount": "356 €/ha", "asutus": "PRIA", "voor": "Apr 7–23"},
    {"name": "Kooreüraski tõrje", "condition": lambda d: d.get("peapuuliik_kood") == "KU" and d.get("keskm_vanus", 0) > 30, "amount": "500 €/ühik", "asutus": "PRIA", "voor": "Sep 1–15"},
    {"name": "Metsastamise toetus", "condition": lambda d: d.get("mets_pindala", 0) == 0 and d.get("siht1") != "ELAMUMAA", "amount": "1420 €/ha", "asutus": "PRIA", "voor": "Apr 16 – May 7"},
    {"name": "Vääriselupaiga hooldus", "condition": lambda d: d.get("vaariselupaik"), "amount": "20a leping", "asutus": "KIK"},
    {"name": "Metsa uuendamise toetus", "condition": lambda d: d.get("keskm_vanus", 0) >= d.get("keskm_raievanus", 999), "amount": "kuni 1500 €/ha", "asutus": "PRIA", "voor": "Jun 16 – Jul 2"},
    {"name": "Metsa hooldamise toetus", "condition": lambda d: 10 <= d.get("keskm_vanus", 0) <= 60, "amount": "kuni 200 €/ha", "asutus": "PRIA"},
    {"name": "Looduskaitse erametsas", "condition": lambda d: d.get("kaitseala"), "amount": "kuni 200 €/ha", "asutus": "KIK"},
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
        })
    return results
