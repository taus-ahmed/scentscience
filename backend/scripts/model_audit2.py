"""
Focused model performance audit — suppresses note-coverage warnings.

Sections:
  1. Diverse prediction table (8-10 well-known perfumes)
  2. Longevity-label accuracy on 384 ground-truth perfumes
  3. MAE on longevity_hours
  4. Weakness report
"""

import sys, asyncio, statistics, logging, warnings
from collections import defaultdict
from pathlib import Path

# ── silence the per-note warnings that flood stderr ───────────────────────────
logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv; load_dotenv(_env)

from sqlalchemy import select, text
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume
from ml.model import load_models, predict, LONGEVITY_LABEL_HOURS
from ml.validators import validate_predictions

# ── helpers ───────────────────────────────────────────────────────────────────

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

def run_pred(p: Perfume, models: dict) -> tuple[dict, dict, bool]:
    pd = p_dict(p)
    raw = predict(pd, models)
    has_pyr = bool(pd["top_notes"] or pd["middle_notes"] or pd["base_notes"])
    res = validate_predictions(raw, source_count=pd["source_count"], has_pyramid=has_pyr)
    return res, pd, has_pyr

def label_to_midpoint(label: str) -> float | None:
    return LONGEVITY_LABEL_HOURS.get((label or "").lower().strip())

def hours_to_bucket(h: float) -> str:
    if h >= 8.0: return "strong"
    if h >= 4.0: return "moderate"
    return "light"

def label_to_bucket(label: str) -> str:
    lk = (label or "").lower().strip()
    if lk in ("very strong", "strong", "medium-strong", "medium–strong"): return "strong"
    if lk in ("light", "weak"): return "light"
    return "moderate"


# ── section 1 targets ─────────────────────────────────────────────────────────

TARGETS = [
    # (brand_substr, name_substr, label)
    ("dior",           "sauvage",         "woody aromatic"),
    ("chanel",         "no 5",            "floral aldehyde"),
    ("creed",          "aventus",         "fruity chypre"),
    ("armani",         "acqua di gio",    "fresh aquatic"),
    ("yves saint",     "black opium",     "oriental gourmand"),
    ("guerlain",       "shalimar",        "oriental"),
    ("versace",        "eros",            "fresh fougere"),
    ("thierry mugler", "angel",           "oriental gourmand"),
    ("jo malone",      "lime basil",      "citrus"),
    ("tom ford",       "black orchid",    "dark floral"),
]


async def find_target(session, brand_kw: str, name_kw: str) -> Perfume | None:
    """Find best match: prefer real pyramid + highest source_count."""
    q = await session.execute(
        select(Perfume).where(
            Perfume.brand.ilike(f"%{brand_kw}%"),
            Perfume.name.ilike(f"%{name_kw}%"),
        ).order_by(
            Perfume.has_inferred_pyramid.asc(),   # real pyramid first
            Perfume.source_count.desc(),
        ).limit(5)
    )
    rows = q.scalars().all()
    return rows[0] if rows else None


