# 🔍 Investidubh — Commercial-Grade OSINT Platform

> **Zero-Cost, Zero-AI, Maximum Intelligence**  
> A self-hosted OSINT platform for automated web investigation, entity extraction, relationship mapping, and intelligence reporting.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## ✨ Features

### 📡 Multi-Source Data Collection & OSINT
| Source | Description |
|--------|-------------|
| **Web Scraping** | Playwright-based HTML/Screenshot preservation |
| **Network Recon** | WHOIS, DNS (A, MX, TXT) automated lookups |
| **Enrichment** | Integration with HIBP, GitHub, etc. |
| **RSS / Social** | Automated news & social media monitoring |
| **Wayback Machine** | Historical snapshot analysis ("Ghost Entities") |

### 🧠 Advanced Analysis Engine
- **Entity Extraction**: 15+ types including CRYPTO, CVE, ASN, SUBDOMAIN
- **TTP Mapping**: Automated mapping to MITRE ATT&CK IDs
- **Sentiment & Relations**: NLP-based relationship extraction
- **Threat Detection**: Watchlist matching & Anomaly detection
- **Integrity Verification**: SHA-256 Hashing & Automated tamper detection

### 🎯 Analyst Workbench
- **Graph Visualization**: Interactive, force-directed graph with TTP styling
- **Timeline Intelligence**: Temporal analysis of events & entities
- **Hypothesis Mode**: "What-if" analysis with shadow nodes/edges
- **Chain of Custody**: Immutable audit logs for all actions
- **Reporting**: One-click PDF Intelligence Reports

### 💻 Command Line Interface (CLI)
- **Headless Operation**: Full feature parity with GUI.
- **Automation**: Scriptable `scan`, `list`, and `search` commands.
- **Rich Output**: Formatted tables and JSON output for integration.

### ️ Deployment Ready
- **Optimized**: Multi-stage Docker builds & .dockerignore
- **Secure**: JWT Auth, Role-based controls, Tor Proxy support
- **Scalable**: Redis-backed queuing & caching

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
              │           │
              ▼           ▼
        ┌──────────┐    ┌──────────┐
        │ Analysis │◄──►│Meilisearch│
        │ (Python) │    │  Search   │
        └──────────┘    └──────────┘
              ▲
              │
        ┌──────────┐
        │   CLI    │
        │ (Python) │
        └──────────┘
```

### Services
| Service | Stack | Purpose |
|---------|-------|---------|
| **Gateway** | Node.js + Fastify | API, Auth (JWT), Search, PDF generation |
| **Collector** | Python + Playwright | Web scraping, evidence preservation |
| **Analysis** | Python + spaCy | NLP, entity extraction, indexing |
| **Frontend** | Next.js + React Flow | Dashboard, graph visualization |
| **CLI** | Python + Click | Terminal-based management & automation |

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
- Python 3.8+ (for CLI)
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

### CLI Setup
```bash
# Install CLI dependencies
pip install -r cli/requirements.txt

# Authenticate
python3 cli/investidubh_cli.py auth login --username admin --password secret

# Verify
python3 cli/investidubh_cli.py list
```

### First Run
1. Register a new account at `http://localhost:3000/register` (or use CLI)
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
| GET | `/api/search` | Search investigations & artifacts |

### Graph & Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/graph` | Get all entities + insights |
| GET | `/api/investigations/:id/timeline` | Get temporal event data |
| PATCH | `/api/entities/:type/:value` | Update entity metadata |

### Reports & Compliance
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/investigations/:id/report` | Generate PDF report |
| GET | `/api/investigations/:id/audit` | Get Chain of Custody logs |
| POST | `/api/admin/verify-integrity` | Run system-wide integrity check |

### Real-time Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts/stream` | SSE stream for real-time alerts |

---

## 🔒 Security

- **Authentication**: JWT-based with bcrypt password hashing
- **Authorization**: User-scoped data isolation
- **OPSEC**: Optional Tor integration for collection
- **Deployment**: Designed for local/VPN use; add HTTPS for public exposure

---

## 📁 Project Structure

```
investidubh/
├── backend/
│   ├── gateway/         # API server (TypeScript)
│   ├── collector/       # Web scraper (Python)
│   └── analysis/        # NLP engine (Python)
├── frontend/            # Next.js dashboard
├── cli/                 # CLI Tool (Python)
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
