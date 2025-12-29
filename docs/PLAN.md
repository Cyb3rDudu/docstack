# DocStack RAG Admin Webapp - Implementation Plan

## Overview

**DocStack** is a comprehensive RAG document management system that enables:
- Creating multiple document stores (docstores) - one per study module (VWL, Marketing, Finance, etc.)
- CRUD operations on documents within each docstore
- Pipeline configuration and management (indexing, querying, chunking, embeddings)
- User authentication (login/logout)
- Integration with LibreChat agents for multi-docstore querying

**Key Design Decision**: Separate OpenSearch indices per docstore for better isolation, performance, and manageability.

---

## Architecture

### Infrastructure
- **Container 111 (librechat)**: Deploy alongside LibreChat
  - IP: 10.36.0.111
  - Ports: 3000 (Next.js frontend - DocStack), 3080 (LibreChat), 3081 (FastAPI backend - DocStack)
  - DocStack will coexist with LibreChat in the same container

### Technology Stack
- **Backend**: FastAPI (Python) + SQLAlchemy + Alembic
- **Frontend**: Next.js 16 + shadcn/ui + TailwindCSS v4
- **Database**: PostgreSQL 17 (container 107, existing)
- **Search**: OpenSearch 2.19.4 (container 110, existing)
- **Pipeline Runtime**: Hayhooks 1.8.0 (container 112, existing)
- **Authentication**: Hybrid JWT + session cookies
- **State Management**: Zustand
- **Forms**: React Hook Form + Zod

### Multi-Docstore Strategy
Each docstore gets:
- Dedicated OpenSearch index: `docstack-{slug}-{timestamp}` (e.g., `docstack-vwl-1735488000`)
- Metadata in PostgreSQL (name, description, stats)
- Dedicated pipelines (indexing + query) deployed to hayhooks
- Model configuration (embedder, splitter settings)

Agents can query:
- **Single docstore**: `POST /api/v1/query/search` with `docstore: "vwl"`
- **Multiple docstores**: `POST /api/v1/query/search-multi` with `docstores: ["vwl", "marketing"]`

**Note**: Since DocStack is deployed on the same container as LibreChat (111), it can easily integrate with LibreChat's existing configuration.

---

## Database Schema (PostgreSQL)

### Core Tables

**users**
- id (UUID, PK)
- email (unique)
- password_hash (bcrypt)
- full_name
- created_at, last_login, is_active

**docstores**
- id (UUID, PK)
- name (e.g., "VWL Grundlagen")
- slug (unique, e.g., "vwl")
- description
- index_name (OpenSearch index, e.g., "docstack-vwl-1735488000")
- created_by (FK users)
- document_count, chunk_count, total_size_bytes (denormalized stats)
- created_at, updated_at, is_active

**documents**
- id (UUID, PK)
- docstore_id (FK docstores, CASCADE)
- filename, original_filename
- mime_type, size_bytes, checksum (SHA256 for deduplication)
- uploaded_at, processed_at
- processing_status ('pending', 'processing', 'completed', 'failed')
- processing_error (text)
- chunk_count, page_count
- source_id (ID in OpenSearch)
- uploaded_by (FK users)

**model_configs**
- id (UUID, PK)
- docstore_id (FK docstores, CASCADE)
- embedder_model (e.g., "BAAI/bge-large-en-v1.5")
- embedder_settings (JSONB: normalize, batch_size, etc.)
- splitter_type ('sentence', 'word', 'passage')
- split_length, split_overlap
- splitter_settings (JSONB)
- created_at, updated_at, is_active

**pipelines**
- id (UUID, PK)
- docstore_id (FK docstores, CASCADE)
- name
- pipeline_type ('indexing', 'query')
- yaml_content (text)
- version (integer)
- is_active, deployed, deployed_at
- created_by (FK users)

**sessions**
- id (UUID, PK)
- user_id (FK users, CASCADE)
- token_hash (bcrypt)
- created_at, expires_at (24 hours), last_activity
- ip_address, user_agent

