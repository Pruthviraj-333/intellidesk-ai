# 3. Functional Requirements

## 3.1 Authentication & Authorization Module (AUTH)

### AUTH-FR-001: User Registration

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall allow new users to register with email, password, full name, and department. |
| Input        | Email, password, confirm password, full name, department (optional)         |
| Processing   | Validate input → Check email uniqueness → Hash password (bcrypt) → Create user record → Send verification email → Return JWT tokens |
| Output       | User account created with "pending_verification" status                     |
| Validation   | Email format (RFC 5322), password (min 8 chars, 1 upper, 1 lower, 1 digit, 1 special), name (2-100 chars) |

**Acceptance Criteria:**
- [ ] User receives a verification email within 60 seconds of registration
- [ ] Duplicate email returns HTTP 409 with descriptive error
- [ ] Password is stored as bcrypt hash with cost factor 12
- [ ] Registration creates audit log entry
- [ ] Default role assigned is "Employee"

### AUTH-FR-002: User Login

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall authenticate users via email/password and return JWT tokens.   |
| Input        | Email, password                                                             |
| Processing   | Validate credentials → Verify email status → Generate access token (15 min) + refresh token (7 days) → Log login event |
| Output       | Access token, refresh token, user profile data                              |

**Acceptance Criteria:**
- [ ] Failed login returns HTTP 401 (no detail on which field is wrong)
- [ ] Account locks after 5 consecutive failed attempts for 15 minutes
- [ ] Unverified accounts cannot log in (HTTP 403)
- [ ] Login event recorded in audit log with IP address and user agent

### AUTH-FR-003: Token Refresh

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall issue new access tokens using valid refresh tokens.            |
| Processing   | Validate refresh token → Check token blacklist → Generate new access token → Rotate refresh token |
| Output       | New access token, new refresh token                                         |

### AUTH-FR-004: Password Reset

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall allow users to reset passwords via email verification.         |
| Processing   | Validate email exists → Generate reset token (1 hour expiry) → Send reset email → Validate token → Update password → Invalidate all sessions |

### AUTH-FR-005: Email Verification

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall verify user email addresses via confirmation tokens.           |
| Processing   | Generate verification token → Send email → User clicks link → Validate token → Update user status to "active" |

### AUTH-FR-006: Role-Based Access Control

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall enforce role-based permissions on all protected endpoints.     |

**Permission Matrix:**

| Resource            | Super Admin | Admin | Manager | Agent | Employee |
|---------------------|:-----------:|:-----:|:-------:|:-----:|:--------:|
| System Settings     | CRUD        | R     | —       | —     | —        |
| User Management     | CRUD        | CRUD  | R       | —     | —        |
| Role Management     | CRUD        | R     | —       | —     | —        |
| All Tickets         | CRUD        | CRUD  | CRUD*   | CRUD* | CR*      |
| Own Tickets         | CRUD        | CRUD  | CRUD    | CRUD  | CR       |
| Incidents           | CRUD        | CRUD  | CRUD    | CRUD  | R*       |
| Problems            | CRUD        | CRUD  | CRUD    | R     | —        |
| Knowledge Base      | CRUD        | CRUD  | CRUD    | CRUD  | R        |
| Documents           | CRUD        | CRUD  | CRUD    | R     | R*       |
| Reports             | CRUD        | CRUD  | R       | R*    | —        |
| Analytics Dashboard | CRUD        | R     | R       | R*    | —        |
| AI Assistant        | Full        | Full  | Full    | Full  | Limited  |
| Audit Logs          | R           | R     | R*      | —     | —        |
| Departments         | CRUD        | CRUD  | R       | R     | R        |
| Projects            | CRUD        | CRUD  | CRUD    | R     | R        |
| Notifications       | CRUD        | CRUD  | RD      | RD    | RD       |
| Prompt Management   | CRUD        | CRUD  | R       | R     | —        |
| System Monitoring   | R           | R     | —       | —     | —        |

*CRUD = Create, Read, Update, Delete. Asterisk (*) indicates scoped access (own department/tickets only).*

### AUTH-FR-007: Profile Management

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall allow users to view and update their profile information.      |
| Editable     | Display name, avatar, phone, department preference, notification preferences, timezone |
| Non-Editable | Email (after verification), role (admin only), created date                 |

---

## 3.2 Ticket Management Module (TKT)

