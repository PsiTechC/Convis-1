"""
Campaign dialer service with sequential calling and Redis locking
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis
from bson import ObjectId
from twilio.rest import Client
import os
import pytz

from app.config.database import Database
from app.services.phone_service import PhoneService

logger = logging.getLogger(__name__)


class CampaignDialer:
    """Service for managing campaign calls"""

    def __init__(self):
        # Redis client for distributed locking
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

        # Twilio client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_client = Client(account_sid, auth_token) if account_sid and auth_token else None

        # Base URL for TwiML
        self.base_url = os.getenv("BASE_URL", "https://your-domain.com")
        self.twiml_url = os.getenv("OUTBOUND_TWIML_URL", f"{self.base_url}/api/twilio-webhooks/outbound-call")
        self.status_callback = os.getenv("TW_STATUS_CALLBACK", f"{self.base_url}/api/twilio-webhooks/call-status")
        self.recording_callback = os.getenv("TW_RECORDING_CALLBACK", f"{self.base_url}/api/twilio-webhooks/recording")

    def acquire_lock(self, campaign_id: str, ttl: int = 180) -> bool:
        """
        Acquire a distributed lock for a campaign.

        Args:
            campaign_id: Campaign ID
            ttl: Lock TTL in seconds (default 3 minutes)

        Returns:
            True if lock acquired, False otherwise
        """
        lock_key = f"lock:campaign:{campaign_id}"
        return self.redis_client.set(lock_key, "1", nx=True, ex=ttl)

    def release_lock(self, campaign_id: str):
        """Release the lock for a campaign"""
        lock_key = f"lock:campaign:{campaign_id}"
        self.redis_client.delete(lock_key)

    def is_within_working_window(self, lead: Dict[str, Any], working_window: Dict[str, Any]) -> bool:
        """
        Check if current time is within the working window for a lead.

        Args:
            lead: Lead document with timezone
            working_window: Working window configuration

        Returns:
            True if within window, False otherwise
        """
        try:
            # Get lead's timezone
            lead_tz = lead.get("timezone", working_window.get("timezone", "America/New_York"))
            tz = pytz.timezone(lead_tz)
            now = datetime.now(tz)

            # Check day of week (0=Monday, 6=Sunday)
            if now.weekday() not in working_window.get("days", []):
                logger.info(f"Lead {lead['_id']} outside working days")
                return False

            # Parse start and end times
            start_time = working_window.get("start", "09:00")
            end_time = working_window.get("end", "17:00")

            start_hour, start_min = map(int, start_time.split(":"))
            end_hour, end_min = map(int, end_time.split(":"))

            # Create datetime objects for comparison
            start_dt = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            end_dt = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)

            if start_dt <= now <= end_dt:
                return True

            logger.info(f"Lead {lead['_id']} outside working hours")
            return False

        except Exception as e:
            logger.error(f"Error checking working window: {e}")
            return False

    def get_next_lead(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the next lead to call for a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Lead document or None
        """
        try:
            db = Database.get_db()
            campaigns_collection = db["campaigns"]
            leads_collection = db["leads"]

            # Get campaign
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return None

            # Get working window
            working_window = campaign.get("working_window", {})

            # Find next queued lead within working window
            leads = leads_collection.find({
                "campaign_id": ObjectId(campaign_id),
                "status": "queued"
            }).sort("_id", 1).limit(10)  # Check next 10 leads

            for lead in leads:
                # Check if within working window
                if self.is_within_working_window(lead, working_window):
                    # Check if max attempts not exceeded
                    max_attempts = campaign.get("retry_policy", {}).get("max_attempts", 3)
                    if lead.get("attempts", 0) < max_attempts:
                        return lead

            logger.info(f"No available leads for campaign {campaign_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting next lead: {e}")
            return None

    def place_call(self, campaign_id: str, lead_id: str) -> Optional[str]:
        """
        Place an outbound call to a lead.

        Args:
            campaign_id: Campaign ID
            lead_id: Lead ID

        Returns:
            Call SID or None if failed
        """
        try:
            if not self.twilio_client:
                logger.error("Twilio client not configured")
                return None

            db = Database.get_db()
            campaigns_collection = db["campaigns"]
            leads_collection = db["leads"]
            call_attempts_collection = db["call_attempts"]

            # Get campaign and lead
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})

            if not campaign or not lead:
                logger.error(f"Campaign or lead not found")
                return None

            # Get caller ID and phone number
            caller_id = campaign.get("caller_id")
            to_number = lead.get("e164")

            if not to_number:
                logger.error(f"Lead {lead_id} has no valid phone number")
                return None

            # Update lead status to calling
            leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$set": {
                        "status": "calling",
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"attempts": 1}
                }
            )

            # Get assistant ID for TwiML
            assistant_id = campaign.get("assistant_id", "")

            # Place the call
            call = self.twilio_client.calls.create(
                to=to_number,
                from_=caller_id,
                url=f"{self.twiml_url}?leadId={lead_id}&campaignId={campaign_id}&assistantId={assistant_id}",
                status_callback=f"{self.status_callback}?leadId={lead_id}&campaignId={campaign_id}",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                status_callback_method="POST",
                record="record-from-answer",
                recording_status_callback=f"{self.recording_callback}?leadId={lead_id}&campaignId={campaign_id}",
                recording_status_callback_method="POST",
                timeout=30
            )

            logger.info(f"Call placed: {call.sid} to {to_number}")

            # Create call attempt record
            attempt_num = lead.get("attempts", 1)
            call_attempts_collection.insert_one({
                "campaign_id": ObjectId(campaign_id),
                "lead_id": ObjectId(lead_id),
                "attempt": attempt_num,
                "call_sid": call.sid,
                "status": "initiated",
                "started_at": datetime.utcnow(),
                "ended_at": None,
                "recording_url": None,
                "transcript": None,
                "analysis": None,
                "duration": None
            })

            # Update lead with call SID
            leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": {"last_call_sid": call.sid}}
            )

            return call.sid

        except Exception as e:
            logger.error(f"Error placing call: {e}")
            # Revert lead status
            db = Database.get_db()
            db["leads"].update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": {"status": "queued"}}
            )
            return None

    def dial_next(self, campaign_id: str) -> bool:
        """
        Dial the next lead in a campaign (with locking).

        Args:
            campaign_id: Campaign ID

        Returns:
            True if call placed successfully, False otherwise
        """
        try:
            # Try to acquire lock
            if not self.acquire_lock(campaign_id):
                logger.info(f"Campaign {campaign_id} is locked, skipping")
                return False

            try:
                # Get next lead
                lead = self.get_next_lead(campaign_id)
                if not lead:
                    logger.info(f"No leads available for campaign {campaign_id}")
                    return False

                # Place call
                call_sid = self.place_call(campaign_id, str(lead["_id"]))
                return call_sid is not None

            finally:
                # Release lock after a delay (call is placed)
                # Keep lock for 30 seconds to prevent immediate re-dial
                pass  # Lock will auto-expire

        except Exception as e:
            logger.error(f"Error in dial_next: {e}")
            self.release_lock(campaign_id)
            return False

    def handle_call_completed(self, campaign_id: str, lead_id: str, call_status: str):
        """
        Handle call completion and schedule retry or next call.

        Args:
            campaign_id: Campaign ID
            lead_id: Lead ID
            call_status: Final call status from Twilio
        """
        try:
            db = Database.get_db()
            leads_collection = db["leads"]
            campaigns_collection = db["campaigns"]

            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})

            if not lead or not campaign:
                return

            # Map Twilio status to our status
            status_map = {
                "completed": "completed",
                "busy": "busy",
                "no-answer": "no-answer",
                "failed": "failed",
                "canceled": "failed"
            }

            new_status = status_map.get(call_status, "failed")

            # Check if we should retry
            should_retry = new_status in ["busy", "no-answer", "failed"]
            max_attempts = campaign.get("retry_policy", {}).get("max_attempts", 3)
            current_attempts = lead.get("attempts", 0)

            if should_retry and current_attempts < max_attempts:
                # Schedule for retry tomorrow
                leads_collection.update_one(
                    {"_id": ObjectId(lead_id)},
                    {
                        "$set": {
                            "status": new_status,
                            "retry_on": "tomorrow",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Lead {lead_id} scheduled for retry")
            else:
                # Mark as final status
                leads_collection.update_one(
                    {"_id": ObjectId(lead_id)},
                    {
                        "$set": {
                            "status": new_status,
                            "retry_on": None,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Lead {lead_id} marked as {new_status}")

            # Release lock and dial next
            self.release_lock(campaign_id)

            # Schedule next dial after a short delay (handled by scheduler)

        except Exception as e:
            logger.error(f"Error handling call completion: {e}")
