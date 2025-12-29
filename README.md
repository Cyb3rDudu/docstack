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
