# 06-演化与谱系研究

## 项目演化阶段

### 阶段 1: MVP 基础能力
- 核心能力：项目扫描、Playbook 蒸馏、技术方案评审
- 技术栈：FastAPI + Pydantic + OpenAI Agents SDK
- 存储：本地文件系统

### 阶段 2: Skill Graph 2.0 P0
- 新增：任务驾驶舱、声明式工作流、Capability/Composite/Graph Playbook 三层定义
- 原子能力注册中心
- Graph Playbook 编译与复杂度告警
- human_approval 节点暂停与恢复
- 本地 JSON 持久化与 run snapshot
- SSE 事件流与快照回放

### 阶段 3: 规划中
- orchestrator composite
- 无限画布编辑
- 多人审批流
- 外部资产生成服务编排
- PostgreSQL + pgvector 存储迁移

## 依赖谱系

- **OpenAI Agents SDK**：核心 Agent 执行框架
- **FastAPI**：Web 框架
- **Pydantic**：数据验证
- **MCP**：模型上下文协议
- **Tavily**：网络搜索
- **griffelib**：图结构库

## 与 oss-skill 方法论的关系

ThirdEye 本身就是基于 oss-skill 方法论构建的系统：
- 代码优先：先读取代码结构，再读取文档
- 多源采集：代码、文档、测试、配置、示例
- 三重验证：跨文件复现、能指导新方案、有项目特异性
- 证据分级：`confirmed` | `inferred` | `preference` | `unknown`

## 来源

- 来源文件：`README.md`, `CONTEXT.md`, `CLAUDE.md`
- 来源类型：`doc`
- 时间：2026-05-19
