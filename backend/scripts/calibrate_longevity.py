"""
Phase 5: Platt/isotonic calibration of longevity_hours on 384 labeled perfumes.

Fits sklearn IsotonicRegression on (predicted_hours, true_label_hours) pairs.
Saves calibrator to ml/models/longevity_calibrator.pkl.
Run from backend/: python scripts/calibrate_longevity.py
"""
import asyncio, sys, pickle
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv; load_dotenv(_env)

import numpy as np
from sqlalchemy import select

from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict, LONGEVITY_LABEL_HOURS
from ml.features import compute_note_coverage

CALIBRATOR_PATH = Path(__file__).parent.parent / "ml" / "models" / "longevity_calibrator.pkl"


def p_dict(p: Perfume) -> dict:
    return {
        "name": p.name, "brand": p.brand,
        "concentration": p.concentration or "EDT",
        "top_notes": p.top_notes or [], "middle_notes": p.middle_notes or [],
        "base_notes": p.base_notes or [], "accords": p.accords or [],
        "gender_vote": p.gender_vote or "unisex",
        "season_spring_votes": p.season_spring_votes or 0,
        "season_summer_votes": p.season_summer_votes or 0,
        "season_fall_votes": p.season_fall_votes or 0,
        "season_winter_votes": p.season_winter_votes or 0,
        "occasion_daily_votes": p.occasion_daily_votes or 0,
        "occasion_evening_votes": p.occasion_evening_votes or 0,
        "occasion_sport_votes": p.occasion_sport_votes or 0,
        "occasion_office_votes": p.occasion_office_votes or 0,
        "occasion_night_votes": p.occasion_night_votes or 0,
        "occasion_beach_votes": p.occasion_beach_votes or 0,
        "community_longevity_rating": p.community_longevity_rating or 3.0,
        "community_sillage_rating": p.community_sillage_rating or 3.0,
        "community_overall_rating": p.community_overall_rating or 3.0,
        "source_count": p.source_count or 1,
        "rating_count": p.rating_count or 0,
        "community_longevity_label": p.community_longevity_label or "",
    }


async def collect_labeled() -> list[tuple[float, float]]:
    """Return (raw_predicted_hours, true_hours) for 384 labeled perfumes.

    Uses skip_calibration=True so the isotonic regression is always fit on
    the raw model output, not on a previously-calibrated value.  Without this,
    re-training a new model and immediately re-calibrating would compose two
    calibrators and produce a mismatch at inference time.
    """
    await init_db()
    models = load_models()
    if not models:
        raise RuntimeError("No trained models found — run test_model.py first.")

    pairs = []
    async with AsyncSessionLocal() as s:
        q = await s.execute(
            select(Perfume).where(Perfume.community_longevity_label.isnot(None))
        )
        labeled = q.scalars().all()

    print(f"Labeled perfumes loaded: {len(labeled)}")

    for p in labeled:
        pd = p_dict(p)
        true_hours = LONGEVITY_LABEL_HOURS.get((pd["community_longevity_label"] or "").lower().strip())
        if true_hours is None:
            continue
        # skip_calibration=True: get raw model output, not any prior calibration
        raw = predict(pd, models, skip_calibration=True)
        pred_hours = float(raw.get("longevity_hours", 5.5))
        pairs.append((pred_hours, true_hours))

    return pairs


def fit_calibrator(pairs: list[tuple[float, float]]):
    from sklearn.isotonic import IsotonicRegression
    xs = np.array([p for p, _ in pairs], dtype=np.float64)
    ys = np.array([t for _, t in pairs], dtype=np.float64)

    # Sort by predicted value (required by IsotonicRegression fit order)
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]

    ir = IsotonicRegression(out_of_bounds="clip", increasing=True)
    ir.fit(xs, ys)

    # Diagnostics
    preds = ir.predict(xs)
    mae = np.mean(np.abs(preds - ys))
    print(f"Calibrator fit MAE: {mae:.3f}h  (on {len(xs)} samples)")
    print(f"Input range:  {xs.min():.2f}h — {xs.max():.2f}h")
    print(f"Output range: {ir.predict([xs.min()])[0]:.2f}h — {ir.predict([xs.max()])[0]:.2f}h")
    return ir


def main():
    pairs = asyncio.run(collect_labeled())
    print(f"Collected {len(pairs)} (predicted, true) pairs")

    if len(pairs) < 20:
        print("Not enough labeled pairs to calibrate — aborting.")
        return

    ir = fit_calibrator(pairs)
    CALIBRATOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CALIBRATOR_PATH, "wb") as f:
        pickle.dump(ir, f)
    print(f"Calibrator saved: {CALIBRATOR_PATH}")


if __name__ == "__main__":
    main()
