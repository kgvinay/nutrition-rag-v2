from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import GenerationResult

logger = logging.getLogger(__name__)


class StreamingGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm_streaming = None
        self._llm_sync = None

    def _get_streaming_llm(self):
        if self._llm_streaming is None:
            from langchain_openai import ChatOpenAI

            self._llm_streaming = ChatOpenAI(
                model=self.settings.generation.llm_model,
                temperature=self.settings.generation.temperature,
                max_tokens=self.settings.generation.max_tokens,
                streaming=True,
            )
        return self._llm_streaming

    def _get_sync_llm(self):
        if self._llm_sync is None:
            from langchain_openai import ChatOpenAI

            self._llm_sync = ChatOpenAI(
                model=self.settings.generation.llm_model,
                temperature=self.settings.generation.temperature,
                max_tokens=self.settings.generation.max_tokens,
                streaming=False,
            )
        return self._llm_sync

    @staticmethod
    def _to_lc_messages(messages: list[dict[str, str]]):
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for msg in messages:
            if msg["role"] == "system":
                lc_messages.append(SystemMessage(content=msg["content"]))
            else:
                lc_messages.append(HumanMessage(content=msg["content"]))
        return lc_messages

    async def generate_streaming(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        start = time.time()
        first_token = True
        lc_messages = self._to_lc_messages(messages)
        llm = self._get_streaming_llm()

        try:
            async for chunk in llm.astream(lc_messages):
                if first_token:
                    latency = (time.time() - start) * 1000
                    logger.info("Time to first token: %.0fms", latency)
                    first_token = False
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error("Streaming failed, falling back to sync: %s", e)
            async for token in self._generate_sync_fallback(lc_messages):
                yield token

    async def _generate_sync_fallback(self, messages) -> AsyncIterator[str]:
        response = await self._get_sync_llm().ainvoke(messages)
        if response.content:
            yield response.content

    async def generate(self, messages: list[dict[str, str]]) -> GenerationResult:
        start = time.time()
        lc_messages = self._to_lc_messages(messages)
        llm = self._get_sync_llm()

        response = await llm.ainvoke(lc_messages)
        latency_ms = (time.time() - start) * 1000
        content = response.content or ""

        return GenerationResult(
            response=content,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            generation_latency_ms=latency_ms,
        )
