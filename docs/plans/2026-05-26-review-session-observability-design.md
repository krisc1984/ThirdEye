# Review Session / Chat Agent 可观察性设计

**Goal:** 为 ThirdEye 的通用 `review session / chat agent` 链路补齐生产可观察性底座，覆盖原始执行日志、时间线、Trace/Task Tree、指标、异常检测、评估与独立观察面板。

**Scope:** 本阶段只做通用 `review session / chat agent`，不扩到 `graph run`。可观察性能力以平台能力方式设计，后续可复用到 `graph run` 与其他业务 Agent。

**Source Article:** `F:\Obsidian\my-vault\Clippings\Agent Harness 可观测性：生产级 AI 项目必须补上的一课.md`

---

## 1. 目标与非目标

### 1.1 目标

1. 为每个 review session 记录独立的原始执行事件流，而不是继续把运行态观测数据混入 `session.messages`。
2. 基于原始事件流派生时间线、Trace 关联、Task Tree、指标、异常和评估结果。
3. 新增独立可观察性面板，入口为 `/observability`，支持会话列表与单会话详情。
4. 保持当前聊天工作区可用，`messages` 继续服务对话展示，不承担全部观测职责。
5. 复用现有 OpenAI Agents SDK tracing 语义，但不依赖外部 tracing export 成功与否。

### 1.2 非目标

1. 本阶段不实现 `graph run` 可观察性改造。
2. 本阶段不做真正的 `LLM-as-judge`。
3. 本阶段不实现完整的回放 diff 与双会话轨迹对比。
4. 本阶段不强制引入模型 `decision` 结构化输出，也不改主 prompt 以实现决策归因。
5. 本阶段不回填历史 review session 的观测数据。

---

## 2. 核心设计决策

本方案基于以下已确认决策：

1. 范围先做通用 `review session / chat agent`。
2. 新增独立 `session event log`，不继续依赖 `session.messages` 承载所有观测数据。
3. 第一版事件协议先覆盖：
   `raw runtime + task status + anomaly + evaluation`
4. 存储格式使用每个 session 一份 `append-only JSONL`。
5. 复用 Agents SDK 的 tracing 语义，不绑定外部 trace export。
6. 任务状态流转采用文章中的显式 `task tree`。
7. 第一版把 `llm_turn` 和 `tool_call` 也建成 task 节点，让任务树先跑起来。
8. 异常检测采用“运行中实时产出 + 会话结束汇总”。
9. 评估先做启发式评估，不做 `LLM-as-judge`。
10. 前端新开独立观察中心，不塞进现有 `AgentWorkspace`。
11. 路由使用通用平台路径 `/observability`。
12. 详情页默认主视图先看“时间线”。
13. 第一版模型输入输出完整落盘。
14. 历史会话不做观测事件回填。

---

## 3. 当前现状与缺口

### 3.1 现状

当前 review session 链路已经具备：

1. `apps/api/app/agents/sdk_runtime.py`
   已通过 `runtime_event_callback` 产出 `llm/tool start/end` 运行事件。
2. `apps/api/app/agents/sdk_chat.py`
   已将部分运行事件转译后写入 `ReviewSessionStore`。
3. `apps/api/app/services/review_sessions.py`
   已支持会话快照、消息列表、resume 状态与 SSE 推送。
4. `apps/api/app/api/reviews.py`
   已提供会话 SSE 流与上下文使用量估算。
5. `apps/web/src/components/AgentWorkspace.tsx`
   已能展示 `user / assistant / llm / tool` 混合时间线。

### 3.2 缺口

当前方案仍缺少：

1. 独立原始事件日志。
2. 稳定的事件协议与 sequence。
3. Trace/Task Tree 的持久化结构。
4. 面向异常与评估的独立事件类型。
5. 独立的 observability 路由与面板。
6. 历史分析入口与可筛选会话列表。

---

## 4. 数据分层

本方案将 review session 数据拆成三层：

### 4.1 会话快照层

继续使用现有：

