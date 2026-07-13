# 6. System Architecture Overview

## 6.1 High-Level Architecture

IntelliDesk AI follows a **Layered Clean Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│                                                                  │
│    React 18 + TypeScript + Vite + TailwindCSS                   │
│    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐    │
│    │  Pages   │ │Components│ │  Hooks   │ │  Redux Store  │    │
│    └──────────┘ └──────────┘ └──────────┘ └───────────────┘    │
│                         ↕ Axios + React Query                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST API
┌──────────────────────────┴──────────────────────────────────────┐
│                       API GATEWAY LAYER                          │
│                                                                  │
│    NGINX (Reverse Proxy, SSL, Rate Limiting, Static Files)      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                     APPLICATION LAYER                             │
│                                                                  │
│    Flask + Gunicorn                                              │
│    ┌───────────────────────────────────────────────────────┐    │
│    │                   Controller Layer                     │    │
│    │        (Flask Blueprints + Route Handlers)             │    │
│    │        Input validation, response formatting           │    │
│    ├───────────────────────────────────────────────────────┤    │
│    │                   Service Layer                        │    │
│    │        Business logic, orchestration, validation       │    │
│    │        AI service, RAG service, ML service             │    │
│    ├───────────────────────────────────────────────────────┤    │
│    │                  Repository Layer                      │    │
│    │        Data access, queries, CRUD operations           │    │
│    │        SQLAlchemy models + ChromaDB client             │    │
│    ├───────────────────────────────────────────────────────┤    │
│    │                    DTO Layer                           │    │
│    │        Marshmallow schemas for serialization           │    │
│    │        Request/Response data transfer objects          │    │
│    ├───────────────────────────────────────────────────────┤    │
│    │                   Utility Layer                        │    │
│    │        Helpers, formatters, validators, decorators     │    │
│    ├───────────────────────────────────────────────────────┤    │
│    │                   Config Layer                         │    │
│    │        Environment config, feature flags, constants    │    │
│    └───────────────────────────────────────────────────────┘    │
└──────────┬──────────┬───────────┬──────────┬────────────────────┘
           │          │           │          │
     ┌─────┴───┐ ┌───┴────┐ ┌───┴───┐ ┌───┴─────────┐
     │PostgreSQL│ │ Redis  │ │ChromaDB│ │  Groq API   │
     │   16+   │ │  7+    │ │       │ │  (External) │
     └─────────┘ └────────┘ └───────┘ └─────────────┘
                      │
                 ┌────┴────┐
                 │ Celery  │
                 │ Workers │
                 └─────────┘
```

## 6.2 Backend Architecture (Clean Architecture)

### Layer Responsibilities

| Layer        | Responsibility                                    | Dependencies             |
|--------------|---------------------------------------------------|--------------------------|
| Controller   | HTTP request handling, input parsing, response formatting | Service Layer        |
| Service      | Business logic, validation, orchestration         | Repository Layer, External APIs |
| Repository   | Data access abstraction, database queries         | ORM (SQLAlchemy), ChromaDB |
| DTO          | Data serialization/deserialization                | Marshmallow schemas      |
| Model        | Database entity definitions                       | SQLAlchemy               |
| Utility      | Cross-cutting concerns (logging, auth decorators) | None (pure functions)    |
| Config       | Application configuration                         | Environment variables    |

### Dependency Rule

Dependencies flow **inward only**:

```
Controller → Service → Repository → Model
     ↓           ↓
    DTO        Utility
                 ↓
              Config
