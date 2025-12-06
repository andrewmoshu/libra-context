"""Base class for content ingestors."""

from abc import ABC, abstractmethod
from pathlib import Path

from libra.core.models import Context, ContextType


class Ingestor(ABC):
    """Abstract base class for content ingestors.

    Ingestors are responsible for extracting text content from various
    sources and converting them into Context objects.
    """

    @abstractmethod
    def can_ingest(self, source: str | Path) -> bool:
        """Check if this ingestor can handle the given source.

        Args:
            source: Path or identifier of the content source

        Returns:
            True if this ingestor can handle the source
        """
        pass

    @abstractmethod
    def ingest(
        self,
        source: str | Path,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
    ) -> list[Context]:
        """Ingest content from a source.

        Args:
            source: Path or content to ingest
            context_type: Type to assign to created contexts
            tags: Tags to apply to created contexts

        Returns:
            List of Context objects created from the source
        """
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this ingestor supports."""
        pass
