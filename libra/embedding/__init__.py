"""Embedding providers for libra.

Supported providers:
- gemini: Google Gemini (default)
- openai: OpenAI API
- ollama: Local models via Ollama
- local: sentence-transformers (fully offline)
- azure_openai: Azure OpenAI
- aws_bedrock: AWS Bedrock (Titan, Cohere)
- huggingface: HuggingFace Inference API
- together: Together AI
- custom: Custom HTTP endpoint
"""

from libra.embedding.base import EmbeddingProvider
from libra.embedding.factory import (
    create_embedding_provider,
    get_supported_embedding_providers,
)
from libra.embedding.gemini import GeminiEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "create_embedding_provider",
    "get_supported_embedding_providers",
]


# Lazy imports for optional providers - only load when accessed
def __getattr__(name: str) -> type:
    """Lazy load optional embedding providers."""
    if name == "OpenAIEmbeddingProvider":
        from libra.embedding.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider
    elif name == "OllamaEmbeddingProvider":
        from libra.embedding.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider
    elif name == "LocalEmbeddingProvider":
        from libra.embedding.local import LocalEmbeddingProvider

        return LocalEmbeddingProvider
    elif name == "AzureOpenAIEmbeddingProvider":
        from libra.embedding.azure_openai import AzureOpenAIEmbeddingProvider

        return AzureOpenAIEmbeddingProvider
    elif name == "AWSBedrockEmbeddingProvider":
        from libra.embedding.aws_bedrock import AWSBedrockEmbeddingProvider

        return AWSBedrockEmbeddingProvider
    elif name == "HuggingFaceEmbeddingProvider":
        from libra.embedding.huggingface import HuggingFaceEmbeddingProvider

        return HuggingFaceEmbeddingProvider
    elif name == "TogetherEmbeddingProvider":
        from libra.embedding.together import TogetherEmbeddingProvider

        return TogetherEmbeddingProvider
    elif name == "CustomEmbeddingProvider":
        from libra.embedding.custom import CustomEmbeddingProvider

        return CustomEmbeddingProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
