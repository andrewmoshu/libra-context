"""SQLite storage with vector search using sqlite-vec."""

import json
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

import sqlite_vec

from libra.core.exceptions import ContextNotFoundError, StorageError
from libra.core.models import (
    AuditEntry,
    Context,
    ContextType,
    LibrarianMode,
    RequestSource,
)


def serialize_float32(vector: list[float]) -> bytes:
    """Serialize a list of floats to bytes for sqlite-vec."""
    return struct.pack(f"{len(vector)}f", *vector)


def deserialize_float32(data: bytes) -> list[float]:
    """Deserialize bytes back to a list of floats."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


class ContextStore:
    """SQLite-based storage with vector search capabilities."""

    def __init__(self, db_path: Path | str, vector_dimensions: int = 768):
        """Initialize the context store.

        Args:
            db_path: Path to the SQLite database file
            vector_dimensions: Dimensions of the embedding vectors
        """
        self.db_path = Path(db_path)
        self.vector_dimensions = vector_dimensions
        self._conn: sqlite3.Connection | None = None
        self._initialize_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get the database connection, creating if necessary."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
        return self._conn

    def _initialize_db(self) -> None:
        """Create database tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn.executescript(
            """
            -- Contexts table
            CREATE TABLE IF NOT EXISTS contexts (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,  -- JSON array
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                metadata TEXT NOT NULL  -- JSON object
            );

            -- Audit log table
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_id TEXT,
                task TEXT NOT NULL,
                contexts_served TEXT NOT NULL,  -- JSON array of UUIDs
                relevance_scores TEXT NOT NULL,  -- JSON array of floats
                tokens_used INTEGER NOT NULL,
                tokens_budget INTEGER NOT NULL,
                request_source TEXT NOT NULL,
                librarian_mode TEXT NOT NULL,
                latency_ms INTEGER NOT NULL
            );

            -- Agents table
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                default_budget INTEGER NOT NULL,
                allowed_types TEXT,  -- JSON array
                created_at TEXT NOT NULL
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_contexts_type ON contexts(type);
            CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
            CREATE INDEX IF NOT EXISTS idx_contexts_accessed_at ON contexts(accessed_at);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id);
        """
        )

        # Create virtual table for vector search
        # Check if it exists first
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='context_embeddings'"
        )
        if cursor.fetchone() is None:
            self.conn.execute(
                f"""
                CREATE VIRTUAL TABLE context_embeddings USING vec0(
                    context_id TEXT PRIMARY KEY,
                    embedding float[{self.vector_dimensions}]
                )
            """
            )

        self.conn.commit()

    def add_context(self, context: Context) -> None:
        """Add a context to the store."""
        try:
            self.conn.execute(
                """
                INSERT INTO contexts (id, type, content, tags, source, created_at,
                                      updated_at, accessed_at, access_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(context.id),
                    context.type,
                    context.content,
                    json.dumps(context.tags),
                    context.source,
                    context.created_at.isoformat(),
                    context.updated_at.isoformat(),
                    context.accessed_at.isoformat() if context.accessed_at else None,
                    context.access_count,
                    json.dumps(context.metadata),
                ),
            )

            # Add embedding if present
            if context.embedding:
                self.conn.execute(
                    """
                    INSERT INTO context_embeddings (context_id, embedding)
                    VALUES (?, ?)
                """,
                    (str(context.id), serialize_float32(context.embedding)),
                )

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise StorageError(f"Failed to add context: {e}")

    def get_context(self, context_id: UUID | str) -> Context:
        """Get a context by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM contexts WHERE id = ?", (str(context_id),)
        )
        row = cursor.fetchone()

        if row is None:
            raise ContextNotFoundError(str(context_id))

        return self._row_to_context(row)

    def update_context(self, context: Context) -> None:
        """Update an existing context."""
        try:
            self.conn.execute(
                """
                UPDATE contexts SET
                    type = ?, content = ?, tags = ?, source = ?,
                    updated_at = ?, accessed_at = ?, access_count = ?, metadata = ?
                WHERE id = ?
            """,
                (
                    context.type,
                    context.content,
                    json.dumps(context.tags),
                    context.source,
                    context.updated_at.isoformat(),
                    context.accessed_at.isoformat() if context.accessed_at else None,
                    context.access_count,
                    json.dumps(context.metadata),
                    str(context.id),
                ),
            )

            # Update embedding if present
            if context.embedding:
                # Delete old embedding
                self.conn.execute(
                    "DELETE FROM context_embeddings WHERE context_id = ?",
                    (str(context.id),),
                )
                # Insert new embedding
                self.conn.execute(
                    """
                    INSERT INTO context_embeddings (context_id, embedding)
                    VALUES (?, ?)
                """,
                    (str(context.id), serialize_float32(context.embedding)),
                )

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise StorageError(f"Failed to update context: {e}")

    def delete_context(self, context_id: UUID | str) -> bool:
        """Delete a context by ID. Returns True if deleted."""
        try:
            # Delete embedding first
            self.conn.execute(
                "DELETE FROM context_embeddings WHERE context_id = ?",
                (str(context_id),),
            )
            cursor = self.conn.execute(
                "DELETE FROM contexts WHERE id = ?", (str(context_id),)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise StorageError(f"Failed to delete context: {e}")

    def list_contexts(
        self,
        types: list[ContextType] | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Context]:
        """List contexts with optional filtering."""
        query = "SELECT * FROM contexts WHERE 1=1"
        params: list = []

        if types:
            placeholders = ",".join("?" for _ in types)
            query += f" AND type IN ({placeholders})"
            params.extend(types)

        if tags:
            # Match any of the tags
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            query += f" AND ({' OR '.join(tag_conditions)})"

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(query, params)
        return [self._row_to_context(row) for row in cursor.fetchall()]

    def search_by_embedding(
        self,
        query_embedding: list[float],
        limit: int = 50,
        types: list[ContextType] | None = None,
        tags: list[str] | None = None,
    ) -> list[tuple[Context, float]]:
        """Search contexts by embedding similarity.

        Returns list of (context, similarity_score) tuples sorted by similarity.
        """
        # First get candidate context IDs from vector search
        cursor = self.conn.execute(
            """
            SELECT context_id, distance
            FROM context_embeddings
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
        """,
            (serialize_float32(query_embedding), limit * 2),
        )

        candidates = cursor.fetchall()
        if not candidates:
            return []

        # Fetch full contexts and apply filters
        results = []
        for row in candidates:
            context_id = row[0]
            distance = row[1]

            # Convert distance to similarity (assuming cosine distance)
            # sqlite-vec uses L2 distance by default, so we use 1 / (1 + distance)
            similarity = 1 / (1 + distance)

            try:
                context = self.get_context(context_id)

                # Apply type filter
                if types and context.type not in types:
                    continue

                # Apply tag filter
                if tags and not any(tag in context.tags for tag in tags):
                    continue

                results.append((context, similarity))

                if len(results) >= limit:
                    break
            except ContextNotFoundError:
                continue

        return results

    def search_by_text(
        self,
        query: str,
        limit: int = 50,
        types: list[ContextType] | None = None,
    ) -> list[Context]:
        """Search contexts by text content (simple LIKE matching)."""
        sql = "SELECT * FROM contexts WHERE content LIKE ?"
        params: list = [f"%{query}%"]

        if types:
            placeholders = ",".join("?" for _ in types)
            sql += f" AND type IN ({placeholders})"
            params.extend(types)

        sql += " ORDER BY access_count DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(sql, params)
        return [self._row_to_context(row) for row in cursor.fetchall()]

    def record_access(self, context_ids: list[UUID | str]) -> None:
        """Record access to contexts (updates accessed_at and access_count)."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            for context_id in context_ids:
                self.conn.execute(
                    """
                    UPDATE contexts
                    SET accessed_at = ?, access_count = access_count + 1
                    WHERE id = ?
                """,
                    (now, str(context_id)),
                )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise StorageError(f"Failed to record access: {e}")

    def add_audit_entry(self, entry: AuditEntry) -> None:
        """Add an audit log entry."""
        try:
            self.conn.execute(
                """
                INSERT INTO audit_log (id, timestamp, agent_id, task, contexts_served,
                                       relevance_scores, tokens_used, tokens_budget,
                                       request_source, librarian_mode, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(entry.id),
                    entry.timestamp.isoformat(),
                    entry.agent_id,
                    entry.task,
                    json.dumps([str(c) for c in entry.contexts_served]),
                    json.dumps(entry.relevance_scores),
                    entry.tokens_used,
                    entry.tokens_budget,
                    entry.request_source,
                    entry.librarian_mode,
                    entry.latency_ms,
                ),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise StorageError(f"Failed to add audit entry: {e}")

    def get_audit_entries(
        self,
        agent_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Get audit log entries."""
        query = "SELECT * FROM audit_log"
        params: list = []

        if agent_id:
            query += " WHERE agent_id = ?"
            params.append(agent_id)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(query, params)
        return [self._row_to_audit_entry(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """Get storage statistics."""
        stats = {}

        # Context counts by type
        cursor = self.conn.execute(
            "SELECT type, COUNT(*) as count FROM contexts GROUP BY type"
        )
        stats["contexts_by_type"] = {row["type"]: row["count"] for row in cursor}

        # Total contexts
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM contexts")
        stats["total_contexts"] = cursor.fetchone()["count"]

        # Total audit entries
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM audit_log")
        stats["total_audit_entries"] = cursor.fetchone()["count"]

        # Contexts with embeddings
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM context_embeddings"
        )
        stats["contexts_with_embeddings"] = cursor.fetchone()["count"]

        return stats

    def iter_contexts(self) -> Iterator[Context]:
        """Iterate over all contexts (memory-efficient for large datasets)."""
        cursor = self.conn.execute("SELECT * FROM contexts ORDER BY created_at")
        for row in cursor:
            yield self._row_to_context(row)

    def _row_to_context(self, row: sqlite3.Row) -> Context:
        """Convert a database row to a Context object."""
        # Get embedding if exists
        embedding = None
        cursor = self.conn.execute(
            "SELECT embedding FROM context_embeddings WHERE context_id = ?",
            (row["id"],),
        )
        embed_row = cursor.fetchone()
        if embed_row:
            embedding = deserialize_float32(embed_row["embedding"])

        return Context(
            id=UUID(row["id"]),
            type=ContextType(row["type"]),
            content=row["content"],
            tags=json.loads(row["tags"]),
            source=row["source"],
            embedding=embedding,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            accessed_at=(
                datetime.fromisoformat(row["accessed_at"])
                if row["accessed_at"]
                else None
            ),
            access_count=row["access_count"],
            metadata=json.loads(row["metadata"]),
        )

    def _row_to_audit_entry(self, row: sqlite3.Row) -> AuditEntry:
        """Convert a database row to an AuditEntry object."""
        return AuditEntry(
            id=UUID(row["id"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            agent_id=row["agent_id"],
            task=row["task"],
            contexts_served=[UUID(c) for c in json.loads(row["contexts_served"])],
            relevance_scores=json.loads(row["relevance_scores"]),
            tokens_used=row["tokens_used"],
            tokens_budget=row["tokens_budget"],
            request_source=RequestSource(row["request_source"]),
            librarian_mode=LibrarianMode(row["librarian_mode"]),
            latency_ms=row["latency_ms"],
        )

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
