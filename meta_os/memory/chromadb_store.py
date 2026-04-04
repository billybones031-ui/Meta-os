"""ChromaDB vector memory store — one collection per agent, shared ISL collections."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

from meta_os.config import config

# Shared collection names
COLL_ISL_CODEBASE = "isl_codebase_memory"
COLL_ISL_DECISIONS = "isl_decisions_memory"
COLL_ISL_COSTS = "isl_costs_memory"


class AgentMemoryStore:
    """Persistent vector memory for all agents via ChromaDB + Ollama embeddings."""

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(config.chroma_path))
        self._ef = OllamaEmbeddingFunction(
            url=f"{config.ollama_host}/api/embeddings",
            model_name=config.ollama_embed_model,
        )
        self._collections: dict[str, chromadb.Collection] = {}

    def _get_coll(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._ef,
            )
        return self._collections[name]

    def agent_coll(self, agent_name: str) -> chromadb.Collection:
        return self._get_coll(f"agent_{agent_name}_memory")

    def shared_coll(self, name: str) -> chromadb.Collection:
        return self._get_coll(name)

    async def add(
        self,
        agent_name: str,
        content: str,
        memory_type: str,  # episodic | semantic | procedural | error
        metadata: Optional[dict] = None,
        shared_collection: Optional[str] = None,
    ) -> str:
        doc_id = str(uuid4())
        meta = {
            "type": memory_type,
            "agent": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }
        coll = self.shared_coll(shared_collection) if shared_collection else self.agent_coll(agent_name)
        coll.add(documents=[content], ids=[doc_id], metadatas=[meta])
        return doc_id

    async def search(
        self,
        agent_name: str,
        query: str,
        n: int = 5,
        memory_type: Optional[str] = None,
        shared_collection: Optional[str] = None,
    ) -> list[dict]:
        coll = self.shared_coll(shared_collection) if shared_collection else self.agent_coll(agent_name)
        count = coll.count()
        if count == 0:
            return []
        where = {"type": memory_type} if memory_type else None
        try:
            results = coll.query(
                query_texts=[query],
                n_results=min(n, count),
                where=where,
            )
            return [
                {"content": doc, "metadata": meta}
                for doc, meta in zip(results["documents"][0], results["metadatas"][0])
            ]
        except Exception:
            return []

    async def add_error(
        self, agent_name: str, task_description: str, error: str, fix: str
    ) -> None:
        content = f"ERROR: {error[:200]} | TASK: {task_description[:200]} | FIX: {fix[:200]}"
        await self.add(agent_name, content, "error")

    async def add_semantic(
        self, agent_name: str, fact: str, source: str = ""
    ) -> None:
        meta = {"source": source} if source else {}
        await self.add(agent_name, fact, "semantic", meta)


# Singleton
memory_store = AgentMemoryStore()
