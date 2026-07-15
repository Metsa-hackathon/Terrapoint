"""Contracts for auditable 2026 forestry subsidy assessments."""

import unittest
from datetime import date
from unittest.mock import patch

from services import subsidies


def _mk_eraldis(
    nr,
    kood="MA",
    vanus=30,
    pindala=1.0,
    kuivendatud=False,
    invent_kp="2025-01-15",
    registreerimise_kp="2025-01-15",
):
    return {
        "eraldis_nr": nr,
        "puuliik": {"MA": "Mänd", "KU": "Kuusk", "KS": "Kask"}.get(kood, kood),
        "puuliik_kood": kood,
        "vanus": vanus,
        "pindala_ha": pindala,
        "kuivendatud": kuivendatud,
        "sisaldab_kuuske": kood == "KU",
        "kuuse_vanus_max": vanus if kood == "KU" else 0,
        "invent_kp": invent_kp,
        "registreerimise_kp": registreerimise_kp,
    }


def _base_data(**overrides):
    data = {
        "forest_data_complete": True,
        "stand_data_complete": True,
        "protection_data_complete": True,
        "natura_2000": False,
        "kaitseala": False,
        "vaariselupaik": False,
        "mets_pindala": 2.0,
        "mets_pindala_ha": 2.0,
        "mittemetsamaa_ha": 0.0,
        "pindala_ha": 2.0,
        "siht1": "MAATULUNDUSMAA",
        "omvorm": "Eraomand",
        "spruce_data_complete": True,
        "eraldised": [_mk_eraldis(1, vanus=40, pindala=2.0)],
    }
    data.update(overrides)
    return data


def _by_id(results, subsidy_id):
    return next(item for item in results if item["id"] == subsidy_id)


