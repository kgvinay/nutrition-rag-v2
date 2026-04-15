# Vector Embedding Pipeline

## Purpose
The embedding pipeline generates high-quality nutrition-domain embeddings and supports model swapping without downtime.

## Requirements

### REQ-EMB-001: Model Management
The system SHALL support multiple embedding models (OpenAI, Cohere, Voyage, and open-source models via sentence-transformers) with hot-swapping capability.

#### Scenario: Hot-swapping embedding models
- **GIVEN** a new embedding model is approved and configured via feature flag
- **WHEN** the feature flag is flipped to the new model
- **THEN** new document chunks SHALL use the new model while existing vectors remain searchable (zero downtime)

### REQ-EMB-002: Batch Processing
Embeddings SHALL be generated in configurable batch sizes with GPU acceleration when available and automatic fallback to CPU.

#### Scenario: Large batch embedding
- **GIVEN** a batch of nutrition-domain document chunks is submitted for embedding
- **WHEN** processing begins
- **THEN** the pipeline SHALL use GPU if available and fall back to CPU without failure

### REQ-EMB-003: Quality Assurance
Every embedding batch SHALL pass a cosine-similarity sanity check against a golden validation set from the nutrition domain.

#### Scenario: Embedding quality validation
- **GIVEN** an embedding batch has been generated
- **WHEN** the quality check runs
- **THEN** the failure rate SHALL be ≤ 2%; if exceeded, an alert SHALL be triggered and the batch SHALL be rolled back

### REQ-EMB-004: Caching
Identical content SHALL reuse cached embeddings to avoid redundant computation.

#### Scenario: Cache hit for duplicate content
- **GIVEN** a document chunk is identical to previously embedded content
- **WHEN** embedding is requested
- **THEN** the cached embedding SHALL be returned from Redis (30-day TTL)