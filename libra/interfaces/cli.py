"""Command-line interface for libra using Typer."""

import json
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from libra.core.config import LibraConfig
from libra.core.models import ContextType, LibrarianMode
from libra.service import LibraService

# Create CLI app
app = typer.Typer(
    name="libra",
    help="Intelligent Context Orchestration for AI Agents",
    add_completion=False,
)

# Rich console for output
console = Console()

# Global service instance
_service: LibraService | None = None


def get_service() -> LibraService:
    """Get or create the service instance."""
    global _service
    if _service is None:
        _service = LibraService()
    return _service


# Context Management Commands


@app.command("add")
def add_context(
    content: str = typer.Argument(..., help="The context content to add"),
    type: str = typer.Option(
        "knowledge",
        "--type",
        "-t",
        help="Context type: knowledge, preference, or history",
    ),
    tags: Optional[str] = typer.Option(
        None, "--tags", help="Comma-separated tags"
    ),
    source: str = typer.Option("manual", "--source", "-s", help="Source identifier"),
) -> None:
    """Add a new context to libra."""
    service = get_service()

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        context_type = ContextType(type.lower())
    except ValueError:
        console.print(f"[red]Invalid type: {type}. Use knowledge, preference, or history.[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Adding context...", total=None)
        context = service.add_context(
            content=content,
            context_type=context_type,
            tags=tag_list,
            source=source,
        )

    console.print(Panel(
        f"[green]Context added successfully![/green]\n\n"
        f"ID: {context.id}\n"
        f"Type: {context.type}\n"
        f"Tags: {', '.join(context.tags) if context.tags else 'none'}",
        title="✓ Added",
    ))


