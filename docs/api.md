# API Reference

Base URL: `/api`
Auth: Bearer Token (JWT) required for most endpoints.

## Authentication

### `POST /auth/register`
Create a new user account.
-   **Body**: `{ "email": "user@example.com", "password": "securepassword" }`

### `POST /auth/login`
Authenticate and receive JWT.
-   **Body**: `{ "email": "...", "password": "..." }`
-   **Response**: `{ "token": "ey..." }`

## Investigations

### `GET /investigations`
List all investigations for the current user.

### `POST /investigations`
Start a new investigation.
-   **Body**: `{ "targetUrl": "https://example.com", "name": "Optional Name" }`

### `GET /investigations/:id`
Get summary details of a specific investigation.

### `GET /investigations/:id/report`
**[New]** Generate and download a PDF intelligence report.
-   **Response**: `application/pdf` binary stream.

### `GET /investigations/:id/audit`
**[New]** Retrieve chain of custody audit logs for this investigation.
-   **Response**: `[ { "action": "VIEW_GRAPH", "timestamp": "...", "user_id": "..." }, ... ]`

### `GET /investigations/:id/timeline`
**[New]** Retrieve aggregated temporal data for timeline visualization.
-   **Response**: `{ "events": [...], "buckets": [...] }`

## Intelligence & Graph

### `GET /graph`
Retrieve the complete node/edge graph for the dashboard.
-   **Query Params**: `investigationId` (optional filter)
-   **Response**: React Flow compatible `{ nodes: [...], edges: [...], insights: {...} }`

### `PATCH /entities/:type/:value`
Update metadata for a specific entity (e.g., adding notes or tags).
-   **Body**: `{ "notes": "...", "tags": ["watchlist", "suspect"] }`

## Admin & System

### `GET /alerts/stream`
**[New]** Server-Sent Events (SSE) endpoint for real-time alerts.

### `POST /admin/verify-integrity`
**[New]** Trigger a system-wide evidence integrity verification.
-   **Response**: `{ "status": "completed", "scanned": 100, "failures": [] }`
