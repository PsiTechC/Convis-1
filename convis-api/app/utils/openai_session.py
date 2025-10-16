"""
Shared utilities for OpenAI Realtime API session management.
Used by both inbound and outbound call handlers.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Event types to log for debugging
LOG_EVENT_TYPES = [
    'response.content.done',
    'rate_limits.updated',
    'response.done',
    'response.created',
    'response.output_item.added',
    'response.output_item.done',
    'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started',
    'session.created',
    'session.updated',
    'response.audio.delta',
    'response.audio.done',
    'response.audio_transcript.delta',
    'response.audio_transcript.done',
    'response.output_audio.delta',
    'response.output_audio.done',
    'response.output_text.delta',
    'response.output_text.done',
    'conversation.item.created',
    'error'
]

async def send_session_update(
    openai_ws,
    system_message: str,
    voice: str,
    temperature: float = 0.8,
    enable_interruptions: bool = True,
    greeting_text: Optional[str] = None
):
    """
    Send session update to OpenAI WebSocket with dynamic configuration.
    CRITICAL: This matches the original pattern where send_initial_conversation_item
    is called INSIDE send_session_update for proper timing.

    Args:
        openai_ws: OpenAI WebSocket connection
        system_message: System instructions for the AI
        voice: Voice to use for output (e.g., 'alloy', 'echo', 'shimmer')
        temperature: Temperature for response generation (0.0-1.0)
        enable_interruptions: Whether to enable interruption handling
        greeting_text: Optional custom greeting text (passed to send_initial_conversation_item)
    """
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": voice,
            "instructions": system_message,
            "modalities": ["audio", "text"],
            "temperature": temperature,
        }
    }

    logger.info(f'Sending session update with voice={voice}, temperature={temperature}')
    logger.info('Session modalities: ["audio", "text"], formats: g711_ulaw')
    await openai_ws.send(json.dumps(session_update))

    # CRITICAL: Call send_initial_conversation_item HERE, matching original pattern (line 223)
    # This ensures proper timing for OpenAI to start generating audio
    await send_initial_conversation_item(openai_ws, greeting_text)

async def send_initial_conversation_item(openai_ws, greeting_text: Optional[str] = None):
    """
    Send initial conversation item so AI speaks first.

    Args:
        openai_ws: OpenAI WebSocket connection
        greeting_text: Optional custom greeting text
    """
    if greeting_text is None:
        greeting_text = (
            "Greet the user with 'Hello there! I am an AI voice assistant that will help you "
            "with any questions you may have. Please ask me anything you want to know.'"
        )

    initial_conversation_item = {
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
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))
    logger.info("Sent initial greeting to AI")

async def send_mark(websocket, stream_sid: str, mark_queue: list):
    """
    Send a mark event to track audio playback position.
    Used for precise interruption handling.

    Args:
        websocket: Twilio WebSocket connection
        stream_sid: Twilio stream SID
        mark_queue: Queue to track marks
    """
    if stream_sid:
        mark_event = {
            "event": "mark",
            "streamSid": stream_sid,
            "mark": {"name": "responsePart"}
        }
        await websocket.send_json(mark_event)
        mark_queue.append('responsePart')

async def handle_interruption(
    openai_ws,
    twilio_ws,
    stream_sid: str,
    last_assistant_item: Optional[str],
    response_start_timestamp: Optional[int],
    latest_media_timestamp: int,
    mark_queue: list,
    show_timing_math: bool = False
):
    """
    Handle interruption when the caller's speech starts.
    Truncates the current AI response and clears the audio buffer.

    Args:
        openai_ws: OpenAI WebSocket connection
        twilio_ws: Twilio WebSocket connection
        stream_sid: Twilio stream SID
        last_assistant_item: ID of the last assistant message
        response_start_timestamp: Timestamp when response started
        latest_media_timestamp: Current media timestamp
        mark_queue: Queue of marks
        show_timing_math: Whether to log timing calculations

    Returns:
        Tuple of (last_assistant_item, response_start_timestamp) after reset
    """
    logger.info("Handling interruption - truncating AI response")

    if mark_queue and response_start_timestamp is not None:
        elapsed_time = latest_media_timestamp - response_start_timestamp

        if show_timing_math:
            logger.info(
                f"Calculating elapsed time for truncation: "
                f"{latest_media_timestamp} - {response_start_timestamp} = {elapsed_time}ms"
            )

        if last_assistant_item:
            if show_timing_math:
                logger.info(f"Truncating item with ID: {last_assistant_item}, at: {elapsed_time}ms")

            truncate_event = {
                "type": "conversation.item.truncate",
                "item_id": last_assistant_item,
                "content_index": 0,
                "audio_end_ms": elapsed_time
            }
            await openai_ws.send(json.dumps(truncate_event))

        # Clear Twilio's audio buffer
        await twilio_ws.send_json({
            "event": "clear",
            "streamSid": stream_sid
        })

        mark_queue.clear()
        logger.info("Cleared audio buffers and mark queue")

    return None, None  # Reset last_assistant_item and response_start_timestamp

async def inject_knowledge_base_context(openai_ws, context: str):
    """
    Inject knowledge base context as a system message into the conversation.

    Args:
        openai_ws: OpenAI WebSocket connection
        context: Knowledge base context to inject
    """
    context_message = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": context
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(context_message))
    logger.info("Injected knowledge base context")