@app.command("list")
def list_contexts(
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Filter by tags (comma-separated)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List contexts with optional filtering."""
    service = get_service()

    types = [ContextType(type.lower())] if type else None
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    contexts = service.list_contexts(types=types, tags=tag_list, limit=limit)

    if json_output:
        output = [
            {
                "id": str(c.id),
                "type": c.type,
                "content": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                "tags": c.tags,
                "source": c.source,
                "created_at": c.created_at.isoformat(),
            }
            for c in contexts
        ]
        console.print(json.dumps(output, indent=2))
        return

    if not contexts:
        console.print("[yellow]No contexts found.[/yellow]")
        return

    table = Table(title=f"Contexts ({len(contexts)} results)")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Type", width=10)
    table.add_column("Content", width=50)
    table.add_column("Tags", width=20)

    for ctx in contexts:
        content_preview = ctx.content[:50] + "..." if len(ctx.content) > 50 else ctx.content
        content_preview = content_preview.replace("\n", " ")
        table.add_row(
            str(ctx.id)[:8] + "...",
            ctx.type,
            content_preview,
            ", ".join(ctx.tags[:3]) + ("..." if len(ctx.tags) > 3 else ""),
        )

    console.print(table)


@app.command("show")
def show_context(
    context_id: str = typer.Argument(..., help="Context ID to show"),
) -> None:
    """Display details of a specific context."""
    service = get_service()

    try:
        context = service.get_context(context_id)
    except Exception:
        console.print(f"[red]Context not found: {context_id}[/red]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]ID:[/bold] {context.id}\n"
        f"[bold]Type:[/bold] {context.type}\n"
        f"[bold]Tags:[/bold] {', '.join(context.tags) if context.tags else 'none'}\n"
        f"[bold]Source:[/bold] {context.source}\n"
        f"[bold]Created:[/bold] {context.created_at.isoformat()}\n"
        f"[bold]Accessed:[/bold] {context.accessed_at.isoformat() if context.accessed_at else 'never'}\n"
        f"[bold]Access Count:[/bold] {context.access_count}\n\n"
        f"[bold]Content:[/bold]\n{context.content}",
        title="Context Details",
    ))


@app.command("delete")
def delete_context(
    context_id: str = typer.Argument(..., help="Context ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a context by ID."""
    service = get_service()

    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete context {context_id}?")
        if not confirm:
            raise typer.Abort()

    deleted = service.delete_context(context_id)

    if deleted:
        console.print(f"[green]Context {context_id} deleted.[/green]")
    else:
        console.print(f"[yellow]Context {context_id} not found.[/yellow]")


# Query Commands


@app.command("query")
def query_context(
    task: str = typer.Argument(..., help="Task description to get context for"),
    max_tokens: int = typer.Option(2000, "--max-tokens", "-m", help="Token budget"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Filter by tags"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get relevant context for a task."""
    service = get_service()

    types = [ContextType(type.lower())] if type else None
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Finding relevant context...", total=None)
        response = service.query(
            task=task,
            max_tokens=max_tokens,
            types=types,
            tags=tag_list,
        )

    if json_output:
        output = {
            "request_id": str(response.request_id),
            "tokens_used": response.tokens_used,
            "librarian_mode": response.librarian_mode,
            "contexts": [
                {
                    "id": str(sc.context.id),
                    "type": sc.context.type,
                    "content": sc.context.content,
                    "relevance_score": sc.relevance_score,
                    "tags": sc.context.tags,
                }
                for sc in response.contexts
            ],
        }
        console.print(json.dumps(output, indent=2))
        return

    if not response.contexts:
        console.print("[yellow]No relevant contexts found.[/yellow]")
        return

    console.print(Panel(
        f"[bold]Task:[/bold] {task}\n"
        f"[bold]Mode:[/bold] {response.librarian_mode}\n"
        f"[bold]Tokens Used:[/bold] {response.tokens_used}/{max_tokens}",
        title="Query Results",
    ))

    for i, sc in enumerate(response.contexts, 1):
        score_color = "green" if sc.relevance_score >= 0.7 else "yellow" if sc.relevance_score >= 0.4 else "dim"
        console.print(Panel(
            f"[{score_color}]Relevance: {sc.relevance_score:.2f}[/{score_color}]\n"
            f"Type: {sc.context.type} | Tags: {', '.join(sc.context.tags[:3])}\n\n"
            f"{sc.context.content[:500]}{'...' if len(sc.context.content) > 500 else ''}",
            title=f"[{i}] {str(sc.context.id)[:8]}...",
        ))


@app.command("search")
def search_contexts(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
) -> None:
    """Search contexts by semantic similarity."""
    service = get_service()

    types = [ContextType(type.lower())] if type else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Searching...", total=None)
        results = service.search_contexts(query=query, types=types, limit=limit)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Score", width=8)
    table.add_column("Type", width=10)
    table.add_column("Content", width=50)

    for ctx, score in results:
        content_preview = ctx.content[:50] + "..." if len(ctx.content) > 50 else ctx.content
        content_preview = content_preview.replace("\n", " ")
        table.add_row(
            str(ctx.id)[:8] + "...",
            f"{score:.2f}",
            ctx.type,
            content_preview,
        )

    console.print(table)


# Ingestion Commands


@app.command("ingest")
def ingest(
    path: Path = typer.Argument(..., help="Path to file or directory"),
    type: str = typer.Option(
        "knowledge",
        "--type",
        "-t",
        help="Context type: knowledge, preference, or history",
    ),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for changes (not yet implemented)"),
) -> None:
    """Ingest a file or directory."""
    service = get_service()

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        context_type = ContextType(type.lower())
    except ValueError:
        console.print(f"[red]Invalid type: {type}[/red]")
        raise typer.Exit(1)

    if not path.exists():
        console.print(f"[red]Path does not exist: {path}[/red]")
        raise typer.Exit(1)

    if watch:
        console.print("[yellow]Watch mode not yet implemented.[/yellow]")
        raise typer.Exit(1)

    def progress_callback(file_path: str, current: int, total: int) -> None:
        console.print(f"[dim]Processing {current}/{total}: {file_path}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Ingesting...", total=None)

        if path.is_file():
            contexts = service.ingest_file(path, context_type, tag_list)
        else:
            contexts = service.ingest_directory(path, context_type, tag_list, progress_callback)

    console.print(Panel(
        f"[green]Ingestion complete![/green]\n\n"
        f"Contexts created: {len(contexts)}\n"
        f"Source: {path}",
        title="✓ Ingested",
    ))


# Server Commands


@app.command("serve")
def serve(
    http: bool = typer.Option(False, "--http", help="Start HTTP server"),
    port: int = typer.Option(8377, "--port", "-p", help="HTTP port"),
    host: str = typer.Option("127.0.0.1", "--host", help="HTTP host"),
    all_servers: bool = typer.Option(False, "--all", help="Start both MCP and HTTP"),
) -> None:
    """Start the libra server (MCP stdio mode by default)."""
    if http or all_servers:
        console.print(f"[blue]Starting HTTP server on {host}:{port}...[/blue]")
        console.print(f"[dim]Web UI: http://{host}:{port}/[/dim]")
        console.print(f"[dim]API Docs: http://{host}:{port}/docs[/dim]")
        try:
            from libra.interfaces.api import run_server
            run_server(host=host, port=port)
        except ImportError:
            console.print("[red]FastAPI not installed. Install with: pip install fastapi uvicorn[/red]")
            raise typer.Exit(1)
    else:
        console.print("[blue]Starting MCP server (stdio mode)...[/blue]")
        try:
            from libra.interfaces.mcp_server import run_mcp_server
            run_mcp_server()
        except ImportError as e:
            console.print(f"[red]MCP SDK not installed: {e}[/red]")
            raise typer.Exit(1)


# Audit Commands


@app.command("audit")
def audit(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results"),
    export: bool = typer.Option(False, "--export", help="Export as JSON"),
) -> None:
    """View audit log entries."""
    service = get_service()

    entries = service.get_audit_log(agent_id=agent, limit=limit)

    if export:
        output = [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "agent_id": e.agent_id,
                "task": e.task,
                "contexts_served": len(e.contexts_served),
                "tokens_used": e.tokens_used,
                "latency_ms": e.latency_ms,
            }
            for e in entries
        ]
        console.print(json.dumps(output, indent=2))
        return

    if not entries:
        console.print("[yellow]No audit entries found.[/yellow]")
        return

    table = Table(title=f"Audit Log ({len(entries)} entries)")
    table.add_column("Time", width=20)
    table.add_column("Agent", width=15)
    table.add_column("Task", width=40)
    table.add_column("Contexts", width=8)
    table.add_column("Tokens", width=8)

    for entry in entries:
        task_preview = entry.task[:35] + "..." if len(entry.task) > 35 else entry.task
        table.add_row(
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            entry.agent_id or "unknown",
            task_preview,
            str(len(entry.contexts_served)),
            str(entry.tokens_used),
        )

    console.print(table)


# Configuration Commands


config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    """Display current configuration."""
    service = get_service()
    config = service.config

    console.print(Panel(
        f"[bold]Data Directory:[/bold] {config.data_dir}\n"
        f"[bold]Log Level:[/bold] {config.log_level}\n\n"
        f"[bold]Librarian:[/bold]\n"
        f"  Mode: {config.librarian.mode}\n"
        f"  LLM: {config.librarian.llm.model}\n"
        f"  Rules: {len(config.librarian.rules)}\n\n"
        f"[bold]Embedding:[/bold]\n"
        f"  Provider: {config.embedding.provider}\n"
        f"  Model: {config.embedding.model}\n"
        f"  Dimensions: {config.embedding.dimensions}\n\n"
        f"[bold]Server:[/bold]\n"
        f"  HTTP Port: {config.server.http_port}\n"
        f"  HTTP Host: {config.server.http_host}\n\n"
        f"[bold]Defaults:[/bold]\n"
        f"  Token Budget: {config.defaults.token_budget}\n"
        f"  Chunk Size: {config.defaults.chunk_size}\n"
        f"  Min Relevance: {config.defaults.min_relevance}",
        title="libra Configuration",
    ))


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., librarian.mode)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    service = get_service()
    config = service.config

    # Simple key mapping
    if key == "librarian.mode":
        config.librarian.mode = LibrarianMode(value)
    elif key == "defaults.token_budget":
        config.defaults.token_budget = int(value)
    elif key == "defaults.chunk_size":
        config.defaults.chunk_size = int(value)
    elif key == "server.http_port":
        config.server.http_port = int(value)
    else:
        console.print(f"[red]Unknown configuration key: {key}[/red]")
        raise typer.Exit(1)

    config.save()
    console.print(f"[green]Set {key} = {value}[/green]")


@config_app.command("edit")
def config_edit() -> None:
    """Open configuration in editor."""
    import os

    service = get_service()
    config_path = service.config.config_path

    # Ensure config exists
    if not config_path.exists():
        service.config.save()

    editor = os.environ.get("EDITOR", "vim")

    console.print(f"[blue]Opening {config_path} in {editor}...[/blue]")

    # Use subprocess.run with list args to prevent shell injection
    try:
        result = subprocess.run([editor, str(config_path)], check=False)
        if result.returncode != 0:
            console.print(f"[yellow]Editor exited with code {result.returncode}[/yellow]")
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor}. Set EDITOR environment variable.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to open editor: {e}[/red]")
        raise typer.Exit(1)


