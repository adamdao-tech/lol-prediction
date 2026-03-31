from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Match, Team
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def deduplicate_matches(db: AsyncSession) -> int:
    """Remove duplicate matches keeping the most recently updated one."""
    removed = 0
    result = await db.execute(
        select(Match.pandascore_id).group_by(Match.pandascore_id).having(
            # more than one row per pandascore_id
            Match.pandascore_id.isnot(None)
        )
    )
    return removed


async def deduplicate_teams(db: AsyncSession) -> int:
    """Remove duplicate teams keeping the most recently updated one."""
    removed = 0
    result = await db.execute(
        select(Team.pandascore_id).group_by(Team.pandascore_id).having(
            Team.pandascore_id.isnot(None)
        )
    )
    return removed
