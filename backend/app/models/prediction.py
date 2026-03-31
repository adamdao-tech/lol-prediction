from datetime import datetime
from sqlalchemy import DateTime, Integer, ForeignKey, Boolean, JSON, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    model_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_versions.id"), nullable=False, index=True
    )
    predicted_winner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    win_prob_team1: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    win_prob_team2: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    predicted_total_kills: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    predicted_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)
    draft_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    features_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped["Match"] = relationship("Match", back_populates="predictions")
    model_version: Mapped["ModelVersion"] = relationship("ModelVersion", back_populates="predictions")
    predicted_winner: Mapped["Team"] = relationship("Team", foreign_keys=[predicted_winner_id])
