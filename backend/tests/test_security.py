"""测试安全工具：密码哈希和 JWT 令牌"""
import pytest
from datetime import datetime, timezone, timedelta

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "my-secret-password-123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_same_password_different_hashes(self):
        pwd = "same-password"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2  # bcrypt salts produce different hashes
        assert verify_password(pwd, h1) is True
        assert verify_password(pwd, h2) is True


class TestJWT:
    def test_create_and_decode(self):
        data = {"sub": "user-123", "role": "free"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "free"
        assert "exp" in payload

    def test_invalid_token(self):
        assert decode_access_token("invalid-token") is None
        assert decode_access_token("") is None

    def test_expired_token(self):
        from app.core.config import settings
        from jose import jwt

        expired = jwt.encode(
            {"sub": "test", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        assert decode_access_token(expired) is None

    def test_custom_expiry(self):
        data = {"sub": "test-user"}
        token = create_access_token(data, expires_delta=timedelta(hours=2))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "test-user"
