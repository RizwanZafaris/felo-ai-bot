"""Pure Anthropic SDK alternative to coach.py — same pipeline, no LangChain.

Useful when you want the leanest possible dependency tree, or for benchmarking
LangChain overhead. Behaviour MUST match coach.run_coach()."""
from coach import CoachOutput, run_coach
from providers import AnthropicProvider


async def run_coach_pure(*, message, history, user_ctx, model, classifier) -> CoachOutput:
    return await run_coach(
        message=message, history=history, user_ctx=user_ctx,
        provider=AnthropicProvider(), model=model, classifier=classifier,
    )
