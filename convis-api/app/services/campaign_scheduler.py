"""
Campaign scheduler service
Handles retry logic, next-day retry lists, and automated campaign execution
"""
import logging
from datetime import datetime, timedelta
from typing import List
from bson import ObjectId
import pytz

from app.config.database import Database
from app.services.campaign_dialer import CampaignDialer

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """Service for scheduling campaign operations"""

    def __init__(self):
        self.db = Database.get_db()
        self.dialer = CampaignDialer()

    def process_retry_leads(self, campaign_id: str):
        """
        Process leads marked for retry.
        Called daily to move "retry_on=tomorrow" leads back to queued.

        Args:
            campaign_id: Campaign ID
        """
        try:
            campaigns_collection = self.db["campaigns"]
            leads_collection = self.db["leads"]

            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return

            # Get working window timezone
            working_window = campaign.get("working_window", {})
            campaign_tz_str = working_window.get("timezone", "America/New_York")
            campaign_tz = pytz.timezone(campaign_tz_str)
            now = datetime.now(campaign_tz)

            # Move retry leads back to queued
            result = leads_collection.update_many(
                {
                    "campaign_id": ObjectId(campaign_id),
                    "retry_on": "tomorrow"
                },
                {
                    "$set": {
                        "status": "queued",
                        "retry_on": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Moved {result.modified_count} leads back to queue for campaign {campaign_id}")

        except Exception as e:
            logger.error(f"Error processing retry leads: {e}")

    def process_all_campaign_retries(self):
        """
        Process retries for all running campaigns.
        Should be called by a daily cron job.
        """
        try:
            campaigns_collection = self.db["campaigns"]

            # Get all running campaigns
            campaigns = campaigns_collection.find({"status": "running"})

            for campaign in campaigns:
                campaign_id = str(campaign["_id"])
                logger.info(f"Processing retries for campaign {campaign_id}")
                self.process_retry_leads(campaign_id)

        except Exception as e:
            logger.error(f"Error processing campaign retries: {e}")

    def check_and_dial_campaigns(self):
        """
        Check all running campaigns and dial next lead if ready.
        Should be called periodically (e.g., every 5-10 minutes).
        """
        try:
            campaigns_collection = self.db["campaigns"]
            leads_collection = self.db["leads"]

            # Get all running campaigns
            campaigns = campaigns_collection.find({"status": "running"})

            for campaign in campaigns:
                campaign_id = str(campaign["_id"])

                start_at = campaign.get("start_at")
                stop_at = campaign.get("stop_at")
                utc_now = datetime.utcnow()

                if start_at and isinstance(start_at, datetime) and utc_now < start_at:
                    logger.info(f"Campaign {campaign_id} scheduled to start at {start_at}, skipping until then")
                    continue

                if stop_at and isinstance(stop_at, datetime) and utc_now > stop_at:
                    logger.info(f"Campaign {campaign_id} stop time reached; marking as completed")
                    campaigns_collection.update_one(
                        {"_id": campaign["_id"]},
                        {"$set": {"status": "completed", "updated_at": datetime.utcnow()}}
                    )
                    continue

                # Check if there's an active call for this campaign
                active_call = leads_collection.find_one({
                    "campaign_id": campaign["_id"],
                    "status": "calling"
                })

                if active_call:
                    logger.info(f"Campaign {campaign_id} has active call, skipping")
                    continue

                # Check if we're within working window
                working_window = campaign.get("working_window", {})
                if not self._is_campaign_window_open(working_window):
                    logger.info(f"Campaign {campaign_id} outside working window")
                    continue

                # Check if there are queued leads
                queued_count = leads_collection.count_documents({
                    "campaign_id": campaign["_id"],
                    "status": "queued"
                })

                if queued_count == 0:
                    logger.info(f"Campaign {campaign_id} has no queued leads")
                    # Mark campaign as completed if all leads processed
                    all_leads = leads_collection.count_documents({"campaign_id": campaign["_id"]})
                    completed_or_failed = leads_collection.count_documents({
                        "campaign_id": campaign["_id"],
                        "status": {"$in": ["completed", "failed"]}
                    })

                    if all_leads == completed_or_failed:
                        campaigns_collection.update_one(
                            {"_id": campaign["_id"]},
                            {"$set": {"status": "completed", "updated_at": datetime.utcnow()}}
                        )
                        logger.info(f"Campaign {campaign_id} marked as completed")
                    continue

                # Dial next lead
                logger.info(f"Attempting to dial next lead for campaign {campaign_id}")
                success = self.dialer.dial_next(campaign_id)
                if success:
                    logger.info(f"Successfully dialed next lead for campaign {campaign_id}")
                else:
                    logger.warning(f"Failed to dial next lead for campaign {campaign_id}")

        except Exception as e:
            logger.error(f"Error checking campaigns: {e}")

    def _is_campaign_window_open(self, working_window: dict) -> bool:
        """
        Check if campaign working window is currently open.

        Args:
            working_window: Working window configuration

        Returns:
            True if window is open, False otherwise
        """
        try:
            tz_str = working_window.get("timezone", "America/New_York")
            tz = pytz.timezone(tz_str)
            now = datetime.now(tz)

            # Check day
            allowed_days = working_window.get("days", [])
            if now.weekday() not in allowed_days:
                return False

            # Check time
            start_time = working_window.get("start", "09:00")
            end_time = working_window.get("end", "17:00")

            start_hour, start_min = map(int, start_time.split(":"))
            end_hour, end_min = map(int, end_time.split(":"))

            start_dt = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            end_dt = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)

            return start_dt <= now <= end_dt

        except Exception as e:
            logger.error(f"Error checking window: {e}")
            return False

    def start_campaign(self, campaign_id: str) -> bool:
        """
        Start a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if started successfully
        """
        try:
            campaigns_collection = self.db["campaigns"]

            # Update status to running
            result = campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {
                    "$set": {
                        "status": "running",
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Campaign {campaign_id} started")
                # Dial first lead
                self.dialer.dial_next(campaign_id)
                return True

            return False

        except Exception as e:
            logger.error(f"Error starting campaign: {e}")
            return False

    def pause_campaign(self, campaign_id: str) -> bool:
        """
        Pause a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if paused successfully
        """
        try:
            campaigns_collection = self.db["campaigns"]

            result = campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {
                    "$set": {
                        "status": "paused",
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Campaign {campaign_id} paused")
                return True

            return False

        except Exception as e:
            logger.error(f"Error pausing campaign: {e}")
            return False

    def stop_campaign(self, campaign_id: str) -> bool:
        """
        Stop a campaign permanently.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if stopped successfully
        """
        try:
            campaigns_collection = self.db["campaigns"]

            result = campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {
                    "$set": {
                        "status": "stopped",
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Campaign {campaign_id} stopped")
                return True

            return False

        except Exception as e:
            logger.error(f"Error stopping campaign: {e}")
            return False
