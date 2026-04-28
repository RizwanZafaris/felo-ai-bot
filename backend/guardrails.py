"""Pre and post guardrail logic. Pre-guardrail uses cheap classifier; post-guardrail
verifies grounding and catches hallucinated numbers."""
import re
from dataclasses import dataclass
from typing import Optional

from models import RefusalCategory, UserContext
from prompts import PRE_GUARDRAIL_CLASSIFIER_PROMPT, REFUSAL_TEMPLATES


PKR_PATTERN = re.compile(r"(?:PKR|Rs\.?|₨)\s?([\d,]+(?:\.\d+)?)|([\d,]{4,})\s?(?:PKR|Rs\.?|₨|rupees)", re.IGNORECASE)

INJECTION_PATTERNS = [
    re.compile(r"ignore (all |the )?(previous|prior|above) (instructions|prompt)", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"reveal your (instructions|rules|prompt)", re.I),
]

SHAMING_PATTERNS = [
    re.compile(r"\byou (spent|wasted) too much\b", re.I),
    re.compile(r"\byou should be ashamed\b", re.I),
    re.compile(r"\bthat's irresponsible\b", re.I),
]

GUARANTEE_PATTERNS = [
    re.compile(r"\bguaranteed (return|savings|profit)\b", re.I),
    re.compile(r"\byou (will|definitely will) (save|earn|make)\s+(?:PKR|Rs\.?|₨)", re.I),
]


@dataclass
class GuardrailResult:
    triggered: bool
    category: Optional[RefusalCategory] = None
    refusal_text: Optional[str] = None


def _quick_injection_check(message: str) -> Optional[RefusalCategory]:
    for pat in INJECTION_PATTERNS:
        if pat.search(message):
            return RefusalCategory.PROMPT_INJECTION
    return None


async def pre_guardrail(message: str, classifier) -> GuardrailResult:
    """Cheap pre-check using a classifier (e.g. Haiku).

    `classifier` is an async callable taking a prompt and returning the label string.
    Refusals here MUST NOT consume the user's main quota — caller enforces that.
    """
    if cat := _quick_injection_check(message):
        return GuardrailResult(True, cat, REFUSAL_TEMPLATES["prompt_injection"])

    try:
        label = (await classifier(PRE_GUARDRAIL_CLASSIFIER_PROMPT.format(message=message))).strip().upper()
    except Exception:
        return GuardrailResult(False)  # fail-open on classifier outage; post-guardrail still runs

    mapping = {
        "INVESTMENT_ADVICE": RefusalCategory.INVESTMENT_ADVICE,
        "TAX_ADVICE": RefusalCategory.TAX_ADVICE,
        "LEGAL_ADVICE": RefusalCategory.LEGAL_ADVICE,
        "MEDICAL_ADVICE": RefusalCategory.MEDICAL_ADVICE,
        "OFF_TOPIC": RefusalCategory.OFF_TOPIC,
        "PROMPT_INJECTION": RefusalCategory.PROMPT_INJECTION,
    }
    if cat := mapping.get(label):
        return GuardrailResult(True, cat, REFUSAL_TEMPLATES[cat.value])
    return GuardrailResult(False)


def _normalize(num_str: str) -> Optional[int]:
    """Normalize a captured number string to an int (PKR rounded down).
    Returns None if the value is below the meaningful threshold."""
    try:
        v = int(float(num_str.replace(",", "")))
    except (ValueError, TypeError):
        return None
    return v if v >= 100 else None


def _extract_numbers(text: str) -> set[int]:
    found: set[int] = set()
    for m in PKR_PATTERN.finditer(text):
        raw = (m.group(1) or m.group(2) or "")
        v = _normalize(raw)
        if v is not None:
            found.add(v)
    return found


def _context_numbers(ctx: UserContext) -> set[int]:
    nums: set[int] = {
        int(ctx.monthly_income_pkr),
        int(ctx.monthly_spend_pkr),
        int(ctx.savings_pkr),
    }
    for t in ctx.transactions:
        nums.add(int(t.amount_pkr))
    for g in ctx.goals:
        nums.add(int(g.target_pkr))
        nums.add(int(g.current_pkr))
    for b in ctx.bills:
        nums.add(int(b.amount_pkr))
    return {n for n in nums if n >= 100}


def post_guardrail(answer: str, ctx: UserContext) -> GuardrailResult:
    """Verify every PKR figure in the answer comes from UserContext, plus heuristic
    checks for shaming language, guarantees, and system-prompt leaks."""
    for pat in SHAMING_PATTERNS:
        if pat.search(answer):
            return GuardrailResult(True, RefusalCategory.SHAMING_LANGUAGE)
    for pat in GUARANTEE_PATTERNS:
        if pat.search(answer):
            return GuardrailResult(True, RefusalCategory.GUARANTEE_RETURNS)
    if "system prompt" in answer.lower() or "COACH_SYSTEM_PROMPT" in answer:
        return GuardrailResult(True, RefusalCategory.SYSTEM_LEAK)

    answer_nums = _extract_numbers(answer)
    allowed = _context_numbers(ctx)
    # Allow ±1 PKR tolerance (rounding from decimal values like 120000.50)
    fabricated = {n for n in answer_nums if not any(abs(n - a) <= 1 for a in allowed)}
    if fabricated:
        return GuardrailResult(True, RefusalCategory.UNGROUNDED_NUMBER)

    return GuardrailResult(False)