**audit_logs**
- id (UUID, PK)
- user_id (FK users)
- action ('create_docstore', 'upload_document', etc.)
- resource_type, resource_id
- details (JSONB)
- created_at, ip_address

---

## API Endpoints (FastAPI)

**Base URL**: `http://10.36.0.111:3081/api/v1/` (or `http://localhost:3081/api/v1/` from within container 111)

### Authentication
- `POST /auth/login` - Login with email/password → JWT + session cookie
- `POST /auth/logout` - Logout (clear session)
- `POST /auth/register` - Register new user
- `GET /auth/verify` - Verify current session

### Docstores
- `GET /docstores/` - List all docstores
- `POST /docstores/` - Create docstore (auto-generates index, pipelines)
- `GET /docstores/{id}` - Get docstore details + stats
- `PATCH /docstores/{id}` - Update docstore metadata
- `DELETE /docstores/{id}` - Delete docstore + OpenSearch index
- `POST /docstores/{id}/reindex` - Trigger full reindex

### Documents
- `GET /docstores/{id}/documents` - List documents in docstore
- `POST /docstores/{id}/documents` - Upload documents (multipart/form-data)
- `GET /documents/{doc_id}` - Get document metadata
- `DELETE /documents/{doc_id}` - Delete document from DB + OpenSearch
- `POST /documents/{doc_id}/rechunk` - Rechunk single document

### Pipelines
- `GET /docstores/{id}/pipelines` - List pipelines for docstore
- `POST /docstores/{id}/pipelines` - Create new pipeline
- `GET /pipelines/{pipeline_id}` - Get pipeline YAML
- `PATCH /pipelines/{pipeline_id}` - Update pipeline settings
- `DELETE /pipelines/{pipeline_id}` - Delete pipeline
- `POST /pipelines/{pipeline_id}/deploy` - Deploy to hayhooks

### Models
- `GET /models/embedders` - List available embedder models
- `GET /models/splitters` - List available splitters
- `POST /docstores/{id}/models` - Set model config for docstore
- `GET /docstores/{id}/models` - Get current model config

### Query
- `POST /query/search` - Query single docstore
- `POST /query/search-multi` - Query multiple docstores

### Health
- `GET /health` - Health check (DB, OpenSearch, hayhooks connectivity)

---

## Frontend Structure (Next.js)

### Page Routes

```
/app/
├── (auth)/
│   ├── login/page.tsx           # Login page
│   └── layout.tsx
├── (dashboard)/
│   ├── layout.tsx                # Sidebar + header
│   ├── page.tsx                  # Dashboard home (stats overview)
│   ├── docstores/
│   │   ├── page.tsx              # List all docstores (grid view)
│   │   ├── new/page.tsx          # Create docstore form
│   │   └── [id]/
│   │       ├── page.tsx          # Docstore detail + stats
│   │       ├── documents/page.tsx # Document management
│   │       ├── pipelines/page.tsx # Pipeline list/editor
│   │       └── settings/page.tsx  # Model configuration
│   ├── query/page.tsx            # Query interface (testing)
│   └── settings/page.tsx         # Global settings
```

### Key Components (shadcn/ui)

**Layout**
- `Sidebar.tsx` - Navigation menu
- `Header.tsx` - User dropdown, logout
- `MainLayout.tsx` - Container with sidebar + content

**Docstores**
- `DocstoreCard.tsx` - Grid card with stats
- `DocstoreForm.tsx` - Create/edit docstore
- `DeleteDocstoreDialog.tsx` - Confirmation dialog

**Documents**
- `DocumentUploader.tsx` - Drag-and-drop with react-dropzone
- `DocumentTable.tsx` - Table with status, filename, size, chunks
- `DeleteDocumentDialog.tsx` - Confirmation with cascade warning

**Pipelines**
- `PipelineEditor.tsx` - Monaco editor for YAML
- `PipelineList.tsx` - List with deploy/activate buttons
- `PipelineTemplates.tsx` - Template selection dropdown

