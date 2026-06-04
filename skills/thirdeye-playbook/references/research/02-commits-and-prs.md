# 02-变更维度研究

## 变更模式分析

基于项目文件结构和代码特征，推断以下变更模式：

### 高频改动区域

| 区域 | 改动类型 | 风险等级 |
|------|----------|----------|
| `apps/api/app/api/` | 新增路由 | 低（路由层隔离） |
| `apps/api/app/schemas/` | 新增/修改 Pydantic 模型 | 中（跨层共享） |
| `apps/api/app/services/` | 业务逻辑变更 | 高（核心逻辑） |
| `apps/api/app/agents/` | Agent 行为/提示词 | 高（LLM 交互） |
| `data/playbooks/` | 新增/更新 playbook | 低（数据层） |

### 回滚与 Breaking Change 处理

- **版本锁定**：关键依赖（`openai-agents==0.17.0`）使用精确版本号锁定，说明团队对依赖稳定性要求高
- **双模式回退**：Agent 执行路径设计为 "SDK 优先 → 回退 deterministic"，说明团队对 LLM 不稳定性有预判
- **配置迁移**：`Settings` 使用 `pydantic-settings` + env 前缀，便于配置变更而不影响代码

### 重构方式

- 服务层职责分离明确：`project_scanner.py`（扫描）、`code_extractor.py`（代码解析）、`document_extractor.py`（文档解析）、`evidence_builder.py`（证据构建）、`playbook_generator.py`（playbook 生成）
- 每个服务模块职责单一，符合 SRP，重构时可按模块独立替换

## 来源

- 来源文件：`apps/api/pyproject.toml`, `apps/api/app/main.py`, `apps/api/app/agents/sdk_runtime.py`, `apps/api/app/services/` 各模块
- 来源类型：`code` / `config`
- 时间：2026-05-19
