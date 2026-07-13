# IntelliDesk AI — Database Design Document

**Document ID:** IDAI-DB-001 | **Version:** 1.0 | **Date:** 

---

## 1. Design Principles

- **PostgreSQL 16** as the sole relational database
- **UUID primary keys** for public-facing IDs; integer surrogate keys internally
- **Soft deletes** via `deleted_at` timestamp on all major entities
- **Audit trail** — `created_at`, `updated_at` on every table
- **Indexes** on all foreign keys and frequently filtered columns
- **Constraints** enforced at the database level, not just application level

---

## 2. Entity Relationship Diagram (Text)

```
users ────────────────────────────────────────────────┐
  │ id (PK)                                           │
  │ uuid                                              │
  │ email (UNIQUE)                                    │
  │ role_id (FK → roles)                              │
  │ department_id (FK → departments)                  │
  └── created_at, updated_at, deleted_at              │
                                                      │
roles                                                 │
  │ id (PK)                                           │
  │ name (UNIQUE): super_admin|admin|manager|agent|employee
  └── permissions (JSONB)                             │
                                                      │
departments ──────────────────────────────────────────┤
  │ id (PK)                                           │
  │ name                                              │
  │ manager_id (FK → users)                           │
  └── sla_config (JSONB)                              │
                                                      │
tickets ──────────────────────────────────────────────┤
  │ id (PK)                                           │
  │ ticket_number (UNIQUE, INDEX)                     │
  │ requester_id (FK → users)                         │
  │ assignee_id (FK → users)                          │
  │ department_id (FK → departments)                  │
  │ project_id (FK → projects)                        │
  │ status, priority, category                        │
  │ sla_response_deadline, sla_resolution_deadline    │
  │ ai_confidence, ai_metadata (JSONB)                │
  └── created_at, updated_at, deleted_at              │
      │                                               │
      ├──< comments                                   │
      │     id, ticket_id, author_id                  │
      │     body, is_internal                         │
      │     created_at                                │
      │                                               │
      ├──< attachments                                │
      │     id, ticket_id, uploader_id                │
      │     file_url, file_name, file_size            │
      │                                               │
      └──○ incidents (optional link)                  │
                                                      │
incidents ────────────────────────────────────────────┤
  │ id (PK)                                           │
  │ incident_number (UNIQUE)                          │
  │ reporter_id (FK → users)                          │
  │ assignee_id (FK → users)                          │
  │ severity, status, impact                          │
  └──< incident_timelines                             │
        id, incident_id, user_id                      │
        event_type, description                       │
        created_at                                    │
                                                      │
problems ─────────────────────────────────────────────┤
  │ id (PK)                                           │
  │ problem_number (UNIQUE)                           │
  │ root_cause, workaround, resolution                │
  └──< problem_notes                                  │
                                                      │
articles ─────────────────────────────────────────────┤
  │ id (PK)                                           │
  │ slug (UNIQUE)                                     │
  │ author_id (FK → users)                            │
  │ category_id (FK → article_categories)             │
  │ status: draft|published|archived                  │
  │ content, search_vector (TSVECTOR)                 │
  └──< article_versions                               │
                                                      │
documents ────────────────────────────────────────────┤
  │ id (PK)                                           │
  │ uploader_id (FK → users)                          │
  │ file_url, file_name, file_type, file_size         │
  │ processing_status: pending|processing|done|failed │
  │ chunk_count                                       │
  └──< document_chunks (metadata in PostgreSQL)       │
        id, document_id, chunk_index                  │
        chroma_chunk_id (reference to ChromaDB)       │
        page_num, token_count                         │
                                                      │
ai_conversations ─────────────────────────────────────┤
  │ id (PK)                                           │
  │ user_id (FK → users)                              │
  │ session_id                                        │
  └──< ai_messages                                    │
        id, conversation_id                           │
        role: user|assistant|system                   │
        content, token_count                          │
        sources (JSONB — citations)                   │
        created_at                                    │
                                                      │
notifications ────────────────────────────────────────┤
  │ id (PK)                                           │
  │ user_id (FK → users)                              │
  │ type, title, body                                 │
  │ resource_type, resource_id                        │
  │ is_read, read_at                                  │
  └── created_at                                      │
                                                      │
audit_logs ───────────────────────────────────────────┤
  │ id (PK)                                           │
  │ user_id (FK → users, nullable)                    │
  │ action, resource_type, resource_id                │
  │ old_values (JSONB), new_values (JSONB)            │
  │ ip_address, user_agent                            │
  └── created_at                                      │
                                                      │
prompt_templates ─────────────────────────────────────┤
  │ id (PK)                                           │
  │ name (UNIQUE), version                            │
  │ system_prompt, user_prompt                        │
  │ variables (JSONB), model_params (JSONB)           │
  │ is_active                                         │
  └── created_at, updated_at                          │
                                                      │
settings ─────────────────────────────────────────────┘
  id (PK)
  key (UNIQUE), value (TEXT)
  value_type: string|int|bool|json
  description
  updated_at
```

