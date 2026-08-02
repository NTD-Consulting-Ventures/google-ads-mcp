# Copyright 2026 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""Tests for hosted OAuth configuration."""

import unittest
from unittest.mock import patch

from ads_mcp import auth_config


class AuthConfigTest(unittest.TestCase):
    def test_partial_oauth_configuration_is_rejected(self):
        with patch.dict(
            "os.environ",
            {"GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "client-id"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                auth_config.oauth_is_configured()

    def test_public_base_url_rejects_plain_http(self):
        with patch.dict(
            "os.environ",
            {"GOOGLE_ADS_MCP_BASE_URL": "http://example.com"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "must use HTTPS"):
                auth_config.public_base_url()

    def test_memory_storage_is_local_only(self):
        with patch.dict(
            "os.environ",
            {"OAUTH_STORAGE_BACKEND": "memory"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "only on loopback"):
                auth_config._oauth_storage("https://example.com")

    def test_local_provider_uses_memory_storage(self):
        env = {
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": (
                "123456789.apps.googleusercontent.com"
            ),
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET": (
                "local-placeholder-client-secret"
            ),
            "GOOGLE_ADS_MCP_BASE_URL": "http://localhost:8080",
            "OAUTH_STORAGE_BACKEND": "memory",
            "OAUTH_JWT_SIGNING_KEY": (
                "local-placeholder-signing-key-0123456789"
            ),
        }
        with patch.dict("os.environ", env, clear=True):
            provider = auth_config.build_google_provider()

        self.assertIsNotNone(provider)


if __name__ == "__main__":
    unittest.main()
