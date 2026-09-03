"""A-share market snapshot capture (optional; needs `pip install fupan-mcp[ashare]`).

When the agent stores a memory we also stamp it with the day's market context,
so recall can match on *situation*, not just text. Fails soft: without akshare
(or off-line) you just get an empty snapshot.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Canonical regime tags the agent is encouraged to use (free-form also allowed).
REGIME_TAGS = [
    "涨停潮", "跌停潮", "普涨", "普跌", "缩量阴跌", "放量长阳", "高位分歧",
    "板块轮动", "题材退潮", "情绪冰点", "情绪高潮", "指数横盘", "V型反转",
    "外围冲击", "政策驱动", "财报季", "北向大幅流入", "北向大幅流出",
]


def capture_snapshot() -> dict[str, Any]:
    try:
        import akshare as ak  # type: ignore
    except ImportError:
        return {"note": "akshare not installed; snapshot skipped"}

    snap: dict[str, Any] = {"captured_at": datetime.now().isoformat(timespec="seconds")}
    try:
        zt = ak.stock_zt_pool_em(date=datetime.now().strftime("%Y%m%d"))
        snap["limit_up_count"] = int(len(zt))
    except Exception:
        pass
    try:
        dt_pool = ak.stock_zt_pool_dtgc_em(date=datetime.now().strftime("%Y%m%d"))
        snap["limit_down_count"] = int(len(dt_pool))
    except Exception:
        pass
    try:
        idx = ak.stock_zh_index_spot_em(symbol="上证系列指数")
        sh = idx[idx["代码"] == "000001"]
        if len(sh):
            snap["sh_index_pct"] = float(sh.iloc[0]["涨跌幅"])
    except Exception:
        pass
    return snap
