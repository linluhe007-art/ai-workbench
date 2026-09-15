# AI 半自动内容生产工作台

> AI 做重活，人做决策 — 个人 AI 内容运营工作台

## 项目概述

面向个人内容创作者的 AI 半自动内容运营工作台。AI 负责热点采集、内容分析、文章生成、封面方案等，用户负责审核、修改和确认发布。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design + Zustand |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 16 |
| 缓存/队列 | Redis 7 |
| 容器化 | Docker + Docker Compose |

## 项目结构

`
ai-workbench/
├── docker-compose.yml          # Docker 编排
├── .env                        # 环境变量
├── .env.example                # 环境变量模板
├── README.md
├── docs/
│   └── architecture.md         # 架构设计文档
│
├── frontend/                   # 前端项目
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx            # 入口
│       ├── App.tsx             # 路由
│       ├── api/                # API 请求层
│       ├── components/         # 通用组件
│       │   └── Layout/         # 主布局
│       ├── pages/              # 页面
│       │   ├── Dashboard/      # 工作台面板
│       │   ├── Chat/           # AI 对话
│       │   ├── TaskCenter/     # 任务中心
│       │   ├── ContentReview/  # 内容审核
│       │   ├── KnowledgeBase/  # 知识库
│       │   └── Login/          # 登录
│       ├── stores/             # Zustand 状态
│       ├── hooks/              # 自定义 Hooks
│       ├── types/              # TypeScript 类型
│       └── utils/              # 工具函数
│
├── backend/                    # 后端项目
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # 数据库迁移
│   └── app/
│       ├── main.py             # FastAPI 入口
│       ├── config.py           # 配置管理
│       ├── api/v1/             # API 路由
│       │   ├── router.py       # 路由聚合
│       │   └── health.py       # 健康检查
│       ├── agents/             # Agent 系统 (Phase 3)
│       │   └── adapters/       # 模型适配器
│       ├── orchestrator/       # 任务编排 (Phase 4)
│       ├── services/           # 业务服务
│       ├── models/             # 数据模型
│       ├── schemas/            # Pydantic Schemas
│       ├── database/           # 数据库连接
│       │   ├── __init__.py     # SQLAlchemy 连接
│       │   └── redis.py        # Redis 连接
│       ├── tasks/              # Celery 任务
│       └── utils/              # 工具
│           └── logger.py       # 日志配置
│
└── scripts/                    # 辅助脚本
`

## 快速开始

### 环境要求

- Docker & Docker Compose
- Git

### 安装步骤

`ash
# 1. 克隆项目
git clone https://github.com/linluhe007-art/ai-workbench.git
cd ai-workbench

# 2. 复制环境变量
cp .env.example .env

# 3. 启动所有服务
docker-compose up --build -d

# 4. 查看日志
docker-compose logs -f
`

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/v1/health |
| 数据库健康 | http://localhost:8000/api/v1/health/db |
| Redis 健康 | http://localhost:8000/api/v1/health/redis |
| 全面检查 | http://localhost:8000/api/v1/health/all |

### 本地开发 (不用 Docker)

`ash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
`

> 注意: 本地开发需自行安装 PostgreSQL 和 Redis，并修改 .env 中的连接地址为 localhost。

## 停止服务

`ash
docker-compose down           # 停止
docker-compose down -v        # 停止并删除数据卷
`

## 开发路线图

- [x] Phase 1: 项目骨架 & 基础设施
- [ ] Phase 2: 用户系统 (注册/登录/JWT)
- [ ] Phase 3: Agent Gateway (AI 模型接入)
- [ ] Phase 4: 任务编排器 (Pipeline)
- [ ] Phase 5: 内容生产 Pipeline
- [ ] Phase 6: 前端工作台完善
- [ ] Phase 7: 测试 & 优化

## 部署前必改（安全提示）

本项目用于个人内容运营，**请勿直接暴露到公网**，上线前至少完成以下两项：

- **修改默认管理员账号**：首次启动会在 `backend/app/auth/service.py` 中播种 `admin / admin` 默认账号，部署前务必改掉密码或删除该种子逻辑。
- **配置真实密钥**：`.env` 中的 `DEEPSEEK_API_KEY` 等敏感项已在 `.env.example` 中留空，请填入你自己的密钥；仓库内不含任何真实凭证（已通过全量历史扫描确认）。

## License

[MIT](./LICENSE) — 可自由使用、修改和分发，保留版权声明即可。