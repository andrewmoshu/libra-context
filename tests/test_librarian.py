"""Tests for librarian layer."""

import pytest

from libra.core.config import LibrarianRule
from libra.core.models import Context, ContextRequest, ContextType, ScoredContext
from libra.librarian.budget import BudgetManager
from libra.librarian.rules import RulesLibrarian


class TestRulesLibrarian:
    """Tests for RulesLibrarian."""

    @pytest.fixture
    def librarian(self):
        """Create a rules librarian with default rules."""
        return RulesLibrarian()

    @pytest.fixture
    def sample_contexts(self):
        """Create sample contexts for testing."""
        return [
            Context(
                type=ContextType.KNOWLEDGE,
                content="Python is a programming language used for web development",
                tags=["python", "programming", "technical"],
            ),
            Context(
                type=ContextType.PREFERENCE,
                content="User prefers functional programming style",
                tags=["coding", "style"],
            ),
            Context(
                type=ContextType.HISTORY,
                content="Last week the auth system was refactored",
                tags=["auth", "decisions"],
            ),
            Context(
                type=ContextType.KNOWLEDGE,
                content="The weather is nice today",
                tags=["weather", "general"],
            ),
        ]

    def test_select_with_coding_task(self, librarian, sample_contexts):
        """Test selection for coding-related task."""
        request = ContextRequest(
            task="Write a Python function to parse JSON",
            max_tokens=2000,
        )

        scored = librarian.select(request, sample_contexts)

        assert len(scored) > 0
        # Python and programming contexts should rank higher
        top_context = scored[0]
        assert "python" in top_context.context.content.lower() or \
               "programming" in top_context.context.content.lower()

    def test_select_empty_candidates(self, librarian):
        """Test selection with no candidates."""
        request = ContextRequest(task="Any task", max_tokens=1000)

        scored = librarian.select(request, [])

        assert scored == []

    def test_select_with_type_filter(self, librarian, sample_contexts):
        """Test selection with type filter."""
        request = ContextRequest(
            task="What happened last week?",
            max_tokens=1000,
            types=[ContextType.HISTORY],
        )

        scored = librarian.select(request, sample_contexts)

        # All results should be history type
        for sc in scored:
            assert sc.context.type == ContextType.HISTORY

    def test_select_with_tag_filter(self, librarian, sample_contexts):
        """Test selection with tag filter."""
        request = ContextRequest(
            task="Tell me about Python",
            max_tokens=1000,
            tags=["python"],
        )

        scored = librarian.select(request, sample_contexts)

        # All results should have the python tag
        for sc in scored:
            assert "python" in sc.context.tags

    def test_add_custom_rule(self, librarian):
        """Test adding a custom rule."""
        rule = LibrarianRule(
            pattern=r"weather|forecast|temperature",
            boost_types=["knowledge"],
            boost_tags=["weather"],
            weight=2.0,
        )
        librarian.add_rule(rule)

        # Now weather-related content should rank higher for weather tasks
        contexts = [
            Context(
                type=ContextType.KNOWLEDGE,
                content="Weather data",
                tags=["weather"],
            ),
            Context(
                type=ContextType.KNOWLEDGE,
                content="Programming data",
                tags=["programming"],
            ),
        ]

        request = ContextRequest(
            task="What's the weather like?",
            max_tokens=1000,
        )

        scored = librarian.select(request, contexts)

        assert len(scored) == 2
        # Weather context should rank first
        assert "weather" in scored[0].context.tags

    def test_remove_rule(self, librarian):
        """Test removing a rule."""
        initial_count = len(librarian.rules)

        # Add a rule
        rule = LibrarianRule(
            pattern=r"test-pattern",
            boost_types=["knowledge"],
            weight=1.0,
        )
        librarian.add_rule(rule)
        assert len(librarian.rules) == initial_count + 1

        # Remove it
        removed = librarian.remove_rule("test-pattern")
        assert removed is True
        assert len(librarian.rules) == initial_count

        # Try to remove non-existent rule
        removed = librarian.remove_rule("nonexistent")
        assert removed is False


class TestBudgetManager:
    """Tests for BudgetManager."""

    @pytest.fixture
    def budget_manager(self):
        """Create a budget manager."""
        return BudgetManager(default_budget=2000)

    @pytest.fixture
    def scored_contexts(self):
        """Create sample scored contexts."""
        return [
            ScoredContext(
                context=Context(
                    type=ContextType.KNOWLEDGE,
                    content="Short content",  # ~2 tokens
                ),
                relevance_score=0.9,
            ),
            ScoredContext(
                context=Context(
                    type=ContextType.KNOWLEDGE,
                    content="Medium length content with more words",  # ~7 tokens
                ),
                relevance_score=0.8,
            ),
            ScoredContext(
                context=Context(
                    type=ContextType.KNOWLEDGE,
                    content="A longer piece of content that takes more tokens to represent " * 10,
                ),
                relevance_score=0.7,
            ),
        ]

    def test_optimize_within_budget(self, budget_manager, scored_contexts):
        """Test that optimization stays within budget."""
        selected, tokens_used = budget_manager.optimize(
            scored_contexts, budget=1000
        )

        assert tokens_used <= 1000
        assert len(selected) >= 1

    def test_optimize_prioritizes_relevance(self, budget_manager, scored_contexts):
        """Test that higher relevance contexts are prioritized."""
        selected, _ = budget_manager.optimize(scored_contexts, budget=100)

        # If multiple contexts are selected, they should be in descending relevance order
        for i in range(len(selected) - 1):
            assert selected[i].relevance_score >= selected[i + 1].relevance_score

    def test_optimize_empty_candidates(self, budget_manager):
        """Test optimization with no candidates."""
        selected, tokens_used = budget_manager.optimize([], budget=1000)

        assert selected == []
        assert tokens_used == 0

    def test_estimate_tokens(self, budget_manager):
        """Test token estimation for contexts."""
        scored = ScoredContext(
            context=Context(
                type=ContextType.KNOWLEDGE,
                content="This is a test sentence with several words.",
            ),
            relevance_score=0.9,
        )

        tokens = budget_manager.estimate_tokens([scored])

        assert tokens > 0
        # Should be approximately 9-10 tokens for this sentence
        assert 5 <= tokens <= 20

    def test_optimize_respects_budget(self, budget_manager):
        """Test that we never exceed budget."""
        # Create contexts with known sizes
        contexts = []
        for i in range(20):
            contexts.append(
                ScoredContext(
                    context=Context(
                        type=ContextType.KNOWLEDGE,
                        content="Word " * (i + 1) * 10,  # Increasing sizes
                    ),
                    relevance_score=0.9 - (i * 0.03),
                )
            )

        selected, tokens_used = budget_manager.optimize(contexts, budget=500)

        assert tokens_used <= 500
