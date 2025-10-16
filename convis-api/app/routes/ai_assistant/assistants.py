from fastapi import APIRouter, HTTPException, status
from app.models.ai_assistant import (
    AIAssistantCreate,
    AIAssistantUpdate,
    AIAssistantResponse,
    AIAssistantListResponse,
    DeleteResponse,
    KnowledgeBaseFile
)
from app.config.database import Database
from app.utils.encryption import encryption_service
from bson import ObjectId
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def resolve_api_key_metadata(api_keys_collection, key_identifier) -> Optional[Dict[str, Any]]:
    """
    Retrieve metadata for a stored API key without exposing the raw secret.
    """
    if not key_identifier:
        return None

    try:
        key_obj_id = key_identifier if isinstance(key_identifier, ObjectId) else ObjectId(key_identifier)
    except Exception:
        return None

    doc = api_keys_collection.find_one({"_id": key_obj_id})
    if not doc:
        return None

    return {
        "id": str(doc['_id']),
        "label": doc['label'],
        "provider": doc['provider'],
    }

def assistant_has_api_key(assistant: dict) -> bool:
    return bool(assistant.get('api_key_id') or assistant.get('openai_api_key'))

@router.post("/", response_model=AIAssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(assistant_data: AIAssistantCreate):
    """
    Create a new AI assistant for a user

    Args:
        assistant_data: AI assistant configuration

    Returns:
        AIAssistantResponse: Created assistant details

    Raises:
        HTTPException: If user not found or error occurs
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        assistants_collection = db['assistants']
        api_keys_collection = db['api_keys']
        api_keys_collection = db['api_keys']

        logger.info(f"Creating AI assistant for user: {assistant_data.user_id}")

        # Verify user exists
        try:
            user_obj_id = ObjectId(assistant_data.user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )

        user = users_collection.find_one({"_id": user_obj_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        selected_key_doc = None
        encrypted_api_key: Optional[str] = None
        api_key_obj_id: Optional[ObjectId] = None

        if assistant_data.api_key_id:
            try:
                api_key_obj_id = ObjectId(assistant_data.api_key_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid api_key_id format"
                )

            selected_key_doc = api_keys_collection.find_one({"_id": api_key_obj_id, "user_id": user_obj_id})
            if not selected_key_doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected API key not found"
                )

            if selected_key_doc.get('provider') != 'openai':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected API key provider is not supported for AI assistants yet"
                )
        elif assistant_data.openai_api_key:
            encrypted_api_key = encryption_service.encrypt(assistant_data.openai_api_key)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An API key selection is required"
            )

        # Create assistant document
        now = datetime.utcnow()
        assistant_doc = {
            "user_id": user_obj_id,
            "name": assistant_data.name,
            "system_message": assistant_data.system_message,
            "voice": assistant_data.voice,
            "temperature": assistant_data.temperature,
            "created_at": now,
            "updated_at": now
        }

        if api_key_obj_id:
            assistant_doc["api_key_id"] = api_key_obj_id
            assistant_doc["openai_api_key"] = None
        else:
            assistant_doc["openai_api_key"] = encrypted_api_key

        result = assistants_collection.insert_one(assistant_doc)
        logger.info(f"AI assistant created with ID: {result.inserted_id}")

        api_key_metadata = None
        if selected_key_doc:
            api_key_metadata = {
                "id": str(selected_key_doc['_id']),
                "label": selected_key_doc['label'],
                "provider": selected_key_doc['provider']
            }

        return AIAssistantResponse(
            id=str(result.inserted_id),
            user_id=str(assistant_data.user_id),
            name=assistant_data.name,
            system_message=assistant_data.system_message,
            voice=assistant_data.voice,
            temperature=assistant_data.temperature,
            has_api_key=True,  # Just created with API key
            api_key_id=api_key_metadata["id"] if api_key_metadata else None,
            api_key_label=api_key_metadata["label"] if api_key_metadata else None,
            api_key_provider=api_key_metadata["provider"] if api_key_metadata else ("openai" if encrypted_api_key else None),
            knowledge_base_files=[],  # New assistants start with no knowledge base
            has_knowledge_base=False,
            created_at=now.isoformat() + "Z",
            updated_at=now.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error creating AI assistant: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create AI assistant: {str(error)}"
        )

@router.get("/user/{user_id}", response_model=AIAssistantListResponse, status_code=status.HTTP_200_OK)
async def get_user_assistants(user_id: str):
    """
    Get all AI assistants for a specific user

    Args:
        user_id: User ID

    Returns:
        AIAssistantListResponse: List of user's assistants

    Raises:
        HTTPException: If user not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']
        api_keys_collection = db['api_keys']
        api_keys_collection = db['api_keys']
        api_keys_collection = db['api_keys']

        logger.info(f"Fetching AI assistants for user: {user_id}")

        # Convert user_id to ObjectId
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )

        # Find all assistants for this user
        assistants_cursor = assistants_collection.find({"user_id": user_obj_id})
        api_keys_collection = db['api_keys']
        api_key_cache: Dict[str, Optional[Dict[str, str]]] = {}
        assistants = []

        for assistant in assistants_cursor:
            # Get knowledge base files
            kb_files = []
            for file_data in assistant.get('knowledge_base_files', []):
                kb_files.append(KnowledgeBaseFile(
                    filename=file_data['filename'],
                    file_type=file_data['file_type'],
                    file_size=file_data['file_size'],
                    uploaded_at=file_data['uploaded_at'].isoformat() + "Z",
                    file_path=file_data['file_path']
                ))

            api_key_metadata = None
            key_identifier = assistant.get('api_key_id')
            if key_identifier:
                cache_key = str(key_identifier)
                if cache_key not in api_key_cache:
                    api_key_cache[cache_key] = resolve_api_key_metadata(api_keys_collection, key_identifier)
                api_key_metadata = api_key_cache.get(cache_key)
            elif assistant.get('openai_api_key'):
                api_key_metadata = {
                    "id": None,
                    "label": "Direct key",
                    "provider": "openai"
                }

            assistants.append(AIAssistantResponse(
                id=str(assistant['_id']),
                user_id=str(assistant['user_id']),
                name=assistant['name'],
                system_message=assistant['system_message'],
                voice=assistant['voice'],
                temperature=assistant['temperature'],
                has_api_key=assistant_has_api_key(assistant),
                api_key_id=api_key_metadata.get("id") if api_key_metadata else None,
                api_key_label=api_key_metadata.get("label") if api_key_metadata else None,
                api_key_provider=api_key_metadata.get("provider") if api_key_metadata else None,
                knowledge_base_files=kb_files,
                has_knowledge_base=len(kb_files) > 0,
                created_at=assistant['created_at'].isoformat() + "Z",
                updated_at=assistant['updated_at'].isoformat() + "Z"
            ))

        logger.info(f"Found {len(assistants)} assistants for user {user_id}")

        return AIAssistantListResponse(
            assistants=assistants,
            total=len(assistants)
        )

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error fetching AI assistants: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch AI assistants: {str(error)}"
        )

