"""
Twilio Management Routes - Scalable phone number operations
Handles number purchase, webhook configuration, and TwiML App management
without requiring manual Twilio Console work.
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import logging

from app.config.database import Database
from app.config.settings import settings
from app.services.twilio_service import TwilioService
from app.utils.twilio_helpers import decrypt_twilio_credentials
from app.models.phone_number import PhoneNumberResponse, PhoneNumberCapabilities

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class PurchaseNumberRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    phone_number: str = Field(..., description="E.164 format phone number to purchase")
    friendly_name: Optional[str] = Field(None, description="Friendly name for the number")
    use_twiml_app: bool = Field(True, description="Attach to TwiML App (recommended)")
    assistant_id: Optional[str] = Field(None, description="Optionally assign to assistant immediately")


class PurchaseNumberResponse(BaseModel):
    message: str
    phone_number: PhoneNumberResponse
    twiml_app_sid: Optional[str] = None
    webhook_configured: bool


class SearchNumbersRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    country_code: str = Field("US", description="Country code (US, CA, GB, etc.)")
    area_code: Optional[str] = Field(None, description="Filter by area code")
    contains: Optional[str] = Field(None, description="Filter by digits in number")
    limit: int = Field(20, description="Max results")


class AvailableNumber(BaseModel):
    phone_number: str
    friendly_name: Optional[str]
    locality: Optional[str]
    region: Optional[str]
    capabilities: PhoneNumberCapabilities


class SearchNumbersResponse(BaseModel):
    message: str
    available_numbers: List[AvailableNumber]
    total: int


class BatchWebhookConfigRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    use_twiml_app: bool = Field(True, description="Attach all numbers to TwiML App")


class BatchWebhookConfigResponse(BaseModel):
    message: str
    numbers_updated: int
    twiml_app_sid: Optional[str] = None


class TwiMLAppInfo(BaseModel):
    sid: str
    friendly_name: str
    voice_url: Optional[str]
    sms_url: Optional[str]
    status_callback: Optional[str]


class TwiMLAppResponse(BaseModel):
    message: str
    app: TwiMLAppInfo


class VerifiedCallerID(BaseModel):
    sid: str
    phone_number: str
    friendly_name: Optional[str]


class VerifiedCallerIDsResponse(BaseModel):
    message: str
    verified_caller_ids: List[VerifiedCallerID]
    total: int


# ==================== Endpoints ====================

@router.post("/search-numbers", response_model=SearchNumbersResponse, status_code=status.HTTP_200_OK)
async def search_available_numbers(request: SearchNumbersRequest):
    """
    Search for available phone numbers to purchase.

    Args:
        request: Search parameters (country, area code, etc.)

    Returns:
        SearchNumbersResponse: List of available numbers
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']

        # Validate user
        try:
            user_obj_id = ObjectId(request.user_id)
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

        # Get Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found. Please connect Twilio first."
            )

        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        # Initialize Twilio service
        twilio_service = TwilioService(account_sid, auth_token)

        # Search for available numbers
        available = await twilio_service.list_available_numbers(
            country_code=request.country_code,
            area_code=request.area_code,
            contains=request.contains,
            limit=request.limit
        )

        available_numbers = [
            AvailableNumber(
                phone_number=num['phone_number'],
                friendly_name=num.get('friendly_name'),
                locality=num.get('locality'),
                region=num.get('region'),
                capabilities=PhoneNumberCapabilities(**num['capabilities'])
            )
            for num in available
        ]

        return SearchNumbersResponse(
            message=f"Found {len(available_numbers)} available numbers",
            available_numbers=available_numbers,
            total=len(available_numbers)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching numbers: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching numbers: {str(e)}"
        )


