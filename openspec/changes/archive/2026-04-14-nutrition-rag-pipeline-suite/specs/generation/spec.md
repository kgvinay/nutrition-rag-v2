## MODIFIED Requirements

### Requirement: REQ-GEN-001 Prompt Engineering
Every prompt SHALL follow a standardized template consisting of system instructions, retrieved context, and user query with conversation history.

#### Scenario: Standard prompt construction
- **WHEN** a user query is received with conversation history and the prompt is built for the LLM
- **THEN** it SHALL include: System prompt (nutrition expert role + disclaimers + citation rules), Context section (retrieved and reranked chunks), User section (original query + relevant conversation history)

### Requirement: REQ-GEN-002 Safety and Compliance
The generation pipeline SHALL enforce strict safety and compliance rules.

#### Scenario: Medical advice refusal
- **WHEN** a user query asks for medical diagnosis or treatment advice
- **THEN** the system SHALL refuse to provide such advice

#### Scenario: Mandatory disclaimer
- **WHEN** any response is generated and the final output is prepared
- **THEN** it SHALL prepend: "This is not medical advice. Consult a licensed professional."

#### Scenario: Source citation
- **WHEN** retrieved chunks are used in generation and the response is produced
- **THEN** sources SHALL be cited inline using chunk IDs

### Requirement: REQ-GEN-003 Streaming and Latency
Responses SHALL support token streaming with low initial latency and fallback capability.

#### Scenario: Streaming response
- **WHEN** a user query is processed and generation begins
- **THEN** the first token SHALL be returned within ≤ 800ms, with graceful fallback to non-streaming mode if needed

### Requirement: REQ-GEN-004 Guardrails
All generated outputs SHALL pass multiple safety and quality checks.

#### Scenario: Output validation
- **WHEN** an LLM response is generated and guardrails are applied
- **THEN** the output SHALL pass PII redaction, toxicity filtering, and nutrition-fact hallucination checks (via self-consistency or external verifier)
