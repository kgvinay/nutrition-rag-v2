## MODIFIED Requirements

### Requirement: REQ-ING-001 Data Sources
The system SHALL support multiple nutrition data sources in priority order.

#### Scenario: Supported data sources
- **WHEN** the ingestion pipeline runs and one of the approved data sources becomes available
- **THEN** it SHALL successfully ingest from: USDA FoodData Central API (full dataset nightly), FDA nutrient databases (PDF + structured exports), Nutritionix API and Open Food Facts, user-uploaded documents (PDFs, CSVs) via secure upload endpoint, curated expert knowledge base (markdown)

### Requirement: REQ-ING-002 Processing Steps
The ingestion pipeline SHALL execute a defined sequence of processing steps that is idempotent and restartable.

#### Scenario: End-to-end ingestion flow
- **WHEN** raw data arrives from any supported source and the pipeline processes the data
- **THEN** it SHALL perform the following steps in order: Extraction (text + tables + images via OCR), Cleaning & normalization (standardize units, remove duplicates), Metadata enrichment (source, timestamp, confidence score, nutritional disclaimers), Semantic chunking (nutrition-aware: food items, recipes, guidelines), Embedding generation, Vector store upsert with deduplication

### Requirement: REQ-ING-003 Production Guarantees
The ingestion pipeline SHALL meet high-scale production standards.

#### Scenario: Scale and idempotency
- **WHEN** large volumes of nutrition data (>1M records/day) are processed during daily or backfill operations
- **THEN** it SHALL be fully idempotent, support restarts, log full provenance for every chunk, enforce GDPR/CCPA compliance and data retention policies, and emit metrics (ingestion latency, error rate, chunk quality score) to the observability stack

### Requirement: REQ-ING-004 Error Handling and Resilience
The pipeline SHALL be resilient to failures with appropriate retry and alerting mechanisms.

#### Scenario: Transient failure handling
- **WHEN** a transient error is detected during ingestion (network, API rate limit, etc.)
- **THEN** the pipeline SHALL retry with exponential backoff

#### Scenario: Permanent failure and alerting
- **WHEN** a permanent failure occurs or the overall failure rate exceeds 5%
- **THEN** failed items SHALL be sent to a dead-letter queue and an alert SHALL be triggered
