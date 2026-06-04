# Skill Graph 2.0 P0 验收说明

日期: 2026-05-13  
适用版本: Skill Graph 2.0 P0

## 1. 范围

本验收文档对应当前仓库已经实现的 Skill Graph 2.0 P0 切片，目标是确认以下能力已经闭环：

- Capability / Composite / Graph Playbook 的声明式定义
- 原子能力注册中心的增删改查与 AI 草稿补全
- Graph Playbook 编译
- chain composite 执行
- `human_approval` 暂停与恢复
- 本地 JSON 持久化
- `/graph` 任务驾驶舱页面

## 2. 自动化验证

后端：

```bash
cd apps/api
pytest tests/test_skill_graph_schemas.py tests/test_skill_graph_storage.py tests/test_skill_graph_registry.py tests/test_skill_graph_compiler.py tests/test_skill_graph_runner.py tests/test_skill_graph_run_events.py tests/test_skill_graph_api.py tests/test_skill_graph_sample_template.py tests/test_skill_graph_smoke.py -q
```

前端：

```bash
cd apps/web
npm run build
```

## 3. 手动验收路径

### 3.1 启动服务

后端：

```bash
cd apps/api
uv run uvicorn app.main:app --reload
```

前端：

```bash
cd apps/web
npm run dev
```

默认地址：

- API: `http://127.0.0.1:8000`
- Web: `http://127.0.0.1:3000`

### 3.2 验收步骤

1. 打开 `/graph`
   确认页面显示“任务驾驶舱”总览，并能看到 capability、composite、任务剧本和 run 统计。

2. 打开 `/graph/playbooks`
   确认能看到 `graph_weekly_competitor_report`。

3. 打开 `/graph/capabilities`
   先点击“新建原子”，选择来源类型 `skill | agent | tool | mcp server`，再选择一个现有来源对象。
   然后点击“AI 填写参数”，确认页面会结合来源对象生成配置、输入输出 Schema 和重试策略草稿，并且可以成功保存。

4. 在原子列表中重新载入刚才保存的 capability
   修改描述或启用状态后保存，确认更新成功。

5. 打开 `/graph/runs`
   点击“启动 Sample Run”。

6. 观察 run 状态
   确认新 run 进入 `waiting_for_human`，当前节点停在 `approve_report`。

7. 在右侧审批队列点击“通过”
   确认 run 继续执行并最终进入 `succeeded`。

8. 刷新 `/graph/runs`
   确认 run 详情仍可从后端加载，说明快照持久化生效。

## 4. 样例模板

当前 P0 样例由以下工件组成：

- capability:
  `cap_fetch_competitor_homepage`
  `cap_summarize_page_changes`
  `cap_render_weekly_report`
- composite:
  `comp_single_competitor_monitor`
- Graph Playbook:
  `graph_weekly_competitor_report`

存储位置：

```text
data/skill-graph/capabilities/
data/skill-graph/composites/
data/skill-graph/graph-playbooks/
```

## 5. 已知限制

- P0 只支持 `chain` composite，不支持 orchestrator 模式。
- `/graph` 前端页面目前聚焦浏览、启动和审批，不提供图形化编辑。
- 原子能力页支持 AI 草稿补全，但当前仍以 JSON 表单编辑为主，不提供图形化 schema 设计器。
- SSE 事件流已经支持快照回放和实时事件，但前端目前只在 run 详情区域消费。
- run 控制接口目前只实现审批恢复，没有完成 pause / cancel / retry 节点等完整干预面。

## 6. P1 跟进

- orchestrator composite
- Asset Container
- 图形化只读画布
- 更完整的 run 控制动作
- 更细的 capability 运行指标与历史统计
