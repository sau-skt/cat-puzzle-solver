"""Runtime configuration loaded from the environment and an optional .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
_ENV_FILES = tuple(
    str(path)
    for path in (_REPO_ROOT / ".env", _BACKEND_ROOT / ".env")
    if path.exists()
)


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://catpuzzle:change-me-db@127.0.0.1:3306/cat_puzzle"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    remember_me_expire_minutes: int = 60 * 24 * 30
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_name: str = "access_token"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    storage_dir: str = "storage"
    max_upload_bytes: int = 8 * 1024 * 1024
    solver_solution_limit: int = 20
    solver_timeout_seconds: float = 10.0
    require_email_verification: bool = False
    debug_return_tokens: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@catpuzzle.local"
    smtp_tls: bool = True
    app_public_url: str = "http://localhost:5173"
    mysql_ssl_ca: str = ""
    login_max_attempts: int = 8
    login_window_seconds: int = 300
    s3_bucket: str = ""
    s3_region: str = ""
    max_board_size: int = Field(default=16)

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        if not path.is_absolute():
            path = _BACKEND_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def mysql_ssl_ca_path(self) -> str:
        raw = self.mysql_ssl_ca.strip()
        if not raw:
            return ""
        path = Path(raw)
        if not path.is_absolute():
            path = _BACKEND_ROOT / path
        return str(path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
