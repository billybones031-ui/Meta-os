"""Async database operations."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from meta_os.config import config
from meta_os.db.models import Base, CostLog, OfflineQueueItem, ScheduledJob, Session, Turn

_engine = create_async_engine(
    f"sqlite+aiosqlite:///{config.db_path}",
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 5},
)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db() -> AsyncSession:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def save_turn(
    session_id: str,
    workspace: str,
    user_message: str,
    bot_response: str,
    agents_used: list[str],
    token_usage: dict,
) -> str:
    turn_id = str(uuid4())
    async with get_db() as db:
        db.add(Turn(
            id=turn_id,
            session_id=session_id,
            workspace=workspace,
            user_message=user_message,
            bot_response=bot_response,
            agents_used=json.dumps(agents_used),
            token_usage=json.dumps(token_usage),
        ))
    return turn_id


async def save_context(session_id: str, workspace: str, context: list) -> None:
    async with get_db() as db:
        obj = await db.get(Session, session_id)
        if obj is None:
            obj = Session(id=session_id, workspace=workspace)
            db.add(obj)
        obj.set_context(context)


async def load_context(session_id: str) -> list:
    async with get_db() as db:
        obj = await db.get(Session, session_id)
        return obj.get_context() if obj else []


async def log_cost_async(
    provider: str, model: str, input_tokens: int, output_tokens: int,
    est_cost: float, workspace: str
) -> None:
    async with get_db() as db:
        db.add(CostLog(
            id=str(uuid4()),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            est_cost_usd=est_cost,
            workspace=workspace,
        ))


async def get_recent_costs(days: int = 7) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with get_db() as db:
        result = await db.execute(select(CostLog).where(CostLog.timestamp >= cutoff))
        return [
            {
                "provider": r.provider, "model": r.model,
                "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "est_cost_usd": r.est_cost_usd, "workspace": r.workspace,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in result.scalars().all()
        ]


async def get_all_turns(limit: int = 20) -> list[dict]:
    async with get_db() as db:
        result = await db.execute(
            select(Turn).order_by(Turn.timestamp.desc()).limit(limit)
        )
        return [
            {
                "id": t.id, "session_id": t.session_id, "workspace": t.workspace,
                "user_message": t.user_message[:100], "bot_response": t.bot_response[:100],
                "agents_used": json.loads(t.agents_used),
                "timestamp": t.timestamp.isoformat(),
            }
            for t in result.scalars().all()
        ]
