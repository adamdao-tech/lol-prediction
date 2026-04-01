from pydantic import BaseModel


class LiveSignals(BaseModel):
    gold_diff: int
    tower_diff: int
    baron_diff: int
    kill_diff: int
    dragon_diff: int
    inhibitor_diff: int


class LivePredictionOut(BaseModel):
    game_id: str
    win_prob_blue: float
    win_prob_red: float
    signals: LiveSignals
    blue_dragons: list[str]
    red_dragons: list[str]
    blue_total_kills: int
    red_total_kills: int
    blue_total_gold: int
    red_total_gold: int
    game_state: str  # "in_game" | "finished" | "unknown"
    frame_timestamp: str | None = None
    game_timer_seconds: int = 0
    game_timer: str = "00:00"
    blue_towers: int = 0
    red_towers: int = 0
    blue_barons: int = 0
    red_barons: int = 0


class LiveWindowOut(BaseModel):
    game_id: str
    prediction: LivePredictionOut | None = None
    raw_participants_blue: list[dict] = []
    raw_participants_red: list[dict] = []
    game_state: str
    prob_history: list[float] = []
    game_timer_seconds: int = 0
