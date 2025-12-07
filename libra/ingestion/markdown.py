"""Markdown file ingestor for libra."""

import re
from pathlib import Path

from libra.core.exceptions import IngestionError
from libra.core.models import Context, ContextType
from libra.ingestion.base import Ingestor
from libra.ingestion.chunker import Chunker


class MarkdownIngestor(Ingestor):
    """Ingestor for Markdown files.

    Handles .md and .markdown files with special handling for:
    - Headers (extracts as tags)
    - Code blocks (preserves formatting)
    - Links and references
    """

    def __init__(
        self,
        chunker: Chunker | None = None,
        split_on_headers: bool = False,
        encoding: str = "utf-8",
    ):
        """Initialize the Markdown ingestor.

        Args:
            chunker: Chunker instance for splitting large files
            split_on_headers: If True, create separate contexts for each section
            encoding: Text encoding to use when reading files
        """
        self.chunker = chunker or Chunker()
        self.split_on_headers = split_on_headers
        self.encoding = encoding

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".md", ".markdown", ".mdown", ".mkd"]

    def can_ingest(self, source: str | Path) -> bool:
        """Check if this ingestor can handle the source."""
        path = Path(source)
        return path.suffix.lower() in self.supported_extensions

    def ingest(
        self,
        source: str | Path,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
    ) -> list[Context]:
        """Ingest content from a Markdown file.

        Args:
            source: Path to Markdown file
            context_type: Type to assign to created contexts
            tags: Tags to apply to created contexts

        Returns:
            List of Context objects
        """
        tags = tags or []
        path = Path(source)

        if not path.exists():
            raise IngestionError(str(source), "File does not exist")

        if not path.is_file():
            raise IngestionError(str(source), "Path is not a file")

        try:
            content = path.read_text(encoding=self.encoding)
        except Exception as e:
            raise IngestionError(str(path), f"Failed to read file: {e}")

        source_path = str(path.absolute())

        # Extract document title from first H1 or filename
        title = self._extract_title(content, path.stem)
        file_tags = tags + [title] if title not in tags else tags

        if self.split_on_headers:
            return self._ingest_by_sections(
                content, source_path, context_type, file_tags
            )
        else:
            return self._ingest_whole(content, source_path, context_type, file_tags)

    def _extract_title(self, content: str, fallback: str) -> str:
        """Extract document title from content."""
        # Look for first H1 header
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return fallback

    def _extract_headers(self, content: str) -> list[str]:
        """Extract all headers from content as potential tags."""
        headers = []
        for match in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
            header = match.group(1).strip()
            # Clean up header: remove special chars, lowercase
            clean = re.sub(r"[^\w\s-]", "", header).lower()
            clean = re.sub(r"\s+", "-", clean)
            if clean and len(clean) <= 50:  # Reasonable tag length
                headers.append(clean)
        return headers

    def _ingest_whole(
        self,
        content: str,
        source: str,
        context_type: ContextType,
        tags: list[str],
    ) -> list[Context]:
        """Ingest entire document, using chunker if needed."""
        if not content.strip():
            return []

        # Extract headers as additional tags
        header_tags = self._extract_headers(content)
        all_tags = list(set(tags + header_tags[:5]))  # Limit header tags

        # Chunk the content
        chunks = self.chunker.chunk(content)

        # Create contexts from chunks
        contexts = []
        for i, chunk in enumerate(chunks):
            ctx = Context(
                type=context_type,
                content=chunk.content,
                tags=all_tags.copy(),
                source=source,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "tokens": chunk.metadata.get("tokens", 0),
                    "format": "markdown",
                },
            )
            contexts.append(ctx)

        return contexts

    def _ingest_by_sections(
        self,
        content: str,
        source: str,
        context_type: ContextType,
        tags: list[str],
    ) -> list[Context]:
        """Ingest document by splitting on headers."""
        sections = self._split_by_headers(content)

        if not sections:
            # No headers found, treat as single section
            return self._ingest_whole(content, source, context_type, tags)

        contexts = []
        for i, (header, section_content) in enumerate(sections):
            if not section_content.strip():
                continue

            # Create tag from header
            section_tag = re.sub(r"[^\w\s-]", "", header).lower()
            section_tag = re.sub(r"\s+", "-", section_tag)
            section_tags = tags + [section_tag] if section_tag else tags

            # Chunk section if needed
            chunks = self.chunker.chunk(section_content)

            for j, chunk in enumerate(chunks):
                ctx = Context(
                    type=context_type,
                    content=chunk.content,
                    tags=section_tags,
                    source=source,
                    metadata={
                        "section": header,
                        "section_index": i,
                        "chunk_index": j,
                        "total_chunks": len(chunks),
                        "tokens": chunk.metadata.get("tokens", 0),
                        "format": "markdown",
                    },
                )
                contexts.append(ctx)

        return contexts

    def _split_by_headers(self, content: str) -> list[tuple[str, str]]:
        """Split content by top-level headers.

        Returns list of (header, content) tuples.
        """
        # Pattern to match headers (any level)
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        sections: list[tuple[str, str]] = []
        current_header = "Introduction"
        current_content: list[str] = []

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            match = header_pattern.match(line)

            if match:
                level = len(match.group(1))
                header_text = match.group(2).strip()

                # Only split on H1 and H2
                if level <= 2:
                    # Save current section
                    if current_content:
                        section_text = "\n".join(current_content).strip()
                        if section_text:
                            sections.append((current_header, section_text))

                    current_header = header_text
                    current_content = [line]  # Include header in content
                else:
                    current_content.append(line)
            else:
                current_content.append(line)

            i += 1

        # Add final section
        if current_content:
            section_text = "\n".join(current_content).strip()
            if section_text:
                sections.append((current_header, section_text))

        return sections

    def extract_code_blocks(self, content: str) -> list[dict]:
        """Extract code blocks from Markdown content.

        Returns list of dicts with 'language' and 'code' keys.
        """
        code_blocks = []
        pattern = re.compile(r"```(\w*)\n([\s\S]*?)```", re.MULTILINE)

        for match in pattern.finditer(content):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({"language": language, "code": code})

        return code_blocks

    def extract_links(self, content: str) -> list[dict]:
        """Extract links from Markdown content.

        Returns list of dicts with 'text' and 'url' keys.
        """
        links = []

        # Standard Markdown links: [text](url)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        for match in link_pattern.finditer(content):
            links.append({"text": match.group(1), "url": match.group(2)})

        return links
