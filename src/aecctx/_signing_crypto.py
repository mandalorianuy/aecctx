from __future__ import annotations

from typing import Any

from .signing import SigningError


def _serialization_modules() -> tuple[Any, Any, Any, Any]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as error:
        raise SigningError("AECCTX_SIGNING_CRYPTO_UNAVAILABLE", "install aecctx[signing]") from error
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def load_private_key(private_key_pem: bytes, password: bytes | None) -> Any:
    _, serialization, Ed25519PrivateKey, _ = _serialization_modules()
    try:
        key = serialization.load_pem_private_key(private_key_pem, password=password)
    except (TypeError, ValueError) as error:
        raise SigningError("AECCTX_SIGNING_PRIVATE_KEY_INVALID", "private key or password is invalid") from error
    if not isinstance(key, Ed25519PrivateKey):
        raise SigningError("AECCTX_SIGNING_PRIVATE_KEY_INVALID", "private key is not Ed25519 PKCS#8")
    return key


def load_public_key(raw_public_key: bytes) -> Any:
    _, _, _, Ed25519PublicKey = _serialization_modules()
    try:
        return Ed25519PublicKey.from_public_bytes(raw_public_key)
    except ValueError as error:
        raise SigningError("AECCTX_SIGNING_PUBLIC_KEY_INVALID", "public key is not a 32-byte Ed25519 key") from error


def sign_bytes(private_key: Any, message: bytes) -> bytes:
    signature = private_key.sign(message)
    if len(signature) != 64:
        raise SigningError("AECCTX_SIGNING_SIGNATURE_INVALID", "Ed25519 produced an invalid signature length")
    return signature


def verify_bytes(public_key: Any, signature: bytes, message: bytes) -> bool:
    InvalidSignature, _, _, _ = _serialization_modules()
    try:
        public_key.verify(signature, message)
    except InvalidSignature:
        return False
    return True
