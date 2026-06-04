# 04-文档维度研究

## 项目文档清单

| 文档 | 内容 | 关键约束 |
|------|------|----------|
| `README.md` | 项目概述、MVP 能力、技术栈、快速开始、测试验证 | MVP 不包含 orchestrator composite、无限画布、多人审批流 |
| `CONTEXT.md` | 术语统一（Review Playbook vs Graph Playbook）、关系定义 | 避免产品需求和现有代码语言混淆 |
| `CLAUDE.md` | Claude Code 工作指南、目录结构、常用命令、架构要点 | 文件存储 MVP 用文件系统，后续迁移 PostgreSQL |
| `docs/mvp-smoke-test.md` | MVP 联调手册 | 端到端验证路径 |
| `docs/skill-graph-acceptance.md` | Skill Graph 2.0 人工验收路径 | P0 切片验收标准 |
| `ThirdEye_微创新报告.md` | 项目创新点分析 | 项目自我定位 |

## 文档中声明的关键约束

1. **MVP 范围边界**：P0 明确不包含 orchestrator composite、无限画布编辑、多人审批流、外部资产生成服务编排
2. **存储策略**：MVP 阶段使用文件系统存储，后续迁移 PostgreSQL + pgvector
3. **模型适配**：`openai` 支持 `responses`；`openai_compatible` MVP 只支持 `chat_completions`，必须提供 `base_url`
4. **依赖对齐**：
   - `openai>=2.26.0,<3`
   - `openai-agents==0.17.0`（精确锁定）
   - `pydantic>=2.12.2,<3`
   - `griffelib>=2,<3`
   - `mcp>=1.19.0,<2`
   - `websockets>=15.0,<17`
5. **敏感数据处理**：API key 在响应中脱敏；生产环境应改为加密存储或 secret manager
6. **忽略规则**：默认忽略 `.git`, `node_modules`, `dist`, `build`, `.next`, `__pycache__`

## 术语统一

| 术语 | 含义 | 避免使用 |
|------|------|----------|
| Review Playbook | 项目级技术评审 skill | Playbook（歧义） |
| Graph Playbook | 顶层业务工作流图 | Review Playbook |
| Capability | 最小可执行技能单元 | Atom, atomic skill |
| Composite | 2-10 个 Capability 组成的子图 | Molecule, combo skill |
| Human Cockpit | 人工确认控制台 | Dashboard, admin panel |
| Knowledge Workspace | 本地资料区 | Knowledge base, asset folder |

## 来源

- 来源文件：`README.md`, `CONTEXT.md`, `CLAUDE.md`, `docs/` 目录
- 来源类型：`doc`
- 时间：2026-05-19
