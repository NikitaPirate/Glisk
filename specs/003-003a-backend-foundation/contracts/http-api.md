# HTTP API Contract: Backend Foundation

**Feature**: 003a Backend Foundation
**API Version**: v1 (foundation)
**Base URL**: `http://localhost:8000` (development)

## Overview

This document defines the minimal HTTP API provided by the backend foundation. The foundation provides only a health check endpoint. Feature-specific endpoints (webhooks, admin operations) are defined in their respective specs (003b-003e).

## Authentication

**Foundation Phase**: No authentication required (health endpoint is public)

**Future Features**: Authentication will be added in 003e (Admin API) using API keys or JWT.

## Common Response Format

All JSON responses follow this structure:

```json
{
  "status": "success" | "error",
  "data": { ... },           // Present on success
  "error": {                 // Present on error
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

## Endpoints

### Health Check

**Endpoint**: `GET /health`

**Purpose**: Verify backend service is running and database connection is healthy

**Authentication**: None (public endpoint)

**Request**: No parameters

**Response** (200 OK):
```json
{
  "status": "healthy"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "error": {
    "code": "DATABASE_CONNECTION_FAILED",
    "message": "Unable to connect to database"
  }
}
```

**Behavior**:
- Returns `200 OK` if:
  - FastAPI application is running
  - Database connection pool has available connections
  - Simple query succeeds (e.g., `SELECT 1`)
- Returns `503 Service Unavailable` if:
  - Database connection fails
  - Connection pool exhausted (should never happen with 200 pool size)
- Response time should be <100ms (see SC-004)

**Implementation Notes**:
```python
@app.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        logger.error("health_check.failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": {
                    "code": "DATABASE_CONNECTION_FAILED",
                    "message": "Unable to connect to database"
                }
            }
        )
```

---

## Future Endpoints

These endpoints will be added in subsequent features:

### 003b: Event Detection
- `POST /webhooks/alchemy` - Receive blockchain events from Alchemy webhook

### 003e: Admin API
- `GET /admin/tokens` - List tokens by status
- `GET /admin/tokens/{id}` - Get token details
- `POST /admin/tokens/{id}/retry` - Retry failed token
- `GET /admin/stats` - System statistics
- `POST /admin/reveal` - Trigger manual reveal batch

---

## Error Codes

### Foundation Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `DATABASE_CONNECTION_FAILED` | 503 | Database connection unavailable |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

### Future Error Codes (003b-003e)

Additional error codes will be defined in feature-specific contract documents.

---

## CORS Configuration

**Development**: CORS enabled for `http://localhost:3000` (frontend dev server)

**Production**: CORS restricted to deployed frontend domain only

**Configuration**: Via environment variable `CORS_ORIGINS` (comma-separated list)

---

## Logging

All HTTP requests/responses are logged at INFO level with structured logging:

```json
{
  "event": "http.request",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 12.3,
  "timestamp": "2025-10-16T10:30:00Z"
}
```

Errors are logged at ERROR level with exception details.

---

## Rate Limiting

**Foundation Phase**: No rate limiting

**Future**: Rate limiting will be added in 003e if needed for admin API endpoints.

---

## OpenAPI Specification

FastAPI automatically generates OpenAPI documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

Auto-generated documentation includes:
- Endpoint descriptions
- Request/response schemas
- Example values

---

## Testing Contract

### Health Check Tests

**Test 1**: Successful health check
```python
async def test_health_check_success(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

**Test 2**: Database connection failure
```python
async def test_health_check_database_failure(client, broken_db):
    response = await client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert "DATABASE_CONNECTION_FAILED" in response.json()["error"]["code"]
```

**Test 3**: Response time under 100ms
```python
async def test_health_check_response_time(client):
    start = time.time()
    response = await client.get("/health")
    duration_ms = (time.time() - start) * 1000
    assert duration_ms < 100
    assert response.status_code == 200
```

---

## Versioning Strategy

**Current**: No versioning (foundation endpoints are stable)

**Future**: If breaking changes needed:
- Add `/v2/` prefix to new endpoints
- Maintain `/v1/` for backward compatibility
- Deprecate old versions after 1 season

---

## Client Examples

### Python (httpx)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8000/health")
    if response.status_code == 200:
        print("Backend is healthy")
    else:
        print(f"Backend unhealthy: {response.json()}")
```

### cURL
```bash
curl http://localhost:8000/health
```

### JavaScript (fetch)
```javascript
const response = await fetch('http://localhost:8000/health');
const data = await response.json();
console.log(data.status);
```

---

## Performance Requirements

| Endpoint | Target Latency | Measured At |
|----------|----------------|-------------|
| `/health` | <100ms p95 | Backend server |

Latency measured from request received to response sent (excludes network time).

---

## Deployment Considerations

### Health Check for Load Balancers

Load balancers (ALB, nginx) should use `/health` endpoint for:
- **Readiness probes**: Don't route traffic until healthy
- **Liveness probes**: Restart container if unhealthy for >30s

**Recommended Configuration** (Kubernetes example):
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
```

---

## Security Headers

**Foundation Phase**: Minimal security headers

**Headers Enabled**:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`

**Future** (003e): Add comprehensive security headers:
- `Content-Security-Policy`
- `Strict-Transport-Security` (HTTPS only)
- `X-XSS-Protection`

---

## Maintenance Mode

**Not Implemented in Foundation**

Future: Add `/health` response variant indicating maintenance mode:
```json
{
  "status": "maintenance",
  "message": "System under maintenance, check back in 10 minutes"
}
```
