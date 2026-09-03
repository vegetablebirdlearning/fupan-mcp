"""SQLite storage for memories. DB defaults to ~/.fupan/memory.db (env FUPAN_DB)."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .embeddings import embed
from .schema import DDL, Memory


def _db_path() -> Path:
    p = os.environ.get("FUPAN_DB")
    if p:
        return Path(p)
    d = Path.home() / ".fupan"
    d.mkdir(parents=True, exist_ok=True)
    return d / "memory.db"


class MemoryStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else _db_path()
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DDL)

    # -- write ---------------------------------------------------------------

    def remember(self, m: Memory) -> int:
        if not m.created_at:
            m.created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        if not m.embedding:
            m.embedding = embed(
                " ".join([m.reasoning or ""] + m.regime_tags + m.themes + [m.sector or "", m.name or ""])
            )
        cur = self.conn.execute(
            """INSERT INTO memories
               (created_at, kind, symbol, name, sector, themes, action, reasoning,
                regime_tags, snapshot, embedding)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                m.created_at, m.kind, m.symbol, m.name, m.sector,
                json.dumps(m.themes, ensure_ascii=False), m.action, m.reasoning,
                json.dumps(m.regime_tags, ensure_ascii=False),
                json.dumps(m.snapshot, ensure_ascii=False),
                json.dumps(m.embedding),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def review(self, memory_id: int, outcome: str, pnl_pct: float | None, lessons: str | None) -> bool:
        cur = self.conn.execute(
            """UPDATE memories SET outcome=?, pnl_pct=?, lessons=?, reviewed_at=? WHERE id=?""",
            (outcome, pnl_pct, lessons,
             datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), memory_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def mark_recalled(self, ids: list[int]) -> None:
        self.conn.executemany("UPDATE memories SET recall_count = recall_count + 1 WHERE id=?",
                              [(i,) for i in ids])
        self.conn.commit()

    def mark_useful(self, memory_id: int) -> bool:
        cur = self.conn.execute(
            "UPDATE memories SET useful_count = useful_count + 1 WHERE id=?", (memory_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # -- read ----------------------------------------------------------------

    def get(self, memory_id: int) -> Memory | None:
        row = self.conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        return Memory.from_row(row) if row else None

    def all(self, kind: str | None = None) -> list[Memory]:
        q = "SELECT * FROM memories"
        args: tuple = ()
        if kind:
            q += " WHERE kind=?"
            args = (kind,)
        return [Memory.from_row(r) for r in self.conn.execute(q, args).fetchall()]

    def lessons(self, symbol: str | None = None, tag: str | None = None) -> list[Memory]:
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE lessons IS NOT NULL AND lessons != ''").fetchall()
        out = [Memory.from_row(r) for r in rows]
        if symbol:
            out = [m for m in out if m.symbol == symbol]
        if tag:
            out = [m for m in out if tag in m.regime_tags or tag in m.themes]
        return out

    def stats(self) -> dict:
        row = self.conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS reviewed,
                      SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) AS wins,
                      SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) AS losses
               FROM memories"""
        ).fetchone()
        return dict(row)
