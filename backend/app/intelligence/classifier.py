"""
TaskClassifier - Classifies tasks into predefined types.
Phase 5.1: coding, research, writing, analysis, document, automation.
"""
from enum import Enum
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskType(str, Enum):
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    DOCUMENT = "document"
    AUTOMATION = "automation"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of task classification."""
    task_type: TaskType = TaskType.UNKNOWN
    confidence: float = 0.0
    keywords_matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type.value,
            "confidence": self.confidence,
            "keywords_matched": self.keywords_matched,
        }


class TaskClassifier:
    """
    Classifies user prompts into predefined task types.
    Uses keyword matching for fast, deterministic classification.
    """

    TYPE_KEYWORDS: dict[TaskType, list[str]] = {
        TaskType.CODING: ["code", "bug", "fix", "refactor", "implement", "debug", "function", "api", "endpoint", "script"],
        TaskType.RESEARCH: ["research", "search", "find", "discover", "explore", "investigate", "study", "learn"],
        TaskType.WRITING: ["write", "draft", "compose", "report", "summarize", "article", "blog", "email", "summary"],
        TaskType.ANALYSIS: ["analyze", "analysis", "compare", "evaluate", "assess", "review", "audit", "examine"],
        TaskType.DOCUMENT: ["pdf", "docx", "document", "spreadsheet", "excel", "csv", "slides", "presentation", "file", "convert"],
        TaskType.AUTOMATION: ["automate", "schedule", "cron", "trigger", "workflow", "pipeline", "batch", "periodic"],
    }

    def classify(self, prompt: str) -> ClassificationResult:
        """Classify a prompt and return the best match."""
        prompt_lower = prompt.lower()
        scores: dict[TaskType, tuple[int, list[str]]] = {}

        for task_type, keywords in self.TYPE_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in prompt_lower]
            if matched:
                scores[task_type] = (len(matched), matched)

        if not scores:
            return ClassificationResult(task_type=TaskType.UNKNOWN, confidence=0.0)

        best_type = max(scores, key=lambda k: scores[k][0])
        best_count, best_keywords = scores[best_type]
        total = sum(v[0] for v in scores.values())
        confidence = best_count / total if total > 0 else 0.0

        return ClassificationResult(
            task_type=best_type,
            confidence=round(confidence, 2),
            keywords_matched=best_keywords,
        )