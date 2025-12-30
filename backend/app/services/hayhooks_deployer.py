import paramiko
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class HayhooksDeployer:
    """Service for deploying pipeline YAML files to Hayhooks via SSH"""

    def __init__(
        self,
        host: str = "10.36.0.112",
        username: str = "root",
        key_filename: str = "/root/.ssh/id_ed25519",
        pipelines_base_dir: str = "/opt/hayhooks/pipelines"
    ):
        self.host = host
        self.username = username
        self.key_filename = key_filename
        self.pipelines_base_dir = pipelines_base_dir

    def _get_ssh_client(self) -> paramiko.SSHClient:
        """Create and return authenticated SSH client"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                self.host,
                username=self.username,
                key_filename=self.key_filename,
                timeout=10
            )
            logger.info(f"SSH connected to {self.host}")
            return ssh
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {e}")
            raise

    def deploy_pipelines(
        self,
        slug: str,
        indexing_yaml: str,
        query_yaml: str
    ) -> bool:
        """
        Deploy indexing and query pipelines to hayhooks

        Args:
            slug: Docstore slug (directory name)
            indexing_yaml: Indexing pipeline YAML content
            query_yaml: Query pipeline YAML content

        Returns:
            True if deployment successful

        Raises:
            Exception if deployment fails
        """
        ssh = None
        sftp = None

        try:
            # Connect via SSH
            ssh = self._get_ssh_client()
            sftp = ssh.open_sftp()

            # Create directory for this docstore
            pipeline_dir = f"{self.pipelines_base_dir}/{slug}"
            try:
                sftp.stat(pipeline_dir)
            except IOError:
                # Directory doesn't exist, create it
                ssh.exec_command(f"mkdir -p {pipeline_dir}")
                logger.info(f"Created directory: {pipeline_dir}")

            # Write indexing pipeline
            indexing_path = f"{pipeline_dir}/indexing.yaml"
            with sftp.open(indexing_path, 'w') as f:
                f.write(indexing_yaml)
            logger.info(f"Deployed indexing pipeline to {indexing_path}")

            # Write query pipeline
            query_path = f"{pipeline_dir}/query.yaml"
            with sftp.open(query_path, 'w') as f:
                f.write(query_yaml)
            logger.info(f"Deployed query pipeline to {query_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to deploy pipelines for {slug}: {e}")
            raise

        finally:
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()

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
        ssh = None

        try:
            ssh = self._get_ssh_client()
            pipeline_dir = f"{self.pipelines_base_dir}/{slug}"

            # Delete the directory and all contents
            stdin, stdout, stderr = ssh.exec_command(f"rm -rf {pipeline_dir}")
            exit_code = stdout.channel.recv_exit_status()

            if exit_code == 0:
                logger.info(f"Deleted pipelines for {slug}")
                return True
            else:
                error = stderr.read().decode()
                logger.error(f"Failed to delete pipelines: {error}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete pipelines for {slug}: {e}")
            raise

        finally:
            if ssh:
                ssh.close()

    def check_deployment(self, slug: str) -> Dict[str, Any]:
        """
        Check if pipelines are deployed

        Args:
            slug: Docstore slug

        Returns:
            Dictionary with deployment status and file list
        """
        ssh = None
        sftp = None

        try:
            ssh = self._get_ssh_client()
            sftp = ssh.open_sftp()

            pipeline_dir = f"{self.pipelines_base_dir}/{slug}"

            try:
                # List files in directory
                files = sftp.listdir(pipeline_dir)

                return {
                    "deployed": True,
                    "files": files,
                    "indexing_exists": "indexing.yaml" in files,
                    "query_exists": "query.yaml" in files
                }

            except IOError:
                # Directory doesn't exist
                return {
                    "deployed": False,
                    "files": [],
                    "indexing_exists": False,
                    "query_exists": False
                }

        except Exception as e:
            logger.error(f"Failed to check deployment for {slug}: {e}")
            return {
                "deployed": False,
                "error": str(e)
            }

        finally:
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()

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

        ssh = None
        sftp = None

        try:
            ssh = self._get_ssh_client()
            sftp = ssh.open_sftp()

            pipeline_path = f"{self.pipelines_base_dir}/{slug}/{pipeline_type}.yaml"

            with sftp.open(pipeline_path, 'w') as f:
                f.write(yaml_content)

            logger.info(f"Updated {pipeline_type} pipeline for {slug}")
            return True

        except Exception as e:
            logger.error(f"Failed to update {pipeline_type} pipeline for {slug}: {e}")
            raise

        finally:
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()


# Singleton instance
hayhooks_deployer = HayhooksDeployer()
