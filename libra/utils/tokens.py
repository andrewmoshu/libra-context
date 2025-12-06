"""Token counting utilities for libra."""

import re
from typing import Any

# Try to import tiktoken for accurate counting, fall back to estimation
try:
    import tiktoken

    _ENCODING: Any = tiktoken.get_encoding("cl100k_base")
    _HAS_TIKTOKEN = True
except ImportError:
    _ENCODING = None
    _HAS_TIKTOKEN = False


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text.

    Uses tiktoken if available, otherwise falls back to word-based estimation.

    Args:
        text: The text to count tokens for

    Returns:
        Number of tokens
    """
    if _HAS_TIKTOKEN and _ENCODING is not None:
        return len(_ENCODING.encode(text))

    # Fallback: estimate based on words and characters
    return estimate_tokens(text)


def estimate_tokens(text: str) -> int:
    """Estimate token count using heuristics.

    Uses the approximation that 1 token ≈ 4 characters or ≈ 0.75 words.
    This is a rough estimate for GPT-style tokenizers.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated number of tokens
    """
    # Count words (split on whitespace and punctuation)
    words = re.split(r"[\s\-_.,;:!?()\"']+", text)
    word_count = len([w for w in words if w])

    # Count characters
    char_count = len(text)

    # Use both methods and take the average for better accuracy
    word_based = int(word_count / 0.75)  # ~0.75 words per token
    char_based = int(char_count / 4)  # ~4 chars per token

    return (word_based + char_based) // 2


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token limit.

    Args:
        text: The text to truncate
        max_tokens: Maximum number of tokens

    Returns:
        Truncated text
    """
    if _HAS_TIKTOKEN and _ENCODING is not None:
        tokens = _ENCODING.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return _ENCODING.decode(tokens[:max_tokens])

    # Fallback: truncate by estimated ratio
    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text

    ratio = max_tokens / current_tokens
    target_length = int(len(text) * ratio * 0.9)  # 0.9 for safety margin
    return text[:target_length] + "..."
