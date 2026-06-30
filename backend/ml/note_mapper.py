"""
Map common note names to fragrance family features and build perfume dicts
for notes that are not in notes_chemistry.json.

NOTE_TO_FEATURE: note → {family_dim: strength, ...}
This is used for display/fallback — the actual feature vector is still built
via build_feature_vector() in features.py using notes_chemistry.json lookups.
"""

from typing import Optional

NOTE_TO_FEATURE: dict[str, dict[str, float]] = {
    # citrus
    "bergamot":       {"citrus": 0.9, "fresh": 0.7},
    "lemon":          {"citrus": 0.95, "fresh": 0.8},
    "orange":         {"citrus": 0.85, "fresh": 0.6},
    "grapefruit":     {"citrus": 0.9, "fresh": 0.75},
    "lime":           {"citrus": 0.88, "fresh": 0.8},
    "mandarin":       {"citrus": 0.85, "fresh": 0.65},
    "yuzu":           {"citrus": 0.9, "fresh": 0.7},
    # floral
    "rose":           {"floral": 0.95, "powdery": 0.3},
    "jasmine":        {"floral": 0.9, "white_floral": 0.7},
    "iris":           {"floral": 0.7, "powdery": 0.6},
    "lily":           {"floral": 0.85, "white_floral": 0.5},
    "violet":         {"floral": 0.7, "powdery": 0.5},
    "tuberose":       {"floral": 0.9, "white_floral": 0.8},
    "gardenia":       {"floral": 0.85, "white_floral": 0.7},
    "peony":          {"floral": 0.8, "fresh": 0.3},
    "magnolia":       {"floral": 0.8, "white_floral": 0.4},
    "geranium":       {"floral": 0.7, "green": 0.5},
    "ylang ylang":    {"floral": 0.85, "oriental": 0.4},
    # woody
    "sandalwood":     {"woody": 0.9, "creamy": 0.4},
    "cedar":          {"woody": 0.85, "dry": 0.5},
    "cedarwood":      {"woody": 0.85, "dry": 0.5},
    "oud":            {"woody": 0.95, "resinous": 0.7, "smoky": 0.3},
    "vetiver":        {"woody": 0.8, "earthy": 0.6, "smoky": 0.3},
    "patchouli":      {"woody": 0.7, "earthy": 0.8, "oriental": 0.5},
    "guaiac wood":    {"woody": 0.8, "smoky": 0.5},
    "birch":          {"woody": 0.7, "smoky": 0.6},
    "pine":           {"woody": 0.75, "fresh": 0.5, "green": 0.5},
    # oriental/warm
    "vanilla":        {"oriental": 0.9, "sweet": 0.8, "gourmand": 0.5},
    "amber":          {"oriental": 0.85, "warm": 0.8, "resinous": 0.5},
    "benzoin":        {"oriental": 0.8, "vanilla": 0.6, "resinous": 0.5},
    "tonka":          {"oriental": 0.75, "sweet": 0.7, "gourmand": 0.4},
    "tonka bean":     {"oriental": 0.75, "sweet": 0.7, "gourmand": 0.4},
    "labdanum":       {"oriental": 0.8, "resinous": 0.7, "earthy": 0.3},
    "myrrh":          {"oriental": 0.8, "resinous": 0.8, "smoky": 0.3},
    "frankincense":   {"oriental": 0.75, "resinous": 0.8, "smoky": 0.4},
    "incense":        {"oriental": 0.7, "smoky": 0.7, "resinous": 0.5},
    # musky/base
    "musk":           {"musky": 0.95, "clean": 0.5},
    "white musk":     {"musky": 0.9, "clean": 0.7, "fresh": 0.3},
    "ambergris":      {"musky": 0.8, "marine": 0.4, "warm": 0.5},
    "ambroxan":       {"musky": 0.85, "woody": 0.3, "warm": 0.4},
    "cashmeran":      {"musky": 0.7, "woody": 0.5, "warm": 0.4},
    # fresh/aquatic
    "sea salt":       {"aquatic": 0.9, "fresh": 0.8, "marine": 0.9},
    "water":          {"aquatic": 0.95, "fresh": 0.9},
    "marine":         {"aquatic": 0.9, "fresh": 0.85, "marine": 0.95},
    "ozonic":         {"aquatic": 0.8, "fresh": 0.85},
    "cucumber":       {"aquatic": 0.7, "fresh": 0.8, "green": 0.4},
    "water lily":     {"aquatic": 0.85, "floral": 0.5},
    # spicy
    "pepper":         {"spicy": 0.9, "dry": 0.5},
    "black pepper":   {"spicy": 0.9, "dry": 0.5},
    "cardamom":       {"spicy": 0.8, "warm": 0.5},
    "cinnamon":       {"spicy": 0.85, "warm": 0.7, "gourmand": 0.3},
    "clove":          {"spicy": 0.85, "warm": 0.6},
    "nutmeg":         {"spicy": 0.7, "warm": 0.6},
    "saffron":        {"spicy": 0.8, "oriental": 0.6},
    "ginger":         {"spicy": 0.75, "fresh": 0.3, "warm": 0.4},
    # herbal/aromatic
    "lavender":       {"aromatic": 0.9, "fresh": 0.5, "herbal": 0.7},
    "rosemary":       {"aromatic": 0.8, "herbal": 0.8, "fresh": 0.4},
    "basil":          {"aromatic": 0.75, "herbal": 0.85, "fresh": 0.5},
    "mint":           {"aromatic": 0.8, "fresh": 0.8, "herbal": 0.7},
    "thyme":          {"aromatic": 0.7, "herbal": 0.85},
    "sage":           {"aromatic": 0.75, "herbal": 0.8, "earthy": 0.3},
    "oregano":        {"aromatic": 0.65, "herbal": 0.85},
    # fruity
    "apple":          {"fruity": 0.9, "fresh": 0.5},
    "peach":          {"fruity": 0.85, "sweet": 0.4},
    "pear":           {"fruity": 0.8, "fresh": 0.4},
    "blackcurrant":   {"fruity": 0.85, "sweet": 0.3},
    "raspberry":      {"fruity": 0.85, "sweet": 0.4},
    "strawberry":     {"fruity": 0.8, "sweet": 0.5},
    "plum":           {"fruity": 0.8, "sweet": 0.5, "oriental": 0.2},
    "cherry":         {"fruity": 0.8, "sweet": 0.5},
    "mango":          {"fruity": 0.85, "tropical": 0.6},
    "pineapple":      {"fruity": 0.8, "tropical": 0.7, "fresh": 0.4},
    # gourmand
    "chocolate":      {"gourmand": 0.95, "sweet": 0.8, "oriental": 0.3},
    "caramel":        {"gourmand": 0.9, "sweet": 0.85},
    "coffee":         {"gourmand": 0.8, "smoky": 0.3, "sweet": 0.4},
    "praline":        {"gourmand": 0.85, "sweet": 0.8},
    "honey":          {"gourmand": 0.75, "sweet": 0.7, "floral": 0.3},
    "almond":         {"gourmand": 0.8, "sweet": 0.6},
    "coconut":        {"gourmand": 0.7, "tropical": 0.6, "creamy": 0.5},
    # earthy/green
    "oakmoss":        {"earthy": 0.85, "woody": 0.5, "chypre": 0.7},
    "moss":           {"earthy": 0.8, "green": 0.5},
    "earth":          {"earthy": 0.9, "woody": 0.4},
    "grass":          {"green": 0.9, "fresh": 0.6},
    "hay":            {"earthy": 0.7, "green": 0.5, "dry": 0.5},
    "tobacco":        {"earthy": 0.6, "smoky": 0.5, "warm": 0.5},
    "leather":        {"earthy": 0.5, "smoky": 0.6, "animalic": 0.7},
}

