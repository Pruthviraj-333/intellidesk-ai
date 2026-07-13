# 4. Non-Functional Requirements

## 4.1 Performance Requirements

| ID         | Requirement                                                            | Target                    |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-PERF-001 | API response time for CRUD operations                               | ≤ 200ms (p95)            |
| NFR-PERF-002 | API response time for search operations                             | ≤ 500ms (p95)            |
| NFR-PERF-003 | AI chat response (first token)                                      | ≤ 2 seconds              |
| NFR-PERF-004 | AI ticket classification                                            | ≤ 3 seconds              |
| NFR-PERF-005 | RAG query response                                                  | ≤ 5 seconds              |
| NFR-PERF-006 | Dashboard page load                                                 | ≤ 3 seconds              |
| NFR-PERF-007 | Document processing (per MB)                                        | ≤ 30 seconds             |
| NFR-PERF-008 | Concurrent users supported                                          | 100 (free tier target)   |
| NFR-PERF-009 | Database query response                                             | ≤ 100ms (p95)            |
| NFR-PERF-010 | Frontend initial page load (Time to Interactive)                    | ≤ 4 seconds              |

## 4.2 Security Requirements

| ID         | Requirement                                                            | Standard/Reference        |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-SEC-001 | All passwords hashed using bcrypt with cost factor ≥ 12              | OWASP Password Storage    |
| NFR-SEC-002 | JWT access tokens expire within 15 minutes                           | OWASP Session Management  |
| NFR-SEC-003 | All API endpoints require authentication except public routes        | OWASP Broken Access Control |
| NFR-SEC-004 | Input validation on all user-supplied data                           | OWASP Injection           |
| NFR-SEC-005 | Output encoding to prevent XSS                                      | OWASP XSS Prevention      |
| NFR-SEC-006 | CSRF protection on all state-changing operations                     | OWASP CSRF Prevention     |
| NFR-SEC-007 | SQL injection prevention via parameterized queries (SQLAlchemy ORM)  | OWASP Injection           |
| NFR-SEC-008 | Secure HTTP headers (HSTS, X-Frame-Options, CSP, etc.)              | OWASP Secure Headers      |
| NFR-SEC-009 | File upload validation (type, size, content inspection)              | OWASP File Upload         |
| NFR-SEC-010 | Rate limiting on authentication endpoints (5 req/min per IP)        | OWASP Brute Force         |
| NFR-SEC-011 | Rate limiting on AI endpoints (20 req/min per user)                 | Resource Protection       |
| NFR-SEC-012 | All secrets stored in environment variables                          | 12-Factor App             |
| NFR-SEC-013 | Audit logging of all authentication and authorization events        | Compliance                |
| NFR-SEC-014 | HTTPS enforcement in production                                     | OWASP Transport Security  |
| NFR-SEC-015 | Dependency vulnerability scanning in CI/CD                          | Supply Chain Security     |

## 4.3 Reliability & Availability

| ID         | Requirement                                                            | Target                    |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-REL-001 | Application uptime target                                            | 99.5% (free tier)        |
| NFR-REL-002 | Graceful degradation when AI provider unavailable                   | Ticket ops continue; AI features show "unavailable" state |
| NFR-REL-003 | Database connection pooling and retry logic                         | 3 retries with exponential backoff |
| NFR-REL-004 | Background job retry on failure                                     | 3 retries with exponential backoff |
| NFR-REL-005 | Health check endpoints for all critical services                    | HTTP 200 / 503 responses  |
| NFR-REL-006 | Data backup strategy                                                | Managed by cloud provider (Neon) |

## 4.4 Scalability

| ID         | Requirement                                                            | Target                    |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-SCA-001 | Horizontal scalability via containerization                         | Docker Compose multi-instance |
| NFR-SCA-002 | Stateless API design for load balancing                             | No server-side sessions    |
| NFR-SCA-003 | Database connection pooling                                         | Max 20 connections (free tier) |
| NFR-SCA-004 | Celery worker scalability                                           | Independent worker scaling |
| NFR-SCA-005 | CDN-ready frontend static assets                                    | Vercel edge deployment     |

## 4.5 Maintainability

