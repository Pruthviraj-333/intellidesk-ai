# 2. Overall Description

## 2.1 Product Perspective

IntelliDesk AI is a **new, self-contained product** designed as a modern alternative to legacy ITSM platforms (ServiceNow, Jira Service Management, Zendesk). It operates as a web-based SaaS application with the following system context:

```
┌─────────────────────────────────────────────────────────┐
│                    INTELLIDESK AI                        │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐    │
│  │  React   │──▶│  Flask   │──▶│   PostgreSQL     │    │
│  │ Frontend │   │  Backend │   │   Database        │    │
│  └──────────┘   └────┬─────┘   └──────────────────┘    │
│                      │                                   │
│              ┌───────┼───────┐                           │
│              ▼       ▼       ▼                           │
│         ┌────────┐ ┌─────┐ ┌──────────┐                │
│         │ Groq   │ │Redis│ │ ChromaDB │                │
│         │  API   │ │     │ │(Vectors) │                │
│         └────────┘ └─────┘ └──────────┘                │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐    │
│  │  Celery  │   │  NGINX   │   │   Cloudinary     │    │
│  │ Workers  │   │  Proxy   │   │   (Storage)      │    │
│  └──────────┘   └──────────┘   └──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### System Interfaces

| Interface           | Technology          | Purpose                                    |
|---------------------|---------------------|--------------------------------------------|
| Web Browser         | React + TypeScript  | Primary user interface                     |
| REST API            | Flask + Marshmallow | Backend service layer                      |
| Database            | PostgreSQL 16       | Persistent data storage                    |
| Cache/Queue         | Redis 7             | Session cache, Celery message broker       |
| Vector Store        | ChromaDB            | Embedding storage for RAG                  |
| LLM Provider        | Groq API            | AI inference (Llama 3.3 70B, etc.)         |
| Embedding Model     | sentence-transformers| Local embedding generation                 |
| Task Queue          | Celery              | Async background job processing            |
| Object Storage      | Cloudinary          | Document and file storage                  |
| Reverse Proxy       | NGINX               | Load balancing, SSL termination            |

## 2.2 Product Functions (High-Level)

The platform provides the following major functional areas:

### Core Service Desk

| ID    | Function                  | Description                                                     |
|-------|---------------------------|-----------------------------------------------------------------|
| F-001 | Ticket Management         | Full lifecycle: create, assign, escalate, resolve, close        |
| F-002 | Incident Management       | ITIL-aligned incident response and tracking                     |
| F-003 | Problem Management        | Root cause analysis and problem record linking                  |
| F-004 | Knowledge Base            | Searchable articles, categories, version control                |
| F-005 | Document Management       | Upload, store, retrieve enterprise documents                    |

### AI & Intelligence

| ID    | Function                  | Description                                                     |
|-------|---------------------------|-----------------------------------------------------------------|
| F-006 | AI Chat Assistant         | Conversational AI for support queries (Groq LLM)               |
| F-007 | Ticket Intelligence       | Auto-classification, priority prediction, routing               |
| F-008 | RAG Engine                | Knowledge retrieval from uploaded documents                     |
| F-009 | ML Predictions            | Resolution time, satisfaction, sentiment models                 |
| F-010 | AI Content Generation     | Summaries, suggested replies, email drafts                      |

### Business Operations

| ID    | Function                  | Description                                                     |
|-------|---------------------------|-----------------------------------------------------------------|
| F-011 | Dashboard & Analytics     | Real-time KPIs, charts, trends, forecasts                      |
| F-012 | Reports                   | Scheduled/on-demand report generation with export               |
| F-013 | Department Management     | Organizational structure and team management                    |
| F-014 | Project Management        | Project-based ticket grouping and tracking                      |
| F-015 | Notifications             | In-app and email notification system                            |

### Platform Administration

| ID    | Function                  | Description                                                     |
|-------|---------------------------|-----------------------------------------------------------------|
| F-016 | Authentication & RBAC     | JWT auth, 5-tier roles, refresh tokens                          |
| F-017 | User Management           | User CRUD, profile management, role assignment                  |
| F-018 | Admin Panel               | System configuration, settings, monitoring                      |
| F-019 | Audit Logging             | Comprehensive action audit trail                                |
| F-020 | System Monitoring         | Health checks, performance metrics, uptime tracking             |

## 2.3 User Classes and Characteristics

### User Role Matrix

| Role           | Access Level | Description                                                     | Est. % |
|----------------|-------------|------------------------------------------------------------------|--------|
| Super Admin    | Full        | Platform owner. Full system access, configuration, user management, system monitoring. | 2%     |
| Admin          | High        | Organization admin. User management, settings, reports, all tickets. | 5%     |
| Manager        | Medium-High | Team lead. Department tickets, team performance, assignments, escalations. | 10%    |
| Support Agent  | Medium      | IT support staff. Assigned tickets, knowledge base, AI assistant, resolutions. | 33%    |
| Employee       | Low         | End user. Submit tickets, track status, search knowledge base, AI chat. | 50%    |

### Detailed User Profiles

**Super Admin**
- Technical background, system administration experience
- Needs: Full platform control, user provisioning, system health monitoring
- Frequency: Daily for monitoring, weekly for configuration changes
- Critical workflows: User management, role configuration, system settings, audit review

**Admin**
- IT management background
- Needs: Organizational oversight, reporting, team management
- Frequency: Daily
- Critical workflows: Report generation, user management, SLA configuration, escalation rules

**Manager**
- Team leadership, moderate technical knowledge
- Needs: Team performance visibility, workload distribution, escalation management
- Frequency: Multiple times daily
- Critical workflows: Ticket assignment, team dashboards, performance reviews, escalation handling

**Support Agent**
- Technical support expertise, product knowledge
- Needs: Efficient ticket resolution, knowledge access, AI assistance
- Frequency: Continuous (primary work tool)
- Critical workflows: Ticket resolution, knowledge search, AI-assisted responses, incident management

**Employee**
- Varies from non-technical to technical
- Needs: Easy ticket submission, status tracking, self-service knowledge search
- Frequency: As needed (issue-driven)
- Critical workflows: Ticket creation, status checking, knowledge base search, AI chat

## 2.4 Operating Environment

### Client Requirements

| Component        | Requirement                                              |
|------------------|----------------------------------------------------------|
| Browser          | Chrome 90+, Firefox 88+, Edge 90+, Safari 14+           |
| Screen Resolution| Minimum 1280×720, optimized for 1920×1080               |
| Network          | Minimum 1 Mbps broadband                                |
| JavaScript       | Must be enabled                                          |

### Server Environment

| Component        | Technology            | Version    | Purpose                    |
|------------------|-----------------------|------------|----------------------------|
| OS               | Ubuntu 22.04 LTS      | 22.04      | Server operating system    |
| Runtime          | Python                | 3.11+      | Backend runtime            |
| Node.js          | Node.js               | 18 LTS+    | Frontend build toolchain   |
| Web Server       | NGINX                 | 1.24+      | Reverse proxy              |
| App Server       | Gunicorn              | 21+        | WSGI HTTP server           |
| Database         | PostgreSQL            | 16+        | Primary data store         |
| Cache            | Redis                 | 7+         | Caching and message broker |
| Containerization | Docker                | 24+        | Container runtime          |
| Orchestration    | Docker Compose        | 2.20+      | Multi-container management |

### Cloud Deployment Targets

| Service          | Provider              | Tier       | Purpose                    |
|------------------|-----------------------|------------|----------------------------|
| Backend Hosting  | Render                | Free       | Flask API hosting          |
| Frontend Hosting | Vercel                | Free       | React SPA hosting          |
| Database         | Neon PostgreSQL       | Free       | Managed PostgreSQL         |
| Object Storage   | Cloudinary            | Free       | File/document storage      |
| CI/CD            | GitHub Actions        | Free       | Build and deployment        |

## 2.5 Design and Implementation Constraints

| Constraint                    | Description                                                              |
|-------------------------------|--------------------------------------------------------------------------|
| Budget                        | All technologies must be free or have a free tier                        |
| LLM Provider                  | Must use Groq API; architecture must allow provider swap                 |
| Embedding Model               | Must use free, open-source models (sentence-transformers)                |
| Vector Database               | Must use ChromaDB or FAISS (no paid services)                            |
| Backend Language              | Python 3.11+ with Flask framework                                       |
| Frontend Framework            | React 18+ with TypeScript and Vite                                      |
| Database                      | PostgreSQL (no NoSQL for primary storage)                                |
| Authentication                | JWT-based (no OAuth2/SAML in v1.0)                                      |
| Architecture                  | Clean Architecture with Repository/Service/DTO patterns                 |
| API Standard                  | RESTful with OpenAPI 3.1 documentation                                  |
| Containerization              | Must support Docker and Docker Compose                                  |
| Code Standards                | PEP 8, SOLID, DRY, KISS principles                                     |

## 2.6 Assumptions and Dependencies

### Assumptions

1. Users have modern web browsers with JavaScript enabled.
2. The Groq API free tier provides sufficient rate limits for development and demonstration.
3. Network connectivity is available for LLM API calls (no offline LLM mode).
4. PostgreSQL free-tier providers (Neon/Supabase) offer sufficient storage for demo data.
5. Cloudinary free tier (25 credits/month) is sufficient for document storage in demo.
6. Users understand basic IT service desk workflows.

### Dependencies

| Dependency            | Risk Level | Mitigation                                            |
|-----------------------|------------|-------------------------------------------------------|
| Groq API availability | Medium     | Abstraction layer allows swap to Ollama/HuggingFace   |
| Neon PostgreSQL uptime| Low        | Docker Compose includes local PostgreSQL fallback      |
| Cloudinary service    | Low        | Local filesystem fallback for development              |
| sentence-transformers | Low        | Multiple model options (MiniLM, BGE)                   |
| ChromaDB stability    | Low        | FAISS as drop-in alternative                           |
| Free tier rate limits | Medium     | Request queuing, caching, graceful degradation         |
