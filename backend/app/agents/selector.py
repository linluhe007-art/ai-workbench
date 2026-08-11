"""
AgentSelector — 动态 Agent 选择器。

根据 capability、Agent 能力匹配度和评分，选择最合适的 Agent。
用于 LLMPlanner 和 Orchestrator 的任务路由。
"""

from typing import TYPE_CHECKING

from typing import TYPE_CHECKING

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry

if TYPE_CHECKING:
    from app.memory.experience import ExperienceMemory

logger = get_logger(__name__)


class AgentSelector:
    """
    动态 Agent 选择器。

    选择逻辑：
    1. 按 capability 查询候选 Agent
    2. 0 个 → 返回 None
    3. 1 个 → 直接返回
    4. 多个 → 按评分排序：
       - capability 匹配数量（更多 = 更好）
       - metadata.score（更高 = 更好）
       - 注册顺序（先注册优先）

    用法：
        selector = AgentSelector(agent_registry)
        agent_id = selector.select("research")
    """

    def __init__(self, registry: "AgentRegistry", experience: "ExperienceMemory | None" = None):
        self._registry = registry
        self._experience = experience

    def select(self, capability: str, context: dict | None = None) -> str | None:
        """
        选择最佳 Agent。
        Args:
            capability: 所需能力标签
            context: 可选上下文（预留扩展）
        Returns:
            最佳 Agent ID，无匹配时返回 None
        """
        candidates = self._registry.get_agents_by_capability(capability)

        if not candidates:
            logger.debug("No agent found for capability", capability=capability)
            return None

        if len(candidates) == 1:
            return candidates[0]

        # 多个候选 → 评分排序
        scored = self._score_candidates(candidates, capability, context)
        best = scored[0]
        logger.debug(
            "Agent selected",
            capability=capability,
            selected=best,
            candidates=len(candidates),
        )
        return best

    def _score_candidates(
        self,
        candidates: list[str],
        capability: str,
        context: dict | None = None,
    ) -> list[str]:
        """对候选 Agent 评分排序（含经验记忆加成）"""
        scores: list[tuple[str, float]] = []
        task_pattern = context.get("task_pattern", capability) if context else capability

        for agent_id in candidates:
            score = 0.0
            agent = self._registry.get(agent_id)
            if agent:
                # 评分维度 1: capability 匹配数量
                agent_caps = agent.get_capabilities()
                score += len(agent_caps) * 10.0

                # 评分维度 2: metadata.score
                if hasattr(agent, "config") and hasattr(agent.config, "extra"):
                    meta_score = agent.config.extra.get("score", 0)
                    score += float(meta_score)

            # 评分维度 3: 经验成功率
            if self._experience:
                exp_rate = self._experience.get_success_rate(task_pattern)
                score += exp_rate * 20.0

            scores.append((agent_id, score))

        # 按分数降序排列
        scores.sort(key=lambda x: x[1], reverse=True)
        return [agent_id for agent_id, _ in scores]

    def select_all(self, capability: str) -> list[str]:
        """返回所有匹配的 Agent ID（未排序）"""
        return self._registry.get_agents_by_capability(capability)