# Utility Commands


@app.command("stats")
def stats() -> None:
    """Show storage statistics."""
    service = get_service()
    data = service.get_stats()

    console.print(Panel(
        f"[bold]Total Contexts:[/bold] {data.get('total_contexts', 0)}\n"
        f"[bold]With Embeddings:[/bold] {data.get('contexts_with_embeddings', 0)}\n"
        f"[bold]Audit Entries:[/bold] {data.get('total_audit_entries', 0)}\n\n"
        f"[bold]By Type:[/bold]\n" +
        "\n".join(
            f"  {t}: {c}" for t, c in data.get('contexts_by_type', {}).items()
        ),
        title="libra Statistics",
    ))


@app.command("export")
def export_contexts(
    output: Path = typer.Option(
        Path("libra_export.json"),
        "--output",
        "-o",
        help="Output file path",
    ),
) -> None:
    """Export all contexts to JSON."""
    service = get_service()

    contexts = service.list_contexts(limit=10000)

    output_data = [
        {
            "id": str(c.id),
            "type": c.type,
            "content": c.content,
            "tags": c.tags,
            "source": c.source,
            "created_at": c.created_at.isoformat(),
            "access_count": c.access_count,
        }
        for c in contexts
    ]

    output.write_text(json.dumps(output_data, indent=2))
    console.print(f"[green]Exported {len(contexts)} contexts to {output}[/green]")


