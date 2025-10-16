from typing import Tuple, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.utils.encryption import encryption_service
import logging

logger = logging.getLogger(__name__)


def resolve_assistant_api_key(db, assistant: dict, required_provider: Optional[str] = "openai") -> Tuple[str, str]:
    """
    Retrieve and decrypt the API key associated with an assistant.

    Args:
        db: Database connection
        assistant: Assistant document
        required_provider: Optional provider constraint (e.g. 'openai')

    Returns:
        Tuple[str, str]: decrypted API key and provider name

    Raises:
        HTTPException: when key is missing, mismatched, or cannot be decrypted
    """
    api_keys_collection = db['api_keys']

    if assistant.get('api_key_id'):
        key_identifier = assistant['api_key_id']
        try:
            key_obj_id = key_identifier if isinstance(key_identifier, ObjectId) else ObjectId(key_identifier)
        except Exception:
            logger.error("Assistant api_key_id is invalid")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assistant API key reference is invalid. Please reassign a key."
            )

        api_key_doc = api_keys_collection.find_one({"_id": key_obj_id})
        if not api_key_doc:
            logger.warning("API key reference missing for assistant %s", assistant.get('_id'))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stored API key is missing. Please update the assistant's API key."
            )

        provider = api_key_doc.get('provider', 'unknown')
        if required_provider and provider != required_provider:
            logger.error("Provider %s not supported (required %s)", provider, required_provider)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Selected API key provider '{provider}' is not supported for this operation."
            )

        try:
            decrypted = encryption_service.decrypt(api_key_doc['key'])
        except Exception:
            logger.exception("Failed to decrypt stored API key")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt stored API key."
            )
        return decrypted, provider

    encrypted_api_key = assistant.get('openai_api_key')
    if encrypted_api_key:
        try:
            decrypted = encryption_service.decrypt(encrypted_api_key)
        except Exception:
            logger.exception("Failed to decrypt legacy API key on assistant %s", assistant.get('_id'))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt API key. Please update the assistant to use a stored key."
            )
        provider = 'openai'
        if required_provider and provider != required_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assistant API key provider '{provider}' is not supported."
            )
        return decrypted, provider

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No API key configured for this assistant. Please assign one before continuing."
    )
