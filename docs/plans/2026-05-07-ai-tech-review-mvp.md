# AI Tech Review MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MVP that lets a user select a local project folder, distill project docs/code into a review playbook skill, then review a technical proposal in chat using that playbook.

**Architecture:** Use a Python FastAPI backend for local project scanning, playbook generation, model provider routing, and review sessions. Use OpenAI Agents SDK for distillation and review workflows, with an OpenAI-compatible model adapter for non-OpenAI providers. Use a React/Next.js frontend for project selection, playbook management, model settings, and chat review.

**Tech Stack:** Python 3.12, FastAPI, OpenAI Agents SDK, Pydantic, SQLite for MVP persistence, local JSON/Markdown artifacts under `data/playbooks/`, React/Next.js, TypeScript, Vitest/pytest.

---

## MVP Delivery Slices

1. Backend foundation and persistence.
2. Local project scanner and safe file access.
3. Model provider adapter and connection test.
4. Playbook artifact schema and storage.
5. Deterministic first-pass distillation pipeline.
6. Agents SDK distillation workflow.
7. Technical proposal review workflow.
8. Frontend shell and pages.
9. End-to-end MVP flow.
10. Hardening, tests, and docs.

## Task 1: Project Skeleton

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/core/config.py`
- Create: `apps/api/app/api/health.py`
- Create: `apps/api/tests/test_health.py`
- Create: `apps/web/package.json`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/layout.tsx`
- Create: `data/.gitkeep`

**Step 1: Create backend package skeleton**

Create a FastAPI app with a `/health` endpoint returning:

```json
{"status":"ok","service":"ai-tech-review-api"}
```

**Step 2: Add backend dependencies**

Backend dependencies:
- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic-settings`
- `pytest`
- `httpx`
- `openai`
- `openai-agents`

**Step 3: Add the failing health test**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-tech-review-api"}
```

**Step 4: Run backend tests**

Run: `cd apps/api && pytest -q`  
Expected: PASS.

**Step 5: Create frontend skeleton**

Create a minimal Next.js app with a home page linking to:
- `/projects`
- `/playbooks`
- `/review`
- `/settings/models`

**Step 6: Run frontend smoke check**

Run: `cd apps/web && npm install && npm run build`  
Expected: build succeeds.

**Step 7: Commit**

```bash
git add apps data
git commit -m "feat: scaffold mvp app"
```

## Task 2: Core Domain Schemas

**Files:**
- Create: `apps/api/app/schemas/project.py`
- Create: `apps/api/app/schemas/playbook.py`
- Create: `apps/api/app/schemas/model_provider.py`
- Create: `apps/api/app/schemas/review.py`
- Create: `apps/api/tests/test_schemas.py`

**Step 1: Write schema tests**

Cover:
- project slug normalization
- playbook version format
- rule evidence ids
- review modes: `quick`, `standard`, `strict`
- provider API shapes: `responses`, `chat_completions`

**Step 2: Implement Pydantic models**

Required models:
- `Project`
- `ProjectScanSummary`
- `PlaybookMetadata`
- `PlaybookRule`
- `EvidenceItem`
- `ModelProviderConfig`
- `ReviewRequest`
- `ReviewFinding`
- `ReviewResponse`

**Step 3: Run tests**

Run: `cd apps/api && pytest tests/test_schemas.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/app/schemas apps/api/tests/test_schemas.py
git commit -m "feat: add mvp domain schemas"
```

## Task 3: Local Persistence Service

**Files:**
- Create: `apps/api/app/services/storage.py`
- Create: `apps/api/tests/test_storage.py`
- Create: `data/projects/.gitkeep`
- Create: `data/playbooks/.gitkeep`
- Create: `data/model-providers/.gitkeep`
- Create: `data/reviews/.gitkeep`

**Step 1: Write storage tests**

Test that storage can:
- save and load JSON by namespace/id
- list namespace records
- reject path traversal ids like `../secret`
- create parent directories automatically

**Step 2: Implement storage**

Use local JSON files for MVP:

```text
data/projects/<project-id>.json
data/playbooks/<playbook-id>/metadata.json
data/model-providers/<provider-id>.json
data/reviews/<review-id>.json
```

**Step 3: Run tests**

Run: `cd apps/api && pytest tests/test_storage.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/app/services/storage.py apps/api/tests/test_storage.py data
git commit -m "feat: add local json storage"
```

