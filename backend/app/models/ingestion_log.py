import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class IngestionStatus(str, enum.Enum):
    success = "success"
    partial = "partial"
    failed = "failed"


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[IngestionStatus] = mapped_column(Enum(IngestionStatus), nullable=False)
    records_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
