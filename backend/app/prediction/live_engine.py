import math


def compute_live_win_prob(window_frame: dict) -> dict:
    """
    Inputs: single frame from /window/{gameId} response (frames[-1])
    Returns: dict with win_prob_blue, win_prob_red, signals, game_time_seconds
    """
    blue = window_frame.get("blueTeam", {})
    red = window_frame.get("redTeam", {})

    gold_diff = blue.get("totalGold", 0) - red.get("totalGold", 0)
    tower_diff = blue.get("towers", 0) - red.get("towers", 0)
    baron_diff = blue.get("barons", 0) - red.get("barons", 0)
    kill_diff = blue.get("totalKills", 0) - red.get("totalKills", 0)
    dragon_diff = len(blue.get("dragons", [])) - len(red.get("dragons", []))
    inhib_diff = blue.get("inhibitors", 0) - red.get("inhibitors", 0)

    score = (
        gold_diff / 1000 * 0.08
        + tower_diff * 0.06
        + baron_diff * 0.15
        + kill_diff * 0.02
        + dragon_diff * 0.04
        + inhib_diff * 0.20
    )

    prob_blue = 1 / (1 + math.exp(-score))
    prob_blue = max(0.05, min(0.95, prob_blue))

    return {
        "win_prob_blue": round(prob_blue, 4),
        "win_prob_red": round(1.0 - prob_blue, 4),
        "signals": {
            "gold_diff": gold_diff,
            "tower_diff": tower_diff,
            "baron_diff": baron_diff,
            "kill_diff": kill_diff,
            "dragon_diff": dragon_diff,
            "inhibitor_diff": inhib_diff,
        },
        "blue_dragons": blue.get("dragons", []),
        "red_dragons": red.get("dragons", []),
        "blue_total_kills": blue.get("totalKills", 0),
        "red_total_kills": red.get("totalKills", 0),
        "blue_total_gold": blue.get("totalGold", 0),
        "red_total_gold": red.get("totalGold", 0),
    }
