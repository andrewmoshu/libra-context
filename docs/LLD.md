# libra - Low-Level Design (LLD)

## 1. Module Structure

```
libra/
├── __init__.py              # Package exports and version
├── service.py               # Main LibraService orchestrator
├── core/
│   ├── __init__.py
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Configuration management
│   └── exceptions.py        # Custom exceptions
├── storage/
│   ├── __init__.py
│   └── database.py          # SQLite + sqlite-vec implementation
├── embedding/
│   ├── __init__.py
│   ├── base.py              # Abstract embedding provider
│   └── gemini.py            # Gemini embedding implementation
├── librarian/
│   ├── __init__.py
│   ├── base.py              # Abstract Librarian interface
│   ├── rules.py             # Rules-based selection
│   ├── llm.py               # Gemini LLM-based selection
│   ├── hybrid.py            # Hybrid mode + factory
│   └── budget.py            # Token budget management
├── ingestion/
│   ├── __init__.py
│   ├── base.py              # Abstract ingestor interface
│   ├── text.py              # Plain text ingestor
│   ├── markdown.py          # Markdown ingestor
│   ├── directory.py         # Directory recursive ingestor
│   └── chunker.py           # Intelligent text chunking
├── interfaces/
│   ├── __init__.py
│   ├── cli.py               # Typer CLI application
│   ├── mcp_server.py        # MCP protocol server
│   ├── api.py               # FastAPI REST application
│   └── web/
│       ├── __init__.py
│       └── routes.py        # Web UI routes and templates
└── utils/
    ├── __init__.py
    ├── logging.py           # Logging configuration
    └── tokens.py            # Token counting utilities
```

## 2. Data Models (core/models.py)

### 2.1 Context

```python
class Context(BaseModel):
    """A discrete unit of information for AI agents."""

    id: UUID                          # Auto-generated UUID4
    type: ContextType                 # knowledge | preference | history
    content: str                      # The actual context text
    tags: list[str]                   # User-defined labels
    source: str                       # Origin: file path, "manual", URL
    embedding: Optional[list[float]]  # 768-dim vector (Gemini)
    created_at: datetime              # UTC timestamp
    updated_at: datetime              # Last modification
    accessed_at: Optional[datetime]   # Last served to agent
    access_count: int                 # Times served
    metadata: dict                    # Extensible metadata
```

### 2.2 ContextType Enum

```python
class ContextType(str, Enum):
    KNOWLEDGE = "knowledge"   # Facts, documentation, reference
    PREFERENCE = "preference" # How user likes things done
    HISTORY = "history"       # Past decisions, events
```

### 2.3 ScoredContext

```python
class ScoredContext(BaseModel):
    """Context with relevance score from Librarian."""

    context: Context
    relevance_score: float  # 0.0 to 1.0, constrained by Pydantic
```

### 2.4 ContextRequest

```python
class ContextRequest(BaseModel):
    """Request for context from an agent."""

    task: str                          # Task description
    max_tokens: int = 2000             # Token budget
    types: Optional[list[ContextType]] # Filter by type
    tags: Optional[list[str]]          # Filter by tags
    agent_id: Optional[str]            # Requesting agent
```

### 2.5 ContextResponse

```python
class ContextResponse(BaseModel):
    """Response containing selected contexts."""

    contexts: list[ScoredContext]      # Selected contexts with scores
    tokens_used: int                   # Total tokens in response
    request_id: UUID                   # For audit correlation
    librarian_mode: LibrarianMode      # Mode used for selection
    explanation: Optional[str]         # Optional selection rationale
```

### 2.6 AuditEntry

```python
class AuditEntry(BaseModel):
    """Record of a context request and response."""

    id: UUID
    timestamp: datetime
    agent_id: Optional[str]
    task: str
    contexts_served: list[UUID]        # IDs of served contexts
    relevance_scores: list[float]      # Corresponding scores
    tokens_used: int
    tokens_budget: int
    request_source: RequestSource      # mcp | api | cli
    librarian_mode: LibrarianMode
    latency_ms: int
```

## 3. Storage Layer (storage/database.py)

### 3.1 Database Schema

