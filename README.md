# Nutrition RAG Pipeline Suite

A production-grade Retrieval-Augmented Generation (RAG) system for semantic search and retrieval over public food composition databases (USDA FoodData Central, FDA, Nutritionix, Open Food Facts). Users query nutrition information through a stateful multi-turn chat interface and receive accurate, cited, and safe responses with mandatory disclaimers.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────┐
│  Chat Orchestrator   │  LangGraph state machine
│  (Rate Limit Check)  │  Redis-backed per-user + global limits
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Medical Advice      │  Detect & refuse diagnosis/treatment queries
│  Detection           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Retrieval Pipeline  │  Hybrid search (vector + BM25 + metadata)
│  + Reranking         │  Cross-encoder or LLM-as-judge reranking
│  + Context Filtering │  Confidence > 0.7, disclaimer enforcement
│  + Personalization   │  User allergy/dietary preference filters
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Generation Pipeline │  Prompt template + streaming (≤800ms TTFT)
│  + Disclaimer        │  Mandatory medical disclaimer
│  + Citation          │  Inline [Source: chunk_id] references
│  + Guardrails        │  PII redaction, toxicity, hallucination checks
└─────────┬───────────┘
          │
          ▼
      Response
```

## Pipelines

### 1. Ingestion Pipeline

Ingests, cleans, chunks, and stores nutrition data from multiple sources with full provenance.

| Component | Description |
|-----------|-------------|
| **USDA Connector** | FoodData Central API with pagination, rate limiting, and data normalization |
| **FDA Connector** | Structured JSON exports + PDF extraction with OCR |
| **Nutritionix Connector** | Search and item lookup with branded + common food data |
| **Open Food Facts Connector** | Barcode lookup and search with multilingual support |
| **User Upload** | PDF and CSV file upload with validation (max 50MB) |
| **Expert KB Loader** | Markdown knowledge base parsing with section detection |
| **Cleaning & Normalization** | Unicode normalization, unit standardization, food name normalization, deduplication |
| **Metadata Enrichment** | Source-based confidence scoring, timestamps, nutritional disclaimers |
| **Semantic Chunker** | Nutrition-aware chunking (food items, recipes, dietary guidelines) with overlap |
| **Vector Store Upsert** | Qdrant upsert with document-level deduplication |
| **Error Handler** | Exponential backoff retry, dead-letter queue, 5% failure rate alerting |

### 2. Embedding Pipeline

Generates embeddings with multi-model support and production reliability.

| Component | Description |
|-----------|-------------|
| **Model Registry** | Unified interface for OpenAI, Cohere, Voyage, and Sentence-Transformers (lazy-loaded) |
| **Hot-Swap Manager** | Feature-flag-based model switching — new chunks use new model, existing vectors remain searchable |
| **Batch Embedder** | Configurable batch sizes with GPU/CPU auto-detection and fallback |
| **Quality Validator** | Cosine-similarity sanity check against golden validation set (≤2% failure threshold, auto-rollback) |
| **Embedding Cache** | Redis-backed cache with SHA-256 content-hash keys and 30-day TTL |

### 3. Retrieval Pipeline

Returns the most relevant nutrition context with multi-stage refinement.

| Component | Description |
|-----------|-------------|
| **Hybrid Search** | Dense vector similarity + sparse BM25 + metadata filters with configurable weights |
| **Reranker** | Cross-encoder (default) or LLM-as-judge with nutrition-specific ranking prompt |
| **Context Filter** | Confidence score > 0.7, disclaimer tag enforcement, LLM context window respect |
| **Personalization** | User allergy exclusion filters, dietary preference matching, age-group awareness |
| **Multi-Turn Context** | Conversation history embedding fusion with metadata constraint extraction |

### 4. Generation Pipeline

Produces safe, cited, nutrition-focused responses with strict guardrails.

| Component | Description |
|-----------|-------------|
| **Prompt Builder** | Standardized template: system (nutrition expert + rules) → context (reranked chunks) → user (query + history) |
| **Medical Advice Detector** | Regex-based detection of diagnosis/treatment queries with refusal response |
| **Disclaimer Prepender** | Mandatory "This is not medical advice. Consult a licensed professional." on every response |
| **Citation Injector** | Inline [Source: chunk_id] references with fallback sources section |
| **Streaming Generator** | Token streaming with ≤800ms time-to-first-token, graceful non-streaming fallback |
| **Guardrails** | PII redaction (SSN, email, phone, ZIP), toxicity keyword detection, nutrition hallucination pattern checks |

### 5. Chat Orchestration Pipeline

Manages stateful multi-turn conversations with memory and resilience.

| Component | Description |
|-----------|-------------|
| **LangGraph State Machine** | Graph-based orchestration: medical check → retrieve → rerank → filter → generate → guardrails |
| **Short-Term Memory** | Last 10 conversation turns via Redis-backed storage |
| **Long-Term Memory** | User profile (allergies, dietary preferences) and facts persisted in Redis |
| **Memory Injector** | Merges short-term history + long-term profile into retrieval and generation context |
| **Failure Recovery** | Retry with exponential backoff (3 attempts), graceful degradation preserving conversation state |
| **Rate Limiter** | Redis sliding-window: per-user (60/min) + global (1000/min) limits |

### 6. Monitoring & Observability Pipeline

Continuous quality monitoring, alerting, and tracing.

| Component | Description |
|-----------|-------------|
| **Retrieval Metrics** | Recall@K, NDCG@K, end-to-end latency |
| **Generation Metrics** | Faithfulness, Answer Relevancy (RAGAS), Toxicity (DeepEval) with heuristic fallbacks |
| **Business Metrics** | User satisfaction (thumbs up/down), query volume |
| **Alerting** | Immediate alerts when faithfulness < 0.85 or toxicity > 0.05 |
| **Daily Reports** | Scheduled RAGAS evaluation reports with summary statistics |
| **Trace Logger** | Full request/response logging with trace IDs via LangSmith and OpenTelemetry |

## Evaluation

The system uses a multi-layer evaluation framework:

| Metric | Tool | Threshold |
|--------|------|-----------|
| **Faithfulness** | RAGAS (or heuristic fallback) | Alert if < 0.85 |
| **Answer Relevancy** | RAGAS (or word-overlap heuristic) | Tracked, no hard threshold |
| **Toxicity** | DeepEval (or keyword heuristic) | Alert if > 0.05 |
| **Recall@K** | Custom implementation | Tracked |
| **NDCG@K** | Custom implementation | Tracked |
| **Embedding Quality** | Cosine similarity vs golden set | Rollback if failure > 2% |
| **Ingestion Failure Rate** | Sliding window counter | Alert if > 5% |

Heuristic fallbacks activate when RAGAS or DeepEval are not installed, ensuring the monitoring pipeline always functions.

## Tools & Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI + Uvicorn | Async REST API with OpenAPI docs |
| Orchestration | LangGraph | Stateful graph-based pipeline with checkpointing |
| LLM Framework | LangChain | Prompt construction, embeddings, tool abstraction |
| LLM | OpenAI GPT-4o | Response generation (configurable) |
| Embeddings | OpenAI / Cohere / Voyage / Sentence-Transformers | Multi-model with hot-swapping |
| Vector Database | Qdrant | Hybrid search (dense + sparse), metadata filtering |
| Cache & Rate Limiting | Redis | Embedding cache (30-day TTL), per-user + global rate limits |
| Validation | Pydantic + pydantic-settings | Data models, configuration (env + YAML) |
| PDF Processing | pypdf + pytesseract (OCR) | FDA PDFs, user uploads |
| Data | pandas, httpx, tenacity | CSV parsing, HTTP clients, retry logic |
| Reranking | Cross-Encoder / LLM-as-Judge | Nutrition-specific reranking |
| Evaluation | RAGAS + DeepEval | Faithfulness, relevancy, toxicity (with heuristic fallbacks) |
| Observability | LangSmith + OpenTelemetry | LLM tracing, infrastructure metrics |
| Containerization | Docker Compose | Qdrant, Redis, FastAPI services |
| Testing | pytest + pytest-asyncio | 9 integration tests |
| Linting | Ruff | Python linting and formatting |

## Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| **Qdrant over Pinecone** | Self-hosted control and hybrid search support, but requires infrastructure management vs managed convenience |
| **Redis for dual purpose (cache + rate limiting)** | Simpler infrastructure, but single point of failure without Sentinel/cluster |
| **LangGraph orchestration** | Built-in checkpointing and state management, but tighter coupling to LangChain ecosystem vs a custom state machine |
| **Regex-based medical advice detection** | Fast and deterministic, but may miss nuanced medical queries or produce false positives — no ML-based intent classification |
| **Heuristic fallbacks for evaluation** | System works without RAGAS/DeepEval installed, but heuristic metrics are less accurate than proper model-based evaluation |
| **Lazy embedding model imports** | Avoids import errors for uninstalled optional packages, but defers configuration errors to runtime |
| **Local in-memory fallbacks (when Redis/Qdrant unavailable)** | Enables testing and development without infrastructure, but not suitable for production — no persistence or scaling |
| **Cross-encoder reranking** | Higher quality than pure vector similarity, but adds latency per query — configurable fallback to skip reranking |
| **Keyword-based toxicity detection** | Zero-latency and no API cost, but less sophisticated than classifier-based approaches (e.g., Perspective API) |

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Install optional extras (as needed)
pip install -e ".[embedding-extras]"  # Cohere, Voyage, sentence-transformers
pip install -e ".[eval]"              # RAGAS, DeepEval
pip install -e ".[otel]"             # OpenTelemetry

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Start infrastructure
docker compose up -d qdrant redis

# 5. Run the server
uvicorn nutrition_rag.api.app:app --reload

# 6. Run tests
pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/chat` | POST | Full RAG chat query |
| `/chat/stream` | POST | Streaming token response |
| `/ingest/upload` | POST | Upload PDF/CSV files |
| `/ingest/trigger` | POST | Trigger ingestion pipeline |
| `/openapi.json` | GET | OpenAPI schema |
| `/docs` | GET | Interactive API docs |

## Project Structure

```
nutrition_RAG_V2/
├── src/nutrition_rag/
│   ├── api/                    # FastAPI application and schemas
│   ├── core/                   # Config, data models
│   └── pipelines/
│       ├── ingestion/          # Connectors, cleaner, chunker, enricher, vector store
│       ├── embedding/          # Registry, hot-swap, batch embedder, cache, validator
│       ├── retrieval/          # Hybrid search, reranker, context filter, personalization
│       ├── generation/         # Prompt builder, streamer, guardrails, citation, disclaimer
│       ├── chat/               # Orchestrator, memory, rate limiter, failure recovery
│       └── monitoring/         # Metrics, alerting, reports, trace logger
├── tests/                      # Integration tests
├── config/                     # Pipeline YAML configuration
├── openspec/                   # Specs, change history
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
└── .env.example
```
