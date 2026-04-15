## MODIFIED Requirements

### Requirement: REQ-RET-001 Hybrid Retrieval
The system SHALL perform hybrid search combining vector similarity, keyword search, and metadata filters.

#### Scenario: Hybrid search execution
- **WHEN** a user query is received and retrieval is triggered
- **THEN** the pipeline SHALL execute hybrid search (vector + keyword + metadata filters) with configurable weights

### Requirement: REQ-RET-002 Multi-Stage Reranking
Top retrieved results SHALL be reranked for higher relevance.

#### Scenario: Reranking process
- **WHEN** initial top-K results (default K=50) are retrieved and reranking is applied
- **THEN** the results SHALL be reordered using a cross-encoder or LLM-as-judge reranker with a nutrition-specific prompt

### Requirement: REQ-RET-003 Context Limits and Safety
Retrieved context SHALL respect LLM context window limits and safety constraints.

#### Scenario: Safe context selection
- **WHEN** chunks are retrieved from the vector store and final context is prepared for generation
- **THEN** only chunks with `confidence_score > 0.7` and containing the `disclaimer` tag SHALL be included, while respecting the LLM's context window

### Requirement: REQ-RET-004 Personalization
Retrieval SHALL incorporate user-specific preferences when available.

#### Scenario: Personalized retrieval
- **WHEN** a user profile exists with allergies, dietary preferences, age, or gender and retrieval is performed
- **THEN** user-specific metadata filters SHALL be applied to prioritize relevant and safe content

### Requirement: REQ-RET-005 Multi-turn Context Awareness
The retrieval pipeline SHALL leverage conversation history for better context.

#### Scenario: Multi-turn nutrition query
- **WHEN** a conversation history exists about a nutrition topic and a new related query arrives
- **THEN** retrieval SHALL use conversation history embeddings combined with metadata filters for topic constraints
