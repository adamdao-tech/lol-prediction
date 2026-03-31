import csv
import io
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Match, OddsSnapshot
from app.models.odds_snapshot import OddsSource

router = APIRouter()


@router.post("/import")
async def import_odds_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Import odds from CSV file.
    Expected columns: match_pandascore_id,bookmaker,team1_odds,team2_odds,snapshot_at
    """
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded CSV")

    reader = csv.DictReader(io.StringIO(text))
    required = {"match_pandascore_id", "bookmaker", "team1_odds", "team2_odds", "snapshot_at"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must have columns: {', '.join(sorted(required))}",
        )

    inserted = 0
    errors = []
    for i, row in enumerate(reader):
        try:
            ps_id = row["match_pandascore_id"].strip()
            bookmaker = row["bookmaker"].strip()
            team1_odds = float(row["team1_odds"])
            team2_odds = float(row["team2_odds"])
            snapshot_at_raw = row["snapshot_at"].strip()

            result = await db.execute(select(Match).where(Match.pandascore_id == ps_id))
            match = result.scalar_one_or_none()
            if match is None:
                errors.append(f"Row {i + 2}: match '{ps_id}' not found")
                continue

            implied1 = 1.0 / team1_odds if team1_odds else 0
            implied2 = 1.0 / team2_odds if team2_odds else 0
            total_implied = implied1 + implied2
            vig = total_implied - 1.0 if total_implied > 0 else None

            snapshot_at = datetime.fromisoformat(snapshot_at_raw.replace("Z", "+00:00"))
            if snapshot_at.tzinfo is None:
                snapshot_at = snapshot_at.replace(tzinfo=timezone.utc)

            snap = OddsSnapshot(
                match_id=match.id,
                bookmaker=bookmaker,
                team1_odds=team1_odds,
                team2_odds=team2_odds,
                implied_prob_team1=implied1,
                implied_prob_team2=implied2,
                vig=vig,
                snapshot_at=snapshot_at,
                source=OddsSource.manual_csv,
            )
            db.add(snap)
            inserted += 1
        except Exception as exc:
            errors.append(f"Row {i + 2}: {exc}")

    await db.flush()
    return {"inserted": inserted, "errors": errors}
