"""Together AI LLM provider."""

import os
from typing import Any

import httpx

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class TogetherLLMProvider(LLMProvider):
    """LLM provider using Together AI.

    Uses meta-llama/Llama-3.2-3B-Instruct-Turbo by default.
    Requires TOGETHER_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "meta-llama/Llama-3.2-3B-Instruct-Turbo",
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        """Initialize the Together AI LLM provider.

        Args:
            model: The Together AI model to use
            api_key: Together API key (or use env var)
            timeout: Request timeout in seconds
        """
        self._model = model
        self.timeout = timeout

        # Get API key
        api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not api_key:
            raise LibrarianError(
                "TOGETHER_API_KEY environment variable is required"
            )

        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)
        self._base_url = "https://api.together.xyz/v1"

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
        """Generate a response from Together AI.

        Args:
            prompt: The prompt to send
            json_mode: If True, request JSON output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            payload: dict[str, Any] = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            }

            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # OpenAI-compatible response format
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
            return ""

        except httpx.HTTPStatusError as e:
            raise LibrarianError(
                f"Together API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise LibrarianError(f"Together generation failed: {e}")

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
