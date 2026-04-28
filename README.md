# FELO Coach — AI Financial Assistant

Pakistani personal-finance AI coach with a multi-provider LLM backend, strict guardrails, monthly quota enforcement, and a 5-stage request pipeline.

## Architecture (5-stage pipeline)

```
Client → [1] Quota → [2] Pre-guardrail (Haiku) → [3] Retrieval (UserContext)
       → [4] LLM (Anthropic / OpenAI / Gemini / DeepSeek)
       → [5] Post-guardrail → deduct quota → log → response
```

A failed pre-guardrail returns a refusal **without** consuming the user's monthly quota. A failed post-guardrail retries once with a correction prompt, then falls back to a safe message.

## Quick start

### Docker

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY at minimum
docker-compose up --build
# backend at http://localhost:8000
# frontend: open frontend/index.html or `python -m http.server -d frontend 3000`
```

### Manual

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# in another shell:
python -m http.server -d frontend 3000
```

## Adding a new LLM provider (3 steps)

1. Subclass `BaseProvider` in `backend/providers.py`, implement `complete()`.
2. Add cost rates to `COST_RATES` in `backend/cost_model.py`.
3. Register in `PROVIDER_REGISTRY` and add an entry to `AVAILABLE_MODELS`.

## Changing tier limits

Single source of truth: `backend/models.py` → `TIER_LIMITS`.

```python
TIER_LIMITS = { Tier.FREE: 30, Tier.PLUS: 150, Tier.PLUS_PLUS: 400, Tier.FAMILY: 400 }
```

## Cost model summary

| Scenario | Per-call (Sonnet) | @1k users / 53 calls avg |
|---|---|---|
| **Naive** (no caching, full ctx every call) | ~$0.022 | ~$1,170/mo |
| **Production** (system-prompt cache) | ~$0.011 | ~$580/mo |
| **Optimised** (cache + context compression + Haiku for trivial Qs) | ~$0.0073 | ~$390/mo |

See `backend/cost_model.py` for raw rates.

## Eval harness

```bash
cd /tmp/felo-ai-bot
pip install -r backend/requirements.txt
pytest                          # offline: test_coach.py + test_guardrails.py
# integration:
uvicorn backend.main:app &
pytest eval/test_api.py
```

## Hard refusal rules (all 11)

The coach will refuse and not consume quota when it detects:

1. **Investment advice** — stocks, funds, crypto, specific products
2. **Tax advice** — filing, deductions, FBR
3. **Legal advice** — contracts, lawsuits
4. **Medical advice** — health, medications
5. **Ungrounded numbers** — any PKR figure not in UserContext (post-guardrail)
6. **Shaming language** — judgmental output (post-guardrail)
7. **Off-topic** — weather, sports, dating, code
8. **Prompt injection** — "ignore previous instructions" etc.
9. **Guaranteed returns** — "you'll definitely save X" (post-guardrail)
10. **System-prompt leak** — reveals coach instructions (post-guardrail)
11. **Cross-user data leak** — never reference data not in UserContext

Pre-guardrail catches 1–4, 7, 8. Post-guardrail catches 5, 6, 9, 10, 11.

## Project layout

```
backend/    FastAPI + coach pipeline
frontend/   Dark-themed dev UI (vanilla JS, no build)
mobile/     Expo / RN client (chat + settings + quota meter)
eval/       Offline + integration tests
db/         init.sql
```

## Notes

- The existing `appuifelo` repo is **Flutter**; the Expo client here is a fallback / dev UI. To wire FELO Coach into the production Flutter app, port `mobile/api/coach.ts` to a Dart `CoachApi` service and replicate the chat screen.
- Conversation content is **never** persisted. Sessions live in-process for `SESSION_TTL_MINUTES` (default 30).
- Logs include token counts and cost — never message content.
