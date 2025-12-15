# 🔍 Investidubh — Commercial-Grade OSINT Platform

> **Zero-Cost, Zero-AI, Maximum Intelligence**  
> A self-hosted OSINT platform for automated web investigation, entity extraction, relationship mapping, and intelligence reporting.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## ✨ Features

### 📡 Multi-Source Data Collection
| Source | Description |
|--------|-------------|
| **Web Scraping** | Playwright-based HTML/Screenshot preservation |
| **RSS Feeds** | Automated news monitoring |
| **Social Media** | Mastodon public timeline, Twitter API v2 |
| **GitHub** | Repository/commit analysis, contributor extraction |
| **Certificate Transparency** | Subdomain discovery via crt.sh |
| **Wayback Machine** | Historical snapshot analysis ("Ghost Entities") |

### 🧠 Analysis Engine
- **Entity Extraction**: PERSON, ORG, EMAIL, DOMAIN, IP, PHONE, SUBDOMAIN, SOCIAL_ACCOUNT
- **Relationship Engine**: NLP-based (spaCy) + heuristic linking
- **Temporal Intelligence**: Aging categories (FRESH → ANCIENT)
- **Priority Score 2.0**: 5-component algorithm (Degree, Frequency, Cross-Investigation, Sentiment, Freshness)
- **Pattern Detection**: Frequency spike anomalies, Key entity identification

### 🎯 Analyst Tools
- **Notes**: Markdown annotation per entity
- **Tagging**: Watchlist, Confirmed, Ignore, Reviewed
- **Pinning**: Fix node positions in graph
- **PDF Report**: Professional intelligence report export

### 🕸️ Graph Visualization
- Interactive React Flow graph
- Priority-based node styling (size, color, glow)
- Relationship edges with dynamic animation
- Timeline slider for temporal exploration

---

## 🏗 Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │◄──►│   Gateway   │◄──►│  Collector  │
│  (Next.js)  │    │  (Fastify)  │    │ (Playwright)│
└─────────────┘    └──────┬──────┘    └─────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │PostgreSQL│ │  MinIO   │ │  Redis   │
        │ Metadata │ │  Blobs   │ │  Queue   │
        └──────────┘ └──────────┘ └──────────┘
              │
              ▼
        ┌──────────┐    ┌──────────┐
        │ Analysis │◄──►│Meilisearch│
        │ (Python) │    │  Search   │
        └──────────┘    └──────────┘
```

### Services
| Service | Stack | Purpose |
|---------|-------|---------|
| **Gateway** | Node.js + Fastify | API, Auth (JWT), PDF generation |
| **Collector** | Python + Playwright | Web scraping, evidence preservation |
| **Analysis** | Python + spaCy | NLP, entity extraction, indexing |
| **Frontend** | Next.js + React Flow | Dashboard, graph visualization |

### Storage
| Storage | Purpose |
|---------|---------|
| **PostgreSQL** | Users, investigations, intelligence, metadata |
| **MinIO** | Raw HTML, screenshots, artifacts |
| **Redis** | Job queue, pub/sub events |
| **Meilisearch** | Full-text search |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM recommended

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/investidubh.git
cd investidubh

# Configure environment
cp .env.example .env
# Edit .env as needed

# Start all services
docker-compose up -d --build

# Access dashboard
open http://localhost:3000
```

### First Run
1. Register a new account at `http://localhost:3000/register`
2. Create your first investigation
3. Enter target URL and start collection
4. View extracted entities in the Graph tab

---

## 🛠 Operations

### View Logs
```bash
docker-compose logs -f gateway
docker-compose logs -f collector
docker-compose logs -f analysis
```

### Reset Database
```bash
docker-compose down -v
docker-compose up -d
```

### Rebuild Services
```bash
docker-compose up -d --build --force-recreate
```

### Run Database Migration
```bash
docker-compose exec analysis python src/migrate_db.py
```

---

## 📊 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |

### Investigations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/investigations` | List investigations |
| POST | `/api/investigations` | Create investigation |
| GET | `/api/investigations/:id` | Get investigation details |

### Graph & Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/graph` | Get all entities + insights |
| PATCH | `/api/entities/:type/:value` | Update entity metadata |
| POST | `/api/report/generate` | Generate PDF report |

---

## 🔒 Security

- **Authentication**: JWT-based with bcrypt password hashing
- **Authorization**: User-scoped data isolation
- **OPSEC**: Optional Tor integration for collection
- **Deployment**: Designed for local/VPN use; add HTTPS for public exposure

---

## 📁 Project Structure

```
investidabh/
├── backend/
│   ├── gateway/         # API server (TypeScript)
│   ├── collector/       # Web scraper (Python)
│   └── analysis/        # NLP engine (Python)
├── frontend/            # Next.js dashboard
├── packages/
│   ├── logger/          # Shared logging
│   └── ts-types/        # TypeScript types
├── storage/
│   └── postgres/        # Database init scripts
├── docs/                # Documentation
└── docker-compose.yml
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📜 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with:
- [spaCy](https://spacy.io/) — NLP
- [Playwright](https://playwright.dev/) — Browser automation
- [React Flow](https://reactflow.dev/) — Graph visualization
- [WeasyPrint](https://weasyprint.org/) — PDF generation
- [Meilisearch](https://meilisearch.com/) — Full-text search

---

**Investidubh** — *Intelligence Gathering, Simplified.*
