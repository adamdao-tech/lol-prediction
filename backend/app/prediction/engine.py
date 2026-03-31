from dataclasses import dataclass


@dataclass
class TeamStats:
    win_rate: float
    avg_kills: float
    avg_duration: float
    match_count: int


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

LAYER_WEIGHTS = {
    "weighted_winrate": 0.35,
    "recent_form": 0.20,
    "head_to_head": 0.15,
    "draft_strength": 0.20,
    "tournament_tier": 0.10,
}

MIN_MATCHES_FOR_FULL_CONFIDENCE = 20


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
    if total_weight == 0:
        return 0.5
    return weighted_wins / total_weight


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
    return 0.5 + (trend * 0.3)


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


def draft_strength_score(blue_picks: list[str], red_picks: list[str]) -> float:
    DEFAULT_WR = 0.50

    def team_score(picks: list[str]) -> float:
        if not picks:
            return DEFAULT_WR
        scores = [PRO_PLAY_CHAMPION_WIN_RATES.get(p.lower(), DEFAULT_WR) for p in picks]
        return sum(scores) / len(scores)

    blue = team_score(blue_picks)
    red = team_score(red_picks)
    total = blue + red
    return blue / total if total > 0 else 0.5


def tournament_tier_factor(matches: list[dict], team_id: str) -> float:
    weighted_wins = 0.0
    total_weight = 0.0
    for m in matches:
        if m.get("status") != "finished":
            continue
        league_slug = ((m.get("league") or {}).get("slug") or "").lower()
        weight = 2.0 if any(s in league_slug for s in MAJOR_LEAGUE_SLUGS) else 1.0
        total_weight += weight
        if str((m.get("winner") or {}).get("id", "")) == str(team_id):
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
    wr1 = weighted_win_rate(matches1, team1_id)
    wr2 = weighted_win_rate(matches2, team2_id)
    wr_total = wr1 + wr2
    wr_score = wr1 / wr_total if wr_total > 0 else 0.5

    form1 = recent_form_score(matches1, team1_id)
    form2 = recent_form_score(matches2, team2_id)
    form_total = form1 + form2
    form_score = form1 / form_total if form_total > 0 else 0.5

    h2h_score = head_to_head_score(h2h_matches, team1_id, team2_id)

    if blue_picks is not None and red_picks is not None:
        raw_draft = draft_strength_score(blue_picks, red_picks)
        draft_score = raw_draft if team1_is_blue else (1.0 - raw_draft)
    else:
        draft_score = 0.5

    tier1 = tournament_tier_factor(matches1, team1_id)
    tier2 = tournament_tier_factor(matches2, team2_id)
    tier_total = tier1 + tier2
    tier_score = tier1 / tier_total if tier_total > 0 else 0.5

    final_prob = (
        LAYER_WEIGHTS["weighted_winrate"] * wr_score +
        LAYER_WEIGHTS["recent_form"] * form_score +
        LAYER_WEIGHTS["head_to_head"] * h2h_score +
        LAYER_WEIGHTS["draft_strength"] * draft_score +
        LAYER_WEIGHTS["tournament_tier"] * tier_score
    )
    final_prob = max(0.05, min(0.95, final_prob))

    all_kills = []
    all_durations = []
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

    finished1 = len([m for m in matches1 if m.get("status") == "finished"])
    finished2 = len([m for m in matches2 if m.get("status") == "finished"])
    confidence = min(min(finished1, finished2) / MIN_MATCHES_FOR_FULL_CONFIDENCE, 1.0)
    if blue_picks:
        confidence = min(confidence + 0.1, 1.0)

    h2h_relevant_count = len([
        m for m in h2h_matches
        if m.get("status") == "finished"
        and str(team1_id) in {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
        and str(team2_id) in {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
    ])

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
        "h2h_match_count": h2h_relevant_count,
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


def _extract_team_stats(matches: list[dict], team_pandascore_id: str) -> TeamStats:
    """Extracts team statistics from a list of finished matches."""
    wins = 0
    total_kills = []
    total_durations = []

    for m in matches:
        if m.get("status") != "finished":
            continue

        opponents = m.get("opponents", [])
        team_ids = [str(o.get("opponent", {}).get("id", "")) for o in opponents]
        if str(team_pandascore_id) not in team_ids:
            continue

        winner = m.get("winner", {})
        if winner and str(winner.get("id", "")) == str(team_pandascore_id):
            wins += 1

        for game in m.get("games", []):
            duration = game.get("length")
            if duration:
                total_durations.append(duration)
            for result in game.get("results", []):
                if str(result.get("team_id", "")) == str(team_pandascore_id):
                    kills = result.get("kills")
                    if kills is not None:
                        total_kills.append(kills)

    n = len(matches)
    if n == 0:
        return TeamStats(win_rate=0.5, avg_kills=15.0, avg_duration=1800.0, match_count=0)

    win_rate = wins / n
    avg_kills = sum(total_kills) / len(total_kills) if total_kills else 15.0
    avg_duration = sum(total_durations) / len(total_durations) if total_durations else 1800.0

    return TeamStats(win_rate=win_rate, avg_kills=avg_kills, avg_duration=avg_duration, match_count=n)


def compute_prediction(stats1: TeamStats, stats2: TeamStats) -> dict:
    """Computes prediction from statistics of both teams."""
    total_wr = stats1.win_rate + stats2.win_rate

    if total_wr > 0:
        win_prob_team1 = stats1.win_rate / total_wr
    else:
        win_prob_team1 = 0.5

    win_prob_team2 = 1.0 - win_prob_team1

    predicted_total_kills = stats1.avg_kills + stats2.avg_kills
    predicted_duration_seconds = int((stats1.avg_duration + stats2.avg_duration) / 2)

    confidence = min(stats1.match_count, stats2.match_count) / 10.0
    confidence_score = min(confidence, 1.0)

    return {
        "win_prob_team1": round(win_prob_team1, 6),
        "win_prob_team2": round(win_prob_team2, 6),
        "predicted_total_kills": round(predicted_total_kills, 2),
        "predicted_duration_seconds": predicted_duration_seconds,
        "confidence_score": round(confidence_score, 6),
    }
