"""
Fix source_count for specific canonical fragrances where the Parfumo import
name-variant mismatch prevented automatic source_count increment.

These records appear in at least 3 data sources (seed/FRA + fra_perfumes +
Parfumo) but source_count stayed at 2 because the import's fuzzy-match
couldn't link the Parfumo variant to the correct DB record.

This script is idempotent — it only raises source_count, never lowers it.

Run from the backend/ directory:
    python scripts/fix_source_counts.py
"""
import asyncio
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

# (perfume_id, brand, name, target_sc)
# Only updates records whose current source_count < target_sc.
DIRECT_FIXES: list[tuple[int, str, str, int]] = [
    (1,     "Dior",    "Sauvage (EDT)",                    3),
    (2,     "Dior",    "Sauvage (EDP)",                    3),
    (9,     "Chanel",  "Bleu de Chanel (EDT)",             3),
    (4826,  "Gucci",   "Gucci Bloom",                      3),
    (21927, "Chanel",  "Bleu de Chanel Eau de Parfum",     3),
]


async def main() -> None:
    await init_db()
    print("fix_source_counts: checking perfumes...")

    async with AsyncSessionLocal() as session:
        ids = [fid for fid, *_ in DIRECT_FIXES]
        result = await session.execute(select(Perfume).where(Perfume.id.in_(ids)))
        perfumes = {p.id: p for p in result.scalars().all()}

        changed = 0
        for pid, brand, label, target_sc in DIRECT_FIXES:
            p = perfumes.get(pid)
            if p is None:
                print(f"  NOT FOUND  id={pid}  {brand} {label}")
                continue
            old_sc = p.source_count or 1
            if old_sc >= target_sc:
                print(f"  SKIP (sc={old_sc})  id={pid}  {p.brand!r} {p.name!r}")
                continue
            p.source_count = target_sc
            changed += 1
            print(f"  UPDATE sc {old_sc}->{target_sc}  id={pid}  {p.brand!r} {p.name!r}")

        if changed:
            await session.commit()
            print(f"\nCommitted {changed} source_count update(s).")
        else:
            print("\nAll records already at target source_count — nothing to do.")


asyncio.run(main())
