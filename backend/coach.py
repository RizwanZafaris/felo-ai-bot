"""Three-layer coach pipeline: pre-guardrail → retrieval+LLM → post-guardrail.

Quota is enforced by the caller (main.py) so a failed guardrail call does not
consume the user's monthly quota."""
import logging
from dataclasses import dataclass
from typing import Optional

from guardrails import GuardrailResult, post_guardrail, pre_guardrail
from models import RefusalCategory, Source, UserContext
from prompts import (
    COACH_SYSTEM_PROMPT_V1,
    POST_GUARDRAIL_CORRECTION_PROMPT,
    REFUSAL_TEMPLATES,
    SAFE_FALLBACK,
)
from providers import BaseProvider, CompletionResult
from retrieval import compress_context, context_sources

log = logging.getLogger(__name__)

# Cap history sent to LLM (defence-in-depth; main.py also bounds via deque maxlen).
MAX_HISTORY = 20


@dataclass
class CoachOutput:
    answer: str
    sources: list[Source]
    guardrail_triggered: bool = False
    refusal_category: Optional[RefusalCategory] = None
    tokens_used: int = 0
    cost_usd: float = 0.0


async def run_coach(
    *,
    message: str,
    history: list[dict],
    user_ctx: UserContext,
    provider: BaseProvider,
    model: str,
    classifier,
) -> CoachOutput:
    pre = await pre_guardrail(message, classifier)
    if pre.triggered:
        return CoachOutput(
            answer=pre.refusal_text or REFUSAL_TEMPLATES.get(
                pre.category.value if pre.category else "off_topic", SAFE_FALLBACK,
            ),
            sources=[],
            guardrail_triggered=True,
            refusal_category=pre.category,
        )

    ctx_str = compress_context(user_ctx)
    system = f"{COACH_SYSTEM_PROMPT_V1}\n\nUSER_CONTEXT:\n{ctx_str}"

    messages = [*history[-MAX_HISTORY:], {"role": "user", "content": message}]
    result: CompletionResult = await provider.complete(messages, system, model, stream=False)

    post = post_guardrail(result.text, user_ctx)
    if post.triggered:
        if post.category == RefusalCategory.UNGROUNDED_NUMBER:
            correction = POST_GUARDRAIL_CORRECTION_PROMPT.format(context=ctx_str, answer=result.text)
            try:
                retry = await provider.complete(
                    [*messages, {"role": "assistant", "content": result.text}, {"role": "user", "content": correction}],
                    system, model, stream=False,
                )
                if not post_guardrail(retry.text, user_ctx).triggered:
                    return CoachOutput(
                        answer=retry.text,
                        sources=[Source(**s) for s in context_sources(user_ctx)],
                        tokens_used=result.input_tokens + result.output_tokens
                                    + retry.input_tokens + retry.output_tokens,
                        cost_usd=result.cost_usd + retry.cost_usd,
                    )
            except Exception as e:
                log.warning("post-guardrail retry failed: %s", e)
        return CoachOutput(
            answer=SAFE_FALLBACK,
            sources=[],
            guardrail_triggered=True,
            refusal_category=post.category,
            tokens_used=result.input_tokens + result.output_tokens,
            cost_usd=result.cost_usd,
        )

    return CoachOutput(
        answer=result.text,
        sources=[Source(**s) for s in context_sources(user_ctx)],
        tokens_used=result.input_tokens + result.output_tokens,
        cost_usd=result.cost_usd,
    )
