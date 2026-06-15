"""
Fix inaccurate generic-default values in notes_chemistry.json for specific notes
that were imported from Parfumo with family-template defaults instead of real
chemistry profiles, and add genuinely missing notes.

Run from the backend/ directory:
    python scripts/fix_notes_chemistry.py
"""
import json
from pathlib import Path

NOTES_PATH = Path(__file__).parent.parent / "data" / "notes_chemistry.json"

# Accurate profiles keyed by EXACT note name as stored in the JSON.
ACCURATE_PROFILES: dict[str, dict] = {
    # ── Musk fixatives (not "fresh" family; very long-lasting, skin-bonding) ──
    "muscenone": {
        "family": "musky", "volatility": 2,
        "heat_performance": 7, "cold_performance": 6, "humidity_performance": 7, "dry_performance": 7,
        "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 8,
        "projection_strength": 7, "longevity_class": 5,
    },
    "Muscenone®": {
        "family": "musky", "volatility": 2,
        "heat_performance": 7, "cold_performance": 6, "humidity_performance": 7, "dry_performance": 7,
        "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 8,
        "projection_strength": 7, "longevity_class": 5,
    },
    "ambrocenide": {
        "family": "musky", "volatility": 2,
        "heat_performance": 8, "cold_performance": 7, "humidity_performance": 7, "dry_performance": 8,
        "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 8,
        "projection_strength": 8, "longevity_class": 5,
    },
    "Ambrocenide®": {
        "family": "musky", "volatility": 2,
        "heat_performance": 8, "cold_performance": 7, "humidity_performance": 7, "dry_performance": 8,
        "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 8,
        "projection_strength": 8, "longevity_class": 5,
    },
    # ── Floral synthetics ──
    "paradisone": {
        "family": "floral", "volatility": 4,
        "heat_performance": 6, "cold_performance": 6, "humidity_performance": 6, "dry_performance": 6,
        "skin_bonding": 7, "dry_skin_boost": 7, "oily_skin_boost": 6,
        "projection_strength": 7, "longevity_class": 4,
    },
    "Paradisone®": {
        "family": "floral", "volatility": 4,
        "heat_performance": 6, "cold_performance": 6, "humidity_performance": 6, "dry_performance": 6,
        "skin_bonding": 7, "dry_skin_boost": 7, "oily_skin_boost": 6,
        "projection_strength": 7, "longevity_class": 4,
    },
    # ── Marine/watery synthetics ──
    "cascalone": {
        "family": "aquatic", "volatility": 7,
        "heat_performance": 5, "cold_performance": 5, "humidity_performance": 7, "dry_performance": 5,
        "skin_bonding": 4, "dry_skin_boost": 5, "oily_skin_boost": 4,
        "projection_strength": 7, "longevity_class": 2,
    },
    "Cascalone®": {
        "family": "aquatic", "volatility": 7,
        "heat_performance": 5, "cold_performance": 5, "humidity_performance": 7, "dry_performance": 5,
        "skin_bonding": 4, "dry_skin_boost": 5, "oily_skin_boost": 4,
        "projection_strength": 7, "longevity_class": 2,
    },
    # ── Woody synthetics ──
    "Akigalawood®": {
        "family": "woody", "volatility": 2,
        "heat_performance": 8, "cold_performance": 7, "humidity_performance": 7, "dry_performance": 8,
        "skin_bonding": 9, "dry_skin_boost": 9, "oily_skin_boost": 8,
        "projection_strength": 7, "longevity_class": 5,
    },
    # ── Floral/tropical naturals ──
    "Tiaré": {
        "family": "floral", "volatility": 5,
        "heat_performance": 7, "cold_performance": 5, "humidity_performance": 7, "dry_performance": 6,
        "skin_bonding": 6, "dry_skin_boost": 7, "oily_skin_boost": 5,
        "projection_strength": 7, "longevity_class": 3,
    },
    "Monoï": {
        "family": "fresh", "volatility": 5,
        "heat_performance": 7, "cold_performance": 4, "humidity_performance": 6, "dry_performance": 5,
        "skin_bonding": 5, "dry_skin_boost": 6, "oily_skin_boost": 5,
        "projection_strength": 6, "longevity_class": 3,
    },
    # ── Green tea / herbaceous ──
    "Maté": {
        "family": "green", "volatility": 6,
        "heat_performance": 6, "cold_performance": 6, "humidity_performance": 5, "dry_performance": 6,
        "skin_bonding": 5, "dry_skin_boost": 5, "oily_skin_boost": 4,
        "projection_strength": 5, "longevity_class": 3,
    },
    # ── Gourmand notes ──
    "Praliné": {
        "family": "gourmand", "volatility": 3,
        "heat_performance": 6, "cold_performance": 8, "humidity_performance": 4, "dry_performance": 7,
        "skin_bonding": 8, "dry_skin_boost": 8, "oily_skin_boost": 7,
        "projection_strength": 6, "longevity_class": 4,
    },
    "Dragée": {
        "family": "gourmand", "volatility": 5,
        "heat_performance": 6, "cold_performance": 7, "humidity_performance": 5, "dry_performance": 7,
        "skin_bonding": 6, "dry_skin_boost": 7, "oily_skin_boost": 5,
        "projection_strength": 5, "longevity_class": 3,
    },
}

