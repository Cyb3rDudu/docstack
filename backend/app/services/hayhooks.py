import httpx
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class HayhooksService:
    """Service for interacting with Hayhooks pipeline runtime"""

    def __init__(self):
        self.base_url = settings.HAYHOOKS_URL
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for document processing

    async def index_documents(
        self,
        docstore_slug: str,
        files: List[tuple],  # List of (filename, file_content, mime_type)
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send documents to Hayhooks indexing pipeline

        Args:
            docstore_slug: Slug of the docstore (determines pipeline name)
            files: List of tuples (filename, content, mime_type)
            metadata: Additional metadata to include

        Returns:
            Response from Hayhooks or None if error
        """
        pipeline_url = f"{self.base_url}/{docstore_slug}_indexing/run"

        try:
            # Prepare multipart form data
            files_data = []
            for filename, content, mime_type in files:
                files_data.append(
                    ("files", (filename, content, mime_type))
                )

            # Add metadata if provided
            data = {}
            if metadata:
                data["metadata"] = str(metadata)

            response = await self.client.post(
                pipeline_url,
                files=files_data,
                data=data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Hayhooks indexing error for {docstore_slug}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during indexing: {e}")
            return None

    async def query_documents(
        self,
        docstore_slug: str,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query documents via Hayhooks query pipeline

        Args:
            docstore_slug: Slug of the docstore
            query_text: Search query text
            top_k: Number of results to return
            filters: Optional filters to apply

        Returns:
            Query results or None if error
        """
        pipeline_url = f"{self.base_url}/{docstore_slug}_query/run"

        try:
            payload = {
                "query": query_text,
                "top_k": top_k
            }
            if filters:
                payload["filters"] = filters

            response = await self.client.post(
                pipeline_url,
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # Hayhooks 1.8.0 format: {"result": {"retriever": {"documents": [...]}}}
            return result.get("result", {})

        except httpx.HTTPError as e:
            logger.error(f"Hayhooks query error for {docstore_slug}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during query: {e}")
            return None

    async def query_multi_docstores(
        self,
        docstore_slugs: List[str],
        query_text: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Query multiple docstores in parallel

        Args:
            docstore_slugs: List of docstore slugs
            query_text: Search query text
            top_k: Number of results per docstore

        Returns:
            Dictionary mapping docstore_slug to results
        """
        results = {}

        # Query all docstores in parallel
        import asyncio
        tasks = [
            self.query_documents(slug, query_text, top_k)
            for slug in docstore_slugs
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for slug, response in zip(docstore_slugs, responses):
            if isinstance(response, Exception):
                logger.error(f"Error querying {slug}: {response}")
                results[slug] = {"error": str(response)}
            else:
                results[slug] = response

        return results

    async def health_check(self) -> bool:
        """Check if Hayhooks is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/status")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Hayhooks health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
hayhooks_service = HayhooksService()
