# libra Implementation Plan

## Overview
Building libra - an intelligent context orchestration platform for AI agents using Gemini models.

## Phase 1: Foundation (Core Data Layer)
1. ✅ Project structure and package setup
2. ✅ Core data models (Context, AuditEntry, Configuration)
3. ✅ SQLite storage layer with sqlite-vec for vector search
4. ✅ Gemini embedding integration

## Phase 2: Intelligence Layer
5. ✅ Rules-based Librarian
6. ✅ Budget manager for token optimization
7. ✅ Gemini LLM-based Librarian (gemini-2.5-flash)
8. ✅ Hybrid mode implementation

## Phase 3: Ingestion Layer
9. ✅ Text and Markdown ingestors
10. ✅ Directory ingestor with .gitignore support
11. ✅ Chunking strategy implementation

## Phase 4: Interface Layer
12. ✅ CLI with Typer
13. ✅ MCP Server (stdio mode)
14. ✅ REST API with FastAPI
15. ⬜ Basic Web UI

## Phase 5: Integration & Polish
16. ✅ Configuration system
17. ✅ Audit logging
18. ✅ Error handling and logging
19. ✅ Tests (53 tests passing)
20. ⬜ Documentation

## Code Quality Improvements (Previous Sessions)
- ✅ Fixed security vulnerability: replaced os.system with subprocess.run in CLI config editor
- ✅ Added embed_document() method to EmbeddingProvider base class
- ✅ Removed unused UUID import from CLI
- ✅ Improved API file ingestion security and error handling
- ✅ Added filename sanitization in API file upload
- ✅ Fixed BudgetManager._optimize_with_allocation type annotation (ContextType vs string)
- ✅ Fixed GeminiEmbeddingProvider.embed_batch return type handling
- ✅ Fixed tokens.py _ENCODING type annotation for conditional tiktoken import
- ✅ Added return type annotations to interfaces/__init__.py
- ✅ Added type annotations to LibraService context manager methods
- ✅ Added type annotations to ContextStore context manager methods
- ✅ Expanded core module exports (ContextRequest, ContextResponse, ScoredContext, etc.)

## Latest Session Updates (December 7, 2025)
- ✅ Added interactive chat command (`libra chat`) - full implementation with:
  - Gemini-powered conversational interface
  - Context-enriched responses using knowledge base
  - Built-in commands (/search, /stats, help)
  - System prompt with knowledge base statistics
- ✅ All 53 tests still passing
- ✅ All mypy type checks passing
- ✅ Verified CLI commands work end-to-end
- ✅ Verified MCP server functionality
- ✅ Verified REST API endpoints

## Session Updates (December 7, 2025 - Verification Pass)
- ✅ Verified all Gemini model usage (gemini-2.5-flash for LLM, gemini-embedding-001 for embeddings)
- ✅ Verified specification conformance - all P0/P1 features implemented except Web UI
- ✅ All 53 tests passing
- ✅ All mypy type checks passing (30 source files)
- ✅ Code quality reviewed and verified

## Current Status
- Phase: MVP Implementation complete ✅
- All 53 tests passing ✅
- All imports verified ✅
- All type checks passing ✅
- CLI functional with all commands including chat ✅
- Updated to latest Gemini models (gemini-2.5-flash, gemini-embedding-001)
- Code quality reviewed and issues fixed ✅

## MVP Features Implemented
### P0 (Must Have) - All Complete ✅
- ✅ Local SQLite storage with vector search (sqlite-vec)
- ✅ Three context types (knowledge, preference, history)
- ✅ Gemini embeddings (gemini-embedding-001)
- ✅ Rules-based Librarian
- ✅ MCP server (stdio mode)
- ✅ Basic CLI (add, list, query, serve, etc.)
- ✅ Configuration file support (~/.libra/config.yaml)
- ✅ Audit logging

### P1 (Should Have) - All Complete ✅
- ✅ Gemini-based Librarian (gemini-2.5-flash)
- ✅ Hybrid Librarian mode (rules + LLM)
- ✅ REST API with FastAPI
- ✅ File ingestion (markdown, text)
- ✅ Directory ingestion with .gitignore support
- ✅ Token budget management
- ✅ Interactive chat mode (`libra chat`)
- ⬜ Basic Web UI (not yet implemented)

### P2 (Nice to Have) - Partial
- ⬜ HTTP mode for MCP
- ✅ Custom rules configuration
- ⬜ Local fallback (sentence-transformers + Ollama)
- ✅ Export/import functionality
- ⬜ Watch mode for ingestion

## Available CLI Commands
```
libra add        - Add a new context
libra list       - List contexts with filtering
libra show       - Display context details
libra delete     - Delete a context
libra query      - Get relevant context for a task
libra search     - Search contexts by similarity
libra ingest     - Ingest file or directory
libra serve      - Start MCP or HTTP server
libra audit      - View audit log
libra stats      - Show storage statistics
libra export     - Export contexts to JSON
libra import     - Import contexts from JSON
libra chat       - Interactive chat with Librarian
libra init       - Initialize libra
libra config     - Configuration management
```

## Technology Stack
- Python 3.11+
- SQLite + sqlite-vec
- Gemini (gemini-2.5-flash for LLM, gemini-embedding-001 for embeddings)
- FastAPI for REST API
- Typer for CLI
- MCP SDK for agent integration

## File Structure (Implemented)
```
libra/
├── __init__.py              # Package exports
├── service.py               # Main LibraService orchestrator
├── core/
│   ├── __init__.py
│   ├── models.py            # Pydantic models
│   ├── config.py            # Configuration management
│   └── exceptions.py        # Custom exceptions
├── storage/
│   ├── __init__.py
│   └── database.py          # SQLite + sqlite-vec
├── embedding/
│   ├── __init__.py
│   ├── base.py              # Abstract embedding provider
│   └── gemini.py            # Gemini embeddings
├── librarian/
│   ├── __init__.py
│   ├── base.py              # Abstract Librarian
│   ├── rules.py             # Rules-based selection
│   ├── llm.py               # Gemini-based selection
│   ├── hybrid.py            # Hybrid mode + factory
│   └── budget.py            # Token budget management
├── ingestion/
│   ├── __init__.py
│   ├── base.py              # Abstract ingestor
│   ├── text.py              # Text file ingestor
│   ├── markdown.py          # Markdown ingestor
│   ├── directory.py         # Directory ingestor
│   └── chunker.py           # Intelligent chunking
├── interfaces/
│   ├── __init__.py
│   ├── cli.py               # Typer CLI (all commands)
│   ├── mcp_server.py        # MCP server (tools, resources, prompts)
│   └── api.py               # FastAPI REST API
└── utils/
    ├── __init__.py
    ├── logging.py           # Logging configuration
    └── tokens.py            # Token counting utilities
```

## Notes
- Use Gemini models exclusively for all LLM operations
- Use docker compose if any additional components need to be deployed
- Local-first: all data stored in ~/.libra/
- Prioritize MVP features (P0 and P1)
