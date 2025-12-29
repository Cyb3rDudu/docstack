from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Path to pipeline templates
TEMPLATES_DIR = Path(__file__).parents[3] / "shared" / "pipeline-templates"


class PipelineGenerator:
    """Service for generating Haystack pipeline YAML from Jinja2 templates"""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate_indexing_pipeline(
        self,
        index_name: str,
        embedder_model: str = "BAAI/bge-large-en-v1.5",
        split_by: str = "sentence",
        split_length: int = 55,
        split_overlap: int = 5,
        normalize_embeddings: bool = True,
        batch_size: int = 32,
        opensearch_host: str = "http://10.36.0.110:9200"
    ) -> str:
        """
        Generate indexing pipeline YAML

        Args:
            index_name: OpenSearch index name
            embedder_model: HuggingFace model ID
            split_by: Splitting method (sentence, word, passage)
            split_length: Number of units per chunk
            split_overlap: Number of units to overlap
            normalize_embeddings: Whether to normalize embeddings
            batch_size: Batch size for embedding
            opensearch_host: OpenSearch URL

        Returns:
            Generated YAML content as string
        """
        template = self.env.get_template("indexing.yaml.j2")

        context = {
            "index_name": index_name,
            "embedder_model": embedder_model,
            "split_by": split_by,
            "split_length": split_length,
            "split_overlap": split_overlap,
            "normalize_embeddings": normalize_embeddings,
            "batch_size": batch_size,
            "opensearch_host": opensearch_host
        }

        yaml_content = template.render(**context)
        logger.info(f"Generated indexing pipeline for index {index_name}")
        return yaml_content

    def generate_query_pipeline(
        self,
        index_name: str,
        embedder_model: str = "BAAI/bge-large-en-v1.5",
        top_k: int = 10,
        normalize_embeddings: bool = True,
        opensearch_host: str = "http://10.36.0.110:9200"
    ) -> str:
        """
        Generate query pipeline YAML

        Args:
            index_name: OpenSearch index name
            embedder_model: HuggingFace model ID (must match indexing)
            top_k: Number of documents to retrieve
            normalize_embeddings: Whether to normalize embeddings
            opensearch_host: OpenSearch URL

        Returns:
            Generated YAML content as string
        """
        template = self.env.get_template("query.yaml.j2")

        context = {
            "index_name": index_name,
            "embedder_model": embedder_model,
            "top_k": top_k,
            "normalize_embeddings": normalize_embeddings,
            "opensearch_host": opensearch_host
        }

        yaml_content = template.render(**context)
        logger.info(f"Generated query pipeline for index {index_name}")
        return yaml_content

    def get_embedding_dimension(self, model_name: str) -> int:
        """
        Get embedding dimension for a model

        This is a lookup table for common models.
        In production, this could query the model or use a more comprehensive database.
        """
        dimension_map = {
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-small-en-v1.5": 384,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "intfloat/e5-large-v2": 1024,
            "intfloat/e5-base-v2": 768,
        }

        return dimension_map.get(model_name, 768)  # Default to 768 if unknown


# Singleton instance
pipeline_generator = PipelineGenerator()
