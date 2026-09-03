"""Hybrid retrieval: the point of this project.

Score = semantic similarity (embedding cosine)
      + market-regime overlap (Jaccard on regime tags)
      + graph proximity (same symbol > same sector > shared theme)
      + usefulness prior (memories that helped before rank higher)
      + recency decay (yesterday's lesson beats last year's, all else equal)

Each returned memory carries a human-readable `why` so the agent (and the
user reading the transcript) can see the match rationale. Roadmap: replace
the implicit attribute graph with an explicit entity graph + collaborative
filtering over (query-context, memory) usefulness pairs.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from .embeddings import cosine, embed
from .schema import Memory

W_SEMANTIC = 0.40
W_REGIME = 0.25
W_GRAPH = 0.20
W_USEFUL = 0.10
W_RECENCY = 0.05
HALF_LIFE_DAYS = 90.0


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _graph_proximity(m: Memory, symbol: str | None, sector: str | None, themes: list[str]) -> float:
    if symbol and m.symbol == symbol:
        return 1.0
    if sector and m.sector == sector:
        return 0.6
    if themes and set(themes) & set(m.themes):
        return 0.4
    return 0.0


def _recency(m: Memory, now: datetime) -> float:
    try:
        dt = datetime.fromisoformat(m.created_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    days = max((now - dt).days, 0)
    return math.pow(0.5, days / HALF_LIFE_DAYS)


def _usefulness(m: Memory) -> float:
    if m.recall_count <= 0:
        return 0.0
    return m.useful_count / m.recall_count


def rank(
    memories: list[Memory],
    query: str,
    regime_tags: list[str] | None = None,
    symbol: str | None = None,
    sector: str | None = None,
    themes: list[str] | None = None,
    k: int = 5,
) -> list[tuple[Memory, float, str]]:
    """Return top-k (memory, score, why)."""
    regime_tags = regime_tags or []
    themes = themes or []
    qvec = embed(" ".join([query] + regime_tags + themes + [sector or ""]))
    now = datetime.now(timezone.utc)

    scored: list[tuple[Memory, float, str]] = []
    for m in memories:
        s_sem = cosine(qvec, m.embedding)
        s_reg = _jaccard(regime_tags, m.regime_tags)
        s_gra = _graph_proximity(m, symbol, sector, themes)
        s_use = _usefulness(m)
        s_rec = _recency(m, now)
        score = (W_SEMANTIC * s_sem + W_REGIME * s_reg + W_GRAPH * s_gra
                 + W_USEFUL * s_use + W_RECENCY * s_rec)
        if score <= 0.02:
            continue
        why_parts = []
        if s_gra >= 1.0:
            why_parts.append("同一标的")
        elif s_gra >= 0.6:
            why_parts.append(f"同板块({m.sector})")
        elif s_gra > 0:
            shared = set(themes) & set(m.themes)
            why_parts.append(f"共享题材({'/'.join(sorted(shared))})")
        if s_reg > 0:
            shared_r = set(regime_tags) & set(m.regime_tags)
            why_parts.append(f"相似行情结构({'/'.join(sorted(shared_r))})")
        if s_sem > 0.25:
            why_parts.append("推理语义相近")
        if s_use > 0.5:
            why_parts.append("历史上多次被证明有用")
        if m.outcome:
            why_parts.append(f"当时结果:{m.outcome}({m.pnl_pct:+.1f}%)" if m.pnl_pct is not None
                             else f"当时结果:{m.outcome}")
        scored.append((m, round(score, 4), "；".join(why_parts) or "综合相似"))

    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]
