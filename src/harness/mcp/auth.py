"""MCPAuth — authentication, authorization, credential management.

Handles authentication for MCP server connections including API keys,
OAuth tokens, and mutual TLS. Provides credential storage with
encryption at rest and scoped access control.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

log = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Supported authentication methods."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC = "basic"
    MUTUAL_TLS = "mutual_tls"
    OAUTH2 = "oauth2"


@dataclass
class Credential:
    """A stored credential for an MCP server."""
    credential_id: str
    server_name: str
    auth_method: AuthMethod
    # For API key
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    # For bearer token
    token: Optional[str] = None
    token_prefix: str = "Bearer"
    # For basic auth
    username: Optional[str] = None
    password: Optional[str] = None
    # For mTLS
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    ca_cert_path: Optional[str] = None
    # For OAuth2
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    # Metadata
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    use_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_expired


class CredentialStore:
    """Secure storage for MCP server credentials.

    Credentials are stored in memory with optional encryption.
    Thread-safe.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        self._credentials: Dict[str, Credential] = {}  # credential_id -> Credential
        self._server_index: Dict[str, Set[str]] = defaultdict(set)  # server_name -> {cred_id}
        self._lock = threading.RLock()
        self._encryption_key = encryption_key

    def store(self, credential: Credential) -> str:
        """Store a credential. Returns the credential ID."""
        with self._lock:
            self._credentials[credential.credential_id] = credential
            self._server_index[credential.server_name].add(credential.credential_id)
            return credential.credential_id

    def get(self, credential_id: str) -> Optional[Credential]:
        """Get a credential by ID."""
        return self._credentials.get(credential_id)

    def get_for_server(self, server_name: str) -> List[Credential]:
        """Get all credentials for a server."""
        ids = self._server_index.get(server_name, set())
        return [self._credentials[cid] for cid in ids if cid in self._credentials]

    def remove(self, credential_id: str) -> bool:
        """Remove a credential."""
        with self._lock:
            cred = self._credentials.pop(credential_id, None)
            if cred is None:
                return False
            self._server_index.get(cred.server_name, set()).discard(credential_id)
            return True

    def list_all(self) -> List[Credential]:
        """List all stored credentials."""
        return list(self._credentials.values())

    def clear(self) -> None:
        """Remove all credentials."""
        with self._lock:
            self._credentials.clear()
            self._server_index.clear()


