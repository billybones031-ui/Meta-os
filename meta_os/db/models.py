"""SQLAlchemy ORM models."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    workspace = Column(String, default="personal")
    context_blob = Column(Text, default="[]")  # JSON messages[]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_context(self) -> list:
        return json.loads(self.context_blob or "[]")

    def set_context(self, ctx: list) -> None:
        self.context_blob = json.dumps(ctx[-50:])  # cap at 50 turns


class Turn(Base):
    __tablename__ = "turns"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    workspace = Column(String, default="personal")
    user_message = Column(Text)
    bot_response = Column(Text)
    agents_used = Column(Text, default="[]")    # JSON list
    token_usage = Column(Text, default="{}")    # JSON dict
    timestamp = Column(DateTime, default=datetime.utcnow)


class CostLog(Base):
    __tablename__ = "cost_logs"
    id = Column(String, primary_key=True)
    provider = Column(String)
    model = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    est_cost_usd = Column(Float, default=0.0)
    workspace = Column(String, default="personal")
    timestamp = Column(DateTime, default=datetime.utcnow)


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    id = Column(String, primary_key=True)
    name = Column(String)
    cron_expr = Column(String)
    prompt = Column(Text)
    workspace = Column(String, default="personal")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OfflineQueueItem(Base):
    __tablename__ = "offline_queue"
    id = Column(String, primary_key=True)
    table_name = Column(String)
    operation = Column(String)  # insert | update
    payload = Column(Text)      # JSON
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
