# Pro-play champion win rates (patch 14.x, based on Oracle's Elixir pro-play data)
# Format: "champion_name_lowercase": win_rate (0.0-1.0)
PRO_PLAY_CHAMPION_WIN_RATES: dict[str, float] = {
    # S-tier
    "aurora": 0.62, "corki": 0.61, "azir": 0.60, "yone": 0.59,
    "vi": 0.58, "leona": 0.58, "nautilus": 0.57, "caitlyn": 0.57,
    "jinx": 0.56, "kalista": 0.56, "ahri": 0.56, "viktor": 0.56,
    # A-tier
    "jayce": 0.55, "jax": 0.55, "varus": 0.54, "lucian": 0.54,
    "thresh": 0.54, "renekton": 0.53, "orianna": 0.53, "zeri": 0.53,
    "garen": 0.53, "tristana": 0.53, "lulu": 0.53, "graves": 0.52,
    "lee sin": 0.52, "viego": 0.52, "rakan": 0.52, "xayah": 0.52,
    "taliyah": 0.52, "sejuani": 0.52, "maokai": 0.51, "rumble": 0.51,
    # B-tier (neutral ~0.50)
    "camille": 0.50, "zed": 0.50, "sylas": 0.50, "irelia": 0.50,
    "yasuo": 0.49, "akali": 0.49, "fiora": 0.49, "gangplank": 0.49,
    "katarina": 0.48, "nidalee": 0.48, "leblanc": 0.48,
    # C-tier
    "ryze": 0.47, "kassadin": 0.47, "twisted fate": 0.46,
    "draven": 0.46, "sivir": 0.46,
}

MAJOR_LEAGUE_SLUGS = {
    "lpl", "lck", "lec", "lcs", "pcs", "vcs", "cblol", "ljl",
    "worlds", "msi", "lol-esports-world-championship",
}


def weighted_win_rate(matches: list[dict], team_id: str, decay: float = 0.85) -> float:
    """Layer 1: Exponentially weighted win rate from recent matches."""
    weighted_wins = 0.0
    total_weight = 0.0
    for i, m in enumerate(matches):  # matches sorted newest-first
        if m.get("status") != "finished":
            continue
        weight = decay ** i
        total_weight += weight
        winner = m.get("winner") or {}
        if str(winner.get("id", "")) == str(team_id):
            weighted_wins += weight
    if total_weight == 0:
        return 0.5
    return weighted_wins / total_weight


def recent_form_score(matches: list[dict], team_id: str) -> float:
    """Layer 2: Compare last-3 win rate vs matches 4-10 to detect momentum."""
    finished = [m for m in matches if m.get("status") == "finished"]

    def wr(ms: list[dict]) -> float:
        if not ms:
            return 0.5
        wins = sum(
            1 for m in ms
            if str((m.get("winner") or {}).get("id", "")) == str(team_id)
        )
        return wins / len(ms)

    last3 = finished[:3]
    prev = finished[3:10]

    wr_last3 = wr(last3)
    wr_prev = wr(prev)

    trend = wr_last3 - wr_prev  # -1.0 to +1.0
    return 0.5 + (trend * 0.3)  # scale to 0.2-0.8


def head_to_head_score(h2h_matches: list[dict], team1_id: str, team2_id: str) -> float:
    """Layer 3: Win rate of team1 in direct matches against team2."""
    relevant = []
    for m in h2h_matches:
        if m.get("status") != "finished":
            continue
        opponent_ids = {
            str(o.get("opponent", {}).get("id", ""))
            for o in m.get("opponents", [])
        }
        if str(team1_id) in opponent_ids and str(team2_id) in opponent_ids:
            relevant.append(m)

    if len(relevant) < 2:
        return 0.5  # insufficient data

    wins_t1 = sum(
        1 for m in relevant
        if str((m.get("winner") or {}).get("id", "")) == str(team1_id)
    )
    return wins_t1 / len(relevant)


def draft_strength_score(blue_picks: list[str], red_picks: list[str]) -> float:
    """Layer 4: Average pro-play win rate of each team's picks; returns blue-side score."""
    DEFAULT_WR = 0.50

    def team_score(picks: list[str]) -> float:
        if not picks:
            return DEFAULT_WR
        scores = [PRO_PLAY_CHAMPION_WIN_RATES.get(p.lower(), DEFAULT_WR) for p in picks]
        return sum(scores) / len(scores)

    blue_score = team_score(blue_picks)
    red_score = team_score(red_picks)

    total = blue_score + red_score
    if total == 0:
        return 0.5
    return blue_score / total