```

No inner layer may reference an outer layer.

## 6.3 AI Architecture

### LLM Provider Abstraction

```
┌───────────────────────────────────────────────┐
│              AI Service Layer                  │
│                                                │
│  ┌──────────────┐  ┌────────────────────────┐ │
│  │ TicketAI     │  │ ChatAI                 │ │
│  │ - classify() │  │ - chat()               │ │
│  │ - predict()  │  │ - stream()             │ │
│  │ - route()    │  │ - summarize()          │ │
│  └──────┬───────┘  └──────────┬─────────────┘ │
│         │                     │                │
│         └──────────┬──────────┘                │
│                    ▼                            │
│  ┌─────────────────────────────────────────┐   │
│  │       LLM Provider Interface            │   │
│  │  (Abstract Base Class)                  │   │
│  │                                         │   │
│  │  + complete(prompt, **kwargs) → str     │   │
│  │  + stream(prompt, **kwargs) → Iterator  │   │
│  │  + structured(prompt, schema) → dict    │   │
│  └───────────┬─────────────────────────────┘   │
│              │ implements                       │
│   ┌──────────┼──────────┐                      │
│   ▼          ▼          ▼                      │
│ ┌──────┐ ┌──────┐ ┌──────────┐                │
│ │ Groq │ │Ollama│ │HuggingFace│               │
│ │(prod)│ │(dev) │ │ (backup) │                │
│ └──────┘ └──────┘ └──────────┘                │
└───────────────────────────────────────────────┘
```

### RAG Pipeline Architecture

```
Document Upload Flow:
  Upload → Extract Text → Chunk (512 tokens) → Embed (MiniLM) → Store (ChromaDB)

Query Flow:
  User Query → Embed Query → Vector Search (ChromaDB, top-k=5) → Re-rank →
  Build Context → LLM Generate (Groq) → Format Response with Citations
```

### ML Model Architecture

```
Training Pipeline:
  Historical Data (PostgreSQL) → Feature Engineering (Pandas) →
  Train Models (scikit-learn) → Evaluate → Save (joblib) → Register

Inference Pipeline:
  New Ticket → Extract Features → Load Model → Predict → Return with Confidence
```

## 6.4 Frontend Architecture

```
src/
├── app/                  # App configuration, store, router
├── features/             # Feature-based modules
│   ├── auth/             # Login, register, password reset
│   ├── dashboard/        # Dashboard views and widgets
│   ├── tickets/          # Ticket CRUD and views
│   ├── incidents/        # Incident management
│   ├── knowledge-base/   # Knowledge articles
│   ├── ai-assistant/     # AI chat interface
│   ├── analytics/        # Charts and reports
│   ├── admin/            # Admin panel
│   └── ...
├── components/           # Shared UI components
│   ├── ui/               # Base components (Button, Input, Card, Modal)
│   ├── layout/           # Layout components (Sidebar, Header, Footer)
│   └── data-display/     # Tables, charts, KPI cards
├── hooks/                # Custom React hooks
├── services/             # API client services (Axios)
├── store/                # Redux Toolkit slices
├── types/                # TypeScript type definitions
├── utils/                # Helper functions
└── styles/               # Global styles, themes
```

## 6.5 Data Flow Diagrams

### Ticket Creation Flow

```
Employee                    Frontend              Backend               Database
   │                           │                     │                     │
   │  Fill ticket form         │                     │                     │
   │ ─────────────────────────▶│                     │                     │
   │                           │  POST /tickets      │                     │
   │                           │ ───────────────────▶│                     │
   │                           │                     │  Validate input     │
   │                           │                     │  Generate ticket ID │
   │                           │                     │──┐                  │
   │                           │                     │  │ AI Classify      │
   │                           │                     │  │ (Groq API)       │
   │                           │                     │◀─┘                  │
   │                           │                     │  Save ticket        │
   │                           │                     │ ───────────────────▶│
   │                           │                     │                     │
   │                           │                     │  Queue notification │
   │                           │                     │──▶ Celery           │
   │                           │                     │                     │
   │                           │  201 + ticket data  │                     │
   │                           │ ◀───────────────────│                     │
   │  Show confirmation        │                     │                     │
   │ ◀────────────────────────│                     │                     │
