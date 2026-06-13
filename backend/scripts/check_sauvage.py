"""Check Sauvage EDT/EDP collision and the confidence formula."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv; load_dotenv(_env)

from sqlalchemy import select, text
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume


async def main():
    await init_db()
    async with AsyncSessionLocal() as s:

        # Full details for id=1 and id=2
        q = await s.execute(select(Perfume).where(Perfume.id.in_([1, 2])))
        for p in sorted(q.scalars(), key=lambda x: x.id):
            print(f"id={p.id}  name={p.name!r}  conc={p.concentration!r}")
            print(f"  source_count={p.source_count}  rating={p.community_overall_rating:.3f}")
            print(f"  accords ({len(p.accords or [])}): {p.accords}")
            print(f"  top_notes: {p.top_notes}")
            print(f"  url: {p.fragrantica_url}")
            print()

        # All exact Sauvage records to show the collision
        rows = await s.execute(
            text("SELECT id, name, concentration, source_count, community_overall_rating, accords "
                 "FROM perfumes WHERE brand='Dior' AND name='Sauvage' ORDER BY id")
        )
        print("All name='Sauvage' brand='Dior' records:")
        for row in rows:
            print(f"  id={row[0]:>5}  conc={row[2]!r:<10}  source_count={row[3]}  "
                  f"rating={row[4]:.2f}  accords={row[5]}")

        # Show SELECT ORDER — which id wins the by_brand slot
        print("\nThe by_brand dict iteration order for 'dior'+'sauvage':")
        rows2 = await s.execute(
            text("SELECT id FROM perfumes WHERE LOWER(brand)='dior' AND LOWER(name)='sauvage' ORDER BY id DESC LIMIT 1")
        )
        for row in rows2:
            print(f"  Last id with normalize('sauvage') under 'dior' = {row[0]} → this is the one in by_brand")

asyncio.run(main())
