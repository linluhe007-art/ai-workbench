"""
Intent - Natural language intent analysis.
Phase 5.1: Extracts task_type, complexity, required_agents, required_tools, confidence.
"""
from dataclasses import dataclass, field
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Intent:
    """Result of intent analysis on a user prompt."""
    task_type: str = "unknown"
    complexity: str = "simple"
    required_agents: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_prompt: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "complexity": self.complexity,
            "required_agents": self.required_agents,
            "required_tools": self.required_tools,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class IntentAnalyzer:
    """
    Analyzes user prompts to determine intent.

    Uses keyword-based classification as the primary strategy.
    Designed to be extended with LLM-based analysis (placeholder).
    """

    # Keyword patterns for each task type
    PATTERNS: dict[str, list[str]] = {
        "coding": [
            "code", "bug", "fix", "refactor", "implement", "debug",
            "compile", "function", "class", "module", "api", "endpoint",
            "program", "script", "algorithm", "测试", "修复",
        ],
        "research": [
            "research", "search", "find", "discover", "explore", "investigate",
            "look up", "lookup", "google", "learn about", "study",
            "研究", "搜索", "查找", "探索", "调研", "调查",
        ],
        "writing": [
            "write", "draft", "compose", "create document", "generate report",
            "summarize", "summary", "essay", "article", "blog", "email",
            "写", "生成报告", "总结", "文章", "周报", "日报",
        ],
        "analysis": [
            "analyze", "analysis", "compare", "evaluate", "assess",
            "review", "audit", "examine", "inspect", "profile",
            "分析", "比较", "评估", "审查", "检查",
        ],
        "document": [
            "pdf", "docx", "document", "spreadsheet", "excel", "csv",
            "slides", "presentation", "pptx", "file", "convert",
            "文档", "表格", "幻灯片", "文件", "转换",
        ],
        "automation": [
            "automate", "schedule", "cron", "trigger", "workflow",
            "pipeline", "batch", "run every", "periodic",
            "自动", "定时", "周期", "批量",
        ],
    }

    # Complexity indicators
    COMPLEXITY_PATTERNS: dict[str, list[str]] = {
        "complex": ["multi-step", "pipeline", "workflow", "multiple", "several", "and then"],
        "medium": ["with", "using", "create"],
        "simple": [],
    }

    def analyze(self, prompt: str) -> Intent:
        """
        Analyze a user prompt and return an Intent.

        Args:
            prompt: Natural language user input

        Returns:
            Intent with task_type, required_agents, confidence, etc.
        """
        prompt_lower = prompt.lower().strip()

        # Classify task type
        task_type, type_confidence = self._classify_type(prompt_lower)

        # Determine complexity
        complexity = self._determine_complexity(prompt_lower)

        # Map to required agents
        required_agents = self._map_agents(task_type)

        # Map to required tools
        required_tools = self._map_tools(task_type, prompt_lower)

        intent = Intent(
            task_type=task_type,
            complexity=complexity,
            required_agents=required_agents,
            required_tools=required_tools,
            confidence=type_confidence,
            raw_prompt=prompt,
            metadata={"analyzer": "keyword", "prompt_length": len(prompt)},
        )

        logger.info(
            "Intent analyzed",
            task_type=task_type,
            confidence=type_confidence,
            complexity=complexity,
        )
        return intent

    def _classify_type(self, prompt: str) -> tuple[str, float]:
        """Classify the task type based on keyword matching."""
        scores: dict[str, int] = {}
        for task_type, keywords in self.PATTERNS.items():
            score = sum(1 for kw in keywords if kw in prompt)
            if score > 0:
                scores[task_type] = score

        if not scores:
            return "unknown", 0.0

        best = max(scores, key=scores.get)  # type: ignore
        best_score = scores[best]
        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.0

        return best, round(min(confidence, 1.0), 2)

    def _determine_complexity(self, prompt: str) -> str:
        """Determine task complexity from the prompt."""
        for level, keywords in self.COMPLEXITY_PATTERNS.items():
            for kw in keywords:
                if kw in prompt:
                    return level
        return "simple"

    def _map_agents(self, task_type: str) -> list[str]:
        """Map task type to recommended agent list."""
        agent_map = {
            "coding": ["mock"],
            "research": ["researcher"],
            "writing": ["writer"],
            "analysis": ["analyst"],
            "document": ["mock"],
            "automation": ["mock"],
            "unknown": ["mock"],
        }
        return agent_map.get(task_type, ["mock"])

    def _map_tools(self, task_type: str, prompt: str) -> list[str]:
        """Map task type and prompt to recommended tools."""
        tools = []
        tool_map = {
            "coding": ["code_executor"],
            "research": ["memory_search", "web_search"],
            "writing": ["artifact_extractor"],
            "analysis": ["memory_search"],
            "document": ["pdf_reader", "docx_reader"],
            "automation": ["task_scheduler"],
        }
        base = tool_map.get(task_type, [])
        tools.extend(base)

        # Additional tool hints from prompt
        if "pdf" in prompt:
            tools.append("pdf_reader")
        if "excel" in prompt or "csv" in prompt:
            tools.append("spreadsheet_reader")
        if "memory" in prompt or "remember" in prompt:
            tools.append("memory_search")

        return list(set(tools))