- `data/review-sessions/{session_id}.json`

职责：

1. 保存当前会话元数据。
2. 保存 `messages`、`last_review`、`resume_available` 等用户面向信息。
3. 提供聊天工作区与会话恢复所需的当前状态。

### 4.2 原始事件层

新增：

- `data/review-session-events/{session_id}.jsonl`

职责：

1. 以 append-only 方式记录原始执行轨迹。
2. 作为时间线、任务树、指标、异常、评估的唯一事实来源。
3. 支持后续离线聚合、回放、对比和导出。

### 4.3 派生摘要层

第一版可按需保存在会话快照中，后续可独立拆出：

- `observability_summary`
- `task_tree_snapshot`
- `metrics_snapshot`

职责：

1. 加速 observability 详情页加载。
2. 避免每次详情页都全量扫完整个 jsonl。
3. 为后续列表页筛选和排序提供稳定字段。

第一版不强制单独落盘派生文件，可先在读取时计算，并在会话完成时写回快照。

---

## 5. 存储结构

新增目录：

```text
data/
  review-session-events/
    rs_xxx.jsonl
```

每行一个 JSON 对象，不允许回写覆盖，不维护数组包装。

建议同时为目录添加：

```text
data/review-session-events/.gitkeep
```

---

## 6. 事件协议

### 6.1 顶层结构

每条事件统一结构如下：

```json
{
  "event_id": "evt_xxx",
  "session_id": "rs_xxx",
  "sequence": 12,
  "event_type": "tool_call_completed",
  "timestamp": "2026-05-26T10:00:00.000000Z",
  "trace_id": "trace_xxx",
  "span_id": "span_xxx",
  "parent_span_id": "span_parent_xxx",
  "runtime_id": "tool_call_123",
  "turn": 2,
  "payload": {}
}
```

### 6.2 字段说明

1. `event_id`
   全局唯一事件 id。
2. `session_id`
   所属 review session。
3. `sequence`
   当前 session 内严格递增序号。
4. `event_type`
   事件类型。
5. `timestamp`
   UTC ISO 时间。
6. `trace_id`
   复用 tracing 语义的 trace 标识。
7. `span_id`
   当前事件对应 span 标识。
8. `parent_span_id`
   父 span 标识，用于构建 Trace Tree。
9. `runtime_id`
   与当前 runtime 执行对象关联的 id，如 `llm_turn_2`、`tool_call_id`。
10. `turn`
    LLM turn 序号。
11. `payload`
    事件业务负载。

### 6.3 第一版事件类型

第一版落地以下事件：

1. `session_started`
2. `user_message`
3. `assistant_message`
4. `model_call_started`
5. `model_call_completed`
6. `tool_call_started`
7. `tool_call_completed`
8. `session_status_changed`
9. `task_created`
10. `task_status_changed`
11. `anomaly_detected`
12. `evaluation_recorded`
13. `session_completed`

### 6.4 预留事件类型

先定义但不在第一版强依赖：

1. `decision_recorded`
2. `replay_requested`
3. `replay_compared`
4. `task_waiting_child`
5. `delegated_agent_started`
6. `delegated_agent_completed`

---

## 7. 任务树模型

### 7.1 设计原则

任务树不是对话树，而是执行树。第一版即使没有真实子 Agent，也要先把 `llm_turn` 与 `tool_call` 建模为 task 节点。

### 7.2 Task 结构

```json
{
  "task_id": "task_xxx",
  "parent_task_id": "task_parent_xxx",
  "session_id": "rs_xxx",
  "source_event_id": "evt_xxx",
  "title": "调用 write_file_chunk",
  "kind": "tool_call",
  "status": "running",
  "created_at": "2026-05-26T10:00:00.000000Z",
  "updated_at": "2026-05-26T10:00:02.000000Z",
  "summary": "第 2 轮调用 write_file_chunk"
}
```

### 7.3 Task kind

第一版支持：

1. `session`
2. `llm_turn`
3. `tool_call`
4. `delegated_agent`

