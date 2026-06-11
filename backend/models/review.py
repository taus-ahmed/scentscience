from sqlalchemy import String, Integer, Float, JSON, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.database import Base
from datetime import datetime


class UserReview(Base):
    __tablename__ = "user_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    perfume_id: Mapped[int] = mapped_column(ForeignKey("perfumes.id"), nullable=False)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("prediction_results.id"), nullable=True)
    actual_longevity_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_sillage: Mapped[float | None] = mapped_column(Float, nullable=True)
    skin_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    season_worn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    climate: Mapped[str | None] = mapped_column(String(30), nullable=True)
    satisfaction_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
