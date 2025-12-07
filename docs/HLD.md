# libra - High-Level Design (HLD)

## 1. Executive Summary

libra is a local-first context orchestration platform that provides intelligent context management for AI agents. It introduces the concept of a "Context Librarian" - a centralized intelligence that understands available context, reasons about what each agent needs, and composes tailored context packages.

### Key Value Propositions

1. **Intelligent Selection**: Reasons about context relevance, not just embedding similarity
2. **Proactive Composition**: Context assembled before agent asks, based on task analysis
3. **Cross-Agent Coherence**: All agents draw from the same context pool
4. **Budget Awareness**: Fits context within token limits while maximizing relevance
5. **Auditability**: Complete trail of what context was served and why
6. **Local-First**: All data stays on user's machine
7. **Multi-Provider Support**: Works with 9 LLM providers and 9 embedding providers
8. **Fully Local Option**: Ollama + sentence-transformers for complete offline operation

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              libra                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      INTERFACE LAYER                               │  │
│  │                                                                    │  │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐     │  │
│  │   │    MCP    │  │   REST    │  │    CLI    │  │  Web UI   │     │  │
│  │   │  Server   │  │   API     │  │           │  │           │     │  │
│  │   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘     │  │
│  │         │              │              │              │            │  │
│  └─────────┼──────────────┼──────────────┼──────────────┼────────────┘  │
│            │              │              │              │                │
│            └──────────────┴──────────────┴──────────────┘                │
│                                    │                                     │
│                                    ▼                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      SERVICE LAYER                                 │  │
│  │                                                                    │  │
│  │                      ┌─────────────────┐                          │  │
│  │                      │  LibraService   │                          │  │
│  │                      │                 │                          │  │
│  │                      │  - query()      │                          │  │
│  │                      │  - add_context()│                          │  │
│  │                      │  - search()     │                          │  │
│  │                      │  - ingest()     │                          │  │
│  │                      └────────┬────────┘                          │  │
│  │                               │                                    │  │
│  └───────────────────────────────┼────────────────────────────────────┘  │
│                                  │                                       │
│            ┌─────────────────────┼─────────────────────┐                 │
│            │                     │                     │                 │
│            ▼                     ▼                     ▼                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │  INTELLIGENCE   │  │   INGESTION     │  │    STORAGE      │          │
│  │     LAYER       │  │     LAYER       │  │     LAYER       │          │
│  │                 │  │                 │  │                 │          │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │          │
│  │  │ Librarian │  │  │  │ Markdown  │  │  │  │  SQLite   │  │          │
│  │  │  (Rules/  │  │  │  │ Ingestor  │  │  │  │  Database │  │          │
│  │  │   LLM/    │  │  │  └───────────┘  │  │  └───────────┘  │          │
│  │  │  Hybrid)  │  │  │  ┌───────────┐  │  │  ┌───────────┐  │          │
│  │  └───────────┘  │  │  │   Text    │  │  │  │sqlite-vec │  │          │
│  │  ┌───────────┐  │  │  │ Ingestor  │  │  │  │  (Vector) │  │          │
│  │  │  Budget   │  │  │  └───────────┘  │  │  └───────────┘  │          │
│  │  │ Manager   │  │  │  ┌───────────┐  │  │                 │          │
│  │  └───────────┘  │  │  │ Directory │  │  │                 │          │
│  │                 │  │  │ Ingestor  │  │  │                 │          │
│  └─────────────────┘  │  └───────────┘  │  └─────────────────┘          │
│                       │  ┌───────────┐  │                                │
│                       │  │  Chunker  │  │                                │
│                       │  └───────────┘  │                                │
│                       └─────────────────┘                                │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                  EMBEDDING LAYER (Multi-Provider)                  │  │
│  │                                                                    │  │
│  │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │  │
│  │   │  Gemini  │ │  OpenAI  │ │  Ollama  │ │  Local   │ │ Azure  │ │  │
│  │   │(default) │ │          │ │          │ │(sent-tr) │ │ OpenAI │ │  │
│  │   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │  │
│  │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │   │ Bedrock  │ │HuggingFce│ │ Together │ │  Custom  │            │  │
│  │   └──────────┘ └──────────┘ └──────────┘ └──────────┘            │  │
│  │                                                                    │  │
│  │              EmbeddingFactory → create_embedding_provider()       │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
  ┌───────────┐              ┌───────────┐              ┌───────────┐
  │  Claude   │              │  Cursor   │              │  Custom   │
  │  Desktop  │              │   IDE     │              │  Agents   │
  └───────────┘              └───────────┘              └───────────┘
