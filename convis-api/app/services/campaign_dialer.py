"""
Campaign dialer service with sequential calling and Redis locking
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

import pytz
import redis
from bson import ObjectId
from twilio.rest import Client

from app.config.database import Database
from app.config.settings import settings
from app.utils.twilio_helpers import decrypt_twilio_credentials

logger = logging.getLogger(__name__)


class CampaignDialer:
    """Service for managing campaign calls"""

    def __init__(self):
        # Redis client for distributed locking
        redis_url = settings.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

        # Default Twilio client (used if no per-user credentials are found)
        account_sid = settings.twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = settings.twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.default_twilio_client = Client(account_sid, auth_token) if account_sid and auth_token else None
        self._user_twilio_clients: Dict[str, Client] = {}

        # Base URL for TwiML
        configured_base_url = settings.base_url or settings.api_base_url
        self.base_url = configured_base_url or os.getenv("BASE_URL", "https://your-domain.com")
        self.twiml_url = os.getenv("OUTBOUND_TWIML_URL")
        if not self.twiml_url:
            self.twiml_url = f"{self.base_url}/api/twilio-webhooks/outbound-call"
        self.status_callback = os.getenv("TW_STATUS_CALLBACK")
        if not self.status_callback:
            self.status_callback = f"{self.base_url}/api/twilio-webhooks/call-status"
        self.recording_callback = os.getenv("TW_RECORDING_CALLBACK")
        if not self.recording_callback:
            self.recording_callback = f"{self.base_url}/api/twilio-webhooks/recording"
        self.last_error: Optional[str] = None

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

    def get_next_lead(self, campaign_id: str, ignore_window: bool = False) -> Optional[Dict[str, Any]]:
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
            }).sort([("order_index", 1), ("_id", 1)]).limit(10)  # Check next 10 leads

            for lead in leads:
                within_window = self.is_within_working_window(lead, working_window)
                if ignore_window and not within_window:
                    logger.info(f"Lead {lead['_id']} outside working window but selected for test call override")
                    within_window = True

                if within_window:
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
            db = Database.get_db()
            campaigns_collection = db["campaigns"]
            leads_collection = db["leads"]
            call_attempts_collection = db["call_attempts"]
            provider_connections_collection = db["provider_connections"]

            # Get campaign and lead
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})

            if not campaign or not lead:
                logger.error(f"Campaign or lead not found")
                self.last_error = "Campaign or lead record is missing in the database."
                return None

            # Get caller ID and phone number
            caller_id = campaign.get("caller_id")
            to_number = lead.get("e164")

            # Validate caller ID and lead phone number before attempting Twilio call
            if not caller_id:
                logger.error(f"Campaign {campaign_id} missing caller ID")
                self.last_error = "Campaign is missing a caller ID. Configure a verified Twilio number for this campaign."
                return None

            if not to_number:
                logger.error(f"Lead {lead_id} has no valid phone number")
                self.last_error = "Lead does not have a valid phone number in E.164 format."
                return None

            twilio_client = self._get_twilio_client_for_campaign(campaign, provider_connections_collection)
            if not twilio_client:
                self.last_error = (
                    "No active Twilio credentials found. Connect Twilio under Settings or "
                    "set TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN environment variables."
                )
                logger.error(f"Missing Twilio credentials for campaign {campaign_id}")
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

            base_url = self.twiml_url
            status_cb = self.status_callback
            recording_cb = self.recording_callback

            if not base_url:
                base_url = f"https://your-domain.com/api/twilio-webhooks/outbound-call"
                logger.warning("OUTBOUND_TWIML_URL not configured; falling back to default placeholder. Update BASE_URL/OUTBOUND_TWIML_URL for production.")

            if "http" not in base_url:
                base_url = f"https://{base_url.lstrip('/')}"

            call = twilio_client.calls.create(
                to=to_number,
                from_=caller_id,
                url=f"{base_url}?leadId={lead_id}&campaignId={campaign_id}&assistantId={assistant_id}",
                status_callback=f"{status_cb}?leadId={lead_id}&campaignId={campaign_id}" if status_cb else None,
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                status_callback_method="POST",
                record="true",
                recording_status_callback=f"{recording_cb}?leadId={lead_id}&campaignId={campaign_id}" if recording_cb else None,
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

            self.last_error = None
            return call.sid

        except Exception as e:
            logger.error(f"Error placing call: {e}")
            # Revert lead status
            db = Database.get_db()
            db["leads"].update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": {"status": "queued"}}
            )
            try:
                from twilio.base.exceptions import TwilioRestException
                if isinstance(e, TwilioRestException):
                    self.last_error = f"Twilio error {e.code}: {e.msg or e.msg}"
                else:
                    self.last_error = str(e)
            except Exception:
                self.last_error = str(e)
            return None

    def _get_twilio_client_for_campaign(self, campaign: Dict[str, Any], provider_connections_collection) -> Optional[Client]:
        """Return a Twilio client using the campaign owner's credentials or fall back to defaults."""
        user_id = campaign.get("user_id")
        if user_id:
            user_key = str(user_id)
            cached = self._user_twilio_clients.get(user_key)
            if cached:
                return cached

            try:
                user_obj_id = ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
            except Exception:
                logger.warning(f"Invalid user_id on campaign {campaign.get('_id')}")
                user_obj_id = None

            if user_obj_id:
                connection = provider_connections_collection.find_one({
                    "user_id": user_obj_id,
                    "provider": "twilio"
                })
                if connection:
                    account_sid, auth_token = decrypt_twilio_credentials(connection)
                    if account_sid and auth_token:
                        try:
                            client = Client(account_sid, auth_token)
                            self._user_twilio_clients[user_key] = client
                            return client
                        except Exception as cred_error:
                            logger.error(f"Failed to initialize Twilio client for user {user_id}: {cred_error}")

        return self.default_twilio_client

    def _map_call_status(self, call_status: str) -> str:
        status_map = {
            "completed": "completed",
            "answered": "completed",
            "busy": "busy",
            "no-answer": "no-answer",
            "failed": "failed",
            "canceled": "failed",
            "machine": "machine",
        }
        return status_map.get(call_status, "failed")

    def _compute_next_retry(
        self,
        campaign: Dict[str, Any],
        attempts: int,
        now: datetime,
        call_status: str,
    ) -> Optional[datetime]:
        policy = campaign.get("attempt_backoff") or {}
        strategy = policy.get("type", "mixed")

        if strategy == "mixed":
            schedule = policy.get("schedule") or []
            if not schedule:
                schedule = ["immediate", "+300s", "next_day_start"]
            index = min(max(attempts - 1, 0), len(schedule) - 1)
            token = schedule[index]
            candidate = self._interpret_backoff_token(token, campaign, now)
        elif strategy == "fixed":
            seconds = policy.get("seconds", 60)
            candidate = now + timedelta(seconds=seconds)
        elif strategy == "exponential":
            initial = policy.get("initial", 120)
            base = policy.get("base", 2)
            delay = initial * (base ** max(attempts - 1, 0))
            candidate = now + timedelta(seconds=delay)
        elif strategy == "daily":
            candidate = self._next_business_start(campaign, now, min_days=1)
        else:
            candidate = now + timedelta(seconds=120)

        if candidate and not self._is_within_window(campaign, candidate):
            candidate = self._next_business_start(campaign, candidate, min_days=0)

        stop_at = campaign.get("stop_at")
        if candidate and stop_at and candidate > stop_at:
            return None

        return candidate

    def _interpret_backoff_token(self, token: str, campaign: Dict[str, Any], now: datetime) -> Optional[datetime]:
        normalized = token.strip().lower()
        if normalized == "immediate":
            return now
        if normalized == "next_day_start":
            return self._next_business_start(campaign, now, min_days=1)
        if normalized.startswith("+"):
            value = normalized[1:].strip()
            multiplier = 1
            try:
                if value.endswith("minutes") or value.endswith("minute"):
                    amount = int(value.split()[0])
                    multiplier = amount * 60
                elif value.endswith("m"):
                    amount = int(value[:-1])
                    multiplier = amount * 60
                elif value.endswith("hours") or value.endswith("hour"):
                    amount = int(value.split()[0])
                    multiplier = amount * 3600
                elif value.endswith("h"):
                    amount = int(value[:-1])
                    multiplier = amount * 3600
                elif value.endswith("s"):
                    amount = int(value[:-1])
                    multiplier = amount
                else:
                    multiplier = int(value)
            except ValueError:
                multiplier = 300
            return now + timedelta(seconds=multiplier)
        return now + timedelta(minutes=5)

    def _is_within_window(self, campaign: Dict[str, Any], moment: datetime) -> bool:
        window = campaign.get("working_window") or {}
        tz_name = window.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        aware_moment = moment if moment.tzinfo else pytz.utc.localize(moment)
        local_dt = aware_moment.astimezone(tz)
        days = window.get("days") or [0, 1, 2, 3, 4]
        if days and local_dt.weekday() not in days:
            return False
        start_str = window.get("start", "09:00")
        end_str = window.get("end", "17:00")
        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))
        start_dt = local_dt.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
        end_dt = local_dt.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
        return start_dt <= local_dt <= end_dt

    def _next_business_start(self, campaign: Dict[str, Any], reference: datetime, min_days: int = 1) -> Optional[datetime]:
        window = campaign.get("working_window") or {}
        tz_name = window.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        days = window.get("days") or [0, 1, 2, 3, 4]
        start_str = window.get("start", "09:00")
        start_hour, start_min = map(int, start_str.split(":"))
        aware_ref = reference if reference.tzinfo else pytz.utc.localize(reference)
        local_ref = aware_ref.astimezone(tz)

        for offset in range(min_days, min_days + 8):
            candidate_day = local_ref + timedelta(days=offset)
            if days and candidate_day.weekday() not in days:
                continue
            naive = datetime(
                candidate_day.year,
                candidate_day.month,
                candidate_day.day,
                start_hour,
                start_min,
                tzinfo=None
            )
            local_start = tz.localize(naive)
            if offset == 0 and local_start <= aware_ref:
                continue
            return local_start.astimezone(pytz.utc).replace(tzinfo=None)
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
        """Handle call completion and schedule retries/fallbacks."""
        try:
            db = Database.get_db()
            leads_collection = db["leads"]
            campaigns_collection = db["campaigns"]

            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})

            if not lead or not campaign:
                logger.warning(f"Lead or campaign not found for call completion: lead={lead_id}, campaign={campaign_id}")
                return

            now = datetime.utcnow()
            mapped_status = self._map_call_status(call_status)
            attempts = lead.get("attempts", 0)
            max_attempts = campaign.get("attempts_per_number") or campaign.get("retry_policy", {}).get("max_attempts", 3)
            update_doc = {
                "last_outcome": call_status,
                "updated_at": now,
            }

            if mapped_status == "completed":
                update_doc.update({
                    "status": "completed",
                    "next_retry_at": None,
                    "fallback_round": lead.get("fallback_round", 0)
                })
                logger.info(f"Lead {lead_id} marked as completed after successful call")
            else:
                if attempts >= max_attempts:
                    update_doc.update({
                        "status": "failed",
                        "next_retry_at": None,
                        "fallback_round": lead.get("fallback_round", 0)
                    })
                    logger.info(f"Lead {lead_id} marked as failed after {attempts} attempts")
                else:
                    next_retry = self._compute_next_retry(campaign, attempts, now, call_status)
                    if next_retry is None:
                        update_doc.update({
                            "status": "failed",
                            "next_retry_at": None,
                            "fallback_round": lead.get("fallback_round", 0)
                        })
                        logger.info(f"Lead {lead_id} marked as failed (no retry schedule)")
                    else:
                        fallback_round = lead.get("fallback_round", 0)
                        if next_retry > now:
                            fallback_round += 1
                        update_doc.update({
                            "status": "queued",
                            "next_retry_at": next_retry,
                            "fallback_round": fallback_round
                        })
                        logger.info(f"Lead {lead_id} queued for retry at {next_retry} (attempt {attempts}/{max_attempts})")

            leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": update_doc}
            )

            logger.info(
                f"Call completed for lead {lead_id}: status={call_status} → {update_doc.get('status')}, next_retry={update_doc.get('next_retry_at')}"
            )

        except Exception as e:
            logger.error(f"Error handling call completion for lead {lead_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Even if there's an error, try to reset lead status so it's not stuck
            try:
                db = Database.get_db()
                db["leads"].update_one(
                    {"_id": ObjectId(lead_id)},
                    {"$set": {"status": "queued", "updated_at": datetime.utcnow()}}
                )
                logger.info(f"Reset lead {lead_id} to queued after error")
            except Exception as reset_error:
                logger.error(f"Failed to reset lead status: {reset_error}")
