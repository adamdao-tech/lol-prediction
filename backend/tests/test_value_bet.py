import pytest
from app.prediction.value_bet import compute_value_bet


def test_value_bet_positive_edge():
    result = compute_value_bet(model_prob=0.65, decimal_odds=2.0)
    # implied = 0.5, edge = 0.15 → is_value
    assert result["implied_prob"] == 0.5
    assert result["edge"] == pytest.approx(0.15, abs=0.001)
    assert result["is_value"] is True
    assert result["kelly_stake_pct"] > 0


def test_value_bet_no_edge():
    result = compute_value_bet(model_prob=0.45, decimal_odds=2.0)
    # implied = 0.5, edge = -0.05 → not value
    assert result["is_value"] is False
    assert result["kelly_stake_pct"] == 0.0


def test_value_bet_below_threshold():
    result = compute_value_bet(model_prob=0.52, decimal_odds=2.0)
    # edge = 0.02 < 0.04 threshold
    assert result["is_value"] is False


def test_value_bet_kelly_capped():
    # Extrémní edge → kelly capped na 5%
    result = compute_value_bet(model_prob=0.99, decimal_odds=10.0)
    assert result["kelly_stake_pct"] <= 5.0


def test_invalid_odds():
    result = compute_value_bet(model_prob=0.7, decimal_odds=0.5)
    assert result["is_value"] is False
    assert result["kelly_stake_pct"] == 0.0
