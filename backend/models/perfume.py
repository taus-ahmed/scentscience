from sqlalchemy import String, Integer, Float, JSON, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.database import Base
from datetime import datetime


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(50), nullable=False)
    volatility: Mapped[float] = mapped_column(Float, default=5.0)
    heat_performance: Mapped[float] = mapped_column(Float, default=5.0)
    cold_performance: Mapped[float] = mapped_column(Float, default=5.0)
    humidity_performance: Mapped[float] = mapped_column(Float, default=5.0)
    dry_performance: Mapped[float] = mapped_column(Float, default=5.0)
    skin_bonding: Mapped[float] = mapped_column(Float, default=5.0)
    dry_skin_boost: Mapped[float] = mapped_column(Float, default=5.0)
    oily_skin_boost: Mapped[float] = mapped_column(Float, default=5.0)
    projection_strength: Mapped[float] = mapped_column(Float, default=5.0)
    longevity_class: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    perfume_notes: Mapped[list["PerfumeNote"]] = relationship(back_populates="note")


class Perfume(Base):
    __tablename__ = "perfumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    concentration: Mapped[str] = mapped_column(String(20), default="EDT")
    fragrantica_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fragrantica_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    top_notes: Mapped[list] = mapped_column(JSON, default=list)
    middle_notes: Mapped[list] = mapped_column(JSON, default=list)
    base_notes: Mapped[list] = mapped_column(JSON, default=list)
    accords: Mapped[list] = mapped_column(JSON, default=list)
    gender_vote: Mapped[str] = mapped_column(String(20), default="unisex")
    season_spring_votes: Mapped[int] = mapped_column(Integer, default=0)
    season_summer_votes: Mapped[int] = mapped_column(Integer, default=0)
    season_fall_votes: Mapped[int] = mapped_column(Integer, default=0)
    season_winter_votes: Mapped[int] = mapped_column(Integer, default=0)
    occasion_daily_votes: Mapped[int] = mapped_column(Integer, default=0)
    occasion_evening_votes: Mapped[int] = mapped_column(Integer, default=0)
    occasion_sport_votes: Mapped[int] = mapped_column(Integer, default=0)
    occasion_office_votes: Mapped[int] = mapped_column(Integer, default=0)
    occasion_night_votes: Mapped[int] = mapped_column(Integer, default=0)
    occasion_beach_votes: Mapped[int] = mapped_column(Integer, default=0)
    community_longevity_rating: Mapped[float] = mapped_column(Float, default=3.0)
    community_sillage_rating: Mapped[float] = mapped_column(Float, default=3.0)
    community_overall_rating: Mapped[float] = mapped_column(Float, default=3.0)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    community_longevity_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_inferred_pyramid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    perfume_notes: Mapped[list["PerfumeNote"]] = relationship(back_populates="perfume")
    predictions: Mapped[list["PredictionResult"]] = relationship(back_populates="perfume")


class PerfumeNote(Base):
    __tablename__ = "perfume_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    perfume_id: Mapped[int] = mapped_column(ForeignKey("perfumes.id"), nullable=False)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), nullable=False)
    position: Mapped[str] = mapped_column(String(10), default="middle")  # top/middle/base

    perfume: Mapped["Perfume"] = relationship(back_populates="perfume_notes")
    note: Mapped["Note"] = relationship(back_populates="perfume_notes")
