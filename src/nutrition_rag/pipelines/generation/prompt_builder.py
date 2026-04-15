from __future__ import annotations

import logging

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk, ConversationTurn

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a certified nutrition expert assistant. Your role is to provide accurate, "
    "evidence-based nutrition information based on the retrieved context.\n\n"
    "Rules:\n"
    "1. Only answer based on the provided context. If the context doesn't contain relevant information, say so.\n"
    "2. Always cite your sources using [Source: chunk_id] format.\n"
    "3. NEVER provide medical diagnosis or treatment advice. If asked, refuse and suggest consulting a licensed professional.\n"
    "4. Include the mandatory disclaimer at the start of every response.\n"
    "5. Be precise with numbers (calories, macros, vitamins, minerals).\n"
    "6. If nutritional values conflict between sources, note the discrepancy.\n"
)


class PromptBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_context_section(self, chunks: list[Chunk]) -> str:
        if not chunks:
            return "No specific retrieved context is available. Answer based on your general nutrition knowledge, but clearly state that the response is not sourced from the database and may be less precise."
        sections = []
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source: {chunk.id}]"
            confidence = f"(confidence: {chunk.confidence_score:.2f})"
            sections.append(f"{source_info} {confidence}\n{chunk.content}")
        return "--- Retrieved Context ---\n" + "\n\n".join(sections) + "\n--- End Context ---"

    def build_user_section(self, query: str, conversation_history: list[ConversationTurn] | None = None) -> str:
        parts = []
        if conversation_history:
            history_lines = []
            for turn in conversation_history[-10:]:
                role = turn.role.capitalize()
                history_lines.append(f"{role}: {turn.content}")
            parts.append("--- Conversation History ---\n" + "\n".join(history_lines) + "\n--- End History ---")
        parts.append(f"User Query: {query}")
        return "\n\n".join(parts)

    def build_prompt(
        self, query: str, chunks: list[Chunk], conversation_history: list[ConversationTurn] | None = None
    ) -> list[dict[str, str]]:
        messages = [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "system", "content": self.build_context_section(chunks)},
            {"role": "user", "content": self.build_user_section(query, conversation_history)},
        ]
        return messages
