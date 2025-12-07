"""LLM providers for the Librarian.

Supported providers:
- gemini: Google Gemini (default)
- openai: OpenAI API
- anthropic: Anthropic Claude
- ollama: Local models via Ollama
- azure_openai: Azure OpenAI
- aws_bedrock: AWS Bedrock (Claude, Llama, Titan)
- huggingface: HuggingFace Inference API
- together: Together AI
- custom: Custom HTTP endpoint
"""

from libra.llm_providers.base import LLMProvider
from libra.llm_providers.factory import (
    create_llm_provider,
    get_supported_llm_providers,
)
from libra.llm_providers.gemini import GeminiLLMProvider

__all__ = [
    "LLMProvider",
    "GeminiLLMProvider",
    "create_llm_provider",
    "get_supported_llm_providers",
]


# Lazy imports for optional providers - only load when accessed
def __getattr__(name: str) -> type:
    """Lazy load optional LLM providers."""
    if name == "OpenAILLMProvider":
        from libra.llm_providers.openai import OpenAILLMProvider

        return OpenAILLMProvider
    elif name == "AnthropicLLMProvider":
        from libra.llm_providers.anthropic import AnthropicLLMProvider

        return AnthropicLLMProvider
    elif name == "OllamaLLMProvider":
        from libra.llm_providers.ollama import OllamaLLMProvider

        return OllamaLLMProvider
    elif name == "AzureOpenAILLMProvider":
        from libra.llm_providers.azure_openai import AzureOpenAILLMProvider

        return AzureOpenAILLMProvider
    elif name == "AWSBedrockLLMProvider":
        from libra.llm_providers.aws_bedrock import AWSBedrockLLMProvider

        return AWSBedrockLLMProvider
    elif name == "HuggingFaceLLMProvider":
        from libra.llm_providers.huggingface import HuggingFaceLLMProvider

        return HuggingFaceLLMProvider
    elif name == "TogetherLLMProvider":
        from libra.llm_providers.together import TogetherLLMProvider

        return TogetherLLMProvider
    elif name == "CustomLLMProvider":
        from libra.llm_providers.custom import CustomLLMProvider

        return CustomLLMProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