class SubsidyCatalogTests(unittest.TestCase):
    def test_catalog_contains_exact_verified_measure_set(self):
        self.assertEqual(
            {item["id"] for item in subsidies.check_subsidies(_base_data())},
            {
                "looduskaitse-piirangute-huvitis",
                "vep-kaitseleping",
                "kliimakindla-metsa-kujundamine",
                "kliimakindla-metsa-rajamine",
                "metsastamine",
                "uraskikahjustuste-ennetamine",
                "metsameede-monitoring",
                "metsa-inventeerimine",
                "parandkultuuri-sailitamine",
                "maaparandussusteemi-korrastamine",
                "vastutustundliku-metsanduse-edendamine",
                "metsauhistu-toetus",
            },
        )

    def test_catalog_public_periods_and_sources_match_verified_fixture(self):
        expected = {
            "looduskaitse-piirangute-huvitis": ("04.04–30.04.2026", "https://www.eramets.ee/toetused/natura-metsa-toetus/"),
            "vep-kaitseleping": ("Aastaringselt", "https://www.eramets.ee/toetused/vaariselupaiga-kaitseks-lepingu-solmimine/"),
            "kliimakindla-metsa-kujundamine": ("07.04–23.04.2026", "https://www.eramets.ee/metsa-kujundamine/"),
            "kliimakindla-metsa-rajamine": ("I voor 16.06–02.07.2026; II voor 17.11–01.12.2026", "https://www.eramets.ee/toetused/metsa-uuendamise-toetus/"),
            "metsastamine": ("16.04–07.05.2026", "https://www.eramets.ee/metsastamine/"),
            "uraskikahjustuste-ennetamine": ("01.09–15.09.2026", "https://www.eramets.ee/uraskikahjustuste-ennetamine/"),
            "metsameede-monitoring": ("2026. aasta kuupäevad avaldamata", "https://www.eramets.ee/toetused/metsameede/"),
            "metsa-inventeerimine": ("01.12–15.12.2026", "https://www.eramets.ee/toetused/metsa-inventeerimise-toetus/"),
            "parandkultuuri-sailitamine": ("16.06–02.07.2026", "https://www.eramets.ee/toetused/parandkultuuri-sailitamise-toetus/"),
            "maaparandussusteemi-korrastamine": ("2026. aasta kuupäevad avaldamata", "https://www.eramets.ee/toetused/metsamaaparandustoode-toetus/"),
            "vastutustundliku-metsanduse-edendamine": ("03.03–17.03.2026", "https://www.eramets.ee/toetused/uhistutoetus/"),
            "metsauhistu-toetus": ("03.03–17.03.2026", "https://www.eramets.ee/toetused/uhistutoetus/"),
        }

        results = {item["id"]: item for item in subsidies.check_subsidies(_base_data())}
        for subsidy_id, (period, source_url) in expected.items():
            with self.subTest(subsidy_id=subsidy_id):
                self.assertEqual(results[subsidy_id]["application_period"], period)
                self.assertEqual(results[subsidy_id]["source_url"], source_url)

    def test_every_catalog_item_has_stable_id_and_source_metadata(self):
        results = subsidies.check_subsidies(_base_data())

        self.assertEqual(len({item["id"] for item in results}), len(results))
        for item in results:
            self.assertRegex(item["id"], r"^[a-z0-9-]+$")
            self.assertTrue(item["source_name"])
            self.assertTrue(item["source_url"].startswith("https://"))
            self.assertRegex(item["source_as_of"], r"^\d{4}-\d{2}(-\d{2})?$")
            self.assertEqual(item["verified_at"], "2026-07-15")
            self.assertLessEqual(date.fromisoformat(item["source_as_of"]), date.fromisoformat(item["verified_at"]))
            self.assertTrue(item["verification_items"])
            self.assertIn("Lõpliku otsuse", item["disclaimer"])

    def test_secondary_official_urls_are_exact(self):
        results = {item["id"]: item for item in subsidies.check_subsidies(_base_data())}
        expected = {
            "looduskaitse-piirangute-huvitis": (
                "https://www.pria.ee/toetused/natura-2000-erametsades-elurikkuse-soodustamise-toetus-2026",
                "https://www.riigiteataja.ee/akt/122032023015?leiaKehtiv",
            ),
            "metsastamine": (None, "https://www.riigiteataja.ee/akt/124032026004"),
            "metsa-inventeerimine": (None, "https://www.riigiteataja.ee/akt/110032026007"),
        }

        for subsidy_id, (application_url, legal_url) in expected.items():
            with self.subTest(subsidy_id=subsidy_id):
                self.assertEqual(results[subsidy_id]["application_url"], application_url)
                self.assertEqual(results[subsidy_id]["legal_url"], legal_url)
                self.assertEqual(results[subsidy_id]["info_url"], results[subsidy_id]["source_url"])

    def test_stale_or_duplicate_measures_are_not_advertised(self):
        results = subsidies.check_subsidies(_base_data())
        names = {item["name"] for item in results}

        self.assertNotIn("Metssigade küttimise toetus", names)
        self.assertNotIn("Metsakasutuse kitsendustest hüvitis", names)

    def test_inventory_measure_has_verified_rate_period_and_association_scope(self):
        item = _by_id(subsidies.check_subsidies(_base_data()), "metsa-inventeerimine")

        self.assertEqual(
            item["amount"],
            "Kuni 20 €/ha inventeerimine; kuni 25 €/ha inventeerimine koos püsimetsakavaga",
        )
        self.assertEqual(item["application_period"], "01.12–15.12.2026")
        self.assertEqual(item["application_channel"], "Uus e-PRIA, taotlejaks metsaühistu")
        self.assertEqual(item["eligibility_status"], "Vajab kontrolli")

    def test_yearless_or_historical_dates_cannot_become_upcoming(self):
        with patch.object(subsidies, "_today", return_value=date(2026, 7, 13)):
            self.assertEqual(
                subsidies._application_status("Täpsustamisel (2025: 16.09–07.10)"),
                "awaiting_dates",
            )
            self.assertEqual(subsidies._application_status("16.09–07.10"), "awaiting_dates")

    def test_fixed_application_statuses_include_boundaries_and_between_rounds(self):
        one_round = {"type": "fixed", "periods": [{"start": "01.09.2026", "end": "15.09.2026"}]}
        two_rounds = {"type": "fixed", "periods": [
            {"start": "16.06.2026", "end": "02.07.2026"},
            {"start": "17.11.2026", "end": "01.12.2026"},
        ]}

        for today, expected in (
            (date(2026, 8, 31), "upcoming"),
            (date(2026, 9, 1), "open"),
            (date(2026, 9, 15), "open"),
            (date(2026, 9, 16), "closed"),
        ):
            with self.subTest(today=today), patch.object(subsidies, "_today", return_value=today):
                self.assertEqual(subsidies._application_status(one_round), expected)

        with patch.object(subsidies, "_today", return_value=date(2026, 7, 13)):
            self.assertEqual(subsidies._application_status(two_rounds), "upcoming")

    def test_catalog_expires_instead_of_looking_current_in_2027(self):
        with patch.object(subsidies, "_today", return_value=date(2027, 1, 1)):
            results = subsidies.check_subsidies(_base_data(
                eraldised=[_mk_eraldis(7, vanus=20, pindala=1.4)],
                mets_pindala=1.4,
            ))

        self.assertTrue(all(item["eligibility_status"] == "Vajab kontrolli" for item in results))
        self.assertTrue(all(item["application_status"] == "awaiting_dates" for item in results))
        self.assertTrue(all("2026" in item["eligibility_reason"] for item in results))

        with patch.object(subsidies, "_today", return_value=date(2026, 12, 31)):
            final_day = subsidies.check_subsidies(_base_data(
                eraldised=[_mk_eraldis(7, vanus=20, pindala=1.4)],
                mets_pindala=1.4,
            ))
        climate = _by_id(final_day, "kliimakindla-metsa-kujundamine")
        self.assertEqual(climate["eligibility_status"], "Tõenäoliselt sobib")

    def test_year_round_vep_agreement_has_correct_status(self):
        item = _by_id(subsidies.check_subsidies(_base_data()), "vep-kaitseleping")

        self.assertEqual(item["application_status"], "year_round")
        self.assertEqual(item["application_period"], "Aastaringselt")


