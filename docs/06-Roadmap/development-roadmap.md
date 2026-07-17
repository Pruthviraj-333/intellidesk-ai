# IntelliDesk AI — Development Roadmap

**Document ID:** IDAI-ROAD-001 | **Version:** 1.0 | **Date:** 

---

## Overview

Development is organized into **6 milestones**, each independently deployable. Each milestone builds on the previous, with the platform growing from a basic authenticated API to a full AI-powered enterprise platform.

---

## Milestone Summary

| # | Milestone | Focus | Deliverables |
|---|-----------|-------|-------------|
| M1 | Project Foundation | Infra, Auth, Core API | Docker stack, JWT auth, User/Role management |
| M2 | Ticket & Incident Management | Core ITSM | Ticket lifecycle, Incidents, Problems, SLA |
| M3 | Knowledge Base & Documents | Content & RAG | KB articles, Document upload, ChromaDB RAG |
| M4 | AI Integration | Intelligence Layer | Groq integration, Classification, Chat, Summaries |
| M5 | Analytics & Reporting | Business Intelligence | Dashboards, Charts, Reports, WebSocket |
| M6 | Frontend & Polish | Full Stack | React SPA, All UI screens, Dark mode, PWA |

---

## Milestone 1 — Project Foundation

**Goal:** Working backend with authentication, RBAC, and base infrastructure.

### Deliverables

#### Backend
- [ ] Flask Application Factory with extensions
- [ ] PostgreSQL models: User, Role, Department, AuditLog, Setting
- [ ] Alembic migrations for all M1 tables
- [ ] JWT Authentication (register, login, refresh, logout)
- [ ] Email verification via Gmail SMTP
- [ ] Password reset flow
- [ ] RBAC decorators (`@role_required`)
- [ ] User CRUD API (admin)
- [ ] Profile management API
- [ ] Department CRUD API
- [ ] Audit logging (auth events)
- [ ] Health check endpoints
- [ ] Standard response envelope + error handlers
- [ ] Structured JSON logging with correlation IDs
- [ ] Rate limiting (Flask-Limiter + Redis)
- [ ] Input validation (Marshmallow DTOs)
- [ ] Unit tests for auth service (≥70% coverage)
- [ ] Integration tests for auth API

#### Infrastructure
- [ ] `docker-compose.yml` (postgres, redis, backend)
- [ ] Backend `Dockerfile` (dev + prod targets)
- [ ] `.env.example` with all variables
- [ ] `Makefile` with developer commands
- [ ] `requirements.txt` + `requirements-dev.txt`
- [ ] Flake8, Black, isort configuration
- [ ] GitHub Actions CI (lint + test only)

### Git Commit
```
feat(M1): Project foundation — Flask app factory, JWT auth, RBAC, User management
```

### Testing
```bash
make up
make migrate
curl -X POST http://localhost:8000/api/v1/auth/register -d '{"email":"test@test.com","password":"Test@1234","confirm_password":"Test@1234","first_name":"Test","last_name":"User"}'
curl -X GET http://localhost:8000/api/v1/health
```

---

## Milestone 2 — Ticket & Incident Management

**Goal:** Full ITSM ticket lifecycle, incidents, problems, and SLA tracking.

### Deliverables

#### Backend
- [ ] Models: Ticket, Comment, Attachment, Incident, IncidentTimeline, Problem, Project
- [ ] Alembic migrations for M2 tables
- [ ] Ticket CRUD API with full filtering, sorting, pagination
- [ ] Ticket status workflow validation
- [ ] Ticket ID generation (`TKT-YYYYMMDD-XXXX`)
- [ ] SLA calculation and deadline setting
- [ ] Comment API (public + internal notes)
- [ ] Attachment upload (Cloudinary integration)
- [ ] Ticket assignment API
- [ ] Bulk ticket update API
- [ ] Incident CRUD API
- [ ] Incident timeline API
- [ ] Problem CRUD API
- [ ] Incident ↔ Ticket linking
- [ ] Problem ↔ Incident linking
- [ ] Notification creation on ticket events
- [ ] Notification API (list, mark read)
- [ ] SLA monitoring Celery task (every 5 min)
- [ ] SLA breach flagging and notification
- [ ] Audit logging for all ticket/incident events
- [ ] Unit + integration tests for ticket service

