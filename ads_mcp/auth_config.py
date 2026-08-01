# Copyright 2026 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Production-safe Google OAuth proxy configuration."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from fastmcp.server.auth.providers.google import GoogleProvider
from key_value.aio.stores.memory import MemoryStore
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from dotenv import load_dotenv

load_dotenv()


_CLAUDE_REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"
_GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


def _required_env(name: str, *, min_length: int = 1) -> str:
    value = os.getenv(name, "").strip()
    if len(value) < min_length:
        raise RuntimeError(f"{name} is required and is not valid")
    return value


def oauth_is_configured() -> bool:
    """Return whether both OAuth credentials exist, rejecting partial setup."""
    client_id = os.getenv("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET", "").strip()
    if bool(client_id) != bool(client_secret):
        raise RuntimeError("Google OAuth configuration is incomplete")
    return bool(client_id)


def public_base_url() -> str:
    """Resolve and validate the externally reachable MCP origin."""
    value = os.getenv("GOOGLE_ADS_MCP_BASE_URL", "").strip().rstrip("/")
    if not value:
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
        if railway_domain:
            value = f"https://{railway_domain}"
    if not value:
        raise RuntimeError("GOOGLE_ADS_MCP_BASE_URL is required")

    parsed = urlsplit(value)
    is_loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and is_loopback
    ):
        raise RuntimeError("GOOGLE_ADS_MCP_BASE_URL must use HTTPS")
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RuntimeError("GOOGLE_ADS_MCP_BASE_URL must be a clean origin URL")
    return value


def _allowed_redirect_uris(base_url: str) -> list[str]:
    configured = os.getenv("MCP_ALLOWED_REDIRECT_URIS", "").strip()
    if configured:
        redirects = [
            item.strip() for item in configured.split(",") if item.strip()
        ]
        if not redirects:
            raise RuntimeError("MCP_ALLOWED_REDIRECT_URIS is not valid")
        return redirects

    if urlsplit(base_url).hostname in {"localhost", "127.0.0.1", "::1"}:
        return [
            _CLAUDE_REDIRECT_URI,
            "http://localhost:*",
            "http://127.0.0.1:*",
        ]
    return [_CLAUDE_REDIRECT_URI]


def _oauth_storage(base_url: str):
    mode = os.getenv("OAUTH_STORAGE_BACKEND", "redis").strip().lower()
    is_loopback = urlsplit(base_url).hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }

    if mode == "memory":
        if not is_loopback:
            raise RuntimeError(
                "In-memory OAuth storage is allowed only on loopback"
            )
        return MemoryStore()
    if mode != "redis":
        raise RuntimeError("OAUTH_STORAGE_BACKEND must be redis or memory")

    redis_url = _required_env("REDIS_URL")
    encryption_key = _required_env(
        "OAUTH_STORAGE_ENCRYPTION_KEY", min_length=32
    )
    try:
        fernet = Fernet(encryption_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError(
            "OAUTH_STORAGE_ENCRYPTION_KEY is not a Fernet key"
        ) from exc

    return FernetEncryptionWrapper(
        key_value=RedisStore(
            url=redis_url,
            default_collection="google-ads-mcp-oauth",
        ),
        fernet=fernet,
    )


def build_google_provider() -> GoogleProvider:
    """Build the Google OAuth proxy with production-safe defaults."""
    client_id = _required_env("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID", min_length=16)
    client_secret = _required_env(
        "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET", min_length=16
    )
    jwt_signing_key = _required_env("OAUTH_JWT_SIGNING_KEY", min_length=32)
    base_url = public_base_url()

    return GoogleProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            _GOOGLE_ADS_SCOPE,
        ],
        allowed_client_redirect_uris=_allowed_redirect_uris(base_url),
        client_storage=_oauth_storage(base_url),
        jwt_signing_key=jwt_signing_key,
        require_authorization_consent=True,
    )
