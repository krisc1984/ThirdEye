# ThirdEye - AI 技术评审系统

基于 `oss-skill` 方法，将本地项目中的工程判断蒸馏为可复用的项目级 review playbook，用于技术方案评审。

当前后端已经接入本仓库内的本地 `src/agents` 代码，并使用 OpenAI Agents SDK 风格的 `Agent + Runner + SQLiteSession` 承载模型测试、Playbook 蒸馏、单轮评审和多轮会话。

## MVP 能力

- 本地项目扫描：读取代码、文档、测试、配置并生成项目概览
- Playbook 蒸馏：产出 `playbook.skill.md`、规则、证据和 metadata
- Playbook 管理：浏览列表、查看详情、查看证据
- 技术方案评审：基于选定 playbook 返回结构化评审结果
- 模型提供方配置：支持 OpenAI 与 OpenAI-compatible provider 的基础配置与连接测试
- 多轮评审会话：基于本地 Agents SDK session 记忆持续追问
- 本地审计日志：记录蒸馏与评审事件，并对密钥与敏感文本做脱敏

## Skill Graph 2.0 P0

当前仓库已经落下 Skill Graph 2.0 的 P0 切片，用来承载“任务驾驶舱”这一层的声明式工作流。

P0 已包含：

- Capability / Composite / Graph Playbook 三层定义
- 原子能力注册中心，支持 `tool | skill | agent | service`
- 原子能力 CRUD 与被引用保护
- 可从应用中已有的 `skill | agent | tool | mcp server` 选择来源对象
- 选择模型后，基于来源对象自动补全原子参数、Schema 与重试策略
- Graph Playbook 编译与复杂度告警
- chain 模式 composite 执行
- `human_approval` 节点暂停与恢复
- 本地 JSON 持久化与 run snapshot
- Graph run SSE 事件流与快照回放
- `/graph` 系列前端页面与任务驾驶舱
- 端到端样例模板：竞品周报

P0 明确不包含：

- orchestrator composite
- 无限画布编辑
- 多人审批流
- 外部资产生成服务编排

## 技术栈

- 后端：Python 3.12+, FastAPI, Pydantic, OpenAI Agents SDK 0.17.0
- 前端：Next.js 15, React 19, TypeScript
- 存储：本地文件系统 JSON/Markdown artifacts

## 前置条件

- Python 3.12+
- Node.js 18+
- `npm`
- 推荐使用 `uv` 管理 Python 依赖

## 快速开始

### 1. 启动后端

```bash
cd apps/api
uv sync
uv run uvicorn app.main:app --reload
```

也可以直接使用仓库根目录脚本同时拉起前后端：

```powershell
./start-dev.ps1
```

默认地址：

```text
http://127.0.0.1:8000
```

### 2. 启动前端

```bash
cd apps/web
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:3000
```

如需显式配置 API 地址：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## 测试与验证

### 后端测试

```bash
cd apps/api
pytest -q
```

### 前端构建验证

```bash
cd apps/web
npm run build
```

### MVP Smoke Flow

```bash
cd apps/api
pytest tests/test_mvp_smoke.py -q
```

也可以参考 [docs/mvp-smoke-test.md](docs/mvp-smoke-test.md) 做手动联调。

### Skill Graph P0 验证

```bash
cd apps/api
pytest tests/test_skill_graph_schemas.py tests/test_skill_graph_storage.py tests/test_skill_graph_registry.py tests/test_skill_graph_compiler.py tests/test_skill_graph_runner.py tests/test_skill_graph_run_events.py tests/test_skill_graph_api.py tests/test_skill_graph_sample_template.py tests/test_skill_graph_smoke.py -q
```

Skill Graph 2.0 的人工验收路径记录在 [docs/skill-graph-acceptance.md](docs/skill-graph-acceptance.md)。

## 模型提供方配置

在左下角齿轮进入 `/settings` 页面后可以创建和测试 provider，旧地址 `/settings/models` 仍可用。

- `openai`：可使用 `responses`
- `openai_compatible`：MVP 只支持 `chat_completions`，并且必须提供 `base_url`

说明：

- API key 会在 API 响应中脱敏
- 当前 MVP 仍将 provider 配置保存在本地 JSON 中
- “发送测试报文” 会真实调用模型 API，不再只是本地配置校验
- 生产环境应改为使用加密存储或 secret manager

## 后端 Agent 架构

后端调用统一收口在 `apps/api/app/agents/`：

