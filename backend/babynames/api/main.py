"""FastAPI application entry point."""

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from babynames.logging import get_logger, new_request_id, setup_logging

setup_logging()
log = get_logger("api")

app = FastAPI(
    title="Baby Names",
    description="Baby name discovery and ranking API",
    version="0.1.0",
)

# CORS — allow frontend dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing and request ID."""
    rid = new_request_id()
    request.state.request_id = rid
    start = time.perf_counter()

    response: Response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    log.info(
        f"{request.method} {request.url.path} → {response.status_code}",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = rid
    return response


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "babynames-api"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler with structured logging."""
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )


# Import and register route modules
from babynames.api.routes import names, ranking, favourites, sessions  # noqa: E402

app.include_router(names.router, prefix="/api", tags=["names"])
app.include_router(ranking.router, prefix="/api", tags=["ranking"])
app.include_router(favourites.router, prefix="/api", tags=["favourites"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
