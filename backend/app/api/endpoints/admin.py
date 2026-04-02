from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db, engine
from app.models.ingestion_log import IngestionLog
from app.ingestion.sync_matches import sync_upcoming_matches, sync_lol_esports_game_ids
from app.ingestion.sync_leagues import sync_leagues
from app.ingestion.sync_teams import sync_teams
from app.config import settings

router = APIRouter()


@router.get("/health")
async def admin_health(db: Annotated[AsyncSession, Depends(get_db)]):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    redis_status = "ok"
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception as exc:
        redis_status = f"error: {exc}"

    pandascore_status = "ok"
    if not settings.PANDASCORE_API_KEY or settings.PANDASCORE_API_KEY == "your_pandascore_api_key_here":
        pandascore_status = "no_api_key"

    return {
        "status": "ok",
        "db": db_status,
        "redis": redis_status,
        "pandascore": pandascore_status,
        "version": "0.1.0",
    }


@router.get("/ingestion-logs")
async def get_ingestion_logs(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(IngestionLog).order_by(IngestionLog.created_at.desc()).limit(100)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "source": log.source,
            "entity_type": log.entity_type,
            "status": log.status.value,
            "records_fetched": log.records_fetched,
            "records_inserted": log.records_inserted,
            "records_updated": log.records_updated,
            "error_message": log.error_message,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.post("/sync/matches")
async def trigger_sync_matches(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await sync_upcoming_matches(db)
    await db.flush()
    return result


@router.post("/sync/leagues")
async def trigger_sync_leagues(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await sync_leagues(db)
    await db.flush()
    return result


@router.post("/sync/teams")
async def trigger_sync_teams(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await sync_teams(db)
    await db.flush()
    return result


@router.post("/sync/lol-game-ids")
async def trigger_sync_lol_game_ids(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await sync_lol_esports_game_ids(db)
    return result
