from typing import Any, Dict, Optional, Tuple

from app.utils.encryption import encryption_service


def decrypt_twilio_credentials(connection: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    """Return decrypted Twilio account SID and auth token from a provider connection document."""
    if not connection:
        return None, None

    account_sid = connection.get("account_sid")
    auth_token = connection.get("auth_token")

    if account_sid:
        account_sid = encryption_service.decrypt(account_sid)
    if auth_token:
        auth_token = encryption_service.decrypt(auth_token)

    return account_sid, auth_token


def mask_sensitive_value(value: Optional[str], show_last: int = 4) -> Optional[str]:
    """Return a masked representation of a sensitive value for logging/UI purposes."""
    if not value:
        return value
    if len(value) <= show_last:
        return value
    return f"{'*' * (len(value) - show_last)}{value[-show_last:]}"
