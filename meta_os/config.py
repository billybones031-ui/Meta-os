"""Configuration — XDG-compliant, env-var driven, zero API keys."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# XDG dirs — works on Debian (Pixel), Kali (Chromebook), Termux
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "meta-os"
DATA_DIR = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "meta-os"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(".env")


class Config(BaseModel):
    # CLI paths (Pro subscriptions, no API keys)
    claude_cli: str = "claude"
    gemini_cli: str = "gemini"

    # Ollama (local, Chromebook)
    ollama_host: str = "http://localhost:11434"
    ollama_default_model: str = "llama3"
    ollama_embed_model: str = "nomic-embed-text"

    # Telegram
    telegram_token: str = ""
    allowed_user_ids: list[int] = Field(default_factory=list)

    # Database
    db_path: Path = DATA_DIR / "meta-os.db"
    offline_queue_path: Path = DATA_DIR / "offline-queue.db"
    db_passphrase: str = ""
    db_master_host: str = "http://localhost:8001"
    is_db_master: bool = False
    db_sync_port: int = 8001

    # Cloudflare
    cloudflare_tunnel_token: str = ""

    # GitHub
    github_pat: str = ""

    # Workspaces
    default_workspace: str = "personal"
    business_workspace: str = "business"

    # Ports
    dashboard_port: int = 7860
    mcp_port_lite: int = 8081
    mcp_port_full: int = 8080

    # ChromaDB
    chroma_path: Path = DATA_DIR / "chromadb"

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def parse_user_ids(cls, v: object) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        return v or []


def load_config() -> Config:
    return Config(
        claude_cli=os.getenv("CLAUDE_CLI_PATH", "claude"),
        gemini_cli=os.getenv("GEMINI_CLI_PATH", "gemini"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_default_model=os.getenv("OLLAMA_DEFAULT_MODEL", "llama3"),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        allowed_user_ids=os.getenv("ALLOWED_USER_IDS", ""),
        db_passphrase=os.getenv("DB_PASSPHRASE", ""),
        db_master_host=os.getenv("DB_MASTER_HOST", "http://localhost:8001"),
        is_db_master=os.getenv("IS_DB_MASTER", "false").lower() == "true",
        db_sync_port=int(os.getenv("DB_SYNC_PORT", "8001")),
        cloudflare_tunnel_token=os.getenv("CLOUDFLARE_TUNNEL_TOKEN", ""),
        github_pat=os.getenv("GITHUB_PAT", ""),
        default_workspace=os.getenv("DEFAULT_WORKSPACE", "personal"),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "7860")),
        mcp_port_lite=int(os.getenv("MCP_PORT_LITE", "8081")),
        mcp_port_full=int(os.getenv("MCP_PORT_FULL", "8080")),
    )


config = load_config()
