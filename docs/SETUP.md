# libra Setup and Usage Guide

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start Tutorial](#quick-start-tutorial)
5. [CLI Reference](#cli-reference)
6. [MCP Integration](#mcp-integration)
7. [REST API Usage](#rest-api-usage)
8. [Web UI](#web-ui)
9. [Python SDK](#python-sdk)
10. [Advanced Configuration](#advanced-configuration)
11. [Troubleshooting](#troubleshooting)

---

## Requirements

### System Requirements

- **Python**: 3.11 or higher
- **Operating System**: macOS, Linux, Windows
- **Memory**: 512MB minimum (1GB recommended)
- **Storage**: 100MB for installation + database storage

### API Requirements

- **Google AI API Key**: Required for Gemini LLM and embeddings
  - Get one at: https://ai.google.dev/
  - Free tier: 15 requests/minute for LLM, 1500/minute for embeddings

---

## Installation

### Option 1: Using pip (Recommended)

```bash
pip install libra-context

# Verify installation
libra --help
```

### Option 2: From Source (For Development)

```bash
# Clone the repository
git clone https://github.com/andrewmoshu/libra-context
cd libra-context

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
libra --help
```

### Option 3: Using UV (Fast Package Manager)

```bash
# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/andrewmoshu/libra-context
cd libra-context
uv sync

# Run commands with uv
uv run libra --help
```

---

## Configuration

### Step 1: Set API Key

```bash
# Set Google AI API key (required)
export GOOGLE_API_KEY="your-api-key-here"

# Or add to your shell profile (~/.bashrc, ~/.zshrc)
echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.zshrc
```

### Step 2: Initialize libra

```bash
# Create config directory and default configuration
libra init
```

This creates:
- `~/.libra/` - Data directory
- `~/.libra/config.yaml` - Configuration file
- `~/.libra/libra.db` - SQLite database

### Step 3: Verify Setup

```bash
# Check configuration
libra config show

# Check storage statistics
libra stats
```

### Configuration File

Location: `~/.libra/config.yaml`

```yaml
# Librarian mode: rules (fast), llm (smart), hybrid (balanced)
librarian:
  mode: hybrid
  llm:
    provider: gemini
    model: gemini-2.5-flash

# Embedding configuration
embedding:
  provider: gemini
  model: gemini-embedding-001
  dimensions: 768

# Default values
defaults:
  token_budget: 2000
  chunk_size: 512
  min_relevance: 0.5

# Server settings
server:
  http_port: 8377
  http_host: 127.0.0.1
```

---

## Quick Start Tutorial

### Step 1: Add Your First Context

```bash
# Add a preference
libra add "I prefer TypeScript over JavaScript for web development" \
    --type preference \
    --tags coding,web

# Add some knowledge
libra add "Our project uses PostgreSQL for the database" \
    --type knowledge \
    --tags database,project

# Add historical context
libra add "Last week we decided to migrate from REST to GraphQL" \
    --type history \
    --tags decisions,architecture
```

### Step 2: Ingest Documentation

```bash
# Ingest a single file
libra ingest ./docs/api-reference.md --type knowledge --tags api,docs

# Ingest a directory
libra ingest ./project-docs/ --type knowledge --tags project
```

### Step 3: Query for Context

```bash
# Get context for a coding task
libra query "Help me design a new API endpoint"

# Get context with token limit
libra query "Refactor the authentication module" --max-tokens 3000

# Filter by type
libra query "What decisions have we made recently?" --types history
```

### Step 4: Search Your Knowledge

```bash
# Semantic search
libra search "database configuration"

# Search with type filter
libra search "coding preferences" --type preference
```

### Step 5: Interactive Chat

```bash
# Start chat session
libra chat
```

In the chat:
```
You: What do you know about our database setup?
Librarian: Based on your knowledge base, your project uses PostgreSQL...

You: /search authentication
[Shows semantic search results]

You: /stats
[Shows knowledge base statistics]
```

---

## CLI Reference

### Context Management

```bash
# Add context
libra add <content> --type <type> --tags <tag1,tag2>

# List contexts
libra list                    # List all
libra list --type knowledge   # Filter by type
libra list --tags api,docs    # Filter by tags
libra list --limit 10         # Limit results

# Show context details
libra show <context-id>

# Delete context
libra delete <context-id>
```

### Query and Search

```bash
# Intelligent query (main feature)
libra query <task> [--max-tokens N] [--types t1,t2] [--tags t1,t2]

# Semantic search
libra search <query> [--type TYPE] [--limit N]
```

### Ingestion

```bash
# Ingest file
libra ingest <path> [--type TYPE] [--tags t1,t2]

# Ingest directory (recursive)
libra ingest ./docs/ [--type TYPE] [--tags t1,t2]
```

### Server

```bash
# Start MCP server (for Claude Desktop)
libra serve

# Start HTTP server (for REST API + Web UI)
libra serve --http

# Start HTTP on custom port
libra serve --http --port 9000

# Start both MCP and HTTP
libra serve --all
```

### Audit and Stats

```bash
# View audit log
libra audit                   # Recent entries
libra audit --agent claude    # Filter by agent
libra audit --limit 50        # Limit results

# View statistics
libra stats
```

### Import/Export

```bash
# Export all contexts to JSON
libra export > backup.json
libra export --output backup.json

# Import from JSON
libra import backup.json
```

### Configuration

```bash
# Show configuration
libra config show

# Set value
libra config set librarian.mode hybrid
libra config set defaults.token_budget 3000

# Edit in editor
libra config edit
```

---

## MCP Integration

### Claude Desktop Setup

1. Open Claude Desktop config file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Add libra configuration:

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

3. Restart Claude Desktop

4. Test by asking Claude:
   - "What tools do you have access to?"
   - "Use libra to get context for refactoring code"

### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_context` | Get relevant context for a task | `task`, `max_tokens?`, `types?`, `tags?` |
| `remember` | Save new context | `content`, `type?`, `tags?` |
| `search` | Search existing contexts | `query`, `type?`, `limit?` |
| `forget` | Delete a context | `id` |

### Cursor/Continue.dev Setup

Similar configuration - check their respective documentation for MCP server configuration location.

---

## REST API Usage

### Start the Server

```bash
libra serve --http
# Server running at http://localhost:8377
```

### API Documentation

- **Swagger UI**: http://localhost:8377/docs
- **ReDoc**: http://localhost:8377/redoc

### Example Requests

**Query for Context (Main Feature)**:

```bash
curl -X POST http://localhost:8377/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Help me design a REST API",
    "max_tokens": 2000,
    "types": ["knowledge", "preference"]
  }'
```

Response:
```json
{
  "contexts": [
    {
      "context": {
        "id": "...",
        "type": "knowledge",
        "content": "Our project uses REST with JSON...",
        "tags": ["api", "architecture"]
      },
      "relevance_score": 0.89
    }
  ],
  "tokens_used": 450,
  "request_id": "...",
  "librarian_mode": "hybrid"
}
```

**Create Context**:

```bash
curl -X POST http://localhost:8377/api/v1/contexts \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Use camelCase for variable names",
    "type": "preference",
    "tags": ["coding", "style"]
  }'
```

**List Contexts**:

```bash
curl "http://localhost:8377/api/v1/contexts?type=knowledge&limit=10"
```

**Search**:

```bash
curl -X POST http://localhost:8377/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database configuration",
    "limit": 10
  }'
```

---

## Web UI

### Access

Start the HTTP server and open http://localhost:8377 in your browser.

```bash
libra serve --http
# Open http://localhost:8377
```

### Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Overview, stats, recent activity |
| Contexts | `/contexts` | Browse and manage contexts |
| Add Context | `/contexts/add` | Create new context |
| Audit Log | `/audit` | View query history |
| Settings | `/settings` | View configuration |

### Features

- **Filter contexts**: By type (knowledge/preference/history) and tags
- **View details**: Click any context to see full content
- **Delete contexts**: Remove unwanted entries
- **Export data**: Download all contexts as JSON
- **Real-time stats**: See knowledge base size and usage

---

## Python SDK

### Basic Usage

```python
from libra import LibraService, ContextType

# Create service
service = LibraService()

# Add context
context = service.add_context(
    content="Python is dynamically typed",
    context_type=ContextType.KNOWLEDGE,
    tags=["python", "coding"]
)

# Query for relevant context
response = service.query(
    task="Help me write Python code",
    max_tokens=2000
)

for scored in response.contexts:
    print(f"[{scored.relevance_score:.2f}] {scored.context.content[:100]}...")

# Search semantically
results = service.search_contexts("python programming", limit=10)
for context, score in results:
    print(f"[{score:.2f}] {context.content[:50]}...")
```

### Context Manager Usage

```python
from libra import LibraService

with LibraService() as service:
    # All operations here
    service.add_context("Some knowledge", ContextType.KNOWLEDGE)
    response = service.query("Find relevant info")
# Connection automatically closed
```

### Ingestion

```python
from pathlib import Path
from libra import LibraService, ContextType

service = LibraService()

# Ingest file
contexts = service.ingest_file(
    Path("./docs/api.md"),
    context_type=ContextType.KNOWLEDGE,
    tags=["api", "documentation"]
)

# Ingest directory
contexts = service.ingest_directory(
    Path("./project-docs/"),
    context_type=ContextType.KNOWLEDGE,
    tags=["project"],
    progress_callback=lambda f, c, t: print(f"Processing {f} ({c}/{t})")
)
```

### Custom Configuration

```python
from libra import LibraService, LibraConfig
from libra.core.models import LibrarianMode

# Create custom config
config = LibraConfig(
    librarian=LibrarianConfig(
        mode=LibrarianMode.LLM,  # Use pure LLM mode
    ),
    defaults=DefaultsConfig(
        token_budget=4000,  # Higher token budget
    ),
)

service = LibraService(config=config)
```

---

## Advanced Configuration

### Custom Rules

Edit `~/.libra/config.yaml`:

```yaml
librarian:
  mode: rules  # or hybrid
  rules:
    # Boost coding contexts for programming tasks
    - pattern: "(code|programming|function|class|method)"
      boost_types: [knowledge, preference]
      boost_tags: [coding, technical, architecture]
      weight: 1.5

    # Boost communication preferences for writing tasks
    - pattern: "(write|draft|email|message|document)"
      boost_types: [preference]
      boost_tags: [communication, style, writing]
      weight: 1.3

    # Custom rule for your project
    - pattern: "(database|sql|query|postgres)"
      boost_types: [knowledge]
      boost_tags: [database, backend]
      weight: 1.4
```

### Agent-Specific Configuration

```yaml
agents:
  claude-desktop:
    description: "General assistant for all tasks"
    default_budget: 2000

  cursor:
    description: "Code editor AI"
    default_budget: 3000
    boost_tags: [coding, technical]

  code-reviewer:
    description: "Code review agent"
    default_budget: 4000
    allowed_types: [knowledge, preference]
```

### Environment Variables

All config values can be overridden:

```bash
# Core settings
export LIBRA_DATA_DIR=~/.libra
export LIBRA_LOG_LEVEL=DEBUG

# Librarian settings
export LIBRA_LIBRARIAN_MODE=llm

# Server settings
export LIBRA_SERVER_HTTP_PORT=9000
export LIBRA_SERVER_HTTP_HOST=0.0.0.0

# API keys
export GOOGLE_API_KEY=your-key-here
```

---

## Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not set"**

```bash
# Set the API key
export GOOGLE_API_KEY="your-key-here"

# Verify it's set
echo $GOOGLE_API_KEY
```

**"No module named libra"**

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Or reinstall
pip install -e .
```

**"Database is locked"**

Only one process can access the database at a time. Close other libra instances.

**"Embedding generation failed"**

- Check API key is valid
- Check internet connection
- Verify API quota at https://ai.google.dev/

**MCP server not recognized by Claude Desktop**

1. Check config file path is correct
2. Ensure `libra` command is in PATH
3. Restart Claude Desktop completely
4. Check Claude Desktop logs

### Debug Mode

```bash
# Enable debug logging
export LIBRA_LOG_LEVEL=DEBUG
libra query "test task"

# Or in config.yaml
log_level: DEBUG
```

### Getting Help

1. Check the documentation: `docs/HLD.md`, `docs/LLD.md`
2. View API docs: http://localhost:8377/docs
3. Ask Claude with libra context: "Using libra, explain how context selection works"
4. Open an issue: https://github.com/andrewmoshu/libra-context/issues

---

## Next Steps

1. **Add your knowledge**: Import documentation, preferences, and historical decisions
2. **Integrate with Claude Desktop**: Set up MCP for automatic context
3. **Explore the Web UI**: Visualize and manage your context
4. **Fine-tune rules**: Customize selection behavior for your workflow
5. **Use the chat**: Interactively explore your knowledge base

Happy context orchestration!
