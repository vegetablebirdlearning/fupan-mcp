# fupan-mcp 复盘

**Every A-share trader does 复盘 (post-market review). Your trading agent should too.**

A memory layer for trading agents, shipped as an MCP server. Before a trade, your agent recalls how similar market situations played out; after the trade, it writes the review back. Memories that actually change decisions get promoted — retrieval learns from its own usefulness.

[中文说明](#中文说明) · MIT

## Why

LLM trading agents ([TradingAgents](https://github.com/TauricResearch/TradingAgents), and friends) reason impressively — then forget everything by the next session. The losses repeat: buying the supporting sector instead of the leading one, catching knives during 题材退潮, re-learning the same lesson every month.

`fupan-mcp` gives any MCP-capable agent a persistent trading memory with **situation-aware recall**:

- **Not just vector search.** Recall blends semantic similarity, market-regime overlap (涨停潮 / 缩量阴跌 / 板块轮动 …), graph proximity (same stock > same sector > shared theme), usefulness feedback, and recency.
- **A-share native.** Optional [akshare] integration stamps each memory with the day's tape (limit-up count, index moves) automatically. Canonical regime tags speak the language of A-share market structure.
- **Explainable.** Every recalled memory comes with `why_matched` — the agent (and you, reading the transcript) sees the rationale.
- **Self-improving.** `mark_useful` feedback trains the ranker: memories that changed real decisions rank higher next time.

## Quickstart

```bash
git clone https://github.com/TODO她的账号/fupan-mcp && cd fupan-mcp
pip install -e .                 # + ".[ashare]" for A-share market snapshots

# Claude Code
claude mcp add fupan -- fupan-mcp

# Any MCP client: run `fupan-mcp` as a stdio server
```

Data lives in `~/.fupan/memory.db` (override with `FUPAN_DB`). Once published to PyPI, installation becomes `uvx fupan-mcp`.

## Tools

| Tool | When | What |
|---|---|---|
| `remember_trade` | at decision time | store decision + reasoning + regime tags + auto market snapshot |
| `recall_similar` | **before** deciding | top-k similar past situations, each with `why_matched` |
| `review_outcome` | after outcome known | write back win/loss, P&L, lessons — the 复盘 |
| `mark_useful` | after a recall helped | usefulness feedback that trains retrieval |
| `distill_lessons` | weekly / before familiar setups | aggregate lessons by symbol or tag |

## Evaluate it on your own history

Skepticism welcome — memory layers should prove they retrieve the right things:

```bash
python examples/replay_eval.py your_history.csv
```

Replays your historical calls in date order and measures whether recall surfaces the past cases that were actually relevant (Hit@K, leakage-free: each day only sees earlier memories).

## Roadmap

- [ ] Explicit entity graph (stock–sector–theme–event) replacing implicit attribute matching
- [ ] Collaborative filtering over (situation, memory) usefulness pairs — recommendation-style retrieval
- [ ] Pluggable embedders (`sentence-transformers`, API embeddings)
- [ ] Paper-trading A/B harness: same agent, with vs. without memory
- [ ] Multi-agent shared memory with per-agent attribution

---

## 中文说明

**每个 A 股股民都复盘，你的交易 agent 也应该。**

fupan-mcp 是给交易 agent 的记忆层（MCP server）：决策前回忆相似行情下的历史决策与结果，交易后把复盘写回记忆。被证明有用的记忆会被优先召回——检索自己会进化。

**和普通向量记忆的区别**：召回融合了语义相似、**行情结构匹配**（涨停潮/缩量阴跌/板块轮动等 regime 标签的重合度）、**图邻近**（同标的 > 同板块 > 共享题材）、有用性反馈和时间衰减；每条召回附带 `why_matched` 说明匹配理由。装上 akshare 后，每条记忆自动盖上当日市场快照（涨停家数、指数涨跌等）。

**效果可验证**：`examples/replay_eval.py` 用你自己的历史操作记录做无泄漏回放评测，量化"该想起来的有没有想起来"。

```bash
git clone https://github.com/TODO她的账号/fupan-mcp && cd fupan-mcp
pip install -e . && claude mcp add fupan -- fupan-mcp
```

欢迎 issue / PR，规划中的方向见 Roadmap（显式实体图谱、推荐式协同过滤检索、模拟盘 A/B 实验框架）。

## License

MIT