- `sdk_runtime.py`：从本仓库 `src/agents` 导入本地 Agents SDK，实现 `Runner`、模型绑定和 `SQLiteSession`
- `review.py`：单轮结构化评审，优先走 Agents SDK，失败时回退 deterministic workflow
- `distillation.py`：Playbook 蒸馏，优先走 Agents SDK，失败时回退 deterministic workflow
- `sdk_chat.py`：多轮评审会话，使用 `SQLiteSession` 维护会话记忆
- `model_providers/adapter.py`：模型连通性测试通过 Agents SDK 发送真实测试报文

运行中的后端会打印 Agents SDK 生命周期日志，默认输出到 API 进程控制台：

- agent start / end
- llm turn start / end
- tool start / end
- tool 参数摘要、tool 返回结果摘要、turn 次数、provider id、model

依赖对齐基于以下核心约束：

- `openai>=2.26.0,<3`
- `openai-agents==0.17.0`
- `pydantic>=2.12.2,<3`
- `griffelib>=2,<3`
- `mcp>=1.19.0,<2`
- `websockets>=15.0,<17`

## 主要路由

后端：

- `GET /health`
- `POST /projects/scan`
- `POST /projects`
- `GET /projects`
- `POST /playbooks/distill`
- `GET /playbooks`
- `GET /playbooks/{playbook_id}`
- `POST /reviews`
- `GET /reviews/{review_id}`
- `POST /reviews/sessions`
- `GET /reviews/sessions/{session_id}`
- `POST /reviews/sessions/{session_id}/messages`
- `GET /graph/capabilities`
- `GET /graph/capabilities/{capability_id}`
- `POST /graph/capabilities`
- `PUT /graph/capabilities/{capability_id}`
- `DELETE /graph/capabilities/{capability_id}`
- `POST /graph/capabilities/draft`
- `GET /graph/composites`
- `POST /graph/composites`
- `POST /graph/composites/{composite_id}/compile`
- `GET /graph/playbooks`
- `POST /graph/playbooks`
- `POST /graph/playbooks/{graph_id}/compile`
- `POST /graph/playbooks/{graph_id}/runs`
- `GET /graph/runs`
- `GET /graph/runs/{run_id}`
- `GET /graph/runs/{run_id}/events`
- `POST /graph/runs/{run_id}/approvals/{approval_id}`
- `GET /model-providers`
- `POST /model-providers`
- `POST /model-providers/{provider_id}/test`

前端：

- `/projects`
- `/playbooks`
- `/playbooks/{id}`
- `/graph`
- `/graph/capabilities`
- `/graph/composites`
- `/graph/playbooks`
- `/graph/runs`
- `/settings`
- `/settings/models`
- `/review`

## 项目结构

```text
ThirdEye/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── agents/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── schemas/
│   │   │   └── services/
│   │   └── tests/
│   └── web/
│       └── src/
├── src/
│   └── agents/
├── data/
│   ├── audit/
│   ├── model-providers/
│   ├── playbooks/
│   ├── projects/
│   ├── reviews/
│   └── skill-graph/
│       ├── assets/
│       ├── capabilities/
│       ├── composites/
│       ├── graph-playbooks/
│       ├── run-events/
│       └── runs/
├── docs/
└── examples/
```

## Skill Graph 样例

仓库内已提供一套可直接跑通的 P0 样例：

- capability:
  `cap_fetch_competitor_homepage`
  `cap_summarize_page_changes`
  `cap_render_weekly_report`
- composite:
  `comp_single_competitor_monitor`
- Graph Playbook:
  `graph_weekly_competitor_report`

样例路径位于 `data/skill-graph/` 下，对应的 smoke test 是 `apps/api/tests/test_skill_graph_smoke.py`。

## 开发原则

1. 代码优先，再读文档
2. 多源采集：代码、文档、测试、配置
3. 证据分级：`confirmed | inferred | preference | unknown`
4. 证据不足时明确暴露不确定性
5. 敏感内容不进入证据摘要和审计日志

## 当前限制

- 本地 `src/agents` 与 Python 环境依赖需要保持对齐，升级 SDK 时要同步检查 `openai / pydantic / griffelib / mcp`
- 数据存储仍为本地 JSON/Markdown，不适合生产
- Review 结果目前以项目规则和基础 heuristics 为主，不是完整 agentic reasoning 系统
- 当前测试仍有若干 `datetime.utcnow()` 弃用 warning，尚未清理

## 明确非目标

- 不做 PR review
- 不做 diff review
- 不接入 GitHub/GitLab
- 不自动修改代码
- 不做 IDE 插件
- 不做多人审批流

## 许可证

MIT

## 致谢

本项目借鉴 [`oss-skill`](https://github.com/lianchi/oss-skill) 的方法论和实现思路。
