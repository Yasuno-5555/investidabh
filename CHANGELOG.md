# Changelog

All notable changes to Investidubh are documented in this file.

## [2.0.0] - 2024-12-15

### 🎉 Season 2: Zero-Cost Commercial Grade OSINT

Major release completing the commercial-grade feature set.

### Added

#### Phase 23: Data Source Expansion
- RSS feed collector for news monitoring
- Social media collector (Mastodon, Twitter API v2)
- GitHub collector for repository/commit analysis
- Infrastructure collector (crt.sh Certificate Transparency)

#### Phase 24: Entity Type Explosion
- New entity types: DOMAIN, EMAIL, IP, SUBDOMAIN, SOCIAL_ACCOUNT, CERTIFICATE
- Entity normalization and deduplication
- Source type tracking (manual, nlp, regex, external, api)
- Confidence scoring

#### Phase 25: Relationship Engine 2.0
- NLP-based relationship extraction using spaCy dependency parsing
- Heuristic linking (EMAIL→DOMAIN, SUBDOMAIN→DOMAIN)
- Relationship storage in JSONB metadata

#### Phase 26: Temporal Intelligence
- Entity aging categories: FRESH, RECENT, STALE, ANCIENT
- First seen / Last seen tracking
- Frequency (sightings) aggregation
- Visual styling based on age (opacity, grayscale)

#### Phase 27: Priority Score 2.0
- 5-component scoring algorithm
- Degree centrality (25%)
- Frequency weight (20%)
- Cross-investigation presence (25%)
- Negative sentiment weight (15%)
- Freshness weight (15%)
- Visual feedback: red glow (high), orange border (medium)

#### Phase 28: Investigator UX
- Analyst notes (Markdown per entity)
- Tagging system (Watchlist, Confirmed, Ignore, Reviewed)
- Node pinning with position persistence
- PATCH API for metadata updates

#### Phase 29: Pattern Detection
- Frequency spike detection (>3x normal = anomaly)
- Key entity identification (top priority + high degree)
- Insights panel with auto-detected threats
- Red pulsing badge for anomalies, gold border for key entities

#### Phase 30: Intelligence Report Pro
- Professional PDF report generation
- WeasyPrint + Jinja2 templates
- Graph image embedding
- Executive summary with key findings and anomalies

### Changed
- Graph API now returns `insights` section
- Node styling based on priority score
- Enhanced Detail Panel with score breakdown

### Fixed
- Entity deduplication across investigations
- Proper JSONB metadata merging
- Cross-investigation edge generation

---

## [1.5.0] - 2024-11-01

### Added
- Phase 14: Subdomain Hunter (crt.sh integration)
- Phase 15: Time Traveler (Wayback Machine)
- Phase 16: Tor Integration for OPSEC

---

## [1.0.0] - 2024-10-01

### Initial Release
- Basic investigation workflow
- Web collection (HTML + Screenshot)
- Entity extraction (NER)
- Graph visualization
- Full-text search
