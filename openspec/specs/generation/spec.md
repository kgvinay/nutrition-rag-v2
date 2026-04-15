# Augmented Generation Pipeline

## Purpose
The generation pipeline produces safe, cited, nutrition-focused responses using RAG with strict guardrails.

## Requirements

### REQ-GEN-001: Prompt Engineering
Every prompt SHALL follow a standardized template consisting of system instructions, retrieved context, and user query with conversation history.

#### Scenario: Standard prompt construction
- **GIVEN** a user query is received with conversation history
- **WHEN** the prompt is built for the LLM
- **THEN** it SHALL include:
  - System prompt: Nutrition expert role + disclaimers + citation rules
  - Context section: Retrieved and reranked chunks
  - User section: Original query + relevant conversation history

### REQ-GEN-002: Safety and Compliance
The generation pipeline SHALL enforce strict safety and compliance rules.

#### Scenario: Medical advice refusal
- **GIVEN** a user query asks for medical diagnosis or treatment advice
- **WHEN** the generation pipeline processes the request
- **THEN** the system SHALL refuse to provide such advice

#### Scenario: Mandatory disclaimer
- **GIVEN** any response is generated
- **WHEN** the final output is prepared
- **THEN** it SHALL prepend: “This is not medical advice. Consult a licensed professional.”

#### Scenario: Source citation
- **GIVEN** retrieved chunks are used in generation
- **WHEN** the response is produced
- **THEN** sources SHALL be cited inline using chunk IDs

### REQ-GEN-003: Streaming and Latency
Responses SHALL support token streaming with low initial latency and fallback capability.

#### Scenario: Streaming response
- **GIVEN** a user query is processed
- **WHEN** generation begins
- **THEN** the first token SHALL be returned within ≤ 800ms, with graceful fallback to non-streaming mode if needed

### REQ-GEN-004: Guardrails
All generated outputs SHALL pass multiple safety and quality checks.

#### Scenario: Output validation
- **GIVEN** an LLM response is generated
- **WHEN** guardrails are applied
- **THEN** the output SHALL pass PII redaction, toxicity filtering, and nutrition-fact hallucination checks (via self-consistency or external verifier)