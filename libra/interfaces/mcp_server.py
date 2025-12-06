"""MCP (Model Context Protocol) server for libra.

Provides tools for AI agents to interact with libra:
- get_context: Get relevant context for a task
- remember: Save new context
- search: Search existing contexts
- forget: Delete a context
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from libra.core.models import ContextType, RequestSource
from libra.service import LibraService

# Create MCP server
mcp = FastMCP(
    name="libra",
    instructions="Intelligent Context Orchestration for AI Agents. Use get_context to retrieve relevant context for tasks, remember to save new context, search to find specific information, and forget to remove outdated context.",
)

# Global service instance
_service: LibraService | None = None


def get_service() -> LibraService:
    """Get or create the service instance."""
    global _service
    if _service is None:
        _service = LibraService()
    return _service


# Tools


@mcp.tool()
def get_context(
    task: str,
    max_tokens: int = 2000,
    types: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Get relevant context for a task.

    This is the main feature of libra - intelligent context selection.
    The librarian analyzes the task and returns the most relevant contexts
    from your knowledge base.

    Args:
        task: Description of the task you need context for
        max_tokens: Maximum tokens for returned context (default 2000)
        types: Comma-separated context types to include (knowledge,preference,history)
        tags: Comma-separated tags to filter by

    Returns:
        JSON with selected contexts and their relevance scores
    """
    service = get_service()

    # Parse filters
    type_list = None
    if types:
        type_list = [ContextType(t.strip().lower()) for t in types.split(",")]

    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    # Query for context
    response = service.query(
        task=task,
        max_tokens=max_tokens,
        types=type_list,
        tags=tag_list,
        agent_id="mcp-client",
        request_source=RequestSource.MCP,
    )

    # Format response
    result = {
        "tokens_used": response.tokens_used,
        "contexts": [
            {
                "id": str(sc.context.id),
                "type": sc.context.type,
                "content": sc.context.content,
                "relevance": sc.relevance_score,
                "tags": sc.context.tags,
            }
            for sc in response.contexts
        ],
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def remember(
    content: str,
    type: str = "knowledge",
    tags: Optional[str] = None,
) -> str:
    """Save new context for future use.

    Use this to remember important information that should be
    available in future conversations.

    Args:
        content: The information to remember
        type: Context type - knowledge, preference, or history
        tags: Comma-separated tags for organization

    Returns:
        JSON with the created context ID and confirmation
    """
    service = get_service()

    try:
        context_type = ContextType(type.lower())
    except ValueError:
        return json.dumps({
            "success": False,
            "error": f"Invalid type: {type}. Use knowledge, preference, or history.",
        })

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    context = service.add_context(
        content=content,
        context_type=context_type,
        tags=tag_list,
        source="mcp-remember",
    )

    return json.dumps({
        "success": True,
        "id": str(context.id),
        "type": context.type,
        "tags": context.tags,
    })


@mcp.tool()
def search(
    query: str,
    type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search existing contexts by semantic similarity.

    Use this to find specific information in your knowledge base.

    Args:
        query: Search query
        type: Optional type filter (knowledge, preference, history)
        limit: Maximum number of results (default 10)

    Returns:
        JSON with matching contexts and similarity scores
    """
    service = get_service()

    type_list = None
    if type:
        try:
            type_list = [ContextType(type.lower())]
        except ValueError:
            return json.dumps({
                "success": False,
                "error": f"Invalid type: {type}",
            })

    results = service.search_contexts(query=query, types=type_list, limit=limit)

    return json.dumps({
        "results": [
            {
                "id": str(ctx.id),
                "type": ctx.type,
                "content": ctx.content[:500] + "..." if len(ctx.content) > 500 else ctx.content,
                "similarity": round(score, 3),
                "tags": ctx.tags,
            }
            for ctx, score in results
        ],
    })


@mcp.tool()
def forget(context_id: str) -> str:
    """Delete a context by ID.

    Use this to remove outdated or incorrect information.

    Args:
        context_id: The ID of the context to delete

    Returns:
        JSON with success status
    """
    service = get_service()

    deleted = service.delete_context(context_id)

    return json.dumps({
        "success": deleted,
        "id": context_id,
        "message": "Context deleted" if deleted else "Context not found",
    })


@mcp.tool()
def list_contexts(
    type: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 20,
) -> str:
    """List all contexts with optional filtering.

    Use this to see what context is available.

    Args:
        type: Optional type filter (knowledge, preference, history)
        tags: Comma-separated tags to filter by
        limit: Maximum number of results (default 20)

    Returns:
        JSON with list of contexts
    """
    service = get_service()

    type_list = None
    if type:
        try:
            type_list = [ContextType(type.lower())]
        except ValueError:
            return json.dumps({"error": f"Invalid type: {type}"})

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    contexts = service.list_contexts(types=type_list, tags=tag_list, limit=limit)

    return json.dumps({
        "count": len(contexts),
        "contexts": [
            {
                "id": str(c.id),
                "type": c.type,
                "content": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                "tags": c.tags,
                "source": c.source,
            }
            for c in contexts
        ],
    })


@mcp.tool()
def get_stats() -> str:
    """Get statistics about the context store.

    Returns:
        JSON with storage statistics
    """
    service = get_service()
    stats = service.get_stats()

    return json.dumps(stats)


# Resources


@mcp.resource("libra://stats")
def resource_stats() -> str:
    """System statistics."""
    service = get_service()
    return json.dumps(service.get_stats())


@mcp.resource("libra://contexts/all")
def resource_all_contexts() -> str:
    """All contexts (first 100)."""
    service = get_service()
    contexts = service.list_contexts(limit=100)
    return json.dumps([
        {
            "id": str(c.id),
            "type": c.type,
            "content": c.content[:200] + "...",
            "tags": c.tags,
        }
        for c in contexts
    ])


@mcp.resource("libra://contexts/knowledge")
def resource_knowledge() -> str:
    """Knowledge contexts."""
    service = get_service()
    contexts = service.list_contexts(types=[ContextType.KNOWLEDGE], limit=100)
    return json.dumps([
        {"id": str(c.id), "content": c.content[:200], "tags": c.tags}
        for c in contexts
    ])


@mcp.resource("libra://contexts/preferences")
def resource_preferences() -> str:
    """Preference contexts."""
    service = get_service()
    contexts = service.list_contexts(types=[ContextType.PREFERENCE], limit=100)
    return json.dumps([
        {"id": str(c.id), "content": c.content[:200], "tags": c.tags}
        for c in contexts
    ])


@mcp.resource("libra://contexts/history")
def resource_history() -> str:
    """History contexts."""
    service = get_service()
    contexts = service.list_contexts(types=[ContextType.HISTORY], limit=100)
    return json.dumps([
        {"id": str(c.id), "content": c.content[:200], "tags": c.tags}
        for c in contexts
    ])


# Prompts


@mcp.prompt()
def with_context(task: str) -> str:
    """Get context for a task and format it for use in a conversation.

    This prompt fetches relevant context and formats it nicely for inclusion
    in a conversation with an AI assistant.
    """
    service = get_service()
    response = service.query(
        task=task,
        max_tokens=2000,
        request_source=RequestSource.MCP,
    )

    if not response.contexts:
        return f"Task: {task}\n\n(No relevant context found in knowledge base)"

    context_text = "\n\n---\n\n".join([
        f"**{sc.context.type.upper()}** (relevance: {sc.relevance_score:.2f})\n{sc.context.content}"
        for sc in response.contexts
    ])

    return f"""Task: {task}

## Relevant Context from Knowledge Base

{context_text}

---

Please use the context above to help with the task."""


@mcp.prompt()
def explain_context() -> str:
    """Explain what context libra has available.

    Returns a summary of the context store contents.
    """
    service = get_service()
    stats = service.get_stats()

    by_type = stats.get("contexts_by_type", {})
    total = stats.get("total_contexts", 0)

    return f"""# libra Context Summary

**Total Contexts:** {total}

**By Type:**
- Knowledge: {by_type.get('knowledge', 0)} items
- Preferences: {by_type.get('preference', 0)} items
- History: {by_type.get('history', 0)} items

To get relevant context for a task, use the `get_context` tool with a description of what you're working on.

To add new context, use the `remember` tool with the content you want to save."""


def run_mcp_server():
    """Run the MCP server in stdio mode."""
    mcp.run()


if __name__ == "__main__":
    run_mcp_server()
