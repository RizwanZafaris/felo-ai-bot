# felo-ai-bot — DEPRECATED (merged into appbackendfelo)

> **Status:** Archived as of 2026-04-28. Active development is in
> [`RizwanZafaris/appbackendfelo`](https://github.com/RizwanZafaris/appbackendfelo)
> under `src/modules/coach/llm/`.

## Why

This Python/FastAPI service was built as a standalone scaffold. Once we
inventoried the actual FELO repos we found:

- `appbackendfelo` already has a `coach` NestJS module with persistence
  (`coach_conversations`, `coach_queries`), Supabase auth, and the Flutter
  integration baked in.
- `appuifelo` already has the Flutter chat UI.

A parallel Python service would have duplicated persistence and added a
network hop with no upside. Instead the LLM pipeline (guardrails, number
grounding, multi-provider adapter, prompts, cost model, quota) was ported
into the NestJS module on branch `feat/coach-llm-merge`.

## Where each piece went

| Python file | NestJS equivalent (in appbackendfelo) |
|---|---|
| `backend/coach.py` | `src/modules/coach/llm/llm-coach.service.ts` |
| `backend/guardrails.py` | `src/modules/coach/llm/guardrails/guardrails.service.ts` |
| `backend/prompts.py` | `src/modules/coach/llm/prompts.ts` |
| `backend/providers.py` | `src/modules/coach/llm/providers/` |
| `backend/cost_model.py` | `src/modules/coach/llm/cost-model.ts` |
| `backend/quota.py` | `src/modules/coach/llm/coach-quota.service.ts` (uses existing `coach_queries` table) |
| `backend/retrieval.py` | `src/modules/coach/llm/retrieval/retrieval.service.ts` |
| `backend/models.py` (Pydantic) | `src/modules/coach/dto/chat.dto.ts` + `llm/retrieval/coach-context.ts` |
| `eval/test_guardrails.py` (9 tests) | `src/modules/coach/llm/guardrails/guardrails.service.spec.ts` (12 Jest tests) |

## Frontend / mobile scaffolds

The `frontend/` and `mobile/` (Expo) scaffolds were development-only
experiments. Production UI lives in
[`RizwanZafaris/appuifelo`](https://github.com/RizwanZafaris/appuifelo)
(Flutter, `lib/features/coach/`).

## Useful as

Kept read-only for:

- Reference implementation when iterating on guardrails or prompts in
  isolation.
- Offline eval harness (Python is faster to iterate on for prompt
  engineering than spinning up the full NestJS stack).
- pytest-based fuzzing of the number-grounding regex.

If you want to revive it as a sidecar later, the last working commit is
`299672c` (security: dep CVE upgrades + bug fixes).
