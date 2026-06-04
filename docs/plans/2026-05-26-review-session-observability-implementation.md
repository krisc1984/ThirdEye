# Review Session Observability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build production-style observability for ThirdEye review sessions by adding append-only event logs, task trees, anomaly detection, heuristic evaluation, observability APIs, and a standalone `/observability` UI.

**Architecture:** Extend the existing review-session runtime instead of replacing it. Keep `review-sessions/{id}.json` as the chat-facing session snapshot, add `review-session-events/{id}.jsonl` as the raw observability source of truth, derive timeline/tasks/metrics from that event stream, and expose a separate observability API plus frontend workspace. Reuse the repo's FastAPI + Pydantic + local JSON storage + SSE-friendly runtime hooks and keep the first version focused on review sessions only.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, local JSON/JSONL storage, Next.js App Router, React, TypeScript

---

## Delivery Slices

1. Event log schema and JSONL storage.
2. Runtime event capture for review sessions.
3. Task tree, anomaly detection, and heuristic evaluation.
4. Observability backend APIs.
5. Standalone observability frontend routes and components.
6. End-to-end tests and docs.

### Task 1: Add observability domain schemas

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\schemas\observability.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\schemas\__init__.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_observability_schemas.py`

**Step 1: Write the failing schema tests**

Cover:
- event type validation
- task kind validation
- task status validation
- anomaly severity validation
- evaluation grade validation
- timeline entry model validation

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_observability_schemas.py -q`  
Expected: FAIL because `app.schemas.observability` does not exist.

**Step 3: Write minimal implementation**

Add Pydantic models for:
- `SessionEventRecord`
- `SessionTaskRecord`
- `SessionAnomalyRecord`
- `SessionEvaluationRecord`
- `ObservabilitySessionSummary`
- `ObservabilityTimelineEntry`
- `ObservabilityMetrics`

Include typed literals for:
- event types
- task kinds
- task statuses
- anomaly severities
- evaluation grades

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_observability_schemas.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/schemas/observability.py apps/api/app/schemas/__init__.py apps/api/tests/test_observability_schemas.py
git commit -m "feat: add observability domain schemas"
```

### Task 2: Add JSONL event log storage

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\storage.py`
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_event_log.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_event_log.py`
- Create: `F:\codebaby\ThirdEye\data\review-session-events\.gitkeep`

**Step 1: Write the failing storage tests**

Test that the event log service can:
- append JSONL records for a session
- read them back in sequence order
- assign incremental `sequence`
- reject path traversal session ids
- keep existing lines when new events are appended

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_event_log.py -q`  
Expected: FAIL because the event log service does not exist.

**Step 3: Write minimal implementation**

Implement:
- per-session file path resolution under `data/review-session-events/`
- `append_event(session_id, event)`
- `list_events(session_id)`
- `next_sequence(session_id)`

Use append-only JSONL, one line per event record.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_event_log.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/storage.py apps/api/app/services/review_session_event_log.py apps/api/tests/test_review_session_event_log.py data/review-session-events/.gitkeep
git commit -m "feat: add review session event log storage"
```

### Task 3: Capture session lifecycle and chat events

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_observability.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\review_sessions.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\api\reviews.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_observability_lifecycle.py`

**Step 1: Write the failing lifecycle tests**

Cover:
- creating a session writes `session_started`
- sending a message writes `user_message`
- assistant completion writes `assistant_message`
- session status changes write `session_status_changed`
- completing a session writes `session_completed`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_observability_lifecycle.py -q`  
Expected: FAIL because lifecycle events are not written.

**Step 3: Write minimal implementation**

Add a service that can build and append event records with:
- `event_id`
- `session_id`
- `sequence`
- `event_type`
- `timestamp`
- `trace_id`
- `span_id`
- `parent_span_id`
- `runtime_id`
- `turn`
- `payload`

Wire it into:
- `ReviewSessionStore.create()`
- `ReviewSessionStore.append_message()`
- `ReviewSessionStore.update_status()`
- `ReviewSessionStore.attach_review_result()`
- review session stop/cancel flows

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_observability_lifecycle.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/review_session_observability.py apps/api/app/services/review_sessions.py apps/api/app/api/reviews.py apps/api/tests/test_review_session_observability_lifecycle.py
git commit -m "feat: log review session lifecycle events"
```

### Task 4: Extend runtime hooks to emit model and tool observability events

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\agents\sdk_runtime.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\agents\sdk_chat.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_runtime_events.py`

**Step 1: Write the failing runtime event tests**

Test that runtime events include:
- `model_call_started`
- `model_call_completed`
- `tool_call_started`
- `tool_call_completed`
- provider/model identifiers
- `runtime_id` and `tool_call_id`
- `turn`
- raw arguments/results

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_runtime_events.py -q`  
Expected: FAIL because runtime callbacks only feed chat messages.

