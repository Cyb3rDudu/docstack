from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import hashlib
import mimetypes

from app.database import get_db
from app.models import User, Docstore, Document, ProcessingStatus
from app.schemas import DocumentUploadResponse, DocumentResponse
from app.core.auth import get_current_user
from app.services.hayhooks import hayhooks_service

router = APIRouter(prefix="/docstores/{docstore_id}/documents", tags=["documents"])


async def calculate_checksum(content: bytes) -> str:
    """Calculate SHA256 checksum of file content"""
    return hashlib.sha256(content).hexdigest()


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    docstore_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents in a docstore"""
    # Verify docstore exists
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    documents = db.query(Document).filter(
        Document.docstore_id == docstore_id
    ).offset(skip).limit(limit).all()

    return documents


@router.post("/", response_model=List[DocumentUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    docstore_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload documents to a docstore

    - Calculates SHA256 checksum for deduplication
    - Stores metadata in PostgreSQL immediately
    - Sends files to Hayhooks for indexing asynchronously
    - Supports PDF, DOCX, TXT files
    """
    # Verify docstore exists
    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
    if not docstore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Docstore not found"
        )

    uploaded_documents = []
    files_for_hayhooks = []

    for file in files:
        # Read file content
        content = await file.read()
        file_size = len(content)

        # Calculate checksum
        checksum = await calculate_checksum(content)

        # Check for duplicates
        existing_doc = db.query(Document).filter(
            Document.docstore_id == docstore_id,
            Document.checksum == checksum
        ).first()

        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document '{file.filename}' already exists in this docstore (duplicate checksum)"
            )

        # Detect MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

        # Validate file type
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ]
        if mime_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {mime_type}. Allowed: PDF, DOCX, TXT"
            )

        # Create document record in database
        document = Document(
            docstore_id=docstore_id,
            uploaded_by=current_user.id,
            filename=file.filename,
            original_filename=file.filename,
            mime_type=mime_type,
            size_bytes=file_size,
            checksum=checksum,
            processing_status=ProcessingStatus.PENDING
        )

        db.add(document)
        db.flush()  # Get the document ID

        # Prepare for Hayhooks
        files_for_hayhooks.append((file.filename, content, mime_type))
        uploaded_documents.append(document)

    # Commit all documents to database
    db.commit()

    # Send files to Hayhooks for indexing (async)
    try:
        # Update status to processing
        for doc in uploaded_documents:
            doc.processing_status = ProcessingStatus.PROCESSING
        db.commit()

        # Call Hayhooks indexing pipeline
        result = await hayhooks_service.index_documents(
            docstore_slug=docstore.slug,
            files=files_for_hayhooks
        )

        if result:
            # Update documents to completed
            for doc in uploaded_documents:
                doc.processing_status = ProcessingStatus.COMPLETED
                doc.processed_at = datetime.utcnow()
                # TODO: Extract chunk_count from Hayhooks response
                doc.chunk_count = 0
            db.commit()

            # Update docstore stats
            docstore.document_count += len(uploaded_documents)
            docstore.total_size_bytes += sum(doc.size_bytes for doc in uploaded_documents)
            db.commit()
        else:
            # Mark as failed
            for doc in uploaded_documents:
                doc.processing_status = ProcessingStatus.FAILED
                doc.processing_error = "Hayhooks indexing failed"
            db.commit()

    except Exception as e:
        # Mark as failed
        for doc in uploaded_documents:
            doc.processing_status = ProcessingStatus.FAILED
            doc.processing_error = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing documents: {str(e)}"
        )

    # Refresh to get latest data
    for doc in uploaded_documents:
        db.refresh(doc)

    return uploaded_documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    docstore_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details by ID"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.docstore_id == docstore_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    docstore_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document

    - Removes from PostgreSQL
    - Deletes chunks from OpenSearch by source_id
    - Updates docstore stats
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.docstore_id == docstore_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()

    # Delete from OpenSearch (if has source_id)
    if document.source_id:
        from app.services.opensearch import opensearch_service
        opensearch_service.delete_document_by_source_id(
            docstore.index_name,
            document.source_id
        )

    # Update docstore stats
    docstore.document_count = max(0, docstore.document_count - 1)
    docstore.total_size_bytes = max(0, docstore.total_size_bytes - document.size_bytes)
    docstore.chunk_count = max(0, docstore.chunk_count - document.chunk_count)

    # Delete from database
    db.delete(document)
    db.commit()

    return None
