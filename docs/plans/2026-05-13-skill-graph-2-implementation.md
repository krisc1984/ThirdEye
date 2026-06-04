# Skill Graph 2.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Skill Graph 2.0 P0 slice for ThirdEye: declarative graph definitions, compilation, execution state, human approval, and a cockpit UI for graph runs.

**Architecture:** Add a new `skill_graph` domain alongside the existing review-playbook system instead of mutating current playbook models. Reuse the repo's established FastAPI + Pydantic + local JSON artifact storage + SSE session event patterns so Graph Playbook runs feel native to the current backend and frontend. Keep P0 strictly focused on chain-mode composites, graph compilation, run state transitions, and human approval; defer orchestrator mode, asset-heavy workflows, and editable canvas to later phases.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, local JSON storage under `data/skill-graph/`, Next.js App Router, React, TypeScript

---

## Delivery Slices

1. Backend schemas and storage for the skill graph domain.
2. Registry and compiler for capabilities, composites, and graph playbooks.
3. Chain-mode runner with resumable human approval.
4. Graph APIs and SSE event stream.
5. Cockpit UI for graph definitions and active runs.
6. End-to-end sample template, tests, and docs.

### Task 1: Add skill graph domain schemas

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\schemas\skill_graph.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\schemas\__init__.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_schemas.py`

**Step 1: Write the failing schema tests**

Cover:
- capability `kind` validation
- composite `mode="chain"` validation
- graph node type validation
- graph version semantic format
- graph complexity guardrails
- run status transitions accepted by schema helpers

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_schemas.py -q`  
Expected: FAIL because `app.schemas.skill_graph` does not exist.

**Step 3: Write minimal implementation**

Add Pydantic models for:
- `CapabilityDefinition`
- `CapabilityRetryPolicy`
- `CompositeNodeDefinition`
- `CompositeDefinition`
- `GraphNodeDefinition`
- `GraphEdgeDefinition`
- `GraphPlaybookDefinition`
- `GraphCompileResult`
- `GraphRun`
- `GraphRunNodeState`
- `GraphApprovalDecision`
- `GraphEvent`

Include typed literals for:
- capability kinds
- composite modes
- graph node types
- graph statuses

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_schemas.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/schemas/skill_graph.py apps/api/app/schemas/__init__.py apps/api/tests/test_skill_graph_schemas.py
git commit -m "feat: add skill graph domain schemas"
```

### Task 2: Extend storage for skill graph artifacts

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\storage.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_storage.py`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\capabilities\.gitkeep`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\composites\.gitkeep`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\graph-playbooks\.gitkeep`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\runs\.gitkeep`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\assets\.gitkeep`

**Step 1: Write the failing storage tests**

Test that storage can:
- save/load graph definitions by namespace
- list graph records
- save nested run snapshots
- reject path traversal in graph ids

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_storage.py -q`  
Expected: FAIL because graph namespaces and helpers are missing.

**Step 3: Write minimal implementation**

Add safe helpers for:
- `save_json(namespace, record_id, payload)`
- `load_json(namespace, record_id)`
- `list_json(namespace)`
- optional helper wrappers for graph namespaces if that matches local style

Persist graph resources under:

```text
data/skill-graph/capabilities/
data/skill-graph/composites/
data/skill-graph/graph-playbooks/
data/skill-graph/runs/
data/skill-graph/assets/
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_storage.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/storage.py apps/api/tests/test_skill_graph_storage.py data/skill-graph
git commit -m "feat: add skill graph storage namespaces"
```

### Task 3: Implement graph registry service

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\skill_graph_registry.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\skill_registry.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_registry.py`

**Step 1: Write the failing registry tests**

Cover:
- register a capability
- register a composite
- register a graph playbook
- reject references to missing capabilities
- derive a capability from an enabled skill registry entry

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_registry.py -q`  
Expected: FAIL because registry service does not exist.

**Step 3: Write minimal implementation**

Implement `SkillGraphRegistryService` with methods to:
- list/get/save capabilities
- list/get/save composites
- list/get/save graph playbooks
- map selected existing skills into capability metadata

Keep it read/write only for graph artifacts. Do not mutate existing review playbook records.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_registry.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/skill_graph_registry.py apps/api/app/services/skill_registry.py apps/api/tests/test_skill_graph_registry.py
git commit -m "feat: add skill graph registry service"
```

### Task 4: Implement graph compiler

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\skill_graph_compiler.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_compiler.py`

**Step 1: Write the failing compiler tests**

Test that compiler:
- rejects cyclic chain composites
- rejects graph playbooks with missing entry nodes
- rejects unreachable graph nodes
- requires approve/reject exits on `human_approval` nodes
- warns when composite count exceeds the configured threshold

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_compiler.py -q`  
Expected: FAIL because compiler service does not exist.

**Step 3: Write minimal implementation**

Implement:
- DAG validation for chain composites
- graph node reachability check
- human approval edge validation
- complexity warning calculation

Return a `GraphCompileResult` with:
- `ok`
- `errors`
- `warnings`
- normalized definition snapshot

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_compiler.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/skill_graph_compiler.py apps/api/tests/test_skill_graph_compiler.py
git commit -m "feat: add skill graph compiler"
```

