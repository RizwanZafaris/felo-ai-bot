"""Quota enforcement. MemoryQuotaStore for dev/tests, PostgresQuotaStore for prod."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from models import Tier, TIER_LIMITS, QuotaInfo

log = logging.getLogger(__name__)


def _ym(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


class QuotaStore(ABC):
    @abstractmethod
    async def check(self, user_id: str, tier: Tier) -> QuotaInfo: ...

    @abstractmethod
    async def increment(self, user_id: str, tier: Tier) -> QuotaInfo: ...


class MemoryQuotaStore(QuotaStore):
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], int] = {}

    async def check(self, user_id: str, tier: Tier) -> QuotaInfo:
        ym = _ym()
        used = self._store.get((user_id, ym), 0)
        limit = TIER_LIMITS[tier]
        return QuotaInfo(
            user_id=user_id, tier=tier, used=used, limit=limit,
            remaining=max(0, limit - used), year_month=ym,
        )

    async def increment(self, user_id: str, tier: Tier) -> QuotaInfo:
        ym = _ym()
        self._store[(user_id, ym)] = self._store.get((user_id, ym), 0) + 1
        return await self.check(user_id, tier)


class PostgresQuotaStore(QuotaStore):
    def __init__(self, engine: AsyncEngine, fallback: Optional[QuotaStore] = None) -> None:
        self.engine = engine
        self.fallback = fallback or MemoryQuotaStore()

    async def check(self, user_id: str, tier: Tier) -> QuotaInfo:
        ym = _ym()
        try:
            async with self.engine.begin() as conn:
                row = (await conn.execute(
                    text("SELECT calls_used FROM quota_usage WHERE user_id=:u AND year_month=:ym"),
                    {"u": user_id, "ym": ym},
                )).first()
                used = row[0] if row else 0
        except Exception as e:
            log.warning("PostgresQuotaStore.check failed, falling back: %s", e)
            return await self.fallback.check(user_id, tier)

        limit = TIER_LIMITS[tier]
        return QuotaInfo(
            user_id=user_id, tier=tier, used=used, limit=limit,
            remaining=max(0, limit - used), year_month=ym,
        )

    async def increment(self, user_id: str, tier: Tier) -> QuotaInfo:
        ym = _ym()
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("""
                    INSERT INTO quota_usage (user_id, year_month, calls_used, updated_at)
                    VALUES (:u, :ym, 1, NOW())
                    ON CONFLICT (user_id, year_month)
                    DO UPDATE SET calls_used = quota_usage.calls_used + 1, updated_at = NOW()
                """), {"u": user_id, "ym": ym})
        except Exception as e:
            log.warning("PostgresQuotaStore.increment failed, falling back: %s", e)
            return await self.fallback.increment(user_id, tier)
        return await self.check(user_id, tier)
