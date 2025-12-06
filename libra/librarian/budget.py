"""Budget manager for token optimization."""

from libra.core.models import ScoredContext
from libra.utils.tokens import count_tokens


class BudgetManager:
    """Manages token budget for context selection.

    Responsible for fitting selected contexts within token limits
    while maximizing relevance.
    """

    def __init__(
        self,
        default_budget: int = 2000,
        type_allocation: dict[str, float] | None = None,
    ):
        """Initialize the budget manager.

        Args:
            default_budget: Default token budget if not specified
            type_allocation: Optional allocation by context type (e.g., {"knowledge": 0.5})
        """
        self.default_budget = default_budget
        self.type_allocation = type_allocation or {}

    def optimize(
        self,
        contexts: list[ScoredContext],
        budget: int | None = None,
    ) -> tuple[list[ScoredContext], int]:
        """Optimize context selection within token budget.

        Uses greedy selection: takes highest relevance first until budget exhausted.

        Args:
            contexts: Scored contexts sorted by relevance
            budget: Token budget (uses default if not specified)

        Returns:
            Tuple of (selected contexts, tokens used)
        """
        if budget is None:
            budget = self.default_budget

        if not contexts:
            return [], 0

        # If type allocation is specified, allocate budget by type
        if self.type_allocation:
            return self._optimize_with_allocation(contexts, budget)

        # Simple greedy selection
        selected = []
        tokens_used = 0

        for sc in contexts:
            context_tokens = count_tokens(sc.context.content)

            if tokens_used + context_tokens <= budget:
                selected.append(sc)
                tokens_used += context_tokens
            elif context_tokens > budget:
                # Skip contexts that alone exceed the budget
                continue

        return selected, tokens_used

    def _optimize_with_allocation(
        self,
        contexts: list[ScoredContext],
        budget: int,
    ) -> tuple[list[ScoredContext], int]:
        """Optimize with type-based budget allocation.

        Args:
            contexts: Scored contexts sorted by relevance
            budget: Total token budget

        Returns:
            Tuple of (selected contexts, tokens used)
        """
        # Group contexts by type (use string keys for type_allocation compatibility)
        by_type: dict[str, list[ScoredContext]] = {}
        for sc in contexts:
            ctx_type_str = sc.context.type if isinstance(sc.context.type, str) else sc.context.type.value
            if ctx_type_str not in by_type:
                by_type[ctx_type_str] = []
            by_type[ctx_type_str].append(sc)

        # Calculate budget per type
        type_budgets: dict[str, int] = {}
        allocated_total = 0.0
        for ctx_type_key, allocation in self.type_allocation.items():
            type_budgets[ctx_type_key] = int(budget * allocation)
            allocated_total += allocation

        # Distribute remaining budget
        if allocated_total < 1.0:
            unallocated_types = [t for t in by_type if t not in type_budgets]
            if unallocated_types:
                remaining = 1.0 - allocated_total
                per_type = remaining / len(unallocated_types)
                for ctx_type_key in unallocated_types:
                    type_budgets[ctx_type_key] = int(budget * per_type)

        # Select from each type
        selected = []
        total_tokens = 0

        for ctx_type_str, type_contexts in by_type.items():
            type_budget = type_budgets.get(ctx_type_str, 0)
            if type_budget <= 0:
                continue

            type_tokens = 0
            for sc in type_contexts:
                context_tokens = count_tokens(sc.context.content)
                if type_tokens + context_tokens <= type_budget:
                    selected.append(sc)
                    type_tokens += context_tokens

            total_tokens += type_tokens

        # Sort by relevance
        selected.sort(key=lambda x: x.relevance_score, reverse=True)

        return selected, total_tokens

    def estimate_tokens(self, contexts: list[ScoredContext]) -> int:
        """Estimate total tokens for a list of contexts.

        Args:
            contexts: List of scored contexts

        Returns:
            Estimated token count
        """
        return sum(count_tokens(sc.context.content) for sc in contexts)

    def fits_budget(
        self,
        contexts: list[ScoredContext],
        budget: int | None = None,
    ) -> bool:
        """Check if contexts fit within budget.

        Args:
            contexts: List of scored contexts
            budget: Token budget to check against

        Returns:
            True if contexts fit within budget
        """
        if budget is None:
            budget = self.default_budget

        return self.estimate_tokens(contexts) <= budget
