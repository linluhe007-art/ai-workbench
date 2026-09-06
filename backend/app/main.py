from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.middleware import RequestIDMiddleware
from app.auth.middleware import AuthMiddleware
from app.config import get_settings
from app.database import init_db
from app.utils.logger import get_logger, setup_logging
from app.utils.errors import install_exception_handlers

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application", app=settings.app_name, env=settings.app_env)
    await init_db()
    logger.info("Database tables ensured")
    # Phase 4.19: Initialize runtime with persistence and recovery
    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()
        init_result = await runtime.initialize()
        logger.info("Runtime initialized", **init_result)
    except Exception as e:
        logger.warning("Runtime initialization skipped", error=str(e)[:200])
    yield
    # Phase 4.19: Graceful shutdown
    logger.info("Shutting down application")
    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()
        await runtime.shutdown()
    except Exception as e:
        logger.warning("Runtime shutdown error", error=str(e)[:200])


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)

app.include_router(api_router)
install_exception_handlers(app)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }