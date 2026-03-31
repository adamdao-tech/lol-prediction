from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    if not raw_data:
        return [], [], True
    blue_picks: list[str] = []
    red_picks: list[str] = []
    team1_is_blue = True
    games = raw_data.get("games", [])
    if not games:
        return [], [], True
    for team_data in games[0].get("teams", []):
        team_id = str((team_data.get("team") or {}).get("id", ""))
        color = (team_data.get("color") or "").lower()
        picks = [
            (p.get("champion") or {}).get("name", "")
            for p in team_data.get("picks", [])
            if (p.get("champion") or {}).get("name")
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
    stmt = (
        select(Match)
        .options(selectinload(Match.team1), selectinload(Match.team2))
        .where(Match.id == match_id)
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    team1: Team | None = match.team1
    team2: Team | None = match.team2

    pred_data = {"win_prob_team1": 0.5, "win_prob_team2": 0.5,
                 "predicted_total_kills": 30.0, "predicted_duration_seconds": 1800,
                 "confidence_score": 0.0}
    draft_adjusted = False

    if team1 and team2 and team1.pandascore_id and team2.pandascore_id:
        try:
            async with PandaScoreClient() as client:
                matches1 = await client.get_team_past_matches(team1.pandascore_id, per_page=20)
                matches2 = await client.get_team_past_matches(team2.pandascore_id, per_page=20)
                h2h_matches = await client.get_head_to_head_matches(team1.pandascore_id, team2.pandascore_id)

            blue_picks, red_picks, team1_is_blue = _extract_picks_from_raw(
                match.raw_data, team1.pandascore_id
            )

            result = compute_full_prediction(
                matches1,
                matches2,
                h2h_matches,
                team1.pandascore_id,
                team2.pandascore_id,
                blue_picks if blue_picks else None,
                red_picks if red_picks else None,
                team1_is_blue,
            )
            pred_data = result
            features = result["features_snapshot"]
            draft_adjusted = bool(blue_picks)
        except Exception as e:
            features = {"error": str(e), "note": "fallback to 50/50"}
            draft_adjusted = False
    else:
        features = {"note": "missing team pandascore_id, fallback to 50/50"}
        draft_adjusted = False

    # Ensure model version exists
    mv_result = await db.execute(
        select(ModelVersion).where(ModelVersion.name == "multi-layer-v2").limit(1)
    )
    model_version = mv_result.scalar_one_or_none()
    if model_version is None:
        model_version = ModelVersion(
            name="multi-layer-v2",
            version="2.0.0",
            description="5-layer: weighted winrate + form + h2h + draft + tier",
            model_type=ModelType.combined,
            is_active=True,
            metrics={"method": "multi_layer_v2"},
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
        features_snapshot=features,
    )
    db.add(prediction)
    await db.flush()
    return prediction