class SubsidyEligibilityTests(unittest.TestCase):
    def test_state_owned_property_has_no_private_forest_recommendations(self):
        results = subsidies.check_subsidies(_base_data(omvorm="Riigiomand"))

        self.assertFalse(any(item["is_recommended"] for item in results))
        self.assertTrue(all(item["relevance"] in {"not_relevant", "archived"} for item in results))

    def test_existing_forest_is_not_recommended_for_afforestation(self):
        item = _by_id(
            subsidies.check_subsidies(_base_data(mets_pindala_ha=2.0, mittemetsamaa_ha=0.0)),
            "metsastamine",
        )

        self.assertFalse(item["is_recommended"])
        self.assertEqual(item["relevance"], "not_relevant")

    def test_recommendations_exclude_closed_and_association_only_programs(self):
        with patch.object(subsidies, "_today", return_value=date(2026, 7, 15)):
            results = subsidies.check_subsidies(_base_data())

        recommended = [item for item in results if item["is_recommended"]]
        self.assertTrue(recommended)
        self.assertTrue(all(item["application_status"] in {"open", "year_round", "upcoming"} for item in recommended))
        self.assertTrue(all(item["category"] != "ühistu" for item in recommended))

    def test_recommendations_on_2026_07_15_are_exact_for_complete_base_data(self):
        with patch.object(subsidies, "_today", return_value=date(2026, 7, 15)):
            recommended_ids = {
                item["id"] for item in subsidies.check_subsidies(_base_data())
                if item["is_recommended"]
            }

        self.assertEqual(recommended_ids, {"metsa-inventeerimine"})

    def test_positive_property_and_compartment_matches_become_recommendations(self):
        cases = (
            (date(2026, 4, 15), "looduskaitse-piirangute-huvitis", {"natura_2000": True}),
            (date(2026, 7, 15), "vep-kaitseleping", {"vaariselupaik": True, "vep_data_complete": True}),
            (date(2026, 4, 15), "kliimakindla-metsa-kujundamine", {
                "eraldised": [_mk_eraldis(1, vanus=20)],
            }),
            (date(2026, 7, 15), "uraskikahjustuste-ennetamine", {
                "eraldised": [_mk_eraldis(1, kood="KU", vanus=55)],
            }),
            (date(2026, 4, 20), "metsastamine", {
                "pindala_ha": 2.0,
                "mets_pindala_ha": 1.0,
                "mittemetsamaa_ha": 1.0,
            }),
        )

        for today, subsidy_id, overrides in cases:
            with self.subTest(subsidy_id=subsidy_id), patch.object(subsidies, "_today", return_value=today):
                item = _by_id(subsidies.check_subsidies(_base_data(**overrides)), subsidy_id)
                self.assertTrue(item["is_recommended"])
                self.assertIn(item["relevance"], {"matched", "possible"})

    def test_unknown_ownership_cannot_become_a_positive_recommendation(self):
        inventory = _by_id(
            subsidies.check_subsidies(_base_data(omvorm=None)),
            "metsa-inventeerimine",
        )

        self.assertFalse(inventory["is_recommended"])
        self.assertEqual(inventory["relevance"], "insufficient_data")
        self.assertIn("eraomand", inventory["eligibility_reason"].lower())

    def test_inventory_uses_registry_entry_date_not_inventory_date(self):
        stand = _mk_eraldis(1, invent_kp="2023-06-01")
        stand["registreerimise_kp"] = "2026-06-15"

        item = _by_id(
            subsidies.check_subsidies(_base_data(eraldised=[stand])),
            "metsa-inventeerimine",
        )

        self.assertEqual(item["relevance"], "possible")
        self.assertTrue(item["is_recommended"])
        self.assertIn("2026", item["eligibility_reason"])

    def test_inventory_rejects_malformed_registry_entry_date(self):
        stand = _mk_eraldis(1)
        stand["registreerimise_kp"] = "2026-garbage"

        item = _by_id(
            subsidies.check_subsidies(_base_data(eraldised=[stand])),
            "metsa-inventeerimine",
        )

        self.assertFalse(item["is_recommended"])
        self.assertEqual(item["relevance"], "insufficient_data")

    def test_missing_drainage_flag_is_not_treated_as_proof_of_ineligibility(self):
        stand = _mk_eraldis(1, kuivendatud=None)

        item = _by_id(
            subsidies.check_subsidies(_base_data(eraldised=[stand])),
            "maaparandussusteemi-korrastamine",
        )

        self.assertEqual(item["eligibility_status"], "Vajab kontrolli")
        self.assertEqual(item["relevance"], "insufficient_data")
        self.assertTrue(item["andmed_piiratud"])

    def test_protection_measure_uses_overlap_specific_legal_source(self):
        natura = _by_id(
            subsidies.check_subsidies(_base_data(natura_2000=True)),
            "looduskaitse-piirangute-huvitis",
        )
        outside_natura = _by_id(
            subsidies.check_subsidies(_base_data(kaitseala=True)),
            "looduskaitse-piirangute-huvitis",
        )

        self.assertEqual(natura["legal_url"], "https://www.riigiteataja.ee/akt/122032023015?leiaKehtiv")
        self.assertEqual(outside_natura["legal_url"], "https://www.riigiteataja.ee/akt/122032023017?leiaKehtiv")
        self.assertIn("ainult omanik", outside_natura["applicant_scope"].lower())

    def test_incomplete_natura_source_does_not_claim_outside_natura_rules(self):
        item = _by_id(
            subsidies.check_subsidies(_base_data(
                kaitseala=True,
                natura_2000=False,
                natura_data_complete=False,
                protection_data_complete=False,
            )),
            "looduskaitse-piirangute-huvitis",
        )

        self.assertIsNone(item["legal_url"])
        self.assertIsNone(item["application_url"])
        self.assertNotIn("ainult omanik", item["applicant_scope"].lower())

    def test_secondary_spruce_does_not_create_beetle_match(self):
        stand = _mk_eraldis(3, "MA", vanus=55, pindala=1.25)
        stand["sisaldab_kuuske"] = True
        stand["kuuse_vanus_max"] = 55

        item = _by_id(
            subsidies.check_subsidies(_base_data(eraldised=[stand])),
            "uraskikahjustuste-ennetamine",
        )

        self.assertFalse(item["is_recommended"])
        self.assertEqual(item["eraldised_match"], [])

    def test_missing_required_property_data_needs_verification(self):
        data = _base_data(
            forest_data_complete=False,
            stand_data_complete=False,
            mets_pindala=0,
            eraldised=[],
        )

        item = _by_id(subsidies.check_subsidies(data), "kliimakindla-metsa-kujundamine")

        self.assertEqual(item["eligibility_status"], "Vajab kontrolli")
        self.assertIn("puuduvad", item["eligibility_reason"].lower())

    def test_missing_or_malformed_stand_fields_need_verification(self):
        for stand in (
            _mk_eraldis(1, vanus=None, pindala=1.2),
            _mk_eraldis(1, vanus=20, pindala=None),
            _mk_eraldis(1, vanus="vana", pindala=1.2),
        ):
            with self.subTest(stand=stand):
                item = _by_id(
                    subsidies.check_subsidies(_base_data(eraldised=[stand])),
                    "kliimakindla-metsa-kujundamine",
                )
                self.assertEqual(item["eligibility_status"], "Vajab kontrolli")

    def test_known_ineligible_condition_is_explicit(self):
        data = _base_data(
            eraldised=[_mk_eraldis(1, vanus=45, pindala=2.0)],
        )

        item = _by_id(subsidies.check_subsidies(data), "kliimakindla-metsa-kujundamine")

        self.assertEqual(item["eligibility_status"], "Ei sobi teadaolevate andmete põhjal")
        self.assertIn("11–30", item["eligibility_reason"])

    def test_sufficiently_supported_match_is_probable(self):
        data = _base_data(
            eraldised=[_mk_eraldis(7, vanus=20, pindala=1.4)],
            mets_pindala=1.4,
        )

        item = _by_id(subsidies.check_subsidies(data), "kliimakindla-metsa-kujundamine")

        self.assertEqual(item["eligibility_status"], "Tõenäoliselt sobib")
        self.assertEqual(item["eraldised_match_count"], 1)
        self.assertEqual(item["eraldised_match_ha"], 1.4)

    def test_matching_compartment_has_area_and_reason(self):
        data = _base_data(
            has_kuusk=True,
            max_kuusk_vanus=55,
            eraldised=[_mk_eraldis(3, "KU", vanus=55, pindala=1.25)],
        )

        item = _by_id(subsidies.check_subsidies(data), "uraskikahjustuste-ennetamine")
        match = item["eraldised_match"][0]

        self.assertEqual(match["eraldis_nr"], 3)
        self.assertEqual(match["pindala_ha"], 1.25)
        self.assertIn("kuusk", match["match_reason"].lower())
        self.assertIn("55", match["match_reason"])

    def test_property_level_protection_is_not_falsely_assigned_to_compartments(self):
        data = _base_data(
            natura_2000=True,
            eraldised=[_mk_eraldis(1), _mk_eraldis(2)],
        )

        item = _by_id(subsidies.check_subsidies(data), "looduskaitse-piirangute-huvitis")

        self.assertEqual(item["eligibility_status"], "Tõenäoliselt sobib")
        self.assertEqual(item["match_scope"], "property")
        self.assertEqual(item["eraldised_match"], [])
        self.assertIn("ruumiline kattuvus", item["eligibility_reason"].lower())

    def test_known_natura_overlap_remains_probable_when_an_alternative_layer_is_incomplete(self):
        item = _by_id(
            subsidies.check_subsidies(_base_data(natura_2000=True, protection_data_complete=False)),
            "looduskaitse-piirangute-huvitis",
        )

        self.assertEqual(item["eligibility_status"], "Tõenäoliselt sobib")

    def test_incomplete_spruce_details_do_not_become_rejection(self):
        data = _base_data(
            spruce_data_complete=False,
            has_kuusk=False,
            max_kuusk_vanus=0,
            eraldised=[_mk_eraldis(1, "MA", vanus=80)],
        )

        item = _by_id(subsidies.check_subsidies(data), "uraskikahjustuste-ennetamine")

        self.assertEqual(item["eligibility_status"], "Vajab kontrolli")
        self.assertTrue(item["andmed_piiratud"])

    def test_no_mature_spruce_does_not_reject_unknown_storm_damage_path(self):
        item = _by_id(
            subsidies.check_subsidies(_base_data(
                eraldised=[_mk_eraldis(1, "MA", vanus=80)],
                spruce_data_complete=True,
            )),
            "uraskikahjustuste-ennetamine",
        )

        self.assertEqual(item["eligibility_status"], "Vajab kontrolli")
        self.assertIn("tormikahjust", item["eligibility_reason"].lower())

    def test_invalid_beetle_match_area_needs_verification(self):
        for area in (0, -1):
            with self.subTest(area=area):
                item = _by_id(
                    subsidies.check_subsidies(_base_data(
                        eraldised=[_mk_eraldis(1, "KU", vanus=55, pindala=area)],
                    )),
                    "uraskikahjustuste-ennetamine",
                )
                self.assertEqual(item["eligibility_status"], "Vajab kontrolli")

    def test_compartment_matches_sort_numeric_strings_and_skip_missing_identifiers(self):
        data = _base_data(
            eraldised=[
                _mk_eraldis("10", vanus=20, pindala=1),
                _mk_eraldis(None, vanus=20, pindala=1),
                _mk_eraldis("2", vanus=20, pindala=1),
            ],
        )

        item = _by_id(subsidies.check_subsidies(data), "kliimakindla-metsa-kujundamine")

        self.assertEqual([match["eraldis_nr"] for match in item["eraldised_match"]], ["2", "10"])

    def test_all_results_keep_legacy_match_contract(self):
        for item in subsidies.check_subsidies(_base_data()):
            self.assertIn("sobib", item)
            self.assertIn("eraldised_match", item)
            self.assertIn("eraldised_match_count", item)
            self.assertIn("eraldised_match_ha", item)
            self.assertIn("eraldised_filter_label", item)


if __name__ == "__main__":
    unittest.main()