---

## 3. Full Table Schemas

### 3.1 `roles`
```sql
CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
-- Seed data: super_admin, admin, manager, agent, employee
```

### 3.2 `departments`
```sql
CREATE TABLE departments (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    manager_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    sla_config  JSONB DEFAULT '{}',  -- Override default SLA targets
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    deleted_at  TIMESTAMP
);
```

### 3.3 `users`
```sql
CREATE TABLE users (
    id                  SERIAL PRIMARY KEY,
    uuid                UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255) NOT NULL,
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    phone               VARCHAR(20),
    avatar_url          VARCHAR(500),
    role_id             INTEGER NOT NULL REFERENCES roles(id),
    department_id       INTEGER REFERENCES departments(id),
    status              VARCHAR(20) DEFAULT 'pending_verification',
    -- status: pending_verification | active | inactive | locked
    email_verified_at   TIMESTAMP,
    last_login_at       TIMESTAMP,
    failed_login_count  INTEGER DEFAULT 0,
    locked_until        TIMESTAMP,
    timezone            VARCHAR(50) DEFAULT 'UTC',
    notification_prefs  JSONB DEFAULT '{}',
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    deleted_at          TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_department_id ON users(department_id);
CREATE INDEX idx_users_status ON users(status);
```

### 3.4 `user_tokens`
```sql
CREATE TABLE user_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_type  VARCHAR(30) NOT NULL,  -- email_verify | password_reset | refresh
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    used_at     TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_tokens_user_id ON user_tokens(user_id);
CREATE INDEX idx_user_tokens_token_hash ON user_tokens(token_hash);
```

### 3.5 `projects`
```sql
CREATE TABLE projects (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    status      VARCHAR(20) DEFAULT 'active',
    start_date  DATE,
    end_date    DATE,
    created_by  INTEGER REFERENCES users(id),
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    deleted_at  TIMESTAMP
);
```

### 3.6 `tickets`
```sql
CREATE TABLE tickets (
    id                       SERIAL PRIMARY KEY,
    ticket_number            VARCHAR(20) UNIQUE NOT NULL,
    title                    VARCHAR(200) NOT NULL,
    description              TEXT NOT NULL,
    status                   VARCHAR(30) DEFAULT 'new',
    -- new | open | in_progress | pending | escalated | on_hold | resolved | closed
    priority                 VARCHAR(20),
    -- critical | high | medium | low
    category                 VARCHAR(50),
    requester_id             INTEGER NOT NULL REFERENCES users(id),
    assignee_id              INTEGER REFERENCES users(id),
    department_id            INTEGER REFERENCES departments(id),
    project_id               INTEGER REFERENCES projects(id),
    incident_id              INTEGER REFERENCES incidents(id),

    -- SLA tracking
    sla_response_deadline    TIMESTAMP,
    sla_resolution_deadline  TIMESTAMP,
    first_responded_at       TIMESTAMP,
    resolved_at              TIMESTAMP,
    closed_at                TIMESTAMP,
    sla_response_breached    BOOLEAN DEFAULT FALSE,
    sla_resolution_breached  BOOLEAN DEFAULT FALSE,

    -- AI metadata
    ai_confidence            FLOAT DEFAULT 0.0,
    ai_category_suggestion   VARCHAR(50),
    ai_priority_suggestion   VARCHAR(20),
    ai_department_suggestion INTEGER REFERENCES departments(id),
    ai_metadata              JSONB DEFAULT '{}',

    -- Counters (denormalized for performance)
    comment_count            INTEGER DEFAULT 0,
    reopen_count             INTEGER DEFAULT 0,

    created_at               TIMESTAMP DEFAULT NOW(),
    updated_at               TIMESTAMP DEFAULT NOW(),
    deleted_at               TIMESTAMP
);

CREATE INDEX idx_tickets_ticket_number ON tickets(ticket_number);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_category ON tickets(category);
CREATE INDEX idx_tickets_requester_id ON tickets(requester_id);
CREATE INDEX idx_tickets_assignee_id ON tickets(assignee_id);
CREATE INDEX idx_tickets_department_id ON tickets(department_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_sla_resolution_deadline ON tickets(sla_resolution_deadline);
```

