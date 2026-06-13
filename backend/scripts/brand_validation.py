"""
Broad confidence + longevity validation across 30 iconic perfumes.

Picks well-known perfumes from top brands, runs the model, and compares
predicted longevity buckets to community consensus (from DB labels where
present, from curated fragrance knowledge otherwise).

Usage:
    cd backend/
    python scripts/brand_validation.py
"""

import asyncio
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)

from sqlalchemy import select
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict
from ml.validators import validate_predictions
from ml.features import compute_note_coverage


# ── Target perfumes ───────────────────────────────────────────────────────────
# (brand_substr, name_substr, prefer_concentration, expected_bucket, notes)
# expected_bucket: "light" | "moderate" | "strong"
# Sources: Fragrantica community longevity polls + broad fragrance-community consensus

TARGETS = [
    # brand,                name_substr,              conc,   expected,   note
    ("chanel",        "coco mademoiselle",             "EDT",  "moderate", "5-8h community avg"),
    ("chanel",        "bleu de chanel eau de parfum",  "EDT",  "strong",   "renamed EDP in DB; 8-12h"),
    ("chanel",        "chanel no 5 parfum",            None,   "strong",   "parfum extract; 12h+"),
    ("chanel",        "chance eau tendre",             "EDT",  "moderate", "fresh floral; 5-7h"),
    ("dior",          "sauvage",                       "EDT",  "moderate", "EDT variant; 6-10h variable"),
    ("dior",          "sauvage",                       "EDP",  "strong",   "EDP Very Strong label in DB"),
    ("dior",          "j adore",                       "EDT",  "moderate", "5-7h, moderate community vote"),
    ("dior",          "hypnotic poison",               "EDT",  "strong",   "8-12h, very tenacious"),
    ("yves saint",    "black opium",                   "EDT",  "strong",   "Strong label in DB"),
    ("yves saint",    "libre",                         "EDT",  "strong",   "Strong label in DB"),
    ("yves saint",    "la nuit de l homme",            "EDT",  "moderate", "5-8h, fresh oriental"),
    ("tom ford",      "black orchid",                  "EDT",  "strong",   "Very Strong label; oud/patchouli"),
    ("tom ford",      "tobacco vanille",               "EDT",  "strong",   "Strong label; 10-14h"),
    ("tom ford",      "oud wood",                      "EDP",  "strong",   "Strong label; oud base"),
    ("tom ford",      "lost cherry",                   "EDT",  "strong",   "Strong label; gourmand cherry"),
    ("creed",         "aventus",                       "EDP",  "strong",   "Strong label; batch variable 6-10h"),
    ("creed",         "green irish tweed",             "EDT",  "moderate", "Medium label; clean fougere 5-7h"),
    ("creed",         "silver mountain water",         "EDT",  "moderate", "Medium label; 4-6h lighter"),
    ("versace",       "eros",                          "EDT",  "strong",   "Strong label; 8-12h beast mode"),
    ("versace",       "crystal noir",                  "EDT",  "moderate", "Medium label; 5-7h floral"),
    ("versace",       "bright crystal",                "EDT",  "moderate", "Medium label; 4-6h fresh floral"),
    ("gucci",         "gucci bloom",                   "EDT",  "moderate", "No label; 5-7h white floral"),
    ("prada",         "prada candy",                   "EDT",  "moderate", "No label; sweet gourmand 6-9h"),
    ("prada",         "luna rossa carbon",             "EDT",  "moderate", "No label; fresh aromatic 5-7h"),
    ("hermes",        "terre d hermes",                "EDT",  "moderate", "No label; woody citrus 5-8h"),
    ("jo malone",     "peony blush suede",             "EDT",  "light",    "No label; Jo Malone known for 2-4h"),
    ("jo malone",     "english pear",                  "EDT",  "light",    "No label; 2-4h fresh, light"),
    ("armani",        "acqua di gio",                  "EDT",  "moderate", "Medium label; 5-7h aquatic"),
    ("armani",        "si",                            "EDT",  "strong",   "Strong label; 8-10h EDP"),
    ("givenchy",      "l interdit",                    "EDT",  "moderate", "No label; 6-9h white floral"),
    ("mugler",        "angel",                         "EDT",  "strong",   "No label; iconic 8-12h oriental"),
    ("mugler",        "alien",                         "EDT",  "strong",   "No label; beast mode 12h+ jasmine"),
    ("lancome",       "la vie est belle",              "EDT",  "strong",   "No label; 8-10h gourmand"),
    ("lancome",       "la nuit tresor",                "EDT",  "strong",   "No label; 8-12h oriental"),
]


