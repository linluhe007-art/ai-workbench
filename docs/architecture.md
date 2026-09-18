# AI 半自动内容生产工作台 — 系统架构设计文档

> 版本: v0.1 | 日期: 2026-08-08 | 状态: 架构设计基线
>
> 说明：本文是项目初期的架构设计基线，用于记录设计意图与取舍。成稿后各 Phase 的对应模块已陆续实现，**实际进度以 [README](../README.md) 的「当前进度」为准**；文中技术选型（如 Celery、向量数据库）为当时的规划，未全部落地。

---

## 一、系统概述

### 1.1 项目定位

面向个人内容创作者的 AI 半自动内容运营工作台。系统核心理念：**AI 做重活，人做决策**。

- AI 负责：热点采集、内容分析、文章/脚本生成、标题/标签/封面方案生成、最终预览输出
- 用户负责：审核、修改、确认发布

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **半自动** | AI 生产内容，人类审核把关，绝不自动发布 |
| **可扩展** | Adapter Pattern 接入新 AI 模型，不改核心代码 |
| **模块化** | 每个功能模块独立，可单独开发/测试/替换 |
| **生产级** | 完整的错误处理、日志、配置管理、Docker 支持 |
| **渐进式** | MVP 优先，按阶段迭代 |

---

## 二、整体架构

### 2.1 架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend (React + TS)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Dashboard │ │AI Chat   │ │Task Center│ │Content   │ │Knowledge │  │
│  │          │ │          │ │          │ │Review    │ │Base      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                    │  HTTP/REST + WebSocket                          │
└────────────────────┼─────────────────────────────────────────────────┘
                     │
┌────────────────────┼─────────────────────────────────────────────────┐
│              Backend API (FastAPI)                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Auth API  │ │Chat API  │ │Task API  │ │Content   │ │Knowledge │  │
│  │          │ │          │ │          │ │API       │ │API       │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                    │                                                  │
│  ┌─────────────────┼──────────────────────────────────────────────┐  │
│  │         AI Orchestrator (任务编排引擎)                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │Task      │ │Pipeline  │ │Scheduler │ │Result            │  │  │
│  │  │Planner   │ │Engine    │ │          │ │Aggregator        │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                    │                                                  │
│  ┌─────────────────┼──────────────────────────────────────────────┐  │
│  │           Agent Gateway (统一 AI 网关)                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │Agent     │ │Adapter   │ │Rate      │ │Fallback          │  │  │
│  │  │Registry  │ │Factory   │ │Limiter   │ │Handler           │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                    │                                                  │
│  ┌─────────────────┼──────────────────────────────────────────────┐  │
│  │           Services Layer (业务服务层)                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │Content   │ │Crawler   │ │Storage   │ │Notification      │  │  │
│  │  │Service   │ │Service   │ │Service   │ │Service           │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                    │                                                  │
│  ┌─────────────────┼──────────────────────────────────────────────┐  │
│  │           Data Layer (数据层)                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │PostgreSQL│ │Redis     │ │Vector DB │ │Object Storage    │  │  │
│  │  │(主数据)  │ │(缓存/队列)│ │(知识库)  │ │(文件/图片)       │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户输入意图
    │
    ▼
Task Planner (任务拆解)
    │
    ▼
Pipeline Engine (流水线调度)
    │
    ├─► Research Agent ──► 采集热点
    ├─► Analysis Agent ──► 分析价值
    ├─► Writing Agent  ──► 生成文章
    ├─► Image Agent    ──► 生成封面
    └─► SEO Agent      ──► 标题标签
    │
    ▼
Result Aggregator (结果汇总)
    │
    ▼
Content Review (用户审核)
    │
    ├─► 通过 ──► 发布队列
    └─► 修改 ──► 局部重新生成 ──► 回到审核
