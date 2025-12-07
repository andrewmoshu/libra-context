"""Interface layer for libra.

Provides multiple ways to interact with libra:
- MCP Server for AI agent integration
- REST API for programmatic access
- CLI for management and scripting
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typer
    from fastapi import FastAPI


# Import functions lazily to avoid circular imports
def create_cli_app() -> "typer.Typer":
    """Create and return the CLI app."""
    from libra.interfaces.cli import create_cli_app as _create_cli_app
    return _create_cli_app()


def create_api_app() -> "FastAPI":
    """Create and return the FastAPI app."""
    from libra.interfaces.api import create_api_app as _create_api_app
    return _create_api_app()


def run_mcp_server() -> None:
    """Run the MCP server."""
    from libra.interfaces.mcp_server import run_mcp_server as _run_mcp_server
    _run_mcp_server()


__all__ = [
    "create_cli_app",
    "create_api_app",
    "run_mcp_server",
]
