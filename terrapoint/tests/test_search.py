import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculators.timber import timber_value
from calculators.carbon import carbon_potential
from calculators.cutting_age import cutting_age_indicator
from calculators.beetle_risk import beetle_risk
from calculators.health_index import health_index


def test_timber_value():
    result = timber_value(245.0, 12.5, "KU")
    assert result["tagavara_m3"] == 3062.5
    assert result["log_price"] == 109.54
    assert result["pulp_price"] == 53.00
    assert result["price_per_m3"] > 0
    assert result["total_value_eur"] > 0


def test_carbon_potential():
    result = carbon_potential(245.0, 12.5, "KU")
    assert result["co2_tons_ha"] > 200  # Should be ~259
    assert result["co2_tons_total"] > 0
    assert result["potential_income_eur"] > 0


def test_cutting_age_green():
    result = cutting_age_indicator(50, "KU", 2, 80)
    assert result["status"] == "green"


def test_cutting_age_yellow():
    result = cutting_age_indicator(70, "KU", 2, 80)
    assert result["status"] == "yellow"


def test_cutting_age_red():
    result = cutting_age_indicator(85, "KU", 2, 80)
    assert result["status"] == "red"


def test_beetle_risk_not_spruce():
    result = beetle_risk("MA", 70)
    assert result["score"] == 0


def test_beetle_risk_young_spruce():
    result = beetle_risk("KU", 30)
    assert result["score"] == 0


def test_beetle_risk_old_spruce():
    result = beetle_risk("KU", 90, kuivendatud=True, taius_1=0.8)
    assert result["score"] >= 2


def test_beetle_risk_official_zone():
    result = beetle_risk("KU", 50, official_zone=True)
    assert result["score"] == 3
    assert result["official_zone"] is True


def test_health_index_good():
    result = health_index(1, True, "1", 0)
    assert result["score"] >= 70
    assert result["label"] == "Hea"


def test_health_index_bad():
    result = health_index(5, False, "3", 3)
    assert result["score"] < 40
    assert result["label"] == "Halb"


if __name__ == "__main__":
    test_timber_value()
    test_carbon_potential()
    test_cutting_age_green()
    test_cutting_age_yellow()
    test_cutting_age_red()
    test_beetle_risk_not_spruce()
    test_beetle_risk_young_spruce()
    test_beetle_risk_old_spruce()
    test_beetle_risk_official_zone()
    test_health_index_good()
    test_health_index_bad()
    print("All tests passed!")