**Models**
- `ModelSelector.tsx` - Dropdown for embedder selection
- `ModelConfigForm.tsx` - Splitter settings (type, length, overlap)

**Query**
- `QueryInterface.tsx` - Search input + docstore selector
- `ResultCard.tsx` - Search result with score, source file
- `DocstoreSelector.tsx` - Multi-select dropdown

---

## Deployment

### Container Setup

**Using Existing Container 111 (librechat)**
- No new container needed - deploy alongside LibreChat
- SSH to container: `ssh root@10.36.0.111`
- LibreChat already running on port 3080
- DocStack will use ports 3000 (frontend) and 3081 (backend)

### Directory Structure

```
/opt/docstack/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── api/v1/              # Route handlers
│   │   ├── core/                # auth.py, security.py
│   │   └── services/            # opensearch.py, hayhooks.py, pipeline_generator.py
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   ├── venv/
│   └── .env
├── frontend/
│   ├── app/                     # Next.js pages
│   ├── components/              # React components
│   ├── lib/                     # Utils
│   ├── stores/                  # Zustand stores
│   ├── types/                   # TypeScript types
│   ├── package.json
│   └── .env.local
└── shared/
    └── pipeline-templates/
        ├── indexing.yaml.j2     # Jinja2 template
        └── query.yaml.j2        # Jinja2 template
```

### Systemd Services

**Backend** (`/etc/systemd/system/docstack-backend.service`)
```ini
[Unit]
Description=DocStack Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/docstack/backend
EnvironmentFile=/opt/docstack/backend/.env
ExecStart=/opt/docstack/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3081 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

**Frontend** (`/etc/systemd/system/docstack-frontend.service`)
```ini
[Unit]
Description=DocStack Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/docstack/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy (Container 100)

```nginx
server {
    listen 80;
    server_name docstack.local;

    location / {
        proxy_pass http://10.36.0.111:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Environment Variables

**Backend (.env)**
```bash
DATABASE_URL=postgresql://docstack_user:PASSWORD@10.36.0.107:5432/docstack
OPENSEARCH_URL=http://10.36.0.110:9200
HAYHOOKS_URL=http://10.36.0.112:1416
JWT_SECRET_KEY=your_secret_key_here
JWT_EXPIRE_MINUTES=60
SESSION_EXPIRE_HOURS=24
CORS_ORIGINS=http://docstack.local,http://10.36.0.111:3000,http://localhost:3000
```

**Frontend (.env.local)**
```bash
NEXT_PUBLIC_API_URL=http://localhost:3081
NEXT_PUBLIC_APP_NAME=DocStack
```

---

## Pipeline Management

### Dynamic Pipeline Generation (Jinja2)

**Template Variables**:
```python
{
    "index_name": "docstack-vwl-1735488000",
    "embedder_model": "BAAI/bge-large-en-v1.5",
    "embedding_dim": 768,  # Auto-detected from model
    "split_by": "sentence",
    "split_length": 55,
    "split_overlap": 5,
    "normalize_embeddings": true,
    "batch_size": 32,
    "opensearch_host": "http://10.36.0.110:9200",
    "top_k": 10
}
```

**Indexing Pipeline Template** (`indexing.yaml.j2`):
- FileTypeRouter (TXT, PDF, DOCX)
- Converters (TextFileToDocument, PyPDFToDocument, DOCXToDocument)
- DocumentJoiner
- DocumentSplitter (configurable split_by, split_length, split_overlap)
- SentenceTransformersDocumentEmbedder (configurable model)
- DocumentWriter (OpenSearchDocumentStore with dynamic index)

**Query Pipeline Template** (`query.yaml.j2`):
- SentenceTransformersTextEmbedder (same model as indexing)
- OpenSearchEmbeddingRetriever (configurable top_k)
- PromptBuilder (with context template)

### Pipeline Deployment to Hayhooks

**Strategy**: SSH to container 112 and write pipeline files to `/opt/hayhooks/pipelines/{docstore_slug}/`

```python
# services/hayhooks_deployer.py
class HayhooksDeployer:
    def deploy_pipeline(self, docstore_slug: str, pipeline_type: str, yaml_content: str):
        # SSH to 10.36.0.112
        # mkdir -p /opt/hayhooks/pipelines/{docstore_slug}
        # Write {pipeline_type}.yaml
        # Hayhooks auto-detects new pipelines
