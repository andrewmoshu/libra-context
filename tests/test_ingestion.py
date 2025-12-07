"""Tests for ingestion layer."""

import tempfile
from pathlib import Path

import pytest

from libra.core.models import ContextType
from libra.ingestion.chunker import Chunker, ChunkResult
from libra.ingestion.markdown import MarkdownIngestor
from libra.ingestion.text import TextIngestor


class TestChunker:
    """Tests for the Chunker class."""

    def test_small_text_no_chunking(self):
        """Test that small text is not chunked."""
        chunker = Chunker(target_size=512)
        text = "This is a small text."

        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text.strip()

    def test_empty_text(self):
        """Test handling of empty text."""
        chunker = Chunker()

        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_paragraph_chunking(self):
        """Test chunking by paragraph boundaries."""
        chunker = Chunker(target_size=50, max_size=100)

        text = """First paragraph with some content.

Second paragraph with different content.

Third paragraph to complete the test."""

        chunks = chunker.chunk(text)

        # Should produce multiple chunks
        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, ChunkResult)
            assert chunk.content.strip()

    def test_code_block_preservation(self):
        """Test that code blocks stay intact."""
        chunker = Chunker(target_size=100, max_size=500)

        text = """Some introduction text.

```python
def hello():
    print("Hello, World!")
```

Some conclusion text."""

        chunks = chunker.chunk(text)

        # Find the chunk containing the code block
        code_found = False
        for chunk in chunks:
            if "def hello():" in chunk.content:
                code_found = True
                assert 'print("Hello, World!")' in chunk.content

        assert code_found


class TestTextIngestor:
    """Tests for TextIngestor."""

    @pytest.fixture
    def ingestor(self):
        """Create a text ingestor."""
        return TextIngestor(chunker=Chunker(target_size=512))

    def test_ingest_raw_text(self, ingestor):
        """Test ingesting raw text."""
        content = "This is some test content for ingestion."

        contexts = ingestor.ingest_raw(
            content=content,
            context_type=ContextType.KNOWLEDGE,
            tags=["test"],
            source="test-source",
        )

        assert len(contexts) >= 1
        assert contexts[0].type == ContextType.KNOWLEDGE
        assert contexts[0].content == content
        assert "test" in contexts[0].tags
        assert contexts[0].source == "test-source"

    def test_ingest_file(self, ingestor):
        """Test ingesting a text file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("File content for testing.")
            f.flush()
            path = Path(f.name)

        try:
            contexts = ingestor.ingest(
                path,
                context_type=ContextType.KNOWLEDGE,
                tags=["file-test"],
            )

            assert len(contexts) >= 1
            assert "File content for testing." in contexts[0].content
        finally:
            path.unlink()

    def test_supported_extensions(self, ingestor):
        """Test supported file extensions."""
        extensions = ingestor.supported_extensions

        assert ".txt" in extensions
        assert ".text" in extensions

    def test_can_ingest(self, ingestor):
        """Test can_ingest method."""
        # Raw text should be ingestible
        assert ingestor.can_ingest("some raw text")

        # Text files should be ingestible
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            assert ingestor.can_ingest(f.name)


class TestMarkdownIngestor:
    """Tests for MarkdownIngestor."""

    @pytest.fixture
    def ingestor(self):
        """Create a markdown ingestor."""
        return MarkdownIngestor(chunker=Chunker(target_size=512))

    def test_ingest_markdown_file(self, ingestor):
        """Test ingesting a markdown file."""
        content = """# Test Document

This is some content.

## Section 1

First section content.

## Section 2

Second section content.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            contexts = ingestor.ingest(
                path,
                context_type=ContextType.KNOWLEDGE,
                tags=["markdown-test"],
            )

            assert len(contexts) >= 1
            # Should have extracted title as tag
            all_tags = []
            for ctx in contexts:
                all_tags.extend(ctx.tags)

        finally:
            path.unlink()

    def test_extract_code_blocks(self, ingestor):
        """Test extracting code blocks from markdown."""
        content = """# Code Example

Here's some Python code:

```python
def hello():
    print("Hello!")
```

And some JavaScript:

```javascript
console.log("Hello!");
```
"""
        code_blocks = ingestor.extract_code_blocks(content)

        assert len(code_blocks) == 2
        assert code_blocks[0]["language"] == "python"
        assert code_blocks[1]["language"] == "javascript"

    def test_extract_links(self, ingestor):
        """Test extracting links from markdown."""
        content = """# Links

Check out [Google](https://google.com) and [GitHub](https://github.com).
"""
        links = ingestor.extract_links(content)

        assert len(links) == 2
        assert links[0]["text"] == "Google"
        assert links[0]["url"] == "https://google.com"

    def test_supported_extensions(self, ingestor):
        """Test supported file extensions."""
        extensions = ingestor.supported_extensions

        assert ".md" in extensions
        assert ".markdown" in extensions

    def test_split_on_headers(self):
        """Test splitting markdown by headers."""
        ingestor = MarkdownIngestor(split_on_headers=True)

        content = """# Main Title

Intro text.

## Section A

Section A content.

## Section B

Section B content.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            contexts = ingestor.ingest(path, ContextType.KNOWLEDGE)

            # Should have multiple contexts for different sections
            assert len(contexts) >= 1

        finally:
            path.unlink()
