"""FastAPI application entrypoint."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("catpuzzle")
_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


class SPAStaticFiles(StaticFiles):
    """Serve the built frontend and fall back to index.html for client routes."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Cat Puzzle Solver",
        version="1.0.0",
        description=(
            "Detect a cat-placement puzzle from a screenshot, correct the board, "
            "and solve it with a local constraint solver. No external AI API is used."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        response = await call_next(request)
        logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = []
        for error in exc.errors():
            message = error.get("msg", "Invalid value")
            if message.startswith("Value error, "):
                message = message[len("Value error, ") :]
            messages.append(message)
        detail = " ".join(dict.fromkeys(messages)) or "Invalid request."
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    app.include_router(api_router, prefix="/api")
    if _STATIC_DIR.is_dir():
        app.mount("/", SPAStaticFiles(directory=_STATIC_DIR, html=True), name="spa")
    return app


app = create_app()
