"""
Calendar integration service for Google Calendar and Microsoft Calendar
"""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx
from bson import ObjectId

from app.config.database import Database

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for calendar operations"""

    def __init__(self):
        self.db = Database.get_db()
        self.calendar_accounts_collection = self.db["calendar_accounts"]
        self.appointments_collection = self.db["appointments"]
        self.leads_collection = self.db["leads"]

    async def get_calendar_account(self, user_id: str, provider: str = "google") -> Optional[Dict[str, Any]]:
        """
        Get calendar account for a user.

        Args:
            user_id: User ID
            provider: "google" or "microsoft"

        Returns:
            Calendar account document or None
        """
        try:
            account = self.calendar_accounts_collection.find_one({
                "user_id": ObjectId(user_id),
                "provider": provider
            })
            return account
        except Exception as e:
            logger.error(f"Error getting calendar account: {e}")
            return None

    async def refresh_access_token(self, account: Dict[str, Any]) -> Optional[str]:
        """
        Refresh OAuth access token.

        Args:
            account: Calendar account document

        Returns:
            New access token or None
        """
        try:
            oauth_data = account.get("oauth", {})
            refresh_token = oauth_data.get("refreshToken")
            provider = account.get("provider")

            if not refresh_token:
                logger.error("No refresh token available")
                return None

            if provider == "google":
                # Google OAuth token refresh
                client_id = oauth_data.get("clientId") or os.getenv("GOOGLE_CLIENT_ID")
                client_secret = oauth_data.get("clientSecret") or os.getenv("GOOGLE_CLIENT_SECRET")

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token"
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    new_access_token = data.get("access_token")

                    # Update stored token
                    self.calendar_accounts_collection.update_one(
                        {"_id": account["_id"]},
                        {
                            "$set": {
                                "oauth.accessToken": new_access_token,
                                "oauth.expiry": datetime.utcnow().timestamp() + data.get("expires_in", 3600),
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )

                    return new_access_token

            elif provider == "microsoft":
                # Microsoft OAuth token refresh
                client_id = oauth_data.get("clientId") or os.getenv("MICROSOFT_CLIENT_ID")
                client_secret = oauth_data.get("clientSecret") or os.getenv("MICROSOFT_CLIENT_SECRET")

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                        data={
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                            "scope": "Calendars.ReadWrite"
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    new_access_token = data.get("access_token")

                    # Update stored token
                    self.calendar_accounts_collection.update_one(
                        {"_id": account["_id"]},
                        {
                            "$set": {
                                "oauth.accessToken": new_access_token,
                                "oauth.expiry": datetime.utcnow().timestamp() + data.get("expires_in", 3600),
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )

                    return new_access_token

        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None

    async def ensure_access_token(self, account: Dict[str, Any]) -> Optional[str]:
        """Return a valid access token, refreshing it if needed."""
        try:
            oauth_data = account.get("oauth", {})
            access_token = oauth_data.get("accessToken")
            expiry = oauth_data.get("expiry", 0)

            if not access_token:
                return None

            # Refresh token if it expires within the next minute
            if datetime.utcnow().timestamp() >= expiry - 60:
                logger.info("Access token expiring soon; refreshing for account %s", account.get("_id"))
                refreshed = await self.refresh_access_token(account)
                if refreshed:
                    access_token = refreshed
            return access_token
        except Exception as exc:
            logger.error(f"Failed to ensure access token: {exc}")
            return None

    async def create_google_event(self, access_token: str, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Create Google Calendar event.

        Args:
            access_token: Google access token
            event_data: Event data with title, start, end, timezone

        Returns:
            Event ID or None
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "summary": event_data.get("title", "Meeting"),
                        "start": {
                            "dateTime": event_data.get("start_iso"),
                            "timeZone": event_data.get("timezone", "America/New_York")
                        },
                        "end": {
                            "dateTime": event_data.get("end_iso"),
                            "timeZone": event_data.get("timezone", "America/New_York")
                        },
                        "description": event_data.get("notes", "")
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                event_id = result.get("id")
                logger.info(f"Google event created: {event_id}")
                return event_id

        except Exception as e:
            logger.error(f"Error creating Google event: {e}")
            return None

    async def create_microsoft_event(self, access_token: str, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Create Microsoft Calendar event.

        Args:
            access_token: Microsoft access token
            event_data: Event data with title, start, end, timezone

        Returns:
            Event ID or None
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://graph.microsoft.com/v1.0/me/events",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "subject": event_data.get("title", "Meeting"),
                        "start": {
                            "dateTime": event_data.get("start_iso"),
                            "timeZone": event_data.get("timezone", "America/New_York")
                        },
                        "end": {
                            "dateTime": event_data.get("end_iso"),
                            "timeZone": event_data.get("timezone", "America/New_York")
                        },
                        "body": {
                            "contentType": "Text",
                            "content": event_data.get("notes", "")
                        }
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                event_id = result.get("id")
                logger.info(f"Microsoft event created: {event_id}")
                return event_id

        except Exception as e:
            logger.error(f"Error creating Microsoft event: {e}")
            return None

    async def fetch_google_events(self, access_token: str, max_events: int = 10) -> List[Dict[str, Any]]:
        """Fetch upcoming Google Calendar events."""
        try:
            now_iso = datetime.utcnow().isoformat() + "Z"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "timeMin": now_iso,
                        "maxResults": max_events,
                        "singleEvents": True,
                        "orderBy": "startTime",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                events: List[Dict[str, Any]] = []
                for item in payload.get("items", []):
                    start = item.get("start", {})
                    end = item.get("end", {})
                    start_iso = start.get("dateTime") or (start.get("date") + "T00:00:00Z" if start.get("date") else None)
                    end_iso = end.get("dateTime") or (end.get("date") + "T00:00:00Z" if end.get("date") else None)
                    events.append({
                        "id": item.get("id"),
                        "title": item.get("summary", "(No title)"),
                        "start": start_iso,
                        "end": end_iso,
                        "location": item.get("location"),
                        "meeting_link": item.get("hangoutLink") or item.get("htmlLink"),
                        "organizer": item.get("organizer", {}).get("email"),
                    })
                return events
        except Exception as exc:
            logger.error(f"Error fetching Google events: {exc}")
            return []

    async def fetch_microsoft_events(self, access_token: str, max_events: int = 10) -> List[Dict[str, Any]]:
        """Fetch upcoming Microsoft (Outlook/Teams) calendar events."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/events",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "$top": max_events,
                        "$orderby": "start/dateTime",
                        "$select": "id,subject,start,end,location,onlineMeetingUrl,organizer,webLink",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                payload = response.json()
                events: List[Dict[str, Any]] = []
                for item in payload.get("value", []):
                    start = item.get("start", {})
                    end = item.get("end", {})
                    events.append({
                        "id": item.get("id"),
                        "title": item.get("subject", "(No title)"),
                        "start": start.get("dateTime"),
                        "end": end.get("dateTime"),
                        "timezone": start.get("timeZone"),
                        "location": (item.get("location") or {}).get("displayName"),
                        "meeting_link": item.get("onlineMeetingUrl") or item.get("webLink"),
                        "organizer": ((item.get("organizer") or {}).get("emailAddress") or {}).get("address"),
                    })
                return events
        except Exception as exc:
            logger.error(f"Error fetching Microsoft events: {exc}")
            return []

    async def fetch_upcoming_events(self, user_id: str, provider: Optional[str] = None, max_events: int = 10) -> List[Dict[str, Any]]:
        """Return aggregated upcoming events for the given user."""
        try:
            query: Dict[str, Any] = {"user_id": ObjectId(user_id)}
            if provider:
                query["provider"] = provider

            accounts = list(self.calendar_accounts_collection.find(query))
            events: List[Dict[str, Any]] = []

            for account in accounts:
                token = await self.ensure_access_token(account)
                if not token:
                    logger.warning("No valid access token for account %s", account.get("_id"))
                    continue

                provider_name = account.get("provider")
                provider_events: List[Dict[str, Any]] = []

                if provider_name == "google":
                    provider_events = await self.fetch_google_events(token, max_events)
                elif provider_name == "microsoft":
                    provider_events = await self.fetch_microsoft_events(token, max_events)

                for event in provider_events:
                    event["provider"] = provider_name
                    event["account_email"] = account.get("email")
                events.extend(provider_events)

            # Sort by start datetime when available
            events.sort(key=lambda evt: evt.get("start") or "")
            return events[:max_events]
        except Exception as exc:
            logger.error(f"Error fetching upcoming events: {exc}")
            return []

    async def book_appointment(self, lead_id: str, campaign_id: str, appointment_data: Dict[str, Any], provider: str = "google"):
        """
        Book an appointment for a lead.

        Args:
            lead_id: Lead ID
            campaign_id: Campaign ID
            appointment_data: Appointment details from AI analysis
            provider: "google" or "microsoft"
        """
        try:
            # Get campaign to find user_id
            campaigns_collection = self.db["campaigns"]
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return

            user_id = str(campaign["user_id"])

            # Get calendar account
            account = await self.get_calendar_account(user_id, provider)
            if not account:
                logger.warning(f"No {provider} calendar account for user {user_id}")
                return

            # Get access token (refresh if needed)
            oauth_data = account.get("oauth", {})
            access_token = oauth_data.get("accessToken")
            expiry = oauth_data.get("expiry", 0)

            # Check if token expired
            if datetime.utcnow().timestamp() >= expiry:
                logger.info("Access token expired, refreshing...")
                access_token = await self.refresh_access_token(account)
                if not access_token:
                    logger.error("Failed to refresh access token")
                    return

            # Create calendar event
            event_id = None
            if provider == "google":
                event_id = await self.create_google_event(access_token, appointment_data)
            elif provider == "microsoft":
                event_id = await self.create_microsoft_event(access_token, appointment_data)

            if not event_id:
                logger.error("Failed to create calendar event")
                return

            # Save appointment record
            appointment_doc = {
                "user_id": ObjectId(user_id),
                "lead_id": ObjectId(lead_id),
                "campaign_id": ObjectId(campaign_id),
                "provider": provider,
                "provider_event_id": event_id,
                "title": appointment_data.get("title", "Meeting"),
                "start": datetime.fromisoformat(appointment_data.get("start_iso")),
                "end": datetime.fromisoformat(appointment_data.get("end_iso")),
                "timezone": appointment_data.get("timezone", "America/New_York"),
                "created_at": datetime.utcnow()
            }

            self.appointments_collection.insert_one(appointment_doc)

            # Update lead
            self.leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": {"calendar_booked": True, "updated_at": datetime.utcnow()}}
            )

            logger.info(f"Appointment booked for lead {lead_id}: {event_id}")

        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            import traceback
            logger.error(traceback.format_exc())
