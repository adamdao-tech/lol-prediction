from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import League
from app.schemas.league import LeagueOut

router = APIRouter()


@router.get("", response_model=list[LeagueOut])
async def list_leagues(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(League).order_by(League.name))
    return result.scalars().all()
