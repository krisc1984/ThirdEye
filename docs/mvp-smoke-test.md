# MVP Smoke Test

This document verifies the current ThirdEye MVP flow from local project scan to proposal review.

## Prerequisites

- Python environment for `apps/api` dependencies is installed.
- Node dependencies for `apps/web` are installed.
- Optional: a model provider configuration if you want to exercise provider-backed review or distillation.

## Start the API

From [apps/api](F:\codebaby\ThirdEye\apps\api):

```bash
python -m uvicorn app.main:app --reload
```

Default API base URL:

```text
http://127.0.0.1:8000
```

## Start the Web App

From [apps/web](F:\codebaby\ThirdEye\apps\web):

```bash
npm run dev
```

Default frontend URL:

```text
http://127.0.0.1:3000
```

If needed, set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Optional: Seed a Sample Playbook

From [apps/api](F:\codebaby\ThirdEye\apps\api):

```bash
python scripts/create_sample_playbook.py
```

This creates a project and playbook for `apps/api/tests/fixtures/sample_project` and prints the generated IDs.

## Manual Smoke Flow

### 1. Create a model provider

Open `/settings/models` and create either:

- `openai` with `responses`
- `openai_compatible` with `chat_completions` and a `base_url`

Use the `Test Connection` button and confirm:

- the request succeeds
- provider capabilities are shown
- the API key stays redacted in the saved list

### 2. Scan and save a project

Open `/projects` and enter:

```text
F:\codebaby\ThirdEye\apps\api\tests\fixtures\sample_project
```

Then:

- click `Scan`
- confirm docs, tests, config files, and language counts render
- click `Save Project`

### 3. Distill a playbook

Still on `/projects`:

- click `Start Distillation`
- confirm the app routes to `/playbooks/{playbook_id}`
- verify the detail page shows skill markdown, rules, evidence, and metadata

### 4. Review a technical proposal

Open `/review` and:

- choose the new playbook
- optionally choose a model provider
- enter a proposal such as:

```text
Add a background indexing worker for project ingestion, keep the API layer thin, touch only the ingestion module, and validate the change with existing pytest coverage.
```

- click `Run Review`

Confirm the UI returns:

- overall judgement
- key risks
- playbook conflicts
- suggested changes
- required validation
- missing information if applicable
- evidence-linked findings with expandable evidence details

## Automated Smoke Test

From [apps/api](F:\codebaby\ThirdEye\apps\api):

```bash
pytest tests/test_mvp_smoke.py -q
```

Expected result:

```text
1 passed
```
