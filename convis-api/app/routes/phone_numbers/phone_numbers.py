from fastapi import APIRouter, HTTPException, status, Request
from app.models.phone_number import (
    ProviderCredentials,
    PhoneNumberResponse,
    PhoneNumberListResponse,
    CallLogResponse,
    CallLogListResponse,
    ConnectProviderResponse,
    PhoneNumberCapabilities,
    AssignAssistantRequest,
    AssignAssistantResponse,
    ProviderConnectionStatus,
    ProviderConnectionResponse
)
from app.config.database import Database
from app.config.settings import settings
from app.utils.encryption import encryption_service
from app.utils.twilio_helpers import decrypt_twilio_credentials
from bson import ObjectId
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/connection-status/{user_id}", response_model=ProviderConnectionResponse, status_code=status.HTTP_200_OK)
async def get_provider_connection_status(user_id: str):
    """
    Check if user has any provider connections established

    Args:
        user_id: User ID

    Returns:
        ProviderConnectionResponse: List of connected providers

    Raises:
        HTTPException: If user not found or error occurs
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Checking provider connections for user: {user_id}")

        # Verify user exists
        try:
            user_obj_id = ObjectId(user_id)
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

        # Find all provider connections for this user
        connections = list(provider_connections_collection.find({"user_id": user_obj_id}))

        connection_statuses = []
        for conn in connections:
            connection_statuses.append(ProviderConnectionStatus(
                provider=conn["provider"],
                is_connected=conn.get("status") == "active",
                account_sid=conn.get("account_sid", "")[:8] + "..." if conn.get("account_sid") else None,  # Masked
                connected_at=conn["created_at"].isoformat() + "Z" if conn.get("created_at") else None
            ))

        # If no connections, return empty list
        if not connection_statuses:
            return ProviderConnectionResponse(
                message="No provider connections found",
                connections=[]
            )

        return ProviderConnectionResponse(
            message=f"Found {len(connection_statuses)} provider connection(s)",
            connections=connection_statuses
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking provider connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking provider connections: {str(e)}"
        )


@router.post("/connect", response_model=ConnectProviderResponse, status_code=status.HTTP_200_OK)
async def connect_provider(credentials: ProviderCredentials):
    """
    Connect a telephony provider and sync phone numbers

    Args:
        credentials: Provider credentials (account_sid, auth_token, etc.)

    Returns:
        ConnectProviderResponse: List of synced phone numbers

    Raises:
        HTTPException: If credentials are invalid or sync fails
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        phone_numbers_collection = db['phone_numbers']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Connecting {credentials.provider} for user: {credentials.user_id}")

        # Verify user exists
        try:
            user_obj_id = ObjectId(credentials.user_id)
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

        phone_numbers = []

        # Handle Twilio provider
        if credentials.provider.lower() == "twilio":
            try:
                # Initialize Twilio client
                client = Client(credentials.account_sid, credentials.auth_token)

                # Test connection and fetch phone numbers
                incoming_phone_numbers = client.incoming_phone_numbers.list(limit=50)

                logger.info(f"Found {len(incoming_phone_numbers)} phone numbers from Twilio")

                # Store or update provider connection
                now = datetime.utcnow()
                encrypted_sid = encryption_service.encrypt(credentials.account_sid)
                encrypted_token = encryption_service.encrypt(credentials.auth_token)

                provider_connection = {
                    "user_id": user_obj_id,
                    "provider": "twilio",
                    "account_sid": encrypted_sid,
                    "auth_token": encrypted_token,
                    "account_sid_last4": credentials.account_sid[-4:],
                    "status": "active",
                    "created_at": now,
                    "updated_at": now
                }

                # Upsert provider connection
                provider_connections_collection.update_one(
                    {"user_id": user_obj_id, "provider": "twilio"},
                    {"$set": provider_connection},
                    upsert=True
                )

                # Store phone numbers
                for record in incoming_phone_numbers:
                    phone_doc = {
                        "user_id": user_obj_id,
                        "phone_number": record.phone_number,
                        "provider": "twilio",
                        "provider_sid": record.sid,
                        "friendly_name": record.friendly_name or record.phone_number,
                        "capabilities": {
                            "voice": record.capabilities.get("voice", False),
                            "sms": record.capabilities.get("sms", False),
                            "mms": record.capabilities.get("mms", False)
                        },
                        "status": "active",
                        "created_at": now,
                        "updated_at": now
                    }

                    # Upsert phone number
                    result = phone_numbers_collection.update_one(
                        {"user_id": user_obj_id, "provider_sid": record.sid},
                        {"$set": phone_doc},
                        upsert=True
                    )

                    # Get the document ID
                    if result.upserted_id:
                        doc_id = str(result.upserted_id)
                    else:
                        doc = phone_numbers_collection.find_one({"user_id": user_obj_id, "provider_sid": record.sid})
                        doc_id = str(doc["_id"])

                    phone_numbers.append(PhoneNumberResponse(
                        id=doc_id,
                        phone_number=record.phone_number,
                        provider="twilio",
                        friendly_name=record.friendly_name or record.phone_number,
                        capabilities=PhoneNumberCapabilities(
                            voice=record.capabilities.get("voice", False),
                            sms=record.capabilities.get("sms", False),
                            mms=record.capabilities.get("mms", False)
                        ),
                        status="active",
                        created_at=now.isoformat() + "Z"
                    ))

                logger.info(f"Successfully synced {len(phone_numbers)} phone numbers")

                return ConnectProviderResponse(
                    message=f"Successfully connected Twilio and synced {len(phone_numbers)} phone numbers",
                    phone_numbers=phone_numbers,
                    provider="twilio"
                )

            except TwilioRestException as e:
                logger.error(f"Twilio API error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid Twilio credentials or API error: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error connecting to Twilio: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error connecting to Twilio: {str(e)}"
                )

        # Handle Frejun/Teler provider
        elif credentials.provider.lower() == "frejun":
            try:
                # Note: Frejun/Teler requires a self-hosted bridge server
                # We'll store credentials and allow manual phone number management
                logger.info(f"Connecting Frejun for user: {credentials.user_id}")

                # Store or update provider connection
                now = datetime.utcnow()
                encrypted_account_id = encryption_service.encrypt(credentials.account_sid)
                encrypted_api_key = encryption_service.encrypt(credentials.auth_token)

                provider_connection = {
                    "user_id": user_obj_id,
                    "provider": "frejun",
                    "account_sid": encrypted_account_id,
                    "auth_token": encrypted_api_key,
                    "account_sid_last4": credentials.account_sid[-4:] if len(credentials.account_sid) >= 4 else "****",
                    "status": "active",
                    "created_at": now,
                    "updated_at": now
                }

                # Upsert provider connection
                provider_connections_collection.update_one(
                    {"user_id": user_obj_id, "provider": "frejun"},
                    {"$set": provider_connection},
                    upsert=True
                )

                logger.info(f"Successfully connected Frejun provider for user {credentials.user_id}")

                # Return success message - phone numbers will be added manually
                return ConnectProviderResponse(
                    message="Successfully connected Frejun. You can now add phone numbers manually or configure your Frejun bridge server.",
                    phone_numbers=[],
                    provider="frejun"
                )
            except Exception as e:
                logger.error(f"Error connecting to Frejun: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error connecting to Frejun: {str(e)}"
                )

        else:
            # Placeholder for other providers
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{credentials.provider}' is not yet supported. Currently supported: Twilio, Frejun."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in connect_provider: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/sync/{user_id}", response_model=ConnectProviderResponse, status_code=status.HTTP_200_OK)
async def sync_phone_numbers(user_id: str):
    """
    Sync phone numbers using existing provider connection
    (No need to re-enter credentials)

    Args:
        user_id: User ID

    Returns:
        ConnectProviderResponse: List of synced phone numbers

    Raises:
        HTTPException: If no provider connection found or sync fails
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        phone_numbers_collection = db['phone_numbers']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Syncing phone numbers for user: {user_id}")

        # Verify user exists
        try:
            user_obj_id = ObjectId(user_id)
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

        # Get existing Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found. Please connect Twilio first."
            )

        phone_numbers = []

        try:
            # Initialize Twilio client with stored credentials
            account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
            if not account_sid or not auth_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stored Twilio credentials are missing or invalid. Please reconnect your provider."
                )

            client = Client(account_sid, auth_token)

            # Fetch phone numbers
            incoming_phone_numbers = client.incoming_phone_numbers.list(limit=50)

            logger.info(f"Found {len(incoming_phone_numbers)} phone numbers from Twilio")

            # Store phone numbers
            now = datetime.utcnow()
            for record in incoming_phone_numbers:
                phone_doc = {
                    "user_id": user_obj_id,
                    "phone_number": record.phone_number,
                    "provider": "twilio",
                    "provider_sid": record.sid,
                    "friendly_name": record.friendly_name or record.phone_number,
                    "capabilities": {
                        "voice": record.capabilities.get("voice", False),
                        "sms": record.capabilities.get("sms", False),
                        "mms": record.capabilities.get("mms", False)
                    },
                    "status": "active",
                    "updated_at": now
                }

                # Upsert phone number (preserve existing assignments)
                result = phone_numbers_collection.update_one(
                    {"user_id": user_obj_id, "provider_sid": record.sid},
                    {"$set": phone_doc, "$setOnInsert": {"created_at": now}},
                    upsert=True
                )

                # Get the document
                doc = phone_numbers_collection.find_one({"user_id": user_obj_id, "provider_sid": record.sid})

                phone_numbers.append(PhoneNumberResponse(
                    id=str(doc["_id"]),
                    phone_number=record.phone_number,
                    provider="twilio",
                    friendly_name=record.friendly_name or record.phone_number,
                    capabilities=PhoneNumberCapabilities(
                        voice=record.capabilities.get("voice", False),
                        sms=record.capabilities.get("sms", False),
                        mms=record.capabilities.get("mms", False)
                    ),
                    status="active",
                    created_at=doc.get("created_at", now).isoformat() + "Z",
                    assigned_assistant_id=str(doc["assigned_assistant_id"]) if doc.get("assigned_assistant_id") else None,
                    assigned_assistant_name=doc.get("assigned_assistant_name"),
                    webhook_url=doc.get("webhook_url")
                ))

            logger.info(f"Successfully synced {len(phone_numbers)} phone numbers")

            return ConnectProviderResponse(
                message=f"Successfully synced {len(phone_numbers)} phone numbers from Twilio",
                phone_numbers=phone_numbers,
                provider="twilio"
            )

        except TwilioRestException as e:
            logger.error(f"Twilio API error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Twilio credentials or API error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error syncing phone numbers: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error syncing phone numbers: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in sync_phone_numbers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=PhoneNumberListResponse)
async def get_user_phone_numbers(user_id: str):
    """
    Get all phone numbers for a user

    Args:
        user_id: User ID

    Returns:
        PhoneNumberListResponse: List of user's phone numbers
    """
    try:
        db = Database.get_db()
        phone_numbers_collection = db['phone_numbers']

        # Validate user_id
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )

        # Fetch phone numbers
        phone_docs = list(phone_numbers_collection.find({"user_id": user_obj_id}))

        phone_numbers = []
        for doc in phone_docs:
            phone_numbers.append(PhoneNumberResponse(
                id=str(doc["_id"]),
                phone_number=doc["phone_number"],
                provider=doc["provider"],
                friendly_name=doc.get("friendly_name"),
                capabilities=PhoneNumberCapabilities(**doc["capabilities"]),
                status=doc.get("status", "active"),
                created_at=doc["created_at"].isoformat() + "Z",
                assigned_assistant_id=str(doc["assigned_assistant_id"]) if doc.get("assigned_assistant_id") else None,
                assigned_assistant_name=doc.get("assigned_assistant_name"),
                webhook_url=doc.get("webhook_url")
            ))

        return PhoneNumberListResponse(
            phone_numbers=phone_numbers,
            total=len(phone_numbers)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching phone numbers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching phone numbers: {str(e)}"
        )


@router.get("/call-logs/user/{user_id}", response_model=CallLogListResponse)
async def get_user_call_logs(user_id: str, limit: int = 100):
    """
    Get comprehensive call logs for all user's phone numbers with all Twilio details

    Args:
        user_id: User ID
        limit: Maximum number of call logs to return (default: 100)

    Returns:
        CallLogListResponse: Detailed list of call logs with all Twilio information
    """
    try:
        db = Database.get_db()
        phone_numbers_collection = db['phone_numbers']
        provider_connections_collection = db['provider_connections']
        assistants_collection = db['assistants']

        # Validate user_id
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )

        # Get user's phone numbers with assistant assignments
        phone_docs = list(phone_numbers_collection.find({"user_id": user_obj_id}))

        if not phone_docs:
            return CallLogListResponse(call_logs=[], total=0)

        # Create a mapping of phone numbers to assistant info
        phone_to_assistant = {}
        for phone_doc in phone_docs:
            if phone_doc.get("assigned_assistant_id"):
                phone_to_assistant[phone_doc["phone_number"]] = {
                    "id": str(phone_doc["assigned_assistant_id"]),
                    "name": phone_doc.get("assigned_assistant_name", "Unknown Assistant")
                }

        # Get Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            return CallLogListResponse(call_logs=[], total=0)

        # Fetch comprehensive call logs from Twilio
        try:
            account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
            if not account_sid or not auth_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stored Twilio credentials are missing or invalid. Please reconnect your provider."
                )

            client = Client(account_sid, auth_token)

            # Get user's phone numbers for filtering
            user_phone_numbers = [doc["phone_number"] for doc in phone_docs]

            # Fetch calls from Twilio (both to and from user's numbers)
            calls = client.calls.list(limit=limit)

            # Also fetch calls from our database (for outbound calls we tracked)
            call_logs_collection = db['call_logs']
            db_calls = list(call_logs_collection.find({"user_id": user_obj_id}).sort("created_at", -1).limit(limit))

            call_logs = []
            processed_sids = set()  # Track which call SIDs we've already processed

            # First, process database calls (our tracked outbound calls)
            for db_call in db_calls:
                call_sid = db_call.get("call_sid")
                if call_sid:
                    processed_sids.add(call_sid)

                # Get assistant info
                assistant_info = None
                if db_call.get("assigned_assistant_id"):
                    assistant_info = {
                        "id": str(db_call["assigned_assistant_id"]),
                        "name": db_call.get("assistant_name", "Unknown Assistant")
                    }
                elif db_call.get("assistant_id"):
                    assistant_info = {
                        "id": str(db_call["assistant_id"]),
                        "name": db_call.get("assistant_name", "Unknown Assistant")
                    }

                call_log = CallLogResponse(
                    id=call_sid or str(db_call["_id"]),
                    **{"from": db_call.get("from_number", "Unknown")},
                    to=db_call.get("to_number", "Unknown"),
                    direction=db_call.get("direction", "outbound-api"),
                    status=db_call.get("status", "unknown"),
                    duration=db_call.get("duration"),
                    start_time=db_call.get("start_time"),
                    end_time=db_call.get("end_time"),
                    date_created=db_call.get("created_at").isoformat() + "Z" if db_call.get("created_at") else None,
                    date_updated=db_call.get("updated_at").isoformat() + "Z" if db_call.get("updated_at") else None,
                    answered_by=None,
                    caller_name=None,
                    forwarded_from=None,
                    parent_call_sid=None,
                    price=None,
                    price_unit=None,
                    recording_url=None,
                    assistant_id=assistant_info["id"] if assistant_info else None,
                    assistant_name=assistant_info["name"] if assistant_info else None,
                    queue_time=None
                )
                call_logs.append(call_log)

            # Then process Twilio calls (skip if already processed from database)
            for call in calls:
                # Skip if we already processed this call from database
                if call.sid in processed_sids:
                    continue
                # Get from number (handle different formats)
                from_number = getattr(call, 'from_', None) or getattr(call, 'from', None)

                # Check if this call involves any of the user's phone numbers
                involves_user = (
                    call.to in user_phone_numbers or
                    from_number in user_phone_numbers
                )

                if not involves_user:
                    continue

                # Determine which assistant handled this call (if inbound)
                assistant_info = None
                if call.direction in ['inbound', 'trunking']:
                    assistant_info = phone_to_assistant.get(call.to)

                # Build comprehensive call log
                call_log = CallLogResponse(
                    id=call.sid,
                    **{"from": getattr(call, 'from_formatted', None) or from_number},
                    to=getattr(call, 'to_formatted', None) or call.to,
                    direction=call.direction,
                    status=call.status,
                    duration=int(call.duration) if call.duration else None,
                    start_time=call.start_time.isoformat() + "Z" if call.start_time else None,
                    end_time=call.end_time.isoformat() + "Z" if call.end_time else None,
                    date_created=call.date_created.isoformat() + "Z" if call.date_created else datetime.utcnow().isoformat() + "Z",
                    date_updated=call.date_updated.isoformat() + "Z" if call.date_updated else None,
                    answered_by=getattr(call, 'answered_by', None),
                    caller_name=getattr(call, 'caller_name', None),
                    forwarded_from=getattr(call, 'forwarded_from', None),
                    parent_call_sid=getattr(call, 'parent_call_sid', None),
                    price=call.price if call.price else None,
                    price_unit=getattr(call, 'price_unit', None) if call.price else None,
                    recording_url=None,  # Will fetch if needed
                    assistant_id=assistant_info["id"] if assistant_info else None,
                    assistant_name=assistant_info["name"] if assistant_info else None,
                    queue_time=getattr(call, 'queue_time', None)
                )

                call_logs.append(call_log)

            logger.info(f"Fetched {len(call_logs)} call logs for user {user_id}")

            return CallLogListResponse(
                call_logs=call_logs,
                total=len(call_logs)
            )

        except TwilioRestException as e:
            logger.error(f"Twilio API error fetching call logs: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error accessing Twilio: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error fetching call logs from Twilio: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching call logs: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_call_logs: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/assign-assistant", response_model=AssignAssistantResponse, status_code=status.HTTP_200_OK)
async def assign_assistant_to_phone_number(request: Request, assignment: AssignAssistantRequest):
    """
    Assign an AI assistant to a phone number and configure Twilio webhook

    Args:
        request: FastAPI request object
        assignment: Phone number ID and assistant ID

    Returns:
        AssignAssistantResponse: Updated phone number with assignment details

    Raises:
        HTTPException: If phone number or assistant not found
    """
    try:
        db = Database.get_db()
        phone_numbers_collection = db['phone_numbers']
        assistants_collection = db['assistants']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Assigning assistant {assignment.assistant_id} to phone number {assignment.phone_number_id}")

        # Validate phone_number_id
        try:
            phone_obj_id = ObjectId(assignment.phone_number_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone_number_id format"
            )

        # Validate assistant_id
        try:
            assistant_obj_id = ObjectId(assignment.assistant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assistant_id format"
            )

        # Fetch phone number
        phone_doc = phone_numbers_collection.find_one({"_id": phone_obj_id})
        if not phone_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not found"
            )

        # Fetch assistant
        assistant_doc = assistants_collection.find_one({"_id": assistant_obj_id})
        if not assistant_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI assistant not found"
            )

        # Verify both belong to same user
        if phone_doc["user_id"] != assistant_doc["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number and assistant belong to different users"
            )

        # Generate webhook URL
        # Use API_BASE_URL from settings if available (for production), otherwise use request URL
        if settings.api_base_url:
            base_url = settings.api_base_url
        else:
            base_url = f"{request.url.scheme}://{request.url.netloc}"

        webhook_url = f"{base_url}/api/inbound-calls/incoming-call/{assignment.assistant_id}"

        logger.info(f"Generated webhook URL: {webhook_url}")

        # Update phone number document
        update_doc = {
            "assigned_assistant_id": assistant_obj_id,
            "assigned_assistant_name": assistant_doc["name"],
            "webhook_url": webhook_url,
            "updated_at": datetime.utcnow()
        }

        phone_numbers_collection.update_one(
            {"_id": phone_obj_id},
            {"$set": update_doc}
        )

        webhook_configured = False

        # Configure Twilio webhook if it's a Twilio number
        if phone_doc["provider"].lower() == "twilio":
            try:
                # Get Twilio credentials
                twilio_connection = provider_connections_collection.find_one({
                    "user_id": phone_doc["user_id"],
                    "provider": "twilio"
                })

                if twilio_connection:
                    account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
                    if account_sid and auth_token:
                        client = Client(account_sid, auth_token)
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Stored Twilio credentials are missing or invalid. Please reconnect your provider."
                        )

                    # Update the phone number's voice webhook
                    incoming_phone_number = client.incoming_phone_numbers(phone_doc["provider_sid"]).update(
                        voice_url=webhook_url,
                        voice_method='POST'
                    )

                    webhook_configured = True
                    logger.info(f"Successfully configured Twilio webhook for {phone_doc['phone_number']}")
                else:
                    logger.warning("Twilio connection not found, webhook URL generated but not configured")

            except Exception as e:
                logger.error(f"Error configuring Twilio webhook: {str(e)}")
                # Don't fail the assignment if webhook config fails
                webhook_configured = False

        # Fetch updated phone number
        updated_phone = phone_numbers_collection.find_one({"_id": phone_obj_id})

        phone_response = PhoneNumberResponse(
            id=str(updated_phone["_id"]),
            phone_number=updated_phone["phone_number"],
            provider=updated_phone["provider"],
            friendly_name=updated_phone.get("friendly_name"),
            capabilities=PhoneNumberCapabilities(**updated_phone["capabilities"]),
            status=updated_phone.get("status", "active"),
            created_at=updated_phone["created_at"].isoformat() + "Z",
            assigned_assistant_id=str(updated_phone["assigned_assistant_id"]),
            assigned_assistant_name=updated_phone["assigned_assistant_name"],
            webhook_url=updated_phone["webhook_url"]
        )

        return AssignAssistantResponse(
            message="AI assistant assigned successfully" + (" and webhook configured" if webhook_configured else ""),
            phone_number=phone_response,
            webhook_configured=webhook_configured
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error assigning assistant to phone number: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning assistant: {str(e)}"
        )


@router.delete("/unassign-assistant/{phone_number_id}", response_model=PhoneNumberResponse, status_code=status.HTTP_200_OK)
async def unassign_assistant_from_phone_number(phone_number_id: str):
    """
    Remove AI assistant assignment from a phone number

    Args:
        phone_number_id: Phone number ID

    Returns:
        PhoneNumberResponse: Updated phone number without assignment

    Raises:
        HTTPException: If phone number not found
    """
    try:
        db = Database.get_db()
        phone_numbers_collection = db['phone_numbers']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Unassigning assistant from phone number {phone_number_id}")

        # Validate phone_number_id
        try:
            phone_obj_id = ObjectId(phone_number_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone_number_id format"
            )

        # Fetch phone number
        phone_doc = phone_numbers_collection.find_one({"_id": phone_obj_id})
        if not phone_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not found"
            )

        # Update phone number document - remove assignment
        update_doc = {
            "updated_at": datetime.utcnow()
        }

        phone_numbers_collection.update_one(
            {"_id": phone_obj_id},
            {
                "$set": update_doc,
                "$unset": {
                    "assigned_assistant_id": "",
                    "assigned_assistant_name": "",
                    "webhook_url": ""
                }
            }
        )

        # Remove Twilio webhook if it's a Twilio number
        if phone_doc["provider"].lower() == "twilio":
            try:
                twilio_connection = provider_connections_collection.find_one({
                    "user_id": phone_doc["user_id"],
                    "provider": "twilio"
                })

                if twilio_connection:
                    account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
                    if account_sid and auth_token:
                        client = Client(account_sid, auth_token)
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Stored Twilio credentials are missing or invalid. Please reconnect your provider."
                        )

                    # Clear the voice webhook
                    incoming_phone_number = client.incoming_phone_numbers(phone_doc["provider_sid"]).update(
                        voice_url='',
                        voice_method='POST'
                    )

                    logger.info(f"Successfully removed Twilio webhook for {phone_doc['phone_number']}")

            except Exception as e:
                logger.error(f"Error removing Twilio webhook: {str(e)}")

        # Fetch updated phone number
        updated_phone = phone_numbers_collection.find_one({"_id": phone_obj_id})

        phone_response = PhoneNumberResponse(
            id=str(updated_phone["_id"]),
            phone_number=updated_phone["phone_number"],
            provider=updated_phone["provider"],
            friendly_name=updated_phone.get("friendly_name"),
            capabilities=PhoneNumberCapabilities(**updated_phone["capabilities"]),
            status=updated_phone.get("status", "active"),
            created_at=updated_phone["created_at"].isoformat() + "Z",
            assigned_assistant_id=None,
            assigned_assistant_name=None,
            webhook_url=None
        )

        return phone_response

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error unassigning assistant from phone number: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unassigning assistant: {str(e)}"
        )
