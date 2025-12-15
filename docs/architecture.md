# Investidubh Architecture

## System Overview

Investidubh is a microservices-based OSINT platform with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│                     (Next.js + React Flow)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        GATEWAY                              │
│                    (Fastify + JWT)                          │
│  • REST API endpoints                                       │
│  • Authentication/Authorization                              │
│  • PDF report generation                                    │
│  • Graph data aggregation                                   │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│    COLLECTOR     │ │    ANALYSIS      │ │     STORAGE      │
│   (Playwright)   │ │  (spaCy + NLP)   │ │                  │
│                  │ │                  │ │  PostgreSQL      │
│  • Web scraping  │ │  • NER           │ │  MinIO           │
│  • Screenshots   │ │  • Sentiment     │ │  Redis           │
│  • RSS/SNS/Git   │ │  • Relationships │ │  Meilisearch     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Data Flow

### Collection Pipeline
1. User creates Investigation with target URL
2. Gateway publishes job to Redis queue
3. Collector picks up job, fetches HTML/screenshot
4. Artifacts stored in MinIO
5. Analysis service extracts entities
6. Entities stored in PostgreSQL, indexed in Meilisearch

### Analysis Pipeline
1. Raw HTML parsed with BeautifulSoup
2. Text extracted and processed with spaCy
3. Named entities identified (NER)
4. Relationships extracted via dependency parsing
5. Sentiment analyzed with TextBlob
6. Entity normalization and deduplication
7. Priority scoring calculated

### Graph Pipeline
1. Gateway aggregates entities from PostgreSQL
2. Temporal stats calculated (first_seen, last_seen, frequency)
3. Aging category assigned (FRESH/RECENT/STALE/ANCIENT)
4. Priority Score computed (5 components)
5. Pattern detection (anomalies, key entities)
6. Nodes and edges formatted for React Flow

## Database Schema

### Tables
- `users` — User accounts (id, username, password_hash)
- `investigations` — Investigation metadata (id, user_id, target_url, status)
- `artifacts` — Collected evidence (id, investigation_id, type, minio_path)
- `intelligence` — Extracted entities (id, investigation_id, entity_type, value, metadata)

### Key ENUMs
- `entity_type_enum`: person, organization, email, domain, ip, phone, subdomain, etc.
- `source_type_enum`: manual, nlp, regex, external, api

### JSONB Metadata
The `intelligence.metadata` column stores:
- `relations`: Extracted relationships
- `notes`: Analyst annotations
- `tags`: Classification tags
- `pinned`: UI pin state
- `pinned_position`: Graph coordinates

## Priority Score Algorithm

```
Priority = 0.25×Degree + 0.20×Frequency + 0.25×CrossInv + 0.15×Sentiment + 0.15×Freshness
```

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Degree Centrality | 25% | log₂(edges) × 20 |
| Frequency | 20% | min(100, sightings × 3) |
| Cross-Investigation | 25% | (inv_count - 1) × 50 |
| Negative Sentiment | 15% | 50 - sentiment × 50 |
| Freshness | 15% | FRESH=100, ANCIENT=0 |

## Pattern Detection

### Frequency Spike
```
spike_ratio = freq_7d / monthly_avg
is_anomaly = spike_ratio > 3 AND freq_7d > 1
```

### Key Entity
```
is_key = priority >= threshold 
       AND degree >= avg_degree 
       AND type IN ('person', 'organization')
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | redis://localhost:6379 | Redis connection |
| `MINIO_ENDPOINT_HOST` | minio | MinIO host |
| `MEILI_HOST` | http://meilisearch:7700 | Meilisearch URL |
| `JWT_SECRET` | — | JWT signing secret |
| `NEXT_PUBLIC_API_URL` | http://localhost:8080 | Frontend API URL |