#### Infrastructure
- [ ] Celery worker + beat service in `docker-compose.yml`
- [ ] Cloudinary configuration + local fallback

### Git Commit
```
feat(M2): Ticket lifecycle, Incident/Problem management, SLA tracking, Notifications
```

---

## Milestone 3 — Knowledge Base & Document RAG

**Goal:** Full knowledge base and RAG-powered document search.

### Deliverables

#### Backend
- [ ] Models: Article, ArticleVersion, ArticleCategory, Tag, Document, DocumentChunk
- [ ] Alembic migrations for M3 tables
- [ ] Article CRUD API
- [ ] Article versioning
- [ ] Full-text search (PostgreSQL tsvector)
- [ ] Article category management
- [ ] Document upload API
- [ ] Document text extraction (PyPDF2, python-docx)
- [ ] Text chunking (RecursiveCharacterTextSplitter, 512 tokens, 50 overlap)
- [ ] Embedding generation (sentence-transformers/all-MiniLM-L6-v2)
- [ ] ChromaDB integration (vector storage)
- [ ] Document processing Celery task
- [ ] Vector similarity search API
- [ ] Hybrid search (keyword + semantic)
- [ ] Document management API (list, detail, delete)
- [ ] VectorRepository (ChromaDB operations)
- [ ] RAGService (retrieval pipeline)
- [ ] EmbeddingService (batch embedding)

#### Infrastructure
- [ ] ChromaDB service in `docker-compose.yml`
- [ ] Embedding model pre-downloaded in Dockerfile
- [ ] Document processing queue configuration

### Git Commit
```
feat(M3): Knowledge Base, Document upload, ChromaDB RAG pipeline, Semantic search
```

---

## Milestone 4 — AI Integration

**Goal:** Full AI feature set using Groq API with provider abstraction.

### Deliverables

#### Backend
- [ ] LLMProvider abstract base class
- [ ] GroqProvider implementation
- [ ] LLMProviderFactory
- [ ] PromptTemplate model + CRUD API
- [ ] PromptManager (load + interpolate templates)
- [ ] Seed default prompt templates
- [ ] AIConversation + AIMessage models
- [ ] Chat API (streaming SSE + non-streaming)
- [ ] Ticket classification API (category + priority + department)
- [ ] AI ticket summarization API
- [ ] Suggested reply generation API
- [ ] Email generation API
- [ ] Action item extraction API
- [ ] RAG-augmented chat (ChromaDB + Groq)
- [ ] Ticket similarity search (vector-based)
- [ ] Root cause analysis for problems
- [ ] AI incident summary generation
- [ ] Token usage tracking
- [ ] AI error handling + graceful degradation
- [ ] Background AI classification on ticket creation
- [ ] Unit tests for AI service (mocked provider)

#### Infrastructure
- [ ] `GROQ_API_KEY` in environment config
- [ ] AI task queue configuration

### Git Commit
```
feat(M4): Groq LLM integration, AI chat, ticket classification, RAG, summaries, replies
```

---

## Milestone 5 — Analytics, BI & Reports

**Goal:** Real-time dashboard, charts, reports, and WebSocket updates.

### Deliverables

#### Backend
- [ ] Analytics service (all KPI calculations)
- [ ] Dashboard API endpoint
- [ ] SLA compliance analytics
- [ ] Historical trend queries
- [ ] Department performance metrics
- [ ] Agent performance metrics
- [ ] Heat map data endpoint
- [ ] Flask-SocketIO setup
- [ ] WebSocket authentication (JWT)
- [ ] Room management (user, department)
- [ ] Real-time event emission on ticket/incident updates
- [ ] Dashboard refresh Celery beat task (30s)
- [ ] Report generation service
- [ ] PDF report (ReportLab or WeasyPrint)
- [ ] CSV report generation
- [ ] AI narrative report generation
- [ ] Report download API
- [ ] Async report generation via Celery