```

**Pipeline Endpoints** (auto-generated by hayhooks):
- `http://10.36.0.112:1416/{docstore_slug}_indexing/run`
- `http://10.36.0.112:1416/{docstore_slug}_query/run`

---

## Integration Points

### 1. OpenSearch Integration
- **Direct API access** for index management (create, delete, stats)
- **Via Hayhooks** for document indexing and querying
- **Library**: `opensearchpy` (AsyncOpenSearch client)

**Operations**:
- Create index with knn_vector mapping (dimension auto-detected)
- Delete index when docstore is deleted
- Delete documents by query (when single document deleted)
- Get index stats (document count, size)

### 2. Hayhooks Integration
- **Document upload**: `POST http://10.36.0.112:1416/{slug}_indexing/run` (multipart files)
- **Query**: `POST http://10.36.0.112:1416/{slug}_query/run` (JSON: query, query_text)
- **Pipeline deployment**: SSH to write YAML files to `/opt/hayhooks/pipelines/{slug}/`

**Response Format** (hayhooks 1.8.0):
```json
{
  "result": {
    "prompt_builder": {"prompt": "..."},
    "retriever": {"documents": [...]}
  }
}
```

### 3. LibreChat Agent Integration

**Option A: Direct API** (Recommended)
- Agents call `http://localhost:3081/api/v1/query/search` (same container)
- Include JWT token in Authorization header
- Specify docstore by slug

**Option B: Proxy via Simple Wrapper**
- Add endpoint to simple_wrapper.py on container 112
- Proxy to DocStack API
- Simpler for LibreChat configuration

