# 05-决策维度研究

## 关键工程事件与取舍

### 1. Agent 执行双模式设计
- **决策**：优先使用 OpenAI Agents SDK，失败时回退到 deterministic workflow
- **原因**：LLM 行为不稳定，需要确定性兜底保障评审可用性
- **权衡**：增加了代码复杂度（两套路径），但提升了系统鲁棒性

### 2. 存储策略演进
- **决策**：MVP 用文件系统，规划迁移 PostgreSQL + pgvector
- **原因**：MVP 快速验证，后续需要向量搜索能力
- **权衡**：文件系统简单但扩展性有限，迁移时需要数据迁移策略

### 3. 依赖版本精确锁定
- **决策**：`openai-agents==0.17.0` 精确锁定
- **原因**：Agent SDK 处于快速演进期，避免 breaking change 影响系统稳定性
- **权衡**：升级成本较高，但保证了当前版本的稳定性

### 4. 敏感数据保护
- **决策**：SecretScanner 扫描敏感文件，内容不入库
- **原因**：密钥、token 等敏感信息不应持久化
- **权衡**：限制了某些调试能力，但符合安全最佳实践

### 5. 术语统一
- **决策**：明确区分 Review Playbook 和 Graph Playbook
- **原因**：避免产品需求和现有代码语言混淆
- **权衡**：增加了学习成本，但提升了沟通清晰度

## 来源

- 来源文件：`README.md`, `CONTEXT.md`, `CLAUDE.md`, `apps/api/app/agents/sdk_runtime.py`, `apps/api/app/services/storage.py`
- 来源类型：`doc` / `code`
- 时间：2026-05-19