其中 `delegated_agent` 先预留。

### 7.4 Task status

统一使用：

1. `pending`
2. `planning`
3. `running`
4. `waiting_child`
5. `succeeded`
6. `failed`
7. `cancelled`

### 7.5 第一版映射规则

1. 创建 session 时创建 `root session task`。
2. `model_call_started` 时创建 `llm_turn task`。
3. `model_call_completed` 时将该 `llm_turn task` 转为 `succeeded` 或 `failed`。
4. `tool_call_started` 时在当前 `llm_turn task` 下创建 `tool_call task`。
5. `tool_call_completed` 时将该 `tool_call task` 转为 `succeeded` 或 `failed`。
6. session 正常结束时 root task 转为 `succeeded`。
7. 取消时 root task 转为 `cancelled`。
8. 不可恢复错误时 root task 转为 `failed`。

---

## 8. Trace 关联策略

### 8.1 复用策略

第一版不依赖 OpenAI tracing export，而是：

1. 复用 SDK tracing 语义。
2. 复用现有 `runtime_id`、`tool_call_id`、turn。
3. 在 ThirdEye 自己的事件日志中写出 `trace_id / span_id / parent_span_id`。

### 8.2 第一版最小关联规则

1. 一个 session 对应一个 `trace_id`。
2. 每个 `llm_turn` 对应一个 `span_id`。
3. 每个 `tool_call` 对应一个 `span_id`，其 `parent_span_id` 指向所在 `llm_turn span`。
4. 后续若有 `delegated_agent`，其 span 可以挂在触发委派的 tool 或 llm span 下。

### 8.3 前端呈现

第一版详情页仍默认展示“时间线”，但保留 `Trace / Task Tree` 区域，优先渲染 task tree，并可在节点中展示 span 关联。

---

## 9. 模型输入输出落盘策略

本次已确认第一版完整落盘模型输入输出。

### 9.1 记录内容

`model_call_started.payload` 建议记录：

1. `provider_id`
2. `model`
3. `system_prompt`
4. `input_items_summary`
5. `input_items_raw`

`model_call_completed.payload` 建议记录：

1. `response_id`
2. `output_items_summary`
3. `output_items_raw`
4. `usage`
5. `duration_ms`
6. `ok`
7. `error`

`tool_call_started.payload` 建议记录：

1. `tool_name`
2. `tool_call_id`
3. `arguments_raw`

`tool_call_completed.payload` 建议记录：

1. `tool_name`
2. `tool_call_id`
3. `result_raw`
4. `ok`
5. `error`
6. `duration_ms`

### 9.2 风险说明

完整落盘会增加：

1. 本地存储占用。
2. 敏感信息落盘风险。
3. 前端读取大 payload 时的性能压力。

因此第一版实现时需要：

1. 仅在 observability API 返回详情时按需下发大字段。
2. 列表页与概要接口不回传完整 raw payload。
3. 在 README 或后续安全文档中明确这是本地开发态能力，不适合作为生产默认策略。

---

## 10. 指标设计

第一版指标从原始事件流派生，不单独作为原始事实存储。

### 10.1 会话级指标

1. `llm_turn_count`
2. `tool_call_count`
3. `tool_error_count`
4. `tool_error_rate`
5. `session_duration_ms`
6. `total_prompt_tokens`
7. `total_completion_tokens`
8. `estimated_total_tokens`
9. `max_context_usage_percent`
10. `resume_count`

### 10.2 时延指标

1. `avg_model_duration_ms`
2. `p95_model_duration_ms`
3. `avg_tool_duration_ms`
4. `slowest_tool_call`

### 10.3 视图用途

1. observability 列表页用于排序和筛选。
2. 详情页指标卡用于快速判断会话健康度。
3. evaluation 与 anomaly 使用这些指标作为启发式输入。

---

## 11. 异常检测

### 11.1 设计原则

异常事件必须支持运行中实时产出，不能只做事后汇总。

### 11.2 第一版实时规则

