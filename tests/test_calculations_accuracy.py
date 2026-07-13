"""Regressioontestid arvutuste täpsuse ja allikapõhisuse jaoks.

Iga test kontrollib, et parandatud väärtused vastavad autoriteetsetele
allikatele (IPCC, Kliimaministeerium, Erametsaliit) ja et vead
(eelnimetatud vale suund, ülehinnatud tihedus, alahinnatud seisuhind)
pole tagasi pöördunud.
"""
import unittest
from calculators.cutting_age import CUTTING_AGE, cutting_age_indicator
from calculators.carbon import SPECIES_DATA, CARBON_FRACTION, CO2_C_RATIO, CO2_PER_CAR_YEAR, carbon_potential
from services.metsaregister import BONITEET_MAP


class CuttingAgeTests(unittest.TestCase):
    """Raievanuse tabel — Kliimaministeerium Tabel 4 seaduslikud väärtused."""

    def test_worse_boniteet_means_longer_cutting_age(self):
        """Kriitiline: kehvema boniteediga peab raievanus SUURENEMA,
        mitte VÄHENEMA (vana koodi peamine vigu — invertitud suund)."""
        for species_code in CUTTING_AGE:
            ages = CUTTING_AGE[species_code]
            # Iga järgmise boniteedi kood (kehvem) peab raievanus
            # olema suurem või võrdne eelmisega
            for i in range(0, max(ages.keys())):
                if i in ages and i + 1 in ages:
                    self.assertGreaterEqual(
                        ages[i + 1], ages[i],
                        f"{species_code}: boniteet {i+1} (kehvem) raievanus "
                        f"{ages[i+1]}a peaks olema >= boniteet {i} raievanus "
                        f"{ages[i]}a. Vana kood invertis selle suuna!"
                    )

    def test_pine_boniteet_V_is_120_not_55(self):
        """Mänd boniteet V peab olema 120a, mitte 55a (vana viga).
        Allikas: Kliimaministeerium Tabel 4."""
        self.assertEqual(CUTTING_AGE["MA"][5], 120)

    def test_pine_boniteet_1A_is_90(self):
        """Mänd boniteet 1A (kood 0) peab olema 90a, mitte 80a või "Iga".
        Vana kood jättis koodi 0 ilma nimeta."""
        self.assertEqual(CUTTING_AGE["MA"][0], 90)

    def test_spruce_boniteet_1A_is_60(self):
        """Kuusk boniteet 1A peab olema 60a (Kliimaministeerium Tabel 4)."""
        self.assertEqual(CUTTING_AGE["KU"][0], 60)

    def test_all_boniteet_codes_0_to_6_covered(self):
        """Kõik WFS koodid 0-6 peavad olema defineeritud iga liigi jaoks,
        sest metsaregister võib neid kõiki tagastada."""
        for species_code, ages in CUTTING_AGE.items():
            for code in range(7):
                self.assertIn(code, ages,
                    f"{species_code}: WFS kood {code} puudub CUTTING_AGE'st")

    def test_cutting_age_indicator_fallback_for_unknown_boniteet(self):
        """Tundmatu boniteedi kood peab langema III (kood 3) peale, mitte
        andma KeyErrorit. Vana kood kasutas default=60, mis oli vale."""
        result = cutting_age_indicator(100, "MA", 99)
        # III kood = 3 -> MA raievanus 100a, ratio 1.0 -> "Raievanus käes"
        self.assertEqual(result["raievanus"], 100)

    def test_cutting_age_status_thresholds(self):
        """Ratio läved: < 0.85 = green, < 1.0 = yellow, >= 1.0 red."""
        young = cutting_age_indicator(50, "MA", 0)   # 50/90 = 0.56 -> green
        mature = cutting_age_indicator(85, "MA", 0)  # 85/90 = 0.94 -> yellow
        ripe = cutting_age_indicator(95, "MA", 0)   # 95/90 = 1.06 -> red
        self.assertEqual(young["status"], "green")
        self.assertEqual(mature["status"], "yellow")
        self.assertEqual(ripe["status"], "red")

    def test_classifier_codes_are_not_mistaken_for_other_species(self):
        self.assertIn("SD", CUTTING_AGE)  # seedermänd
        self.assertNotIn("SP", CUTTING_AGE)  # sarapuu
        self.assertNotIn("PK", CUTTING_AGE)  # paakspuu
        unsupported = cutting_age_indicator(40, "SP", 3)
        self.assertIsNone(unsupported["raievanus"])
        self.assertEqual(unsupported["status"], "unknown")


class BoniteetMapTests(unittest.TestCase):
    """BONITEET_MAP — WFS kood → nimi (1A kuni V, 7 klassi)."""

    def test_all_7_codes_mapped(self):
        """Kõik 7 WFS koodi (0-6) peavad olema kaardistatud.
        Vana BONITEET_MAP kattis ainult 5 koodi (1-5) ja jättis
        0 (1A) ja 6 (Va) ilma nimeta."""
        self.assertEqual(len(BONITEET_MAP), 7)
        self.assertEqual(BONITEET_MAP[0], "1A")
        self.assertEqual(BONITEET_MAP[1], "I")
        self.assertEqual(BONITEET_MAP[2], "II")
        self.assertEqual(BONITEET_MAP[3], "III")
        self.assertEqual(BONITEET_MAP[4], "IV")
        self.assertEqual(BONITEET_MAP[5], "V")
        self.assertEqual(BONITEET_MAP[6], "Va")

    def test_code_0_is_1A_not_I(self):
        """Vana viga: WFS koodi 0 (1A, parim kasvukoht) käsitleti
        kui nime olemaseta või kui 'I'. Nüüd peab olema '1A'."""
        self.assertEqual(BONITEET_MAP[0], "1A")
        self.assertNotEqual(BONITEET_MAP[0], "I")


