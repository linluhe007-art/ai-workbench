# AI 半自动内容生产工作台

> AI 做重活，人做决策 — 个人 AI 内容运营工作台

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](./LICENSE)

## 项目概述

面向个人内容创作者的 AI 半自动内容运营工作台。AI 负责热点采集、内容分析、文章生成、封面方案等，用户负责审核、修改和确认发布。

设计信条是**半自动**：AI 生产内容，人类审核把关，**绝不自动发布**。系统的价值不在于替人发文，而在于把「找选题、读资料、写初稿、配标题」这些重活压缩成一次审核动作。

## 功能亮点

| 能力 | 说明 |
|------|------|
| 🤖 Agent 体系 | Agent 注册表、能力标签、生命周期管理、心跳与调度，可插拔接入不同模型 |
| 🧭 任务编排 | 把一句意图拆成任务 DAG，按依赖调度执行，支持失败重试与单步重跑 |
| 📄 内容生产流水线 | 采集 → 分析 → 写作 → 封面方案 → 标题标签，每步结果落库，可断点续传 |
| ✅ 内容审核中心 | 在线编辑、单步重新生成、版本对比、通过/打回/搁置 |
| 🧠 知识库与长期记忆 | 沉淀用户偏好、写作风格与历史内容，生成时检索并注入 Prompt |
| 🔌 统一模型接入层 | Adapter 模式封装模型差异，密钥只走环境变量，前端零接触 |
| 📊 可观测性 | 结构化日志、调用链路追踪、指标统计与审计记录 |
| 🖥 Web 工作台 | React 前端，覆盖仪表盘、对话、任务中心、审核、知识库等 30 个页面 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript 5.6 + Vite 6 + Ant Design 5 + Zustand 5 + TanStack Query + React Flow |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0（async）+ Pydantic v2 |
| 数据库 | PostgreSQL 16（asyncpg 驱动） |
| 缓存 | Redis 7 |
| 认证 | JWT（python-jose）+ bcrypt（passlib）+ 基于角色的权限层 |
| 日志 | structlog 结构化日志 |
| 测试 | pytest + httpx（后端）、Vitest + Testing Library（前端） |
| 容器化 | Docker + Docker Compose |

## 项目结构

```text
ai-workbench/
├── docker-compose.yml           # 一键编排 postgres / redis / backend / frontend
├── .env.example                 # 环境变量模板（复制为 .env 后填入自己的值）
├── README.md
├── DEPLOYMENT.md                # 部署说明
├── LICENSE                      # MIT
├── docs/
│   └── architecture.md          # 架构设计文档
│
├── frontend/                    # React 18 + TS + Vite
│   └── src/
│       ├── main.tsx             # 入口
│       ├── App.tsx              # 路由
│       ├── pages/               # 30 个页面（仪表盘/对话/任务中心/审核/知识库…）
│       ├── components/          # 通用组件
│       ├── api/                 # API 请求层
│       ├── stores/              # Zustand 状态
│       ├── websocket/           # 实时通信
│       ├── hooks/ types/ utils/
│       └── __tests__/           # 前端测试
│
├── backend/                     # FastAPI
│   ├── requirements.txt
│   ├── alembic/                 # 数据库迁移
│   ├── tests/                   # 127 个测试模块
│   └── app/
│       ├── main.py              # 应用入口
│       ├── config.py            # 配置管理
│       ├── api/v1/              # 34 个路由模块
│       ├── auth/                # 认证、RBAC 权限、中间件
│       ├── agents/              # Agent 注册表 / 生命周期 / 调度 / 心跳
│       ├── llm/                 # 模型接入与适配
│       ├── orchestrator/        # 任务编排引擎
│       ├── planning/            # 任务规划
│       ├── execution/           # 执行器
│       ├── automation/          # 自动化流水线
│       ├── knowledge/ memory/   # 知识库与长期记忆
│       ├── analytics/ observability/ audit/   # 统计、可观测性、审计
│       ├── models/ schemas/     # ORM 模型与 Pydantic Schema
│       └── database/            # PostgreSQL / Redis 连接
│
└── scripts/                     # 辅助脚本
```

