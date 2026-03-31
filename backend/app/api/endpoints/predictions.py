from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Match, Prediction, ModelVersion
from app.models.model_version import ModelType
from app.schemas.prediction import PredictionOut

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
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    # Ensure a default model version exists
    mv_result = await db.execute(
        select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
    )
    model_version = mv_result.scalar_one_or_none()
    if model_version is None:
        model_version = ModelVersion(
            name="baseline",
            version="0.1.0",
            description="Placeholder baseline model",
            model_type=ModelType.combined,
            is_active=True,
            metrics={"note": "stub"},
        )
        db.add(model_version)
        await db.flush()

    prediction = Prediction(
        match_id=match_id,
        model_version_id=model_version.id,
        win_prob_team1=0.5,
        win_prob_team2=0.5,
        predicted_total_kills=30.0,
        predicted_duration_seconds=1800,
        confidence_score=0.5,
        draft_adjusted=False,
        features_snapshot={"note": "stub prediction"},
    )
    db.add(prediction)
    await db.flush()
    return prediction
