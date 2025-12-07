"""AWS Bedrock embedding provider."""

import json
import os
from typing import Any

from libra.core.exceptions import EmbeddingError
from libra.embedding.base import EmbeddingProvider


class AWSBedrockEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using AWS Bedrock.

    Supports Amazon Titan and Cohere embedding models.
    Uses amazon.titan-embed-text-v2:0 by default (1024 dimensions).
    Requires AWS credentials configured.
    """

    # Model configurations
    MODEL_CONFIGS = {
        "amazon.titan-embed-text-v2:0": {
            "dimensions": 1024,
            "input_key": "inputText",
            "output_key": "embedding",
        },
        "amazon.titan-embed-text-v1": {
            "dimensions": 1536,
            "input_key": "inputText",
            "output_key": "embedding",
        },
        "amazon.titan-embed-image-v1": {
            "dimensions": 1024,
            "input_key": "inputText",
            "output_key": "embedding",
        },
        "cohere.embed-english-v3": {
            "dimensions": 1024,
            "input_key": "texts",
            "output_key": "embeddings",
            "is_batch": True,
        },
        "cohere.embed-multilingual-v3": {
            "dimensions": 1024,
            "input_key": "texts",
            "output_key": "embeddings",
            "is_batch": True,
        },
    }

    def __init__(
        self,
        model: str = "amazon.titan-embed-text-v2:0",
        region: str | None = None,
        profile: str | None = None,
        dimensions: int | None = None,
    ):
        """Initialize the AWS Bedrock embedding provider.

        Args:
            model: The Bedrock model ID to use
            region: AWS region (or use AWS_DEFAULT_REGION env var)
            profile: AWS profile name (optional)
            dimensions: Output vector dimensions (model-specific defaults)
        """
        try:
            import boto3
        except ImportError:
            raise EmbeddingError(
                "boto3 package not installed. Install with: pip install boto3"
            )

        self.model = model

        # Get model config
        self._config = self.MODEL_CONFIGS.get(model, {
            "dimensions": 1024,
            "input_key": "inputText",
            "output_key": "embedding",
        })

        # Get dimensions
        if dimensions is not None:
            self._dimensions = dimensions
        else:
            self._dimensions = int(self._config.get("dimensions", 1024))

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
    def dimensions(self) -> int:
        """Return the dimensionality of embeddings."""
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        try:
            input_key = self._config.get("input_key", "inputText")
            output_key = self._config.get("output_key", "embedding")
            is_batch = self._config.get("is_batch", False)

            if is_batch:
                # Cohere models use batch API
                body = json.dumps({
                    input_key: [text],
                    "input_type": "search_document",
                })
            else:
                # Titan models
                body = json.dumps({input_key: text})

            response = self._client.invoke_model(
                modelId=self.model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())

            if is_batch:
                embeddings = response_body.get(output_key, [[]])
                return list(embeddings[0])
            else:
                embedding = response_body.get(output_key, [])
                return list(embedding)

        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}", e)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        is_batch = self._config.get("is_batch", False)

        if is_batch:
            # Cohere models support native batch
            try:
                input_key = self._config.get("input_key", "texts")
                output_key = self._config.get("output_key", "embeddings")

                body = json.dumps({
                    input_key: texts,
                    "input_type": "search_document",
                })

                response = self._client.invoke_model(
                    modelId=self.model,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )

                response_body = json.loads(response["body"].read())
                embeddings = response_body.get(output_key, [])
                return [list(emb) for emb in embeddings]

            except Exception as e:
                raise EmbeddingError(f"Failed to generate batch embeddings: {e}", e)
        else:
            # Titan models don't support batch, process individually
            embeddings = []
            for text in texts:
                embedding = self.embed(text)
                embeddings.append(embedding)
            return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a query.

        Uses search_query input type for Cohere models.

        Args:
            query: The query text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        is_batch = self._config.get("is_batch", False)

        if is_batch:
            # Cohere models with search_query type
            try:
                input_key = self._config.get("input_key", "texts")
                output_key = self._config.get("output_key", "embeddings")

                body = json.dumps({
                    input_key: [query],
                    "input_type": "search_query",
                })

                response = self._client.invoke_model(
                    modelId=self.model,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )

                response_body = json.loads(response["body"].read())
                embeddings = response_body.get(output_key, [[]])
                return list(embeddings[0])

            except Exception as e:
                raise EmbeddingError(f"Failed to generate query embedding: {e}", e)

        return self.embed(query)
