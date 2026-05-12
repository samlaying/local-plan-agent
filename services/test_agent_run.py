"""
端到端 Agent 链路冒烟测试（不需要 Docker / PostgreSQL）

跳过 ProfileNode（DB）和 FeedbackNode（DB），直接跑：
  IntentParserNode → RetrievalNode → PlanningNode → VerifierNode

运行方式：
  cd /Users/10294698/Documents/local-plan-agent
  PYTHONPATH=services/api:services python3 services/test_agent_run.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("smoke_test")

# 关闭 httpx 的 info 噪声
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def main() -> None:
    from app.core.llm import get_llm_client
    from agent.nodes.intent_parser import IntentParserNode
    from agent.nodes.retrieval_node import RetrievalNode
    from agent.nodes.planning_node import PlanningNode
    from agent.nodes.verifier_node import VerifierNode
    from agent.state.types import PlanningState
    from tools.poi.amap_searcher import AmapSearcher
    from tools.poi.mock_searcher import MockPOISearcher
    from app.repositories.mock_poi_repository import MockPOIRepository

    # ── 测试参数 ──────────────────────────────────────────────
    TEST_QUERY = "这周日下午，我和老婆带5岁孩子从上海人民广场出发，想玩4-5小时，有轻度减脂需求"
    SESSION_ID = "smoke-test-001"
    USE_MOCK_POI = os.getenv("USE_MOCK_POI", "true").lower() in ("true", "1", "yes")
    # ─────────────────────────────────────────────────────────

    sep = "─" * 60

    print(f"\n{sep}")
    print(f"  🚀  Agent 链路冒烟测试")
    print(f"  查询: {TEST_QUERY}")
    print(f"  POI模式: {'Mock' if USE_MOCK_POI else '真实 AMap'}")
    print(f"{sep}\n")

    llm_client = get_llm_client()

    # 初始化节点
    intent_node = IntentParserNode(llm_client=llm_client)
    if USE_MOCK_POI:
        poi_searcher = MockPOISearcher(repository=MockPOIRepository())
    else:
        poi_searcher = AmapSearcher()
    retrieval_node = RetrievalNode(searcher=poi_searcher, llm_client=llm_client)
    planning_node = PlanningNode(llm_client=llm_client, retrieval_node=retrieval_node)
    verifier_node = VerifierNode(llm_client=llm_client)

    # 初始化状态
    state = PlanningState(
        session_id=SESSION_ID,
        raw_input=TEST_QUERY,
        origin_location={"lat": 31.229381, "lng": 121.474539},  # 人民广场
    )

    def print_trace(label: str) -> None:
        new_events = state.trace
        if new_events:
            print(f"  [{label} trace]")
            for e in new_events[-5:]:  # 只打最后 5 条
                print(f"    {e.status:8s} {e.agent}: {e.message}")

    # ── Phase 1: IntentParserNode ─────────────────────────────
    print(f"{'─'*4} Phase 1: IntentParser {'─'*34}")
    prev_len = len(state.trace)
    await intent_node.run(state)
    new_events = state.trace[prev_len:]
    for e in new_events:
        print(f"  {e.status:8s} {e.agent}: {e.message}")

    if state.intent is None:
        print(f"\n  ⚠️  intent 为 None（需要追问）: {state.pending_clarification}")
        print("  追加回答后重试 ...")
        state.raw_input += " 家庭场景，孩子5岁，轻度运动"
        state.pending_clarification = None
        prev_len = len(state.trace)
        await intent_node.run(state)
        for e in state.trace[prev_len:]:
            print(f"  {e.status:8s} {e.agent}: {e.message}")

    if state.intent:
        i = state.intent
        print(f"\n  ✅ Intent 解析成功")
        print(f"     城市={i.city}  出发地={i.origin}")
        print(f"     时间={i.time_window.date} {i.time_window.start}–{i.time_window.end}")
        print(f"     时长={i.duration_hours_min}–{i.duration_hours_max}h  人数={sum(p.count for p in i.participants)}")
        print(f"     场景={i.scenario}  饮食={i.diet_requirements}")
        print(f"     软偏好={i.soft_preferences}")
    else:
        print("  ❌ Intent 解析失败，终止")
        return

    # ── Phase 2: RetrievalNode ────────────────────────────────
    print(f"\n{'─'*4} Phase 2: Retrieval {'─'*36}")
    prev_len = len(state.trace)
    await retrieval_node.run(state)
    for e in state.trace[prev_len:]:
        print(f"  {e.status:8s} {e.agent}: {e.message}")

    print(f"\n  天气: {state.retrieval.weather[:60] if state.retrieval else 'N/A'}...")
    print(f"  策略结果: {len(state.retrieval_strategies)} 个")
    for i, r in enumerate(state.retrieval_strategies):
        print(f"    策略{i} [{r.style}]: 活动{len(r.activities)}条 餐厅{len(r.restaurants)}条")

    # ── Phase 3: PlanningNode ─────────────────────────────────
    print(f"\n{'─'*4} Phase 3: Planning {'─'*37}")
    prev_len = len(state.trace)
    await planning_node.run(state)
    for e in state.trace[prev_len:]:
        print(f"  {e.status:8s} {e.agent}: {e.message}")

    print(f"\n  候选方案: {len(state.candidate_plans)} 个")
    for p in state.candidate_plans:
        print(f"    [{p.id}] {p.title}")
        print(f"      {p.summary}")
        print(f"      时长={p.total_duration_minutes}min  费用={p.estimated_cost_min}–{p.estimated_cost_max}元/人  评分={p.score}")
        print(f"      POI: {[poi.name for poi in p.pois]}")

    # ── Phase 4: VerifierNode ─────────────────────────────────
    print(f"\n{'─'*4} Phase 4: Verifier {'─'*37}")
    prev_len = len(state.trace)
    await verifier_node.run(state)
    for e in state.trace[prev_len:]:
        print(f"  {e.status:8s} {e.agent}: {e.message}")

    print(f"\n  通过校验方案: {len(state.candidate_plans)} 个")
    if state.verifier_rejection_reasons:
        print(f"  被拒绝批次: {len(state.verifier_rejection_reasons)} 轮")
        rej = state.verifier_rejection_reason
        if rej:
            print(f"  拒绝详情:\n    {rej[:300]}")
    for p in state.candidate_plans:
        print(f"    ✅ [{p.id}] {p.title}")

    print(f"\n{sep}")
    print("  测试完成")
    print(f"{sep}\n")


if __name__ == "__main__":
    asyncio.run(main())
