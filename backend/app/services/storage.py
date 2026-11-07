"""Local image storage. Paths saved in the database are relative to the storage root."""

from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import get_settings


def save_bytes(relative_path: str, data: bytes) -> str:
    path = _absolute(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return relative_path


def read_bytes(relative_path: str) -> bytes:
    path = _absolute(relative_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored image is missing.")
    return path.read_bytes()


def delete_tree(relative_dir: str) -> None:
    path = _absolute(relative_dir)
    if not path.exists():
        return
    if path.is_file():
        path.unlink()
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def _absolute(relative_path: str) -> Path:
    root = get_settings().storage_path.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path.")
    return candidate
