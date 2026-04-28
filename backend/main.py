"""FastAPI app wiring quota → pre-guardrail → retrieval → LLM → post-guardrail."""
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from coach import run_coach
from config import settings
from database import dispose_engine, get_engine
from models import (
    ChatRequest, CoachResponse, ModelInfo, ModelsResponse,
    QuotaInfo, Tier,
)
from prompts import COACH_SYSTEM_PROMPT_V1
from providers import AVAILABLE_MODELS, get_provider
from quota import MemoryQuotaStore, PostgresQuotaStore, QuotaStore
from retrieval import compress_context, fetch_user_context
from cost_model import COST_RATES

logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger("felo.coach")

# In-memory session store — short-lived, NEVER persisted.
# Key is (user_id, session_id) so a stolen session_id alone cannot read another
# user's conversation history.
_sessions: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=settings.MAX_SESSION_MESSAGES))
_session_touched: dict[tuple[str, str], float] = {}

_quota: QuotaStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _quota
    engine = get_engine()
    _quota = PostgresQuotaStore(engine, fallback=MemoryQuotaStore()) if engine else MemoryQuotaStore()
    yield
    await dispose_engine()


limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

app = FastAPI(title="FELO Coach", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8081"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request, exc):
    return _err(429, "rate_limited", "Too many requests. Please slow down.")


def _err(status: int, code: str, msg: str, **extra):
    raise HTTPException(status_code=status, detail={"error": code, "message": msg, **extra})


async def _haiku_classifier(prompt: str) -> str:
    """Cheap classifier used by pre-guardrail. Uses Anthropic Haiku."""
    try:
        provider = get_provider("anthropic")
        result = await provider.complete(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a strict classifier. Reply with one label only.",
            model="claude-haiku-4-5", stream=False,
        )
        return result.text
    except Exception as e:
        log.warning("classifier failed: %s", e)
        return "ALLOW"


def _trim_sessions() -> None:
    now = time.time()
    ttl = settings.SESSION_TTL_MINUTES * 60
    stale = [k for k, t in _session_touched.items() if now - t > ttl]
    for k in stale:
        _sessions.pop(k, None)
        _session_touched.pop(k, None)


VALID_PAIRS: set[tuple[str, str]] = {(m["provider"], m["model"]) for m in AVAILABLE_MODELS}


async def _resolve_tier(user_id: str) -> Tier:
    engine = get_engine()
    if engine is None:
        return Tier.FREE
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            row = (await conn.execute(text("SELECT tier FROM user_profile WHERE user_id=:u"), {"u": user_id})).first()
            return Tier(row[0]) if row else Tier.FREE
    except Exception:
        return Tier.FREE


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/models", response_model=ModelsResponse)
async def list_models():
    items = []
    for m in AVAILABLE_MODELS:
        rates = COST_RATES.get(m["model"], {})
        items.append(ModelInfo(
            provider=m["provider"], model=m["model"],
            input_per_m=rates.get("input", 0), output_per_m=rates.get("output", 0),
        ))
    return ModelsResponse(models=items)


@app.get("/api/quota/{user_id}", response_model=QuotaInfo)
async def get_quota(user_id: str):
    tier = await _resolve_tier(user_id)
    return await _quota.check(user_id, tier)


@app.delete("/api/chat/{session_id}")
async def clear_session(session_id: str, user_id: str):
    """user_id is required as a query param so a leaked session_id alone can't
    delete another user's history."""
    key = (user_id, session_id)
    _sessions.pop(key, None)
    _session_touched.pop(key, None)
    return {"cleared": True}


def _validate_provider_model(provider: str, model: str) -> None:
    if (provider, model) not in VALID_PAIRS:
        _err(400, "unknown_provider_model",
             f"Provider/model pair not supported: {provider}/{model}")


@app.post("/api/chat", response_model=CoachResponse)
async def chat(req: ChatRequest, request: Request):
    _validate_provider_model(req.provider, req.model)

    _trim_sessions()
    tier = await _resolve_tier(req.user_id)
    qinfo = await _quota.check(req.user_id, tier)
    if qinfo.remaining <= 0:
        _err(429, "quota_exceeded", "Monthly quota exhausted.",
             quota={"used": qinfo.used, "limit": qinfo.limit, "year_month": qinfo.year_month})

    user_ctx = await fetch_user_context(get_engine(), req.user_id)
    key = (req.user_id, req.session_id)
    history = list(_sessions[key])

    try:
        provider = get_provider(req.provider)
    except ValueError as e:
        _err(400, "unknown_provider", str(e))

    output = await run_coach(
        message=req.message, history=history, user_ctx=user_ctx,
        provider=provider, model=req.model, classifier=_haiku_classifier,
    )

    if not output.guardrail_triggered:
        _sessions[key].append({"role": "user", "content": req.message})
        _sessions[key].append({"role": "assistant", "content": output.answer})
        _session_touched[key] = time.time()
        qinfo = await _quota.increment(req.user_id, tier)

    log.info(
        "chat user=%s session=%s tokens=%d cost=$%.5f guardrail=%s",
        req.user_id, req.session_id, output.tokens_used, output.cost_usd, output.guardrail_triggered,
    )

    return CoachResponse(
        answer=output.answer,
        session_id=req.session_id,
        sources=output.sources,
        guardrail_triggered=output.guardrail_triggered,
        refusal_category=output.refusal_category,
        tokens_used=output.tokens_used,
        cost_usd=output.cost_usd,
        quota_remaining=qinfo.remaining,
    )


def _sse_escape(text: str) -> str:
    """Escape newlines so SSE event delimiters aren't broken by data tokens."""
    return text.replace("\r", "").replace("\n", "\\n")


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming. Pre/post-guardrail still apply: pre runs before any stream
    starts; post runs on the accumulated text after the stream completes."""
    _validate_provider_model(req.provider, req.model)
    _trim_sessions()

    tier = await _resolve_tier(req.user_id)
    qinfo = await _quota.check(req.user_id, tier)
    if qinfo.remaining <= 0:
        _err(429, "quota_exceeded", "Monthly quota exhausted.")

    user_ctx = await fetch_user_context(get_engine(), req.user_id)
    key = (req.user_id, req.session_id)
    history = list(_sessions[key])
    provider = get_provider(req.provider)

    async def _event_stream():
        from guardrails import post_guardrail, pre_guardrail
        from prompts import SAFE_FALLBACK

        pre = await pre_guardrail(req.message, _haiku_classifier)
        if pre.triggered:
            yield f"event: refusal\ndata: {_sse_escape(pre.refusal_text or '')}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        ctx_str = compress_context(user_ctx)
        system = f"{COACH_SYSTEM_PROMPT_V1}\n\nUSER_CONTEXT:\n{ctx_str}"
        messages = [*history, {"role": "user", "content": req.message}]
        accumulated = ""
        try:
            stream_gen = await provider.complete(messages, system, req.model, stream=True)
            async for token in stream_gen:
                accumulated += token
                yield f"data: {_sse_escape(token)}\n\n"
        except Exception as e:
            log.warning("stream failed: %s", e)
            yield "event: error\ndata: stream failed\n\n"
            return

        post = post_guardrail(accumulated, user_ctx)
        if post.triggered:
            yield f"event: guardrail\ndata: {_sse_escape(SAFE_FALLBACK)}\n\n"
        else:
            _sessions[key].append({"role": "user", "content": req.message})
            _sessions[key].append({"role": "assistant", "content": accumulated})
            _session_touched[key] = time.time()
            await _quota.increment(req.user_id, tier)

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
