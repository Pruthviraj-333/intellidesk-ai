# IntelliDesk AI — Complete API Reference

## Base URL
```
http://localhost:5000/api/v1
```

## Authentication
All protected endpoints require a JWT Bearer token:
```
Authorization: Bearer <access_token>
```

---

## Auth Endpoints (`/api/v1/auth`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/auth/register` | Register a new user | Public |
| POST | `/auth/login` | Login and get tokens | Public |
| POST | `/auth/refresh` | Refresh access token | Authenticated |
| POST | `/auth/logout` | Revoke access token | Authenticated |
| POST | `/auth/forgot-password` | Request password reset email | Public |
| POST | `/auth/reset-password` | Reset password with token | Public |
| GET  | `/auth/verify-email/:token` | Verify email address | Public |
| GET  | `/auth/me` | Get current user profile | Authenticated |

---

## User Endpoints (`/api/v1/users`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/users` | List all users (paginated) | Admin+ |
| GET | `/users/:id` | Get user by ID | Admin+ |
| PUT | `/users/:id` | Update user profile | Admin+ |
| PUT | `/users/:id/role` | Change user role | Admin+ |
| PUT | `/users/:id/status` | Activate/deactivate user | Admin+ |
| DELETE | `/users/:id` | Soft delete user | Super Admin |
| PUT | `/users/me` | Update own profile | Authenticated |
| PUT | `/users/me/password` | Change own password | Authenticated |

---

## Department Endpoints (`/api/v1/departments`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/departments` | List all departments | Authenticated |
| POST | `/departments` | Create department | Admin+ |
| PUT | `/departments/:id` | Update department | Admin+ |
| DELETE | `/departments/:id` | Delete department | Admin+ |

---

## Ticket Endpoints (`/api/v1/tickets`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/tickets/` | Create new ticket | Authenticated |
| GET | `/tickets/` | List tickets (role-scoped) | Authenticated |
| GET | `/tickets/:id` | Get ticket detail | Authenticated |
| PUT | `/tickets/:id` | Update ticket | Agent+, own |
| DELETE | `/tickets/:id` | Soft delete ticket | Admin+ |
| PUT | `/tickets/:id/assign` | Assign ticket to agent | Manager+ |
| PUT | `/tickets/bulk-update` | Bulk status/assign update | Manager+ |
| GET | `/tickets/:id/comments` | List ticket comments | Authenticated |
| POST | `/tickets/:id/comments` | Add comment | Authenticated |
| DELETE | `/tickets/:id/comments/:cid` | Delete comment | Admin+ |

---

## Incident Endpoints (`/api/v1/incidents`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/incidents/` | Create incident | Agent+ |
| GET | `/incidents/` | List incidents | Agent+ |
| GET | `/incidents/:id` | Get incident detail | Agent+ |
| PUT | `/incidents/:id` | Update incident | Agent+ |
| DELETE | `/incidents/:id` | Soft delete incident | Admin+ |
| POST | `/incidents/:id/timeline` | Add timeline entry | Agent+ |

## Problem Endpoints (`/api/v1/problems`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/problems/` | Create problem record | Manager+ |
| GET | `/problems/` | List problems | Manager+ |
| GET | `/problems/:id` | Get problem detail | Manager+ |
| PUT | `/problems/:id` | Update root cause/workaround | Manager+ |
| DELETE | `/problems/:id` | Soft delete | Admin+ |

---

## Notification Endpoints (`/api/v1/notifications`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/notifications/` | Get own notifications | Authenticated |
| PUT | `/notifications/:id/read` | Mark notification read | Authenticated |
| PUT | `/notifications/read-all` | Mark all read | Authenticated |

---

## Dashboard Endpoints (`/api/v1/dashboard`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/dashboard/summary` | Role-scoped KPI summary | Authenticated |
| GET | `/dashboard/ticket-trends` | 30-day ticket trend data | Manager+ |
| GET | `/dashboard/sla-compliance` | SLA compliance by priority | Manager+ |
| GET | `/dashboard/agent-performance` | Agent resolution stats | Manager+ |

