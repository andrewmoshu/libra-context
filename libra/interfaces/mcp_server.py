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

# Usage instructions for LLMs
USAGE_INSTRUCTIONS = """## Libra Context Orchestration - Usage Guide

### Primary Workflow: Call `get_context` BEFORE Responding

**IMPORTANT**: For best results, call `get_context` BEFORE generating your response to task-oriented queries.

### When to call `get_context`:
✓ BEFORE responding to any task-oriented user query
✓ When the user references personal context ("my project", "our discussion", "my preferences")
✓ When personalization would improve the response
✓ When the user asks for help with a task
✓ When previous context might inform the current request

### When NOT to call `get_context`:
✗ Simple greetings ("hi", "hello", "how are you")
✗ General knowledge questions with no personal context ("what is Python?", "explain quantum physics")
✗ When user explicitly opts out ("without using my context", "ignore my preferences")
✗ Meta questions about yourself or capabilities

### Recommended Workflow:
1. User sends message
2. **Call `get_context(task=<user's request>)` FIRST**
3. Review returned contexts and their relevance scores
4. Integrate relevant context into your response
5. Respond to user with personalized, context-aware answer

### Tool Priority (order of typical usage):
1. `get_context` - Priority 1.0 (call first, before responding)
2. `remember` - Priority 0.7 (call when user shares important info)
3. `search` - Priority 0.6 (call when user wants to find specific stored info)
4. `list_contexts` - Priority 0.5 (call when user wants to see what's stored)
5. `get_stats` - Priority 0.4 (call for overview of knowledge base)
6. `forget` - Priority 0.3 (call when user wants to delete context)

### Other Tools:
- `remember`: Save important context for future use (call AFTER the user shares important information)
- `search`: Find specific information by semantic query
- `list_contexts`: See all stored contexts (with optional filters)
- `get_stats`: Get statistics about the knowledge base
- `forget`: Delete a specific context by ID

### Example Usage Pattern:
```
User: "Help me design the API for my e-commerce project"

1. Call: get_context(task="Help me design the API for my e-commerce project")
2. Receive: contexts about user's tech stack preferences, previous architectural decisions, coding style
3. Respond: Using context to provide personalized API design recommendations
4. Optional: Call remember() if user makes new decisions during the conversation
```

### Context Types:
- **knowledge**: Facts, information, documentation
- **preference**: User preferences, coding style, communication style
- **history**: Past decisions, conversations, project history
"""

