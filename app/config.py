"""Environment based configuration for the recommendation API."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return parsed


def _read_optional(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _read_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded once when the application starts."""

    backend_api_base_url: str
    model_name: str
    api_timeout: int
    api_page_size: int
    use_route_api: bool
    tour_data_path: Optional[str]
    backend_auth_cookie: Optional[str]
    cors_allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            backend_api_base_url=os.getenv(
                "BACKEND_API_BASE_URL",
                "https://oiso.duckdns.org",
            ).rstrip("/"),
            model_name=os.getenv(
                "MODEL_NAME",
                "jhgan/ko-sroberta-multitask",
            ),
            api_timeout=_read_int("API_TIMEOUT", 10),
            api_page_size=_read_int("API_PAGE_SIZE", 100),
            use_route_api=_read_bool("USE_ROUTE_API", True),
            tour_data_path=_read_optional("TOUR_DATA_PATH"),
            backend_auth_cookie=_read_optional("BACKEND_AUTH_COOKIE"),
            cors_allowed_origins=_read_csv(
                "CORS_ALLOWED_ORIGINS",
                (
                    "http://localhost:5173",
                    "https://oiso-fe.vercel.app",
                ),
            ),
        )

