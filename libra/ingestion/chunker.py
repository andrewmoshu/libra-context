"""Intelligent text chunking for libra."""

import re
from dataclasses import dataclass

from libra.utils.tokens import count_tokens


@dataclass
class ChunkResult:
    """Result of chunking a document."""

    content: str
    start_index: int
    end_index: int
    metadata: dict


class Chunker:
    """Intelligent text chunker that respects semantic boundaries.

    Splits text into chunks that:
    - Fit within token limits
    - Preserve paragraph boundaries
    - Keep code blocks intact
    - Include slight overlap for context continuity
    """

    def __init__(
        self,
        target_size: int = 512,
        max_size: int = 1024,
        overlap: int = 50,
        min_size: int = 100,
    ):
        """Initialize the chunker.

        Args:
            target_size: Target chunk size in tokens
            max_size: Maximum chunk size in tokens
            overlap: Number of tokens to overlap between chunks
            min_size: Minimum chunk size (avoid tiny chunks)
        """
        self.target_size = target_size
        self.max_size = max_size
        self.overlap = overlap
        self.min_size = min_size

    def chunk(self, text: str) -> list[ChunkResult]:
        """Split text into chunks.

        Args:
            text: The text to chunk

        Returns:
            List of ChunkResult objects
        """
        if not text.strip():
            return []

        # If text fits in one chunk, return as-is
        total_tokens = count_tokens(text)
        if total_tokens <= self.target_size:
            return [
                ChunkResult(
                    content=text.strip(),
                    start_index=0,
                    end_index=len(text),
                    metadata={"tokens": total_tokens},
                )
            ]

        # Split by semantic boundaries
        segments = self._split_by_boundaries(text)

        # Merge segments into chunks
        chunks = self._merge_segments(segments)

        return chunks

    def _split_by_boundaries(self, text: str) -> list[tuple[str, int, int]]:
        """Split text by semantic boundaries (paragraphs, headers, code blocks).

        Returns list of (content, start_index, end_index) tuples.
        """
        segments = []

        # First, extract code blocks as they should stay intact
        code_block_pattern = re.compile(r"```[\s\S]*?```", re.MULTILINE)
        current_pos = 0
        temp_segments = []

        for match in code_block_pattern.finditer(text):
            # Add text before code block
            if match.start() > current_pos:
                temp_segments.append((text[current_pos : match.start()], False))

            # Add code block (marked as non-splittable)
            temp_segments.append((match.group(), True))
            current_pos = match.end()

        # Add remaining text
        if current_pos < len(text):
            temp_segments.append((text[current_pos:], False))

        # Now split non-code segments by paragraphs
        current_index = 0
        for segment, is_code in temp_segments:
            if is_code:
                # Keep code blocks intact
                segments.append((segment, current_index, current_index + len(segment)))
                current_index += len(segment)
            else:
                # Split by double newlines (paragraphs)
                para_pattern = re.compile(r"\n\n+")
                para_pos = 0
                for match in para_pattern.finditer(segment):
                    if match.start() > para_pos:
                        para = segment[para_pos : match.start()]
                        if para.strip():
                            segments.append(
                                (
                                    para,
                                    current_index + para_pos,
                                    current_index + match.start(),
                                )
                            )
                    para_pos = match.end()

                # Add remaining text
                if para_pos < len(segment):
                    remaining = segment[para_pos:]
                    if remaining.strip():
                        segments.append(
                            (
                                remaining,
                                current_index + para_pos,
                                current_index + len(segment),
                            )
                        )

                current_index += len(segment)

        return segments

    def _merge_segments(
        self, segments: list[tuple[str, int, int]]
    ) -> list[ChunkResult]:
        """Merge segments into chunks respecting size limits."""
        if not segments:
            return []

        chunks = []
        current_content = ""
        current_start = 0
        current_tokens = 0

        for content, start, end in segments:
            segment_tokens = count_tokens(content)

            # If segment alone exceeds max size, split it
            if segment_tokens > self.max_size:
                # Save current chunk if any
                if current_content.strip():
                    chunks.append(
                        ChunkResult(
                            content=current_content.strip(),
                            start_index=current_start,
                            end_index=start,
                            metadata={"tokens": current_tokens},
                        )
                    )

                # Split large segment by sentences
                sub_chunks = self._split_large_segment(content, start)
                chunks.extend(sub_chunks)

                current_content = ""
                current_start = end
                current_tokens = 0
                continue

            # Check if adding this segment exceeds target
            if current_tokens + segment_tokens > self.target_size:
                # Save current chunk if it meets minimum size
                if current_tokens >= self.min_size:
                    chunks.append(
                        ChunkResult(
                            content=current_content.strip(),
                            start_index=current_start,
                            end_index=start,
                            metadata={"tokens": current_tokens},
                        )
                    )

                    # Start new chunk with overlap
                    if self.overlap > 0 and current_content:
                        overlap_text = self._get_overlap_text(current_content)
                        current_content = overlap_text + "\n\n" + content
                        current_start = start - len(overlap_text)
                        current_tokens = count_tokens(current_content)
                    else:
                        current_content = content
                        current_start = start
                        current_tokens = segment_tokens
                else:
                    # Current chunk too small, keep adding
                    current_content += "\n\n" + content
                    current_tokens += segment_tokens
            else:
                # Add to current chunk
                if current_content:
                    current_content += "\n\n" + content
                else:
                    current_content = content
                    current_start = start
                current_tokens += segment_tokens

        # Add final chunk
        if current_content.strip():
            chunks.append(
                ChunkResult(
                    content=current_content.strip(),
                    start_index=current_start,
                    end_index=len(segments[-1][0]) if segments else 0,
                    metadata={"tokens": current_tokens},
                )
            )

        return chunks

    def _split_large_segment(
        self, content: str, start_index: int
    ) -> list[ChunkResult]:
        """Split a large segment by sentences."""
        chunks = []

        # Split by sentence-ending punctuation
        sentences = re.split(r"(?<=[.!?])\s+", content)

        current_content = ""
        current_start = start_index
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = count_tokens(sentence)

            if current_tokens + sentence_tokens > self.target_size:
                if current_content.strip():
                    chunks.append(
                        ChunkResult(
                            content=current_content.strip(),
                            start_index=current_start,
                            end_index=current_start + len(current_content),
                            metadata={"tokens": current_tokens},
                        )
                    )

                current_content = sentence
                current_start += len(current_content)
                current_tokens = sentence_tokens
            else:
                current_content += " " + sentence if current_content else sentence
                current_tokens += sentence_tokens

        if current_content.strip():
            chunks.append(
                ChunkResult(
                    content=current_content.strip(),
                    start_index=current_start,
                    end_index=current_start + len(current_content),
                    metadata={"tokens": current_tokens},
                )
            )

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of a chunk."""
        # Get last few sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        overlap_text = ""
        overlap_tokens = 0

        for sentence in reversed(sentences):
            sentence_tokens = count_tokens(sentence)
            if overlap_tokens + sentence_tokens > self.overlap:
                break
            overlap_text = sentence + " " + overlap_text
            overlap_tokens += sentence_tokens

        return overlap_text.strip()
