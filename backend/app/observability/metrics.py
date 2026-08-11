"""
RuntimeMetrics — 运行时指标统计。

从 TraceCollector 的事件中计算运行时指标。
"""

from typing import TYPE_CHECKING

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.observability.collector import TraceCollector

logger = get_logger(__name__)


class RuntimeMetrics:
    """
    运行时指标统计。

    从 TraceCollector 中提取并计算指标：
    - total_tasks: 总任务数
    - success_rate: 成功率
    - average_duration: 平均耗时
    - agent_success_rate: Agent 成功率
    - tool_failure_rate: 工具失败率
    """

    def __init__(self, collector: "TraceCollector"):
        self._collector = collector

    def compute(self) -> dict:
        """计算所有指标"""
        events = self._collector._events

        # 任务级别指标
        task_starts = [e for e in events if e.event_type == "start" and e.component == "loop"]
        task_ends = [e for e in events if e.event_type == "end" and e.component == "loop"]
        task_errors = [e for e in events if e.event_type == "error" and e.component == "loop"]

        total_tasks = len(task_starts)
        successful = len([e for e in task_ends if e.metadata.get("success", False)])
        success_rate = successful / total_tasks if total_tasks > 0 else 0.0

        durations = [e.duration_ms for e in task_ends if e.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Agent 级别指标
        agent_starts = [e for e in events if e.event_type == "start" and e.component == "agent"]
        agent_ends = [e for e in events if e.event_type == "end" and e.component == "agent"]
        agent_errors = [e for e in events if e.event_type == "error" and e.component == "agent"]

        total_agent_runs = len(agent_starts)
        agent_successes = len([e for e in agent_ends if e.metadata.get("success", True)])
        agent_success_rate = agent_successes / total_agent_runs if total_agent_runs > 0 else 0.0

        # Step 级别指标
        step_starts = [e for e in events if e.event_type == "start" and e.component == "executor"]
        step_ends = [e for e in events if e.event_type == "end" and e.component == "executor"]
        step_errors = [e for e in events if e.event_type == "error" and e.component == "executor"]

        total_steps = len(step_starts)
        step_failures = len(step_errors)
        tool_failure_rate = step_failures / total_steps if total_steps > 0 else 0.0

        return {
            "total_tasks": total_tasks,
            "success_rate": round(success_rate, 3),
            "average_duration_ms": round(avg_duration, 1),
            "agent_runs": total_agent_runs,
            "agent_success_rate": round(agent_success_rate, 3),
            "total_steps": total_steps,
            "step_failure_rate": round(tool_failure_rate, 3),
            "total_errors": len(task_errors) + len(agent_errors) + len(step_errors),
        }

    def get_summary(self) -> str:
        """获取指标摘要"""
        m = self.compute()
        return (
            f"Tasks: {m['total_tasks']} (success: {m['success_rate']:.0%}), "
            f"Avg duration: {m['average_duration_ms']:.0f}ms, "
            f"Agent success: {m['agent_success_rate']:.0%}, "
            f"Step failure: {m['step_failure_rate']:.0%}"
        )