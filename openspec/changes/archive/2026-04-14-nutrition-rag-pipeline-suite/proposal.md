## Why

There is no working implementation of the Nutrition RAG system. Six comprehensive specifications exist (ingestion, embedding, retrieval, generation, chat, monitoring) but no code has been written. The full pipeline must be built from scratch to enable semantic search and retrieval over public food composition databases (USDA FoodData Central, FDA, Nutritionix, Open Food Facts), providing users with accurate, cited, and safe nutrition information through a stateful multi-turn chat interface.

## What Changes

- Implement the **Ingestion Pipeline**: data extraction, cleaning, metadata enrichment, semantic chunking, and vector store upsert for all supported nutrition data sources (USDA, FDA, Nutritionix, Open Food Facts, user uploads, expert knowledge base)
- Implement the **Embedding Pipeline**: multi-model support (OpenAI, Cohere, Voyage, sentence-transformers), hot-swapping via feature flags, batch processing with GPU/CPU fallback, quality validation against golden sets, and Redis caching
- Implement the **Retrieval Pipeline**: hybrid search (vector + keyword + metadata), multi-stage reranking (cross-encoder / LLM-as-judge), confidence filtering, personalization via user profiles, and multi-turn context awareness
- Implement the **Generation Pipeline**: standardized prompt templates, medical advice refusal, mandatory disclaimers, inline source citations, token streaming with low latency, and output guardrails (PII redaction, toxicity filtering, hallucination checks)
- Implement the **Chat Orchestration Pipeline**: LangGraph state machine orchestration, short-term memory (10-turn window), long-term memory (vector + graph store), error recovery, and Redis-backed rate limiting
- Implement the **Monitoring Pipeline**: retrieval and generation metrics (Recall@K, NDCG, Faithfulness, Answer Relevancy, Toxicity), alerting on quality thresholds, daily RAGAS evaluation reports, and full request/response tracing via LangSmith and OpenTelemetry
- Set up project infrastructure: Python project structure, configuration management, dependency management, Docker support

## Capabilities

### New Capabilities

_(None — all capabilities already have spec files in `openspec/specs/`)_

### Modified Capabilities

- `ingestion`: Implement full ingestion pipeline from existing spec (data source connectors, processing steps, error handling, production guarantees)
- `embedding`: Implement embedding pipeline from existing spec (model management, batch processing, quality assurance, caching)
- `retrieval`: Implement retrieval pipeline from existing spec (hybrid search, reranking, context limits, personalization, multi-turn awareness)
- `generation`: Implement generation pipeline from existing spec (prompt engineering, safety/compliance, streaming, guardrails)
- `chat`: Implement chat orchestration from existing spec (memory management, pipeline orchestration, rate limiting)
- `monitoring`: Implement monitoring pipeline from existing spec (metrics collection, alerting, logging/tracing)

## Impact

- **New codebase**: Full Python project from scratch — no existing code to modify
- **Key dependencies**: LangChain/LangGraph, LangSmith, OpenAI/Cohere/Voyage APIs, Redis, Qdrant/Pinecone (vector DB), RAGAS/DeepEval, OpenTelemetry, FastAPI, Docker
- **APIs**: New REST/chat endpoints for user interaction, internal pipeline APIs
- **Infrastructure**: Vector database deployment, Redis instance, GPU-enabled embedding workers, observability stack (LangSmith + OTel)
- **External data**: USDA FoodData Central API, FDA databases, Nutritionix API, Open Food Facts
