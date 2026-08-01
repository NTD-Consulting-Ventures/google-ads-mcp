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

"""Test cases for the server module."""

import unittest

from starlette.testclient import TestClient


class TestUtils(unittest.TestCase):
    """Test cases for the server module."""

    def test_server_initialization(self):
        """Tests that the MCP server instance is initialized.

        This servers as a smoke test to confirm there are no obvious issues
        with initialization, such as missing imports.
        """
        from ads_mcp import server

        self.assertIsNotNone(server.mcp, "MCP server instance not initialized")

    def test_health_is_public_and_minimal(self):
        from ads_mcp import server

        with TestClient(
            server.mcp.http_app(path="/mcp", stateless_http=True)
        ) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "ok")

    def test_branding_metadata(self):
        from ads_mcp import server

        self.assertEqual(server.mcp.name, "Naturbummler Google Ads")
        self.assertEqual(server.mcp.website_url, "https://naturbummler.de")
        self.assertEqual(
            str(server.mcp.icons[0].src),
            "https://naturbummler.de/cdn/shop/files/"
            "1000x628px_Logo_1000x628.png",
        )

    def test_invalid_port_is_rejected(self):
        from ads_mcp import server
        from unittest.mock import patch

        with patch.dict("os.environ", {"PORT": "70000"}):
            with self.assertRaisesRegex(RuntimeError, "between 1 and 65535"):
                server._port_from_env()
