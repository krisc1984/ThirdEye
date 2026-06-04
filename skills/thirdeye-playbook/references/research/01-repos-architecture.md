# 01-架构维度研究

## 项目定位

ThirdEye 是一个本地 AI 技术评审系统，核心能力：
1. **本地项目扫描** — 读取代码、文档、测试、配置并生成项目概览
2. **Playbook 蒸馏** — 产出 `playbook.skill.md`、规则、证据和 metadata
3. **技术方案评审** — 基于选定 playbook 返回结构化评审结果
4. **Skill Graph 2.0 P0** — 任务驾驶舱声明式工作流

## 目录结构

```
ThirdEye/
├── apps/
│   ├── api/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── api/      # 路由层
│   │   │   ├── agents/   # Agent 实现（distill/review/chat）
│   │   │   ├── core/     # 配置（config.py）
│   │   │   ├── schemas/  # Pydantic 数据模型
│   │   │   ├── services/ # 业务服务（扫描、蒸馏、证据、存储等）
│   │   │   └── main.py   # 应用入口
│   │   ├── tests/        # pytest 测试
│   │   └── pyproject.toml
│   └── web/              # Next.js 前端
├── data/
│   └── playbooks/        # 生成的 playbook skill 存储
├── docs/                 # 产品文档和计划
├── src/agents/           # 本地 Agents SDK 实现
├── skills/               # 技能目录（含 thirdeye-playbook）
└── scripts/              # 辅助脚本
```

## 模块边界

| 模块 | 职责 | 边界原则 |
|------|------|----------|
| `apps/api/app/api/` | HTTP 路由层 | 仅负责请求/响应编排，不处理业务逻辑 |
| `apps/api/app/services/` | 业务服务层 | 核心逻辑所在，被 API 路由调用 |
| `apps/api/app/agents/` | Agent 执行层 | 封装 LLM 调用、结构化输出、回退逻辑 |
| `apps/api/app/schemas/` | 数据模型层 | Pydantic 模型定义，被所有层共享 |
| `apps/api/app/core/` | 配置层 | 单一 `Settings` 类，env 前缀 `AI_REVIEW_` |
| `src/agents/` | 本地 Agents SDK 实现 | 被 `agents/` 目录导入使用 |
| `skills/` | 技能目录 | 存储可复用的 playbook skill |

## 依赖策略

- **后端框架**：FastAPI + Pydantic + uvicorn
- **Agent SDK**：OpenAI Agents SDK 0.17.0（严格版本锁定）
- **MCP**：`mcp>=1.19.0,<2`
- **工具**：`griffelib>=2,<3`、`tavily`（搜索）
- **存储**：当前为本地文件系统 JSON/Markdown，规划迁移 PostgreSQL + pgvector
- **前端**：Next.js 15 + React 19 + TypeScript

## 关键架构决策

1. **Agent 执行双模式**：优先走 OpenAI Agents SDK，失败时回退到 deterministic workflow（`sdk_runtime.py` + `review.py`/`distillation.py`）
2. **证据分级**：`confirmed` | `inferred` | `preference` | `unknown`（`evidence_builder.py`）
3. **敏感数据保护**：SecretScanner 扫描 `.env`、密钥文件，内容不入库（`secret_scanner.py`）
4. **配置集中化**：所有配置通过 `Settings` 类，env 前缀 `AI_REVIEW_`，不硬编码
5. **技能目录与 playbook 分离**：`skills/` 存储可复用 skill，`data/playbooks/` 存储项目级 playbook

## 来源

- 来源文件：`README.md`, `CONTEXT.md`, `CLAUDE.md`, `apps/api/pyproject.toml`, `apps/api/app/main.py`, `apps/api/app/core/config.py`, `apps/api/app/services/project_scanner.py`, `apps/api/app/agents/sdk_runtime.py`
- 来源类型：`doc` / `code` / `config`
- 时间：2026-05-19
