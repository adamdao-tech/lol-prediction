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

    trend = wr(finished[:3]) - wr(finished[3:10])
    return max(0.1, min(0.9, 0.5 + trend * 0.3))


def head_to_head_score(h2h_matches: list[dict], team1_id: str, team2_id: str) -> float:
    relevant = [
        m for m in h2h_matches
        if m.get("status") == "finished"
        and str(team1_id) in {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
        and str(team2_id) in {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
    ]
    if len(relevant) < 2:
        return 0.5
    wins = sum(1 for m in relevant if str((m.get("winner") or {}).get("id", "")) == str(team1_id))
    return wins / len(relevant)


def draft_strength_score(blue_picks: list[str], red_picks: list[str]) -> float:
    default = 0.50

    def team_score(picks: list[str]) -> float:
        if not picks:
            return default
        return sum(PRO_PLAY_CHAMPION_WIN_RATES.get(p.lower(), default) for p in picks) / len(picks)

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
    # Layer 1: weighted win rate
    wr1 = weighted_win_rate(matches1, team1_id)
    wr2 = weighted_win_rate(matches2, team2_id)
    wr_score = wr1 / (wr1 + wr2) if (wr1 + wr2) > 0 else 0.5

    # Layer 2: recent form
    form1 = recent_form_score(matches1, team1_id)
    form2 = recent_form_score(matches2, team2_id)
    form_score = form1 / (form1 + form2) if (form1 + form2) > 0 else 0.5

    # Layer 3: head-to-head
    h2h_score = head_to_head_score(h2h_matches, team1_id, team2_id)

    # Layer 4: draft
    if blue_picks is not None and red_picks is not None:
        raw_draft = draft_strength_score(blue_picks, red_picks)
        draft_score = raw_draft if team1_is_blue else (1.0 - raw_draft)
    else:
        draft_score = 0.5

    # Layer 5: tournament tier
    tier1 = tournament_tier_factor(matches1, team1_id)
    tier2 = tournament_tier_factor(matches2, team2_id)
    tier_score = tier1 / (tier1 + tier2) if (tier1 + tier2) > 0 else 0.5

    final_prob = max(0.05, min(0.95,
        0.35 * wr_score +
        0.20 * form_score +
        0.15 * h2h_score +
        0.20 * draft_score +
        0.10 * tier_score
    ))

    # Kills and duration from historical data
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

    avg_kills = sum(all_kills) / len(all_kills) if all_kills else 15.0
    predicted_total_kills = round(avg_kills * 2, 2)
    predicted_duration = int(sum(all_durations) / len(all_durations)) if all_durations else 1800

    f1 = len([m for m in matches1 if m.get("status") == "finished"])
    f2 = len([m for m in matches2 if m.get("status") == "finished"])
    confidence = min(min(f1, f2) / 20.0, 1.0)
    if blue_picks:
        confidence = min(confidence + 0.1, 1.0)

    h2h_count = len([
        m for m in h2h_matches
        if m.get("status") == "finished"
        and str(team1_id) in {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
        and str(team2_id) in {str(o.get("opponent", {}).get("id", "")) for o in m.get("opponents", [])}
    ])

    return {
        "win_prob_team1": round(final_prob, 6),
        "win_prob_team2": round(1.0 - final_prob, 6),
        "predicted_total_kills": predicted_total_kills,
        "predicted_duration_seconds": predicted_duration,
        "confidence_score": round(confidence, 6),
        "features_snapshot": {
            "weighted_winrate_score": round(wr_score, 4),
            "recent_form_score": round(form_score, 4),
            "head_to_head_score": round(h2h_score, 4),
            "draft_strength_score": round(draft_score, 4),
            "tournament_tier_score": round(tier_score, 4),
            "team1_weighted_wr": round(wr1, 4),
            "team2_weighted_wr": round(wr2, 4),
            "team1_form": round(form1, 4),
            "team2_form": round(form2, 4),
            "h2h_match_count": h2h_count,
            "draft_adjusted": blue_picks is not None,
            "blue_picks": blue_picks,
            "red_picks": red_picks,
        },
    }
