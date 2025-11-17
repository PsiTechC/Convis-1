"""
Twilio Mark Event Handler
Handles mark events for audio playback tracking and interruption detection
Based on Bolna's mark event architecture
"""
import uuid
import json
import base64
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TwilioMarkHandler:
    """
    Handle Twilio mark events for interruption detection
    Implements Bolna's pre/post mark pattern for audio playback tracking
    """

    def __init__(self, websocket, stream_sid: Optional[str] = None):
        self.websocket = websocket
        self.stream_sid = stream_sid
        self.mark_events = {}  # mark_id -> metadata mapping
        self.is_playing_audio = False
        self.current_audio_text = ""

    def set_stream_sid(self, stream_sid: str):
        """Update stream SID (called when start event received)"""
        self.stream_sid = stream_sid

    async def send_mark(self, mark_id: str, metadata: Dict[str, Any]):
        """
        Send mark event to Twilio

        Args:
            mark_id: Unique identifier for this mark
            metadata: Metadata to store (type, text, is_final, etc.)
        """
        if not self.stream_sid:
            logger.warning("[MARK_HANDLER] Cannot send mark: stream_sid not set")
            return

        mark_message = {
            "event": "mark",
            "streamSid": self.stream_sid,
            "mark": {"name": mark_id}
        }

        self.mark_events[mark_id] = metadata
        await self.websocket.send_json(mark_message)
        logger.debug(f"[MARK_HANDLER] Sent mark: {mark_id} ({metadata.get('type')})")

    async def send_audio_with_marks(self, audio_data: bytes, text: str, is_final: bool = False):
        """
        Send audio with pre/post mark events (Bolna pattern)

        Args:
            audio_data: μ-law encoded audio bytes
            text: Text that was synthesized
            is_final: Whether this is the final chunk in response
        """
        if not self.stream_sid:
            logger.warning("[MARK_HANDLER] Cannot send audio: stream_sid not set")
            return

        # Pre-mark (before audio)
        pre_mark_id = str(uuid.uuid4())
        await self.send_mark(pre_mark_id, {
            "type": "pre_mark",
            "text": text,
            "is_first_chunk": not self.is_playing_audio
        })

        self.is_playing_audio = True
        self.current_audio_text = text

        # Send audio in chunks (20ms @ 8kHz μ-law = 160 bytes)
        chunk_size = 160
        total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size

        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            chunk_base64 = base64.b64encode(chunk).decode('utf-8')

            media_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": chunk_base64}
            }

            await self.websocket.send_json(media_message)

        logger.debug(f"[MARK_HANDLER] Sent {total_chunks} audio chunks ({len(audio_data)} bytes)")

        # Post-mark (after audio)
        post_mark_id = str(uuid.uuid4())
        await self.send_mark(post_mark_id, {
            "type": "post_mark",
            "text": text,
            "is_final": is_final,
            "duration": len(audio_data) / 8000.0  # Calculate duration in seconds
        })

    def process_mark_received(self, mark_id: str):
        """
        Called when Twilio confirms mark was processed

        Args:
            mark_id: Mark ID from Twilio's mark event
        """
        if mark_id in self.mark_events:
            metadata = self.mark_events[mark_id]

            logger.debug(f"[MARK_HANDLER] Mark confirmed: {mark_id} ({metadata.get('type')})")

            # If this is a final post-mark, audio playback is complete
            if metadata.get("type") == "post_mark" and metadata.get("is_final"):
                self.is_playing_audio = False
                self.current_audio_text = ""
                logger.info(f"[MARK_HANDLER] Audio playback complete")

            # Clean up processed mark
            del self.mark_events[mark_id]
        else:
            logger.warning(f"[MARK_HANDLER] Received unknown mark: {mark_id}")

    def clear_marks(self):
        """Clear all pending marks (used for interruptions)"""
        self.mark_events.clear()
        self.is_playing_audio = False
        self.current_audio_text = ""
        logger.info("[MARK_HANDLER] Cleared all marks")

    def get_playback_state(self) -> Dict[str, Any]:
        """Get current playback state"""
        return {
            "is_playing": self.is_playing_audio,
            "current_text": self.current_audio_text,
            "pending_marks": len(self.mark_events)
        }
