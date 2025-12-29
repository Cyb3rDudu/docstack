# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DocStack** is a RAG (Retrieval-Augmented Generation) document management system designed to manage multiple document stores (docstores) for integration with LibreChat agents. Each docstore represents a study module (e.g., VWL, Marketing, Finance) with its own documents, pipelines, and model configurations.

**Key Design Pattern**: Separate OpenSearch indices per docstore for isolation, performance, and manageability.

## Architecture

### Tech Stack
- **Backend**: FastAPI (Python) on port 3081
- **Frontend**: Next.js 16 on port 3000
- **Database**: PostgreSQL 17 (container 107 at 10.36.0.107)
- **Search**: OpenSearch 2.19.4 (container 110 at 10.36.0.110)
- **Pipeline Runtime**: Hayhooks 1.8.0 (container 112 at 10.36.0.112)
- **Deployment Target**: Container 111 (librechat) at 10.36.0.111

### Multi-Docstore Strategy
Each docstore gets:
- Dedicated OpenSearch index: `docstack-{slug}-{timestamp}`
- Metadata in PostgreSQL (name, description, stats)
- Dedicated pipelines (indexing + query) deployed to Hayhooks
- Model configuration (embedder, splitter settings)

Agents can query:
- **Single docstore**: `POST /api/v1/query/search` with `docstore: "vwl"`
- **Multiple docstores**: `POST /api/v1/query/search-multi` with `docstores: ["vwl", "marketing"]`

## Development Commands

### Backend (FastAPI)

```bash
# Navigate to backend
cd backend

# Create virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with actual credentials

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 3081

# Run tests
pytest

# Create new migration
alembic revision --autogenerate -m "description"

# Format code
black app/
isort app/
```

### Frontend (Next.js)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# Edit .env.local if needed

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm run start

# Lint code
npm run lint
```

## Database Schema Overview

### Core Tables
- **users**: User authentication (email, password_hash, JWT sessions)
- **docstores**: Document stores (name, slug, index_name, stats)
- **documents**: Documents within docstores (filename, status, chunks)
- **model_configs**: Embedder and splitter settings per docstore
- **pipelines**: Indexing and query pipelines (YAML, deployment status)
- **sessions**: User sessions (JWT tokens, expiration)
- **audit_logs**: Audit trail for all operations

### Important Relationships
- Documents CASCADE delete when docstore is deleted
- Pipelines CASCADE delete when docstore is deleted
- Each docstore has one active model_config
- Each docstore has two pipelines (indexing + query)

## API Architecture

**Base URL**: `http://10.36.0.111:3081/api/v1/` (production) or `http://localhost:3081/api/v1/` (development)

### Key Endpoint Groups
- `/auth/*` - Authentication (login, logout, register, verify)
- `/docstores/*` - Docstore CRUD and management
- `/docstores/{id}/documents` - Document upload/management
- `/docstores/{id}/pipelines` - Pipeline configuration
- `/query/*` - Query single or multiple docstores
- `/health` - Health check (DB, OpenSearch, Hayhooks connectivity)

### Authentication Flow
- **Web App**: Hybrid JWT + session cookies (httpOnly, Secure, SameSite=Lax)
- **LibreChat Agents**: JWT tokens in Authorization header
- **Password Hashing**: Bcrypt with 12 rounds

## Pipeline Management

### Pipeline Deployment Flow
1. User creates/updates pipeline in UI (YAML editor)
2. Backend validates YAML structure
3. Backend uses Jinja2 to generate final pipeline with docstore-specific variables:
   - `index_name`: `docstack-{slug}-{timestamp}`
   - `embedder_model`: from model_config
   - `split_by`, `split_length`, `split_overlap`: from model_config
4. Backend SSHs to container 112 (Hayhooks) via paramiko
5. Writes pipeline YAML to `/opt/hayhooks/pipelines/{docstore_slug}/`
6. Hayhooks auto-detects and deploys new pipelines

### Pipeline Templates Location
- `shared/pipeline-templates/indexing.yaml.j2` - Indexing pipeline template
- `shared/pipeline-templates/query.yaml.j2` - Query pipeline template

### Hayhooks Integration
- **Indexing endpoint**: `http://10.36.0.112:1416/{docstore_slug}_indexing/run`
- **Query endpoint**: `http://10.36.0.112:1416/{docstore_slug}_query/run`
- **Response format** (Hayhooks 1.8.0):
  ```json
  {
    "result": {
      "prompt_builder": {"prompt": "..."},
      "retriever": {"documents": [...]}
    }
  }
  ```

## OpenSearch Integration

### Direct Operations (via opensearch-py)
- Create index with knn_vector mapping (dimension from model_config)
- Delete index when docstore is deleted
- Delete documents by query (when single document deleted)
- Get index stats (document count, size)

### Via Hayhooks (for indexing/querying)
- Document upload triggers indexing pipeline
- Query requests go through query pipeline
- Multi-docstore queries use index pattern: `docstack-vwl-*,docstack-marketing-*`

## File Upload & Processing Flow

