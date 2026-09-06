"""
Phase 5.1 tests - IntentAnalyzer, TaskClassifier, CommandRouter, CommandProcessor
"""
import pytest
from app.intelligence.intent import IntentAnalyzer, Intent
from app.intelligence.classifier import TaskClassifier, TaskType, ClassificationResult
from app.intelligence.router import CommandRouter
from app.intelligence.command import CommandProcessor, CommandResult


class TestIntentAnalyzer:
    def test_analyze_research(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("help me research AI trends")
        assert intent.task_type == "research"
        assert intent.confidence > 0

    def test_analyze_writing(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("write a report about sales")
        assert intent.task_type == "writing"

    def test_analyze_coding(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("fix the bug in the API endpoint")
        assert intent.task_type == "coding"

    def test_analyze_analysis(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("analyze the market data and compare trends")
        assert intent.task_type == "analysis"

    def test_analyze_document(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("convert this pdf to excel")
        assert intent.task_type == "document"

    def test_analyze_automation(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("automate the daily report pipeline")
        assert intent.task_type == "automation"

    def test_analyze_unknown(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("xyzzy nothing matches")
        assert intent.task_type == "unknown"
        assert intent.confidence == 0.0

    def test_analyze_returns_complexity(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("create a multi-step pipeline")
        assert intent.complexity == "complex"

    def test_analyze_medium_complexity(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("analyze data using python")
        assert intent.complexity == "medium"

    def test_analyze_simple_complexity(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("search for news")
        assert intent.complexity == "simple"

    def test_analyze_returns_agents(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("research AI")
        assert len(intent.required_agents) > 0

    def test_analyze_returns_tools(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("analyze this pdf document")
        assert "pdf_reader" in intent.required_tools

    def test_analyze_chinese_prompt(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("帮我研究一下人工智能趋势")
        assert intent.task_type == "research"

    def test_analyze_chinese_writing(self):
        analyzer = IntentAnalyzer()
        intent = analyzer.analyze("生成本周的周报")
        assert intent.task_type == "writing"

    def test_intent_to_dict(self):
        intent = Intent(task_type="research", confidence=0.8, complexity="simple")
        d = intent.to_dict()
        assert d["task_type"] == "research"
        assert d["confidence"] == 0.8

    def test_intent_defaults(self):
        intent = Intent()
        assert intent.task_type == "unknown"
        assert intent.confidence == 0.0
        assert intent.required_agents == []


class TestTaskClassifier:
    def test_classify_coding(self):
        c = TaskClassifier()
        result = c.classify("fix the bug and refactor the module")
        assert result.task_type == TaskType.CODING

    def test_classify_research(self):
        c = TaskClassifier()
        result = c.classify("search for new discoveries in ML")
        assert result.task_type == TaskType.RESEARCH

    def test_classify_unknown(self):
        c = TaskClassifier()
        result = c.classify("hello world")
        assert result.task_type == TaskType.UNKNOWN
        assert result.confidence == 0.0

    def test_classify_returns_keywords(self):
        c = TaskClassifier()
        result = c.classify("write an article and summarize the report")
        assert len(result.keywords_matched) > 0

    def test_classification_result_to_dict(self):
        r = ClassificationResult(task_type=TaskType.WRITING, confidence=0.9, keywords_matched=["write", "report"])
        d = r.to_dict()
        assert d["task_type"] == "writing"
        assert d["confidence"] == 0.9

    def test_task_type_enum_values(self):
        assert TaskType.CODING.value == "coding"
        assert TaskType.UNKNOWN.value == "unknown"


class TestCommandRouter:
    @pytest.mark.asyncio
    async def test_route_returns_intent(self):
        router = CommandRouter()
        result = await router.route("research AI trends")
        assert "intent" in result
        assert result["intent"]["task_type"] == "research"

    @pytest.mark.asyncio
    async def test_route_returns_classification(self):
        router = CommandRouter()
        result = await router.route("write a report")
        assert "classification" in result

    @pytest.mark.asyncio
    async def test_route_no_task_creator(self):
        router = CommandRouter()
        result = await router.route("do something")
        assert result["task_id"] == ""


class TestCommandProcessor:
    @pytest.mark.asyncio
    async def test_process_returns_result(self):
        processor = CommandProcessor()
        result = await processor.process("research AI")
        assert isinstance(result, CommandResult)
        assert result.intent["task_type"] == "research"

    @pytest.mark.asyncio
    async def test_process_unknown(self):
        processor = CommandProcessor()
        result = await processor.process("xyz")
        assert result.intent["task_type"] == "unknown"

    def test_get_history(self):
        processor = CommandProcessor()
        assert processor.get_history() == []

    @pytest.mark.asyncio
    async def test_history_tracks_commands(self):
        processor = CommandProcessor()
        await processor.process("research AI")
        history = processor.get_history()
        assert len(history) == 1
        assert history[0]["prompt"] == "research AI"

    def test_clear_history(self):
        processor = CommandProcessor()
        processor.clear_history()
        assert processor.get_history() == []

    def test_command_result_to_dict(self):
        r = CommandResult(intent={"task_type": "research"}, task_id="t1", confidence=0.9)
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["intent"]["task_type"] == "research"