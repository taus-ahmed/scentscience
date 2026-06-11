"""Seed the database with notes and perfumes from JSON files."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import AsyncSessionLocal, init_db
from models.perfume import Note, Perfume
from sqlalchemy import select


async def seed_notes(session) -> dict[str, Note]:
    data_path = Path(__file__).parent.parent / "data" / "notes_chemistry.json"
    with open(data_path) as f:
        notes_data = json.load(f)

    note_map = {}
    for nd in notes_data:
        existing = await session.execute(select(Note).where(Note.name == nd["name"]))
        note = existing.scalar_one_or_none()
        if not note:
            note = Note(**nd)
            session.add(note)
            await session.flush()
        note_map[nd["name"].lower()] = note

    print(f"Seeded {len(notes_data)} notes.")
    return note_map


async def seed_perfumes(session):
    data_path = Path(__file__).parent.parent / "data" / "seed_perfumes.json"
    with open(data_path) as f:
        perfumes_data = json.load(f)

    count = 0
    for pd in perfumes_data:
        existing = await session.execute(
            select(Perfume).where(
                Perfume.name == pd["name"],
                Perfume.brand == pd["brand"],
                Perfume.concentration == pd["concentration"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        perfume = Perfume(**pd)
        session.add(perfume)
        count += 1

    print(f"Seeded {count} perfumes.")


async def seed_all():
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_notes(session)
        await seed_perfumes(session)
        await session.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_all())