```

---

## 三、技术选型详表

### 3.1 前端技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | React | 18.x | UI 框架 |
| 语言 | TypeScript | 5.x | 类型安全 |
| 构建 | Vite | 5.x | 开发/构建工具 |
| UI 库 | Ant Design | 5.x | 组件库 |
| 状态 | Zustand | 4.x | 全局状态管理 |
| 网络 | Axios | 1.x | HTTP 请求 |
| 实时 | WebSocket | native | 实时通信 |
| 路由 | React Router | 6.x | 页面路由 |
| 富文本 | TipTap / Slate | - | 内容编辑器 |
| Markdown | react-markdown | - | Markdown 渲染 |
| 图表 | @ant-design/charts | - | 数据可视化 |

### 3.2 后端技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 框架 | FastAPI | Web API 框架 |
| 语言 | Python 3.11+ | 后端语言 |
| ORM | SQLAlchemy 2.0 | 数据库 ORM |
| 迁移 | Alembic | 数据库迁移 |
| 任务队列 | Celery + Redis | 异步任务/定时调度 |
| 缓存 | Redis | 缓存/消息队列 |
| 认证 | python-jose + passlib | JWT 认证 |
| 日志 | structlog | 结构化日志 |
| 配置 | pydantic-settings | 配置管理 |
| HTTP 客户端 | httpx | 异步 HTTP |
| WebSocket | FastAPI WebSocket | 实时通信 |

### 3.3 数据层

| 组件 | 技术 | 用途 |
|------|------|------|
| 主数据库 | PostgreSQL 16 | 业务数据存储 |
| 缓存/队列 | Redis 7 | 缓存/Celery Broker/Session |
| 向量数据库 | ChromaDB (MVP) → Milvus (生产) | 知识库长期记忆 |
| 对象存储 | MinIO (本地) → S3 (生产) | 文件/图片存储 |

### 3.4 基础设施

| 组件 | 技术 | 用途 |
|------|------|------|
| 容器化 | Docker + Docker Compose | 开发/部署环境 |
| 反向代理 | Nginx | 静态资源/API 代理 |
| 进程管理 | Supervisor / Docker | 进程管理 |

---

## 四、模块详细设计

### 4.1 模块1：AI Agent 管理中心

#### 设计模式：Adapter Pattern + Registry Pattern

```
                    ┌─────────────────┐
                    │  BaseAgent       │  (抽象基类)
                    │  + chat()        │
                    │  + execute()     │
                    │  + get_caps()    │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
  ┌───────┴───────┐  ┌──────┴──────┐  ┌───────┴───────┐
  │ CodexAdapter  │  │HunyuanAdapter│  │ClaudeAdapter  │
  │               │  │             │  │               │
  └───────────────┘  └─────────────┘  └───────────────┘
```

#### Agent Registry 数据结构

```python
class AgentConfig(BaseModel):
    id: str                    # 唯一标识, e.g. "codex-v1"
    name: str                  # 显示名称, e.g. "Codex Agent"
    type: AgentType            # 类型枚举
    model: str                 # 模型标识, e.g. "gpt-4"
    api_endpoint: str          # API 端点
    api_key_env: str           # 环境变量名 (不存明文)
    capabilities: list[str]    # 能力标签
    status: AgentStatus        # online/offline/error
    max_concurrent: int        # 最大并发
    rate_limit: RateLimitConfig
    fallback_agent_id: str | None  # 降级 Agent
```

#### 能力标签体系

```
capability_tags = {
    "research":     ["web_search", "rss_parse", "news_crawl"],
    "analysis":     ["content_eval", "trend_analysis", "sentiment"],
    "writing":      ["article_gen", "script_gen", "copywriting"],
    "image":        ["cover_gen", "image_edit", "banner_gen"],
    "seo":          ["title_gen", "tag_suggest", "topic_research"],
    "multimodal":   ["image_understand", "video_analyze"],
}
```

#### 扩展机制

新增 Agent 只需：
1. 创建新文件 backend/agents/adapters/new_agent.py
2. 继承 BaseAgent
3. 实现必要方法
4. 在 config/agents.yaml 注册配置

**零核心代码修改。**

---

### 4.2 模块2：任务编排系统 (Orchestrator)

#### 任务拆解引擎

```
用户意图 ──► Intent Parser ──► Task DAG Builder ──► Scheduler ──► Executor
```

#### Task DAG (有向无环图)

```python
class TaskNode(BaseModel):
    id: str
    type: TaskType          # research/analysis/writing/image/seo
    agent_id: str           # 指定 Agent
    input_template: dict    # 输入模板 (引用上游结果)
    depends_on: list[str]   # 依赖的上游 Task ID
    status: TaskStatus
    result: dict | None
    retry_count: int
    max_retries: int
