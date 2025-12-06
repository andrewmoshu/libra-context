"""Base class for Librarian implementations."""

from abc import ABC, abstractmethod

from libra.core.models import Context, ContextRequest, ScoredContext


class Librarian(ABC):
    """Abstract base class for Librarian implementations.

    The Librarian is the intelligent core of libra. It receives a task
    description and available contexts, then selects and ranks contexts
    by relevance.
    """

    @abstractmethod
    def select(
        self,
        request: ContextRequest,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Select and score relevant contexts for a task.

        Args:
            request: The context request with task description
            candidates: List of candidate contexts to evaluate

        Returns:
            List of scored contexts sorted by relevance (highest first)
        """
        pass

    def explain_selection(
        self,
        request: ContextRequest,
        selected: list[ScoredContext],
    ) -> str:
        """Generate an explanation for why contexts were selected.

        Args:
            request: The original context request
            selected: The contexts that were selected

        Returns:
            Human-readable explanation of the selection
        """
        if not selected:
            return "No contexts were selected for this task."

        lines = [f"Selected {len(selected)} contexts for task: {request.task[:50]}..."]
        for i, sc in enumerate(selected, 1):
            lines.append(
                f"  {i}. [{sc.context.type}] {sc.context.content[:50]}... "
                f"(score: {sc.relevance_score:.2f})"
            )
        return "\n".join(lines)
