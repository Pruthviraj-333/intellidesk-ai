# IntelliDesk AI — Tech Stack Justification

**Document ID:** IDAI-TECH-001 | **Version:** 1.0 | **Date:** 

---

## Backend

### Python 3.11+
**Why:** Industry-standard for backend AI/ML systems. Mature ecosystem for Flask, SQLAlchemy, Celery, and all ML libraries. Strong typing support with 3.11+ improvements. Expected in all target job roles.

### Flask 3.x
**Why over Django:** Flask is intentionally micro — perfect for Clean Architecture where we control every layer. Django's ORM and admin force patterns that conflict with our Repository/Service design. Flask scales via Blueprints without fighting the framework. Lightweight means faster cold starts on free-tier hosting.  
**Why over FastAPI:** FastAPI is excellent but Flask has broader adoption at enterprise companies. Flask's ecosystem (JWT-Extended, SocketIO, Migrate, Limiter) is more mature. Flask-SocketIO is needed for WebSocket support.

### SQLAlchemy 2.x + Alembic
**Why:** Industry-standard Python ORM. SQLAlchemy 2.0 introduced a cleaner declarative API with proper type hints. Alembic provides version-controlled migrations — essential for production databases. Repository Pattern maps naturally to SQLAlchemy session management.

### PostgreSQL 16
**Why over MySQL/SQLite:** PostgreSQL's `JSONB`, `TSVECTOR` (full-text search), `INET`, and window functions are used directly in this project. `tsvector` eliminates a separate search engine for knowledge base search. `JSONB` stores AI metadata, permissions, and settings efficiently. PostgreSQL 16's performance improvements benefit analytical queries.

### Redis 7
**Why:** Dual purpose — Celery message broker AND application cache. Token blacklisting for JWT logout. Rate limiting state storage. Fast in-memory reads for dashboard caching. Free tier available on Render/Railway.

### Flask-JWT-Extended
**Why:** Purpose-built JWT library for Flask. Handles access + refresh token pattern, blacklisting, and `current_user` injection. More opinionated than PyJWT alone — reduces security implementation mistakes.

### Celery 5 + Redis Broker
**Why:** The only mature Python distributed task queue. Essential for: async document processing (embedding is slow), email sending, report generation, scheduled SLA checks. RedBeat scheduler for persistent beat scheduling.

### Marshmallow 3
**Why over Pydantic:** Marshmallow is Flask-native and integrates seamlessly with SQLAlchemy via `flask-marshmallow`. Excellent for both request validation and response serialization. Pydantic is better with FastAPI; Marshmallow is the right tool for Flask.

### Flask-SocketIO + python-socketio
**Why:** Real-time WebSocket support with automatic polling fallback. Room-based broadcasting fits our department/user notification model. Works with Gunicorn eventlet workers.

### Gunicorn + eventlet
**Why:** Production WSGI server for Flask. `eventlet` worker class required for SocketIO. Stable, widely deployed, Render-compatible.

---

## AI Stack

### Groq API (Primary LLM)
**Why:** Groq's LPU hardware delivers inference 10-25x faster than GPU-based providers. Free tier includes ~14,400 requests/day. `llama-3.3-70b-versatile` is competitive with GPT-4 class models. Zero cost for portfolio demonstration.

### Llama 3.3 70B (Primary Model)
**Why:** Meta's open-weight model — strong reasoning, instruction following, and JSON output. 70B parameters provide GPT-4-class quality. Available on Groq free tier. Fallback: `llama-3.1-8b-instant` for faster/simpler tasks.

### sentence-transformers/all-MiniLM-L6-v2
**Why:** Free, locally-run embedding model. 384-dimension vectors are compact (less storage, faster search). Strong semantic similarity performance for its size. No API calls needed — runs on CPU. Apache 2.0 license. Widely used in production RAG systems.