**LibreChat Tool Configuration**:
```yaml
# librechat.yaml
endpoints:
  agents:
    tools:
      - name: search_documents
        description: "Search documents in a study module docstore"
        parameters:
          - name: docstore
            type: string
            description: "Docstore slug (vwl, marketing, finance)"
            required: true
          - name: query
            type: string
            description: "Search query"
            required: true
        endpoint: http://localhost:3081/api/v1/query/search
        method: POST
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
1. **Infrastructure**
   - SSH to container 111 (librechat)
   - Install Python 3.11, Node.js 20 (if not already present), PostgreSQL client
   - Create PostgreSQL database and user on container 107

2. **Backend Skeleton**
   - Initialize FastAPI project with SQLAlchemy
   - Create database models (users, docstores, documents, etc.)
   - Set up Alembic migrations
   - Implement JWT + session authentication
   - Create basic CRUD endpoints for users

3. **Frontend Skeleton**
   - Initialize Next.js 16 project
   - Install shadcn/ui components
   - Configure TailwindCSS v4
   - Create basic layout (sidebar, header)
   - Implement login page with authentication flow

### Phase 2: Core Features (Week 3-4)
4. **Docstore Management**
   - Backend: Docstore CRUD API
   - Frontend: Docstore list, create form, delete dialog
   - OpenSearch service: create/delete index
   - Pipeline generator: Jinja2 templates for indexing/query

5. **Document Management**
   - Backend: Document upload endpoint with hayhooks integration
   - Frontend: File uploader (drag-and-drop with react-dropzone)
   - Document table with status, filename, size, chunks
   - Delete document (remove from DB + OpenSearch)
   - SHA256 checksum for deduplication

6. **Pipeline Management**
   - Backend: Pipeline CRUD API
   - Pipeline generator service with Jinja2
   - Hayhooks deployer (SSH + file write)
   - Frontend: Pipeline editor with Monaco
   - Deploy/activate pipeline buttons

### Phase 3: Advanced Features (Week 5-6)
7. **Query Interface**
   - Backend: Query endpoint (single + multi-docstore)
   - Parse hayhooks response format (result wrapper)
   - Frontend: Query UI with docstore selector
   - Result cards with score, source file, content preview

8. **Model Configuration**
   - Backend: Model config CRUD
   - Embedding dimension auto-detection
   - Frontend: Embedder selector (dropdown)
   - Splitter configuration form (type, length, overlap)

9. **Reindexing**
   - Backend: Reindex endpoint (create new index, migrate documents)
   - Progress tracking (job queue optional)
   - Update docstore index_name after completion
   - Frontend: Reindex button with progress indicator

### Phase 4: Polish (Week 7-8)
10. **Error Handling**
    - Comprehensive error messages
    - Input validation (Pydantic + Zod)
    - Retry mechanisms for failed uploads
    - Graceful degradation

11. **Monitoring & Logging**
    - Structured logging (JSON format)
    - Health checks (/api/v1/health)
    - Audit logging (all CRUD operations)
    - Statistics dashboard

12. **Testing & Documentation**
    - Backend unit tests (pytest)
    - API integration tests
    - Frontend component tests (Vitest)
    - API documentation (FastAPI auto-docs)
    - User guide (README)

13. **Deployment & Integration**
    - Systemd services (backend + frontend)
    - Nginx reverse proxy configuration
    - LibreChat agent integration
    - Production environment setup

---

## Critical Files

### To Create

**Backend**:
- `/opt/docstack/backend/app/main.py` - FastAPI application
- `/opt/docstack/backend/app/models/docstore.py` - Docstore SQLAlchemy model
- `/opt/docstack/backend/app/models/document.py` - Document SQLAlchemy model
- `/opt/docstack/backend/app/api/v1/docstores.py` - Docstore endpoints
- `/opt/docstack/backend/app/api/v1/documents.py` - Document endpoints
- `/opt/docstack/backend/app/services/opensearch.py` - OpenSearch client
- `/opt/docstack/backend/app/services/hayhooks.py` - Hayhooks integration
- `/opt/docstack/backend/app/services/pipeline_generator.py` - Jinja2 templates
- `/opt/docstack/backend/app/core/auth.py` - JWT + session auth
- `/opt/docstack/backend/requirements.txt` - Python dependencies
- `/opt/docstack/backend/.env` - Environment variables

**Frontend**:
- `/opt/docstack/frontend/app/(dashboard)/docstores/page.tsx` - Docstore list
- `/opt/docstack/frontend/app/(dashboard)/docstores/new/page.tsx` - Create docstore
- `/opt/docstack/frontend/app/(dashboard)/docstores/[id]/documents/page.tsx` - Document management
- `/opt/docstack/frontend/components/documents/DocumentUploader.tsx` - File upload
- `/opt/docstack/frontend/components/pipelines/PipelineEditor.tsx` - YAML editor
- `/opt/docstack/frontend/stores/docstoreStore.ts` - Zustand store
- `/opt/docstack/frontend/stores/authStore.ts` - Auth state
- `/opt/docstack/frontend/package.json` - Dependencies

**Templates**:
- `/opt/docstack/shared/pipeline-templates/indexing.yaml.j2` - Indexing pipeline template
- `/opt/docstack/shared/pipeline-templates/query.yaml.j2` - Query pipeline template

**System**:
- `/etc/systemd/system/docstack-backend.service` - Backend service
- `/etc/systemd/system/docstack-frontend.service` - Frontend service

### To Reference

- `/opt/hayhooks/simple_wrapper.py` - FastAPI wrapper pattern for hayhooks
- `/opt/hayhooks/pipelines/indexing.yaml` - Current indexing pipeline
- `/opt/hayhooks/pipelines/query.yaml` - Current query pipeline (hayhooks 1.8.0 format)
- `/opt/LibreChat/librechat.yaml` - Agent tool configuration pattern

---

## Key Implementation Notes

1. **Embedding Dimension Auto-Detection**: Create a lookup table for common models (bge-large: 1024, bge-base: 768, etc.). Verify actual dimensions with current config.

2. **Index Naming with Timestamps**: Use `int(time.time())` for unique index names to support zero-downtime reindexing.

3. **Pipeline Deployment**: Use paramiko (SSH) to write YAML files to container 112's `/opt/hayhooks/pipelines/{slug}/` directory.

4. **Document Deduplication**: Calculate SHA256 checksum before upload, check against existing documents in same docstore.

5. **Session Cleanup**: Use APScheduler to clean expired sessions every hour.

6. **File Upload Flow**:
   - Save metadata to PostgreSQL immediately
   - Send file to hayhooks for indexing
   - Update metadata with chunk count and status
   - Store checksum for deduplication

7. **Multi-Docstore Query**: Use OpenSearch multi-index syntax: `docstack-vwl-*,docstack-marketing-*`

8. **Authentication**:
   - JWT for API access (LibreChat agents)
   - Session cookies for web app (httpOnly, Secure, SameSite=Lax)
   - Bcrypt for password hashing (12 rounds)

---

## Git Repository Initialization

### Step 1: Create Repository on Local Machine

Create repository at: `/Users/dudu/Documents/Code/docstack`

```bash
cd /Users/dudu/Documents/Code
mkdir docstack
cd docstack
git init
```

### Step 2: Initial File Structure

Create the following initial files:

**README.md**:
```markdown
# DocStack - RAG Document Management System

