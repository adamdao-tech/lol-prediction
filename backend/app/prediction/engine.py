from dataclasses import dataclass


@dataclass
class TeamStats:
    win_rate: float
    avg_kills: float
    avg_duration: float
    match_count: int


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

        # Win check
        winner = m.get("winner", {})
        if winner and str(winner.get("id", "")) == str(team_pandascore_id):
            wins += 1

        # Kills and duration from games
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
