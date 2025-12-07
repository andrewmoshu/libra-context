"""Azure OpenAI LLM provider."""

import os
from typing import Any

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class AzureOpenAILLMProvider(LLMProvider):
    """LLM provider using Azure OpenAI.

    Requires Azure OpenAI deployment and credentials.
    """

    def __init__(
        self,
        deployment: str,
        azure_endpoint: str | None = None,
        api_key: str | None = None,
        api_version: str = "2024-02-01",
    ):
        """Initialize the Azure OpenAI LLM provider.

        Args:
            deployment: Azure deployment name for the model
            azure_endpoint: Azure OpenAI endpoint (or use AZURE_OPENAI_ENDPOINT env var)
            api_key: Azure API key (or use AZURE_OPENAI_API_KEY env var)
            api_version: API version to use
        """
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise LibrarianError(
                "openai package not installed. Install with: pip install openai"
            )

        self._deployment = deployment

        # Get endpoint and API key
        azure_endpoint = azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not azure_endpoint:
            raise LibrarianError(
                "AZURE_OPENAI_ENDPOINT environment variable is required"
            )

        api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise LibrarianError(
                "AZURE_OPENAI_API_KEY environment variable is required"
            )

        self._client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    @property
    def model_name(self) -> str:
        """Return the deployment name."""
        return self._deployment

    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from Azure OpenAI.

        Args:
            prompt: The prompt to send
            json_mode: If True, request JSON output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            kwargs: dict[str, Any] = {
                "model": self._deployment,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            response = self._client.chat.completions.create(**kwargs)

            return response.choices[0].message.content or ""

        except Exception as e:
            raise LibrarianError(f"Azure OpenAI generation failed: {e}")
