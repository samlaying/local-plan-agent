"""
Agent CLI — 交互式命令行调用 Agent 完整链路

用法：
  PYTHONPATH=services/api:services python3 services/agent_cli.py
  PYTHONPATH=services/api:services python3 services/agent_cli.py "这周日下午带孩子去上海人民广场附近玩4小时"

输出风格：每个阶段实时打印 trace，最终展示候选方案详情。
"""

from __future__ import annotations

import asyncio
import os
import sys
import textwrap
from pathlib import Path

# ── 加载 .env ─────────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ── 关闭 httpx/httpcore 噪声 ──────────────────────────────────────────────────
import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("agent").setLevel(logging.WARNING)
logging.getLogger("tools").setLevel(logging.WARNING)

# ── ANSI 颜色 ─────────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
MAGENTA= "\033[35m"

def _c(color: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"{color}{text}{RESET}"
    return text

def _phase(n: int, title: str) -> None:
    print(f"\n{_c(BOLD+CYAN, f'── Phase {n}: {title} ' + '─'*(48-len(title)))}")

def _trace(status: str, agent: str, msg: str) -> None:
    icon = {"running": "·", "done": "✓", "error": "✗"}.get(status, "·")
    color = {"running": DIM, "done": GREEN, "error": RED}.get(status, DIM)
    print(f"  {_c(color, icon)}  {_c(DIM, agent+':')} {msg}")

def _ok(msg: str) -> None:
    print(f"  {_c(GREEN, '✓')}  {msg}")

def _warn(msg: str) -> None:
    print(f"  {_c(YELLOW, '!')}  {msg}")

def _info(key: str, val: str) -> None:
    print(f"  {_c(DIM, key+':')} {val}")

def _hr() -> None:
    print(_c(DIM, "  " + "─"*56))


# ── 主逻辑 ────────────────────────────────────────────────────────────────────

async def run(query: str) -> None:
    from app.core.llm import get_llm_client
    from agent.nodes.intent_parser import IntentParserNode
    from agent.nodes.retrieval_node import RetrievalNode
    from agent.nodes.planning_node import PlanningNode
    from agent.nodes.verifier_node import VerifierNode
    from agent.state.types import PlanningState, MAX_CLARIFICATION_COUNT
    from tools.poi.amap_searcher import AmapSearcher
    from tools.poi.mock_searcher import MockPOISearcher
    from app.repositories.mock_poi_repository import MockPOIRepository

    use_mock = os.getenv("USE_MOCK_POI", "true").lower() in ("true", "1", "yes")

    print()
    print(_c(BOLD, "  LocalPlan Agent CLI"))
    print(_c(DIM,  "  " + "─"*56))
    print(f"  {_c(DIM, 'query:')} {query}")
    print(f"  {_c(DIM, 'POI:  ')} {'Mock 数据' if use_mock else '真实 AMap'}")

    llm_client = get_llm_client()
    intent_node    = IntentParserNode(llm_client=llm_client)
    poi_searcher   = MockPOISearcher(repository=MockPOIRepository()) if use_mock else AmapSearcher()
    retrieval_node = RetrievalNode(searcher=poi_searcher, llm_client=llm_client)
    planning_node  = PlanningNode(llm_client=llm_client)
    verifier_node  = VerifierNode(llm_client=llm_client)

    state = PlanningState(
        session_id="cli-session",
        raw_input=query,
        origin_location=None,
    )

    # ── Phase 1: Intent ───────────────────────────────────────────────────────
    _phase(1, "Intent Parser  意图解析")
    clarification_round = 0
    while True:
        prev = len(state.trace)
        await intent_node.run(state)
        for e in state.trace[prev:]:
            _trace(e.status, e.agent, e.message)

        if state.intent is not None:
            break

        clarification_round += 1
        if clarification_round > MAX_CLARIFICATION_COUNT:
            _warn("追问次数已达上限，使用默认值继续")
            break

        question = state.pending_clarification or "请补充更多信息"
        state.pending_clarification = None
        print()
        print(f"  {_c(YELLOW+BOLD, '? 追问')} {question}")
        try:
            answer = input(f"  {_c(CYAN, '> ')}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  已取消")
            return
        state.raw_input = state.raw_input + " " + answer

    if state.intent is None:
        _warn("意图解析失败，无法继续")
        return

    i = state.intent
    print()
    _ok(f"场景={_c(BOLD, i.scenario)}")
    _info("城市/出发", f"{i.city} · {i.origin}")
    _info("时间",       f"{i.time_window.date}  {i.time_window.start or '?'}–{i.time_window.end or '?'}")
    _info("时长",       f"{i.duration_hours_min}–{i.duration_hours_max} 小时")
    participants_str = "  ".join(
        f"{p.type}×{p.count}" + (f"({p.age}岁)" if p.age else "")
        for p in i.participants
    )
    _info("人员",       participants_str)
    if i.diet_requirements:
        _info("饮食",   "  ".join(i.diet_requirements))
    if i.soft_preferences:
        _info("偏好",   "  ".join(i.soft_preferences))
    if i.hard_constraints:
        _info("约束",   "  ".join(i.hard_constraints))

    # ── Phase 2: Retrieval ────────────────────────────────────────────────────
    _phase(2, "Retrieval  检索 POI + 天气路线")
    prev = len(state.trace)
    await retrieval_node.run(state)
    for e in state.trace[prev:]:
        _trace(e.status, e.agent, e.message)

    print()
    if state.retrieval and state.retrieval.weather:
        _info("天气", state.retrieval.weather)
    _info("策略数", str(len(state.retrieval_strategies)))
    for idx, r in enumerate(state.retrieval_strategies):
        _info(f"  策略{idx} [{r.style}]", f"活动 {len(r.activities)} 条 · 餐厅 {len(r.restaurants)} 条")

    # ── Phase 3: Planning ─────────────────────────────────────────────────────
    _phase(3, "Planning  生成候选方案")
    prev = len(state.trace)
    await planning_node.run(state)
    for e in state.trace[prev:]:
        _trace(e.status, e.agent, e.message)

    # ── Phase 4: Verifier ─────────────────────────────────────────────────────
    _phase(4, "Verifier  两阶段质量校验")
    prev = len(state.trace)
    await verifier_node.run(state)
    for e in state.trace[prev:]:
        _trace(e.status, e.agent, e.message)

    if state.verifier_rejection_reasons:
        print()
        _warn(f"有 {len(state.verifier_rejection_reasons)} 批方案被拒绝")
        reason = state.verifier_rejection_reason
        if reason:
            for line in reason.splitlines()[:5]:
                print(f"  {_c(DIM, line)}")

    # ── 展示候选方案 ──────────────────────────────────────────────────────────
    print()
    print(_c(BOLD+CYAN, "  ── 候选方案 " + "─"*44))

    if not state.candidate_plans:
        _warn("没有通过校验的方案")
        return

    for n, plan in enumerate(state.candidate_plans, 1):
        print()
        print(f"  {_c(BOLD, f'方案 {n}')}{_c(DIM, f'  [{plan.id}]')}")
        print(f"  {_c(BOLD, plan.title)}")
        print(f"  {textwrap.fill(plan.summary, width=60, subsequent_indent='  ')}")
        _hr()
        _info("时长",   f"{plan.total_duration_minutes} 分钟")
        _info("费用",   f"{plan.estimated_cost_min}–{plan.estimated_cost_max} 元/人")
        _info("评分",   f"{plan.score}/100")
        _info("风险",   plan.risk_level)
        print()

        # 行程步骤
        for step in plan.steps:
            if step.type == "transit":
                print(f"  {_c(DIM, f'  {step.start_time} →  {step.title}')}")
            else:
                type_icon = {"activity": "★", "meal": "♨", "extra": "◆"}.get(step.type, "·")
                print(f"  {_c(CYAN, type_icon)} {_c(BOLD, step.start_time)}  {step.title}")
                if step.description:
                    wrapped = textwrap.fill(step.description, width=56, subsequent_indent="              ")
                    print(f"              {_c(DIM, wrapped)}")
                if step.fit_reasons:
                    print(f"              {_c(GREEN, '+ ' + '  '.join(step.fit_reasons[:2]))}")
                if step.risks:
                    print(f"              {_c(YELLOW, '! ' + step.risks[0])}")

        print()
        # POI 卡片
        for poi in plan.pois:
            print(f"  {_c(DIM, '  ')}📍 {_c(BOLD, poi.name)}{_c(DIM, f'  {poi.subcategory}')}")
            print(f"       评分 {poi.rating:.1f}  距离 {poi.distance_km:.1f}km  "
                  f"人均 {poi.price_per_person}元  排队 {poi.queue.wait_minutes}min")
            print(f"       营业 {poi.business_hours.open}–{poi.business_hours.close}"
                  + (f"  可预约" if poi.reservable else ""))

    print()
    print(_c(DIM, "  " + "─"*56))
    print(_c(BOLD+GREEN, f"  完成  共 {len(state.candidate_plans)} 个候选方案"))
    print()


def _poi_fit_score(plan, poi) -> int:
    """返回 POI 在方案中的 audience_fit 综合分（近似）。"""
    af = poi.audience_fit
    return int((af.family + af.child_age_5) / 2)


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        _query = " ".join(sys.argv[1:])
    else:
        print(_c(CYAN, "LocalPlan Agent CLI"))
        print(_c(DIM, "输入你的出行需求（例：这周日下午带孩子从人民广场出发玩4小时）"))
        try:
            _query = input(_c(CYAN, "> ")).strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)
        if not _query:
            sys.exit(0)

    try:
        asyncio.run(run(_query))
    except KeyboardInterrupt:
        print("\n  已中断")
