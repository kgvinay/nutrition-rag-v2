# Retrieval and Reranking Pipeline

## Purpose
The retrieval pipeline returns the most relevant, accurate, and up-to-date nutrition context while minimizing hallucinations and toxicity.

## Requirements

### REQ-RET-001: Hybrid Retrieval
The system SHALL perform hybrid search combining vector similarity, keyword search, and metadata filters.

#### Scenario: Hybrid search execution
- **GIVEN** a user query is received
- **WHEN** retrieval is triggered
- **THEN** the pipeline SHALL execute hybrid search (vector + keyword + metadata filters) with configurable weights

### REQ-RET-002: Multi-Stage Reranking
Top retrieved results SHALL be reranked for higher relevance.

#### Scenario: Reranking process
- **GIVEN** initial top-K results (default K=50) are retrieved
- **WHEN** reranking is applied
- **THEN** the results SHALL be reordered using a cross-encoder or LLM-as-judge reranker with a nutrition-specific prompt

### REQ-RET-003: Context Limits and Safety
Retrieved context SHALL respect LLM context window limits and safety constraints.

#### Scenario: Safe context selection
- **GIVEN** chunks are retrieved from the vector store
- **WHEN** final context is prepared for generation
- **THEN** only chunks with `confidence_score > 0.7` and containing the `disclaimer` tag SHALL be included, while respecting the LLM's context window

### REQ-RET-004: Personalization
Retrieval SHALL incorporate user-specific preferences when available.

#### Scenario: Personalized retrieval
- **GIVEN** a user profile exists with allergies, dietary preferences, age, or gender
- **WHEN** retrieval is performed
- **THEN** user-specific metadata filters SHALL be applied to prioritize relevant and safe content

### REQ-RET-005: Multi-turn Context Awareness
The retrieval pipeline SHALL leverage conversation history for better context.

#### Scenario: Multi-turn nutrition query
- **GIVEN** a conversation history exists about “high-protein vegan meals”
- **WHEN** a new related query arrives
- **THEN** retrieval SHALL use conversation history embeddings combined with metadata filters for vegan and protein constraints