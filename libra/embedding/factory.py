"""Factory functions for creating embedding providers."""

from typing import Any

from libra.core.config import EmbeddingConfig
from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


def create_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """Create an embedding provider based on configuration.

    Args:
        config: Embedding configuration

    Returns:
        An initialized EmbeddingProvider instance

    Raises:
        EmbeddingError: If the provider is not supported or cannot be initialized
    """
    provider = config.provider.lower()

    if provider == "gemini":
        from libra.embedding.gemini import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(
            model=config.model,
            api_key=config.api_key,
            output_dimensionality=config.dimensions,
        )

    elif provider == "openai":
        from libra.embedding.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            model=config.model,
            api_key=config.api_key,
            dimensions=config.dimensions,
            base_url=config.base_url,
        )

    elif provider == "ollama":
        from libra.embedding.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
            dimensions=config.dimensions,
        )

    elif provider == "local":
        from libra.embedding.local import LocalEmbeddingProvider

        return LocalEmbeddingProvider(
            model=config.model,
            dimensions=config.dimensions,
        )

    elif provider == "azure_openai":
        from libra.embedding.azure_openai import AzureOpenAIEmbeddingProvider

        if not config.azure_deployment:
            raise EmbeddingError(
                "azure_deployment is required for Azure OpenAI embedding provider"
            )

        return AzureOpenAIEmbeddingProvider(
            deployment=config.azure_deployment,
            azure_endpoint=config.azure_endpoint,
            api_key=config.api_key,
            api_version=config.api_version or "2024-02-01",
            dimensions=config.dimensions,
        )

    elif provider == "aws_bedrock":
        from libra.embedding.aws_bedrock import AWSBedrockEmbeddingProvider

        return AWSBedrockEmbeddingProvider(
            model=config.model,
            region=config.aws_region,
            profile=config.aws_profile,
            dimensions=config.dimensions,
        )

    elif provider == "huggingface":
        from libra.embedding.huggingface import HuggingFaceEmbeddingProvider

        return HuggingFaceEmbeddingProvider(
            model=config.model,
            api_key=config.api_key,
            dimensions=config.dimensions,
        )

    elif provider == "together":
        from libra.embedding.together import TogetherEmbeddingProvider

        return TogetherEmbeddingProvider(
            model=config.model,
            api_key=config.api_key,
            dimensions=config.dimensions,
        )

    elif provider == "custom":
        from libra.embedding.custom import CustomEmbeddingProvider

        if not config.base_url:
            raise EmbeddingError(
                "base_url is required for custom embedding provider"
            )

        return CustomEmbeddingProvider(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            dimensions=config.dimensions,
        )

    else:
        raise EmbeddingError(
            f"Unknown embedding provider: {provider}. "
            f"Supported providers: gemini, openai, ollama, local, azure_openai, "
            f"aws_bedrock, huggingface, together, custom"
        )


def get_supported_embedding_providers() -> list[dict[str, Any]]:
    """Get list of supported embedding providers with their details.

    Returns:
        List of provider info dictionaries
    """
    return [
        {
            "name": "gemini",
            "display_name": "Google Gemini",
            "description": "Google's Gemini embedding models (gemini-embedding-001)",
            "env_vars": ["GOOGLE_AI_API_KEY", "GEMINI_API_KEY"],
            "default_model": "gemini-embedding-001",
            "default_dimensions": 768,
        },
        {
            "name": "openai",
            "display_name": "OpenAI",
            "description": "OpenAI embedding models (text-embedding-3-small/large)",
            "env_vars": ["OPENAI_API_KEY"],
            "default_model": "text-embedding-3-small",
            "default_dimensions": 1536,
        },
        {
            "name": "ollama",
            "display_name": "Ollama",
            "description": "Local embedding models via Ollama",
            "env_vars": [],
            "default_model": "nomic-embed-text",
            "default_dimensions": 768,
            "requires": "Ollama running locally",
        },
        {
            "name": "local",
            "display_name": "Local (sentence-transformers)",
            "description": "Fully local embeddings using sentence-transformers",
            "env_vars": [],
            "default_model": "all-MiniLM-L6-v2",
            "default_dimensions": 384,
            "requires": "sentence-transformers package",
        },
        {
            "name": "azure_openai",
            "display_name": "Azure OpenAI",
            "description": "Azure-hosted OpenAI embedding models",
            "env_vars": ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"],
            "default_model": "text-embedding-3-small",
            "default_dimensions": 1536,
        },
        {
            "name": "aws_bedrock",
            "display_name": "AWS Bedrock",
            "description": "AWS Bedrock embedding models (Titan, Cohere)",
            "env_vars": [],
            "default_model": "amazon.titan-embed-text-v2:0",
            "default_dimensions": 1024,
            "requires": "AWS credentials configured",
        },
        {
            "name": "huggingface",
            "display_name": "HuggingFace",
            "description": "HuggingFace Inference API embeddings",
            "env_vars": ["HUGGINGFACE_API_KEY", "HF_TOKEN"],
            "default_model": "sentence-transformers/all-MiniLM-L6-v2",
            "default_dimensions": 384,
        },
        {
            "name": "together",
            "display_name": "Together AI",
            "description": "Together AI embedding models",
            "env_vars": ["TOGETHER_API_KEY"],
            "default_model": "togethercomputer/m2-bert-80M-8k-retrieval",
            "default_dimensions": 768,
        },
        {
            "name": "custom",
            "display_name": "Custom Endpoint",
            "description": "Custom HTTP endpoint (OpenAI-compatible)",
            "env_vars": ["CUSTOM_EMBEDDING_API_KEY"],
            "default_model": "embedding-model",
            "default_dimensions": 768,
            "requires": "base_url configuration",
        },
    ]
