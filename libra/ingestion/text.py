"""Text file ingestor for libra."""

from pathlib import Path

from libra.core.exceptions import IngestionError
from libra.core.models import Context, ContextType
from libra.ingestion.base import Ingestor
from libra.ingestion.chunker import Chunker


class TextIngestor(Ingestor):
    """Ingestor for plain text files.

    Handles .txt files and raw text content.
    """

    def __init__(
        self,
        chunker: Chunker | None = None,
        encoding: str = "utf-8",
    ):
        """Initialize the text ingestor.

        Args:
            chunker: Chunker instance for splitting large files
            encoding: Text encoding to use when reading files
        """
        self.chunker = chunker or Chunker()
        self.encoding = encoding

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".txt", ".text"]

    def can_ingest(self, source: str | Path) -> bool:
        """Check if this ingestor can handle the source."""
        if isinstance(source, str) and not Path(source).exists():
            # Raw text content
            return True

        path = Path(source)
        return path.suffix.lower() in self.supported_extensions

    def ingest(
        self,
        source: str | Path,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
    ) -> list[Context]:
        """Ingest text from a file or raw content.

        Args:
            source: Path to text file or raw text content
            context_type: Type to assign to created contexts
            tags: Tags to apply to created contexts

        Returns:
            List of Context objects
        """
        tags = tags or []

        # Determine if source is a file or raw text
        path = Path(source) if isinstance(source, Path) else Path(source)

        if path.exists() and path.is_file():
            return self._ingest_file(path, context_type, tags)
        else:
            # Treat as raw text
            return self._ingest_text(str(source), "manual", context_type, tags)

    def _ingest_file(
        self,
        path: Path,
        context_type: ContextType,
        tags: list[str],
    ) -> list[Context]:
        """Ingest from a file."""
        try:
            content = path.read_text(encoding=self.encoding)
        except Exception as e:
            raise IngestionError(str(path), f"Failed to read file: {e}")

        source_path = str(path.absolute())
        file_tags = tags + [path.stem]

        return self._ingest_text(content, source_path, context_type, file_tags)

    def _ingest_text(
        self,
        content: str,
        source: str,
        context_type: ContextType,
        tags: list[str],
    ) -> list[Context]:
        """Ingest raw text content."""
        if not content.strip():
            return []

        # Chunk the content
        chunks = self.chunker.chunk(content)

        # Create contexts from chunks
        contexts = []
        for i, chunk in enumerate(chunks):
            ctx = Context(
                type=context_type,
                content=chunk.content,
                tags=tags.copy(),
                source=source,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "tokens": chunk.metadata.get("tokens", 0),
                },
            )
            contexts.append(ctx)

        return contexts

    def ingest_raw(
        self,
        content: str,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
        source: str = "manual",
    ) -> list[Context]:
        """Ingest raw text content directly.

        Args:
            content: Raw text content
            context_type: Type to assign
            tags: Tags to apply
            source: Source identifier

        Returns:
            List of Context objects
        """
        return self._ingest_text(content, source, context_type, tags or [])
