import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "Delta"


def set_secret(provider: str, value: str) -> bool:
    try:
        keyring.set_password(SERVICE_NAME, provider, value)
    except (KeyringError, RuntimeError):
        return False
    return True


def get_secret(provider: str) -> str | None:
    try:
        return keyring.get_password(SERVICE_NAME, provider)
    except (KeyringError, RuntimeError):
        return None


def delete_secret(provider: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, provider)
    except (KeyringError, RuntimeError):
        return