| ID         | Requirement                                                            | Target                    |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-MNT-001 | Code coverage by unit tests                                         | ≥ 70%                    |
| NFR-MNT-002 | Clean Architecture adherence                                        | Repository → Service → Controller layers |
| NFR-MNT-003 | API versioning strategy                                             | URL path versioning (`/api/v1/`) |
| NFR-MNT-004 | Database migrations via Alembic                                     | All schema changes tracked |
| NFR-MNT-005 | Comprehensive API documentation                                    | OpenAPI 3.1 / Swagger UI  |
| NFR-MNT-006 | Structured logging with correlation IDs                             | JSON-formatted logs       |
| NFR-MNT-007 | Environment-based configuration                                    | Dev, Staging, Production profiles |
| NFR-MNT-008 | Code style enforcement                                              | PEP 8, ESLint, Prettier   |

## 4.6 Usability

| ID         | Requirement                                                            | Target                    |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-USE-001 | Responsive design                                                   | Desktop, tablet, mobile   |
| NFR-USE-002 | Dark mode and light mode support                                    | User preference toggle    |
| NFR-USE-003 | Keyboard navigation support                                        | All primary workflows     |
| NFR-USE-004 | Loading states and skeleton screens                                 | All data-fetching views   |
| NFR-USE-005 | Error messages user-friendly and actionable                        | No technical stack traces  |
| NFR-USE-006 | Consistent design system                                            | Shared component library   |
| NFR-USE-007 | Maximum 3 clicks to reach any primary function                     | Navigation efficiency     |

## 4.7 Compatibility

| ID         | Requirement                                                            | Target                    |
|------------|------------------------------------------------------------------------|---------------------------|
| NFR-CMP-001 | Browser support                                                     | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+ |
| NFR-CMP-002 | Docker support                                                      | Docker 24+, Docker Compose 2.20+ |
| NFR-CMP-003 | Python version                                                      | 3.11+                     |
| NFR-CMP-004 | Node.js version                                                     | 18 LTS+                   |
| NFR-CMP-005 | PostgreSQL version                                                  | 16+                       |

---

# 5. External Interface Requirements

## 5.1 User Interfaces

### 5.1.1 General UI Requirements

- Modern single-page application (SPA) with React
- Responsive layout (mobile-first approach)
- Dark mode / Light mode toggle with system preference detection
- Consistent design system using TailwindCSS utility framework
- Loading skeletons for all data-driven components
- Toast notifications for action feedback
- Modal confirmations for destructive actions
- Breadcrumb navigation for hierarchical views

### 5.1.2 Key Screens

| Screen                  | Primary Users              | Key Elements                                    |
|-------------------------|----------------------------|-------------------------------------------------|
| Login / Register        | All                        | Form, social-style layout, branding             |
| Main Dashboard          | Agent, Manager, Admin      | KPI cards, charts, quick actions                |
| Employee Dashboard      | Employee                   | My tickets, quick submit, AI chat               |
| Ticket List             | Agent, Manager, Admin      | Data table, filters, bulk actions               |
| Ticket Detail           | All                        | Info panel, timeline, comments, AI sidebar      |
| Create Ticket           | All                        | Form with AI-assisted fields                    |
| Incident List/Detail    | Agent, Manager, Admin      | Incident board, timeline, linked tickets        |
| Knowledge Base          | All                        | Article cards, search, categories               |
| AI Chat                 | All                        | Chat interface, citations, suggested questions  |
| Analytics               | Manager, Admin             | Interactive charts, date filters, export        |
| Admin Panel             | Admin, Super Admin         | Settings, users, roles, system config           |
| User Profile            | All                        | Profile info, preferences, activity             |
| Document Management     | Agent, Manager, Admin      | Upload, list, processing status                 |

## 5.2 Software Interfaces

### 5.2.1 Database Interface

| Parameter        | Value                                                        |
|------------------|--------------------------------------------------------------|
| System           | PostgreSQL 16+                                               |
| Protocol         | TCP/IP (port 5432)                                           |
| ORM              | SQLAlchemy 2.x                                               |
| Migrations       | Alembic                                                      |
| Connection Pool  | SQLAlchemy pool (max 20)                                     |

### 5.2.2 Cache & Message Broker Interface

| Parameter        | Value                                                        |
|------------------|--------------------------------------------------------------|
| System           | Redis 7+                                                     |
| Protocol         | TCP/IP (port 6379)                                           |
| Usage            | Session cache, rate limiting, Celery broker, result backend  |

### 5.2.3 Vector Database Interface

| Parameter        | Value                                                        |
|------------------|--------------------------------------------------------------|
| System           | ChromaDB                                                     |
| Mode             | Persistent (local storage or server mode)                    |
| Embedding Model  | sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)     |

