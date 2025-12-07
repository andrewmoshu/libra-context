"""Local embedding provider using sentence-transformers."""

from typing import cast

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers for local embeddings.

    Uses all-MiniLM-L6-v2 by default (384 dimensions).
    Can also use all-mpnet-base-v2 (768 dimensions) or other models.
    Requires sentence-transformers package to be installed.
    """

    # Default dimensions for common sentence-transformers models
    MODEL_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-MiniLM-L6-v2": 384,
        "multi-qa-MiniLM-L6-cos-v1": 384,
        "msmarco-distilbert-base-v4": 768,
    }

    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        device: str | None = None,
        dimensions: int | None = None,
    ):
        """Initialize the local embedding provider.

        Args:
            model: The sentence-transformers model to use
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto)
            dimensions: Output vector dimensions (model-specific defaults)
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise EmbeddingError(
                "sentence-transformers package not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            self._dimensions = self.MODEL_DIMENSIONS.get(model, 384)

        # Initialize model
        try:
            self._model = SentenceTransformer(model, device=device)
            # Update dimensions from loaded model if available
            if hasattr(self._model, "get_sentence_embedding_dimension"):
                self._dimensions = self._model.get_sentence_embedding_dimension()
        except Exception as e:
            raise EmbeddingError(f"Failed to load model {model}: {e}", e)

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
            embedding = self._model.encode(text, convert_to_numpy=True)
            return cast(list[float], embedding.tolist())
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
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}", e)

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a query.

        Uses the model's query encoding if available.

        Args:
            query: The query text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        try:
            # Some models have special query encoding
            if hasattr(self._model, "encode_queries"):
                embedding = self._model.encode_queries([query], convert_to_numpy=True)
                return cast(list[float], embedding[0].tolist())
            return self.embed(query)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate query embedding: {e}", e)

    def embed_document(self, document: str) -> list[float]:
        """Generate an embedding for a document.

        Uses the model's document encoding if available.

        Args:
            document: The document text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        try:
            # Some models have special document encoding
            if hasattr(self._model, "encode_corpus"):
                embedding = self._model.encode_corpus([document], convert_to_numpy=True)
                return cast(list[float], embedding[0].tolist())
            return self.embed(document)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate document embedding: {e}", e)