1. `repeated_tool_failure`
   同一 `tool_name` 或同一 `tool_call pattern` 连续失败超过阈值。
2. `empty_llm_response_loop`
   连续多轮模型返回空输出、无有效工具调用或无有效 assistant 进展。
3. `high_context_pressure`
   上下文占用超过阈值，如 `>= 85%`。
4. `excessive_turn_count`
   turn 数接近上限，如达到 `max_turns` 的 80%。
5. `resume_loop`
   会话多次从断点恢复后仍反复卡在同一节点或同类失败。

### 11.3 异常事件结构

```json
{
  "event_type": "anomaly_detected",
  "payload": {
    "code": "repeated_tool_failure",
    "severity": "high",
    "title": "同一工具连续失败",
    "summary": "write_file_chunk 连续失败 3 次",
    "related_runtime_ids": ["tool_call_a", "tool_call_b"],
    "related_task_ids": ["task_a", "task_b"]
  }
}
```

### 11.4 严重度

第一版建议：

1. `low`
2. `medium`
3. `high`

---

## 12. 评估设计

### 12.1 评估策略

第一版只做启发式评估，不做 `LLM-as-judge`。

### 12.2 评估等级

1. `success`
2. `partial_success`
3. `failed`

### 12.3 启发式信号

1. 是否产出 assistant 最终回复。
2. 是否存在高严重度 anomaly。
3. tool 错误率是否超阈值。
4. 是否命中 excessive turn / resume loop。
5. 会话是否以取消或不可恢复错误结束。

### 12.4 评估事件结构

```json
{
  "event_type": "evaluation_recorded",
  "payload": {
    "grade": "partial_success",
    "summary": "会话完成，但工具失败率较高",
    "signals": {
      "has_final_reply": true,
      "high_severity_anomaly_count": 1,
      "tool_error_rate": 0.4,
      "resume_count": 1
    }
  }
}
```

---

## 13. API 设计

### 13.1 新增路由

新增独立 observability 路由：

1. `GET /observability/sessions`
2. `GET /observability/sessions/{session_id}`
3. `GET /observability/sessions/{session_id}/timeline`
4. `GET /observability/sessions/{session_id}/events`
5. `GET /observability/sessions/{session_id}/tasks`
6. `GET /observability/sessions/{session_id}/metrics`

### 13.2 接口职责

`GET /observability/sessions`

1. 返回具备观测数据的新会话列表。
2. 支持后续按状态、异常、评估等级筛选。

`GET /observability/sessions/{session_id}`

1. 返回详情页概要信息。
2. 包括 session 元数据、指标摘要、异常摘要、评估摘要。

`GET /observability/sessions/{session_id}/timeline`

1. 返回按时间排序的事件视图模型。
2. 适合详情页默认首屏。

`GET /observability/sessions/{session_id}/events`

1. 返回原始事件流或分页原始事件。
2. 用于深度调试和后续导出。

`GET /observability/sessions/{session_id}/tasks`

1. 返回 task tree。
2. 包括 task 状态、父子关系、相关 event/span。

`GET /observability/sessions/{session_id}/metrics`

1. 返回聚合指标。
2. 可被详情页与列表页复用。

### 13.3 历史会话策略

对没有 `jsonl` 事件文件的老 session：

1. 列表页可不展示。
2. 或展示为 `observability_unavailable=true`。

第一版更建议直接只展示“已具备观测数据”的会话。

---

## 14. 前端设计

### 14.1 路由

新增：

1. `/observability`
2. `/observability/sessions/[sessionId]`

### 14.2 列表页

第一版展示：

1. session id
2. playbook id
3. provider/model
4. status
5. evaluation grade
6. anomaly count
7. updated_at

### 14.3 详情页

默认主视图为“时间线”。

建议分区：

1. 顶部概要
   session 基本信息、状态、评估结果、异常数量
2. 时间线
   默认主视图，展示 `user_message / model / tool / anomaly / evaluation`
3. Task Tree
   展示 root task、llm_turn、tool_call 层级关系
