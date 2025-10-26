"""Shared helpers for processing Twilio call status callbacks."""

from datetime import datetime
from typing import Optional

import logging

from app.config.database import Database
from app.services.campaign_dialer import CampaignDialer

logger = logging.getLogger(__name__)

_dialer = CampaignDialer()


def process_call_status(
    call_sid: Optional[str],
    call_status: Optional[str],
    call_duration: Optional[str],
    lead_id: Optional[str],
    campaign_id: Optional[str],
):
    """Update call attempt records and notify the dialer about completion."""
    if not call_sid or not call_status:
        raise ValueError("call_sid and call_status are required")

    db = Database.get_db()
    call_attempts_collection = db["call_attempts"]

    update_data = {
        "status": call_status,
        "updated_at": datetime.utcnow()
    }

    if call_duration:
        try:
            update_data["duration"] = int(call_duration)
        except ValueError:
            logger.warning("Invalid CallDuration '%s' for CallSid %s", call_duration, call_sid)

    if call_status in ["completed", "busy", "no-answer", "failed", "canceled"]:
        update_data["ended_at"] = datetime.utcnow()

    call_attempts_collection.update_one(
        {"call_sid": call_sid},
        {"$set": update_data},
        upsert=True
    )

    if call_status in ["completed", "busy", "no-answer", "failed", "canceled"] and lead_id and campaign_id:
        _dialer.handle_call_completed(campaign_id, lead_id, call_status)
