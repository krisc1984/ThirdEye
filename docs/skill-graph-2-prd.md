# Skill Graph 2.0 PRD

版本: v0.1 / P0 已落地  
日期: 2026-05-13  
关联需求: `docs/技能图谱.md`  
适用产品: ThirdEye

## 1. 背景

ThirdEye 当前已经具备项目扫描、Review Playbook 蒸馏、技术方案评审、多轮会话、知识空间绑定、skill 管理和基础执行追踪能力。现有系统的核心价值是把项目工程判断沉淀成可复用的评审能力，但用户仍主要以对话方式驱动单次评审，缺少面向复杂业务流程的分层编排、状态可视化和人工确认机制。

`docs/技能图谱.md` 提出的 Skill Graph 2.0 要解决的是注意力瓶颈：让用户从逐个驱动原子操作，升级为驾驶顶层业务工作流。它通过三层结构把确定性逻辑固化在图中：Capability -> Composite -> Graph Playbook，并把人的判断保留在关键审批点。

本 PRD 将该方案落到 ThirdEye 当前架构中，并明确一个术语边界：现有代码中的 `Playbook` 指项目评审 skill，本需求中的顶层工作流统一命名为 **Graph Playbook / 图谱剧本**。

实现落地后，前端对外展示文案统一采用“任务驾驶舱”作为 UI 名称，但数据模型和 API 中仍保留 `Graph Playbook` 这一术语。

## 2. 产品目标

### 2.1 目标

- 建立声明式 Skill Graph 注册与执行体系，支持 Capability、Composite、Graph Playbook 三层定义。
- 支持 Graph Playbook 的运行态管理：启动、暂停、继续、失败恢复、人工确认、审计追踪。
- 在 Human Cockpit 中展示多个 Graph Playbook 的进度、健康状态和待处理人工确认点。
- 支持知识空间和运行产物作为图谱上下文，服务后续“AI 漫剧式无限画布”等多步骤内容生产流程。
- 与现有 Review Playbook 并存，不破坏当前技术评审 MVP。

### 2.2 非目标

- v0.1 不做通用低代码自动化平台。
- v0.1 不做任意节点自由拖拽执行引擎。
- v0.1 不承诺所有 Capability 都由 LLM 自动生成。
- v0.1 不做多人权限、组织审批流和跨租户协作。
- v0.1 不接入外部视频生成、图像生成、CRM 等生产服务，只定义扩展接口和样例 Capability。
- v0.1 不替换现有 Review Playbook、Review Session 和 Agent Workspace。

## 3. 用户与场景

### 3.1 目标用户

- AI 工作流设计者: 希望把常用复杂任务拆成稳定、可复用、可观察的图谱。
- 内容生产者: 希望把小说、分镜、素材、提示词、视频片段等多步骤流程自动串起来，只在关键节点判断质量。
- Tech Lead / 架构师: 希望把项目内的评审、验收、发布前检查变成可重复运行的流程。
- Agent 工具使用者: 希望明确每一步 AI 能做什么、何时需要人接管、失败后如何恢复。

### 3.2 核心场景

1. 每周竞品监测报告  
   用户选择“竞品周报 Graph Playbook”，系统自动抓取更新、分析变化、汇总 Markdown，并在最终报告处等待人工确认。

2. 技术方案上线前检查  
   用户提交方案文档，系统依次运行需求完整性检查、Review Playbook 评审、测试计划检查、上线风险检查，并在高风险结论处挂起。

3. 小说到视频工作流  
   用户上传小说或梗概，系统生成剧本、分镜、角色/场景资料库、关键帧提示词和视频片段任务。画布默认展示 L3/L2 进度，人物和场景素材进入 Asset Container。

4. Skill Graph 调试  
   用户展开某个 Composite，查看 Capability 的输入、输出、错误码、重试记录和上下文快照。

## 4. 核心原则

