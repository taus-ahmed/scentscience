"""
Expand notes_chemistry.json by scraping additional note data.
Run: python scrapers/notes_db.py
"""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "notes_chemistry.json"


def get_existing_names() -> set[str]:
    if not DATA_PATH.exists():
        return set()
    with open(DATA_PATH) as f:
        return {n["name"].lower() for n in json.load(f)}


def add_note(note: dict):
    with open(DATA_PATH) as f:
        notes = json.load(f)
    if note["name"].lower() not in {n["name"].lower() for n in notes}:
        notes.append(note)
        with open(DATA_PATH, "w") as f:
            json.dump(notes, f, indent=2)
        print(f"Added: {note['name']}")
    else:
        print(f"Already exists: {note['name']}")


if __name__ == "__main__":
    print(f"Current notes: {len(get_existing_names())}")
    print("Add notes programmatically via add_note() or by editing notes_chemistry.json directly.")