**Step 3: Write minimal implementation**

Update runtime callback payloads to include:
- explicit observability event type mapping
- trace/span fields
- duration when available
- full tool args/results
- full model input/output summaries and usage

Have `sdk_chat.py` write these callback events into the observability event log while keeping existing chat message behavior.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_runtime_events.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/agents/sdk_runtime.py apps/api/app/agents/sdk_chat.py apps/api/tests/test_review_session_runtime_events.py
git commit -m "feat: persist review session runtime events"
```

### Task 5: Add task tree builder and task status transitions

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_tasks.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_observability.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_tasks.py`

**Step 1: Write the failing task tree tests**

Cover:
- root session task creation
- llm turn task creation on `model_call_started`
- tool call task creation under the correct llm task
- task status updates on completion/failure/cancel
- task parent-child relationships are stable across event replay

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_tasks.py -q`  
Expected: FAIL because task records are not derived.

**Step 3: Write minimal implementation**

Implement task derivation rules:
- create root task on `session_started`
- create `llm_turn` task on `model_call_started`
- create `tool_call` task on `tool_call_started`
- update statuses on matching completion events
- expose helpers to rebuild task tree from raw events

Write derived task events:
- `task_created`
- `task_status_changed`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_tasks.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/review_session_tasks.py apps/api/app/services/review_session_observability.py apps/api/tests/test_review_session_tasks.py
git commit -m "feat: add review session task tree derivation"
```

### Task 6: Add anomaly detection

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_anomalies.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_observability.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\api\reviews.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_anomalies.py`

**Step 1: Write the failing anomaly tests**

Cover:
- repeated tool failure anomaly
- excessive turn count anomaly
- high context pressure anomaly
- resume loop anomaly
- anomaly events are appended exactly once per trigger

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_anomalies.py -q`  
Expected: FAIL because anomaly detection does not exist.

**Step 3: Write minimal implementation**

Implement rules for:
- `repeated_tool_failure`
- `empty_llm_response_loop`
- `high_context_pressure`
- `excessive_turn_count`
- `resume_loop`

Emit `anomaly_detected` events with:
- `code`
- `severity`
- `title`
- `summary`
- `related_runtime_ids`
- `related_task_ids`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_anomalies.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/review_session_anomalies.py apps/api/app/services/review_session_observability.py apps/api/app/api/reviews.py apps/api/tests/test_review_session_anomalies.py
git commit -m "feat: detect review session anomalies"
```

### Task 7: Add heuristic evaluation and observability summary

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\review_session_observability.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\review_sessions.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_evaluation.py`

**Step 1: Write the failing evaluation tests**

Test that:
- a successful run records `evaluation_recorded` with `success`
- a run with anomalies can record `partial_success`
- a cancelled or failed run records `failed`
- summary fields can be read back for list/detail APIs

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_evaluation.py -q`  
Expected: FAIL because evaluation is not generated.

**Step 3: Write minimal implementation**

Implement heuristic evaluation using:
- final assistant reply presence
- high-severity anomaly count
- tool error rate
- excessive turns
- resume count
- terminal session status

Append `evaluation_recorded` and optionally write a compact observability summary back into the session snapshot.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_evaluation.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/review_session_observability.py apps/api/app/services/review_sessions.py apps/api/tests/test_review_session_evaluation.py
git commit -m "feat: add review session evaluation summary"
```

### Task 8: Add observability API

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\api\observability.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\main.py`
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_observability_api.py`

**Step 1: Write the failing API tests**

Endpoints:
- `GET /observability/sessions`
- `GET /observability/sessions/{session_id}`
- `GET /observability/sessions/{session_id}/timeline`
- `GET /observability/sessions/{session_id}/events`
- `GET /observability/sessions/{session_id}/tasks`
- `GET /observability/sessions/{session_id}/metrics`

Test that old sessions without event files are excluded or marked unavailable.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_observability_api.py -q`  
Expected: FAIL because the router does not exist.

**Step 3: Write minimal implementation**

Add API helpers that:
- list sessions with observability data
- load raw event files
- derive timeline entries
- derive task tree
- derive metrics and summary data

Keep raw payloads out of the lightweight list response.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_observability_api.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/api/observability.py apps/api/app/main.py apps/api/tests/test_observability_api.py
git commit -m "feat: add observability api"
```

### Task 9: Add frontend API models and routes

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\web\src\lib\api.ts`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\components\AppNav.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\observability\page.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\app\observability\sessions\[sessionId]\page.tsx`

**Step 1: Add frontend API types**

Add typed client models and request helpers for:
- observability session list
- observability detail
- timeline
- tasks
- metrics
- raw events

