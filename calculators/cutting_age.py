"""Raievanus (felling age) by species and boniteet.

Allikas: Kliimaministeerium — Uuendusraie arvutus, Tabel 4 (seaduslikud
raievanused). https://kliimaministeerium.ee/media/1034/download

Eesti Metsaseaduse alusel on raievanus suurim kehvema kasvukoha boniteedi
korral — puud kasvavad aeglasemini ja vajavad rohkem aega küpsuse
jõudmiseks. Vana kood invertis selle suuna: väiksem raievanus kehvema
boniteedi puhul, mis soovitas eelaealisi raieid (nt mänd boniteet V koodis
55a, aga seaduse järgi 120a). Võis viia seadusevastaste raiesoovitusteni.

Boniteedi koodid (WFS metsaregister.eraldis.boniteedi_kood):
    0 = 1A  (kõige parem kasvukoht)
    1 = I
    2 = II
    3 = III
    4 = IV
    5 = V   (kõige kehvem)
    6 = Va  (alam-V; kliimaministeeriumi tabelist väljas; kasutan V väärtust)

Kliimaministeeriumi Tabel 4 baseerub Metsaseaduse § 41 lg 2 ja KKM
määrusele. Tabelis puudub eraldi veerg WFS 6 (Va) jaoks — kasutame V
väärtust kui turvaline fallback, et mitte kunagi lubada raie enne
seaduslikku raievanust.

Liikide kaupa Tabel 4 väärtused (vastavalt kliimaministeeriumi dokumendi
veergudele 1A, I, II, III, IV, V):
  - Mänd (MA), Lehis (LH), Seedermänd (SP): okaspuud, pikk eluiga
  - Kuusk (KU): okaspuu, tundlikum pinnasele (stab 60-90a)
  - Kask (KS), Vaher (VA): keskmised lehtpuud
  - Haab (HB), Sanglepp (LM), Hall lepp (LV), Remmelgas (RE): kiired
    kasvajad, lühike raievanus (30-60a)
  - Tamm (TA), Saar (SA), Pöök (PK), Jalakas (JA): kõvad lehtpuud,
    pikk raievanus (90-130a)
"""

# Raievanus (aastat) liigi ja boniteedi koodi (0-6) järgi.
# Suurem boniteedi kood = kehvem kasvukoht = PIKEM seaduslik raievanus
# (vastupidiselt vana koodi, mis vähendas). Allikas: Kliimaministeerium
# uuendusraie dokumendi Tabel 4. WFS kood 6 (Va) = kasutab V väärtust.
CUTTING_AGE = {
    # Okaspuud — Mänd (MA), Lehis (LH), Seedermänd (SP) — pikk eluiga
    "MA": {0: 90,  1: 90,  2: 90,  3: 100, 4: 110, 5: 120, 6: 120},
    "LH": {0: 90,  1: 90,  2: 90,  3: 100, 4: 110, 5: 120, 6: 120},
    "SP": {0: 90,  1: 90,  2: 90,  3: 100, 4: 110, 5: 120, 6: 120},
    # Kuusk (KU) — tundlikum pinnasele
    "KU": {0: 60,  1: 70,  2: 80,  3: 90,  4: 90,  5: 90,  6: 90},
    # Kõvad lehtpuud — Tamm (TA), Saar (SA), Pöök (PK), Jalakas (JA)
    "TA": {0: 90,  1: 90,  2: 100, 3: 110, 4: 120, 5: 130, 6: 130},
    "SA": {0: 90,  1: 90,  2: 100, 3: 110, 4: 120, 5: 130, 6: 130},
    "PK": {0: 90,  1: 90,  2: 100, 3: 110, 4: 120, 5: 130, 6: 130},
    "JA": {0: 90,  1: 90,  2: 100, 3: 110, 4: 120, 5: 130, 6: 130},
    # Keskmised lehtpuud — Kask (KS), Vaher (VA)
    "KS": {0: 60,  1: 60,  2: 70,  3: 70,  4: 70,  5: 70,  6: 70},
    "VA": {0: 60,  1: 60,  2: 70,  3: 70,  4: 70,  5: 70,  6: 70},
    # Kiired lehtpuud — Haab (HB), Sanglepp (LM), Remmelgas (RE)
    "HB": {0: 30,  1: 40,  2: 40,  3: 50,  4: 50,  5: 50,  6: 50},
    "LM": {0: 60,  1: 60,  2: 60,  3: 60,  4: 60,  5: 60,  6: 60},
    "RE": {0: 30,  1: 30,  2: 30,  3: 30,  4: 30,  5: 30,  6: 30},
    # Hall lepp (LV) — kiire kasv, kogu vahemikus 30a
    "LV": {0: 30,  1: 30,  2: 30,  3: 30,  4: 30,  5: 30,  6: 30},
}


def cutting_age_indicator(vanus: int, puuliik_kood: str, boniteedi_kood: int) -> dict:
    """Arvuta raievanus indikaator liigi ja boniteedi põhjal.

    Boniteedi_kood väärtused 0-6 (WFS metsaregister.eraldis):
      0=1A (parim), 1=I, 2=II, 3=III, 4=IV, 5=V (kehveim),
      6=Va (alam-V; kliimaministeeriumi tabelis puudub — kasutan V'd).

    Tagastab:
      - raievanus: seaduslik raievanus antud liigile + boniteedile (a)
      - ratio: vanus / raievanus (1.0 = raievanus saavutatud)
      - status: green/yellow/red
      - label: inimloetav staatus eesti keeles
    """
    species = CUTTING_AGE.get(puuliik_kood, CUTTING_AGE["MA"])
    # Tagavara: kui boniteedi_kood on väljaspool 0-6 (nt None või >6),
    # kasutame keskmist boniteeti III (kood 3) — turvaline vaikeväärtus
    # (mitte 60a väärtus vana koodist).
    if boniteedi_kood not in species:
        boniteedi_kood = 3
    raievanus = species[boniteedi_kood]
    ratio = vanus / raievanus if raievanus else 0
    if ratio < 0.85:
        status, label = "green", "Hooldusraie"
    elif ratio < 1.0:
        status, label = "yellow", "Läheneb raievanusele"
    else:
        status, label = "red", "Raievanus käes"
    return {"status": status, "label": label, "ratio": round(ratio, 2), "raievanus": raievanus}