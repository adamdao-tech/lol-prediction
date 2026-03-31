from __future__ import annotations

# Pro-play champion win rates based on Oracle's Elixir patch 14.x data
PRO_PLAY_CHAMPION_WIN_RATES: dict[str, float] = {
    "aurora": 0.62, "corki": 0.61, "azir": 0.60, "yone": 0.59,
    "vi": 0.58, "leona": 0.58, "nautilus": 0.57, "caitlyn": 0.57,
    "jinx": 0.56, "kalista": 0.56, "ahri": 0.56, "viktor": 0.56,
    "jayce": 0.55, "jax": 0.55, "varus": 0.54, "lucian": 0.54,
    "thresh": 0.54, "renekton": 0.53, "orianna": 0.53, "zeri": 0.53,
    "tristana": 0.53, "lulu": 0.53, "graves": 0.52, "lee sin": 0.52,
    "viego": 0.52, "rakan": 0.52, "taliyah": 0.52, "sejuani": 0.52,
    "maokai": 0.51, "rumble": 0.51, "camille": 0.50, "zed": 0.50,
    "sylas": 0.50, "irelia": 0.50, "yasuo": 0.49, "akali": 0.49,
    "fiora": 0.49, "gangplank": 0.49, "katarina": 0.48, "nidalee": 0.48,
    "leblanc": 0.48, "ryze": 0.47, "kassadin": 0.47, "twisted fate": 0.46,
    "draven": 0.46, "sivir": 0.46,
}

MAJOR_LEAGUE_SLUGS = {"lpl", "lck", "lec", "lcs", "pcs", "vcs", "cblol", "ljl", "worlds", "msi"}

LAYER_WEIGHTS = {
    "weighted_winrate": 0.35,
    "recent_form": 0.20,
    "head_to_head": 0.15,
    "draft_strength": 0.20,
    "tournament_tier": 0.10,
}

MIN_MATCHES_FOR_FULL_CONFIDENCE = 10


def weighted_win_rate(matches: list[dict], team_id: str, decay: float = 0.85) -> float:
    weighted_wins = 0.0
    total_weight = 0.0
    for i, m in enumerate(matches):
        if m.get("status") != "finished":
            continue
        weight = decay ** i
        total_weight += weight
        winner = m.get("winner") or {}
        if str(winner.get("id", "")) == str(team_id):
            weighted_wins += weight
    return weighted_wins / total_weight if total_weight > 0 else 0.5


def recent_form_score(matches: list[dict], team_id: str) -> float:
    finished = [m for m in matches if m.get("status") == "finished"]

    def wr(ms: list[dict]) -> float:
        if not ms:
            return 0.5
        wins = sum(1 for m in ms if str((m.get("winner") or {}).get("id", "")) == str(team_id))
        return wins / len(ms)

    wr_last3 = wr(finished[:3])
    wr_prev = wr(finished[3:10])
    trend = wr_last3 - wr_prev
    return max(0.0, min(1.0, 0.5 + (trend * 0.3)))


