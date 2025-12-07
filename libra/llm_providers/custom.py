"""Custom HTTP endpoint LLM provider."""

import os
from typing import Any, cast

import httpx

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class CustomLLMProvider(LLMProvider):
    """LLM provider using a custom HTTP endpoint.

    Supports OpenAI-compatible API format by default.
    Can be configured for different API formats.
    """

    def __init__(
        self,
        base_url: str,
        model: str = "default",
        api_key: str | None = None,
        timeout: float = 120.0,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        request_format: str = "openai",  # "openai" or "simple"
    ):
        """Initialize the custom endpoint LLM provider.

        Args:
            base_url: Base URL of the LLM API
            model: Model name to send in requests
            api_key: API key for authentication (optional)
            timeout: Request timeout in seconds
            auth_header: Header name for authentication
            auth_prefix: Prefix for the auth token (e.g., "Bearer")
            request_format: API format ("openai" or "simple")
        """
        self._model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.request_format = request_format

        # Get API key if provided
        self._api_key = api_key or os.environ.get("CUSTOM_LLM_API_KEY")

        self._client = httpx.Client(timeout=timeout)

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers[self.auth_header] = f"{self.auth_prefix} {self._api_key}".strip()
        return headers

    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from the custom endpoint.

        Args:
            prompt: The prompt to send
            json_mode: If True, request JSON output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            headers = self._build_headers()

            if self.request_format == "openai":
                # OpenAI-compatible format
                url = f"{self.base_url}/chat/completions"
                payload: dict[str, Any] = {
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }

                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens

            else:
                # Simple format - just send prompt
                url = self.base_url
                payload = {
                    "prompt": prompt,
                    "model": self._model,
                    "temperature": temperature,
                }

                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens

            response = self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse response based on format
            if self.request_format == "openai":
                # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return cast(str, message.get("content", ""))
                return ""
            else:
                # Simple format: {"response": "..."} or {"text": "..."}
                result = data.get("response") or data.get("text")
                return str(result) if result is not None else str(data)

        except httpx.HTTPStatusError as e:
            raise LibrarianError(
                f"Custom API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise LibrarianError(f"Custom LLM generation failed: {e}")

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
