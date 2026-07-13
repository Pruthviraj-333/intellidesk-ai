# API Spec — Knowledge Base, Documents, AI & Analytics

---

## KNOWLEDGE BASE ENDPOINTS

---

### POST /articles
**Description:** Create a new knowledge base article.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "title": "How to Reset VPN Client Credentials",
  "content": "## Overview\n\nThis article explains how to reset your VPN credentials...\n\n## Steps\n1. Open the VPN client\n2. Click 'Forgot Password'...",
  "category_id": 5,
  "tags": ["vpn", "network", "credentials", "reset"],
  "status": "published"
}
```

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": 30,
    "uuid": "...",
    "slug": "how-to-reset-vpn-client-credentials",
    "title": "How to Reset VPN Client Credentials",
    "content": "## Overview...",
    "status": "published",
    "version": 1,
    "category": { "id": 5, "name": "Network" },
    "tags": ["vpn", "network", "credentials", "reset"],
    "author": { "id": 15, "name": "Jane Smith" },
    "view_count": 0,
    "helpful_count": 0,
    "published_at": "2026-07-06T00:00:00Z",
    "created_at": "2026-07-06T00:00:00Z"
  }
}
```

---

### GET /articles
**Description:** List knowledge base articles.  
**Auth Required:** Yes | **Roles:** All

**Query Parameters:** `status`, `category_id`, `tag`, `search`, `author_id`, `page`, `per_page`, `sort_by`, `order`

---

### GET /articles/:id
**Description:** Get a single article. Increments view_count.  
**Auth Required:** Yes | **Roles:** All

---

### PUT /articles/:id
**Description:** Update an article. Creates a new version entry.  
**Auth Required:** Yes | **Roles:** Author, Manager, Admin, Super Admin

---

### DELETE /articles/:id
**Description:** Soft-delete an article.  
**Auth Required:** Yes | **Roles:** Admin, Super Admin

---

### GET /articles/search
**Description:** Full-text + semantic search across articles.  
**Auth Required:** Yes | **Roles:** All

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| q | string | Required. Search query |
| mode | string | `keyword` \| `semantic` \| `hybrid` (default: hybrid) |
| category_id | int | Scope to category |
| limit | int | Max results (default: 10) |

**Success Response `200`:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 30,
      "slug": "how-to-reset-vpn-client-credentials",
      "title": "How to Reset VPN Client Credentials",
      "excerpt": "This article explains how to reset your VPN credentials using the admin portal...",
      "category": { "id": 5, "name": "Network" },
      "tags": ["vpn", "network"],
      "relevance_score": 0.95,
      "view_count": 142,
      "published_at": "2026-07-06T00:00:00Z"
    }
  ]
}
```

---

### POST /articles/:id/helpful
**Description:** Mark an article as helpful (one per user).  
**Auth Required:** Yes | **Roles:** All

---

### GET /article-categories
**Description:** List all article categories.  
**Auth Required:** Yes | **Roles:** All

---

## DOCUMENT ENDPOINTS

---

### POST /documents/upload
**Description:** Upload a document for RAG processing.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin  
**Content-Type:** `multipart/form-data`

**Form Fields:**
| Field | Type | Rules |
|-------|------|-------|
| file | file | Required, PDF/DOCX/TXT/MD, max 25MB |
| department_id | int | Optional — scope document to department |
| description | string | Optional, max 500 chars |

**Success Response `202`:** *(Accepted — async processing begins)*
```json
{
  "status": "success",
  "data": {
    "id": 8,
    "uuid": "...",
    "file_name": "it-security-policy-2026.pdf",
    "original_name": "IT Security Policy 2026.pdf",
    "file_type": "pdf",
    "file_size": 2457600,
    "processing_status": "pending",
    "chunk_count": 0,
    "uploader": { "id": 15, "name": "Jane Smith" },
    "created_at": "2026-07-06T00:00:00Z"
  }
}
```

**Processing Status Values:** `pending` → `processing` → `processed` | `failed`

---

### GET /documents
**Description:** List uploaded documents.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Query Parameters:** `processing_status`, `file_type`, `department_id`, `page`, `per_page`

---

### GET /documents/:id
**Description:** Get document detail including processing status and chunk count.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

---

### DELETE /documents/:id
**Description:** Delete document and its vector embeddings from ChromaDB.  
**Auth Required:** Yes | **Roles:** Admin, Super Admin

---

### POST /documents/search
**Description:** Semantic search across all processed documents.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "query": "What is the password policy for employee accounts?",
  "top_k": 5,
  "department_id": null,
  "min_score": 0.5
}
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "query": "What is the password policy for employee accounts?",
    "results": [
      {
        "chunk_text": "All employee passwords must be at least 12 characters long, contain uppercase and lowercase letters, numbers, and special characters. Passwords must be rotated every 90 days...",
        "document": {
          "id": 8,
          "file_name": "it-security-policy-2026.pdf",
          "file_type": "pdf"
        },
        "page_num": 14,
        "similarity_score": 0.91,
        "confidence": "high"
      }
    ],
    "total_results": 3
  }
}
```

