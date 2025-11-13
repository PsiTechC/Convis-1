"""
Post-call AI processing service
Handles transcription, sentiment analysis, and summary generation using OpenAI
"""
import logging
import os
import json
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from app.config.database import Database

logger = logging.getLogger(__name__)


class PostCallProcessor:
    """Service for post-call AI processing"""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - post-call processing will be limited")

    async def download_recording(self, recording_url: str, account_sid: str = None, auth_token: str = None) -> Optional[bytes]:
        """
        Download recording file from Twilio.

        Args:
            recording_url: URL to the recording (with .mp3 extension)
            account_sid: Twilio Account SID (optional, will use env if not provided)
            auth_token: Twilio Auth Token (optional, will use env if not provided)

        Returns:
            Recording bytes or None
        """
        try:
            # Use provided credentials or fall back to environment variables
            if not account_sid:
                account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            if not auth_token:
                auth_token = os.getenv("TWILIO_AUTH_TOKEN")

            if not account_sid or not auth_token:
                logger.error("Twilio credentials not configured")
                return None

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    recording_url,
                    auth=(account_sid, auth_token),
                    timeout=60.0
                )
                response.raise_for_status()
                return response.content

        except Exception as e:
            logger.error(f"Error downloading recording: {e}")
            return None

    async def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper.

        Args:
            audio_bytes: Audio file bytes

        Returns:
            Transcript text or None
        """
        try:
            if not self.openai_api_key:
                return None

            # OpenAI Whisper API
            async with httpx.AsyncClient() as client:
                files = {
                    "file": ("recording.mp3", audio_bytes, "audio/mpeg"),
                    "model": (None, "whisper-1")
                }

                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                    files=files,
                    timeout=120.0
                )
                response.raise_for_status()

                result = response.json()
                transcript = result.get("text", "")
                logger.info(f"Transcription completed: {len(transcript)} characters")
                return transcript

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None

    async def analyze_transcript(self, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Analyze transcript using GPT to extract sentiment, summary, and appointment info.

        Args:
            transcript: Call transcript

        Returns:
            Analysis dict with sentiment, summary, and appointment or None
        """
        try:
            if not self.openai_api_key or not transcript or len(transcript.strip()) < 10:
                # Empty or very short transcript
                return {
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "summary": "Call too short or empty transcript.",
                    "appointment": None
                }

            # Construct prompt for GPT
            prompt = f"""Analyze the following phone call transcript and provide a structured JSON response.

Transcript:
{transcript}

Provide a JSON response with these exact fields:
- sentiment: one of "positive", "neutral", or "negative"
- sentiment_score: a float between -1.0 (very negative) and 1.0 (very positive)
- summary: a concise summary in 3-8 sentences describing what was discussed
- appointment: if a meeting/appointment was scheduled, provide an object with {{title, start_iso, end_iso, timezone}}, otherwise null

Example format:
{{
  "sentiment": "positive",
  "sentiment_score": 0.7,
  "summary": "The caller inquired about product pricing...",
  "appointment": {{
    "title": "Follow-up Meeting",
    "start_iso": "2025-01-13T13:00:00",
    "end_iso": "2025-01-13T14:00:00",
    "timezone": "America/New_York"
  }}
}}

Return ONLY the JSON, no other text."""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are an expert call analyst. Always return valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
                    },
                    timeout=60.0
                )
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()

                # Parse JSON response
                # Remove markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                analysis = json.loads(content)
                logger.info(f"Analysis completed: sentiment={analysis.get('sentiment')}")

                return analysis

        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}")
            # Return default values on error
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "summary": "Unable to analyze call.",
                "appointment": None
            }

    async def process_call(self, call_sid: str, lead_id: str, campaign_id: str):
        """
        Process a completed call: transcribe, analyze, and update database.

        Args:
            call_sid: Twilio Call SID
            lead_id: Lead ID
            campaign_id: Campaign ID
        """
        try:
            logger.info(f"Processing call {call_sid} for lead {lead_id}")

            db = Database.get_db()
            call_attempts_collection = db["call_attempts"]
            leads_collection = db["leads"]

            # Get call attempt
            call_attempt = call_attempts_collection.find_one({"call_sid": call_sid})
            if not call_attempt:
                logger.error(f"Call attempt not found for CallSid: {call_sid}")
                return

            recording_url = call_attempt.get("recording_url")
            if not recording_url:
                logger.warning(f"No recording URL for call {call_sid}")
                return

            # Step 1: Download recording
            logger.info(f"Downloading recording from {recording_url}")
            audio_bytes = await self.download_recording(recording_url)
            if not audio_bytes:
                logger.error("Failed to download recording")
                return

            # Step 2: Transcribe
            logger.info("Transcribing audio...")
            transcript = await self.transcribe_audio(audio_bytes)
            if not transcript:
                logger.error("Failed to transcribe audio")
                transcript = ""

            # Update call attempt with transcript
            call_attempts_collection.update_one(
                {"_id": call_attempt["_id"]},
                {"$set": {"transcript": transcript, "updated_at": datetime.utcnow()}}
            )

            # Step 3: Analyze
            logger.info("Analyzing transcript...")
            analysis = await self.analyze_transcript(transcript)
            if not analysis:
                logger.error("Failed to analyze transcript")
                return

            # Update call attempt with analysis
            call_attempts_collection.update_one(
                {"_id": call_attempt["_id"]},
                {
                    "$set": {
                        "analysis": analysis,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Step 4: Update lead with sentiment and summary
            sentiment_data = {
                "label": analysis.get("sentiment", "neutral"),
                "score": analysis.get("sentiment_score", 0.0)
            }

            leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$set": {
                        "sentiment": sentiment_data,
                        "summary": analysis.get("summary", ""),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Step 5: Handle appointment booking if present
            appointment = analysis.get("appointment")
            if appointment and appointment.get("start_iso"):
                logger.info(f"Appointment detected for lead {lead_id}: {appointment.get('title')}")
                try:
                    from app.services.calendar_service import CalendarService
                    from app.services.appointment_whatsapp_service import AppointmentWhatsAppService

                    calendar_service = CalendarService()
                    event_id = await calendar_service.book_appointment(lead_id, campaign_id, appointment)

                    # Step 5a: Send WhatsApp confirmation if phone number available and calendar event created
                    if event_id:
                        try:
                            # Get lead details for phone number
                            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})
                            if lead and lead.get("phone"):
                                phone_number = lead["phone"]
                                customer_name = lead.get("full_name") or lead.get("first_name", "Customer")

                                # Get user_id from campaign
                                campaigns_collection = db["campaigns"]
                                campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
                                if campaign:
                                    user_id = str(campaign["user_id"])

                                    # Prepare booking data for WhatsApp
                                    booking_data = {
                                        "_id": call_sid,
                                        "customer_name": customer_name,
                                        "start_time": appointment.get("start_iso"),
                                        "location": appointment.get("location", "Phone Call"),
                                        "duration": appointment.get("duration", 30)
                                    }

                                    # Send WhatsApp confirmation
                                    whatsapp_result = await AppointmentWhatsAppService.send_appointment_confirmation(
                                        user_id=user_id,
                                        booking_data=booking_data,
                                        phone_number=phone_number
                                    )

                                    if whatsapp_result.get("success"):
                                        logger.info(f"WhatsApp confirmation sent to {phone_number} for outbound call {call_sid}")
                                    else:
                                        logger.warning(f"Failed to send WhatsApp confirmation: {whatsapp_result.get('error')}")
                        except Exception as whatsapp_error:
                            logger.error(f"Error sending WhatsApp confirmation for outbound call: {whatsapp_error}")
                            # Don't fail the entire process if WhatsApp fails

                except ImportError:
                    logger.warning("CalendarService not yet implemented")

            logger.info(f"Post-call processing completed for call {call_sid}")

        except Exception as e:
            logger.error(f"Error in post-call processing: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def transcribe_and_update_call(self, call_sid: str, recording_url: str):
        """
        Transcribe a call recording and update call_logs with the transcript.
        This is used for regular (non-campaign) calls.

        Args:
            call_sid: Twilio Call SID
            recording_url: URL to the recording (with .mp3 extension)
        """
        try:
            logger.info(f"Transcribing call {call_sid}")

            db = Database.get_db()
            call_logs_collection = db["call_logs"]

            # Get the call to find the user_id
            call = call_logs_collection.find_one({"call_sid": call_sid})
            if not call:
                logger.error(f"Call {call_sid} not found in database")
                return

            user_id = call.get("user_id")
            if not user_id:
                logger.error(f"No user_id for call {call_sid}")
                return

            # Get user's Twilio credentials from provider_connections
            from bson import ObjectId
            from app.utils.twilio_helpers import decrypt_twilio_credentials

            provider_connections = db["provider_connections"]
            twilio_connection = provider_connections.find_one({
                "user_id": user_id if isinstance(user_id, ObjectId) else ObjectId(user_id),
                "provider": "twilio"
            })

            if not twilio_connection:
                logger.error(f"No Twilio connection found for user {user_id}")
                return

            account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
            if not account_sid or not auth_token:
                logger.error(f"Invalid Twilio credentials for user {user_id}")
                return

            # Step 1: Download recording
            logger.info(f"Downloading recording from {recording_url}")
            audio_bytes = await self.download_recording(recording_url, account_sid, auth_token)
            if not audio_bytes:
                logger.error(f"Failed to download recording for {call_sid}")
                return

            # Step 2: Transcribe
            logger.info("Transcribing audio using OpenAI Whisper...")
            transcript = await self.transcribe_audio(audio_bytes)
            if not transcript:
                logger.warning(f"Transcription failed or empty for {call_sid}")
                transcript = "[Transcription unavailable]"

            # Step 3: Analyze
            logger.info("Analyzing transcript...")
            analysis = await self.analyze_transcript(transcript)
            if not analysis:
                analysis = {
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "summary": "Unable to analyze call.",
                    "appointment": None
                }

            # Step 4: Update call log with transcript and analysis
            call_logs_collection.update_one(
                {"call_sid": call_sid},
                {
                    "$set": {
                        "transcript": transcript,
                        "transcription_status": "completed",
                        "analysis": analysis,
                        "sentiment": analysis.get("sentiment", "neutral"),
                        "sentiment_score": analysis.get("sentiment_score", 0.0),
                        "summary": analysis.get("summary", ""),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Transcription completed for call {call_sid}: {len(transcript)} characters")

        except Exception as e:
            logger.error(f"Error transcribing call {call_sid}: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Update with error status
            try:
                db = Database.get_db()
                call_logs_collection = db["call_logs"]
                call_logs_collection.update_one(
                    {"call_sid": call_sid},
                    {
                        "$set": {
                            "transcription_status": "failed",
                            "transcription_error": str(e),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            except Exception:
                pass
