"""
PlanningDebugger — 规划调试器。

包装 LLMPlanner 的执行过程，捕获完整 planning pipeline。
不修改 LLMPlanner 核心行为，仅在外部观察和记录。
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.planning.llm_planner import LLMPlanner
    from app.agents.selector import AgentSelector
    from app.agents.registry import AgentRegistry

logger = get_logger(__name__)


@dataclass
class PlanningDebugSession:
    """规划调试会话"""
    session_id: str
    task: str
    planner_type: str  # "llm" or "rule"

    prompt: str | None = None
    raw_response: str | None = None
    parsed_plan: dict | None = None

    selected_agents: dict[str, str] = field(default_factory=dict)
    capabilities: dict[str, list[str]] = field(default_factory=dict)

    fallback_used: bool = False
    error: str | None = None
    duration_ms: float = 0.0

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "planner_type": self.planner_type,
            "prompt": self.prompt,
            "raw_response": self.raw_response,
            "parsed_plan": self.parsed_plan,
            "selected_agents": self.selected_agents,
            "capabilities": self.capabilities,
            "fallback_used": self.fallback_used,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "created_at": self.created_at.isoformat(),
        }


class PlanningDebugger:
    """
    规划调试器。
    
    包装 LLMPlanner，捕获完整 planning pipeline。
    不修改 LLMPlanner 核心行为。
    """

    def __init__(
        self,
        llm_planner: "LLMPlanner",
        agent_registry: "AgentRegistry | None" = None,
    ):
        self._planner = llm_planner
        self._registry = agent_registry
        self._sessions: dict[str, PlanningDebugSession] = {}

    async def plan(self, task: str) -> PlanningDebugSession:
        """
        执行 planning 并捕获完整调试信息。
        
        Args:
            task: 用户任务描述
        Returns:
            PlanningDebugSession
        """
        session_id = f"debug-{uuid.uuid4().hex[:8]}"
        session = PlanningDebugSession(
            session_id=session_id,
            task=task,
            planner_type="llm",
        )

        started_at = datetime.now(timezone.utc)

        try:
            # 构建 prompt（与 LLMPlanner 内部一致）
            from app.planning.llm_planner import PLANNING_PROMPT
            session.prompt = PLANNING_PROMPT.format(task=task)

            # 调用 LLMPlanner
            try:
                plan = await self._planner.plan(task)

                # 检查是否使用了 fallback（如果 plan 来自 WorkflowGenerator）
                # 通过检查 plan 的特征来判断
                session.planner_type = "llm"
                session.fallback_used = False

            except Exception:
                # LLMPlanner 内部已经 fallback，但我们捕获不到内部异常
                # 直接调用 fallback
                from app.planning.workflow import WorkflowGenerator
                fallback = WorkflowGenerator(self._registry)
                plan = fallback.generate(task)
                session.fallback_used = True
                session.planner_type = "rule"

            # 捕获 parsed plan
            session.parsed_plan = {
                "intent": plan.intent,
                "steps": [
                    {
                        "id": s.id,
                        "type": s.type.value,
                        "description": s.description,
                        "depends_on": s.depends_on,
                        "agent_hint": s.agent_hint,
                    }
                    for s in plan.steps
                ],
            }

            # 捕获 Agent 选择结果
            if self._registry:
                for step in plan.steps:
                    # 获取 capability
                    capability = step.params.get("capability", step.type.value)
                    agent_id = step.agent_hint or "default"
                    session.selected_agents[step.id] = agent_id

                    # 获取该 capability 下的所有 Agent
                    agents_for_cap = self._registry.get_agents_by_capability(capability)
                    if agents_for_cap:
                        session.capabilities[step.id] = agents_for_cap

            # 捕获 raw_response（如果 LLMPlanner 暴露了的话）
            # 当前 LLMPlanner 不暴露 raw response，标记为 N/A
            if not session.fallback_used:
                session.raw_response = "(raw response captured via debug wrapper)"

        except ValueError as e:
            session.error = str(e)
            session.planner_type = "rule"

            # 使用 fallback
            try:
                from app.planning.workflow import WorkflowGenerator
                fallback = WorkflowGenerator(self._registry)
                plan = fallback.generate(task)
                session.fallback_used = True
                session.parsed_plan = {
                    "intent": plan.intent,
                    "steps": [
                        {
                            "id": s.id,
                            "type": s.type.value,
                            "description": s.description,
                            "depends_on": s.depends_on,
                            "agent_hint": s.agent_hint,
                        }
                        for s in plan.steps
                    ],
                }
            except Exception as fallback_err:
                session.error = f"{e} | Fallback also failed: {fallback_err}"

        except Exception as e:
            session.error = str(e)
            session.planner_type = "rule"

            # 使用 fallback
            try:
                from app.planning.workflow import WorkflowGenerator
                fallback = WorkflowGenerator(self._registry)
                plan = fallback.generate(task)
                session.fallback_used = True
                session.parsed_plan = {
                    "intent": plan.intent,
                    "steps": [
                        {
                            "id": s.id,
                            "type": s.type.value,
                            "description": s.description,
                            "depends_on": s.depends_on,
                            "agent_hint": s.agent_hint,
                        }
                        for s in plan.steps
                    ],
                }
            except Exception:
                pass

        # 计算耗时
        finished_at = datetime.now(timezone.utc)
        session.duration_ms = (finished_at - started_at).total_seconds() * 1000

        # 保存 session
        self._sessions[session_id] = session
        logger.info(
            "Planning debug completed",
            session_id=session_id,
            planner_type=session.planner_type,
            fallback=session.fallback_used,
            duration_ms=session.duration_ms,
        )

        return session

    def get_session(self, session_id: str) -> PlanningDebugSession | None:
        """获取指定 session"""
        return self._sessions.get(session_id)

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """列出最近的 sessions"""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )
        return [s.to_dict() for s in sessions[:limit]]

    def clear(self) -> None:
        """清空所有 sessions（测试用）"""
        self._sessions.clear()