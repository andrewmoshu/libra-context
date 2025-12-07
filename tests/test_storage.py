"""Tests for storage layer."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from libra.core.exceptions import ContextNotFoundError
from libra.core.models import (
    AuditEntry,
    Context,
    ContextType,
    LibrarianMode,
    RequestSource,
)
from libra.storage.database import ContextStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = ContextStore(db_path, vector_dimensions=768)
        yield store
        store.close()


class TestContextStore:
    """Tests for ContextStore."""

    def test_add_and_get_context(self, temp_db):
        """Test adding and retrieving a context."""
        context = Context(
            type=ContextType.KNOWLEDGE,
            content="Python is a programming language",
            tags=["python", "programming"],
        )

        temp_db.add_context(context)
        retrieved = temp_db.get_context(context.id)

        assert retrieved.id == context.id
        assert retrieved.content == context.content
        assert retrieved.type == ContextType.KNOWLEDGE
        assert retrieved.tags == ["python", "programming"]

    def test_get_nonexistent_context(self, temp_db):
        """Test getting a context that doesn't exist."""
        with pytest.raises(ContextNotFoundError):
            temp_db.get_context(uuid4())

    def test_update_context(self, temp_db):
        """Test updating a context."""
        context = Context(
            type=ContextType.PREFERENCE,
            content="Original content",
            tags=["original"],
        )
        temp_db.add_context(context)

        context.content = "Updated content"
        context.tags = ["updated"]
        temp_db.update_context(context)

        retrieved = temp_db.get_context(context.id)
        assert retrieved.content == "Updated content"
        assert retrieved.tags == ["updated"]

    def test_delete_context(self, temp_db):
        """Test deleting a context."""
        context = Context(
            type=ContextType.HISTORY,
            content="Past event",
        )
        temp_db.add_context(context)

        deleted = temp_db.delete_context(context.id)
        assert deleted is True

        with pytest.raises(ContextNotFoundError):
            temp_db.get_context(context.id)

    def test_delete_nonexistent_context(self, temp_db):
        """Test deleting a context that doesn't exist."""
        deleted = temp_db.delete_context(uuid4())
        assert deleted is False

    def test_list_contexts(self, temp_db):
        """Test listing contexts."""
        for i in range(5):
            context = Context(
                type=ContextType.KNOWLEDGE,
                content=f"Content {i}",
            )
            temp_db.add_context(context)

        contexts = temp_db.list_contexts(limit=10)
        assert len(contexts) == 5

    def test_list_contexts_by_type(self, temp_db):
        """Test listing contexts filtered by type."""
        temp_db.add_context(
            Context(type=ContextType.KNOWLEDGE, content="Knowledge")
        )
        temp_db.add_context(
            Context(type=ContextType.PREFERENCE, content="Preference")
        )
        temp_db.add_context(
            Context(type=ContextType.HISTORY, content="History")
        )

        knowledge = temp_db.list_contexts(types=[ContextType.KNOWLEDGE])
        assert len(knowledge) == 1
        assert knowledge[0].type == ContextType.KNOWLEDGE

    def test_list_contexts_by_tags(self, temp_db):
        """Test listing contexts filtered by tags."""
        temp_db.add_context(
            Context(type=ContextType.KNOWLEDGE, content="Python", tags=["python"])
        )
        temp_db.add_context(
            Context(type=ContextType.KNOWLEDGE, content="Java", tags=["java"])
        )

        python_contexts = temp_db.list_contexts(tags=["python"])
        assert len(python_contexts) == 1
        assert "python" in python_contexts[0].tags

    def test_record_access(self, temp_db):
        """Test recording access to contexts."""
        context = Context(
            type=ContextType.KNOWLEDGE,
            content="Test content",
        )
        temp_db.add_context(context)

        temp_db.record_access([context.id])

        retrieved = temp_db.get_context(context.id)
        assert retrieved.access_count == 1
        assert retrieved.accessed_at is not None


class TestAuditLog:
    """Tests for audit logging."""

    def test_add_audit_entry(self, temp_db):
        """Test adding an audit entry."""
        entry = AuditEntry(
            agent_id="test-agent",
            task="Test task",
            tokens_used=100,
            tokens_budget=1000,
            request_source=RequestSource.API,
            librarian_mode=LibrarianMode.RULES,
            latency_ms=50,
        )

        temp_db.add_audit_entry(entry)

        entries = temp_db.get_audit_entries(limit=1)
        assert len(entries) == 1
        assert entries[0].agent_id == "test-agent"

    def test_get_audit_entries_by_agent(self, temp_db):
        """Test filtering audit entries by agent."""
        for i in range(3):
            temp_db.add_audit_entry(
                AuditEntry(
                    agent_id="agent-1",
                    task=f"Task {i}",
                    tokens_used=100,
                    tokens_budget=1000,
                )
            )
        temp_db.add_audit_entry(
            AuditEntry(
                agent_id="agent-2",
                task="Other task",
                tokens_used=100,
                tokens_budget=1000,
            )
        )

        agent1_entries = temp_db.get_audit_entries(agent_id="agent-1")
        assert len(agent1_entries) == 3


class TestStorageStats:
    """Tests for storage statistics."""

    def test_get_stats(self, temp_db):
        """Test getting storage statistics."""
        temp_db.add_context(
            Context(type=ContextType.KNOWLEDGE, content="Knowledge 1")
        )
        temp_db.add_context(
            Context(type=ContextType.KNOWLEDGE, content="Knowledge 2")
        )
        temp_db.add_context(
            Context(type=ContextType.PREFERENCE, content="Preference")
        )

        stats = temp_db.get_stats()

        assert stats["total_contexts"] == 3
        assert stats["contexts_by_type"]["knowledge"] == 2
        assert stats["contexts_by_type"]["preference"] == 1


class TestVectorSearch:
    """Tests for vector search functionality."""

    def test_context_with_embedding(self, temp_db):
        """Test storing and retrieving context with embedding."""
        embedding = [0.1] * 768  # Simple test embedding

        context = Context(
            type=ContextType.KNOWLEDGE,
            content="Test content",
            embedding=embedding,
        )
        temp_db.add_context(context)

        retrieved = temp_db.get_context(context.id)
        assert retrieved.embedding is not None
        assert len(retrieved.embedding) == 768

    def test_search_by_embedding(self, temp_db):
        """Test searching by embedding similarity."""
        # Add contexts with embeddings
        for i in range(5):
            embedding = [float(i) / 10] * 768
            context = Context(
                type=ContextType.KNOWLEDGE,
                content=f"Content {i}",
                embedding=embedding,
            )
            temp_db.add_context(context)

        # Search with a query embedding
        query_embedding = [0.25] * 768
        results = temp_db.search_by_embedding(query_embedding, limit=3)

        assert len(results) == 3
        for ctx, score in results:
            assert isinstance(ctx, Context)
            assert 0 <= score <= 1
