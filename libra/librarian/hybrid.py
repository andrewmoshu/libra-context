"""Hybrid Librarian combining rules-based pre-filtering with LLM selection."""

from libra.core.config import LibrarianRule
from libra.core.models import Context, ContextRequest, ScoredContext
from libra.librarian.base import Librarian
from libra.librarian.llm import GeminiLibrarian
from libra.librarian.rules import RulesLibrarian


class HybridLibrarian(Librarian):
    """Hybrid Librarian that combines rules and LLM-based selection.

    First uses rules-based pre-filtering to reduce candidates,
    then uses Gemini for intelligent final selection.

    This provides the speed of rules with the intelligence of LLM reasoning.
    """

    def __init__(
        self,
        rules: list[LibrarianRule] | None = None,
        gemini_model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        prefilter_limit: int = 50,
        min_prefilter_score: float = 0.2,
    ):
        """Initialize the Hybrid Librarian.

        Args:
            rules: Rules for pre-filtering (uses defaults if None)
            gemini_model: Gemini model to use for final selection
            api_key: Google AI API key
            prefilter_limit: Maximum candidates to pass to LLM
            min_prefilter_score: Minimum score from rules to consider
        """
        self.rules_librarian = RulesLibrarian(rules=rules)
        self.llm_librarian = GeminiLibrarian(model=gemini_model, api_key=api_key)
        self.prefilter_limit = prefilter_limit
        self.min_prefilter_score = min_prefilter_score

    def select(
        self,
        request: ContextRequest,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Select contexts using hybrid rules + LLM approach.

        Args:
            request: The context request with task description
            candidates: List of candidate contexts to evaluate

        Returns:
            List of scored contexts sorted by relevance (highest first)
        """
        if not candidates:
            return []

        # Step 1: Rules-based pre-filtering
        prefiltered = self.rules_librarian.select(request, candidates)

        # Filter by minimum score
        prefiltered = [
            sc for sc in prefiltered if sc.relevance_score >= self.min_prefilter_score
        ]

        # Limit candidates for LLM
        if len(prefiltered) > self.prefilter_limit:
            prefiltered = prefiltered[: self.prefilter_limit]

        if not prefiltered:
            # If no candidates pass rules, fall back to embedding-based candidates
            # Just use top candidates by order
            prefiltered = [
                ScoredContext(context=c, relevance_score=0.5)
                for c in candidates[: self.prefilter_limit]
            ]

        # Step 2: LLM-based final selection
        prefiltered_contexts = [sc.context for sc in prefiltered]
        final_selection = self.llm_librarian.select(request, prefiltered_contexts)

        return final_selection

    def explain_selection(
        self,
        request: ContextRequest,
        selected: list[ScoredContext],
    ) -> str:
        """Generate an explanation for the hybrid selection."""
        return self.llm_librarian.explain_selection(request, selected)


def create_librarian(
    mode: str = "hybrid",
    rules: list[LibrarianRule] | None = None,
    gemini_model: str = "gemini-2.5-flash",
    api_key: str | None = None,
) -> Librarian:
    """Factory function to create a Librarian based on mode.

    Args:
        mode: "rules", "llm", or "hybrid"
        rules: Optional rules for rules/hybrid modes
        gemini_model: Gemini model for llm/hybrid modes
        api_key: Google AI API key for llm/hybrid modes

    Returns:
        A Librarian instance
    """
    if mode == "rules":
        return RulesLibrarian(rules=rules)
    elif mode == "llm":
        return GeminiLibrarian(model=gemini_model, api_key=api_key)
    elif mode == "hybrid":
        return HybridLibrarian(
            rules=rules, gemini_model=gemini_model, api_key=api_key
        )
    else:
        raise ValueError(f"Unknown librarian mode: {mode}")
