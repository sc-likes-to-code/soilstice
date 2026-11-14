"""FastAPI application entry point: `uvicorn app.main:app` (from backend/)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.routes import router
from app.config import Settings, get_settings
from app.contracts import CONTRACT_VERSION, ApiErrorBody, ApiErrorResponse
from app.errors import HTTP_STATUS, RETRYABLE, ApiException
from app.logging import configure_logging, get_logger, request_id_var
from app.services.container import Container, build_container
from app.services.fields import seed_farms
from app.services.pipeline import recover_interrupted_jobs

API_PREFIX = "/api/v1"
log = get_logger("api")
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _error(request: Request, code: str, message: str, details: dict | None = None) -> JSONResponse:
    body = ApiErrorResponse(error=ApiErrorBody(code=code, message=message, details=details,
                                               request_id=getattr(request.state, "request_id", "unknown"),
                                               retryable=code in RETRYABLE))
    return JSONResponse(status_code=HTTP_STATUS[code], content=body.model_dump(mode="json"))


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        c = container or build_container(settings)
        seed_farms(c)
        n = recover_interrupted_jobs(c)
        if n:
            log.warning("marked interrupted jobs as failed", extra={"count": n})
        app.state.container = c
        log.info("startup", extra={"version": __version__, "contract_version": CONTRACT_VERSION,
                                   "earthdata_configured": settings.earthdata_configured,
                                   "crop_kb": c.kb.status_message})
        yield
        c.shutdown()

    app = FastAPI(
        title="SOILSTICE API", version=__version__, lifespan=lifespan,
        description=f"SOILSTICE backend. Contract {CONTRACT_VERSION}. All responses use the ApiResponse envelope; "
                    "errors use ApiErrorResponse. Coarse products (POWER) are labelled support class R and are never "
                    "presented as field measurements.",
        openapi_url=f"{API_PREFIX}/openapi.json", docs_url=f"{API_PREFIX}/docs", redoc_url=None,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                       allow_headers=["*"], expose_headers=["X-Request-ID"])

    hits: dict[str, deque] = defaultdict(deque)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:16]}"
        request.state.request_id = rid
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            if request.method in WRITE_METHODS and settings.rate_limit_writes_per_minute > 0:
                key = request.client.host if request.client else "unknown"
                q, now = hits[key], time.monotonic()
                while q and now - q[0] > 60:
                    q.popleft()
                if len(q) >= settings.rate_limit_writes_per_minute:
                    resp = _error(request, "RATE_LIMITED", "Too many write requests; retry in a minute.")
                    resp.headers["X-Request-ID"] = rid
                    return resp
                q.append(now)
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            log.info("request", extra={"method": request.method, "path": request.url.path,
                                       "status": response.status_code,
                                       "duration_ms": round((time.perf_counter() - start) * 1000, 1)})
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(ApiException)
    async def api_exc(request: Request, exc: ApiException):
        return _error(request, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(request: Request, exc: RequestValidationError):
        errs = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return _error(request, "VALIDATION_ERROR", "Request validation failed.", {"errors": errs})

    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "VALIDATION_ERROR", 501: "NOT_IMPLEMENTED"}.get(exc.status_code, "INTERNAL")
        return _error(request, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error", extra={"path": request.url.path})
        return _error(request, "INTERNAL", "Internal server error.")

    app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
