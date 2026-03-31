import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, JSON, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelType(str, enum.Enum):
    winner = "winner"
    kills = "kills"
    duration = "duration"
    combined = "combined"


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    model_type: Mapped[ModelType] = mapped_column(Enum(ModelType), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="model_version")
