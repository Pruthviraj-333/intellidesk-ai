# 6. Project Folder Structure

## 6.1 Root Repository Layout

```
intellidesk-ai/                         # Root repository
├── backend/                            # Flask Python API
├── frontend/                           # React TypeScript SPA
├── nginx/                              # NGINX configuration
├── docs/                               # All documentation
│   ├── 01-SRS/                         # Software Requirement Specification
│   ├── 02-Architecture/                # Architecture Design Documents
│   ├── 03-Database/                    # DB schema and ER diagrams
│   ├── 04-API/                         # OpenAPI specification
│   ├── 05-Wireframes/                  # UI wireframes
│   └── 06-Roadmap/                     # Development roadmap
├── .github/
│   └── workflows/
│       └── ci-cd.yml                   # GitHub Actions CI/CD
├── docker-compose.yml                  # Full stack local setup
├── docker-compose.prod.yml             # Production overrides
├── .env.example                        # Environment variable template
├── Makefile                            # Developer convenience commands
└── README.md                           # Project README
```

## 6.2 Backend Folder Structure

```
backend/
├── app/
│   ├── __init__.py                     # Application factory (create_app)
│   ├── extensions.py                   # Flask extensions (db, jwt, socketio...)
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                 # BaseConfig, DevelopmentConfig, ProductionConfig
│   │
│   ├── models/                         # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                     # TimestampMixin, SoftDeleteMixin
│   │   ├── user.py                     # User, Role models
│   │   ├── ticket.py                   # Ticket, Comment, Attachment
│   │   ├── incident.py                 # Incident, IncidentTimeline
│   │   ├── problem.py                  # Problem, ProblemNote
│   │   ├── knowledge.py                # Article, ArticleVersion, Tag
│   │   ├── document.py                 # Document, DocumentChunk
│   │   ├── department.py               # Department
│   │   ├── project.py                  # Project
│   │   ├── notification.py             # Notification
│   │   ├── audit_log.py                # AuditLog
│   │   ├── ai_conversation.py          # AIConversation, AIMessage
│   │   ├── prompt_template.py          # PromptTemplate
│   │   └── setting.py                  # Setting (key-value store)
│   │
│   ├── repositories/                   # Data access layer
│   │   ├── __init__.py
│   │   ├── base_repository.py          # Generic CRUD base class
│   │   ├── user_repository.py
│   │   ├── ticket_repository.py
│   │   ├── incident_repository.py
│   │   ├── problem_repository.py
│   │   ├── article_repository.py
│   │   ├── document_repository.py
│   │   ├── department_repository.py
│   │   ├── project_repository.py
│   │   ├── notification_repository.py
│   │   ├── audit_log_repository.py
│   │   ├── ai_conversation_repository.py
│   │   ├── prompt_repository.py
│   │   ├── setting_repository.py
│   │   └── vector_repository.py        # ChromaDB operations
│   │
│   ├── services/                       # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py             # Registration, login, token management
│   │   ├── user_service.py             # User CRUD, role management
│   │   ├── ticket_service.py           # Ticket lifecycle management
│   │   ├── comment_service.py          # Ticket comments and replies
│   │   ├── incident_service.py         # Incident management
│   │   ├── problem_service.py          # Problem management
│   │   ├── article_service.py          # Knowledge base articles
│   │   ├── document_service.py         # Document upload and management
│   │   ├── rag_service.py              # RAG pipeline orchestration
│   │   ├── analytics_service.py        # KPIs, charts, metrics
│   │   ├── report_service.py           # Report generation
│   │   ├── department_service.py       # Department management
│   │   ├── project_service.py          # Project management
│   │   ├── notification_service.py     # In-app and email notifications
│   │   ├── email_service.py            # Gmail SMTP integration
│   │   ├── audit_service.py            # Audit log creation
│   │   ├── settings_service.py         # System settings management
│   │   ├── health_service.py           # Service health checks
│   │   └── ai/
│   │       ├── __init__.py
│   │       ├── ticket_ai_service.py    # Ticket classification, routing, summary
│   │       ├── chat_ai_service.py      # Conversational chat with RAG
│   │       ├── prompt_service.py       # Prompt template management
│   │       └── embedding_service.py    # Text embedding generation
│   │
│   ├── controllers/                    # Flask Blueprint controllers
│   │   ├── __init__.py
│   │   ├── auth_controller.py          # /api/v1/auth/*
│   │   ├── user_controller.py          # /api/v1/users/*
│   │   ├── ticket_controller.py        # /api/v1/tickets/*
│   │   ├── incident_controller.py      # /api/v1/incidents/*
│   │   ├── problem_controller.py       # /api/v1/problems/*
│   │   ├── article_controller.py       # /api/v1/articles/*
│   │   ├── ai_controller.py            # /api/v1/ai/*
│   │   ├── document_controller.py      # /api/v1/documents/*
│   │   ├── analytics_controller.py     # /api/v1/analytics/*
│   │   ├── report_controller.py        # /api/v1/reports/*
│   │   ├── department_controller.py    # /api/v1/departments/*
│   │   ├── project_controller.py       # /api/v1/projects/*
│   │   ├── notification_controller.py  # /api/v1/notifications/*
│   │   ├── admin_controller.py         # /api/v1/admin/*
│   │   └── health_controller.py        # /api/v1/health/*
│   │
│   ├── dtos/                           # Marshmallow request/response schemas
│   │   ├── __init__.py
│   │   ├── auth_dto.py
│   │   ├── user_dto.py
│   │   ├── ticket_dto.py
│   │   ├── incident_dto.py
│   │   ├── problem_dto.py
│   │   ├── article_dto.py
│   │   ├── document_dto.py
│   │   ├── ai_dto.py
│   │   ├── analytics_dto.py
│   │   ├── department_dto.py
│   │   ├── project_dto.py
│   │   ├── notification_dto.py
│   │   └── admin_dto.py
│   │
│   ├── ai/                             # AI provider abstraction layer
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # LLMProvider abstract base class
│   │   │   ├── groq_provider.py        # Groq API implementation
│   │   │   └── factory.py              # Provider factory
│   │   └── prompts/
│   │       └── defaults.py             # Default prompt templates (seed data)
│   │
│   ├── tasks/                          # Celery async tasks
│   │   ├── __init__.py
│   │   ├── email_tasks.py              # Send emails async
│   │   ├── document_tasks.py           # Document processing pipeline
│   │   ├── ai_tasks.py                 # Background AI operations
│   │   ├── report_tasks.py             # Report generation
│   │   ├── sla_tasks.py                # SLA monitoring and alerts
│   │   └── maintenance_tasks.py        # Cleanup and maintenance
│   │
│   ├── utils/                          # Cross-cutting utilities
│   │   ├── __init__.py
│   │   ├── decorators.py               # @jwt_required, @role_required, @validate_input
│   │   ├── response.py                 # Response envelope helpers
│   │   ├── exceptions.py               # Custom exception classes
│   │   ├── constants.py                # Enums: TicketStatus, Priority, UserRole...
│   │   ├── helpers.py                  # ID generation, slugs, formatters
│   │   ├── validators.py               # Email, password, file validators
│   │   ├── logger.py                   # Structured JSON logger
│   │   ├── pagination.py               # Pagination helper
│   │   └── file_handler.py             # File upload / Cloudinary helper
│   │
│   └── sockets/                        # Flask-SocketIO event handlers
│       ├── __init__.py
│       ├── connection.py               # Connect/disconnect handlers
│       └── events.py                   # Event emitter helpers
│
├── migrations/                         # Alembic migration files
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── conftest.py                     # Fixtures (test app, test db, auth headers)
│   ├── unit/
│   │   ├── services/
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_ticket_service.py
│   │   │   └── test_ai_service.py
│   │   ├── repositories/
│   │   │   └── test_ticket_repository.py
│   │   └── utils/
│   │       └── test_helpers.py
│   └── integration/
│       ├── test_auth_api.py
│       ├── test_tickets_api.py
│       ├── test_ai_api.py
│       └── test_health_api.py
│
├── Dockerfile
├── requirements.txt                    # Production dependencies
├── requirements-dev.txt                # Dev/test dependencies
├── .flake8                             # Flake8 config
├── pyproject.toml                      # Black, isort config
└── wsgi.py                             # Gunicorn entry point
```

