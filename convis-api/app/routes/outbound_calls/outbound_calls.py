import os
import json
import asyncio
import re
import websockets
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, WebSocket, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from bson import ObjectId
from app.config.database import Database
from app.config.settings import settings
from app.utils.assistant_keys import resolve_assistant_api_key
from app.utils.twilio_helpers import decrypt_twilio_credentials
from app.utils import conversational_rag
from app.utils.openai_session import (
    send_session_update,
    send_mark,
    handle_interruption,
    inject_knowledge_base_context,
    LOG_EVENT_TYPES,
    transcript_has_hangup_intent,
    transcript_confirms_hangup,
    transcript_denies_hangup,
    request_call_end_confirmation,
    send_call_end_acknowledgement,
    send_call_continue_acknowledgement,
)
from app.services.calendar_service import CalendarService
from app.services.calendar_intent_service import CalendarIntentService
from app.models.outbound_calls import (
    OutboundCallRequest,
    OutboundCallResponse,
    CheckNumberResponse,
    OutboundCallConfig
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Note: Twilio credentials are now fetched per-user from the database
# This ensures proper security and multi-tenancy support

# Configuration for interruption handling
SHOW_TIMING_MATH = False

@router.get("/", response_class=JSONResponse)
async def outbound_calls_index():
    """Health check for outbound calls service"""
    return {
        "message": "Outbound calls service is running",
        "note": "Twilio credentials are fetched per-user from database"
    }

@router.get("/config/{assistant_id}", response_model=OutboundCallResponse, status_code=status.HTTP_200_OK)
async def get_outbound_call_config(assistant_id: str):
    """
    Get AI assistant configuration for outbound calls

    Args:
        assistant_id: The AI assistant ID to fetch configuration for

    Returns:
        OutboundCallResponse: Configuration details

    Raises:
        HTTPException: If assistant not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']
        campaigns_collection = db['campaigns']

        logger.info(f"Fetching configuration for assistant: {assistant_id}")

        # Convert to ObjectId
        try:
            assistant_obj_id = ObjectId(assistant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assistant_id format"
            )

        # Fetch assistant configuration
        assistant = assistants_collection.find_one({"_id": assistant_obj_id})

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI assistant not found"
            )

        return OutboundCallResponse(
            message="Configuration retrieved successfully",
            assistant_id=str(assistant['_id']),
            status="ready"
        )

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error fetching assistant configuration: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch assistant configuration: {str(error)}"
        )

@router.get("/call-status/{call_sid}/{user_id}", status_code=status.HTTP_200_OK)
async def get_call_status(call_sid: str, user_id: str):
    """
    Get the current status of an active call from Twilio.

    Args:
        call_sid: Twilio Call SID
        user_id: User ID to fetch Twilio credentials

    Returns:
        Call status information (ringing, in-progress, completed, etc.)
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']
        call_logs_collection = db['call_logs']

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

        # Initialize Twilio client
        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        twilio_client = Client(account_sid, auth_token)

        # Fetch call status from Twilio
        call = twilio_client.calls(call_sid).fetch()

        # Update database with latest status
        call_logs_collection.update_one(
            {"call_sid": call_sid, "user_id": user_obj_id},
            {
                "$set": {
                    "status": call.status,
                    "duration": call.duration,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return {
            "call_sid": call.sid,
            "status": call.status,
            "direction": call.direction,
            "from": call.from_formatted,
            "to": call.to_formatted,
            "duration": call.duration,
            "start_time": call.start_time.isoformat() if call.start_time else None,
            "end_time": call.end_time.isoformat() if call.end_time else None
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error fetching call status: {str(error)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch call status: {str(error)}"
        )


@router.post("/hangup/{call_sid}/{user_id}", status_code=status.HTTP_200_OK)
async def hangup_call(call_sid: str, user_id: str):
    """
    Hang up an active call.

    Args:
        call_sid: Twilio Call SID
        user_id: User ID to fetch Twilio credentials

    Returns:
        Success message
    """
    try:
        db = Database.get_db()
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']
        call_logs_collection = db['call_logs']

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

        # Initialize Twilio client
        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        twilio_client = Client(account_sid, auth_token)

        # Hang up the call
        call = twilio_client.calls(call_sid).update(status='completed')

        # Update database
        call_logs_collection.update_one(
            {"call_sid": call_sid, "user_id": user_obj_id},
            {
                "$set": {
                    "status": "completed",
                    "updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"Call {call_sid} hung up successfully")

        return {
            "message": "Call ended successfully",
            "call_sid": call_sid,
            "status": call.status
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error hanging up call: {str(error)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to hang up call: {str(error)}"
        )


@router.post("/check-number/{user_id}", response_model=CheckNumberResponse, status_code=status.HTTP_200_OK)
async def check_phone_number(user_id: str, phone_number: str):
    """
    Check if a phone number is allowed to be called.

    Validates against:
    - Twilio verified outgoing caller IDs
    - Twilio incoming phone numbers (owned numbers)

    Args:
        user_id: User ID to fetch Twilio credentials
        phone_number: Phone number in E.164 format (e.g., +1234567890)

    Returns:
        CheckNumberResponse: Validation result
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
                detail="No Twilio connection found. Please connect Twilio first."
            )

        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        # Initialize Twilio client with user's credentials
        twilio_client = Client(account_sid, auth_token)

        # Check if number is allowed
        is_allowed = await check_number_allowed(twilio_client, phone_number)

        return CheckNumberResponse(
            phone_number=phone_number,
            is_allowed=is_allowed,
            message="Number is allowed" if is_allowed else "Number is not verified or owned"
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error checking phone number: {str(error)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check phone number: {str(error)}"
        )

@router.post("/make-call/{assistant_id}", response_model=OutboundCallResponse, status_code=status.HTTP_200_OK)
async def make_outbound_call(assistant_id: str, request: OutboundCallRequest):
    """
    Initiate an outbound call using the specified AI assistant.

    Args:
        assistant_id: The AI assistant ID to use for this call
        request: OutboundCallRequest with phone_number

    Returns:
        OutboundCallResponse: Call details including call_sid

    Raises:
        HTTPException: If validation fails or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']
        users_collection = db['users']
        provider_connections_collection = db['provider_connections']

        logger.info(f"Initiating outbound call for assistant: {assistant_id}")

        # Convert to ObjectId
        try:
            assistant_obj_id = ObjectId(assistant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid assistant_id format"
            )

        # Fetch assistant configuration
        assistant = assistants_collection.find_one({"_id": assistant_obj_id})

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI assistant not found"
            )

        # Get user_id from assistant
        user_obj_id = assistant.get('user_id')
        if not user_obj_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assistant is not associated with a user"
            )

        # Validate user exists
        user = users_collection.find_one({"_id": user_obj_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get Twilio connection for this user
        twilio_connection = provider_connections_collection.find_one({
            "user_id": user_obj_id,
            "provider": "twilio"
        })

        if not twilio_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Twilio connection found. Please connect Twilio in your account settings."
            )

        account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Twilio credentials are missing or invalid. Please reconnect Twilio."
            )

        # Initialize Twilio client with user's credentials
        twilio_client = Client(account_sid, auth_token)

        # Validate phone number format (basic E.164 check)
        phone_number = request.phone_number.strip()
        if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format. Use E.164 format (e.g., +1234567890)"
            )

        # Check if number is allowed to be called
        is_allowed = await check_number_allowed(twilio_client, phone_number)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"The number {phone_number} is not recognized as a valid outgoing number or caller ID. "
                    "Please verify the number in your Twilio console first."
                )
            )

        try:
            openai_api_key, _ = resolve_assistant_api_key(db, assistant, required_provider="openai")
        except HTTPException as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)

        # Get the phone number to call FROM (the one assigned to this assistant)
        phone_numbers_collection = db['phone_numbers']
        phone_number_doc = phone_numbers_collection.find_one({
            "assigned_assistant_id": assistant_obj_id,
            "user_id": user_obj_id,
            "status": "active"
        })

        if not phone_number_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No phone number assigned to this assistant"
            )

        phone_number_from = phone_number_doc["phone_number"]
        logger.info(f"Using assigned phone number: {phone_number_from}")

        # Ensure API_BASE_URL is configured
        if not settings.api_base_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API_BASE_URL not configured in .env file"
            )

        # Clean domain (remove protocols and trailing slashes)
        domain = re.sub(r'(^\w+:|^)\/\/|\/+$', '', settings.api_base_url)

        # Create TwiML to connect to media stream
        outbound_twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response>'
            f'<Connect>'
            f'<Stream url="wss://{domain}/api/outbound-calls/media-stream/{assistant_id}" />'
            f'</Connect>'
            f'</Response>'
        )

        logger.info(f"Calling {phone_number} from {phone_number_from}")
        logger.info(f"WebSocket URL: wss://{domain}/api/outbound-calls/media-stream/{assistant_id}")

        # Make the call
        call = twilio_client.calls.create(
            from_=phone_number_from,
            to=phone_number,
            twiml=outbound_twiml
        )

        logger.info(f"Call created with SID: {call.sid}")

        # Store call in database for tracking
        call_logs_collection = db['call_logs']
        call_log = {
            "user_id": user_obj_id,
            "assistant_id": assistant_obj_id,
            "assistant_name": assistant.get("name"),
            "phone_number": phone_number_doc["_id"],
            "phone_number_value": phone_number_from,
            "call_sid": call.sid,
            "direction": "outbound",
            "from_number": phone_number_from,
            "to_number": phone_number,
            "status": "initiated",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        call_logs_collection.insert_one(call_log)
        logger.info(f"Call log stored for SID: {call.sid}")

        return OutboundCallResponse(
            message="Outbound call initiated successfully",
            call_sid=call.sid,
            status="initiated",
            assistant_id=assistant_id
        )

    except HTTPException:
        raise
    except TwilioRestException as e:
        logger.error(f"Twilio error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Twilio error: {e.msg}"
        )
    except Exception as error:
        import traceback
        logger.error(f"Error making outbound call: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to make outbound call: {str(error)}"
        )

@router.websocket("/media-stream/{assistant_id}")
async def handle_media_stream(websocket: WebSocket, assistant_id: str):
    """
    Handle WebSocket connections between Twilio and OpenAI for outbound calls.
    This is the same as inbound but triggered by outbound call initiation.

    Args:
        websocket: WebSocket connection
        assistant_id: The AI assistant ID to use for this call
    """
    logger.info(f"Outbound call media stream connected for assistant: {assistant_id}")
    await websocket.accept()

    try:
        db = Database.get_db()
        assistants_collection = db['assistants']

        # Convert to ObjectId
        try:
            assistant_obj_id = ObjectId(assistant_id)
        except Exception as e:
            logger.error(f"Invalid assistant_id format: {e}")
            await websocket.close(code=1008, reason="Invalid assistant_id")
            return

        # Fetch assistant configuration
        assistant = assistants_collection.find_one({"_id": assistant_obj_id})

        if not assistant:
            logger.error(f"Assistant not found: {assistant_id}")
            await websocket.close(code=1008, reason="Assistant not found")
            return

        provider_connections_collection = db['provider_connections']
        twilio_client = None
        assistant_user_id = assistant.get('user_id')
        try:
            twilio_connection = None
            if assistant_user_id:
                twilio_connection = provider_connections_collection.find_one({
                    "user_id": assistant_user_id,
                    "provider": "twilio"
                })
            account_sid = None
            auth_token = None
            if twilio_connection:
                account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
            if not account_sid:
                account_sid = settings.twilio_account_sid
            if not auth_token:
                auth_token = settings.twilio_auth_token
            if account_sid and auth_token:
                twilio_client = Client(account_sid, auth_token)
            else:
                logger.warning(
                    "Twilio credentials not available for assistant %s; hangup control will be limited",
                    assistant_id
                )
        except Exception as cred_error:
            logger.error(f"Failed to initialize Twilio client for assistant {assistant_id}: {cred_error}")
            twilio_client = None

        system_message = assistant['system_message']
        voice = assistant['voice']
        temperature = assistant['temperature']
        call_greeting = assistant.get('call_greeting')
        timezone_hint = (
            assistant.get('timezone')
            or settings.default_timezone
            or "America/New_York"
        )

        calendar_enabled = False
        default_calendar_provider = "google"
        calendar_service: Optional[CalendarService] = None
        calendar_intent_service: Optional[CalendarIntentService] = None
        conversation_history: List[Dict[str, str]] = []
        scheduling_task: Optional[asyncio.Task] = None
        appointment_scheduled = False
        appointment_metadata: Dict[str, Any] = {}
        lead_id: Optional[str] = None
        campaign_id: Optional[str] = None

        campaign = None
        campaign_id_param = websocket.query_params.get("campaignId")
        lead_id_param = websocket.query_params.get("leadId")

        if lead_id_param:
            try:
                ObjectId(lead_id_param)
                lead_id = lead_id_param
            except Exception:
                logger.warning("Invalid leadId provided (%s); disabling realtime calendar scheduling", lead_id_param)
                lead_id = None

        if campaign_id_param:
            try:
                campaign_obj_id = ObjectId(campaign_id_param)
                campaign = campaigns_collection.find_one({"_id": campaign_obj_id})
                if campaign:
                    campaign_id = campaign_id_param
                    logger.info(f"Loaded campaign {campaign_id_param} for outbound media stream")
            except Exception as e:
                logger.error(f"Failed to load campaign {campaign_id_param}: {e}")

        if campaign and campaign.get("system_prompt_override"):
            override = campaign["system_prompt_override"]
            if override:
                system_message = f"{system_message}\n\n---\nCampaign Instructions:\n{override.strip()}"

        calendar_accounts_collection = db["calendar_accounts"]
        if campaign and campaign.get("calendar_enabled") and lead_id and campaign_id:
            calendar_enabled = True
            calendar_service = CalendarService()
            calendar_intent_service = CalendarIntentService()
            working_window = campaign.get("working_window") or {}
            timezone_hint = working_window.get("timezone", timezone_hint)

            calendar_account_id = campaign.get("calendar_account_id")
            account_doc = None
            if calendar_account_id:
                account_doc = calendar_accounts_collection.find_one({"_id": calendar_account_id})
            elif assistant_user_id:
                account_doc = calendar_accounts_collection.find_one({"user_id": assistant_user_id})
            if account_doc:
                default_calendar_provider = account_doc.get("provider", "google")

        # Add calendar scheduling instructions if calendar is enabled
        if calendar_enabled:
            calendar_instructions = """

---
Calendar Scheduling Instructions:
You can schedule meetings and appointments during this call. When the person requests to schedule a meeting or appointment:

1. Ask for the preferred date and time
2. Confirm the meeting title/purpose
3. Confirm the duration (default to 30 minutes if not specified)
4. Let them know you'll schedule it

Example conversation:
Person: "Can we schedule a follow-up meeting?"
You: "Of course! When would you like to schedule the meeting? What date and time works best for you?"
Person: "How about next Tuesday at 2 PM?"
You: "Perfect! I'll schedule a follow-up meeting for next Tuesday at 2 PM. It will be for 30 minutes. Is that correct?"
Person: "Yes, that works."
You: "Great! I've noted that down and the meeting will be added to your calendar."

IMPORTANT: Be natural and conversational. Don't mention "the system" or technical details. Simply confirm the appointment details with the person and let them know it will be scheduled."""
            system_message = f"{system_message}{calendar_instructions}"

        async def maybe_schedule_from_conversation(trigger: str = "") -> None:
            """Analyze recent conversation context and book a calendar event if appropriate."""
            nonlocal scheduling_task, appointment_scheduled, appointment_metadata, call_sid

            if (
                not calendar_enabled
                or calendar_intent_service is None
                or calendar_service is None
                or appointment_scheduled
                or not campaign_id
                or not lead_id
            ):
                return

            if scheduling_task and not scheduling_task.done():
                return

            if not conversation_history or not openai_api_key:
                return

            if not call_sid:
                logger.debug("Call SID unavailable; delaying calendar analysis")
                return

            async def _run_analysis() -> None:
                nonlocal appointment_scheduled, appointment_metadata
                try:
                    result = await calendar_intent_service.extract_from_conversation(
                        conversation_history,
                        openai_api_key,
                        timezone_hint,
                    )
                    if not result or not result.get("should_schedule"):
                        return

                    appointment = result.get("appointment") or {}
                    start_iso = appointment.get("start_iso")
                    end_iso = appointment.get("end_iso")
                    if not start_iso or not end_iso:
                        logger.debug(
                            "Appointment payload missing start/end. Payload: %s",
                            appointment,
                        )
                        return

                    appointment.setdefault("timezone", timezone_hint)
                    appointment.setdefault("notes", result.get("reason"))
                    provider = appointment.get("provider") or default_calendar_provider

                    event_id = await calendar_service.book_appointment(
                        lead_id=lead_id,
                        campaign_id=campaign_id,
                        appointment_data=appointment,
                        provider=provider,
                    )
                    if not event_id:
                        logger.warning("Calendar booking returned no event ID; check calendar configuration")
                        return

                    appointment_scheduled = True
                    appointment_metadata = {**appointment, "event_id": event_id, "provider": provider}

                    call_log_update: Dict[str, Any] = {
                        "appointment_booked": True,
                        "appointment_details": appointment_metadata,
                        "calendar_event_id": event_id,
                        "appointment_source": "realtime",
                        "updated_at": datetime.utcnow(),
                    }
                    if lead_id:
                        try:
                            call_log_update["lead_id"] = ObjectId(lead_id)
                        except Exception:
                            call_log_update["lead_id"] = lead_id
                    if campaign_id:
                        try:
                            call_log_update["campaign_id"] = ObjectId(campaign_id)
                        except Exception:
                            call_log_update["campaign_id"] = campaign_id

                    try:
                        db["call_logs"].update_one(
                            {"call_sid": call_sid},
                            {"$set": call_log_update},
                        )
                    except Exception as dberr:
                        logger.error(f"Failed to update call log with appointment details: {dberr}")

                    confirmation_text = result.get("confirmation_text") or (
                        f"The meeting '{appointment.get('title', 'Meeting')}' was scheduled for "
                        f"{appointment.get('start_iso')} {appointment.get('timezone')}."
                    )
                    system_prompt = (
                        "Calendar event scheduled successfully. "
                        "Politely confirm the booking details with the contact. "
                        f"Suggested response: {confirmation_text}"
                    )

                    await openai_ws.send(
                        json.dumps(
                            {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "system",
                                    "content": [{"type": "input_text", "text": system_prompt}],
                                },
                            }
                        )
                    )
                    await openai_ws.send(json.dumps({"type": "response.create"}))
                    logger.info(
                        "Realtime calendar event booked for call %s (event_id=%s)",
                        call_sid,
                        event_id,
                    )
                except Exception as exc:
                    logger.error(f"Calendar scheduling workflow failed: {exc}")

            scheduling_task = asyncio.create_task(_run_analysis())

            def _clear_task(_future: asyncio.Future) -> None:
                nonlocal scheduling_task
                scheduling_task = None

            scheduling_task.add_done_callback(_clear_task)

        # OpenAI Realtime API requires temperature >= 0.6
        if temperature < 0.6:
            logger.warning(f"Temperature {temperature} is below OpenAI minimum. Adjusting to 0.6")
            temperature = 0.6

        try:
            openai_api_key, _ = resolve_assistant_api_key(db, assistant, required_provider="openai")
        except HTTPException as exc:
            logger.error(f"Failed to resolve API key for assistant {assistant_id}: {exc.detail}")
            await websocket.close(code=1008, reason=exc.detail)
            return

        logger.info(f"Using configuration - Voice: {voice}, Temperature: {temperature}")

        # Connect to OpenAI WebSocket using the assistant's API key (exact URL from original)
        # Increased timeout to handle connection delays
        async with websockets.connect(
            f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview&temperature={temperature}",
            additional_headers={
                "Authorization": f"Bearer {openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            },
            open_timeout=30,  # Increased from default 10s to 30s
            close_timeout=10,
            ping_interval=20,
            ping_timeout=20
        ) as openai_ws:
            # Initialize session with interruption handling enabled
            # NOTE: send_session_update now calls send_initial_conversation_item internally
            # This matches the original pattern from CallTack_IN_out/outbound_call.py
            await send_session_update(
                openai_ws,
                system_message,
                voice,
                temperature,
                enable_interruptions=True,
                greeting_text=call_greeting,
            )

            # Connection specific state
            stream_sid = None
            latest_media_timestamp = 0
            last_assistant_item = None
            mark_queue = []
            response_start_timestamp_twilio = None
            call_sid = None
            awaiting_hangup_confirmation = False
            pending_hangup_goodbye = False
            hangup_completed = False

            async def receive_from_twilio():
                """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
                nonlocal stream_sid, latest_media_timestamp, call_sid, hangup_completed
                try:
                    async for message in websocket.iter_text():
                        if hangup_completed:
                            logger.info("Hangup already completed; stopping outbound receive loop")
                            break
                        data = json.loads(message)
                        if data['event'] == 'media' and openai_ws.state.name == 'OPEN':
                            latest_media_timestamp = int(data['media']['timestamp'])
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": data['media']['payload']
                            }
                            await openai_ws.send(json.dumps(audio_append))
                        elif data['event'] == 'start':
                            start_info = data['start']
                            stream_sid = start_info.get('streamSid')
                            call_sid = start_info.get('callSid') or start_info.get('call_sid') or call_sid
                            logger.info(f"Outbound stream has started {stream_sid}")
                            response_start_timestamp_twilio = None
                            latest_media_timestamp = 0
                            last_assistant_item = None
                        elif data['event'] == 'mark':
                            if mark_queue:
                                mark_queue.pop(0)
                except WebSocketDisconnect:
                    logger.info("Client disconnected from outbound call.")
                    if openai_ws.state.name == 'OPEN':
                        await openai_ws.close()

            async def send_to_twilio():
                """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
                nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
                nonlocal awaiting_hangup_confirmation, pending_hangup_goodbye, hangup_completed
                nonlocal conversation_history, appointment_scheduled, scheduling_task

                response_transcript_buffers: Dict[str, str] = {}

                async def finalize_call():
                    nonlocal hangup_completed, pending_hangup_goodbye
                    if hangup_completed:
                        return
                    hangup_completed = True
                    pending_hangup_goodbye = False
                    if twilio_client and call_sid:
                        try:
                            twilio_client.calls(call_sid).update(status="completed")
                            logger.info(f"Requested Twilio to end outbound call {call_sid}")
                        except TwilioRestException as twilio_error:
                            logger.error(f"Twilio error ending outbound call {call_sid}: {twilio_error}")
                        except Exception as generic_error:
                            logger.error(f"Unexpected error ending outbound call {call_sid}: {generic_error}")
                    else:
                        logger.warning("Cannot end outbound call automatically - missing Twilio client or call SID")

                    try:
                        if openai_ws.state.name == 'OPEN':
                            await openai_ws.close()
                    except Exception as close_err:
                        logger.debug(f"Error closing OpenAI websocket: {close_err}")

                    try:
                        await websocket.close(code=1000, reason="Call ended by assistant confirmation")
                    except Exception as ws_err:
                        logger.debug(f"Error closing Twilio websocket: {ws_err}")

                try:
                    async for openai_message in openai_ws:
                        response = json.loads(openai_message)

                        if response['type'] in LOG_EVENT_TYPES:
                            logger.info(f"Received event: {response['type']}")
                            # Log error details if it's an error
                            if response['type'] == 'error':
                                logger.error(f"OpenAI Error: {json.dumps(response, indent=2)}")
                            # Log response.done details for debugging
                            if response['type'] == 'response.done':
                                resp_data = response.get('response', {})
                                logger.info(f"Response done - Status: {resp_data.get('status')}, "
                                          f"Output items: {len(resp_data.get('output', []))}")

                                if pending_hangup_goodbye and resp_data.get('status') == 'completed':
                                    logger.info("Final goodbye response delivered on outbound call; ending now")
                                    await finalize_call()
                                    return

                        # Log ALL events for debugging audio issues
                        if response['type'] not in LOG_EVENT_TYPES:
                            logger.debug(f"Received event (not in LOG_EVENT_TYPES): {response['type']}")

                        # Handle response creation
                        if response.get('type') == 'response.created':
                            response_data = response.get('response', {})
                            logger.info(f"Response created: {response_data.get('id')}")
                            logger.info(f"Response modalities: {response_data.get('modalities', [])}")
                            logger.info(f"Response output: {list(response_data.get('output', []))[:2]}")  # First 2 items

                        # Handle audio delta (AI speaking)
                        if response.get('type') == 'response.audio.delta' and 'delta' in response:
                            audio_payload = response['delta']
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_payload
                                }
                            }
                            await websocket.send_json(audio_delta)

                            if response_start_timestamp_twilio is None:
                                response_start_timestamp_twilio = latest_media_timestamp
                                if SHOW_TIMING_MATH:
                                    logger.info(f"Setting start timestamp for new response: {response_start_timestamp_twilio}ms")

                            # Update last_assistant_item safely
                            if response.get('item_id'):
                                last_assistant_item = response['item_id']

                            await send_mark(websocket, stream_sid, mark_queue)

                        # Handle audio transcript for debugging
                        if response.get('type') == 'response.audio_transcript.delta':
                            delta_text = response.get('delta', '')
                            logger.info(f"AI transcript: {delta_text}")
                            resp_id = response.get('response_id')
                            if resp_id and delta_text:
                                response_transcript_buffers[resp_id] = (
                                    response_transcript_buffers.get(resp_id, "") + delta_text
                                )

                        if response.get('type') == 'response.audio_transcript.done':
                            resp_id = response.get('response_id')
                            transcript_text = ""
                            if resp_id and resp_id in response_transcript_buffers:
                                transcript_text = response_transcript_buffers.pop(resp_id)
                            transcript_text = transcript_text or response.get('transcript', '')
                            if transcript_text:
                                conversation_history.append({"role": "assistant", "text": transcript_text})
                                if len(conversation_history) > 30:
                                    conversation_history = conversation_history[-30:]
                                await maybe_schedule_from_conversation("assistant_transcript")

                        # Handle interruption when user starts speaking
                        if response.get('type') == 'input_audio_buffer.speech_started':
                            logger.info("Speech started detected - handling interruption")
                            if last_assistant_item:
                                logger.info(f"Interrupting response with id: {last_assistant_item}")
                                last_assistant_item, response_start_timestamp_twilio = await handle_interruption(
                                    openai_ws,
                                    websocket,
                                    stream_sid,
                                    last_assistant_item,
                                    response_start_timestamp_twilio,
                                    latest_media_timestamp,
                                    mark_queue,
                                    SHOW_TIMING_MATH
                                )

                        # When user's speech is transcribed, check knowledge base
                        if response['type'] == 'conversation.item.created':
                            item = response.get('item', {})
                            # Check if this is a user message with transcript
                            if item.get('role') == 'user' and item.get('type') == 'message':
                                content_list = item.get('content', [])
                                for content in content_list:
                                    if content.get('type') == 'input_audio':
                                        transcript = content.get('transcript', '')
                                        if transcript:
                                            logger.info(f"User said: {transcript}")
                                            hangup_handled = False
                                            if not hangup_completed:
                                                if awaiting_hangup_confirmation:
                                                    if transcript_confirms_hangup(transcript) or transcript_has_hangup_intent(transcript):
                                                        logger.info("Caller confirmed hangup on outbound call.")
                                                        awaiting_hangup_confirmation = False
                                                        pending_hangup_goodbye = True
                                                        await send_call_end_acknowledgement(openai_ws)
                                                        hangup_handled = True
                                                    elif transcript_denies_hangup(transcript):
                                                        logger.info("Caller declined hangup on outbound call; continuing.")
                                                        awaiting_hangup_confirmation = False
                                                        await send_call_continue_acknowledgement(openai_ws)
                                                        hangup_handled = True
                                                elif transcript_has_hangup_intent(transcript):
                                                    logger.info("Detected caller intent to end outbound call; requesting confirmation.")
                                                    awaiting_hangup_confirmation = True
                                                    await request_call_end_confirmation(openai_ws)
                                                    hangup_handled = True

                                            if hangup_handled or pending_hangup_goodbye:
                                                continue

                                            conversation_history.append({"role": "user", "text": transcript})
                                            if len(conversation_history) > 30:
                                                conversation_history = conversation_history[-30:]
                                            await maybe_schedule_from_conversation("user_transcript")

                                            # Search knowledge base
                                            try:
                                                kb_context = conversational_rag.search_conversation_context(
                                                    assistant_id=assistant_id,
                                                    query=transcript,
                                                    api_key=openai_api_key,
                                                    top_k=3,
                                                    relevance_threshold=0.7
                                                )
                                                if kb_context:
                                                    logger.info("Found relevant knowledge base context")
                                                    await inject_knowledge_base_context(openai_ws, kb_context)
                                            except Exception as e:
                                                logger.error(f"Error searching knowledge base: {e}")

                except Exception as e:
                    logger.error(f"Error in send_to_twilio: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            await asyncio.gather(receive_from_twilio(), send_to_twilio())

    except WebSocketDisconnect:
        logger.info(f"Client disconnected normally from outbound call for assistant: {assistant_id}")
    except Exception as error:
        import traceback
        logger.error(f"Error in outbound media stream for assistant {assistant_id}: {str(error)}")
        logger.error(traceback.format_exc())
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass  # WebSocket might already be closed
    finally:
        # Ensure cleanup happens
        logger.info(f"Cleaning up outbound call resources for assistant: {assistant_id}")
        # WebSocket and OpenAI connections will be closed by context managers

# Helper functions

async def check_number_allowed(twilio_client: Client, phone_number: str) -> bool:
    """
    Check if a number is allowed to be called.

    Checks against:
    - Twilio verified outgoing caller IDs
    - Twilio incoming phone numbers (owned by account)

    Args:
        twilio_client: Twilio client instance for the user
        phone_number: Phone number to check

    Returns:
        bool: True if allowed, False otherwise
    """
    try:
        # Check if it's one of our incoming phone numbers
        incoming_numbers = twilio_client.incoming_phone_numbers.list(phone_number=phone_number)
        if incoming_numbers:
            logger.info(f"{phone_number} is an owned incoming number")
            return True

        # Check if it's a verified outgoing caller ID
        outgoing_caller_ids = twilio_client.outgoing_caller_ids.list(phone_number=phone_number)
        if outgoing_caller_ids:
            logger.info(f"{phone_number} is a verified caller ID")
            return True

        logger.warning(f"{phone_number} is not verified or owned")
        return False
    except Exception as e:
        logger.error(f"Error checking phone number: {e}")
        return False

async def get_twilio_phone_number(twilio_client: Client) -> str:
    """
    Get the first available Twilio phone number from the account.

    Args:
        twilio_client: Twilio client instance for the user

    Returns:
        str: Phone number in E.164 format, or None if no numbers available
    """
    try:
        incoming_numbers = twilio_client.incoming_phone_numbers.list(limit=1)
        if incoming_numbers:
            phone_number = incoming_numbers[0].phone_number
            logger.info(f"Using Twilio phone number: {phone_number}")
            return phone_number

        logger.error("No Twilio phone numbers found in account")
        return None
    except Exception as e:
        logger.error(f"Error fetching Twilio phone number: {e}")
        return None
