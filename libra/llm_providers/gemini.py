"""Google Gemini LLM provider."""

import os
from typing import Any

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class GeminiLLMProvider(LLMProvider):
    """LLM provider using Google's Gemini API.

    Uses gemini-2.5-flash by default for fast, high-quality responses.
    Supports JSON mode for structured output.
    Requires GOOGLE_AI_API_KEY or GEMINI_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
    ):
        """Initialize the Gemini LLM provider.

        Args:
            model: The Gemini model to use
            api_key: Google AI API key (or use env var)
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise LibrarianError(
                "google-genai package not installed. Install with: pip install google-genai"
            )

        self._model = model

        # Get API key
        api_key = api_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LibrarianError(
                "GOOGLE_AI_API_KEY or GEMINI_API_KEY environment variable is required"
            )

        self._client = genai.Client(api_key=api_key)
        self._types = types

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
        """Generate a response from Gemini.

        Args:
            prompt: The prompt to send
            json_mode: If True, request JSON output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            config_kwargs: dict[str, Any] = {
                "temperature": temperature,
            }

            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"

            if max_tokens is not None:
                config_kwargs["max_output_tokens"] = max_tokens

            config = self._types.GenerateContentConfig(**config_kwargs)

            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )

            return response.text or ""

        except Exception as e:
            raise LibrarianError(f"Gemini generation failed: {e}")
