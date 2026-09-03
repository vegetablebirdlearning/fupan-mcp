"""fupan-mcp server: five tools that give a trading agent a memory.

Run directly (stdio):  uvx fupan-mcp
Add to Claude Code:    claude mcp add fupan -- uvx fupan-mcp
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from .context import REGIME_TAGS, capture_snapshot
from .retrieval import rank
from .schema import Memory
from .store import MemoryStore

mcp = MCPServer(
    "fupan",
    instructions=(
        "复盘 memory for trading agents. BEFORE making a trading decision, call "
        "recall_similar with the current situation. AFTER a trade closes (or a "
        "call is proven right/wrong), call review_outcome to write the 复盘 back. "
        "Mark memories that actually changed your decision with mark_useful — "
        "this trains retrieval. Canonical regime tags: " + ", ".join(REGIME_TAGS)
    ),
)

_store: MemoryStore | None = None


def store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


@mcp.tool()
def remember_trade(
    reasoning: str,
    action: str = "buy",
    symbol: str | None = None,
    name: str | None = None,
    sector: str | None = None,
    themes: list[str] | None = None,
    regime_tags: list[str] | None = None,
    capture_market_snapshot: bool = True,
) -> str:
    """Store a trading decision with its full context. Call at decision time.

    Args:
        reasoning: Why you are making this decision, in your own words. Be specific —
            this text is what future recall matches against.
        action: buy | sell | hold | pass.
        symbol: Instrument code, e.g. "600519".
        name: Instrument name, e.g. "贵州茅台".
        sector: Sector/industry, e.g. "白酒".
        themes: Concept/theme tags, e.g. ["高股息", "国企改革"].
        regime_tags: Market regime tags describing today's tape, e.g. ["缩量阴跌", "板块轮动"].
        capture_market_snapshot: Auto-stamp today's market stats (needs akshare).
    """
    snap = capture_snapshot() if capture_market_snapshot else {}
    mid = store().remember(Memory(
        kind="trade", symbol=symbol, name=name, sector=sector,
        themes=themes or [], action=action, reasoning=reasoning,
        regime_tags=regime_tags or [], snapshot=snap,
    ))
    return json.dumps({"memory_id": mid, "snapshot": snap}, ensure_ascii=False)


@mcp.tool()
def recall_similar(
    situation: str,
    symbol: str | None = None,
    sector: str | None = None,
    themes: list[str] | None = None,
    regime_tags: list[str] | None = None,
    k: int = 5,
) -> str:
    """Recall past decisions made in similar situations. Call BEFORE deciding.

    Args:
        situation: Describe the current setup/dilemma in plain words.
        symbol/sector/themes: Current instrument context, if any.
        regime_tags: Today's market regime tags.
        k: Max memories to return.
    """
    results = rank(store().all(), situation, regime_tags, symbol, sector, themes, k)
    store().mark_recalled([m.id for m, _, _ in results if m.id])
    payload = [
        {**m.to_public(), "match_score": s, "why_matched": why}
        for m, s, why in results
    ]
    return json.dumps(payload, ensure_ascii=False, default=str)


@mcp.tool()
def review_outcome(memory_id: int, outcome: str, pnl_pct: float | None = None,
                   lessons: str | None = None) -> str:
    """Write the 复盘 back onto a memory once the outcome is known.

    Args:
        memory_id: The memory to review.
        outcome: win | loss | flat | invalidated.
        pnl_pct: Realized P&L percent, if applicable.
        lessons: What to do differently (or keep doing) next time.
    """
    ok = store().review(memory_id, outcome, pnl_pct, lessons)
    return json.dumps({"updated": ok})


@mcp.tool()
def mark_useful(memory_id: int) -> str:
    """Mark a recalled memory as having genuinely influenced your decision.
    This feedback trains future retrieval ranking."""
    return json.dumps({"updated": store().mark_useful(memory_id)})


@mcp.tool()
def distill_lessons(symbol: str | None = None, tag: str | None = None) -> str:
    """Aggregate all written-back lessons, optionally filtered by symbol or tag.
    Use this for a weekly review or before entering a familiar setup."""
    ms = store().lessons(symbol=symbol, tag=tag)
    payload = {
        "stats": store().stats(),
        "lessons": [
            {"memory_id": m.id, "date": m.created_at[:10], "symbol": m.symbol,
             "outcome": m.outcome, "pnl_pct": m.pnl_pct, "lessons": m.lessons}
            for m in ms
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
