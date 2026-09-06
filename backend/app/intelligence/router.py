"""
CommandRouter - Routes user input through Intent -> Task creation.
Phase 5.1: Natural language to task pipeline.
"""
from app.intelligence.intent import IntentAnalyzer, Intent
from app.intelligence.classifier import TaskClassifier
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CommandRouter:
    """
    Routes a natural language command to task creation.

    Pipeline:
        user_prompt -> IntentAnalyzer -> Intent -> TaskClassifier -> create_task

    Also provides WebSocket event emission during the pipeline.
    """

    def __init__(self, intent_analyzer=None, classifier=None, task_creator=None, ws_broadcast=None):
        self._analyzer = intent_analyzer or IntentAnalyzer()
        self._classifier = classifier or TaskClassifier()
        self._task_creator = task_creator  # async fn(task, max_iterations) -> TaskRecord
        self._ws = ws_broadcast  # async fn(task_id, event) -> None

    async def route(self, prompt: str, user_id: str = "") -> dict:
        """
        Route a user command to task creation.

        Args:
            prompt: Natural language user input
            user_id: Optional user context

        Returns:
            {"intent": dict, "task": dict, "task_id": str, "workflow_id": str}
        """
        # Step 1: Analyze intent
        intent = self._analyzer.analyze(prompt)
        classification = self._classifier.classify(prompt)

        if self._ws:
            await self._ws("command_received", {"prompt": prompt[:200], "user_id": user_id})

        if self._ws:
            await self._ws("intent_detected", {
                "task_type": intent.task_type,
                "confidence": intent.confidence,
                "complexity": intent.complexity,
            })

        # Step 2: Create task
        max_iterations = 3
        if intent.complexity == "medium":
            max_iterations = 5
        elif intent.complexity == "complex":
            max_iterations = 7

        task = None
        task_id = ""
        if self._task_creator:
            task = await self._task_creator(prompt, max_iterations)
            task_id = task.task_id

        if self._ws and task_id:
            await self._ws("task_created_from_command", {
                "task_id": task_id,
                "intent": intent.to_dict(),
                "max_iterations": max_iterations,
            })

        return {
            "intent": intent.to_dict(),
            "classification": classification.to_dict(),
            "task_id": task_id,
            "confidence": intent.confidence,
        }