### 3.7 `comments`
```sql
CREATE TABLE comments (
    id          SERIAL PRIMARY KEY,
    ticket_id   INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES users(id),
    body        TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,  -- Internal note vs public reply
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    deleted_at  TIMESTAMP
);

CREATE INDEX idx_comments_ticket_id ON comments(ticket_id);
```

### 3.8 `attachments`
```sql
CREATE TABLE attachments (
    id           SERIAL PRIMARY KEY,
    ticket_id    INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    comment_id   INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    uploader_id  INTEGER NOT NULL REFERENCES users(id),
    file_url     VARCHAR(500) NOT NULL,
    file_name    VARCHAR(255) NOT NULL,
    file_size    INTEGER NOT NULL,  -- bytes
    file_type    VARCHAR(50) NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);
```

### 3.9 `incidents`
```sql
CREATE TABLE incidents (
    id               SERIAL PRIMARY KEY,
    incident_number  VARCHAR(20) UNIQUE NOT NULL,
    title            VARCHAR(200) NOT NULL,
    description      TEXT NOT NULL,
    severity         VARCHAR(20) NOT NULL,  -- critical | high | medium | low
    status           VARCHAR(30) DEFAULT 'open',
    impact           VARCHAR(20),           -- high | medium | low
    affected_services TEXT,
    reporter_id      INTEGER NOT NULL REFERENCES users(id),
    assignee_id      INTEGER REFERENCES users(id),
    department_id    INTEGER REFERENCES departments(id),
    problem_id       INTEGER REFERENCES problems(id),
    resolved_at      TIMESTAMP,
    resolution_notes TEXT,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW(),
    deleted_at       TIMESTAMP
);

CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
```

### 3.10 `incident_timelines`
```sql
CREATE TABLE incident_timelines (
    id           SERIAL PRIMARY KEY,
    incident_id  INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    user_id      INTEGER REFERENCES users(id),
    event_type   VARCHAR(50) NOT NULL,
    description  TEXT NOT NULL,
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMP DEFAULT NOW()
);
```

### 3.11 `problems`
```sql
CREATE TABLE problems (
    id              SERIAL PRIMARY KEY,
    problem_number  VARCHAR(20) UNIQUE NOT NULL,
    title           VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    status          VARCHAR(30) DEFAULT 'open',
    root_cause      TEXT,
    workaround      TEXT,
    resolution      TEXT,
    owner_id        INTEGER REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP
);
```

### 3.12 `article_categories`
```sql
CREATE TABLE article_categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_id   INTEGER REFERENCES article_categories(id),
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### 3.13 `articles`
```sql
CREATE TABLE articles (
    id              SERIAL PRIMARY KEY,
    uuid            UUID UNIQUE DEFAULT gen_random_uuid(),
    slug            VARCHAR(200) UNIQUE NOT NULL,
    title           VARCHAR(200) NOT NULL,
    content         TEXT NOT NULL,
    author_id       INTEGER NOT NULL REFERENCES users(id),
    category_id     INTEGER REFERENCES article_categories(id),
    status          VARCHAR(20) DEFAULT 'draft',
    version         INTEGER DEFAULT 1,
    view_count      INTEGER DEFAULT 0,
    helpful_count   INTEGER DEFAULT 0,
    search_vector   TSVECTOR,  -- For PostgreSQL full-text search
    published_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP
);

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_search_vector ON articles USING GIN(search_vector);
```

### 3.14 `documents`
```sql
CREATE TABLE documents (
    id                SERIAL PRIMARY KEY,
    uuid              UUID UNIQUE DEFAULT gen_random_uuid(),
    file_name         VARCHAR(255) NOT NULL,
    original_name     VARCHAR(255) NOT NULL,
    file_url          VARCHAR(500) NOT NULL,
    file_type         VARCHAR(10) NOT NULL,  -- pdf | docx | txt | md
    file_size         INTEGER NOT NULL,
    processing_status VARCHAR(20) DEFAULT 'pending',
    -- pending | processing | processed | failed
    chunk_count       INTEGER DEFAULT 0,
    error_message     TEXT,
    uploader_id       INTEGER NOT NULL REFERENCES users(id),
    department_id     INTEGER REFERENCES departments(id),
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),
    deleted_at        TIMESTAMP
);
```

### 3.15 `document_chunks`
```sql
CREATE TABLE document_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chroma_chunk_id VARCHAR(100) NOT NULL,  -- Reference to ChromaDB
    page_num        INTEGER,
    token_count     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