- 人只驾驶最高价值判断点。系统默认折叠 Capability 细节，只把人工确认、阻塞和风险状态推到 Human Cockpit。
- Capability 必须 schema-first。每个 Capability 有输入 schema、输出 schema、错误码、超时和重试配置。
- Composite 必须有崩溃半径。单个 Composite 最多 10 个 Capability，失败只能影响当前子图。
- Graph Playbook 必须有复杂度阈值。超过 8 个 Composite 时提示拆分或增加人工确认点。
- Orchestrator 受控决策。Agent 只能调用定义中白名单 Capability，不能越界自由操作。
- 运行状态可恢复。每次节点执行必须保存输入、输出摘要、状态、错误和上下文引用。
- 与现有 ThirdEye 资产兼容。Review Playbook、Knowledge Workspace、Business Agent、Model Provider 都应能作为图谱资源被引用。

## 5. 术语与现有系统映射

| 新术语 | 定义 | ThirdEye 当前映射 |
| --- | --- | --- |
| Capability | 最小可执行技能单元 | 可复用 function tool、skill action、服务函数 |
| Composite | 2 到 10 个 Capability 组成的有界任务 | 新增实体，类似受控工作流或小型 agent loop |
| Graph Playbook | 顶层业务工作流图 | 新增实体，避免混淆现有 `PlaybookMetadata` |
| Review Playbook | 项目评审 skill | 现有 `PlaybookMetadata`、`playbook.skill.md` |
| Human Cockpit | 工作流驾驶舱 | 可基于现有 `AgentWorkspace` 扩展 |
| Knowledge Workspace | 项目资料区 | 现有 `/knowledge-workspace` API |
| Asset Container | 图谱运行产物集合 | 新增实体，可落在 data artifacts 或知识空间子目录 |

## 6. 功能需求

### 6.1 Capability 注册中心

**描述**: 管理所有可被 Composite 调用的原子能力。

需求：
- 支持通过 YAML/JSON 注册 Capability。
- 支持在 UI 中按 `tool | skill | agent | service` 选择能力类型。
- 支持从应用中已有的 `skill | agent | tool | mcp server` 选择来源对象。
- 支持 capability 的新增、查看、修改、删除。
- 支持选择模型后由大模型结合来源对象生成 capability 草稿；无模型时回退到 deterministic 模板。
- 每个 Capability 包含：
  - `id`
  - `name`
  - `description`
  - `kind`: `tool | skill | agent | service`
  - `input_schema`
  - `output_schema`
  - `timeout_sec`
  - `retry_policy`
  - `error_codes`
  - `permissions`
  - `enabled`
- 支持从现有 skill registry 派生 Capability。
- 支持从 FastAPI 服务函数包装内部 Capability。
- 支持连接测试和 schema 校验。
- 支持查看最近运行成功率、平均耗时、失败原因分布。

优先级: P0

### 6.2 Composite 定义与执行

**描述**: 支持把 Capability 编排为有界任务。

需求：
- 支持两种 Composite 模式：
  - `chain`: 确定性 DAG，按依赖顺序执行。
  - `orchestrator`: 受控 Agent 循环，只能调用白名单 Capability。
- Composite 定义包含：
  - `id`
  - `mode`
  - `nodes`
  - `edges`
  - `input_mapping`
  - `output_mapping`
  - `max_steps`
  - `rollback_policy`
  - `local_context_schema`
- Chain 模式必须在启动前校验 DAG 无环。
- Orchestrator 模式必须限制 `allowed_capabilities` 和 `max_steps`。
- 单个 Composite 超过 10 个 Capability 时保存失败，并给出拆分建议。
- 支持 Composite 级别的暂停、重试、跳过和失败终止。
- 保存 Composite 局部上下文，不允许 Capability 直接读取 Graph Playbook 全局上下文。

优先级: P0

### 6.3 Graph Playbook 定义与编译

**描述**: 顶层工作流以声明式图谱定义，由多个 Composite 和人工确认点组成。

需求：
- Graph Playbook 定义包含：
  - `id`
  - `name`
  - `description`
  - `version`
  - `entry_node`
  - `nodes`
  - `edges`
  - `global_context_schema`
  - `human_approval_nodes`
  - `complexity_policy`
- 节点类型支持：
  - `composite`
  - `human_approval`
  - `condition`
  - `asset_container`
  - `notification`
- 支持条件分支：基于上游输出、人工选择或错误码决定下一节点。
- 注册时编译图谱并验证：
  - 节点引用存在。
  - entry 节点唯一。
  - 无不可达节点。
  - 条件分支有兜底路径。
  - 人工确认节点必须有 approve/reject 路径。
