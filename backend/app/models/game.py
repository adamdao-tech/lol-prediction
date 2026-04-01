import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class GameStatus(str, enum.Enum):
    not_started = "not_started"
    running = "running"
    finished = "finished"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    pandascore_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    lol_esports_game_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    game_number: Mapped[int] = mapped_column(Integer, nullable=False)
    team1_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    team2_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    winner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    blue_side_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    red_side_team_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_kills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team1_kills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team2_kills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus), nullable=False, default=GameStatus.not_started
    )
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    match: Mapped["Match"] = relationship("Match", back_populates="games")
    team1: Mapped["Team"] = relationship("Team", foreign_keys=[team1_id])
    team2: Mapped["Team"] = relationship("Team", foreign_keys=[team2_id])
    winner: Mapped["Team"] = relationship("Team", foreign_keys=[winner_id])
    blue_side_team: Mapped["Team"] = relationship("Team", foreign_keys=[blue_side_team_id])
    red_side_team: Mapped["Team"] = relationship("Team", foreign_keys=[red_side_team_id])
    drafts: Mapped[list["Draft"]] = relationship("Draft", back_populates="game")
