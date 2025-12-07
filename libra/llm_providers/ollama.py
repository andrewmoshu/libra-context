"""Ollama LLM provider for local models."""

import httpx

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class OllamaLLMProvider(LLMProvider):
    """LLM provider using Ollama for local models.

    Uses llama3.2 by default.
    Requires Ollama to be running locally.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        """Initialize the Ollama LLM provider.

        Args:
            model: The Ollama model to use
            base_url: Ollama server URL
            timeout: Request timeout in seconds
        """
        self._model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

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
        """Generate a response from Ollama.

        Args:
            prompt: The prompt to send
            json_mode: If True, request JSON output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            if json_mode:
                payload["format"] = "json"

            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens

            response = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            return data.get("response", "")

        except httpx.ConnectError as e:
            raise LibrarianError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running.", e
            )
        except httpx.HTTPStatusError as e:
            raise LibrarianError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}", e
            )
        except Exception as e:
            raise LibrarianError(f"Ollama generation failed: {e}")

    def __del__(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
