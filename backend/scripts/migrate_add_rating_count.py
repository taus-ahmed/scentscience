"""Add rating_count column to perfumes table (idempotent)."""
import asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv; load_dotenv(_env)

from sqlalchemy import text
from models.database import engine, init_db


async def main():
    await init_db()
    async with engine.begin() as conn:
        # Check if column exists first
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='perfumes' AND column_name='rating_count'"
        ))
        if result.fetchone():
            print("Column 'rating_count' already exists — nothing to do.")
            return
        await conn.execute(text(
            "ALTER TABLE perfumes ADD COLUMN rating_count INTEGER NOT NULL DEFAULT 0"
        ))
    print("Migration complete: added rating_count INTEGER DEFAULT 0 to perfumes.")


asyncio.run(main())
