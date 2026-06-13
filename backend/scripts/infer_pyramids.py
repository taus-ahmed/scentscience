"""
Infer note pyramids for the ~43k perfumes that have accords but no note data.

Algorithm:
  1. Load reference set: perfumes with both accords AND at least some notes.
  2. Build a binary accord matrix (rows=perfumes, cols=accord vocab) for both
     the reference set and the target set.
  3. For each target, find the TOP_N_SIMILAR most similar reference perfumes
     using Jaccard similarity on accord vectors (computed via batched numpy
     matrix multiplication — no per-row Python loop over 22k refs).
  4. Aggregate all notes from those similar refs, weighted by Jaccard score.
     Notes that appear across more similar perfumes and with higher similarity
     rank higher.
  5. Take the top 15 notes by aggregate weight; sort them by volatility from
     notes_chemistry.json to assign pyramid positions:
       highest volatility → top_notes  (5 notes)
       middle volatility  → middle_notes (5 notes)
       lowest volatility  → base_notes  (5 notes)
  6. Persist in batches of 500, set has_inferred_pyramid=TRUE.
"""

import sys
import asyncio
import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np

_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

SETTINGS = get_settings()
BATCH_SIZE = 500
PROGRESS_EVERY = 2000
TOP_N_SIMILAR = 5
NOTES_PER_POSITION = 5
CHUNK_SIZE = 1000        # targets processed per numpy chunk

# ── load note chemistry for volatility-based position assignment ──────────────
_notes_path = Path(__file__).parent.parent / "data" / "notes_chemistry.json"
_notes_chem: dict[str, float] = {}
if _notes_path.exists():
    with open(_notes_path) as f:
        for entry in json.load(f):
            _notes_chem[entry["name"].lower()] = float(entry.get("volatility", 5.0))


def _volatility(note: str) -> float:
    return _notes_chem.get(note.lower(), 5.0)


# ── migration ─────────────────────────────────────────────────────────────────
async def run_migration(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE perfumes "
            "ADD COLUMN IF NOT EXISTS has_inferred_pyramid BOOLEAN NOT NULL DEFAULT FALSE"
        ))
    log.info("Migration: has_inferred_pyramid column ready")


# ── data loading ──────────────────────────────────────────────────────────────
async def load_reference_perfumes(engine) -> list[dict]:
    """Perfumes with accords AND at least some notes (the training/reference set)."""
    sql = text("""
        SELECT id, accords, top_notes, middle_notes, base_notes
        FROM perfumes
        WHERE json_array_length(accords) > 0
          AND (
            COALESCE(json_array_length(top_notes), 0)    > 0
            OR COALESCE(json_array_length(middle_notes), 0) > 0
            OR COALESCE(json_array_length(base_notes), 0)   > 0
          )
    """)
    result = []
    async with engine.connect() as conn:
        rows = await conn.execute(sql)
        for row in rows:
            accords = row[1] or []
            top     = [n for n in (row[2] or []) if n]
            mid     = [n for n in (row[3] or []) if n]
            base    = [n for n in (row[4] or []) if n]
            if accords and (top or mid or base):
                result.append({
                    "id":           row[0],
                    "accords":      [a.lower().strip() for a in accords if a],
                    "top_notes":    top,
                    "middle_notes": mid,
                    "base_notes":   base,
                })
    return result


async def load_target_perfumes(engine) -> list[dict]:
    """Perfumes with accords but no notes, not already inferred."""
    sql = text("""
        SELECT id, accords
        FROM perfumes
        WHERE json_array_length(accords) > 0
          AND COALESCE(json_array_length(top_notes), 0)    = 0
          AND COALESCE(json_array_length(middle_notes), 0) = 0
          AND COALESCE(json_array_length(base_notes), 0)   = 0
          AND has_inferred_pyramid = FALSE
    """)
    result = []
    async with engine.connect() as conn:
        rows = await conn.execute(sql)
        for row in rows:
            accords = row[1] or []
            if accords:
                result.append({
                    "id":      row[0],
                    "accords": [a.lower().strip() for a in accords if a],
                })
    return result


# ── accord vocabulary & binary vectors ───────────────────────────────────────
def build_vocab(refs: list[dict], targets: list[dict]) -> tuple[list[str], dict[str, int]]:
    vocab_set: set[str] = set()
    for p in refs:
        vocab_set.update(p["accords"])
    for p in targets:
        vocab_set.update(p["accords"])
    vocab = sorted(vocab_set)
    return vocab, {a: i for i, a in enumerate(vocab)}


def to_binary_matrix(perfumes: list[dict], vocab_idx: dict[str, int], V: int) -> np.ndarray:
    mat = np.zeros((len(perfumes), V), dtype=np.float32)
    for row_i, p in enumerate(perfumes):
        for a in p["accords"]:
            if a in vocab_idx:
                mat[row_i, vocab_idx[a]] = 1.0
    return mat


# ── Jaccard similarity (chunked numpy) ───────────────────────────────────────
def jaccard_batch(
    target_chunk: np.ndarray,   # (chunk, V)
    ref_mat: np.ndarray,        # (R, V)
    target_sums: np.ndarray,    # (chunk,)
    ref_sums: np.ndarray,       # (R,)
) -> np.ndarray:
    """Return (chunk, R) Jaccard matrix."""
    dot = target_chunk @ ref_mat.T                       # (chunk, R) intersections
    union = target_sums[:, None] + ref_sums[None, :] - dot
    union = np.maximum(union, 1e-9)
    return dot / union


