# 1. System Architecture

## 1.1 Architecture Style

IntelliDesk AI uses a **Layered Monolith** architecture with clear module boundaries. This provides:
- Simplicity of deployment (single backend process)
- Clean separation via Flask Blueprints (each module = 1 Blueprint)
- Easy migration path to microservices if needed later

## 1.2 System Context Diagram

```
                    ┌─────────────────────┐
                    │     End Users        │
                    │  (Browser Clients)   │
                    └──────────┬──────────┘
                               │ HTTPS
                    ┌──────────▼──────────┐
                    │       NGINX         │
                    │   (Reverse Proxy)   │
                    │   SSL Termination   │
                    │   Static Files      │
                    │   Rate Limiting     │
                    └───┬─────────────┬───┘
                        │             │
              ┌─────────▼───┐   ┌────▼──────────┐
              │   React     │   │   Flask API    │
              │   Frontend  │   │   (Gunicorn)   │
              │   (Vercel)  │   │   (Render)     │
              └─────────────┘   └──┬──┬──┬──┬───┘
                                   │  │  │  │
                 ┌─────────────────┘  │  │  └──────────────────┐
                 │           ┌────────┘  └────────┐            │
          ┌──────▼─────┐ ┌──▼──────┐  ┌──────────▼──┐  ┌──────▼──────┐
          │ PostgreSQL │ │  Redis  │  │   ChromaDB  │  │  Groq API   │
          │   (Neon)   │ │ (Cache  │  │  (Vectors)  │  │  (LLM)      │
          │            │ │ +Broker)│  │             │  │             │
          └────────────┘ └────┬────┘  └─────────────┘  └─────────────┘
                              │
                       ┌──────▼──────┐
                       │   Celery    │
                       │   Workers   │
                       │             │
                       │ - Email     │
                       │ - Doc Proc  │
                       │ - Reports   │
                       │ - AI Tasks  │
                       └─────────────┘
```

## 1.3 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FLASK APPLICATION                              │
│                                                                         │
│  ┌──── BLUEPRINTS (Controller Layer) ──────────────────────────────┐   │
│  │                                                                  │   │
│  │  /api/v1/auth     → AuthController                              │   │
│  │  /api/v1/users    → UserController                              │   │
│  │  /api/v1/tickets  → TicketController                            │   │
│  │  /api/v1/incidents→ IncidentController                          │   │
│  │  /api/v1/problems → ProblemController                           │   │
│  │  /api/v1/articles → ArticleController                           │   │
│  │  /api/v1/ai       → AIController                                │   │
│  │  /api/v1/documents→ DocumentController                          │   │
│  │  /api/v1/analytics→ AnalyticsController                         │   │
│  │  /api/v1/reports  → ReportController                            │   │
│  │  /api/v1/departments → DepartmentController                     │   │
│  │  /api/v1/projects → ProjectController                           │   │
│  │  /api/v1/notifications → NotificationController                 │   │
│  │  /api/v1/admin    → AdminController                             │   │
│  │  /api/v1/health   → HealthController                            │   │
│  │                                                                  │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                           │
│  ┌──── SERVICE LAYER ───────▼──────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  AuthService          TicketService        IncidentService      │   │
│  │  UserService          CommentService       ProblemService       │   │
│  │  AIService            KnowledgeService     DocumentService      │   │
│  │  RAGService           AnalyticsService     ReportService        │   │
│  │  NotificationService  DepartmentService    ProjectService       │   │
│  │  AuditService         SettingsService      HealthService        │   │
│  │  PromptService        EmailService                              │   │
│  │                                                                  │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                           │
│  ┌──── REPOSITORY LAYER ───▼──────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  UserRepository       TicketRepository     IncidentRepository   │   │
│  │  CommentRepository    ArticleRepository    DocumentRepository   │   │
│  │  NotificationRepo     DepartmentRepo       ProjectRepository   │   │
│  │  AuditLogRepository   SettingsRepository   PromptRepository    │   │
│  │  ProblemRepository    VectorRepository (ChromaDB)              │   │
│  │                                                                  │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                           │
│  ┌──── MODEL LAYER ────────▼──────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  User, Role, Ticket, Comment, Incident, IncidentTimeline,      │   │
│  │  Problem, ProblemNote, Article, ArticleVersion, Document,      │   │
│  │  DocumentChunk, Department, Project, Notification, AuditLog,   │   │
│  │  AIConversation, AIMessage, PromptTemplate, Setting            │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──── CROSS-CUTTING ──────────────────────────────────────────────┐   │
│  │  DTOs (Marshmallow)  │  Auth Decorators  │  Error Handlers     │   │
│  │  Logging             │  Rate Limiting    │  CORS               │   │
│  │  Config              │  Extensions       │  Middleware          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 1.4 Technology Integration Map

