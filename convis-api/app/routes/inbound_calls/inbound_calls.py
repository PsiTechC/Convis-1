import os
import json
import asyncio
import websockets
from datetime import datetime
from fastapi import APIRouter, WebSocket, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
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
from app.models.inbound_calls import InboundCallConfig, InboundCallResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration for interruption handling
SHOW_TIMING_MATH = False

@router.get("/", response_class=JSONResponse)
async def inbound_calls_index():
    """Health check for inbound calls service"""
    return {"message": "Inbound calls service is running"}

@router.get("/config/{assistant_id}", response_model=InboundCallResponse, status_code=status.HTTP_200_OK)
async def get_inbound_call_config(assistant_id: str):
    """
    Get AI assistant configuration for inbound calls

    Args:
        assistant_id: The AI assistant ID to fetch configuration for

    Returns:
        InboundCallResponse: Configuration details

    Raises:
        HTTPException: If assistant not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']

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

        config = InboundCallConfig(
            assistant_id=str(assistant['_id']),
            system_message=assistant['system_message'],
            voice=assistant['voice'],
            temperature=assistant['temperature']
        )

        return InboundCallResponse(
            message="Configuration retrieved successfully",
            config=config
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

@router.api_route("/incoming-call/{assistant_id}", methods=["GET", "POST"])
async def handle_incoming_call(assistant_id: str, request: Request):
    """
    Handle incoming call and return TwiML response to connect to Media Stream.
    Fetches configuration from MongoDB based on assistant_id.

    Args:
        assistant_id: The AI assistant ID to use for this call
        request: FastAPI request object

    Returns:
        HTMLResponse: TwiML XML response

    Raises:
        HTTPException: If assistant not found or error occurs
    """
    try:
        db = Database.get_db()
        assistants_collection = db['assistants']

        logger.info(f"Incoming call for assistant: {assistant_id}")

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

        # Create TwiML response with initial greeting
        # Note: User requested to keep these greeting messages
        response = VoiceResponse()
        response.say("Please wait while we connect your call to the AI voice assistant.")
        response.pause(length=1)
        response.say("You can start talking in a moment.")
        response.pause(length=1)

        # Use API_BASE_URL from settings if available
        if settings.api_base_url:
            # Extract hostname from API_BASE_URL (remove http:// or https://)
            host = settings.api_base_url.replace('https://', '').replace('http://', '')
        else:
            host = request.url.hostname

        logger.info(f"WebSocket URL: wss://{host}/api/inbound-calls/media-stream/{assistant_id}")

        connect = Connect()
        connect.stream(url=f'wss://{host}/api/inbound-calls/media-stream/{assistant_id}')
        response.append(connect)

        # Enable call recording
        # Record both inbound and outbound audio, transcribe the call
        response.record(
            recording_status_callback=f'{settings.api_base_url or f"https://{host}"}/api/inbound-calls/recording-status',
            recording_status_callback_method='POST',
            transcribe=True,
            transcribe_callback=f'{settings.api_base_url or f"https://{host}"}/api/inbound-calls/transcription-status',
            max_length=3600,  # Max 1 hour
            timeout=5,
            play_beep=False
        )

        return HTMLResponse(content=str(response), media_type="application/xml")

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        logger.error(f"Error handling incoming call: {str(error)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle incoming call: {str(error)}"
        )

@router.websocket("/media-stream/{assistant_id}")
async def handle_media_stream(websocket: WebSocket, assistant_id: str):
    """
    Handle WebSocket connections between Twilio and OpenAI.
    Fetches configuration from MongoDB based on assistant_id.

    Args:
        websocket: WebSocket connection
        assistant_id: The AI assistant ID to use for this call
    """
    logger.info(f"Client connected for assistant: {assistant_id}")
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

        # OpenAI Realtime API requires temperature >= 0.6
        if temperature < 0.6:
            logger.warning(f"Temperature {temperature} is below OpenAI minimum. Adjusting to 0.6")
            temperature = 0.6

        # Retrieve the assistant's OpenAI API key
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
            # This matches the original pattern from CallTack_IN_out/inbound_calls.py line 223
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
                            logger.info("Hangup already completed; stopping Twilio receive loop")
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
                            logger.info(f"Incoming stream has started {stream_sid}")
                            response_start_timestamp_twilio = None
                            latest_media_timestamp = 0
                            last_assistant_item = None
                        elif data['event'] == 'mark':
                            if mark_queue:
                                mark_queue.pop(0)
                except WebSocketDisconnect:
                    logger.info("Client disconnected.")
                    if openai_ws.state.name == 'OPEN':
                        await openai_ws.close()

            async def send_to_twilio():
                """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
                nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
                nonlocal awaiting_hangup_confirmation, pending_hangup_goodbye, hangup_completed

                async def finalize_call():
                    nonlocal hangup_completed, pending_hangup_goodbye
                    if hangup_completed:
                        return
                    hangup_completed = True
                    pending_hangup_goodbye = False
                    if twilio_client and call_sid:
                        try:
                            twilio_client.calls(call_sid).update(status="completed")
                            logger.info(f"Requested Twilio to end call {call_sid}")
                        except TwilioRestException as twilio_error:
                            logger.error(f"Twilio error ending call {call_sid}: {twilio_error}")
                        except Exception as generic_error:
                            logger.error(f"Unexpected error ending call {call_sid}: {generic_error}")
                    else:
                        logger.warning("Cannot end call automatically - Twilio client or call SID missing")

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
                                    logger.info("Final goodbye response delivered; ending call now")
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
                            logger.info(f"AI transcript: {response.get('delta', '')}")

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
                                    # Check for input_audio with transcript (new API format)
                                    if content.get('type') == 'input_audio':
                                        transcript = content.get('transcript', '')
                                        if transcript:
                                            logger.info(f"User said: {transcript}")
                                            hangup_handled = False
                                            if not hangup_completed:
                                                if awaiting_hangup_confirmation:
                                                    if transcript_confirms_hangup(transcript) or transcript_has_hangup_intent(transcript):
                                                        logger.info("Caller confirmed hangup request.")
                                                        awaiting_hangup_confirmation = False
                                                        pending_hangup_goodbye = True
                                                        await send_call_end_acknowledgement(openai_ws)
                                                        hangup_handled = True
                                                    elif transcript_denies_hangup(transcript):
                                                        logger.info("Caller declined hangup; continuing conversation.")
                                                        awaiting_hangup_confirmation = False
                                                        await send_call_continue_acknowledgement(openai_ws)
                                                        hangup_handled = True
                                                elif transcript_has_hangup_intent(transcript):
                                                    logger.info("Detected caller intent to end call; requesting confirmation.")
                                                    awaiting_hangup_confirmation = True
                                                    await request_call_end_confirmation(openai_ws)
                                                    hangup_handled = True

                                            if hangup_handled or pending_hangup_goodbye:
                                                continue

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
        logger.info(f"Client disconnected normally for assistant: {assistant_id}")
    except Exception as error:
        import traceback
        logger.error(f"Error in media stream for assistant {assistant_id}: {str(error)}")
        logger.error(traceback.format_exc())
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass  # WebSocket might already be closed
    finally:
        # Ensure cleanup happens
        logger.info(f"Cleaning up resources for assistant: {assistant_id}")
        # WebSocket and OpenAI connections will be closed by context managers


