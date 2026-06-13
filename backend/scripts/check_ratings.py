"""Quick check of current rating_count state in DB."""
import asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
env = Path(__file__).parent.parent.parent / ".env"
if env.exists():
    from dotenv import load_dotenv; load_dotenv(env)

from models.database import AsyncSessionLocal, init_db
from sqlalchemy import text

async def main():
    await init_db()
    async with AsyncSessionLocal() as s:
        r = await s.execute(text("SELECT COUNT(*) FROM perfumes WHERE rating_count > 0"))
        print("rating_count > 0:", r.scalar())
        r2 = await s.execute(text("SELECT COUNT(*) FROM perfumes WHERE rating_count = 0 OR rating_count IS NULL"))
        print("rating_count = 0:", r2.scalar())
        r3 = await s.execute(text(
            "SELECT id, name, brand, rating_count, source_count FROM perfumes "
            "WHERE LOWER(brand) LIKE '%dior%' AND LOWER(name) LIKE '%sauvage%' "
            "ORDER BY source_count DESC LIMIT 5"
        ))
        print("Dior Sauvage rows:")
        for row in r3:
            print(" ", row)

asyncio.run(main())
