"""HuggingFace Inference API embedding provider."""

import os

import httpx

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using HuggingFace Inference API.

    Uses sentence-transformers/all-MiniLM-L6-v2 by default (384 dimensions).
    Requires HUGGINGFACE_API_KEY environment variable.
    """

    # Default dimensions for common HuggingFace embedding models
    MODEL_DIMENSIONS = {
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
        "sentence-transformers/paraphrase-MiniLM-L6-v2": 384,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
        "thenlper/gte-small": 384,
        "thenlper/gte-base": 768,
        "thenlper/gte-large": 1024,
    }

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: str | None = None,
        dimensions: int | None = None,
        timeout: float = 60.0,
    ):
        """Initialize the HuggingFace embedding provider.

        Args:
            model: The embedding model to use
            api_key: HuggingFace API key (or use HUGGINGFACE_API_KEY env var)
            dimensions: Output vector dimensions (model-specific defaults)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.timeout = timeout

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            self._dimensions = self.MODEL_DIMENSIONS.get(model, 384)

        # Get API key
        api_key = api_key or os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
        if not api_key:
            raise EmbeddingError(
                "HUGGINGFACE_API_KEY or HF_TOKEN environment variable is required"
            )

        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)
        self._base_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}"

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
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": texts,
                    "options": {"wait_for_model": True},
                },
            )
            response.raise_for_status()
            data = response.json()

            # HuggingFace returns embeddings directly as a list
            # Each embedding may be nested (e.g., for token-level embeddings)
            # We take the mean if needed
            embeddings = []
            for item in data:
                if isinstance(item[0], list):
                    # Token-level embeddings - compute mean
                    import statistics
                    num_dims = len(item[0])
                    mean_embedding = [
                        statistics.mean(token[i] for token in item)
                        for i in range(num_dims)
                    ]
                    embeddings.append(mean_embedding)
                else:
                    embeddings.append(list(item))

            return embeddings

        except httpx.HTTPStatusError as e:
            error_msg = e.response.text
            if "is currently loading" in error_msg:
                raise EmbeddingError(
                    f"Model {self.model} is loading. Please retry in a moment.", e
                )
            raise EmbeddingError(
                f"HuggingFace API error: {e.response.status_code} - {error_msg}", e
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}", e)

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
