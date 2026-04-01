from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.ingestion.odds_api_client import OddsApiClient
from app.models import Match
from app.models.match import MatchStatus
from app.models.odds_snapshot import OddsSnapshot, OddsSource
from app.utils.logging import get_logger

logger = get_logger(__name__)

_MATCH_WINDOW_HOURS = 2


def _normalize_team_name(name: str) -> str:
    """Lowercase and strip common suffixes for fuzzy matching."""
    return name.lower().strip()


def _teams_match(api_name: str, db_name: str) -> bool:
    """Return True if team names are similar enough to be the same team."""
    a = _normalize_team_name(api_name)
    b = _normalize_team_name(db_name)
    return a == b or a in b or b in a


async def sync_lol_odds(db: AsyncSession) -> dict:
    """
    Fetches LoL odds from The Odds API and saves OddsSnapshots.
    Skips gracefully if API key not set.
    """
    if not settings.THE_ODDS_API_KEY:
        logger.info("sync_lol_odds: THE_ODDS_API_KEY not set, skipping")
        return {"skipped": True, "reason": "THE_ODDS_API_KEY not set"}

    async with OddsApiClient() as client:
        events = await client.get_lol_odds()

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    for event in events:
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence_time_raw = event.get("commence_time")

        if not home_team or not away_team or not commence_time_raw:
            skipped += 1
            continue

        try:
            commence_time = datetime.fromisoformat(
                commence_time_raw.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            skipped += 1
            continue

        # Find a matching Match in DB: scheduled_at within ±MATCH_WINDOW_HOURS, only active matches
        window_start = commence_time - timedelta(hours=_MATCH_WINDOW_HOURS)
        window_end = commence_time + timedelta(hours=_MATCH_WINDOW_HOURS)

        result = await db.execute(
            select(Match).where(
                Match.scheduled_at >= window_start,
                Match.scheduled_at <= window_end,
                Match.status.in_([MatchStatus.scheduled, MatchStatus.running]),
            )
        )
        candidates = result.scalars().all()

        match = None
        for candidate in candidates:
            t1_name = candidate.team1.name if candidate.team1 else ""
            t2_name = candidate.team2.name if candidate.team2 else ""
            if (
                _teams_match(home_team, t1_name) and _teams_match(away_team, t2_name)
            ) or (
                _teams_match(home_team, t2_name) and _teams_match(away_team, t1_name)
            ):
                match = candidate
                break

        if match is None:
            logger.debug(
                "sync_lol_odds: no DB match found",
                home=home_team,
                away=away_team,
                commence=commence_time_raw,
            )
            skipped += 1
            continue

        for bookmaker in event.get("bookmakers", []):
            bookmaker_name = bookmaker.get("key", bookmaker.get("title", "unknown"))
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = market.get("outcomes", [])
                if len(outcomes) < 2:
                    continue

                # Map outcomes to team1/team2 order matching the DB match
                team1_odds: float | None = None
                team2_odds: float | None = None
                for outcome in outcomes:
                    oname = outcome.get("name", "")
                    oprice = float(outcome.get("price", 0))
                    t1_name = match.team1.name if match.team1 else ""
                    t2_name = match.team2.name if match.team2 else ""
                    if _teams_match(oname, t1_name):
                        team1_odds = oprice
                    elif _teams_match(oname, t2_name):
                        team2_odds = oprice

                if team1_odds is None or team2_odds is None:
                    # Fall back to positional assignment
                    team1_odds = float(outcomes[0].get("price", 0))
                    team2_odds = float(outcomes[1].get("price", 0))

                if team1_odds <= 0 or team2_odds <= 0:
                    continue

                implied1 = 1.0 / team1_odds
                implied2 = 1.0 / team2_odds
                total_implied = implied1 + implied2
                vig = total_implied - 1.0 if total_implied > 1.0 else 0.0

                snap = OddsSnapshot(
                    match_id=match.id,
                    bookmaker=bookmaker_name,
                    team1_odds=team1_odds,
                    team2_odds=team2_odds,
                    implied_prob_team1=implied1,
                    implied_prob_team2=implied2,
                    vig=vig,
                    snapshot_at=now,
                    source=OddsSource.api,
                    raw_data=event,
                )
                db.add(snap)
                inserted += 1

    await db.flush()
    logger.info("sync_lol_odds done", inserted=inserted, skipped=skipped)
    return {"inserted": inserted, "skipped": skipped}
