# Voice of Customer Backend Deployment Instructions

## Important: Database Reversion to Original Architecture

This deployment reverts the application back to the pre-cache architecture that uses direct database queries with the original schema.

## Database Setup

The application now requires the original `voice_of_customer.db` database file with the following schema:

### Required Tables:
1. **feedback** - Main table with 5,828 records
2. **jira_tickets** - For team assignment
3. **team_directory** - Team information
4. **users** - Authentication

### Database Upload to Production

1. **Remove sensitive data from database**:
   ```bash
   # Create a sanitized copy without AWS keys
   sqlite3 voice_of_customer.db
   UPDATE feedback SET notes = REPLACE(notes, 'AKIA', 'XXXX') WHERE notes LIKE '%AKIA%';
   .quit
   ```

2. **Upload database to Render.com**:
   - Use Render dashboard to upload the sanitized database
   - Place at `/data/voice_of_customer.db`
   - Ensure persistent disk is mounted at `/data`

## Architecture Changes

### What Changed:
- ❌ Removed `intelligent_cache.py` and JSON storage
- ❌ Removed cache refresh scheduling
- ✅ Direct database queries with original schema
- ✅ Kept enhanced team assignment using CSV
- ✅ Kept improved field mapping logic

### Key Files Modified:
- `app/routers/feedback.py` - Direct database queries
- `app/routers/customer_pulse.py` - Direct database queries
- `main.py` - Removed cache initialization
- `team_assignment_service.py` - NEW: CSV-based team assignment

## Environment Variables

Ensure these are set in Render.com:
```
DATABASE_PATH=/data/voice_of_customer.db
OPENAI_API_KEY=your-key-here
```

## Deployment Steps

1. Push code to GitHub (without database file)
2. Upload sanitized database to Render persistent disk
3. Restart Render service
4. Verify API returns 5,828 records

## Testing Production

```bash
# Test record count
curl https://voice-of-customer-backend.onrender.com/feedback/ | jq '. | length'
# Should return: 5828

# Test single record
curl https://voice-of-customer-backend.onrender.com/feedback/recHOE2fPFPinp1cV
```

## Rollback Plan

If issues occur, the cache-based version is backed up at:
- `app/routers/feedback_cache_version.py.bak`
- Previous git commits contain full cache architecture