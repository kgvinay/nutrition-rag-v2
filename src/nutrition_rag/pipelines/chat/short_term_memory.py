from __future__ import annotations

import logging
from typing import Any

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import ConversationTurn

logger = logging.getLogger(__name__)


class ShortTermMemory:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self.max_turns = settings.chat.short_term_memory_turns
        self._redis = redis_client
        self._local_store: dict[str, list[dict[str, Any]]] = {}

    def _key(self, conversation_id: str) -> str:
        return f"chat:memory:short:{conversation_id}"

    async def get_turns(self, conversation_id: str) -> list[ConversationTurn]:
        if self._redis:
            import json

            raw = await self._redis.lrange(self._key(conversation_id), -self.max_turns, -1)
            turns = [ConversationTurn(**json.loads(t)) for t in raw]
        else:
            raw = self._local_store.get(conversation_id, [])
            turns = [ConversationTurn(**t) for t in raw[-self.max_turns :]]
        logger.debug("Short-term memory: %d turns for conversation %s", len(turns), conversation_id)
        return turns

    async def add_turn(self, conversation_id: str, turn: ConversationTurn) -> None:
        if self._redis:
            import json

            await self._redis.rpush(self._key(conversation_id), json.dumps(turn.model_dump()))
            await self._redis.ltrim(self._key(conversation_id), -self.max_turns, -1)
        else:
            if conversation_id not in self._local_store:
                self._local_store[conversation_id] = []
            self._local_store[conversation_id].append(turn.model_dump())
            self._local_store[conversation_id] = self._local_store[conversation_id][-self.max_turns :]

    async def clear(self, conversation_id: str) -> None:
        if self._redis:
            await self._redis.delete(self._key(conversation_id))
        else:
            self._local_store.pop(conversation_id, None)
