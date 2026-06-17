"""
Set community_longevity_label = 'Strong' for well-known long-lasting perfumes
where the label is currently NULL or wrong.

Run from the backend/ directory:
    python scripts/fix_longevity_labels.py
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

# (brand_substr, name_substr, concentration_filter, new_label)
# concentration_filter=None means any concentration matches
FIXES = [
    ("mugler",      "angel",            "EDP",  "Strong"),  # Angel EDP: legendary 10h+
    ("yves saint",  "l homme libre",    None,   "Strong"),  # L'Homme Libre: heavy oriental
    ("mugler",      "alien",            "EDP",  "Strong"),  # Alien EDP: 8-10h
    ("tom ford",    "black orchid",     "EDP",  "Strong"),  # Black Orchid: 10h+
    ("lancome",     "la nuit tresor",   "EDP",  "Strong"),  # La Nuit Trésor: 8-10h
]


def _matches(p: Perfume, brand_s: str, name_s: str, conc: str | None) -> bool:
    b = (p.brand or "").lower()
    n = (p.name or "").lower()
    if brand_s not in b:
        return False
    if name_s not in n:
        return False
    if conc and (p.concentration or "").upper() != conc.upper():
        return False
    return True


async def main() -> None:
    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Perfume))
        all_perfumes = result.scalars().all()
        print(f"Loaded {len(all_perfumes)} perfumes from DB")

        changed: list[Perfume] = []

        for brand_s, name_s, conc, label in FIXES:
            matches = [p for p in all_perfumes if _matches(p, brand_s, name_s, conc)]
            if not matches:
                print(f"  NO MATCH: brand={brand_s!r} name={name_s!r} conc={conc!r}")
                continue

            for p in matches:
                old = p.community_longevity_label
                if old == label:
                    print(
                        f"  SKIP (already {label!r}): "
                        f"{p.brand!r} {p.name!r} [{p.concentration}]"
                    )
                    continue
                p.community_longevity_label = label
                changed.append(p)
                print(
                    f"  UPDATE {old!r} -> {label!r}: "
                    f"{p.brand!r} {p.name!r} [{p.concentration}]"
                )

        if changed:
            await session.commit()
            print(f"\nCommitted {len(changed)} label updates.")
        else:
            print("\nNo updates needed.")


asyncio.run(main())
