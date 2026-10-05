import asyncio
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from backend.app.config import Config
from backend.app.models.schemas import Label, Settings
from backend.app.services.metrics import summarize
from backend.app.services.worker import Worker


def create_app(config: Config | None = None, run_worker: bool = True) -> FastAPI:
    config = config or Config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker = Worker(config)
        app.state.worker = worker
        task = asyncio.create_task(worker.run()) if run_worker else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await worker.close()

    app = FastAPI(title="PriorInbox", version="0.1.0", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        allowed = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        }
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Local origins only"}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and (
            request.headers.get("x-priorinbox") != "local"
        ):
            return JSONResponse({"detail": "Missing local client header"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/api/status")
    async def status(request: Request):
        w = request.app.state.worker
        return {
            "health": w.health,
            "source_error": w.source_error,
            "notification_error": w.notifier.last_error,
            "fixture": w.config.fixture,
            "source": w.config.source,
            "persistent": w.config.persist_raw,
        }

    @app.get("/api/messages")
    async def messages(
        request: Request,
        view: Literal["all", "important"] = "all",
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        rows = request.app.state.worker.store.records()
        if view == "important":
            rows = [r for r in rows if r["classification"] and r["classification"]["important"]]
        rows.sort(key=lambda r: r["timestamp"], reverse=True)
        return {"items": rows[offset : offset + limit], "total": len(rows)}

    @app.get("/api/analytics")
    async def analytics(request: Request):
        w = request.app.state.worker
        return summarize(w.store.records(), time.perf_counter() - w.started)

    @app.get("/api/settings")
    async def settings(request: Request):
        return request.app.state.worker.settings

    @app.put("/api/settings")
    async def save_settings(settings: Settings, request: Request):
        w = request.app.state.worker
        # These synchronous operations are atomic within the single event loop.
        # Do not wait behind an inference batch that may take several minutes.
        w.store.save_settings(settings)
        w.settings = settings
        return settings

    @app.get("/api/models")
    async def models(request: Request):
        try:
            return {"models": await request.app.state.worker.pipeline.models()}
        except Exception:
            return {"models": [], "error": "Ollama is unavailable; run ollama serve"}

    @app.put("/api/messages/{id}/label")
    async def label(id: str, label: Label, request: Request):
        if not request.app.state.worker.store.label(id, label):
            raise HTTPException(404, "Message not found")
        return {"saved": True}

    dashboard = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    # This module is backend/app/main.py: the workspace root is two parents up.
    if dashboard.is_dir():
        app.mount("/", StaticFiles(directory=dashboard, html=True), name="dashboard")
    return app


app = create_app()
