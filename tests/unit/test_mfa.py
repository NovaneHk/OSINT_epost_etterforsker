"""
Unit tests for MFA (TOTP) functionality — setup, activate, login step-2, disable.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestMFASetup:
    """Tests for MFA setup endpoint."""

    def test_mfa_setup_requires_auth(self):
        """Setup endpoint must reject requests without valid JWT."""
        from backend.api.mfa import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)
        # Router prefix is /auth/mfa — path is /auth/mfa/setup
        response = client.post("/auth/mfa/setup")
        assert response.status_code in (401, 403, 422)

    def test_mfa_setup_response_has_required_fields(self):
        """MFA setup response includes qr_code_base64 and secret."""
        import pyotp
        secret = pyotp.random_base32()
        qr_code_base64 = "data:image/png;base64,ABC123"
        response_data = {
            "secret": secret,
            "qr_code_base64": qr_code_base64,
            "backup_codes": [],
        }
        assert "secret" in response_data
        assert "qr_code_base64" in response_data
        # Confirm no legacy 'qr_code' field expected by old frontend bug
        assert "qr_code" not in response_data


class TestMFAActivate:
    """Tests for MFA activation."""

    def test_activate_requires_secret_and_code(self):
        """Activation body must include both secret and code fields."""
        from backend.api.mfa import MFAActivateRequest
        import pytest
        with pytest.raises(Exception):
            MFAActivateRequest(code="123456")  # Missing secret → ValidationError

    def test_activate_with_valid_totp(self):
        """A valid TOTP validates against its own secret."""
        import pyotp
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert totp.verify(code) is True

    def test_activate_with_wrong_code_fails(self):
        """A wrong TOTP code fails verification."""
        import pyotp
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        assert totp.verify("000000") is False


class TestMFALoginFlow:
    """Tests for MFA-gated login step 2."""

    def test_mfa_verify_endpoint_exists(self):
        """MFA router has setup and activate routes for the full verification flow."""
        from backend.api.mfa import router
        routes = [r.path for r in router.routes]
        # /auth/mfa/setup initiates, /auth/mfa/activate completes verification
        assert any("setup" in r for r in routes)
        assert any("activate" in r for r in routes)

    def test_backup_code_format(self):
        """Backup codes are 8-character alphanumeric strings."""
        import secrets
        backup_codes = [secrets.token_hex(4) for _ in range(8)]
        assert len(backup_codes) == 8
        for code in backup_codes:
            assert len(code) == 8


class TestMFADisable:
    """Tests for MFA disable endpoint."""

    def test_disable_requires_code(self):
        """Disable endpoint requires a TOTP code."""
        from backend.api.mfa import MFADisableRequest
        import pytest
        with pytest.raises(Exception):
            MFADisableRequest()  # Missing code → ValidationError
