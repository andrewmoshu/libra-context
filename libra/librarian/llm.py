"""Gemini-based Librarian using LLM reasoning for context selection."""

import json
import os

from google import genai
from google.genai import types

from libra.core.exceptions import LibrarianError
from libra.core.models import Context, ContextRequest, ScoredContext
from libra.librarian.base import Librarian

SELECTION_PROMPT = """You are an intelligent context selector for an AI assistant.

Given a task description and a list of candidate contexts, evaluate each context's relevance to the task.

TASK: {task}

CANDIDATE CONTEXTS:
{contexts}

For each context, provide a relevance score from 0.0 to 1.0:
- 1.0: Highly relevant, essential for the task
- 0.7-0.9: Relevant, would significantly help
- 0.4-0.6: Somewhat relevant, might be useful
- 0.1-0.3: Marginally relevant
- 0.0: Not relevant at all

Consider:
1. Direct relevance to the task keywords and intent
2. Whether the context provides useful background or constraints
3. The context type (knowledge, preference, history) and how it applies
4. Recency for historical contexts

Return ONLY a valid JSON object with this structure:
{{
  "selections": [
    {{"id": "context-id-1", "score": 0.85, "reason": "brief reason"}},
    {{"id": "context-id-2", "score": 0.4, "reason": "brief reason"}}
  ]
}}

Include ALL contexts in your response, even with score 0.0."""


class GeminiLibrarian(Librarian):
    """LLM-based Librarian using Gemini for intelligent context selection.

    Uses gemini-2.5-flash for fast, high-quality reasoning about
    context relevance. Returns structured JSON responses.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        max_candidates_per_request: int = 30,
        min_score: float = 0.3,
    ):
        """Initialize the Gemini Librarian.

        Args:
            model: Gemini model to use
            api_key: Google AI API key (or use GOOGLE_AI_API_KEY/GEMINI_API_KEY env var)
            max_candidates_per_request: Maximum candidates to evaluate per LLM call
            min_score: Minimum score to include in results
        """
        self.model_name = model
        self.max_candidates = max_candidates_per_request
        self.min_score = min_score

        # Get API key from parameter or environment
        api_key = api_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LibrarianError(
                "GOOGLE_AI_API_KEY or GEMINI_API_KEY environment variable is required for Gemini Librarian"
            )

        # Initialize the client
        self._client = genai.Client(api_key=api_key)

        # Store generation config for reuse
        self._generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for consistent scoring
        )

    def select(
        self,
        request: ContextRequest,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Select and score contexts using Gemini reasoning.

        Args:
            request: The context request with task description
            candidates: List of candidate contexts to evaluate

        Returns:
            List of scored contexts sorted by relevance (highest first)
        """
        if not candidates:
            return []

        # Apply request filters first
        filtered = self._apply_filters(candidates, request)
        if not filtered:
            return []

        # If too many candidates, process in batches
        if len(filtered) > self.max_candidates:
            return self._batch_select(request, filtered)

        # Format candidates for the prompt
        contexts_text = self._format_candidates(filtered)

        # Generate selection using Gemini
        prompt = SELECTION_PROMPT.format(task=request.task, contexts=contexts_text)

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._generation_config,
            )
            selections = self._parse_response(response.text, filtered)

            # Filter by minimum score and sort
            scored = [s for s in selections if s.relevance_score >= self.min_score]
            scored.sort(key=lambda x: x.relevance_score, reverse=True)

            return scored

        except Exception as e:
            raise LibrarianError(f"Gemini selection failed: {e}")

    def _apply_filters(
        self,
        candidates: list[Context],
        request: ContextRequest,
    ) -> list[Context]:
        """Apply request filters to candidates."""
        filtered = candidates

        if request.types:
            filtered = [c for c in filtered if c.type in request.types]

        if request.tags:
            filtered = [
                c for c in filtered if any(t in c.tags for t in request.tags)
            ]

        return filtered

    def _format_candidates(self, candidates: list[Context]) -> str:
        """Format candidates for the prompt."""
        lines = []
        for ctx in candidates:
            # Truncate content for prompt efficiency
            content = ctx.content[:500] + "..." if len(ctx.content) > 500 else ctx.content
            lines.append(
                f"ID: {ctx.id}\n"
                f"Type: {ctx.type}\n"
                f"Tags: {', '.join(ctx.tags)}\n"
                f"Content: {content}\n"
            )
        return "\n---\n".join(lines)

    def _parse_response(
        self,
        response_text: str,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Parse the JSON response from Gemini."""
        # Build ID to context mapping
        id_to_context = {str(c.id): c for c in candidates}

        try:
            data = json.loads(response_text)
            selections = data.get("selections", [])

            scored = []
            for sel in selections:
                context_id = sel.get("id")
                score = sel.get("score", 0.0)

                if context_id in id_to_context:
                    scored.append(
                        ScoredContext(
                            context=id_to_context[context_id],
                            relevance_score=min(1.0, max(0.0, float(score))),
                        )
                    )

            return scored

        except json.JSONDecodeError as e:
            raise LibrarianError(f"Failed to parse Gemini response: {e}")

    def _batch_select(
        self,
        request: ContextRequest,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Process large candidate sets in batches.

        Selects top candidates from each batch, then does a final selection.
        """
        # Split into batches
        batches = [
            candidates[i : i + self.max_candidates]
            for i in range(0, len(candidates), self.max_candidates)
        ]

        # Process each batch
        all_scored: list[ScoredContext] = []
        for batch in batches:
            batch_scored = self.select(request, batch)
            # Take top half from each batch
            all_scored.extend(batch_scored[: len(batch_scored) // 2 + 1])

        # If still too many, do final selection
        if len(all_scored) > self.max_candidates:
            # Sort by score and take top candidates
            all_scored.sort(key=lambda x: x.relevance_score, reverse=True)
            final_candidates = [s.context for s in all_scored[: self.max_candidates]]
            return self.select(request, final_candidates)

        # Sort and return
        all_scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_scored

    def explain_selection(
        self,
        request: ContextRequest,
        selected: list[ScoredContext],
    ) -> str:
        """Generate an explanation for why contexts were selected."""
        if not selected:
            return "No contexts were selected as relevant for this task."

        lines = [
            f"🤖 Gemini Analysis for: {request.task[:50]}...",
            f"Selected {len(selected)} relevant contexts:",
            "",
        ]

        for i, sc in enumerate(selected, 1):
            lines.append(
                f"{i}. [{sc.context.type.upper()}] Score: {sc.relevance_score:.2f}"
            )
            lines.append(f"   Content: {sc.context.content[:80]}...")
            if sc.context.tags:
                lines.append(f"   Tags: {', '.join(sc.context.tags)}")
            lines.append("")

        return "\n".join(lines)