```sql
-- Contexts table
CREATE TABLE contexts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,                -- knowledge | preference | history
    content TEXT NOT NULL,
    tags TEXT NOT NULL,                -- JSON array
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,          -- ISO8601
    updated_at TEXT NOT NULL,          -- ISO8601
    accessed_at TEXT,                  -- ISO8601 or NULL
    access_count INTEGER DEFAULT 0,
    metadata TEXT NOT NULL             -- JSON object
);

-- Vector embeddings (sqlite-vec virtual table)
CREATE VIRTUAL TABLE context_embeddings USING vec0(
    context_id TEXT PRIMARY KEY,
    embedding float[768]               -- Gemini embedding dimensions
);

-- Audit log table
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    agent_id TEXT,
    task TEXT NOT NULL,
    contexts_served TEXT NOT NULL,     -- JSON array of UUIDs
    relevance_scores TEXT NOT NULL,    -- JSON array of floats
    tokens_used INTEGER NOT NULL,
    tokens_budget INTEGER NOT NULL,
    request_source TEXT NOT NULL,
    librarian_mode TEXT NOT NULL,
    latency_ms INTEGER NOT NULL
);

-- Indexes
CREATE INDEX idx_contexts_type ON contexts(type);
CREATE INDEX idx_contexts_created_at ON contexts(created_at);
CREATE INDEX idx_contexts_accessed_at ON contexts(accessed_at);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_agent ON audit_log(agent_id);
```

### 3.2 ContextStore Class

```python
class ContextStore:
    """SQLite-based storage with vector search."""

    def __init__(self, db_path: Path, vector_dimensions: int = 768):
        self.db_path = Path(db_path)
        self.vector_dimensions = vector_dimensions
        self._conn: sqlite3.Connection | None = None
        self._initialize_db()

    # CRUD Operations
    def add_context(self, context: Context) -> None
    def get_context(self, context_id: UUID | str) -> Context
    def update_context(self, context: Context) -> None
    def delete_context(self, context_id: UUID | str) -> bool

    # Query Operations
    def list_contexts(types, tags, limit, offset) -> list[Context]
    def search_by_embedding(query_embedding, limit, types, tags) -> list[tuple[Context, float]]
    def search_by_text(query, limit, types) -> list[Context]

    # Access Tracking
    def record_access(context_ids: list[UUID | str]) -> None

    # Audit Operations
    def add_audit_entry(entry: AuditEntry) -> None
    def get_audit_entries(agent_id, limit, offset) -> list[AuditEntry]

    # Statistics
    def get_stats() -> dict
    def iter_contexts() -> Iterator[Context]
```

### 3.3 Vector Serialization

```python
def serialize_float32(vector: list[float]) -> bytes:
    """Pack float list to bytes for sqlite-vec."""
    return struct.pack(f"{len(vector)}f", *vector)

def deserialize_float32(data: bytes) -> list[float]:
    """Unpack bytes back to float list."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))
```

## 4. Embedding Layer (embedding/)

### 4.1 EmbeddingProvider Interface

```python
class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Embed a search query."""

    @abstractmethod
    def embed_document(self, text: str) -> list[float]:
        """Embed a document for storage."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
```

### 4.2 GeminiEmbeddingProvider

```python
class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini embedding implementation."""

    def __init__(
        self,
        model: str = "models/gemini-embedding-001",
        api_key: str | None = None,
        output_dimensionality: int = 768,
    ):
        self.model = model
        self.output_dimensionality = output_dimensionality
        genai.configure(api_key=api_key or os.environ.get("GOOGLE_API_KEY"))

    def embed_query(self, query: str) -> list[float]:
        result = genai.embed_content(
            model=self.model,
            content=query,
            task_type="retrieval_query",
            output_dimensionality=self.output_dimensionality,
        )
        return result["embedding"]

    def embed_document(self, text: str) -> list[float]:
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document",
            output_dimensionality=self.output_dimensionality,
        )
        return result["embedding"]
```

## 5. Librarian Layer (librarian/)

### 5.1 Librarian Interface

