# Realtime Calendar Booking

The realtime call handlers (`/api/inbound-calls/media-stream/{assistant_id}` and `/api/outbound-calls/media-stream/{assistant_id}`) now support hands-free calendar scheduling while the call is still in progress.

## Prerequisites

- A Google or Microsoft calendar account must be connected for the owning user through the `/api/calendar/{provider}/auth-url` and callback flow. Tokens are stored in `calendar_accounts`.
- Assistants use their configured OpenAI API key (Realtime + gpt-4o-mini) for intent extraction. Ensure the key has access to both models.
- For outbound campaign calls, the campaign must have `calendar_enabled = true` and include a `calendar_account_id`. The initiating WebSocket connection must provide valid `campaignId` and `leadId` query parameters.

## How it works

1. The assistant gathers appointment details conversationally (title/purpose, date/time, duration).
2. After each user and assistant turn, we analyse the recent transcript with `CalendarIntentService` (gpt-4o-mini, JSON output).
3. When sufficient details are present, the backend books the meeting immediately via `CalendarService`:
   - Inbound calls use `book_inbound_appointment`.
   - Outbound campaign calls use `book_appointment` and respect the campaign-assigned calendar account.
4. Successful bookings update the `call_logs` document with `appointment_details` and send a system message to the OpenAI Realtime session so the assistant can confirm the meeting on the call.

## Operational notes

- Appointments default to the user's or campaign's timezone (configurable in settings / working window) when the caller does not specify one.
- Duplicate scheduling is prevented per call by a simple in-memory flag and call log updates. If booking fails (e.g. missing refresh token), the assistant will not attempt further inserts until the issue is resolved.
- The realtime scheduler only runs when a calendar account is connected. Calls proceed normally when no calendar is configured.
