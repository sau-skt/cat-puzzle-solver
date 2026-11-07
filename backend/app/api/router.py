"""Top-level API router."""

from fastapi import APIRouter

from app.api import auth, puzzles

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(puzzles.router)


@api_router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "cat-puzzle-solver"}