### Git Commit
```
feat(M5): Analytics dashboard, KPIs, charts, WebSocket real-time, PDF/CSV reports
```

---

## Milestone 6 — React Frontend

**Goal:** Full responsive React SPA with all screens, dark mode, and production build.

### Deliverables

#### Frontend Structure
- [ ] Vite + React 18 + TypeScript setup
- [ ] TailwindCSS + dark/light mode
- [ ] Redux Toolkit store (auth, UI slices)
- [ ] React Query (TanStack) setup
- [ ] React Router v6 with protected routes
- [ ] Axios API client with JWT interceptor + auto-refresh
- [ ] Socket.IO client with auth

#### Auth Screens
- [ ] Login page
- [ ] Registration page
- [ ] Forgot password page
- [ ] Email verification page
- [ ] Password reset page

#### Core Layout
- [ ] App shell (sidebar + header + content area)
- [ ] Role-aware sidebar navigation
- [ ] Header (search, notifications bell, profile dropdown)
- [ ] Dark/light mode toggle
- [ ] Notification dropdown

#### Shared UI Components
- [ ] Button, Input, Select, Textarea, Modal
- [ ] Badge (status, priority), Avatar, Tooltip
- [ ] Skeleton loaders, Spinner, Toast
- [ ] DataTable (sortable, filterable)
- [ ] KPI Card, Timeline, Empty State, Pagination

#### Feature Pages
- [ ] Dashboard (KPI grid + 8 charts)
- [ ] Ticket list (table + filters + bulk actions)
- [ ] Ticket detail (info + timeline + comments + AI sidebar)
- [ ] Create ticket (AI-assisted form)
- [ ] Incident list + detail + timeline
- [ ] Problem list + detail
- [ ] Knowledge base (article cards + search)
- [ ] Article detail (markdown render + helpful button)
- [ ] Create/edit article
- [ ] AI Chat (streaming chat window with citations)
- [ ] Document management (upload + list + status)
- [ ] Analytics (interactive charts + date filters)
- [ ] Reports (generate + download)
- [ ] Notifications page
- [ ] User profile page
- [ ] Admin: User management
- [ ] Admin: Department management
- [ ] Admin: System settings
- [ ] Admin: Audit log viewer
- [ ] Admin: Prompt template manager
- [ ] Admin: System health monitor
- [ ] 404 Not Found page

#### Infrastructure
- [ ] `frontend/Dockerfile`
- [ ] NGINX serving React build
- [ ] Vercel deployment config (`vercel.json`)
- [ ] GitHub Actions: frontend lint + build + deploy

### Git Commit
```
feat(M6): Complete React frontend — all screens, dark mode, real-time updates, AI chat
```

---

## Post-Launch Enhancements (v1.1+)

| Enhancement | Priority |
|-------------|----------|
| Multi-language support (i18n) | Medium |
| SSO / OAuth2 login (Google, Microsoft) | High |
| Mobile-responsive PWA | Medium |
| Webhook integrations (Slack, Teams) | High |
| ML models for prediction (when data accumulates) | High |
| ServiceNow/Jira import connector | Low |
| Advanced SLA configuration UI | Medium |
| Customer satisfaction surveys (CSAT) | High |
| Multi-tenant architecture | Low |

---

## Estimated Scope

| Metric | Count |
|--------|-------|
| Backend Python files | ~80 |
| Frontend TypeScript/React files | ~120 |
| Database tables | 21 |
| API endpoints | ~80 |
| React pages | ~25 |
| Shared components | ~35 |
| Celery tasks | 10 |
| Test files | ~30 |