- Graph Playbook 超过 8 个 Composite 时给出 warning；超过 10 个时默认不允许发布为 active，除非显式标记为 experimental。

优先级: P0

### 6.4 分层执行引擎

**描述**: 执行 Capability、Composite 和 Graph Playbook，并维护可恢复状态。

需求：
- 支持启动 Graph Playbook run。
- 支持运行状态：
  - `queued`
  - `running`
  - `waiting_for_human`
  - `paused`
  - `succeeded`
  - `failed`
  - `cancelled`
- 每个 run 保存：
  - Graph Playbook 版本快照
  - 输入参数
  - 全局上下文摘要
  - 节点状态
  - 当前阻塞原因
  - 审计事件
  - 产物路径
- Capability 失败时按 retry policy 自动重试。
- Composite 失败时向 Graph Playbook 抛出标准化错误。
- 连续两个 Composite 进入人工异常处理时，自动暂停整个 Graph Playbook。
- 支持从 `waiting_for_human` 或 `paused` 状态恢复。
- 支持运行时 SSE 事件，复用当前 Review Session 的事件流设计经验。

优先级: P0

### 6.5 Human Cockpit

**描述**: 用户查看 Graph Playbook 状态、处理人工确认点和强制干预。

需求：
- 展示 Graph Playbook run 列表。
- 每个 run 展示：
  - 当前 Composite
  - 总进度
  - 健康状态
  - 最近错误
  - 是否等待人工确认
  - 预计剩余步骤
- 人工确认点展示：
  - 审批标题
  - 上游摘要
  - 推荐决策
  - approve/reject/modify 操作
  - 可选备注
- 支持用户操作：
  - 暂停
  - 继续
  - 取消
  - 重试当前节点
  - 跳过当前节点
  - 回滚到上一个 Composite
- 默认只展示 L3/L2 状态，Capability 细节放在展开面板。

优先级: P0

### 6.6 无限画布视图

**描述**: 将 Graph Playbook 投影为可折叠、可展开、可回溯的无限画布。

需求：
- L3 展示 Graph Playbook 主流程，每个节点代表 Composite 或人工确认点。
- 双击 L3 节点展开 L2 Composite 子图。
- L1 Capability 默认折叠，只在调试模式显示。
- 超过复杂度阈值时在画布上标记安全区、警告区、高风险区。
- 支持 Asset Container 固定在画布侧栏。
- 支持节点版本分支：对某个分镜、报告段落或中间产物发起迭代，生成并列候选。
- 支持查看节点上下文快照。

优先级: P1

### 6.7 Asset Container

**描述**: 管理 Graph Playbook 运行中的可复用产物。

需求：
- 支持产物类型：
  - `document`
  - `image`
  - `prompt`
  - `video_clip`
  - `structured_data`
  - `external_reference`
- 每个 asset 保存：
  - `id`
  - `run_id`
  - `producer_node_id`
  - `name`
  - `type`
  - `path`
  - `summary`
  - `metadata`
  - `version`
- 支持后续 Composite 通过 asset id 引用产物。
- 支持把 asset 落到 Knowledge Workspace 或 `data/graph-runs/`。
- v0.1 只要求文档、提示词和结构化数据；图像/视频作为接口预留。

优先级: P1

### 6.8 Graph Templates

**描述**: 提供可直接试用的模板，降低从 0 到 1 的成本。

首批模板：
- 竞品周报 Graph Playbook。
- 技术方案上线前检查 Graph Playbook。
- 小说到视频前期制作 Graph Playbook。

每个模板包含：
- graph YAML
- Capability 清单
- 示例输入
- 预期输出
- 人工确认点说明

优先级: P1

## 7. 数据模型

### 7.1 CapabilityDefinition

```json
{
  "id": "cap_fetch_competitor_homepage",
  "name": "抓取竞品官网",
  "kind": "tool",
  "description": "读取指定 URL 的公开页面并输出正文摘要。",
  "input_schema": {},
  "output_schema": {},
  "timeout_sec": 30,
  "retry_policy": {
    "max_attempts": 3,
    "backoff": "exponential"
  },
  "error_codes": ["network_error", "permission_denied", "schema_mismatch"],
  "enabled": true
}
```

### 7.2 CompositeDefinition

