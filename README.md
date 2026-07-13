# IntelliDesk AI

> **AI-Powered Enterprise Service Desk & Incident Management Platform**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## What is IntelliDesk AI?

IntelliDesk AI is a production-grade enterprise IT Service Management (ITSM) platform combining:

- **Full ticket lifecycle management** — Create, assign, escalate, resolve, close with SLA tracking
- **ITIL-aligned incident & problem management** — Root cause analysis, timeline tracking
- **AI-powered automation** — Auto-classification, priority prediction, department routing via Groq LLM
- **RAG knowledge retrieval** — Upload PDFs/DOCX → chunk → embed → query with citations
- **Conversational AI assistant** — Context-aware chat with knowledge base and document search
- **Business intelligence dashboards** — Real-time KPIs, charts, SLA compliance, agent performance
- **Enterprise RBAC** — 5-tier role system (Super Admin → Employee) with JWT authentication
- **WebSocket real-time updates** — Live dashboard and notifications via Socket.IO

Inspired by: ServiceNow · Jira Service Management · Zendesk · Freshservice · Microsoft Copilot

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, Flask 3, SQLAlchemy 2, Alembic, Marshmallow, Flask-JWT-Extended |
| **Task Queue** | Celery 5, Redis 7, Celery Beat |
| **Real-time** | Flask-SocketIO (WebSockets) |
| **Database** | PostgreSQL 16 (Neon) |
| **Vector DB** | ChromaDB |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 (local) |
| **LLM** | Groq API (Llama 3.3 70B) |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **State** | Redux Toolkit + TanStack Query |
| **Charts** | Chart.js + react-chartjs-2 |
| **Infra** | Docker, Docker Compose, NGINX, Gunicorn |
| **CI/CD** | GitHub Actions |
| **Hosting** | Render (API) + Vercel (Frontend) + Neon (DB) |

**Total infrastructure cost: $0/month**

---

## Architecture

```
Browser → NGINX → Gunicorn (Flask)
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   PostgreSQL        Redis        ChromaDB
   (Neon)         (Cache+Queue)  (Vectors)
                       │
                    Celery
                    Workers
                       │
                  Groq API (LLM)
```

Clean Architecture: **Controller → Service → Repository → Model**  
AI Provider Abstraction: **Strategy Pattern** (Groq primary, swappable)

---

## Documentation

All design documents are in the `docs/` folder:

| Document | Path |
|----------|------|
| Software Requirement Specification | [docs/01-SRS/](./docs/01-SRS/README.md) |
| Architecture Design | [docs/02-Architecture/](./docs/02-Architecture/README.md) |
| Database Design | [docs/03-Database/](./docs/03-Database/database-design.md) |
| API Specification | [docs/04-API/](./docs/04-API/README.md) |
| Development Roadmap | [docs/06-Roadmap/](./docs/06-Roadmap/development-roadmap.md) |
| Tech Stack Justification | [docs/07-TechStack/](./docs/07-TechStack/tech-stack-justification.md) |

---

## Quick Start (Local Development)

### Prerequisites
- Docker Desktop
- Git
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/intellidesk-ai.git
cd intellidesk-ai

# Copy environment file
cp .env.example .env
# Edit .env and add your GROQ_API_KEY, GMAIL credentials, etc.

# Build and start all services
make build
make up

# Run database migrations and seed data
make migrate
make seed

# Access the application
# Frontend: http://localhost (via NGINX)
# API:      http://localhost/api/v1
# API Docs: http://localhost/api/v1/docs
# Flower:   http://localhost:5555
```

### Default Credentials (after seed)
| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@intellidesk.ai | Admin@123! |
| Manager | manager@intellidesk.ai | Manager@123! |
| Agent | agent@intellidesk.ai | Agent@123! |
| Employee | employee@intellidesk.ai | Employee@123! |

---

## Key Features Demonstrated

### For Software Engineer / Backend Roles
- Clean Architecture (Controller → Service → Repository → DTO → Model)
- Flask Blueprint-based modular API design
- SQLAlchemy ORM with complex queries, relationships, and migrations
- JWT authentication with refresh token rotation and blacklisting
- Celery async task processing with multiple queues
- WebSocket real-time events with Flask-SocketIO
- Rate limiting, input validation, error handling
- Comprehensive test suite (unit + integration)

### For AI / ML Engineer Roles
- LLM provider abstraction (Strategy Pattern) — Groq with swappable interface
- RAG pipeline: text extraction → chunking → embedding → vector search → LLM generate
- Structured JSON output from LLMs
- Streaming LLM responses via SSE
- Prompt template management system
- Semantic similarity search with confidence scoring
- Citation and source attribution in AI responses

### For Full Stack / React Roles
- React 18 SPA with TypeScript
- Redux Toolkit + TanStack Query hybrid state management
- JWT interceptors with auto-refresh token rotation
- WebSocket client with reconnection logic
- Feature-based modular architecture
- Comprehensive shared component library
- Dark/light mode with system preference detection

### For DevOps Roles
- Multi-stage Docker builds (dev + prod targets)
- Docker Compose multi-service orchestration
- NGINX as reverse proxy with rate limiting and WebSocket support
- GitHub Actions CI/CD (lint → test → deploy)
- Health check endpoints for all services
- Environment-based configuration
- Structured JSON logging with correlation IDs

---

## API Documentation

Interactive Swagger UI available at: `http://localhost/api/v1/docs`

Or import the OpenAPI spec from: `docs/04-API/openapi.yaml`

---

## Project Structure

```
intellidesk-ai/
├── backend/          # Flask Python API (Clean Architecture)
├── frontend/         # React TypeScript SPA
├── nginx/            # NGINX configuration
├── docs/             # Complete design documentation
├── .github/          # GitHub Actions CI/CD
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

---

## License

MIT License — see [LICENSE](./LICENSE)

---

*Built as a portfolio project demonstrating production-grade enterprise software engineering.*  
*Every design decision documented. Every technology justified. Every pattern intentional.*
