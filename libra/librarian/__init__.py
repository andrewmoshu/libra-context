"""Librarian components for intelligent context selection.

The Librarian is the intelligent core of libra. It receives a task
description and available contexts, then selects and ranks contexts
by relevance.

Available modes:
- rules: Fast rules-based selection
- llm: LLM-based intelligent selection (supports multiple providers)
- hybrid: Combines rules pre-filtering with LLM selection (default)

Supported LLM providers:
- gemini: Google Gemini (default)
- openai: OpenAI GPT
- anthropic: Anthropic Claude
- ollama: Local models via Ollama
- azure_openai, aws_bedrock, huggingface, together, custom
"""

from libra.librarian.base import Librarian
from libra.librarian.budget import BudgetManager
from libra.librarian.hybrid import HybridLibrarian, create_librarian
from libra.librarian.llm import GeminiLibrarian
from libra.librarian.llm_generic import GenericLLMLibrarian
from libra.librarian.rules import RulesLibrarian

__all__ = [
    "Librarian",
    "RulesLibrarian",
    "GeminiLibrarian",
    "GenericLLMLibrarian",
    "HybridLibrarian",
    "BudgetManager",
    "create_librarian",
]