### Task 5: Add chain-mode graph runner

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\skill_graph_runner.py`
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\skill_graph_actions.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_runner.py`

**Step 1: Write the failing runner tests**

Cover:
- successful chain composite execution
- capability retry policy on transient failure
- graph pauses at `human_approval`
- graph resumes from approval
- graph transitions to failed when a capability exhausts retries

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_runner.py -q`  
Expected: FAIL because runner does not exist.

**Step 3: Write minimal implementation**

Implement a runner that:
- expands graph nodes into composite execution
- runs chain nodes in dependency order
- records per-node state
- stores run snapshots after each transition
- pauses on `human_approval`
- resumes from stored snapshot

For P0, implement action handlers as Python callables with a small built-in sample set instead of full external tool orchestration.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_runner.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/skill_graph_runner.py apps/api/app/services/skill_graph_actions.py apps/api/tests/test_skill_graph_runner.py
git commit -m "feat: add chain-mode skill graph runner"
```

### Task 6: Add graph run event streaming

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\skill_graph_run_events.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_events.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_run_events.py`

**Step 1: Write the failing event tests**

Test that:
- run events are appended in order
- event payload includes status and node state
- event stream can replay the latest run snapshot

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_run_events.py -q`  
Expected: FAIL because graph event service does not exist.

**Step 3: Write minimal implementation**

Mirror the existing review-session event approach:
- append JSON event entries
- expose a replayable snapshot
- keep event shapes simple and frontend-friendly

Refactor shared pieces only if that clearly reduces duplication without touching unrelated behavior.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_run_events.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/skill_graph_run_events.py apps/api/app/services/review_session_events.py apps/api/tests/test_skill_graph_run_events.py
git commit -m "feat: add skill graph run events"
```

### Task 7: Add graph API routes

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\api\skill_graph.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\main.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_api.py`

**Step 1: Write the failing API tests**

Endpoints:
- `GET /graph/capabilities`
- `POST /graph/capabilities`
- `GET /graph/composites`
- `POST /graph/composites`
- `POST /graph/composites/{id}/compile`
- `GET /graph/playbooks`
- `POST /graph/playbooks`
- `POST /graph/playbooks/{id}/compile`
- `POST /graph/playbooks/{id}/runs`
- `GET /graph/runs/{run_id}`
- `POST /graph/runs/{run_id}/approvals/{approval_id}`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_api.py -q`  
Expected: FAIL because router does not exist.

**Step 3: Write minimal implementation**

Add a FastAPI router that wires:
- registry service
- compiler service
- runner service
- event replay endpoint

Return compile warnings in response bodies. Keep payload shapes aligned with `skill_graph.py` schemas.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_api.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/api/skill_graph.py apps/api/app/main.py apps/api/tests/test_skill_graph_api.py
git commit -m "feat: add skill graph api"
```

### Task 8: Seed a sample graph template

**Files:**
- Create: `F:\codebaby\ThirdEye\data\skill-graph\capabilities\cap_fetch_competitor_homepage.json`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\capabilities\cap_summarize_page_changes.json`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\capabilities\cap_render_weekly_report.json`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\composites\comp_single_competitor_monitor.json`
- Create: `F:\codebaby\ThirdEye\data\skill-graph\graph-playbooks\graph_weekly_competitor_report.json`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_sample_template.py`

**Step 1: Write the failing sample test**

Assert that the sample graph:
- compiles cleanly
- can be loaded from storage
- pauses at report approval when run with fixture inputs

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_sample_template.py -q`  
Expected: FAIL because sample graph artifacts do not exist.

**Step 3: Write minimal implementation**

Create a P0-friendly sample:
- three capabilities
- one chain composite
- one graph playbook
- one human approval node

Use simple deterministic handlers so the sample works in tests without network access.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_sample_template.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add data/skill-graph apps/api/tests/test_skill_graph_sample_template.py
git commit -m "feat: add sample skill graph template"
```

### Task 9: Add frontend graph API client and routes

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\web\src\lib\api.ts`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\components\AppNav.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\graph\page.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\graph\playbooks\page.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\graph\runs\page.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\graph\capabilities\page.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\graph\composites\page.tsx`

**Step 1: Write the frontend API types**

Add typed client models and request helpers for:
- graph capabilities
- composites
- graph playbooks
- graph runs
- approvals
- event stream URL

**Step 2: Build route shells**

Create route pages that fetch and render:
- graph overview
- playbook list
- run list
- capability list
- composite list

**Step 3: Run build to verify it passes**

Run: `npm run build`  
Workdir: `F:\codebaby\ThirdEye\apps\web`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/components/AppNav.tsx apps/web/src/app/graph
git commit -m "feat: add skill graph frontend routes"
```

### Task 10: Build cockpit components

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphCapabilityList.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphCompositeList.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphPlaybookList.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphRunList.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphRunDetail.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphApprovalQueue.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\GraphStatusBadge.tsx`

**Step 1: Build list and detail components**

Render:
- compile warnings
- current node
- run status
- approval queue
- node-level summaries