## 6.3 Frontend Folder Structure

```
frontend/
├── public/
│   ├── favicon.ico
│   ├── logo.svg
│   └── robots.txt
│
├── src/
│   ├── main.tsx                        # React app entry point
│   ├── App.tsx                         # Root component with router
│   ├── vite-env.d.ts
│   │
│   ├── app/
│   │   ├── store.ts                    # Redux store configuration
│   │   ├── router.tsx                  # React Router configuration
│   │   └── queryClient.ts             # React Query client setup
│   │
│   ├── features/                       # Feature-based modules
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── RegisterForm.tsx
│   │   │   │   └── ForgotPasswordForm.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useLogin.ts
│   │   │   │   └── useRegister.ts
│   │   │   ├── services/
│   │   │   │   └── authApi.ts
│   │   │   ├── store/
│   │   │   │   └── authSlice.ts        # JWT tokens, current user
│   │   │   ├── types/
│   │   │   │   └── auth.types.ts
│   │   │   └── pages/
│   │   │       ├── LoginPage.tsx
│   │   │       ├── RegisterPage.tsx
│   │   │       └── ForgotPasswordPage.tsx
│   │   │
│   │   ├── dashboard/
│   │   │   ├── components/
│   │   │   │   ├── KPIGrid.tsx
│   │   │   │   ├── TicketTrendChart.tsx
│   │   │   │   ├── DepartmentPerformance.tsx
│   │   │   │   ├── RecentTickets.tsx
│   │   │   │   └── SLAComplianceChart.tsx
│   │   │   ├── hooks/
│   │   │   │   └── useDashboard.ts
│   │   │   ├── services/
│   │   │   │   └── analyticsApi.ts
│   │   │   └── pages/
│   │   │       └── DashboardPage.tsx
│   │   │
│   │   ├── tickets/
│   │   │   ├── components/
│   │   │   │   ├── TicketList.tsx
│   │   │   │   ├── TicketTable.tsx
│   │   │   │   ├── TicketFilters.tsx
│   │   │   │   ├── TicketDetail.tsx
│   │   │   │   ├── TicketForm.tsx
│   │   │   │   ├── TicketComments.tsx
│   │   │   │   ├── TicketTimeline.tsx
│   │   │   │   ├── TicketAISidebar.tsx  # AI suggestions panel
│   │   │   │   └── SLATimer.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useTickets.ts
│   │   │   │   ├── useTicket.ts
│   │   │   │   └── useTicketMutations.ts
│   │   │   ├── services/
│   │   │   │   └── ticketApi.ts
│   │   │   ├── types/
│   │   │   │   └── ticket.types.ts
│   │   │   └── pages/
│   │   │       ├── TicketListPage.tsx
│   │   │       ├── TicketDetailPage.tsx
│   │   │       └── CreateTicketPage.tsx
│   │   │
│   │   ├── incidents/
│   │   ├── problems/
│   │   ├── knowledge-base/
│   │   ├── ai-assistant/
│   │   │   ├── components/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── ChatMessage.tsx      # With citation rendering
│   │   │   │   ├── ChatInput.tsx
│   │   │   │   └── SuggestedQuestions.tsx
│   │   │   └── pages/
│   │   │       └── AIChatPage.tsx
│   │   ├── analytics/
│   │   ├── documents/
│   │   ├── notifications/
│   │   ├── admin/
│   │   └── profile/
│   │
│   ├── components/                     # Shared component library
│   │   ├── ui/
│   │   ├── layout/
│   │   ├── data-display/
│   │   ├── charts/
│   │   └── guards/
│   │       ├── AuthGuard.tsx           # Redirects unauthenticated users
│   │       └── RoleGuard.tsx           # Restricts by role
│   │
│   ├── hooks/                          # Global custom hooks
│   │   ├── useAuth.ts                  # Auth state helpers
│   │   ├── useSocket.ts                # WebSocket connection
│   │   ├── useToast.ts                 # Toast notifications
│   │   ├── useTheme.ts                 # Dark/light mode
│   │   └── usePagination.ts           # Pagination state
│   │
│   ├── services/
│   │   ├── apiClient.ts                # Axios instance + interceptors
│   │   └── socketClient.ts             # Socket.IO client
│   │
│   ├── store/
│   │   ├── index.ts                    # Redux store root
│   │   ├── authSlice.ts
│   │   └── uiSlice.ts                  # Theme, sidebar, modals
│   │
│   ├── types/
│   │   ├── api.types.ts                # Common API response types
│   │   └── common.types.ts
│   │
│   ├── utils/
│   │   ├── formatters.ts               # Date, number, duration formatters
│   │   ├── constants.ts                # Priority colors, status labels
│   │   └── validators.ts
│   │
│   └── styles/
│       └── globals.css                 # Global CSS + Tailwind directives
│
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── .eslintrc.cjs
├── .prettierrc
└── package.json
```

## 6.4 Makefile (Developer Commands)

```makefile
# Makefile

.PHONY: help build up down logs test lint migrate seed

help:
	@echo "IntelliDesk AI — Developer Commands"
	@echo "  make build     Build all Docker images"
	@echo "  make up        Start all services"
	@echo "  make down      Stop all services"
	@echo "  make logs      Tail all service logs"
	@echo "  make migrate   Run database migrations"
	@echo "  make seed      Seed database with demo data"
	@echo "  make test      Run backend test suite"
	@echo "  make lint      Run all linters"
	@echo "  make shell     Open backend Python shell"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

migrate:
	docker-compose exec backend flask db upgrade

seed:
	docker-compose exec backend flask seed-db

test:
	docker-compose exec backend pytest --cov=app -v

lint:
	docker-compose exec backend flake8 .
	docker-compose exec backend black . --check
	docker-compose exec frontend npm run lint

shell:
	docker-compose exec backend flask shell
```
