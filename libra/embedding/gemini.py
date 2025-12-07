"""Gemini embedding provider using Google's GenAI SDK."""

import os
from typing import Literal

from google import genai
from google.genai import types

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider

TaskType = Literal[
    "RETRIEVAL_QUERY",
    "RETRIEVAL_DOCUMENT",
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
    "CLUSTERING",
]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Google's Gemini API.

    Uses gemini-embedding-001 model by default (768 dimensions).
    The Gemini Embedding model supports up to 3072 dimensions but
    we default to 768 for backward compatibility with sqlite-vec storage.
    Requires GOOGLE_AI_API_KEY or GEMINI_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "gemini-embedding-001",
        api_key: str | None = None,
        output_dimensionality: int = 768,
    ):
        """Initialize the Gemini embedding provider.

        Args:
            model: The embedding model to use
            api_key: Google AI API key (or use GOOGLE_AI_API_KEY/GEMINI_API_KEY env var)
            output_dimensionality: Output vector dimensions (max 3072 for gemini-embedding-001)
        """
        self.model = model
        self._dimensions = output_dimensionality

        # Get API key from parameter or environment
        api_key = api_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EmbeddingError(
                "GOOGLE_AI_API_KEY or GEMINI_API_KEY environment variable is required for Gemini embeddings"
            )

        # Initialize the client
        self._client = genai.Client(api_key=api_key)

    @property
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._dimensions

    def embed(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_DOCUMENT",
    ) -> list[float]:
        """Generate an embedding for a single text.

        Args:
            text: The text to embed
            task_type: The task type for embedding optimization

        Returns:
            A list of floats representing the embedding vector
        """
        try:
            result = self._client.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self._dimensions,
                ),
            )
            return list(result.embeddings[0].values)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}", e)

    def embed_batch(
        self,
        texts: list[str],
        task_type: TaskType = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            task_type: The task type for embedding optimization

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            result = self._client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self._dimensions,
                ),
            )
            return [list(emb.values) for emb in result.embeddings]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}", e)

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a query.

        Uses RETRIEVAL_QUERY task type for better query matching.

        Args:
            query: The query text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        return self.embed(query, task_type="RETRIEVAL_QUERY")

    def embed_document(self, document: str) -> list[float]:
        """Generate an embedding for a document.

        Uses RETRIEVAL_DOCUMENT task type for better document indexing.

        Args:
            document: The document text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        return self.embed(document, task_type="RETRIEVAL_DOCUMENT")
