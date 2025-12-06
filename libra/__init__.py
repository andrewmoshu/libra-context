"""
libra - Intelligent Context Orchestration for AI Agents

libra is a local-first context orchestration platform that acts as an
intelligent intermediary between users' knowledge and their AI agents.
"""

__version__ = "0.1.0"
__author__ = "libra team"

from libra.core.models import (
    Context,
    ContextType,
    AuditEntry,
    ContextRequest,
    ContextResponse,
    ScoredContext,
)
from libra.core.config import LibraConfig
from libra.service import LibraService, get_service

__all__ = [
    # Models
    "Context",
    "ContextType",
    "AuditEntry",
    "ContextRequest",
    "ContextResponse",
    "ScoredContext",
    # Configuration
    "LibraConfig",
    # Service
    "LibraService",
    "get_service",
    # Version
    "__version__",
]
