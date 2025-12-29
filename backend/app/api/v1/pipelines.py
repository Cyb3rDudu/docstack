from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime

from app.database import get_db
from app.models import User, Docstore, Pipeline, PipelineType, ModelConfig
from app.schemas import PipelineCreate, PipelineUpdate, PipelineResponse
from app.core.auth import get_current_user
from app.services.pipeline_generator import pipeline_generator

router = APIRouter(prefix="/docstores/{docstore_id}/pipelines", tags=["pipelines"])


@router.get("/", response_model=List[PipelineResponse])
def list_pipelines(
    docstore_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pipelines for a docstore"""
    # Verify docstore exists
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    pipelines = db.query(Pipeline).filter(
        Pipeline.docstore_id == docstore_id
    ).all()

    return pipelines


@router.post("/generate", response_model=Dict[str, str])
def generate_default_pipelines(
    docstore_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate default indexing and query pipelines for a docstore
    based on its model configuration
    """
    # Verify docstore exists
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    # Get active model config
    model_config = db.query(ModelConfig).filter(
        ModelConfig.docstore_id == docstore_id,
        ModelConfig.is_active == True
    ).first()

    if not model_config:
        # Create default model config
        model_config = ModelConfig(
            docstore_id=docstore_id,
            embedder_model="BAAI/bge-large-en-v1.5",
            splitter_type="sentence",
            split_length=55,
            split_overlap=5,
            embedder_settings={"normalize_embeddings": True, "batch_size": 32}
        )
        db.add(model_config)
        db.commit()
        db.refresh(model_config)

    # Generate indexing pipeline
    indexing_yaml = pipeline_generator.generate_indexing_pipeline(
        index_name=docstore.index_name,
        embedder_model=model_config.embedder_model,
        split_by=model_config.splitter_type,
        split_length=model_config.split_length,
        split_overlap=model_config.split_overlap,
        normalize_embeddings=model_config.embedder_settings.get("normalize_embeddings", True),
        batch_size=model_config.embedder_settings.get("batch_size", 32)
    )

    # Generate query pipeline
    query_yaml = pipeline_generator.generate_query_pipeline(
        index_name=docstore.index_name,
        embedder_model=model_config.embedder_model,
        normalize_embeddings=model_config.embedder_settings.get("normalize_embeddings", True),
        top_k=10
    )

    return {
        "indexing": indexing_yaml,
        "query": query_yaml
    }


@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    docstore_id: str,
    pipeline_data: PipelineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new pipeline for a docstore"""
    # Verify docstore exists
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    # Deactivate other pipelines of the same type
    db.query(Pipeline).filter(
        Pipeline.docstore_id == docstore_id,
        Pipeline.pipeline_type == pipeline_data.pipeline_type
    ).update({"is_active": False})

    # Create new pipeline
    pipeline = Pipeline(
        docstore_id=docstore_id,
        created_by=current_user.id,
        name=pipeline_data.name,
        pipeline_type=pipeline_data.pipeline_type,
        yaml_content=pipeline_data.yaml_content,
        is_active=True
    )

    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    return pipeline


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    docstore_id: str,
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pipeline details by ID"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.docstore_id == docstore_id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )

    return pipeline


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    docstore_id: str,
    pipeline_id: str,
    pipeline_data: PipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a pipeline"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.docstore_id == docstore_id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )

    # Update fields
    if pipeline_data.name is not None:
        pipeline.name = pipeline_data.name
    if pipeline_data.yaml_content is not None:
        pipeline.yaml_content = pipeline_data.yaml_content
        pipeline.version += 1
        pipeline.deployed = False  # Mark as not deployed after update
    if pipeline_data.is_active is not None:
        # If activating, deactivate other pipelines of same type
        if pipeline_data.is_active:
            db.query(Pipeline).filter(
                Pipeline.docstore_id == docstore_id,
                Pipeline.pipeline_type == pipeline.pipeline_type,
                Pipeline.id != pipeline_id
            ).update({"is_active": False})
        pipeline.is_active = pipeline_data.is_active

    pipeline.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pipeline)

    return pipeline


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline(
    docstore_id: str,
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a pipeline"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.docstore_id == docstore_id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )

    db.delete(pipeline)
    db.commit()

    return None


@router.post("/{pipeline_id}/deploy", status_code=status.HTTP_202_ACCEPTED)
def deploy_pipeline(
    docstore_id: str,
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deploy a pipeline to Hayhooks

    TODO: Implement SSH deployment to container 112
    For now, returns accepted status
    """
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.docstore_id == docstore_id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )

    # TODO: Implement SSH deployment via paramiko
    # Write pipeline YAML to /opt/hayhooks/pipelines/{docstore_slug}/{pipeline_type}.yaml
    # Hayhooks will auto-detect and deploy

    # For now, mark as deployed
    pipeline.deployed = True
    pipeline.deployed_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Pipeline deployment started",
        "pipeline_id": pipeline_id,
        "status": "deployed"
    }
