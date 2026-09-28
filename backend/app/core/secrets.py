from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


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
