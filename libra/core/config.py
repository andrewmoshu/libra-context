"""Configuration management for libra."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from libra.core.models import LibrarianMode


class LibrarianRule(BaseModel):
    """A rule for the rules-based Librarian."""

    pattern: str  # Regex pattern to match against task
    boost_types: list[str] = Field(default_factory=list)
    boost_tags: list[str] = Field(default_factory=list)
    weight: float = 1.0


class LLMConfig(BaseModel):
    """Configuration for LLM-based Librarian."""

    provider: str = "gemini"
    model: str = "gemini-2.5-flash"


class EmbeddingConfig(BaseModel):
    """Configuration for embedding provider."""

    provider: str = "gemini"
    model: str = "gemini-embedding-001"
    dimensions: int = 768


class ServerConfig(BaseModel):
    """Configuration for HTTP server."""

    http_port: int = 8377
    http_host: str = "127.0.0.1"
    enable_cors: bool = False


class DefaultsConfig(BaseModel):
    """Default values for various operations."""

    token_budget: int = 2000
    chunk_size: int = 512
    min_relevance: float = 0.3


class LibrarianConfig(BaseModel):
    """Configuration for the Librarian component."""

    mode: LibrarianMode = LibrarianMode.HYBRID
    llm: LLMConfig = Field(default_factory=LLMConfig)
    rules: list[LibrarianRule] = Field(default_factory=list)


class LibraConfig(BaseModel):
    """Main configuration for libra."""

    data_dir: Path = Field(default_factory=lambda: Path.home() / ".libra")
    log_level: str = "info"
    librarian: LibrarianConfig = Field(default_factory=LibrarianConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def default_rules(cls) -> list[LibrarianRule]:
        """Get default Librarian rules."""
        return [
            LibrarianRule(
                pattern=r"(code|programming|function|refactor|debug|implement)",
                boost_types=["knowledge", "preference"],
                boost_tags=["coding", "technical", "api"],
                weight=1.5,
            ),
            LibrarianRule(
                pattern=r"(write|email|message|draft|document)",
                boost_types=["preference"],
                boost_tags=["communication", "style", "writing"],
                weight=1.3,
            ),
            LibrarianRule(
                pattern=r"(remember|recall|previous|last time|before)",
                boost_types=["history"],
                boost_tags=["decisions", "past"],
                weight=1.4,
            ),
            LibrarianRule(
                pattern=r"(fix|bug|error|issue|problem)",
                boost_types=["knowledge", "history"],
                boost_tags=["debugging", "errors", "technical"],
                weight=1.5,
            ),
        ]

    @classmethod
    def load(cls, path: Path | None = None) -> "LibraConfig":
        """Load configuration from file or create default."""
        if path is None:
            path = Path.home() / ".libra" / "config.yaml"

        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            config = cls.model_validate(data)
        else:
            config = cls()
            # Add default rules if no rules specified
            if not config.librarian.rules:
                config.librarian.rules = cls.default_rules()

        # Override with environment variables
        config = config._apply_env_overrides()

        return config

    def _apply_env_overrides(self) -> "LibraConfig":
        """Apply environment variable overrides."""
        env_mapping: dict[str, tuple[str, Callable[[str], Any]]] = {
            "LIBRA_DATA_DIR": ("data_dir", lambda x: Path(x)),
            "LIBRA_LOG_LEVEL": ("log_level", str),
            "LIBRA_LIBRARIAN_MODE": ("librarian.mode", LibrarianMode),
            "LIBRA_EMBEDDING_PROVIDER": ("embedding.provider", str),
            "LIBRA_SERVER_HTTP_PORT": ("server.http_port", int),
        }

        data = self.model_dump()

        for env_var, (path, converter) in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                parts = path.split(".")
                obj = data
                for part in parts[:-1]:
                    obj = obj[part]
                obj[parts[-1]] = converter(value)

        return LibraConfig.model_validate(data)

    def save(self, path: Path | None = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = self.data_dir / "config.yaml"

        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and handle special types
        data = self.model_dump(mode="json")
        data["data_dir"] = str(self.data_dir)

        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        """Get the database file path."""
        return self.data_dir / "libra.db"

    @property
    def config_path(self) -> Path:
        """Get the config file path."""
        return self.data_dir / "config.yaml"
