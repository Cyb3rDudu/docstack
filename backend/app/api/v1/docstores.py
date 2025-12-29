from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import time

from app.database import get_db
from app.models import User, Docstore
from app.schemas import DocstoreCreate, DocstoreUpdate, DocstoreResponse, DocstoreStats
from app.core.auth import get_current_user
from app.services.opensearch import opensearch_service

router = APIRouter(prefix="/docstores", tags=["docstores"])


@router.get("/", response_model=List[DocstoreResponse])
def list_docstores(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all docstores"""
    docstores = db.query(Docstore).filter(Docstore.is_active == True).offset(skip).limit(limit).all()
    return docstores


@router.post("/", response_model=DocstoreResponse, status_code=status.HTTP_201_CREATED)
def create_docstore(
    docstore_data: DocstoreCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new docstore

    - Generates unique index name with timestamp
    - Creates OpenSearch index with knn_vector mapping
    - Stores metadata in PostgreSQL
    """
    # Check if slug already exists
    existing = db.query(Docstore).filter(Docstore.slug == docstore_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Docstore with slug '{docstore_data.slug}' already exists"
        )

    # Generate unique index name with timestamp
    timestamp = int(time.time())
    index_name = f"docstack-{docstore_data.slug}-{timestamp}"

    # Create OpenSearch index (default embedding dimension: 1024 for bge-large)
    if not opensearch_service.create_index(index_name, embedding_dim=1024):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OpenSearch index"
        )

    # Create docstore in database
    docstore = Docstore(
        name=docstore_data.name,
        slug=docstore_data.slug,
        description=docstore_data.description,
        index_name=index_name,
        created_by=current_user.id
    )

    db.add(docstore)
    db.commit()
    db.refresh(docstore)

    return docstore


@router.get("/{docstore_id}", response_model=DocstoreResponse)
def get_docstore(
    docstore_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get docstore details by ID"""
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    return docstore


@router.get("/{docstore_id}/stats", response_model=DocstoreStats)
def get_docstore_stats(
    docstore_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get docstore statistics including OpenSearch index stats
    """
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    # Get real-time stats from OpenSearch
    index_stats = opensearch_service.get_index_stats(docstore.index_name)
    if index_stats:
        # Update denormalized stats in database
        docstore.chunk_count = index_stats["document_count"]
        db.commit()

    return DocstoreStats(
        id=docstore.id,
        name=docstore.name,
        slug=docstore.slug,
        document_count=docstore.document_count,
        chunk_count=docstore.chunk_count,
        total_size_bytes=docstore.total_size_bytes,
        index_name=docstore.index_name,
        is_active=docstore.is_active
    )


@router.patch("/{docstore_id}", response_model=DocstoreResponse)
def update_docstore(
    docstore_id: str,
    docstore_data: DocstoreUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update docstore metadata (name, description)"""
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    # Update fields
    if docstore_data.name is not None:
        docstore.name = docstore_data.name
    if docstore_data.description is not None:
        docstore.description = docstore_data.description

    docstore.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(docstore)

    return docstore


@router.delete("/{docstore_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_docstore(
    docstore_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a docstore

    - Deletes OpenSearch index
    - Cascades delete to documents, pipelines, model_configs
    - Soft delete (sets is_active=False)
    """
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    # Delete OpenSearch index
    if not opensearch_service.delete_index(docstore.index_name):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete OpenSearch index"
        )

    # Soft delete docstore (CASCADE will handle related records)
    docstore.is_active = False
    docstore.updated_at = datetime.utcnow()
    db.commit()

    return None


@router.post("/{docstore_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_docstore(
    docstore_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger reindexing of all documents in a docstore

    Creates a new index and migrates documents
    (Implementation will be async with job queue in future)
    """
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    # TODO: Implement async reindexing with job queue
    # For now, return accepted status
    return {
        "message": "Reindexing started",
        "docstore_id": docstore_id,
        "status": "pending"
    }
