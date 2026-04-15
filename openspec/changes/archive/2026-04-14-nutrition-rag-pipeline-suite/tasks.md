## 1. Project Scaffolding and Configuration

- [x] 1.1 Initialize Python project with pyproject.toml, directory structure (src/nutrition_rag/), and core dependencies (fastapi, langchain, langgraph, qdrant-client, redis, pydantic-settings)
- [x] 1.2 Create pydantic-settings configuration module with environment variable + YAML loading for pipeline configs (model names, batch sizes, thresholds, feature flags)
- [x] 1.3 Set up Docker Compose with Qdrant, Redis, and the FastAPI application service
- [x] 1.4 Create shared data models (Pydantic schemas) for Chunk, Document, UserQuery, RetrievedContext, GenerationResult, and PipelineTrace

## 2. Ingestion Pipeline

- [x] 2.1 Implement USDA FoodData Central API connector with pagination, rate limit handling, and data normalization
- [x] 2.2 Implement FDA nutrient database connector (PDF extraction via OCR + structured export parsing)
- [x] 2.3 Implement Nutritionix and Open Food Facts API connectors with error handling
- [x] 2.4 Implement user upload endpoint (PDFs, CSVs) with secure file handling and validation
- [x] 2.5 Implement curated expert knowledge base loader (markdown parsing)
- [x] 2.6 Implement cleaning and normalization module (standardize units, remove duplicates, normalize food names)
- [x] 2.7 Implement metadata enrichment module (source, timestamp, confidence score, nutritional disclaimers)
- [x] 2.8 Implement nutrition-aware semantic chunking (food items, recipes, dietary guidelines)
- [x] 2.9 Implement vector store upsert with deduplication logic
- [x] 2.10 Implement ingestion pipeline orchestrator with idempotent execution and full provenance logging
- [x] 2.11 Implement error handling: exponential backoff retry, dead-letter queue, and 5% failure rate alerting

## 3. Embedding Pipeline

- [x] 3.1 Implement embedding model registry supporting OpenAI, Cohere, Voyage, and sentence-transformers with unified interface
- [x] 3.2 Implement feature-flag-based hot-swapping: new model for new chunks while existing vectors remain searchable
- [x] 3.3 Implement configurable batch embedding with GPU/CPU auto-detection and fallback
- [x] 3.4 Implement embedding quality validation: cosine-similarity check against golden nutrition validation set with ≤2% failure threshold and rollback
- [x] 3.5 Implement Redis-based embedding cache with content-hash keys and 30-day TTL

## 4. Retrieval Pipeline

- [x] 4.1 Implement hybrid search combining vector similarity (dense), keyword search (sparse/BM25), and metadata filters with configurable weights
- [x] 4.2 Implement multi-stage reranking: cross-encoder or LLM-as-judge reranker with nutrition-specific prompt for top-K results (default K=50)
- [x] 4.3 Implement context filtering: confidence_score > 0.7, disclaimer tag enforcement, and LLM context window respect
- [x] 4.4 Implement personalized retrieval: apply user profile filters (allergies, dietary preferences, age, gender) as metadata constraints
- [x] 4.5 Implement multi-turn context awareness: combine conversation history embeddings with current query and metadata filters

## 5. Generation Pipeline

- [x] 5.1 Implement standardized prompt template: system prompt (nutrition expert role + disclaimers + citation rules), context section (reranked chunks), user section (query + conversation history)
- [x] 5.2 Implement medical advice refusal: detect medical diagnosis/treatment queries and refuse with appropriate response
- [x] 5.3 Implement mandatory disclaimer prepending ("This is not medical advice. Consult a licensed professional.")
- [x] 5.4 Implement inline source citation using chunk IDs from retrieved context
- [x] 5.5 Implement token streaming with ≤800ms time-to-first-token and graceful fallback to non-streaming mode
- [x] 5.6 Implement output guardrails: PII redaction, toxicity filtering, and nutrition-fact hallucination checks (self-consistency or external verifier)

## 6. Chat Orchestration Pipeline

- [x] 6.1 Implement LangGraph state machine orchestrating retrieval → generation with stateful checkpointing
- [x] 6.2 Implement short-term memory: last 10 turns via LangGraph checkpointing
- [x] 6.3 Implement long-term memory: store and retrieve user preferences, allergies, and facts from vector + graph memory store
- [x] 6.4 Implement memory context injection into the retrieval and generation pipelines
- [x] 6.5 Implement transient failure recovery: retry or graceful degradation without losing conversation state
- [x] 6.6 Implement Redis-backed per-user rate limiting with configurable quotas and global rate limit enforcement

## 7. Monitoring and Observability Pipeline

- [x] 7.1 Implement retrieval metrics collection: Recall@K, NDCG, end-to-end latency
- [x] 7.2 Implement generation metrics collection: Faithfulness, Answer Relevancy, Toxicity score via RAGAS/DeepEval
- [x] 7.3 Implement business metrics: user satisfaction (thumbs up/down), query volume
- [x] 7.4 Implement alerting: faithfulness < 0.85 or toxicity > 0.05 triggers immediate alert
- [x] 7.5 Implement daily scheduled RAGAS evaluation report generation and distribution
- [x] 7.6 Implement request/response logging with full trace ID, retrieved chunks, generated response, and latency breakdown via LangSmith and OpenTelemetry

## 8. API Layer and Integration

- [x] 8.1 Implement FastAPI application with chat endpoint, health check, and ingestion trigger endpoints
- [x] 8.2 Implement request/response schemas and API documentation (OpenAPI)
- [x] 8.3 Implement end-to-end integration test: query → retrieval → generation → response with streaming
