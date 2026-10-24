"""FlowDesk API entry point.

Serves the REST API under /api and the web SPA as static files.
Interactive API docs are available at /docs (OpenAPI).
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import auth, dashboard, projects, tasks

app = FastAPI(
    title="FlowDesk API",
    version="1.0.0",
    description="Team project management: projects, kanban tasks, comments, activity.",
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "flowdesk"}


_WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
