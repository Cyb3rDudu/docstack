import requests
from typing import Optional, Dict, Any
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class HayhooksDeployer:
    """Service for deploying pipeline YAML files to Hayhooks via HTTP API"""

    def __init__(
        self,
        base_url: str = "http://10.36.0.112:1416"
    ):
        self.base_url = base_url.rstrip('/')

    def deploy_pipelines(
        self,
        slug: str,
        indexing_yaml: str,
        query_yaml: str
    ) -> bool:
        """
        Deploy indexing and query pipelines to hayhooks via HTTP API

        Args:
            slug: Docstore slug (used as pipeline name prefix)
            indexing_yaml: Indexing pipeline YAML content
            query_yaml: Query pipeline YAML content

        Returns:
            True if deployment successful

        Raises:
            Exception if deployment fails
        """
        try:
            # Deploy indexing pipeline
            indexing_name = f"{slug}_indexing"
            indexing_response = requests.post(
                f"{self.base_url}/deploy-yaml",
                json={
                    "name": indexing_name,
                    "source_code": indexing_yaml,
                    "description": f"Indexing pipeline for {slug}",
                    "overwrite": False,
                    "save_file": True
                },
                timeout=30
            )

            if indexing_response.status_code not in [200, 201]:
                raise Exception(
                    f"Failed to deploy indexing pipeline: "
                    f"{indexing_response.status_code} - {indexing_response.text}"
                )

            logger.info(f"Deployed indexing pipeline: {indexing_name}")

            # Deploy query pipeline
            query_name = f"{slug}_query"
            query_response = requests.post(
                f"{self.base_url}/deploy-yaml",
                json={
                    "name": query_name,
                    "source_code": query_yaml,
                    "description": f"Query pipeline for {slug}",
                    "overwrite": False,
                    "save_file": True
                },
                timeout=30
            )

            if query_response.status_code not in [200, 201]:
                # Rollback: undeploy indexing pipeline
                self._undeploy_single_pipeline(indexing_name)
                raise Exception(
                    f"Failed to deploy query pipeline: "
                    f"{query_response.status_code} - {query_response.text}"
                )

            logger.info(f"Deployed query pipeline: {query_name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed while deploying pipelines for {slug}: {e}")
            raise Exception(f"Failed to connect to hayhooks: {e}")
        except Exception as e:
            logger.error(f"Failed to deploy pipelines for {slug}: {e}")
            raise

    def _undeploy_single_pipeline(self, pipeline_name: str) -> bool:
        """
        Undeploy a single pipeline (internal helper)

        Args:
            pipeline_name: Name of the pipeline to undeploy

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.delete(
                f"{self.base_url}/undeploy/{pipeline_name}",
                timeout=10
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to undeploy {pipeline_name}: {e}")
            return False

    def delete_pipelines(self, slug: str) -> bool:
        """
        Delete pipelines for a docstore

        Args:
            slug: Docstore slug

        Returns:
            True if deletion successful

        Raises:
            Exception if deletion fails
        """
        try:
            indexing_name = f"{slug}_indexing"
            query_name = f"{slug}_query"

            # Delete both pipelines
            indexing_deleted = self._undeploy_single_pipeline(indexing_name)
            query_deleted = self._undeploy_single_pipeline(query_name)

            if indexing_deleted or query_deleted:
                logger.info(f"Deleted pipelines for {slug}")
                return True
            else:
                logger.warning(f"No pipelines found to delete for {slug}")
                return True  # Not an error if they don't exist

        except Exception as e:
            logger.error(f"Failed to delete pipelines for {slug}: {e}")
            raise

    def check_deployment(self, slug: str) -> Dict[str, Any]:
        """
        Check if pipelines are deployed

        Args:
            slug: Docstore slug

        Returns:
            Dictionary with deployment status
        """
        try:
            indexing_name = f"{slug}_indexing"
            query_name = f"{slug}_query"

            # Get status of both pipelines
            response = requests.get(f"{self.base_url}/status", timeout=10)

            if response.status_code != 200:
                return {
                    "deployed": False,
                    "error": f"Failed to get status: {response.status_code}"
                }

            status_data = response.json()
            pipelines = status_data.get("pipelines", [])
            pipeline_names = [p.get("name") for p in pipelines]

            indexing_exists = indexing_name in pipeline_names
            query_exists = query_name in pipeline_names

            return {
                "deployed": indexing_exists and query_exists,
                "indexing_exists": indexing_exists,
                "query_exists": query_exists,
                "pipelines": [indexing_name, query_name] if indexing_exists and query_exists else []
            }

        except Exception as e:
            logger.error(f"Failed to check deployment for {slug}: {e}")
            return {
                "deployed": False,
                "error": str(e)
            }

    def update_pipeline(self, slug: str, pipeline_type: str, yaml_content: str) -> bool:
        """
        Update a specific pipeline (indexing or query)

        Args:
            slug: Docstore slug
            pipeline_type: "indexing" or "query"
            yaml_content: New YAML content

        Returns:
            True if update successful

        Raises:
            Exception if update fails
        """
        if pipeline_type not in ["indexing", "query"]:
            raise ValueError("pipeline_type must be 'indexing' or 'query'")

        try:
            pipeline_name = f"{slug}_{pipeline_type}"

            response = requests.post(
                f"{self.base_url}/deploy-yaml",
                json={
                    "name": pipeline_name,
                    "source_code": yaml_content,
                    "description": f"{pipeline_type.capitalize()} pipeline for {slug}",
                    "overwrite": True,  # Allow overwriting for updates
                    "save_file": True
                },
                timeout=30
            )

            if response.status_code not in [200, 201]:
                raise Exception(
                    f"Failed to update {pipeline_type} pipeline: "
                    f"{response.status_code} - {response.text}"
                )

            logger.info(f"Updated {pipeline_type} pipeline for {slug}")
            return True

        except Exception as e:
            logger.error(f"Failed to update {pipeline_type} pipeline for {slug}: {e}")
            raise

    def get_all_pipelines(self) -> Dict[str, Any]:
        """
        Get all deployed pipelines from hayhooks

        Returns:
            Dictionary with status and list of pipelines
        """
        try:
            response = requests.get(f"{self.base_url}/status", timeout=10)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to get status: {response.status_code}"
                }

            return {
                "success": True,
                "data": response.json()
            }

        except Exception as e:
            logger.error(f"Failed to get all pipelines: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
hayhooks_deployer = HayhooksDeployer()