Keep the visual language consistent with the current app instead of inventing a disconnected design system.

**Step 2: Add approval actions**

Wire:
- approve
- reject
- resume

Start with regular action buttons and server roundtrips. Do not add optimistic state until the baseline flow is stable.

**Step 3: Run build to verify it passes**

Run: `npm run build`  
Workdir: `F:\codebaby\ThirdEye\apps\web`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/components/Graph*.tsx
git commit -m "feat: add skill graph cockpit components"
```

### Task 11: Add SSE-backed run updates

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\web\src\components\GraphRunList.tsx`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\components\GraphRunDetail.tsx`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\app\graph\runs\page.tsx`

**Step 1: Write minimal UI behavior expectations**

Support:
- opening a run detail
- streaming new events
- refreshing current status after approval

**Step 2: Implement event subscription**

Use the same EventSource pattern already present in `AgentWorkspace.tsx` where appropriate. Reuse logic carefully instead of duplicating fragile event parsing.

**Step 3: Run build to verify it passes**

Run: `npm run build`  
Workdir: `F:\codebaby\ThirdEye\apps\web`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/components/GraphRunList.tsx apps/web/src/components/GraphRunDetail.tsx apps/web/src/app/graph/runs/page.tsx
git commit -m "feat: stream skill graph run updates"
```

### Task 12: Add backend smoke and acceptance tests

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_skill_graph_smoke.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\tests\conftest.py`

**Step 1: Write the failing smoke test**

Scenario:
- load sample graph
- compile graph playbook
- start a run
- verify it reaches `waiting_for_human`
- approve it
- verify it reaches `succeeded`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_graph_smoke.py -q`  
Expected: FAIL until full backend flow is wired.

**Step 3: Implement missing glue**

Patch fixtures or service wiring so the entire happy path runs through public service/API boundaries instead of test-only shortcuts.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_graph_smoke.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/tests/test_skill_graph_smoke.py apps/api/tests/conftest.py
git commit -m "test: add skill graph smoke flow"
```

### Task 13: Document the new system

**Files:**
- Modify: `F:\codebaby\ThirdEye\README.md`
- Create: `F:\codebaby\ThirdEye\docs\skill-graph-acceptance.md`
- Modify: `F:\codebaby\ThirdEye\docs\skill-graph-2-prd.md`

**Step 1: Update README**

Document:
- what Skill Graph 2.0 P0 includes
- new routes
- storage layout
- sample graph workflow

**Step 2: Write acceptance notes**

Include:
- test commands
- sample run path
- known limitations
- P1 follow-ups

**Step 3: Tighten PRD references**

Mark any decisions that were concretized during implementation planning, especially:
- chain-only P0
- local JSON persistence
- sample graph template choice

**Step 4: Run doc sanity check**

Run: `git diff --check -- README.md docs/skill-graph-2-prd.md docs/skill-graph-acceptance.md docs/plans/2026-05-13-skill-graph-2-implementation.md`  
Expected: no whitespace or conflict issues.

**Step 5: Commit**

```bash
git add README.md docs/skill-graph-acceptance.md docs/skill-graph-2-prd.md docs/plans/2026-05-13-skill-graph-2-implementation.md
git commit -m "docs: add skill graph implementation and acceptance notes"
```

## Verification Checklist

Run these before calling the P0 slice complete:

1. `pytest tests/test_skill_graph_schemas.py tests/test_skill_graph_storage.py tests/test_skill_graph_registry.py tests/test_skill_graph_compiler.py tests/test_skill_graph_runner.py tests/test_skill_graph_run_events.py tests/test_skill_graph_api.py tests/test_skill_graph_sample_template.py tests/test_skill_graph_smoke.py -q`
2. `pytest tests/test_health.py tests/test_projects_api.py tests/test_playbooks_api.py tests/test_reviews_api.py -q`
3. `npm run build` in `F:\codebaby\ThirdEye\apps\web`
4. Manual check:
Load `/graph/runs`, start the sample graph, confirm it pauses for approval, approve it, and verify the run reaches `succeeded`.

## Notes For Execution

- Keep `Graph Playbook` as the canonical term in new code and UI. Do not reuse `PlaybookMetadata` for this feature.
- Reuse existing patterns from review sessions for event streaming and persisted run state where they fit naturally.
- Avoid building the infinite canvas in this plan. P0 ends when graph definitions, runs, approvals, and cockpit screens are stable.
- Keep capability execution deterministic in tests. Network-backed capabilities belong behind clearly swappable handlers later.
- Favor narrow commits per task so regressions are easy to isolate.

## Post-Plan Update

- `/graph/capabilities` 已从只读列表页补齐为原子能力注册工作台。
- capability `kind` 实际落地为 `tool | skill | agent | service`。
- 已新增 capability CRUD、引用保护删除和 `POST /graph/capabilities/draft` 草稿生成接口。
- 原子能力支持从应用中已有的 `skill | agent | tool | mcp server` 选择来源对象。
- 草稿生成支持两种路径：
  - 未选择 model provider 时，回退到 deterministic 模板。
  - 选择 model provider 时，结合来源对象调用大模型补全 config、input_schema、output_schema 和 retry_policy。