_CONC_NORMALIZE: dict[str, str] = {
    "cologne":   "EDC",
    "edc":       "EDC",
    "edt":       "EDT",
    "edp":       "EDP",
    "parfum":    "Parfum",
    "extrait":   "Extrait",
    "perfume":   "Parfum",
}


def normalize_concentration(raw: str) -> str:
    """Normalize free-text concentration values (e.g. from Gemini) to our canonical set."""
    return _CONC_NORMALIZE.get(raw.lower().strip(), "EDT")


def build_perfume_dict_from_notes(
    name: str,
    brand: str,
    top_notes: list[str],
    middle_notes: list[str],
    base_notes: list[str],
    concentration: str = "EDP",
    family: Optional[str] = None,
) -> dict:
    """
    Build a perfume dict suitable for ml.model.predict() from user-supplied or AI-inferred notes.
    Community vote fields are zeroed — the model falls back to pure chemistry.
    """
    return {
        "name": name,
        "brand": brand,
        "top_notes": [n.strip() for n in top_notes if n.strip()],
        "middle_notes": [n.strip() for n in middle_notes if n.strip()],
        "base_notes": [n.strip() for n in base_notes if n.strip()],
        "concentration": normalize_concentration(concentration),
        "accords": [family.lower().strip()] if family else [],
        "gender_vote": "unisex",
        "community_longevity_rating": 3.0,
        "community_sillage_rating": 3.0,
        "community_overall_rating": 3.0,
        "season_spring_votes": 0,
        "season_summer_votes": 0,
        "season_fall_votes": 0,
        "season_winter_votes": 0,
        "occasion_daily_votes": 0,
        "occasion_evening_votes": 0,
        "occasion_sport_votes": 0,
        "occasion_office_votes": 0,
        "occasion_night_votes": 0,
        "occasion_beach_votes": 0,
        "source_count": 1,
        "rating_count": 0,
        "community_longevity_label": "",
    }
