from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Team, Player
from app.models.ingestion_log import IngestionLog, IngestionStatus
from app.ingestion.pandascore_client import PandaScoreClient
from app.utils.logging import get_logger
import time

logger = get_logger(__name__)


async def sync_teams(db: AsyncSession) -> dict:
    start = time.monotonic()
    inserted = updated = fetched = 0
    error_msg = None
    status = IngestionStatus.success

    try:
        page = 1
        while True:
            async with PandaScoreClient() as client:
                teams_data = await client.get_lol_teams(page=page)
            if not teams_data:
                break
            fetched += len(teams_data)

            for item in teams_data:
                ps_id = str(item.get("id", ""))
                if not ps_id:
                    continue
                result = await db.execute(select(Team).where(Team.pandascore_id == ps_id))
                team = result.scalar_one_or_none()
                if team is None:
                    team = Team(
                        pandascore_id=ps_id,
                        name=item.get("name", ""),
                        slug=item.get("slug"),
                        acronym=item.get("acronym"),
                        image_url=item.get("image_url"),
                        region=item.get("location"),
                    )
                    db.add(team)
                    await db.flush()
                    inserted += 1
                else:
                    team.name = item.get("name", team.name)
                    team.slug = item.get("slug", team.slug)
                    team.acronym = item.get("acronym", team.acronym)
                    team.image_url = item.get("image_url", team.image_url)
                    team.region = item.get("location", team.region)
                    updated += 1
                    await db.flush()

                for player_data in item.get("players", []):
                    await _upsert_player(db, player_data, team.id)

            if len(teams_data) < 100:
                break
            page += 1
    except Exception as exc:
        error_msg = str(exc)
        status = IngestionStatus.failed
        logger.error("sync_teams failed", error=error_msg)

    duration_ms = int((time.monotonic() - start) * 1000)
    log = IngestionLog(
        source="pandascore",
        entity_type="team",
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


async def _upsert_player(db: AsyncSession, data: dict, team_id: int) -> None:
    ps_id = str(data.get("id", ""))
    if not ps_id:
        return
    result = await db.execute(select(Player).where(Player.pandascore_id == ps_id))
    player = result.scalar_one_or_none()
    if player is None:
        player = Player(
            pandascore_id=ps_id,
            name=data.get("name", ""),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            role=data.get("role"),
            image_url=data.get("image_url"),
            nationality=data.get("nationality"),
            current_team_id=team_id,
        )
        db.add(player)
    else:
        player.name = data.get("name", player.name)
        player.first_name = data.get("first_name", player.first_name)
        player.last_name = data.get("last_name", player.last_name)
        player.role = data.get("role", player.role)
        player.image_url = data.get("image_url", player.image_url)
        player.nationality = data.get("nationality", player.nationality)
        player.current_team_id = team_id
