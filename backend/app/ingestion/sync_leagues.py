from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import League
from app.models.ingestion_log import IngestionLog, IngestionStatus
from app.ingestion.pandascore_client import PandaScoreClient
from app.utils.logging import get_logger
import time

logger = get_logger(__name__)


async def sync_leagues(db: AsyncSession) -> dict:
    start = time.monotonic()
    inserted = updated = fetched = 0
    error_msg = None
    status = IngestionStatus.success

    try:
        async with PandaScoreClient() as client:
            leagues_data = await client.get_lol_leagues()

        fetched = len(leagues_data)
        logger.info("Fetched leagues", count=fetched)

        for item in leagues_data:
            ps_id = str(item.get("id", ""))
            if not ps_id:
                continue
            result = await db.execute(select(League).where(League.pandascore_id == ps_id))
            league = result.scalar_one_or_none()
            if league is None:
                league = League(
                    pandascore_id=ps_id,
                    name=item.get("name", ""),
                    slug=item.get("slug"),
                    image_url=item.get("image_url"),
                    region=item.get("region"),
                )
                db.add(league)
                inserted += 1
            else:
                league.name = item.get("name", league.name)
                league.slug = item.get("slug", league.slug)
                league.image_url = item.get("image_url", league.image_url)
                league.region = item.get("region", league.region)
                updated += 1

        await db.flush()
    except Exception as exc:
        error_msg = str(exc)
        status = IngestionStatus.failed
        logger.error("sync_leagues failed", error=error_msg)

    duration_ms = int((time.monotonic() - start) * 1000)
    log = IngestionLog(
        source="pandascore",
        entity_type="league",
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
