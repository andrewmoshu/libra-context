"""Ollama embedding provider for local models."""

import httpx

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Ollama for local models.

    Uses nomic-embed-text by default (768 dimensions).
    Can also use mxbai-embed-large (1024 dimensions) or other models.
    Requires Ollama to be running locally.
    """

    # Default dimensions for common Ollama embedding models
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "snowflake-arctic-embed": 1024,
    }

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimensions: int | None = None,
        timeout: float = 60.0,
    ):
        """Initialize the Ollama embedding provider.

        Args:
            model: The embedding model to use
            base_url: Ollama server URL
            dimensions: Output vector dimensions (model-specific defaults)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            self._dimensions = self.MODEL_DIMENSIONS.get(model, 768)

        self._client = httpx.Client(timeout=timeout)

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
            response = self._client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])
            if not embedding:
                raise EmbeddingError("No embedding returned from Ollama")
            return list(embedding)
        except httpx.HTTPStatusError as e:
            raise EmbeddingError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}", e
            )
        except httpx.ConnectError as e:
            raise EmbeddingError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running.", e
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}", e)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Ollama doesn't support batch embedding, so we process sequentially.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        for text in texts:
            embedding = self.embed(text)
            embeddings.append(embedding)
        return embeddings

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