```json
{
  "id": "comp_single_competitor_monitor",
  "name": "单竞品监测",
  "mode": "chain",
  "nodes": [
    {
      "id": "fetch_homepage",
      "capability_id": "cap_fetch_competitor_homepage"
    },
    {
      "id": "summarize_changes",
      "capability_id": "cap_summarize_changes",
      "depends_on": ["fetch_homepage"]
    }
  ],
  "max_steps": 8,
  "local_context_schema": {}
}
```

### 7.3 GraphPlaybookDefinition

```json
{
  "id": "graph_weekly_competitor_report",
  "name": "竞品周报",
  "version": "1.0.0",
  "entry_node": "monitor_competitors",
  "nodes": [
    {
      "id": "monitor_competitors",
      "type": "composite",
      "composite_id": "comp_single_competitor_monitor"
    },
    {
      "id": "approve_report",
      "type": "human_approval",
      "title": "确认周报是否可发布"
    }
  ],
  "edges": [
    {
      "from": "monitor_competitors",
      "to": "approve_report"
    }
  ],
  "global_context_schema": {}
}
```

### 7.4 GraphRun

```json
{
  "id": "grun_001",
  "graph_playbook_id": "graph_weekly_competitor_report",
  "version": "1.0.0",
  "status": "waiting_for_human",
  "current_node_id": "approve_report",
  "input": {},
  "context_summary": "已完成 4 个竞品监测，发现 2 个定价页变化。",
  "created_at": "2026-05-13T10:00:00+08:00",
  "updated_at": "2026-05-13T10:12:00+08:00"
}
```

## 8. API 需求

### 8.1 Capability API

- `GET /graph/capabilities`
- `POST /graph/capabilities`
- `POST /graph/capabilities/draft`
- `GET /graph/capabilities/{capability_id}`
- `PUT /graph/capabilities/{capability_id}`
- `DELETE /graph/capabilities/{capability_id}`

### 8.2 Composite API

- `GET /graph/composites`
- `POST /graph/composites`
- `GET /graph/composites/{composite_id}`
- `PUT /graph/composites/{composite_id}`
- `POST /graph/composites/{composite_id}/compile`
- `POST /graph/composites/{composite_id}/test-run`

### 8.3 Graph Playbook API

- `GET /graph/playbooks`
- `POST /graph/playbooks`
- `GET /graph/playbooks/{graph_playbook_id}`
- `PUT /graph/playbooks/{graph_playbook_id}`
- `POST /graph/playbooks/{graph_playbook_id}/compile`
- `POST /graph/playbooks/{graph_playbook_id}/runs`

### 8.4 Graph Run API

- `GET /graph/runs`
- `GET /graph/runs/{run_id}`
- `GET /graph/runs/{run_id}/events`
- `POST /graph/runs/{run_id}/pause`
- `POST /graph/runs/{run_id}/resume`
- `POST /graph/runs/{run_id}/cancel`
- `POST /graph/runs/{run_id}/nodes/{node_id}/retry`
- `POST /graph/runs/{run_id}/approvals/{approval_id}`

## 9. 前端需求

### 9.1 Graph Playbooks 页面

- Graph Playbook 列表。
- 模板创建入口。
- 版本、状态、复杂度、最近运行结果。
- 编译错误展示。
- 发布为 active / archived。

### 9.2 Graph Run Cockpit 页面

- 运行列表。
- 状态筛选：运行中、等待人工、失败、已完成。
- 当前节点进度条。
- 人工确认队列。
- 审计事件时间线。
- 节点详情抽屉。

### 9.3 Composite Builder 页面

- v0.1 支持表单和 YAML 编辑。
- v0.1 不要求拖拽画布。
- 提供 schema 校验、DAG 校验和试运行。

### 9.4 Canvas 页面

- P1 实现。
- 使用 Graph Playbook run 作为数据源。
- 节点可折叠、展开、查看快照。
- Asset Container 固定侧栏。
- 节点迭代产生版本分支。

## 10. 技术方案

### 10.1 后端

- 继续使用 FastAPI + Pydantic。
- 新增 `apps/api/app/schemas/skill_graph.py`。
- 新增 `apps/api/app/api/skill_graph.py`。
- 新增 `apps/api/app/services/skill_graph_registry.py`。
- 新增 `apps/api/app/services/skill_graph_runner.py`。
- 新增本地存储目录：

