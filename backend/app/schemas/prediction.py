from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    model_version_id: int
    predicted_winner_id: int | None = None
    win_prob_team1: float
    win_prob_team2: float
    predicted_total_kills: float | None = None
    predicted_duration_seconds: int | None = None
    confidence_score: float | None = None
    draft_adjusted: bool
    created_at: datetime
