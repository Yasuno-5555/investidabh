# System Architecture

## Overview
Investidubh is a modular, containerized OSINT platform designed for automated intelligence gathering and analysis. It follows a microservices architecture to ensure scalability and separation of concerns.

## Components

### 1. Gateway Service (`backend/gateway`)
The entry point for all client interactions.
-   **Framework**: Fastify (Node.js/TypeScript)
-   **Responsibilities**:
    -   **API Layer**: REST endpoints for frontend.
    -   **Authentication**: JWT issuance and verification.
    -   **Proxy**: Forwards specific requests to MinIO or other internal services if needed.
    -   **Reporting**: Generates PDF reports on-demand using `pdfkit`.
    -   **Real-time Updates**: SSE (Server-Sent Events) for alerts via `/api/alerts/stream`.
    -   **Chain of Custody**: Logs all critical actions to `audit_logs`.

### 2. Collector Service (`backend/collector`)
Responsible for fetching external data.
-   **Framework**: Python (Playwright)
-   **Responsibilities**:
    -   **Web Scraping**: Headless browsing to capture HTML and Screenshots.
    -   **Tor Integration**: Can route traffic through Tor proxy for anonymity.
    -   **Evidence Preservation**: Hashes (SHA-256) and stores raw artifacts in MinIO.

### 3. Analysis Service (`backend/analysis`)
The brain of the operation. Processes raw data into intelligence.
-   **Framework**: Python (AsyncIO)
-   **Pipeline**:
    1.  **Extraction**: Regex and pattern matching for basic entities (Email, IP, etc.).
    2.  **NLP**: spaCy-based Named Entity Recognition (NER) and relationship extraction.
    3.  **Enrichment**:
        -   **Network**: WHOIS, DNS resolution.
        -   **OSINT**: HIBP, External APIs.
    4.  **TTP Mapping**: Maps text/behaviors to MITRE ATT&CK IDs.
    5.  **Alerting**: Checks watchlists and newly detected TTPs via `AlertManager`.
    6.  **Indexing**: Pushes processed data to Meilisearch for full-text search.

### 4. Frontend (`frontend`)
The user interface.
-   **Framework**: Next.js (React)
-   **Features**:
    -   **Graph View**: Interactive React Flow visualization.
    -   **Timeline**: Temporal analysis view.
    -   **Hypothesis Canvas**: "What-if" scenario planning.
    -   **Dashboards**: Real-time alerts and investigation management.

### 5. Infrastructure
-   **PostgreSQL**: Primary relational database. Stores User, Investigation, Intelligence, Artifacts, and Audit Logs.
-   **MinIO**: S3-compatible object storage for large binary blobs (screenshots, HTML).
-   **Redis**: Message broker (Pub/Sub) for inter-service communication and job queues.
-   **Meilisearch**: Search engine for instant text queries.
-   **Tor**: Optional SOCKS5 proxy for anonymization.

## Data Flow

### Collection & Analysis Flow
1.  **User** submits URL via Frontend.
2.  **Gateway** creates Investigation ID and publishes `investigation_created` event to **Redis**.
3.  **Collector** picks up event, scrapes URL, stores artifacts in **MinIO**, saves hash in **Postgres**, and publishes `collection_completed`.
4.  **Analysis** picks up `collection_completed`:
    -   Fetches HTML from MinIO.
    -   Runs Extraction -> NLP -> Enrichment -> TTP Mapping.
    -   Stores Intelligence in **Postgres**.
    -   Indexes content in **Meilisearch**.
    -   checks Watchlists -> publishes `alert` to Redis if match found.
5.  **Gateway** (subscribed to `alert`) pushes notification to Frontend via SSE.

### Integrity Verification Flow
1.  **User/Admin** requests Integrity Check.
2.  **Gateway** triggers verification job.
3.  **System** iterates all `artifacts`:
    -   Fetches blob from **MinIO**.
    -   Calculates SHA-256.
    -   Compares with DB hash.
4.  **Result**: Report generated and logged to `audit_logs`.

## schemas

### Intelligence Table
-   `id`: UUID
-   `type`: ENUM (person, organization, ip, etc.)
-   `value`: Text (The entity itself)
-   `metadata`: JSONB (Enrichment data, TTP tags, etc.)
-   `confidence_score`: Float (0.0 - 1.0)

### Artifacts Table
-   `id`: UUID
-   `investigation_id`: UUID
-   `artifact_type`: ENUM (html, screenshot)
-   `storage_path`: Text (MinIO path)
-   `hash_sha256`: Varchar(64) (Evidence Integrity)
