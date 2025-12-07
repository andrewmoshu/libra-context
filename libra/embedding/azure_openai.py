"""Azure OpenAI embedding provider."""

import os
from typing import Any

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Azure OpenAI.

    Requires Azure OpenAI deployment with an embedding model.
    Uses text-embedding-3-small by default (1536 dimensions).
    """

    # Default dimensions for each model
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        deployment: str,
        azure_endpoint: str | None = None,
        api_key: str | None = None,
        api_version: str = "2024-02-01",
        dimensions: int | None = None,
    ):
        """Initialize the Azure OpenAI embedding provider.

        Args:
            deployment: Azure deployment name for the embedding model
            azure_endpoint: Azure OpenAI endpoint (or use AZURE_OPENAI_ENDPOINT env var)
            api_key: Azure API key (or use AZURE_OPENAI_API_KEY env var)
            api_version: API version to use
            dimensions: Output vector dimensions (model-specific defaults)
        """
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise EmbeddingError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        self.deployment = deployment

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            # Try to infer from deployment name
            for model, dims in self.MODEL_DIMENSIONS.items():
                if model in deployment.lower():
                    self._dimensions = dims
                    break
            else:
                self._dimensions = 1536  # Default

        # Get endpoint and API key
        azure_endpoint = azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not azure_endpoint:
            raise EmbeddingError(
                "AZURE_OPENAI_ENDPOINT environment variable is required"
            )

        api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise EmbeddingError(
                "AZURE_OPENAI_API_KEY environment variable is required"
            )

        # Initialize client
        self._client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        try:
            response = self._client.embeddings.create(
                model=self.deployment,
                input=text,
            )
            return list(response.data[0].embedding)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}", e)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            response = self._client.embeddings.create(
                model=self.deployment,
                input=texts,
            )
            # Sort by index to ensure correct order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [list(item.embedding) for item in sorted_data]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}", e)
