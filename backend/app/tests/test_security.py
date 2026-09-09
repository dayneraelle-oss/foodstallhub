from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_roundtrip():
    hashed = hash_password("super-secret-123")
    assert hashed != "super-secret-123"
    assert verify_password("super-secret-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_verify_rejects_garbage_hash():
    assert verify_password("anything", "not-a-hash") is False


def test_access_token_roundtrip():
    token = create_access_token(subject="42", role="vendor")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "vendor"
    assert "exp" in payload
    assert "iat" in payload