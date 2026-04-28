"""Fetch and compress UserContext to <500 tokens before sending to LLM."""
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from models import Bill, Goal, Tier, Transaction, UserContext

log = logging.getLogger(__name__)

MAX_TRANSACTIONS = 10
MAX_GOALS = 5
MAX_BILLS = 8


async def fetch_user_context(engine: Optional[AsyncEngine], user_id: str) -> UserContext:
    """Fetch from DB; on any failure return a minimal stub so the coach can still
    respond ("ask the user for missing info") rather than crash."""
    if engine is None:
        return _stub(user_id)
    try:
        async with engine.connect() as conn:
            prof = (await conn.execute(text("""
                SELECT tier, monthly_income_pkr, monthly_spend_pkr, savings_pkr
                FROM user_profile WHERE user_id=:u
            """), {"u": user_id})).first()
            if not prof:
                return _stub(user_id)

            tx_rows = (await conn.execute(text("""
                SELECT id, amount_pkr, category, merchant, occurred_at
                FROM transactions WHERE user_id=:u
                ORDER BY occurred_at DESC LIMIT :n
            """), {"u": user_id, "n": MAX_TRANSACTIONS})).all()

            goal_rows = (await conn.execute(text("""
                SELECT id, name, target_pkr, current_pkr, deadline
                FROM goals WHERE user_id=:u LIMIT :n
            """), {"u": user_id, "n": MAX_GOALS})).all()

            bill_rows = (await conn.execute(text("""
                SELECT id, name, amount_pkr, due_day, paid_this_month
                FROM bills WHERE user_id=:u LIMIT :n
            """), {"u": user_id, "n": MAX_BILLS})).all()

        return UserContext(
            user_id=user_id,
            tier=Tier(prof[0]),
            monthly_income_pkr=float(prof[1] or 0),
            monthly_spend_pkr=float(prof[2] or 0),
            savings_pkr=float(prof[3] or 0),
            transactions=[Transaction(id=r[0], amount_pkr=float(r[1]), category=r[2], merchant=r[3], occurred_at=r[4]) for r in tx_rows],
            goals=[Goal(id=r[0], name=r[1], target_pkr=float(r[2]), current_pkr=float(r[3]), deadline=r[4]) for r in goal_rows],
            bills=[Bill(id=r[0], name=r[1], amount_pkr=float(r[2]), due_day=int(r[3]), paid_this_month=bool(r[4])) for r in bill_rows],
        )
    except Exception as e:
        log.warning("fetch_user_context failed for %s: %s", user_id, e)
        return _stub(user_id)


def _stub(user_id: str) -> UserContext:
    return UserContext(
        user_id=user_id, tier=Tier.FREE,
        monthly_income_pkr=0, monthly_spend_pkr=0, savings_pkr=0,
    )


def compress_context(ctx: UserContext) -> str:
    """Render UserContext as a compact string (<500 tokens) for the LLM prompt."""
    lines = [
        f"PROFILE: tier={ctx.tier.value} income={int(ctx.monthly_income_pkr)} spend={int(ctx.monthly_spend_pkr)} savings={int(ctx.savings_pkr)} (PKR/month)",
    ]
    if ctx.transactions:
        lines.append("TRANSACTIONS (recent):")
        for t in ctx.transactions[:MAX_TRANSACTIONS]:
            merchant = f" {t.merchant}" if t.merchant else ""
            lines.append(f"- {t.occurred_at.date()} {t.category}{merchant} {int(t.amount_pkr)}")
    if ctx.goals:
        lines.append("GOALS:")
        for g in ctx.goals:
            dl = f" by {g.deadline.date()}" if g.deadline else ""
            lines.append(f"- {g.name}: {int(g.current_pkr)}/{int(g.target_pkr)}{dl}")
    if ctx.bills:
        lines.append("BILLS:")
        for b in ctx.bills:
            paid = "paid" if b.paid_this_month else "due"
            lines.append(f"- {b.name} {int(b.amount_pkr)} day-{b.due_day} {paid}")
    return "\n".join(lines)


def context_sources(ctx: UserContext) -> list[dict]:
    out = [
        {"type": "profile", "label": "monthly income", "value": f"PKR {int(ctx.monthly_income_pkr)}"},
        {"type": "profile", "label": "monthly spend", "value": f"PKR {int(ctx.monthly_spend_pkr)}"},
        {"type": "profile", "label": "savings", "value": f"PKR {int(ctx.savings_pkr)}"},
    ]
    if ctx.goals:
        out.append({"type": "goals", "label": "active goals", "value": str(len(ctx.goals))})
    if ctx.bills:
        out.append({"type": "bills", "label": "tracked bills", "value": str(len(ctx.bills))})
    return out
