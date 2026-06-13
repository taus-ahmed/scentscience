"""
Full model performance audit.

Sections:
  1. Diverse prediction table (real pyramid vs inferred, sc1/2/3+, families)
  2. Longevity-label accuracy on 384 ground-truth perfumes
  3. MAE on longevity_hours vs label midpoints
  4. Weakness report
"""

import sys
import asyncio
import statistics
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)

from sqlalchemy import select, text
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict, LONGEVITY_LABEL_HOURS
from ml.validators import validate_predictions

# ── label helpers ─────────────────────────────────────────────────────────────

LABEL_MIDPOINTS = LONGEVITY_LABEL_HOURS   # from model.py

def label_to_midpoint(label: str) -> float | None:
    if not label:
        return None
    return LABEL_MIDPOINTS.get(label.lower().strip())

def hours_to_bucket(h: float) -> str:
    if h >= 8.0:
        return "strong"
    if h >= 4.0:
        return "moderate"
    return "light"

def label_to_bucket(label: str) -> str:
    lk = label.lower().strip()
    if lk in ("very strong", "strong", "medium-strong", "medium–strong"):
        return "strong"
    if lk in ("light", "weak"):
        return "light"
    return "moderate"   # medium, moderate, light-medium

# ── perfume dict ──────────────────────────────────────────────────────────────

def p_dict(p: Perfume) -> dict:
    return {
        "name": p.name, "brand": p.brand,
        "concentration": p.concentration or "EDT",
        "top_notes": p.top_notes or [], "middle_notes": p.middle_notes or [],
        "base_notes": p.base_notes or [], "accords": p.accords or [],
        "gender_vote": p.gender_vote or "unisex",
        "season_spring_votes": p.season_spring_votes or 0,
        "season_summer_votes": p.season_summer_votes or 0,
        "season_fall_votes":   p.season_fall_votes or 0,
        "season_winter_votes": p.season_winter_votes or 0,
        "occasion_daily_votes":   p.occasion_daily_votes or 0,
        "occasion_evening_votes": p.occasion_evening_votes or 0,
        "occasion_sport_votes":   p.occasion_sport_votes or 0,
        "occasion_office_votes":  p.occasion_office_votes or 0,
        "occasion_night_votes":   p.occasion_night_votes or 0,
        "occasion_beach_votes":   p.occasion_beach_votes or 0,
        "community_longevity_rating": p.community_longevity_rating or 3.0,
        "community_sillage_rating":   p.community_sillage_rating or 3.0,
        "community_overall_rating":   p.community_overall_rating or 3.0,
        "source_count": p.source_count or 1,
        "community_longevity_label": p.community_longevity_label or "",
    }

def run_predict(p: Perfume, models: dict) -> dict:
    pd = p_dict(p)
    raw = predict(pd, models)
    has_pyr = bool(pd["top_notes"] or pd["middle_notes"] or pd["base_notes"])
    return validate_predictions(raw, source_count=pd["source_count"], has_pyramid=has_pyr), pd, has_pyr


# ── section 1: diverse prediction table ──────────────────────────────────────

DIVERSE_TARGETS = [
    # (brand_kw, name_kw, description)
    ("dior",          "sauvage",         "Sauvage EDT — woody aromatic, sc=2, real pyr"),
    ("chanel",        "no 5",            "Chanel No.5 — floral aldehyde, sc=2, real pyr"),
    ("creed",         "aventus",         "Aventus — fruity chypre, sc=2, real pyr"),
    ("giorgio armani","acqua di gio",    "Acqua di Gio — fresh aquatic, sc=2, real pyr"),
    ("yves saint laurent", "black opium","Black Opium — oriental gourmand, sc=2, real pyr"),
    ("guerlain",      "shalimar",        "Shalimar — oriental, sc>=2, real pyr"),
    ("versace",       "eros",            "Versace Eros — fresh fougere, sc>=2, real pyr"),
    ("tom ford",      "oud wood",        "Oud Wood — woody oriental, sc>=2, real pyr"),
    ("jo malone",     "lime basil",      "Jo Malone Lime Basil — citrus, sc>=2, real pyr"),
    ("mugler",         "angel",          "Angel — oriental gourmand, sc>=2, real pyr"),
]

