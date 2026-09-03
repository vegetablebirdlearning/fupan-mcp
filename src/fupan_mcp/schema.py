"""Memory entry schema.

A memory is one trading decision (or observation) plus the market context it
was made in. Outcomes and lessons are written back later — that write-back is
the 复盘 (post-market review).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any

DDL = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,            -- ISO date of the decision
    kind TEXT NOT NULL DEFAULT 'trade',  -- trade | observation | lesson
    symbol TEXT,                         -- e.g. 600519 / TSLA; nullable for market-level notes
    name TEXT,                           -- human name of the instrument
    sector TEXT,                         -- 板块/行业
    themes TEXT NOT NULL DEFAULT '[]',   -- JSON list: 题材/概念 tags
    action TEXT,                         -- buy | sell | hold | pass
    reasoning TEXT NOT NULL,             -- why the decision was made (agent's own words)
    regime_tags TEXT NOT NULL DEFAULT '[]', -- JSON list: market regime tags, e.g. 涨停潮/缩量阴跌/板块轮动
    snapshot TEXT NOT NULL DEFAULT '{}', -- JSON dict: market context snapshot (auto-captured if akshare available)
    embedding TEXT NOT NULL DEFAULT '[]',-- JSON list[float]: text embedding of reasoning+tags
    -- 复盘 write-back fields --
    outcome TEXT,                        -- win | loss | flat | invalidated
    pnl_pct REAL,                        -- realized/paper P&L percent
    lessons TEXT,                        -- what to remember next time
    reviewed_at TEXT,
    -- retrieval feedback loop --
    recall_count INTEGER NOT NULL DEFAULT 0,   -- how often surfaced
    useful_count INTEGER NOT NULL DEFAULT 0    -- how often marked useful by the agent
);
CREATE INDEX IF NOT EXISTS idx_memories_symbol ON memories(symbol);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
"""


@dataclass
class Memory:
    id: int | None = None
    created_at: str = ""
    kind: str = "trade"
    symbol: str | None = None
    name: str | None = None
    sector: str | None = None
    themes: list[str] = field(default_factory=list)
    action: str | None = None
    reasoning: str = ""
    regime_tags: list[str] = field(default_factory=list)
    snapshot: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    outcome: str | None = None
    pnl_pct: float | None = None
    lessons: str | None = None
    reviewed_at: str | None = None
    recall_count: int = 0
    useful_count: int = 0

    @classmethod
    def from_row(cls, row) -> "Memory":
        d = dict(row)
        for k in ("themes", "regime_tags", "embedding"):
            d[k] = json.loads(d.get(k) or "[]")
        d["snapshot"] = json.loads(d.get("snapshot") or "{}")
        return cls(**d)

    def to_public(self) -> dict[str, Any]:
        """Dict for returning to the agent — drop internal fields."""
        d = asdict(self)
        d.pop("embedding", None)
        return d