```

#### 内容生产 Pipeline 模板

```python
CONTENT_PIPELINE = {
    "name": "standard_content",
    "tasks": [
        {"id": "research",  "type": "research",  "depends_on": []},
        {"id": "analysis",  "type": "analysis",  "depends_on": ["research"]},
        {"id": "writing",   "type": "writing",   "depends_on": ["analysis"]},
        {"id": "image",     "type": "image",      "depends_on": ["analysis"]},
        {"id": "seo",       "type": "seo",        "depends_on": ["writing"]},
    ]
}
```

分析和写作串行，封面生成和 SEO 可并行。

#### 状态机

```
pending ──► running ──► success
                │
                └──► failed ──► retry? ──► running
                                │
                                └──► dead_letter
```

---

### 4.3 模块3：内容生产 Pipeline

#### Pipeline 步骤定义

| 步骤 | Agent 类型 | 输入 | 输出 |
|------|-----------|------|------|
| Research | Research Agent | 关键词/话题 | 新闻列表 + 摘要 |
| Analysis | Analysis Agent | 新闻列表 | 价值评分 + 推荐选题 |
| Writing | Writing Agent | 选题 + 风格 | 文章/脚本正文 |
| Image | Image Agent | 文章摘要 | 封面方案描述 |
| SEO | SEO Agent | 文章正文 | 标题 + 标签 + 话题 |

#### 中间状态持久化

每步完成后将结果写入数据库，支持：
- 断点续传
- 单步重跑
- 结果版本管理

---

### 4.4 模块4：内容审核中心

#### 功能清单

```
审核页面
├── 内容预览 (标题/正文/封面/标签)
├── 在线编辑器 (富文本 / Markdown)
├── 单步重新生成
│   ├── 重新生成标题
│   ├── 重新生成正文
│   ├── 重新生成封面
│   └── 重新生成标签
├── 版本历史对比
├── 审批操作
│   ├── 通过 → 发布队列
│   ├── 打回 → 标记原因
│   └── 搁置 → 草稿箱
└── 发布计划
    ├── 选择平台
    ├── 设置时间
    └── 确认发布
```

---

### 4.5 模块5：知识库与长期记忆

#### 存储结构

```python
class KnowledgeEntry(BaseModel):
    id: str
    user_id: str
    category: str       # "preference" / "style" / "history" / "reference"
    content: str        # 文本内容
    metadata: dict      # 元数据
    embedding: list[float]  # 向量 (由后端生成)
    created_at: datetime
```

#### 使用场景

- 生成内容时：检索用户偏好 + 风格 + 历史爆款 → 注入 Prompt
- 采集新闻时：检索用户关注领域 → 过滤/排序
- 生成标题时：检索用户标题风格 → 参考生成

---

### 4.6 模块6：内容采集服务 (Crawler)

#### 架构

```
CrawlerService
├── RSSCrawler          # RSS 订阅源
├── WebParser           # 网页内容解析
├── SearchAPICrawler    # 搜索 API (扩展)
└── SocialCrawler       # 社交媒体 (扩展)
```

#### MVP 数据源

```yaml
sources:
  - name: "36kr AI"
    type: rss
    url: "https://36kr.com/feed"
    category: ai_tech
  - name: "机器之心"
    type: rss
    url: "https://www.jiqizhixin.com/rss"
    category: ai_tech
  - name: "Hacker News"
    type: rss
    url: "https://hnrss.org/newest?q=AI"
    category: tech
