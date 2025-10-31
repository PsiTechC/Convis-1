"""
FreJun (Teler) Integration Routes
Handles incoming calls, outbound calls, and webhooks for FreJun platform
"""

import logging
import json
import asyncio
import os
import websockets
import base64
import audioop  # Built-in module for Python < 3.13
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson import ObjectId

from app.config.database import Database
from app.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== Pydantic Models ====================

class CallFlowRequest(BaseModel):
    """Request model for FreJun call flow configuration"""
    call_id: str
    account_id: str
    from_number: str
    to_number: str

class CallStatusWebhook(BaseModel):
    """Webhook model for call status updates from FreJun"""
    call_id: str
    status: str
    duration: Optional[int] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None

class OutboundCallRequest(BaseModel):
    """Request model for initiating outbound calls via FreJun"""
    from_number: str
    to_number: str
    assistant_id: str
    user_id: str

# ==================== Helper Functions ====================

def get_assistant_config(assistant_id: str):
    """Fetch AI assistant configuration from database"""
    try:
        db = Database.get_db()
        assistants_collection = db['ai_assistants']

        if not ObjectId.is_valid(assistant_id):
            logger.error(f"Assistant ID {assistant_id} is not a valid ObjectId")
            return None

        assistant = assistants_collection.find_one({"_id": ObjectId(assistant_id)})

        if not assistant:
            logger.error(f"Assistant {assistant_id} not found")
            return None

        raw_user_id = assistant.get("user_id")
        if isinstance(raw_user_id, ObjectId):
            user_id = str(raw_user_id)
        elif isinstance(raw_user_id, str) and ObjectId.is_valid(raw_user_id):
            user_id = raw_user_id
        else:
            user_id = None

        return {
            "assistant_id": str(assistant["_id"]),
            "system_message": assistant.get("system_message", "You are a helpful AI assistant."),
            "voice": assistant.get("voice", "alloy"),
            "temperature": assistant.get("temperature", 0.8),
            "user_id": user_id,
            "greeting": assistant.get("greeting", "Hello! How can I help you today?"),
        }
    except Exception as e:
        logger.error(f"Error fetching assistant config: {e}")
        return None

