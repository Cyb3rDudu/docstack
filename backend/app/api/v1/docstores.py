from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import time
import re

from app.database import get_db
from app.models import User, Docstore, ModelConfig, Pipeline
from app.schemas import DocstoreCreate, DocstoreUpdate, DocstoreResponse, DocstoreStats
from app.core.auth import get_current_user
from app.services.opensearch import opensearch_service
from app.services.pipeline_generator import pipeline_generator
from app.services.hayhooks_deployer import hayhooks_deployer

router = APIRouter(prefix="/docstores", tags=["docstores"])


def generate_slug(name: str) -> str:
    """Generate URL-safe slug from docstore name"""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug


def generate_index_name(slug: str) -> str:
    """Generate unique OpenSearch index name with timestamp"""
    timestamp = int(time.time())
    return f"docstack-{slug}-{timestamp}"


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
    Create a new document store with semantic chunking

    Complete flow:
    1. Generate slug from name
    2. Create OpenSearch index with knn_vector mapping
    3. Generate indexing and query pipeline YAML files
    4. Deploy pipelines to hayhooks via SSH
    5. Save docstore, model_config, and pipelines to PostgreSQL
    """
    # 1. Generate slug and index name
    slug = generate_slug(docstore_data.name)
    index_name = generate_index_name(slug)

    # Check if slug already exists
    existing = db.query(Docstore).filter(Docstore.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Docstore with slug '{slug}' already exists. Please choose a different name."
        )

    # 2. Get embedding dimension and create OpenSearch index
    embedding_dim = pipeline_generator.get_embedding_dimension(docstore_data.embedding_model)

    try:
        if not opensearch_service.create_index(index_name, embedding_dim=embedding_dim):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create OpenSearch index"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create OpenSearch index: {str(e)}"
        )

    # 3. Generate pipeline YAML files
    try:
        indexing_yaml = pipeline_generator.generate_indexing_pipeline(
            docstore_name=docstore_data.name,
            index_name=index_name,
            embedder_model=docstore_data.embedding_model,
            split_by=docstore_data.split_by or "sentence",
            split_length=docstore_data.chunk_size,
            split_overlap=docstore_data.chunk_overlap
        )

        query_yaml = pipeline_generator.generate_query_pipeline(
            docstore_name=docstore_data.name,
            index_name=index_name,
            embedder_model=docstore_data.embedding_model,
            top_k=10
        )
    except Exception as e:
        # Rollback: delete OpenSearch index
        opensearch_service.delete_index(index_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate pipeline YAML: {str(e)}"
        )

    # 4. Deploy pipelines to hayhooks
    try:
        hayhooks_deployer.deploy_pipelines(slug, indexing_yaml, query_yaml)
    except Exception as e:
        # Rollback: delete OpenSearch index
        opensearch_service.delete_index(index_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy pipelines to hayhooks: {str(e)}"
        )

    # 5. Save to database (transaction)
    try:
        # Create docstore
        docstore = Docstore(
            name=docstore_data.name,
            slug=slug,
            description=docstore_data.description,
            index_name=index_name,
            created_by=current_user.id
        )
        db.add(docstore)
        db.flush()  # Get docstore.id without committing

        # Create model config
        model_config = ModelConfig(
            docstore_id=docstore.id,
            embedder_model=docstore_data.embedding_model,
            embedder_settings={"normalize": True, "batch_size": 32},
            splitter_type=docstore_data.split_by or "sentence",
            split_length=docstore_data.chunk_size,
            split_overlap=docstore_data.chunk_overlap,
            is_active=True
        )
        db.add(model_config)

        # Save indexing pipeline
        indexing_pipeline = Pipeline(
            docstore_id=docstore.id,
            name=f"{slug}_indexing",
            pipeline_type="indexing",
            yaml_content=indexing_yaml,
            version=1,
            is_active=True,
            deployed=True,
            created_by=current_user.id
        )
        db.add(indexing_pipeline)

        # Save query pipeline
        query_pipeline = Pipeline(
            docstore_id=docstore.id,
            name=f"{slug}_query",
            pipeline_type="query",
            yaml_content=query_yaml,
            version=1,
            is_active=True,
            deployed=True,
            created_by=current_user.id
        )
        db.add(query_pipeline)

        # Commit all changes
        db.commit()
        db.refresh(docstore)

        return docstore

    except Exception as e:
        db.rollback()
        # Rollback: delete index and pipelines
        opensearch_service.delete_index(index_name)
        hayhooks_deployer.delete_pipelines(slug)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save docstore to database: {str(e)}"
        )


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


@router.get("/models/embedding")
def list_embedding_models(
    current_user: User = Depends(get_current_user)
):
    """
    List available embedding models with their dimensions
    """
    models = [
        {
            "id": "BAAI/bge-large-en-v1.5",
            "name": "BGE Large EN v1.5",
            "dimension": 1024,
            "description": "High quality, larger model (1024 dims)"
        },
        {
            "id": "BAAI/bge-base-en-v1.5",
            "name": "BGE Base EN v1.5",
            "dimension": 768,
            "description": "Balanced performance and size (768 dims)"
        },
        {
            "id": "BAAI/bge-small-en-v1.5",
            "name": "BGE Small EN v1.5",
            "dimension": 384,
            "description": "Fast and lightweight (384 dims)"
        },
        {
            "id": "sentence-transformers/all-MiniLM-L6-v2",
            "name": "MiniLM L6 v2",
            "dimension": 384,
            "description": "Popular lightweight model (384 dims)"
        },
        {
            "id": "sentence-transformers/all-mpnet-base-v2",
            "name": "MPNet Base v2",
            "dimension": 768,
            "description": "High quality general purpose (768 dims)"
        },
        {
            "id": "intfloat/e5-large-v2",
            "name": "E5 Large v2",
            "dimension": 1024,
            "description": "State-of-the-art embeddings (1024 dims)"
        },
        {
            "id": "intfloat/e5-base-v2",
            "name": "E5 Base v2",
            "dimension": 768,
            "description": "Efficient and accurate (768 dims)"
        }
    ]
    return {"models": models}


@router.get("/chunking-strategies")
def list_chunking_strategies(
    current_user: User = Depends(get_current_user)
):
    """
    List available chunking strategies
    """
    strategies = [
        {
            "value": "sentence",
            "label": "Sentence-based (Semantic)",
            "description": "Split by sentence boundaries - best for semantic coherence",
            "recommended_chunk_size": 3,
            "recommended_overlap": 1,
            "size_unit": "sentences"
        },
        {
            "value": "word",
            "label": "Word-based (Fixed)",
            "description": "Split by word count - precise control over chunk size",
            "recommended_chunk_size": 200,
            "recommended_overlap": 20,
            "size_unit": "words"
        },
        {
            "value": "passage",
            "label": "Passage-based (Semantic)",
            "description": "Split by paragraph boundaries - preserves larger context",
            "recommended_chunk_size": 2,
            "recommended_overlap": 1,
            "size_unit": "passages"
        }
    ]
    return {"strategies": strategies}


@router.get("/pipelines/hayhooks")
def list_hayhooks_pipelines(
    current_user: User = Depends(get_current_user)
):
    """
    List all pipelines currently deployed in hayhooks
    """
    result = hayhooks_deployer.get_all_pipelines()

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hayhooks pipelines: {result.get('error')}"
        )

    return result.get("data", {})
