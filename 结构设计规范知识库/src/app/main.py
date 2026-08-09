import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .admin.jobs import job_manager
from .api import admin, chat, health, images, knowledge
from .core.config import settings
from .core.logging import configure_logging
from .core.middleware import ServiceMiddleware
from .retrieval.hybrid_search import retrieval_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.job_recovery = job_manager.reconcile_interrupted_jobs()
    logging.info(
        "job_startup_reconciliation_completed",
        extra={"extra_data": app.state.job_recovery},
    )
    retrieval_state.initialize()
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_title, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(ServiceMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    app.include_router(health.router)
    app.include_router(images.router)
    app.include_router(knowledge.router)
    app.include_router(admin.router)
    app.include_router(chat.router)

    @app.get("/")
    async def root():
        return RedirectResponse(url="/static/index.html")

    return app


app = create_app()