```

---

## 五、数据库设计 (ER 模型)

### 5.1 核心表

```
┌─────────────────────────────────────────────────────────┐
│ users                                                    │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ username        VARCHAR     UNIQUE                      │
│ email           VARCHAR     UNIQUE                      │
│ hashed_password VARCHAR                                 │
│ nickname        VARCHAR                                 │
│ avatar_url      VARCHAR                                 │
│ role            VARCHAR     (admin/editor/viewer)       │
│ preferences     JSONB       (用户偏好设置)               │
│ is_active       BOOLEAN     DEFAULT true                │
│ created_at      TIMESTAMPTZ                             │
│ updated_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ agents                                                   │
├─────────────────────────────────────────────────────────┤
│ id              VARCHAR     PK                          │
│ name            VARCHAR                                 │
│ type            VARCHAR     (research/writing/image..)  │
│ model           VARCHAR                                 │
│ api_endpoint    VARCHAR                                 │
│ api_key_env     VARCHAR     (环境变量名)                 │
│ capabilities    JSONB       (能力标签列表)               │
│ status          VARCHAR     (online/offline/error)      │
│ config          JSONB       (Agent特有配置)              │
│ max_concurrent  INTEGER     DEFAULT 5                   │
│ created_at      TIMESTAMPTZ                             │
│ updated_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ conversations                                            │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ user_id         UUID        FK → users                  │
│ agent_id        VARCHAR     FK → agents                 │
│ title           VARCHAR                                 │
│ context         JSONB       (上下文信息)                 │
│ status          VARCHAR     (active/archived)           │
│ created_at      TIMESTAMPTZ                             │
│ updated_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ messages                                                 │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ conversation_id UUID        FK → conversations          │
│ role            VARCHAR     (user/assistant/system)     │
│ content         TEXT                                    │
│ content_type    VARCHAR     (text/markdown/json)        │
│ metadata        JSONB       (token用量/耗时等)          │
│ created_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ tasks                                                    │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ user_id         UUID        FK → users                  │
│ conversation_id UUID        FK → conversations (nullable)│
│ pipeline_id     VARCHAR     (pipeline模板ID)             │
│ type            VARCHAR     (research/analysis/writing..)│
│ parent_task_id  UUID        FK → tasks (nullable, 上级) │
│ agent_id        VARCHAR     FK → agents                 │
│ input_data      JSONB       (任务输入)                   │
│ output_data     JSONB       (任务输出)                   │
│ status          VARCHAR     (pending/running/success/failed)│
│ error_message   TEXT                                    │
│ retry_count     INTEGER     DEFAULT 0                   │
│ started_at      TIMESTAMPTZ                             │
│ completed_at    TIMESTAMPTZ                             │
│ created_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ contents                                                 │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ user_id         UUID        FK → users                  │
│ task_id         UUID        FK → tasks                  │
│ platform        VARCHAR     (toutiao/douyin/xiaohongshu)│
│ title           VARCHAR                                 │
│ body            TEXT                                    │
│ body_format     VARCHAR     (markdown/html/rich_text)   │
│ summary         VARCHAR                                 │
│ cover_url       VARCHAR                                 │
│ cover_prompt    TEXT                                    │
│ tags            JSONB       (标签列表)                   │
│ topics          JSONB       (话题列表)                   │
│ publish_time    TIMESTAMPTZ (建议发布时间)               │
│ status          VARCHAR     (draft/reviewing/approved/published)│
│ version         INTEGER     DEFAULT 1                   │
│ metadata        JSONB       (SEO数据/阅读量预估等)      │
│ created_at      TIMESTAMPTZ                             │
│ updated_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ content_versions                                         │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ content_id      UUID        FK → contents               │
│ version         INTEGER                                 │
│ title           VARCHAR                                 │
│ body            TEXT                                    │
│ tags            JSONB                                   │
│ changed_by      VARCHAR     (user/agent)                │
│ change_reason   VARCHAR                                 │
│ created_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ knowledge_entries                                        │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ user_id         UUID        FK → users                  │
│ category        VARCHAR     (preference/style/history)  │
│ title           VARCHAR                                 │
│ content         TEXT                                    │
│ metadata        JSONB                                   │
│ embedding_id    VARCHAR     (向量数据库中的ID)           │
│ is_active       BOOLEAN     DEFAULT true                │
│ created_at      TIMESTAMPTZ                             │
│ updated_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ platform_accounts                                        │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ user_id         UUID        FK → users                  │
│ platform        VARCHAR     (toutiao/douyin/xiaohongshu)│
│ account_name    VARCHAR                                 │
│ account_id      VARCHAR     (平台账号ID)                │
│ credentials     JSONB       (加密存储的凭证)             │
│ status          VARCHAR     (active/inactive/expired)   │
│ metadata        JSONB       (粉丝数/认证信息等)         │
│ created_at      TIMESTAMPTZ                             │
│ updated_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ crawler_sources                                          │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ name            VARCHAR                                 │
│ type            VARCHAR     (rss/web/api)               │
│ url             VARCHAR                                 │
│ category        VARCHAR                                 │
│ config          JSONB       (解析规则/频率等)            │
│ is_active       BOOLEAN     DEFAULT true                │
│ last_crawled_at TIMESTAMPTZ                             │
│ created_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ crawled_items                                            │
├─────────────────────────────────────────────────────────┤
│ id              UUID        PK                          │
│ source_id       UUID        FK → crawler_sources        │
│ external_id     VARCHAR     (原始ID/URL hash)           │
│ title           VARCHAR                                 │
│ url             VARCHAR                                 │
│ summary         TEXT                                    │
│ content         TEXT                                    │
│ published_at    TIMESTAMPTZ                             │
│ metadata        JSONB                                   │
│ embedding_id    VARCHAR     (向量ID, 用于相似度搜索)    │
│ is_used         BOOLEAN     DEFAULT false               │
│ created_at      TIMESTAMPTZ                             │
└─────────────────────────────────────────────────────────┘
```

### 5.2 索引策略

```sql
-- 高频查询索引
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_contents_user_status ON contents(user_id, status);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_crawled_items_source ON crawled_items(source_id, created_at);
CREATE INDEX idx_knowledge_user_category ON knowledge_entries(user_id, category);
```

---

## 六、API 设计概览

### 6.1 认证

```
POST   /api/v1/auth/register          注册
POST   /api/v1/auth/login             登录 → JWT
POST   /api/v1/auth/refresh           刷新 Token
GET    /api/v1/auth/me                当前用户信息
```

### 6.2 Agent 管理

```
GET    /api/v1/agents                 列表
GET    /api/v1/agents/{id}            详情
GET    /api/v1/agents/{id}/status     状态
POST   /api/v1/agents                 创建 (管理员)
PUT    /api/v1/agents/{id}            更新
```

### 6.3 对话 & 聊天

```
GET    /api/v1/conversations          列表
POST   /api/v1/conversations          创建
GET    /api/v1/conversations/{id}     详情+消息
POST   /api/v1/conversations/{id}/messages   发送消息
WS     /ws/conversations/{id}         WebSocket 实时流
```

### 6.4 任务

```
POST   /api/v1/tasks                  创建任务 (触发 Pipeline)
GET    /api/v1/tasks                  任务列表
GET    /api/v1/tasks/{id}             任务详情
POST   /api/v1/tasks/{id}/retry       重试任务
POST   /api/v1/tasks/{id}/cancel      取消任务
```

### 6.5 内容

```
GET    /api/v1/contents               内容列表
GET    /api/v1/contents/{id}          内容详情
PUT    /api/v1/contents/{id}          编辑内容
POST   /api/v1/contents/{id}/approve  审批通过
POST   /api/v1/contents/{id}/reject   打回
POST   /api/v1/contents/{id}/regenerate/{step}  单步重新生成
GET    /api/v1/contents/{id}/versions 版本历史
```

### 6.6 知识库

```
GET    /api/v1/knowledge              知识列表
POST   /api/v1/knowledge              添加知识
PUT    /api/v1/knowledge/{id}         更新
DELETE /api/v1/knowledge/{id}         删除
POST   /api/v1/knowledge/search       向量搜索
```

### 6.7 采集源

```
GET    /api/v1/crawler/sources        源列表
POST   /api/v1/crawler/sources        添加源
POST   /api/v1/crawler/sources/{id}/trigger  手动触发采集
GET    /api/v1/crawler/items          采集结果列表
```

---

## 七、项目目录结构

```
ai-workbench/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── docs/                           # 文档
│   ├── architecture.md
│   ├── api-spec.md
│   └── development-guide.md
│
├── frontend/                       # 前端项目
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── vite-env.d.ts
│       ├── api/                    # API 请求层
│       │   ├── client.ts           # Axios 实例
│       │   ├── auth.ts
│       │   ├── agents.ts
│       │   ├── conversations.ts
│       │   ├── tasks.ts
│       │   ├── contents.ts
│       │   └── knowledge.ts
│       ├── components/             # 通用组件
│       │   ├── Layout/
│       │   │   ├── index.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   └── Header.tsx
│       │   ├── Chat/
│       │   │   ├── ChatWindow.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── AgentSelector.tsx
│       │   │   └── StreamingText.tsx
│       │   ├── Task/
│       │   │   ├── TaskCard.tsx
│       │   │   ├── TaskTimeline.tsx
│       │   │   └── PipelineView.tsx
│       │   ├── Content/
│       │   │   ├── ContentEditor.tsx
│       │   │   ├── ContentPreview.tsx
│       │   │   ├── VersionHistory.tsx
│       │   │   └── TagEditor.tsx
│       │   └── Common/
│       │       ├── Loading.tsx
│       │       └── ErrorBoundary.tsx
│       ├── pages/                  # 页面
│       │   ├── Dashboard/
│       │   │   └── index.tsx
│       │   ├── Chat/
│       │   │   └── index.tsx
│       │   ├── TaskCenter/
│       │   │   └── index.tsx
│       │   ├── ContentReview/
│       │   │   ├── index.tsx
│       │   │   └── Detail.tsx
│       │   ├── KnowledgeBase/
│       │   │   └── index.tsx
│       │   └── Login/
│       │       └── index.tsx
│       ├── stores/                 # Zustand 状态
│       │   ├── authStore.ts
│       │   ├── chatStore.ts
│       │   ├── taskStore.ts
│       │   └── contentStore.ts
│       ├── hooks/                  # 自定义 Hooks
│       │   ├── useWebSocket.ts
│       │   └── useAuth.ts
│       ├── types/                  # TypeScript 类型
│       │   └── index.ts
│       └── utils/                  # 工具函数
│           ├── token.ts
│           └── format.ts
│
├── backend/                        # 后端项目
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置管理
│   │   ├── dependencies.py         # 依赖注入
│   │   │
│   │   ├── api/                    # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py       # 总路由
│   │   │   │   ├── auth.py
│   │   │   │   ├── agents.py
│   │   │   │   ├── conversations.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── contents.py
│   │   │   │   ├── knowledge.py
│   │   │   │   └── crawler.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── models/                 # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── user.py
│   │   │   ├── agent.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── task.py
│   │   │   ├── content.py
│   │   │   ├── knowledge.py
│   │   │   ├── platform.py
│   │   │   └── crawler.py
│   │   │
│   │   ├── schemas/                # Pydantic Schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── agent.py
│   │   │   ├── conversation.py
│   │   │   ├── task.py
│   │   │   ├── content.py
│   │   │   ├── knowledge.py
│   │   │   └── crawler.py
│   │   │
│   │   ├── agents/                 # Agent 系统
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # BaseAgent 抽象类
│   │   │   ├── registry.py         # Agent Registry
│   │   │   ├── gateway.py          # Agent Gateway
│   │   │   └── adapters/           # 各模型适配器
│   │   │       ├── __init__.py
│   │   │       ├── openai_adapter.py
│   │   │       ├── hunyuan_adapter.py
│   │   │       └── ...
│   │   │
│   │   ├── orchestrator/           # 任务编排
│   │   │   ├── __init__.py
│   │   │   ├── planner.py          # 任务拆解
│   │   │   ├── pipeline.py         # Pipeline 引擎
│   │   │   ├── scheduler.py        # 调度器
│   │   │   └── aggregator.py       # 结果汇总
│   │   │
│   │   ├── services/               # 业务服务
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── content_service.py
│   │   │   ├── knowledge_service.py
│   │   │   ├── crawler_service.py
│   │   │   └── storage_service.py
│   │   │
│   │   ├── database/               # 数据库
│   │   │   ├── __init__.py
│   │   │   ├── session.py
│   │   │   └── redis.py
│   │   │
│   │   ├── tasks/                  # Celery 任务
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── content_tasks.py
│   │   │   └── crawler_tasks.py
│   │   │
│   │   └── utils/                  # 工具
│   │       ├── __init__.py
│   │       ├── security.py
│   │       ├── logger.py
│   │       └── helpers.py
│   │
│   └── config/                     # 配置文件
│       ├── agents.yaml             # Agent 注册配置
│       └── pipelines.yaml          # Pipeline 模板
│
└── scripts/                        # 脚本
    ├── init_db.py
    ├── seed_agents.py
    └── start_dev.sh
```

---

## 八、开发路线图

### Phase 1 — 项目骨架 & 基础设施

**目标**: 前后端项目可运行，数据库连接正常

**范围**:
- 创建完整项目目录结构
- 初始化前端 (React + Vite + TypeScript)
- 初始化后端 (FastAPI + SQLAlchemy)
- 配置 PostgreSQL + Redis + Docker Compose
- 数据库迁移框架 (Alembic)
- 基础配置管理 (.env + pydantic-settings)
- Docker Compose 开发环境
- 健康检查 API

**产出**: docker-compose up 后前后端可访问

---

### Phase 2 — 用户系统

**目标**: 完整的认证体系

**范围**:
- 用户模型 & 迁移
- 注册/登录/Token 刷新 API
- JWT 认证中间件
- 前端登录页面
- 路由守卫
- 用户偏好设置

---

### Phase 3 — Agent Gateway

**目标**: 统一的 AI Agent 接入层

**范围**:
- BaseAgent 抽象类
- Agent Registry + 配置加载
- OpenAI Adapter (首个实现)
- Agent Gateway (路由/限流/降级)
- Agent 管理 API
- 前端 Agent 状态展示

---

### Phase 4 — 任务编排器

**目标**: 任务拆解和 Pipeline 调度

**范围**:
- 任务模型 & 迁移
- Task Planner (意图解析 → 任务 DAG)
- Pipeline Engine (DAG 执行)
- Celery 异步任务
- WebSocket 实时进度推送
- 前端任务中心页面

---

### Phase 5 — 内容生产 Pipeline

**目标**: 端到端内容生成

**范围**:
- Research Agent (RSS 采集)
- Analysis Agent (内容分析)
- Writing Agent (文章生成)
- SEO Agent (标题/标签)
- 内容审核中心
- 单步重新生成
- 版本管理

---

### Phase 6 — 前端工作台

**目标**: 完整的交互界面

**范围**:
- Dashboard 数据面板
- AI Chat 对话界面
- Task Center 流程视图
- Content Review 审核编辑
- Knowledge Base 管理
- WebSocket 实时更新

---

### Phase 7 — 测试 & 优化

**目标**: 生产就绪

**范围**:
- 单元测试 + 集成测试
- API 文档 (自动生成)
- 性能优化
- Docker 生产配置
- 部署文档
- README 完善

---

## 九、安全设计要点

1. **API Key 管理**: 所有 AI 模型密钥存 .env，通过环境变量注入，前端零接触
2. **JWT 认证**: Access Token (15min) + Refresh Token (7d)
3. **密码哈希**: bcrypt
4. **输入校验**: Pydantic 严格校验所有输入
5. **SQL 注入防护**: SQLAlchemy ORM 参数化查询
6. **CORS 配置**: 仅允许前端域名
7. **Rate Limiting**: 基于 Redis 的接口限流
8. **日志脱敏**: 敏感信息 (Token/密码) 不写入日志

---

## 十、开发约定

1. 后端所有 API 遵循 RESTful 规范
2. 响应格式统一: {"code": 0, "data": {...}, "message": "ok"}
3. 错误码分层: 1xxx 认证, 2xxx 业务, 5xxx 系统
4. 前端组件: PascalCase; 后端文件: snake_case
5. Git 提交: conventional commits 格式
6. 每个 Phase 完成后确保代码可运行

---

> **下一步**: 本设计文档成稿后进入编码阶段；各 Phase 的实际完成情况见 [README](../README.md)。
