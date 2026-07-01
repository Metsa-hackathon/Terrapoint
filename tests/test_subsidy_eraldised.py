"""Tests for the per-eraldis subsidy matching feature.

Verifies that check_subsidies returns the correct eraldised matches for
each subsidy program based on the input data, including edge cases like
empty eraldised lists, missing fields, and full property-wide subsidies.
"""

import unittest

from services.subsidies import check_subsidies


def _mk_eraldis(nr, kood="MA", vanus=30, pindala=1.0, raievanus=80, kuivendatud=False):
    return {
        "eraldis_nr": nr,
        "puuliik": {"MA": "Mänd", "KU": "Kuusk", "KS": "Kask", "HB": "Haab"}.get(kood, kood),
        "puuliik_kood": kood,
        "vanus": vanus,
        "pindala_ha": pindala,
        "raievanus": raievanus,
        "kuivendatud": kuivendatud,
    }


def _nrs(subsidy):
    """Helper: extract list of eraldis numbers from a subsidy result."""
    return sorted(e["eraldis_nr"] for e in subsidy.get("eraldised_match", []))


class SubsidyEraldisedMatchingTests(unittest.TestCase):
    def test_natura_subsidy_returns_all_eraldised_when_protected(self):
        # Looduskaitseliste piirangute hüvitamine: kaitsealal kõik eraldised sobivad
        data = {
            "kaitseala": True, "natura_2000": False, "mets_pindala": 5.0,
            "eraldised": [_mk_eraldis(1), _mk_eraldis(2, "KU"), _mk_eraldis(3, "KS")],
        }
        result = next(r for r in check_subsidies(data) if "Looduskaitseliste" in r["nimi"])
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [1, 2, 3])
        self.assertEqual(result["eraldised_match_count"], 3)

    def test_natura_subsidy_empty_when_not_protected(self):
        data = {
            "kaitseala": False, "natura_2000": False, "mets_pindala": 5.0,
            "eraldised": [_mk_eraldis(1), _mk_eraldis(2)],
        }
        result = next(r for r in check_subsidies(data) if "Looduskaitseliste" in r["nimi"])
        self.assertFalse(result["sobib"])
        # Isegi kui ei sobi, tuleb match tühi (mitte eraldised)
        self.assertEqual(result["eraldised_match"], [])

    def test_metsameede_filters_by_age_10_to_60(self):
        # Metsameede: eraldised vanusega 10-60
        data = {
            "keskm_vanus": 30, "mets_pindala": 5.0,
            "eraldised": [
                _mk_eraldis(1, vanus=8),     # too young
                _mk_eraldis(2, vanus=25),    # OK
                _mk_eraldis(3, vanus=45),    # OK
                _mk_eraldis(4, vanus=80),    # too old
            ],
        }
        result = next(r for r in check_subsidies(data) if r["nimi"] == "Metsameede")
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [2, 3])
        self.assertAlmostEqual(result["eraldised_match_ha"], 2.0, places=2)

    def test_kliimakindla_metsa_filters_by_age_11_to_30(self):
        # Kliimakindla metsa kujundamine: eraldised vanusega 11-30
        data = {
            "keskm_vanus": 20, "mets_pindala": 5.0,
            "eraldised": [
                _mk_eraldis(1, vanus=10),    # too young
                _mk_eraldis(2, vanus=15),    # OK
                _mk_eraldis(3, vanus=28),    # OK
                _mk_eraldis(4, vanus=45),    # too old
            ],
        }
        result = next(r for r in check_subsidies(data) if "Kliimakindla" in r["nimi"])
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [2, 3])

    def test_kooreyraski_filters_by_kuusk_over_30(self):
        # Kooreüraski tõrje: KU eraldised vanusega > 30
        data = {
            "has_kuusk": True, "max_kuusk_vanus": 45,
            "eraldised": [
                _mk_eraldis(1, "MA", vanus=70),
                _mk_eraldis(2, "KU", vanus=25),   # KU noor
                _mk_eraldis(3, "KU", vanus=45),   # KU vana
                _mk_eraldis(4, "KS", vanus=80),
            ],
        }
        result = next(r for r in check_subsidies(data) if r["nimi"] == "Kooreüraski tõrje")
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [3])

    def test_maaparandus_filters_drained_eraldised(self):
        # Maaparandussüsteemi: ainult kuivendatud eraldised
        data = {
            "mets_pindala": 5.0,
            "eraldised": [
                _mk_eraldis(1, kuivendatud=False),
                _mk_eraldis(2, kuivendatud=True),
                _mk_eraldis(3, kuivendatud=True),
                _mk_eraldis(4, kuivendatud=False),
            ],
        }
        result = next(r for r in check_subsidies(data) if "Maaparandus" in r["nimi"])
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [2, 3])

    def test_metsa_uuendamine_filters_ripe_eraldised(self):
        # Metsa uuendamine: vanus >= raievanus
        data = {
            "keskm_vanus": 80, "keskm_raievanus": 80, "mets_pindala": 5.0,
            "eraldised": [
                _mk_eraldis(1, vanus=60, raievanus=80),  # not ripe
                _mk_eraldis(2, vanus=80, raievanus=80),  # ripe
                _mk_eraldis(3, vanus=100, raievanus=90), # ripe
            ],
        }
        result = next(r for r in check_subsidies(data) if "uuendamis" in r["nimi"].lower())
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [2, 3])

    def test_empty_eraldised_no_matches(self):
        data = {
            "natura_2000": False, "kaitseala": False, "mets_pindala": 0,
            "pindala_ha": 1.0, "siht1": "ELAMUMAA", "keskm_vanus": 0,
            "eraldised": [],
        }
        results = check_subsidies(data)
        # Kõik eligible toetused peaksid saama match_count=0 (kuna eraldisi pole)
        for r in results:
            if r["sobib"]:
                self.assertEqual(r["eraldised_match_count"], 0,
                    f'{r["nimi"]} should have 0 matches but has {r["eraldised_match_count"]}')

    def test_eraldised_with_missing_eraldis_nr_filtered_out(self):
        # Eraldis ilma eraldis_nr-ita ei tohiks matchida
        data = {
            "mets_pindala": 5.0,
            "eraldised": [
                {"eraldis_nr": None, "puuliik_kood": "MA", "vanus": 30, "pindala_ha": 1.0},
                _mk_eraldis(2, vanus=30, pindala=1.0),
            ],
        }
        result = next(r for r in check_subsidies(data) if r["nimi"] == "Metsa inventeerimise toetus")
        self.assertTrue(result["sobib"])
        self.assertEqual(_nrs(result), [2])

    def test_ha_total_is_sum_of_matched_pindala(self):
        data = {
            "kaitseala": True, "natura_2000": False, "mets_pindala": 5.0,
            "eraldised": [
                _mk_eraldis(1, pindala=2.5),
                _mk_eraldis(2, pindala=3.5),
            ],
        }
        result = next(r for r in check_subsidies(data) if "Looduskaitseliste" in r["nimi"])
        self.assertAlmostEqual(result["eraldised_match_ha"], 6.0, places=2)

    def test_all_subsidies_have_eraldised_match_field(self):
        data = {"mets_pindala": 5.0, "eraldised": [_mk_eraldis(1)]}
        results = check_subsidies(data)
        for r in results:
            self.assertIn("eraldised_match", r,
                f'{r["nimi"]} missing eraldised_match field')
            self.assertIn("eraldised_match_count", r)
            self.assertIn("eraldised_match_ha", r)
            self.assertIn("eraldised_filter_label", r)

    def test_filter_label_is_non_empty_for_every_subsidy(self):
        data = {"mets_pindala": 5.0, "eraldised": [_mk_eraldis(1)]}
        results = check_subsidies(data)
        for r in results:
            self.assertTrue(r["eraldised_filter_label"],
                f'{r["nimi"]} has empty eraldised_filter_label')


if __name__ == "__main__":
    unittest.main()
