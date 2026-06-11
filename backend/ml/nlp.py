import os
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are ScentScience, a data-driven fragrance analyst. You receive ML model prediction \
scores for a perfume and convert them into an expert analysis paragraph and Instagram video talking points. \
Be specific, use exact numbers from the scores, be confident and authoritative. Never be vague."""


def _format_scores(perfume_name: str, brand: str, predictions: dict) -> str:
    return f"""
Perfume: {brand} {perfume_name}

PERFORMANCE
- Projection at 1h: {predictions.get('proj_1hr', 0):.1f}/10
- Projection at 3h: {predictions.get('proj_3hr', 0):.1f}/10
- Projection at 6h: {predictions.get('proj_6hr', 0):.1f}/10
- Longevity: {predictions.get('longevity_hours', 0):.1f} hours
- Sillage: {predictions.get('sillage_score', 0):.1f}/10
- Dry down: {predictions.get('dry_down_character', 'N/A')}

SEASONS (out of 10)
- Spring: {predictions.get('season_spring', 0):.1f}  Summer: {predictions.get('season_summer', 0):.1f}
- Fall: {predictions.get('season_fall', 0):.1f}  Winter: {predictions.get('season_winter', 0):.1f}

CLIMATE
- Tropical: {predictions.get('climate_tropical', 0):.1f}  Arid: {predictions.get('climate_arid', 0):.1f}
- Temperate: {predictions.get('climate_temperate', 0):.1f}  Cold: {predictions.get('climate_cold', 0):.1f}
- Optimal temp: {predictions.get('temp_optimal_min_c', 0):.0f}°C – {predictions.get('temp_optimal_max_c', 0):.0f}°C

OCCASIONS
- Office: {predictions.get('occ_office', 0):.1f}  Date: {predictions.get('occ_date', 0):.1f}  Casual: {predictions.get('occ_casual', 0):.1f}
- Formal: {predictions.get('occ_formal', 0):.1f}  Sport: {predictions.get('occ_sport', 0):.1f}  Travel: {predictions.get('occ_travel', 0):.1f}
- Social distance: {predictions.get('social_distance', 'personal')}

PERSON FIT
- Skin: Dry {predictions.get('skin_dry_score', 0):.1f} / Oily {predictions.get('skin_oily_score', 0):.1f} / Combo {predictions.get('skin_combo_score', 0):.1f}
- Age fit: 18-25: {predictions.get('age_18_25', 0):.1f}  25-35: {predictions.get('age_25_35', 0):.1f}  35-50: {predictions.get('age_35_50', 0):.1f}  50+: {predictions.get('age_50_plus', 0):.1f}
- Gender: Masc {predictions.get('gender_masculine', 0):.1f} / Fem {predictions.get('gender_feminine', 0):.1f} / Unisex {predictions.get('gender_unisex', 0):.1f}

VALUE
- Versatility: {predictions.get('versatility_score', 0):.1f}/10
- Compliment score: {predictions.get('compliment_score', 0):.1f}/10
- Blind buy score: {predictions.get('blind_buy_score', 0):.1f}/10
- Cost per wear: {predictions.get('cost_per_wear_score', 0):.1f}/10
""".strip()


async def generate_nlp_conclusion(
    perfume_name: str, brand: str, predictions: dict
) -> tuple[str, str]:
    """Returns (nlp_conclusion, instagram_brief)."""
    api_key = settings.anthropic_api_key
    if not api_key:
        return _fallback_conclusion(perfume_name, brand, predictions), _fallback_instagram(perfume_name, brand, predictions)

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)

        scores_text = _format_scores(perfume_name, brand, predictions)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"""Based on these ML prediction scores, generate:

1. NLP_CONCLUSION: A 3-4 sentence expert analysis paragraph. Be specific with numbers. Explain the performance profile, ideal user, and best use case.

