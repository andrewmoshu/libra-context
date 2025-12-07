"""Custom HTTP endpoint embedding provider."""

import os
from typing import Any

import httpx

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class CustomEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using a custom HTTP endpoint.

    Supports OpenAI-compatible API format by default.
    Can be configured for different API formats.
    """

    def __init__(
        self,
        base_url: str,
        model: str = "embedding-model",
        api_key: str | None = None,
        dimensions: int = 768,
        timeout: float = 60.0,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        request_format: str = "openai",  # "openai" or "simple"
    ):
        """Initialize the custom endpoint embedding provider.

        Args:
            base_url: Base URL of the embedding API
            model: Model name to send in requests
            api_key: API key for authentication (optional)
            dimensions: Output vector dimensions
            timeout: Request timeout in seconds
            auth_header: Header name for authentication
            auth_prefix: Prefix for the auth token (e.g., "Bearer")
            request_format: API format ("openai" or "simple")
        """
        self.model = model
        self._dimensions = dimensions
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.request_format = request_format

        # Get API key if provided
        self._api_key = api_key or os.environ.get("CUSTOM_EMBEDDING_API_KEY")

        self._client = httpx.Client(timeout=timeout)

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._dimensions

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers[self.auth_header] = f"{self.auth_prefix} {self._api_key}".strip()
        return headers

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
            headers = self._build_headers()

            if self.request_format == "openai":
                # OpenAI-compatible format
                url = f"{self.base_url}/embeddings"
                payload: dict[str, Any] = {
                    "model": self.model,
                    "input": texts,
                }
            else:
                # Simple format - just send texts
                url = self.base_url
                payload = {"texts": texts, "model": self.model}

            response = self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse response based on format
            if self.request_format == "openai":
                # OpenAI format: {"data": [{"embedding": [...], "index": 0}, ...]}
                embeddings_data = data.get("data", [])
                sorted_data = sorted(embeddings_data, key=lambda x: x.get("index", 0))
                return [item.get("embedding", []) for item in sorted_data]
            else:
                # Simple format: {"embeddings": [[...], ...]}
                return data.get("embeddings", [])

        except httpx.HTTPStatusError as e:
            raise EmbeddingError(
                f"API error: {e.response.status_code} - {e.response.text}", e
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}", e)

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
