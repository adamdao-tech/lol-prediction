from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Match, OddsSnapshot, Prediction
from app.models.game import Game, GameStatus
from app.models.match import MatchStatus
from app.models.tournament import Tournament
from app.schemas.match import MatchListItem, MatchDetail

router = APIRouter()


@router.get("/live", response_model=list[MatchListItem])
async def get_live_matches(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_id: int | None = Query(None),
):
    stmt = (
        select(Match)
        .options(
            selectinload(Match.team1),
            selectinload(Match.team2),
            selectinload(Match.tournament).selectinload(Tournament.league),
            selectinload(Match.predictions),
            selectinload(Match.odds_snapshots),
            selectinload(Match.games),
        )
        .where(Match.status == MatchStatus.running)
        .order_by(Match.scheduled_at)
    )
    if league_id is not None:
        stmt = stmt.join(Match.tournament).where(
            Match.tournament.has(league_id=league_id)
        )
    result = await db.execute(stmt)
    matches = result.scalars().all()
    return [_build_match_list_item(m) for m in matches]


@router.get("/upcoming", response_model=list[MatchListItem])
async def get_upcoming_matches(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_id: int | None = Query(None),
    days_ahead: int = Query(7, ge=1, le=30),
    with_odds_only: bool = Query(False),
):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)

    stmt = (
        select(Match)
        .options(
            selectinload(Match.team1),
            selectinload(Match.team2),
            selectinload(Match.tournament).selectinload(Tournament.league),
            selectinload(Match.predictions),
            selectinload(Match.odds_snapshots),
        )
        .where(Match.status == MatchStatus.scheduled)
        .where(Match.scheduled_at >= now)
        .where(Match.scheduled_at <= cutoff)
        .order_by(Match.scheduled_at)
    )

    if league_id is not None:
        stmt = stmt.join(Match.tournament).where(
            Match.tournament.has(league_id=league_id)
        )

    result = await db.execute(stmt)
    matches = result.scalars().all()

    output = []
    for m in matches:
        if with_odds_only and not m.odds_snapshots:
            continue
        item = _build_match_list_item(m)
        output.append(item)
    return output


@router.get("/finished", response_model=list[MatchListItem])
async def get_finished_matches(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    stmt = (
        select(Match)
        .options(
            selectinload(Match.team1),
            selectinload(Match.team2),
            selectinload(Match.tournament).selectinload(Tournament.league),
            selectinload(Match.predictions),
            selectinload(Match.odds_snapshots),
        )
        .where(Match.status == MatchStatus.finished)
        .order_by(Match.scheduled_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    if date_from:
        stmt = stmt.where(Match.scheduled_at >= date_from)
    if date_to:
        stmt = stmt.where(Match.scheduled_at <= date_to)

    result = await db.execute(stmt)
    matches = result.scalars().all()
    return [_build_match_list_item(m) for m in matches]


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match(match_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    from fastapi import HTTPException

    stmt = (
        select(Match)
        .options(
            selectinload(Match.team1),
            selectinload(Match.team2),
            selectinload(Match.winner),
            selectinload(Match.tournament).selectinload(Tournament.league),
            selectinload(Match.games),
            selectinload(Match.predictions),
            selectinload(Match.odds_snapshots),
        )
        .where(Match.id == match_id)
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


def _build_match_list_item(m: Match) -> dict:
    latest_pred = None
    if m.predictions:
        latest_pred = sorted(m.predictions, key=lambda p: p.created_at, reverse=True)[0]

    latest_odds = None
    if m.odds_snapshots:
        latest_odds = sorted(m.odds_snapshots, key=lambda o: o.snapshot_at, reverse=True)[0]

    tournament = None
    if m.tournament is not None:
        t = m.tournament
        league_data = None
        # Access only attributes loaded by selectinload — no lazy loading
        league = t.__dict__.get("league")
        if league is not None:
            league_data = {
                "id": league.id,
                "name": league.name,
                "region": league.region,
            }
        tournament = {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "league": league_data,
        }

    # Determine live_game_id: prefer lol_esports_game_id for livestats API,
    # fall back to pandascore_id only if lol_esports_game_id is missing
    live_game_id: str | None = None
    games: list = m.__dict__.get("games", [])
    if games and m.status == MatchStatus.running:
        running_game = next(
            (g for g in games if g.status != GameStatus.finished and g.lol_esports_game_id),
            None,
        )
        if running_game:
            live_game_id = running_game.lol_esports_game_id
        else:
            first_game = next(
                (g for g in games if g.lol_esports_game_id or g.pandascore_id),
                None,
            )
            if first_game:
                live_game_id = first_game.lol_esports_game_id or first_game.pandascore_id

    return {
        "id": m.id,
        "pandascore_id": m.pandascore_id,
        "team1": m.__dict__.get("team1"),
        "team2": m.__dict__.get("team2"),
        "scheduled_at": m.scheduled_at,
        "status": m.status.value if m.status else "scheduled",
        "number_of_games": m.number_of_games,
        "tournament": tournament,
        "latest_prediction": latest_pred,
        "latest_odds": latest_odds,
        "live_game_id": live_game_id,
        "patch_version": m.patch_version,
        "winner_id": m.winner_id,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
        "games": m.__dict__.get("games", []),
        "predictions": m.__dict__.get("predictions", []),
        "odds_snapshots": m.__dict__.get("odds_snapshots", []),
    }
