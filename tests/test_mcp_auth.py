"""Tests for MCPAuth — authentication, authorization, credential management."""
from __future__ import annotations

import pytest

from harness.mcp.auth import MCPAuth, CredentialStore, Credential, AuthMethod


class TestAuthMethod:
    def test_values(self):
        assert AuthMethod.NONE.value == "none"
        assert AuthMethod.API_KEY.value == "api_key"
        assert AuthMethod.BEARER_TOKEN.value == "bearer_token"
        assert AuthMethod.BASIC.value == "basic"
        assert AuthMethod.MUTUAL_TLS.value == "mutual_tls"
        assert AuthMethod.OAUTH2.value == "oauth2"


class TestCredential:
    def test_create(self):
        cred = Credential(
            credential_id="c1",
            server_name="s1",
            auth_method=AuthMethod.API_KEY,
            api_key="secret",
        )
        assert cred.credential_id == "c1"
        assert cred.server_name == "s1"
        assert cred.auth_method == AuthMethod.API_KEY
        assert cred.api_key == "secret"

    def test_is_expired_no_expiry(self):
        cred = Credential(
            credential_id="c1",
            server_name="s1",
            auth_method=AuthMethod.API_KEY,
        )
        assert cred.is_expired is False

    def test_is_expired_with_future_expiry(self):
        import time
        cred = Credential(
            credential_id="c1",
            server_name="s1",
            auth_method=AuthMethod.BEARER_TOKEN,
            expires_at=time.time() + 3600,
        )
        assert cred.is_expired is False

    def test_is_expired_with_past_expiry(self):
        import time
        cred = Credential(
            credential_id="c1",
            server_name="s1",
            auth_method=AuthMethod.BEARER_TOKEN,
            expires_at=time.time() - 100,
        )
        assert cred.is_expired is True

    def test_is_valid(self):
        cred = Credential(
            credential_id="c1",
            server_name="s1",
            auth_method=AuthMethod.API_KEY,
        )
        assert cred.is_valid is True


class TestCredentialStore:
    def test_create(self):
        store = CredentialStore()
        assert store.list_all() == []

    def test_store(self):
        store = CredentialStore()
        cred = Credential(credential_id="c1", server_name="s1", auth_method=AuthMethod.API_KEY)
        store.store(cred)
        assert store.get("c1") == cred

    def test_get(self):
        store = CredentialStore()
        cred = Credential(credential_id="c1", server_name="s1", auth_method=AuthMethod.API_KEY)
        store.store(cred)
        assert store.get("c1").server_name == "s1"

    def test_get_nonexistent(self):
        store = CredentialStore()
        assert store.get("nonexistent") is None

    def test_get_for_server(self):
        store = CredentialStore()
        cred1 = Credential(credential_id="c1", server_name="s1", auth_method=AuthMethod.API_KEY)
        cred2 = Credential(credential_id="c2", server_name="s1", auth_method=AuthMethod.BEARER_TOKEN)
        store.store(cred1)
        store.store(cred2)
        result = store.get_for_server("s1")
        assert len(result) == 2

    def test_remove(self):
        store = CredentialStore()
        cred = Credential(credential_id="c1", server_name="s1", auth_method=AuthMethod.API_KEY)
        store.store(cred)
        assert store.remove("c1") is True
        assert store.get("c1") is None

    def test_remove_nonexistent(self):
        store = CredentialStore()
        assert store.remove("nonexistent") is False

    def test_list_all(self):
        store = CredentialStore()
        cred1 = Credential(credential_id="c1", server_name="s1", auth_method=AuthMethod.API_KEY)
        cred2 = Credential(credential_id="c2", server_name="s2", auth_method=AuthMethod.API_KEY)
        store.store(cred1)
        store.store(cred2)
        assert len(store.list_all()) == 2

    def test_clear(self):
        store = CredentialStore()
        cred = Credential(credential_id="c1", server_name="s1", auth_method=AuthMethod.API_KEY)
        store.store(cred)
        store.clear()
        assert store.list_all() == []


