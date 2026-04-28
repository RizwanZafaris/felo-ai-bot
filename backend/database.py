"""Async SQLAlchemy engine + session management."""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import settings

log = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None


def get_engine() -> Optional[AsyncEngine]:
    global _engine
    if _engine is None:
        try:
            _engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=5)
        except Exception as e:
            log.warning("Failed to create DB engine: %s", e)
            _engine = None
    return _engine


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