```python
class Librarian(ABC):
    """Abstract base for context selection strategies."""

    @abstractmethod
    def select(
        self,
        request: ContextRequest,
        candidates: list[Context],
    ) -> list[ScoredContext]:
        """Select and score relevant contexts."""
```

### 5.2 RulesLibrarian

Pattern-based selection using configurable rules.

```python
class RulesLibrarian(Librarian):
    """Fast, predictable rules-based selection."""

    def __init__(self, rules: list[LibrarianRule] | None = None):
        self.rules = rules or LibraConfig.default_rules()
        self._compiled_rules = [
            (re.compile(rule.pattern, re.IGNORECASE), rule)
            for rule in self.rules
        ]

    def select(self, request, candidates) -> list[ScoredContext]:
        # 1. Find matching rules for task
        matched_rules = [rule for pattern, rule in self._compiled_rules
                        if pattern.search(request.task)]

        # 2. Score each candidate
        scored = []
        for context in candidates:
            score = self._calculate_score(context, matched_rules, request)
            if score > 0:
                scored.append(ScoredContext(context=context, relevance_score=score))

        # 3. Sort by score descending
        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored

    def _calculate_score(self, context, matched_rules, request) -> float:
        # Base score: 0.3
        # Rule boost: +0.2 per type match, +0.15 per tag match
        # Keyword overlap: up to +0.3
        # Recency boost: +0.1 if accessed in last 7 days
        # Frequency boost: up to +0.1 based on access_count
        # Final score normalized to 0-1
```

**Default Rules:**

| Pattern | Boost Types | Boost Tags | Weight |
|---------|-------------|------------|--------|
| `code\|programming\|function\|refactor` | knowledge, preference | coding, technical | 1.5 |
| `write\|email\|message\|draft` | preference | communication, style | 1.3 |
| `debug\|error\|fix\|bug` | history, knowledge | debugging, errors | 1.4 |
| `remember\|recall\|previous\|last` | history | - | 1.2 |

### 5.3 GeminiLibrarian

LLM-powered selection using Gemini reasoning.

```python
class GeminiLibrarian(Librarian):
    """Intelligent selection using Gemini LLM."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        max_candidates_per_request: int = 30,
        min_score: float = 0.3,
    ):
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,  # Low for consistent scoring
            ),
        )

    def select(self, request, candidates) -> list[ScoredContext]:
        # 1. Apply request filters
        filtered = self._apply_filters(candidates, request)

        # 2. Batch if too many candidates
        if len(filtered) > self.max_candidates:
            return self._batch_select(request, filtered)

        # 3. Format candidates for prompt
        contexts_text = self._format_candidates(filtered)

        # 4. Generate selection via Gemini
        prompt = SELECTION_PROMPT.format(task=request.task, contexts=contexts_text)
        response = self.model.generate_content(prompt)

        # 5. Parse JSON response
        return self._parse_response(response.text, filtered)
```

**Selection Prompt Structure:**

```
You are an intelligent context selector for an AI assistant.

TASK: {task}

CANDIDATE CONTEXTS:
ID: {id}
Type: {type}
Tags: {tags}
Content: {content truncated to 500 chars}
---
[... more contexts ...]

Return JSON:
{
  "selections": [
    {"id": "context-id", "score": 0.85, "reason": "brief reason"},
    ...
  ]
}
```

### 5.4 HybridLibrarian

Combines rules for speed with LLM for quality.

```python
class HybridLibrarian(Librarian):
    """Rules pre-filter + LLM final selection."""

    def __init__(self, rules_librarian, gemini_librarian):
        self.rules = rules_librarian
        self.gemini = gemini_librarian

    def select(self, request, candidates) -> list[ScoredContext]:
        # 1. Rules-based pre-filter (fast)
        pre_filtered = self.rules.select(request, candidates)

        # 2. Take top candidates for LLM evaluation
        top_candidates = [sc.context for sc in pre_filtered[:30]]

        # 3. LLM final selection (smart)
        return self.gemini.select(request, top_candidates)
```

### 5.5 BudgetManager

Optimizes context selection within token limits.

