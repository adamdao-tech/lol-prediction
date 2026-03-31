from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Team, Match
from app.models.match import MatchStatus
from app.schemas.team import TeamOut, TeamDetail

router = APIRouter()


@router.get("", response_model=list[TeamOut])
async def list_teams(
    db: Annotated[AsyncSession, Depends(get_db)],
    region: str | None = Query(None),
    search: str | None = Query(None),
):
    stmt = select(Team).order_by(Team.name)
    if region:
        stmt = stmt.where(Team.region.ilike(f"%{region}%"))
    if search:
        stmt = stmt.where(
            Team.name.ilike(f"%{search}%") | Team.acronym.ilike(f"%{search}%")
        )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(team_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