# Notes that are genuinely absent and need to be added
NEW_NOTES: list[dict] = [
    {
        "name": "Durian",
        "family": "fresh",
        "volatility": 5,
        "heat_performance": 7,
        "cold_performance": 4,
        "humidity_performance": 6,
        "dry_performance": 5,
        "skin_bonding": 5,
        "dry_skin_boost": 6,
        "oily_skin_boost": 5,
        "projection_strength": 8,
        "longevity_class": 3,
    },
    {
        "name": "Cachaça",
        "family": "gourmand",
        "volatility": 9,
        "heat_performance": 5,
        "cold_performance": 4,
        "humidity_performance": 5,
        "dry_performance": 6,
        "skin_bonding": 3,
        "dry_skin_boost": 4,
        "oily_skin_boost": 3,
        "projection_strength": 7,
        "longevity_class": 1,
    },
    {
        "name": "Piña Colada",
        "family": "fresh",
        "volatility": 7,
        "heat_performance": 7,
        "cold_performance": 4,
        "humidity_performance": 7,
        "dry_performance": 5,
        "skin_bonding": 4,
        "dry_skin_boost": 5,
        "oily_skin_boost": 4,
        "projection_strength": 6,
        "longevity_class": 2,
    },
    {
        "name": "Champagne Rosé",
        "family": "fresh",
        "volatility": 9,
        "heat_performance": 5,
        "cold_performance": 5,
        "humidity_performance": 5,
        "dry_performance": 6,
        "skin_bonding": 3,
        "dry_skin_boost": 4,
        "oily_skin_boost": 3,
        "projection_strength": 6,
        "longevity_class": 1,
    },
    {
        "name": "Canelé",
        "family": "gourmand",
        "volatility": 4,
        "heat_performance": 7,
        "cold_performance": 7,
        "humidity_performance": 5,
        "dry_performance": 7,
        "skin_bonding": 7,
        "dry_skin_boost": 8,
        "oily_skin_boost": 6,
        "projection_strength": 6,
        "longevity_class": 4,
    },
    {
        "name": "Crème Brûlée",
        "family": "gourmand",
        "volatility": 4,
        "heat_performance": 7,
        "cold_performance": 7,
        "humidity_performance": 5,
        "dry_performance": 7,
        "skin_bonding": 7,
        "dry_skin_boost": 8,
        "oily_skin_boost": 6,
        "projection_strength": 6,
        "longevity_class": 4,
    },
]


def main() -> None:
    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        notes: list[dict] = json.load(f)

    name_to_idx = {n["name"]: i for i, n in enumerate(notes)}

    updated_count = 0
    for note_name, profile in ACCURATE_PROFILES.items():
        idx = name_to_idx.get(note_name)
        if idx is None:
            print(f"  SKIP (not found): {note_name!r}")
            continue
        old = notes[idx]
        notes[idx] = {**old, **profile}
        updated_count += 1
        print(
            f"  UPDATED {note_name!r}: "
            f"vol {old['volatility']}->{profile['volatility']}  "
            f"long {old['longevity_class']}->{profile['longevity_class']}  "
            f"bond {old['skin_bonding']}->{profile['skin_bonding']}  "
            f"fam {old['family']}->{profile['family']}"
        )

    added_count = 0
    existing_names = {n["name"] for n in notes}
    for new_note in NEW_NOTES:
        if new_note["name"] in existing_names:
            print(f"  SKIP (already exists): {new_note['name']!r}")
        else:
            notes.append(new_note)
            added_count += 1
            print(f"  ADDED: {new_note['name']!r}")

    with open(NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Updated {updated_count} entries, added {added_count} new entries.")
    print(f"Total notes: {len(notes)}")


if __name__ == "__main__":
    main()
