"""
Value bet detection: porovnání predikce modelu s bookmaker odds.

Edge formula:
  edge = model_prob - implied_prob
  implied_prob = 1 / decimal_odds  (bez vig korekce — jednoduché)

Kelly criterion (fractional Kelly = 25%):
  kelly_fraction = edge / (decimal_odds - 1) * 0.25
  capped na max 5%

Value bet je detekován, pokud edge > MIN_EDGE_THRESHOLD (default 0.04 = 4%)
"""
from __future__ import annotations

MIN_EDGE_THRESHOLD = 0.04  # 4% minimální edge


def compute_value_bet(
    model_prob: float,
    decimal_odds: float,
    kelly_fraction: float = 0.25,
) -> dict:
    """
    Vrátí dict s detaily value bet analýzy.

    Args:
        model_prob: pravděpodobnost výhry z modelu (0–1)
        decimal_odds: kurz od bookmakera (např. 1.85)
        kelly_fraction: fractional Kelly koeficient (default 0.25 = quarter Kelly)

    Returns:
        {
          "implied_prob": float,
          "edge": float,
          "is_value": bool,
          "kelly_stake_pct": float,  # doporučená sázka v % bankrollu
          "expected_value": float,   # EV na 1 jednotku sázky
        }
    """
    if decimal_odds <= 1.0:
        return {
            "implied_prob": 1.0,
            "edge": 0.0,
            "is_value": False,
            "kelly_stake_pct": 0.0,
            "expected_value": 0.0,
        }

    implied_prob = 1.0 / decimal_odds
    edge = model_prob - implied_prob
    is_value = edge > MIN_EDGE_THRESHOLD

    # Kelly criterion
    if decimal_odds > 1.0 and is_value:
        raw_kelly = edge / (decimal_odds - 1.0)
        kelly_stake_pct = min(raw_kelly * kelly_fraction * 100, 5.0)  # max 5%
    else:
        kelly_stake_pct = 0.0

    # Expected value na jednotku sázky (profit/loss)
    expected_value = model_prob * (decimal_odds - 1.0) - (1.0 - model_prob)

    return {
        "implied_prob": round(implied_prob, 4),
        "edge": round(edge, 4),
        "is_value": is_value,
        "kelly_stake_pct": round(kelly_stake_pct, 2),
        "expected_value": round(expected_value, 4),
    }
