from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.ingestion.oddspapi_client import OddsPapiClient
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
    Fetches LoL odds from OddsPapi.io and saves OddsSnapshots.
    Skips gracefully if API key not set.
    """
    if not settings.ODDSPAPI_SECRET_KEY:
        logger.info("sync_lol_odds: ODDSPAPI_SECRET_KEY not set, skipping")
        return {"skipped": True, "reason": "ODDSPAPI_SECRET_KEY not set"}

    async with OddsPapiClient() as client:
        events = await client.get_lol_odds()

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    for event in events:
        home_team = event.get("home", "")
        away_team = event.get("away", "")
        commence_time_raw = event.get("date")

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
            select(Match)
            .options(selectinload(Match.team1), selectinload(Match.team2))
            .where(
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

        # OddsPapi bookmakers is a dict: {bookmaker_name: [markets]}
        bookmakers_data = event.get("bookmakers", {})
        if isinstance(bookmakers_data, list):
            logger.warning(
                "sync_lol_odds: unexpected list format for bookmakers, expected dict",
                event_id=event.get("id"),
            )
            bookmaker_items = [
                (bk.get("key", bk.get("title", "unknown")), bk.get("markets", []))
                for bk in bookmakers_data
            ]
        else:
            bookmaker_items = [
                (name, markets) for name, markets in bookmakers_data.items()
            ]

        for bookmaker_name, markets in bookmaker_items:
            for market in markets:
                market_name = market.get("name", market.get("key", ""))
                if market_name not in ("ML", "h2h"):
                    continue

                odds_list = market.get("odds", [])
                outcomes = market.get("outcomes", [])

                team1_odds: float = 0.0
                team2_odds: float = 0.0

                if odds_list:
                    first_odds = odds_list[0] if odds_list else {} 
                    raw_home = first_odds.get("home", 0)
                    raw_away = first_odds.get("away", 0)
                    try:
                        home_odds_val = float(raw_home)
                        away_odds_val = float(raw_away)
                    except (ValueError, TypeError):
                        continue

                    t1_name = match.team1.name if match.team1 else ""
                    if _teams_match(home_team, t1_name):
                        team1_odds = home_odds_val
                        team2_odds = away_odds_val
                    else:
                        team1_odds = away_odds_val
                        team2_odds = home_odds_val

                elif len(outcomes) >= 2:
                    team1_odds_opt: float | None = None
                    team2_odds_opt: float | None = None
                    t1_name = match.team1.name if match.team1 else ""
                    t2_name = match.team2.name if match.team2 else ""
                    for outcome in outcomes:
                        oname = outcome.get("name", "")
                        oprice = float(outcome.get("price", 0))
                        if _teams_match(oname, t1_name):
                            team1_odds_opt = oprice
                        elif _teams_match(oname, t2_name):
                            team2_odds_opt = oprice

                    if team1_odds_opt is None or team2_odds_opt is None:
                        team1_odds_opt = float(outcomes[0].get("price", 0))
                        team2_odds_opt = float(outcomes[1].get("price", 0))

                    team1_odds = team1_odds_opt
                    team2_odds = team2_odds_opt
                else:
                    continue

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