# API Reference

## Authentication

All API endpoints (except `/api/auth/*`) require JWT authentication.

Include token in header:
```
Authorization: Bearer <token>
```

---

## Auth Endpoints

### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "analyst",
  "password": "secure123"
}
```

**Response:**
```json
{
  "id": "uuid",
  "username": "analyst"
}
```

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "analyst",
  "password": "secure123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Investigation Endpoints

### List Investigations
```http
GET /api/investigations
Authorization: Bearer <token>
```

### Create Investigation
```http
POST /api/investigations
Authorization: Bearer <token>
Content-Type: application/json

{
  "target_url": "https://example.com"
}
```

### Get Investigation
```http
GET /api/investigations/:id
Authorization: Bearer <token>
```

### Delete Investigation
```http
DELETE /api/investigations/:id
Authorization: Bearer <token>
```

---

## Graph & Analysis

### Get Graph Data
```http
GET /api/graph
Authorization: Bearer <token>
```

**Response:**
```json
{
  "nodes": [
    {
      "id": "ent-person-john",
      "data": {
        "label": "John Smith",
        "type": "person",
        "stats": {
          "frequency": 5,
          "first_seen": "2024-01-01T00:00:00Z",
          "last_seen": "2024-12-15T00:00:00Z",
          "aging_category": "FRESH"
        },
        "priority": {
          "score": 75,
          "level": "high",
          "breakdown": {
            "degree": 70,
            "frequency": 50,
            "cross_investigation": 100,
            "sentiment": 60,
            "freshness": 100
          }
        }
      }
    }
  ],
  "edges": [...],
  "insights": {
    "top_entities": [...],
    "anomalies": [...],
    "stats": {
      "total_nodes": 45,
      "avg_priority": 42
    }
  }
}
```

### Update Entity Metadata
```http
PATCH /api/entities/:entityType/:entityValue
Authorization: Bearer <token>
Content-Type: application/json

{
  "notes": "Confirmed threat actor",
  "tags": ["watchlist", "confirmed"],
  "pinned": true,
  "pinned_position": { "x": 100, "y": 200 }
}
```

---

## Reports

### Generate PDF Report
```http
POST /api/report/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "investigation_id": "uuid",
  "graph_image": "data:image/png;base64,..."
}
```

**Response:** `application/pdf` binary

---

## Search

### Full-Text Search
```http
GET /api/search?q=example
Authorization: Bearer <token>
```

---

## Error Responses

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": "Additional info"
}
```

| Code | Status | Description |
|------|--------|-------------|
| UNAUTHORIZED | 401 | Invalid/missing token |
| NOT_FOUND | 404 | Resource not found |
| INTERNAL_ERROR | 500 | Server error |
