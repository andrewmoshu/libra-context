"""Base class for LLM providers used by the Librarian."""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    LLM providers are used by the Librarian for intelligent context selection.
    They should support structured JSON output for reliable parsing.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            json_mode: If True, request JSON output from the model
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens to generate (None = model default)

        Returns:
            The generated text response
        """
        pass

    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate a JSON response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON response as a dictionary

        Raises:
            ValueError: If the response is not valid JSON
        """
        import json

        response = self.generate(
            prompt,
            json_mode=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            # Try to extract JSON from the response
            # Some models wrap JSON in markdown code blocks
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response}")
