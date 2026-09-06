"""
Phase 4.8 tests - ArtifactExtractor
Covers: text, json, markdown, list, url extraction, empty result,
multiple artifacts, metadata, skip failed, skip metadata keys, mixed results.
"""

import pytest
from app.artifacts.extractor import ArtifactExtractor
from app.orchestrator.executor import StepStatus


class FakeStepResult:
    def __init__(self, status, output=None, agent_id="test-agent", error=""):
        self.status = status
        self.output = output or {}
        self.agent_id = agent_id
        self.error = error


class FakeExecutionResult:
    def __init__(self, step_results=None):
        self.step_results = step_results or {}


@pytest.fixture
def extractor():
    return ArtifactExtractor()


@pytest.mark.asyncio
async def test_extract_empty_result(extractor):
    result = FakeExecutionResult({})
    artifacts = await extractor.extract("t1", result)
    assert artifacts == []

@pytest.mark.asyncio
async def test_extract_none_result(extractor):
    artifacts = await extractor.extract("t1", None)
    assert artifacts == []

@pytest.mark.asyncio
async def test_extract_text_output(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {"summary": "AI trends report"})
    result = FakeExecutionResult({"research": step})
    artifacts = await extractor.extract("t1", result)
    assert len(artifacts) >= 1
    names = [a["name"] for a in artifacts]
    assert "summary" in names

@pytest.mark.asyncio
async def test_extract_json_output(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {"analysis": {"score": 8, "verdict": "good"}})
    result = FakeExecutionResult({"analysis": step})
    artifacts = await extractor.extract("t1", result)
    json_arts = [a for a in artifacts if a["type"] == "json"]
    assert len(json_arts) >= 1

@pytest.mark.asyncio
async def test_extract_list_output(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {"topics": ["AI", "ML", "NLP"]})
    result = FakeExecutionResult({"research": step})
    artifacts = await extractor.extract("t1", result)
    list_arts = [a for a in artifacts if a["type"] == "list"]
    assert len(list_arts) >= 1

@pytest.mark.asyncio
async def test_extract_url_output(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {"link": "https://example.com/article"})
    result = FakeExecutionResult({"research": step})
    artifacts = await extractor.extract("t1", result)
    url_arts = [a for a in artifacts if a["type"] == "url"]
    assert len(url_arts) >= 1
    assert url_arts[0]["content"] == "https://example.com/article"

@pytest.mark.asyncio
async def test_extract_markdown_output(extractor):
    md = "## Title\n\nSome **bold** text\n- item 1\n- item 2"
    step = FakeStepResult(StepStatus.SUCCESS, {"content": md})
    result = FakeExecutionResult({"writing": step})
    artifacts = await extractor.extract("t1", result)
    md_arts = [a for a in artifacts if a["type"] == "markdown"]
    assert len(md_arts) >= 1

@pytest.mark.asyncio
async def test_skip_failed_steps(extractor):
    step = FakeStepResult(StepStatus.FAILED, {"error": "timeout"})
    result = FakeExecutionResult({"research": step})
    artifacts = await extractor.extract("t1", result)
    assert artifacts == []

@pytest.mark.asyncio
async def test_metadata_population(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {"text": "hello"}, agent_id="researcher")
    result = FakeExecutionResult({"s1": step})
    artifacts = await extractor.extract("t1", result)
    assert len(artifacts) >= 1
    meta = artifacts[0]["metadata"]
    assert meta["task_id"] == "t1"
    assert meta["step_id"] == "s1"
    assert meta["created_by"] == "researcher"

@pytest.mark.asyncio
async def test_skip_metadata_keys(extractor):
    output = {"agent": "research", "status": "ok", "error": "", "duration_ms": 100, "summary": "done"}
    step = FakeStepResult(StepStatus.SUCCESS, output)
    result = FakeExecutionResult({"s1": step})
    artifacts = await extractor.extract("t1", result)
    names = [a["name"] for a in artifacts]
    assert "agent" not in names
    assert "status" not in names
    assert "error" not in names
    assert "duration_ms" not in names

@pytest.mark.asyncio
async def test_multiple_artifacts_per_step(extractor):
    output = {"title": "My Article", "tags": ["ai", "ml"], "link": "https://example.com"}
    step = FakeStepResult(StepStatus.SUCCESS, output)
    result = FakeExecutionResult({"writing": step})
    artifacts = await extractor.extract("t1", result)
    assert len(artifacts) == 3

@pytest.mark.asyncio
async def test_scalar_output_becomes_text(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {})
    step.output = "plain string output"
    result = FakeExecutionResult({"s1": step})
    artifacts = await extractor.extract("t1", result)
    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "text"

@pytest.mark.asyncio
async def test_empty_output_dict_no_artifacts(extractor):
    step = FakeStepResult(StepStatus.SUCCESS, {})
    result = FakeExecutionResult({"s1": step})
    artifacts = await extractor.extract("t1", result)
    assert artifacts == []

@pytest.mark.asyncio
async def test_mixed_step_results(extractor):
    s1 = FakeStepResult(StepStatus.SUCCESS, {"summary": "ok"})
    s2 = FakeStepResult(StepStatus.FAILED, {"error": "bad"})
    s3 = FakeStepResult(StepStatus.SUCCESS, {"content": "# Title\n\nBody"})
    result = FakeExecutionResult({"research": s1, "analysis": s2, "writing": s3})
    artifacts = await extractor.extract("t1", result)
    assert len(artifacts) >= 2

@pytest.mark.asyncio
async def test_none_value_skipped(extractor):
    output = {"a": None, "b": "valid"}
    step = FakeStepResult(StepStatus.SUCCESS, output)
    result = FakeExecutionResult({"s1": step})
    artifacts = await extractor.extract("t1", result)
    assert len(artifacts) == 1
    assert artifacts[0]["name"] == "b"


class TestMarkdownDetection:
    def test_heading_detected(self):
        assert ArtifactExtractor._looks_like_markdown("## Heading") is True

    def test_list_detected(self):
        assert ArtifactExtractor._looks_like_markdown("- item 1\n- item 2") is True

    def test_bold_detected(self):
        assert ArtifactExtractor._looks_like_markdown("some **bold** text") is True

    def test_code_block_detected(self):
        assert ArtifactExtractor._looks_like_markdown("```python\nprint()\n```") is True

    def test_plain_text_not_markdown(self):
        assert ArtifactExtractor._looks_like_markdown("just plain text") is False