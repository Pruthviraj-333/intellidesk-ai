# API Spec — Tickets, Incidents & Problems

---

## TICKET ENDPOINTS

---

### POST /tickets
**Description:** Create a new support ticket. AI classification runs automatically.  
**Auth Required:** Yes  
**Roles:** All

**Request Body:**
```json
{
  "title": "Cannot access VPN from home",
  "description": "Since yesterday I am unable to connect to the company VPN. I get error code 800. I have tried restarting but issue persists.",
  "category": "Network",
  "priority": "high",
  "department_id": 3,
  "project_id": null
}
```

**Notes:**
- `category`, `priority`, `department_id` are optional — AI fills missing values automatically
- Ticket ID auto-generated: `TKT-YYYYMMDD-XXXX`
- SLA deadlines set automatically based on priority

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": 101,
    "ticket_number": "TKT-20260706-0042",
    "title": "Cannot access VPN from home",
    "description": "Since yesterday I am unable...",
    "status": "new",
    "priority": "high",
    "category": "Network",
    "requester": { "id": 42, "name": "John Doe", "email": "john.doe@company.com", "avatar_url": null },
    "assignee": null,
    "department": { "id": 3, "name": "IT Support" },
    "project": null,
    "sla_response_deadline": "2026-07-06T01:00:00Z",
    "sla_resolution_deadline": "2026-07-06T08:00:00Z",
    "sla_response_breached": false,
    "sla_resolution_breached": false,
    "ai_confidence": 0.92,
    "ai_category_suggestion": "Network",
    "ai_priority_suggestion": "high",
    "comment_count": 0,
    "created_at": "2026-07-06T00:00:00Z",
    "updated_at": "2026-07-06T00:00:00Z"
  }
}
```

---

### GET /tickets
**Description:** List tickets with filtering, sorting, and pagination.  
**Auth Required:** Yes  
**Roles:** All (scoped by role — employees see only their own tickets)

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | new\|open\|in_progress\|pending\|escalated\|on_hold\|resolved\|closed |
| priority | string | critical\|high\|medium\|low |
| category | string | Hardware\|Software\|Network\|... |
| department_id | int | Filter by department |
| assignee_id | int | Filter by assignee |
| requester_id | int | Filter by requester |
| sla_breached | bool | Filter SLA-breached tickets |
| from_date | date | Created after (YYYY-MM-DD) |
| to_date | date | Created before (YYYY-MM-DD) |
| search | string | Full-text search on title and description |
| page | int | Default: 1 |
| per_page | int | Default: 20, max: 100 |
| sort_by | string | created_at\|updated_at\|priority\|sla_resolution_deadline |
| order | string | asc\|desc |

**Success Response `200`:**
```json
{
  "status": "success",
  "data": [ { "id": 101, "ticket_number": "TKT-20260706-0042", "..." } ],
  "pagination": { "page": 1, "per_page": 20, "total_items": 340, "total_pages": 17, "has_next": true, "has_prev": false }
}
```

---

### GET /tickets/:id
**Description:** Get complete ticket detail including comments, timeline, and AI metadata.  
**Auth Required:** Yes  
**Roles:** All (employees can only access their own tickets)

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "id": 101,
    "ticket_number": "TKT-20260706-0042",
    "title": "Cannot access VPN from home",
    "description": "Since yesterday...",
    "status": "in_progress",
    "priority": "high",
    "category": "Network",
    "requester": { "id": 42, "name": "John Doe", "avatar_url": null },
    "assignee": { "id": 15, "name": "Jane Smith", "avatar_url": "https://..." },
    "department": { "id": 3, "name": "IT Support" },
    "sla_response_deadline": "2026-07-06T01:00:00Z",
    "sla_resolution_deadline": "2026-07-06T08:00:00Z",
    "sla_response_breached": false,
    "sla_resolution_breached": false,
    "first_responded_at": "2026-07-06T00:45:00Z",
    "ai_confidence": 0.92,
    "ai_metadata": { "classification_reasoning": "VPN connectivity..." },
    "comment_count": 3,
    "comments": [
      {
        "id": 201,
        "author": { "id": 15, "name": "Jane Smith" },
        "body": "Hi John, can you please provide the exact error message?",
        "is_internal": false,
        "created_at": "2026-07-06T00:45:00Z"
      }
    ],
    "attachments": [],
    "created_at": "2026-07-06T00:00:00Z",
    "updated_at": "2026-07-06T00:45:00Z"
  }
}
```

---

### PUT /tickets/:id
**Description:** Update ticket fields or change status.  
**Auth Required:** Yes  
**Roles:** Agent (own assigned), Manager (department), Admin, Super Admin

**Request Body:** *(all fields optional — send only what changes)*
```json
{
  "status": "in_progress",
  "priority": "critical",
  "assignee_id": 15,
  "department_id": 3,
  "category": "Network",
  "resolution_notes": "Reset VPN client credentials and re-enrolled certificate."
}
```

**Business Rules:**
- Status transitions must follow allowed flow (see SRS §TKT-FR-004)
- Changing status to `resolved` requires `resolution_notes`
- Changing priority logs an audit entry with before/after values
- Reassignment triggers notification to new assignee

**Success Response `200`:** *(Full ticket object)*

---

### DELETE /tickets/:id
**Description:** Soft-delete a ticket.  
**Auth Required:** Yes  
**Roles:** Admin, Super Admin

**Success Response `204`:** *(No content)*

---

### POST /tickets/:id/comments
**Description:** Add a comment or internal note to a ticket.  
**Auth Required:** Yes  
**Roles:** All (is_internal only available to Agent+)

