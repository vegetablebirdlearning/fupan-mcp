import os
import tempfile

os.environ["FUPAN_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fupan_mcp.retrieval import rank  # noqa: E402
from fupan_mcp.schema import Memory  # noqa: E402
from fupan_mcp.store import MemoryStore  # noqa: E402


def make_store():
    return MemoryStore(os.environ["FUPAN_DB"])


def test_remember_and_get():
    s = make_store()
    mid = s.remember(Memory(
        symbol="600519", name="贵州茅台", sector="白酒", themes=["高股息"],
        action="buy", reasoning="缩量回踩年线企稳，北向连续三日回流",
        regime_tags=["缩量阴跌", "情绪冰点"],
    ))
    m = s.get(mid)
    assert m is not None and m.symbol == "600519"
    assert m.embedding and len(m.embedding) == 256


def test_review_and_lessons():
    s = make_store()
    mid = s.remember(Memory(symbol="000001", reasoning="银行搭台，试探性买入",
                            regime_tags=["板块轮动"]))
    assert s.review(mid, "loss", -3.2, "搭台的不涨，唱戏的才涨——别买搭台板块")
    ls = s.lessons(symbol="000001")
    assert len(ls) == 1 and ls[0].outcome == "loss"


def test_rank_prefers_same_regime_and_symbol():
    s = make_store()
    a = s.remember(Memory(symbol="600519", sector="白酒",
                          reasoning="情绪冰点抄底龙头", regime_tags=["情绪冰点"]))
    s.remember(Memory(symbol="300750", sector="电池",
                      reasoning="放量突破平台追高", regime_tags=["情绪高潮"]))
    results = rank(s.all(), "冰点期要不要接白酒龙头", regime_tags=["情绪冰点"],
                   symbol="600519", sector="白酒", k=2)
    assert results and results[0][0].id == a
    assert "同一标的" in results[0][2]


def test_usefulness_feedback():
    s = make_store()
    mid = s.remember(Memory(reasoning="测试反馈", regime_tags=["普涨"]))
    s.mark_recalled([mid])
    assert s.mark_useful(mid)
    m = s.get(mid)
    assert m.recall_count == 1 and m.useful_count == 1
