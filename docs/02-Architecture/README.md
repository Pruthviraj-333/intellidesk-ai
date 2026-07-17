# IntelliDesk AI — Architecture Design Document

**Document ID:** IDAI-ARCH-001 | **Version:** 1.0 | **Date:** 

---

## Document Index

| # | Section | File |
|---|---------|------|
| 1 | System Architecture & Component Design | [01-system-architecture.md](./01-system-architecture.md) |
| 2 | Backend Architecture (Clean Architecture) | [02-backend-architecture.md](./02-backend-architecture.md) |
| 3 | Frontend Architecture | [03-frontend-architecture.md](./03-frontend-architecture.md) |
| 4 | AI & RAG Architecture | [04-ai-architecture.md](./04-ai-architecture.md) |
| 5 | Infrastructure & DevOps | [05-infrastructure.md](./05-infrastructure.md) |
| 6 | Project Folder Structure | [06-folder-structure.md](./06-folder-structure.md) |

## Key Decisions Applied

| Decision | Choice |
|----------|--------|
| Email | Gmail SMTP |
| Real-time | WebSockets (Flask-SocketIO) with polling fallback |
| Ticket ID | TKT-YYYYMMDD-XXXX |
| SLA | Default targets confirmed |
| ML Strategy | LLM-based prediction only for v1.0 |
