from __future__ import annotations

import logging
import time

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self._redis = redis_client
        self._local_counters: dict[str, list[float]] = {}

    def _user_key(self, user_id: str) -> str:
        return f"rate_limit:user:{user_id}"

    def _global_key(self) -> str:
        return "rate_limit:global"

    async def check_user_limit(self, user_id: str) -> tuple[bool, int]:
        limit = self.settings.chat.per_user_rate_limit
        window = self.settings.chat.per_user_rate_window_seconds
        return await self._check_limit(self._user_key(user_id), limit, window)

    async def check_global_limit(self) -> tuple[bool, int]:
        limit = self.settings.chat.global_rate_limit
        window = self.settings.chat.global_rate_window_seconds
        return await self._check_limit(self._global_key(), limit, window)

    async def _check_limit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        if self._redis:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            results = await pipe.execute()
            count = results[1]
            allowed = count < limit
            if not allowed:
                logger.warning("Rate limit exceeded for key %s: %d/%d", key, count, limit)
            return allowed, count
        else:
            if key not in self._local_counters:
                self._local_counters[key] = []
            self._local_counters[key] = [t for t in self._local_counters[key] if t > now - window]
            count = len(self._local_counters[key])
            self._local_counters[key].append(now)
            allowed = count < limit
            if not allowed:
                logger.warning("Rate limit exceeded for key %s: %d/%d", key, count, limit)
            return allowed, count

    async def check_all(self, user_id: str | None = None) -> tuple[bool, str]:
        global_ok, global_count = await self.check_global_limit()
        if not global_ok:
            return False, "Global rate limit exceeded. Please try again later."
        if user_id:
            user_ok, user_count = await self.check_user_limit(user_id)
            if not user_ok:
                return False, "Per-user rate limit exceeded. Please try again later."
        return True, ""