## Task 4: Safe Project Scanner

**Files:**
- Create: `apps/api/app/services/ignore_rules.py`
- Create: `apps/api/app/services/project_scanner.py`
- Create: `apps/api/tests/fixtures/sample_project/README.md`
- Create: `apps/api/tests/fixtures/sample_project/src/app.py`
- Create: `apps/api/tests/fixtures/sample_project/tests/test_app.py`
- Create: `apps/api/tests/test_project_scanner.py`

**Step 1: Write scanner tests**

Test that scanner:
- respects default ignored folders
- respects `.gitignore`
- returns language counts
- returns document files
- returns test files
- flags likely sensitive files without reading secret values
- skips files above size limit

**Step 2: Implement ignore handling**

Default ignores:

```text
.git
node_modules
dist
build
.next
.venv
__pycache__
*.log
*.png
*.jpg
*.jpeg
*.gif
*.pdf
*.zip
```

**Step 3: Implement scanner**

Return `ProjectScanSummary` with:
- root path
- total files
- scanned files
- skipped files
- languages
- docs
- tests
- config files
- entrypoint candidates
- sensitive file warnings

**Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_project_scanner.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/ignore_rules.py apps/api/app/services/project_scanner.py apps/api/tests
git commit -m "feat: add safe local project scanner"
```

## Task 5: Project API

**Files:**
- Create: `apps/api/app/api/projects.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_projects_api.py`

**Step 1: Write API tests**

Endpoints:
- `POST /projects/scan`
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`

**Step 2: Implement routes**

`POST /projects/scan` accepts:

```json
{"root_path":"F:/codebaby/ThirdEye","extra_ignore_patterns":[]}
```

It returns scan summary without persisting.

`POST /projects` persists project metadata and latest scan summary.

**Step 3: Run tests**

Run: `cd apps/api && pytest tests/test_projects_api.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/app/api/projects.py apps/api/app/main.py apps/api/tests/test_projects_api.py
git commit -m "feat: add project scan api"
```

## Task 6: Evidence Extraction

**Files:**
- Create: `apps/api/app/services/document_extractor.py`
- Create: `apps/api/app/services/code_extractor.py`
- Create: `apps/api/app/services/evidence_builder.py`
- Create: `apps/api/tests/test_evidence_builder.py`

**Step 1: Write extraction tests**

Use the sample project to assert:
- README becomes doc evidence
- source files become code evidence summaries
- tests become test evidence
- config files become config evidence
- evidence ids are stable for the same file path

**Step 2: Implement document extractor**

For MVP, chunk Markdown by headings and cap chunk length.

**Step 3: Implement code extractor**

For MVP, avoid full AST. Extract:
- file path
- language
- top-level function/class names with simple regex
- imports
- short file summary scaffold

**Step 4: Implement evidence builder**

Build `evidence.jsonl` records with:
- id
- source_type
- path
- symbol
- summary
- evidence_level
- metadata

**Step 5: Run tests**

Run: `cd apps/api && pytest tests/test_evidence_builder.py -q`  
Expected: PASS.

**Step 6: Commit**

```bash
git add apps/api/app/services/*extractor.py apps/api/app/services/evidence_builder.py apps/api/tests/test_evidence_builder.py
git commit -m "feat: extract project evidence"
```

## Task 7: Deterministic Playbook Generator

**Files:**
- Create: `apps/api/app/services/playbook_generator.py`
- Create: `apps/api/app/templates/playbook.skill.md.j2`
- Create: `apps/api/tests/test_playbook_generator.py`

**Step 1: Write generator tests**

Assert generated artifacts include:
- `playbook.skill.md`
- `project-summary.md`
- `rules.json`
- `evidence.jsonl`
- `metadata.json`

Assert playbook contains:
- activation rules
- core maintenance consensus
- decision heuristics
- anti-patterns
- technical proposal review workflow
- honesty boundary

**Step 2: Implement deterministic generator**

Before adding LLM distillation, generate a usable baseline from scan/evidence:
- infer project architecture from folders
- infer test policy from test files
- infer docs policy from README/docs
- create conservative `inferred` rules

**Step 3: Run tests**

Run: `cd apps/api && pytest tests/test_playbook_generator.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/app/services/playbook_generator.py apps/api/app/templates apps/api/tests/test_playbook_generator.py
git commit -m "feat: generate baseline playbook artifacts"
```

## Task 8: Playbook API

