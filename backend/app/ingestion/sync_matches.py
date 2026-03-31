from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Match, Team, Tournament, League
from app.models.match import MatchStatus
from app.models.ingestion_log import IngestionLog, IngestionStatus
from app.ingestion.pandascore_client import PandaScoreClient
from app.utils.logging import get_logger
import time

logger = get_logger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def _map_status(status: str) -> MatchStatus:
    mapping = {
        "not_started": MatchStatus.scheduled,
        "running": MatchStatus.running,
        "finished": MatchStatus.finished,
        "cancelled": MatchStatus.cancelled,
        "postponed": MatchStatus.cancelled,
    }
    return mapping.get(status, MatchStatus.scheduled)


async def _ensure_team(db: AsyncSession, data: dict | None) -> int | None:
    if not data:
        return None
    ps_id = str(data.get("id", ""))
    if not ps_id:
        return None
    result = await db.execute(select(Team).where(Team.pandascore_id == ps_id))
    team = result.scalar_one_or_none()
    if team is None:
        team = Team(
            pandascore_id=ps_id,
            name=data.get("name", ""),
            slug=data.get("slug"),
            acronym=data.get("acronym"),
            image_url=data.get("image_url"),
        )
        db.add(team)
        await db.flush()
    return team.id


async def _ensure_league(db: AsyncSession, data: dict | None) -> int | None:
    if not data:
        return None
    ps_id = str(data.get("id", ""))
    if not ps_id:
        return None
    result = await db.execute(select(League).where(League.pandascore_id == ps_id))
    league = result.scalar_one_or_none()
    if league is None:
        league = League(
            pandascore_id=ps_id,
            name=data.get("name", ""),
            slug=data.get("slug"),
            image_url=data.get("image_url"),
        )
        db.add(league)
        await db.flush()
    return league.id


async def _ensure_tournament(db: AsyncSession, data: dict | None, league_id: int | None) -> int | None:
    if not data:
        return None
    ps_id = str(data.get("id", ""))
    if not ps_id:
        return None
    result = await db.execute(select(Tournament).where(Tournament.pandascore_id == ps_id))
    tournament = result.scalar_one_or_none()
    if tournament is None:
        tournament = Tournament(
            pandascore_id=ps_id,
            league_id=league_id,
            name=data.get("name", ""),
            slug=data.get("slug"),
            tier=data.get("tier"),
            begin_at=_parse_dt(data.get("begin_at")),
            end_at=_parse_dt(data.get("end_at")),
        )
        db.add(tournament)
        await db.flush()
    return tournament.id


async def sync_upcoming_matches(db: AsyncSession) -> dict:
    start = time.monotonic()
    inserted = updated = fetched = 0
    error_msg = None
    status = IngestionStatus.success

    try:
        async with PandaScoreClient() as client:
            matches_data = await client.get_lol_upcoming_matches()

        fetched = len(matches_data)
        logger.info("Fetched upcoming matches", count=fetched)

        for item in matches_data:
            ps_id = str(item.get("id", ""))
            if not ps_id:
                continue

            opponents = item.get("opponents", [])
            team1_data = opponents[0].get("opponent") if len(opponents) > 0 else None
            team2_data = opponents[1].get("opponent") if len(opponents) > 1 else None

            team1_id = await _ensure_team(db, team1_data)
            team2_id = await _ensure_team(db, team2_data)

            league_data = item.get("league")
            league_id = await _ensure_league(db, league_data)

            tournament_data = item.get("tournament")
            tournament_id = await _ensure_tournament(db, tournament_data, league_id)

            winner_data = item.get("winner")
            winner_id = None
            if winner_data and winner_data.get("id"):
                winner_id = await _ensure_team(db, winner_data)

            result = await db.execute(select(Match).where(Match.pandascore_id == ps_id))
            match = result.scalar_one_or_none()

            match_status = _map_status(item.get("status", "not_started"))

            if match is None:
                match = Match(
                    pandascore_id=ps_id,
                    tournament_id=tournament_id,
                    team1_id=team1_id,
                    team2_id=team2_id,
                    scheduled_at=_parse_dt(item.get("scheduled_at")),
                    status=match_status,
                    number_of_games=item.get("number_of_games"),
                    winner_id=winner_id,
                    raw_data=item,
                )
                db.add(match)
                inserted += 1
            else:
                match.tournament_id = tournament_id
                match.team1_id = team1_id
                match.team2_id = team2_id
                match.scheduled_at = _parse_dt(item.get("scheduled_at"))
                match.status = match_status
                match.number_of_games = item.get("number_of_games")
                match.winner_id = winner_id
                match.raw_data = item
                updated += 1

        await db.flush()
    except Exception as exc:
        error_msg = str(exc)
        status = IngestionStatus.failed
        logger.error("sync_upcoming_matches failed", error=error_msg)

    duration_ms = int((time.monotonic() - start) * 1000)
    log = IngestionLog(
        source="pandascore",
        entity_type="match",
        status=status,
        records_fetched=fetched,
        records_inserted=inserted,
        records_updated=updated,
        error_message=error_msg,
        duration_ms=duration_ms,
    )
    db.add(log)
    await db.flush()

    return {"fetched": fetched, "inserted": inserted, "updated": updated}
