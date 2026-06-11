from sqlalchemy import String, Integer, Float, JSON, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.database import Base
from datetime import datetime


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    perfume_id: Mapped[int] = mapped_column(ForeignKey("perfumes.id"), nullable=False)
    input_context: Mapped[dict] = mapped_column(JSON, default=dict)

    # Performance
    proj_1hr: Mapped[float] = mapped_column(Float, default=0.0)
    proj_3hr: Mapped[float] = mapped_column(Float, default=0.0)
    proj_6hr: Mapped[float] = mapped_column(Float, default=0.0)
    proj_8hr: Mapped[float] = mapped_column(Float, default=0.0)
    longevity_hours: Mapped[float] = mapped_column(Float, default=0.0)
    sillage_score: Mapped[float] = mapped_column(Float, default=0.0)
    performance_peak_hour: Mapped[float] = mapped_column(Float, default=1.0)
    dry_down_character: Mapped[str] = mapped_column(Text, default="")
    heat_amplification: Mapped[float] = mapped_column(Float, default=5.0)

    # Environmental
    season_spring: Mapped[float] = mapped_column(Float, default=0.0)
    season_summer: Mapped[float] = mapped_column(Float, default=0.0)
    season_fall: Mapped[float] = mapped_column(Float, default=0.0)
    season_winter: Mapped[float] = mapped_column(Float, default=0.0)
    climate_tropical: Mapped[float] = mapped_column(Float, default=0.0)
    climate_arid: Mapped[float] = mapped_column(Float, default=0.0)
    climate_temperate: Mapped[float] = mapped_column(Float, default=0.0)
    climate_cold: Mapped[float] = mapped_column(Float, default=0.0)
    temp_optimal_min_c: Mapped[float] = mapped_column(Float, default=10.0)
    temp_optimal_max_c: Mapped[float] = mapped_column(Float, default=25.0)
    humidity_performance: Mapped[float] = mapped_column(Float, default=5.0)
    indoor_score: Mapped[float] = mapped_column(Float, default=5.0)
    outdoor_score: Mapped[float] = mapped_column(Float, default=5.0)
    time_morning: Mapped[float] = mapped_column(Float, default=0.0)
    time_afternoon: Mapped[float] = mapped_column(Float, default=0.0)
    time_evening: Mapped[float] = mapped_column(Float, default=0.0)
    time_night: Mapped[float] = mapped_column(Float, default=0.0)

    # Person fit
    skin_dry_score: Mapped[float] = mapped_column(Float, default=5.0)
    skin_oily_score: Mapped[float] = mapped_column(Float, default=5.0)
    skin_combo_score: Mapped[float] = mapped_column(Float, default=5.0)
    age_18_25: Mapped[float] = mapped_column(Float, default=5.0)
    age_25_35: Mapped[float] = mapped_column(Float, default=5.0)
    age_35_50: Mapped[float] = mapped_column(Float, default=5.0)
    age_50_plus: Mapped[float] = mapped_column(Float, default=5.0)
    gender_masculine: Mapped[float] = mapped_column(Float, default=5.0)
    gender_feminine: Mapped[float] = mapped_column(Float, default=5.0)
    gender_unisex: Mapped[float] = mapped_column(Float, default=5.0)
    personality_dominant: Mapped[float] = mapped_column(Float, default=5.0)
    personality_intellectual: Mapped[float] = mapped_column(Float, default=5.0)
    personality_casual: Mapped[float] = mapped_column(Float, default=5.0)
    personality_romantic: Mapped[float] = mapped_column(Float, default=5.0)

    # Occasion
    occ_office: Mapped[float] = mapped_column(Float, default=5.0)
    occ_date: Mapped[float] = mapped_column(Float, default=5.0)
    occ_casual: Mapped[float] = mapped_column(Float, default=5.0)
    occ_formal: Mapped[float] = mapped_column(Float, default=5.0)
    occ_sport: Mapped[float] = mapped_column(Float, default=5.0)
    occ_travel: Mapped[float] = mapped_column(Float, default=5.0)
    social_distance: Mapped[str] = mapped_column(String(20), default="personal")

    # Value
    cost_per_wear_score: Mapped[float] = mapped_column(Float, default=5.0)
    versatility_score: Mapped[float] = mapped_column(Float, default=5.0)
    compliment_score: Mapped[float] = mapped_column(Float, default=5.0)
    blind_buy_score: Mapped[float] = mapped_column(Float, default=5.0)

    # Geo
    geo_tropical_cities: Mapped[list] = mapped_column(JSON, default=list)
    geo_arid_cities: Mapped[list] = mapped_column(JSON, default=list)
    geo_cold_cities: Mapped[list] = mapped_column(JSON, default=list)
    geo_temperate_cities: Mapped[list] = mapped_column(JSON, default=list)

    nlp_conclusion: Mapped[str] = mapped_column(Text, default="")
    instagram_brief: Mapped[str] = mapped_column(Text, default="")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    model_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    perfume: Mapped["Perfume"] = relationship(back_populates="predictions")