```

### 2.2 Layer Descriptions

#### Interface Layer
Provides multiple ways to interact with libra:
- **MCP Server**: Primary integration for AI agents (Claude Desktop, Cursor, etc.)
- **REST API**: HTTP endpoints for programmatic access
- **CLI**: Command-line interface for management
- **Web UI**: Browser-based dashboard

#### Service Layer
**LibraService** is the main orchestrator that coordinates all operations:
- Context CRUD operations
- Query processing (intelligent context selection)
- File/directory ingestion
- Audit logging

#### Intelligence Layer
The "brain" of libra:
- **Librarian**: Selects and ranks contexts by task relevance
  - Rules mode: Pattern-based, fast, predictable
  - LLM mode: LLM-powered reasoning (9 providers supported)
  - Hybrid mode: Rules pre-filter + LLM final selection
- **LLM Providers**: Gemini (default), OpenAI, Anthropic, Ollama, Azure OpenAI, AWS Bedrock, HuggingFace, Together AI, Custom
- **Budget Manager**: Optimizes context selection within token limits

#### Ingestion Layer
Converts external content into contexts:
- **Markdown Ingestor**: Parses .md files, extracts structure
- **Text Ingestor**: Handles plain text files
- **Directory Ingestor**: Recursive processing with .gitignore support
- **Chunker**: Splits large documents into semantic chunks

#### Storage Layer
Persists all data locally:
- **SQLite Database**: Contexts, audit log, configuration
- **sqlite-vec**: Vector extension for embedding-based search

#### Embedding Layer
Generates vector representations for semantic search:
- **9 Embedding Providers**: Gemini (default), OpenAI, Ollama, Local (sentence-transformers), Azure OpenAI, AWS Bedrock, HuggingFace, Together AI, Custom
- **EmbeddingFactory**: Creates configured provider via `create_embedding_provider()`
- **Configurable Dimensions**: Each provider supports different embedding dimensions

## 3. Data Flow

### 3.1 Context Query Flow (Main Feature)

```
Agent Request                   libra Processing                      Response
───────────────────────────────────────────────────────────────────────────────

1. Agent sends task         ┌─────────────────────────────────┐
   "refactor auth module"   │                                 │
   ─────────────────────────►  Embed Query                    │
                            │  (Gemini Embedding)             │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Vector Search                  │
                            │  (Get 100 candidates)           │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Librarian Selection            │
                            │  (Score & rank by relevance)    │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Budget Optimization            │
                            │  (Fit within token limit)       │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Audit Logging                  │
                            │  (Record what was served)       │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                                    Context Package
                                    (5-10 relevant contexts)
                            ◄───────────────────────────────────
```

### 3.2 Ingestion Flow

```
File/Directory Input              libra Processing                  Output
───────────────────────────────────────────────────────────────────────────────

1. User provides path       ┌─────────────────────────────────┐
   ./docs/                  │                                 │
   ─────────────────────────►  Directory Scan                 │
                            │  (Respect .gitignore)           │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  File Parsing                   │
                            │  (MD/TXT/etc. ingestors)        │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Chunking                       │
                            │  (Split into 512-1024 tokens)   │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Embedding Generation           │
                            │  (Gemini for each chunk)        │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                            ┌─────────────────────────────────┐
                            │  Storage                        │
                            │  (SQLite + sqlite-vec)          │
                            └───────────────┬─────────────────┘
                                            │
                                            ▼
                                    Created Contexts
                            ◄───────────────────────────────────
```

## 4. Component Interactions

### 4.1 MCP Integration

```
┌───────────────────┐         ┌───────────────────┐         ┌───────────────────┐
│   Claude Desktop  │         │    MCP Server     │         │   LibraService    │
└─────────┬─────────┘         └─────────┬─────────┘         └─────────┬─────────┘
          │                             │                             │
          │  get_context(task)          │                             │
          ├────────────────────────────►│                             │
          │                             │  service.query(task)        │
          │                             ├────────────────────────────►│
          │                             │                             │
          │                             │   ContextResponse           │
          │                             │◄────────────────────────────┤
          │  contexts + tokens_used     │                             │
          │◄────────────────────────────┤                             │
          │                             │                             │
          │  remember(content, type)    │                             │
          ├────────────────────────────►│                             │
          │                             │  service.add_context()      │
          │                             ├────────────────────────────►│
          │                             │                             │
          │                             │   Context                   │
          │                             │◄────────────────────────────┤
          │  success: true              │                             │
          │◄────────────────────────────┤                             │