4. 指标
   token、耗时、错误率、上下文压力
5. 异常
   以卡片形式展示异常事件
6. 原始事件
   调试折叠面板
7. 决策归因
   第一版占位，显示“即将支持”
8. 回放与对比
   第一版占位，提供“再次运行”或未来入口占位

### 14.4 与聊天页关系

1. `AgentWorkspace` 保留当前聊天体验。
2. 聊天页可以后续增加“查看可观察性”跳转按钮，但不是本阶段必需。
3. observability 面板作为独立工作台存在。

---

## 15. 后端改造点

### 15.1 新增服务

建议新增：

1. `apps/api/app/services/review_session_observability.py`
2. `apps/api/app/services/review_session_event_log.py`
3. `apps/api/app/services/review_session_tasks.py`
4. `apps/api/app/services/review_session_anomalies.py`
5. `apps/api/app/api/observability.py`

### 15.2 修改点

`apps/api/app/agents/sdk_runtime.py`

1. 丰富 runtime callback 事件内容。
2. 增加持续时间、trace/span 关联字段。

`apps/api/app/agents/sdk_chat.py`

1. 保留现有消息写入逻辑。
2. 同时把 runtime 事件写入独立 jsonl。
3. 在适当时机创建与推进 task tree。

`apps/api/app/services/review_sessions.py`

1. 不再把 observability 当成 message 的唯一来源。
2. 可在 session 完成时回写 observability 摘要。

`apps/api/app/api/reviews.py`

1. 在会话创建、发送消息、恢复、终止、完成时写入事件。
2. 会话结束时触发启发式评估。

---

## 16. 实施分期

### Phase 1: 事件底座

1. 增加 `review-session-events/{session_id}.jsonl`
2. 设计统一事件协议
3. 接入 session、message、llm、tool 事件写入
4. 补充 sequence 与 event_id

### Phase 2: Task Tree 与异常

1. 创建 root task / llm_turn task / tool_call task
2. 实时产出 anomaly 事件
3. 会话结束产出 evaluation

### Phase 3: Observability API

1. 新增 `/observability` 路由
2. 提供列表、详情、时间线、任务树、指标接口

### Phase 4: 前端独立面板

1. `/observability` 列表页
2. `/observability/sessions/[sessionId]` 详情页
3. 默认时间线视图
4. Task Tree / 指标 / 异常 / 原始事件分区

### Phase 5: 后续扩展

1. `decision_recorded`
2. `LLM-as-judge`
3. replay / compare
4. `graph run` 复用

---

## 17. 风险与注意事项

1. 完整落盘模型输入输出会带来本地敏感信息风险，后续需要补权限和脱敏策略。
2. jsonl 文件会持续增长，后续需要考虑压缩、归档或按时间切片。
3. 如果 runtime callback 信息不足，可能需要扩展 `sdk_runtime.py` 中 hook 的 payload。
4. 现有 `messages` 与新事件流会并存一段时间，必须明确两者职责边界。
5. 第一版不回填老 session，因此 observability 面板初期只对新会话有数据。

---

## 18. 第一版验收标准

满足以下条件即可认为第一版设计目标达成：

1. 新创建的 review session 会生成独立 `jsonl` 原始事件文件。
2. 事件文件至少包含 session、user、assistant、model、tool、task、anomaly、evaluation 事件。
3. 能从事件流生成时间线与 task tree。
4. 能在运行中实时发现并记录 anomaly。
5. 会话结束后能生成启发式 evaluation。
6. `/observability` 有独立列表页与详情页。
7. 详情页默认展示时间线，并能查看 task tree、指标与异常。

---

## 19. 后续建议

1. 第二阶段优先补 `decision_recorded`，但要谨慎评估对主 prompt 和 provider 兼容性的影响。
2. 第三阶段再引入 `LLM-as-judge`，避免评估系统先于观测底座复杂化。
3. 等 review session 版稳定后，再将同一套事件协议抽象复用到 `graph run`。