### TKT-FR-001: Ticket Creation

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall allow authorized users to create support tickets.              |
| Input        | Title, description, category, priority (optional), department (optional), attachments (optional) |
| Processing   | Validate input → Auto-assign ticket ID (TKT-YYYYMMDD-XXXX) → AI classification (category, priority, department) → Create record → Notify assigned team → Create audit entry |
| Output       | Ticket record with auto-generated metadata                                  |

**Acceptance Criteria:**
- [ ] Ticket ID format: `TKT-YYYYMMDD-XXXX` (sequential daily counter)
- [ ] AI auto-classifies category with confidence score ≥ 70%
- [ ] AI auto-predicts priority if not provided
- [ ] AI auto-routes to department based on content analysis
- [ ] File attachments limited to 10MB each, max 5 per ticket
- [ ] Supported formats: PDF, DOCX, PNG, JPG, TXT

### TKT-FR-002: Ticket Listing & Filtering

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall display tickets with filtering, sorting, and pagination.       |
| Filters      | Status, priority, category, department, assignee, date range, SLA status    |
| Sorting      | Created date, updated date, priority, SLA deadline                          |
| Pagination   | Default 20 per page, configurable (10, 20, 50, 100)                        |

### TKT-FR-003: Ticket Detail View

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall display complete ticket information with activity timeline.    |
| Display      | All ticket fields, comments/replies, attachments, activity history, SLA timer, related tickets, AI suggestions |

### TKT-FR-004: Ticket Status Workflow

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall enforce ticket status transitions.                             |

**Status Flow:**
```
[New] → [Open] → [In Progress] → [Pending] → [Resolved] → [Closed]
                       ↓              ↑
                  [Escalated] ────────┘
                       ↓
                  [On Hold] ──→ [In Progress]
```

**Valid Transitions:**

| From         | To                                          |
|--------------|---------------------------------------------|
| New          | Open, Closed (duplicate/invalid)            |
| Open         | In Progress, Closed                         |
| In Progress  | Pending, Resolved, Escalated, On Hold       |
| Pending      | In Progress, Resolved, Closed               |
| Escalated    | In Progress, Pending                        |
| On Hold      | In Progress                                 |
| Resolved     | Closed, In Progress (reopened)              |
| Closed       | In Progress (reopened, with audit log)      |

### TKT-FR-005: Ticket Assignment

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall support manual and AI-assisted ticket assignment.              |
| Modes        | Manual (by Manager/Admin), Auto-assign (round-robin), AI-suggested (based on agent expertise and workload) |

### TKT-FR-006: Ticket Comments & Replies

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall support threaded comments on tickets.                          |
| Types        | Public reply (visible to ticket creator), Internal note (agents only)       |
| Features     | Rich text, attachments, @mentions, AI-suggested replies                     |

### TKT-FR-007: SLA Management

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall track SLA compliance per ticket based on priority.             |

**Default SLA Targets:**

| Priority  | First Response | Resolution |
|-----------|----------------|------------|
| Critical  | 15 minutes     | 4 hours    |
| High      | 1 hour         | 8 hours    |
| Medium    | 4 hours        | 24 hours   |
| Low       | 8 hours        | 72 hours   |

### TKT-FR-008: Similar Ticket Search

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall use vector similarity to find related tickets.                 |
| Processing   | Generate embedding of ticket description → Search ChromaDB → Return top 5 similar tickets with similarity score |

---

## 3.3 Incident Management Module (INC)

### INC-FR-001: Incident Creation

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall support creation of incident records with severity classification. |
| Input        | Title, description, severity (Critical/High/Medium/Low), affected services, impact scope, related tickets |
| ID Format    | `INC-YYYYMMDD-XXXX`                                                        |

### INC-FR-002: Incident Severity & Impact Matrix

| Severity | Impact: High       | Impact: Medium     | Impact: Low        |
|----------|--------------------|--------------------|---------------------|
| Critical | P1 — Immediate     | P1 — Immediate     | P2 — Urgent        |
| High     | P1 — Immediate     | P2 — Urgent        | P3 — Standard      |
| Medium   | P2 — Urgent        | P3 — Standard      | P4 — Low           |
| Low      | P3 — Standard      | P4 — Low           | P4 — Low           |

### INC-FR-003: Incident Timeline

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall maintain a detailed incident timeline with all activities logged. |
| Events       | Created, assigned, updated, escalated, communications sent, resolved, post-mortem added |

