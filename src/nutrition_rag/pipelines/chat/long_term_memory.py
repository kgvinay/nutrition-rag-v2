from __future__ import annotations

import logging
from typing import Any

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import UserProfile

logger = logging.getLogger(__name__)


class LongTermMemory:
    def __init__(self, settings: Settings, redis_client=None, qdrant_client=None):
        self.settings = settings
        self._redis = redis_client
        self._qdrant = qdrant_client
        self._local_store: dict[str, dict[str, Any]] = {}

    def _key(self, user_id: str) -> str:
        return f"chat:memory:long:{user_id}"

    async def store_user_profile(self, user_id: str, profile: UserProfile) -> None:
        data = profile.model_dump()
        if self._redis:
            import json

            await self._redis.set(self._key(user_id), json.dumps(data))
        else:
            self._local_store[user_id] = data
        logger.info("Long-term memory: stored profile for user %s", user_id)

    async def get_user_profile(self, user_id: str) -> UserProfile | None:
        if self._redis:
            import json

            raw = await self._redis.get(self._key(user_id))
            if raw:
                return UserProfile(**json.loads(raw))
        else:
            data = self._local_store.get(user_id)
            if data:
                return UserProfile(**data)
        return None

    async def store_fact(self, user_id: str, key: str, value: str) -> None:
        fact_key = f"{self._key(user_id)}:facts:{key}"
        if self._redis:
            await self._redis.set(fact_key, value)
        else:
            if user_id not in self._local_store:
                self._local_store[user_id] = {}
            if "_facts" not in self._local_store[user_id]:
                self._local_store[user_id]["_facts"] = {}
            self._local_store[user_id]["_facts"][key] = value
        logger.debug("Long-term memory: stored fact '%s' for user %s", key, user_id)

    async def get_facts(self, user_id: str) -> dict[str, str]:
        if self._redis:
            pattern = f"{self._key(user_id)}:facts:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            facts = {}
            for key in keys:
                val = await self._redis.get(key)
                if val:
                    fact_name = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
                    facts[fact_name] = val if isinstance(val, str) else val.decode()
            return facts
        else:
            return self._local_store.get(user_id, {}).get("_facts", {})
