from __future__ import annotations

import logging
from typing import Any

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)

NUTRITION_RERANK_PROMPT = (
    "You are a nutrition domain expert. Rank the following food/nutrition passages "
    "by how well they answer the user's query. Prioritize accuracy, relevance to "
    "nutritional content, and presence of specific quantitative data (calories, macros, vitamins). "
    "Penalize vague or generic health claims."
)


class Reranker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.reranker_type = settings.retrieval.reranker_type
        self._cross_encoder = None

    def _get_cross_encoder(self):
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder

            self._cross_encoder = CrossEncoder(self.settings.retrieval.reranker_model)
        return self._cross_encoder

    async def rerank_cross_encoder(self, query: str, chunks: list[Chunk], top_n: int | None = None) -> list[Chunk]:
        if not chunks:
            return chunks
        top_n = top_n or min(10, len(chunks))
        encoder = self._get_cross_encoder()
        pairs = [(query, chunk.content) for chunk in chunks]
        scores = encoder.predict(pairs)
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        result = [chunk for chunk, _ in scored[:top_n]]
        logger.info("Cross-encoder reranking: %d → %d chunks", len(chunks), len(result))
        return result

    async def rerank_llm_as_judge(
        self, query: str, chunks: list[Chunk], top_n: int | None = None, llm=None
    ) -> list[Chunk]:
        if not chunks:
            return chunks
        top_n = top_n or min(10, len(chunks))
        if llm is None:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=self.settings.generation.llm_model, temperature=0)

        scored_chunks: list[tuple[Chunk, float]] = []
        for chunk in chunks:
            prompt = (
                f"{NUTRITION_RERANK_PROMPT}\n\n"
                f"Query: {query}\n\n"
                f"Passage: {chunk.content[:500]}\n\n"
                f"Score this passage from 0.0 to 1.0 for relevance. Reply with only the number."
            )
            try:
                response = await llm.ainvoke(prompt)
                score = float(response.content.strip())
            except (ValueError, Exception) as e:
                logger.debug("LLM reranking score failed: %s", e)
                score = 0.5
            scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        result = [chunk for chunk, _ in scored_chunks[:top_n]]
        logger.info("LLM-as-judge reranking: %d → %d chunks", len(chunks), len(result))
        return result

    async def rerank(self, query: str, chunks: list[Chunk], top_n: int | None = None, llm=None) -> list[Chunk]:
        if self.reranker_type == "cross-encoder":
            return await self.rerank_cross_encoder(query, chunks, top_n)
        elif self.reranker_type == "llm-as-judge":
            return await self.rerank_llm_as_judge(query, chunks, top_n, llm)
        else:
            raise ValueError(f"Unknown reranker type: {self.reranker_type}")