2. INSTAGRAM_BRIEF: Exactly 5 bullet points for a fragrance review video. Each bullet must reference a specific score or prediction from the data.

Format your response EXACTLY as:
NLP_CONCLUSION:
[your paragraph]

INSTAGRAM_BRIEF:
• [point 1]
• [point 2]
• [point 3]
• [point 4]
• [point 5]

Scores:
{scores_text}"""
                }
            ]
        )

        text = message.content[0].text
        nlp_part = ""
        ig_part = ""

        if "NLP_CONCLUSION:" in text and "INSTAGRAM_BRIEF:" in text:
            parts = text.split("INSTAGRAM_BRIEF:")
            nlp_raw = parts[0].replace("NLP_CONCLUSION:", "").strip()
            ig_raw = parts[1].strip()
            nlp_part = nlp_raw
            ig_part = ig_raw
        else:
            nlp_part = text[:500]
            ig_part = text[500:]

        return nlp_part.strip(), ig_part.strip()

    except Exception as e:
        print(f"Claude API error: {e}")
        return _fallback_conclusion(perfume_name, brand, predictions), _fallback_instagram(perfume_name, brand, predictions)


def _fallback_conclusion(perfume_name: str, brand: str, predictions: dict) -> str:
    long_h = predictions.get("longevity_hours", 6)
    sil = predictions.get("sillage_score", 5)
    best_season = max(
        [("Spring", predictions.get("season_spring", 5)),
         ("Summer", predictions.get("season_summer", 5)),
         ("Fall", predictions.get("season_fall", 5)),
         ("Winter", predictions.get("season_winter", 5))],
        key=lambda x: x[1]
    )[0]
    best_occ = max(
        [("office", predictions.get("occ_office", 5)),
         ("date nights", predictions.get("occ_date", 5)),
         ("casual wear", predictions.get("occ_casual", 5)),
         ("formal events", predictions.get("occ_formal", 5))],
        key=lambda x: x[1]
    )[0]
    return (
        f"{brand} {perfume_name} projects a sillage of {sil:.1f}/10 and lasts approximately "
        f"{long_h:.1f} hours on skin. The model rates it highest for {best_season} wear, "
        f"making it a strong choice for {best_occ}. "
        f"Versatility score of {predictions.get('versatility_score', 5):.1f}/10 indicates "
        f"{'broad' if predictions.get('versatility_score', 5) > 6 else 'moderate'} occasion range."
    )


def _fallback_instagram(perfume_name: str, brand: str, predictions: dict) -> str:
    return f"""• Longevity: {predictions.get('longevity_hours', 6):.1f} hours — {
        'beast mode performer' if predictions.get('longevity_hours', 6) > 8 else 'solid daily wear'
    }
• Sillage {predictions.get('sillage_score', 5):.1f}/10 — {
        'crowd-filling projection' if predictions.get('sillage_score', 5) > 7 else 'personal aura scent'
    }
• Best season: peaks at {max(
        [('Spring', predictions.get('season_spring', 5)),
         ('Summer', predictions.get('season_summer', 5)),
         ('Fall', predictions.get('season_fall', 5)),
         ('Winter', predictions.get('season_winter', 5))],
        key=lambda x: x[1]
    )[0]} {max(
        [('Spring', predictions.get('season_spring', 5)),
         ('Summer', predictions.get('season_summer', 5)),
         ('Fall', predictions.get('season_fall', 5)),
         ('Winter', predictions.get('season_winter', 5))],
        key=lambda x: x[1]
    )[1]:.1f}/10
• Blind buy score: {predictions.get('blind_buy_score', 5):.1f}/10 — {
        'safe to blind buy' if predictions.get('blind_buy_score', 5) > 6.5 else 'sample first'
    }
• Compliment factor: {predictions.get('compliment_score', 5):.1f}/10 — {
        'head-turner' if predictions.get('compliment_score', 5) > 7 else 'subtle signature'
    }"""
