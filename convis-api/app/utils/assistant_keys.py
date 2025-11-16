from typing import Tuple, Optional, Dict, Union
from bson import ObjectId
from fastapi import HTTPException, status
from app.utils.encryption import encryption_service
import os
import logging

logger = logging.getLogger(__name__)

# NOTE: Deployments now supply provider API keys via environment variables.
# The new helper resolve_env_provider_keys below lets callers enforce env-only
# resolution (no DB lookups) to keep the voice pipelines deterministic.


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


def resolve_provider_keys(db, assistant: dict, user_id: ObjectId) -> Dict[str, str]:
    """
    Resolve API keys for all providers configured in the assistant.
    Falls back to environment variables if not configured in database.

    Args:
        db: Database connection
        assistant: Assistant document
        user_id: User ID for looking up stored API keys

    Returns:
        Dict[str, str]: Dictionary mapping provider names to API keys
        Example: {
            'openai': 'sk-...',
            'deepgram': '...',
            'cartesia': 'sk_car_...',
            'elevenlabs': 'sk_...',
            'groq': 'gsk_...',
            'anthropic': 'sk-ant-...'
        }
    """
    provider_keys = {}

    # Get ASR, TTS, and LLM providers from assistant config
    asr_provider = assistant.get('asr_provider', 'openai').lower()
    tts_provider = assistant.get('tts_provider', 'openai').lower()
    llm_provider = assistant.get('llm_provider', 'openai').lower()

    # Collect unique providers needed
    needed_providers = set([asr_provider, tts_provider, llm_provider])

    logger.info(f"Resolving keys for providers: {needed_providers}")

    # Try to get keys from database first (user's stored API keys)
    api_keys_collection = db['api_keys']

    for provider in needed_providers:
        # Skip if already resolved
        if provider in provider_keys:
            continue

        # 1. Check if assistant has a specific API key configured
        api_key_id = assistant.get('api_key_id')
        if api_key_id:
            try:
                key_obj_id = api_key_id if isinstance(api_key_id, ObjectId) else ObjectId(api_key_id)
                api_key_doc = api_keys_collection.find_one({"_id": key_obj_id})

                if api_key_doc and api_key_doc.get('provider', '').lower() == provider:
                    try:
                        decrypted_key = encryption_service.decrypt(api_key_doc['key'])
                        provider_keys[provider] = decrypted_key
                        logger.info(f"✓ Resolved {provider} key from assistant's stored API key")
                        continue
                    except Exception as e:
                        logger.error(f"Failed to decrypt {provider} key: {e}")
            except Exception as e:
                logger.error(f"Error resolving API key ID: {e}")

        # 2. Search for any API key of this provider type for the user
        user_api_key = api_keys_collection.find_one({
            "user_id": user_id,
            "provider": provider
        })

        if user_api_key:
            try:
                decrypted_key = encryption_service.decrypt(user_api_key['key'])
                provider_keys[provider] = decrypted_key
                logger.info(f"✓ Resolved {provider} key from user's stored API keys")
                continue
            except Exception as e:
                logger.error(f"Failed to decrypt {provider} key for user: {e}")

        # 3. Fall back to environment variables
        env_var_map = {
            'openai': 'OPENAI_API_KEY',
            'deepgram': 'DEEPGRAM_API_KEY',
            'sarvam': 'SARVAM_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'cartesia': 'CARTESIA_API_KEY',
            'elevenlabs': 'ELEVENLABS_API_KEY',
            'groq': 'GROQ_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY'
        }

        env_var = env_var_map.get(provider)
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                provider_keys[provider] = env_value.strip()
                logger.info(f"✓ Resolved {provider} key from environment variable {env_var}")
            else:
                logger.warning(f"⚠ No {provider} API key found (not in DB or env var {env_var})")
        else:
            logger.warning(f"⚠ Unknown provider: {provider}, no env var mapping")

    return provider_keys


def resolve_user_provider_key(
    db,
    user_id: Union[str, ObjectId],
    provider: str,
    allow_env_fallback: bool = True
) -> Optional[str]:
    """
    Retrieve a decrypted API key for a specific provider stored by the user.

    Args:
        db: Database connection
        user_id: User's ObjectId (or string convertible to ObjectId)
        provider: Provider name (e.g., 'openai')
        allow_env_fallback: Whether to fall back to env vars if DB lookup fails

    Returns:
        Decrypted API key string or None if unavailable
    """
    try:
        user_obj_id = user_id if isinstance(user_id, ObjectId) else ObjectId(str(user_id))
    except Exception:
        logger.error(f"Invalid user_id provided for provider key lookup: {user_id}")
        return None

    api_keys_collection = db['api_keys']
    key_doc = api_keys_collection.find_one({
        "user_id": user_obj_id,
        "provider": provider.lower()
    })

    if key_doc:
        try:
            return encryption_service.decrypt(key_doc['key'])
        except Exception as exc:
            logger.error(f"Failed to decrypt {provider} key for user {user_id}: {exc}")
            return None

    if not allow_env_fallback:
        return None

    env_var_map = {
        'openai': 'OPENAI_API_KEY',
        'deepgram': 'DEEPGRAM_API_KEY',
        'sarvam': 'SARVAM_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'cartesia': 'CARTESIA_API_KEY',
        'elevenlabs': 'ELEVENLABS_API_KEY',
        'groq': 'GROQ_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY'
    }

    env_var = env_var_map.get(provider.lower())
    if env_var:
        env_value = os.getenv(env_var)
        if env_value:
            logger.info(f"Falling back to environment variable {env_var} for provider {provider}")
            return env_value.strip()
        logger.warning(f"No environment variable configured for provider {provider} ({env_var})")
    else:
        logger.warning(f"No environment mapping defined for provider {provider}")

    return None


def resolve_env_provider_keys(
    asr_provider: str,
    tts_provider: str,
    llm_provider: str
) -> Dict[str, str]:
    """
    Resolve required provider keys strictly from environment variables.
    This bypasses any database lookup to align with deployments where
    keys are injected via container envs only.
    """
    provider_env_map = {
        'openai': 'OPENAI_API_KEY',
        'openai-realtime': 'OPENAI_API_KEY',
        'deepgram': 'DEEPGRAM_API_KEY',
        'sarvam': 'SARVAM_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'cartesia': 'CARTESIA_API_KEY',
        'elevenlabs': 'ELEVENLABS_API_KEY',
        'groq': 'GROQ_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY'
    }

    needed = {asr_provider.lower(), tts_provider.lower(), llm_provider.lower()}
    keys: Dict[str, str] = {}
    missing = []

    for provider in needed:
        env_var = provider_env_map.get(provider)
        if not env_var:
            missing.append(provider)
            continue
        value = os.getenv(env_var)
        if value:
            keys[provider] = value.strip()
        else:
            missing.append(provider)

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API keys for providers: {', '.join(sorted(missing))}. "
                   "Ensure they are set via environment variables."
        )

    return keys