```python
class BudgetManager:
    """Manages token budget for context selection."""

    def __init__(self, default_budget: int = 2000):
        self.default_budget = default_budget

    def optimize(
        self,
        scored_contexts: list[ScoredContext],
        budget: int,
    ) -> tuple[list[ScoredContext], int]:
        """Greedy selection maximizing relevance within budget."""

        selected = []
        tokens_used = 0

        # Sort by relevance descending
        sorted_contexts = sorted(
            scored_contexts,
            key=lambda x: x.relevance_score,
            reverse=True
        )

        # Greedily select until budget exhausted
        for sc in sorted_contexts:
            tokens = self.estimate_tokens(sc.context.content)
            if tokens_used + tokens <= budget:
                selected.append(sc)
                tokens_used += tokens

        return selected, tokens_used

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken."""
        # Uses cl100k_base encoding (GPT-4/Claude compatible)
```

## 6. Ingestion Layer (ingestion/)

### 6.1 Ingestor Interface

```python
class Ingestor(ABC):
    """Abstract base for content ingestors."""

    @abstractmethod
    def ingest(
        self,
        path: Path,
        context_type: ContextType,
        tags: list[str] | None,
    ) -> list[Context]:
        """Ingest content from path."""

    @abstractmethod
    def can_ingest(self, path: Path) -> bool:
        """Check if this ingestor can handle the path."""

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
```

### 6.2 TextIngestor

```python
class TextIngestor(Ingestor):
    """Handles plain text files."""

    supported_extensions = [".txt", ".text"]

    def ingest(self, path, context_type, tags) -> list[Context]:
        content = path.read_text(encoding="utf-8")
        chunks = self.chunker.chunk(content)
        return [
            Context(
                type=context_type,
                content=chunk,
                tags=tags or [],
                source=str(path),
            )
            for chunk in chunks
        ]
```

### 6.3 MarkdownIngestor

```python
class MarkdownIngestor(Ingestor):
    """Handles markdown files with structure extraction."""

    supported_extensions = [".md", ".markdown"]

    def ingest(self, path, context_type, tags) -> list[Context]:
        content = path.read_text(encoding="utf-8")

        # Extract structure
        headers = self._extract_headers(content)
        code_blocks = self._extract_code_blocks(content)
        links = self._extract_links(content)

        # Option: split on headers
        if self.split_on_headers:
            return self._split_by_headers(content, context_type, tags, path)

        # Otherwise chunk normally
        chunks = self.chunker.chunk(content)
        return [
            Context(
                type=context_type,
                content=chunk,
                tags=tags or [],
                source=str(path),
                metadata={"headers": headers, "links": links},
            )
            for chunk in chunks
        ]
```

### 6.4 DirectoryIngestor

```python
class DirectoryIngestor(Ingestor):
    """Recursively ingests directories."""

    def ingest(self, path, context_type, tags, progress_callback=None):
        # 1. Find all eligible files (respecting .gitignore)
        files = self._scan_directory(path)

        # 2. Process each file with appropriate ingestor
        contexts = []
        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(str(file_path), i + 1, len(files))

            ingestor = self._get_ingestor(file_path)
            if ingestor:
                contexts.extend(ingestor.ingest(file_path, context_type, tags))

        return contexts

    def _scan_directory(self, path) -> list[Path]:
        """Scan directory, respecting .gitignore patterns."""
        # Uses pathspec library for .gitignore matching
```

### 6.5 Chunker

```python
class Chunker:
    """Intelligent text chunking."""

    def __init__(
        self,
        target_size: int = 512,
        overlap: int = 50,
        min_size: int = 100,
    ):
        self.target_size = target_size
        self.overlap = overlap
        self.min_size = min_size

    def chunk(self, text: str) -> list[str]:
        # 1. Check if small enough (no chunking needed)
        if self.estimate_tokens(text) <= self.target_size:
            return [text]

        # 2. Split by paragraphs first
        paragraphs = self._split_paragraphs(text)

        # 3. Combine into target-sized chunks
        chunks = []
        current = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            if current_tokens + para_tokens > self.target_size and current:
                # Save current chunk
                chunks.append("\n\n".join(current))
                # Start new chunk with overlap
                current = current[-1:] if self.overlap else []
                current_tokens = sum(self.estimate_tokens(p) for p in current)

            current.append(para)
            current_tokens += para_tokens

        if current:
            chunks.append("\n\n".join(current))

        return chunks
```