def create_call_log(call_id: str, assistant_id: str, user_id: str, from_number: str, to_number: str, call_type: str = "inbound"):
    """Create a call log entry in the database"""
    try:
        db = Database.get_db()
        call_logs_collection = db['call_logs']

        assistant_obj_id = assistant_id
        if assistant_id and ObjectId.is_valid(assistant_id):
            assistant_obj_id = ObjectId(assistant_id)

        user_obj_id = None
        if user_id and ObjectId.is_valid(user_id):
            user_obj_id = ObjectId(user_id)

        call_log_entry = {
            "call_sid": call_id,  # Using FreJun call_id as call_sid for consistency
            "frejun_call_id": call_id,
            "assistant_id": assistant_obj_id,
            "user_id": user_obj_id,
            "from_number": from_number,
            "to_number": to_number,
            "call_type": call_type,
            "call_status": "initiated",
            "platform": "frejun",
            "started_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = call_logs_collection.insert_one(call_log_entry)
        logger.info(f"Created FreJun call log: {result.inserted_id} for call {call_id}")
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error creating call log: {e}")
        return None

def update_call_log(call_id: str, update_data: dict):
    """Update call log entry"""
    try:
        db = Database.get_db()
        call_logs_collection = db['call_logs']

        update_data["updated_at"] = datetime.utcnow()

        result = call_logs_collection.update_one(
            {"frejun_call_id": call_id},
            {"$set": update_data}
        )

        logger.info(f"Updated FreJun call log for call {call_id}: {result.modified_count} documents modified")
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating call log: {e}")
        return False

# ==================== Call Flow Configuration ====================

@router.post("/flow", status_code=200)
async def get_call_flow(payload: dict = Body(...)):
    """
    FreJun calls this endpoint to get the call flow configuration.
    This is called when an incoming call is received.

    The flow configuration tells FreJun:
    - Where to stream the audio (WebSocket URL)
    - Audio chunk size
    - Whether to record the call
    """
    logger.info(f"[FREJUN] Raw flow request payload: {payload}")

    # Extract fields from payload (flexible format)
    call_id = payload.get("call_id") or payload.get("callId") or payload.get("id")
    from_number = payload.get("from_number") or payload.get("from") or payload.get("fromNumber")
    to_number = payload.get("to_number") or payload.get("to") or payload.get("toNumber")

    logger.info(f"[FREJUN] Call flow requested - Call ID: {call_id}, From: {from_number}, To: {to_number}")

    try:
        # Look up which assistant is assigned to this phone number
        db = Database.get_db()
        phone_numbers_collection = db['phone_numbers']

        phone_doc = phone_numbers_collection.find_one({"phone_number": to_number})

        if not phone_doc:
            logger.warning(f"[FREJUN] Phone number {to_number} not found in database")
            return JSONResponse({
                "error": "Phone number not configured"
            }, status_code=404)

        assigned_assistant_id = phone_doc.get("assigned_assistant_id")

        if not assigned_assistant_id:
            logger.warning(f"[FREJUN] No assistant assigned to {to_number}")
            return JSONResponse({
                "error": "No assistant assigned to this number"
            }, status_code=404)

        assistant_id = str(assigned_assistant_id)

        if not ObjectId.is_valid(assistant_id):
            logger.warning(f"[FREJUN] Assistant ID {assistant_id} for {to_number} is invalid")
            return JSONResponse({
                "error": "Assistant configuration invalid"
            }, status_code=400)

        # Get assistant configuration
        assistant_config = get_assistant_config(assistant_id)

        if not assistant_config:
            logger.error(f"[FREJUN] Assistant {assistant_id} configuration not found")
            return JSONResponse({
                "error": "Assistant configuration not found"
            }, status_code=404)

        # Create call log
        create_call_log(
            call_id=call_id,
            assistant_id=assistant_id,
            user_id=assistant_config["user_id"],
            from_number=from_number,
            to_number=to_number,
            call_type="inbound"
        )

        # Get the server domain
        server_domain = (
            settings.api_base_url
            or settings.base_url
            or os.getenv("API_BASE_URL")
            or "https://api.convis.ai"
        )
        server_domain = server_domain.rstrip("/")
        ws_protocol = "wss" if server_domain.startswith("https") else "ws"
        ws_domain = server_domain.replace("https://", "").replace("http://", "")

        # Return call flow configuration with WebSocket streaming
        flow_config = {
            "type": "stream",
            "ws_url": f"{ws_protocol}://{ws_domain}/api/frejun/media-stream/{assistant_id}?call_id={call_id}",
            "chunk_size": 500,  # Audio chunk size in bytes
            "record": True  # Enable call recording
        }

        logger.info(f"[FREJUN] Returning flow config: {flow_config}")
        return JSONResponse(flow_config)

    except Exception as e:
        logger.error(f"[FREJUN] Error in call flow: {e}", exc_info=True)
        return JSONResponse({
            "error": "Internal server error"
        }, status_code=500)

# ==================== Call Status Webhook ====================

@router.post("/webhook", status_code=200)
async def call_status_webhook(data: dict = Body(...)):
    """
    FreJun sends call status updates to this endpoint.
    Status values: initiated, ringing, in-progress, completed, busy, failed, no-answer
    """
    logger.info(f"[FREJUN WEBHOOK] Call status update received: {data}")

    try:
        call_id = data.get("call_id")
        status = data.get("status")
        duration = data.get("duration")

        if not call_id or not status:
            logger.warning(f"[FREJUN WEBHOOK] Missing required fields in webhook data")
            return JSONResponse({"status": "error", "message": "Missing required fields"})

        # Update call log in database
        update_data = {
            "call_status": status,
        }

        if duration:
            update_data["duration"] = int(duration)

        if status in ["completed", "busy", "failed", "no-answer"]:
            update_data["ended_at"] = datetime.utcnow()

        update_call_log(call_id, update_data)

        logger.info(f"[FREJUN WEBHOOK] Updated call {call_id} with status {status}")

        return JSONResponse({"status": "received"})

    except Exception as e:
        logger.error(f"[FREJUN WEBHOOK] Error processing webhook: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)})

# ==================== WebSocket Media Streaming ====================

@router.websocket("/media-stream/{assistant_id}")
async def handle_media_stream(websocket: WebSocket, assistant_id: str):
    """
    WebSocket endpoint for bidirectional audio streaming between FreJun and OpenAI Realtime API.

    FreJun sends audio chunks as base64-encoded PCM audio (8kHz, 16-bit, mono).
    OpenAI expects PCM audio at 24kHz, 16-bit, mono.

    This handler:
    1. Accepts WebSocket connection from FreJun
    2. Connects to OpenAI Realtime API
    3. Bridges audio between the two platforms with format conversion
    """
    await websocket.accept()
    logger.info(f"[FREJUN WS] WebSocket connected for assistant {assistant_id}")

    # Extract call_id from query params
    call_id = websocket.query_params.get("call_id", "unknown")

    # Get assistant configuration
    assistant_config = get_assistant_config(assistant_id)

    if not assistant_config:
        logger.error(f"[FREJUN WS] Assistant {assistant_id} not found")
        await websocket.close(code=1008, reason="Assistant not found")
        return

    user_id = assistant_config.get("user_id")
    if not user_id or not ObjectId.is_valid(user_id):
        logger.error(f"[FREJUN WS] Assistant {assistant_id} is missing a valid user association")
        await websocket.close(code=1008, reason="Assistant owner not configured")
        return

    # Get OpenAI API key
    db = Database.get_db()
    users_collection = db['users']
    user = users_collection.find_one({"_id": ObjectId(user_id)})

    if not user:
        logger.error(f"[FREJUN WS] User not found for assistant {assistant_id}")
        await websocket.close(code=1008, reason="User not found")
        return

    # Get OpenAI API key
    openai_api_key = user.get("openai_key")
    if not openai_api_key:
        logger.error(f"[FREJUN WS] OpenAI API key not found for user")
        await websocket.close(code=1008, reason="OpenAI API key not configured")
        return

    voice = assistant_config.get("voice", "alloy")
    temperature = assistant_config.get("temperature", 0.8) or 0.8
    if temperature < 0.6:
        logger.warning(f"[FREJUN WS] Temperature {temperature} below minimum, adjusting to 0.6")
        temperature = 0.6
    greeting_text = assistant_config.get("greeting") or "Hello! How can I help you today?"

    # Update call log to in-progress
    update_call_log(call_id, {"call_status": "in-progress"})

    openai_ws = None

    try:
        # Connect to OpenAI Realtime API
        openai_url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

        logger.info(f"[FREJUN WS] Connecting to OpenAI Realtime API...")

        async with websockets.connect(
            openai_url,
            additional_headers={
                "Authorization": f"Bearer {openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            },
            open_timeout=30,
            close_timeout=10,
            ping_interval=20,
            ping_timeout=20
        ) as openai_ws:
            logger.info(f"[FREJUN WS] Connected to OpenAI Realtime API")

            # Configure OpenAI session
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": assistant_config["system_message"],
                    "voice": voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "temperature": temperature,
                }
            }

            await openai_ws.send(json.dumps(session_config))
            logger.info(f"[FREJUN WS] Sent session configuration to OpenAI")

            initial_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": greeting_text
                        }
                    ]
                }
            }
            await openai_ws.send(json.dumps(initial_message))
            await openai_ws.send(json.dumps({"type": "response.create"}))
            logger.info(f"[FREJUN WS] Sent initial greeting to OpenAI")

            resample_state_up = None
            resample_state_down = None
            user_audio_active = False

            # Stream handler: FreJun -> OpenAI
            async def frejun_to_openai():
                """Receive audio from FreJun and send to OpenAI"""
                nonlocal resample_state_up, user_audio_active
                try:
                    while True:
                        message = await websocket.receive_text()
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            logger.warning(f"[FREJUN WS] Received non-JSON payload from FreJun")
                            continue

                        if data.get("type") == "audio":
                            # FreJun sends 8kHz audio, OpenAI expects 24kHz
                            # Convert sample rate
                            # FreJun format: {"type": "audio", "data": {"audio_b64": "..."}}
                            data_obj = data.get("data", {})
                            audio_b64 = data_obj.get("audio_b64")

                            if audio_b64:
                                # Decode base64 audio
                                try:
                                    audio_bytes = base64.b64decode(audio_b64)
                                except Exception as decode_error:
                                    logger.warning(f"[FREJUN WS] Failed to decode audio chunk: {decode_error}")
                                    continue

                                # Resample from 8kHz to 24kHz (3x upsampling)
                                resampled_audio, resample_state_up = audioop.ratecv(
                                    audio_bytes,
                                    2,  # 16-bit samples = 2 bytes
                                    1,  # mono
                                    8000,  # from 8kHz
                                    24000,  # to 24kHz
                                    resample_state_up
                                )

                                # Encode back to base64
                                resampled_b64 = base64.b64encode(resampled_audio).decode('utf-8')

                                # Send to OpenAI
                                openai_msg = {
                                    "type": "input_audio_buffer.append",
                                    "audio": resampled_b64
                                }
                                await openai_ws.send(json.dumps(openai_msg))
                                user_audio_active = True

                        elif data.get("type") == "start":
                            logger.info(f"[FREJUN WS] Stream started for call {call_id}")

                        elif data.get("type") == "stop":
                            logger.info(f"[FREJUN WS] Stream stopped for call {call_id}")
                            if user_audio_active:
                                try:
                                    await openai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                                    await openai_ws.send(json.dumps({"type": "response.create"}))
                                except Exception as commit_error:
                                    logger.error(f"[FREJUN WS] Failed to finalize OpenAI input buffer: {commit_error}", exc_info=True)
                                user_audio_active = False

                except WebSocketDisconnect:
                    logger.info(f"[FREJUN WS] FreJun WebSocket disconnected")
                except Exception as e:
                    logger.error(f"[FREJUN WS] Error in frejun_to_openai: {e}", exc_info=True)
                finally:
                    if openai_ws and not openai_ws.closed:
                        try:
                            await openai_ws.close()
                        except Exception:
                            pass

            # Stream handler: OpenAI -> FreJun
            async def openai_to_frejun():
                """Receive audio from OpenAI and send to FreJun"""
                chunk_id = 1
                nonlocal resample_state_down

                try:
                    async for message in openai_ws:
                        data = json.loads(message)
                        event_type = data.get("type")

                        # Handle audio responses from OpenAI
                        if event_type == "response.audio.delta":
                            audio_b64 = data.get("delta")

                            if audio_b64:
                                # OpenAI sends 24kHz, FreJun expects 8kHz
                                # Decode base64
                                try:
                                    audio_bytes = base64.b64decode(audio_b64)
                                except Exception as decode_error:
                                    logger.warning(f"[FREJUN WS] Failed to decode OpenAI audio chunk: {decode_error}")
                                    continue

                                # Downsample from 24kHz to 8kHz
                                resampled_audio, resample_state_down = audioop.ratecv(
                                    audio_bytes,
                                    2,  # 16-bit samples
                                    1,  # mono
                                    24000,  # from 24kHz
                                    8000,  # to 8kHz
                                    resample_state_down
                                )

                                # Encode back to base64
                                resampled_b64 = base64.b64encode(resampled_audio).decode('utf-8')

                                # Send to FreJun
                                frejun_msg = {
                                    "type": "audio",
                                    "audio_b64": resampled_b64,
                                    "chunk_id": chunk_id
                                }

                                try:
                                    await websocket.send_text(json.dumps(frejun_msg))
                                except (WebSocketDisconnect, RuntimeError) as send_error:
                                    logger.info(f"[FREJUN WS] Unable to forward audio to FreJun (connection closed): {send_error}")
                                    break

                                chunk_id += 1

                        # Handle interruptions
                        elif event_type == "input_audio_buffer.speech_started":
                            logger.info(f"[FREJUN WS] User started speaking - interrupting AI")
                            # Send clear command to FreJun to stop playing current audio
                            try:
                                await websocket.send_text(json.dumps({"type": "clear"}))
                            except (WebSocketDisconnect, RuntimeError) as send_error:
                                logger.info(f"[FREJUN WS] Unable to send clear event to FreJun: {send_error}")
                                break
                            try:
                                await openai_ws.send(json.dumps({"type": "response.cancel"}))
                            except Exception as cancel_error:
                                logger.warning(f"[FREJUN WS] Failed to send response.cancel: {cancel_error}")

                        # Log transcripts
                        elif event_type == "conversation.item.created":
                            item = data.get("item", {})
                            if item.get("type") == "message":
                                content = item.get("content", [])
                                for c in content:
                                    if c.get("type") == "input_audio":
                                        transcript = c.get("transcript")
                                        if transcript:
                                            logger.info(f"[FREJUN WS] User said: {transcript}")
                                    elif c.get("type") == "text":
                                        text = c.get("text")
                                        if text:
                                            logger.info(f"[FREJUN WS] AI said: {text}")

                        # Session created
                        elif event_type == "session.created":
                            logger.info(f"[FREJUN WS] OpenAI session created")

                        # Session updated
                        elif event_type == "session.updated":
                            logger.info(f"[FREJUN WS] OpenAI session updated")

                        # Error handling
                        elif event_type == "error":
                            error = data.get("error", {})
                            logger.error(f"[FREJUN WS] OpenAI error: {error}")

                except websockets.exceptions.ConnectionClosedOK:
                    logger.info(f"[FREJUN WS] OpenAI WebSocket closed gracefully")
                except websockets.exceptions.ConnectionClosedError as conn_error:
                    logger.warning(f"[FREJUN WS] OpenAI WebSocket closed with error: {conn_error}")
                except Exception as e:
                    logger.error(f"[FREJUN WS] Error in openai_to_frejun: {e}", exc_info=True)
                finally:
                    pass
            # Run both stream handlers concurrently
            await asyncio.gather(
                frejun_to_openai(),
                openai_to_frejun()
            )

    except Exception as e:
        logger.error(f"[FREJUN WS] WebSocket error: {e}", exc_info=True)

    finally:
        # Update call log to completed
        update_call_log(call_id, {"call_status": "completed", "ended_at": datetime.utcnow()})
        logger.info(f"[FREJUN WS] WebSocket connection closed for call {call_id}")