---

## AI ENDPOINTS

---

### POST /ai/chat
**Description:** Send a message to the AI assistant. Returns streaming SSE response.  
**Auth Required:** Yes | **Roles:** All  
**Rate Limit:** 20 req/min per user

**Request Body:**
```json
{
  "message": "How do I reset my VPN password?",
  "conversation_id": null,
  "ticket_id": null,
  "stream": true
}
```

**Success Response (streaming) `200`:**
```
Content-Type: text/event-stream

data: {"type": "token", "content": "To "}
data: {"type": "token", "content": "reset "}
data: {"type": "token", "content": "your VPN password... "}
data: {"type": "sources", "sources": [{"document": "IT Security Policy 2026.pdf", "page": 14, "score": 0.91}]}
data: {"type": "done", "conversation_id": "abc123", "message_id": 501, "confidence": 0.88}
```

**Success Response (non-streaming) `200`:**
```json
{
  "status": "success",
  "data": {
    "reply": "To reset your VPN password, follow these steps:\n\n1. Go to the IT Self-Service portal at https://itsupport.company.com\n2. Click 'Reset VPN Credentials'...",
    "conversation_id": "abc123",
    "message_id": 501,
    "sources": [
      {
        "document": "IT Security Policy 2026.pdf",
        "page": 14,
        "excerpt": "All employee passwords must be...",
        "score": 0.91
      }
    ],
    "confidence": 0.88,
    "tokens_used": 312
  }
}
```

---

### POST /ai/classify
**Description:** Classify a ticket using AI (category + priority + department routing).  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "title": "Cannot access VPN from home",
  "description": "Since yesterday I am unable to connect to the company VPN. Error code 800."
}
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "category": "Network",
    "category_confidence": 0.93,
    "priority": "high",
    "priority_confidence": 0.87,
    "priority_reasoning": "VPN connectivity is business-critical for remote work.",
    "department": { "id": 3, "name": "IT Support" },
    "department_confidence": 0.91,
    "suggested_tags": ["vpn", "remote-access", "connectivity"],
    "model_used": "llama-3.3-70b-versatile"
  }
}
```

---

### POST /ai/summarize
**Description:** Generate an AI summary of a ticket or incident.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "resource_type": "ticket",
  "resource_id": 101
}
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "summary": "User John Doe reported inability to connect to the company VPN from home since July 5. Error code 800 is returned. Agent Jane Smith is currently investigating. The issue appears to be related to expired VPN client certificates.",
    "key_issues": [
      "VPN connection failing with error 800",
      "Affects remote work capability",
      "Certificate expiry suspected"
    ],
    "action_items": [
      "Verify certificate expiry date",
      "Re-issue VPN client certificate",
      "Test connection after renewal"
    ],
    "sentiment": "neutral",
    "estimated_resolution": "2-4 hours",
    "tokens_used": 418
  }
}
```

---

