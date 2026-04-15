from __future__ import annotations

import time
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from nutrition_rag import settings
from nutrition_rag.core.models import (
    ConversationTurn,
    GenerationResult,
    PipelineTrace,
    UserQuery,
    UserProfile,
)
from nutrition_rag.pipelines.chat.memory_injector import MemoryInjector
from nutrition_rag.pipelines.chat.long_term_memory import LongTermMemory
from nutrition_rag.pipelines.chat.orchestrator import ChatOrchestrator
from nutrition_rag.pipelines.chat.rate_limiter import RateLimiter
from nutrition_rag.pipelines.chat.short_term_memory import ShortTermMemory
from nutrition_rag.pipelines.generation.streamer import StreamingGenerator
from nutrition_rag.pipelines.generation.prompt_builder import PromptBuilder
from nutrition_rag.pipelines.ingestion.connectors.upload import UserUploadConnector
from nutrition_rag.pipelines.ingestion.orchestrator import IngestionPipeline
from nutrition_rag.pipelines.monitoring.trace_logger import TraceLogger
from nutrition_rag.pipelines.monitoring.business_metrics import BusinessMetrics

app = FastAPI(title=settings.app_name, version="0.1.0")

_short_term = ShortTermMemory(settings)
_long_term = LongTermMemory(settings)
_memory_injector = MemoryInjector(_short_term, _long_term)
_orchestrator = ChatOrchestrator(settings)
_rate_limiter = RateLimiter(settings)
_trace_logger = TraceLogger(settings)
_business_metrics = BusinessMetrics()
_upload_connector = UserUploadConnector()
_ingestion_pipeline = IngestionPipeline(settings)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/chat")
async def chat(query: UserQuery):
    allowed, reason = await _rate_limiter.check_all(query.user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    await _business_metrics.record_query()
    trace_id = _trace_logger.create_trace_id()
    start = time.time()

    turns, profile = await _memory_injector.inject_context(
        query.conversation_id or str(uuid.uuid4()),
        query.user_id,
    )

    result = await _orchestrator.run(
        query=query.query,
        conversation_id=query.conversation_id,
        user_id=query.user_id,
        user_profile=profile or query.user_profile,
        conversation_history=turns,
    )

    total_latency = (time.time() - start) * 1000
    response_text = result.get("response", "")
    generation_result = result.get("generation_result")

    if query.conversation_id:
        await _short_term.add_turn(query.conversation_id, ConversationTurn(role="user", content=query.query))
        await _short_term.add_turn(query.conversation_id, ConversationTurn(role="assistant", content=response_text))

    trace = PipelineTrace(
        trace_id=trace_id,
        user_id=query.user_id,
        conversation_id=query.conversation_id,
        query=query.query,
        retrieved_chunks=result.get("filtered_chunks", []),
        generation_result=generation_result,
        total_latency_ms=total_latency,
        retrieval_latency_ms=result.get("metadata", {}).get("retrieval_latency_ms", 0),
        generation_latency_ms=generation_result.generation_latency_ms if generation_result else 0,
        metadata=result.get("metadata", {}),
    )
    await _trace_logger.log_trace(trace)

    return {
        "response": response_text,
        "trace_id": trace_id,
        "conversation_id": query.conversation_id,
        "latency_ms": total_latency,
    }


@app.post("/chat/stream")
async def chat_stream(query: UserQuery):
    allowed, reason = await _rate_limiter.check_all(query.user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    async def generate() -> AsyncIterator[str]:
        prompt_builder = PromptBuilder(settings)
        streamer = StreamingGenerator(settings)
        turns, profile = await _memory_injector.inject_context(
            query.conversation_id or str(uuid.uuid4()),
            query.user_id,
        )
        from nutrition_rag.pipelines.retrieval.hybrid_search import HybridSearcher
        from nutrition_rag.pipelines.retrieval.reranker import Reranker
        from nutrition_rag.pipelines.retrieval.context_filter import ContextFilter
        from nutrition_rag.pipelines.embedding.registry import EmbeddingRegistry

        registry = EmbeddingRegistry(settings)
        searcher = HybridSearcher(settings, registry)
        reranker = Reranker(settings)
        context_filter = ContextFilter(settings)

        chunks = await searcher.search(query.query)
        reranked = await reranker.rerank(query.query, chunks, top_n=10)
        filtered = context_filter.filter_chunks(reranked)
        messages = prompt_builder.build_prompt(query.query, filtered, turns)

        async for token in streamer.generate_streaming(messages):
            yield token

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        documents = _upload_connector.process_upload(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"filename": file.filename, "documents_extracted": len(documents)}


@app.post("/ingest/trigger")
async def trigger_ingestion():
    return {"status": "triggered", "message": "Ingestion pipeline started"}
