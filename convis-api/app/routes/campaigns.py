from datetime import datetime
from typing import List
import csv
import io

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse

from app.config.database import Database
from app.models.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignResponse,
    LeadUploadResponse,
    CampaignStatusUpdate,
    CampaignStats,
    LeadResponse,
)
from app.services.phone_service import PhoneService
from app.services.campaign_dialer import CampaignDialer

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
phone_service = PhoneService()
dialer_service = CampaignDialer()


def serialize_campaign(doc: dict) -> CampaignResponse:
    doc = doc.copy()
    doc["_id"] = str(doc.pop("_id"))
    doc["user_id"] = str(doc["user_id"]) if isinstance(doc.get("user_id"), ObjectId) else doc.get("user_id")
    if doc.get("assistant_id") and isinstance(doc["assistant_id"], ObjectId):
        doc["assistant_id"] = str(doc["assistant_id"])
    doc["created_at"] = doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at")
    doc["updated_at"] = doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at")
    return CampaignResponse(**doc)


def serialize_lead(doc: dict) -> LeadResponse:
    doc = doc.copy()
    doc["_id"] = str(doc.pop("_id"))
    doc["campaign_id"] = str(doc["campaign_id"]) if isinstance(doc.get("campaign_id"), ObjectId) else doc.get("campaign_id")
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if isinstance(doc.get("updated_at"), datetime):
        doc["updated_at"] = doc["updated_at"].isoformat()
    return LeadResponse(**doc)


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate):
    """Create a new outbound campaign."""
    try:
        logger.info(f"Creating campaign with payload: {payload.model_dump()}")

        db = Database.get_db()
        campaigns_collection = db["campaigns"]
        campaigns_collection.create_index([("user_id", 1), ("status", 1)])

        # Validate and convert user_id to ObjectId
        try:
            user_obj_id = ObjectId(payload.user_id)
        except Exception as e:
            logger.error(f"Invalid user_id format: {payload.user_id}, error: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid user_id format: {str(e)}")

        # Validate and convert assistant_id to ObjectId if provided
        assistant_obj_id = None
        if payload.assistant_id:
            try:
                assistant_obj_id = ObjectId(payload.assistant_id)
            except Exception as e:
                logger.error(f"Invalid assistant_id format: {payload.assistant_id}, error: {e}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid assistant_id format: {str(e)}")

        now = datetime.utcnow()
        doc = {
            "user_id": user_obj_id,
            "name": payload.name,
            "country": payload.country,
            "working_window": payload.working_window.model_dump(),
            "caller_id": payload.caller_id,
            "assistant_id": assistant_obj_id,
            "retry_policy": payload.retry_policy.model_dump(),
            "pacing": payload.pacing.model_dump(),
            "start_at": payload.start_at,
            "stop_at": payload.stop_at,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "next_index": 0,
        }

        logger.info(f"Inserting campaign document: {doc}")
        result = campaigns_collection.insert_one(doc)
        logger.info(f"Created campaign {result.inserted_id} for user {payload.user_id}")

        created = campaigns_collection.find_one({"_id": result.inserted_id})
        if not created:
            raise Exception("Campaign was created but not found in database")

        return serialize_campaign(created)

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error creating campaign: {error}")
        logger.error(f"Full traceback: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(error)}"
        )


@router.get("/user/{user_id}", response_model=CampaignListResponse, status_code=status.HTTP_200_OK)
async def list_campaigns(user_id: str):
    """Return all campaigns for a user."""
    try:
        db = Database.get_db()
        campaigns_collection = db["campaigns"]

        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format")

        docs: List[dict] = list(
            campaigns_collection.find({"user_id": user_obj_id}).sort("created_at", -1)
        )
        campaigns = [serialize_campaign(doc) for doc in docs]
        return CampaignListResponse(campaigns=campaigns, total=len(campaigns))

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error listing campaigns: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch campaigns")