## 快速开始

### 环境要求

- Docker & Docker Compose
- Git

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/linluhe007-art/ai-workbench.git
cd ai-workbench

# 2. 复制环境变量
cp .env.example .env

# 3. 启动所有服务
docker compose up --build -d

# 4. 查看日志
docker compose logs -f
```

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

```bash
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
```

> 注意: 本地开发需自行安装 PostgreSQL 和 Redis，并修改 .env 中的连接地址为 localhost。

### 运行测试

```bash
# 后端
cd backend
pip install -r requirements-dev.txt
pytest

# 前端
cd frontend
npm test
```

## 停止服务

```bash
docker compose down           # 停止
docker compose down -v        # 停止并删除数据卷
```

## 当前进度

| 模块 | 状态 |
|------|------|
| 项目骨架与基础设施（Docker Compose 四服务、配置管理、健康检查） | ✅ 已完成 |
| 用户系统（注册/登录/JWT/刷新、RBAC 权限层） | ✅ 已完成 |
| Agent 体系（注册表、能力标签、生命周期、调度、心跳） | ✅ 已完成 |
| 统一模型接入层（Adapter 模式、密钥环境变量注入） | ✅ 已完成 |
| 任务编排（意图拆解、DAG 调度、重试、执行记录） | ✅ 已完成 |
| 内容生产流水线（采集/分析/写作/封面/SEO + 结果持久化） | ✅ 已完成 |
| 内容审核中心（在线编辑、单步重生成、版本管理） | ✅ 已完成 |
| 前端工作台（30 个页面，含实时通信） | ✅ 已完成 |
| 后端测试（127 个测试模块） | ✅ 已完成 |
| 持续集成（GitHub Actions 自动跑测试） | ⏳ 待补 |
| 迁移脚本覆盖全量 Schema（当前仅 1 个初始版本） | ⏳ 待补 |

## 安全现状与部署前必改

> ⚠️ **本项目处于开发阶段，请勿直接暴露到公网。**

### 认证层尚未接入路由（重要）

`backend/app/auth/` 下的 JWT、用户/角色、RBAC 权限层已经实现并有测试覆盖，但**目前还没有挂到任何 API 路由上**——全部 158 个接口当前都是匿名可访问的。因此：

- 只在本机或内网运行，不要做公网部署或端口映射；
- 如需对外提供服务，请先把权限依赖接到路由上。`app/auth/permission.py` 已提供 `require_permission` / `require_any_permission` 装饰器，但接入前需先修正其"找不到 `Request` 参数时静默放行"的行为，否则装饰器会静默失效。

### 部署前必改

- **修改默认管理员账号**：首次启动会在 `backend/app/auth/service.py` 中播种 `admin / admin` 默认账号（拥有全部权限），部署前务必改掉密码或删除该种子逻辑。
- **换掉 JWT 密钥**：`JWT_SECRET_KEY` 的默认值随仓库公开，用它签发 token 等于任何人都能伪造管理员身份。`APP_ENV` 非 development/test 时应用会**拒绝以该占位符启动**；生成方式：`python -c "import secrets; print(secrets.token_urlsafe(48))"`。
- **换掉数据库口令**：`docker-compose.yml` / `.env.example` 里的 `change_me_local_dev_only` 只是占位符，生产部署请替换，并同步更新 `DATABASE_URL`。
- **配置真实模型密钥**：`DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 等已在 `.env.example` 中留空，请填入你自己的密钥。仓库内不含任何 API 密钥或生产凭证（已对**全部提交历史**逐对象扫描确认）。
- **保持开发用身份头关闭**：`AUTH_ALLOW_DEV_USER_HEADER` 默认为 `false`。它只在 `DEBUG=true` 且 `APP_ENV` 为 development/local 时才可能生效，且需要显式打开——请不要在生产环境开启。

## License

[MIT](./LICENSE) — 可自由使用、修改和分发，保留版权声明即可。