def head_to_head_score(h2h_matches: list[dict], team1_id: str, team2_id: str) -> float:
    relevant = []
    for m in h2h_matches:
        if m.get("status") != "finished":
            continue
        opponent_ids = {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
        if str(team1_id) in opponent_ids and str(team2_id) in opponent_ids:
            relevant.append(m)
    if len(relevant) < 2:
        return 0.5
    wins_t1 = sum(1 for m in relevant if str((m.get("winner") or {}).get("id", "")) == str(team1_id))
    return wins_t1 / len(relevant)


def draft_strength_score(blue_picks: list[str], red_picks: list[str], team1_is_blue: bool = True) -> float:
    DEFAULT_WR = 0.50

    def team_score(picks: list[str]) -> float:
        if not picks:
            return DEFAULT_WR
        scores = [PRO_PLAY_CHAMPION_WIN_RATES.get(p.lower(), DEFAULT_WR) for p in picks]
        return sum(scores) / len(scores)

    blue = team_score(blue_picks)
    red = team_score(red_picks)
    total = blue + red
    if total == 0:
        return 0.5
    blue_advantage = blue / total
    return blue_advantage if team1_is_blue else (1.0 - blue_advantage)


def tournament_tier_factor(matches: list[dict], team_id: str) -> float:
    weighted_wins = 0.0
    total_weight = 0.0
    for m in matches:
        if m.get("status") != "finished":
            continue
        slug = ((m.get("league") or {}).get("slug") or "").lower()
        weight = 2.0 if any(s in slug for s in MAJOR_LEAGUE_SLUGS) else 1.0
        total_weight += weight
        if str((m.get("winner") or {}).get("id", "")) == str(team_id):
            weighted_wins += weight
    return weighted_wins / total_weight if total_weight > 0 else 0.5


def compute_full_prediction(
    matches1: list[dict],
    matches2: list[dict],
    h2h_matches: list[dict],
    team1_id: str,
    team2_id: str,
    blue_picks: list[str] | None = None,
    red_picks: list[str] | None = None,
    team1_is_blue: bool = True,
) -> dict:
    wr1 = weighted_win_rate(matches1, team1_id)
    wr2 = weighted_win_rate(matches2, team2_id)
    total_wr = wr1 + wr2
    wr_score = wr1 / total_wr if total_wr > 0 else 0.5

    form1 = recent_form_score(matches1, team1_id)
    form2 = recent_form_score(matches2, team2_id)
    total_form = form1 + form2
    form_score = form1 / total_form if total_form > 0 else 0.5

    h2h_s = head_to_head_score(h2h_matches, team1_id, team2_id)

    if blue_picks is not None and red_picks is not None:
        draft_s = draft_strength_score(blue_picks, red_picks, team1_is_blue)
    else:
        draft_s = 0.5

    tier1 = tournament_tier_factor(matches1, team1_id)
    tier2 = tournament_tier_factor(matches2, team2_id)
    total_tier = tier1 + tier2
    tier_score = tier1 / total_tier if total_tier > 0 else 0.5

    final_prob = (
        LAYER_WEIGHTS["weighted_winrate"] * wr_score
        + LAYER_WEIGHTS["recent_form"] * form_score
        + LAYER_WEIGHTS["head_to_head"] * h2h_s
        + LAYER_WEIGHTS["draft_strength"] * draft_s
        + LAYER_WEIGHTS["tournament_tier"] * tier_score
    )
    final_prob = max(0.05, min(0.95, final_prob))
    win_prob_team2 = 1.0 - final_prob

    n1 = len([m for m in matches1 if m.get("status") == "finished"])
    n2 = len([m for m in matches2 if m.get("status") == "finished"])
    confidence = min(n1, n2) / MIN_MATCHES_FOR_FULL_CONFIDENCE
    confidence_score = min(confidence, 1.0)

    finished1 = [m for m in matches1 if m.get("status") == "finished"]
    finished2 = [m for m in matches2 if m.get("status") == "finished"]

    total_kills1 = []
    total_kills2 = []
    durations1 = []
    durations2 = []
    for m in finished1:
        for game in m.get("games", []):
            d = game.get("length")
            if d:
                durations1.append(d)
            for result in game.get("results", []):
                if str(result.get("team_id", "")) == str(team1_id):
                    k = result.get("kills")
                    if k is not None:
                        total_kills1.append(k)
    for m in finished2:
        for game in m.get("games", []):
            d = game.get("length")
            if d:
                durations2.append(d)
            for result in game.get("results", []):
                if str(result.get("team_id", "")) == str(team2_id):
                    k = result.get("kills")
                    if k is not None:
                        total_kills2.append(k)

    avg_kills1 = sum(total_kills1) / len(total_kills1) if total_kills1 else 15.0
    avg_kills2 = sum(total_kills2) / len(total_kills2) if total_kills2 else 15.0
    avg_dur1 = sum(durations1) / len(durations1) if durations1 else 1800.0
    avg_dur2 = sum(durations2) / len(durations2) if durations2 else 1800.0

    predicted_total_kills = round(avg_kills1 + avg_kills2, 2)
    predicted_duration_seconds = int((avg_dur1 + avg_dur2) / 2)

    features_snapshot = {
        "layer_scores": {
            "weighted_winrate": round(wr_score, 4),
            "recent_form": round(form_score, 4),
            "head_to_head": round(h2h_s, 4),
            "draft_strength": round(draft_s, 4),
            "tournament_tier": round(tier_score, 4),
        },
        "team1": {
            "weighted_wr": round(wr1, 4),
            "form": round(form1, 4),
            "tier": round(tier1, 4),
            "match_count": n1,
        },
        "team2": {
            "weighted_wr": round(wr2, 4),
            "form": round(form2, 4),
            "tier": round(tier2, 4),
            "match_count": n2,
        },
    }

    return {
        "win_prob_team1": round(final_prob, 6),
        "win_prob_team2": round(win_prob_team2, 6),
        "predicted_total_kills": predicted_total_kills,
        "predicted_duration_seconds": predicted_duration_seconds,
        "confidence_score": round(confidence_score, 6),
        "features_snapshot": features_snapshot,
    }
