from __future__ import annotations

import logging

from nutrition_rag.core.models import (
    ConversationTurn,
    RetrievedContext,
    UserProfile,
)
from nutrition_rag.pipelines.chat.long_term_memory import LongTermMemory
from nutrition_rag.pipelines.chat.short_term_memory import ShortTermMemory

logger = logging.getLogger(__name__)


class MemoryInjector:
    def __init__(self, short_term: ShortTermMemory, long_term: LongTermMemory):
        self.short_term = short_term
        self.long_term = long_term

    async def inject_context(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> tuple[list[ConversationTurn], UserProfile | None]:
        turns = await self.short_term.get_turns(conversation_id)
        profile = None
        if user_id:
            profile = await self.long_term.get_user_profile(user_id)
            if profile:
                logger.debug(
                    "Injected long-term memory for user %s: %d preferences, %d allergies",
                    user_id,
                    len(profile.dietary_preferences),
                    len(profile.allergies),
                )
        logger.debug("Injected short-term memory: %d turns for conversation %s", len(turns), conversation_id)
        return turns, profile
