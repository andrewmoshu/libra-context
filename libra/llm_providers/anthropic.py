"""Anthropic Claude LLM provider."""

import os
from typing import Any

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class AnthropicLLMProvider(LLMProvider):
    """LLM provider using Anthropic's Claude API.

    Uses claude-3-5-haiku-latest by default for fast responses.
    Requires ANTHROPIC_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "claude-3-5-haiku-latest",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize the Anthropic LLM provider.

        Args:
            model: The Claude model to use
            api_key: Anthropic API key (or use env var)
            base_url: Optional base URL for API
        """
        try:
            import anthropic
        except ImportError:
            raise LibrarianError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        self._model = model

        # Get API key
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LibrarianError(
                "ANTHROPIC_API_KEY environment variable is required"
            )

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = anthropic.Anthropic(**client_kwargs)

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
        """Generate a response from Claude.

        Args:
            prompt: The prompt to send
            json_mode: If True, instruct the model to output JSON
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            The generated text response
        """
        try:
            # Claude doesn't have a native JSON mode, but we can instruct it
            if json_mode:
                prompt = f"{prompt}\n\nRespond with valid JSON only. No additional text."

            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from content blocks
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)

            return "".join(text_parts)

        except Exception as e:
            raise LibrarianError(f"Anthropic generation failed: {e}")
