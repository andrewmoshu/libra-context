"""Rules-based Librarian for pattern-based context selection."""

import re

from libra.core.config import LibrarianRule
from libra.core.models import Context, ContextRequest, ScoredContext
from libra.librarian.base import Librarian


class RulesLibrarian(Librarian):
    """Rules-based Librarian using pattern matching.

    Fast and predictable context selection based on configurable rules.
    Each rule has a pattern to match against the task and weights to
    boost certain context types or tags.
    """

    def __init__(self, rules: list[LibrarianRule] | None = None):
        """Initialize the rules-based Librarian.

        Args:
            rules: List of rules for context selection. If None, uses defaults.
        """
        from libra.core.config import LibraConfig

        self.rules = rules if rules is not None else LibraConfig.default_rules()
        # Compile regex patterns for efficiency
        self._compiled_rules = [
            (re.compile(rule.pattern, re.IGNORECASE), rule) for rule in self.rules
        ]

    def select(
        self,
        request: ContextRequest,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Select and score contexts using rule-based matching.

        Args:
            request: The context request with task description
            candidates: List of candidate contexts to evaluate

        Returns:
            List of scored contexts sorted by relevance (highest first)
        """
        if not candidates:
            return []

        # Find matching rules
        matched_rules = []
        for pattern, rule in self._compiled_rules:
            if pattern.search(request.task):
                matched_rules.append(rule)

        # Score each candidate
        scored = []
        for context in candidates:
            score = self._calculate_score(context, matched_rules, request)
            if score > 0:
                scored.append(ScoredContext(context=context, relevance_score=score))

        # Sort by score descending
        scored.sort(key=lambda x: x.relevance_score, reverse=True)

        return scored

    def _calculate_score(
        self,
        context: Context,
        matched_rules: list[LibrarianRule],
        request: ContextRequest,
    ) -> float:
        """Calculate relevance score for a context.

        Args:
            context: The context to score
            matched_rules: Rules that matched the task
            request: The original request for filter checking

        Returns:
            Relevance score between 0 and 1
        """
        # Base score
        base_score = 0.3

        # Apply type and tag filters from request
        if request.types and context.type not in request.types:
            return 0.0

        if request.tags and not any(tag in context.tags for tag in request.tags):
            return 0.0

        # Apply matched rules
        rule_boost = 0.0
        for rule in matched_rules:
            # Check type boost
            if context.type in rule.boost_types:
                rule_boost += 0.2 * rule.weight

            # Check tag boost
            for tag in context.tags:
                if tag in rule.boost_tags:
                    rule_boost += 0.15 * rule.weight

        # Check for keyword overlap between task and content
        task_words = set(request.task.lower().split())
        content_words = set(context.content.lower().split())
        overlap = len(task_words & content_words)
        keyword_boost = min(0.3, overlap * 0.05)

        # Recency boost (more recently accessed = higher score)
        recency_boost = 0.0
        if context.accessed_at:
            # Simple heuristic: if accessed in last 7 days, boost
            from datetime import datetime, timedelta

            if datetime.utcnow() - context.accessed_at < timedelta(days=7):
                recency_boost = 0.1

        # Access frequency boost
        frequency_boost = min(0.1, context.access_count * 0.01)

        # Calculate final score
        total = base_score + rule_boost + keyword_boost + recency_boost + frequency_boost

        # Normalize to 0-1 range
        return min(1.0, total)

    def add_rule(self, rule: LibrarianRule) -> None:
        """Add a new rule to the Librarian.

        Args:
            rule: The rule to add
        """
        self.rules.append(rule)
        self._compiled_rules.append(
            (re.compile(rule.pattern, re.IGNORECASE), rule)
        )

    def remove_rule(self, pattern: str) -> bool:
        """Remove a rule by its pattern.

        Args:
            pattern: The pattern of the rule to remove

        Returns:
            True if a rule was removed, False otherwise
        """
        for i, rule in enumerate(self.rules):
            if rule.pattern == pattern:
                del self.rules[i]
                del self._compiled_rules[i]
                return True
        return False
