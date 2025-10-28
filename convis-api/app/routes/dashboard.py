from datetime import datetime, timedelta
from typing import Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.config.database import Database
from app.models.dashboard import AssistantSentimentBreakdown, AssistantSummaryItem, AssistantSummaryResponse
from app.utils.twilio_helpers import decrypt_twilio_credentials

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


TIMEFRAME_LABELS = {
    "total": "Total Cost",
    "last_7d": "Last 7 Days",
    "last_30d": "Last 30 Days",
    "last_90d": "Last 90 Days",
    "current_year": "Current Year",
}

POSITIVE_STATUSES = {"completed"}
NEGATIVE_STATUSES = {"failed", "busy", "no-answer", "canceled", "not-answered"}
NEUTRAL_STATUSES = {"in-progress", "queued", "ringing"}


def should_include_call(
    start_time: Optional[datetime],
    created_at: Optional[datetime],
    timeframe: str,
) -> bool:
    """Determine if a call falls within the selected timeframe."""
    if timeframe == "total":
        return True

    now = datetime.utcnow()
    cutoff: Optional[datetime] = None

    if timeframe == "last_7d":
        cutoff = now - timedelta(days=7)
    elif timeframe == "last_30d":
        cutoff = now - timedelta(days=30)
    elif timeframe == "last_90d":
        cutoff = now - timedelta(days=90)
    elif timeframe == "current_year":
        cutoff = datetime(now.year, 1, 1)

    reference_time = start_time or created_at
    if cutoff and reference_time:
        # Handle timezone-aware vs timezone-naive datetime comparison
        if reference_time.tzinfo is not None and cutoff.tzinfo is None:
            # Make cutoff timezone-aware (UTC)
            from datetime import timezone
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        elif reference_time.tzinfo is None and cutoff.tzinfo is not None:
            # Make reference_time timezone-aware (UTC)
            from datetime import timezone
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        return reference_time >= cutoff

    return cutoff is None


def update_sentiment_counts(sentiment: AssistantSentimentBreakdown, status: str) -> None:
    normalized = (status or "").lower()
    if normalized in POSITIVE_STATUSES:
        sentiment.positive += 1
    elif normalized in NEGATIVE_STATUSES:
        sentiment.negative += 1
    elif normalized in NEUTRAL_STATUSES:
        sentiment.neutral += 1
    else:
        sentiment.unknown += 1