| Component | Technology | Protocol | Port | Purpose |
|-----------|-----------|----------|------|---------|
| Web Server | NGINX | HTTP/HTTPS | 80/443 | Reverse proxy, SSL, static files |
| App Server | Gunicorn | WSGI | 8000 | Flask application server |
| Database | PostgreSQL | TCP | 5432 | Primary data storage |
| Cache | Redis | TCP | 6379 | Caching, session store, Celery broker |
| Vector DB | ChromaDB | HTTP | 8001 | Embedding storage and similarity search |
| Task Queue | Celery | AMQP (Redis) | — | Background job processing |
| LLM | Groq API | HTTPS | 443 | AI inference (external) |
| Email | Gmail SMTP | SMTP/TLS | 587 | Email notifications |
| Storage | Cloudinary | HTTPS | 443 | File/document storage (external) |
| WebSocket | Flask-SocketIO | WS | 8000 | Real-time dashboard updates |
| Frontend | Vite Dev / Vercel | HTTP | 5173 | React SPA |

## 1.5 Request Flow (Sequence)

```
Browser → NGINX → Gunicorn → Flask App
                                 │
                    ┌────────────▼────────────┐
                    │    Middleware Stack      │
                    │  1. CORS                │
                    │  2. Request Logging     │
                    │  3. Rate Limiting       │
                    │  4. JWT Validation      │
                    │  5. Request ID Gen      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Blueprint Router     │
                    │  Route → Controller     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Controller           │
                    │  1. Parse request       │
                    │  2. Validate via DTO    │
                    │  3. Call service        │
                    │  4. Format response     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Service              │
                    │  1. Business logic      │
                    │  2. Authorization check │
                    │  3. Call repository     │
                    │  4. Call external APIs  │
                    │  5. Emit events         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Repository           │
                    │  1. Build query         │
                    │  2. Execute via ORM     │
                    │  3. Return model(s)     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Response             │
                    │  1. Serialize via DTO   │
                    │  2. Wrap in envelope    │
                    │  3. Set status code     │
                    │  4. Return JSON         │
                    └─────────────────────────┘
```

## 1.6 Authentication Flow

```
┌─── LOGIN ─────────────────────────────────────────────────┐
│                                                            │
│  Client                    Server                          │
│    │  POST /api/v1/auth/login                              │
│    │  { email, password }                                  │
│    │ ──────────────────────▶│                               │
│    │                        │ Validate credentials         │
│    │                        │ Check account status          │
│    │                        │ Generate access_token (15m)   │
│    │                        │ Generate refresh_token (7d)   │
│    │                        │ Log audit event               │
│    │  { access_token,       │                               │
│    │    refresh_token,      │                               │
│    │    user }              │                               │
│    │ ◀──────────────────────│                               │
│    │                                                       │
│    │  Store tokens (httpOnly cookie or localStorage)       │
│                                                            │
└────────────────────────────────────────────────────────────┘

┌─── AUTHENTICATED REQUEST ─────────────────────────────────┐
│                                                            │
│  Client                    Server                          │
│    │  GET /api/v1/tickets                                  │
│    │  Authorization: Bearer <access_token>                 │
│    │ ──────────────────────▶│                               │
│    │                        │ Decode JWT                    │
│    │                        │ Verify signature & expiry     │
│    │                        │ Check blacklist (Redis)       │
│    │                        │ Load user & role              │
│    │                        │ Check RBAC permissions        │
│    │                        │ Process request               │
│    │  200 { data }          │                               │
│    │ ◀──────────────────────│                               │
│                                                            │
└────────────────────────────────────────────────────────────┘

┌─── TOKEN REFRESH ─────────────────────────────────────────┐
│                                                            │
│  Client                    Server                          │
│    │  POST /api/v1/auth/refresh                            │
│    │  { refresh_token }                                    │
│    │ ──────────────────────▶│                               │
│    │                        │ Validate refresh token        │
│    │                        │ Check blacklist               │
│    │                        │ Blacklist old refresh token   │
│    │                        │ Issue new access + refresh    │
│    │  { access_token,       │                               │
│    │    refresh_token }     │                               │
│    │ ◀──────────────────────│                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## 1.7 WebSocket Architecture (Real-Time)

```
┌─── DASHBOARD REAL-TIME UPDATES ───────────────────────────┐
│                                                            │
│  Client (React)             Server (Flask-SocketIO)        │
│    │                              │                        │
│    │  connect(token)              │                        │
│    │ ────────────────────────────▶│ Validate JWT           │
│    │                              │ Join room: user_{id}   │
│    │                              │ Join room: dept_{id}   │
│    │  connected ✓                 │                        │
│    │ ◀────────────────────────────│                        │
│    │                              │                        │
│    │      ... ticket gets updated by another user ...      │
│    │                              │                        │
│    │  event: ticket_updated       │                        │
│    │  { ticket_id, status, ... }  │                        │
│    │ ◀────────────────────────────│                        │
│    │                              │                        │
│    │  event: notification         │                        │
│    │  { message, type, ... }      │                        │
│    │ ◀────────────────────────────│                        │
│    │                              │                        │
│    │  event: dashboard_refresh    │                        │
│    │  { kpi_data }                │                        │
│    │ ◀────────────────────────────│                        │
│                                                            │
└────────────────────────────────────────────────────────────┘

Events emitted by server:
  - ticket_created, ticket_updated, ticket_assigned
  - incident_created, incident_updated
  - notification_new
  - dashboard_refresh (every 30 seconds)
  - sla_warning, sla_breach
```