**Files:**
- Create: `apps/api/app/api/playbooks.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_playbooks_api.py`

**Step 1: Write API tests**

Endpoints:
- `POST /playbooks/distill`
- `GET /playbooks`
- `GET /playbooks/{playbook_id}`
- `GET /playbooks/{playbook_id}/artifact/{name}`
- `POST /playbooks/{playbook_id}/regenerate`

**Step 2: Implement routes**

`POST /playbooks/distill` accepts a `project_id`, runs scanner + evidence builder + baseline generator, and persists artifacts.

**Step 3: Run tests**

Run: `cd apps/api && pytest tests/test_playbooks_api.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/api/app/api/playbooks.py apps/api/app/main.py apps/api/tests/test_playbooks_api.py
git commit -m "feat: add playbook distillation api"
```

## Task 9: Model Provider Adapter

**Files:**
- Create: `apps/api/app/model_providers/adapter.py`
- Create: `apps/api/app/api/model_providers.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_model_providers.py`

**Step 1: Write adapter tests**

Test:
- OpenAI provider config validates without `base_url`
- OpenAI-compatible provider requires `base_url`
- API key is masked in serialized responses
- unsupported `api_shape` fails validation
- connection test can be mocked

**Step 2: Implement adapter**

Support:
- `responses` for OpenAI default path
- `chat_completions` using `AsyncOpenAI(base_url, api_key)` and `OpenAIChatCompletionsModel`
- tracing disabled by default for OpenAI-compatible providers

**Step 3: Implement provider API**

Endpoints:
- `POST /model-providers`
- `GET /model-providers`
- `GET /model-providers/{provider_id}`
- `POST /model-providers/{provider_id}/test`

**Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_model_providers.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/model_providers apps/api/app/api/model_providers.py apps/api/tests/test_model_providers.py
git commit -m "feat: add model provider adapter"
```

## Task 10: Agents SDK Distillation Workflow

**Files:**
- Create: `apps/api/app/agents/distillation.py`
- Create: `apps/api/app/agents/prompts/distillation.md`
- Modify: `apps/api/app/services/playbook_generator.py`
- Create: `apps/api/tests/test_distillation_workflow.py`

**Step 1: Write workflow tests with a fake model**

Test that when an LLM result is provided, the workflow:
- enriches baseline rules
- preserves evidence ids
- marks unsupported claims as `inferred`
- still writes all required artifacts

**Step 2: Implement distillation prompt**

Prompt must enforce:
- project-specific rules only
- evidence ids required for stable rules
- no PR/GitHub assumptions
- no code review/diff review behavior in MVP
- output JSON for rules and Markdown for skill

**Step 3: Implement workflow wrapper**

Use Agents SDK `Agent` and `Runner` through an internal service function:

```python
async def run_playbook_distillation(project, scan, evidence, provider_config) -> PlaybookArtifacts:
    ...
```

Fall back to deterministic generator when no model provider is configured.

**Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_distillation_workflow.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/agents apps/api/app/services/playbook_generator.py apps/api/tests/test_distillation_workflow.py
git commit -m "feat: add agents sdk distillation workflow"
```

## Task 11: Technical Proposal Review Workflow

**Files:**
- Create: `apps/api/app/agents/review.py`
- Create: `apps/api/app/agents/prompts/review.md`
- Create: `apps/api/app/services/playbook_loader.py`
- Create: `apps/api/app/api/reviews.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_review_workflow.py`
- Create: `apps/api/tests/test_reviews_api.py`

**Step 1: Write review workflow tests**

Given:
- a sample playbook
- a proposal text

Assert response includes:
- overall judgement
- key risks
- conflicts with playbook
- suggested changes
- required validation
- evidence levels

**Step 2: Implement playbook loader**

Load:
- `playbook.skill.md`
- `rules.json`
- `evidence.jsonl`
- `metadata.json`

**Step 3: Implement review prompt**

Prompt must enforce:
- evaluate proposal against selected project playbook
- no generic advice without project tie-in
- ask for missing information instead of inventing facts
- do not perform code review

**Step 4: Implement review API**

Endpoint:
- `POST /reviews`
- `GET /reviews/{review_id}`

**Step 5: Run tests**

Run: `cd apps/api && pytest tests/test_review_workflow.py tests/test_reviews_api.py -q`  
Expected: PASS.

**Step 6: Commit**

