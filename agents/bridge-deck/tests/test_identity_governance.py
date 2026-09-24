#!/usr/bin/env python3
"""
Test Suite for Phase 5 Identity & Multi-User Governance (D55 Resolution).
Verifies:
- Authenticated principal extraction (Google Cloud IAP, Google IAM, X-Bridge-Principal)
- Principal-to-tenant binding resolution and enforcement
- Rejection of unauthorized cross-tenant access with HTTP 403 Forbidden
- Fallback single-tenant compatibility when no bindings are configured
- GET /api/identity introspection endpoint
"""

import os
import sys
import json
import io
import unittest
import unittest.mock
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.identity import (
    Principal,
    PrincipalBinding,
    IdentityManager,
    TenantAccessDeniedError,
    get_identity_manager,
    set_identity_manager,
)
from core.tenant import DEFAULT_TENANT_ID
import bridge_runner


class TestPrincipalAndBinding(unittest.TestCase):
    def test_principal_properties(self):
        p_admin = Principal(id="admin_user", roles=["admin"])
        self.assertTrue(p_admin.is_admin)

        p_collab = Principal(id="collab_user", roles=["collaborator"])
        self.assertFalse(p_collab.is_admin)

    def test_principal_binding_access(self):
        binding = PrincipalBinding(
            principal_id="user_test",
            tenant_ids=["tenant_alpha", "tenant_beta"],
            default_tenant_id="tenant_alpha",
        )
        self.assertTrue(binding.can_access("tenant_alpha"))
        self.assertTrue(binding.can_access("tenant_beta"))
        self.assertFalse(binding.can_access("tenant_gamma"))
        # Test case insensitivity and sanitization
        self.assertTrue(binding.can_access("TENANT_ALPHA"))
        self.assertTrue(binding.can_access(" tenant_alpha "))
        self.assertTrue(binding.can_access("tenant-alpha"))