---

## Knowledge Base (`/api/v1/knowledge`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/knowledge/articles` | Create draft article | Agent+ |
| GET | `/knowledge/articles` | List articles (role-scoped) | Authenticated |
| GET | `/knowledge/articles/:slug` | Get article by slug | Authenticated |
| PUT | `/knowledge/articles/:id` | Update article | Agent+ |
| DELETE | `/knowledge/articles/:id` | Soft delete | Admin+ |
| PUT | `/knowledge/articles/:id/publish` | Publish & index in ChromaDB | Manager+ |
| POST | `/knowledge/articles/:id/vote` | Vote helpful/not-helpful | Authenticated |
| GET | `/knowledge/search?q=...` | Semantic search (RAG) | Authenticated |
| GET | `/knowledge/categories` | List categories | Authenticated |
| POST | `/knowledge/categories` | Create category | Admin+ |
| GET | `/knowledge/tags` | Popular tags autocomplete | Authenticated |

---

## Document Management (`/api/v1/documents`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/documents/` | Upload document (multipart) | Agent+ |
| GET | `/documents/` | List documents (role-scoped) | Agent+ |
| GET | `/documents/:id` | Get document + processing status | Agent+ |
| POST | `/documents/:id/reprocess` | Re-queue failed document | Manager+ |
| DELETE | `/documents/:id` | Soft delete | Admin+ |

---

## AI Assistant (`/api/v1/ai`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/ai/chat` | Send message to AI (RAG+LLM) | Authenticated |
| GET | `/ai/sessions` | List conversation sessions | Authenticated |
| GET | `/ai/sessions/:uuid` | Get session message history | Authenticated |
| DELETE | `/ai/sessions/:uuid` | Delete session | Authenticated |
| POST | `/ai/tickets/:id/classify` | AI classify ticket | Agent+ |
| GET | `/ai/tickets/:id/classification` | Get AI classification result | Agent+ |
| POST | `/ai/tickets/:id/classification/feedback` | Submit feedback | Agent+ |
| POST | `/ai/tickets/:id/suggest-response` | Generate agent reply draft | Agent+ |
| POST | `/ai/tickets/:id/summarize` | Summarize comment thread | Agent+ |
| POST | `/ai/resolution-guide` | Get AI troubleshooting steps | Authenticated |

---

## Analytics (`/api/v1/analytics`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/analytics/summary` | Platform KPI totals | Manager+ |
| GET | `/analytics/trends?days=30` | Daily trend chart data | Manager+ |
| GET | `/analytics/sla-compliance` | SLA rates by priority | Manager+ |
| GET | `/analytics/ticket-volume` | Tickets by category | Manager+ |
| GET | `/analytics/agent-leaderboard` | Top agents by resolution | Manager+ |
| GET | `/analytics/heatmap?days=90` | Ticket heatmap (hour×day) | Manager+ |

---

## Reports (`/api/v1/reports`)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/reports/available` | List downloadable report types | Manager+ |
| GET | `/reports/tickets/pdf` | Download PDF report | Manager+ |
| GET | `/reports/tickets/csv` | Download CSV export | Manager+ |
| GET | `/reports/analytics/excel` | Download Excel workbook | Manager+ |

---

## Health Check

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/health` | App health + DB/Redis status | Public |

---

## Standard Response Envelope

### Success
```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-06T08:00:00Z"
  }
}
```

### Paginated
```json
{
  "status": "success",
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 482,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  },
  "meta": { ... }
}
```

### Error
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed.",
    "details": [
      { "field": "priority", "message": "Must be one of: critical, high, medium, low." }
    ]
  },
  "meta": { ... }
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — successful GET/PUT |
| 201 | Created — successful POST |
| 204 | No Content — successful DELETE |
| 400 | Bad Request — validation error |
| 401 | Unauthorized — missing/invalid token |
| 403 | Forbidden — insufficient role |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — duplicate resource (email, slug) |
| 422 | Unprocessable — business logic error |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error |
