from fastapi import APIRouter
from app.api.endpoints import matches, teams, leagues, predictions, odds, admin, live, value_bets

router = APIRouter()
router.include_router(matches.router, prefix="/matches", tags=["matches"])
router.include_router(teams.router, prefix="/teams", tags=["teams"])
router.include_router(leagues.router, prefix="/leagues", tags=["leagues"])
router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
router.include_router(odds.router, prefix="/odds", tags=["odds"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(live.router, prefix="/live", tags=["live"])
router.include_router(value_bets.router, prefix="/value-bets", tags=["value-bets"])
