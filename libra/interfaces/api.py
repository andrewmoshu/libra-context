"""REST API for libra using FastAPI.

Provides HTTP endpoints for programmatic access to libra:
- Context CRUD operations
- Query for relevant context
- Search contexts
- Ingestion
- Audit log
- System stats and configuration
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from libra.core.config import LibraConfig
from libra.core.exceptions import ContextNotFoundError
from libra.core.models import ContextType, LibrarianMode, RequestSource
from libra.service import LibraService

# API Models


class ContextCreate(BaseModel):
    """Request model for creating a context."""

    content: str = Field(..., min_length=1, description="The context content")
    type: str = Field(default="knowledge", description="Context type")
    tags: list[str] = Field(default_factory=list, description="Tags for organization")
    source: str = Field(default="api", description="Source identifier")


class ContextUpdate(BaseModel):
    """Request model for updating a context."""

    content: Optional[str] = None
    tags: Optional[list[str]] = None


class ContextResponse(BaseModel):
    """Response model for a context."""

    id: str
    type: str
    content: str
    tags: list[str]
    source: str
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime]
    access_count: int


class QueryRequest(BaseModel):
    """Request model for context query."""

    task: str = Field(..., min_length=1, description="Task description")
    max_tokens: int = Field(default=2000, ge=100, le=10000, description="Token budget")
    types: Optional[list[str]] = Field(default=None, description="Filter by types")
    tags: Optional[list[str]] = Field(default=None, description="Filter by tags")


class ScoredContextResponse(BaseModel):
    """Response model for a scored context."""

    id: str
    type: str
    content: str
    relevance: float
    tags: list[str]


class QueryResponse(BaseModel):
    """Response model for context query."""

    contexts: list[ScoredContextResponse]
    tokens_used: int
    request_id: str
    librarian_mode: str


class SearchResult(BaseModel):
    """Response model for search result."""

    id: str
    type: str
    content: str
    similarity: float
    tags: list[str]


class IngestTextRequest(BaseModel):
    """Request model for text ingestion."""

    content: str = Field(..., min_length=1)
    type: str = Field(default="knowledge")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="api")


class IngestDirectoryRequest(BaseModel):
    """Request model for directory ingestion."""

    path: str = Field(..., description="Path to directory")
    type: str = Field(default="knowledge")
    tags: list[str] = Field(default_factory=list)


class AuditEntryResponse(BaseModel):
    """Response model for audit entry."""

    id: str
    timestamp: datetime
    agent_id: Optional[str]
    task: str
    contexts_served: int
    tokens_used: int
    tokens_budget: int
    latency_ms: int


class StatsResponse(BaseModel):
    """Response model for statistics."""

    total_contexts: int
    contexts_with_embeddings: int
    total_audit_entries: int
    contexts_by_type: dict[str, int]


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    db_path: str


# Create FastAPI app
app = FastAPI(
    title="libra API",
    description="Intelligent Context Orchestration for AI Agents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Global service instance
_service: LibraService | None = None


def get_service() -> LibraService:
    """Get or create the service instance."""
    global _service
    if _service is None:
        _service = LibraService()
    return _service


# CORS middleware (disabled by default, can be enabled in config)
def setup_cors(config: LibraConfig) -> None:
    """Setup CORS if enabled in config."""
    if config.server.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


# Context Endpoints


@app.get("/api/v1/contexts", response_model=list[ContextResponse], tags=["Contexts"])
def list_contexts(
    type: Optional[str] = Query(None, description="Filter by type"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[ContextResponse]:
    """List contexts with optional filtering."""
    service = get_service()

    type_list = None
    if type:
        try:
            type_list = [ContextType(type.lower())]
        except ValueError:
            raise HTTPException(400, f"Invalid type: {type}")

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    contexts = service.list_contexts(types=type_list, tags=tag_list, limit=limit, offset=offset)

    return [
        ContextResponse(
            id=str(c.id),
            type=c.type,
            content=c.content,
            tags=c.tags,
            source=c.source,
            created_at=c.created_at,
            updated_at=c.updated_at,
            accessed_at=c.accessed_at,
            access_count=c.access_count,
        )
        for c in contexts
    ]


@app.post("/api/v1/contexts", response_model=ContextResponse, status_code=201, tags=["Contexts"])
def create_context(request: ContextCreate) -> ContextResponse:
    """Create a new context."""
    service = get_service()

    try:
        context_type = ContextType(request.type.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid type: {request.type}")

    context = service.add_context(
        content=request.content,
        context_type=context_type,
        tags=request.tags,
        source=request.source,
    )

    return ContextResponse(
        id=str(context.id),
        type=context.type,
        content=context.content,
        tags=context.tags,
        source=context.source,
        created_at=context.created_at,
        updated_at=context.updated_at,
        accessed_at=context.accessed_at,
        access_count=context.access_count,
    )


@app.get("/api/v1/contexts/{context_id}", response_model=ContextResponse, tags=["Contexts"])
def get_context(context_id: str) -> ContextResponse:
    """Get a specific context by ID."""
    service = get_service()

    try:
        context = service.get_context(context_id)
    except ContextNotFoundError:
        raise HTTPException(404, f"Context not found: {context_id}")

    return ContextResponse(
        id=str(context.id),
        type=context.type,
        content=context.content,
        tags=context.tags,
        source=context.source,
        created_at=context.created_at,
        updated_at=context.updated_at,
        accessed_at=context.accessed_at,
        access_count=context.access_count,
    )


@app.put("/api/v1/contexts/{context_id}", response_model=ContextResponse, tags=["Contexts"])
def update_context(context_id: str, request: ContextUpdate) -> ContextResponse:
    """Update an existing context."""
    service = get_service()

    try:
        context = service.update_context(
            context_id=context_id,
            content=request.content,
            tags=request.tags,
        )
    except ContextNotFoundError:
        raise HTTPException(404, f"Context not found: {context_id}")

    return ContextResponse(
        id=str(context.id),
        type=context.type,
        content=context.content,
        tags=context.tags,
        source=context.source,
        created_at=context.created_at,
        updated_at=context.updated_at,
        accessed_at=context.accessed_at,
        access_count=context.access_count,
    )


@app.delete("/api/v1/contexts/{context_id}", status_code=204, tags=["Contexts"])
def delete_context(context_id: str) -> None:
    """Delete a context by ID."""
    service = get_service()

    deleted = service.delete_context(context_id)
    if not deleted:
        raise HTTPException(404, f"Context not found: {context_id}")


# Query Endpoints


@app.post("/api/v1/query", response_model=QueryResponse, tags=["Query"])
def query_context(request: QueryRequest) -> QueryResponse:
    """Get relevant context for a task.

    This is the main feature of libra - intelligent context selection.
    """
    service = get_service()

    type_list = None
    if request.types:
        try:
            type_list = [ContextType(t.lower()) for t in request.types]
        except ValueError as e:
            raise HTTPException(400, f"Invalid type: {e}")

    response = service.query(
        task=request.task,
        max_tokens=request.max_tokens,
        types=type_list,
        tags=request.tags,
        request_source=RequestSource.API,
    )

    return QueryResponse(
        contexts=[
            ScoredContextResponse(
                id=str(sc.context.id),
                type=sc.context.type,
                content=sc.context.content,
                relevance=sc.relevance_score,
                tags=sc.context.tags,
            )
            for sc in response.contexts
        ],
        tokens_used=response.tokens_used,
        request_id=str(response.request_id),
        librarian_mode=response.librarian_mode,
    )


@app.post("/api/v1/search", response_model=list[SearchResult], tags=["Query"])
def search_contexts(
    query: str = Query(..., min_length=1, description="Search query"),
    type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
) -> list[SearchResult]:
    """Search contexts by semantic similarity."""
    service = get_service()

    type_list = None
    if type:
        try:
            type_list = [ContextType(type.lower())]
        except ValueError:
            raise HTTPException(400, f"Invalid type: {type}")

    results = service.search_contexts(query=query, types=type_list, limit=limit)

    return [
        SearchResult(
            id=str(ctx.id),
            type=ctx.type,
            content=ctx.content,
            similarity=score,
            tags=ctx.tags,
        )
        for ctx, score in results
    ]


# Ingestion Endpoints


@app.post("/api/v1/ingest/text", response_model=list[ContextResponse], tags=["Ingestion"])
def ingest_text(request: IngestTextRequest) -> list[ContextResponse]:
    """Ingest raw text content."""
    service = get_service()

    try:
        context_type = ContextType(request.type.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid type: {request.type}")

    contexts = service.ingest_text(
        content=request.content,
        context_type=context_type,
        tags=request.tags,
        source=request.source,
    )

    return [
        ContextResponse(
            id=str(c.id),
            type=c.type,
            content=c.content,
            tags=c.tags,
            source=c.source,
            created_at=c.created_at,
            updated_at=c.updated_at,
            accessed_at=c.accessed_at,
            access_count=c.access_count,
        )
        for c in contexts
    ]


@app.post("/api/v1/ingest/file", response_model=list[ContextResponse], tags=["Ingestion"])
async def ingest_file(
    file: UploadFile = File(...),
    type: str = Query("knowledge", description="Context type"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
) -> list[ContextResponse]:
    """Ingest an uploaded file."""
    import re
    import tempfile

    service = get_service()

    try:
        context_type = ContextType(type.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid type: {type}")

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Sanitize file extension to prevent path traversal or injection
    filename = file.filename or "file.txt"
    # Extract only alphanumeric extension, max 10 chars
    suffix_match = re.search(r'\.([a-zA-Z0-9]{1,10})$', filename)
    suffix = f".{suffix_match.group(1)}" if suffix_match else ".txt"

    # Save to temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        contexts = service.ingest_file(tmp_path, context_type, tag_list)
    except Exception as e:
        raise HTTPException(500, f"Failed to ingest file: {str(e)}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()

    return [
        ContextResponse(
            id=str(c.id),
            type=c.type,
            content=c.content,
            tags=c.tags,
            source=c.source,
            created_at=c.created_at,
            updated_at=c.updated_at,
            accessed_at=c.accessed_at,
            access_count=c.access_count,
        )
        for c in contexts
    ]


@app.post("/api/v1/ingest/directory", response_model=dict, tags=["Ingestion"])
def ingest_directory(request: IngestDirectoryRequest) -> dict[str, object]:
    """Ingest a local directory."""
    service = get_service()

    path = Path(request.path)
    if not path.exists():
        raise HTTPException(400, f"Directory does not exist: {request.path}")
    if not path.is_dir():
        raise HTTPException(400, f"Path is not a directory: {request.path}")

    try:
        context_type = ContextType(request.type.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid type: {request.type}")

    contexts = service.ingest_directory(path, context_type, request.tags)

    return {
        "success": True,
        "contexts_created": len(contexts),
        "source": str(path),
    }


# Audit Endpoints


@app.get("/api/v1/audit", response_model=list[AuditEntryResponse], tags=["Audit"])
def get_audit_log(
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[AuditEntryResponse]:
    """Get audit log entries."""
    service = get_service()

    entries = service.get_audit_log(agent_id=agent_id, limit=limit, offset=offset)

    return [
        AuditEntryResponse(
            id=str(e.id),
            timestamp=e.timestamp,
            agent_id=e.agent_id,
            task=e.task,
            contexts_served=len(e.contexts_served),
            tokens_used=e.tokens_used,
            tokens_budget=e.tokens_budget,
            latency_ms=e.latency_ms,
        )
        for e in entries
    ]


@app.get("/api/v1/audit/stats", response_model=dict, tags=["Audit"])
def get_audit_stats() -> dict[str, int]:
    """Get audit statistics."""
    service = get_service()
    stats = service.get_stats()

    return {
        "total_queries": stats.get("total_audit_entries", 0),
    }


# System Endpoints


@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Health check endpoint."""
    service = get_service()

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        db_path=str(service.config.db_path),
    )


@app.get("/api/v1/stats", response_model=StatsResponse, tags=["System"])
def get_stats() -> StatsResponse:
    """Get storage statistics."""
    service = get_service()
    stats = service.get_stats()

    return StatsResponse(
        total_contexts=stats.get("total_contexts", 0),
        contexts_with_embeddings=stats.get("contexts_with_embeddings", 0),
        total_audit_entries=stats.get("total_audit_entries", 0),
        contexts_by_type=stats.get("contexts_by_type", {}),
    )


@app.get("/api/v1/config", response_model=dict, tags=["System"])
def get_config() -> dict[str, object]:
    """Get current configuration (safe fields only)."""
    service = get_service()
    config = service.config

    return {
        "librarian_mode": config.librarian.mode,
        "embedding_provider": config.embedding.provider,
        "embedding_model": config.embedding.model,
        "default_token_budget": config.defaults.token_budget,
        "default_chunk_size": config.defaults.chunk_size,
    }


def create_api_app() -> FastAPI:
    """Create and return the FastAPI app."""
    return app


def run_server(host: str = "127.0.0.1", port: int = 8377) -> None:
    """Run the API server."""
    import uvicorn

    # Setup CORS if configured
    service = get_service()
    setup_cors(service.config)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
