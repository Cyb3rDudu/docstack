from fastapi import APIRouter
from app.api.v1 import auth, docstores, documents, pipelines

api_router = APIRouter(prefix="/api/v1")

# Include route modules
api_router.include_router(auth.router)
api_router.include_router(docstores.router)
api_router.include_router(documents.router)
api_router.include_router(pipelines.router)