```bash
git add apps/api/app/agents/review.py apps/api/app/agents/prompts/review.md apps/api/app/services/playbook_loader.py apps/api/app/api/reviews.py apps/api/tests/test_review*
git commit -m "feat: add technical proposal review workflow"
```

## Task 12: Audit Logging

**Files:**
- Create: `apps/api/app/services/audit_log.py`
- Create: `apps/api/tests/test_audit_log.py`
- Modify: `apps/api/app/api/playbooks.py`
- Modify: `apps/api/app/api/reviews.py`

**Step 1: Write audit tests**

Test:
- distillation request writes audit event
- review request writes audit event
- API keys are redacted
- file content is not stored in audit log

**Step 2: Implement audit logger**

Write JSONL events under:

```text
data/audit/YYYY-MM-DD.jsonl
```

**Step 3: Wire audit calls**

Log:
- workflow name
- project id
- playbook id
- provider id
- timestamps
- success/failure
- artifact paths

**Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_audit_log.py tests/test_playbooks_api.py tests/test_reviews_api.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services/audit_log.py apps/api/tests/test_audit_log.py apps/api/app/api
git commit -m "feat: add local audit log"
```

## Task 13: Frontend API Client and Layout

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/components/AppNav.tsx`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/app/page.tsx`

**Step 1: Add API client**

Implement typed functions for:
- scan project
- create project
- distill playbook
- list playbooks
- get playbook
- create model provider
- test provider
- create review

**Step 2: Add navigation**

Nav links:
- Projects
- Playbooks
- Review
- Model Settings

**Step 3: Run frontend build**

Run: `cd apps/web && npm run build`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src
git commit -m "feat: add frontend shell and api client"
```

## Task 14: Project Distillation UI

**Files:**
- Create: `apps/web/src/app/projects/page.tsx`
- Create: `apps/web/src/components/ProjectScanForm.tsx`
- Create: `apps/web/src/components/ProjectScanSummary.tsx`
- Create: `apps/web/src/components/DistillProjectButton.tsx`

**Step 1: Build scan form**

Fields:
- root path
- extra ignore patterns textarea

Actions:
- Scan
- Save Project
- Start Distillation

**Step 2: Build scan summary**

Show:
- total files
- scanned files
- skipped files
- languages
- docs
- tests
- config files
- warnings

**Step 3: Wire distillation**

After distillation, route user to `/playbooks/{playbook_id}`.

**Step 4: Run build**

Run: `cd apps/web && npm run build`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/web/src/app/projects apps/web/src/components
git commit -m "feat: add project distillation ui"
```

## Task 15: Playbook Management UI

**Files:**
- Create: `apps/web/src/app/playbooks/page.tsx`
- Create: `apps/web/src/app/playbooks/[id]/page.tsx`
- Create: `apps/web/src/components/PlaybookList.tsx`
- Create: `apps/web/src/components/PlaybookDetail.tsx`
- Create: `apps/web/src/components/EvidenceList.tsx`

**Step 1: Build playbook list**

Display:
- name
- project
- version
- created time
- status

**Step 2: Build playbook detail**

Tabs:
- Skill Markdown
- Rules
- Evidence
- Metadata

**Step 3: Run build**

Run: `cd apps/web && npm run build`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/app/playbooks apps/web/src/components
git commit -m "feat: add playbook management ui"
```

## Task 16: Model Settings UI

**Files:**
- Create: `apps/web/src/app/settings/models/page.tsx`
- Create: `apps/web/src/components/ModelProviderForm.tsx`
- Create: `apps/web/src/components/ModelProviderList.tsx`

**Step 1: Build provider form**

Fields:
- provider name
- type
- base URL
- API key
- model
- API shape
- tracing enabled

**Step 2: Add connection test action**

Show:
- success/failure
- capability warnings
- redacted key

**Step 3: Run build**

Run: `cd apps/web && npm run build`  
Expected: PASS.

**Step 4: Commit**

```bash
git add apps/web/src/app/settings apps/web/src/components
git commit -m "feat: add model provider settings ui"
```

## Task 17: Review Chat UI

**Files:**
- Create: `apps/web/src/app/review/page.tsx`
- Create: `apps/web/src/components/ReviewComposer.tsx`
- Create: `apps/web/src/components/ReviewResult.tsx`
- Create: `apps/web/src/components/EvidencePanel.tsx`

**Step 1: Build review composer**