@router.get("/{assistant_id}", response_model=AIAssistantResponse, status_code=status.HTTP_200_OK)
async def get_assistant(assistant_id: str):
    """
    Get a specific AI assistant by ID

    Args:
        assistant_id: Assistant ID

    Returns:
        AIAssistantResponse: Assistant details

    Raises:
        HTTPException: If assistant not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']

        logger.info(f"Fetching AI assistant: {assistant_id}")

        # Convert to ObjectId
        try:
            assistant_obj_id = ObjectId(assistant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assistant_id format"
            )

        assistant = assistants_collection.find_one({"_id": assistant_obj_id})

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI assistant not found"
            )

        kb_files = []
        for file_data in assistant.get('knowledge_base_files', []):
            kb_files.append(KnowledgeBaseFile(
                filename=file_data['filename'],
                file_type=file_data['file_type'],
                file_size=file_data['file_size'],
                uploaded_at=file_data['uploaded_at'].isoformat() + "Z",
                file_path=file_data['file_path']
            ))

        api_key_metadata = None
        api_keys_collection = db['api_keys']
        if assistant.get('api_key_id'):
            api_key_metadata = resolve_api_key_metadata(api_keys_collection, assistant.get('api_key_id'))
        elif assistant.get('openai_api_key'):
            api_key_metadata = {
                "id": None,
                "label": "Direct key",
                "provider": "openai"
            }

        return AIAssistantResponse(
            id=str(assistant['_id']),
            user_id=str(assistant['user_id']),
            name=assistant['name'],
            system_message=assistant['system_message'],
            voice=assistant['voice'],
            temperature=assistant['temperature'],
            has_api_key=assistant_has_api_key(assistant),
            api_key_id=api_key_metadata.get("id") if api_key_metadata else None,
            api_key_label=api_key_metadata.get("label") if api_key_metadata else None,
            api_key_provider=api_key_metadata.get("provider") if api_key_metadata else None,
            knowledge_base_files=kb_files,
            has_knowledge_base=len(kb_files) > 0,
            created_at=assistant['created_at'].isoformat() + "Z",
            updated_at=assistant['updated_at'].isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error fetching AI assistant: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch AI assistant: {str(error)}"
        )

@router.put("/{assistant_id}", response_model=AIAssistantResponse, status_code=status.HTTP_200_OK)
async def update_assistant(assistant_id: str, update_data: AIAssistantUpdate):
    """
    Update an existing AI assistant

    Args:
        assistant_id: Assistant ID
        update_data: Fields to update

    Returns:
        AIAssistantResponse: Updated assistant details

    Raises:
        HTTPException: If assistant not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']
        api_keys_collection = db['api_keys']

        logger.info(f"Updating AI assistant: {assistant_id}")

        # Convert to ObjectId
        try:
            assistant_obj_id = ObjectId(assistant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assistant_id format"
            )

        # Check if assistant exists
        assistant = assistants_collection.find_one({"_id": assistant_obj_id})
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI assistant not found"
            )

        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}

        if update_data.name is not None:
            update_doc["name"] = update_data.name
        if update_data.system_message is not None:
            update_doc["system_message"] = update_data.system_message
        if update_data.voice is not None:
            update_doc["voice"] = update_data.voice
        if update_data.temperature is not None:
            update_doc["temperature"] = update_data.temperature
        if update_data.api_key_id is not None:
            if update_data.api_key_id == "":
                update_doc["api_key_id"] = None
            else:
                try:
                    api_key_obj_id = ObjectId(update_data.api_key_id)
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid api_key_id format"
                    )
                api_key_doc = api_keys_collection.find_one({"_id": api_key_obj_id, "user_id": assistant['user_id']})
                if not api_key_doc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Selected API key not found"
                    )
                if api_key_doc.get('provider') != 'openai':
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected API key provider is not supported for AI assistants yet"
                    )
                update_doc["api_key_id"] = api_key_obj_id
                update_doc["openai_api_key"] = None
        if update_data.openai_api_key is not None:
            # Encrypt the new API key
            update_doc["openai_api_key"] = encryption_service.encrypt(update_data.openai_api_key)
            update_doc["api_key_id"] = None

        # Update the assistant
        assistants_collection.update_one(
            {"_id": assistant_obj_id},
            {"$set": update_doc}
        )

        # Fetch updated assistant
        updated_assistant = assistants_collection.find_one({"_id": assistant_obj_id})

        logger.info(f"AI assistant {assistant_id} updated successfully")

        # Get knowledge base files
        kb_files = []
        for file_data in updated_assistant.get('knowledge_base_files', []):
            kb_files.append(KnowledgeBaseFile(
                filename=file_data['filename'],
                file_type=file_data['file_type'],
                file_size=file_data['file_size'],
                uploaded_at=file_data['uploaded_at'].isoformat() + "Z",
                file_path=file_data['file_path']
            ))

        api_key_metadata = None
        if updated_assistant.get('api_key_id'):
            api_key_metadata = resolve_api_key_metadata(api_keys_collection, updated_assistant.get('api_key_id'))
        elif updated_assistant.get('openai_api_key'):
            api_key_metadata = {
                "id": None,
                "label": "Direct key",
                "provider": "openai"
            }

        return AIAssistantResponse(
            id=str(updated_assistant['_id']),
            user_id=str(updated_assistant['user_id']),
            name=updated_assistant['name'],
            system_message=updated_assistant['system_message'],
            voice=updated_assistant['voice'],
            temperature=updated_assistant['temperature'],
            has_api_key=assistant_has_api_key(updated_assistant),
            api_key_id=api_key_metadata.get("id") if api_key_metadata else None,
            api_key_label=api_key_metadata.get("label") if api_key_metadata else None,
            api_key_provider=api_key_metadata.get("provider") if api_key_metadata else None,
            knowledge_base_files=kb_files,
            has_knowledge_base=len(kb_files) > 0,
            created_at=updated_assistant['created_at'].isoformat() + "Z",
            updated_at=updated_assistant['updated_at'].isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error updating AI assistant: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI assistant: {str(error)}"
        )

@router.delete("/{assistant_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_assistant(assistant_id: str):
    """
    Delete an AI assistant

    Args:
        assistant_id: Assistant ID

    Returns:
        DeleteResponse: Success message

    Raises:
        HTTPException: If assistant not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']

        logger.info(f"Deleting AI assistant: {assistant_id}")

        # Convert to ObjectId
        try:
            assistant_obj_id = ObjectId(assistant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assistant_id format"
            )

        # Delete the assistant
        result = assistants_collection.delete_one({"_id": assistant_obj_id})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI assistant not found"
            )

        logger.info(f"AI assistant {assistant_id} deleted successfully")

        return DeleteResponse(message="AI assistant deleted successfully")

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error deleting AI assistant: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete AI assistant: {str(error)}"
        )
