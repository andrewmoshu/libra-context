"""Tests for core data models and configuration."""

import pytest
from datetime import datetime
from uuid import UUID

from libra.core.models import (
    Context,
    ContextType,
    AuditEntry,
    ContextRequest,
    ContextResponse,
    ScoredContext,
    LibrarianMode,
    RequestSource,
)
from libra.core.config import LibraConfig, LibrarianRule
from libra.core.exceptions import (
    LibraError,
    ContextNotFoundError,
    EmbeddingError,
    StorageError,
)


class TestContextModel:
    """Tests for the Context model."""

    def test_context_creation(self):
        """Test basic context creation."""
        context = Context(
            type=ContextType.KNOWLEDGE,
            content="Test content",
            tags=["test", "example"],
        )

        assert context.type == ContextType.KNOWLEDGE
        assert context.content == "Test content"
        assert context.tags == ["test", "example"]
        assert context.source == "manual"
        assert context.access_count == 0
        assert isinstance(context.id, UUID)
        assert isinstance(context.created_at, datetime)

    def test_context_touch(self):
        """Test context access tracking."""
        context = Context(
            type=ContextType.PREFERENCE,
            content="User likes Python",
        )

        assert context.accessed_at is None
        assert context.access_count == 0

        context.touch()

        assert context.accessed_at is not None
        assert context.access_count == 1

    def test_context_update(self):
        """Test content update."""
        context = Context(
            type=ContextType.HISTORY,
            content="Original content",
        )
        original_updated_at = context.updated_at

        context.update_content("New content")

        assert context.content == "New content"
        assert context.updated_at >= original_updated_at


class TestContextType:
    """Tests for ContextType enum."""

    def test_context_types(self):
        """Test all context types exist."""
        assert ContextType.KNOWLEDGE == "knowledge"
        assert ContextType.PREFERENCE == "preference"
        assert ContextType.HISTORY == "history"

    def test_context_type_from_string(self):
        """Test creating context type from string."""
        assert ContextType("knowledge") == ContextType.KNOWLEDGE
        assert ContextType("preference") == ContextType.PREFERENCE
        assert ContextType("history") == ContextType.HISTORY


class TestContextRequest:
    """Tests for ContextRequest model."""

    def test_basic_request(self):
        """Test basic request creation."""
        request = ContextRequest(
            task="Write a Python function",
            max_tokens=1000,
        )

        assert request.task == "Write a Python function"
        assert request.max_tokens == 1000
        assert request.types is None
        assert request.tags is None

    def test_request_with_filters(self):
        """Test request with filters."""
        request = ContextRequest(
            task="Debug the API",
            max_tokens=2000,
            types=[ContextType.KNOWLEDGE, ContextType.HISTORY],
            tags=["api", "debugging"],
        )

        assert len(request.types) == 2
        assert ContextType.KNOWLEDGE in request.types
        assert request.tags == ["api", "debugging"]


class TestScoredContext:
    """Tests for ScoredContext model."""

    def test_scored_context(self):
        """Test scored context creation."""
        context = Context(
            type=ContextType.KNOWLEDGE,
            content="Test content",
        )
        scored = ScoredContext(
            context=context,
            relevance_score=0.85,
        )

        assert scored.context == context
        assert scored.relevance_score == 0.85

    def test_score_validation(self):
        """Test score is bounded between 0 and 1."""
        context = Context(
            type=ContextType.KNOWLEDGE,
            content="Test",
        )

        # Valid scores should work
        ScoredContext(context=context, relevance_score=0.0)
        ScoredContext(context=context, relevance_score=1.0)
        ScoredContext(context=context, relevance_score=0.5)


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_audit_entry_creation(self):
        """Test audit entry creation."""
        entry = AuditEntry(
            agent_id="test-agent",
            task="Test task",
            tokens_used=500,
            tokens_budget=1000,
        )

        assert entry.agent_id == "test-agent"
        assert entry.task == "Test task"
        assert entry.tokens_used == 500
        assert entry.tokens_budget == 1000
        assert isinstance(entry.id, UUID)
        assert isinstance(entry.timestamp, datetime)


class TestLibraConfig:
    """Tests for configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LibraConfig()

        assert config.log_level == "info"
        assert config.librarian.mode == LibrarianMode.HYBRID
        assert config.embedding.provider == "gemini"
        assert config.embedding.model == "text-embedding-004"
        assert config.defaults.token_budget == 2000
        assert config.defaults.chunk_size == 512

    def test_default_rules(self):
        """Test default librarian rules."""
        rules = LibraConfig.default_rules()

        assert len(rules) > 0
        assert all(isinstance(r, LibrarianRule) for r in rules)

        # Check that coding rule exists
        coding_rules = [r for r in rules if "code" in r.pattern]
        assert len(coding_rules) > 0


class TestExceptions:
    """Tests for custom exceptions."""

    def test_libra_error(self):
        """Test base LibraError."""
        error = LibraError("Test error")
        assert str(error) == "Test error"

    def test_context_not_found(self):
        """Test ContextNotFoundError."""
        error = ContextNotFoundError("abc-123")
        assert "abc-123" in str(error)
        assert error.context_id == "abc-123"

    def test_embedding_error(self):
        """Test EmbeddingError."""
        original = ValueError("Original error")
        error = EmbeddingError("Failed to embed", original)
        assert "Failed to embed" in str(error)
        assert error.original_error == original
