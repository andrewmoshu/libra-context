"""OpenAI embedding provider."""

import os
from typing import Any

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI's API.

    Uses text-embedding-3-small by default (1536 dimensions).
    Can also use text-embedding-3-large (3072 dimensions).
    Requires OPENAI_API_KEY environment variable.
    """

    # Default dimensions for each model
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,  # Legacy
    }

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        dimensions: int | None = None,
        base_url: str | None = None,
    ):
        """Initialize the OpenAI embedding provider.

        Args:
            model: The embedding model to use
            api_key: OpenAI API key (or use OPENAI_API_KEY env var)
            dimensions: Output vector dimensions (model-specific defaults)
            base_url: Optional base URL for API (for proxies/compatible APIs)
        """
        try:
            import openai
        except ImportError:
            raise EmbeddingError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        self.model = model

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            self._dimensions = self.MODEL_DIMENSIONS.get(model, 1536)

        # Get API key
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EmbeddingError(
                "OPENAI_API_KEY environment variable is required for OpenAI embeddings"
            )

        # Initialize client
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = openai.OpenAI(**client_kwargs)

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
                model=self.model,
                input=text,
                dimensions=self._dimensions,
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
                model=self.model,
                input=texts,
                dimensions=self._dimensions,
            )
            # Sort by index to ensure correct order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [list(item.embedding) for item in sorted_data]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}", e)
