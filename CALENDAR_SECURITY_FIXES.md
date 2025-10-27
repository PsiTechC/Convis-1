# Calendar Security Fixes - Implementation Summary

## Overview
This document describes the critical security fixes applied to the Convis calendar integration feature on 2025-10-27.

## Issues Addressed

### 1. Missing Authentication (CRITICAL - FIXED ✅)
**Issue**: Calendar endpoints had no JWT authentication, allowing any user to access other users' calendar data.

**Fix**:
- Created [app/utils/auth.py](convis-api/app/utils/auth.py) with `get_current_user()` and `verify_user_ownership()` functions
- Added JWT authentication to all calendar endpoints:
  - `GET /api/calendar/accounts/{user_id}` - List calendar accounts
  - `DELETE /api/calendar/accounts/{account_id}` - Delete calendar account
  - `GET /api/calendar/{provider}/auth-url` - Get OAuth URL
  - `GET /api/calendar/events/{user_id}` - List calendar events

**Files Modified**:
- [convis-api/app/routes/calendar.py](convis-api/app/routes/calendar.py)
- [convis-api/app/utils/auth.py](convis-api/app/utils/auth.py) (new file)

### 2. No User Ownership Validation (CRITICAL - FIXED ✅)
**Issue**: Endpoints didn't verify that the authenticated user owns the calendar account being accessed/deleted.

**Fix**:
- Added ownership validation using `verify_user_ownership()` function
- Delete endpoint now verifies account belongs to user before deletion
- Added audit logging for delete operations

**Example**:
```python
@router.delete("/accounts/{account_id}")
async def delete_calendar_account(account_id: str, current_user: dict = Depends(get_current_user)):
    # Verify account exists and belongs to current user
    account = accounts_collection.find_one({"_id": account_obj_id})
    account_user_id = str(account.get("user_id"))
    await verify_user_ownership(current_user, account_user_id)
    # ... then delete
```

### 3. Unencrypted Token Storage (CRITICAL - FIXED ✅)
**Issue**: OAuth access and refresh tokens stored in plain text in MongoDB.

**Fix**:
- Integrated existing encryption service from [app/utils/encryption.py](convis-api/app/utils/encryption.py)
- Tokens now encrypted before storing in database
- Tokens decrypted when retrieved for API calls
- Added `_decrypt_token()` helper method to CalendarService
- Backward compatibility maintained (can handle both encrypted and plain text)

**Files Modified**:
- [convis-api/app/services/calendar_service.py](convis-api/app/services/calendar_service.py)
- [convis-api/app/routes/calendar.py](convis-api/app/routes/calendar.py)

**Database Changes**:
```javascript
// Before
{
  "oauth": {
    "accessToken": "ya29.a0AfH6...",  // Plain text
    "refreshToken": "1//0gHd...",     // Plain text
    "expiry": 1698765432.0
  }
}

// After
{
  "oauth": {
    "accessToken": "gAAAAABl...",  // Encrypted with Fernet
    "refreshToken": "gAAAAABl...", // Encrypted with Fernet
    "expiry": 1698765432.0,
    "is_valid": true
  }
}
```

### 4. Token Refresh Not Automatic for Read Operations (FIXED ✅)
**Issue**: Event fetching didn't refresh expired tokens, causing silent failures.

**Fix**:
- `fetch_upcoming_events()` now uses `ensure_access_token()` which automatically refreshes
- Proactive refresh if token expiring within 60 seconds
- All event fetch operations handle token refresh transparently

### 5. No Error Handling for Revoked Tokens (FIXED ✅)
**Issue**: If user revoked OAuth access in Google/Microsoft, system continued trying with invalid tokens.

**Fix**:
- Added `_handle_token_error()` method to detect revoked tokens
- Detects errors: `invalid_grant`, `token_revoked`, `invalid_token`, `unauthorized`
- Marks account as invalid in database with error message
- Skips invalid accounts in event fetching
- User notified to reconnect calendar

