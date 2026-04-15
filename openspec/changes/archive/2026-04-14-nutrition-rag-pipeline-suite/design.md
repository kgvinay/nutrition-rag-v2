## Context

This project builds a complete Nutrition RAG (Retrieval-Augmented Generation) system from scratch. No existing codebase exists — only six comprehensive specification documents defining the required behavior for ingestion, embedding, retrieval, generation, chat orchestration, and monitoring pipelines. The system will enable semantic search and retrieval over public food composition databases (USDA FoodData Central, FDA, Nutritionix, Open Food Facts) and provide users with accurate, cited, and safe nutrition information through a stateful multi-turn chat interface.

## Goals / Non-Goals

**Goals:**
- Build a production-grade Nutrition RAG pipeline with all six subsystems fully implemented
- Support multiple nutrition data sources with automated ingestion and provenance tracking
- Enable hybrid retrieval (vector + keyword + metadata) with multi-stage reranking
- Provide safe, cited, streaming responses with medical disclaimers and guardrails
- Support stateful multi-turn conversations with persistent memory
- Implement comprehensive observability, metrics, and alerting

**Non-Goals:**
- Mobile or desktop client applications (API-first design)
- Real-time collaborative editing
- Multi-tenant isolation beyond per-user rate limiting
- Custom fine-tuned embedding or language models
- Payment or billing integration

## Decisions

### D1: Python + FastAPI for API Layer
FastAPI provides async support, automatic OpenAPI docs, and native Pydantic validation. Alternatives: Flask (no native async), Django (too heavy for microservice). Choice: FastAPI for its async performance and LangChain ecosystem compatibility.

### D2: LangChain/LangGraph for Orchestration
LangGraph provides stateful graph-based orchestration with checkpointing, which maps directly to the chat pipeline's state machine requirements (REQ-CHAT-002). LangChain provides the abstraction layer for LLMs, embeddings, and vector stores. Alternative: custom state machine (more control but more maintenance). Choice: LangGraph for built-in checkpointing and LangChain ecosystem.

### D3: Qdrant for Vector Store
Qdrant offers hybrid search (dense + sparse vectors), filtering, and is open-source with a managed cloud option. Supports the hybrid retrieval requirement (REQ-RET-001). Alternatives: Pinecone (managed only, vendor lock-in), Weaviate (heavier), Chroma (limited production features). Choice: Qdrant for hybrid search support and self-hosting option.

### D4: Redis for Caching and Rate Limiting
Redis serves dual purpose: embedding cache (REQ-EMB-004, 30-day TTL) and rate limiting (REQ-CHAT-003). Reduces infrastructure complexity. Alternative: separate systems for cache and rate limiting. Choice: Redis for simplicity.

### D5: Modular Pipeline Architecture
Each pipeline (ingestion, embedding, retrieval, generation, chat, monitoring) is a separate Python module with well-defined interfaces. Pipelines communicate through shared data models and can be tested independently. This supports the hot-swapping requirement (REQ-EMB-001) and error isolation.

### D6: Configuration via Environment Variables + YAML
Settings managed through pydantic-settings with `.env` files for secrets and YAML for pipeline configuration (model names, batch sizes, thresholds). Feature flags for model hot-swapping via environment variables. Alternative: dedicated config service. Choice: env + YAML for simplicity in initial deployment.

### D7: RAGAS + DeepEval for Evaluation
RAGAS provides Faithfulness and Answer Relevancy metrics (REQ-MON-001). DeepEval adds Toxicity scoring. Both integrate with LangSmith for tracing. Alternative: custom evaluation scripts. Choice: RAGAS + DeepEval for established metrics and community support.

### D8: OpenTelemetry + LangSmith for Observability
OpenTelemetry for infrastructure-level tracing and metrics. LangSmith for LLM-specific tracing (prompt chains, retrieval quality). Both satisfy REQ-MON-003. Alternative: only LangSmith (misses infra visibility). Choice: both for comprehensive coverage.

## Risks / Trade-offs

- **[API rate limits from data sources]** → Implement configurable backoff and respect rate limit headers; schedule heavy ingestion during off-peak hours
- **[Embedding model swap requires re-indexing]** → Support dual-index strategy: old vectors remain searchable while new index is built; rotate after validation
- **[LLM hallucination on nutrition facts]** → Multi-layer defense: confidence filtering (REQ-RET-003), guardrails (REQ-GEN-004), and mandatory disclaimers (REQ-GEN-002)
- **[Cold start latency on first embedding model load]** → Warm-up health check endpoint; pre-load models on container startup
- **[Redis single point of failure]** → Use Redis Sentinel or managed Redis with automatic failover in production
- **[Qdrant scaling under load]** → Start with single-node; horizontal scaling via sharding when needed
