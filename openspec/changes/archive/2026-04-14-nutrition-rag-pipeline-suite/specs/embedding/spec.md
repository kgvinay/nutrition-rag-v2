## MODIFIED Requirements

### Requirement: REQ-EMB-001 Model Management
The system SHALL support multiple embedding models (OpenAI, Cohere, Voyage, and open-source models via sentence-transformers) with hot-swapping capability.

#### Scenario: Hot-swapping embedding models
- **WHEN** a new embedding model is approved and configured via feature flag and the feature flag is flipped to the new model
- **THEN** new document chunks SHALL use the new model while existing vectors remain searchable (zero downtime)

### Requirement: REQ-EMB-002 Batch Processing
Embeddings SHALL be generated in configurable batch sizes with GPU acceleration when available and automatic fallback to CPU.

#### Scenario: Large batch embedding
- **WHEN** a batch of nutrition-domain document chunks is submitted for embedding and processing begins
- **THEN** the pipeline SHALL use GPU if available and fall back to CPU without failure

### Requirement: REQ-EMB-003 Quality Assurance
Every embedding batch SHALL pass a cosine-similarity sanity check against a golden validation set from the nutrition domain.

#### Scenario: Embedding quality validation
- **WHEN** an embedding batch has been generated and the quality check runs
- **THEN** the failure rate SHALL be ≤ 2%; if exceeded, an alert SHALL be triggered and the batch SHALL be rolled back

### Requirement: REQ-EMB-004 Caching
Identical content SHALL reuse cached embeddings to avoid redundant computation.

#### Scenario: Cache hit for duplicate content
- **WHEN** a document chunk is identical to previously embedded content and embedding is requested
- **THEN** the cached embedding SHALL be returned from Redis (30-day TTL)
