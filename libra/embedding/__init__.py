"""Embedding providers for libra."""

from libra.embedding.base import EmbeddingProvider
from libra.embedding.gemini import GeminiEmbeddingProvider

__all__ = ["EmbeddingProvider", "GeminiEmbeddingProvider"]