@router.post("/purchase-number", response_model=PurchaseNumberResponse, status_code=status.HTTP_201_CREATED)
async def purchase_phone_number(request: Request, purchase_request: PurchaseNumberRequest):
    """
    Purchase a phone number with automatic webhook configuration.
    No manual Console work required!

    Args:
        request: FastAPI request object
        purchase_request: Purchase details

    Returns:
        PurchaseNumberResponse: Purchased number details
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        phone_numbers_collection = db['phone_numbers']
        provider_connections_collection = db['provider_connections']
        assistants_collection = db['assistants']

        logger.info(f"Purchasing number {purchase_request.phone_number} for user {purchase_request.user_id}")

        # Validate user
        try:
            user_obj_id = ObjectId(purchase_request.user_id)
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

        # Get Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found. Please connect Twilio first."
            )

        # Initialize Twilio service
        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        twilio_service = TwilioService(account_sid, auth_token)

        # Determine base URL for webhooks
        if settings.api_base_url:
            base_url = settings.api_base_url
        else:
            base_url = f"{request.url.scheme}://{request.url.netloc}"

        twiml_app_sid = None
        webhook_configured = False

        # Option 1: Use TwiML App (recommended)
        if purchase_request.use_twiml_app:
            # Dynamic routing URL - routes based on To number
            voice_url = f"{base_url}/api/twilio-webhooks/voice"
            status_callback = f"{base_url}/api/twilio-webhooks/voice-status"

            # Ensure TwiML App exists
            twiml_app_sid = await twilio_service.ensure_twiml_app(
                friendly_name="Convis Voice Router",
                voice_url=voice_url,
                status_callback=status_callback
            )

            # Purchase number and attach to TwiML App
            number_details = await twilio_service.buy_number(
                phone_number=purchase_request.phone_number,
                voice_application_sid=twiml_app_sid,
                friendly_name=purchase_request.friendly_name or purchase_request.phone_number
            )

            webhook_configured = True

        # Option 2: Direct webhook URLs (if assistant assigned immediately)
        else:
            if purchase_request.assistant_id:
                voice_url = f"{base_url}/api/inbound-calls/incoming-call/{purchase_request.assistant_id}"

                number_details = await twilio_service.buy_number(
                    phone_number=purchase_request.phone_number,
                    voice_url=voice_url,
                    friendly_name=purchase_request.friendly_name or purchase_request.phone_number
                )
                webhook_configured = True
            else:
                # No webhook yet - will configure when assistant is assigned
                number_details = await twilio_service.buy_number(
                    phone_number=purchase_request.phone_number,
                    friendly_name=purchase_request.friendly_name or purchase_request.phone_number
                )

        # Store in database
        now = datetime.utcnow()
        phone_doc = {
            "user_id": user_obj_id,
            "phone_number": number_details['phone_number'],
            "provider": "twilio",
            "provider_sid": number_details['sid'],
            "friendly_name": number_details.get('friendly_name') or purchase_request.phone_number,
            "capabilities": number_details['capabilities'],
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "twiml_app_sid": twiml_app_sid
        }

        # If assistant assigned immediately, add that info
        if purchase_request.assistant_id:
            try:
                assistant_obj_id = ObjectId(purchase_request.assistant_id)
                assistant = assistants_collection.find_one({"_id": assistant_obj_id})

                if assistant and assistant["user_id"] == user_obj_id:
                    phone_doc["assigned_assistant_id"] = assistant_obj_id
                    phone_doc["assigned_assistant_name"] = assistant["name"]
                    phone_doc["webhook_url"] = f"{base_url}/api/inbound-calls/incoming-call/{purchase_request.assistant_id}"
            except Exception as e:
                logger.warning(f"Could not assign assistant: {e}")

        result = phone_numbers_collection.insert_one(phone_doc)
        phone_doc["_id"] = result.inserted_id

        # Build response
        phone_response = PhoneNumberResponse(
            id=str(phone_doc["_id"]),
            phone_number=phone_doc["phone_number"],
            provider="twilio",
            friendly_name=phone_doc["friendly_name"],
            capabilities=PhoneNumberCapabilities(**phone_doc["capabilities"]),
            status="active",
            created_at=now.isoformat() + "Z",
            assigned_assistant_id=str(phone_doc["assigned_assistant_id"]) if phone_doc.get("assigned_assistant_id") else None,
            assigned_assistant_name=phone_doc.get("assigned_assistant_name"),
            webhook_url=phone_doc.get("webhook_url")
        )

        logger.info(f"Successfully purchased and configured {number_details['phone_number']}")

        return PurchaseNumberResponse(
            message=f"Successfully purchased {number_details['phone_number']}" +
                    (" and configured webhook" if webhook_configured else ""),
            phone_number=phone_response,
            twiml_app_sid=twiml_app_sid,
            webhook_configured=webhook_configured
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing number: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error purchasing number: {str(e)}"
        )


@router.post("/batch-configure-webhooks", response_model=BatchWebhookConfigResponse, status_code=status.HTTP_200_OK)
async def batch_configure_webhooks(request: Request, batch_request: BatchWebhookConfigRequest):
    """
    Batch operation: Configure webhooks for all existing numbers.
    Use this for one-time migration from manual Twilio Console setup.

    Args:
        request: FastAPI request object
        batch_request: Configuration options

    Returns:
        BatchWebhookConfigResponse: Number of numbers updated
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        phone_numbers_collection = db['phone_numbers']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Batch configuring webhooks for user {batch_request.user_id}")

        # Validate user
        try:
            user_obj_id = ObjectId(batch_request.user_id)
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

        # Get Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found. Please connect Twilio first."
            )

        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        # Initialize Twilio service
        twilio_service = TwilioService(account_sid, auth_token)

        twiml_app_sid = None

        if batch_request.use_twiml_app:
            # Determine base URL
            if settings.api_base_url:
                base_url = settings.api_base_url
            else:
                base_url = f"{request.url.scheme}://{request.url.netloc}"

            voice_url = f"{base_url}/api/twilio-webhooks/voice"
            status_callback = f"{base_url}/api/twilio-webhooks/voice-status"

            # Ensure TwiML App exists
            twiml_app_sid = await twilio_service.ensure_twiml_app(
                friendly_name="Convis Voice Router",
                voice_url=voice_url,
                status_callback=status_callback
            )

            # Attach all numbers to the app
            count = await twilio_service.attach_all_numbers_to_app(twiml_app_sid)

            # Update database records
            phone_numbers_collection.update_many(
                {"user_id": user_obj_id, "provider": "twilio"},
                {"$set": {
                    "twiml_app_sid": twiml_app_sid,
                    "updated_at": datetime.utcnow()
                }}
            )

            return BatchWebhookConfigResponse(
                message=f"Successfully attached {count} numbers to TwiML App",
                numbers_updated=count,
                twiml_app_sid=twiml_app_sid
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch configuration requires use_twiml_app=true"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch webhook configuration: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch configuration: {str(e)}"
        )


