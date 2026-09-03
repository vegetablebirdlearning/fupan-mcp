"""Replay evaluation: measure retrieval quality on your own historical calls.

Feed a CSV of historical recommendations (date, symbol, name, sector, themes,
reasoning, regime_tags, outcome, pnl_pct) — e.g. exported from your quant
pipeline — then, for each day D, ask: "with only memories from before D, does
recall_similar surface the past cases a human reviewer would consider relevant?"

Metrics: Hit@K on same-symbol/same-regime relevance, plus outcome-weighted
precision (did we surface the memories whose lessons would have helped?).

Usage:
    python examples/replay_eval.py history.csv
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fupan_mcp.retrieval import rank  # noqa: E402
from fupan_mcp.schema import Memory  # noqa: E402
from fupan_mcp.store import MemoryStore  # noqa: E402


def load_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return sorted(csv.DictReader(f), key=lambda r: r["date"])


def main(path: str, k: int = 5) -> None:
    rows = load_rows(path)
    store = MemoryStore(Path(tempfile.mkdtemp()) / "replay.db")
    hits = total = 0

    for row in rows:
        past = store.all()
        if past:
            results = rank(
                past,
                row["reasoning"],
                regime_tags=json.loads(row.get("regime_tags") or "[]"),
                symbol=row["symbol"],
                sector=row.get("sector"),
                themes=json.loads(row.get("themes") or "[]"),
                k=k,
            )
            relevant = {m.id for m, _, _ in results
                        if m.symbol == row["symbol"]
                        or set(m.regime_tags) & set(json.loads(row.get("regime_tags") or "[]"))}
            total += 1
            hits += bool(relevant)
        mid = store.remember(Memory(
            created_at=row["date"], symbol=row["symbol"], name=row.get("name"),
            sector=row.get("sector"), themes=json.loads(row.get("themes") or "[]"),
            action=row.get("action", "buy"), reasoning=row["reasoning"],
            regime_tags=json.loads(row.get("regime_tags") or "[]"),
        ))
        if row.get("outcome"):
            store.review(mid, row["outcome"],
                         float(row["pnl_pct"]) if row.get("pnl_pct") else None,
                         row.get("lessons"))

    print(f"Replayed {len(rows)} decisions; Hit@{k} = {hits}/{total} "
          f"({hits / total:.1%})" if total else "Not enough history to evaluate.")


if __name__ == "__main__":
    main(sys.argv[1])
