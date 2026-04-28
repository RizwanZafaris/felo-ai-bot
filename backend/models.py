from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Tier(str, Enum):
    FREE = "free"
    PLUS = "plus"
    PLUS_PLUS = "plus_plus"
    FAMILY = "family"


TIER_LIMITS: dict[Tier, int] = {
    Tier.FREE: 30,
    Tier.PLUS: 150,
    Tier.PLUS_PLUS: 400,
    Tier.FAMILY: 400,
}


class RefusalCategory(str, Enum):
    INVESTMENT_ADVICE = "investment_advice"
    TAX_ADVICE = "tax_advice"
    LEGAL_ADVICE = "legal_advice"
    MEDICAL_ADVICE = "medical_advice"
    UNGROUNDED_NUMBER = "ungrounded_number"
    SHAMING_LANGUAGE = "shaming_language"
    OFF_TOPIC = "off_topic"
    PROMPT_INJECTION = "prompt_injection"
    GUARANTEE_RETURNS = "guarantee_returns"
    SYSTEM_LEAK = "system_leak"
    PERSONAL_DATA_LEAK = "personal_data_leak"


class Transaction(BaseModel):
    id: str
    amount_pkr: float
    category: str
    merchant: Optional[str] = None
    occurred_at: datetime


class Goal(BaseModel):
    id: str
    name: str
    target_pkr: float
    current_pkr: float
    deadline: Optional[datetime] = None


class Bill(BaseModel):
    id: str
    name: str
    amount_pkr: float
    due_day: int
    paid_this_month: bool = False


class UserContext(BaseModel):
    user_id: str
    tier: Tier
    monthly_income_pkr: float
    monthly_spend_pkr: float
    savings_pkr: float
    transactions: list[Transaction] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)
    bills: list[Bill] = Field(default_factory=list)


class Source(BaseModel):
    type: str
    label: str
    value: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str
    user_id: str
    model: str = "claude-sonnet-4-6"
    provider: str = "anthropic"


class CoachResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[Source] = Field(default_factory=list)
    guardrail_triggered: bool = False
    refusal_category: Optional[RefusalCategory] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    quota_remaining: int = 0


class QuotaInfo(BaseModel):
    user_id: str
    tier: Tier
    used: int
    limit: int
    remaining: int
    year_month: str


class ModelInfo(BaseModel):
    provider: str
    model: str
    input_per_m: float
    output_per_m: float


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
