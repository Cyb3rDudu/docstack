from opensearchpy import OpenSearch, exceptions
from typing import Optional, Dict, Any, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service for managing OpenSearch indices and operations"""

    def __init__(self):
        self.client = OpenSearch(
            hosts=[settings.OPENSEARCH_URL],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
        )

    def create_index(self, index_name: str, embedding_dim: int = 1024, ef_search: int = 512) -> bool:
        """
        Create an OpenSearch index with knn_vector mapping for embeddings

        Args:
            index_name: Name of the index to create
            embedding_dim: Dimension of the embedding vectors
            ef_search: ef_search parameter for knn (default: 512)

        Returns:
            True if created successfully, False otherwise
        """
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": ef_search
                },
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": embedding_dim,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "meta": {"type": "object", "enabled": True},
                    "id": {"type": "keyword"}
                }
            }
        }

        try:
            response = self.client.indices.create(index=index_name, body=index_body)
            logger.info(f"Created index: {index_name}")
            return response.get("acknowledged", False)
        except exceptions.RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.warning(f"Index {index_name} already exists")
                return True
            logger.error(f"Error creating index {index_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating index {index_name}: {e}")
            return False

    def delete_index(self, index_name: str) -> bool:
        """
        Delete an OpenSearch index

        Args:
            index_name: Name of the index to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = self.client.indices.delete(index=index_name)
            logger.info(f"Deleted index: {index_name}")
            return response.get("acknowledged", False)
        except exceptions.NotFoundError:
            logger.warning(f"Index {index_name} not found")
            return True
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {e}")
            return False

    def index_exists(self, index_name: str) -> bool:
        """Check if an index exists"""
        try:
            return self.client.indices.exists(index=index_name)
        except Exception as e:
            logger.error(f"Error checking if index {index_name} exists: {e}")
            return False

    def get_index_stats(self, index_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for an index

        Args:
            index_name: Name of the index

        Returns:
            Dictionary with index stats or None if error
        """
        try:
            stats = self.client.indices.stats(index=index_name)
            index_stats = stats["indices"][index_name]

            return {
                "document_count": index_stats["total"]["docs"]["count"],
                "size_bytes": index_stats["total"]["store"]["size_in_bytes"],
                "deleted_docs": index_stats["total"]["docs"]["deleted"]
            }
        except Exception as e:
            logger.error(f"Error getting stats for index {index_name}: {e}")
            return None

    def delete_documents_by_query(self, index_name: str, query: Dict[str, Any]) -> bool:
        """
        Delete documents matching a query

        Args:
            index_name: Name of the index
            query: OpenSearch query DSL

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = self.client.delete_by_query(
                index=index_name,
                body={"query": query}
            )
            deleted = response.get("deleted", 0)
            logger.info(f"Deleted {deleted} documents from {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents from {index_name}: {e}")
            return False

    def delete_document_by_source_id(self, index_name: str, source_id: str) -> bool:
        """
        Delete documents with a specific source_id

        Args:
            index_name: Name of the index
            source_id: Source ID to match

        Returns:
            True if deleted successfully, False otherwise
        """
        query = {"term": {"source_id": source_id}}
        return self.delete_documents_by_query(index_name, query)

    def search(self, index_name: str, query: Dict[str, Any], size: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Search documents in an index

        Args:
            index_name: Name of the index
            query: OpenSearch query DSL
            size: Number of results to return

        Returns:
            List of matching documents or None if error
        """
        try:
            response = self.client.search(
                index=index_name,
                body={"query": query, "size": size}
            )
            hits = response.get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        except Exception as e:
            logger.error(f"Error searching index {index_name}: {e}")
            return None

    def health_check(self) -> bool:
        """Check if OpenSearch is healthy"""
        try:
            health = self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return False


# Singleton instance
opensearch_service = OpenSearchService()