@app.command("import")
def import_contexts(
    input_file: Path = typer.Argument(..., help="JSON file to import"),
) -> None:
    """Import contexts from JSON."""
    service = get_service()

    if not input_file.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(1)

    data = json.loads(input_file.read_text())

    count = 0
    for item in data:
        try:
            service.add_context(
                content=item["content"],
                context_type=ContextType(item["type"]),
                tags=item.get("tags", []),
                source=item.get("source", "import"),
            )
            count += 1
        except Exception as e:
            console.print(f"[yellow]Failed to import: {e}[/yellow]")

    console.print(f"[green]Imported {count} contexts from {input_file}[/green]")


@app.command("chat")
def chat_command(
    max_tokens: int = typer.Option(3000, "--max-tokens", "-m", help="Token budget for context"),
) -> None:
    """Interactive chat with the Librarian about your contexts.

    Ask questions about what contexts you have, get recommendations,
    and have the Librarian help you understand your knowledge base.
    """
    import os

    import google.generativeai as genai

    service = get_service()

    # Check for API key
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        console.print("[red]GOOGLE_AI_API_KEY environment variable is required for chat mode.[/red]")
        raise typer.Exit(1)

    genai.configure(api_key=api_key)

    # Get stats for system context
    stats = service.get_stats()
    by_type = stats.get("contexts_by_type", {})
    total_contexts = stats.get("total_contexts", 0)

    # Build system prompt with context about the user's knowledge base
    system_prompt = f"""You are the libra Librarian, an intelligent assistant that helps users
understand and work with their personal knowledge base.

Current knowledge base statistics:
- Total contexts: {total_contexts}
- Knowledge items: {by_type.get('knowledge', 0)}
- Preferences: {by_type.get('preference', 0)}
- History items: {by_type.get('history', 0)}

You can help users:
1. Understand what context they have stored
2. Suggest how to organize their knowledge
3. Answer questions about their stored information
4. Recommend new contexts to add based on their needs

Be helpful, concise, and proactive in suggesting how to improve their context library.
When asked about specific topics, you can search the knowledge base and provide relevant information."""

    # Initialize chat model
    model = genai.GenerativeModel(
        model_name=service.config.librarian.llm.model,
        system_instruction=system_prompt,
    )
    chat = model.start_chat()

    console.print(Panel(
        f"[blue]Welcome to libra Chat![/blue]\n\n"
        f"You have {total_contexts} contexts in your knowledge base.\n"
        f"Ask me anything about your stored information.\n\n"
        f"[dim]Type 'quit' or 'exit' to leave, 'help' for commands.[/dim]",
        title="🔮 Librarian Chat",
    ))

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "help":
            console.print(Panel(
                "[bold]Available commands:[/bold]\n\n"
                "• quit/exit/q - Exit chat\n"
                "• help - Show this help\n"
                "• /search <query> - Search your contexts\n"
                "• /stats - Show knowledge base statistics\n\n"
                "[bold]Or just ask anything about your knowledge base![/bold]",
                title="Help",
            ))
            continue

        if user_input.startswith("/search "):
            query = user_input[8:].strip()
            if query:
                results = service.search_contexts(query=query, limit=5)
                if results:
                    console.print(f"\n[bold]Found {len(results)} results for '{query}':[/bold]")
                    for ctx, score in results:
                        preview = ctx.content[:100].replace("\n", " ")
                        console.print(f"  [{ctx.type}] {preview}... (score: {score:.2f})")
                else:
                    console.print(f"[yellow]No results found for '{query}'[/yellow]")
            continue

        if user_input.lower() == "/stats":
            console.print(Panel(
                f"[bold]Total Contexts:[/bold] {stats.get('total_contexts', 0)}\n"
                f"[bold]With Embeddings:[/bold] {stats.get('contexts_with_embeddings', 0)}\n"
                f"[bold]Audit Entries:[/bold] {stats.get('total_audit_entries', 0)}\n\n"
                f"[bold]By Type:[/bold]\n" +
                "\n".join(f"  {t}: {c}" for t, c in stats.items() if t == "contexts_by_type" for t, c in stats.get("contexts_by_type", {}).items()),
                title="Statistics",
            ))
            continue

        # For other queries, first check if we should include context from the knowledge base
        enriched_prompt = user_input

        # If the user seems to be asking about specific topics, fetch relevant context
        search_keywords = ["what", "how", "tell me", "show", "find", "about", "information", "know"]
        if any(kw in user_input.lower() for kw in search_keywords):
            try:
                response = service.query(
                    task=user_input,
                    max_tokens=max_tokens,
                )
                if response.contexts:
                    context_text = "\n\n".join([
                        f"[{sc.context.type.upper()}] {sc.context.content[:500]}"
                        for sc in response.contexts[:3]
                    ])
                    enriched_prompt = f"""Based on the user's knowledge base, here's relevant context:

{context_text}

User question: {user_input}

Please answer using the context above when relevant."""
            except Exception:
                pass  # Fall back to unenriched prompt

        try:
            with console.status("[bold blue]Thinking...[/bold blue]"):
                chat_response = chat.send_message(enriched_prompt)

            console.print(f"\n[bold blue]Librarian:[/bold blue] {chat_response.text}")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


@app.command("init")
def init() -> None:
    """Initialize libra (create config directory and default config)."""
    config = LibraConfig()
    config.ensure_data_dir()
    config.save()

    console.print(Panel(
        f"[green]libra initialized![/green]\n\n"
        f"Data directory: {config.data_dir}\n"
        f"Config file: {config.config_path}\n\n"
        f"Next steps:\n"
        f"1. Set your API key: export GOOGLE_AI_API_KEY=your-key\n"
        f"2. Add some context: libra add 'Your context here'\n"
        f"3. Query for context: libra query 'Your task'",
        title="✓ Initialized",
    ))


def create_cli_app() -> typer.Typer:
    """Create and return the CLI app."""
    return app


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