def hours_to_bucket(h: float) -> str:
    if h >= 8.0:
        return "strong"
    if h >= 4.0:
        return "moderate"
    return "light"


def bucket_match(predicted: str, expected: str) -> str:
    if predicted == expected:
        return "YES"
    # adjacent buckets (light<->moderate, moderate<->strong)
    adjacency = {("light", "moderate"), ("moderate", "light"),
                 ("moderate", "strong"), ("strong", "moderate")}
    if (predicted, expected) in adjacency:
        return "CLOSE"
    return "MISS"


async def find_perfume(
    session,
    brand_substr: str,
    name_substr: str,
    prefer_conc: str | None,
) -> Perfume | None:
    """Find the best-matching DB record for a target."""
    from rapidfuzz import fuzz

    q = await session.execute(
        select(Perfume)
        .where(Perfume.brand.ilike(f"%{brand_substr}%"))
        .where(Perfume.name.ilike(f"%{name_substr}%"))
        .order_by(Perfume.source_count.desc(), Perfume.rating_count.desc().nullslast())
        .limit(10)
    )
    candidates = q.scalars().all()
    if not candidates:
        return None

    if prefer_conc:
        conc_match = [c for c in candidates if c.concentration == prefer_conc]
        if conc_match:
            return conc_match[0]

    return candidates[0]


