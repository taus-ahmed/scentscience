"""
Parse community longevity + sillage vote distributions from the FragDB fragrances.csv
sample and update the matching DB records.

Columns parsed: longevity, sillage (pipe-delimited vote strings like
    longevity_very_weak:152:1.0;longevity_weak:356:3.0;...
Each entry maps to a 1-5 weighted average:
    very_weak/very_soft=1, weak/soft=2, moderate/medium=3,
    long_lasting/heavy/strong=4, eternal/enormous=5

Usage:
    cd backend/
    python scripts/update_community_ratings.py [--dry-run]
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)

from sqlalchemy import select, update
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume

FRAGRANCES_CSV = Path(__file__).parent.parent / "data" / "datasets" / "fragrances.csv"


def _tier(label: str) -> int | None:
    l = label.lower()
    if "very_weak" in l or "very weak" in l or "very_soft" in l:
        return 1
    if "weak" in l or "soft" in l:
        return 2
    if "moderate" in l or "medium" in l:
        return 3
    if "long_lasting" in l or "heavy" in l or "strong" in l:
        return 4
    if "eternal" in l or "enormous" in l or "very_long" in l:
        return 5
    return None


def parse_votes(raw: str) -> float | None:
    if not raw:
        return None
    total_v = total_w = 0
    for item in raw.split(";"):
        parts = item.strip().split(":")
        if len(parts) != 3:
            continue
        label, votes_s = parts[0], parts[1]
        try:
            votes = int(votes_s)
        except ValueError:
            continue
        t = _tier(label)
        if t is None:
            continue
        total_v += votes
        total_w += votes * t
    if total_v == 0:
        return None
    return round(total_w / total_v, 3)


def _normalize(s: str) -> str:
    return s.lower().strip()


async def run(dry_run: bool) -> None:
    await init_db()

    rows: list[dict] = []
    with open(FRAGRANCES_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            brand_raw = (row.get("brand") or "").split(";")[0].strip()
            name_raw = (row.get("name") or "").strip()
            longevity = parse_votes(row.get("longevity") or "")
            sillage = parse_votes(row.get("sillage") or "")
            if name_raw and brand_raw:
                rows.append({
                    "brand": brand_raw,
                    "name": name_raw,
                    "longevity": longevity,
                    "sillage": sillage,
                })

    print(f"Parsed {len(rows)} rows from fragrances.csv")

    async with AsyncSessionLocal() as session:
        for r in rows:
            result = await session.execute(
                select(Perfume)
                .where(Perfume.brand.ilike(f"%{r['brand']}%"))
                .where(Perfume.name.ilike(r["name"]))
            )
            perfumes = result.scalars().all()
            if not perfumes:
                print(f"  NO MATCH: '{r['name']}' by '{r['brand']}'")
                continue

            for p in perfumes:
                updates: dict = {}
                if r["longevity"] is not None and (
                    p.community_longevity_rating is None
                    or abs((p.community_longevity_rating or 3.0) - 3.0) < 0.01
                ):
                    updates["community_longevity_rating"] = r["longevity"]
                if r["sillage"] is not None and (
                    p.community_sillage_rating is None
                    or abs((p.community_sillage_rating or 3.0) - 3.0) < 0.01
                ):
                    updates["community_sillage_rating"] = r["sillage"]

                if not updates:
                    print(f"  SKIP (already set): {p.name} by {p.brand}")
                    continue

                print(
                    f"  UPDATE id={p.id}: {p.name} by {p.brand} — "
                    + ", ".join(f"{k}={v}" for k, v in updates.items())
                )
                if not dry_run:
                    await session.execute(
                        update(Perfume).where(Perfume.id == p.id).values(**updates)
                    )

        if not dry_run:
            await session.commit()
            print("Committed all updates.")
        else:
            print("[DRY RUN] No changes written.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.dry_run))


if __name__ == "__main__":
    main()
