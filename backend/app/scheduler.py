from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.database import AsyncSessionLocal
from app.ingestion.sync_matches import sync_upcoming_matches, sync_running_matches, sync_lol_esports_game_ids
from app.ingestion.sync_leagues import sync_leagues
from app.ingestion.sync_teams import sync_teams
from app.ingestion.sync_odds import sync_lol_odds
from app.utils.logging import get_logger

logger = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def _run_sync_matches() -> None:
    logger.info("scheduler: starting sync_upcoming_matches")
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_upcoming_matches(db)
            await db.commit()
            logger.info("scheduler: sync_upcoming_matches done", **result)
        except Exception as exc:
            await db.rollback()
            logger.error("scheduler: sync_upcoming_matches error", error=str(exc))


async def _run_sync_running_matches() -> None:
    logger.info("scheduler: starting sync_running_matches")
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_running_matches(db)
            await db.commit()
            logger.info("scheduler: sync_running_matches done", **result)
        except Exception as exc:
            await db.rollback()
            logger.error("scheduler: sync_running_matches error", error=str(exc))


async def _run_sync_leagues() -> None:
    logger.info("scheduler: starting sync_leagues")
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_leagues(db)
            await db.commit()
            logger.info("scheduler: sync_leagues done", **result)
        except Exception as exc:
            await db.rollback()
            logger.error("scheduler: sync_leagues error", error=str(exc))


async def _run_sync_teams() -> None:
    logger.info("scheduler: starting sync_teams")
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_teams(db)
            await db.commit()
            logger.info("scheduler: sync_teams done", **result)
        except Exception as exc:
            await db.rollback()
            logger.error("scheduler: sync_teams error", error=str(exc))


async def _run_sync_odds() -> None:
    logger.info("scheduler: starting sync_lol_odds")
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_lol_odds(db)
            await db.commit()
            logger.info("scheduler: sync_lol_odds done", **result)
        except Exception as exc:
            await db.rollback()
            logger.error("scheduler: sync_lol_odds error", error=str(exc))


async def _run_sync_lol_game_ids() -> None:
    logger.info("scheduler: starting sync_lol_esports_game_ids")
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_lol_esports_game_ids(db)
            await db.commit()
            logger.info("scheduler: sync_lol_esports_game_ids done", **result)
        except Exception as exc:
            await db.rollback()
            logger.error("scheduler: sync_lol_esports_game_ids error", error=str(exc))


def start_scheduler() -> None:
    scheduler.add_job(
        _run_sync_matches,
        trigger=IntervalTrigger(minutes=30),
        id="sync_upcoming_matches",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_sync_running_matches,
        trigger=IntervalTrigger(minutes=2),
        id="sync_running_matches",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_sync_leagues,
        trigger=IntervalTrigger(hours=24),
        id="sync_leagues",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_sync_teams,
        trigger=IntervalTrigger(hours=6),
        id="sync_teams",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_sync_odds,
        trigger=IntervalTrigger(minutes=60),
        id="sync_lol_odds",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_sync_lol_game_ids,
        trigger=IntervalTrigger(minutes=5),
        id="sync_lol_game_ids",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