### 5.2.4 LLM API Interface

| Parameter        | Value                                                        |
|------------------|--------------------------------------------------------------|
| Provider         | Groq                                                         |
| Protocol         | HTTPS REST API                                               |
| Auth             | API Key (Bearer token)                                       |
| Primary Model    | llama-3.3-70b-versatile                                      |
| Fallback Models  | llama-3.1-8b-instant, gemma2-9b-it                          |
| Rate Limits      | Free tier: ~30 req/min, 14,400 req/day                      |

### 5.2.5 Object Storage Interface

| Parameter        | Value                                                        |
|------------------|--------------------------------------------------------------|
| Provider         | Cloudinary                                                   |
| Protocol         | HTTPS REST API                                               |
| Auth             | API Key + Secret                                             |
| Free Tier        | 25 credits/month                                             |
| Fallback         | Local filesystem (development)                               |

## 5.3 API Interface

### 5.3.1 REST API Standards

| Aspect           | Standard                                                     |
|------------------|--------------------------------------------------------------|
| Base URL         | `/api/v1/`                                                   |
| Content Type     | `application/json`                                           |
| Authentication   | `Authorization: Bearer <JWT>`                                |
| Pagination       | `?page=1&per_page=20`                                        |
| Filtering        | `?status=open&priority=high`                                 |
| Sorting          | `?sort_by=created_at&order=desc`                             |
| Error Format     | `{ "error": { "code": "...", "message": "...", "details": [...] } }` |

### 5.3.2 API Endpoint Summary

| Resource        | Endpoints                                                     |
|-----------------|---------------------------------------------------------------|
| Auth            | POST /register, POST /login, POST /refresh, POST /logout, POST /forgot-password, POST /reset-password, POST /verify-email |
| Users           | GET /users, GET /users/:id, PUT /users/:id, DELETE /users/:id, GET /users/me, PUT /users/me |
| Tickets         | GET /tickets, POST /tickets, GET /tickets/:id, PUT /tickets/:id, DELETE /tickets/:id, POST /tickets/:id/comments, GET /tickets/:id/similar |
| Incidents       | GET /incidents, POST /incidents, GET /incidents/:id, PUT /incidents/:id, POST /incidents/:id/timeline |
| Problems        | GET /problems, POST /problems, GET /problems/:id, PUT /problems/:id |
| Knowledge Base  | GET /articles, POST /articles, GET /articles/:id, PUT /articles/:id, DELETE /articles/:id, GET /articles/search |
| AI              | POST /ai/chat, POST /ai/classify, POST /ai/summarize, POST /ai/suggest-reply, POST /ai/generate-email |
| Documents       | GET /documents, POST /documents/upload, GET /documents/:id, DELETE /documents/:id, POST /documents/search |
| Analytics       | GET /analytics/dashboard, GET /analytics/trends, GET /analytics/sla, GET /analytics/department |
| Reports         | GET /reports, POST /reports/generate, GET /reports/:id/download |
| Departments     | GET /departments, POST /departments, GET /departments/:id, PUT /departments/:id |
| Projects        | GET /projects, POST /projects, GET /projects/:id, PUT /projects/:id |
| Notifications   | GET /notifications, PUT /notifications/:id/read, PUT /notifications/read-all |
| Admin           | GET /admin/settings, PUT /admin/settings, GET /admin/audit-logs, GET /admin/system-monitor |
| Health          | GET /health, GET /health/detailed                            |

### 5.3.3 Standard Response Envelope

**Success (Single Resource):**
```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

**Success (Collection):**
```json
{
  "status": "success",
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 156,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

**Error:**
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### 5.3.4 HTTP Status Codes

| Code | Usage                                                           |
|------|-----------------------------------------------------------------|
| 200  | Successful GET, PUT                                             |
| 201  | Successful POST (resource created)                              |
| 204  | Successful DELETE (no content)                                  |
| 400  | Bad request / validation error                                  |
| 401  | Unauthorized (invalid/missing token)                            |
| 403  | Forbidden (insufficient permissions)                            |
| 404  | Resource not found                                              |
| 409  | Conflict (duplicate resource)                                   |
| 422  | Unprocessable entity (semantic validation)                      |
| 429  | Rate limit exceeded                                             |
| 500  | Internal server error                                           |
| 503  | Service unavailable (dependency down)                           |
