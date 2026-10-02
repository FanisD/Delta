from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.keyring_store import get_secret


class EncryptionKeyNotConfigured(RuntimeError):
    pass


def _fernet() -> Fernet:
    if not settings.encryption_key:
        raise EncryptionKeyNotConfigured(
            "Set APP_ENCRYPTION_KEY before saving cloud provider credentials."
        )
    try:
        return Fernet(settings.encryption_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise EncryptionKeyNotConfigured("APP_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionKeyNotConfigured(
            "APP_ENCRYPTION_KEY cannot decrypt the saved provider key."
        ) from exc


def load_provider_secret(provider: str, encrypted_fallback: str | None) -> str | None:
    """Read the OS keyring first, then the encrypted database fallback."""

    return get_secret(provider) or (
        decrypt_secret(encrypted_fallback) if encrypted_fallback else None
    )