```

### 3.16 `ai_conversations`
```sql
CREATE TABLE ai_conversations (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    session_id  VARCHAR(100) UNIQUE NOT NULL,
    title       VARCHAR(200),  -- Auto-generated from first message
    ticket_id   INTEGER REFERENCES tickets(id),  -- Optional context
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

### 3.17 `ai_messages`
```sql
CREATE TABLE ai_messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,  -- user | assistant | system
    content         TEXT NOT NULL,
    token_count     INTEGER DEFAULT 0,
    sources         JSONB DEFAULT '[]',   -- Citations from RAG
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_messages_conversation_id ON ai_messages(conversation_id);
```

### 3.18 `notifications`
```sql
CREATE TABLE notifications (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type          VARCHAR(50) NOT NULL,
    -- ticket_assigned | ticket_updated | incident_created | sla_warning | mention
    title         VARCHAR(200) NOT NULL,
    body          TEXT,
    resource_type VARCHAR(50),  -- ticket | incident | article | etc
    resource_id   INTEGER,
    is_read       BOOLEAN DEFAULT FALSE,
    read_at       TIMESTAMP,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
```

### 3.19 `audit_logs`
```sql
CREATE TABLE audit_logs (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action        VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id   INTEGER,
    old_values    JSONB,
    new_values    JSONB,
    ip_address    INET,
    user_agent    TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### 3.20 `prompt_templates`
```sql
CREATE TABLE prompt_templates (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) UNIQUE NOT NULL,
    display_name  VARCHAR(200) NOT NULL,
    description   TEXT,
    version       INTEGER DEFAULT 1,
    system_prompt TEXT NOT NULL,
    user_prompt   TEXT,
    variables     JSONB DEFAULT '[]',
    model_params  JSONB DEFAULT '{}',
    is_active     BOOLEAN DEFAULT TRUE,
    created_by    INTEGER REFERENCES users(id),
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);
```

### 3.21 `settings`
```sql
CREATE TABLE settings (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(100) UNIQUE NOT NULL,
    value       TEXT,
    value_type  VARCHAR(20) DEFAULT 'string',
    description TEXT,
    updated_by  INTEGER REFERENCES users(id),
    updated_at  TIMESTAMP DEFAULT NOW()
);
-- Seed keys: org_name, timezone, default_sla_critical, default_sla_high,
--            ai_model, max_upload_mb, email_notifications_enabled
```

---

## 4. Association Tables

```sql
-- Many-to-many: incidents ↔ tickets
CREATE TABLE incident_tickets (
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    ticket_id   INTEGER NOT NULL REFERENCES tickets(id),
    PRIMARY KEY (incident_id, ticket_id)
);

-- Many-to-many: problems ↔ incidents
CREATE TABLE problem_incidents (
    problem_id  INTEGER NOT NULL REFERENCES problems(id),
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    PRIMARY KEY (problem_id, incident_id)
);

-- Many-to-many: articles ↔ tags
CREATE TABLE tags (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE article_tags (
    article_id INTEGER NOT NULL REFERENCES articles(id),
    tag_id     INTEGER NOT NULL REFERENCES tags(id),
    PRIMARY KEY (article_id, tag_id)
);

-- Many-to-many: projects ↔ users (members)
CREATE TABLE project_members (
    project_id INTEGER NOT NULL REFERENCES projects(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    role       VARCHAR(20) DEFAULT 'member',  -- member | lead
    PRIMARY KEY (project_id, user_id)
);
```

---

## 5. ChromaDB Collections

| Collection | Stored By | Metadata Keys |
|-----------|-----------|---------------|
| `documents` | DocumentChunk | doc_id, chunk_index, page_num, file_type, department_id, uploader_id |
| `knowledge_articles` | Article | article_id, title, category, status, author_id |
| `tickets` | Ticket | ticket_id, status, priority, category, department_id |

---

## 6. Index Strategy Summary

| Table | Indexed Columns | Reason |
|-------|----------------|--------|
| users | email, role_id, department_id, status | Auth lookup, filtering |
| tickets | ticket_number, status, priority, category, requester_id, assignee_id, department_id, created_at, sla_resolution_deadline | Core query performance |
| comments | ticket_id | Ticket detail fetch |
| incidents | status, severity | Incident dashboard |
| articles | status, search_vector (GIN) | Full-text search |
| notifications | user_id, is_read, created_at | Notification fetch |
| audit_logs | user_id, action, resource_type+id, created_at | Audit queries |

---

## 7. Migration Strategy

- All schema changes managed via **Alembic** migrations
- Migrations versioned and committed to source control
- Zero-downtime migrations enforced: no locking `ALTER TABLE` on large tables
- Rollback scripts included for every migration
- Migration naming: `YYYYMMDD_HHMMSS_description.py`