### INC-FR-004: AI Incident Summary

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall generate AI-powered incident summaries using Groq LLM.        |
| Output       | Executive summary, timeline summary, impact analysis, action items          |

---

## 3.4 Problem Management Module (PRB)

### PRB-FR-001: Problem Record Creation

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall support creation of problem records linked to incidents.       |
| ID Format    | `PRB-YYYYMMDD-XXXX`                                                        |

### PRB-FR-002: Root Cause Analysis

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall provide AI-assisted root cause analysis for problems.          |
| Processing   | Analyze linked incidents → Search knowledge base → Generate root cause hypothesis → Suggest remediation steps |

---

## 3.5 Knowledge Base Module (KB)

### KB-FR-001: Article Management

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall support CRUD operations for knowledge base articles.           |
| Fields       | Title, content (rich text/Markdown), category, tags, author, status (draft/published/archived), version |
| Features     | Version history, rich text editor, image embedding, cross-referencing       |

### KB-FR-002: Article Search

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall provide full-text and semantic search across articles.         |
| Search Types | Keyword search (PostgreSQL full-text), Semantic search (ChromaDB vectors)  |

### KB-FR-003: AI Knowledge Search

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall use RAG to answer questions from knowledge base content.       |
| Processing   | User query → Generate embedding → Vector search → Retrieve top-k chunks → LLM generates answer with citations |

---

## 3.6 AI Assistant Module (AI)

### AI-FR-001: Conversational AI Chat

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall provide an AI-powered chat assistant for support queries.      |
| Features     | Multi-turn conversation, context retention (session), RAG-augmented responses, citation of sources |
| Provider     | Groq API (Llama 3.3 70B primary)                                           |
| Constraints  | Max context window: 8,192 tokens, streaming responses, response timeout: 30s |

### AI-FR-002: Ticket Classification

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall auto-classify tickets by category using LLM.                  |
| Categories   | Hardware, Software, Network, Access/Permissions, Email, Database, Security, General |
| Output       | Predicted category + confidence score (0.0–1.0)                             |

### AI-FR-003: Priority Prediction

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall auto-predict ticket priority using LLM analysis.              |
| Levels       | Critical, High, Medium, Low                                                 |
| Output       | Predicted priority + confidence score + reasoning                           |

### AI-FR-004: Department Routing

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall auto-route tickets to appropriate departments using AI.       |
| Processing   | Analyze ticket content → Match against department descriptions → Route with confidence score |

### AI-FR-005: AI Suggested Replies

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall generate suggested replies for support agents.                |
| Input        | Ticket context, conversation history, knowledge base results                |
| Output       | 2-3 suggested reply options with professional tone                          |

### AI-FR-006: AI Ticket Summary

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall generate concise ticket summaries for quick review.           |
| Output       | Summary paragraph, key issues list, action items, sentiment                 |

### AI-FR-007: AI Email Generation

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall generate professional emails related to tickets/incidents.    |
| Types        | Status update, escalation notice, resolution notification, follow-up       |

### AI-FR-008: Action Item Extraction

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall extract action items from ticket conversations and incidents. |
| Output       | Structured list: action, assignee (suggested), deadline (suggested), status |

### AI-FR-009: Prompt Template Management

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall support configurable prompt templates for all AI features.    |
| Features     | CRUD for prompts, variable interpolation, version control, A/B testing     |

### AI-FR-010: AI Provider Abstraction

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall abstract LLM provider behind a unified interface.             |
| Design       | Strategy pattern — providers implement common interface (complete, stream, embed) |
| Providers    | Groq (primary), extensible to Ollama, HuggingFace, OpenAI                  |

---

## 3.7 Document Management & RAG Module (DOC)

### DOC-FR-001: Document Upload

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall accept document uploads for RAG processing.                   |
| Formats      | PDF, DOCX, TXT, Markdown (.md)                                             |
| Size Limit   | 25 MB per file                                                              |

### DOC-FR-002: Document Processing Pipeline

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall process uploaded documents through chunking and embedding pipeline. |
| Pipeline     | Upload → Text extraction → Chunking (512 tokens, 50 token overlap) → Embedding (MiniLM-L6-v2) → Store in ChromaDB → Index metadata in PostgreSQL |

