import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class MatchStatus(str, enum.Enum):
    scheduled = "scheduled"
    running = "running"
    finished = "finished"
    cancelled = "cancelled"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    pandascore_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    tournament_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=True, index=True
    )
    team1_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    team2_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), nullable=False, default=MatchStatus.scheduled
    )
    number_of_games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    patch_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="matches")
    team1: Mapped["Team"] = relationship("Team", foreign_keys=[team1_id])
    team2: Mapped["Team"] = relationship("Team", foreign_keys=[team2_id])
    winner: Mapped["Team"] = relationship("Team", foreign_keys=[winner_id])
    games: Mapped[list["Game"]] = relationship("Game", back_populates="match")
    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="match")
    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship("OddsSnapshot", back_populates="match")