```

### 4.2 Web UI Interaction

```
┌───────────────────┐         ┌───────────────────┐         ┌───────────────────┐
│     Browser       │         │    FastAPI App    │         │   LibraService    │
└─────────┬─────────┘         └─────────┬─────────┘         └─────────┬─────────┘
          │                             │                             │
          │  GET /                      │                             │
          ├────────────────────────────►│                             │
          │                             │  service.get_stats()        │
          │                             ├────────────────────────────►│
          │                             │                             │
          │                             │   stats dict                │
          │                             │◄────────────────────────────┤
          │  HTML Dashboard             │                             │
          │◄────────────────────────────┤                             │
          │                             │                             │
          │  POST /api/v1/query         │                             │
          │  {task: "...", max: 2000}   │                             │
          ├────────────────────────────►│                             │
          │                             │  service.query(...)         │
          │                             ├────────────────────────────►│
          │                             │                             │
          │                             │   ContextResponse           │
          │                             │◄────────────────────────────┤
          │  JSON response              │                             │
          │◄────────────────────────────┤                             │
```

## 5. Technology Decisions

### 5.1 Multi-Provider Architecture

libra supports 9 LLM providers and 9 embedding providers to give users maximum flexibility:

| Layer | Supported Providers |
|-------|---------------------|
| **LLM** | Gemini (default), OpenAI, Anthropic, Ollama, Azure OpenAI, AWS Bedrock, HuggingFace, Together AI, Custom |
| **Embeddings** | Gemini (default), OpenAI, Ollama, Local (sentence-transformers), Azure OpenAI, AWS Bedrock, HuggingFace, Together AI, Custom |

#### Why Gemini as Default?

| Consideration | Decision Rationale |
|---------------|-------------------|
| **LLM Provider** | Gemini (gemini-2.5-flash) - Fast inference, high quality, generous free tier |
| **Embeddings** | Gemini (gemini-embedding-001) - 768 dimensions, excellent quality, same API |
| **Single API Key** | Both LLM and embeddings use one Google API key - simpler setup |
| **Structured Output** | Native JSON mode for reliable Librarian responses |

#### Fully Local Option

For users requiring complete offline operation or maximum privacy:
- **LLM**: Ollama with models like llama3.2, mistral, etc.
- **Embeddings**: Local provider using sentence-transformers (all-MiniLM-L6-v2)
- **No external API calls** - all processing happens locally

### 5.2 Why SQLite + sqlite-vec?

| Consideration | Decision Rationale |
|---------------|-------------------|
| **Local-First** | Single file database - no server needed |
| **Portability** | Easy backup and migration - just copy one file |
| **Vector Search** | sqlite-vec extension provides efficient similarity search |
| **Simplicity** | No external dependencies (Redis, Postgres, etc.) |

### 5.3 Why MCP?

| Consideration | Decision Rationale |
|---------------|-------------------|
| **Compatibility** | Works with Claude Desktop, Cursor, Continue.dev, etc. |
| **Standard Protocol** | Emerging standard for AI agent integration |
| **Two-Way Communication** | Agents can both read and write context |

## 6. Scalability Considerations

### Current Limits (MVP)
- Designed for single-user, local usage
- SQLite handles millions of contexts efficiently
- sqlite-vec uses HNSW for fast approximate nearest neighbor

### Future Scaling Paths
1. **Multi-User**: Add user authentication, separate databases
2. **Server Mode**: Deploy as shared service
3. **Distributed**: Replace SQLite with PostgreSQL + pgvector
4. **Cloud Sync**: Optional encrypted cloud backup

## 7. Security Model

### Data Protection
- All data stored locally in `~/.libra/`
- No cloud dependency for core function
- MCP stdio mode has no network exposure
- HTTP server binds to localhost by default

### API Security
- Optional API key authentication for HTTP endpoints
- CORS disabled by default
- Rate limiting available (not enabled in MVP)

### Third-Party Considerations
- Cloud providers (Gemini, OpenAI, Anthropic, etc.) send content to external servers
- **Fully local option** available: Ollama (LLM) + sentence-transformers (embeddings)
- Provider choice is user-configurable via `libra init` or config file
- Clear disclosure in documentation

## 8. Deployment Options

### Local Development
```bash
pip install -e .
libra init
libra serve --http
```

### Production (Single User)
```bash
pip install libra-context
libra init
libra serve --all  # MCP + HTTP
```

### Docker
```bash
docker build -t libra .
docker run -v ~/.libra:/root/.libra -p 8377:8377 libra
```

## 9. Monitoring and Observability

### Audit Log
- Every context request logged with:
  - Timestamp, agent, task
  - Contexts served (IDs and relevance scores)
  - Tokens used/budgeted
  - Latency

### Statistics
- Context counts by type
- Total tokens stored
- Query patterns over time
- Storage size

### Logging
- Structured logging to `~/.libra/libra.log`
- Configurable log levels
- Debug mode for development