A comprehensive RAG admin webapp for managing multiple document stores with LibreChat integration.

## Features
- Multi-docstore management (one per study module)
- Document CRUD operations (PDF, DOCX, TXT)
- Pipeline configuration (indexing, query)
- Model configuration (embedders, splitters)
- User authentication
- LibreChat agent integration

## Architecture
- Backend: FastAPI (Python) on port 3081
- Frontend: Next.js 16 on port 3000
- Database: PostgreSQL 17 (container 107)
- Search: OpenSearch 2.19.4 (container 110)
- Pipeline Runtime: Hayhooks 1.8.0 (container 112)
- Deployment: Container 111 (librechat)

## Deployment
See `docs/DEPLOYMENT.md` for setup instructions.

## API Documentation
Once running, visit: http://10.36.0.111:3081/docs

## Development
See `docs/DEVELOPMENT.md` for development workflow.
```

**.gitignore**:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.env
.venv

# Node.js
node_modules/
.next/
.env.local
.env.production
dist/
build/

# IDEs
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Alembic
alembic/versions/*.pyc

# Logs
*.log

# Database
*.db
*.sqlite

# Testing
.coverage
.pytest_cache/
htmlcov/

# Temporary files
tmp/
temp/
*.tmp
```

**backend/requirements.txt**:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
alembic==1.13.3
psycopg2-binary==2.9.9
pydantic==2.9.0
pydantic-settings==2.5.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.27.0
opensearch-py==2.7.0
jinja2==3.1.4
paramiko==3.5.0
apscheduler==3.10.4
python-dotenv==1.0.1
```

**backend/app/main.py** (minimal skeleton):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DocStack API", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://10.36.0.111:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "DocStack API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "docstack-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3081)
```

**backend/.env.example**:
```bash
DATABASE_URL=postgresql://docstack_user:PASSWORD@10.36.0.107:5432/docstack
OPENSEARCH_URL=http://10.36.0.110:9200
HAYHOOKS_URL=http://10.36.0.112:1416
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
SESSION_EXPIRE_HOURS=24
CORS_ORIGINS=http://docstack.local,http://10.36.0.111:3000,http://localhost:3000
```

**frontend/package.json**:
```json
{
  "name": "docstack-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "tailwindcss": "^4.0.0",
    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.0.0",
    "react-hook-form": "^7.53.0",
    "zod": "^3.23.0",
    "react-dropzone": "^14.2.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.6.0"
  }
}
```

