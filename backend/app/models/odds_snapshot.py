import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum, JSON, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class OddsSource(str, enum.Enum):
    manual_csv = "manual_csv"
    api = "api"


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    bookmaker: Mapped[str] = mapped_column(String(100), nullable=False)
    team1_odds: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    team2_odds: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    implied_prob_team1: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    implied_prob_team2: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    vig: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[OddsSource] = mapped_column(Enum(OddsSource), nullable=False, default=OddsSource.manual_csv)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped["Match"] = relationship("Match", back_populates="odds_snapshots")
