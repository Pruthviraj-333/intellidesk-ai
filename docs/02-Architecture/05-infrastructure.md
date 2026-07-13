# 5. Infrastructure & DevOps Architecture

## 5.1 Docker Compose Architecture

```
docker-compose.yml services:
┌─────────────────────────────────────────────────────┐
│                                                      │
│  nginx        → Port 80/443 (public entry point)    │
│  frontend     → Port 5173  (React dev server)       │
│  backend      → Port 8000  (Gunicorn/Flask)         │
│  postgres     → Port 5432  (PostgreSQL 16)          │
│  redis        → Port 6379  (Redis 7)                │
│  chromadb     → Port 8001  (ChromaDB server)        │
│  celery_worker→ (no port)  (Background jobs)        │
│  celery_beat  → (no port)  (Scheduled tasks)        │
│  flower       → Port 5555  (Celery monitoring)      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## 5.2 Docker Compose Configuration

```yaml
# docker-compose.yml

version: '3.9'

x-backend-env: &backend-env
  FLASK_ENV: ${FLASK_ENV:-development}
  DATABASE_URL: postgresql://intellidesk:${DB_PASSWORD}@postgres:5432/intellidesk
  REDIS_URL: redis://redis:6379/0
  CHROMA_HOST: chromadb
  CHROMA_PORT: 8001
  GROQ_API_KEY: ${GROQ_API_KEY}
  GROQ_MODEL: ${GROQ_MODEL:-llama-3.3-70b-versatile}
  SECRET_KEY: ${SECRET_KEY}
  JWT_SECRET_KEY: ${JWT_SECRET_KEY}
  GMAIL_USER: ${GMAIL_USER}
  GMAIL_APP_PASSWORD: ${GMAIL_APP_PASSWORD}
  CLOUDINARY_URL: ${CLOUDINARY_URL}

services:
  postgres:
    image: postgres:16-alpine
    container_name: intellidesk_postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: intellidesk
      POSTGRES_USER: intellidesk
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U intellidesk"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - "5432:5432"
    networks:
      - intellidesk_network

  redis:
    image: redis:7-alpine
    container_name: intellidesk_redis
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - "6379:6379"
    networks:
      - intellidesk_network

  chromadb:
    image: chromadb/chroma:latest
    container_name: intellidesk_chromadb
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      IS_PERSISTENT: "TRUE"
      ANONYMIZED_TELEMETRY: "FALSE"
    ports:
      - "8001:8000"
    networks:
      - intellidesk_network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: intellidesk_backend
    environment: *backend-env
    volumes:
      - ./backend:/app
      - media_data:/app/media
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - intellidesk_network
    command: >
      sh -c "flask db upgrade &&
             gunicorn --bind 0.0.0.0:8000
                      --workers 2
                      --worker-class eventlet
                      --timeout 120
                      'app:create_app()'"

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: intellidesk_celery_worker
    environment: *backend-env
    volumes:
      - ./backend:/app
      - media_data:/app/media
    depends_on:
      - backend
      - redis
    networks:
      - intellidesk_network
    command: celery -A app.celery worker --loglevel=info --queues=default,ai,email,reports

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: ${BUILD_TARGET:-development}
    container_name: intellidesk_celery_beat
    environment: *backend-env
    volumes:
      - ./backend:/app
    depends_on:
      - redis
    networks:
      - intellidesk_network
    command: celery -A app.celery beat --loglevel=info --scheduler=redbeat.RedBeatScheduler

  flower:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: intellidesk_flower
    environment: *backend-env
    ports:
      - "5555:5555"
    depends_on:
      - redis
    networks:
      - intellidesk_network
    command: celery -A app.celery flower --port=5555

  nginx:
    image: nginx:alpine
    container_name: intellidesk_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    networks:
      - intellidesk_network

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  media_data:

networks:
  intellidesk_network:
    driver: bridge
```

## 5.3 Backend Dockerfile

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download embedding model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; \
               SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

# Development target
FROM base AS development
ENV FLASK_ENV=development
EXPOSE 8000

# Production target
FROM base AS production
ENV FLASK_ENV=production
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser
EXPOSE 8000
```

## 5.4 NGINX Configuration