**frontend/next.config.js**:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
```

**frontend/app/page.tsx** (minimal homepage):
```typescript
export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold">DocStack</h1>
      <p className="mt-4 text-lg">RAG Document Management System</p>
    </main>
  )
}
```

**frontend/.env.local.example**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:3081
NEXT_PUBLIC_APP_NAME=DocStack
```

**docs/DEPLOYMENT.md**:
```markdown
# Deployment Guide

## Prerequisites
- Container 111 (librechat) running
- PostgreSQL 17 on container 107
- OpenSearch 2.19.4 on container 110
- Hayhooks 1.8.0 on container 112

## Step 1: Database Setup

```sql
-- On PostgreSQL (container 107)
CREATE DATABASE docstack;
CREATE USER docstack_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE docstack TO docstack_user;
```

## Step 2: Backend Deployment

```bash
# SSH to container 111
ssh root@10.36.0.111

# Create directory
mkdir -p /opt/docstack/backend
cd /opt/docstack/backend

# Clone or copy repository
# (instructions depend on how you're transferring the code)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with actual credentials

# Run database migrations
alembic upgrade head

# Create systemd service (see PLAN.md for service file)
systemctl enable docstack-backend
systemctl start docstack-backend
```

## Step 3: Frontend Deployment

```bash
# Still on container 111
cd /opt/docstack/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Build production
npm run build

# Create systemd service
systemctl enable docstack-frontend
systemctl start docstack-frontend
```

## Step 4: Nginx Configuration

See PLAN.md for nginx reverse proxy configuration.
```

**docs/PLAN.md**:
(Copy the entire plan from `/Users/dudu/.claude/plans/sparkling-hopping-porcupine.md`)

### Step 3: Initial Commit

```bash
# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: DocStack project structure

- Add README with project overview
- Add .gitignore for Python and Node.js
- Add backend skeleton (FastAPI with health endpoint)
- Add frontend skeleton (Next.js 16 with minimal homepage)
- Add deployment documentation
- Add requirements.txt and package.json
- Add environment variable templates
- Include full implementation plan in docs/PLAN.md

Ready for handoff to implementation phase."

# Create develop branch
git checkout -b develop
git checkout main
```

### Step 4: Handoff Instructions

The repository is now ready for implementation. The next Claude instance should:

1. **Review the plan** in `docs/PLAN.md`
2. **Set up the environment** on container 111 (librechat)
3. **Create PostgreSQL database** on container 107
4. **Implement Phase 1** (Foundation):
   - Complete backend skeleton with database models
   - Set up Alembic migrations
   - Implement authentication (JWT + sessions)
   - Create basic user CRUD
5. **Continue with subsequent phases** as outlined in the plan

### Repository Structure After Init

```
docstack/
├── .git/
├── .gitignore
├── README.md
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   └── page.tsx
│   ├── package.json
│   ├── next.config.js
│   └── .env.local.example
└── docs/
    ├── DEPLOYMENT.md
    └── PLAN.md (full implementation plan)
```

---

## Success Criteria

- [x] Users can create multiple docstores (one per study module)
- [x] Users can upload documents (PDF, DOCX, TXT) to any docstore
- [x] Documents are automatically chunked and indexed with semantic splitting
- [x] Users can configure embedder model and splitter settings per docstore
- [x] Users can create and edit pipelines (YAML)
- [x] Pipelines are deployed to hayhooks automatically
- [x] Users can query documents in single or multiple docstores
- [x] LibreChat agents can query specific docstores via API
- [x] User authentication works (login/logout)
- [x] Document deduplication prevents duplicates
- [x] Reindexing updates existing docstores without downtime
- [x] All operations are logged for audit trail
- [x] System is deployed on dedicated container with systemd services
- [x] Nginx reverse proxy provides clean URL access

---

## Next Steps

After plan approval:
1. Create git repository at `/Users/dudu/Documents/Code/docstack`
2. Create container 114 on Proxmox
3. Set up PostgreSQL database on container 107
4. Initialize backend (FastAPI + SQLAlchemy)
5. Initialize frontend (Next.js + shadcn/ui)
6. Begin Phase 1 implementation
