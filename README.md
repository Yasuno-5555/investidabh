# Investidubh - Personal OSINT Platform

Investidubh is a self-hosted OSINT platform for automating, preserving, and analyzing web investigations.

## 🏗 Architecture

- **Gateway (Node.js/Fastify):** API authentication, request routing, PDF report generation
- **Collector (Python/Playwright):** Headless browser for evidence preservation (HTML/Screenshot)
- **Analysis (Python/BeautifulSoup):** Entity extraction, full-text index registration
- **Storage:**
  - **PostgreSQL:** Metadata, User management
  - **MinIO:** Raw data (Blob) storage
  - **Redis:** Job queue, Event bus
  - **Meilisearch:** Full-text search engine
- **Frontend (Next.js):** Dashboard UI

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose

### Installation

1. Clone repo & Setup environment
   ```bash
   cp .env.example .env
   # (If .env.example doesn't exist, ensure variables in docker-compose are set)
   ```

2.  Start System

    ```bash
    docker-compose up -d --build
    ```

3.  Access Dashboard

      - URL: http://localhost:3000
      - Register a new account to begin.

## 🛠 Operational Commands

### Reset Database (Caution: Deletes all data)

```bash
docker-compose down -v
```

### Backfill Search Index

If you have data collected before Meilisearch was active:

```bash
docker-compose exec analysis python src/backfill.py
```

### View Logs

```bash
docker-compose logs -f [gateway|collector|analysis]
```

## 🔒 Security Notes

  - This system uses JWT for authentication.
  - Designed for local or VPN usage. If exposing to public internet, configure HTTPS/Traefik.
