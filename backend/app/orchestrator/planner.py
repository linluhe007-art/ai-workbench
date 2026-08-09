"""
任务规划器 (Planner)
职责：将用户意图拆解为可执行的任务 DAG。
目前为规则引擎实现，后续可替换为 LLM 驱动的规划。
"""

from dataclasses import dataclass, field
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskType(str, Enum):
    RESEARCH = "research"       # 信息采集
    ANALYSIS = "analysis"       # 内容分析
    WRITING = "writing"         # 文章/脚本生成
    IMAGE = "image"             # 图片/封面生成
    SEO = "seo"                 # 标题/标签生成
    CHAT = "chat"               # 自由对话
    CUSTOM = "custom"           # 自定义任务


@dataclass
class TaskStep:
    """单个任务步骤"""
    id: str
    type: TaskType
    description: str
    depends_on: list[str] = field(default_factory=list)
    agent_hint: str = ""        # 建议使用的 Agent
    params: dict = field(default_factory=dict)


@dataclass
class TaskPlan:
    """任务计划 (DAG)"""
    intent: str                 # 用户原始意图
    steps: list[TaskStep]       # 有序步骤列表
    context_query: str = ""     # 需要查询 Memory 的关键词


# 预定义的 Pipeline 模板
CONTENT_PIPELINE = [
    TaskStep(
        id="research", type=TaskType.RESEARCH,
        description="采集相关热点信息",
        agent_hint="research",
    ),
    TaskStep(
        id="analysis", type=TaskType.ANALYSIS,
        description="分析内容价值和选题方向",
        depends_on=["research"],
        agent_hint="analysis",
    ),
    TaskStep(
        id="writing", type=TaskType.WRITING,
        description="生成文章或短视频脚本",
        depends_on=["analysis"],
        agent_hint="writing",
    ),
    TaskStep(
        id="image", type=TaskType.IMAGE,
        description="生成封面方案",
        depends_on=["analysis"],
        agent_hint="image",
    ),
    TaskStep(
        id="seo", type=TaskType.SEO,
        description="生成标题、标签和话题",
        depends_on=["writing"],
        agent_hint="seo",
    ),
]


class TaskPlanner:
    """
    任务规划器
    根据用户输入的意图，自动拆解为结构化的任务步骤。
    当前使用关键词匹配规则，后续可接入 LLM 做更智能的规划。
    """

    # 意图关键词 → Pipeline 模板映射
    INTENT_PATTERNS: dict[str, list[str]] = {
        "content_production": ["写文章", "写一篇", "生成内容", "发布", "新闻", "热点", "脚本", "短视频"],
        "research": ["搜索", "查找", "采集", "调研", "了解"],
        "analysis": ["分析", "评估", "判断", "对比"],
        "writing": ["写", "撰写", "创作", "改写", "润色"],
        "chat": ["你好", "请问", "帮我", "什么是", "怎么"],
    }

    def plan(self, user_input: str) -> TaskPlan:
        """根据用户输入生成任务计划"""
        intent_type = self._classify_intent(user_input)
        logger.info("Task classified", intent=intent_type, input=user_input[:50])

        if intent_type == "content_production":
            return self._plan_content_pipeline(user_input)
        elif intent_type == "research":
            return self._plan_single_task(user_input, TaskType.RESEARCH, "research")
        elif intent_type == "analysis":
            return self._plan_single_task(user_input, TaskType.ANALYSIS, "analysis")
        elif intent_type == "writing":
            return self._plan_single_task(user_input, TaskType.WRITING, "writing")
        else:
            return self._plan_chat(user_input)

    def _classify_intent(self, text: str) -> str:
        """意图分类 (规则引擎)"""
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for intent, keywords in self.INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return "chat"

        return max(scores, key=scores.get)

    def _plan_content_pipeline(self, user_input: str) -> TaskPlan:
        """生成完整内容生产 Pipeline"""
        steps = []
        for template in CONTENT_PIPELINE:
            step = TaskStep(
                id=template.id,
                type=template.type,
                description=template.description,
                depends_on=list(template.depends_on),
                agent_hint=template.agent_hint,
                params={"user_input": user_input},
            )
            steps.append(step)

        # 从用户输入提取关键词用于 Memory 查询
        context_query = self._extract_topic(user_input)

        return TaskPlan(
            intent=user_input,
            steps=steps,
            context_query=context_query,
        )

    def _plan_single_task(self, user_input: str, task_type: TaskType, agent_hint: str) -> TaskPlan:
        """生成单步任务"""
        step = TaskStep(
            id="task_1",
            type=task_type,
            description=user_input,
            agent_hint=agent_hint,
            params={"user_input": user_input},
        )
        return TaskPlan(
            intent=user_input,
            steps=[step],
            context_query=self._extract_topic(user_input),
        )

    def _plan_chat(self, user_input: str) -> TaskPlan:
        """生成对话任务"""
        step = TaskStep(
            id="chat",
            type=TaskType.CHAT,
            description=user_input,
            agent_hint="default",
            params={"user_input": user_input},
        )
        return TaskPlan(intent=user_input, steps=[step])

    def _extract_topic(self, text: str) -> str:
        """从用户输入中提取主题关键词 (简易实现)"""
        # 移除常见动词和虚词，保留核心名词
        stopwords = {"的", "了", "在", "是", "我", "要", "请", "帮", "写", "一篇", "关于", "今天", "下午", "点", "发布"}
        words = set(text) & {"AI", "ai", "人工智能", "科技", "新闻", "技术", "大模型", "GPT", "芯片", "机器人"}
        if words:
            return " ".join(words)
        # 简单返回去掉停用词后的文本
        cleaned = text
        for sw in stopwords:
            cleaned = cleaned.replace(sw, " ")
        return cleaned.strip()[:50] or text[:30]