class TestIdentityManager(unittest.TestCase):
    def setUp(self):
        self.im = IdentityManager()

    def test_extract_iap_headers(self):
        headers = {
            "X-Goog-Authenticated-User-Email": "accounts.google.com:testuser@example.com",
            "X-Goog-Authenticated-User-Id": "accounts.google.com:10987654321",
        }
        # When IAP is enabled via environment variable
        with unittest.mock.patch.dict(os.environ, {"BRIDGE_IDENTITY_PROVIDER": "iap"}):
            principal = self.im.extract_principal(headers)
            self.assertEqual(principal.id, "testuser@example.com")
            self.assertEqual(principal.email, "testuser@example.com")
            self.assertEqual(principal.provider, "google-iap")
            self.assertEqual(principal.metadata.get("sub"), "10987654321")

        # When IAP is NOT enabled, untrusted IAP headers are ignored
        with unittest.mock.patch.dict(os.environ, {"BRIDGE_IDENTITY_PROVIDER": ""}):
            principal_untrusted = self.im.extract_principal(headers)
            self.assertEqual(principal_untrusted.provider, "local")

    def test_extract_bridge_header_loopback_only(self):
        headers = {
            "X-Bridge-Principal": "service-worker-1",
            "X-Bridge-Role": "admin",
        }
        # Loopback caller can provide X-Bridge-Principal
        principal = self.im.extract_principal(headers, is_loopback=True)
        self.assertEqual(principal.id, "service-worker-1")
        self.assertEqual(principal.provider, "bridge-header")
        self.assertTrue(principal.is_admin)

        # Remote / non-loopback caller cannot forge X-Bridge-Principal
        principal_remote = self.im.extract_principal(headers, is_loopback=False)
        self.assertNotEqual(principal_remote.provider, "bridge-header")
        self.assertEqual(principal_remote.id, "anonymous")
        self.assertEqual(principal_remote.provider, "remote")
        self.assertFalse(principal_remote.is_admin)

    def test_is_authorized_action_enforcement_q1(self):
        # Ratified Q1: secure-by-default read-only until write granted
        self.im.bind_principal("reader_user", tenant_ids=["tenant_proj"], role="reader")
        self.im.bind_principal("writer_user", tenant_ids=["tenant_proj"], role="collaborator")

        p_reader = Principal(id="reader_user", roles=["reader"])
        p_writer = Principal(id="writer_user", roles=["collaborator"])
        p_unbound = Principal(id="unbound_user", roles=["viewer"])

        # Reader can read but cannot write
        self.assertTrue(self.im.is_authorized(p_reader, "tenant_proj", action="read"))
        self.assertFalse(self.im.is_authorized(p_reader, "tenant_proj", action="write"))

        # Unbound user is denied write under Q1
        self.assertTrue(self.im.is_authorized(p_unbound, "tenant_proj", action="read"))
        self.assertFalse(self.im.is_authorized(p_unbound, "tenant_proj", action="write"))

        # Writer can both read and write
        self.assertTrue(self.im.is_authorized(p_writer, "tenant_proj", action="read"))
        self.assertTrue(self.im.is_authorized(p_writer, "tenant_proj", action="write"))

    def test_extract_bearer_token(self):
        headers = {
            "Authorization": "Bearer ya29.test_oauth_token",
        }
        principal = self.im.extract_principal(headers)
        self.assertEqual(principal.id, "iam-bearer-caller")
        self.assertEqual(principal.provider, "google-iam")

    def test_fallback_local_principal(self):
        headers = {}
        # Loopback caller defaults to operator admin
        principal = self.im.extract_principal(headers, is_loopback=True)
        self.assertEqual(principal.id, "operator")
        self.assertEqual(principal.provider, "local")
        self.assertTrue(principal.is_admin)

        # Remote caller defaults to anonymous viewer
        principal_remote = self.im.extract_principal(headers, is_loopback=False)
        self.assertEqual(principal_remote.id, "anonymous")
        self.assertEqual(principal_remote.provider, "remote")
        self.assertFalse(principal_remote.is_admin)

    def test_invalid_bindings_json_raises_in_cloud_mode(self):
        old_env = dict(os.environ)
        try:
            os.environ["CLOUD_RUN"] = "true"
            os.environ["BRIDGE_PRINCIPAL_BINDINGS"] = "{ invalid json"
            with self.assertRaises(ValueError) as ctx:
                IdentityManager()
            self.assertIn("Invalid BRIDGE_PRINCIPAL_BINDINGS", str(ctx.exception))
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_resolve_tenant_no_bindings(self):
        # When no bindings configured, open to requested tenant or default
        principal = Principal(id="any_user")
        self.assertEqual(self.im.resolve_tenant_for_principal(principal, "custom_t"), "custom_t")
        self.assertEqual(self.im.resolve_tenant_for_principal(principal, None), DEFAULT_TENANT_ID)

    def test_resolve_tenant_with_bindings(self):
        self.im.bind_principal(
            "user_a",
            tenant_ids=["tenant_1", "tenant_2"],
            default_tenant_id="tenant_1",
        )
        principal_a = Principal(id="user_a")

        # Default tenant when none requested
        resolved = self.im.resolve_tenant_for_principal(principal_a)
        self.assertEqual(resolved, "tenant_1")

        # Authorized tenant
        resolved_t2 = self.im.resolve_tenant_for_principal(principal_a, requested_tenant="tenant_2")
        self.assertEqual(resolved_t2, "tenant_2")

        # Unauthorized tenant raises TenantAccessDeniedError
        with self.assertRaises(TenantAccessDeniedError):
            self.im.resolve_tenant_for_principal(principal_a, requested_tenant="tenant_secret")

    def test_strict_mode_unbound_principal(self):
        strict_im = IdentityManager(strict_mode=True)
        strict_im.bind_principal("user_registered", ["tenant_reg"])
        unbound = Principal(id="user_unregistered")

        with self.assertRaises(TenantAccessDeniedError):
            strict_im.resolve_tenant_for_principal(unbound)

    def test_environment_variable_loading(self):
        env_config = {
            "alice@example.com": {
                "tenants": ["project_alpha", "project_shared"],
                "default": "project_alpha",
                "role": "lead",
            }
        }
        with unittest.mock.patch.dict(os.environ, {"BRIDGE_PRINCIPAL_BINDINGS": json.dumps(env_config)}):
            im = IdentityManager()
            binding = im.get_binding("alice@example.com")
            self.assertIsNotNone(binding)
            self.assertIn("project_alpha", binding.tenant_ids)
            self.assertEqual(binding.default_tenant_id, "project_alpha")
            self.assertEqual(binding.role, "lead")


