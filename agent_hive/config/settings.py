"""Configuration settings for Agent Hive."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import os
import json


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    # Primary model for complex reasoning (Queen, strategic decisions)
    primary_model: str = "gemini-2.5-flash"

    # Fast model for simple tasks (Drones, routine operations)
    fast_model: str = "gemini-2.5-flash"

    # ACE learning model (can be different provider)
    ace_model: str = "gpt-4o-mini"

    # API keys (loaded from environment if not provided)
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    def __post_init__(self):
        if self.google_api_key is None:
            self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class ReplicationConfig:
    """Configuration for agent self-replication."""

    # Minimum task queue depth before considering replication
    min_queue_depth: int = 10

    # Maximum number of drones per type
    max_drones_per_type: int = 5

    # Cost threshold: only replicate if expected revenue > cost * multiplier
    cost_revenue_multiplier: float = 2.0

    # Cooldown between replications (seconds)
    replication_cooldown: int = 300

    # Initial number of each drone type
    initial_workers: int = 1
    initial_builders: int = 1
    initial_sellers: int = 0
    initial_researchers: int = 1


@dataclass
class LearningConfig:
    """Configuration for ACE-based learning."""

    # Path to shared skillbook file
    skillbook_path: str = "data/hive_skillbook.json"

    # Number of recent reflections to keep in context
    reflection_window: int = 5

    # Enable async learning (faster but eventual consistency)
    async_learning: bool = True

    # Number of parallel reflector workers
    max_reflector_workers: int = 3

    # Skill deduplication threshold
    dedup_threshold: float = 0.85

    # Checkpoint interval (save skillbook every N successful tasks)
    checkpoint_interval: int = 10


@dataclass
class MonetizationConfig:
    """Configuration for monetization strategies."""

    # Enable/disable monetization features
    enabled: bool = True

    # Minimum profitability threshold
    min_profit_margin: float = 0.2

    # Product pricing strategies
    pricing_strategies: List[str] = field(
        default_factory=lambda: ["cost_plus", "value_based", "competitive"]
    )

    # Revenue tracking database path
    treasury_db_path: str = "data/treasury.db"

    # Supported payment methods
    payment_methods: List[str] = field(
        default_factory=lambda: ["stripe", "crypto", "manual"]
    )


@dataclass
class HiveConfig:
    """Main configuration for the Agent Hive."""

    # Hive identification
    hive_name: str = "DefaultHive"
    hive_id: Optional[str] = None

    # Component configurations
    llm: LLMConfig = field(default_factory=LLMConfig)
    replication: ReplicationConfig = field(default_factory=ReplicationConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    monetization: MonetizationConfig = field(default_factory=MonetizationConfig)

    # Paths
    data_dir: str = "data"
    logs_dir: str = "logs"

    # Execution settings
    max_concurrent_tasks: int = 10
    task_timeout: int = 300  # seconds

    # Debug settings
    debug: bool = False
    verbose: bool = False

    def __post_init__(self):
        """Initialize derived settings and create directories."""
        import uuid

        if self.hive_id is None:
            self.hive_id = str(uuid.uuid4())[:8]

        # Create required directories
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "hive_name": self.hive_name,
            "hive_id": self.hive_id,
            "llm": {
                "primary_model": self.llm.primary_model,
                "fast_model": self.llm.fast_model,
                "ace_model": self.llm.ace_model,
            },
            "replication": {
                "min_queue_depth": self.replication.min_queue_depth,
                "max_drones_per_type": self.replication.max_drones_per_type,
                "cost_revenue_multiplier": self.replication.cost_revenue_multiplier,
                "replication_cooldown": self.replication.replication_cooldown,
                "initial_workers": self.replication.initial_workers,
                "initial_builders": self.replication.initial_builders,
                "initial_sellers": self.replication.initial_sellers,
                "initial_researchers": self.replication.initial_researchers,
            },
            "learning": {
                "skillbook_path": self.learning.skillbook_path,
                "reflection_window": self.learning.reflection_window,
                "async_learning": self.learning.async_learning,
                "max_reflector_workers": self.learning.max_reflector_workers,
                "dedup_threshold": self.learning.dedup_threshold,
                "checkpoint_interval": self.learning.checkpoint_interval,
            },
            "monetization": {
                "enabled": self.monetization.enabled,
                "min_profit_margin": self.monetization.min_profit_margin,
                "pricing_strategies": self.monetization.pricing_strategies,
                "treasury_db_path": self.monetization.treasury_db_path,
                "payment_methods": self.monetization.payment_methods,
            },
            "data_dir": self.data_dir,
            "logs_dir": self.logs_dir,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_timeout": self.task_timeout,
            "debug": self.debug,
            "verbose": self.verbose,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HiveConfig":
        """Create config from dictionary."""
        llm_data = data.get("llm", {})
        replication_data = data.get("replication", {})
        learning_data = data.get("learning", {})
        monetization_data = data.get("monetization", {})

        return cls(
            hive_name=data.get("hive_name", "DefaultHive"),
            hive_id=data.get("hive_id"),
            llm=LLMConfig(
                primary_model=llm_data.get("primary_model", "gemini-2.5-flash"),
                fast_model=llm_data.get("fast_model", "gemini-2.5-flash"),
                ace_model=llm_data.get("ace_model", "gpt-4o-mini"),
            ),
            replication=ReplicationConfig(
                min_queue_depth=replication_data.get("min_queue_depth", 10),
                max_drones_per_type=replication_data.get("max_drones_per_type", 5),
                cost_revenue_multiplier=replication_data.get(
                    "cost_revenue_multiplier", 2.0
                ),
                replication_cooldown=replication_data.get("replication_cooldown", 300),
                initial_workers=replication_data.get("initial_workers", 1),
                initial_builders=replication_data.get("initial_builders", 1),
                initial_sellers=replication_data.get("initial_sellers", 0),
                initial_researchers=replication_data.get("initial_researchers", 1),
            ),
            learning=LearningConfig(
                skillbook_path=learning_data.get(
                    "skillbook_path", "data/hive_skillbook.json"
                ),
                reflection_window=learning_data.get("reflection_window", 5),
                async_learning=learning_data.get("async_learning", True),
                max_reflector_workers=learning_data.get("max_reflector_workers", 3),
                dedup_threshold=learning_data.get("dedup_threshold", 0.85),
                checkpoint_interval=learning_data.get("checkpoint_interval", 10),
            ),
            monetization=MonetizationConfig(
                enabled=monetization_data.get("enabled", True),
                min_profit_margin=monetization_data.get("min_profit_margin", 0.2),
                pricing_strategies=monetization_data.get(
                    "pricing_strategies", ["cost_plus", "value_based", "competitive"]
                ),
                treasury_db_path=monetization_data.get(
                    "treasury_db_path", "data/treasury.db"
                ),
                payment_methods=monetization_data.get(
                    "payment_methods", ["stripe", "crypto", "manual"]
                ),
            ),
            data_dir=data.get("data_dir", "data"),
            logs_dir=data.get("logs_dir", "logs"),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 10),
            task_timeout=data.get("task_timeout", 300),
            debug=data.get("debug", False),
            verbose=data.get("verbose", False),
        )

    def save(self, path: str) -> None:
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "HiveConfig":
        """Load config from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
