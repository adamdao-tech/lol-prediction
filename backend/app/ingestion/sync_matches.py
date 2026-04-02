from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Match, Team, Tournament, League
from app.models.game import Game, GameStatus
from app.models.match import MatchStatus
from app.models.ingestion_log import IngestionLog, IngestionStatus
from app.ingestion.pandascore_client import PandaScoreClient
from app.ingestion.lol_esports_client import LoLEsportsClient
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


def _map_game_status(status: str) -> GameStatus:
    mapping = {
        "not_started": GameStatus.not_started,
        "running": GameStatus.running,
        "finished": GameStatus.finished,
    }
    return mapping.get(status, GameStatus.not_started)


async def _ensure_game(db: AsyncSession, match_id: int, game_data: dict) -> None:
    """Upsert a Game record from PandaScore game data."""
    ps_game_id = str(game_data.get("id", "")) if game_data.get("id") else None
    game_number = game_data.get("position") or game_data.get("game_number") or 1
    game_status = _map_game_status(game_data.get("status", "not_started"))

    if ps_game_id:
        result = await db.execute(select(Game).where(Game.pandascore_id == ps_game_id))
        game = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Game).where(Game.match_id == match_id, Game.game_number == game_number)
        )
        game = result.scalar_one_or_none()

    if game is None:
        game = Game(
            pandascore_id=ps_game_id,
            lol_esports_game_id=None,
            match_id=match_id,
            game_number=game_number,
            status=game_status,
        )
        db.add(game)
    else:
        game.status = game_status


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

            for game_data in item.get("games") or []:
                await _ensure_game(db, match.id, game_data)
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


async def sync_running_matches(db: AsyncSession) -> dict:
    start = time.monotonic()
    inserted = updated = fetched = 0
    error_msg = None
    status = IngestionStatus.success

    try:
        async with PandaScoreClient() as client:
            matches_data = await client.get_lol_running_matches()

        fetched = len(matches_data)
        logger.info("Fetched running matches", count=fetched)

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

            result = await db.execute(select(Match).where(Match.pandascore_id == ps_id))
            match = result.scalar_one_or_none()

            match_status = MatchStatus.running

            if match is None:
                match = Match(
                    pandascore_id=ps_id,
                    tournament_id=tournament_id,
                    team1_id=team1_id,
                    team2_id=team2_id,
                    scheduled_at=_parse_dt(item.get("scheduled_at")),
                    status=match_status,
                    number_of_games=item.get("number_of_games"),
                    raw_data=item,
                )
                db.add(match)
                inserted += 1
            else:
                match.status = match_status
                match.tournament_id = tournament_id
                match.team1_id = team1_id
                match.team2_id = team2_id
                match.number_of_games = item.get("number_of_games")
                match.raw_data = item
                updated += 1

            await db.flush()

            for game_data in item.get("games") or []:
                await _ensure_game(db, match.id, game_data)

        await db.flush()
    except Exception as exc:
        error_msg = str(exc)
        status = IngestionStatus.failed
        logger.error("sync_running_matches failed", error=error_msg)

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


async def sync_lol_esports_game_ids(db: AsyncSession) -> dict:
    """Fetch real LoL Esports game IDs from the LoL Esports schedule API and update Game records.

    Matches our stored Match records against LoL Esports schedule events by team
    codes/acronyms, then calls getEventDetails to get the authoritative game IDs
    (18-digit strings required by the livestats API).
    """
    updated = 0
    error_msg = None

    try:
        # Load scheduled and running matches together with their games and teams
        result = await db.execute(
            select(Match)
            .where(Match.status.in_([MatchStatus.scheduled, MatchStatus.running]))
            .options(
                selectinload(Match.games),
                selectinload(Match.team1),
                selectinload(Match.team2),
            )
        )
        matches = result.scalars().all()

        if not matches:
            return {"updated": 0}

        # Build lookup: frozenset({team1_code, team2_code}) -> Match
        # Use acronym first, fall back to name; normalise to lowercase
        match_lookup: dict[frozenset, Match] = {}
        for match in matches:
            t1 = match.team1
            t2 = match.team2
            if not t1 or not t2:
                continue
            code1 = (t1.acronym or t1.name or "").lower().strip()
            code2 = (t2.acronym or t2.name or "").lower().strip()
            if code1 and code2:
                match_lookup[frozenset([code1, code2])] = match

        async with LoLEsportsClient() as lol_client:
            schedule = await lol_client.get_schedule()
            events = schedule.get("data", {}).get("schedule", {}).get("events", [])

            for event in events:
                match_data = event.get("match") or {}
                lol_match_id = match_data.get("id")
                if not lol_match_id:
                    continue

                teams = match_data.get("teams") or []
                if len(teams) < 2:
                    continue

                code1 = (teams[0].get("code") or teams[0].get("name") or "").lower().strip()
                code2 = (teams[1].get("code") or teams[1].get("name") or "").lower().strip()
                if not code1 or not code2:
                    continue

                our_match = match_lookup.get(frozenset([code1, code2]))
                if our_match is None:
                    continue

                try:
                    details = await lol_client.get_event_details(str(lol_match_id))
                    event_match = details.get("data", {}).get("event", {}).get("match", {})
                    lol_games = event_match.get("games") or []

                    # Build game_number -> lol_game_id mapping from the response
                    lol_id_by_number: dict[int, str] = {}
                    for g in lol_games:
                        g_id = g.get("id")
                        g_num = g.get("number")
                        if g_id and g_num is not None:
                            lol_id_by_number[int(g_num)] = str(g_id)

                    for game in our_match.games:
                        real_id = lol_id_by_number.get(game.game_number)
                        if real_id and game.lol_esports_game_id != real_id:
                            game.lol_esports_game_id = real_id
                            updated += 1

                except Exception as exc:
                    logger.warning(
                        "Failed to fetch event details",
                        lol_match_id=lol_match_id,
                        error=str(exc),
                    )

        await db.flush()
    except Exception as exc:
        logger.error("sync_lol_esports_game_ids failed", error=str(exc))
        return {"updated": updated, "error": "sync failed — see server logs"}

    logger.info("sync_lol_esports_game_ids complete", updated=updated)
    return {"updated": updated}
