from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import (
    Chunk,
    ConversationState,
    ConversationTurn,
    GenerationResult,
    RetrievedContext,
    UserProfile,
)
from nutrition_rag.pipelines.generation.citation import CitationInjector
from nutrition_rag.pipelines.generation.disclaimer import DisclaimerPrepender
from nutrition_rag.pipelines.generation.guardrails import Guardrails
from nutrition_rag.pipelines.generation.medical_refusal import MedicalAdviceDetector
from nutrition_rag.pipelines.generation.prompt_builder import PromptBuilder
from nutrition_rag.pipelines.generation.streamer import StreamingGenerator
from nutrition_rag.pipelines.retrieval.context_filter import ContextFilter
from nutrition_rag.pipelines.retrieval.hybrid_search import HybridSearcher
from nutrition_rag.pipelines.retrieval.personalization import PersonalizationFilter
from nutrition_rag.pipelines.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class PipelineState(dict):
    query: str
    conversation_id: str
    user_id: str | None
    user_profile: UserProfile | None
    conversation_history: list[ConversationTurn]
    retrieved_chunks: list[Chunk]
    reranked_chunks: list[Chunk]
    filtered_chunks: list[Chunk]
    generation_result: GenerationResult | None
    response: str
    error: str | None
    metadata: dict[str, Any]


class ChatOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.searcher = HybridSearcher(settings, _get_registry(settings))
        self.reranker = Reranker(settings)
        self.context_filter = ContextFilter(settings)
        self.personalization = PersonalizationFilter()
        self.prompt_builder = PromptBuilder(settings)
        self.medical_detector = MedicalAdviceDetector()
        self.disclaimer = DisclaimerPrepender(settings)
        self.citation = CitationInjector()
        self.guardrails = Guardrails(settings)
        self.generator = StreamingGenerator(settings)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(PipelineState)
        graph.add_node("check_medical", self._check_medical)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("rerank", self._rerank)
        graph.add_node("filter_context", self._filter_context)
        graph.add_node("generate", self._generate)
        graph.add_node("apply_guardrails", self._apply_guardrails)
        graph.set_entry_point("check_medical")
        graph.add_conditional_edges("check_medical", self._medical_route, {"retrieve": "retrieve", "refuse": END})
        graph.add_edge("retrieve", "rerank")
        graph.add_edge("rerank", "filter_context")
        graph.add_edge("filter_context", "generate")
        graph.add_edge("generate", "apply_guardrails")
        graph.add_edge("apply_guardrails", END)
        return graph.compile()

    async def _check_medical(self, state: PipelineState) -> PipelineState:
        if self.medical_detector.detect(state.get("query", "")):
            state["response"] = self.medical_detector.get_refusal_response()
            state["generation_result"] = GenerationResult(
                response=state["response"],
                has_medical_refusal=True,
            )
        return state

    def _medical_route(self, state: PipelineState) -> str:
        if state.get("generation_result") and state["generation_result"].has_medical_refusal:
            return "refuse"
        return "retrieve"

    async def _retrieve(self, state: PipelineState) -> PipelineState:
        start = time.time()
        query = state.get("query", "")
        user_profile = state.get("user_profile")
        must_filters = self.personalization.build_must_filters(user_profile)
        try:
            chunks = await self.searcher.search(query, must_filters=must_filters if must_filters else None)
            state["retrieved_chunks"] = chunks
        except Exception as e:
            logger.warning("Retrieval failed, continuing with empty context: %s", e)
            state["retrieved_chunks"] = []
            state["error"] = f"Retrieval unavailable: {type(e).__name__}"
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["retrieval_latency_ms"] = (time.time() - start) * 1000
        return state

    async def _rerank(self, state: PipelineState) -> PipelineState:
        chunks = state.get("retrieved_chunks", [])
        query = state.get("query", "")
        try:
            reranked = await self.reranker.rerank(query, chunks)
            state["reranked_chunks"] = reranked
        except Exception as e:
            logger.warning("Reranking failed, using original order: %s", e)
            state["reranked_chunks"] = chunks
        return state

    async def _filter_context(self, state: PipelineState) -> PipelineState:
        chunks = state.get("reranked_chunks", [])
        filtered = self.context_filter.filter_chunks(chunks)
        state["filtered_chunks"] = filtered
        return state

    async def _generate(self, state: PipelineState) -> PipelineState:
        start = time.time()
        query = state.get("query", "")
        chunks = state.get("filtered_chunks", [])
        history = state.get("conversation_history", [])
        messages = self.prompt_builder.build_prompt(query, chunks, history)
        try:
            result = await self.generator.generate(messages)
            response = result.response
            response, cited_ids = self.citation.inject(response, chunks)
            response = self.disclaimer.prepend(response)
            result.response = response
            result.cited_chunk_ids = cited_ids
            result.generation_latency_ms = (time.time() - start) * 1000
            state["generation_result"] = result
            state["response"] = response
        except Exception as e:
            logger.error("Generation failed: %s", e)
            fallback = "I'm unable to generate a response right now due to a service issue. Please try again later."
            state["response"] = self.disclaimer.prepend(fallback)
            state["generation_result"] = GenerationResult(
                response=state["response"],
                generation_latency_ms=(time.time() - start) * 1000,
            )
            state["error"] = f"Generation failed: {type(e).__name__}"
        return state

    async def _apply_guardrails(self, state: PipelineState) -> PipelineState:
        response = state.get("response", "")
        context_texts = [c.content for c in state.get("filtered_chunks", [])]
        safe_response, checks = self.guardrails.apply(response, context_texts)
        state["response"] = safe_response
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["guardrails"] = checks
        if state.get("generation_result"):
            state["generation_result"].response = safe_response
        return state

    async def run(
        self,
        query: str,
        conversation_id: str | None = None,
        user_id: str | None = None,
        user_profile: UserProfile | None = None,
        conversation_history: list[ConversationTurn] | None = None,
    ) -> PipelineState:
        conversation_id = conversation_id or str(uuid.uuid4())
        initial_state = PipelineState(
            query=query,
            conversation_id=conversation_id,
            user_id=user_id,
            user_profile=user_profile,
            conversation_history=conversation_history or [],
            retrieved_chunks=[],
            reranked_chunks=[],
            filtered_chunks=[],
            generation_result=None,
            response="",
            error=None,
            metadata={},
        )
        result = await self.graph.ainvoke(initial_state)
        return result


def _get_registry(settings: Settings):
    from nutrition_rag.pipelines.embedding.registry import EmbeddingRegistry

    return EmbeddingRegistry(settings)
