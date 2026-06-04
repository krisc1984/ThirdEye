# MVP Acceptance

## Completed Scope

- Local project scanning with ignore rules, language counts, docs/tests/config discovery, and sensitive-file warnings
- Deterministic playbook generation with persisted markdown, rules, evidence, and metadata artifacts
- Optional provider-aware distillation and review workflow wrappers
- Review API with structured findings, validation guidance, and evidence references
- Model provider configuration and lightweight connection testing
- Frontend pages for project scan, playbook browsing, model settings, and proposal review
- Local audit logging with key redaction and content filtering
- Security hardening for secret-like file detection and redacted evidence summaries

## Verification Commands

Backend:

```bash
cd apps/api
pytest -q
```

Frontend:

```bash
cd apps/web
npm run build
```

Smoke test:

```bash
cd apps/api
pytest tests/test_mvp_smoke.py -q
```

Manual smoke flow:

- See [docs/mvp-smoke-test.md](F:\codebaby\ThirdEye\docs\mvp-smoke-test.md)

## Known Limitations

- Provider persistence is local JSON and should not be treated as production-safe secret storage
- OpenAI-compatible providers are validated at configuration level, not via a guaranteed full inference call
- Review quality is intentionally bounded by local evidence and deterministic heuristics
- Playbook rule editing and regeneration tuning are still minimal

## Follow-up Backlog

- Replace local provider secret storage with encrypted persistence or a secret manager
- Add stronger provider capability negotiation and real inference smoke checks
- Improve review quality with richer prompt orchestration and structured model outputs
- Add GitHub/GitLab import and non-MVP PR review as a later phase
- Introduce incremental indexing and higher-fidelity code understanding
