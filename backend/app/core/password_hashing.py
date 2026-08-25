"""
Password hashing — Argon2id (RFC 9106) via argon2-cffi.

Security decisions:
- Argon2id is the recommended password-hashing scheme (OWASP Password Storage
  Cheat Sheet). argon2-cffi ships prebuilt wheels on Windows / Linux / macOS,
  so no native compilation is required in any deployment target.
- Legacy hashes produced by the previous SHA-256 salt scheme
  (``sha256$<salt>$<digest>``) remain verifiable so existing accounts can log
  in. Verified legacy hashes are transparently upgraded to Argon2id on the
  next successful login (see auth_service).
- Hashes are prefixed (``$argon2id$...`` / ``sha256$...``) so the verification
  path is unambiguous and no custom crypto is used anywhere.
"""
import hmac
import hashlib

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Tuned per OWASP Argon2id guidance (m=19456 KiB, t=2, p=1 as of 2024).
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)

_LEGACY_PREFIX = "sha256$"


def _legacy_sha256_verify(plain_password: str, hashed_password: str) -> bool:
    """Verify a legacy ``sha256$<salt>$<hex>`` hash. Read-only compatibility path."""
    try:
        _, salt, stored_digest = hashed_password.split("$", 2)
    except ValueError:
        return False
    computed = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, stored_digest)


def is_legacy_hash(hashed_password: str) -> bool:
    return hashed_password.startswith(_LEGACY_PREFIX)


def hash_password(password: str) -> str:
    """Hash a password with Argon2id. Never store plaintext passwords or log them."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verification supporting both Argon2id and legacy SHA-256 hashes."""
    if not hashed_password:
        return False
    if hashed_password.startswith(_LEGACY_PREFIX):
        return _legacy_sha256_verify(plain_password, hashed_password)
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """True when an Argon2id hash should be upgraded (parameters changed) or
    when the hash is still the legacy SHA-256 format."""
    if not hashed_password:
        return False
    if hashed_password.startswith(_LEGACY_PREFIX):
        return True
    try:
        return _hasher.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return True


__all__ = [
    "hash_password",
    "verify_password",
    "needs_rehash",
    "is_legacy_hash",
]
