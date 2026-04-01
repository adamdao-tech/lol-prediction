"""
GET /api/v1/value-bets

Vrátí seznam nadcházejících zápasů, pro které existují:
- predikce modelu (tabulka predictions)
- odds snapshot (tabulka odds_snapshots)

A vypočítá value bet analýzu.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Match, Prediction, Team
from app.models.match import MatchStatus
from app.models.odds_snapshot import OddsSnapshot
from app.prediction.value_bet import compute_value_bet
from app.schemas.value_bet import ValueBetOut, ValueBetDetail

router = APIRouter()


@router.get("", response_model=list[ValueBetOut])
async def list_value_bets(
    db: AsyncSession = Depends(get_db),
    min_edge: float = Query(0.04, ge=0.0, le=1.0, description="Minimální edge (default 4%)"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Vrátí nadcházející zápasy s value bet příležitostmi.
    Seřazeno podle edge sestupně.
    """
    # Načti scheduled matches s predikcemi
    result = await db.execute(
        select(Match)
        .where(Match.status == MatchStatus.scheduled)
        .options(
            selectinload(Match.team1),
            selectinload(Match.team2),
        )
        .order_by(Match.scheduled_at.asc())
        .limit(200)
    )
    matches = result.scalars().all()

    if not matches:
        return []

    match_ids = [m.id for m in matches]

    # Načti nejnovější predikce pro tyto zápasy
    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.match_id.in_(match_ids))
        .order_by(Prediction.created_at.desc())
    )
    predictions = pred_result.scalars().all()
    pred_by_match: dict[int, Prediction] = {}
    for p in predictions:
        if p.match_id not in pred_by_match:
            pred_by_match[p.match_id] = p

    # Načti nejnovější odds pro tyto zápasy (pole jsou team1_odds, team2_odds, snapshot_at)
    odds_result = await db.execute(
        select(OddsSnapshot)
        .where(OddsSnapshot.match_id.in_(match_ids))
        .order_by(OddsSnapshot.snapshot_at.desc())
    )
    odds_list = odds_result.scalars().all()
    odds_by_match: dict[int, OddsSnapshot] = {}
    for o in odds_list:
        if o.match_id not in odds_by_match:
            odds_by_match[o.match_id] = o

    output: list[ValueBetOut] = []

    for match in matches:
        pred = pred_by_match.get(match.id)
        odds = odds_by_match.get(match.id)

        if not pred:
            continue

        model_prob1 = float(pred.win_prob_team1) if pred.win_prob_team1 is not None else 0.5
        model_prob2 = float(pred.win_prob_team2) if pred.win_prob_team2 is not None else (1.0 - model_prob1)

        odds_t1 = None
        odds_t2 = None
        value_t1 = None
        value_t2 = None

        if odds:
            odds_t1 = float(odds.team1_odds) if odds.team1_odds is not None else None
            odds_t2 = float(odds.team2_odds) if odds.team2_odds is not None else None

            if odds_t1 and odds_t1 > 1.0:
                vb1 = compute_value_bet(model_prob1, odds_t1)
                value_t1 = ValueBetDetail(**vb1)

            if odds_t2 and odds_t2 > 1.0:
                vb2 = compute_value_bet(model_prob2, odds_t2)
                value_t2 = ValueBetDetail(**vb2)

        # Filtruj: alespoň jeden team musí mít edge >= min_edge (pokud chceme filtrovat)
        has_value = (
            (value_t1 and value_t1.edge >= min_edge) or
            (value_t2 and value_t2.edge >= min_edge) or
            (min_edge == 0.0)  # bez filtru vrať vše s predikcí
        )

        if not has_value:
            continue

        team1_name = match.team1.name if match.team1 else f"Team {match.team1_id}"
        team2_name = match.team2.name if match.team2 else f"Team {match.team2_id}"

        output.append(ValueBetOut(
            match_id=match.id,
            team1_name=team1_name,
            team2_name=team2_name,
            model_prob_team1=round(model_prob1, 4),
            model_prob_team2=round(model_prob2, 4),
            odds_team1=odds_t1,
            odds_team2=odds_t2,
            value_team1=value_t1,
            value_team2=value_t2,
            scheduled_at=match.scheduled_at.isoformat() if match.scheduled_at else None,
        ))

    # Seřaď podle max edge sestupně
    def max_edge(item: ValueBetOut) -> float:
        edges = []
        if item.value_team1:
            edges.append(item.value_team1.edge)
        if item.value_team2:
            edges.append(item.value_team2.edge)
        return max(edges) if edges else 0.0

    output.sort(key=max_edge, reverse=True)
    return output[:limit]