@router.api_route("/recording-status", methods=["GET", "POST"])
async def handle_recording_status(request: Request):
    """
    Callback endpoint for Twilio recording status updates.
    Saves recording URL to database when recording is completed.

    Twilio sends these parameters:
    - RecordingSid: Unique recording identifier
    - RecordingUrl: URL to download the recording
    - RecordingStatus: completed, in-progress, absent
    - RecordingDuration: Length of recording in seconds
    - CallSid: Call identifier
    - AccountSid: Twilio account SID
    """
    try:
        # Get form data from Twilio
        if request.method == "POST":
            form_data = await request.form()
        else:
            form_data = request.query_params

        recording_sid = form_data.get('RecordingSid')
        recording_url = form_data.get('RecordingUrl')
        recording_status = form_data.get('RecordingStatus')
        recording_duration = form_data.get('RecordingDuration')
        call_sid = form_data.get('CallSid')

        logger.info(f"Recording status: {recording_status} for call {call_sid}")
        logger.info(f"Recording URL: {recording_url}")

        if recording_status == 'completed' and call_sid:
            # Update call log with recording information
            db = Database.get_db()
            call_logs_collection = db['call_logs']

            update_data = {
                'recording_sid': recording_sid,
                'recording_url': recording_url,
                'recording_duration': int(recording_duration) if recording_duration else None,
                'recording_status': recording_status,
                'updated_at': datetime.utcnow()
            }

            result = call_logs_collection.update_one(
                {'call_sid': call_sid},
                {'$set': update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Updated call log with recording URL for call {call_sid}")
            else:
                logger.warning(f"Call log not found for call_sid: {call_sid}")

        return {"status": "success", "message": "Recording status received"}

    except Exception as error:
        logger.error(f"Error handling recording status: {str(error)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(error)}


@router.api_route("/transcription-status", methods=["GET", "POST"])
async def handle_transcription_status(request: Request):
    """
    Callback endpoint for Twilio transcription status updates.
    Saves transcription text to database when transcription is completed.

    Twilio sends these parameters:
    - TranscriptionSid: Unique transcription identifier
    - TranscriptionText: The full transcription
    - TranscriptionStatus: completed, in-progress, failed
    - RecordingSid: Associated recording SID
    - CallSid: Call identifier
    - TranscriptionUrl: URL to fetch transcription
    """
    try:
        # Get form data from Twilio
        if request.method == "POST":
            form_data = await request.form()
        else:
            form_data = request.query_params

        transcription_sid = form_data.get('TranscriptionSid')
        transcription_text = form_data.get('TranscriptionText')
        transcription_status = form_data.get('TranscriptionStatus')
        recording_sid = form_data.get('RecordingSid')
        call_sid = form_data.get('CallSid')
        transcription_url = form_data.get('TranscriptionUrl')

        logger.info(f"Transcription status: {transcription_status} for call {call_sid}")

        if transcription_status == 'completed' and call_sid and transcription_text:
            # Update call log with transcription
            db = Database.get_db()
            call_logs_collection = db['call_logs']

            update_data = {
                'transcription_sid': transcription_sid,
                'transcription_text': transcription_text,
                'transcription_url': transcription_url,
                'transcription_status': transcription_status,
                'updated_at': datetime.utcnow()
            }

            result = call_logs_collection.update_one(
                {'call_sid': call_sid},
                {'$set': update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Updated call log with transcription for call {call_sid}")
                logger.info(f"Transcription preview: {transcription_text[:100]}...")
            else:
                logger.warning(f"Call log not found for call_sid: {call_sid}")

        return {"status": "success", "message": "Transcription status received"}

    except Exception as error:
        logger.error(f"Error handling transcription status: {str(error)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(error)}
