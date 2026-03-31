from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Match, Prediction, ModelVersion, Team
from app.models.model_version import ModelType
from app.schemas.prediction import PredictionOut
from app.ingestion.pandascore_client import PandaScoreClient
from app.prediction.engine import compute_full_prediction

router = APIRouter()


def _extract_picks_from_raw(
    raw_data: dict | None, team1_pandascore_id: str
) -> tuple[list[str], list[str], bool]:
    """Extract blue/red picks from raw PandaScore match data.

    Returns (blue_picks, red_picks, team1_is_blue).
    """
    if not raw_data:
        return [], [], True

    blue_picks: list[str] = []
    red_picks: list[str] = []
    team1_is_blue = True

    games = raw_data.get("games", [])
    if not games:
        return [], [], True

    first_game = games[0]
    for team_data in first_game.get("teams", []):
        team_id = str(team_data.get("team", {}).get("id", ""))
        color = team_data.get("color", "")
        picks = [
            p.get("champion", {}).get("name", "")
            for p in team_data.get("picks", [])
            if p.get("champion")
        ]

        if color == "blue":
            blue_picks = picks
            if team_id == str(team1_pandascore_id):
                team1_is_blue = True
        elif color == "red":
            red_picks = picks
            if team_id == str(team1_pandascore_id):
                team1_is_blue = False

    return blue_picks, red_picks, team1_is_blue


@router.get("", response_model=list[PredictionOut])
async def list_predictions(
    db: Annotated[AsyncSession, Depends(get_db)],
    match_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    stmt = (
        select(Prediction)
        .order_by(Prediction.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    if match_id is not None:
        stmt = stmt.where(Prediction.match_id == match_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{match_id}/generate", response_model=PredictionOut)
async def generate_prediction(match_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Load match with teams and games
    stmt = (
        select(Match)
        .options(
            selectinload(Match.team1),
            selectinload(Match.team2),
            selectinload(Match.games),
        )
        .where(Match.id == match_id)
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    team1: Team | None = match.team1
    team2: Team | None = match.team2

    # Default fallback prediction
    pred_data: dict = {
        "win_prob_team1": 0.5,
        "win_prob_team2": 0.5,
        "predicted_total_kills": 30.0,
        "predicted_duration_seconds": 1800,
        "confidence_score": 0.0,
        "features_snapshot": {},
    }
    draft_adjusted = False

    if team1 and team2 and team1.pandascore_id and team2.pandascore_id:
        try:
            async with PandaScoreClient() as client:
                matches1 = await client.get_team_past_matches(team1.pandascore_id, per_page=20)
                matches2 = await client.get_team_past_matches(team2.pandascore_id, per_page=20)
                h2h_matches = await client.get_head_to_head_matches(
                    team1.pandascore_id, team2.pandascore_id, per_page=20
                )

            # Try to load draft picks from DB (via games → drafts)
            blue_picks: list[str] | None = None
            red_picks: list[str] | None = None
            team1_is_blue = True

            from app.models.draft import Draft

            for game in match.games:
                draft_result = await db.execute(
                    select(Draft).where(Draft.game_id == game.id).limit(1)
                )
                draft = draft_result.scalar_one_or_none()
                if draft and (draft.blue_picks or draft.red_picks):
                    blue_picks = draft.blue_picks or []
                    red_picks = draft.red_picks or []
                    # Determine side from game model
                    if game.blue_side_team_id and team1.id:
                        team1_is_blue = game.blue_side_team_id == team1.id
                    break

            # Fall back to raw_data from DB match record
            if blue_picks is None:
                blue_picks, red_picks, team1_is_blue = _extract_picks_from_raw(
                    match.raw_data, team1.pandascore_id
                )
                if not blue_picks and not red_picks:
                    blue_picks = None
                    red_picks = None

            pred_data = compute_full_prediction(
                matches1=matches1,
                matches2=matches2,
                h2h_matches=h2h_matches,
                team1_id=team1.pandascore_id,
                team2_id=team2.pandascore_id,
                blue_picks=blue_picks,
                red_picks=red_picks,
                team1_is_blue=team1_is_blue,
            )
            draft_adjusted = blue_picks is not None

        except Exception as e:
            pred_data["features_snapshot"] = {"error": str(e), "note": "fallback to 50/50"}
    else:
        pred_data["features_snapshot"] = {"note": "missing team pandascore_id, fallback to 50/50"}

    # Ensure v2 model version exists (create only once, deactivate old versions on first creation)
    mv_result = await db.execute(
        select(ModelVersion).where(
            ModelVersion.name == "multi-layer-v2",
            ModelVersion.version == "2.0.0",
        ).limit(1)
    )
    model_version = mv_result.scalar_one_or_none()
    if model_version is None:
        await db.execute(update(ModelVersion).values(is_active=False))
        model_version = ModelVersion(
            name="multi-layer-v2",
            version="2.0.0",
            description="5-layer prediction: weighted winrate + form + h2h + draft + tier",
            model_type=ModelType.combined,
            is_active=True,
            metrics={
                "weights": {
                    "weighted_winrate": 0.35,
                    "recent_form": 0.20,
                    "head_to_head": 0.15,
                    "draft_strength": 0.20,
                    "tournament_tier": 0.10,
                }
            },
        )
        db.add(model_version)
        await db.flush()

    prediction = Prediction(
        match_id=match_id,
        model_version_id=model_version.id,
        win_prob_team1=pred_data["win_prob_team1"],
        win_prob_team2=pred_data["win_prob_team2"],
        predicted_total_kills=pred_data["predicted_total_kills"],
        predicted_duration_seconds=pred_data["predicted_duration_seconds"],
        confidence_score=pred_data["confidence_score"],
        draft_adjusted=draft_adjusted,
        features_snapshot=pred_data.get("features_snapshot", {}),
    )
    db.add(prediction)
    await db.flush()
    return prediction

