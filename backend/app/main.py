from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import resolve_shop_code
from app.core.logging import configure_logging
from app.services.chat_realtime_gateway import ChatRealtimeGateway

configure_logging()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    chat_gateway = ChatRealtimeGateway(redis_url=settings.redis_url, channel=settings.chat_redis_channel)
    app.state.chat_gateway = chat_gateway
    await chat_gateway.start()
    try:
        yield
    finally:
        await chat_gateway.stop()


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def shop_context_middleware(request: Request, call_next):
    if request.url.path.startswith(settings.api_v1_prefix):
        try:
            resolve_shop_code(request=request, required=False)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


media_root = settings.media_root_path
media_root.mkdir(parents=True, exist_ok=True)
settings.invoice_media_dir.mkdir(parents=True, exist_ok=True)
settings.prescription_media_dir.mkdir(parents=True, exist_ok=True)
settings.chat_storage_root_path.mkdir(parents=True, exist_ok=True)

if not settings.is_production:
    app.mount(settings.media_url_prefix, StaticFiles(directory=str(media_root)), name="media")

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/healthz", tags=["health"])
def readiness_check() -> dict[str, str]:
    return {"status": "ok"}
