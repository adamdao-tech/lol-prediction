import enum
from datetime import datetime
from sqlalchemy import DateTime, Integer, ForeignKey, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DraftSource(str, enum.Enum):
    api = "api"
    manual = "manual"
    ocr = "ocr"


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    blue_bans: Mapped[list | None] = mapped_column(JSON, nullable=True)
    red_bans: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blue_picks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    red_picks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source: Mapped[DraftSource] = mapped_column(Enum(DraftSource), nullable=False, default=DraftSource.api)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    game: Mapped["Game"] = relationship("Game", back_populates="drafts")