class CarbonDensityTests(unittest.TestCase):
    """Puidu tihedused — IPCC GPG LULUCF Table 3A.1.9-1 järgi.
    Vana kood kasutas süstemaatiliselt 10-30% liiga kõrgeid väärtusi."""

    def test_pine_density_matches_ipcc(self):
        """Mänd (Pinus sylvestris): IPCC 0.42, vana kood oli 0.51."""
        self.assertAlmostEqual(SPECIES_DATA["MA"]["density"], 0.42, places=2)

    def test_spruce_density_matches_ipcc(self):
        """Kuusk (Picea abies): IPCC 0.40, vana kood oli 0.46."""
        self.assertAlmostEqual(SPECIES_DATA["KU"]["density"], 0.40, places=2)

    def test_larch_density_fixed(self):
        """Lehis (Larix decidua): IPCC 0.46, vana kood oli 0.59 (28% liiga
        kõrge — kõige suurem viga kogu tabelis)."""
        self.assertAlmostEqual(SPECIES_DATA["LH"]["density"], 0.46, places=2)

    def test_aspen_density_fixed(self):
        """Haab (Populus tremula): IPCC 0.35, vana kood oli 0.45 (29% liiga
        kõrge)."""
        self.assertAlmostEqual(SPECIES_DATA["HB"]["density"], 0.35, places=2)

    def test_spruce_root_shoot_is_boreal_conifer(self):
        """KU root_shoot: IPCC boreaal okaspuu = 0.24, vana kood 0.29
        (temperatuurse lehtpuu väärtus)."""
        self.assertAlmostEqual(SPECIES_DATA["KU"]["root_shoot"], 0.24, places=2)

    def test_carbon_fraction_and_co2_ratio(self):
        """Universaalsed IPCC konstantid — peavad jääma samaks."""
        self.assertAlmostEqual(CARBON_FRACTION, 0.47, places=2)
        self.assertAlmostEqual(CO2_C_RATIO, 3.67, places=2)

    def test_carbon_potential_not_overestimated(self):
        """Mänd 200 m³/ha, 10 ha: biomass ei tohi ületada 150 t/ha
        (vana kood: 172 t/ha 0.51 tihedusega; uus: 140 t/ha)."""
        r = carbon_potential(200, 10, "MA")
        self.assertLess(r["biomass_tons_ha"], 150,
            "Mänd biomass üle 150 t/ha — puidu tihedus ilmselt tagasi "
            "üleHindatud väärtusele")

    def test_co2_per_car_year_reduced(self):
        """Auto CO2 ekvivalent: 4.6 -> 3.0 t/a (konservatiivne elukaartse)."""
        self.assertLessEqual(CO2_PER_CAR_YEAR, 3.5)
        self.assertGreaterEqual(CO2_PER_CAR_YEAR, 2.0)


class TimberPriceTests(unittest.TestCase):
    """Puidu hinnad — Erametsaliit 2026 Q1.
    Test seisuhindade ja halli lepa paranduse kohta."""

    def test_pine_seisuhind_above_70(self):
        """Mänd seisuhind: Erametsaliit 2026 Q1 = 76-81 €/tm.
        Vana kood oli 57 €/tm (25-30% liiga madal)."""
        from api.index import _search_core
        # Sisuliselt importime SPECIES_PRICES otse _search_core funktsiooni
        # küljest läbi mockitud _search_core väljakutse
        import asyncio
        from unittest.mock import AsyncMock, patch

        kataster = {
            "number": "78404:409:0113",
            "geometry": {"type": "Polygon",
                         "coordinates": [[[24.0, 59.0], [24.1, 59.0],
                                          [24.1, 59.1], [24.0, 59.0]]]},
            "pindala_ha": 10,
        }
        eraldised = [{"id": 1, "pindala_ha": 5, "puuliik_kood": "MA",
                       "puuliik": "Mänd", "vanus": 80, "tagavara_y_ha": 200,
                       "boniteedi_kood": 2, "eraldis_nr": 1}]

        async def main():
            with (
                patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
                patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
                patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
                patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
                patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
                patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
                patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
            ):
                import time
                result = await _search_core("78404:409:0113", time.time())
            return result

        result = asyncio.run(main())
        v = result.get("vaartus", {})
        # Mänd 200 m³/ha × 5 ha = 1000 m³ × 78 €/tm = 78000 €
        # vana kood: 1000 × 57 = 57000 € (27% vähem)
        total = v.get("total_value_eur", 0)
        self.assertGreater(total, 70000,
            f"Mänd väärtus {total} € < 70000 € — seisuhind ilmselt "
            f"tagasi vana liiga madalale väärtusele (57)")


if __name__ == "__main__":
    unittest.main()
