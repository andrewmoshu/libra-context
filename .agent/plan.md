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

## Code Quality Improvements (Latest Session)
- ✅ Fixed security vulnerability: replaced os.system with subprocess.run in CLI config editor
- ✅ Added embed_document() method to EmbeddingProvider base class
- ✅ Removed unused UUID import from CLI
- ✅ Improved API file ingestion security and error handling
- ✅ Added filename sanitization in API file upload
- ✅ All 53 tests passing after changes

## Current Status
- Phase: MVP Implementation complete ✅
- All 53 tests passing ✅
- All imports verified ✅
- CLI functional with all commands ✅
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
- ⬜ Basic Web UI

### P2 (Nice to Have) - Partial
- ⬜ HTTP mode for MCP
- ✅ Custom rules configuration
- ⬜ Local fallback (sentence-transformers + Ollama)
- ✅ Export/import functionality
- ⬜ Interactive chat mode

## Technology Stack
- Python 3.11+
- SQLite + sqlite-vec
- Gemini (gemini-2.5-flash for LLM, gemini-embedding-001 for embeddings)
- FastAPI for REST API
- Typer for CLI
- MCP SDK for agent integration

## File Structure (Target)
```
libra/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py          # Pydantic models
│   ├── config.py          # Configuration management
│   └── exceptions.py      # Custom exceptions
├── storage/
│   ├── __init__.py
│   ├── database.py        # SQLite + sqlite-vec
│   └── migrations.py      # Schema management
├── embedding/
│   ├── __init__.py
│   ├── base.py            # Abstract embedding provider
│   └── gemini.py          # Gemini embeddings
├── librarian/
│   ├── __init__.py
│   ├── base.py            # Abstract Librarian
│   ├── rules.py           # Rules-based selection
│   ├── llm.py             # Gemini-based selection
│   ├── hybrid.py          # Hybrid mode
│   └── budget.py          # Token budget management
├── ingestion/
│   ├── __init__.py
│   ├── base.py            # Abstract ingestor
│   ├── text.py            # Text file ingestor
│   ├── markdown.py        # Markdown ingestor
│   ├── directory.py       # Directory ingestor
│   └── chunker.py         # Intelligent chunking
├── interfaces/
│   ├── __init__.py
│   ├── cli.py             # Typer CLI
│   ├── mcp_server.py      # MCP server
│   └── api.py             # FastAPI REST API
└── utils/
    ├── __init__.py
    └── tokens.py          # Token counting utilities
```

## Notes
- Use Gemini models exclusively for all LLM operations
- Use docker compose if any aditional components need to be deployed
- Local-first: all data stored in ~/.libra/
- Prioritize MVP features (P0 and P1)
