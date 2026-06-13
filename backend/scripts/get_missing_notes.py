"""Query all distinct note names from the DB, find which are missing from notes_chemistry.json."""
import asyncio, sys, json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv; load_dotenv(_env)

from sqlalchemy import select
from models.database import AsyncSessionLocal, init_db
from models.perfume import Perfume

NOTES_PATH = Path(__file__).parent.parent / "data" / "notes_chemistry.json"


async def main():
    await init_db()

    known: set[str] = set()
    with open(NOTES_PATH) as f:
        for e in json.load(f):
            known.add(e["name"].lower())

    print(f"Known notes in notes_chemistry.json: {len(known)}")

    note_freq: Counter = Counter()
    async with AsyncSessionLocal() as s:
        offset = 0
        batch = 2000
        while True:
            q = await s.execute(
                select(Perfume.top_notes, Perfume.middle_notes, Perfume.base_notes)
                .where(
                    (Perfume.top_notes != None) |
                    (Perfume.middle_notes != None) |
                    (Perfume.base_notes != None)
                )
                .offset(offset).limit(batch)
            )
            rows = q.all()
            if not rows:
                break
            for top, mid, base in rows:
                for note in (top or []) + (mid or []) + (base or []):
                    if note and note.lower() not in known:
                        note_freq[note.lower()] += 1
            offset += batch
            if offset % 10000 == 0:
                print(f"  scanned {offset}...")

    missing = sorted(note_freq.items(), key=lambda x: -x[1])
    print(f"\nTotal unique missing notes: {len(missing)}")
    print(f"\nAll missing notes (frequency across all perfumes):")
    print(f"{'Note':<50}  {'Freq':>6}")
    print("-" * 60)
    for note, freq in missing:
        print(f"{note:<50}  {freq:>6}")

    # Also dump as JSON for use in the fill script
    out = {"missing": [{"note": n, "freq": f} for n, f in missing]}
    with open(Path(__file__).parent / "missing_notes.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved to scripts/missing_notes.json")

asyncio.run(main())
