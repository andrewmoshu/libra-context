# libra

**Intelligent Context Orchestration for AI Agents**

libra is a local-first context orchestration platform that acts as an intelligent intermediary between your knowledge and AI agents. Rather than having each agent independently search for context, libra serves as a "Context Librarian" that understands what context exists, what each agent needs, and composes tailored context packages for any task.

## Features

- **Intelligent Context Selection**: Uses Gemini-powered reasoning to select relevant context, not just embedding similarity
- **Token Budget Management**: Fits context within token limits while maximizing relevance
- **Multiple Librarian Modes**: Rules-based (fast), LLM-based (smart), or Hybrid (balanced)
- **MCP Integration**: Works with Claude Desktop, Cursor, Continue.dev, and other MCP clients
- **REST API**: Full HTTP API for custom integrations
- **CLI**: Complete command-line interface for management
- **Web UI**: Browser-based dashboard for visual management
- **Audit Logging**: Complete trail of what context was served to which agent

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/libra-context/libra
cd libra

# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Configuration

```bash
# Set your Gemini API key
export GOOGLE_API_KEY="your-api-key-here"

# Initialize libra (creates ~/.libra/ directory)
libra init
```

### Basic Usage

```bash
# Add context manually
libra add "I prefer TypeScript over JavaScript" --type preference --tags coding

# Ingest documentation
libra ingest ~/Documents/project-docs/ --type knowledge --tags project

# Query for relevant context
libra query "Help me refactor the authentication module"

# Search contexts semantically
libra search "authentication patterns"

# Start the MCP server (for Claude Desktop integration)
libra serve

# Start the HTTP server (for REST API and Web UI)
libra serve --http

# Interactive chat with your context
libra chat
```

### Claude Desktop Integration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

Restart Claude Desktop to enable the integration.

## Context Types

libra organizes context into three types:

| Type | Description | Examples |
|------|-------------|----------|
| **Knowledge** | Facts, documentation, reference material | API docs, technical specs, project info |
| **Preference** | How you like things done | Coding style, communication preferences |
| **History** | Past decisions and events | Previous architectural choices, bugs fixed |

## CLI Commands

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

## API Endpoints

When running with `libra serve --http`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/contexts` | GET | List contexts |
| `/api/v1/contexts` | POST | Create context |
| `/api/v1/contexts/{id}` | GET | Get context |
| `/api/v1/contexts/{id}` | PUT | Update context |
| `/api/v1/contexts/{id}` | DELETE | Delete context |
| `/api/v1/query` | POST | Get context for task |
| `/api/v1/search` | POST | Semantic search |
| `/api/v1/audit` | GET | View audit log |
| `/api/v1/stats` | GET | Storage statistics |
| `/docs` | GET | OpenAPI documentation |

## Web UI

Access at `http://localhost:8377` when running `libra serve --http`:

- **Dashboard**: Overview of context store and statistics
- **Contexts**: Browse, search, and manage contexts
- **Audit Log**: Review what context was served to agents
- **Settings**: Configure libra behavior

## Configuration

Configuration file: `~/.libra/config.yaml`

```yaml
librarian:
  mode: hybrid  # rules, llm, or hybrid
  llm:
    provider: gemini
    model: gemini-2.5-flash

embedding:
  provider: gemini
  model: gemini-embedding-001
  dimensions: 768

defaults:
  token_budget: 2000
  chunk_size: 512
  min_relevance: 0.5

server:
  http_port: 8377
  http_host: 127.0.0.1
```

## Python API

```python
from libra import LibraService, ContextType

# Create service
service = LibraService()

# Add context
context = service.add_context(
    content="Our API uses REST with JSON responses",
    context_type=ContextType.KNOWLEDGE,
    tags=["api", "architecture"]
)

# Query for relevant context
response = service.query(
    task="How should I design the new endpoint?",
    max_tokens=2000
)

for scored in response.contexts:
    print(f"{scored.relevance_score:.2f}: {scored.context.content[:100]}...")
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Type checking
mypy libra/

# Linting
ruff check libra/

# Format code
black libra/ tests/
```

## Technology Stack

- **Python 3.11+**
- **SQLite + sqlite-vec**: Local storage with vector search
- **Gemini**: LLM and embedding provider
- **FastAPI**: REST API
- **Typer**: CLI framework
- **MCP SDK**: Agent integration protocol

## Documentation

- [High-Level Design (HLD)](docs/HLD.md)
- [Low-Level Design (LLD)](docs/LLD.md)
- [Setup Guide](docs/SETUP.md)
- [API Reference](http://localhost:8377/docs) (when server running)

## License

Business Source License 1.1 - see LICENSE file for details.

This project is licensed under the Business Source License 1.1. After 4 years, the license automatically converts to Apache License 2.0.
