# libra

> Intelligent Context Orchestration for AI Agents

---

## Executive Summary

libra is a local-first context orchestration platform that acts as an intelligent intermediary between users' knowledge and their AI agents. Rather than having each AI agent independently search for and retrieve context, libra serves as a "Context General" — a centralized intelligence that understands what context exists, what each agent needs, and how to compose the right context package for any given task.

The core insight is simple: current approaches to AI context (RAG, memory layers, agent tool-use) all put the burden of context discovery on either the user or the agent itself. libra inverts this by introducing a dedicated layer whose sole job is understanding context and serving it intelligently.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Overview](#2-solution-overview)
3. [Core Concepts](#3-core-concepts)
4. [System Architecture](#4-system-architecture)
5. [Component Deep Dives](#5-component-deep-dives)
6. [Data Model](#6-data-model)
7. [Integration Model](#7-integration-model)
8. [User Flows](#8-user-flows)
9. [Security & Privacy](#9-security--privacy)
10. [Configuration System](#10-configuration-system)
11. [Interfaces](#11-interfaces)
12. [Technology Choices](#12-technology-choices)
13. [MVP Scope & Milestones](#13-mvp-scope--milestones)
14. [Future Roadmap](#14-future-roadmap)
15. [Success Metrics](#15-success-metrics)

---

## 1. Problem Statement

### The Current State of AI Context

Today's AI agents face a fundamental challenge: they need context to be useful, but they don't inherently know what context they need or where to find it.

**Approach 1: User-Provided Context**
Users manually paste relevant information into prompts. This works but doesn't scale — users must remember what context exists and judge what's relevant for each interaction.

**Approach 2: RAG (Retrieval-Augmented Generation)**
Systems embed documents and retrieve based on query similarity. The limitation is that embedding similarity doesn't equal task relevance. A query about "refactoring auth" might retrieve documents that mention "auth" but miss crucial context about the user's coding preferences or past architectural decisions.

**Approach 3: Agent Tool-Use**
Agents are given tools to search for information. This creates a chicken-and-egg problem: the agent must know what it doesn't know. Agents often retrieve too much (wasting tokens), too little (missing context), or the wrong things entirely.

**Approach 4: Memory Layers**
Products like Mem0, Zep, and MemGPT focus on persistence — remembering things across conversations. But persistence isn't intelligence. These systems store and recall; they don't reason about what context a specific task actually requires.

### The Gap

No existing solution provides **intelligent context composition** — the ability to understand a task, reason about what context would make an agent successful, and assemble a tailored context package that fits within token budgets while maximizing relevance.

### Consequences of the Gap

- **Wasted tokens**: Agents receive irrelevant context, consuming expensive context window space
- **Missed context**: Critical information isn't surfaced because it doesn't match query embeddings
- **Inconsistent behavior**: The same user gets different quality responses depending on what context happened to be retrieved
- **User burden**: Users must manually manage context, defeating the purpose of AI assistance
- **No cross-agent coherence**: Each agent has its own siloed view; there's no unified context layer

---

## 2. Solution Overview

### The Context General Model

libra introduces a new architectural primitive: the **Context Librarian** (or "Context General" in military terms).

Think of it like commanding an army. You wouldn't give every soldier access to all intelligence databases and expect them to figure out what they need. Instead, a general understands the full battlefield, knows each unit's role, and pushes relevant intel down the chain of command. Each soldier receives a focused brief tailored to their mission.

libra applies this model to AI agents:

```
┌─────────────────────────────────────────────────────────┐
│                   CONTEXT LIBRARIAN                     │
│                                                         │
│  • Sees all available context                           │
│  • Understands each agent's role and capabilities       │
│  • Reasons about what context serves the task           │
│  • Composes tailored context packages                   │
│  • Respects token budgets and priorities                │
│  • Maintains audit trail of what was served             │
│                                                         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           │  Tailored context packages
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   [Claude]            [Cursor]          [Local LLM]
   
   Gets: user prefs,   Gets: codebase    Gets: task-specific
   communication       knowledge,        context only
   style, task         coding style,     
   history             past decisions    
```

### Key Differentiators

1. **Intelligent, not just retrieval**: libra reasons about context relevance, not just embedding similarity

2. **Proactive, not reactive**: Context is composed before the agent asks, based on task analysis

3. **Cross-agent coherent**: All agents draw from the same context pool with consistent understanding

4. **Budget-aware**: Fits context within token limits while maximizing information value

5. **Auditable**: Complete trail of what context was served to which agent and why

6. **Local-first**: All data stays on user's machine; no cloud dependency for core function

---

## 3. Core Concepts

### 3.1 Context

A **Context** is a discrete unit of information that might be useful to an AI agent. Contexts are categorized by type and tagged for organization.

**Context Types:**

| Type | Description | Examples |
|------|-------------|----------|
| **Knowledge** | Facts, documentation, reference material | "Project X uses PostgreSQL 15", API documentation, technical specs |
| **Preference** | How the user likes things done | "Prefers TypeScript over JavaScript", "Likes concise responses", "Uses functional programming style" |
| **History** | Past interactions, decisions, events | "Last week decided to use Redis for caching", "Previous refactor caused session bugs" |

**Context Attributes:**
- **Content**: The actual information
- **Type**: Knowledge, Preference, or History
- **Tags**: User-defined labels for organization
- **Source**: Where the context came from (file, manual entry, inferred)
- **Embedding**: Vector representation for semantic search
- **Timestamps**: Creation and last-accessed times
- **Access count**: How often this context has been served

### 3.2 The Librarian

The **Librarian** is the intelligent core of libra. It receives a task description and available contexts, then selects and ranks contexts by relevance.

The Librarian operates in three modes:

**Rules Mode (Fast)**
Pattern-based selection using configurable rules. Example: if task contains "code" or "refactor", boost technical knowledge and coding preferences. Predictable, fast, no external dependencies.

**LLM Mode (Smart)**
Uses Gemini (gemini-2.0-flash) to reason about context relevance. Fast, high-quality, with generous free tier. Can explain its selections.

**Hybrid Mode (Balanced)**
Rules-based pre-filtering followed by LLM-based final selection. Gets the speed of rules with the intelligence of LLM reasoning.

### 3.3 Token Budget

Every context request includes a **token budget** — the maximum tokens the requesting agent can accept. The Librarian must select contexts that fit within this budget while maximizing relevance.

This creates an optimization problem: given N contexts with varying relevance scores and token counts, select the subset that maximizes total relevance while staying under the token limit.

### 3.4 Agents

An **Agent** is any AI system that requests context from libra. Agents are identified by ID and can have associated metadata:

- **Agent ID**: Unique identifier (e.g., "claude-desktop", "cursor", "code-reviewer")
- **Role description**: What this agent does (helps Librarian understand context needs)
- **Default token budget**: Standard context budget for this agent
- **Allowed context types**: Optional restrictions on what context types this agent can access

### 3.5 Audit Log

Every context request and response is logged in the **Audit Log**:

- Timestamp
- Requesting agent
- Task description
- Contexts served (with relevance scores)
- Tokens used
- Request source (MCP, API, CLI)

This enables users to understand what their agents are seeing and debug unexpected behavior.

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                              libra                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      INGESTION LAYER                        │   │
│  │                                                             │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │   │ Markdown │  │   Text   │  │Directory │  │  Manual  │   │   │
│  │   │ Ingestor │  │ Ingestor │  │ Ingestor │  │  Input   │   │   │
│  │   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │   │
│  │        │             │             │             │         │   │
│  │        └─────────────┴──────┬──────┴─────────────┘         │   │
│  │                             │                               │   │
│  │                             ▼                               │   │
│  │                     ┌──────────────┐                        │   │
│  │                     │   Chunker    │                        │   │
│  │                     └──────┬───────┘                        │   │
│  │                            │                                │   │
│  └────────────────────────────┼────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     EMBEDDING LAYER                         │   │
│  │                                                             │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │   │
│  │   │    Local     │  │    Ollama    │  │    OpenAI    │     │   │
│  │   │ (sent-trans) │  │  Embeddings  │  │  Embeddings  │     │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘     │   │
│  │                                                             │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │                                    │
│                                ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      STORAGE LAYER                          │   │
│  │                                                             │   │
│  │   ┌─────────────────────────────────────────────────────┐  │   │
│  │   │                    SQLite                            │  │   │
│  │   │                                                      │  │   │
│  │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │   │
│  │   │  │  Contexts   │  │   Vectors   │  │  Audit Log  │  │  │   │
│  │   │  │   Table     │  │   (vec0)    │  │    Table    │  │  │   │
│  │   │  └─────────────┘  └─────────────┘  └─────────────┘  │  │   │
│  │   │                                                      │  │   │
│  │   └─────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │                                    │
│                                ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    INTELLIGENCE LAYER                       │   │
│  │                                                             │   │
│  │   ┌─────────────────────────────────────────────────────┐  │   │
│  │   │                   LIBRARIAN                          │  │   │
│  │   │                                                      │  │   │
│  │   │  ┌───────────┐  ┌───────────┐  ┌───────────┐        │  │   │
│  │   │  │   Rules   │  │    LLM    │  │  Hybrid   │        │  │   │
│  │   │  │   Mode    │  │   Mode    │  │   Mode    │        │  │   │
│  │   │  └───────────┘  └───────────┘  └───────────┘        │  │   │
│  │   │                                                      │  │   │
│  │   │  ┌───────────┐  ┌───────────┐                       │  │   │
│  │   │  │  Ranker   │  │  Budget   │                       │  │   │
│  │   │  │           │  │  Manager  │                       │  │   │
│  │   │  └───────────┘  └───────────┘                       │  │   │
│  │   │                                                      │  │   │
│  │   └─────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │                                    │
│                                ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     INTERFACE LAYER                         │   │
│  │                                                             │   │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │   │
│  │   │    MCP    │  │   REST    │  │    CLI    │  │  Web UI │ │   │
│  │   │  Server   │  │   API     │  │           │  │         │ │   │
│  │   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬────┘ │   │
│  │         │              │              │              │      │   │
│  └─────────┼──────────────┼──────────────┼──────────────┼──────┘   │
│            │              │              │              │           │
└────────────┼──────────────┼──────────────┼──────────────┼───────────┘
             │              │              │              │
             ▼              ▼              ▼              ▼
      ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
      │  Claude   │  │  Custom   │  │  Terminal │  │  Browser  │
      │  Cursor   │  │  Agents   │  │           │  │           │
      │  Continue │  │           │  │           │  │           │
      └───────────┘  └───────────┘  └───────────┘  └───────────┘
```

### 4.2 Layer Responsibilities

**Ingestion Layer**
Responsible for getting content into libra. Handles different file formats, extracts text, and chunks large documents into manageable pieces. The chunker uses intelligent splitting (respecting paragraph boundaries, code blocks, etc.) rather than naive character limits.

**Embedding Layer**
Generates vector embeddings for semantic search. Supports multiple backends: Gemini (primary for MVP), local via sentence-transformers, or OpenAI. Gemini offers excellent quality with generous free tier, making it ideal for MVP validation.

**Storage Layer**
Persists contexts, embeddings, and audit logs. Uses SQLite with the sqlite-vec extension for vector operations. Single-file database makes backup and portability trivial.

**Intelligence Layer**
The Librarian and its supporting components. Takes context requests, reasons about relevance, and returns optimized context packages. This is where libra's differentiation lives.

**Interface Layer**
Multiple ways to interact with libra: MCP for AI agent integration, REST API for programmatic access, CLI for management, Web UI for visual interaction.

### 4.3 Data Flow

**Ingestion Flow:**
```
User adds content
       │
       ▼
Ingestor extracts text based on format
       │
       ▼
Chunker splits into context-sized pieces
       │
       ▼
User assigns type (knowledge/preference/history) and tags
       │
       ▼
Embedding engine generates vector
       │
       ▼
Context stored in SQLite with embedding in vec0
```

**Query Flow:**
```
Agent requests context for task
       │
       ▼
MCP Server receives request
       │
       ▼
Librarian analyzes task
       │
       ▼
Storage layer retrieves candidate contexts (embedding similarity + filters)
       │
       ▼
Librarian ranks candidates by task relevance
       │
       ▼
Budget manager selects optimal subset within token limit
       │
       ▼
Audit entry recorded
       │
       ▼
Context package returned to agent
```

---

## 5. Component Deep Dives

### 5.1 Ingestors

Ingestors are responsible for extracting text content from various sources. MVP includes:

**Markdown Ingestor**
Parses markdown files, preserving structure information (headers become tags). Can optionally split on headers to create one context per section.

**Text Ingestor**
Handles plain text files. Simple but necessary for universal compatibility.

**Directory Ingestor**
Recursively processes a directory, applying the appropriate ingestor to each file based on extension. Respects .gitignore patterns. Useful for ingesting entire project documentation folders.

**Manual Input**
Direct text input via CLI or API. User provides content, type, and tags directly.

**Chunking Strategy**
Large documents are split into chunks that fit within embedding model limits while preserving semantic coherence:
- Prefer splitting at paragraph boundaries
- Keep code blocks intact when possible
- Overlap chunks slightly to maintain context across boundaries
- Target chunk size: 512-1024 tokens (configurable)

### 5.2 Embedding Engine

The embedding engine converts text to vectors for semantic search. Supports pluggable backends:

**Gemini (Default for MVP)**
Uses Google's Gemini embedding API (`text-embedding-004`). 768 dimensions, excellent quality. Generous free tier (1,500 requests/min) makes it ideal for MVP. Requires Google AI API key.

**Local (sentence-transformers)**
Fallback option. Uses `all-MiniLM-L6-v2` model (384 dimensions). Runs entirely on CPU, no external dependencies. Good for offline use or privacy-sensitive contexts.

**OpenAI**
Uses OpenAI's embedding API. Alternative cloud option for users already in OpenAI ecosystem.

**Embedding Caching**
Embeddings are computed once and stored. Re-embedding only occurs if content changes.

### 5.3 The Librarian

The Librarian is libra's brain. It decides what context is relevant for a given task.

**Input:**
- Task description (natural language)
- Token budget
- Optional filters (context types, tags)
- Agent ID (optional, for role-aware selection)

**Output:**
- Ranked list of contexts with relevance scores
- Total tokens used
- Selection explanation (in debug mode)

**Selection Process:**

1. **Candidate Retrieval**: Query storage layer for contexts matching any filters. Use embedding similarity to get initial candidates (typically 50-100).

2. **Relevance Scoring**: Apply Librarian mode to score each candidate:
   - Rules mode: Pattern matching against task text
   - LLM mode: Ask local LLM to evaluate relevance
   - Hybrid: Rules pre-filter → LLM final selection

3. **Ranking**: Sort candidates by relevance score

4. **Budget Optimization**: Select highest-relevance contexts that fit within token budget. This is a variant of the knapsack problem; we use greedy selection (take highest relevance first until budget exhausted).

5. **Audit**: Record what was selected and why

**Rules Mode Details**

Rules are pattern-action pairs:
```
IF task matches pattern THEN boost/penalize certain context types/tags
```

Default rules cover common patterns:
- Coding tasks → boost technical knowledge, coding preferences
- Writing tasks → boost communication preferences
- Questions about past → boost history contexts
- Debugging tasks → boost error history, technical docs

Users can add custom rules via configuration.

**LLM Mode Details**

Uses Gemini (gemini-2.0-flash via Google AI API) to reason about relevance. The prompt provides:
- The task description
- List of candidate contexts (truncated if too many)
- Instructions to return relevance scores

The LLM returns structured output (JSON) with context IDs and scores. This allows nuanced reasoning like "this context mentions auth but is about a different project, so lower relevance."

Gemini Flash is ideal for this use case: fast inference (~200ms), high quality reasoning, generous free tier (15 RPM / 1M TPM free), and structured output support.

**Hybrid Mode Details**

Best of both worlds:
1. Rules mode quickly filters 1000 contexts down to 30 candidates
2. Gemini carefully evaluates those 30 and picks the best 5-10

This keeps latency reasonable (<1s total) while preserving intelligent selection.

### 5.4 Budget Manager

Responsible for fitting selected contexts within token limits.

**Token Counting**
Uses tiktoken (or simple word-based estimation) to count tokens. Different models have different tokenizers; we use cl100k_base (GPT-4/Claude) as default.

**Optimization Strategy**
Given contexts with relevance scores and token counts, maximize total relevance within budget:

1. Sort by relevance (descending)
2. Greedily add contexts until budget would be exceeded
3. Optionally: try swapping lower-relevance large contexts for higher-relevance smaller ones

For MVP, greedy selection is sufficient. Future versions could use dynamic programming for optimal selection.

**Budget Allocation**
When multiple context types are needed, Budget Manager can allocate portions of the budget:
- 50% for knowledge
- 30% for preferences  
- 20% for history

This ensures diversity in served context. Allocation is configurable.

### 5.5 Storage (Context Store)

SQLite-based storage with vector search capabilities.

**Schema Overview**

*Contexts Table*
Stores context metadata: ID, type, content, tags, source, timestamps, access statistics.

*Vectors Table (sqlite-vec)*
Stores embeddings as virtual table for efficient similarity search. Linked to contexts by ID.

*Audit Log Table*
Stores all context requests and responses: timestamp, agent, task, contexts served, tokens used.

*Configuration Table*
Stores user settings: Librarian mode, default budgets, rules, etc.

**Query Patterns**

*Semantic Search*
Find contexts similar to a query embedding, optionally filtered by type/tags.

*List/Filter*
Retrieve contexts by type, tags, date range. For UI display and management.

*Audit Query*
Retrieve audit entries by agent, date range, task pattern. For debugging and analysis.

**Indexing**
- B-tree indexes on type, tags, timestamps
- Vector index (HNSW via sqlite-vec) on embeddings
- Full-text search index on content (optional, for keyword search)

### 5.6 MCP Server

The MCP (Model Context Protocol) server is the primary integration point for AI agents.

**Why MCP**

MCP is becoming the standard for AI agent integrations. One MCP server provides compatibility with:
- Claude Desktop
- Claude Code
- Cursor
- Continue.dev
- Zed
- Any future MCP-compatible client

**MCP Primitives**

*Tools* — Actions agents can take:

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_context` | Get relevant context for a task | task (string), max_tokens (int), types (array), tags (array) |
| `remember` | Save new context for future | content (string), type (string), tags (array) |
| `search` | Search existing contexts | query (string), type (string), limit (int) |
| `forget` | Delete a context | context_id (string) |

*Resources* — Context that can be read:

| Resource | Description |
|----------|-------------|
| `libra://contexts/knowledge` | All knowledge contexts |
| `libra://contexts/preferences` | All preference contexts |
| `libra://contexts/history` | All history contexts |
| `libra://contexts/recent` | Recently accessed contexts |

*Prompts* — Reusable prompt templates:

| Prompt | Description |
|--------|-------------|
| `with_context` | Wraps a task with relevant context pre-loaded |
| `explain_context` | Asks libra to explain what context it has |

**Server Modes**

*stdio mode* (default)
For Claude Desktop and similar local clients. libra runs as a subprocess, communicating via stdin/stdout.

*HTTP mode*
For networked access. Enables remote clients and web-based integrations. Optional authentication.

### 5.7 REST API

HTTP API for programmatic access and web UI backend.

**Endpoints Overview**

*Context Management*
- `GET /contexts` — List contexts with filtering
- `POST /contexts` — Create new context
- `GET /contexts/{id}` — Get specific context
- `PUT /contexts/{id}` — Update context
- `DELETE /contexts/{id}` — Delete context

*Query*
- `POST /query` — Get context for a task (main endpoint)
- `POST /search` — Semantic search

*Ingestion*
- `POST /ingest/text` — Ingest raw text
- `POST /ingest/file` — Ingest uploaded file
- `POST /ingest/directory` — Ingest directory (local path)

*Audit*
- `GET /audit` — Query audit log
- `GET /audit/stats` — Aggregate statistics

*System*
- `GET /health` — Health check
- `GET /stats` — System statistics
- `GET /config` — Get configuration
- `PUT /config` — Update configuration

**Response Format**
All responses are JSON. Errors include code, message, and details.

### 5.8 CLI

Command-line interface for management and scripting.

**Command Structure**

```
libra <command> [subcommand] [options]
```

**Commands**

*Context Management*
- `libra add <content>` — Add context interactively or with flags
- `libra list` — List contexts with filtering
- `libra show <id>` — Display context details
- `libra edit <id>` — Edit context
- `libra delete <id>` — Delete context

*Ingestion*
- `libra ingest <path>` — Ingest file or directory
- `libra ingest --watch <path>` — Watch directory for changes

*Query*
- `libra query <task>` — Get context for a task
- `libra search <query>` — Search contexts

*Server*
- `libra serve` — Start MCP server (stdio mode)
- `libra serve --http` — Start HTTP server
- `libra serve --all` — Start both MCP and HTTP

*Audit*
- `libra audit` — View recent audit entries
- `libra audit --agent <id>` — Filter by agent
- `libra audit --export` — Export audit log

*Configuration*
- `libra config show` — Display configuration
- `libra config set <key> <value>` — Set configuration value
- `libra config edit` — Open config in editor

*Utilities*
- `libra stats` — Show statistics
- `libra chat` — Interactive chat with the Librarian (ask about your contexts)
- `libra export` — Export all contexts
- `libra import` — Import contexts

### 5.9 Web UI

Browser-based interface for visual management.

**Pages/Views**

*Dashboard*
Overview of context store: counts by type, recent activity, storage usage.

*Contexts*
List view with filtering, search, and sorting. Click to view/edit. Bulk operations (delete, re-tag).

*Add Context*
Form for manual context entry. Type selection, tag input, content editor.

*Audit Log*
Table of recent context requests. Filter by agent, date, task. Click to see details of what was served.

*Settings*
Configuration editor: Librarian mode, embedding backend, rules editor, default budgets.

**Design Principles**
- Minimal, functional interface
- Works without JavaScript for core functions (progressive enhancement)
- Real-time updates via WebSocket (optional)
- Mobile-responsive

---

## 6. Data Model

### 6.1 Context

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| type | Enum | knowledge, preference, history |
| content | Text | The actual context content |
| tags | Array[String] | User-defined labels |
| source | String | Origin: file path, "manual", URL |
| embedding | Vector | Embedding for semantic search |
| created_at | Timestamp | When created |
| updated_at | Timestamp | When last modified |
| accessed_at | Timestamp | When last served to an agent |
| access_count | Integer | Number of times served |
| metadata | JSON | Extensible metadata |

### 6.2 Audit Entry

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| timestamp | Timestamp | When request occurred |
| agent_id | String | Requesting agent identifier |
| task | Text | Task description |
| contexts_served | Array[UUID] | Which contexts were returned |
| relevance_scores | Array[Float] | Scores for each context |
| tokens_used | Integer | Total tokens in response |
| tokens_budget | Integer | Requested budget |
| request_source | Enum | mcp, api, cli |
| librarian_mode | Enum | rules, llm, hybrid |
| latency_ms | Integer | Processing time |

### 6.3 Agent (Optional)

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier |
| name | String | Display name |
| description | Text | What this agent does |
| default_budget | Integer | Default token budget |
| allowed_types | Array[Enum] | Allowed context types |
| created_at | Timestamp | When registered |

### 6.4 Configuration

| Field | Type | Description |
|-------|------|-------------|
| librarian_mode | Enum | rules, llm, hybrid |
| llm_backend | String | Ollama model or endpoint |
| embedding_backend | Enum | local, ollama, openai |
| default_budget | Integer | Default token budget |
| chunk_size | Integer | Target chunk size for ingestion |
| rules | JSON | Custom Librarian rules |

---

## 7. Integration Model

### 7.1 MCP Integration (Primary)

**Claude Desktop Setup**

User adds libra to Claude Desktop config:

Location: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "libra": {
      "command": "libra",
      "args": ["serve"]
    }
  }
}
```

After restart, Claude Desktop can use libra tools.

**How Claude Uses libra**

When user starts a conversation, Claude sees available tools:
- `get_context`: Get relevant context for a task
- `remember`: Save something for later
- `search`: Find specific context

Claude can call `get_context` at the start of complex tasks to load relevant information.

Example flow:
1. User: "Help me refactor the auth module"
2. Claude calls `get_context` with task "refactor auth module"
3. libra returns: coding preferences, auth module docs, past decisions about auth
4. Claude proceeds with full context

**Cursor / Continue.dev / Other MCP Clients**

Similar setup process — each client has its own config location but the same libra server works for all.

### 7.2 REST API Integration

For custom agents or applications that don't support MCP:

```
POST /query
{
  "task": "Write a professional email to decline a meeting",
  "max_tokens": 1500,
  "types": ["preference", "history"]
}

Response:
{
  "contexts": [
    {
      "id": "...",
      "type": "preference",
      "content": "User prefers concise, direct communication...",
      "relevance": 0.92
    },
    {
      "id": "...",
      "type": "history", 
      "content": "Last email to this recipient used formal tone...",
      "relevance": 0.78
    }
  ],
  "tokens_used": 847,
  "request_id": "..."
}
```

The calling application prepends these contexts to its prompt.

### 7.3 Proxy Mode (Future)

For agents that can't be modified, libra can act as an API proxy:

```
Agent → libra Proxy → OpenAI/Anthropic API
```

The proxy intercepts requests, enriches prompts with relevant context, and forwards to the actual LLM API. This allows context injection without any agent modifications.

---

## 8. User Flows

### 8.1 Initial Setup

1. User installs libra (`pip install libra-context` or download binary)
2. User runs `libra init` to create config directory
3. User sets Gemini API key: `export GOOGLE_AI_API_KEY=your-key` (or `libra config set api_key`)
4. User configures Claude Desktop (or other MCP client) to use libra
5. User adds initial context:
   - `libra ingest ~/Documents/work-notes/` (bulk import)
   - `libra add "I prefer TypeScript over JavaScript" --type preference`
   - `libra add "Our API uses REST, not GraphQL" --type knowledge`
6. libra is ready to serve context

### 8.2 Daily Usage

**Automatic Context (MCP)**
User works with Claude Desktop normally. When starting complex tasks, Claude automatically calls `get_context`. User doesn't need to do anything — context flows automatically.

**Manual Context Query**
User can test what context would be served:
```
libra query "refactor the payment processing module"
```
Shows what contexts would be returned, useful for debugging.

**Adding New Context**
As user learns things or makes decisions:
```
libra add "Decided to use Stripe for payments instead of Square" --type history --tags payments,decisions
```

Or through Claude: "Remember that we decided to use Stripe for payments" → Claude calls `remember` tool.

### 8.3 Context Management

**Reviewing Contexts**
```
libra list --type knowledge --tags api
```
Or use Web UI for visual browsing.

**Cleaning Up**
```
libra audit --agent claude-desktop --last 7d
```
See what contexts have been served. Identify outdated or irrelevant contexts. Delete or update as needed.

**Bulk Operations**
```
libra ingest ~/new-project-docs/ --type knowledge --tags new-project
```

### 8.4 Debugging

**Why did Claude say that?**
Check audit log:
```
libra audit --last 5
```
See exactly what context Claude received.

**Context isn't being served**
1. Check if context exists: `libra search "payment"`
2. Check if it matches task: `libra query "process payment"`
3. Adjust tags or Librarian rules if needed

---

## 9. Security & Privacy

### 9.1 Core Principles

1. **Local-first**: All data stored locally by default
2. **No cloud dependency**: Core functionality works entirely offline
3. **User owns data**: Easy export, real deletion
4. **Minimal data exposure**: Only serve context that's needed

### 9.2 Data Storage

**Location**
All data stored in `~/.libra/` (configurable):
- `libra.db` — SQLite database (contexts, vectors, audit log)
- `config.yaml` — Configuration
- `keys/` — Encryption keys (future)

**Encryption at Rest (Future)**
Optional encryption of the database using user-provided passphrase. Contexts decrypted only when needed.

### 9.3 Data in Transit

**MCP (stdio)**
Communication is local (stdin/stdout) — no network exposure.

**MCP/API (HTTP)**
When running HTTP server:
- Binds to localhost by default (not accessible from network)
- Optional: enable network access with authentication
- Optional: TLS for encrypted connections

### 9.4 Third-Party LLM Considerations

MVP uses Gemini (Google AI) for both embeddings and LLM reasoning:
- Content is sent to Google's servers for processing
- Google's data usage policies apply
- Clear disclosure in documentation and first-run setup

**Mitigations:**
- Only send context metadata to LLM, not full content when possible
- Support local fallback (sentence-transformers + Ollama) for privacy-sensitive users
- Let users configure per-context sensitivity levels
- Embedding caching minimizes repeated API calls

```yaml
# Privacy-focused configuration (post-MVP)
privacy:
  embedding_provider: local  # Use sentence-transformers
  llm_provider: ollama       # Use local Ollama
  sensitive_contexts:
    - type: personal
      providers: [local_only]
```

### 9.5 Context Access Control (Future)

For multi-agent scenarios:
- Tag contexts with access levels
- Agents can only access contexts they're permitted
- Example: personal-agent gets all contexts, work-agent only gets work-tagged contexts

### 9.6 Audit Trail

Complete audit log enables:
- Review what data was shared with which agent
- Compliance reporting (what AI saw what)
- Anomaly detection (unexpected context access patterns)

---

## 10. Configuration System

### 10.1 Configuration File

Location: `~/.libra/config.yaml`

```yaml
# Core settings
data_dir: ~/.libra
log_level: info

# Librarian configuration
librarian:
  mode: hybrid  # rules, llm, hybrid
  
  # LLM mode settings (Gemini)
  llm:
    provider: gemini
    model: gemini-2.0-flash
    # API key via environment: GOOGLE_AI_API_KEY
  
  # Rules mode settings
  rules:
    - pattern: "(code|programming|function|refactor)"
      boost_types: [knowledge, preference]
      boost_tags: [coding, technical]
      weight: 1.5
    
    - pattern: "(write|email|message|draft)"
      boost_types: [preference]
      boost_tags: [communication, style]
      weight: 1.3

# Embedding configuration
embedding:
  provider: gemini  # gemini, local, openai
  model: text-embedding-004  # for gemini
  # model: all-MiniLM-L6-v2  # for local fallback
  # API key via environment: GOOGLE_AI_API_KEY

# Default budgets
defaults:
  token_budget: 2000
  chunk_size: 512
  min_relevance: 0.5

# Server configuration  
server:
  http_port: 8377
  http_host: 127.0.0.1
  enable_cors: false

# Agent configurations (optional)
agents:
  claude-desktop:
    description: "General assistant"
    default_budget: 2000
    
  cursor:
    description: "Code editor AI"
    default_budget: 3000
    boost_tags: [coding]
```

### 10.2 Environment Variables

All config values can be overridden via environment variables:

```
LIBRA_DATA_DIR=~/.libra
LIBRA_LIBRARIAN_MODE=hybrid
LIBRA_EMBEDDING_PROVIDER=gemini
LIBRA_SERVER_HTTP_PORT=8377
GOOGLE_AI_API_KEY=your-api-key-here  # Required for Gemini
```

### 10.3 CLI Configuration

```bash
libra config show                    # Display current config
libra config set librarian.mode llm  # Set value
libra config edit                    # Open in $EDITOR
```

---

## 11. Interfaces

### 11.1 MCP Interface

**Tools**

| Tool | Input | Output |
|------|-------|--------|
| `get_context` | `{task: string, max_tokens?: int, types?: string[], tags?: string[]}` | `{contexts: Context[], tokens_used: int}` |
| `remember` | `{content: string, type?: string, tags?: string[]}` | `{id: string, success: bool}` |
| `search` | `{query: string, type?: string, limit?: int}` | `{contexts: Context[]}` |
| `forget` | `{id: string}` | `{success: bool}` |

**Resources**

| URI | Description |
|-----|-------------|
| `libra://stats` | System statistics |
| `libra://contexts/all` | All contexts (paginated) |
| `libra://contexts/{type}` | Contexts by type |

### 11.2 REST API Interface

**Base URL**: `http://localhost:8377/api/v1`

**Authentication**: Optional API key via `Authorization: Bearer <key>` header

**Endpoints**: See Section 5.7 for full endpoint list

### 11.3 CLI Interface

See Section 5.8 for full command reference.

### 11.4 Web UI Interface

Served at `http://localhost:8377` when HTTP server is running.

---

## 12. Technology Choices

### 12.1 Core Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | Ecosystem (ML libs), rapid development, good async support |
| Database | SQLite + sqlite-vec | Single file, no server, vector search built-in |
| LLM | Gemini (gemini-2.0-flash) | Fast, high quality, generous free tier, structured output support |
| Embeddings | Gemini (text-embedding-004) | 768 dimensions, excellent quality, same API key as LLM |
| API Framework | FastAPI | Modern, async, auto-docs, Pydantic integration |
| CLI Framework | Typer | Clean syntax, auto-help, Click-based |
| MCP SDK | mcp (official) | Standard library for MCP servers |

### 12.2 Optional Components

| Component | Technology | When Used |
|-----------|------------|-----------|
| Local Embeddings | sentence-transformers | Offline/privacy fallback |
| Local LLM | Ollama | Offline/privacy fallback |
| Web UI | Svelte + Vite | Visual management |
| Tokenizer | tiktoken | Accurate token counting |

### 12.3 Why Gemini for MVP

| Consideration | Gemini Advantage |
|---------------|------------------|
| Cost | Generous free tier: 15 RPM, 1M TPM for Flash; 1,500 RPM for embeddings |
| Quality | State-of-the-art reasoning and embedding quality |
| Speed | Flash model optimized for low latency (~200ms) |
| Simplicity | Single API key for both LLM and embeddings |
| Structured Output | Native JSON mode for reliable Librarian responses |
| SDK | Official `google-generativeai` Python package |

**Trade-off acknowledged**: Gemini requires internet and sends data to Google. For users needing full privacy, local fallback (sentence-transformers + Ollama) is available but not the default MVP path.

### 12.3 Distribution

| Method | Use Case |
|--------|----------|
| PyPI (`pip install libra-context`) | Python users, developers |
| Standalone binary (PyInstaller) | Non-technical users |
| Docker image | Containerized deployments |
| Homebrew formula | macOS users |

---

## 13. MVP Scope & Milestones

### 13.1 What's In MVP

**Must Have (P0)**
- Local SQLite storage with vector search
- Three context types (knowledge, preference, history)
- Gemini embeddings (text-embedding-004)
- Rules-based Librarian
- MCP server (stdio mode)
- Basic CLI (add, list, query, serve)
- Configuration file support
- Audit logging

**Should Have (P1)**
- Gemini-based Librarian (gemini-2.0-flash)
- Hybrid Librarian mode
- REST API
- File ingestion (markdown, text)
- Directory ingestion
- Basic Web UI
- Token budget management

**Nice to Have (P2)**
- HTTP mode for MCP
- Custom rules configuration
- Local fallback (sentence-transformers + Ollama)
- Export/import functionality
- Interactive chat mode

### 13.2 Milestones

**Week 1-2: Foundation**
- Project structure and tooling
- SQLite store with vector search
- Context data model
- Gemini embedding integration
- Unit tests for core

**Week 3: Intelligence**
- Rules-based Librarian
- Budget manager
- Relevance scoring
- Integration tests

**Week 4: MCP Integration**
- MCP server implementation
- Tool definitions
- Claude Desktop integration
- End-to-end testing

**Week 5: CLI & Ingestion**
- Full CLI implementation
- Markdown/text ingestors
- Directory ingestion
- Documentation

**Week 6: API & Polish**
- REST API implementation
- Configuration system
- Error handling
- Logging improvements

**Week 7: Gemini LLM Mode**
- Gemini Flash integration for Librarian
- Structured output parsing
- Hybrid mode
- Performance testing

**Week 8: UI & Release**
- Basic Web UI
- Final documentation
- Packaging (PyPI, binary)
- Release v0.1.0

### 13.3 MVP Success Criteria

1. **Functional**: User can add context, query it, and have it served to Claude Desktop
2. **Intelligent**: Different tasks receive different context (not just nearest-neighbor retrieval)
3. **Fast**: Context queries complete in <300ms (rules mode), <1s (hybrid mode with Gemini)
4. **Integrated**: Works seamlessly with Gemini API for embeddings and reasoning
5. **Documented**: Another developer can install and use in <10 minutes
6. **Tested**: Core functionality has unit and integration tests

---

## 14. Future Roadmap

### 14.1 Post-MVP Features

**Version 0.2: Enhanced Intelligence**
- Context relationship modeling (this context relates to that context)
- Automatic context inference from conversations
- Multi-turn conversation context
- Proactive context suggestions

**Version 0.3: Enterprise Features**
- Multi-user support
- Role-based access control
- Team context sharing
- SSO integration

**Version 0.4: Advanced Integrations**
- OpenAI API proxy mode
- Browser extension (capture context from web)
- IDE plugins (beyond MCP)
- Mobile app (context on the go)

**Version 0.5: Cloud Option**
- Optional cloud sync (encrypted)
- Cross-device context
- Backup and restore
- Collaboration features

### 14.2 Long-Term Vision

libra becomes the standard context layer for AI agents:
- Every AI interaction is context-aware
- Users build rich context graphs over time
- Enterprise deployments with full governance
- Ecosystem of integrations and plugins

---

## 15. Success Metrics

### 15.1 MVP Metrics

| Metric | Target |
|--------|--------|
| Installation success rate | >90% complete install without errors |
| Time to first context served | <5 minutes from install |
| Query latency (rules mode) | <300ms p95 |
| Query latency (hybrid mode) | <1s p95 (includes Gemini API call) |
| Context relevance (subjective) | Users report relevant context >80% of time |

### 15.2 Growth Metrics (Post-MVP)

| Metric | Description |
|--------|-------------|
| Weekly active users | Users who query context at least once |
| Contexts per user | Average contexts in user's store |
| Queries per user per day | How often context is requested |
| Agent diversity | Number of different agents using libra |
| Retention | Users still active after 30/60/90 days |

### 15.3 Quality Metrics

| Metric | Description |
|--------|-------------|
| Context hit rate | % of queries where relevant context exists |
| Selection accuracy | % of served contexts rated relevant by user |
| Token efficiency | Relevance per token (are we wasting budget?) |
| Error rate | Failed queries / total queries |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| Context | A discrete unit of information useful to an AI agent |
| Librarian | The intelligent component that selects relevant context |
| MCP | Model Context Protocol — standard for AI agent integrations |
| Token Budget | Maximum tokens an agent can accept for context |
| Embedding | Vector representation of text for semantic search |
| RAG | Retrieval-Augmented Generation — technique for adding knowledge to LLMs |

---

## Appendix B: References

- Model Context Protocol: https://modelcontextprotocol.io
- Google AI (Gemini): https://ai.google.dev
- google-generativeai SDK: https://github.com/google-gemini/generative-ai-python
- sqlite-vec: https://github.com/asg017/sqlite-vec
- sentence-transformers: https://www.sbert.net
- Ollama: https://ollama.ai
- FastAPI: https://fastapi.tiangolo.com
- Typer: https://typer.tiangolo.com

---

*Document version: 1.0*
*Last updated: December 2024*
