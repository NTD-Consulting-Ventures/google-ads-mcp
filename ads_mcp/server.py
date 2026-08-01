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

"""Entry point for the hosted MCP server."""

import logging
import os

from ads_mcp.auth_config import oauth_is_configured
from ads_mcp.coordinator import mcp

# The following imports are necessary to register the resources with the `mcp`
# object, even though they are not directly used in this file.
# Tools are loaded dynamically via reflection in coordinator.py.
# The `# noqa: F401` comment tells the linter to ignore the "unused import"
# warning.
from ads_mcp.resources import (
    discovery,
    metrics,
    release_notes,
    segments,
)  # noqa: F401

logger = logging.getLogger(__name__)


def _port_from_env() -> int:
    try:
        port = int(os.getenv("PORT", "8080"))
    except ValueError as exc:
        raise RuntimeError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be between 1 and 65535")
    return port


def _validate_hosted_configuration() -> None:
    if not oauth_is_configured() or mcp.auth is None:
        raise RuntimeError("OAuth is required for the hosted MCP server")
    if not os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip():
        raise RuntimeError("GOOGLE_ADS_DEVELOPER_TOKEN is required")


def run_server() -> None:
    try:
        _validate_hosted_configuration()
        port = _port_from_env()
        logger.info("Starting Google Ads MCP server on configured HTTP port")
        mcp.run(
            transport="http",
            port=port,
            host="0.0.0.0",
            path="/mcp",
            show_banner=False,
            stateless_http=True,
            uvicorn_config={
                "access_log": False,
                "server_header": False,
            },
        )
    except KeyboardInterrupt:
        logger.info("Google Ads MCP server stopped")
    except Exception:
        logger.error("Google Ads MCP server failed to start")
        raise SystemExit(1) from None


if __name__ == "__main__":
    run_server()