**Step 2: Build route shells**

Create route pages that fetch and render:
- `/observability`
- `/observability/sessions/[sessionId]`

**Step 3: Run build to verify it passes**

Run: `npm run build`  
Workdir: `F:\codebaby\ThirdEye\apps\web`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/components/AppNav.tsx apps/web/src/app/observability
git commit -m "feat: add observability frontend routes"
```

### Task 10: Build observability list and detail components

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\ObservabilitySessionList.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\ObservabilitySessionDetail.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\ObservabilityTimeline.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\ObservabilityTaskTree.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\ObservabilityMetricsPanel.tsx`
- Create: `F:\codebaby\ThirdEye\apps\web\src\components\ObservabilityAnomalyPanel.tsx`

**Step 1: Build list component**

Render:
- session id
- provider/model
- status
- evaluation grade
- anomaly count
- updated time

**Step 2: Build detail component**

Render sections for:
- summary header
- timeline default view
- task tree
- metrics
- anomaly cards
- raw events
- placeholder panels for decision/replay

**Step 3: Run build to verify it passes**

Run: `npm run build`  
Workdir: `F:\codebaby\ThirdEye\apps\web`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/components/Observability*.tsx
git commit -m "feat: add observability workspace components"
```

### Task 11: Add backend smoke tests for observability flow

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\tests\test_review_session_observability_smoke.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\tests\conftest.py`

**Step 1: Write the failing smoke test**

Scenario:
- create a review session
- send a message
- simulate or run a tool/llm path
- verify JSONL event file exists
- verify timeline can be loaded
- verify tasks and metrics APIs return data
- verify evaluation exists when session completes

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_review_session_observability_smoke.py -q`  
Expected: FAIL until the end-to-end flow is wired.

**Step 3: Implement missing glue**

Patch fixtures or service wiring so the happy path runs through public APIs and real event files, not only isolated helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_review_session_observability_smoke.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/tests/test_review_session_observability_smoke.py apps/api/tests/conftest.py
git commit -m "test: add review session observability smoke flow"
```

### Task 12: Document the feature

**Files:**
- Modify: `F:\codebaby\ThirdEye\README.md`
- Modify: `F:\codebaby\ThirdEye\docs\plans\2026-05-26-review-session-observability-design.md`
- Create: `F:\codebaby\ThirdEye\docs\observability-acceptance.md`

**Step 1: Update README**

Document:
- what review session observability includes
- new storage layout
- new API routes
- new frontend routes
- local-only caution for full prompt/result persistence

**Step 2: Write acceptance notes**

Include:
- test commands
- manual verification path
- known limitations
- deferred items: decision blocks, LLM judge, replay compare

**Step 3: Tighten design doc references**

Mark implementation choices that became concrete during planning:
- exact filenames
- exact API route set
- first-pass anomaly rule list

**Step 4: Run doc sanity check**

Run: `git diff --check -- README.md docs/observability-acceptance.md docs/plans/2026-05-26-review-session-observability-design.md docs/plans/2026-05-26-review-session-observability-implementation.md`  
Expected: no whitespace or conflict issues.

**Step 5: Commit**

```bash
git add README.md docs/observability-acceptance.md docs/plans/2026-05-26-review-session-observability-design.md docs/plans/2026-05-26-review-session-observability-implementation.md
git commit -m "docs: add observability implementation and acceptance notes"
```

## Verification Checklist

Run these before calling the feature complete:

1. `pytest tests/test_observability_schemas.py tests/test_review_session_event_log.py tests/test_review_session_observability_lifecycle.py tests/test_review_session_runtime_events.py tests/test_review_session_tasks.py tests/test_review_session_anomalies.py tests/test_review_session_evaluation.py tests/test_observability_api.py tests/test_review_session_observability_smoke.py -q`
2. `pytest tests/test_reviews_api.py tests/test_review_workflow.py tests/test_mvp_smoke.py -q`
3. `npm run build` in `F:\codebaby\ThirdEye\apps\web`
4. Manual check:
   start a new review session, send a prompt that triggers llm/tool activity, open `/observability`, verify the session appears, open the detail page, confirm timeline, task tree, metrics, anomalies, and evaluation all render.

## Notes For Execution

- Keep `review session` as the canonical term for this feature. Do not rename it to `chat run` or introduce a parallel domain name in code.
- Reuse existing runtime hooks and review session flow where possible. The first goal is better observability, not a rewrite of the chat system.
- Keep raw prompt/result payloads available in the event log, but keep list and summary APIs light.
- Do not backfill historical sessions. Observability begins with new sessions created after this feature lands.
- Avoid implementing decision blocks or replay diff in this plan. They are explicitly deferred.
