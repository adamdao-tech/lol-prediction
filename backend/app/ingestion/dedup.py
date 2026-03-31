from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models import Match, Team
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def deduplicate_matches(db: AsyncSession) -> int:
    """Remove duplicate matches, keeping the row with the lowest id for each pandascore_id."""
    result = await db.execute(
        select(Match.pandascore_id, func.min(Match.id).label("keep_id"))
        .where(Match.pandascore_id.isnot(None))
        .group_by(Match.pandascore_id)
        .having(func.count(Match.id) > 1)
    )
    rows = result.all()
    removed = 0
    for row in rows:
        del_result = await db.execute(
            delete(Match)
            .where(Match.pandascore_id == row.pandascore_id)
            .where(Match.id != row.keep_id)
        )
        removed += del_result.rowcount
    if removed:
        logger.info("Deduplicated matches", removed=removed)
    return removed


async def deduplicate_teams(db: AsyncSession) -> int:
    """Remove duplicate teams, keeping the row with the lowest id for each pandascore_id."""
    result = await db.execute(
        select(Team.pandascore_id, func.min(Team.id).label("keep_id"))
        .where(Team.pandascore_id.isnot(None))
        .group_by(Team.pandascore_id)
        .having(func.count(Team.id) > 1)
    )
    rows = result.all()
    removed = 0
    for row in rows:
        del_result = await db.execute(
            delete(Team)
            .where(Team.pandascore_id == row.pandascore_id)
            .where(Team.id != row.keep_id)
        )
        removed += del_result.rowcount
    if removed:
        logger.info("Deduplicated teams", removed=removed)
    return removed
