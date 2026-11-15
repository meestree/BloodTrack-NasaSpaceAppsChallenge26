"""Application entry point; connect API routers here."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware

from backend.api.router import router
from backend.storage.auth import AuthStore
from backend.storage.measurements import MeasurementStore


def create_app(database_path: Path | None = None) -> FastAPI:
    """Build an independent application instance."""
    path = database_path if database_path is not None else Path(__file__).resolve().parents[2] / "data" / "astronautas.db"
    store = AuthStore(path)
    measurements = MeasurementStore(store)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store.initialize()
        measurements.initialize()
        yield

    application = FastAPI(title="NASA Space Apps API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
    application.state.auth_store = store
    application.state.measurement_store = measurements

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        # FastAPI's default validation response can echo submitted passwords.
        errors = [{key: item[key] for key in ("type", "loc", "msg")} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})
    application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
