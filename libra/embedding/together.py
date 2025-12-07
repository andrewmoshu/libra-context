"""Together API embedding provider."""

import os
from typing import Any

import httpx

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class TogetherEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Together API.

    Uses togethercomputer/m2-bert-80M-8k-retrieval by default (768 dimensions).
    Requires TOGETHER_API_KEY environment variable.
    """

    # Default dimensions for common Together embedding models
    MODEL_DIMENSIONS = {
        "togethercomputer/m2-bert-80M-8k-retrieval": 768,
        "togethercomputer/m2-bert-80M-32k-retrieval": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "BAAI/bge-base-en-v1.5": 768,
        "sentence-transformers/msmarco-bert-base-dot-v5": 768,
    }

    def __init__(
        self,
        model: str = "togethercomputer/m2-bert-80M-8k-retrieval",
        api_key: str | None = None,
        dimensions: int | None = None,
        timeout: float = 60.0,
    ):
        """Initialize the Together embedding provider.

        Args:
            model: The embedding model to use
            api_key: Together API key (or use TOGETHER_API_KEY env var)
            dimensions: Output vector dimensions (model-specific defaults)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.timeout = timeout

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            self._dimensions = self.MODEL_DIMENSIONS.get(model, 768)

        # Get API key
        api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            raise EmbeddingError(
                "TOGETHER_API_KEY environment variable is required"
            )

        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)
        self._base_url = "https://api.together.xyz/v1"

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
        return self.embed_batch([text])[0]

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
            response = self._client.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Sort by index to ensure correct order
            embeddings_data = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            return [item.get("embedding", []) for item in embeddings_data]

        except httpx.HTTPStatusError as e:
            raise EmbeddingError(
                f"Together API error: {e.response.status_code} - {e.response.text}", e
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}", e)

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