```nginx
# nginx/nginx.conf

events { worker_connections 1024; }

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name intellidesk.example.com;

        ssl_certificate     /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header X-Frame-Options "DENY";
        add_header X-Content-Type-Options "nosniff";
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
        add_header Content-Security-Policy "default-src 'self'; script-src 'self';";

        # Frontend (React SPA)
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            expires 1h;
        }

        # Backend API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 120s;
        }

        # Auth endpoints — stricter rate limiting
        location /api/v1/auth/ {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # WebSocket
        location /socket.io/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

## 5.5 Celery Task Queue Design

### Queue Architecture

| Queue | Workers | Tasks | Priority |
|-------|---------|-------|----------|
| `default` | 2 | General tasks | Normal |
| `ai` | 1 | AI classification, RAG, embeddings | High |
| `email` | 1 | Email notifications | Normal |
| `reports` | 1 | Report generation | Low |

### Scheduled Tasks (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| `check_sla_breaches` | Every 5 minutes | Find and flag overdue tickets |
| `send_sla_warnings` | Every 15 minutes | Warn when 80% of SLA time used |
| `refresh_dashboard_cache` | Every 30 seconds | Push fresh KPIs via WebSocket |
| `cleanup_notifications` | Daily at 2 AM | Delete notifications older than 30 days |
| `cleanup_audit_logs` | Weekly Sunday 3 AM | Archive logs older than 90 days |
| `process_pending_documents` | Every 10 minutes | Retry failed document processing |
| `send_daily_summary` | Daily at 8 AM | Email daily digest to managers |

## 5.6 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci-cd.yml

name: IntelliDesk AI CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: intellidesk_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - name: Install dependencies
        run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - name: Lint (Flake8 + Black)
        run: |
          cd backend
          flake8 . --max-line-length=100
          black . --check
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-fail-under=70
        env:
          DATABASE_URL: postgresql://postgres:test_password@localhost/intellidesk_test
          SECRET_KEY: test-secret-key
          JWT_SECRET_KEY: test-jwt-secret

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: TypeScript check
        run: cd frontend && npx tsc --noEmit
      - name: Lint (ESLint)
        run: cd frontend && npm run lint
      - name: Run tests
        run: cd frontend && npm test

  deploy-backend:
    needs: [backend-tests, frontend-tests]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Render
        run: curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}

  deploy-frontend:
    needs: [backend-tests, frontend-tests]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build
        env:
          VITE_API_URL: ${{ secrets.PRODUCTION_API_URL }}
          VITE_WS_URL: ${{ secrets.PRODUCTION_WS_URL }}
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
```

## 5.7 Environment Variables Reference

```bash
# .env.example

# ─── Flask ────────────────────────────────────
FLASK_ENV=development
SECRET_KEY=your-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars

# ─── Database ─────────────────────────────────
DATABASE_URL=postgresql://intellidesk:password@postgres:5432/intellidesk

# ─── Redis ────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── ChromaDB ─────────────────────────────────
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# ─── AI ───────────────────────────────────────
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# ─── Email (Gmail SMTP) ───────────────────────
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
EMAIL_FROM_NAME=IntelliDesk AI

# ─── Cloudinary ───────────────────────────────
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name

# ─── Frontend ─────────────────────────────────
FRONTEND_URL=http://localhost:5173

# ─── App Settings ─────────────────────────────
MAX_UPLOAD_SIZE_MB=25
DEFAULT_TIMEZONE=UTC
```

## 5.8 Health Check Endpoints

| Endpoint | Access | Response |
|----------|--------|----------|
| `GET /api/v1/health` | Public | `{"status": "healthy", "version": "1.0.0"}` |
| `GET /api/v1/health/detailed` | Admin only | Full status of all dependencies |

```json
// GET /api/v1/health/detailed (Admin only)
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-07-06T00:00:00Z",
  "services": {
    "database":   { "status": "healthy", "latency_ms": 12 },
    "redis":      { "status": "healthy", "latency_ms": 2  },
    "chromadb":   { "status": "healthy", "latency_ms": 8  },
    "celery":     { "status": "healthy", "active_workers": 3 },
    "groq_api":   { "status": "healthy", "latency_ms": 245 }
  }
}
```