```text
data/
  skill-graph/
    capabilities/
    composites/
    graph-playbooks/
    runs/
    assets/
```

- v0.1 继续使用本地 JSON/Markdown artifacts，暂不强制引入数据库。
- 执行器复用现有 Agents SDK runtime、model provider adapter 和 SSE 事件经验。
- Capability 包装层优先接入现有 skill registry、内部 service function 和 Review Playbook 调用。

当前 P0 已按该方向实现，并进一步 concretize 为：

- schema 文件：
  `apps/api/app/schemas/skill_graph.py`
- 服务文件：
  `skill_graph_registry.py`
  `skill_graph_compiler.py`
  `skill_graph_runner.py`
  `skill_graph_actions.py`
  `skill_graph_run_events.py`
- API 文件：
  `apps/api/app/api/skill_graph.py`
- 持久化目录：
  `data/skill-graph/`
  以及 `skill-graph/run-events`
- 样例模板：
  `graph_weekly_competitor_report`

### 10.2 前端

- 继续使用 Next.js + React。
- 新增路由：
  - `/graph`
  - `/graph/playbooks`
  - `/graph/runs`
  - `/graph/capabilities`
  - `/graph/composites`
- `AppNav` 增加 Graph 入口。
- v0.1 使用列表、详情、YAML 编辑器和状态面板。
- P1 再引入图可视化库；推荐优先评估 React Flow。

当前 P0 已实现：

- `/graph`
- `/graph/capabilities`
- `/graph/composites`
- `/graph/playbooks`
- `/graph/runs`

这些页面以“任务驾驶舱”为统一工作台 UI 文案，并复用现有 `AgentWorkspace` 的布局语言。
其中 `/graph/capabilities` 已升级为原子能力注册工作台，支持列表切换、CRUD、来源对象选择和 AI 草稿补全。

### 10.3 执行策略

- Chain Composite 使用拓扑排序执行。
- Orchestrator Composite 使用受限 Agent loop。
- Graph Playbook 使用状态机推进。
- 每个节点执行前后写入事件。
- 所有外部调用必须通过 Capability 层。
- 所有用户审批必须进入 `waiting_for_human` 状态，并保存恢复点。

## 11. 分期计划

### 11.1 P0: 图谱内核 MVP

- Capability schema 与注册中心。
- Composite chain 模式。
- Graph Playbook 定义、编译和复杂度检查。
- Graph Run 状态机。
- Human approval 节点。
- Cockpit 列表和人工确认队列。
- 本地 artifacts 存储。
- 一个端到端模板：竞品周报。

状态：已实现

对应样例：

- capability:
  `cap_fetch_competitor_homepage`
  `cap_summarize_page_changes`
  `cap_render_weekly_report`
- composite:
  `comp_single_competitor_monitor`
- Graph Playbook:
  `graph_weekly_competitor_report`

### 11.2 P1: 受控智能体与产物

- Composite orchestrator 模式。
- Asset Container。
- 节点上下文快照。
- 技术方案上线前检查模板。
- 小说到视频前期制作模板。
- 无限画布只读视图。

### 11.3 P2: 画布编辑与复杂流程

- Canvas 编辑 Graph Playbook。
- 节点版本分支与对比。
- 跨 Graph Playbook 复用 Composite。
- Capability 运行指标。
- 外部服务连接器市场。

## 12. 验收标准

### 12.1 图谱定义验收

- 用户可以注册至少 5 个 Capability。
- 用户可以创建一个包含 3 个 Capability 的 chain Composite。
- 系统能拒绝有环 Composite。
- 系统能在 Graph Playbook 超过复杂度阈值时给出 warning 或阻止发布。
- Graph Playbook 定义能被编译成可执行状态机。

### 12.2 执行验收

- 用户可以启动一个 Graph Playbook run。
- Chain Composite 能按依赖顺序执行。
- Capability 输入输出不符合 schema 时，当前节点失败并记录标准错误。
- Human approval 节点能挂起 run，并在用户 approve 后继续。
- 用户可以暂停、继续和取消 run。
- Run 事件能通过 SSE 推送到前端。

### 12.3 Cockpit 验收

