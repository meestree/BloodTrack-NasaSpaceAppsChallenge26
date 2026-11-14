"""Application entry point; connect API routers here."""

from fastapi import FastAPI

from backend.api.router import router


def create_app() -> FastAPI:
    """Build an independent application instance."""
    application = FastAPI(title="NASA Space Apps API", version="0.1.0")
    application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
