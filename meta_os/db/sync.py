"""Cross-device DB sync: Chromebook = master, Pixel = replica with offline queue."""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from meta_os.config import config
from meta_os.db.models import Base, OfflineQueueItem

# Offline queue engine (always local, even on master)
_queue_engine = create_async_engine(
    f"sqlite+aiosqlite:///{config.offline_queue_path}",
    connect_args={"check_same_thread": False, "timeout": 5},
)
_queue_session = async_sessionmaker(_queue_engine, expire_on_commit=False)


async def init_sync_db() -> None:
    async with _queue_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def queue_write(table_name: str, operation: str, payload: dict) -> None:
    """Queue a write for sync to master when online."""
    if config.is_db_master:
        return  # master writes directly, no queue needed
    async with _queue_session() as session:
        session.add(OfflineQueueItem(
            id=str(uuid4()),
            table_name=table_name,
            operation=operation,
            payload=json.dumps(payload),
        ))
        await session.commit()


async def flush_queue() -> int:
    """Sync offline queue to Chromebook master. Returns count synced."""
    if config.is_db_master:
        return 0
    synced = 0
    async with _queue_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(OfflineQueueItem).where(OfflineQueueItem.synced == False).limit(100)  # noqa
        )
        items = result.scalars().all()
        if not items:
            return 0
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{config.db_master_host}/sync/batch",
                    json=[{
                        "table": i.table_name,
                        "operation": i.operation,
                        "payload": json.loads(i.payload),
                    } for i in items]
                )
                if resp.status_code == 200:
                    for item in items:
                        item.synced = True
                    await session.commit()
                    synced = len(items)
        except Exception:
            pass  # Will retry on next flush
    return synced


# FastAPI router for the master DB sync endpoint (runs on Chromebook)
sync_app = FastAPI()


@sync_app.post("/sync/batch")
async def receive_batch(items: list[dict]) -> dict:
    """Receive batched writes from Pixel and apply to master DB."""
    from meta_os.db.ops import get_db
    from meta_os.db.models import Turn, CostLog
    applied = 0
    async with get_db() as db:
        for item in items:
            table, op, payload = item["table"], item["operation"], item["payload"]
            if table == "turns" and op == "insert":
                db.add(Turn(**payload))
                applied += 1
            elif table == "cost_logs" and op == "insert":
                db.add(CostLog(**payload))
                applied += 1
    return {"applied": applied}


async def sync_loop() -> None:
    """Background loop: flush offline queue every 30s."""
    while True:
        await asyncio.sleep(30)
        await flush_queue()