### DOC-FR-003: Vector Search

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall perform semantic similarity search across document embeddings. |
| Output       | Top-k results with: chunk text, source document, page/section, similarity score, confidence rating |

### DOC-FR-004: Citation & Confidence

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | All RAG-generated answers shall include source citations and confidence scores. |
| Format       | `[Source: document_name, Section: X, Confidence: 0.XX]`                    |

---

## 3.8 Analytics & Business Intelligence Module (BI)

### BI-FR-001: Real-Time Dashboard

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall display a real-time dashboard with key service desk metrics.  |

**KPI Cards:**

| KPI                    | Calculation                                              |
|------------------------|----------------------------------------------------------|
| Open Tickets           | Count of tickets with status ∉ {Resolved, Closed}       |
| Resolved Today         | Count of tickets resolved in current day                 |
| Avg Resolution Time    | Mean time from creation to resolution (last 30 days)     |
| SLA Compliance Rate    | % of tickets resolved within SLA target                  |
| Customer Satisfaction  | Average CSAT score (1-5) for resolved tickets            |
| Active Incidents       | Count of open incidents                                  |
| Pending Approvals      | Count of tickets in Pending status                       |
| Overdue Tickets        | Count of tickets past SLA deadline                       |

**Charts:**

| Chart                       | Type        | Data                                      |
|-----------------------------|-------------|-------------------------------------------|
| Tickets by Status           | Donut       | Status distribution                       |
| Tickets by Priority         | Bar         | Priority distribution                     |
| Tickets by Department       | Horizontal Bar | Department workload                    |
| Daily Ticket Trend          | Line        | Created vs Resolved (last 30 days)        |
| Monthly Volume              | Area        | Ticket volume (last 12 months)            |
| SLA Compliance Trend        | Line        | SLA % over time                           |
| Resolution Time Distribution| Histogram   | Resolution time buckets                   |
| Department Performance      | Radar       | Multi-metric department comparison         |
| Category Distribution       | Pie         | Ticket categories                          |
| Agent Performance           | Table       | Tickets resolved, avg time, CSAT per agent |
| Heat Map                    | Heat Map    | Ticket volume by day-of-week × hour        |

### BI-FR-002: Report Generation

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall generate downloadable reports.                                 |
| Formats      | PDF, CSV, Excel                                                             |
| Report Types | Daily Summary, Weekly Summary, Monthly Summary, SLA Report, Department Report, Agent Performance, AI Usage Report |

### BI-FR-003: AI-Generated Reports

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall use LLM to generate narrative report summaries.               |
| Output       | Executive summary, key findings, trend analysis, recommendations           |

---

## 3.9 Department & Project Management (ORG)

### ORG-FR-001: Department Management

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall support organizational department hierarchy.                  |
| Fields       | Name, description, manager, members, SLA configuration, auto-assignment rules |

### ORG-FR-002: Project Management

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall support project-based ticket grouping.                        |
| Fields       | Name, description, start date, end date, status, members, linked tickets   |

---

## 3.10 Notification Module (NTF)

### NTF-FR-001: In-App Notifications

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall deliver real-time in-app notifications.                       |
| Triggers     | Ticket assigned, status changed, comment added, SLA warning, mention, escalation |

### NTF-FR-002: Email Notifications

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall send email notifications for critical events.                 |
| Triggers     | Ticket created (to assignee), resolved (to requester), SLA breach, incident created |

---

## 3.11 Admin & Settings Module (ADM)

### ADM-FR-001: System Settings

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P1 — High                                                                   |
| Requirement  | System shall provide configurable system settings.                         |
| Settings     | Organization name, timezone, SLA defaults, email templates, AI model selection, theme preferences |

### ADM-FR-002: Audit Logging

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P0 — Critical                                                               |
| Requirement  | System shall log all significant user and system actions.                  |
| Log Fields   | Timestamp, user ID, action type, resource type, resource ID, old value, new value, IP address, user agent |
| Retention    | 90 days minimum                                                             |

### ADM-FR-003: System Monitoring

| Field        | Value                                                                       |
|--------------|-----------------------------------------------------------------------------|
| Priority     | P2 — Medium                                                                 |
| Requirement  | System shall expose health check and monitoring endpoints.                 |
| Endpoints    | `/api/v1/health` (basic), `/api/v1/health/detailed` (admin only — DB, Redis, Celery, ChromaDB, Groq API status) |
