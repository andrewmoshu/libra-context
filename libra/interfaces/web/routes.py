"""Web UI routes for libra.

Provides browser-based interface for managing contexts, viewing audit logs,
and configuring libra. Works without JavaScript for core functions.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Form, Query, Request

if TYPE_CHECKING:
    from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from libra.core.exceptions import ContextNotFoundError
from libra.core.models import ContextType
from libra.service import LibraService

# Setup paths
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

# Templates instance
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Router
router = APIRouter()

# Global service instance (shared with API)
_service: LibraService | None = None


def get_service() -> LibraService:
    """Get or create the service instance."""
    global _service
    if _service is None:
        _service = LibraService()
    return _service


def set_service(service: LibraService) -> None:
    """Set the service instance (for sharing with API)."""
    global _service
    _service = service


# Dashboard
@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request) -> HTMLResponse:
    """Dashboard page with overview statistics."""
    service = get_service()

    stats = service.get_stats()
    recent_audit = service.get_audit_log(limit=5)
    recent_contexts = service.list_contexts(limit=5)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "stats": stats,
            "recent_audit": recent_audit,
            "recent_contexts": recent_contexts,
        },
    )


# Contexts List
@router.get("/contexts", response_class=HTMLResponse, name="contexts_list")
async def contexts_list(
    request: Request,
    page: int = Query(1, ge=1),
    type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> HTMLResponse:
    """List contexts with filtering and pagination."""
    service = get_service()

    per_page = 20
    offset = (page - 1) * per_page

    # Parse filters
    type_list = None
    if type:
        try:
            type_list = [ContextType(type.lower())]
        except ValueError:
            type_list = None

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    # Get contexts
    contexts = service.list_contexts(
        types=type_list,
        tags=tag_list,
        limit=per_page,
        offset=offset,
    )

    # Get total count (approximate for now)
    all_contexts = service.list_contexts(types=type_list, tags=tag_list, limit=10000)
    total_contexts = len(all_contexts)
    total_pages = math.ceil(total_contexts / per_page) if total_contexts > 0 else 1

    return templates.TemplateResponse(
        request=request,
        name="contexts.html",
        context={
            "active_page": "contexts",
            "contexts": contexts,
            "current_page": page,
            "total_pages": total_pages,
            "total_contexts": total_contexts,
            "filter_type": type,
            "filter_tags": tags,
            "search_query": search,
        },
    )


# Add Context Page
@router.get("/contexts/add", response_class=HTMLResponse, name="add_context_page")
async def add_context_page(request: Request) -> HTMLResponse:
    """Add context form page."""
    return templates.TemplateResponse(
        request=request,
        name="add_context.html",
        context={
            "active_page": "add",
            "form_data": None,
        },
    )


# Add Context Submit
@router.post("/contexts/add", response_class=HTMLResponse, name="add_context_submit")
async def add_context_submit(
    request: Request,
    content: str = Form(...),
    type: str = Form("knowledge"),
    tags: str = Form(""),
    source: str = Form("manual"),
) -> Response:
    """Handle add context form submission."""
    service = get_service()

    try:
        context_type = ContextType(type.lower())
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="add_context.html",
            context={
                "active_page": "add",
                "form_data": {"content": content, "type": type, "tags": tags, "source": source},
                "messages": [{"type": "error", "text": f"Invalid context type: {type}"}],
            },
        )

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    context = service.add_context(
        content=content,
        context_type=context_type,
        tags=tag_list,
        source=source,
    )

    return RedirectResponse(
        url=request.url_for("context_detail", context_id=str(context.id)),
        status_code=303,
    )


# Context Detail
@router.get("/contexts/{context_id}", response_class=HTMLResponse, name="context_detail")
async def context_detail(request: Request, context_id: str) -> HTMLResponse:
    """View context details."""
    service = get_service()

    try:
        context = service.get_context(context_id)
    except ContextNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="contexts.html",
            context={
                "active_page": "contexts",
                "contexts": [],
                "messages": [{"type": "error", "text": f"Context not found: {context_id}"}],
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="context_detail.html",
        context={
            "active_page": "contexts",
            "context": context,
        },
    )


# Edit Context Page
@router.get("/contexts/{context_id}/edit", response_class=HTMLResponse, name="edit_context_page")
async def edit_context_page(request: Request, context_id: str) -> Response:
    """Edit context form page."""
    service = get_service()

    try:
        context = service.get_context(context_id)
    except ContextNotFoundError:
        return RedirectResponse(url=request.url_for("contexts_list"), status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="edit_context.html",
        context={
            "active_page": "contexts",
            "context": context,
        },
    )


# Edit Context Submit
@router.post("/contexts/{context_id}/edit", response_class=HTMLResponse, name="edit_context_submit")
async def edit_context_submit(
    request: Request,
    context_id: str,
    content: str = Form(...),
    tags: str = Form(""),
) -> Response:
    """Handle edit context form submission."""
    service = get_service()

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        service.update_context(
            context_id=context_id,
            content=content,
            tags=tag_list,
        )
    except ContextNotFoundError:
        return RedirectResponse(url=request.url_for("contexts_list"), status_code=303)

    return RedirectResponse(
        url=request.url_for("context_detail", context_id=context_id),
        status_code=303,
    )


# Delete Context Confirmation
@router.get("/contexts/{context_id}/delete", response_class=HTMLResponse, name="delete_context_confirm")
async def delete_context_confirm(request: Request, context_id: str) -> Response:
    """Delete confirmation page."""
    service = get_service()

    try:
        context = service.get_context(context_id)
    except ContextNotFoundError:
        return RedirectResponse(url=request.url_for("contexts_list"), status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="delete_context.html",
        context={
            "active_page": "contexts",
            "context": context,
        },
    )


# Delete Context Submit
@router.post("/contexts/{context_id}/delete", name="delete_context_submit")
async def delete_context_submit(request: Request, context_id: str) -> Response:
    """Handle delete context form submission."""
    service = get_service()
    service.delete_context(context_id)
    return RedirectResponse(url=request.url_for("contexts_list"), status_code=303)


# Audit Log
@router.get("/audit", response_class=HTMLResponse, name="audit_page")
async def audit_page(
    request: Request,
    page: int = Query(1, ge=1),
    agent_id: Optional[str] = Query(None),
) -> HTMLResponse:
    """Audit log page."""
    service = get_service()

    per_page = 50
    offset = (page - 1) * per_page

    entries = service.get_audit_log(
        agent_id=agent_id if agent_id else None,
        limit=per_page,
        offset=offset,
    )

    # Get total count
    all_entries = service.get_audit_log(
        agent_id=agent_id if agent_id else None,
        limit=10000,
    )
    total_entries = len(all_entries)
    total_pages = math.ceil(total_entries / per_page) if total_entries > 0 else 1

    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "active_page": "audit",
            "entries": entries,
            "current_page": page,
            "total_pages": total_pages,
            "total_entries": total_entries,
            "filter_agent": agent_id,
        },
    )


# Settings Page
@router.get("/settings", response_class=HTMLResponse, name="settings_page")
async def settings_page(request: Request) -> HTMLResponse:
    """Settings page."""
    service = get_service()
    config = service.config
    stats = service.get_stats()

    # Get config as dict for display
    config_dict = {
        "librarian_mode": config.librarian.mode,
        "embedding_provider": config.embedding.provider,
        "embedding_model": config.embedding.model,
        "default_token_budget": config.defaults.token_budget,
        "default_chunk_size": config.defaults.chunk_size,
    }

    # Get rules
    rules = config.librarian.rules if hasattr(config.librarian, "rules") else []

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "config": config_dict,
            "stats": stats,
            "db_path": str(config.db_path),
            "rules": rules,
        },
    )


# Export Contexts
@router.get("/export", name="export_contexts")
async def export_contexts(request: Request) -> Response:
    """Export all contexts as JSON."""
    service = get_service()
    contexts = service.list_contexts(limit=100000)

    export_data = {
        "version": "1.0",
        "contexts": [
            {
                "id": str(ctx.id),
                "type": ctx.type,
                "content": ctx.content,
                "tags": ctx.tags,
                "source": ctx.source,
                "created_at": ctx.created_at.isoformat(),
                "updated_at": ctx.updated_at.isoformat(),
            }
            for ctx in contexts
        ],
    }

    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=libra-export.json"},
    )


def setup_web_ui(app: FastAPI, service: Optional[LibraService] = None) -> None:
    """Setup the Web UI on a FastAPI app.

    Args:
        app: FastAPI application instance
        service: Optional LibraService instance to use (shares state with API)
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a FastAPI instance")

    # Set service if provided
    if service is not None:
        set_service(service)

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Include router
    app.include_router(router)