@router.get("/{campaign_id}", response_model=CampaignResponse, status_code=status.HTTP_200_OK)
async def get_campaign(campaign_id: str):
    try:
        db = Database.get_db()
        campaigns_collection = db["campaigns"]

        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign_id format")

        doc = campaigns_collection.find_one({"_id": campaign_obj_id})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

        return serialize_campaign(doc)

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error fetching campaign: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load campaign")


@router.post("/{campaign_id}/leads/upload", response_model=LeadUploadResponse, status_code=status.HTTP_200_OK)
async def upload_leads(campaign_id: str, file: UploadFile = File(...)):
    """
    Upload leads from CSV file.
    Expected columns: phone, name (optional), email (optional)
    """
    try:
        db = Database.get_db()
        campaigns_collection = db["campaigns"]
        leads_collection = db["leads"]

        # Verify campaign exists
        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign_id format")

        campaign = campaigns_collection.find_one({"_id": campaign_obj_id})
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

        # Get campaign country and timezone
        campaign_country = campaign.get("country", "US")
        campaign_tz = campaign.get("working_window", {}).get("timezone", "America/New_York")

        # Read CSV
        contents = await file.read()
        csv_text = contents.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_text))

        # Process leads
        total = 0
        valid = 0
        invalid = 0
        mismatches = 0
        now = datetime.utcnow()

        leads_to_insert = []

        for row in csv_reader:
            total += 1
            raw_number = row.get("phone", "").strip()
            name = row.get("name", "").strip() or None
            email = row.get("email", "").strip() or None

            # Validate and normalize phone number
            is_valid, e164, region, timezones = phone_service.normalize_and_validate(raw_number, campaign_country)

            if not is_valid:
                invalid += 1
                continue

            # Check for region mismatch
            is_mismatch = phone_service.check_region_mismatch(e164, campaign_country)
            if is_mismatch:
                mismatches += 1

            # Detect timezone
            lead_tz = timezones[0] if timezones else campaign_tz

            # Create lead document
            lead_doc = {
                "campaign_id": campaign_obj_id,
                "raw_number": raw_number,
                "e164": e164,
                "timezone": lead_tz,
                "name": name,
                "email": email,
                "status": "queued",
                "attempts": 0,
                "last_call_sid": None,
                "retry_on": None,
                "sentiment": None,
                "summary": None,
                "calendar_booked": False,
                "created_at": now,
                "updated_at": now,
                "custom_fields": {k: v for k, v in row.items() if k not in ["phone", "name", "email"]}
            }

            leads_to_insert.append(lead_doc)
            valid += 1

        # Bulk insert leads
        if leads_to_insert:
            leads_collection.insert_many(leads_to_insert)
            # Create indexes
            leads_collection.create_index([("campaign_id", 1), ("status", 1), ("_id", 1)])
            leads_collection.create_index([("campaign_id", 1), ("retry_on", 1)])
            logger.info(f"Inserted {len(leads_to_insert)} leads for campaign {campaign_id}")

        message = f"Uploaded {valid} valid leads"
        if invalid > 0:
            message += f", {invalid} invalid"
        if mismatches > 0:
            message += f", {mismatches} region mismatches"

        return LeadUploadResponse(
            total=total,
            valid=valid,
            invalid=invalid,
            mismatches=mismatches,
            message=message
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error uploading leads: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload leads: {str(error)}")


@router.get("/{campaign_id}/leads", response_model=List[LeadResponse], status_code=status.HTTP_200_OK)
async def get_campaign_leads(campaign_id: str, skip: int = 0, limit: int = 100):
    """Get leads for a campaign"""
    try:
        db = Database.get_db()
        leads_collection = db["leads"]

        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign_id format")

        docs = list(
            leads_collection.find({"campaign_id": campaign_obj_id})
            .sort("_id", 1)
            .skip(skip)
            .limit(limit)
        )

        return [serialize_lead(doc) for doc in docs]

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error fetching leads: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch leads")


@router.patch("/{campaign_id}/status", response_model=CampaignResponse, status_code=status.HTTP_200_OK)
async def update_campaign_status(campaign_id: str, payload: CampaignStatusUpdate):
    """Update campaign status (start, pause, stop)"""
    try:
        db = Database.get_db()
        campaigns_collection = db["campaigns"]

        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign_id format")

        # Validate status
        if payload.status not in ["running", "paused", "stopped", "completed"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

        # Update campaign
        result = campaigns_collection.update_one(
            {"_id": campaign_obj_id},
            {
                "$set": {
                    "status": payload.status,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

        # If starting, trigger first dial
        if payload.status == "running":
            dialer_service.dial_next(campaign_id)

        # Get updated campaign
        doc = campaigns_collection.find_one({"_id": campaign_obj_id})
        return serialize_campaign(doc)

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error updating campaign status: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")


@router.get("/{campaign_id}/stats", response_model=CampaignStats, status_code=status.HTTP_200_OK)
async def get_campaign_stats(campaign_id: str):
    """Get campaign statistics"""
    try:
        db = Database.get_db()
        leads_collection = db["leads"]
        call_attempts_collection = db["call_attempts"]

        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign_id format")

        # Aggregate lead stats
        lead_stats = list(leads_collection.aggregate([
            {"$match": {"campaign_id": campaign_obj_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]))

        # Convert to dict
        stats_dict = {item["_id"]: item["count"] for item in lead_stats}
        total_leads = sum(stats_dict.values())

        # Get sentiment average
        sentiment_pipeline = [
            {"$match": {"campaign_id": campaign_obj_id, "sentiment": {"$ne": None}}},
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$sentiment.score"}
                }
            }
        ]
        sentiment_result = list(leads_collection.aggregate(sentiment_pipeline))
        avg_sentiment = sentiment_result[0]["avg_score"] if sentiment_result else None

        # Get calendar bookings
        calendar_bookings = leads_collection.count_documents({
            "campaign_id": campaign_obj_id,
            "calendar_booked": True
        })

        # Get call stats
        call_stats = list(call_attempts_collection.aggregate([
            {"$match": {"campaign_id": campaign_obj_id}},
            {
                "$group": {
                    "_id": None,
                    "total_calls": {"$sum": 1},
                    "avg_duration": {"$avg": "$duration"}
                }
            }
        ]))

        total_calls = call_stats[0]["total_calls"] if call_stats else 0
        avg_duration = call_stats[0]["avg_duration"] if call_stats else None

        return CampaignStats(
            total_leads=total_leads,
            queued=stats_dict.get("queued", 0),
            completed=stats_dict.get("completed", 0),
            failed=stats_dict.get("failed", 0),
            no_answer=stats_dict.get("no-answer", 0),
            busy=stats_dict.get("busy", 0),
            calling=stats_dict.get("calling", 0),
            avg_sentiment_score=avg_sentiment,
            calendar_bookings=calendar_bookings,
            total_calls=total_calls,
            avg_call_duration=avg_duration
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error fetching campaign stats: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch stats")


@router.get("/{campaign_id}/export", status_code=status.HTTP_200_OK)
async def export_campaign_report(campaign_id: str):
    """Export campaign report as CSV"""
    try:
        db = Database.get_db()
        leads_collection = db["leads"]
        call_attempts_collection = db["call_attempts"]

        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign_id format")

        # Get all leads with call attempts
        leads = list(leads_collection.find({"campaign_id": campaign_obj_id}))

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "Lead ID",
            "Number",
            "Name",
            "Status",
            "Attempts",
            "Sentiment",
            "Sentiment Score",
            "Calendar Booked",
            "Recording URL",
            "Summary"
        ])

        # Write data rows
        for lead in leads:
            lead_id = str(lead["_id"])

            # Get last call attempt with recording
            call_attempt = call_attempts_collection.find_one(
                {"lead_id": lead["_id"], "recording_url": {"$ne": None}},
                sort=[("started_at", -1)]
            )

            recording_url = call_attempt.get("recording_url") if call_attempt else ""
            sentiment = lead.get("sentiment", {})

            writer.writerow([
                lead_id,
                lead.get("e164", ""),
                lead.get("name", ""),
                lead.get("status", ""),
                lead.get("attempts", 0),
                sentiment.get("label", "") if sentiment else "",
                sentiment.get("score", "") if sentiment else "",
                "Yes" if lead.get("calendar_booked") else "No",
                recording_url,
                lead.get("summary", "")
            ])

        # Return as streaming response
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_report.csv"}
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error exporting campaign: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to export report")


# ===== DELETE CAMPAIGN =====

@router.delete("/{campaign_id}", status_code=status.HTTP_200_OK)
async def delete_campaign(campaign_id: str):
    """
    Delete a campaign and all its associated data (leads, call attempts).

    Args:
        campaign_id: Campaign ID

    Returns:
        Success message

    Raises:
        HTTPException: If campaign not found or error occurs
    """
    try:
        db = Database.get_db()
        campaigns_collection = db['campaigns']
        leads_collection = db['leads']
        call_attempts_collection = db['call_attempts']

        logger.info(f"Deleting campaign: {campaign_id}")

        # Validate and convert campaign_id to ObjectId
        try:
            campaign_obj_id = ObjectId(campaign_id)
        except Exception as e:
            logger.error(f"Invalid campaign_id format: {campaign_id}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid campaign_id format: {str(e)}"
            )

        # Check if campaign exists
        campaign = campaigns_collection.find_one({"_id": campaign_obj_id})
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        # Delete all call attempts for this campaign's leads
        leads_cursor = leads_collection.find({"campaign_id": campaign_obj_id})
        lead_ids = [lead["_id"] for lead in leads_cursor]

        if lead_ids:
            call_attempts_result = call_attempts_collection.delete_many(
                {"lead_id": {"$in": lead_ids}}
            )
            logger.info(f"Deleted {call_attempts_result.deleted_count} call attempts")

        # Delete all leads for this campaign
        leads_result = leads_collection.delete_many({"campaign_id": campaign_obj_id})
        logger.info(f"Deleted {leads_result.deleted_count} leads")

        # Delete the campaign
        campaigns_collection.delete_one({"_id": campaign_obj_id})
        logger.info(f"Campaign {campaign_id} deleted successfully")

        return {
            "message": "Campaign deleted successfully",
            "deleted_leads": leads_result.deleted_count,
            "deleted_call_attempts": call_attempts_result.deleted_count if lead_ids else 0
        }

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error deleting campaign: {error}")
        logger.error(f"Full traceback: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete campaign: {str(error)}"
        )


# ===== SCHEDULER ENDPOINTS (for cron jobs) =====

@router.post("/scheduler/check", status_code=status.HTTP_200_OK)
async def scheduler_check_campaigns():
    """
    Scheduler endpoint: Check all running campaigns and dial next leads.
    Call this periodically (every 5-10 minutes) via cron or scheduler.
    """
    try:
        from app.services.campaign_scheduler import CampaignScheduler
        scheduler = CampaignScheduler()
        scheduler.check_and_dial_campaigns()
        return {"message": "Campaign check completed"}
    except Exception as error:
        logger.error(f"Error in scheduler check: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scheduler check failed")


@router.post("/scheduler/retry", status_code=status.HTTP_200_OK)
async def scheduler_process_retries():
    """
    Scheduler endpoint: Process retry leads for all campaigns.
    Call this once daily (e.g., 8 AM) via cron.
    """
    try:
        from app.services.campaign_scheduler import CampaignScheduler
        scheduler = CampaignScheduler()
        scheduler.process_all_campaign_retries()
        return {"message": "Retry processing completed"}
    except Exception as error:
        logger.error(f"Error in scheduler retry: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Scheduler retry failed")
