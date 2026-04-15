from __future__ import annotations

import logging

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import ConversationTurn
from nutrition_rag.pipelines.embedding.registry import EmbeddingRegistry

logger = logging.getLogger(__name__)


class MultiTurnContext:
    def __init__(self, settings: Settings, registry: EmbeddingRegistry):
        self.settings = settings
        self.registry = registry

    async def build_contextual_query(
        self,
        current_query: str,
        conversation_history: list[ConversationTurn],
    ) -> str:
        if not conversation_history:
            return current_query

        recent = conversation_history[-5:]
        history_text = " ".join(turn.content for turn in recent)
        combined = f"{history_text} {current_query}"
        logger.debug("Multi-turn context: combined query length=%d", len(combined))
        return combined

    async def get_history_embedding(
        self,
        conversation_history: list[ConversationTurn],
    ) -> list[float] | None:
        if not conversation_history:
            return None
        recent = conversation_history[-5:]
        combined = " ".join(turn.content for turn in recent)
        provider = self.registry.get_active_provider()
        return await provider.embed_query(combined)

    def extract_metadata_constraints(
        self,
        conversation_history: list[ConversationTurn],
    ) -> dict[str, list[str]]:
        constraints: dict[str, list[str]] = {"topics": [], "restrictions": []}
        topic_keywords = {
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "keto": "keto",
            "protein": "high_protein",
            "low carb": "low_carb",
            "low fat": "low_fat",
            "gluten free": "gluten_free",
            "dairy free": "dairy_free",
        }
        for turn in conversation_history:
            text_lower = turn.content.lower()
            for keyword, tag in topic_keywords.items():
                if keyword in text_lower and tag not in constraints["topics"]:
                    constraints["topics"].append(tag)
        return constraints
