# Chat Orchestration and Memory Pipeline

## Purpose
The chat pipeline maintains stateful, multi-turn conversations with persistent user memory.

## Requirements

### REQ-CHAT-001: Memory Management
The system SHALL maintain both short-term and long-term memory for each user conversation.

#### Scenario: Short-term conversation context
- **GIVEN** an ongoing multi-turn conversation
- **WHEN** the user sends a new message
- **THEN** the last 10 turns SHALL be available via LangGraph checkpointing

#### Scenario: Long-term user memory retrieval
- **GIVEN** the user has previously shared preferences, allergies, or important facts
- **WHEN** a relevant query is made in a new session
- **THEN** those facts SHALL be retrievable from the vector + graph memory store

### REQ-CHAT-002: Pipeline Orchestration
All pipelines (retrieval → generation) SHALL be orchestrated via a LangGraph state machine with error recovery.

#### Scenario: Normal execution flow
- **GIVEN** a valid user query arrives
- **WHEN** the orchestration layer executes the full pipeline
- **THEN** memory context SHALL be injected and a response SHALL be generated

#### Scenario: Transient failure recovery
- **GIVEN** a downstream pipeline (embedding, retrieval, or generation) fails transiently
- **WHEN** the error occurs during execution
- **THEN** the orchestration layer SHALL retry or gracefully degrade without losing conversation state

### REQ-CHAT-003: Rate Limiting and Quotas
The system SHALL enforce per-user and global rate limits.

#### Scenario: Per-user quota enforcement
- **GIVEN** a user has reached their request limit for the current window
- **WHEN** the user sends another request
- **THEN** the request SHALL be rejected with an appropriate rate-limit response (Redis-backed)

#### Scenario: Global quota enforcement
- **GIVEN** the global rate limit has been reached
- **WHEN** any user sends a request
- **THEN** the request SHALL be throttled or rejected appropriately