**Request Body:**
```json
{
  "body": "I have reset the VPN client. Please try connecting again and let me know.",
  "is_internal": false
}
```

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": 205,
    "ticket_id": 101,
    "author": { "id": 15, "name": "Jane Smith" },
    "body": "I have reset the VPN client...",
    "is_internal": false,
    "created_at": "2026-07-06T01:00:00Z"
  }
}
```

---

### POST /tickets/:id/attachments
**Description:** Upload an attachment to a ticket.  
**Auth Required:** Yes  
**Content-Type:** `multipart/form-data`

**Form Fields:**
| Field | Type | Rules |
|-------|------|-------|
| file | file | Required, PDF/DOCX/PNG/JPG/TXT, max 10MB |

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": 10,
    "file_name": "vpn_error_screenshot.png",
    "file_url": "https://res.cloudinary.com/...",
    "file_size": 245678,
    "file_type": "png",
    "created_at": "2026-07-06T00:05:00Z"
  }
}
```

---

### GET /tickets/:id/similar
**Description:** Find similar tickets using vector similarity search.  
**Auth Required:** Yes  
**Roles:** Agent, Manager, Admin, Super Admin

**Success Response `200`:**
```json
{
  "status": "success",
  "data": [
    {
      "ticket_id": 88,
      "ticket_number": "TKT-20260615-0019",
      "title": "VPN connection failing for remote users",
      "status": "resolved",
      "similarity_score": 0.94,
      "resolution_summary": "Renewed VPN certificates and updated DNS settings."
    },
    {
      "ticket_id": 73,
      "ticket_number": "TKT-20260601-0007",
      "title": "Unable to connect to VPN after password change",
      "status": "resolved",
      "similarity_score": 0.87,
      "resolution_summary": "Synced AD password with VPN gateway."
    }
  ]
}
```

---

### PUT /tickets/:id/assign
**Description:** Assign or reassign a ticket.  
**Auth Required:** Yes  
**Roles:** Manager, Admin, Super Admin

**Request Body:**
```json
{ "assignee_id": 15 }
```

---

### POST /tickets/bulk-update
**Description:** Update multiple tickets at once (status, assignee, priority).  
**Auth Required:** Yes  
**Roles:** Manager, Admin, Super Admin

**Request Body:**
```json
{
  "ticket_ids": [101, 102, 103],
  "updates": { "status": "closed", "assignee_id": 15 }
}
```

---

## INCIDENT ENDPOINTS

---

### POST /incidents
**Description:** Create a new incident record.  
**Auth Required:** Yes  
**Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "title": "Production database unreachable",
  "description": "The primary PostgreSQL database is refusing connections since 23:00. All services affected.",
  "severity": "critical",
  "impact": "high",
  "affected_services": "All application services, API, frontend",
  "department_id": 2,
  "linked_ticket_ids": [101, 102]
}
```

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": 55,
    "incident_number": "INC-20260706-0003",
    "title": "Production database unreachable",
    "severity": "critical",
    "impact": "high",
    "status": "open",
    "affected_services": "All application services, API, frontend",
    "reporter": { "id": 15, "name": "Jane Smith" },
    "assignee": null,
    "department": { "id": 2, "name": "Infrastructure" },
    "linked_tickets": [
      { "ticket_id": 101, "ticket_number": "TKT-20260706-0042" }
    ],
    "timeline": [],
    "created_at": "2026-07-06T00:00:00Z"
  }
}
```

---

### GET /incidents
**Description:** List incidents.  
**Auth Required:** Yes  
**Roles:** Agent, Manager, Admin, Super Admin

**Query Parameters:** `status`, `severity`, `department_id`, `from_date`, `to_date`, `page`, `per_page`

---

### GET /incidents/:id
**Description:** Get incident detail with full timeline.  
**Auth Required:** Yes  
**Roles:** Agent, Manager, Admin, Super Admin

---

### PUT /incidents/:id
**Description:** Update incident fields or resolve.  
**Auth Required:** Yes  
**Roles:** Agent (assigned only), Manager, Admin, Super Admin

**Request Body:**
```json
{
  "status": "resolved",
  "resolution_notes": "Failover to replica DB. Primary restored after disk expansion.",
  "assignee_id": 10
}
```

---

### POST /incidents/:id/timeline
**Description:** Add a timeline entry to an incident.  
**Auth Required:** Yes  
**Roles:** Agent, Manager, Admin, Super Admin

**Request Body:**
```json
{
  "event_type": "update",
  "description": "Failover initiated to replica database. Monitoring in progress."
}
```

**Event Types:** `created` | `assigned` | `escalated` | `update` | `communication` | `resolved` | `postmortem`

---

## PROBLEM ENDPOINTS

---

### POST /problems
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

**Request Body:**
```json
{
  "title": "Recurring VPN authentication failures",
  "description": "Multiple incidents of VPN authentication failures traced to certificate renewal process.",
  "linked_incident_ids": [55, 48, 41]
}
```

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "id": 12,
    "problem_number": "PRB-20260706-0001",
    "title": "Recurring VPN authentication failures",
    "status": "open",
    "root_cause": null,
    "workaround": null,
    "resolution": null,
    "linked_incidents": [ { "id": 55, "incident_number": "INC-20260706-0003" } ],
    "owner": null,
    "created_at": "2026-07-06T00:00:00Z"
  }
}
```

---

### GET /problems
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

---

### GET /problems/:id
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

---

### PUT /problems/:id
**Description:** Update problem, add root cause, workaround, or resolution.  
**Auth Required:** Yes | **Roles:** Manager, Admin, Super Admin

**Request Body:**
```json
{
  "root_cause": "VPN certificate renewal automation script fails silently when AD connector is unreachable.",
  "workaround": "Manually renew certificates via admin portal if VPN auth fails.",
  "resolution": "Fixed AD connector retry logic. Added alerting for certificate expiry.",
  "status": "resolved"
}
```