```

### RAG Query Flow

```
User                   Frontend              Backend           ChromaDB        Groq API
 │                        │                     │                  │               │
 │  Ask question          │                     │                  │               │
 │ ──────────────────────▶│                     │                  │               │
 │                        │ POST /ai/chat       │                  │               │
 │                        │ ────────────────────▶│                  │               │
 │                        │                     │ Embed query       │               │
 │                        │                     │ (MiniLM local)   │               │
 │                        │                     │──┐               │               │
 │                        │                     │◀─┘               │               │
 │                        │                     │ Vector search    │               │
 │                        │                     │ ────────────────▶│               │
 │                        │                     │ Top-k results    │               │
 │                        │                     │ ◀────────────────│               │
 │                        │                     │ Build prompt      │               │
 │                        │                     │ + context chunks  │               │
 │                        │                     │ Stream generate   │               │
 │                        │                     │ ───────────────────────────────▶│
 │                        │  SSE stream         │ Stream tokens     │               │
 │                        │ ◀───────────────────│ ◀──────────────────────────────│
 │  Show streaming answer │                     │                  │               │
 │ ◀──────────────────────│                     │                  │               │
```

---

# 7. Data Requirements

## 7.1 Core Entity Summary

| Entity            | Description                                      | Estimated Volume (Year 1) |
|-------------------|--------------------------------------------------|---------------------------|
| User              | Platform users with roles                        | 500                       |
| Ticket            | Service desk tickets                             | 50,000                    |
| Comment           | Ticket comments and internal notes               | 150,000                   |
| Incident          | Incident records                                 | 5,000                     |
| Problem           | Problem records                                  | 1,000                     |
| Article           | Knowledge base articles                          | 2,000                     |
| Document          | Uploaded documents for RAG                       | 500                       |
| DocumentChunk     | Chunked document segments                        | 25,000                    |
| Department        | Organizational departments                       | 50                        |
| Project           | Projects for ticket grouping                     | 100                       |
| Notification      | User notifications                               | 500,000                   |
| AuditLog          | Audit trail entries                              | 1,000,000                 |
| AIConversation    | AI chat sessions                                 | 20,000                    |
| AIMessage         | AI chat messages                                 | 100,000                   |
| PromptTemplate    | Configurable AI prompts                          | 50                        |
| Setting           | System configuration key-value pairs             | 100                       |
| MLModel           | Trained ML model metadata                        | 20                        |

## 7.2 Key Entity Relationships

```
User ──┬──< Ticket (as requester)
       ├──< Ticket (as assignee)
       ├──< Comment
       ├──< Incident (as reporter)
       ├──< Incident (as assignee)
       ├──< Article (as author)
       ├──< Notification
       ├──< AuditLog
       ├──< AIConversation
       └──< Document (as uploader)

Ticket ──┬──< Comment
         ├──< Attachment
         ├──○ Incident (optional link)
         ├──○ Department
         ├──○ Project
         └──< AuditLog

Incident ──┬──< IncidentTimeline
           ├──< Ticket (linked)
           └──○ Problem

Problem ──┬──< Incident (linked)
          └──< ProblemNote

Department ──┬──< User (members)
             ├──< Ticket (assigned)
             └──○ User (manager)

Article ──┬──< ArticleVersion
          └──< Tag

Document ──┬──< DocumentChunk
           └──< DocumentMetadata

