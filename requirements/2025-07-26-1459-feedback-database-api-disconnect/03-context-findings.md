# Context Findings

## Current Implementation Analysis

### Architecture Overview
- **Technology Stack**: Python FastAPI backend with SQLite database using WAL mode
- **Data Flow**: Airtable → intelligent_cache.py → SQLite → feedback.py API → Frontend
- **Storage**: JSON-based field storage in simplified schema (recently refactored)

### Key Files Analyzed

#### Core Cache System Files:
1. **`intelligent_cache.py`** - New function-based cache architecture
   - Functions: `refresh_full()`, `refresh_incremental()`, `get_status()`
   - Uses simplified JSON storage in `feedback` table
   - No automated scheduling mechanism implemented

2. **`airtable.py`** - Airtable API client
   - Handles pagination correctly with 100 records per page
   - Filters for 2025 records: `YEAR({Created}) = 2025`
   - Supports incremental updates with `since` parameter

3. **`app/routers/feedback.py`** - Main API endpoint
   - Returns data from local SQLite database
   - Parses JSON fields from new schema format
   - Maps Airtable fields to API response format

4. **`app/routers/cache_status.py`** - Cache management endpoints
   - Manual refresh endpoints: `/update-full`, `/update-incremental`
   - Status monitoring: cache status, total records, last update time

#### Configuration & Infrastructure:
5. **`config.py`** - Environment configuration
   - Database path: `/data/voice_of_customer.db` (production)
   - Airtable credentials from environment variables
   - Debug refresh logging available

6. **`db_connection.py`** - Database connection management
   - Context manager pattern with WAL mode
   - Thread-safe connections for background tasks

### Current Issues Identified

#### 1. **Missing Automated Scheduling**
- **Issue**: No cron job or scheduler for the required schedule:
  - Full refresh: Sundays at 11:59 PM
  - Incremental: Hourly during business hours (9 AM - 9 PM, Mon-Fri)
- **Impact**: Cache updates only happen manually
- **Files to modify**: Need new scheduling system

#### 2. **No Production Schema Initialization**
- **Issue**: New cache schema may not be initialized in production
- **Impact**: Database tables may not exist, causing API failures
- **Solution**: Auto-initialize schema on startup or via endpoint

#### 3. **Potential Airtable Filter Issues**
- **Current Filter**: `YEAR({Created}) = 2025`
- **Risk**: May miss records if Airtable field names vary
- **Verification needed**: Confirm exact field names in production Airtable

#### 4. **Error Handling Gaps**
- **Missing**: Robust retry logic for Airtable API failures
- **Missing**: Graceful degradation when cache is empty
- **Missing**: Monitoring/alerting for failed cache updates

### Similar Features Found
- **Response times cache**: Has cron job setup in `setup_cron.sh`
- **Pattern to follow**: Sunday night batch updates
- **Integration point**: Can extend existing cron infrastructure

### Technical Constraints
- **Deployment**: Render.com platform (based on config files)
- **Database**: SQLite with persistent disk at `/data/`
- **Rate limits**: Airtable API (5 requests/second)
- **Memory**: Large dataset (5,000+ records) needs efficient processing

### Integration Points
- **Frontend**: Expects specific JSON format from `/api/feedback/`
- **Background tasks**: FastAPI BackgroundTasks for async processing
- **Monitoring**: Cache status endpoints for health checks
- **Environment**: Production vs development database paths