# ==================== Outbound Calls ====================

@router.post("/initiate-call", status_code=200)
async def initiate_outbound_call(request: OutboundCallRequest):
    """
    Initiate an outbound call using FreJun (Teler) API.

    This endpoint:
    1. Creates a call log entry
    2. Uses the teler client to initiate the call
    3. Returns the call ID
    """
    logger.info(f"[FREJUN] Initiating outbound call from {request.from_number} to {request.to_number}")

    try:
        # Verify assistant exists
        assistant_config = get_assistant_config(request.assistant_id)

        if not assistant_config:
            raise HTTPException(status_code=404, detail="Assistant not found")

        # Get FreJun API key from settings
        frejun_api_key = settings.frejun_api_key

        if not frejun_api_key:
            raise HTTPException(status_code=500, detail="FreJun API key not configured")

        # Import teler client
        from teler import AsyncClient

        # Get server domain for callbacks
        server_domain = (
            settings.api_base_url
            or settings.base_url
            or os.getenv("API_BASE_URL")
            or "https://api.convis.ai"
        )
        server_domain = server_domain.rstrip("/")

        # Create call using teler client
        async with AsyncClient(api_key=frejun_api_key, timeout=10) as client:
            call = await client.calls.create(
                from_number=request.from_number,
                to_number=request.to_number,
                flow_url=f"{server_domain}/api/frejun/flow",
                status_callback_url=f"{server_domain}/api/frejun/webhook",
                record=True
            )

            call_id = call.id

            logger.info(f"[FREJUN] Call initiated successfully - Call ID: {call_id}")

            # Create call log
            create_call_log(
                call_id=call_id,
                assistant_id=request.assistant_id,
                user_id=request.user_id,
                from_number=request.from_number,
                to_number=request.to_number,
                call_type="outbound"
            )

            return JSONResponse({
                "success": True,
                "call_id": call_id,
                "message": "Call initiated successfully"
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FREJUN] Error initiating call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")

# ==================== Health Check ====================

@router.get("/health", status_code=200)
async def health_check():
    """Health check endpoint for FreJun integration"""
    return JSONResponse({
        "status": "healthy",
        "service": "frejun-integration",
        "version": "1.0.0"
    })

@router.get("/test", status_code=200)
async def test_endpoint():
    """Test endpoint for FreJun to verify connectivity"""
    return JSONResponse({
        "status": "ok",
        "message": "FreJun webhook endpoint is reachable",
        "timestamp": datetime.utcnow().isoformat()
    })

@router.post("/test", status_code=200)
async def test_endpoint_post(data: dict = Body(None)):
    """Test endpoint for FreJun to verify POST connectivity"""
    logger.info(f"[FREJUN TEST] Received test POST request: {data}")
    return JSONResponse({
        "status": "ok",
        "message": "FreJun webhook endpoint is reachable",
        "received_data": data,
        "timestamp": datetime.utcnow().isoformat()
    })
