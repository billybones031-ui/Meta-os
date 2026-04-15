"""Pydantic schemas for the entire Meta-OS pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Workspace(str, Enum):
    PERSONAL = "personal"
    BUSINESS = "business"


class TaskType(str, Enum):
    SIMPLE = "simple"          # Fast, Ollama handles
    COMPLEX = "complex"        # Deep reasoning, Claude handles
    PRIVATE = "private"        # Never leaves device, Ollama only
    DESTRUCTIVE = "destructive"  # Requires Telegram confirmation
    MULTIMODAL = "multimodal"  # Image/audio, Gemini handles
    CODING = "coding"          # Routes to coding team
    SUPPORT = "support"        # Routes to support team


class AgentName(str, Enum):
    # Orchestrator
    OPENCLAW = "openclaw"
    # Core providers
    CLAUDE = "claude"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    # Coding team
    ARCHITECT = "architect"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    SECURITY = "security"
    AI_ML = "ai_ml"
    MOBILE = "mobile"
    DATA = "data"
    # Support team
    PROJECT_MANAGER = "project_manager"
    RESEARCH = "research"
    WRITER = "writer"
    COST_MONITOR = "cost_monitor"
    CALENDAR = "calendar"
    MEMORY_CURATOR = "memory_curator"


class UserMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: Optional[str] = None
    voice_path: Optional[str] = None
    image_path: Optional[str] = None
    workspace: Workspace = Workspace.PERSONAL
    user_id: int = 0
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GeminiParsed(BaseModel):
    """Structured output of Gemini's intent-parsing step."""
    intent: str
    task_type: TaskType
    requires_tools: list[str] = Field(default_factory=list)
    is_destructive: bool = False
    suggested_agent: Optional[AgentName] = None
    confidence: float = 1.0
    raw_text: str = ""


class AgentTask(BaseModel):
    """Task OpenClaw delegates to a worker agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    assigned_agent: AgentName
    instruction: str
    context: list[dict[str, Any]] = Field(default_factory=list)
    tools_available: list[str] = Field(default_factory=list)
    workspace: Workspace = Workspace.PERSONAL
    timeout_seconds: int = 120


class AgentResult(BaseModel):
    """Result any worker agent returns to OpenClaw."""
    task_id: str
    agent: AgentName
    success: bool
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
    duration_ms: int = 0
    error: Optional[str] = None


class OrchestratorDecision(BaseModel):
    """OpenClaw routing decision."""
    task_type: TaskType
    primary_agent: AgentName
    consultant_agents: list[AgentName] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    reasoning: str = ""


class PendingConfirmation(BaseModel):
    """Stored while waiting for user to confirm a destructive action."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    original_message: str
    decision: OrchestratorDecision
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FinalResponse(BaseModel):
    """Final response sent back via Telegram."""
    text: str
    voice_bytes: Optional[bytes] = None
    session_id: str = ""
    agents_used: list[AgentName] = Field(default_factory=list)
    workspace: Workspace = Workspace.PERSONAL
    token_usage: dict[str, int] = Field(default_factory=dict)


class SessionTurn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    workspace: Workspace
    user_message: str
    bot_response: str
    agents_used: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CostEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    est_cost_usd: float = 0.0
    workspace: Workspace = Workspace.PERSONAL
    timestamp: datetime = Field(default_factory=datetime.utcnow)
