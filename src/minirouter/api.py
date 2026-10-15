"""Local FastAPI interface for the experimental MiniRouter V3 bundle."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator

from .contract import CAPABILITIES
from .runtime import MiniRouter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE_BUNDLE = PROJECT_ROOT / "model"
DEFAULT_BUNDLE = RELEASE_BUNDLE if RELEASE_BUNDLE.is_dir() else PROJECT_ROOT / "artifacts" / "trained-v3-bundle"
MAX_BODY_BYTES = 50_000
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
Capability = Literal["coding", "reasoning", "search", "database"]
ContextText = Annotated[str, StringConstraints(min_length=1, max_length=8_192, strip_whitespace=True)]


class RouteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: Annotated[str, StringConstraints(min_length=1, max_length=32_768, strip_whitespace=True)]
    context: list[ContextText] = Field(default_factory=list, max_length=4)
    available_capabilities: list[Capability] = Field(default_factory=lambda: list(CAPABILITIES))
    calculator: bool = True
    locale: Annotated[str, StringConstraints(min_length=2, max_length=32)] = "en"
    context_complete: bool = True

    @field_validator("available_capabilities")
    @classmethod
    def capabilities_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("available_capabilities must not contain duplicates")
        return value


def create_app(bundle: str | Path | None = None, *, router: MiniRouter | None = None) -> FastAPI:
    """Create a local API app; the pinned runtime is loaded once per app lifespan."""
    selected_bundle = Path(bundle or DEFAULT_BUNDLE).resolve()
    inference = router
    inference_limit = asyncio.Semaphore(2)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal inference
        if inference is None:
            inference = MiniRouter(selected_bundle, threads=4)
        app.state.router = inference
        yield

    app = FastAPI(title="MiniRouter local preview", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse({"error": _validation_message(exc)}, status_code=422)

    @app.middleware("http")
    async def loopback_same_origin(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/api/route":
            host_header = request.headers.get("host", "")
            host = _parse_host(host_header)
            if host not in LOOPBACK_HOSTS:
                return JSONResponse({"error": "Requests must use a loopback host"}, status_code=403)
            origin = request.headers.get("origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS or parsed.netloc.casefold() != host_header.casefold():
                    return JSONResponse({"error": "Origin not permitted"}, status_code=403)
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.get("/health")
    async def health(request: Request):
        return {"loaded": getattr(request.app.state, "router", None) is not None}

    @app.get("/api/meta")
    async def metadata(request: Request):
        loaded = getattr(request.app.state, "router", None)
        if loaded is None:
            return JSONResponse({"error": "Model is not loaded"}, status_code=503)
        return {
            "bundle_bytes": loaded.bundle_bytes,
            "parameters": loaded.config["parameter_counts"]["total"],
            "state": "Experimental V3",
            "calibration": loaded.calibration.get("status"),
            "model_version": "MiniRouter V3",
            "limits": {
                "routes": ["coding", "reasoning", "search", "database", "no_llm"],
                "locale": "English (en) only",
                "max_tokens": loaded.policy.max_tokens,
                "max_text_characters": 32_768,
                "max_context_items": 4,
                "max_context_characters_each": 8_192,
            },
            "evidence": {
                "main_primary_accuracy": 0.99,
                "capability_macro_f1": 0.725422,
                "capability_target_met": False,
                "locked_report_complete": False,
                "production_ready": False,
                "note": "Internal experimental results; supporting capability estimates are below target. Review every recommendation.",
            },
        }

    @app.post("/api/route")
    async def route(request: Request):
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > MAX_BODY_BYTES:
                    return JSONResponse({"error": f"Request body exceeds {MAX_BODY_BYTES} bytes"}, status_code=413)
            except ValueError:
                return JSONResponse({"error": "Invalid Content-Length"}, status_code=400)
        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BODY_BYTES:
                return JSONResponse({"error": f"Request body exceeds {MAX_BODY_BYTES} bytes"}, status_code=413)
            chunks.append(chunk)
        try:
            payload = RouteInput.model_validate_json(b"".join(chunks))
        except ValidationError as exc:
            return JSONResponse({"error": _validation_message(exc)}, status_code=422)
        loaded = getattr(request.app.state, "router", None)
        if loaded is None:
            return JSONResponse({"error": "Model is not loaded"}, status_code=503)
        try:
            async with inference_limit:
                result = await asyncio.to_thread(
                    loaded.route,
                    payload.text,
                    context=payload.context,
                    available_capabilities=payload.available_capabilities,
                    calculator=payload.calculator,
                    locale=payload.locale,
                    context_complete=payload.context_complete,
                )
            return result
        except (ValueError, TypeError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "web"), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        from fastapi.responses import FileResponse
        return FileResponse(PROJECT_ROOT / "web" / "index.html", media_type="text/html")

    return app


def _parse_host(host_header: str) -> str | None:
    try:
        parsed = urlsplit("//" + host_header)
        return parsed.hostname.casefold() if parsed.hostname else None
    except ValueError:
        return None


def _validation_message(exc: ValidationError | RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    message = str(first.get("msg", "Invalid request"))
    return f"{location}: {message}" if location else message
