"""Main LibraService orchestrator for libra.

Coordinates all components to provide a unified interface for
context storage, retrieval, and intelligent selection.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from libra.core.config import LibraConfig

logger = logging.getLogger("libra.service")
from libra.core.exceptions import LibraError
from libra.core.models import (
    AuditEntry,
    Context,
    ContextRequest,
    ContextResponse,
    ContextType,
    LibrarianMode,
    RequestSource,
    ScoredContext,
)
from libra.embedding.base import EmbeddingProvider
from libra.embedding.gemini import GeminiEmbeddingProvider
from libra.ingestion.chunker import Chunker
from libra.ingestion.directory import DirectoryIngestor
from libra.ingestion.markdown import MarkdownIngestor
from libra.ingestion.text import TextIngestor
from libra.librarian.base import Librarian
from libra.librarian.budget import BudgetManager
from libra.librarian.hybrid import create_librarian
from libra.storage.database import ContextStore


class LibraService:
    """Main service class that orchestrates all libra components.

    Provides a unified interface for:
    - Adding and managing contexts
    - Querying for relevant contexts
    - Ingesting files and directories
    - Configuration management
    """

    def __init__(
        self,
        config: LibraConfig | None = None,
        config_path: Path | None = None,
    ):
        """Initialize the libra service.

        Args:
            config: Configuration object (loads from file if None)
            config_path: Path to config file (uses default if None)
        """
        # Load or use provided configuration
        if config is not None:
            self.config = config
        else:
            self.config = LibraConfig.load(config_path)

        # Ensure data directory exists
        self.config.ensure_data_dir()
        logger.info(f"LibraService initialized with data_dir={self.config.data_dir}")

        # Initialize components
        self._store: ContextStore | None = None
        self._embedding_provider: EmbeddingProvider | None = None
        self._librarian: Librarian | None = None
        self._budget_manager: BudgetManager | None = None
        self._chunker: Chunker | None = None

        # Ingestors
        self._text_ingestor: TextIngestor | None = None
        self._markdown_ingestor: MarkdownIngestor | None = None
        self._directory_ingestor: DirectoryIngestor | None = None

    @property
    def store(self) -> ContextStore:
        """Get the context store, initializing if needed."""
        if self._store is None:
            self._store = ContextStore(
                self.config.db_path,
                vector_dimensions=self.config.embedding.dimensions,
            )
        return self._store

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """Get the embedding provider, initializing if needed."""
        if self._embedding_provider is None:
            if self.config.embedding.provider == "gemini":
                self._embedding_provider = GeminiEmbeddingProvider(
                    model=f"models/{self.config.embedding.model}",
                    output_dimensionality=self.config.embedding.dimensions,
                )
            else:
                raise LibraError(
                    f"Unknown embedding provider: {self.config.embedding.provider}"
                )
        return self._embedding_provider

    @property
    def librarian(self) -> Librarian:
        """Get the librarian, initializing if needed."""
        if self._librarian is None:
            self._librarian = create_librarian(
                mode=self.config.librarian.mode.value,
                rules=self.config.librarian.rules or LibraConfig.default_rules(),
                gemini_model=self.config.librarian.llm.model,
            )
        return self._librarian

    @property
    def budget_manager(self) -> BudgetManager:
        """Get the budget manager, initializing if needed."""
        if self._budget_manager is None:
            self._budget_manager = BudgetManager(
                default_budget=self.config.defaults.token_budget,
            )
        return self._budget_manager

    @property
    def chunker(self) -> Chunker:
        """Get the chunker, initializing if needed."""
        if self._chunker is None:
            self._chunker = Chunker(
                target_size=self.config.defaults.chunk_size,
            )
        return self._chunker

    # Context Management

    def add_context(
        self,
        content: str,
        context_type: ContextType | str = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
        source: str = "manual",
        generate_embedding: bool = True,
    ) -> Context:
        """Add a new context to the store.

        Args:
            content: The context content
            context_type: Type of context (knowledge, preference, history)
            tags: Tags to apply
            source: Source identifier
            generate_embedding: Whether to generate embedding

        Returns:
            The created Context object
        """
        if isinstance(context_type, str):
            context_type = ContextType(context_type)

        context = Context(
            type=context_type,
            content=content,
            tags=tags or [],
            source=source,
        )

        if generate_embedding:
            context.embedding = self.embedding_provider.embed_document(content)

        self.store.add_context(context)
        logger.debug(f"Added context {context.id} of type {context.type}")
        return context

    def get_context(self, context_id: UUID | str) -> Context:
        """Get a context by ID.

        Args:
            context_id: UUID of the context

        Returns:
            The Context object
        """
        return self.store.get_context(context_id)

    def update_context(
        self,
        context_id: UUID | str,
        content: str | None = None,
        tags: list[str] | None = None,
        regenerate_embedding: bool = True,
    ) -> Context:
        """Update an existing context.

        Args:
            context_id: UUID of the context
            content: New content (optional)
            tags: New tags (optional)
            regenerate_embedding: Whether to regenerate embedding

        Returns:
            The updated Context object
        """
        context = self.store.get_context(context_id)

        if content is not None:
            context.update_content(content)
            if regenerate_embedding:
                context.embedding = self.embedding_provider.embed_document(content)

        if tags is not None:
            context.tags = tags

        self.store.update_context(context)
        return context

    def delete_context(self, context_id: UUID | str) -> bool:
        """Delete a context by ID.

        Args:
            context_id: UUID of the context

        Returns:
            True if deleted
        """
        return self.store.delete_context(context_id)

    def list_contexts(
        self,
        types: list[ContextType] | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Context]:
        """List contexts with optional filtering.

        Args:
            types: Filter by context types
            tags: Filter by tags
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Context objects
        """
        return self.store.list_contexts(types, tags, limit, offset)

    def search_contexts(
        self,
        query: str,
        types: list[ContextType] | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[tuple[Context, float]]:
        """Search contexts by semantic similarity.

        Args:
            query: Search query
            types: Filter by context types
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of (Context, similarity_score) tuples
        """
        query_embedding = self.embedding_provider.embed_query(query)
        return self.store.search_by_embedding(query_embedding, limit, types, tags)

    # Context Query (Main Feature)

    def query(
        self,
        task: str,
        max_tokens: int | None = None,
        types: list[ContextType] | None = None,
        tags: list[str] | None = None,
        agent_id: str | None = None,
        request_source: RequestSource = RequestSource.API,
    ) -> ContextResponse:
        """Get relevant context for a task.

        This is the main feature of libra - intelligent context selection.

        Args:
            task: Task description
            max_tokens: Token budget (uses default if None)
            types: Filter by context types
            tags: Filter by tags
            agent_id: Requesting agent identifier
            request_source: Source of the request

        Returns:
            ContextResponse with selected contexts
        """
        start_time = time.time()

        if max_tokens is None:
            max_tokens = self.config.defaults.token_budget

        # Create request object
        request = ContextRequest(
            task=task,
            max_tokens=max_tokens,
            types=types,
            tags=tags,
            agent_id=agent_id,
        )

        # Step 1: Get candidate contexts via embedding similarity
        query_embedding = self.embedding_provider.embed_query(task)
        candidates_with_scores = self.store.search_by_embedding(
            query_embedding,
            limit=100,
            types=types,
            tags=tags,
        )
        candidates = [ctx for ctx, _ in candidates_with_scores]

        # Step 2: Use Librarian to score and rank candidates
        scored_contexts = self.librarian.select(request, candidates)

        # Step 3: Optimize for token budget
        selected, tokens_used = self.budget_manager.optimize(
            scored_contexts, max_tokens
        )

        # Step 4: Record access
        context_uuids: list[UUID] = [sc.context.id for sc in selected]
        if context_uuids:
            # Convert to list that accepts UUID | str for record_access
            ids_for_access: list[UUID | str] = list(context_uuids)
            self.store.record_access(ids_for_access)

        # Step 5: Create response
        response = ContextResponse(
            contexts=selected,
            tokens_used=tokens_used,
            librarian_mode=self.config.librarian.mode,
        )

        # Step 6: Log audit entry
        latency_ms = int((time.time() - start_time) * 1000)
        audit_entry = AuditEntry(
            agent_id=agent_id,
            task=task,
            contexts_served=context_uuids,
            relevance_scores=[sc.relevance_score for sc in selected],
            tokens_used=tokens_used,
            tokens_budget=max_tokens,
            request_source=request_source,
            librarian_mode=self.config.librarian.mode,
            latency_ms=latency_ms,
        )
        self.store.add_audit_entry(audit_entry)

        logger.info(
            f"Query completed: task='{task[:50]}...' contexts={len(selected)} "
            f"tokens={tokens_used}/{max_tokens} latency={latency_ms}ms"
        )
        return response

    # Ingestion

    def ingest_text(
        self,
        content: str,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
        source: str = "manual",
    ) -> list[Context]:
        """Ingest raw text content.

        Args:
            content: Text content to ingest
            context_type: Type to assign
            tags: Tags to apply
            source: Source identifier

        Returns:
            List of created Context objects
        """
        if self._text_ingestor is None:
            self._text_ingestor = TextIngestor(chunker=self.chunker)

        contexts = self._text_ingestor.ingest_raw(content, context_type, tags, source)

        # Generate embeddings and store
        for ctx in contexts:
            ctx.embedding = self.embedding_provider.embed_document(ctx.content)
            self.store.add_context(ctx)

        return contexts

    def ingest_file(
        self,
        path: Path | str,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
    ) -> list[Context]:
        """Ingest a file.

        Args:
            path: Path to file
            context_type: Type to assign
            tags: Tags to apply

        Returns:
            List of created Context objects
        """
        path = Path(path)

        if path.suffix.lower() in [".md", ".markdown"]:
            if self._markdown_ingestor is None:
                self._markdown_ingestor = MarkdownIngestor(chunker=self.chunker)
            contexts = self._markdown_ingestor.ingest(path, context_type, tags)
        else:
            if self._text_ingestor is None:
                self._text_ingestor = TextIngestor(chunker=self.chunker)
            contexts = self._text_ingestor.ingest(path, context_type, tags)

        # Generate embeddings and store
        for ctx in contexts:
            ctx.embedding = self.embedding_provider.embed_document(ctx.content)
            self.store.add_context(ctx)

        return contexts

    def ingest_directory(
        self,
        path: Path | str,
        context_type: ContextType = ContextType.KNOWLEDGE,
        tags: list[str] | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> list[Context]:
        """Ingest a directory recursively.

        Args:
            path: Path to directory
            context_type: Type to assign
            tags: Tags to apply
            progress_callback: Optional callback(file_path, current, total)

        Returns:
            List of created Context objects
        """
        if self._directory_ingestor is None:
            self._directory_ingestor = DirectoryIngestor(chunker=self.chunker)

        contexts = self._directory_ingestor.ingest(
            path, context_type, tags, progress_callback
        )

        # Generate embeddings and store
        for ctx in contexts:
            ctx.embedding = self.embedding_provider.embed_document(ctx.content)
            self.store.add_context(ctx)

        return contexts

    # Audit and Stats

    def get_audit_log(
        self,
        agent_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Get audit log entries.

        Args:
            agent_id: Filter by agent
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of AuditEntry objects
        """
        return self.store.get_audit_entries(agent_id, limit, offset)

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary of statistics
        """
        return self.store.get_stats()

    # Lifecycle

    def close(self) -> None:
        """Close all resources."""
        if self._store is not None:
            self._store.close()
            self._store = None

    def __enter__(self) -> "LibraService":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Convenience function for quick access
def get_service(config_path: Path | None = None) -> LibraService:
    """Get a LibraService instance.

    Args:
        config_path: Optional path to config file

    Returns:
        LibraService instance
    """
    return LibraService(config_path=config_path)
