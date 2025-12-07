"""HuggingFace Inference API LLM provider."""

import os
from typing import Any, cast

import httpx

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class HuggingFaceLLMProvider(LLMProvider):
    """LLM provider using HuggingFace Inference API.

    Uses meta-llama/Llama-3.2-3B-Instruct by default.
    Requires HUGGINGFACE_API_KEY or HF_TOKEN environment variable.
    """

    def __init__(
        self,
        model: str = "meta-llama/Llama-3.2-3B-Instruct",
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        """Initialize the HuggingFace LLM provider.

        Args:
            model: The HuggingFace model to use
            api_key: HuggingFace API key (or use env var)
            timeout: Request timeout in seconds
        """
        self._model = model
        self.timeout = timeout

        # Get API key
        api_key = api_key or os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
        if not api_key:
            raise LibrarianError(
                "HUGGINGFACE_API_KEY or HF_TOKEN environment variable is required"
            )

        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)
        self._base_url = f"https://api-inference.huggingface.co/models/{model}"

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
        """Generate a response from HuggingFace.

        Args:
            prompt: The prompt to send
            json_mode: If True, instruct the model to output JSON
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            if json_mode:
                prompt = f"{prompt}\n\nRespond with valid JSON only. No additional text."

            parameters: dict[str, Any] = {
                "temperature": temperature,
                "return_full_text": False,
            }
            if max_tokens is not None:
                parameters["max_new_tokens"] = max_tokens

            payload: dict[str, Any] = {
                "inputs": prompt,
                "parameters": parameters,
                "options": {"wait_for_model": True},
            }

            response = self._client.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # HuggingFace returns a list of generated texts
            if isinstance(data, list) and data:
                return cast(str, data[0].get("generated_text", ""))
            return str(data)

        except httpx.HTTPStatusError as e:
            error_msg = e.response.text
            if "is currently loading" in error_msg:
                raise LibrarianError(
                    f"Model {self._model} is loading. Please retry in a moment."
                )
            raise LibrarianError(
                f"HuggingFace API error: {e.response.status_code} - {error_msg}"
            )
        except Exception as e:
            raise LibrarianError(f"HuggingFace generation failed: {e}")

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
