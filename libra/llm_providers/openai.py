"""OpenAI LLM provider."""

import os
from typing import Any

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    """LLM provider using OpenAI's API.

    Uses gpt-4o-mini by default for fast, cost-effective responses.
    Supports JSON mode for structured output.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize the OpenAI LLM provider.

        Args:
            model: The OpenAI model to use
            api_key: OpenAI API key (or use env var)
            base_url: Optional base URL for API (for proxies/compatible APIs)
        """
        try:
            import openai
        except ImportError:
            raise LibrarianError(
                "openai package not installed. Install with: pip install openai"
            )

        self._model = model

        # Get API key
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LibrarianError(
                "OPENAI_API_KEY environment variable is required"
            )

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = openai.OpenAI(**client_kwargs)

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model

    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from OpenAI.

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
                "model": self._model,
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
            raise LibrarianError(f"OpenAI generation failed: {e}")