### POST /ai/suggest-reply
**Description:** Generate suggested reply options for an agent.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "ticket_id": 101,
  "context": "User is frustrated. Issue with VPN since yesterday."
}
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "suggestions": [
      {
        "text": "Hi John,\n\nThank you for reaching out. I can see you're experiencing VPN connectivity issues with error code 800. I've checked your account and it appears your VPN certificate may have expired.\n\nI'm initiating a certificate renewal now. Please try connecting again in approximately 15 minutes. If the issue persists, please let me know.\n\nBest regards,\nIT Support Team",
        "tone": "professional"
      },
      {
        "text": "Hi John,\n\nThanks for your patience. I'm looking into the VPN error 800 issue. I'll have an update for you within the next 30 minutes.\n\nRegards,\nIT Support",
        "tone": "concise"
      }
    ],
    "tokens_used": 285
  }
}
```

---

### POST /ai/generate-email
**Description:** Generate a professional email related to a ticket or incident.  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "resource_type": "ticket",
  "resource_id": 101,
  "email_type": "status_update",
  "recipient_name": "John Doe",
  "additional_context": "Certificate has been renewed."
}
```

**Email Types:** `status_update` | `escalation_notice` | `resolution_notification` | `follow_up` | `sla_warning`

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "subject": "[TKT-20260706-0042] VPN Access Issue — Resolved",
    "body": "Dear John,\n\nWe're pleased to inform you that your VPN access issue (Ticket #TKT-20260706-0042) has been resolved...",
    "tokens_used": 198
  }
}
```

---

### POST /ai/extract-actions
**Description:** Extract action items from text (ticket conversation or incident timeline).  
**Auth Required:** Yes | **Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "text": "Jane: I'll renew the certificate today. Bob: And I'll update the VPN documentation. Jane: Mark, can you schedule a review for Friday?",
  "context_type": "ticket_conversation"
}
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "action_items": [
      { "action": "Renew VPN certificate", "assignee_hint": "Jane", "deadline_hint": "today", "status": "pending" },
      { "action": "Update VPN documentation", "assignee_hint": "Bob", "deadline_hint": null, "status": "pending" },
      { "action": "Schedule documentation review", "assignee_hint": "Mark", "deadline_hint": "Friday", "status": "pending" }
    ],
    "tokens_used": 156
  }
}
```

---

## ANALYTICS ENDPOINTS

---

### GET /analytics/dashboard
**Description:** Get all dashboard KPI data.  
**Auth Required:** Yes | **Roles:** Agent (limited), Manager, Admin, Super Admin

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| department_id | int | Scope to department (Manager scoped by default) |
| from_date | date | Date range start (default: 30 days ago) |
| to_date | date | Date range end (default: today) |

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "kpis": {
      "open_tickets": 87,
      "resolved_today": 23,
      "avg_resolution_hours": 6.4,
      "sla_compliance_rate": 94.2,
      "active_incidents": 2,
      "overdue_tickets": 5,
      "pending_approvals": 12,
      "total_tickets_period": 340
    },
    "tickets_by_status": {
      "new": 15, "open": 32, "in_progress": 40, "pending": 12,
      "escalated": 3, "on_hold": 5, "resolved": 180, "closed": 53
    },
    "tickets_by_priority": { "critical": 8, "high": 45, "medium": 178, "low": 109 },
    "tickets_by_category": { "Network": 95, "Software": 80, "Hardware": 65, "Access": 45, "Other": 55 },
    "daily_trend": [
      { "date": "2026-07-01", "created": 12, "resolved": 10 },
      { "date": "2026-07-02", "created": 8, "resolved": 11 }
    ],
    "top_agents": [
      { "agent": { "id": 15, "name": "Jane Smith" }, "resolved": 42, "avg_hours": 4.2, "csat": 4.8 }
    ],
    "department_performance": [
      { "department": "IT Support", "open": 30, "resolved": 120, "sla_compliance": 96.5, "avg_hours": 5.1 }
    ]
  }
}
```

---

### GET /analytics/sla
**Description:** SLA compliance breakdown.  
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

---

### GET /analytics/trends
**Description:** Historical trend data for charts.  
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

**Query Parameters:** `metric` (volume|resolution_time|sla|sentiment), `granularity` (day|week|month), `from_date`, `to_date`

---

### GET /analytics/heatmap
**Description:** Ticket volume by day-of-week × hour-of-day.  
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "heatmap": [
      { "day": "Monday", "hour": 9, "count": 24 },
      { "day": "Monday", "hour": 10, "count": 31 }
    ]
  }
}
```

