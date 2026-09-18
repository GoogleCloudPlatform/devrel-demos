#!/usr/bin/env python3
"""
Identity, Principal-to-Tenant Binding, and Governance Module for Project Bridge Deck (D55).

Implements authenticated principal extraction (Google Cloud IAP, Google IAM, X-Bridge-Principal)
and deterministic principal-to-tenant binding policies to clear Gate G1.
Enforces multi-tenant boundary isolation and prevents unauthorized cross-tenant access.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from core.tenant import sanitize_tenant_id, DEFAULT_TENANT_ID, is_cloud


class TenantAccessDeniedError(PermissionError):
    """Raised when an authenticated principal attempts to access an unauthorized tenant."""
    pass


@dataclass
class Principal:
    """Represents an authenticated caller or user identity."""
    id: str
    email: Optional[str] = None
    provider: str = "local"
    roles: List[str] = field(default_factory=lambda: ["collaborator"])
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles or "operator" in self.roles


@dataclass
class PrincipalBinding:
    """Binds an authenticated principal to authorized tenant environments."""
    principal_id: str
    tenant_ids: List[str]
    default_tenant_id: str
    role: str = "collaborator"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_access(self, tenant_id: str) -> bool:
        norm = sanitize_tenant_id(tenant_id)
        return norm in [sanitize_tenant_id(t) for t in self.tenant_ids]


class IdentityManager:
    """
    Manages identity extraction, principal-to-tenant mapping, and access authorization.
    Supports Google Cloud IAP headers, IAM OIDC tokens, and application principal headers.
    """

    def __init__(self, bindings_config: Optional[Dict[str, Any]] = None, strict_mode: bool = False):
        self._bindings: Dict[str, PrincipalBinding] = {}
        self.strict_mode = strict_mode
        self._load_bindings(bindings_config)

    def _load_bindings(self, config: Optional[Dict[str, Any]] = None):
        """Loads bindings from explicit configuration or environment variable."""
        raw_config = config
        if raw_config is None:
            env_val = os.environ.get("BRIDGE_PRINCIPAL_BINDINGS")
            if env_val:
                try:
                    raw_config = json.loads(env_val)
                except Exception as e:
                    print(f"⚠️ Warning: Failed to parse BRIDGE_PRINCIPAL_BINDINGS environment variable: {e}")
                    if is_cloud():
                        raise ValueError(f"Invalid BRIDGE_PRINCIPAL_BINDINGS configuration in cloud mode: {e}")
                    raw_config = {}

        if not raw_config:
            return

        # Expected format:
        # { "user@example.com": {"tenants": ["default", "alpha"], "default": "default", "role": "admin"} }
        for pid, b_data in raw_config.items():
            if isinstance(b_data, list):
                tenants = [sanitize_tenant_id(t) for t in b_data]
                def_t = tenants[0] if tenants else DEFAULT_TENANT_ID
                self.bind_principal(pid, tenant_ids=tenants, default_tenant_id=def_t)
            elif isinstance(b_data, dict):
                tenants = [sanitize_tenant_id(t) for t in b_data.get("tenants", [DEFAULT_TENANT_ID])]
                def_t = sanitize_tenant_id(b_data.get("default") or (tenants[0] if tenants else DEFAULT_TENANT_ID))
                role = b_data.get("role", "collaborator")
                self.bind_principal(pid, tenant_ids=tenants, default_tenant_id=def_t, role=role, metadata=b_data.get("metadata", {}))

    def bind_principal(
        self,
        principal_id: str,
        tenant_ids: List[str],
        default_tenant_id: Optional[str] = None,
        role: str = "collaborator",
        metadata: Optional[Dict[str, Any]] = None
    ) -> PrincipalBinding:
        norm_pid = principal_id.strip().lower()
        norm_tenants = [sanitize_tenant_id(t) for t in tenant_ids]
        norm_default = sanitize_tenant_id(default_tenant_id) if default_tenant_id else (norm_tenants[0] if norm_tenants else DEFAULT_TENANT_ID)

        binding = PrincipalBinding(
            principal_id=norm_pid,
            tenant_ids=norm_tenants,
            default_tenant_id=norm_default,
            role=role,
            metadata=metadata or {}
        )
        self._bindings[norm_pid] = binding
        return binding

    def get_binding(self, principal_id: str) -> Optional[PrincipalBinding]:
        norm_pid = principal_id.strip().lower()
        return self._bindings.get(norm_pid)

    def extract_principal(self, headers: Dict[str, str], is_loopback: bool = True) -> Principal:
        """
        Extracts authenticated principal from request headers.
        Checks Google Cloud IAP, Google IAM, and loopback application principal headers.
        """
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # 1. Google Cloud IAP authenticated email header (only trusted if IAP is enabled)
        iap_enabled = os.environ.get("BRIDGE_IDENTITY_PROVIDER") == "iap" or bool(os.environ.get("BRIDGE_ALLOW_IAP_HEADERS"))
        iap_email_header = headers_lower.get("x-goog-authenticated-user-email")
        if iap_email_header and iap_enabled:
            # Format is typically "accounts.google.com:user@example.com"
            email = iap_email_header.split(":")[-1].strip().lower()
            sub = headers_lower.get("x-goog-authenticated-user-id", email).split(":")[-1].strip()
            return Principal(
                id=email,
                email=email,
                provider="google-iap",
                roles=["collaborator"],
                metadata={"sub": sub}
            )

        # 2. Google Cloud IAM Authorization header (Bearer token)
        auth_header = headers_lower.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            return Principal(
                id="iam-bearer-caller",
                provider="google-iam",
                roles=["collaborator"],
                metadata={"has_token": bool(token)}
            )

        # 3. Application custom principal header (X-Bridge-Principal or X-Bridge-User)
        # Hardening B4: Client-supplied principal headers are strictly restricted to loopback callers
        if is_loopback:
            app_principal = (
                headers_lower.get("x-bridge-principal")
                or headers_lower.get("x-bridge-user")
                or headers_lower.get("x-principal")
            )
            if app_principal:
                norm_p = app_principal.strip().lower()
                role = headers_lower.get("x-bridge-role", "collaborator")
                return Principal(
                    id=norm_p,
                    email=norm_p if "@" in norm_p else None,
                    provider="bridge-header",
                    roles=[role]
                )

        # 4. Fallback: local operator principal (if loopback), otherwise unauthenticated viewer
        if is_loopback:
            return Principal(
                id="operator",
                provider="local",
                roles=["admin"]
            )
        return Principal(
            id="anonymous",
            provider="remote",
            roles=["viewer"]
        )

    def resolve_tenant_for_principal(
        self,
        principal: Principal,
        requested_tenant: Optional[str] = None
    ) -> str:
        """
        Resolves and verifies the authorized tenant for an authenticated principal.
        Enforces tenant boundary isolation; raises TenantAccessDeniedError if unauthorized.
        """
        # If no bindings are registered, allow requested or default tenant (fail-closed in cloud)
        if not self._bindings:
            if is_cloud():
                return DEFAULT_TENANT_ID
            if requested_tenant:
                return sanitize_tenant_id(requested_tenant)
            return DEFAULT_TENANT_ID

        norm_pid = principal.id.strip().lower()
        binding = self._bindings.get(norm_pid)

        # In strict mode, unknown principals without a binding are rejected
        if not binding:
            if self.strict_mode:
                raise TenantAccessDeniedError(
                    f"Principal '{principal.id}' is not bound to any tenant environment"
                )
            # Default fallback in non-strict mode
            if requested_tenant:
                return sanitize_tenant_id(requested_tenant)
            return DEFAULT_TENANT_ID

        # Principal has an explicit binding
        if requested_tenant:
            target = sanitize_tenant_id(requested_tenant)
            if not binding.can_access(target):
                raise TenantAccessDeniedError(
                    f"Principal '{principal.id}' is not authorized to access tenant '{target}'"
                )
            return target

        return binding.default_tenant_id

    def is_authorized(self, principal: Principal, tenant_id: str, action: str = "read") -> bool:
        """
        Checks if principal has permission for given action within tenant.
        Enforces Ratified Q1: Secure-by-default READ-ONLY access until explicitly granted write access.
        """
        try:
            self.resolve_tenant_for_principal(principal, requested_tenant=tenant_id)
            if action.lower() in ("write", "mutate", "delete"):
                # Local loopback operator always retains administrative write privileges
                if principal.provider == "local" and principal.id == "operator":
                    return True

                norm_pid = principal.id.strip().lower()
                binding = self._bindings.get(norm_pid)
                # Ratified Q1: The binding is the sole authoritative source of role; unbound principals default to "viewer"
                roles = [binding.role.lower()] if binding else ["viewer"]
                if any(r in ("reader", "viewer", "guest") for r in roles):
                    return False
                allowed_writers = {"collaborator", "admin", "operator", "lead", "writer", "developer"}
                return any(r in allowed_writers for r in roles)
            return True
        except TenantAccessDeniedError:
            return False


# Global singleton identity manager
_identity_manager: Optional[IdentityManager] = None


def get_identity_manager() -> IdentityManager:
    global _identity_manager
    if _identity_manager is None:
        strict = bool(os.environ.get("BRIDGE_STRICT_IDENTITY") == "true")
        _identity_manager = IdentityManager(strict_mode=strict)
    return _identity_manager


def set_identity_manager(manager: Optional[IdentityManager]):
    global _identity_manager
    _identity_manager = manager