1. User uploads file(s) via frontend (react-dropzone)
2. Backend saves metadata to PostgreSQL immediately (status: 'pending')
3. Backend calculates SHA256 checksum for deduplication
4. Backend sends file to Hayhooks indexing endpoint
5. Hayhooks processes: FileTypeRouter → Converter → Splitter → Embedder → DocumentWriter
6. Backend updates document metadata with chunk count and status ('completed' or 'failed')

## Frontend Structure

### Route Organization
```
/app/
├── (auth)/
│   ├── login/page.tsx           # Login page
│   └── layout.tsx
├── (dashboard)/
│   ├── layout.tsx               # Sidebar + header
│   ├── page.tsx                 # Dashboard overview
│   ├── docstores/
│   │   ├── page.tsx             # List all docstores
│   │   ├── new/page.tsx         # Create docstore
│   │   └── [id]/
│   │       ├── page.tsx         # Docstore details
│   │       ├── documents/page.tsx
│   │       ├── pipelines/page.tsx
│   │       └── settings/page.tsx
│   ├── query/page.tsx           # Query interface
│   └── settings/page.tsx
```

### State Management
- **Zustand stores**:
  - `authStore.ts` - User authentication state
  - `docstoreStore.ts` - Docstore management
- **React Query** (@tanstack/react-query) - Server state management
- **React Hook Form + Zod** - Form validation

### UI Components (shadcn/ui + Radix UI)
- All UI components use shadcn/ui patterns
- TailwindCSS v4 for styling
- Monaco editor for YAML pipeline editing
- react-dropzone for file uploads

## LibreChat Integration

DocStack is deployed on the same container (111) as LibreChat, enabling seamless integration:

### Option A: Direct API (Recommended)
Agents call `http://localhost:3081/api/v1/query/search` with:
- JWT token in Authorization header
- `docstore` slug in request body
- `query` text in request body

### Option B: Proxy via simple_wrapper.py
Add endpoint to simple_wrapper.py on container 112 to proxy requests to DocStack API.

### LibreChat Tool Configuration Example
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
            required: true
          - name: query
            type: string
            required: true
        endpoint: http://localhost:3081/api/v1/query/search
        method: POST
```

## Critical Implementation Notes

### Index Naming with Timestamps
Use `int(time.time())` for unique index names to support zero-downtime reindexing. Old indices can be kept temporarily while new ones are built.

### Document Deduplication
Calculate SHA256 checksum before upload and check against existing documents in the same docstore to prevent duplicates.

### Session Cleanup
Use APScheduler to clean expired sessions every hour (configured in backend).

### Embedding Dimension Auto-Detection
Maintain a lookup table for common models:
- `BAAI/bge-large-en-v1.5`: 1024 dimensions
- `BAAI/bge-base-en-v1.5`: 768 dimensions
- Verify actual dimensions with current embedder configuration

### Multi-Docstore Query Pattern
Use OpenSearch multi-index syntax: `docstack-vwl-*,docstack-marketing-*` to query multiple docstores simultaneously.

## Deployment

### Target Environment
- **Container 111** at 10.36.0.111
- Runs alongside LibreChat (port 3080)
- DocStack uses ports 3000 (frontend) and 3081 (backend)

### Systemd Services
- `docstack-backend.service` - Backend API (uvicorn)
- `docstack-frontend.service` - Frontend (Next.js)

### Access via Nginx
Reverse proxy on container 100 routes `docstack.local` to container 111:3000

See `docs/DEPLOYMENT.md` for detailed deployment instructions.

## Important Files to Reference

### Backend
- `backend/app/main.py` - FastAPI application entry point
- `backend/app/models/` - SQLAlchemy database models
- `backend/app/api/v1/` - API route handlers
- `backend/app/services/opensearch.py` - OpenSearch client
- `backend/app/services/hayhooks.py` - Hayhooks integration
- `backend/app/services/pipeline_generator.py` - Jinja2 pipeline templates
- `backend/app/core/auth.py` - JWT + session authentication

### Frontend
- `frontend/app/(dashboard)/docstores/[id]/documents/page.tsx` - Document management UI
- `frontend/components/documents/DocumentUploader.tsx` - File upload component
- `frontend/components/pipelines/PipelineEditor.tsx` - YAML editor
- `frontend/stores/` - Zustand state management

### Templates
- `shared/pipeline-templates/indexing.yaml.j2` - Indexing pipeline template
- `shared/pipeline-templates/query.yaml.j2` - Query pipeline template

### Documentation
- `docs/PLAN.md` - Complete implementation plan with all technical details
- `docs/DEPLOYMENT.md` - Deployment guide

## External Service References

When implementing integrations, reference these existing implementations:
- `/opt/hayhooks/simple_wrapper.py` (on container 112) - FastAPI wrapper pattern
- `/opt/hayhooks/pipelines/indexing.yaml` (on container 112) - Current indexing pipeline
- `/opt/hayhooks/pipelines/query.yaml` (on container 112) - Current query pipeline format
- `/opt/LibreChat/librechat.yaml` (on container 111) - Agent tool configuration pattern