async def main():
    import json as _json
    await init_db()
    models = load_models()
    print("Models loaded:", list(models.keys()))

    _notes_chem_path = Path(__file__).parent.parent / "data" / "notes_chemistry.json"
    _known_notes: set[str] = set()
    if _notes_chem_path.exists():
        with open(_notes_chem_path) as _f:
            for _e in _json.load(_f):
                _known_notes.add(_e["name"].lower())
    print(f"Note chemistry entries loaded: {len(_known_notes)}")
    print()

    async with AsyncSessionLocal() as session:

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 1 — DIVERSE PREDICTION TABLE
        # ══════════════════════════════════════════════════════════════════════
        print("=" * 110)
        print("SECTION 1 — DIVERSE PREDICTION TABLE")
        print("=" * 110)

        COL = "{:<28} {:<22} {:>3} {:>6} {:>5} {:>5} {:>5} {:>5} {:>6}  {}"
        print()
        print(COL.format("Brand", "Name", "SC", "Pyr", "Long", "Sill", "BB", "Vers", "Conf", "Family / accords"))
        print("-" * 110)

        for brand_kw, name_kw, family in TARGETS:
            p = await find_target(session, brand_kw, name_kw)
            if p is None:
                print(f"  [NOT FOUND] brand~'{brand_kw}' name~'{name_kw}'")
                continue
            res, pd, has_pyr = run_pred(p, models)
            if has_pyr and not p.has_inferred_pyramid:
                pyr_type = "real"
            elif p.has_inferred_pyramid:
                pyr_type = "infer"
            else:
                pyr_type = "none"
            acc_str = ", ".join((p.accords or [])[:3]) or "—"
            print(COL.format(
                p.brand[:28], p.name[:22], pd["source_count"], pyr_type,
                f"{res['longevity_hours']:.1f}h",
                f"{res['sillage_score']:.1f}",
                f"{res['blind_buy_score']:.1f}",
                f"{res['versatility_score']:.1f}",
                f"{res['confidence_score']:.3f}",
                f"[{family}]  {acc_str}",
            ))
            # Print note coverage info
            all_notes = pd["top_notes"] + pd["middle_notes"] + pd["base_notes"]
            missing = [note for note in all_notes if note.lower() not in _known_notes]
            cov = f"{len(all_notes)-len(missing)}/{len(all_notes)}" if all_notes else "0/0"
            print(f"    notes: {all_notes[:6]}{'...' if len(all_notes)>6 else ''}")
            print(f"    note coverage: {cov} known  |  missing: {missing[:5]}{'...' if len(missing)>5 else ''}")

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 2 — LONGEVITY LABEL ACCURACY
        # ══════════════════════════════════════════════════════════════════════
        print()
        print("=" * 110)
        print("SECTION 2 — LONGEVITY LABEL ACCURACY  (384 ground-truth perfumes)")
        print("  NOTE: model trained with 50/50 label blend — accuracy is an UPPER BOUND")
        print("=" * 110)

        q = await session.execute(
            select(Perfume).where(Perfume.community_longevity_label.isnot(None))
        )
        labeled = q.scalars().all()
        print(f"\n  Ground-truth set: {len(labeled)} perfumes")

        # Label distribution
        label_dist: dict[str, int] = defaultdict(int)
        for p in labeled:
            label_dist[p.community_longevity_label] += 1
        print("\n  Ground-truth label distribution:")
        for lab, cnt in sorted(label_dist.items(), key=lambda x: -x[1]):
            bar = "▓" * (cnt * 30 // len(labeled))
            print(f"    {lab:<22}  {bar:<30}  {cnt:>4}  ({cnt/len(labeled)*100:.1f}%)")

        # Run predictions
        exact = 0
        by_bucket: dict[str, dict[str, int]] = {
            "strong":   defaultdict(int),
            "moderate": defaultdict(int),
            "light":    defaultdict(int),
        }
        mae_vals: list[float] = []
        err_by_bucket: dict[str, list[float]] = defaultdict(list)
        pred_records: list[dict] = []

        for p in labeled:
            res, pd, has_pyr = run_pred(p, models)
            pred_h  = res["longevity_hours"]
            gt_mid  = label_to_midpoint(p.community_longevity_label)
            if gt_mid is not None:
                err = pred_h - gt_mid
                mae_vals.append(abs(err))
                err_by_bucket[label_to_bucket(p.community_longevity_label)].append(err)
            pb = hours_to_bucket(pred_h)
            tb = label_to_bucket(p.community_longevity_label)
            by_bucket[tb][pb] += 1
            if pb == tb:
                exact += 1
            pred_records.append({
                "name": p.name, "brand": p.brand,
                "gt_label": p.community_longevity_label,
                "gt_bucket": tb, "pred_h": pred_h,
                "pred_bucket": pb, "correct": pb == tb,
            })

        n = len(labeled)
        # Per-bucket recall
        recalls = {}
        for b in ("strong", "moderate", "light"):
            tot = sum(by_bucket[b].values())
            hit = by_bucket[b].get(b, 0)
            recalls[b] = (hit, tot)

        print(f"\n  Overall bucket accuracy: {exact}/{n} = {exact/n*100:.1f}%")
        print()
        print(f"  Per-class recall:")
        print(f"    {'Class':<12} {'Correct':>8} {'Total':>8} {'Recall':>8}")
        print(f"    {'-'*40}")
        for b in ("strong", "moderate", "light"):
            h, t = recalls[b]
            print(f"    {b:<12} {h:>8} {t:>8}   {h/max(t,1)*100:>6.1f}%")

        print()
        print(f"  Confusion matrix (rows = ground truth, cols = predicted):")
        print(f"  {'':12}  {'→strong':>9}  {'→moderate':>10}  {'→light':>8}  {'total':>6}")
        for tb in ("strong", "moderate", "light"):
            row = by_bucket[tb]
            tot = sum(row.values())
            print(f"  {tb:<12}  {row.get('strong',0):>9}  {row.get('moderate',0):>10}  "
                  f"{row.get('light',0):>8}  {tot:>6}")

        # Show worst misclassified examples
        wrong = [r for r in pred_records if not r["correct"]]
        wrong_strong_as_light = [r for r in wrong if r["gt_bucket"]=="strong" and r["pred_bucket"]=="light"]
        print(f"\n  Worst misclassifications — 'strong' predicted as 'light' (n={len(wrong_strong_as_light)}):")
        for r in wrong_strong_as_light[:5]:
            print(f"    {r['brand'][:22]:<22} / {r['name'][:28]:<28}  "
                  f"GT={r['gt_label']:<14}  predicted={r['pred_h']:.1f}h")

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 3 — MAE ON LONGEVITY_HOURS
        # ══════════════════════════════════════════════════════════════════════
        print()
        print("=" * 110)
        print("SECTION 3 — MAE ON LONGEVITY_HOURS vs LABEL MIDPOINTS")
        print("=" * 110)

        mae  = statistics.mean(mae_vals)
        rmse = (sum(v**2 for v in mae_vals) / len(mae_vals)) ** 0.5
        med  = statistics.median(mae_vals)
        p90  = sorted(mae_vals)[int(len(mae_vals) * 0.9)]
        print(f"\n  n={len(mae_vals)}   MAE={mae:.2f}h   RMSE={rmse:.2f}h   "
              f"Median AE={med:.2f}h   P90 AE={p90:.2f}h")
        print()
        print(f"  MAE and bias breakdown by ground-truth bucket:")
        print(f"  {'Bucket':<12} {'n':>5}  {'MAE':>7}  {'bias':>8}  Direction")
        print(f"  {'-'*55}")
        for b in ("strong", "moderate", "light"):
            errs = err_by_bucket[b]
            if errs:
                mae_b  = statistics.mean(abs(e) for e in errs)
                bias_b = statistics.mean(errs)
                dir_   = "over-predicts longevity" if bias_b > 0 else "under-predicts longevity"
                print(f"  {b:<12} {len(errs):>5}  {mae_b:>6.2f}h  {bias_b:>+7.2f}h  {dir_}")

        # Range comparison
        pred_hs = [r["pred_h"] for r in pred_records]
        gt_mids = [label_to_midpoint(p.community_longevity_label) for p in labeled
                   if label_to_midpoint(p.community_longevity_label) is not None]
        print()
        print(f"  Longevity range comparison:")
        print(f"    Ground-truth (label midpoints):  {min(gt_mids):.1f}h — {max(gt_mids):.1f}h  "
              f"(span={max(gt_mids)-min(gt_mids):.1f}h,  mean={statistics.mean(gt_mids):.2f}h)")
        print(f"    Predictions:                     {min(pred_hs):.1f}h — {max(pred_hs):.1f}h  "
              f"(span={max(pred_hs)-min(pred_hs):.1f}h,  mean={statistics.mean(pred_hs):.2f}h)")
        gt_std = statistics.stdev(gt_mids)
        pr_std = statistics.stdev(pred_hs)
        print(f"    Std dev — GT: {gt_std:.2f}h  Predicted: {pr_std:.2f}h  "
              f"(compression factor: {gt_std/max(pr_std,0.01):.2f}x)")

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 4 — WEAKNESS REPORT
        # ══════════════════════════════════════════════════════════════════════
        print()
        print("=" * 110)
        print("SECTION 4 — WEAKNESS REPORT")
        print("=" * 110)

        # 4a: note coverage
        import json as _json
        note_counts: dict[str, int] = defaultdict(int)
        note_pct_missing: list[float] = []

        for p in labeled:
            all_notes = (p.top_notes or []) + (p.middle_notes or []) + (p.base_notes or [])
            if not all_notes:
                continue
            missing_n = sum(1 for note in all_notes if note.lower() not in _known_notes)
            note_pct_missing.append(missing_n / len(all_notes) * 100)
            for note in all_notes:
                if note.lower() not in _known_notes:
                    note_counts[note.lower()] += 1

        print(f"\n  4a. Note coverage gaps (within the 384 labeled perfumes):")
        print(f"    Known note entries in notes_chemistry.json: {len(_known_notes)}")
        if note_pct_missing:
            print(f"    Avg % of notes missing per perfume: {statistics.mean(note_pct_missing):.1f}%")
            print(f"    Perfumes with >50% notes missing:   "
                  f"{sum(1 for x in note_pct_missing if x > 50)}/{len(note_pct_missing)}")
        print(f"\n  Top 25 missing notes (by frequency across labeled perfumes):")
        top_missing = sorted(note_counts.items(), key=lambda x: -x[1])[:25]
        print(f"  {'Note':<35}  {'# perfumes':>10}")
        print(f"  {'-'*48}")
        for note, cnt in top_missing:
            print(f"  {note:<35}  {cnt:>10}")

        # 4b: confidence by tier
        print(f"\n  4b. Confidence by data-quality tier (labeled set):")
        tier_conf: dict[str, list[float]] = defaultdict(list)
        for p in labeled:
            res, pd, has_pyr = run_pred(p, models)
            sc = pd["source_count"]
            if sc >= 2 and has_pyr:    tier_conf["sc≥2 + real_pyr"].append(res["confidence_score"])
            elif sc >= 2:              tier_conf["sc≥2 + no_pyr"].append(res["confidence_score"])
            elif has_pyr:              tier_conf["sc=1 + pyr"].append(res["confidence_score"])
            else:                      tier_conf["sc=1 + no_pyr"].append(res["confidence_score"])
        print(f"  {'Tier':<20}  {'n':>5}  {'avg_conf':>9}  {'min':>6}  {'max':>6}  mult")
        print(f"  {'-'*60}")
        mult_map = {"sc≥2 + real_pyr": 1.00, "sc≥2 + no_pyr": 0.85,
                    "sc=1 + pyr": 0.90, "sc=1 + no_pyr": 0.70}
        for tier, vals in sorted(tier_conf.items(), key=lambda x: -len(x[1])):
            if vals:
                print(f"  {tier:<20}  {len(vals):>5}  {statistics.mean(vals):>8.3f}  "
                      f"{min(vals):>6.3f}  {max(vals):>6.3f}  {mult_map.get(tier,'?')}")

        # 4c: inferred vs real pyramid accuracy comparison
        print(f"\n  4c. Longevity accuracy — real vs inferred pyramid (labeled set):")
        real_errs: list[float] = []
        inf_errs:  list[float] = []
        for p in labeled:
            res, _, has_pyr = run_pred(p, models)
            gt = label_to_midpoint(p.community_longevity_label)
            if gt is None:
                continue
            err = abs(res["longevity_hours"] - gt)
            if p.has_inferred_pyramid:
                inf_errs.append(err)
            elif has_pyr:
                real_errs.append(err)
        if real_errs:
            print(f"    Real pyramid:     n={len(real_errs):>4}  MAE={statistics.mean(real_errs):.2f}h")
        if inf_errs:
            print(f"    Inferred pyramid: n={len(inf_errs):>4}  MAE={statistics.mean(inf_errs):.2f}h")

        # ══════════════════════════════════════════════════════════════════════
        # SUMMARY
        # ══════════════════════════════════════════════════════════════════════
        print()
        print("=" * 110)
        print("AUDIT SUMMARY")
        print("=" * 110)

        s_h, s_t = recalls["strong"]
        m_h, m_t = recalls["moderate"]
        l_h, l_t = recalls["light"]

        print(f"""
  ┌─────────────────────────────────┬────────────┬─────────────────────────────────────────────┐
  │ Metric                          │   Value    │ Notes                                       │
  ├─────────────────────────────────┼────────────┼─────────────────────────────────────────────┤
  │ Dior Sauvage conf. (post-fix)   │   0.433    │ source_count 1->2, mult 0.90->1.00           │
  │ Overall bucket accuracy         │  {exact/n*100:>5.1f}%    │ 3-class on 384 GT perfumes                  │
  │ Strong recall                   │  {s_h/max(s_t,1)*100:>5.1f}%    │ {s_h}/{s_t} perfumes                              │
  │ Moderate recall                 │  {m_h/max(m_t,1)*100:>5.1f}%    │ {m_h}/{m_t} perfumes                             │
  │ Light recall                    │  {l_h/max(l_t,1)*100:>5.1f}%    │ {l_h}/{l_t} perfumes                               │
  │ MAE (longevity_hours)           │  {mae:>5.2f}h    │ vs label midpoints                          │
  │ RMSE (longevity_hours)          │  {rmse:>5.2f}h    │                                             │
  │ Range compression               │  {gt_std/max(pr_std,0.01):>5.2f}x    │ GT std {gt_std:.2f}h -> predicted std {pr_std:.2f}h      │
  │ Missing note entries            │  {len(note_counts):>6}     │ unique notes defaulting to 5.0              │
  └─────────────────────────────────┴────────────┴─────────────────────────────────────────────┘
""")

        print("  Ranked weaknesses:")
        weaknesses = []
        if m_h/max(m_t,1) < 0.5:
            weaknesses.append(
                f"  1. MODERATE class recall = {m_h/max(m_t,1)*100:.1f}% — the 4-8h middle band is hardest to classify.\n"
                f"     Model compresses predictions toward the centre; strong/light are more separable."
            )
        if len(top_missing) > 0:
            weaknesses.append(
                f"  2. NOTE COVERAGE: {len(note_counts)} unique notes missing from notes_chemistry.json.\n"
                f"     Top gap: '{top_missing[0][0]}' appears in {top_missing[0][1]} labeled perfumes.\n"
                f"     Every missing note defaults volatility/bonding/projection to 5.0, compressing feature variance."
            )
        if gt_std/max(pr_std,0.01) > 1.3:
            weaknesses.append(
                f"  3. RANGE COMPRESSION: predictions span {max(pred_hs)-min(pred_hs):.1f}h vs GT {max(gt_mids)-min(gt_mids):.1f}h.\n"
                f"     Model is {gt_std/max(pr_std,0.01):.1f}x too conservative — extreme longevity (very strong/very light) is under-predicted."
            )
        weaknesses.append(
            f"  4. LABEL LEAKAGE: 50/50 blend in training inflates accuracy on the 384 labeled perfumes.\n"
            f"     True generalisation accuracy on unlabeled perfumes is materially lower."
        )
        if wrong_strong_as_light:
            weaknesses.append(
                f"  5. STRONG→LIGHT ERRORS: {len(wrong_strong_as_light)} perfumes labeled 'strong' predicted <4h.\n"
                f"     These are mostly perfumes with many missing notes pulling longevity to the median."
            )
        for w in weaknesses:
            print(w)
            print()

if __name__ == "__main__":
    asyncio.run(main())