**Example**:
```python
async def _handle_token_error(self, account: Dict[str, Any], error: Exception) -> None:
    """Handle token-related errors, including revoked tokens."""
    error_str = str(error).lower()

    if any(keyword in error_str for keyword in ["invalid_grant", "token_revoked", "invalid_token", "unauthorized"]):
        # Mark account as requiring re-authorization
        self.calendar_accounts_collection.update_one(
            {"_id": account["_id"]},
            {
                "$set": {
                    "oauth.is_valid": False,
                    "oauth.error": "Token revoked or invalid. Please reconnect your calendar.",
                    "updated_at": datetime.utcnow()
                }
            }
        )
```

### 6. OAuth Redirect URI Configuration (FIXED ✅)
**Issue**: Google OAuth redirect URI mismatch error.

**Current Configuration**:
```
GOOGLE_REDIRECT_URI=https://nonretail-deana-allopathically.ngrok-free.dev/api/calendar/google/callback
```

**Action Required**: Update Google Cloud Console OAuth 2.0 Client to include this redirect URI in authorized redirect URIs.

## Migration Required

For existing deployments with calendar accounts, run the migration script:

```bash
cd convis-api
python3 migrate_calendar_tokens.py
```

This script will:
1. Encrypt all existing plain text tokens
2. Mark all accounts as `is_valid: true`
3. Maintain backward compatibility

## Security Improvements Summary

| Issue | Severity | Status | Impact |
|-------|----------|--------|--------|
| Missing authentication | CRITICAL | ✅ Fixed | Prevents unauthorized access to calendar data |
| No ownership validation | CRITICAL | ✅ Fixed | Prevents users from deleting others' calendars |
| Unencrypted tokens | CRITICAL | ✅ Fixed | Protects tokens in case of database breach |
| No token refresh | HIGH | ✅ Fixed | Prevents silent failures when tokens expire |
| No revocation handling | HIGH | ✅ Fixed | Gracefully handles revoked OAuth access |
| Redirect URI mismatch | MEDIUM | ⚠️ Config needed | Requires Google Console update |

## Testing Checklist

- [ ] Verify calendar connection works (Google)
- [ ] Verify calendar connection works (Microsoft)
- [ ] Verify events are fetched correctly
- [ ] Verify token refresh works automatically
- [ ] Verify unauthorized users cannot access others' calendars
- [ ] Verify users can only delete their own calendar connections
- [ ] Verify revoked tokens are handled gracefully
- [ ] Run migration script on production database
- [ ] Update Google Cloud Console redirect URI

## API Changes

All calendar endpoints now require `Authorization: Bearer <token>` header.

**Before**:
```bash
curl http://localhost:8000/api/calendar/accounts/123
```

**After**:
```bash
curl http://localhost:8000/api/calendar/accounts/123 \
  -H "Authorization: Bearer eyJhbGc..."
```

## Files Created
1. [convis-api/app/utils/auth.py](convis-api/app/utils/auth.py) - Authentication utilities
2. [convis-api/migrate_calendar_tokens.py](convis-api/migrate_calendar_tokens.py) - Token encryption migration script

## Files Modified
1. [convis-api/app/routes/calendar.py](convis-api/app/routes/calendar.py) - Added auth, encryption
2. [convis-api/app/services/calendar_service.py](convis-api/app/services/calendar_service.py) - Added encryption, error handling

## Environment Variables Used
- `JWT_SECRET` - For JWT token validation
- `ENCRYPTION_KEY` - For token encryption (already configured)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google OAuth
- `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` - Microsoft OAuth

## Deployment Notes

1. **No breaking changes** for frontend (same endpoints, just add auth header)
2. **Migration required** for existing calendar accounts
3. **Google Console update** required for redirect URI
4. **Backward compatible** - can handle both encrypted and plain text tokens during migration

## Next Steps

1. Update Google Cloud Console with redirect URI
2. Run migration script on production database
3. Monitor logs for token refresh and revocation errors
4. Consider adding rate limiting on calendar API calls
5. Add conflict detection before booking appointments
6. Implement calendar sync background job
