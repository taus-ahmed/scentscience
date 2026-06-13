"""
Expand notes_chemistry.json with all 1478 missing notes.
- High-freq notes get hand-tuned chemistry values
- Remainder get family-based defaults
- Runs idempotent: skips notes already present
"""
import json, sys
from pathlib import Path

NOTES_PATH = Path(__file__).parent.parent / "data" / "notes_chemistry.json"
MISSING_PATH = Path(__file__).parent / "missing_notes.json"

# ─── Family defaults ─────────────────────────────────────────────────────────
FAMILY_DEFAULTS = {
    "citrus":    dict(volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "floral":    dict(volatility=6, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "white_floral": dict(volatility=5, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "woody":     dict(volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "oriental":  dict(volatility=2, heat_performance=8, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "resinous":  dict(volatility=2, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "fresh":     dict(volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "gourmand":  dict(volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "musky":     dict(volatility=3, heat_performance=7, cold_performance=6, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=6, longevity_class=4),
    "green":     dict(volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "aquatic":   dict(volatility=8, heat_performance=6, cold_performance=4, humidity_performance=8, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=6, longevity_class=2),
    "spicy":     dict(volatility=6, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "earthy":    dict(volatility=2, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=5, longevity_class=5),
    "smoky":     dict(volatility=3, heat_performance=6, cold_performance=8, humidity_performance=5, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "animalic":  dict(volatility=2, heat_performance=8, cold_performance=7, humidity_performance=8, dry_performance=8, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=7, longevity_class=5),
    "chypre":    dict(volatility=3, heat_performance=6, cold_performance=8, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "powdery":   dict(volatility=4, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=5, longevity_class=4),
    "fougere":   dict(volatility=5, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=6, projection_strength=6, longevity_class=3),
}

# ─── Hand-tuned entries for high-frequency notes ────────────────────────────
# Format: "note name (lowercase)": {full chemistry dict with "name" key}
HAND_TUNED = {
    # ── Citrus aliases / variants ───────────────────────────────────────────
    "ylang-ylang": dict(name="ylang-ylang", family="floral", volatility=6, heat_performance=7, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "agarwood (oud)": dict(name="agarwood (oud)", family="woody", volatility=1, heat_performance=9, cold_performance=8, humidity_performance=8, dry_performance=9, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=9, longevity_class=5),
    "agarwood": dict(name="agarwood", family="woody", volatility=1, heat_performance=9, cold_performance=8, humidity_performance=8, dry_performance=9, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=9, longevity_class=5),
    "black currant": dict(name="black currant", family="fresh", volatility=8, heat_performance=5, cold_performance=5, humidity_performance=6, dry_performance=7, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "woodsy notes": dict(name="woodsy notes", family="woody", volatility=4, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=5, projection_strength=6, longevity_class=4),
    "virginia cedar": dict(name="virginia cedar", family="woody", volatility=4, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=5, projection_strength=6, longevity_class=4),
    "vanille": dict(name="vanille", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "vanila": dict(name="vanila", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "olibanum": dict(name="olibanum", family="resinous", volatility=3, heat_performance=8, cold_performance=8, humidity_performance=7, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "violet leaf": dict(name="violet leaf", family="floral", volatility=6, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=5, longevity_class=3),
    "oak moss": dict(name="oak moss", family="chypre", volatility=2, heat_performance=6, cold_performance=8, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "moss": dict(name="moss", family="chypre", volatility=3, heat_performance=5, cold_performance=8, humidity_performance=8, dry_performance=6, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "lily of the valley": dict(name="lily of the valley", family="floral", volatility=7, heat_performance=5, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=2),
    "myrhh": dict(name="myrhh", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "myrrh": dict(name="myrrh", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "orris": dict(name="orris", family="floral", volatility=4, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=6, projection_strength=5, longevity_class=4),

    # ── High-freq florals ───────────────────────────────────────────────────
    "peony": dict(name="peony", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "tuberose": dict(name="tuberose", family="floral", volatility=5, heat_performance=7, cold_performance=5, humidity_performance=7, dry_performance=5, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=8, longevity_class=3),
    "magnolia": dict(name="magnolia", family="floral", volatility=6, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "gardenia": dict(name="gardenia", family="floral", volatility=5, heat_performance=7, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "heliotrope": dict(name="heliotrope", family="powdery", volatility=5, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "jasmine sambac": dict(name="jasmine sambac", family="floral", volatility=6, heat_performance=8, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=8, longevity_class=3),
    "lily": dict(name="lily", family="floral", volatility=6, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "carnation": dict(name="carnation", family="spicy", volatility=6, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "mimosa": dict(name="mimosa", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=2),
    "water lily": dict(name="water lily", family="aquatic", volatility=7, heat_performance=6, cold_performance=5, humidity_performance=8, dry_performance=4, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "cyclamen": dict(name="cyclamen", family="floral", volatility=7, heat_performance=5, cold_performance=7, humidity_performance=6, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "honeysuckle": dict(name="honeysuckle", family="floral", volatility=7, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=2),
    "lilac": dict(name="lilac", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=2),
    "osmanthus": dict(name="osmanthus", family="floral", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "hyacinth": dict(name="hyacinth", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=2),
    "cherry blossom": dict(name="cherry blossom", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "frangipani": dict(name="frangipani", family="floral", volatility=5, heat_performance=8, cold_performance=4, humidity_performance=7, dry_performance=4, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "wisteria": dict(name="wisteria", family="floral", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "tiare flower": dict(name="tiare flower", family="floral", volatility=5, heat_performance=8, cold_performance=4, humidity_performance=7, dry_performance=4, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "african orange flower": dict(name="african orange flower", family="floral", volatility=6, heat_performance=7, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "damask rose": dict(name="damask rose", family="floral", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "bulgarian rose": dict(name="bulgarian rose", family="floral", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "turkish rose": dict(name="turkish rose", family="floral", volatility=5, heat_performance=7, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "red rose": dict(name="red rose", family="floral", volatility=5, heat_performance=7, cold_performance=6, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "may rose": dict(name="may rose", family="floral", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "rose de mai": dict(name="rose de mai", family="floral", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "egyptian jasmine": dict(name="egyptian jasmine", family="floral", volatility=6, heat_performance=8, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=8, longevity_class=3),
    "indian jasmine": dict(name="indian jasmine", family="floral", volatility=6, heat_performance=8, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=8, longevity_class=3),
    "white flowers": dict(name="white flowers", family="floral", volatility=6, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "floral notes": dict(name="floral notes", family="floral", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "vanilla orchid": dict(name="vanilla orchid", family="floral", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "peach blossom": dict(name="peach blossom", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "apple blossom": dict(name="apple blossom", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "marigold": dict(name="marigold", family="floral", volatility=6, heat_performance=6, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "hibiscus": dict(name="hibiscus", family="floral", volatility=6, heat_performance=7, cold_performance=4, humidity_performance=7, dry_performance=4, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=2),
    "cotton flower": dict(name="cotton flower", family="floral", volatility=7, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "sweet pea": dict(name="sweet pea", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=2),
    "pink peony": dict(name="pink peony", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "white lily": dict(name="white lily", family="floral", volatility=5, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "wild rose": dict(name="wild rose", family="floral", volatility=6, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "rose water": dict(name="rose water", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=5, longevity_class=2),
    "rose petals": dict(name="rose petals", family="floral", volatility=6, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "iris flower": dict(name="iris flower", family="floral", volatility=4, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=5, longevity_class=4),
    "tuscan iris": dict(name="tuscan iris", family="floral", volatility=4, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=5, longevity_class=4),
    "white iris": dict(name="white iris", family="floral", volatility=4, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=5, longevity_class=4),
    "pink rose": dict(name="pink rose", family="floral", volatility=6, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "rose hip": dict(name="rose hip", family="floral", volatility=6, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=5, longevity_class=3),

    # ── High-freq fruits ────────────────────────────────────────────────────
    "pear": dict(name="pear", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=1),
    "raspberry": dict(name="raspberry", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "litchi": dict(name="litchi", family="fresh", volatility=7, heat_performance=5, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "mango": dict(name="mango", family="fresh", volatility=7, heat_performance=6, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "strawberry": dict(name="strawberry", family="fresh", volatility=8, heat_performance=5, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "red apple": dict(name="red apple", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=1),
    "passionfruit": dict(name="passionfruit", family="fresh", volatility=7, heat_performance=6, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "rhubarb": dict(name="rhubarb", family="fresh", volatility=8, heat_performance=4, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=1),
    "fig": dict(name="fig", family="green", volatility=6, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=5, longevity_class=3),
    "red currant": dict(name="red currant", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "nectarine": dict(name="nectarine", family="fresh", volatility=8, heat_performance=4, cold_performance=7, humidity_performance=7, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "watermelon": dict(name="watermelon", family="aquatic", volatility=8, heat_performance=7, cold_performance=3, humidity_performance=8, dry_performance=4, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=5, longevity_class=1),
    "cherry": dict(name="cherry", family="fresh", volatility=8, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "blueberry": dict(name="blueberry", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "guava": dict(name="guava", family="fresh", volatility=7, heat_performance=7, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "pomelo": dict(name="pomelo", family="citrus", volatility=9, heat_performance=5, cold_performance=4, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "lychee": dict(name="lychee", family="fresh", volatility=7, heat_performance=5, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "red fruits": dict(name="red fruits", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "fruity notes": dict(name="fruity notes", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "fruits": dict(name="fruits", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "tropical fruits": dict(name="tropical fruits", family="fresh", volatility=7, heat_performance=6, cold_performance=4, humidity_performance=7, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "white peach": dict(name="white peach", family="fresh", volatility=8, heat_performance=4, cold_performance=7, humidity_performance=7, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "granny smith apple": dict(name="granny smith apple", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=1),
    "green pear": dict(name="green pear", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=1),
    "sour cherry": dict(name="sour cherry", family="fresh", volatility=8, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "black cherry": dict(name="black cherry", family="fresh", volatility=7, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "wild berries": dict(name="wild berries", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "berry fruits": dict(name="berry fruits", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "boysenberry": dict(name="boysenberry", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "cranberry": dict(name="cranberry", family="fresh", volatility=8, heat_performance=4, cold_performance=7, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "kiwi": dict(name="kiwi", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "quince": dict(name="quince", family="fresh", volatility=8, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "fig tree": dict(name="fig tree", family="green", volatility=6, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=6, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=5, longevity_class=3),
    "plum blossom": dict(name="plum blossom", family="floral", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "dried fruits": dict(name="dried fruits", family="gourmand", volatility=5, heat_performance=5, cold_performance=7, humidity_performance=4, dry_performance=8, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=5, longevity_class=3),

    # ── Citrus variants ─────────────────────────────────────────────────────
    "tangerine": dict(name="tangerine", family="citrus", volatility=9, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "amalfi lemon": dict(name="amalfi lemon", family="citrus", volatility=9, heat_performance=5, cold_performance=4, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "calabrian bergamot": dict(name="calabrian bergamot", family="citrus", volatility=9, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=7, longevity_class=1),
    "sicilian bergamot": dict(name="sicilian bergamot", family="citrus", volatility=9, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=7, longevity_class=1),
    "blood orange": dict(name="blood orange", family="citrus", volatility=9, heat_performance=5, cold_performance=4, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=6, longevity_class=1),
    "bitter orange": dict(name="bitter orange", family="citrus", volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=7, longevity_class=1),
    "yuzu": dict(name="yuzu", family="citrus", volatility=10, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=7, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "citron": dict(name="citron", family="citrus", volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=7, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "clementine": dict(name="clementine", family="citrus", volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "pink grapefruit": dict(name="pink grapefruit", family="citrus", volatility=9, heat_performance=5, cold_performance=4, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "haitian vetiver": dict(name="haitian vetiver", family="earthy", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=5, longevity_class=5),
    "italian lemon": dict(name="italian lemon", family="citrus", volatility=9, heat_performance=5, cold_performance=4, humidity_performance=4, dry_performance=7, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "citruses": dict(name="citruses", family="citrus", volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "sweet orange": dict(name="sweet orange", family="citrus", volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "orange peel": dict(name="orange peel", family="citrus", volatility=9, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=7, longevity_class=1),
    "sicilian mandarin": dict(name="sicilian mandarin", family="citrus", volatility=9, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=6, longevity_class=1),
    "italian mandarin": dict(name="italian mandarin", family="citrus", volatility=9, heat_performance=5, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=6, longevity_class=1),
    "yellow mandarin": dict(name="yellow mandarin", family="citrus", volatility=9, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=6, longevity_class=1),
    "lemon zest": dict(name="lemon zest", family="citrus", volatility=10, heat_performance=4, cold_performance=5, humidity_performance=5, dry_performance=7, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "lemongrass": dict(name="lemongrass", family="citrus", volatility=8, heat_performance=6, cold_performance=4, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=7, longevity_class=2),
    "petitgrain": dict(name="petitgrain", family="citrus", volatility=8, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "tunisian neroli": dict(name="tunisian neroli", family="citrus", volatility=8, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=2),

    # ── Resinous / oriental ─────────────────────────────────────────────────
    "incense": dict(name="incense", family="resinous", volatility=3, heat_performance=8, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=8, longevity_class=4),
    "styrax": dict(name="styrax", family="resinous", volatility=3, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "opoponax": dict(name="opoponax", family="resinous", volatility=2, heat_performance=8, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "tolu balsam": dict(name="tolu balsam", family="resinous", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "balsam fir": dict(name="balsam fir", family="resinous", volatility=4, heat_performance=5, cold_performance=8, humidity_performance=5, dry_performance=8, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=4),
    "castoreum": dict(name="castoreum", family="animalic", volatility=2, heat_performance=7, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=7, longevity_class=5),
    "copal": dict(name="copal", family="resinous", volatility=3, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "resins": dict(name="resins", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "resin": dict(name="resin", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "gurjan balsam": dict(name="gurjan balsam", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "french labdanum": dict(name="french labdanum", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "spanish labdanum": dict(name="spanish labdanum", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "siam benzoin": dict(name="siam benzoin", family="resinous", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "white amber": dict(name="white amber", family="oriental", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "black amber": dict(name="black amber", family="oriental", volatility=2, heat_performance=8, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=8, longevity_class=5),
    "crystal amber": dict(name="crystal amber", family="oriental", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "palo santo": dict(name="palo santo", family="resinous", volatility=3, heat_performance=8, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "immortelle": dict(name="immortelle", family="resinous", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "myrrh oil": dict(name="myrrh oil", family="resinous", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),

    # ── Woody variants ──────────────────────────────────────────────────────
    "palisander rosewood": dict(name="palisander rosewood", family="woody", volatility=4, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "brazilian rosewood": dict(name="brazilian rosewood", family="woody", volatility=4, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "white woods": dict(name="white woods", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=5, longevity_class=4),
    "teak wood": dict(name="teak wood", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "precious woods": dict(name="precious woods", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "exotic woods": dict(name="exotic woods", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "driftwood": dict(name="driftwood", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=7, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=5, longevity_class=4),
    "white wood": dict(name="white wood", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=5, longevity_class=4),
    "dry wood": dict(name="dry wood", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=4, dry_performance=9, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "hinoki wood": dict(name="hinoki wood", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "hinoki": dict(name="hinoki", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "ebony wood": dict(name="ebony wood", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "sequoia": dict(name="sequoia", family="woody", volatility=3, heat_performance=6, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "australian sandalwood": dict(name="australian sandalwood", family="woody", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "mysore sandalwood": dict(name="mysore sandalwood", family="woody", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "sandalowood": dict(name="sandalowood", family="woody", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "sandal": dict(name="sandal", family="woody", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=5),
    "white cedar extract": dict(name="white cedar extract", family="woody", volatility=4, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=5, projection_strength=6, longevity_class=4),
    "moroccan cedar": dict(name="moroccan cedar", family="woody", volatility=4, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "red cedar": dict(name="red cedar", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "texas cedar": dict(name="texas cedar", family="woody", volatility=4, heat_performance=6, cold_performance=6, humidity_performance=4, dry_performance=8, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "himalayan cedar": dict(name="himalayan cedar", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "cedar needles": dict(name="cedar needles", family="woody", volatility=5, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "indian oud": dict(name="indian oud", family="woody", volatility=1, heat_performance=9, cold_performance=8, humidity_performance=8, dry_performance=9, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=9, longevity_class=5),
    "cambodian oud": dict(name="cambodian oud", family="woody", volatility=1, heat_performance=9, cold_performance=8, humidity_performance=8, dry_performance=9, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=9, longevity_class=5),
    "laotian oud": dict(name="laotian oud", family="woody", volatility=1, heat_performance=9, cold_performance=8, humidity_performance=8, dry_performance=9, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=9, longevity_class=5),
    "white oud": dict(name="white oud", family="woody", volatility=1, heat_performance=8, cold_performance=8, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=8, longevity_class=5),
    "vetyver": dict(name="vetyver", family="earthy", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=5, longevity_class=5),
    "bourbon vetiver": dict(name="bourbon vetiver", family="earthy", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=5, longevity_class=5),
    "java vetiver oil": dict(name="java vetiver oil", family="earthy", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=5, longevity_class=5),
    "patchouli leaf": dict(name="patchouli leaf", family="earthy", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=10, dry_skin_boost=9, oily_skin_boost=8, projection_strength=8, longevity_class=5),
    "indonesian patchouli leaf": dict(name="indonesian patchouli leaf", family="earthy", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=10, dry_skin_boost=9, oily_skin_boost=8, projection_strength=8, longevity_class=5),
    "cypriol oil or nagarmotha": dict(name="cypriol oil or nagarmotha", family="earthy", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "oak": dict(name="oak", family="woody", volatility=3, heat_performance=6, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "amyris": dict(name="amyris", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "pine": dict(name="pine", family="woody", volatility=5, heat_performance=5, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "pine tree": dict(name="pine tree", family="woody", volatility=5, heat_performance=5, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "pine needles": dict(name="pine needles", family="woody", volatility=6, heat_performance=4, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "fir": dict(name="fir", family="woody", volatility=5, heat_performance=5, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "cypress": dict(name="cypress", family="woody", volatility=5, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=8, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "blonde woods": dict(name="blonde woods", family="woody", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=5, longevity_class=4),

    # ── Green / herbal ──────────────────────────────────────────────────────
    "galbanum": dict(name="galbanum", family="green", volatility=7, heat_performance=4, cold_performance=7, humidity_performance=6, dry_performance=6, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=7, longevity_class=2),
    "clary sage": dict(name="clary sage", family="green", volatility=6, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=6, longevity_class=3),
    "thyme": dict(name="thyme", family="green", volatility=7, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "petitgrain bigarade": dict(name="petitgrain bigarade", family="citrus", volatility=8, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "grass": dict(name="grass", family="green", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=7, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "ivy": dict(name="ivy", family="green", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=7, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "eucalyptus": dict(name="eucalyptus", family="fresh", volatility=8, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=7, longevity_class=2),
    "wormwood": dict(name="wormwood", family="green", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "angelica": dict(name="angelica", family="green", volatility=6, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=3),
    "green leaves": dict(name="green leaves", family="green", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=7, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "hay": dict(name="hay", family="green", volatility=5, heat_performance=6, cold_performance=7, humidity_performance=4, dry_performance=8, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=5, longevity_class=3),
    "coumarin": dict(name="coumarin", family="fougere", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "tea": dict(name="tea", family="green", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "black tea": dict(name="black tea", family="green", volatility=5, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=5, longevity_class=3),
    "white tea": dict(name="white tea", family="green", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=5, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "mate": dict(name="mate", family="green", volatility=6, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=3),
    "peppermint": dict(name="peppermint", family="fresh", volatility=9, heat_performance=4, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=7, longevity_class=1),
    "fern": dict(name="fern", family="green", volatility=6, heat_performance=4, cold_performance=7, humidity_performance=8, dry_performance=4, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=5, longevity_class=3),
    "vetiver root": dict(name="vetiver root", family="earthy", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=5, longevity_class=5),
    "verbena": dict(name="verbena", family="citrus", volatility=8, heat_performance=6, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=6, longevity_class=1),
    "tomato leaf": dict(name="tomato leaf", family="green", volatility=8, heat_performance=5, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=6, longevity_class=2),
    "herbal notes": dict(name="herbal notes", family="green", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "aromatic notes": dict(name="aromatic notes", family="fougere", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "carrot seeds": dict(name="carrot seeds", family="spicy", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "davana": dict(name="davana", family="spicy", volatility=5, heat_performance=7, cold_performance=5, humidity_performance=5, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "tarragon": dict(name="tarragon", family="green", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "chamomile": dict(name="chamomile", family="floral", volatility=6, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=6, skin_bonding=5, dry_skin_boost=6, oily_skin_boost=4, projection_strength=5, longevity_class=3),

    # ── Aquatic / fresh ─────────────────────────────────────────────────────
    "water notes": dict(name="water notes", family="aquatic", volatility=8, heat_performance=6, cold_performance=4, humidity_performance=8, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "watery notes": dict(name="watery notes", family="aquatic", volatility=8, heat_performance=6, cold_performance=4, humidity_performance=8, dry_performance=5, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "ozonic notes": dict(name="ozonic notes", family="aquatic", volatility=9, heat_performance=5, cold_performance=5, humidity_performance=7, dry_performance=6, skin_bonding=2, dry_skin_boost=3, oily_skin_boost=2, projection_strength=6, longevity_class=1),
    "sea water": dict(name="sea water", family="aquatic", volatility=8, heat_performance=7, cold_performance=4, humidity_performance=9, dry_performance=4, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "seaweed": dict(name="seaweed", family="aquatic", volatility=7, heat_performance=6, cold_performance=5, humidity_performance=8, dry_performance=4, skin_bonding=4, dry_skin_boost=4, oily_skin_boost=4, projection_strength=5, longevity_class=2),
    "marine notes": dict(name="marine notes", family="aquatic", volatility=8, heat_performance=7, cold_performance=4, humidity_performance=8, dry_performance=4, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "solar notes": dict(name="solar notes", family="aquatic", volatility=7, heat_performance=8, cold_performance=3, humidity_performance=7, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=6, longevity_class=2),

    # ── Spicy variants ──────────────────────────────────────────────────────
    "white pepper": dict(name="white pepper", family="spicy", volatility=7, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=2),
    "clove": dict(name="clove", family="spicy", volatility=5, heat_performance=7, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=8, longevity_class=3),
    "anise": dict(name="anise", family="spicy", volatility=7, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=2),
    "cumin": dict(name="cumin", family="spicy", volatility=6, heat_performance=8, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "cassia": dict(name="cassia", family="spicy", volatility=5, heat_performance=7, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "pimento": dict(name="pimento", family="spicy", volatility=6, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "absinthe": dict(name="absinthe", family="green", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=7, longevity_class=2),
    "licorice": dict(name="licorice", family="gourmand", volatility=5, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "red pepper": dict(name="red pepper", family="spicy", volatility=7, heat_performance=7, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=8, longevity_class=2),
    "chili pepper": dict(name="chili pepper", family="spicy", volatility=7, heat_performance=8, cold_performance=5, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=8, longevity_class=2),
    "turmeric": dict(name="turmeric", family="spicy", volatility=5, heat_performance=8, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "marjoram": dict(name="marjoram", family="green", volatility=7, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=6, longevity_class=2),
    "bay leaf": dict(name="bay leaf", family="spicy", volatility=6, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "allspice": dict(name="allspice", family="spicy", volatility=5, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "ceylon cinnamon": dict(name="ceylon cinnamon", family="spicy", volatility=5, heat_performance=7, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "fennel": dict(name="fennel", family="spicy", volatility=7, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=2),
    "mace": dict(name="mace", family="spicy", volatility=6, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "exotic spices": dict(name="exotic spices", family="spicy", volatility=5, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "aromatic spices": dict(name="aromatic spices", family="spicy", volatility=5, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "black cardamom": dict(name="black cardamom", family="spicy", volatility=6, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "guatemalan cardamom": dict(name="guatemalan cardamom", family="spicy", volatility=6, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "cardamon": dict(name="cardamon", family="spicy", volatility=7, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=2),
    "spearmint": dict(name="spearmint", family="fresh", volatility=9, heat_performance=4, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=6, longevity_class=1),

    # ── Gourmand variants ───────────────────────────────────────────────────
    "praline": dict(name="praline", family="gourmand", volatility=3, heat_performance=6, cold_performance=8, humidity_performance=4, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "almond": dict(name="almond", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "bourbon vanilla": dict(name="bourbon vanilla", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "hazelnut": dict(name="hazelnut", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "coffee": dict(name="coffee", family="gourmand", volatility=5, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "rum": dict(name="rum", family="gourmand", volatility=5, heat_performance=7, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "brown sugar": dict(name="brown sugar", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "sweet notes": dict(name="sweet notes", family="gourmand", volatility=5, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=6, longevity_class=3),
    "milk": dict(name="milk", family="gourmand", volatility=5, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=6, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=5, longevity_class=3),
    "powdery notes": dict(name="powdery notes", family="powdery", volatility=4, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=5, projection_strength=5, longevity_class=4),
    "toffee": dict(name="toffee", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "white chocolate": dict(name="white chocolate", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=6, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "marshmallow": dict(name="marshmallow", family="gourmand", volatility=4, heat_performance=5, cold_performance=7, humidity_performance=4, dry_performance=7, skin_bonding=7, dry_skin_boost=8, oily_skin_boost=6, projection_strength=5, longevity_class=3),
    "vanilla absolute": dict(name="vanilla absolute", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "vanilla bean": dict(name="vanilla bean", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "tahitian vanilla": dict(name="tahitian vanilla", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "vanilla pod": dict(name="vanilla pod", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "vanilla flower": dict(name="vanilla flower", family="gourmand", volatility=3, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "indian vanilla": dict(name="indian vanilla", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "tonka": dict(name="tonka", family="gourmand", volatility=2, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=7, longevity_class=5),
    "cacao pod": dict(name="cacao pod", family="gourmand", volatility=5, heat_performance=7, cold_performance=6, humidity_performance=5, dry_performance=6, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "marzipan": dict(name="marzipan", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=4, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=3),
    "coconut milk": dict(name="coconut milk", family="gourmand", volatility=5, heat_performance=7, cold_performance=5, humidity_performance=7, dry_performance=5, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=5, longevity_class=3),
    "pistachio": dict(name="pistachio", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=7, oily_skin_boost=5, projection_strength=5, longevity_class=3),
    "nougat": dict(name="nougat", family="gourmand", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=4, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=5, longevity_class=3),
    "cognac": dict(name="cognac", family="gourmand", volatility=5, heat_performance=7, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),
    "beeswax": dict(name="beeswax", family="gourmand", volatility=3, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=8, dry_skin_boost=9, oily_skin_boost=6, projection_strength=5, longevity_class=4),
    "white honey": dict(name="white honey", family="gourmand", volatility=4, heat_performance=6, cold_performance=6, humidity_performance=4, dry_performance=6, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=5, longevity_class=3),
    "sugar cane": dict(name="sugar cane", family="gourmand", volatility=5, heat_performance=6, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=5, longevity_class=3),
    "whiskey": dict(name="whiskey", family="gourmand", volatility=5, heat_performance=7, cold_performance=6, humidity_performance=4, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=7, longevity_class=3),

    # ── Musky / animalic ────────────────────────────────────────────────────
    "ambrette (musk mallow)": dict(name="ambrette (musk mallow)", family="musky", volatility=3, heat_performance=7, cold_performance=6, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=6, longevity_class=4),
    "ambrette": dict(name="ambrette", family="musky", volatility=3, heat_performance=7, cold_performance=6, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=6, longevity_class=4),
    "suede": dict(name="suede", family="musky", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=5, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "natural musk": dict(name="natural musk", family="musky", volatility=3, heat_performance=7, cold_performance=6, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=6, longevity_class=5),
    "cashmere musk": dict(name="cashmere musk", family="musky", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=5, longevity_class=4),
    "black musk": dict(name="black musk", family="musky", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=7, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "egyptian musk": dict(name="egyptian musk", family="musky", volatility=3, heat_performance=7, cold_performance=6, humidity_performance=7, dry_performance=7, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=6, longevity_class=4),
    "animal notes": dict(name="animal notes", family="animalic", volatility=2, heat_performance=8, cold_performance=7, humidity_performance=8, dry_performance=8, skin_bonding=10, dry_skin_boost=10, oily_skin_boost=9, projection_strength=7, longevity_class=5),
    "black leather": dict(name="black leather", family="smoky", volatility=3, heat_performance=7, cold_performance=8, humidity_performance=5, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=8, longevity_class=5),
    "white suede": dict(name="white suede", family="musky", volatility=4, heat_performance=6, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "russian leather": dict(name="russian leather", family="smoky", volatility=3, heat_performance=6, cold_performance=8, humidity_performance=5, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=5),

    # ── Misc high-freq ──────────────────────────────────────────────────────
    "orange blossom": dict(name="orange blossom", family="floral", volatility=7, heat_performance=7, cold_performance=5, humidity_performance=6, dry_performance=5, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=2),
    "juniper berries": dict(name="juniper berries", family="fresh", volatility=7, heat_performance=5, cold_performance=7, humidity_performance=5, dry_performance=7, skin_bonding=4, dry_skin_boost=5, oily_skin_boost=4, projection_strength=7, longevity_class=2),
    "mineral notes": dict(name="mineral notes", family="fresh", volatility=6, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "earthy notes": dict(name="earthy notes", family="earthy", volatility=3, heat_performance=6, cold_performance=7, humidity_performance=7, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "salt": dict(name="salt", family="aquatic", volatility=7, heat_performance=7, cold_performance=5, humidity_performance=8, dry_performance=4, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=5, longevity_class=2),
    "balsamic notes": dict(name="balsamic notes", family="resinous", volatility=3, heat_performance=7, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "oriental notes": dict(name="oriental notes", family="oriental", volatility=2, heat_performance=8, cold_performance=8, humidity_performance=6, dry_performance=8, skin_bonding=9, dry_skin_boost=9, oily_skin_boost=8, projection_strength=7, longevity_class=5),
    "oriental flower notes": dict(name="oriental flower notes", family="oriental", volatility=4, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=7, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=7, longevity_class=4),
    "metallic notes": dict(name="metallic notes", family="fresh", volatility=7, heat_performance=5, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=3, dry_skin_boost=3, oily_skin_boost=3, projection_strength=6, longevity_class=2),
    "camphor": dict(name="camphor", family="fresh", volatility=8, heat_performance=5, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=3, dry_skin_boost=4, oily_skin_boost=3, projection_strength=7, longevity_class=2),
    "cinammon": dict(name="cinammon", family="spicy", volatility=5, heat_performance=7, cold_performance=8, humidity_performance=5, dry_performance=7, skin_bonding=6, dry_skin_boost=6, oily_skin_boost=5, projection_strength=7, longevity_class=3),
    "cedar essence": dict(name="cedar essence", family="woody", volatility=4, heat_performance=6, cold_performance=6, humidity_performance=5, dry_performance=7, skin_bonding=7, dry_skin_boost=7, oily_skin_boost=6, projection_strength=6, longevity_class=4),
    "cashmirwood": dict(name="cashmirwood", family="woody", volatility=3, heat_performance=7, cold_performance=7, humidity_performance=6, dry_performance=8, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=6, longevity_class=4),
    "peat": dict(name="peat", family="earthy", volatility=3, heat_performance=6, cold_performance=8, humidity_performance=8, dry_performance=6, skin_bonding=8, dry_skin_boost=8, oily_skin_boost=7, projection_strength=5, longevity_class=4),
    "cannabis": dict(name="cannabis", family="green", volatility=6, heat_performance=6, cold_performance=6, humidity_performance=6, dry_performance=6, skin_bonding=5, dry_skin_boost=5, oily_skin_boost=5, projection_strength=7, longevity_class=3),
}


def classify_note(name: str) -> str:
    """Heuristic family classification for unknown notes."""
    n = name.lower()

    # Check specific keywords
    citrus_kw = ["lemon", "lime", "orange", "bergamot", "grapefruit", "mandarin",
                 "tangerine", "citrus", "citron", "yuzu", "neroli", "petitgrain",
                 "clementine", "pomelo", "kumquat", "bigarade", "calamansi"]
    floral_kw = ["rose", "jasmine", "peony", "lily", "flower", "blossom", "orchid",
                 "violet", "iris", "gardenia", "tuberose", "magnolia", "freesia",
                 "wisteria", "honeysuckle", "lilac", "carnation", "cyclamen",
                 "heliotrope", "mimosa", "osmanthus", "frangipani", "hibiscus",
                 "dahlia", "petunia", "narcissus", "hyacinth", "daisy", "tulip",
                 "tiare", "plumeria", "champaca", "lotus", "cherry blossom",
                 "ylang", "floral"]
    woody_kw = ["wood", "cedar", "sandalwood", "vetiver", "birch", "oak", "pine",
                "cypress", "fir", "oud", "agarwood", "ebony", "mahogany",
                "patchouli", "guaiac", "teak", "cashmere wood", "driftwood",
                "sequoia", "hinoki", "palo santo"]
    resinous_kw = ["resin", "balsam", "benzoin", "frankincense", "incense", "olibanum",
                   "myrrh", "labdanum", "cistus", "storax", "copal", "elemi",
                   "styrax", "opoponax", "tolu", "gurjan"]
    gourmand_kw = ["vanilla", "caramel", "chocolate", "honey", "sugar", "praline",
                   "coffee", "almond", "hazelnut", "milk", "cream", "cake", "candy",
                   "cookie", "marzipan", "toffee", "nougat", "rum", "bourbon",
                   "cognac", "whiskey", "biscuit", "caramel", "licorice"]
    fresh_kw = ["apple", "pear", "peach", "berry", "berries", "raspberry", "strawberry",
                "cherry", "mango", "litchi", "lychee", "melon", "watermelon",
                "pineapple", "passion", "blueberry", "cranberry", "guava",
                "kiwi", "plum", "apricot", "quince", "fruit"]
    aquatic_kw = ["water", "marine", "aquatic", "sea", "ocean", "wave", "salt",
                  "ozonic", "seaweed", "algae", "dew", "rain"]
    spicy_kw = ["pepper", "spice", "spicy", "cinnamon", "clove", "cardamom", "ginger",
                "cumin", "saffron", "nutmeg", "anise", "fennel", "allspice", "chili",
                "turmeric", "paprika", "cassia", "mace"]
    green_kw = ["grass", "leaf", "leaves", "green", "herb", "herbal", "fern",
                "moss", "ivy", "thyme", "sage", "basil", "mint", "eucalyptus",
                "bamboo", "tea", "tobacco leaf", "hay", "wormwood"]
    musky_kw = ["musk", "suede", "ambrette", "musken", "cashmere"]
    smoky_kw = ["smoke", "leather", "tobacco", "tar", "birch tar", "oud smoke"]
    earthy_kw = ["earth", "earthy", "vetiver", "patchouli", "soil", "peat", "mushroom",
                 "truffle", "dirt"]

    for kw in citrus_kw:
        if kw in n: return "citrus"
    for kw in resinous_kw:
        if kw in n: return "resinous"
    for kw in earthy_kw:
        if kw in n: return "earthy"
    for kw in smoky_kw:
        if kw in n: return "smoky"
    for kw in musky_kw:
        if kw in n: return "musky"
    for kw in woody_kw:
        if kw in n: return "woody"
    for kw in floral_kw:
        if kw in n: return "floral"
    for kw in gourmand_kw:
        if kw in n: return "gourmand"
    for kw in aquatic_kw:
        if kw in n: return "aquatic"
    for kw in spicy_kw:
        if kw in n: return "spicy"
    for kw in green_kw:
        if kw in n: return "green"
    for kw in fresh_kw:
        if kw in n: return "fresh"

    return "fresh"  # safe neutral default


def make_entry(name: str) -> dict:
    """Generate entry: use hand-tuned if available, else classify + default."""
    key = name.lower().strip()
    if key in HAND_TUNED:
        return HAND_TUNED[key]
    family = classify_note(key)
    defaults = dict(FAMILY_DEFAULTS.get(family, FAMILY_DEFAULTS["fresh"]))
    defaults["name"] = name
    defaults["family"] = family if family not in ("white_floral",) else "floral"
    return defaults


def main():
    with open(NOTES_PATH) as f:
        existing = json.load(f)
    with open(MISSING_PATH) as f:
        missing_data = json.load(f)

    existing_names = {e["name"].lower() for e in existing}
    print(f"Existing entries: {len(existing)}")

    to_add = []
    skipped_alias = 0
    for item in missing_data["missing"]:
        note_name = item["note"]
        # Use title-case name from the hand-tuned dict if available
        key = note_name.lower().strip()
        if key in HAND_TUNED:
            entry = HAND_TUNED[key]
        else:
            entry = make_entry(note_name)
            # Normalise: use the exact casing from the DB
            entry["name"] = note_name

        if entry["name"].lower() in existing_names:
            skipped_alias += 1
            continue

        to_add.append(entry)
        existing_names.add(entry["name"].lower())

    print(f"Skipped (already present): {skipped_alias}")
    print(f"Adding: {len(to_add)}")

    combined = existing + to_add
    with open(NOTES_PATH, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Total entries now: {len(combined)}")
    print(f"Written to {NOTES_PATH}")


if __name__ == "__main__":
    main()