@router.get(
    "/assistant-summary/{user_id}",
    response_model=AssistantSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_assistant_summary(
    user_id: str,
    timeframe: str = Query("total", regex="^(total|last_7d|last_30d|last_90d|current_year)$"),
):
    """
    Aggregate outbound/inbound call metrics per assistant for dashboard summary.
    """
    try:
        db = Database.get_db()
        users_collection = db["users"]
        phone_numbers_collection = db["phone_numbers"]
        provider_connections_collection = db["provider_connections"]
        assistants_collection = db["assistants"]
        call_logs_collection = db["call_logs"]

        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format",
            )

        user = users_collection.find_one({"_id": user_obj_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        phone_docs = list(phone_numbers_collection.find({"user_id": user_obj_id}))
        assistant_docs = list(assistants_collection.find({"user_id": user_obj_id}))
        phone_to_assistant: Dict[str, Dict[str, str]] = {}
        assistant_lookup: Dict[ObjectId, Dict[str, str]] = {}

        for phone_doc in phone_docs:
            assistant_id = phone_doc.get("assigned_assistant_id")
            if assistant_id:
                assistant_info = {
                    "id": str(assistant_id),
                    "name": phone_doc.get("assigned_assistant_name", "Unknown Assistant"),
                }
                phone_to_assistant[phone_doc["phone_number"]] = assistant_info
                assistant_lookup[assistant_id] = assistant_info

        twilio_connection = provider_connections_collection.find_one(
            {"user_id": user_obj_id, "provider": "twilio"}
        )

        twilio_client: Optional[Client] = None
        if twilio_connection:
            account_sid, auth_token = decrypt_twilio_credentials(twilio_connection)
            if account_sid and auth_token:
                twilio_client = Client(account_sid, auth_token)

        assistant_summary: Dict[str, AssistantSummaryItem] = {}
        total_cost = 0.0
        total_calls = 0

        def ensure_summary_entry(assistant_info: Optional[Dict[str, str]]) -> AssistantSummaryItem:
            key = assistant_info["id"] if assistant_info else "unassigned"
            if key not in assistant_summary:
                assistant_summary[key] = AssistantSummaryItem(
                    assistant_id=assistant_info["id"] if assistant_info else None,
                    assistant_name=assistant_info["name"] if assistant_info else "Unassigned",
                )
            return assistant_summary[key]

        # Process internal call logs first (outbound API calls tracked in our DB)
        db_calls = list(
            call_logs_collection.find({"user_id": user_obj_id}).sort("created_at", -1)
        )
        processed_sids = set()

        for db_call in db_calls:
            start_time = db_call.get("start_time")
            created_at = db_call.get("created_at")
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                except ValueError:
                    start_time = None

            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    created_at = None

            if not should_include_call(start_time, created_at, timeframe):
                continue

            assistant_info = None
            assigned_id = db_call.get("assigned_assistant_id") or db_call.get("assistant_id")
            if assigned_id:
                lookup_id: Optional[ObjectId] = None
                if isinstance(assigned_id, ObjectId):
                    lookup_id = assigned_id
                else:
                    try:
                        lookup_id = ObjectId(str(assigned_id))
                    except Exception:
                        lookup_id = None

                if lookup_id:
                    if lookup_id in assistant_lookup:
                        assistant_info = assistant_lookup[lookup_id]
                    else:
                        assistant_doc = assistants_collection.find_one({"_id": lookup_id})
                        if assistant_doc:
                            assistant_info = {
                                "id": str(assistant_doc["_id"]),
                                "name": assistant_doc.get("name", "Unknown Assistant"),
                            }
                            assistant_lookup[lookup_id] = assistant_info

            summary_entry = ensure_summary_entry(assistant_info)
            summary_entry.total_calls += 1
            total_calls += 1

            duration = db_call.get("duration")
            if duration:
                try:
                    summary_entry.total_duration_seconds += float(duration)
                except (ValueError, TypeError):
                    pass

            price = db_call.get("price")
            if price:
                try:
                    cost = abs(float(price))
                    summary_entry.total_cost += cost
                    total_cost += cost
                except (ValueError, TypeError):
                    pass

            status = db_call.get("status", "unknown")
            summary_entry.status_counts[status] = summary_entry.status_counts.get(status, 0) + 1
            update_sentiment_counts(summary_entry.sentiment, status)

            call_sid = db_call.get("call_sid")
            if call_sid:
                processed_sids.add(call_sid)

        # Process Twilio call logs for additional data (inbound/outbound not captured in DB)
        if twilio_client:
            try:
                calls = twilio_client.calls.list(limit=500)
            except TwilioRestException as e:
                logger.error(f"Twilio API error while fetching calls: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Error accessing Twilio: {str(e)}",
                )

            user_phone_numbers = {doc["phone_number"] for doc in phone_docs}

            for call in calls:
                call_start = call.start_time or call.date_created
                if call_start and should_include_call(call_start, None, timeframe):
                    if call.sid in processed_sids:
                        continue

                    from_number = getattr(call, "from_", None) or getattr(call, "from", None)
                    to_number = call.to

                    involves_user = to_number in user_phone_numbers or from_number in user_phone_numbers
                    if not involves_user:
                        continue

                    assistant_info = None
                    if call.direction in ("inbound", "trunking"):
                        assistant_info = phone_to_assistant.get(to_number)
                    elif call.direction.startswith("outbound") and from_number in phone_to_assistant:
                        assistant_info = phone_to_assistant.get(from_number)

                    summary_entry = ensure_summary_entry(assistant_info)
                    summary_entry.total_calls += 1
                    total_calls += 1

                    if call.duration:
                        try:
                            summary_entry.total_duration_seconds += float(call.duration)
                        except (ValueError, TypeError):
                            pass

                    if call.price:
                        try:
                            cost = abs(float(call.price))
                            summary_entry.total_cost += cost
                            total_cost += cost
                        except (ValueError, TypeError):
                            pass

                    status = call.status or "unknown"
                    summary_entry.status_counts[status] = summary_entry.status_counts.get(status, 0) + 1
                    update_sentiment_counts(summary_entry.sentiment, status)

                    processed_sids.add(call.sid)

        # Include assistants with no recent activity
        for assistant_doc in assistant_docs:
            key = str(assistant_doc["_id"])
            if key not in assistant_summary:
                assistant_summary[key] = AssistantSummaryItem(
                    assistant_id=key,
                    assistant_name=assistant_doc.get("name", "Unknown Assistant"),
                )

        summary_list = sorted(
            assistant_summary.values(),
            key=lambda item: item.total_cost,
            reverse=True,
        )

        return AssistantSummaryResponse(
            timeframe=TIMEFRAME_LABELS.get(timeframe, "Total Cost"),
            total_cost=round(total_cost, 4),
            total_calls=total_calls,
            assistants=summary_list,
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error building assistant summary: {error}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build assistant summary: {str(error)}",
        )
