"""AWS Bedrock LLM provider."""

import json
import os
from typing import Any

from libra.core.exceptions import LibrarianError
from libra.llm_providers.base import LLMProvider


class AWSBedrockLLMProvider(LLMProvider):
    """LLM provider using AWS Bedrock.

    Supports Claude, Llama, and other Bedrock models.
    Uses anthropic.claude-3-5-haiku-20241022-v1:0 by default.
    Requires AWS credentials configured.
    """

    # Model configurations for different providers
    MODEL_CONFIGS = {
        "anthropic": {
            "prompt_key": "messages",
            "format": "anthropic",
        },
        "amazon": {
            "prompt_key": "inputText",
            "format": "titan",
        },
        "meta": {
            "prompt_key": "prompt",
            "format": "llama",
        },
        "mistral": {
            "prompt_key": "prompt",
            "format": "mistral",
        },
    }

    def __init__(
        self,
        model: str = "anthropic.claude-3-5-haiku-20241022-v1:0",
        region: str | None = None,
        profile: str | None = None,
    ):
        """Initialize the AWS Bedrock LLM provider.

        Args:
            model: The Bedrock model ID to use
            region: AWS region (or use AWS_DEFAULT_REGION env var)
            profile: AWS profile name (optional)
        """
        try:
            import boto3
        except ImportError:
            raise LibrarianError(
                "boto3 package not installed. Install with: pip install boto3"
            )

        self._model = model

        # Determine model provider
        self._provider = model.split(".")[0] if "." in model else "anthropic"
        self._config = self.MODEL_CONFIGS.get(self._provider, self.MODEL_CONFIGS["anthropic"])

        # Get region
        region = region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

        # Initialize client
        session_kwargs: dict[str, Any] = {}
        if profile:
            session_kwargs["profile_name"] = profile

        session = boto3.Session(**session_kwargs)
        self._client = session.client(
            "bedrock-runtime",
            region_name=region,
        )

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model

    def _build_request_body(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """Build the request body based on model provider."""
        format_type = self._config.get("format", "anthropic")

        if format_type == "anthropic":
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens or 4096,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
        elif format_type == "titan":
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "temperature": temperature,
                    "maxTokenCount": max_tokens or 4096,
                },
            }
        elif format_type == "llama":
            body = {
                "prompt": prompt,
                "temperature": temperature,
                "max_gen_len": max_tokens or 2048,
            }
        elif format_type == "mistral":
            body = {
                "prompt": f"<s>[INST] {prompt} [/INST]",
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
            }
        else:
            body = {"prompt": prompt}

        return json.dumps(body)

    def _parse_response(self, response_body: dict[str, Any]) -> str:
        """Parse the response based on model provider."""
        format_type = self._config.get("format", "anthropic")

        if format_type == "anthropic":
            content = response_body.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            return ""
        elif format_type == "titan":
            results = response_body.get("results", [])
            if results:
                return results[0].get("outputText", "")
            return ""
        elif format_type == "llama":
            return response_body.get("generation", "")
        elif format_type == "mistral":
            outputs = response_body.get("outputs", [])
            if outputs:
                return outputs[0].get("text", "")
            return ""
        else:
            return str(response_body)

    def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from AWS Bedrock.

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

            body = self._build_request_body(prompt, temperature, max_tokens)

            response = self._client.invoke_model(
                modelId=self._model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            return self._parse_response(response_body)

        except Exception as e:
            raise LibrarianError(f"AWS Bedrock generation failed: {e}")
