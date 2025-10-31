from typing import Any, Dict, Optional, Tuple

from app.utils.encryption import encryption_service


def decrypt_frejun_credentials(connection: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    """Return decrypted FreJun API key and secret from a provider connection document."""
    if not connection:
        return None, None

    api_key = connection.get("api_key")
    api_secret = connection.get("api_secret")

    if api_key:
        api_key = encryption_service.decrypt(api_key)
    if api_secret:
        api_secret = encryption_service.decrypt(api_secret)

    return api_key, api_secret


def mask_sensitive_value(value: Optional[str], show_last: int = 4) -> Optional[str]:
    """Return a masked representation of a sensitive value for logging/UI purposes."""
    if not value:
        return value
    if len(value) <= show_last:
        return value
    return f"{'*' * (len(value) - show_last)}{value[-show_last:]}"