def tournament_tier_factor(matches: list[dict], team_id: str) -> float:
    """Layer 5: Win rate weighted by league tier (major leagues count double)."""
    weighted_wins = 0.0
    total_weight = 0.0

    for m in matches:
        if m.get("status") != "finished":
            continue
        league_slug = (m.get("league", {}) or {}).get("slug", "").lower()
        weight = 2.0 if any(slug in league_slug for slug in MAJOR_LEAGUE_SLUGS) else 1.0
        total_weight += weight
        winner = m.get("winner") or {}
        if str(winner.get("id", "")) == str(team_id):
            weighted_wins += weight

    if total_weight == 0:
        return 0.5
    return weighted_wins / total_weight


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
    """5-layer prediction combining weighted winrate, form, h2h, draft and tier."""
    # Layer 1: weighted win rate
    wr1 = weighted_win_rate(matches1, team1_id)
    wr2 = weighted_win_rate(matches2, team2_id)
    wr_total = wr1 + wr2
    wr_score = wr1 / wr_total if wr_total > 0 else 0.5

    # Layer 2: recent form
    form1 = recent_form_score(matches1, team1_id)
    form2 = recent_form_score(matches2, team2_id)
    form_total = form1 + form2
    form_score = form1 / form_total if form_total > 0 else 0.5

    # Layer 3: head to head
    h2h_score = head_to_head_score(h2h_matches, team1_id, team2_id)

    # Layer 4: draft
    if blue_picks is not None and red_picks is not None:
        raw_draft = draft_strength_score(blue_picks, red_picks)
        # If team1 is on red side, invert (blue_picks belong to team2)
        draft_score = raw_draft if team1_is_blue else (1.0 - raw_draft)
    else:
        draft_score = 0.5

    # Layer 5: tournament tier
    tier1 = tournament_tier_factor(matches1, team1_id)
    tier2 = tournament_tier_factor(matches2, team2_id)
    tier_total = tier1 + tier2
    tier_score = tier1 / tier_total if tier_total > 0 else 0.5

    # Final weighted combination
    final_prob = (
        0.35 * wr_score
        + 0.20 * form_score
        + 0.15 * h2h_score
        + 0.20 * draft_score
        + 0.10 * tier_score
    )
    final_prob = max(0.05, min(0.95, final_prob))  # clamp

    # Aggregate kills and duration from historical game data
    all_kills: list[float] = []
    all_durations: list[int] = []
    for matches, tid in [(matches1, team1_id), (matches2, team2_id)]:
        for m in matches:
            for game in m.get("games", []):
                dur = game.get("length")
                if dur:
                    all_durations.append(dur)
                for result in game.get("results", []):
                    if str(result.get("team_id", "")) == str(tid):
                        k = result.get("kills")
                        if k is not None:
                            all_kills.append(k)

    avg_kills_per_team = sum(all_kills) / len(all_kills) if all_kills else 15.0
    predicted_total_kills = round(avg_kills_per_team * 2, 2)
    predicted_duration = int(sum(all_durations) / len(all_durations)) if all_durations else 1800

    match_count = min(
        len([m for m in matches1 if m.get("status") == "finished"]),
        len([m for m in matches2 if m.get("status") == "finished"]),
    )
    confidence = min(match_count / 20.0, 1.0)
    if blue_picks:
        confidence = min(confidence + 0.1, 1.0)

    features = {
        "weighted_winrate_score": round(wr_score, 4),
        "recent_form_score": round(form_score, 4),
        "head_to_head_score": round(h2h_score, 4),
        "draft_strength_score": round(draft_score, 4),
        "tournament_tier_score": round(tier_score, 4),
        "team1_weighted_wr": round(wr1, 4),
        "team2_weighted_wr": round(wr2, 4),
        "team1_form": round(form1, 4),
        "team2_form": round(form2, 4),
        "h2h_match_count": len([m for m in h2h_matches if m.get("status") == "finished"]),
        "draft_adjusted": blue_picks is not None,
        "blue_picks": blue_picks,
        "red_picks": red_picks,
    }

    return {
        "win_prob_team1": round(final_prob, 6),
        "win_prob_team2": round(1.0 - final_prob, 6),
        "predicted_total_kills": predicted_total_kills,
        "predicted_duration_seconds": predicted_duration,
        "confidence_score": round(confidence, 6),
        "features_snapshot": features,
    }
