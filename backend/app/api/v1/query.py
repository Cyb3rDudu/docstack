from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Docstore
from app.core.auth import get_current_user
from app.services.hayhooks_deployer import hayhooks_deployer

router = APIRouter(prefix="/query", tags=["query"])


class MultiDocstoreQueryRequest(BaseModel):
    docstore_ids: List[str]
    query: str
    top_k: int = 10


@router.post("/multi")
def query_multiple_docstores(
    request: MultiDocstoreQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query multiple docstores and aggregate results
    """
    if not request.docstore_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one docstore ID is required"
        )

    all_results = []

    for docstore_id in request.docstore_ids:
        # Get docstore
        docstore = db.query(Docstore).filter(Docstore.id == docstore_id).first()
        if not docstore:
            continue

        try:
            # Query this docstore
            result = hayhooks_deployer.query_pipeline(
                slug=docstore.slug,
                query=request.query,
                top_k=request.top_k
            )

            # Add docstore metadata to results
            if isinstance(result, dict) and 'documents' in result:
                for doc in result['documents']:
                    if isinstance(doc, dict):
                        doc['metadata'] = doc.get('metadata', {})
                        doc['metadata']['docstore_name'] = docstore.name
                        doc['metadata']['docstore_id'] = str(docstore.id)
                all_results.extend(result['documents'])

        except Exception as e:
            # Log error but continue with other docstores
            print(f"Error querying docstore {docstore.slug}: {e}")
            continue

    # Sort by score (highest first) and limit to top_k
    all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    all_results = all_results[:request.top_k]

    return {
        "results": all_results,
        "total": len(all_results),
        "docstores_queried": len(request.docstore_ids)
    }