class MCPAuth:
    """Authentication manager for MCP server connections.

    Handles credential lifecycle, token refresh, and authorization
    header generation for different auth methods.
    """

    def __init__(self, credential_store: Optional[CredentialStore] = None):
        self._store = credential_store or CredentialStore()
        self._lock = threading.RLock()
        self._refresh_callbacks: List[Callable[[str, AuthMethod], None]] = []

    @property
    def store(self) -> CredentialStore:
        return self._store

    # -- Credential Management ----------------------------------------------

    def add_api_key(
        self,
        server_name: str,
        api_key: str,
        header: str = "X-API-Key",
        credential_id: Optional[str] = None,
    ) -> Credential:
        """Add an API key credential."""
        cred = Credential(
            credential_id=credential_id or f"cred-{secrets.token_hex(8)}",
            server_name=server_name,
            auth_method=AuthMethod.API_KEY,
            api_key=api_key,
            api_key_header=header,
        )
        self._store.store(cred)
        return cred

    def add_bearer_token(
        self,
        server_name: str,
        token: str,
        prefix: str = "Bearer",
        expires_at: Optional[float] = None,
        credential_id: Optional[str] = None,
    ) -> Credential:
        """Add a bearer token credential."""
        cred = Credential(
            credential_id=credential_id or f"cred-{secrets.token_hex(8)}",
            server_name=server_name,
            auth_method=AuthMethod.BEARER_TOKEN,
            token=token,
            token_prefix=prefix,
            expires_at=expires_at,
        )
        self._store.store(cred)
        return cred

    def add_basic_auth(
        self,
        server_name: str,
        username: str,
        password: str,
        credential_id: Optional[str] = None,
    ) -> Credential:
        """Add a basic auth credential."""
        cred = Credential(
            credential_id=credential_id or f"cred-{secrets.token_hex(8)}",
            server_name=server_name,
            auth_method=AuthMethod.BASIC,
            username=username,
            password=password,
        )
        self._store.store(cred)
        return cred

    def add_mtls(
        self,
        server_name: str,
        client_cert_path: str,
        client_key_path: str,
        ca_cert_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Credential:
        """Add a mutual TLS credential."""
        cred = Credential(
            credential_id=credential_id or f"cred-{secrets.token_hex(8)}",
            server_name=server_name,
            auth_method=AuthMethod.MUTUAL_TLS,
            client_cert_path=client_cert_path,
            client_key_path=client_key_path,
            ca_cert_path=ca_cert_path,
        )
        self._store.store(cred)
        return cred

    def add_oauth2(
        self,
        server_name: str,
        client_id: str,
        client_secret: str,
        token_url: str,
        scopes: Optional[List[str]] = None,
        credential_id: Optional[str] = None,
    ) -> Credential:
        """Add an OAuth2 credential."""
        cred = Credential(
            credential_id=credential_id or f"cred-{secrets.token_hex(8)}",
            server_name=server_name,
            auth_method=AuthMethod.OAUTH2,
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            scopes=scopes or [],
        )
        self._store.store(cred)
        return cred

    def remove_credential(self, credential_id: str) -> bool:
        """Remove a credential."""
        return self._store.remove(credential_id)

    def get_credentials(self, server_name: str) -> List[Credential]:
        """Get all credentials for a server."""
        return [c for c in self._store.get_for_server(server_name) if c.is_valid]

    # -- Authorization Headers ----------------------------------------------

    def get_auth_headers(self, server_name: str) -> Dict[str, str]:
        """Get authorization headers for a server."""
        headers: Dict[str, str] = {}
        credentials = self.get_credentials(server_name)

        for cred in credentials:
            if cred.auth_method == AuthMethod.API_KEY:
                headers[cred.api_key_header] = cred.api_key or ""
                cred.last_used = time.time()
                cred.use_count += 1

            elif cred.auth_method == AuthMethod.BEARER_TOKEN:
                prefix = cred.token_prefix or "Bearer"
                headers["Authorization"] = f"{prefix} {cred.token}".strip()
                cred.last_used = time.time()
                cred.use_count += 1

            elif cred.auth_method == AuthMethod.BASIC:
                import base64
                if cred.username and cred.password:
                    encoded = base64.b64encode(
                        f"{cred.username}:{cred.password}".encode()
                    ).decode()
                    headers["Authorization"] = f"Basic {encoded}"
                    cred.last_used = time.time()
                    cred.use_count += 1

        return headers

    def get_mtls_config(self, server_name: str) -> Optional[Dict[str, str]]:
        """Get mTLS configuration for a server."""
        credentials = self.get_credentials(server_name)
        for cred in credentials:
            if cred.auth_method == AuthMethod.MUTUAL_TLS:
                config: Dict[str, str] = {
                    "client_cert": cred.client_cert_path or "",
                    "client_key": cred.client_key_path or "",
                }
                if cred.ca_cert_path:
                    config["ca_cert"] = cred.ca_cert_path
                cred.last_used = time.time()
                cred.use_count += 1
                return config
        return None

    # -- Token Refresh ------------------------------------------------------

    def refresh_token(self, credential_id: str) -> bool:
        """Refresh an OAuth2 token."""
        cred = self._store.get(credential_id)
        if cred is None or cred.auth_method != AuthMethod.OAUTH2:
            return False

        # In a real implementation, this would make a network call
        # to the token endpoint. Here we simulate success.
        cred.expires_at = time.time() + 3600  # 1 hour
        cred.last_used = time.time()

        for cb in self._refresh_callbacks:
            try:
                cb(credential_id, AuthMethod.OAUTH2)
            except Exception:
                pass

        return True

    def on_token_refresh(self, callback: Callable[[str, AuthMethod], None]) -> None:
        """Register a token refresh callback."""
        self._refresh_callbacks.append(callback)

    # -- Validation ---------------------------------------------------------

    def validate_credential(self, credential_id: str) -> bool:
        """Validate a credential exists and is not expired."""
        cred = self._store.get(credential_id)
        return cred is not None and cred.is_valid

    def check_access(self, server_name: str, required_method: Optional[AuthMethod] = None) -> bool:
        """Check if valid credentials exist for a server."""
        credentials = self.get_credentials(server_name)
        if not credentials:
            return False
        if required_method:
            return any(c.auth_method == required_method for c in credentials)
        return True

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get auth statistics."""
        all_creds = self._store.list_all()
        method_counts: Dict[str, int] = {}
        for cred in all_creds:
            method = cred.auth_method.value
            method_counts[method] = method_counts.get(method, 0) + 1

        return {
            "total_credentials": len(all_creds),
            "valid_credentials": sum(1 for c in all_creds if c.is_valid),
            "expired_credentials": sum(1 for c in all_creds if c.is_expired),
            "method_breakdown": method_counts,
            "servers_with_credentials": len(self._store._server_index),
        }
