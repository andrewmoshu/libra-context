"""Base class for embedding providers."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings produced by this provider."""
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a query.

        By default, this is the same as embed(), but some providers
        may use different models/settings for queries vs documents.

        Args:
            query: The query text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        return self.embed(query)

    def embed_document(self, document: str) -> list[float]:
        """Generate an embedding for a document.

        By default, this is the same as embed(), but some providers
        may use different models/settings for document indexing.

        Args:
            document: The document text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        return self.embed(document)
