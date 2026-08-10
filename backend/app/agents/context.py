"""
AgentContext — Agent 执行上下文
在 Pipeline 执行期间，将 Memory 上下文和上游结果注入到每个步骤。
"""

from dataclasses import dataclass, field


@dataclass
class AgentContext:
    """
    Agent 执行上下文
    携带 Memory 检索结果、上游步骤输出、任务元信息。
    """
    # Memory 检索到的相关文档
    documents: list[dict] = field(default_factory=list)
    # Memory 检索到的相关标签
    tags: list[str] = field(default_factory=list)
    # Memory 内部链接
    related_links: list[str] = field(default_factory=list)
    # Memory 拼接摘要
    memory_summary: str = ""
    # 上游步骤的输出 {step_id: output_dict}
    upstream_results: dict[str, dict] = field(default_factory=dict)
    # 任务描述
    task_description: str = ""
    # Agent 类型 (用于 Memory 差异化查询)
    agent_type: str = ""

    def to_dict(self) -> dict:
        return {
            "documents_count": len(self.documents),
            "tags": self.tags,
            "related_links": self.related_links,
            "memory_summary": self.memory_summary[:500],
            "upstream_steps": list(self.upstream_results.keys()),
        }