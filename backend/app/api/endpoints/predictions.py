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
from app.prediction.engine import _extract_team_stats, compute_prediction

router = APIRouter()


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
    # Load match with teams
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

    # Download historical data from PandaScore and compute prediction
    pred_data = {"win_prob_team1": 0.5, "win_prob_team2": 0.5,
                 "predicted_total_kills": 30.0, "predicted_duration_seconds": 1800,
                 "confidence_score": 0.0}

    if team1 and team2 and team1.pandascore_id and team2.pandascore_id:
        try:
            async with PandaScoreClient() as client:
                matches1 = await client.get_team_past_matches(team1.pandascore_id, per_page=10)
                matches2 = await client.get_team_past_matches(team2.pandascore_id, per_page=10)

            stats1 = _extract_team_stats(matches1, team1.pandascore_id)
            stats2 = _extract_team_stats(matches2, team2.pandascore_id)
            pred_data = compute_prediction(stats1, stats2)

            features = {
                "team1_win_rate": stats1.win_rate,
                "team2_win_rate": stats2.win_rate,
                "team1_avg_kills": stats1.avg_kills,
                "team2_avg_kills": stats2.avg_kills,
                "team1_match_count": stats1.match_count,
                "team2_match_count": stats2.match_count,
            }
        except Exception as e:
            features = {"error": str(e), "note": "fallback to 50/50"}
    else:
        features = {"note": "missing team pandascore_id, fallback to 50/50"}

    # Ensure model version exists
    mv_result = await db.execute(
        select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
    )
    model_version = mv_result.scalar_one_or_none()
    if model_version is None:
        model_version = ModelVersion(
            name="pandascore-stats",
            version="1.0.0",
            description="Win rate based prediction from PandaScore historical data",
            model_type=ModelType.combined,
            is_active=True,
            metrics={"method": "win_rate_ratio"},
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
        draft_adjusted=False,
        features_snapshot=features,
    )
    db.add(prediction)
    await db.flush()
    return prediction

