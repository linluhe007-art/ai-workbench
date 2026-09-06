"""
ArtifactExtractor - Extract presentable artifacts from ExecutionResult.
Iterates over step results and produces structured artifact dicts.
Supported types: text, markdown, json, list, url.
"""

import json
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactExtractor:
    """
    Extract artifacts from Pipeline execution results.
    Each successful step output is inspected and classified.
    """

    # Keys whose values are treated as primary content
    _CONTENT_KEYS = {"content", "text", "body", "result", "output", "data", "summary", "title"}

    async def extract(
        self,
        task_id: str,
        execution_result: Any,
    ) -> list[dict]:
        """
        Extract artifacts from an ExecutionResult.
        Args:
            task_id: owning task id
            execution_result: PipelineExecutor.ExecutionResult (duck-typed)
        Returns:
            list of artifact dicts
        """
        artifacts: list[dict] = []
        if not execution_result or not hasattr(execution_result, "step_results"):
            return artifacts

        for step_id, step_result in execution_result.step_results.items():
            # Only extract from successful steps
            if not hasattr(step_result, "status"):
                continue
            from app.orchestrator.executor import StepStatus
            if step_result.status != StepStatus.SUCCESS:
                continue

            output = getattr(step_result, "output", None) or {}
            agent_id = getattr(step_result, "agent_id", "unknown")

            step_artifacts = self._extract_from_output(task_id, step_id, agent_id, output)
            artifacts.extend(step_artifacts)

        logger.info("Extracted artifacts", task_id=task_id, count=len(artifacts))
        return artifacts

    def _extract_from_output(
        self,
        task_id: str,
        step_id: str,
        agent_id: str,
        output: dict,
    ) -> list[dict]:
        """Extract artifacts from a single step output dict."""
        artifacts: list[dict] = []
        if not isinstance(output, dict):
            # Scalar output -> text artifact
            artifacts.append(self._make_artifact(
                artifact_type="text",
                name=f"{step_id}_result",
                content=str(output),
                task_id=task_id,
                agent_id=agent_id,
                step_id=step_id,
            ))
            return artifacts

        # Iterate output keys and classify
        for key, value in output.items():
            if key in ("agent", "status", "error", "duration_ms"):
                continue  # skip metadata keys
            artifact = self._classify_and_build(task_id, step_id, agent_id, key, value)
            if artifact:
                artifacts.append(artifact)

        # If no artifacts extracted, wrap entire output as json
        if not artifacts and output:
            artifacts.append(self._make_artifact(
                artifact_type="json",
                name=f"{step_id}_output",
                content=json.dumps(output, ensure_ascii=False, indent=2),
                task_id=task_id,
                agent_id=agent_id,
                step_id=step_id,
            ))

        return artifacts

    def _classify_and_build(
        self,
        task_id: str,
        step_id: str,
        agent_id: str,
        key: str,
        value: Any,
    ) -> dict | None:
        """Classify a single key/value and return an artifact dict."""
        if value is None:
            return None

        # URL detection
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return self._make_artifact(
                artifact_type="url",
                name=key,
                content=value,
                task_id=task_id,
                agent_id=agent_id,
                step_id=step_id,
            )

        # List -> list artifact
        if isinstance(value, list):
            return self._make_artifact(
                artifact_type="list",
                name=key,
                content=json.dumps(value, ensure_ascii=False, indent=2),
                task_id=task_id,
                agent_id=agent_id,
                step_id=step_id,
                raw_data=value,
            )

        # Dict -> json artifact
        if isinstance(value, dict):
            return self._make_artifact(
                artifact_type="json",
                name=key,
                content=json.dumps(value, ensure_ascii=False, indent=2),
                task_id=task_id,
                agent_id=agent_id,
                step_id=step_id,
                raw_data=value,
            )

        # String with markdown indicators
        if isinstance(value, str) and self._looks_like_markdown(value):
            return self._make_artifact(
                artifact_type="markdown",
                name=key,
                content=value,
                task_id=task_id,
                agent_id=agent_id,
                step_id=step_id,
            )

        # Default -> text
        return self._make_artifact(
            artifact_type="text",
            name=key,
            content=str(value),
            task_id=task_id,
            agent_id=agent_id,
            step_id=step_id,
        )

    @staticmethod
    def _looks_like_markdown(text: str) -> bool:
        """Heuristic: does the text contain markdown markers?"""
        markers = ["# ", "## ", "- ", "* ", "```", "**", "__", "> "]
        return any(m in text for m in markers)

    @staticmethod
    def _make_artifact(
        artifact_type: str,
        name: str,
        content: str,
        task_id: str,
        agent_id: str,
        step_id: str,
        raw_data: Any = None,
    ) -> dict:
        """Build a normalized artifact dict."""
        artifact: dict[str, Any] = {
            "type": artifact_type,
            "name": name,
            "content": content,
            "metadata": {
                "task_id": task_id,
                "step_id": step_id,
                "created_by": agent_id,
            },
        }
        if raw_data is not None:
            artifact["raw_data"] = raw_data
        return artifact