### ChromaDB
**Why over FAISS:** ChromaDB offers a server mode, persistent storage, metadata filtering, and a Python client — production-ready out of the box. FAISS requires more boilerplate for persistence. ChromaDB's collection model maps perfectly to our document/article/ticket segmentation. Apache 2.0 license, actively maintained.

---

## Frontend

### React 18 + TypeScript
**Why:** Industry-standard SPA framework. TypeScript eliminates entire classes of runtime bugs. React 18 concurrent features (useTransition, Suspense) improve perceived performance. Expected skill in all frontend/full-stack job roles.

### Vite 5
**Why over Create React App:** Vite's native ESM dev server starts in <1 second vs CRA's webpack minutes. Hot Module Replacement is near-instant. Production builds are faster. CRA is deprecated. Vite is the current industry standard.

### TailwindCSS 3
**Why:** Utility-first CSS eliminates dead CSS, component isolation is natural, dark mode via `dark:` variant is trivial. Design system via `tailwind.config.ts` (colors, fonts, spacing). No CSS-in-JS runtime overhead.

### Redux Toolkit 2
**Why:** Minimal boilerplate Redux. Used only for global client state (auth tokens, theme). RTK's `createSlice` and `createAsyncThunk` are the official Redux patterns. DevTools integration for debugging.

### TanStack Query (React Query) 5
**Why:** Server state management done right. Automatic caching, background refetching, stale-while-revalidate, pagination, and optimistic updates. Eliminates manual loading/error state management. Pairs perfectly with Redux — Redux for client state, React Query for server state.

### React Router v6
**Why:** Official React routing solution. Nested routes, loader/action patterns, and `createBrowserRouter` are modern and clean. Used in virtually every React enterprise project.

### Axios
**Why over fetch:** Interceptors for JWT attachment and auto-refresh. Request cancellation. Better error handling. Request/response transformation. TypeScript generics for typed responses.

### Chart.js + react-chartjs-2
**Why over Recharts/Victory:** Chart.js is the most widely used charting library. Excellent performance with large datasets. Supports all required chart types. `react-chartjs-2` provides clean React bindings.

---

## DevOps & Infrastructure

### Docker + Docker Compose
**Why:** Eliminates "works on my machine" issues. Single command to start the full stack locally. Production parity. Free, open-source, universally expected in enterprise roles. Multi-stage builds keep images small.

### GitHub Actions
**Why:** Free for public repositories. Tight GitHub integration. Extensive marketplace of actions. Used by virtually all companies. Demonstrates CI/CD competency.

### NGINX
**Why:** Production-grade reverse proxy. Handles SSL termination, static file serving, rate limiting at the network level, WebSocket proxying, and load balancing. Free, open-source, industry standard.

### Render (Backend)
**Why:** Free tier for Docker deployments. PostgreSQL addon. Auto-deploy from GitHub. No credit card required. Closer to real production than Heroku's limited free tier.

### Vercel (Frontend)
**Why:** Zero-config React deployment. Automatic preview deployments per branch. Global CDN edge network. Free for hobby projects. Professional-grade performance.

### Neon PostgreSQL
**Why:** Free serverless PostgreSQL with 0.5GB storage. Branching feature for dev/staging. Standard PostgreSQL 16 — no vendor lock-in. Hibernates when idle (perfect for demo).

---

## Summary: Free Technology Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| LLM Inference | Groq API | Free tier |
| Embedding Model | sentence-transformers (local) | Free |
| Vector Database | ChromaDB (self-hosted) | Free |
| Primary Database | Neon PostgreSQL | Free tier |
| Cache + Queue | Redis (Docker) | Free |
| Object Storage | Cloudinary | Free tier (25 credits/mo) |
| Backend Hosting | Render | Free tier |
| Frontend Hosting | Vercel | Free tier |
| CI/CD | GitHub Actions | Free for public repos |
| All frameworks | Open-source (MIT/Apache/BSD) | Free |
| **Total** | | **$0/month** |