## 7. Interface Layer (interfaces/)

### 7.1 CLI (cli.py)

Built with Typer framework.

```python
app = typer.Typer(
    name="libra",
    help="Intelligent Context Orchestration for AI Agents"
)

@app.command()
def add(content: str, type: str = "knowledge", tags: list[str] = None):
    """Add a new context."""
    service = get_service()
    context = service.add_context(content, ContextType(type), tags)
    console.print(f"[green]Created context {context.id}[/green]")

@app.command()
def query(task: str, max_tokens: int = 2000, format: str = "rich"):
    """Get relevant context for a task."""
    service = get_service()
    response = service.query(task, max_tokens)
    _display_response(response, format)

@app.command()
def serve(http: bool = False, port: int = 8377):
    """Start the server."""
    if http:
        uvicorn.run(api_app, host="127.0.0.1", port=port)
    else:
        # MCP stdio mode
        asyncio.run(mcp_server.run())

@app.command()
def chat():
    """Interactive chat with Librarian."""
    # Uses Gemini for conversational interface
    # Enriches responses with relevant context from knowledge base
```

### 7.2 MCP Server (mcp_server.py)

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("libra")

@server.list_tools()
async def list_tools():
    return [
        Tool(name="get_context", description="Get relevant context for a task"),
        Tool(name="remember", description="Save new context"),
        Tool(name="search", description="Search existing contexts"),
        Tool(name="forget", description="Delete a context"),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    service = get_service()

    if name == "get_context":
        response = service.query(
            task=arguments["task"],
            max_tokens=arguments.get("max_tokens", 2000),
            types=arguments.get("types"),
            tags=arguments.get("tags"),
        )
        return _format_mcp_response(response)

    elif name == "remember":
        context = service.add_context(
            content=arguments["content"],
            context_type=arguments.get("type", "knowledge"),
            tags=arguments.get("tags"),
        )
        return {"id": str(context.id), "success": True}
    # ... other tools

@server.list_resources()
async def list_resources():
    return [
        Resource(uri="libra://stats", name="Statistics"),
        Resource(uri="libra://contexts/all", name="All Contexts"),
    ]

async def run():
    async with stdio_server() as (read, write):
        await server.run(read, write, InitializationOptions())
```

### 7.3 REST API (api.py)

FastAPI application with automatic OpenAPI docs.

```python
app = FastAPI(title="libra API", version="0.1.0")

# Context endpoints
@app.get("/api/v1/contexts")
async def list_contexts(type: str = None, tags: str = None, limit: int = 100):
    service = get_service()
    return service.list_contexts(...)

@app.post("/api/v1/contexts")
async def create_context(body: ContextCreateRequest):
    service = get_service()
    context = service.add_context(body.content, body.type, body.tags)
    return ContextResponse.from_context(context)

@app.get("/api/v1/contexts/{context_id}")
async def get_context(context_id: str):
    service = get_service()
    return service.get_context(context_id)

# Query endpoint (main feature)
@app.post("/api/v1/query")
async def query(body: QueryRequest):
    service = get_service()
    response = service.query(body.task, body.max_tokens, body.types, body.tags)
    return response

# Search endpoint
@app.post("/api/v1/search")
async def search(body: SearchRequest):
    service = get_service()
    results = service.search_contexts(body.query, body.types, body.tags, body.limit)
    return {"results": [{"context": c, "score": s} for c, s in results]}

# Audit endpoint
@app.get("/api/v1/audit")
async def get_audit(agent_id: str = None, limit: int = 100):
    service = get_service()
    return service.get_audit_log(agent_id, limit)
```

### 7.4 Web UI (web/routes.py)

Jinja2-based server-rendered pages.

```python
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    service = get_service()
    stats = service.get_stats()
    recent = service.get_audit_log(limit=10)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats, "recent": recent}
    )

