"""Factory functions for creating LLM providers."""

from typing import Any

from libra.core.config import LLMConfig
from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """Create an LLM provider based on configuration.

    Args:
        config: LLM configuration

    Returns:
        An initialized LLMProvider instance

    Raises:
        LibrarianError: If the provider is not supported or cannot be initialized
    """
    provider = config.provider.lower()

    if provider == "gemini":
        from libra.llm_providers.gemini import GeminiLLMProvider

        return GeminiLLMProvider(
            model=config.model,
            api_key=config.api_key,
        )

    elif provider == "openai":
        from libra.llm_providers.openai import OpenAILLMProvider

        return OpenAILLMProvider(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    elif provider == "anthropic":
        from libra.llm_providers.anthropic import AnthropicLLMProvider

        return AnthropicLLMProvider(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    elif provider == "ollama":
        from libra.llm_providers.ollama import OllamaLLMProvider

        return OllamaLLMProvider(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
        )

    elif provider == "azure_openai":
        from libra.llm_providers.azure_openai import AzureOpenAILLMProvider

        if not config.azure_deployment:
            raise LibrarianError(
                "azure_deployment is required for Azure OpenAI LLM provider"
            )

        return AzureOpenAILLMProvider(
            deployment=config.azure_deployment,
            azure_endpoint=config.azure_endpoint,
            api_key=config.api_key,
            api_version=config.api_version or "2024-02-01",
        )

    elif provider == "aws_bedrock":
        from libra.llm_providers.aws_bedrock import AWSBedrockLLMProvider

        return AWSBedrockLLMProvider(
            model=config.model,
            region=config.aws_region,
            profile=config.aws_profile,
        )

    elif provider == "huggingface":
        from libra.llm_providers.huggingface import HuggingFaceLLMProvider

        return HuggingFaceLLMProvider(
            model=config.model,
            api_key=config.api_key,
        )

    elif provider == "together":
        from libra.llm_providers.together import TogetherLLMProvider

        return TogetherLLMProvider(
            model=config.model,
            api_key=config.api_key,
        )

    elif provider == "custom":
        from libra.llm_providers.custom import CustomLLMProvider

        if not config.base_url:
            raise LibrarianError(
                "base_url is required for custom LLM provider"
            )

        return CustomLLMProvider(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
        )

    else:
        raise LibrarianError(
            f"Unknown LLM provider: {provider}. "
            f"Supported providers: gemini, openai, anthropic, ollama, azure_openai, "
            f"aws_bedrock, huggingface, together, custom"
        )


def get_supported_llm_providers() -> list[dict[str, Any]]:
    """Get list of supported LLM providers with their details.

    Returns:
        List of provider info dictionaries
    """
    return [
        {
            "name": "gemini",
            "display_name": "Google Gemini",
            "description": "Google's Gemini models (gemini-2.5-flash)",
            "env_vars": ["GOOGLE_AI_API_KEY", "GEMINI_API_KEY"],
            "default_model": "gemini-2.5-flash",
        },
        {
            "name": "openai",
            "display_name": "OpenAI",
            "description": "OpenAI GPT models (gpt-4o-mini, gpt-4o)",
            "env_vars": ["OPENAI_API_KEY"],
            "default_model": "gpt-4o-mini",
        },
        {
            "name": "anthropic",
            "display_name": "Anthropic Claude",
            "description": "Anthropic Claude models (claude-3-5-haiku, claude-3-5-sonnet)",
            "env_vars": ["ANTHROPIC_API_KEY"],
            "default_model": "claude-3-5-haiku-latest",
        },
        {
            "name": "ollama",
            "display_name": "Ollama",
            "description": "Local models via Ollama (llama3.2, mistral, etc.)",
            "env_vars": [],
            "default_model": "llama3.2",
            "requires": "Ollama running locally",
        },
        {
            "name": "azure_openai",
            "display_name": "Azure OpenAI",
            "description": "Azure-hosted OpenAI models",
            "env_vars": ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"],
            "default_model": "gpt-4o-mini",
        },
        {
            "name": "aws_bedrock",
            "display_name": "AWS Bedrock",
            "description": "AWS Bedrock models (Claude, Llama, Titan)",
            "env_vars": [],
            "default_model": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "requires": "AWS credentials configured",
        },
        {
            "name": "huggingface",
            "display_name": "HuggingFace",
            "description": "HuggingFace Inference API",
            "env_vars": ["HUGGINGFACE_API_KEY", "HF_TOKEN"],
            "default_model": "meta-llama/Llama-3.2-3B-Instruct",
        },
        {
            "name": "together",
            "display_name": "Together AI",
            "description": "Together AI inference API",
            "env_vars": ["TOGETHER_API_KEY"],
            "default_model": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
        },
        {
            "name": "custom",
            "display_name": "Custom Endpoint",
            "description": "Custom HTTP endpoint (OpenAI-compatible)",
            "env_vars": ["CUSTOM_LLM_API_KEY"],
            "default_model": "default",
            "requires": "base_url configuration",
        },
    ]
