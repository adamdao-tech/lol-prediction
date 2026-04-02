from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.ingestion.lol_esports_client import LoLEsportsClient, LiveDataNotAvailable
from app.ingestion.sync_matches import sync_lol_esports_game_ids
from app.models import Match
from app.models.game import Game, GameStatus
from app.prediction.live_engine import compute_live_win_prob
from app.schemas.live import LivePredictionOut, LiveSignals, LiveWindowOut

router = APIRouter()

_MAX_PROB_HISTORY = 20
# LoL Esports internal game IDs are 18-digit strings; anything shorter is invalid
# (e.g. PandaScore game IDs are typically 5-7 digits).
_MIN_LOL_ESPORTS_GAME_ID_LENGTH = 15


def _find_valid_game(games: list) -> Game | None:
    """Return the best game with a valid LoL Esports game ID.

    Prefers a currently running game; falls back to any game with a valid ID.
    A valid ID has at least _MIN_LOL_ESPORTS_GAME_ID_LENGTH characters (18-digit strings).
    """
    # Prefer a running game with a valid lol_esports_game_id
    for g in games:
        if (
            g.lol_esports_game_id
            and len(g.lol_esports_game_id) >= _MIN_LOL_ESPORTS_GAME_ID_LENGTH
            and g.status == GameStatus.running
        ):
            return g
    # Fall back to any game with a valid lol_esports_game_id
    for g in games:
        if g.lol_esports_game_id and len(g.lol_esports_game_id) >= _MIN_LOL_ESPORTS_GAME_ID_LENGTH:
            return g
    return None


def _build_live_window_out(game_id: str, window_data: dict) -> LiveWindowOut:
    """Build a LiveWindowOut response from raw livestats window data."""
    frames = window_data.get("frames", [])
    if not frames:
        raise HTTPException(status_code=404, detail="No live data available for this game_id")

    game_state = window_data.get("gameMetadata", {}).get("gameState", "unknown")
    game_metadata = window_data.get("gameMetadata", {})

    prob_history: list[float] = []
    for frame in frames[-_MAX_PROB_HISTORY:]:
        enriched = {**frame, "gameMetadata": game_metadata}
        frame_pred = compute_live_win_prob(enriched)
        prob_history.append(frame_pred["win_prob_blue"])

    latest_frame = frames[-1]
    enriched_latest = {**latest_frame, "gameMetadata": game_metadata}
    prediction_data = compute_live_win_prob(enriched_latest)
    signals = LiveSignals(**prediction_data["signals"])

    prediction = LivePredictionOut(
        game_id=game_id,
        win_prob_blue=prediction_data["win_prob_blue"],
        win_prob_red=prediction_data["win_prob_red"],
        signals=signals,
        blue_dragons=prediction_data["blue_dragons"],
        red_dragons=prediction_data["red_dragons"],
        blue_total_kills=prediction_data["blue_total_kills"],
        red_total_kills=prediction_data["red_total_kills"],
        blue_total_gold=prediction_data["blue_total_gold"],
        red_total_gold=prediction_data["red_total_gold"],
        game_state=game_state,
        frame_timestamp=latest_frame.get("rfc460Timestamp"),
        game_timer_seconds=prediction_data["game_timer_seconds"],
        game_timer=prediction_data["game_timer"],
        blue_towers=prediction_data["blue_towers"],
        red_towers=prediction_data["red_towers"],
        blue_barons=prediction_data["blue_barons"],
        red_barons=prediction_data["red_barons"],
    )

    blue_participants = latest_frame.get("blueTeam", {}).get("participants", [])
    red_participants = latest_frame.get("redTeam", {}).get("participants", [])

    return LiveWindowOut(
        game_id=game_id,
        prediction=prediction,
        raw_participants_blue=blue_participants,
        raw_participants_red=red_participants,
        game_state=game_state,
        prob_history=prob_history,
        game_timer_seconds=prediction_data["game_timer_seconds"],
    )


@router.get("/by-match/{match_id}", response_model=LiveWindowOut)
async def get_live_by_match(
    match_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Fetch live stats for a match by its DB match ID.

    Looks up the running game with a valid LoL Esports game ID. If none is found,
    attempts a sync from the LoL Esports schedule API before retrying.
    """
    result = await db.execute(
        select(Match)
        .where(Match.id == match_id)
        .options(selectinload(Match.games))
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    game = _find_valid_game(match.games)

    if game is None:
        # Attempt to sync LoL Esports game IDs for this match and retry
        await sync_lol_esports_game_ids(db)
        # Reload games after sync
        await db.refresh(match, ["games"])
        game = _find_valid_game(match.games)

    if game is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No valid LoL Esports game ID found for match {match_id}. "
                "Run POST /api/admin/sync/lol-game-ids to populate game IDs."
            ),
        )

    game_id = game.lol_esports_game_id
    assert game_id is not None  # guaranteed by _find_valid_game

    async with LoLEsportsClient() as client:
        try:
            window_data = await client.get_live_window(game_id)
        except LiveDataNotAvailable as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Upstream livestats unavailable: {exc}")

    return _build_live_window_out(game_id, window_data)


@router.get("/{game_id}", response_model=LiveWindowOut)
async def get_live_prediction(game_id: str):
    # LoL Esports livestats API requires an 18-digit internal game ID.
    # Short numeric IDs (e.g. PandaScore game IDs) are not valid.
    if game_id.isdigit() and len(game_id) < _MIN_LOL_ESPORTS_GAME_ID_LENGTH:
        raise HTTPException(
            status_code=404,
            detail=(
                f"game_id '{game_id}' looks like a PandaScore ID and is not valid for the "
                "LoL Esports livestats API. Use the LoL Esports internal game ID instead."
            ),
        )
    client = LoLEsportsClient()
    try:
        async with client:
            window_data = await client.get_live_window(game_id)
    except LiveDataNotAvailable as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream livestats unavailable: {exc}")

    return _build_live_window_out(game_id, window_data)
