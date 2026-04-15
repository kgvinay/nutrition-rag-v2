## MODIFIED Requirements

### Requirement: REQ-CHAT-001 Memory Management
The system SHALL maintain both short-term and long-term memory for each user conversation.

#### Scenario: Short-term conversation context
- **WHEN** the user sends a new message in an ongoing multi-turn conversation
- **THEN** the last 10 turns SHALL be available via LangGraph checkpointing

#### Scenario: Long-term user memory retrieval
- **WHEN** the user has previously shared preferences, allergies, or important facts and a relevant query is made in a new session
- **THEN** those facts SHALL be retrievable from the vector + graph memory store

### Requirement: REQ-CHAT-002 Pipeline Orchestration
All pipelines (retrieval → generation) SHALL be orchestrated via a LangGraph state machine with error recovery.

#### Scenario: Normal execution flow
- **WHEN** a valid user query arrives and the orchestration layer executes the full pipeline
- **THEN** memory context SHALL be injected and a response SHALL be generated

#### Scenario: Transient failure recovery
- **WHEN** a downstream pipeline (embedding, retrieval, or generation) fails transiently
- **THEN** the orchestration layer SHALL retry or gracefully degrade without losing conversation state

### Requirement: REQ-CHAT-003 Rate Limiting and Quotas
The system SHALL enforce per-user and global rate limits.

#### Scenario: Per-user quota enforcement
- **WHEN** a user has reached their request limit for the current window and sends another request
- **THEN** the request SHALL be rejected with an appropriate rate-limit response (Redis-backed)

#### Scenario: Global quota enforcement
- **WHEN** the global rate limit has been reached and any user sends a request
- **THEN** the request SHALL be throttled or rejected appropriately
