from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.team import TeamOut
from app.schemas.prediction import PredictionOut


class TournamentInMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str | None = None
    league: "LeagueInMatch | None" = None


class LeagueInMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    region: str | None = None


TournamentInMatch.model_rebuild()


class OddsSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bookmaker: str
    team1_odds: float
    team2_odds: float
    implied_prob_team1: float
    implied_prob_team2: float
    vig: float | None = None
    snapshot_at: datetime


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_number: int
    status: str
    duration_seconds: int | None = None
    total_kills: int | None = None
    team1_kills: int | None = None
    team2_kills: int | None = None
    winner_id: int | None = None
    pandascore_id: str | None = None
    lol_esports_game_id: str | None = None


class MatchListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pandascore_id: str
    team1: TeamOut | None = None
    team2: TeamOut | None = None
    scheduled_at: datetime | None = None
    status: str
    number_of_games: int | None = None
    tournament: TournamentInMatch | None = None
    latest_prediction: "PredictionOut | None" = None
    latest_odds: OddsSnapshotOut | None = None
    live_game_id: str | None = None


class MatchOut(MatchListItem):
    patch_version: str | None = None
    winner_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MatchDetail(MatchOut):
    games: list[GameOut] = []
    predictions: list["PredictionOut"] = []
    odds_snapshots: list[OddsSnapshotOut] = []