# ── note aggregation & position assignment ───────────────────────────────────
def infer_notes(
    top5_refs: list[dict],
    weights: list[float],
) -> tuple[list[str], list[str], list[str]]:
    """
    Aggregate notes from the top-N most similar reference perfumes.
    Weight each note by the Jaccard similarity of the perfume it came from.
    Sort the top-15 by volatility to assign pyramid positions.
    """
    note_weight: dict[str, float] = defaultdict(float)
    for ref, w in zip(top5_refs, weights):
        all_notes = ref["top_notes"] + ref["middle_notes"] + ref["base_notes"]
        seen: set[str] = set()
        for note in all_notes:
            if note and note not in seen:
                note_weight[note] += w
                seen.add(note)

    if not note_weight:
        return [], [], []

    # Top 15 notes by aggregate weight (more popular across similar perfumes wins)
    top15 = [n for n, _ in sorted(note_weight.items(), key=lambda x: -x[1])][:15]

    if len(top15) < 3:
        return top15, [], []

    # Re-sort by volatility descending: highest → top notes, lowest → base notes
    sorted_by_vol = sorted(top15, key=lambda n: -_volatility(n))
    n = len(sorted_by_vol)

    per = min(NOTES_PER_POSITION, max(1, n // 3))
    top_notes    = sorted_by_vol[:per]
    base_notes   = sorted_by_vol[n - per:]
    middle_notes = sorted_by_vol[per: n - per][:NOTES_PER_POSITION]

    return top_notes, middle_notes, base_notes


# ── batch DB write ────────────────────────────────────────────────────────────
async def flush_batch(engine, updates: list[dict]) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("""
                UPDATE perfumes
                SET top_notes            = CAST(:top AS json),
                    middle_notes         = CAST(:mid AS json),
                    base_notes           = CAST(:base AS json),
                    has_inferred_pyramid = TRUE
                WHERE id = :pid
            """),
            [
                {
                    "pid":  u["pid"],
                    "top":  json.dumps(u["top"]),
                    "mid":  json.dumps(u["mid"]),
                    "base": json.dumps(u["base"]),
                }
                for u in updates
            ],
        )


# ── main ──────────────────────────────────────────────────────────────────────
async def main() -> None:
    engine = create_async_engine(SETTINGS.async_database_url, echo=False)

    await run_migration(engine)

    log.info("Loading reference perfumes (accords + pyramid)…")
    refs = await load_reference_perfumes(engine)
    log.info("  %d reference perfumes", len(refs))

    log.info("Loading target perfumes (accords, no pyramid)…")
    targets = await load_target_perfumes(engine)
    log.info("  %d target perfumes", len(targets))

    if not targets:
        log.info("Nothing to infer — all done.")
        await engine.dispose()
        return

    # Build vocab and matrices
    vocab, vocab_idx = build_vocab(refs, targets)
    V = len(vocab)
    log.info("  Accord vocabulary: %d unique accords", V)

    log.info("Building accord matrices…")
    ref_mat    = to_binary_matrix(refs,    vocab_idx, V)
    target_mat = to_binary_matrix(targets, vocab_idx, V)
    ref_sums    = ref_mat.sum(axis=1)     # (R,)
    target_sums = target_mat.sum(axis=1)  # (T,)

    # Filter targets whose accords are all unknown (sum=0 means no vocab match)
    valid_mask    = target_sums > 0
    valid_indices = np.where(valid_mask)[0]
    skipped_no_map = int((~valid_mask).sum())
    log.info("  %d targets mappable; %d skipped (no vocab match)",
             len(valid_indices), skipped_no_map)

    updates: list[dict] = []
    inferred = 0
    skipped_no_notes = 0

    log.info("Inferring pyramids in chunks of %d…", CHUNK_SIZE)

    for chunk_start in range(0, len(valid_indices), CHUNK_SIZE):
        chunk_idx    = valid_indices[chunk_start: chunk_start + CHUNK_SIZE]
        chunk_tmat   = target_mat[chunk_idx]    # (chunk, V)
        chunk_tsums  = target_sums[chunk_idx]   # (chunk,)

        sim_matrix = jaccard_batch(chunk_tmat, ref_mat, chunk_tsums, ref_sums)
        # sim_matrix: (chunk, R)

        k = min(TOP_N_SIMILAR, len(refs))
        for local_i, global_i in enumerate(chunk_idx):
            sims = sim_matrix[local_i]               # (R,)
            # argpartition is O(R); then sort only the k candidates
            top_k_idx = np.argpartition(sims, -k)[-k:]
            top_k_idx = top_k_idx[np.argsort(sims[top_k_idx])[::-1]]
            top_k_weights = sims[top_k_idx].tolist()
            top_k_refs    = [refs[ri] for ri in top_k_idx]

            top_n, mid_n, base_n = infer_notes(top_k_refs, top_k_weights)
            if not top_n and not mid_n and not base_n:
                skipped_no_notes += 1
                continue

            updates.append({
                "pid":  int(targets[global_i]["id"]),
                "top":  top_n,
                "mid":  mid_n,
                "base": base_n,
            })
            inferred += 1

            if inferred % PROGRESS_EVERY == 0:
                log.info("  …%d pyramids inferred", inferred)

        if len(updates) >= BATCH_SIZE:
            await flush_batch(engine, updates)
            updates.clear()

    # Flush remainder
    if updates:
        await flush_batch(engine, updates)

    await engine.dispose()

    print(f"\n{'=' * 54}")
    print(f"  Pyramid inference complete")
    print(f"  Inferred:             {inferred:>8,}")
    print(f"  Skipped (no vocab):   {skipped_no_map:>8,}")
    print(f"  Skipped (no notes):   {skipped_no_notes:>8,}")
    print(f"  Real pyramids before: {22_879:>8,}")
    print(f"  Total w/ pyramids:   ~{22_879 + inferred:>8,}")
    print(f"{'=' * 54}")


if __name__ == "__main__":
    asyncio.run(main())