AIConversation ──< AIMessage
```

## 7.3 Data Retention Policy

| Data Type         | Retention Period | Archival Strategy                        |
|-------------------|------------------|------------------------------------------|
| Active Tickets    | Indefinite       | Archived after 1 year of closure         |
| Audit Logs        | 90 days (active) | Compressed archive after 90 days         |
| Notifications     | 30 days          | Auto-deleted after 30 days               |
| AI Conversations  | 90 days          | Summarized and archived                  |
| Documents         | Indefinite       | Managed by storage provider              |
| ML Model Artifacts| 6 months         | Keep latest 3 versions per model         |

---

# 8. AI/ML Requirements

## 8.1 LLM Integration Requirements

| ID       | Requirement                                                              |
|----------|--------------------------------------------------------------------------|
| AI-001   | All LLM calls must go through the provider abstraction layer             |
| AI-002   | Provider must be configurable via environment variable                   |
| AI-003   | Groq API key stored as environment secret                                |
| AI-004   | All AI requests must have a timeout of 30 seconds                        |
| AI-005   | Failed AI requests must not break core ticket/incident operations        |
| AI-006   | AI responses must be logged for quality monitoring                       |
| AI-007   | Prompt templates must be stored in the database and admin-configurable   |
| AI-008   | Streaming responses must use Server-Sent Events (SSE)                    |
| AI-009   | Structured responses must conform to defined JSON schemas                |
| AI-010   | Token usage must be tracked per request for monitoring                   |

## 8.2 Embedding Requirements

| ID       | Requirement                                                              |
|----------|--------------------------------------------------------------------------|
| EMB-001  | Use sentence-transformers/all-MiniLM-L6-v2 as default embedding model   |
| EMB-002  | Embedding model must run locally (no API calls for embeddings)           |
| EMB-003  | Embedding dimension: 384                                                 |
| EMB-004  | Support batch embedding for document processing                          |
| EMB-005  | Model must be downloaded and cached on first run                         |

## 8.3 RAG Requirements

| ID       | Requirement                                                              |
|----------|--------------------------------------------------------------------------|
| RAG-001  | Document chunking: 512 tokens per chunk, 50 token overlap               |
| RAG-002  | Vector search: return top-k results (default k=5, configurable)         |
| RAG-003  | Minimum similarity threshold: 0.5 (configurable)                        |
| RAG-004  | All RAG responses must include source citations                          |
| RAG-005  | Confidence score calculated from average similarity of retrieved chunks  |
| RAG-006  | Support incremental document updates (re-embed changed chunks only)     |
| RAG-007  | ChromaDB collections: separate collections for documents, articles, tickets |

## 8.4 ML Model Requirements

| ID       | Requirement                                                              |
|----------|--------------------------------------------------------------------------|
| ML-001   | Models trained on historical ticket data                                 |
| ML-002   | Minimum training data: 500 labeled tickets per model                     |
| ML-003   | Model evaluation metrics tracked: accuracy, precision, recall, F1        |
| ML-004   | Models versioned and stored with metadata                                |
| ML-005   | Prediction confidence threshold: 0.6 (below = "uncertain")              |
| ML-006   | Models retrained weekly via Celery scheduled task                        |
| ML-007   | Feature engineering pipeline documented and reproducible                 |

### ML Models Specification

| Model                     | Type              | Features                                  | Target           |
|---------------------------|-------------------|-------------------------------------------|------------------|
| Resolution Time Predictor | Regression        | Category, priority, department, description length, time of day | Hours to resolve |
| Priority Predictor        | Classification    | Title, description, category, keywords    | Critical/High/Medium/Low |
| Category Predictor        | Classification    | Title, description, keywords              | Hardware/Software/Network/... |
| Department Router         | Classification    | Title, description, category              | Department ID    |
| Sentiment Analyzer        | Classification    | Comment text                              | Positive/Neutral/Negative |
| CSAT Predictor            | Regression        | Resolution time, interactions, reopens    | Score 1-5        |

---

# 9. User Stories

## 9.1 Epic: Authentication & Access

| ID      | Story                                                                           | Priority | Points |
|---------|---------------------------------------------------------------------------------|----------|--------|
| US-001  | As an employee, I want to register for an account so I can access the platform. | P0       | 5      |
| US-002  | As a user, I want to log in with my credentials so I can access my dashboard.   | P0       | 3      |
| US-003  | As a user, I want to reset my password so I can recover my account.             | P1       | 5      |
| US-004  | As a user, I want to verify my email so I can activate my account.              | P1       | 3      |
| US-005  | As a user, I want to update my profile so I can keep my information current.    | P1       | 3      |
| US-006  | As an admin, I want to manage user roles so I can control access permissions.   | P0       | 5      |
| US-007  | As a super admin, I want to view audit logs so I can monitor system activity.   | P1       | 5      |

## 9.2 Epic: Ticket Management

| ID      | Story                                                                           | Priority | Points |
|---------|---------------------------------------------------------------------------------|----------|--------|
| US-010  | As an employee, I want to create a ticket so I can report an issue.             | P0       | 5      |
| US-011  | As an employee, I want to view my tickets so I can track their status.          | P0       | 3      |
| US-012  | As an agent, I want to view all assigned tickets so I can manage my workload.   | P0       | 5      |
| US-013  | As an agent, I want to update ticket status so I can track resolution progress. | P0       | 3      |
| US-014  | As an agent, I want to add comments to tickets so I can communicate with the requester. | P0 | 3    |
| US-015  | As a manager, I want to assign tickets to agents so I can distribute workload.  | P0       | 3      |
| US-016  | As a manager, I want to escalate tickets so I can ensure critical issues are addressed. | P1 | 3    |
| US-017  | As an agent, I want to search for similar tickets so I can find existing solutions. | P2    | 5      |
| US-018  | As a user, I want SLA tracking on tickets so I can know expected resolution time. | P1     | 8      |

## 9.3 Epic: AI Features

| ID      | Story                                                                           | Priority | Points |
|---------|---------------------------------------------------------------------------------|----------|--------|
| US-020  | As an employee, I want AI to auto-classify my ticket so I don't need to choose a category. | P0 | 8   |
| US-021  | As an employee, I want to chat with AI so I can get quick answers to common questions. | P0  | 13     |
| US-022  | As an agent, I want AI to suggest replies so I can respond faster.              | P1       | 8      |
| US-023  | As an agent, I want AI to summarize long tickets so I can understand them quickly. | P1     | 5      |
| US-024  | As a manager, I want AI to predict ticket priority so we can prioritize effectively. | P1   | 8      |
| US-025  | As a manager, I want AI to route tickets to the right department automatically. | P1       | 8      |
| US-026  | As an agent, I want AI to find relevant knowledge articles for my ticket.       | P1       | 8      |
| US-027  | As a manager, I want AI to generate incident summaries for executive review.    | P2       | 5      |
| US-028  | As an admin, I want to manage AI prompt templates so I can customize AI behavior. | P1     | 8      |

## 9.4 Epic: Knowledge Base & RAG

| ID      | Story                                                                           | Priority | Points |
|---------|---------------------------------------------------------------------------------|----------|--------|
| US-030  | As an agent, I want to create knowledge articles so I can document solutions.   | P0       | 5      |
| US-031  | As an employee, I want to search the knowledge base so I can find self-service solutions. | P0 | 5  |
| US-032  | As an admin, I want to upload documents so they can be used by the AI system.   | P0       | 8      |
| US-033  | As a user, I want AI to search uploaded documents when answering my questions.  | P1       | 13     |
| US-034  | As a user, I want to see citations in AI responses so I can verify the information. | P1    | 5      |

## 9.5 Epic: Analytics & BI

| ID      | Story                                                                           | Priority | Points |
|---------|---------------------------------------------------------------------------------|----------|--------|
| US-040  | As a manager, I want a dashboard showing ticket KPIs so I can monitor operations. | P0     | 13     |
| US-041  | As a manager, I want to see SLA compliance rates so I can ensure service quality. | P1     | 8      |
| US-042  | As an admin, I want to generate reports so I can share metrics with stakeholders. | P1     | 8      |
| US-043  | As a manager, I want to see department performance so I can identify bottlenecks. | P1     | 5      |
| US-044  | As an admin, I want AI-generated report summaries so I can quickly understand trends. | P2  | 8      |
| US-045  | As a manager, I want to download reports as PDF/CSV so I can share them offline. | P2     | 5      |

## 9.6 Epic: Administration

| ID      | Story                                                                           | Priority | Points |
|---------|---------------------------------------------------------------------------------|----------|--------|
| US-050  | As a super admin, I want to configure system settings so I can customize the platform. | P1 | 5     |
| US-051  | As an admin, I want to manage departments so I can reflect org structure.       | P1       | 5      |
| US-052  | As an admin, I want to monitor system health so I can ensure platform reliability. | P2    | 8      |
| US-053  | As a user, I want to receive notifications so I stay informed about ticket updates. | P1   | 8      |
| US-054  | As a user, I want dark mode so I can reduce eye strain.                         | P2       | 3      |

---

# 10. Appendices

## 10.1 Technology Stack Summary

| Layer              | Technology                          | Version   | License       |
|--------------------|-------------------------------------|-----------|---------------|
| Frontend Framework | React                               | 18.x      | MIT           |
| Frontend Language  | TypeScript                          | 5.x       | Apache 2.0    |
| Build Tool         | Vite                                | 5.x       | MIT           |
| CSS Framework      | TailwindCSS                         | 3.x       | MIT           |
| State Management   | Redux Toolkit                       | 2.x       | MIT           |
| Data Fetching      | React Query (TanStack Query)        | 5.x       | MIT           |
| HTTP Client        | Axios                               | 1.x       | MIT           |
| Charts             | Chart.js                            | 4.x       | MIT           |
| Icons              | Heroicons + Lucide                  | Latest    | MIT           |
| Routing            | React Router                        | 6.x       | MIT           |
| Backend Framework  | Flask                               | 3.x       | BSD           |
| ORM                | SQLAlchemy                          | 2.x       | MIT           |
| Migrations         | Alembic                             | 1.x       | MIT           |
| Serialization      | Marshmallow                         | 3.x       | MIT           |
| Auth               | Flask-JWT-Extended                  | 4.x       | MIT           |
| Task Queue         | Celery                              | 5.x       | BSD           |
| Database           | PostgreSQL                          | 16+       | PostgreSQL    |
| Cache              | Redis                               | 7+        | BSD           |
| Vector DB          | ChromaDB                            | 0.5+      | Apache 2.0    |
| Embedding          | sentence-transformers (MiniLM-L6-v2)| Latest    | Apache 2.0    |
| LLM Provider       | Groq API                            | Latest    | Free tier     |
| ML Libraries       | scikit-learn, Pandas, NumPy         | Latest    | BSD           |
| Containerization   | Docker + Docker Compose             | 24+       | Apache 2.0    |
| CI/CD              | GitHub Actions                      | N/A       | Free tier     |
| Web Server         | NGINX                               | 1.24+     | BSD           |
| App Server         | Gunicorn                            | 21+       | MIT           |

## 10.2 Glossary

| Term                  | Definition                                                         |
|-----------------------|--------------------------------------------------------------------|
| Ticket                | A formal record of a service request or reported issue             |
| Incident              | An unplanned interruption to a service or reduction in quality     |
| Problem               | The underlying cause of one or more incidents                      |
| Knowledge Article     | A document providing information or solutions for common issues    |
| SLA                   | An agreement defining expected service response and resolution times|
| RAG                   | A technique combining information retrieval with LLM generation    |
| Embedding             | A dense vector representation of text for semantic similarity      |
| Chunk                 | A segment of a document used for embedding and retrieval           |
| Confidence Score      | A numerical measure (0-1) of AI prediction certainty              |
| CSAT                  | Customer Satisfaction score                                        |

## 10.3 Document Cross-References

| Document                      | ID           | Status          |
|-------------------------------|--------------|-----------------|
| Architecture Design Document  | IDAI-ARCH-001| Planned         |
| Database Design Document      | IDAI-DB-001  | Planned         |
| API Specification              | IDAI-API-001 | Planned         |
| UI/UX Wireframes              | IDAI-UX-001  | Planned         |
| Development Roadmap           | IDAI-ROAD-001| Planned         |
| Testing Strategy              | IDAI-TEST-001| Planned         |
| Deployment Guide              | IDAI-DEPL-001| Planned         |
| Security Assessment           | IDAI-SEC-001 | Planned         |

---

*End of Software Requirement Specification*

*Document ID: IDAI-SRS-001 | Version: 1.0 | Classification: Internal*