---

### POST /reports/generate
**Description:** Generate and queue a report for download.  
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

**Request Body:**
```json
{
  "report_type": "monthly_summary",
  "format": "pdf",
  "from_date": "2026-06-01",
  "to_date": "2026-06-30",
  "department_id": null,
  "include_ai_narrative": true
}
```

**Report Types:** `daily_summary` | `weekly_summary` | `monthly_summary` | `sla_report` | `department_report` | `agent_performance` | `ai_usage`

**Success Response `202`:**
```json
{
  "status": "success",
  "data": {
    "report_id": "rep_abc123",
    "status": "queued",
    "estimated_completion": "2026-07-06T00:05:00Z"
  }
}
```

---

### GET /reports/:id/download
**Description:** Download a generated report file.  
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

**Success Response `200`:** *(Binary file stream — Content-Type: application/pdf or text/csv)*

---

## ADMIN ENDPOINTS

---

### GET /admin/audit-logs
**Auth Required:** Yes | **Roles:** Admin, Super Admin

**Query Parameters:** `user_id`, `action`, `resource_type`, `from_date`, `to_date`, `page`, `per_page`

**Success Response `200`:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 10001,
      "user": { "id": 15, "name": "Jane Smith" },
      "action": "ticket_status_changed",
      "resource_type": "ticket",
      "resource_id": 101,
      "old_values": { "status": "open" },
      "new_values": { "status": "in_progress" },
      "ip_address": "192.168.1.100",
      "created_at": "2026-07-06T00:45:00Z"
    }
  ],
  "pagination": { "page": 1, "per_page": 50, "total_items": 12453 }
}
```

---

### GET /admin/settings
**Auth Required:** Yes | **Roles:** Admin, Super Admin

---

### PUT /admin/settings
**Auth Required:** Yes | **Roles:** Super Admin

**Request Body:**
```json
{
  "org_name": "Acme Corporation",
  "timezone": "America/New_York",
  "default_sla_critical_response_minutes": 15,
  "default_sla_critical_resolution_hours": 4,
  "ai_model": "llama-3.3-70b-versatile",
  "email_notifications_enabled": true
}
```

---

### GET /health
**Auth Required:** No

**Success Response `200`:**
```json
{ "status": "healthy", "version": "1.0.0", "environment": "production" }
```

---

### GET /health/detailed
**Auth Required:** Yes | **Roles:** Admin, Super Admin

**Success Response `200`:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database":  { "status": "healthy", "latency_ms": 12 },
    "redis":     { "status": "healthy", "latency_ms": 2  },
    "chromadb":  { "status": "healthy", "latency_ms": 8  },
    "celery":    { "status": "healthy", "active_workers": 3 },
    "groq_api":  { "status": "healthy", "latency_ms": 245 }
  }
}
```

---

### GET /departments
**Auth Required:** Yes | **Roles:** All

### POST /departments
**Auth Required:** Yes | **Roles:** Admin, Super Admin

### PUT /departments/:id
**Auth Required:** Yes | **Roles:** Admin, Super Admin

### GET /notifications
**Auth Required:** Yes | **Roles:** All  
**Query Parameters:** `is_read`, `type`, `page`, `per_page`

### PUT /notifications/:id/read
**Auth Required:** Yes | **Roles:** All

### PUT /notifications/read-all
**Auth Required:** Yes | **Roles:** All

### GET /prompt-templates
**Auth Required:** Yes | **Roles:** Admin, Super Admin

### PUT /prompt-templates/:id
**Auth Required:** Yes | **Roles:** Admin, Super Admin