# Create MCP server
mcp = FastMCP(
    name="libra",
    instructions="""Intelligent Context Orchestration for AI Agents.

🎯 PRIMARY INSTRUCTION: Call `get_context()` BEFORE responding to task-oriented queries.

Quick Start:
1. For task-oriented queries → Call get_context(task=<user request>) FIRST
2. Review the returned contexts and integrate them into your response
3. After user shares important info → Call remember() to save it
4. For finding specific stored info → Call search()

Call get_usage_instructions() for detailed guidance on when and how to use each tool.

Tools: get_context, remember, search, forget, list_contexts, get_stats, get_usage_instructions
Resources: libra://instructions, libra://context-summary, libra://stats, libra://contexts/*""",
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

    ⚡ INVOCATION HINT: Call this BEFORE responding to task-oriented queries

    📋 METADATA:
      - invocation_hint: pre_response
      - priority_hint: 1.0 (highest priority - call first)
      - phase_hint: context_gathering
      - read_only: true
      - idempotent: true

    ✅ TRIGGER PATTERNS (when to call):
      - User asks for help with a task
      - User references personal/professional context
      - User mentions "my project", "our discussion", "my preferences"
      - Questions that could benefit from personalization
      - Technical or creative tasks

    ❌ SKIP PATTERNS (when NOT to call):
      - Simple greetings ("hi", "hello")
      - General knowledge questions with no personal context
      - User explicitly says "don't use context" or "ignore my preferences"
      - Meta questions about the assistant's capabilities

    ---

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

    📋 METADATA:
      - invocation_hint: on_demand
      - priority_hint: 0.7
      - phase_hint: action
      - read_only: false
      - idempotent: false

    ✅ TRIGGER PATTERNS (when to call):
      - User shares important information to remember
      - User makes a decision ("I've decided to...", "We'll use...")
      - User expresses a preference ("I prefer...", "I like...")
      - User provides facts about their project/work
      - After a meaningful discussion that should be saved

    ❌ SKIP PATTERNS (when NOT to call):
      - Temporary or transient information
      - Information already well-documented elsewhere
      - User hasn't shared anything new or important

    ---

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

    📋 METADATA:
      - invocation_hint: on_demand
      - priority_hint: 0.6
      - phase_hint: context_gathering
      - read_only: true
      - idempotent: true

    ✅ TRIGGER PATTERNS (when to call):
      - User asks "do I have context about..."
      - User wants to find specific stored information
      - User asks "what did I say about..."
      - User wants to verify what's been remembered

    ---

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

    📋 METADATA:
      - invocation_hint: on_demand
      - priority_hint: 0.3
      - phase_hint: action
      - read_only: false
      - idempotent: true
      - destructive: true

    ✅ TRIGGER PATTERNS (when to call):
      - User asks to delete/remove/forget specific context
      - User says information is outdated or incorrect
      - User wants to clean up their knowledge base

    ---

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

    📋 METADATA:
      - invocation_hint: on_demand
      - priority_hint: 0.5
      - phase_hint: context_gathering
      - read_only: true
      - idempotent: true

    ✅ TRIGGER PATTERNS (when to call):
      - User asks "what do you know about me?"
      - User wants to see all stored contexts
      - User asks "show me my preferences"
      - User wants an overview of the knowledge base

    ---

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

    📋 METADATA:
      - invocation_hint: on_demand
      - priority_hint: 0.4
      - phase_hint: context_gathering
      - read_only: true
      - idempotent: true

    ✅ TRIGGER PATTERNS (when to call):
      - User asks "how much do you know about me?"
      - User wants statistics about the knowledge base
      - User asks about storage or context counts

    ---

    Returns:
        JSON with storage statistics
    """
    service = get_service()
    stats = service.get_stats()

    return json.dumps(stats)


@mcp.tool()
def get_usage_instructions() -> str:
    """Get instructions for how an LLM should use libra tools.

    📋 METADATA:
      - invocation_hint: on_session_start
      - priority_hint: 0.9 (call early in a new session)
      - phase_hint: initialization
      - read_only: true
      - idempotent: true

    ✅ TRIGGER PATTERNS (when to call):
      - At the start of a new conversation session
      - When an LLM needs guidance on libra usage
      - When integrating libra for the first time

    ---

    Call this once at the start of a session to understand libra's capabilities
    and best practices for using its tools.

    Returns:
        Comprehensive usage guide for LLMs
    """
    return USAGE_INSTRUCTIONS


# Resources


@mcp.resource("libra://instructions")
def resource_instructions() -> str:
    """Usage instructions for LLMs on how to use libra tools.

    Clients can auto-inject this into LLM context for automatic guidance.
    """
    return USAGE_INSTRUCTIONS


@mcp.resource("libra://context-summary")
def resource_context_summary() -> str:
    """Summary of the user's context knowledge base.

    Provides an overview of what context is available without retrieving full content.
    Useful for LLMs to understand what information is stored.
    """
    service = get_service()
    stats = service.get_stats()
    contexts = service.list_contexts(limit=50)

    summary = {
        "stats": stats,
        "sample_contexts": [
            {
                "id": str(c.id),
                "type": c.type,
                "preview": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                "tags": c.tags,
            }
            for c in contexts
        ],
        "usage_hint": "Use get_context() with a task description to retrieve relevant contexts for your response."
    }

    return json.dumps(summary, indent=2)


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


def run_mcp_server() -> None:
    """Run the MCP server in stdio mode."""
    mcp.run()


if __name__ == "__main__":
    run_mcp_server()
