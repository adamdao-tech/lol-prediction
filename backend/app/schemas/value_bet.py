from pydantic import BaseModel, ConfigDict


class ValueBetDetail(BaseModel):
    implied_prob: float
    edge: float
    is_value: bool
    kelly_stake_pct: float
    expected_value: float


class ValueBetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    match_id: int
    team1_name: str
    team2_name: str
    model_prob_team1: float
    model_prob_team2: float
    odds_team1: float | None = None
    odds_team2: float | None = None
    value_team1: ValueBetDetail | None = None
    value_team2: ValueBetDetail | None = None
    scheduled_at: str | None = None
