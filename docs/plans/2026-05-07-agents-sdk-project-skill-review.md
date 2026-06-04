# Agents SDK Project Skill Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an OpenAI Agents SDK backed flow where project distillation produces a project-specific skill and review runs as a multi-turn conversation against that skill.

**Architecture:** Keep the existing deterministic and provider-backed one-shot flows intact for compatibility, but add a new agent orchestration layer on the backend. Distillation will generate project skill artifacts plus agent metadata, and review will move to session-based conversations using Agents SDK `Runner`, `handoff`, and `SQLiteSession`.

**Tech Stack:** FastAPI, Pydantic, OpenAI Agents SDK, SQLiteSession, Next.js App Router, React

---

### Task 1: Extend backend schemas for project-skill and chat review

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\schemas\playbook.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\schemas\review.py`

**Step 1: Add project-skill metadata fields**

Add fields for generated skill artifact name/path and orchestration mode to playbook metadata.

**Step 2: Add conversation request/response models**

Define session creation, chat turn, transcript message, and conversation summary models.

**Step 3: Keep existing one-shot review response shape**

Preserve current response models so old `/reviews` still works.

### Task 2: Add reusable playbook loading and conversation storage helpers

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\storage.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\services\playbook_loader.py`
- Create: `F:\codebaby\ThirdEye\apps\api\app\services\review_sessions.py`

**Step 1: Add generic artifact listing helpers**

Expose safe helper methods for listing and saving session records.

**Step 2: Add conversation session storage service**

Persist session metadata, transcript snapshots, and map them to SQLite session ids.

### Task 3: Implement Agents SDK orchestration for distillation and review

**Files:**
- Create: `F:\codebaby\ThirdEye\apps\api\app\agents\sdk_review.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\agents\distillation.py`

**Step 1: Build agent tools**

Implement tools to load project skill, project summary, rules, and evidence snippets.

**Step 2: Build triage and project reviewer agents**

Use `handoff()` to move from a triage agent into a project reviewer agent.

**Step 3: Add SQLiteSession-backed run helper**

Create and reuse session memory so follow-up questions preserve context.

**Step 4: Update distillation output**

Persist a project-specific skill artifact designed for the project reviewer agent.

### Task 4: Add new conversation APIs while preserving old review API

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\api\app\api\playbooks.py`
- Modify: `F:\codebaby\ThirdEye\apps\api\app\api\reviews.py`

**Step 1: Add session create endpoint**

Create a review session from a selected playbook and provider.

**Step 2: Add send-message endpoint**

Run one agent turn and return assistant output plus updated transcript.

**Step 3: Add transcript fetch endpoint**

Allow frontend reload and continued chat.

### Task 5: Replace one-shot review page with chat UX

**Files:**
- Modify: `F:\codebaby\ThirdEye\apps\web\src\lib\api.ts`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\components\ReviewComposer.tsx`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\components\ReviewResult.tsx`
- Modify: `F:\codebaby\ThirdEye\apps\web\src\app\layout.tsx`

**Step 1: Add session and message client functions**

Call new conversation endpoints from frontend.

**Step 2: Convert review form into chat composer**

First message creates a session, later messages continue the same conversation.

**Step 3: Show transcript and structured latest review state**

Keep structured findings panel, but drive it from the latest assistant turn and session state.

### Task 6: Verify

**Files:**
- Modify if needed: backend tests and frontend types

**Step 1: Run targeted backend tests**

Run review, playbook, distillation, and model provider test groups.

**Step 2: Run frontend build**

Run `npm run build` in `apps/web`.

**Step 3: Fix regressions**

Patch any schema or rendering mismatches.
