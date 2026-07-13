import datetime as dt
import unittest

from api import index as api


class ForestDataQualityTests(unittest.TestCase):
    def test_inventory_older_than_five_years_gets_freshness_warning(self):
        summary = api._inventory_summary([
            {
                "invent_kp": "2020-07-12Z",
                "registreerimise_kp": "2021-01-10T09:00:00Z",
                "pindala_ha": 2.5,
            }
        ], today=dt.date(2026, 7, 13))

        self.assertEqual(summary["staatus"], "hoiatus")
        self.assertEqual(summary["inventuuri_vanus_max_a"], 6)
        self.assertEqual(summary["vanem_kui_5a_eraldisi"], 1)
        self.assertEqual(summary["oiguslikult_aegunud_eraldisi"], 0)

    def test_registration_older_than_ten_years_gets_critical_warning(self):
        summary = api._inventory_summary([
            {
                "invent_kp": "2014-06-01Z",
                "registreerimise_kp": "2015-06-30T09:00:00Z",
                "pindala_ha": 4,
            }
        ], today=dt.date(2026, 7, 13))

        self.assertEqual(summary["staatus"], "kriitiline")
        self.assertEqual(summary["vanem_kui_10a_eraldisi"], 1)
        self.assertEqual(summary["oiguslikult_aegunud_eraldisi"], 1)

    def test_historical_clearcut_period_reports_age_without_claiming_exact_year(self):
        periods = api._historical_clearcut_periods([
            {"properties": {"periood_a": 2013, "periood_o": 2015}},
            {"properties": {"periood_a": 2013, "periood_o": 2015}},
            {"properties": {"periood_a": None, "periood_o": 2016}},
        ], today=dt.date(2026, 7, 13))

        self.assertEqual(periods, [
            {"periood_algus": 2013, "periood_lopp": 2015, "vanus_vahemalt_a": 10},
            {"periood_algus": None, "periood_lopp": 2016, "vanus_vahemalt_a": 9},
        ])

    def test_clearcut_compares_only_with_intersecting_stand_inventory(self):
        cut = {
            "geometry": {"type": "Polygon", "coordinates": [[[24.0, 59.0], [24.05, 59.0], [24.05, 59.05], [24.0, 59.0]]]},
            "properties": {"periood_a": 2013, "periood_o": 2015},
        }
        stands = [
            {
                "geometry": {"type": "Polygon", "coordinates": [[[24.0, 59.0], [24.04, 59.0], [24.04, 59.04], [24.0, 59.0]]]},
                "invent_kp": "2012-01-01Z",
            },
            {
                "geometry": {"type": "Polygon", "coordinates": [[[24.06, 59.06], [24.09, 59.06], [24.09, 59.09], [24.06, 59.06]]]},
                "invent_kp": "2020-01-01Z",
            },
        ]

        periods = api._historical_clearcut_periods([cut], stands, today=dt.date(2026, 7, 13))

        self.assertEqual(periods[0]["kattuvaid_eraldisi"], 1)
        self.assertTrue(periods[0]["inventuurist_hilisem"])

    def test_clearcut_touching_only_stand_boundary_does_not_match(self):
        cut = {
            "geometry": {"type": "Polygon", "coordinates": [[[24.0, 59.0], [24.05, 59.0], [24.05, 59.05], [24.0, 59.0]]]},
            "properties": {"periood_a": 2013, "periood_o": 2015},
        }
        touching_stand = {
            "geometry": {"type": "Polygon", "coordinates": [[[24.05, 59.0], [24.08, 59.0], [24.08, 59.05], [24.05, 59.0]]]},
            "invent_kp": "2012-01-01Z",
        }

        periods = api._historical_clearcut_periods([cut], [touching_stand], today=dt.date(2026, 7, 13))

        self.assertEqual(periods[0]["kattuvaid_eraldisi"], 0)
        self.assertFalse(periods[0]["inventuurist_hilisem"])

    def test_notice_is_post_inventory_only_when_approval_is_newer(self):
        self.assertTrue(api._is_after(
            "2024-03-15T10:00:00Z",
            "2020-06-01Z",
        ))
        self.assertFalse(api._is_after(
            "2019-03-15T10:00:00Z",
            "2020-06-01Z",
        ))
        self.assertFalse(api._is_after(None, "2020-06-01Z"))

    def test_missing_inventory_date_is_not_reported_as_fresh(self):
        summary = api._inventory_summary([
            {"invent_kp": None, "registreerimise_kp": None, "pindala_ha": 1}
        ], today=dt.date(2026, 7, 13))

        self.assertEqual(summary["staatus"], "hoiatus")
        self.assertEqual(summary["kuupaev_puudub_eraldisi"], 1)

    def test_five_year_warning_starts_the_day_after_the_anniversary(self):
        on_anniversary = api._inventory_summary([{
            "invent_kp": "2021-07-13Z",
            "registreerimise_kp": "2022-01-01T00:00:00Z",
        }], today=dt.date(2026, 7, 13))
        after_anniversary = api._inventory_summary([{
            "invent_kp": "2021-07-12Z",
            "registreerimise_kp": "2022-01-01T00:00:00Z",
        }], today=dt.date(2026, 7, 13))

        self.assertEqual(on_anniversary["staatus"], "värske")
        self.assertEqual(after_anniversary["staatus"], "hoiatus")
        self.assertEqual(after_anniversary["vanem_kui_5a_eraldisi"], 1)

    def test_ten_year_legal_warning_starts_the_day_after_the_anniversary(self):
        summary = api._inventory_summary([{
            "invent_kp": "2026-01-01Z",
            "registreerimise_kp": "2016-07-12T00:00:00Z",
        }], today=dt.date(2026, 7, 13))

        self.assertEqual(summary["staatus"], "kriitiline")
        self.assertEqual(summary["oiguslikult_aegunud_eraldisi"], 1)

    def test_missing_registration_date_makes_legal_validity_unknown(self):
        summary = api._inventory_summary([{
            "invent_kp": "2026-01-01Z",
            "registreerimise_kp": None,
        }], today=dt.date(2026, 7, 13))

        self.assertEqual(summary["staatus"], "hoiatus")
        self.assertEqual(summary["registrikande_kuupaev_puudub_eraldisi"], 1)

    def test_valid_stand_number_wins_over_coincidental_area_match(self):
        resolved = api._resolve_notice_stand(
            raw_stand=2,
            notice_area=1.0,
            valid_stands={1, 2},
            stands_by_area={1.0: [1], 2.0: [2]},
        )

        self.assertEqual(resolved, 2)

    def test_invalid_stand_number_can_use_unique_area_recovery(self):
        resolved = api._resolve_notice_stand(
            raw_stand=2026,
            notice_area=1.0,
            valid_stands={1, 2},
            stands_by_area={1.0: [1], 2.0: [2]},
        )

        self.assertEqual(resolved, 1)


if __name__ == "__main__":
    unittest.main()