async def fetch_diverse(session, all_perfumes: list[Perfume]) -> list[tuple[str, Perfume]]:
    found = []
    used_ids: set[int] = set()
    for brand_kw, name_kw, desc in DIVERSE_TARGETS:
        best = None
        for p in all_perfumes:
            if p.id in used_ids:
                continue
            if (brand_kw in p.brand.lower() or p.brand.lower() in brand_kw) and \
               (name_kw in p.name.lower() or p.name.lower() in name_kw):
                # Prefer real pyramid + highest source_count
                if best is None:
                    best = p
                elif (not best.has_inferred_pyramid and p.has_inferred_pyramid):
                    pass
                elif (best.has_inferred_pyramid and not p.has_inferred_pyramid):
                    best = p
                elif p.source_count > best.source_count:
                    best = p
        if best:
            found.append((desc, best))
            used_ids.add(best.id)

    # Fill with diversity if short
    families_wanted = [
        ("woody",    lambda p: any("wood" in a.lower() for a in (p.accords or []))),
        ("citrus",   lambda p: any("citrus" in a.lower() for a in (p.accords or []))),
        ("floral",   lambda p: any("floral" in a.lower() or "rose" in a.lower() for a in (p.accords or []))),
        ("oriental", lambda p: any("amber" in a.lower() or "oriental" in a.lower() for a in (p.accords or []))),
        ("inferred", lambda p: p.has_inferred_pyramid),
        ("sc=1",     lambda p: p.source_count == 1),
        ("sc=3+",    lambda p: p.source_count >= 3),
    ]
    for label, filt in families_wanted:
        if len(found) >= 15:
            break
        for p in sorted(all_perfumes, key=lambda x: x.community_overall_rating or 0, reverse=True):
            if p.id in used_ids and not (label in ("inferred", "sc=1", "sc=3+")):
                continue
            if p.id in used_ids:
                continue
            if filt(p):
                found.append((f"[{label}] {p.brand} {p.name}", p))
                used_ids.add(p.id)
                break

    return found


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    await init_db()
    models = load_models()
    print("Models loaded:", list(models.keys()))

    async with AsyncSessionLocal() as session:

        # ── load all perfumes (needed for diverse fetch) ───────────────────────
        print("Loading all perfumes... (this takes a moment)")
        all_rows = (await session.execute(select(Perfume))).scalars().all()
        print(f"  {len(all_rows):,} perfumes loaded.\n")

        # ── SECTION 1 ─────────────────────────────────────────────────────────
        print("=" * 90)
        print("SECTION 1 — DIVERSE PREDICTION TABLE")
        print("=" * 90)

        diverse = await fetch_diverse(session, all_rows)

        # Table header
        hdr = (f"{'Perfume':<42} {'SC':>3} {'Pyr':>4} {'Infer':>5} "
               f"{'Long':>5} {'Sill':>5} {'BB':>5} {'Vers':>5} {'Conf':>6}  Family/notes")
        print(f"\n{hdr}")
        print("-" * 110)

        for desc, p in diverse:
            res, pd, has_pyr = run_predict(p, models)
            label_str = "real" if (has_pyr and not p.has_inferred_pyramid) else \
                        "inf"  if p.has_inferred_pyramid else "none"
            name_trunc = f"{p.brand[:14]} / {p.name[:22]}"
            accords_short = ", ".join((p.accords or [])[:3])
            print(
                f"  {name_trunc:<42} {pd['source_count']:>3}  {has_pyr!s:>4}  {p.has_inferred_pyramid!s:>5}  "
                f"{res['longevity_hours']:>4.1f}  {res['sillage_score']:>4.1f}  "
                f"{res['blind_buy_score']:>4.1f}  {res['versatility_score']:>4.1f}  "
                f"{res['confidence_score']:>5.3f}  {accords_short}"
            )

        # ── SECTION 2: Longevity-label accuracy ───────────────────────────────
        print("\n\n" + "=" * 90)
        print("SECTION 2 — LONGEVITY LABEL ACCURACY (384 ground-truth perfumes)")
        print("NOTE: model was TRAINED with 50/50 label blend — accuracy is upper-bound estimate")
        print("=" * 90)

        labeled = [p for p in all_rows if p.community_longevity_label]
        print(f"\n  Ground-truth perfumes with longevity label: {len(labeled)}")

        label_dist: dict[str, int] = defaultdict(int)
        for p in labeled:
            label_dist[p.community_longevity_label] += 1
        print("  Label distribution in ground-truth set:")
        for lab, cnt in sorted(label_dist.items(), key=lambda x: -x[1]):
            print(f"    {lab:<20} {cnt:>4}  ({cnt/len(labeled)*100:.1f}%)")

        # Predict all labeled perfumes
        exact_match = 0    # predicted bucket == ground-truth bucket
        strong_hits = 0; strong_total = 0
        moderate_hits = 0; moderate_total = 0
        light_hits    = 0; light_total    = 0
        confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        mae_vals: list[float] = []
        errors_by_bucket: dict[str, list[float]] = defaultdict(list)

        for p in labeled:
            res, pd_data, has_pyr = run_predict(p, models)
            pred_h  = res["longevity_hours"]
            gt_mid  = label_to_midpoint(p.community_longevity_label)
            if gt_mid is not None:
                mae_vals.append(abs(pred_h - gt_mid))
                errors_by_bucket[label_to_bucket(p.community_longevity_label)].append(pred_h - gt_mid)

            pred_bucket = hours_to_bucket(pred_h)
            true_bucket = label_to_bucket(p.community_longevity_label)
            confusion[true_bucket][pred_bucket] += 1
            if pred_bucket == true_bucket:
                exact_match += 1
            if true_bucket == "strong":
                strong_total += 1
                if pred_bucket == "strong":
                    strong_hits += 1
            elif true_bucket == "moderate":
                moderate_total += 1
                if pred_bucket == "moderate":
                    moderate_hits += 1
            else:
                light_total += 1
                if pred_bucket == "light":
                    light_hits += 1

        n = len(labeled)
        print(f"\n  Overall bucket accuracy: {exact_match}/{n} = {exact_match/n*100:.1f}%")
        print(f"  Strong  recall: {strong_hits}/{strong_total}   = {strong_hits/max(strong_total,1)*100:.1f}%")
        print(f"  Moderate recall: {moderate_hits}/{moderate_total} = {moderate_hits/max(moderate_total,1)*100:.1f}%")
        print(f"  Light   recall: {light_hits}/{light_total}    = {light_hits/max(light_total,1)*100:.1f}%")

        print("\n  Confusion matrix (rows=ground truth, cols=predicted):")
        print(f"  {'':12}  {'->strong':>9}  {'->moderate':>10}  {'->light':>8}")
        for true_b in ("strong", "moderate", "light"):
            row = confusion[true_b]
            print(f"  {true_b:<12}  {row.get('strong',0):>9}  {row.get('moderate',0):>10}  {row.get('light',0):>8}")

        # ── SECTION 3: MAE ────────────────────────────────────────────────────
        print("\n\n" + "=" * 90)
        print("SECTION 3 — MAE ON LONGEVITY_HOURS vs LABEL MIDPOINTS")
        print("=" * 90)

        if mae_vals:
            mae = statistics.mean(mae_vals)
            rmse = (sum(v**2 for v in mae_vals) / len(mae_vals)) ** 0.5
            med  = statistics.median(mae_vals)
            p90  = sorted(mae_vals)[int(len(mae_vals)*0.9)]
            print(f"\n  n={len(mae_vals)}  MAE={mae:.2f}h  RMSE={rmse:.2f}h  Median={med:.2f}h  P90={p90:.2f}h")
            print(f"\n  MAE by ground-truth bucket:")
            for bucket in ("strong", "moderate", "light"):
                errs = errors_by_bucket[bucket]
                if errs:
                    mae_b = statistics.mean(abs(e) for e in errs)
                    bias  = statistics.mean(errs)
                    print(f"    {bucket:<10}  n={len(errs):>4}  MAE={mae_b:.2f}h  bias={bias:+.2f}h "
                          f"({'over' if bias > 0 else 'under'}-predicts longevity)")
        else:
            print("  No labeled perfumes with mapped midpoints found.")

        # ── SECTION 4: Weakness report ────────────────────────────────────────
        print("\n\n" + "=" * 90)
        print("SECTION 4 — WEAKNESS REPORT")
        print("=" * 90)

        # 4a: confidence distribution
        print("\n  4a. Confidence score distribution (sample of 5k perfumes):")
        sample = all_rows[:5000]
        conf_vals: list[float] = []
        for p in sample:
            res, _, _ = run_predict(p, models)
            conf_vals.append(res["confidence_score"])
        buckets = {"<0.3": 0, "0.3-0.35": 0, "0.35-0.4": 0, "0.4-0.45": 0,
                   "0.45-0.5": 0, ">0.5": 0}
        for c in conf_vals:
            if c < 0.30: buckets["<0.3"] += 1
            elif c < 0.35: buckets["0.3-0.35"] += 1
            elif c < 0.40: buckets["0.35-0.4"] += 1
            elif c < 0.45: buckets["0.4-0.45"] += 1
            elif c < 0.50: buckets["0.45-0.5"] += 1
            else: buckets[">0.5"] += 1
        for rng, cnt in buckets.items():
            bar = "#" * (cnt * 40 // len(sample))
            print(f"    {rng:<12}  {bar:<40} {cnt:>5} ({cnt/len(sample)*100:.1f}%)")

        # 4b: source_count vs avg confidence
        print("\n  4b. Avg confidence by source_count tier (sample):")
        sc_groups: dict[str, list[float]] = defaultdict(list)
        for p, c in zip(sample, conf_vals):
            sc = p.source_count or 1
            key = "1" if sc == 1 else ("2" if sc == 2 else "3+")
            sc_groups[key].append(c)
        for k in ("1", "2", "3+"):
            vals = sc_groups[k]
            if vals:
                print(f"    source_count={k}  n={len(vals):>5}  avg_conf={statistics.mean(vals):.3f}  "
                      f"min={min(vals):.3f}  max={max(vals):.3f}")

        # 4c: inferred vs real pyramid confidence
        print("\n  4c. Real pyramid vs inferred pyramid confidence (sample):")
        real_pyr_conf  = [c for p, c in zip(sample, conf_vals)
                          if not p.has_inferred_pyramid and (p.top_notes or p.middle_notes or p.base_notes)]
        inf_pyr_conf   = [c for p, c in zip(sample, conf_vals) if p.has_inferred_pyramid]
        no_pyr_conf    = [c for p, c in zip(sample, conf_vals)
                          if not (p.top_notes or p.middle_notes or p.base_notes)]
        for label, vals in [("real pyramid", real_pyr_conf),
                             ("inferred pyr", inf_pyr_conf),
                             ("no pyramid  ", no_pyr_conf)]:
            if vals:
                print(f"    {label}  n={len(vals):>5}  avg_conf={statistics.mean(vals):.3f}")

        # 4d: note coverage gaps
        print("\n  4d. Notes with no chemistry data (defaulting to 5.0 — top 20 by frequency):")
        note_counts: dict[str, int] = defaultdict(int)
        import json
        notes_chem_path = Path(__file__).parent.parent / "data" / "notes_chemistry.json"
        known_notes: set[str] = set()
        if notes_chem_path.exists():
            with open(notes_chem_path) as f:
                for entry in json.load(f):
                    known_notes.add(entry["name"].lower())
        for p in all_rows:
            for note in ((p.top_notes or []) + (p.middle_notes or []) + (p.base_notes or [])):
                if note and note.lower() not in known_notes:
                    note_counts[note.lower()] += 1
        top_missing = sorted(note_counts.items(), key=lambda x: -x[1])[:20]
        for note, cnt in top_missing:
            print(f"    {note:<30}  appears in {cnt:>6} perfumes")

        # 4e: longevity bias summary
        print("\n  4e. Longevity bias summary:")
        print("    The performance model derives longevity_hours from note chemistry + community")
        print("    ratings. The 384 labeled perfumes blend in label midpoints (50/50), so")
        print("    predictions on those are anchored to the label. On UNLABELED perfumes,")
        print("    the model relies entirely on chemistry defaults — notes missing from")
        print(f"    notes_chemistry.json (defaulting to volatility=5.0) will pull longevity")
        print(f"    toward the median, compressing the range and biasing scores toward ~4-5h.")

        # 4f: longevity_hours distribution across all labeled predictions
        pred_longs = []
        gt_longs   = []
        for p in labeled:
            res, pd_data, _ = run_predict(p, models)
            m = label_to_midpoint(p.community_longevity_label)
            if m:
                pred_longs.append(res["longevity_hours"])
                gt_longs.append(m)
        if pred_longs:
            print(f"\n  4f. Longevity range comparison (labeled perfumes, n={len(pred_longs)}):")
            print(f"    Ground-truth range:  {min(gt_longs):.1f}h — {max(gt_longs):.1f}h  "
                  f"mean={statistics.mean(gt_longs):.2f}h")
            print(f"    Predicted range:     {min(pred_longs):.1f}h — {max(pred_longs):.1f}h  "
                  f"mean={statistics.mean(pred_longs):.2f}h")
            print(f"    Range compression:   GT span={max(gt_longs)-min(gt_longs):.1f}h, "
                  f"Pred span={max(pred_longs)-min(pred_longs):.1f}h")

        # ── summary ───────────────────────────────────────────────────────────
        print("\n\n" + "=" * 90)
        print("AUDIT SUMMARY")
        print("=" * 90)
        print(f"""
  Metric                   Value      Notes
  ──────────────────────── ────────   ─────────────────────────────────────────
  Longevity bucket acc.    {exact_match/n*100:.1f}%      3-class (strong/moderate/light) on 384 GT
  Strong recall            {strong_hits/max(strong_total,1)*100:.1f}%
  Moderate recall          {moderate_hits/max(moderate_total,1)*100:.1f}%
  Light recall             {light_hits/max(light_total,1)*100:.1f}%
  MAE (longevity_hours)    {mae:.2f}h      vs label midpoints
  RMSE (longevity_hours)   {rmse:.2f}h
  Avg confidence (sc=1)    {statistics.mean(sc_groups['1']):.3f}      quality mult = 0.70/0.90
  Avg confidence (sc>=2)   {statistics.mean(sc_groups.get('2',[])+sc_groups.get('3+',[])):.3f}      quality mult = 0.85/1.00
  Missing note coverage    {len(note_counts):>4} unique    pull predictions toward median
""")

        print("  Top weaknesses to fix:")
        print(f"  1. Note coverage: {len(note_counts)} unique notes have NO chemistry data — "
              f"top gap is '{top_missing[0][0]}' ({top_missing[0][1]:,} perfumes).")
        print(f"  2. Label leakage: model trained on 50/50 label blend; "
              f"true generalization accuracy is lower than {exact_match/n*100:.1f}%.")
        print(f"  3. Range compression: predicted longevity spans "
              f"{max(pred_longs)-min(pred_longs):.1f}h vs GT {max(gt_longs)-min(gt_longs):.1f}h — "
              f"model is too conservative.")
        if moderate_hits / max(moderate_total, 1) < 0.5:
            print(f"  4. Moderate class is hardest: {moderate_hits/max(moderate_total,1)*100:.1f}% recall — "
                  f"boundary between strong/moderate is blurry.")
        print()


if __name__ == "__main__":
    asyncio.run(main())
