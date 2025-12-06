"""Core data models for libra."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class ContextType(str, Enum):
    """Types of context that libra can store and serve."""

    KNOWLEDGE = "knowledge"  # Facts, documentation, reference material
    PREFERENCE = "preference"  # How the user likes things done
    HISTORY = "history"  # Past interactions, decisions, events


class RequestSource(str, Enum):
    """Source of a context request."""

    MCP = "mcp"
    API = "api"
    CLI = "cli"


class LibrarianMode(str, Enum):
    """Mode for the Librarian to operate in."""

    RULES = "rules"  # Pattern-based selection
    LLM = "llm"  # Gemini-based reasoning
    HYBRID = "hybrid"  # Rules pre-filter + LLM final selection


class Context(BaseModel):
    """A discrete unit of information that might be useful to an AI agent."""

    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    type: ContextType
    content: str
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"  # file path, "manual", URL
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    accessed_at: Optional[datetime] = None
    access_count: int = 0
    metadata: dict = Field(default_factory=dict)

    def touch(self) -> None:
        """Update access timestamp and count."""
        self.accessed_at = utc_now()
        self.access_count += 1

    def update_content(self, content: str) -> None:
        """Update content and timestamp."""
        self.content = content
        self.updated_at = utc_now()


class ScoredContext(BaseModel):
    """A context with a relevance score."""

    model_config = ConfigDict(use_enum_values=True)

    context: Context
    relevance_score: float = Field(ge=0.0, le=1.0)


class AuditEntry(BaseModel):
    """Record of a context request and response."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=utc_now)
    agent_id: Optional[str] = None
    task: str
    contexts_served: list[UUID] = Field(default_factory=list)
    relevance_scores: list[float] = Field(default_factory=list)
    tokens_used: int = 0
    tokens_budget: int = 0
    request_source: RequestSource = RequestSource.API
    librarian_mode: LibrarianMode = LibrarianMode.RULES
    latency_ms: int = 0


class Agent(BaseModel):
    """An AI agent that requests context from libra."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    name: str
    description: Optional[str] = None
    default_budget: int = 2000
    allowed_types: Optional[list[ContextType]] = None
    created_at: datetime = Field(default_factory=utc_now)


class ContextRequest(BaseModel):
    """A request for context from an agent."""

    model_config = ConfigDict(use_enum_values=True)

    task: str
    max_tokens: int = 2000
    types: Optional[list[ContextType]] = None
    tags: Optional[list[str]] = None
    agent_id: Optional[str] = None


class ContextResponse(BaseModel):
    """Response containing selected contexts for a task."""

    model_config = ConfigDict(use_enum_values=True)

    contexts: list[ScoredContext]
    tokens_used: int
    request_id: UUID = Field(default_factory=uuid4)
    librarian_mode: LibrarianMode = LibrarianMode.RULES
    explanation: Optional[str] = None