- 用户能看到所有运行中的 Graph Playbook。
- 用户能快速识别等待人工确认的 run。
- 用户能查看当前 Composite、上游摘要和推荐决策。
- 用户能展开查看 Capability 级别日志。

### 12.4 安全验收

- Capability 权限必须显式声明。
- Graph Run 不得输出 API key、token 或敏感配置值。
- 写文件能力只能写入允许的数据目录或用户明确选择的 Knowledge Workspace。
- Orchestrator 不得调用白名单外 Capability。
- 人工确认备注和运行输入进入审计日志。

## 13. 指标

### 13.1 产品指标

- 用户同时关注 5 个 Graph Playbook run 时，待处理人工确认点数量清晰可见。
- P0 模板从启动到人工确认点的成功率 > 90%。
- 用户处理人工确认点的平均耗时 < 2 分钟。
- 运行失败后能定位到具体 Capability 的比例 = 100%。

### 13.2 工程指标

- Graph Playbook 编译成功率可观测。
- Capability schema 校验覆盖率 = 100%。
- Graph Run 状态转换事件覆盖率 = 100%。
- P0 后端核心单元测试覆盖：schema、compiler、runner、approval resume。

## 14. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 与现有 Review Playbook 术语冲突 | 开发和用户理解混乱 | 新实体统一命名 Graph Playbook，文档中保留 Review Playbook |
| 一上来做无限画布导致范围失控 | MVP 难以闭环 | P0 先做声明式定义、执行和 Cockpit，P1 再做只读画布 |
| Capability 可靠性不足 | 上层流程频繁失败 | schema-first、错误码、重试策略、连接测试、运行指标 |
| Orchestrator 越界行动 | 安全和可预测性下降 | allowed_capabilities 强约束，max_steps 强约束 |
| 图谱过大不可理解 | 用户注意力负担反而上升 | Composite <= 10 Capability，Graph Playbook > 8 Composite 警告 |
| 运行状态不可恢复 | 长流程失败成本高 | 每节点保存快照、事件、输入输出摘要和恢复点 |

## 15. 推荐决策

1. P0 先做“图谱定义 + 编译 + 运行 + 人工确认”，不要先做拖拽画布。
2. 新顶层工作流命名为 `Graph Playbook`，避免与现有 `PlaybookMetadata` 混淆。
3. v0.1 存储继续沿用本地 JSON artifacts，等运行量和查询需求稳定后再迁移数据库。
4. 第一条端到端模板选“竞品周报”，因为它不依赖高风险外部生产动作，适合验证注意力杠杆。
5. “小说到视频”作为 P1 体验模板，先实现资料库、提示词和分镜文档产物，不直接调用视频生成服务。

## 16. 开放问题

- Capability 的 `kind=skill` 是否直接调用当前 `SkillLoader`，还是先包装为统一 action adapter？
- Graph Run 是否需要与现有 Review Session 共享消息模型，还是独立为 workflow event model？
- Knowledge Workspace 中的 asset 是否应由用户手动选择写入路径，还是统一写入系统管理目录后再引用？
- P1 无限画布是否只读即可，还是必须支持编辑和节点重连？
- Orchestrator 模式是否允许多模型配置，还是继承 Graph Playbook run 的单一 provider？

## 18. 当前实现备注

截至当前仓库状态，以下决策已经具体化：

- P0 仅支持 `chain` composite，未实现 orchestrator。
- capability `kind` 当前实现为：`tool | skill | agent | service`。
- `/graph/capabilities` 已支持 CRUD、引用保护删除、来源对象选择，以及基于 model provider 的草稿补全。
- run 状态机当前实现为：
  `pending | running | waiting_for_human | succeeded | failed | cancelled`
- 人工确认通过 `POST /graph/runs/{run_id}/approvals/{approval_id}` 恢复执行。
- SSE 事件流支持快照回放；测试环境可使用 `replay_only=true` 做一次性回放。
- 任务驾驶舱样例使用本地 deterministic handler，不依赖网络访问。

## 17. 参考

- `docs/技能图谱.md`
- `docs/ai-tech-review-system-prd.md`
- `README.md`
- `apps/api/app/schemas/playbook.py`
- `apps/api/app/schemas/review.py`
- `apps/api/app/schemas/knowledge_workspace.py`
- `apps/web/src/components/AgentWorkspace.tsx`
