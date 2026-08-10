"""
ToolExecutor — 工具执行器
接收 ToolCall，通过 ToolRegistry 查找并执行工具，返回 ToolResult。
"""

from dataclasses import dataclass, field

from app.tools.base import ToolCall, ToolResult
from app.tools.registry import ToolRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolCallResult:
    """单次工具调用的完整结果"""
    tool_call: ToolCall
    result: ToolResult


@dataclass
class ToolExecutionReport:
    """批量工具调用的汇总报告"""
    results: list[ToolCallResult] = field(default_factory=list)

    @property
    def all_success(self) -> bool:
        return all(r.result.success for r in self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.result.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.result.success)

    def to_llm_messages(self) -> list[dict]:
        """
        转换为 LLM tool 结果消息列表
        用于将工具执行结果回传给 LLM 继续生成。
        格式: [{"role": "tool", "tool_call_id": "...", "content": "..."}]
        """
        messages = []
        for cr in self.results:
            if cr.result.success:
                import json
                content = json.dumps(cr.result.data, ensure_ascii=False, default=str)
            else:
                content = f"Error: {cr.result.error}"
            messages.append({
                "role": "tool",
                "tool_call_id": cr.tool_call.id,
                "content": content,
            })
        return messages


class ToolExecutor:
    """
    工具执行器
    接收 ToolCall 列表，通过 ToolRegistry 查找并执行。
    """

    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    async def execute(self, tool_call: ToolCall) -> ToolCallResult:
        """执行单个 ToolCall"""
        tool = self._registry.get(tool_call.name)
        if tool is None:
            logger.warning("Tool not found", tool_name=tool_call.name)
            return ToolCallResult(
                tool_call=tool_call,
                result=ToolResult(success=False, error=f"Tool not found: {tool_call.name}"),
            )

        logger.info("Executing tool", tool_name=tool_call.name, call_id=tool_call.id)

        try:
            result = await tool.execute(**tool_call.arguments)
            return ToolCallResult(tool_call=tool_call, result=result)
        except Exception as e:  # noqa: BLE001 — tool execution wraps errors
            logger.error("Tool execution failed", tool_name=tool_call.name, error=str(e))
            return ToolCallResult(
                tool_call=tool_call,
                result=ToolResult(success=False, error=str(e)),
            )

    async def execute_all(self, tool_calls: list[ToolCall]) -> ToolExecutionReport:
        """批量执行多个 ToolCall"""
        results = []
        for tc in tool_calls:
            cr = await self.execute(tc)
            results.append(cr)
        return ToolExecutionReport(results=results)