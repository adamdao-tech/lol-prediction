import math


def _format_game_timer(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def compute_live_win_prob(window_frame: dict) -> dict:
    """
    Inputs: single frame from /window/{gameId} response (frames[-1]).
    The frame may be enriched with top-level gameMetadata from the window response.
    Returns: dict with win_prob_blue, win_prob_red, signals, game_timer_seconds, game_timer, etc.
    """
    blue = window_frame.get("blueTeam", {})
    red = window_frame.get("redTeam", {})

    # Extract game length in seconds from enriched frame (gameMetadata injected by caller)
    game_timer_seconds: int = int(
        window_frame.get("gameMetadata", {}).get("gameLength", 0)
        or window_frame.get("gameLength", 0)
        or 0
    )
    game_timer = _format_game_timer(game_timer_seconds)

    gold_diff = blue.get("totalGold", 0) - red.get("totalGold", 0)
    blue_towers = blue.get("towers", 0)
    red_towers = red.get("towers", 0)
    tower_diff = blue_towers - red_towers
    blue_barons = blue.get("barons", 0)
    red_barons = red.get("barons", 0)
    baron_diff = blue_barons - red_barons
    kill_diff = blue.get("totalKills", 0) - red.get("totalKills", 0)
    dragon_diff = len(blue.get("dragons", [])) - len(red.get("dragons", []))
    inhib_diff = blue.get("inhibitors", 0) - red.get("inhibitors", 0)

    # Game-phase-aware weights
    game_minutes = game_timer_seconds / 60
    if game_minutes < 15:
        # Early game: lower gold weight, higher kill weight
        w_gold = 0.05
        w_tower = 0.05
        w_baron = 0.12
        w_kill = 0.04
        w_dragon = 0.04
        w_inhib = 0.18
    elif game_minutes < 25:
        # Mid game: default weights
        w_gold = 0.08
        w_tower = 0.06
        w_baron = 0.15
        w_kill = 0.02
        w_dragon = 0.04
        w_inhib = 0.20
    else:
        # Late game: higher gold and inhib weight
        w_gold = 0.12
        w_tower = 0.07
        w_baron = 0.15
        w_kill = 0.02
        w_dragon = 0.04
        w_inhib = 0.25

    score = (
        gold_diff / 1000 * w_gold
        + tower_diff * w_tower
        + baron_diff * w_baron
        + kill_diff * w_kill
        + dragon_diff * w_dragon
        + inhib_diff * w_inhib
    )

    prob_blue = 1 / (1 + math.exp(-score))
    prob_blue = max(0.05, min(0.95, prob_blue))

    return {
        "win_prob_blue": round(prob_blue, 4),
        "win_prob_red": round(1.0 - prob_blue, 4),
        "game_timer_seconds": game_timer_seconds,
        "game_timer": game_timer,
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
        "blue_towers": blue_towers,
        "red_towers": red_towers,
        "blue_barons": blue_barons,
        "red_barons": red_barons,
    }
