"""Directory ingestor for libra.

Recursively processes directories, applying appropriate ingestors
to each file based on extension.
"""

from pathlib import Path
from typing import Callable

from libra.core.exceptions import IngestionError
from libra.core.models import Context, ContextType
from libra.ingestion.base import Ingestor
from libra.ingestion.chunker import Chunker


class DirectoryIngestor(Ingestor):
    """Ingestor for directories.

    Recursively processes a directory, applying the appropriate ingestor
    to each file based on extension. Respects .gitignore patterns.
    """

    def __init__(
        self,
        chunker: Chunker | None = None,
        respect_gitignore: bool = True,
        max_depth: int = 10,
        max_files: int = 1000,
        encoding: str = "utf-8",
    ):
        """Initialize the directory ingestor.

        Args:
            chunker: Chunker instance for splitting large files
            respect_gitignore: Whether to respect .gitignore patterns
            max_depth: Maximum recursion depth
            max_files: Maximum number of files to process
            encoding: Text encoding to use when reading files
        """
        self.chunker = chunker or Chunker()
        self.respect_gitignore = respect_gitignore
        self.max_depth = max_depth
        self.max_files = max_files
        self.encoding = encoding
        self._file_count = 0
        self._ingestors: dict[str, Ingestor] = {}
        self._gitignore_patterns: list[str] = []

        # Register default ingestors
        self._register_default_ingestors()

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions (all registered)."""
        extensions = []
        for ingestor in self._ingestors.values():
            extensions.extend(ingestor.supported_extensions)
        return list(set(extensions))

    def _register_default_ingestors(self) -> None:
        """Register default file type ingestors."""
        from libra.ingestion.markdown import MarkdownIngestor
        from libra.ingestion.text import TextIngestor

        text_ingestor = TextIngestor(chunker=self.chunker, encoding=self.encoding)
        markdown_ingestor = MarkdownIngestor(chunker=self.chunker, encoding=self.encoding)

        for ext in text_ingestor.supported_extensions:
            self._ingestors[ext] = text_ingestor

        for ext in markdown_ingestor.supported_extensions:
            self._ingestors[ext] = markdown_ingestor

    def register_ingestor(self, extension: str, ingestor: Ingestor) -> None:
        """Register an ingestor for a file extension.

        Args:
            extension: File extension (with dot, e.g., ".py")
            ingestor: Ingestor instance to use for this extension
        """
        self._ingestors[extension.lower()] = ingestor

    def can_ingest(self, source: str | Path) -> bool:
        """Check if this ingestor can handle the source."""
        path = Path(source)
        return path.is_dir() and path.exists()

    def ingest(
        self,
        source: str | Path,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> list[Context]:
        """Ingest content from a directory.

        Args:
            source: Path to directory
            context_type: Type to assign to created contexts
            tags: Tags to apply to created contexts
            progress_callback: Optional callback(file_path, current, total)

        Returns:
            List of Context objects from all files
        """
        tags = tags or []
        path = Path(source)

        if not path.exists():
            raise IngestionError(str(source), "Directory does not exist")

        if not path.is_dir():
            raise IngestionError(str(source), "Path is not a directory")

        self._file_count = 0
        self._gitignore_patterns = []

        # Load gitignore patterns if present
        if self.respect_gitignore:
            self._load_gitignore(path)

        # Collect all files first
        files = list(self._collect_files(path, depth=0))
        total_files = len(files)

        # Process each file
        all_contexts = []
        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(str(file_path), i + 1, total_files)

            try:
                contexts = self._ingest_file(file_path, context_type, tags, path)
                all_contexts.extend(contexts)
            except Exception:
                # Log but continue on individual file failures
                continue

        return all_contexts

    def _collect_files(self, directory: Path, depth: int) -> list[Path]:
        """Recursively collect files to process.

        Args:
            directory: Directory to scan
            depth: Current recursion depth

        Yields:
            Paths to files that should be processed
        """
        if depth > self.max_depth:
            return []

        files = []
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return []

        for entry in sorted(entries):
            if self._file_count >= self.max_files:
                break

            # Skip hidden files/directories
            if entry.name.startswith("."):
                continue

            # Check gitignore
            if self._is_gitignored(entry):
                continue

            if entry.is_file():
                if entry.suffix.lower() in self._ingestors:
                    files.append(entry)
                    self._file_count += 1
            elif entry.is_dir():
                files.extend(self._collect_files(entry, depth + 1))

        return files

    def _ingest_file(
        self,
        file_path: Path,
        context_type: ContextType,
        tags: list[str],
        root_dir: Path,
    ) -> list[Context]:
        """Ingest a single file.

        Args:
            file_path: Path to file
            context_type: Type to assign
            tags: Base tags to apply
            root_dir: Root directory for relative path calculation

        Returns:
            List of contexts from the file
        """
        extension = file_path.suffix.lower()
        ingestor = self._ingestors.get(extension)

        if not ingestor:
            return []

        # Add relative path as tag
        try:
            rel_path = file_path.relative_to(root_dir)
            path_tag = str(rel_path.parent).replace("/", "-").replace("\\", "-")
            file_tags = tags + [path_tag] if path_tag and path_tag != "." else tags
        except ValueError:
            file_tags = tags

        return ingestor.ingest(file_path, context_type, file_tags)

    def _load_gitignore(self, directory: Path) -> None:
        """Load .gitignore patterns from directory."""
        gitignore_path = directory / ".gitignore"
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text()
                for line in content.split("\n"):
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith("#"):
                        self._gitignore_patterns.append(line)
            except Exception:
                pass

        # Add common patterns
        self._gitignore_patterns.extend([
            "__pycache__",
            "*.pyc",
            "node_modules",
            ".git",
            ".venv",
            "venv",
            ".env",
            "*.egg-info",
            "dist",
            "build",
            ".DS_Store",
            "Thumbs.db",
        ])

    def _is_gitignored(self, path: Path) -> bool:
        """Check if a path matches gitignore patterns."""
        name = path.name

        for pattern in self._gitignore_patterns:
            # Simple pattern matching (not full gitignore spec)
            if pattern.startswith("*"):
                # Wildcard at start: *.pyc
                if name.endswith(pattern[1:]):
                    return True
            elif pattern.endswith("*"):
                # Wildcard at end: build*
                if name.startswith(pattern[:-1]):
                    return True
            elif pattern.endswith("/"):
                # Directory pattern
                if path.is_dir() and name == pattern[:-1]:
                    return True
            else:
                # Exact match
                if name == pattern:
                    return True

        return False

    def get_file_count(self, directory: Path) -> int:
        """Count files that would be processed.

        Args:
            directory: Directory to scan

        Returns:
            Number of files that would be ingested
        """
        self._file_count = 0
        if self.respect_gitignore:
            self._gitignore_patterns = []
            self._load_gitignore(directory)

        files = self._collect_files(directory, depth=0)
        return len(files)