@router.get("/twiml-app/{user_id}", response_model=TwiMLAppResponse, status_code=status.HTTP_200_OK)
async def get_twiml_app_info(user_id: str):
    """
    Get TwiML App information for a user.

    Args:
        user_id: User ID

    Returns:
        TwiMLAppResponse: TwiML App details
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']

        # Validate user
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

        # Get Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found"
            )

        # Initialize Twilio service
        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        twilio_service = TwilioService(account_sid, auth_token)

        # Get or create TwiML App
        app_sid = await twilio_service.ensure_twiml_app(friendly_name="Convis Voice Router")

        # Fetch app details
        app = twilio_service.client.applications(app_sid).fetch()

        return TwiMLAppResponse(
            message="TwiML App retrieved successfully",
            app=TwiMLAppInfo(
                sid=app.sid,
                friendly_name=app.friendly_name,
                voice_url=app.voice_url,
                sms_url=app.sms_url,
                status_callback=app.status_callback
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching TwiML App: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching TwiML App: {str(e)}"
        )


@router.get("/verified-caller-ids/{user_id}", response_model=VerifiedCallerIDsResponse, status_code=status.HTTP_200_OK)
async def get_verified_caller_ids(user_id: str):
    """
    Get verified caller IDs for outbound calls.
    Required for Twilio trial accounts - outbound calls can only be made to verified numbers.

    Args:
        user_id: User ID

    Returns:
        VerifiedCallerIDsResponse: List of verified caller IDs
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Fetching verified caller IDs for user {user_id}")

        # Validate user
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

        # Get Twilio connection
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found. Please connect Twilio first."
            )

        # Initialize Twilio service
        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        twilio_service = TwilioService(account_sid, auth_token)

        # Fetch verified caller IDs from Twilio
        verified_callers = twilio_service.client.outgoing_caller_ids.list()

        caller_ids = [
            VerifiedCallerID(
                sid=caller.sid,
                phone_number=caller.phone_number,
                friendly_name=caller.friendly_name
            )
            for caller in verified_callers
        ]

        logger.info(f"Found {len(caller_ids)} verified caller IDs for user {user_id}")

        return VerifiedCallerIDsResponse(
            message=f"Found {len(caller_ids)} verified caller ID(s)",
            verified_caller_ids=caller_ids,
            total=len(caller_ids)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching verified caller IDs: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching verified caller IDs: {str(e)}"
        )