def perfume_to_dict(p: Perfume) -> dict:
    return {
        "name": p.name,
        "brand": p.brand,
        "concentration": p.concentration or "EDT",
        "top_notes": p.top_notes or [],
        "middle_notes": p.middle_notes or [],
        "base_notes": p.base_notes or [],
        "accords": p.accords or [],
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


async def run_validation() -> None:
    await init_db()
    models = load_models()
    if not models:
        print("ERROR: No trained models found. Run scripts/test_model.py first.")
        sys.exit(1)
    print(f"Models loaded: {list(models.keys())}")

    results = []

    async with AsyncSessionLocal() as session:
        for (brand_s, name_s, pref_conc, expected_bucket, consensus_note) in TARGETS:
            p = await find_perfume(session, brand_s, name_s, pref_conc)
            if p is None:
                results.append({
                    "brand": brand_s.title(), "name": name_s.title(),
                    "found": False, "expected": expected_bucket,
                })
                continue

            pd = perfume_to_dict(p)
            raw = predict(pd, models)

            has_pyramid = bool(pd["top_notes"] or pd["middle_notes"] or pd["base_notes"])
            coverage = compute_note_coverage(pd["top_notes"], pd["middle_notes"], pd["base_notes"])
            total_cv = sum(
                pd.get(k, 0) or 0 for k in (
                    "season_spring_votes", "season_summer_votes",
                    "season_fall_votes", "season_winter_votes",
                    "occasion_daily_votes", "occasion_evening_votes",
                    "occasion_sport_votes", "occasion_office_votes",
                    "occasion_night_votes", "occasion_beach_votes",
                )
            )
            res = validate_predictions(
                raw,
                source_count=pd["source_count"],
                has_pyramid=has_pyramid,
                has_inferred_pyramid=bool(p.has_inferred_pyramid),
                note_coverage=coverage,
                rating_count=pd["rating_count"],
                total_community_votes=total_cv,
            )

            long_h = res["longevity_hours"]
            pred_bucket = hours_to_bucket(long_h)
            match = bucket_match(pred_bucket, expected_bucket)

            # Community label: use DB label if present, else the target's consensus note
            db_label = p.community_longevity_label or ""
            if db_label:
                community_ref = db_label
            else:
                community_ref = f"~{expected_bucket} (consensus)"

            rc = pd["rating_count"]
            if rc <= 0:
                rating_mult = 0.80
            else:
                lf = min(1.0, max(0.0, (math.log10(rc) - 1.0) / 3.0))
                rating_mult = 0.85 + 0.35 * lf

            results.append({
                "found": True,
                "brand": p.brand,
                "name": p.name,
                "conc": p.concentration or "?",
                "pred_hours": long_h,
                "pred_bucket": pred_bucket,
                "expected": expected_bucket,
                "match": match,
                "confidence": res["confidence_score"],
                "community_ref": community_ref,
                "sc": pd["source_count"],
                "rc": rc,
                "pyr": "real" if (has_pyramid and not p.has_inferred_pyramid) else ("infer" if p.has_inferred_pyramid else "none"),
                "rating_mult": rating_mult,
                "consensus_note": consensus_note,
            })

    # ── Print table ───────────────────────────────────────────────────────────

    print("\n" + "=" * 130)
    print("BRAND VALIDATION — 30 ICONIC PERFUMES")
    print("=" * 130)

    col_w = {"brand": 18, "name": 32, "c": 5, "ph": 6, "pb": 8, "exp": 8,
             "m": 5, "conf": 6, "sc": 3, "rc": 7, "pyr": 5, "ref": 20}

    hdr = (
        f"{'Brand':<{col_w['brand']}}  {'Name':<{col_w['name']}}  "
        f"{'Conc':<{col_w['c']}}  {'Hrs':>{col_w['ph']}}  "
        f"{'Pred':<{col_w['pb']}}  {'Expect':<{col_w['exp']}}  "
        f"{'OK?':<{col_w['m']}}  {'Conf':>{col_w['conf']}}  "
        f"{'SC':>{col_w['sc']}}  {'RC':>{col_w['rc']}}  "
        f"{'Pyr':<{col_w['pyr']}}  {'Community Ref':<{col_w['ref']}}"
    )
    print(hdr)
    print("-" * 130)

    yes_count = close_count = miss_count = not_found = 0

    failures = []
    for r in results:
        if not r["found"]:
            not_found += 1
            print(f"  [NOT FOUND] {r['brand'].title()} — {r['name'].title()}")
            continue

        match_sym = {"YES": "YES  ", "CLOSE": "CLOSE", "MISS": "MISS "}[r["match"]]
        if r["match"] == "YES":
            yes_count += 1
        elif r["match"] == "CLOSE":
            close_count += 1
        else:
            miss_count += 1
            failures.append(r)

        name_trunc = r["name"][:col_w["name"]]
        ref_trunc = r["community_ref"][:col_w["ref"]]
        print(
            f"{r['brand']:<{col_w['brand']}}  {name_trunc:<{col_w['name']}}  "
            f"{r['conc']:<{col_w['c']}}  {r['pred_hours']:>{col_w['ph']}.1f}h  "
            f"{r['pred_bucket']:<{col_w['pb']}}  {r['expected']:<{col_w['exp']}}  "
            f"{match_sym}  {r['confidence']:>{col_w['conf']}.3f}  "
            f"{r['sc']:>{col_w['sc']}}  {r['rc']:>{col_w['rc']}}  "
            f"{r['pyr']:<{col_w['pyr']}}  {ref_trunc}"
        )

    total_found = yes_count + close_count + miss_count
    print("-" * 130)
    print(f"\nRESULTS:  YES={yes_count}  CLOSE={close_count}  MISS={miss_count}  NOT_FOUND={not_found}")
    print(f"Accuracy (YES+CLOSE) / found = {(yes_count + close_count)}/{total_found} = "
          f"{(yes_count + close_count) / total_found * 100:.1f}%")
    print(f"Strict accuracy (YES only)   = {yes_count}/{total_found} = "
          f"{yes_count / total_found * 100:.1f}%")

    # ── Confidence distribution ───────────────────────────────────────────────
    found_results = [r for r in results if r["found"]]
    confs = [r["confidence"] for r in found_results]
    avg_conf = sum(confs) / len(confs) if confs else 0

    conf_buckets = {
        "0.97 (cap)": sum(1 for c in confs if c >= 0.97),
        "0.90-0.97":  sum(1 for c in confs if 0.90 <= c < 0.97),
        "0.80-0.90":  sum(1 for c in confs if 0.80 <= c < 0.90),
        "0.70-0.80":  sum(1 for c in confs if 0.70 <= c < 0.80),
        "<0.70":       sum(1 for c in confs if c < 0.70),
    }
    print(f"\nCONFIDENCE DISTRIBUTION (n={len(confs)}):")
    print(f"  Average: {avg_conf:.3f}")
    for bucket, cnt in conf_buckets.items():
        bar = "#" * cnt
        print(f"  {bucket:>12}  {bar:<20}  {cnt}")

    # ── Failure analysis ──────────────────────────────────────────────────────
    if failures:
        print(f"\nMISS ANALYSIS ({len(failures)} failures):")
        print("-" * 80)

        # Group by direction
        over_pred = [f for f in failures if f["pred_bucket"] == "strong" and f["expected"] in ("light", "moderate")]
        under_pred = [f for f in failures if f["pred_bucket"] == "light" and f["expected"] in ("moderate", "strong")]
        moderate_miss = [f for f in failures if
                         (f["pred_bucket"] == "moderate" and f["expected"] == "strong") or
                         (f["pred_bucket"] == "moderate" and f["expected"] == "light")]

        if over_pred:
            print("\n  OVER-PREDICTED (predicted strong, expected lower):")
            for f in over_pred:
                print(f"    {f['brand']} {f['name'][:30]} | {f['pred_hours']:.1f}h → {f['pred_bucket']} (expected {f['expected']}) | {f['consensus_note']}")

        if under_pred:
            print("\n  UNDER-PREDICTED (predicted light, expected higher):")
            for f in under_pred:
                print(f"    {f['brand']} {f['name'][:30]} | {f['pred_hours']:.1f}h → {f['pred_bucket']} (expected {f['expected']}) | {f['consensus_note']}")

        if moderate_miss:
            print("\n  MODERATE MISSES (predicted moderate, expected strong or light):")
            for f in moderate_miss:
                print(f"    {f['brand']} {f['name'][:30]} | {f['pred_hours']:.1f}h → {f['pred_bucket']} (expected {f['expected']}) | {f['consensus_note']}")

        # Pattern analysis
        miss_sc = [f["sc"] for f in failures]
        miss_pyr = [f["pyr"] for f in failures]
        miss_rc = [f["rc"] for f in failures]

        print(f"\n  FAILURE PATTERNS:")
        print(f"    source_count distribution: {sorted(miss_sc)}")
        print(f"    pyramid type distribution: {miss_pyr}")
        print(f"    avg rating_count of failures: {sum(miss_rc)/len(miss_rc):.0f} (all set: {sum(r['rc'] for r in found_results)/len(found_results):.0f})")

        # Brand pattern
        from collections import Counter
        miss_brands = Counter(f["brand"] for f in failures)
        print(f"    brands with most misses: {miss_brands.most_common(5)}")

        # Concentration pattern
        miss_conc = Counter(f["conc"] for f in failures)
        print(f"    concentration of failures: {miss_conc}")

    # ── SC tier summary ───────────────────────────────────────────────────────
    print(f"\nCONFIDENCE BY SOURCE_COUNT TIER:")
    for sc_val in sorted(set(r["sc"] for r in found_results)):
        tier = [r for r in found_results if r["sc"] == sc_val]
        tier_confs = [r["confidence"] for r in tier]
        tier_acc = sum(1 for r in tier if r["match"] == "YES") / len(tier) * 100
        print(f"  sc={sc_val}: n={len(tier)}  avg_conf={sum(tier_confs)/len(tier_confs):.3f}  "
              f"strict_acc={tier_acc:.0f}%  names={[r['name'][:20] for r in tier]}")


if __name__ == "__main__":
    asyncio.run(run_validation())