Inputs:
- playbook selector
- model provider selector
- review mode selector
- proposal textarea

**Step 2: Build result renderer**

Display:
- overall judgement
- key risks
- playbook conflicts
- suggested changes
- required validation
- missing information
- evidence references

**Step 3: Add evidence expansion**

Click evidence reference to show evidence summary and source path.

**Step 4: Run build**

Run: `cd apps/web && npm run build`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/web/src/app/review apps/web/src/components
git commit -m "feat: add technical proposal review ui"
```

## Task 18: End-to-End Smoke Script

**Files:**
- Create: `apps/api/scripts/create_sample_playbook.py`
- Create: `apps/api/tests/test_mvp_smoke.py`
- Create: `docs/mvp-smoke-test.md`

**Step 1: Write smoke test**

The test should:
- scan `apps/api/tests/fixtures/sample_project`
- create a project
- distill a playbook
- submit a sample technical proposal
- assert the review response has required fields

**Step 2: Add sample script**

Script creates a sample playbook from the fixture project for frontend manual testing.

**Step 3: Document manual smoke test**

Include:
- start API command
- start web command
- create provider
- scan project
- distill playbook
- review proposal

**Step 4: Run smoke test**

Run: `cd apps/api && pytest tests/test_mvp_smoke.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/scripts apps/api/tests/test_mvp_smoke.py docs/mvp-smoke-test.md
git commit -m "test: add mvp smoke flow"
```

## Task 19: Security Hardening

**Files:**
- Create: `apps/api/app/services/secret_scanner.py`
- Create: `apps/api/tests/test_secret_scanner.py`
- Modify: `apps/api/app/services/project_scanner.py`
- Modify: `apps/api/app/services/evidence_builder.py`
- Modify: `apps/api/app/services/audit_log.py`

**Step 1: Write secret scanner tests**

Detect patterns:
- `OPENAI_API_KEY=`
- `sk-`
- `password=`
- `BEGIN PRIVATE KEY`
- `.env`

**Step 2: Implement secret scanner**

Return warnings and redacted summaries. Do not store secret values.

**Step 3: Integrate scanner**

Ensure sensitive file content is not included in evidence or audit logs.

**Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_secret_scanner.py tests/test_project_scanner.py tests/test_evidence_builder.py tests/test_audit_log.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/app/services apps/api/tests/test_secret_scanner.py
git commit -m "feat: harden local file scanning"
```

## Task 20: Final MVP Verification

**Files:**
- Modify: `README.md`
- Create: `docs/mvp-acceptance.md`

**Step 1: Run backend tests**

Run: `cd apps/api && pytest -q`  
Expected: all tests pass.

**Step 2: Run frontend build**

Run: `cd apps/web && npm run build`  
Expected: build succeeds.

**Step 3: Run manual MVP flow**

Use `docs/mvp-smoke-test.md` and verify:
- local folder scan works
- playbook skill is generated
- playbook detail page renders artifacts
- OpenAI-compatible provider can be configured or mocked
- technical proposal review returns structured result

**Step 4: Update README**

Include:
- prerequisites
- backend setup
- frontend setup
- model provider setup
- MVP limitations
- explicit non-goals: no PR review, no GitHub integration, no code modification

**Step 5: Write acceptance summary**

Create `docs/mvp-acceptance.md` with:
- completed scope
- test commands
- known limitations
- follow-up backlog

**Step 6: Commit**

```bash
git add README.md docs/mvp-acceptance.md
git commit -m "docs: add mvp setup and acceptance notes"
```

## Implementation Notes

- Start with deterministic playbook generation before relying on LLM output. This gives stable tests and a working product even without a configured model provider.
- Keep filesystem tools read-only for selected project roots. Only write to `data/playbooks`, `data/reviews`, `data/model-providers`, and `data/audit`.
- Store API keys redacted in API responses. If persistence is local JSON for MVP, document that production must use encryption or a secret manager.
- Treat OpenAI-compatible providers as capability-variable. Connection tests should report supported features instead of assuming tool calling or structured output works.
- Keep PR/GitHub/diff review out of MVP code paths. It belongs in the P2 backlog only.

## P2 Backlog

- GitHub/GitLab project import.
- PR review and diff review.
- IDE plugin.
- Rule editing UI beyond enable/disable.
- Incremental project indexing.
- tree-sitter based symbol extraction.
- pgvector semantic retrieval.
- Team permissions and approval workflow.