class TestMCPAuth:
    def test_create(self):
        auth = MCPAuth()
        assert auth.store is not None

    def test_add_api_key(self):
        auth = MCPAuth()
        cred = auth.add_api_key("s1", "my-secret-key")
        assert cred.auth_method == AuthMethod.API_KEY
        assert cred.api_key == "my-secret-key"
        assert cred.api_key_header == "X-API-Key"

    def test_add_bearer_token(self):
        auth = MCPAuth()
        cred = auth.add_bearer_token("s1", "token123")
        assert cred.auth_method == AuthMethod.BEARER_TOKEN
        assert cred.token == "token123"

    def test_add_basic_auth(self):
        auth = MCPAuth()
        cred = auth.add_basic_auth("s1", "user", "pass")
        assert cred.auth_method == AuthMethod.BASIC
        assert cred.username == "user"
        assert cred.password == "pass"

    def test_add_mtls(self):
        auth = MCPAuth()
        cred = auth.add_mtls("s1", "/path/cert.pem", "/path/key.pem")
        assert cred.auth_method == AuthMethod.MUTUAL_TLS
        assert cred.client_cert_path == "/path/cert.pem"

    def test_add_oauth2(self):
        auth = MCPAuth()
        cred = auth.add_oauth2("s1", "client123", "secret", "https://auth.example.com/token")
        assert cred.auth_method == AuthMethod.OAUTH2
        assert cred.client_id == "client123"
        assert cred.token_url == "https://auth.example.com/token"

    def test_remove_credential(self):
        auth = MCPAuth()
        cred = auth.add_api_key("s1", "key")
        assert auth.remove_credential(cred.credential_id) is True
        assert auth.store.get(cred.credential_id) is None

    def test_get_credentials(self):
        auth = MCPAuth()
        auth.add_api_key("s1", "key1")
        auth.add_bearer_token("s1", "token1")
        creds = auth.get_credentials("s1")
        assert len(creds) == 2

    def test_get_credentials_expired(self):
        import time
        auth = MCPAuth()
        cred = auth.add_bearer_token("s1", "token")
        cred.expires_at = time.time() - 100
        creds = auth.get_credentials("s1")
        assert len(creds) == 0

    def test_get_auth_headers_api_key(self):
        auth = MCPAuth()
        auth.add_api_key("s1", "my-key", header="X-Custom-Key")
        headers = auth.get_auth_headers("s1")
        assert "X-Custom-Key" in headers
        assert headers["X-Custom-Key"] == "my-key"

    def test_get_auth_headers_bearer(self):
        auth = MCPAuth()
        auth.add_bearer_token("s1", "token123")
        headers = auth.get_auth_headers("s1")
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer token123"

    def test_get_auth_headers_no_credentials(self):
        auth = MCPAuth()
        headers = auth.get_auth_headers("nonexistent")
        assert headers == {}

    def test_validate_credential(self):
        auth = MCPAuth()
        cred = auth.add_api_key("s1", "key")
        assert auth.validate_credential(cred.credential_id) is True

    def test_validate_credential_nonexistent(self):
        auth = MCPAuth()
        assert auth.validate_credential("nonexistent") is False

    def test_check_access(self):
        auth = MCPAuth()
        auth.add_api_key("s1", "key")
        assert auth.check_access("s1") is True
        assert auth.check_access("nonexistent") is False

    def test_check_access_with_method(self):
        auth = MCPAuth()
        auth.add_api_key("s1", "key")
        assert auth.check_access("s1", AuthMethod.API_KEY) is True
        assert auth.check_access("s1", AuthMethod.BEARER_TOKEN) is False

    def test_refresh_token(self):
        auth = MCPAuth()
        cred = auth.add_oauth2("s1", "client", "secret", "https://example.com/token")
        assert auth.refresh_token(cred.credential_id) is True
        assert cred.is_expired is False

    def test_refresh_token_non_oauth(self):
        auth = MCPAuth()
        cred = auth.add_api_key("s1", "key")
        assert auth.refresh_token(cred.credential_id) is False

    def test_on_token_refresh(self):
        auth = MCPAuth()
        refreshed = []
        auth.on_token_refresh(lambda cid, method: refreshed.append(cid))
        cred = auth.add_oauth2("s1", "client", "secret", "https://example.com/token")
        auth.refresh_token(cred.credential_id)
        assert len(refreshed) == 1

    def test_get_stats(self):
        auth = MCPAuth()
        auth.add_api_key("s1", "key")
        auth.add_bearer_token("s2", "token")
        stats = auth.get_stats()
        assert stats["total_credentials"] == 2
        assert stats["valid_credentials"] == 2
        assert "api_key" in stats["method_breakdown"]
        assert "bearer_token" in stats["method_breakdown"]
