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

    def test_neutral_age_class_boundaries_are_additive(self):
        expected = {
            49: ("young", "Noor"),
            50: ("middle_aged", "Keskealine"),
            84: ("middle_aged", "Keskealine"),
            85: ("maturing", "Valmiv"),
            99: ("maturing", "Valmiv"),
            100: ("cutting_age_reached", "Raievanus saavutatud"),
        }

        for age, (class_id, label) in expected.items():
            with self.subTest(age=age):
                result = cutting_age_indicator(age, "MA", 3)
                self.assertEqual(result["age_class"], class_id)
                self.assertEqual(result["age_class_label"], label)
                self.assertRegex(result["age_class_color"], r"^#[0-9a-fA-F]{6}$")
                self.assertEqual(result["age_class_provenance"], "Terrapointi tuletis")
                self.assertIn("status", result)
                self.assertIn("label", result)
                self.assertIn("ratio", result)
                self.assertIn("raievanus", result)

    def test_neutral_age_class_is_unknown_when_age_or_cutting_age_is_unknown(self):
        for age, species in ((None, "MA"), (40, "SP")):
            with self.subTest(age=age, species=species):
                result = cutting_age_indicator(age, species, 3)
                self.assertEqual(result["age_class"], "unknown")
                self.assertEqual(result["age_class_label"], "Määramata")
                self.assertEqual(result["age_class_provenance"], "Terrapointi tuletis")

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

    def test_pine_unknown_assortment_uses_firewood_to_sawlog_scenarios(self):
        """Männi sortimendita keskpunkt ei käsitle kogu mahtu palgina.
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
                       "boniteedi_kood": 2, "eraldis_nr": 1,
                       "kuivendatud": True}]

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
        # Ilma sortimendiandmeteta ulatub stsenaarium küttepuidust palgini;
        # keskne komponendireferents on nende piiride keskpunkt, mitte turuhind.
        self.assertEqual(v["total_value_eur"], 45850)
        self.assertEqual(v["base_value_eur"], 45850)
        self.assertLess(v["range_low_eur"], v["base_value_eur"])
        self.assertGreater(v["range_high_eur"], v["base_value_eur"])
        self.assertEqual(v["price_per_m3"], 45.85)
        self.assertEqual(v["base_price_per_m3"], 45.85)
        self.assertEqual(v["methodology"], "Terrapoint unknown-assortment range v3")
        self.assertEqual(v["price_updated"], "2026-Q1")
        self.assertEqual(v["price_as_of"], "2026-03")
        self.assertEqual(v["market_context_updated"], "2026-06")
        self.assertTrue(v["sources"])
        self.assertFalse(v["property_estimate"]["has_transaction_comparables"])
        self.assertFalse(v["property_estimate"]["land_reference_available"])
        self.assertIsNone(v["maa_turuhind"])
        self.assertIsNone(v["kinnistu_turuväärtus"])
        self.assertTrue(v["legacy_market_value_fields_deprecated"])
        self.assertEqual(v["range_low_eur"], 10600)
        self.assertEqual(v["range_high_eur"], 81100)

    def test_each_stand_uses_its_own_species_elements(self):
        from api.index import _search_core
        import asyncio
        from unittest.mock import AsyncMock, patch

        geometry = {"type": "Polygon", "coordinates": [[[24, 59], [24.1, 59], [24.1, 59.1], [24, 59]]]}
        kataster = {"number": "78404:409:0113", "geometry": geometry, "pindala_ha": 2, "maks_hind": 10_000}
        stands = [
            {"id": 1, "pindala_ha": 1, "puuliik_kood": "MA", "puuliik": "mänd", "vanus": 60, "tagavara_y_ha": 100, "boniteedi_kood": 2, "eraldis_nr": 1},
            {"id": 2, "pindala_ha": 1, "puuliik_kood": "LV", "puuliik": "hall lepp", "vanus": 40, "tagavara_y_ha": 100, "boniteedi_kood": 2, "eraldis_nr": 2},
        ]
        elements = [
            [{"puuliik_kood": "MA", "tagavara_y_ha": 100, "vanus": 60}],
            [{"puuliik_kood": "LV", "tagavara_y_ha": 100, "vanus": 40}],
        ]

        async def main():
            with (
                patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
                patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
                patch("api.index.query_eraldis_element", new=AsyncMock(side_effect=elements)),
                patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
                patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
                patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
                patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
            ):
                return await _search_core("78404:409:0113", 0)

        result = asyncio.run(main())
        values = result["mets"]["eraldised"]
        self.assertEqual(values[0]["vaartus_hinnang_eur"], 4585)
        self.assertEqual(values[1]["vaartus_hinnang_eur"], 1710)
        self.assertEqual(result["vaartus"]["base_value_eur"], 6295)


if __name__ == "__main__":
    unittest.main()