@router.get("/contexts", response_class=HTMLResponse)
async def contexts_list(request: Request, type: str = None, tags: str = None):
    service = get_service()
    contexts = service.list_contexts(types=[type] if type else None)
    return templates.TemplateResponse(
        "contexts.html",
        {"request": request, "contexts": contexts}
    )

@router.get("/audit", response_class=HTMLResponse)
async def audit_log(request: Request, agent_id: str = None):
    service = get_service()
    entries = service.get_audit_log(agent_id)
    return templates.TemplateResponse(
        "audit.html",
        {"request": request, "entries": entries}
    )
```

## 8. Configuration (core/config.py)

### 8.1 LibraConfig Model

```python
class LibraConfig(BaseModel):
    """Configuration for libra."""

    data_dir: Path = Path.home() / ".libra"
    log_level: str = "INFO"

    librarian: LibrarianConfig = LibrarianConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    defaults: DefaultsConfig = DefaultsConfig()
    server: ServerConfig = ServerConfig()

    @classmethod
    def load(cls, path: Path | None = None) -> "LibraConfig":
        """Load config from YAML file."""
        path = path or cls._default_path()
        if path.exists():
            data = yaml.safe_load(path.read_text())
            return cls(**data)
        return cls()

    def save(self, path: Path | None = None) -> None:
        """Save config to YAML file."""
        path = path or self._default_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(self.model_dump(), default_flow_style=False))
```

### 8.2 Sub-Configurations

```python
class LibrarianConfig(BaseModel):
    mode: LibrarianMode = LibrarianMode.HYBRID
    llm: LLMConfig = LLMConfig()
    rules: list[LibrarianRule] | None = None

class LLMConfig(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"

class EmbeddingConfig(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-embedding-001"
    dimensions: int = 768

class DefaultsConfig(BaseModel):
    token_budget: int = 2000
    chunk_size: int = 512
    min_relevance: float = 0.5

class ServerConfig(BaseModel):
    http_port: int = 8377
    http_host: str = "127.0.0.1"
    enable_cors: bool = False
```

## 9. Error Handling (core/exceptions.py)

```python
class LibraError(Exception):
    """Base exception for libra."""
    pass

class ContextNotFoundError(LibraError):
    """Raised when a context is not found."""
    def __init__(self, context_id: str):
        self.context_id = context_id
        super().__init__(f"Context not found: {context_id}")

class StorageError(LibraError):
    """Raised for storage/database errors."""
    pass

class EmbeddingError(LibraError):
    """Raised for embedding generation errors."""
    pass

class LibrarianError(LibraError):
    """Raised for Librarian selection errors."""
    pass

class ConfigurationError(LibraError):
    """Raised for configuration errors."""
    pass
```

## 10. Token Utilities (utils/tokens.py)

```python
# Conditional tiktoken import
try:
    import tiktoken
    _ENCODING: tiktoken.Encoding | None = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _ENCODING = None

def count_tokens(text: str) -> int:
    """Count tokens in text."""
    if _ENCODING is not None:
        return len(_ENCODING.encode(text))
    # Fallback: word-based estimation
    return len(text.split()) * 4 // 3

def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit."""
    if _ENCODING is not None:
        tokens = _ENCODING.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return _ENCODING.decode(tokens[:max_tokens])
    # Fallback: character-based truncation
    estimated_chars = max_tokens * 4
    return text[:estimated_chars]
```

## 11. Testing Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_core.py         # Models, config, exceptions
├── test_storage.py      # Database operations
├── test_librarian.py    # Selection algorithms
├── test_ingestion.py    # File parsing, chunking
└── test_web_ui.py       # Web interface
```

### Key Test Fixtures

```python
@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    store = ContextStore(db_path)
    yield store
    store.close()

@pytest.fixture
def sample_context():
    """Create sample context for testing."""
    return Context(
        type=ContextType.KNOWLEDGE,
        content="Python is a programming language.",
        tags=["coding", "python"],
        source="test",
    )

@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider for testing."""
    provider = Mock(spec=EmbeddingProvider)
    provider.embed_query.return_value = [0.0] * 768
    provider.embed_document.return_value = [0.0] * 768
    return provider
```
