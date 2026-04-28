"""Optional LangGraph wrapper around the coach pipeline.

Kept minimal — the real logic lives in coach.run_coach. This module exists so
future tool-using agent flows (e.g. let the model query goals/bills via
function-calls instead of inlining UserContext) can plug in without rewriting
main.py."""
from typing import TypedDict

from coach import CoachOutput, run_coach
from models import UserContext


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict]
    user_ctx: UserContext
    output: CoachOutput


async def coach_node(state: AgentState, *, provider, model, classifier) -> AgentState:
    out = await run_coach(
        message=state["message"], history=state.get("history", []),
        user_ctx=state["user_ctx"], provider=provider, model=model, classifier=classifier,
    )
    return {**state, "output": out}
