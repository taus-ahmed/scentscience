"""
Brand DNA: per-brand average note-chemistry vectors computed from seed_perfumes.json.

Used as a last-resort fallback when a perfume has no note pyramid and no accord
tags — lets the feature vector reflect the brand's typical chemistry profile
(at 30% weight) rather than staying at neutral 5.0 defaults.

The 10-dimensional prior matches the feature order in features.py:
  [volatility, heat, cold, humidity, dry, skin_bonding, dry_skin_boost,
   oily_skin_boost, projection_strength, longevity_class]
"""

from __future__ import annotations

import json
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

_PRIOR_FIELDS = [
    "volatility", "heat_performance", "cold_performance",
    "humidity_performance", "dry_performance", "skin_bonding",
    "dry_skin_boost", "oily_skin_boost", "projection_strength",
    "longevity_class",
]

_brand_cache: dict[str, np.ndarray] | None = None


def _compute_brand_cache() -> dict[str, np.ndarray]:
    """Compute per-brand chemistry averages from seed_perfumes.json."""
    from ml.features import _get_note

    seed_path = os.path.join(os.path.dirname(__file__), "..", "data", "seed_perfumes.json")
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            perfumes = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("brand_dna: could not load seed_perfumes.json: %s", exc)
        return {}

    brand_vecs: dict[str, list[np.ndarray]] = {}
    for p in perfumes:
        brand = (p.get("brand") or "").lower().strip()
        if not brand:
            continue
        all_notes = (
            (p.get("top_notes") or [])
            + (p.get("middle_notes") or [])
            + (p.get("base_notes") or [])
        )
        if not all_notes:
            continue
        note_vecs: list[np.ndarray] = []
        for name in all_notes:
            note = _get_note(name)
            if note:
                vec = np.array(
                    [float(note.get(f, 5.0)) for f in _PRIOR_FIELDS],
                    dtype=np.float32,
                )
                note_vecs.append(vec)
        if note_vecs:
            brand_vecs.setdefault(brand, []).append(
                np.mean(note_vecs, axis=0).astype(np.float32)
            )

    result: dict[str, np.ndarray] = {}
    for brand, vecs in brand_vecs.items():
        result[brand] = np.mean(vecs, axis=0).astype(np.float32)
    logger.info("brand_dna: computed priors for %d brands", len(result))
    return result


def _load_brand_cache() -> dict[str, np.ndarray]:
    global _brand_cache
    if _brand_cache is None:
        _brand_cache = _compute_brand_cache()
    return _brand_cache


def get_brand_prior(brand: str) -> np.ndarray | None:
    """
    Return the 10-dim average chemistry vector for *brand*, or None if unknown.

    The vector is ordered to match _PRIOR_FIELDS above. Call from features.py
    build_feature_vector() only when notes AND accords are both empty.
    """
    if not brand:
        return None
    cache = _load_brand_cache()
    return cache.get(brand.lower().strip())


def initialize_brand_dna(perfumes: list[dict]) -> None:
    """
    Pre-populate the brand cache from an external list of perfume dicts
    (e.g., all DB perfumes loaded at startup) rather than from seed_perfumes.json.
    Call this once from the model-loading path for richer brand coverage.
    """
    global _brand_cache
    from ml.features import _get_note

    brand_vecs: dict[str, list[np.ndarray]] = {}
    for p in perfumes:
        brand = (p.get("brand") or "").lower().strip()
        if not brand:
            continue
        all_notes = (
            (p.get("top_notes") or [])
            + (p.get("middle_notes") or [])
            + (p.get("base_notes") or [])
        )
        if not all_notes:
            continue
        note_vecs: list[np.ndarray] = []
        for name in all_notes:
            note = _get_note(name)
            if note:
                vec = np.array(
                    [float(note.get(f, 5.0)) for f in _PRIOR_FIELDS],
                    dtype=np.float32,
                )
                note_vecs.append(vec)
        if note_vecs:
            brand_vecs.setdefault(brand, []).append(
                np.mean(note_vecs, axis=0).astype(np.float32)
            )

    result: dict[str, np.ndarray] = {}
    for brand, vecs in brand_vecs.items():
        result[brand] = np.mean(vecs, axis=0).astype(np.float32)
    _brand_cache = result
    logger.info("brand_dna: initialized from %d perfumes, %d brands", len(perfumes), len(result))