import tempfile


class TestBridgeRunnerIdentityIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.old_data_dir = os.environ.get("BRIDGE_DATA_DIR")
        os.environ["BRIDGE_DATA_DIR"] = str(Path(self.tmp_dir.name) / "data")
        self.saved_im = get_identity_manager()
        self.test_im = IdentityManager()
        set_identity_manager(self.test_im)

    def tearDown(self):
        set_identity_manager(self.saved_im)
        if self.old_data_dir is not None:
            os.environ["BRIDGE_DATA_DIR"] = self.old_data_dir
        else:
            os.environ.pop("BRIDGE_DATA_DIR", None)
        self.tmp_dir.cleanup()

    def test_send_error_json_maps_tenant_access_denied_to_403(self):
        handler = bridge_runner.BridgeRequestHandler.__new__(bridge_runner.BridgeRequestHandler)
        handler.wfile = io.BytesIO()
        handler.headers = {}

        sent_statuses = []
        def mock_send_response(code):
            sent_statuses.append(code)

        def mock_send_header(k, v):
            pass

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers

        denied_err = TenantAccessDeniedError("Access to tenant 'forbidden' rejected")
        handler.send_error_json(denied_err)

        self.assertIn(403, sent_statuses)
        response_body = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertFalse(response_body["success"])
        self.assertIn("rejected", response_body["error"])

    def test_get_identity_endpoint(self):
        self.test_im.bind_principal(
            "dev_user@example.com",
            tenant_ids=["tenant_x", "tenant_y"],
            default_tenant_id="tenant_x",
        )

        handler = bridge_runner.BridgeRequestHandler.__new__(bridge_runner.BridgeRequestHandler)
        handler.wfile = io.BytesIO()
        handler.path = "/api/identity"
        handler.headers = {
            "X-Goog-Authenticated-User-Email": "accounts.google.com:dev_user@example.com",
            "X-Bridge-Tenant-ID": "tenant_x",
        }

        sent_statuses = []
        def mock_send_response(code):
            sent_statuses.append(code)

        def mock_send_header(k, v):
            pass

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers

        with unittest.mock.patch.object(handler, "_check_auth", return_value=True), \
             unittest.mock.patch.dict(os.environ, {"BRIDGE_IDENTITY_PROVIDER": "iap"}):
            handler._dispatch_GET()

        self.assertIn(200, sent_statuses)
        data = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertEqual(data["principal"]["id"], "dev_user@example.com")
        self.assertEqual(data["current_tenant"], "tenant_x")
        self.assertEqual(data["default_tenant"], "tenant_x")
        self.assertIn("tenant_x", data["authorized_tenants"])
        self.assertIn("tenant_y", data["authorized_tenants"])

    def test_unauthorized_tenant_get_request_returns_403(self):
        self.test_im.bind_principal(
            "dev_user@example.com",
            tenant_ids=["tenant_allowed"],
            default_tenant_id="tenant_allowed",
        )

        handler = bridge_runner.BridgeRequestHandler.__new__(bridge_runner.BridgeRequestHandler)
        handler.wfile = io.BytesIO()
        handler.path = "/api/history?tenant=tenant_forbidden"
        handler.headers = {
            "X-Goog-Authenticated-User-Email": "accounts.google.com:dev_user@example.com",
            "X-Bridge-Tenant-ID": "tenant_forbidden",
        }

        sent_statuses = []
        def mock_send_response(code):
            sent_statuses.append(code)

        def mock_send_header(k, v):
            pass

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers

        with unittest.mock.patch.object(handler, "_check_auth", return_value=True), \
             unittest.mock.patch.dict(os.environ, {"BRIDGE_IDENTITY_PROVIDER": "iap"}):
            handler.do_GET()

        self.assertIn(403, sent_statuses)
        data = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertFalse(data["success"])
        self.assertIn("not authorized", data["error"])


if __name__ == "__main__":
    unittest.main()
