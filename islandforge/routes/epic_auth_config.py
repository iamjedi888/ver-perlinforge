"""
Shared Epic OAuth configuration helpers.
"""

import os


_PLACEHOLDER_VALUES = {
    "",
    "PENDING_APPROVAL",
    "PLACEHOLDER",
    "YOUR_EPIC_CLIENT_ID_HERE",
    "YOUR_EPIC_CLIENT_SECRET_HERE",
    "YOUR_EPIC_DEPLOYMENT_ID_HERE",
    "YOUR_SECRET_HERE",
}


def _clean_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _is_placeholder(value: str) -> bool:
    return value in _PLACEHOLDER_VALUES


def get_epic_auth_config() -> dict:
    base_url = _clean_env("APP_BASE_URL", "https://triptokforge.org").rstrip("/")
    redirect_uri = _clean_env("EPIC_REDIRECT_URI", f"{base_url}/auth/callback")
    return {
        "client_id": _clean_env("EPIC_CLIENT_ID"),
        "client_secret": _clean_env("EPIC_CLIENT_SECRET"),
        "deployment_id": _clean_env("EPIC_DEPLOYMENT_ID"),
        "base_url": base_url,
        "redirect_uri": redirect_uri,
        "auth_url": "https://www.epicgames.com/id/authorize",
        "token_url": "https://api.epicgames.dev/epic/oauth/v2/token",
        "api_base": "https://api.epicgames.dev",
    }


def epic_missing_config(config: dict | None = None) -> list[str]:
    config = config or get_epic_auth_config()
    missing = []
    if _is_placeholder(config["client_id"]):
        missing.append("EPIC_CLIENT_ID")
    if _is_placeholder(config["client_secret"]):
        missing.append("EPIC_CLIENT_SECRET")
    if _is_placeholder(config["deployment_id"]):
        missing.append("EPIC_DEPLOYMENT_ID")
    return missing


def epic_auth_ready(config: dict | None = None) -> bool:
    return not epic_missing_config(config)
