"""Hybrid Librarian combining rules-based pre-filtering with LLM selection."""

from libra.core.config import LibrarianRule, LLMConfig
from libra.core.models import Context, ContextRequest, ScoredContext
from libra.librarian.base import Librarian
from libra.librarian.rules import RulesLibrarian
from libra.llm_providers.base import LLMProvider


class HybridLibrarian(Librarian):
    """Hybrid Librarian that combines rules and LLM-based selection.

    First uses rules-based pre-filtering to reduce candidates,
    then uses an LLM for intelligent final selection.

    This provides the speed of rules with the intelligence of LLM reasoning.
    Supports multiple LLM providers: Gemini, OpenAI, Anthropic, Ollama, etc.
    """

    def __init__(
        self,
        rules: list[LibrarianRule] | None = None,
        llm_provider: LLMProvider | None = None,
        llm_config: LLMConfig | None = None,
        gemini_model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        prefilter_limit: int = 50,
        min_prefilter_score: float = 0.2,
    ):
        """Initialize the Hybrid Librarian.

        Args:
            rules: Rules for pre-filtering (uses defaults if None)
            llm_provider: Pre-configured LLM provider (takes precedence)
            llm_config: LLM configuration to create a provider
            gemini_model: Gemini model to use (legacy, prefer llm_config)
            api_key: Google AI API key (legacy, prefer llm_config)
            prefilter_limit: Maximum candidates to pass to LLM
            min_prefilter_score: Minimum score from rules to consider
        """
        from libra.librarian.llm_generic import GenericLLMLibrarian

        self.rules_librarian = RulesLibrarian(rules=rules)

        # Create LLM librarian with priority: provider > config > legacy
        # Type is Librarian (base class) to allow either GenericLLMLibrarian or GeminiLibrarian
        self.llm_librarian: Librarian
        if llm_provider is not None:
            self.llm_librarian = GenericLLMLibrarian(llm_provider=llm_provider)
        elif llm_config is not None:
            self.llm_librarian = GenericLLMLibrarian(llm_config=llm_config)
        else:
            # Legacy behavior: use Gemini with provided model/key
            from libra.librarian.llm import GeminiLibrarian

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
    llm_provider: LLMProvider | None = None,
    llm_config: LLMConfig | None = None,
    gemini_model: str = "gemini-2.5-flash",
    api_key: str | None = None,
) -> Librarian:
    """Factory function to create a Librarian based on mode.

    Args:
        mode: "rules", "llm", or "hybrid"
        rules: Optional rules for rules/hybrid modes
        llm_provider: Pre-configured LLM provider (takes precedence)
        llm_config: LLM configuration to create a provider
        gemini_model: Gemini model for llm/hybrid modes (legacy)
        api_key: Google AI API key for llm/hybrid modes (legacy)

    Returns:
        A Librarian instance
    """
    if mode == "rules":
        return RulesLibrarian(rules=rules)
    elif mode == "llm":
        from libra.librarian.llm_generic import GenericLLMLibrarian

        if llm_provider is not None:
            return GenericLLMLibrarian(llm_provider=llm_provider)
        elif llm_config is not None:
            return GenericLLMLibrarian(llm_config=llm_config)
        else:
            # Legacy behavior
            from libra.librarian.llm import GeminiLibrarian

            return GeminiLibrarian(model=gemini_model, api_key=api_key)
    elif mode == "hybrid":
        return HybridLibrarian(
            rules=rules,
            llm_provider=llm_provider,
            llm_config=llm_config,
            gemini_model=gemini_model,
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unknown librarian mode: {mode}")
