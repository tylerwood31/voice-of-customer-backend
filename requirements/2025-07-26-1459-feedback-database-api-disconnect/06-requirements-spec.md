# Requirements Specification: Feedback Database/API Disconnect Fix

## Problem Statement

The Voice of Customer application's feedback API is currently returning only 7 records instead of the expected 5,000+ records from 2025 that exist in Airtable. This represents a critical data synchronization failure affecting production users immediately.

## Solution Overview

Implement automated scheduling for the existing cache refresh system to ensure reliable data synchronization between Airtable and the application database, with immediate fixes for production data availability.

## Functional Requirements

### FR1: Immediate Data Recovery
- **Requirement**: All 5,000+ 2025 records from Airtable must be immediately available through the feedback API
- **Implementation**: Execute full cache refresh in production to populate database
- **Success Criteria**: API returns 5,000+ records instead of 7

### FR2: Automated Scheduling System  
- **Requirement**: Implement automated cache refresh scheduling
- **Schedule**:
  - **Incremental Updates**: Hourly from 9 AM - 6 PM EST, Monday-Friday
  - **Full Refresh**: Sundays at 11:59 PM EST
- **Implementation**: Add scheduling mechanism to existing cache system
- **Success Criteria**: Cache updates run automatically without manual intervention

### FR3: Robust Error Handling
- **Requirement**: System must gracefully handle Airtable API failures and network issues
- **Implementation**: Add retry logic and error recovery mechanisms
- **Success Criteria**: Temporary failures don't prevent data access

### FR4: Data Consistency
- **Requirement**: Ensure all 2025 records are properly filtered and synchronized
- **Implementation**: Verify Airtable filter `YEAR({Created}) = 2025` works correctly
- **Success Criteria**: No data loss during synchronization

## Technical Requirements

### TR1: Database Schema Initialization
- **File**: `intelligent_cache.py`
- **Implementation**: Auto-initialize database schema if tables don't exist
- **Pattern**: Use existing `init_schema()` function on startup
- **Assumption**: Auto-initialization prevents deployment failures

### TR2: Scheduling Infrastructure
- **Files**: New scheduling module or extend `setup_cron.sh`
- **Implementation**: Add cron jobs or background scheduler
- **Schedule Conversion**:
  - Incremental: `0 9-18 * * 1-5` (EST converted to server time)
  - Full refresh: `59 23 * * 0` (EST converted to server time)
- **Assumption**: Use cron-based scheduling for reliability

### TR3: Enhanced Error Handling
- **Files**: `airtable.py`, `intelligent_cache.py`
- **Implementation**: Add retry logic with exponential backoff
- **Pattern**: Try 3 attempts with 1s, 2s, 4s delays
- **Assumption**: Standard retry patterns improve reliability

### TR4: Cache Status Monitoring
- **Files**: `app/routers/cache_status.py`
- **Implementation**: Enhanced status reporting with scheduling info
- **Pattern**: Follow existing status endpoint patterns
- **Success Criteria**: Monitoring shows schedule execution status

### TR5: Production Database Path
- **Files**: `config.py`
- **Implementation**: Ensure `/data/voice_of_customer.db` path is correctly used
- **Pattern**: Follow existing database path configuration
- **Verification**: Database persists through deployments

## Implementation Hints

### Cache Refresh Pattern
```python
# Follow existing pattern in intelligent_cache.py
def scheduled_refresh():
    try:
        if is_full_refresh_time():
            result = refresh_full()
        else:
            status = get_status()
            since = status.get("last_update", "1970-01-01T00:00:00Z")
            result = refresh_incremental(since)
        return result
    except Exception as e:
        # Log error but don't crash
        print(f"Scheduled refresh failed: {e}")
```

### Scheduling Integration
- **Option 1**: Extend `setup_cron.sh` with new cache refresh cron jobs
- **Option 2**: Add background scheduler using APScheduler or similar
- **Follow**: Existing response times cache scheduling pattern

### Error Recovery
```python
# Add to airtable.py fetch_all_records()
for attempt in range(3):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            break
    except Exception as e:
        if attempt == 2:  # Last attempt
            raise
        time.sleep(2 ** attempt)  # Exponential backoff
```

## File Modifications Required

### Primary Files:
1. **`intelligent_cache.py`** - Add auto-initialization on import
2. **`airtable.py`** - Add retry logic and better error handling  
3. **`app/routers/cache_status.py`** - Add scheduling status endpoints
4. **New file**: Scheduling module or enhanced `setup_cron.sh`

### Secondary Files:
5. **`config.py`** - Add scheduling configuration variables
6. **`main.py`** - Add schema initialization on startup
7. **`db_connection.py`** - Verify handles concurrent scheduled operations

## Acceptance Criteria

### AC1: Data Recovery
- [ ] Production API returns 5,000+ feedback records
- [ ] All 2025 Airtable records are accessible via `/api/feedback/`
- [ ] No data loss from previous state

### AC2: Automated Operation  
- [ ] Incremental updates run hourly 9 AM - 6 PM EST weekdays
- [ ] Full refresh runs Sundays 11:59 PM EST
- [ ] No manual intervention required for normal operation

### AC3: System Reliability
- [ ] Temporary Airtable failures don't crash the system
- [ ] Existing cached data remains available during update failures
- [ ] Cache status endpoint shows scheduling information

### AC4: Production Deployment
- [ ] Database schema initializes automatically in new deployments
- [ ] Persistent database path `/data/voice_of_customer.db` works correctly
- [ ] Scheduling works in Render.com production environment

## Assumptions for Unknown Requirements

1. **Scheduling Method**: Use cron-based scheduling for reliability and simplicity
2. **Schema Initialization**: Auto-initialize on startup to prevent deployment issues
3. **Error Handling**: Implement standard retry patterns (3 attempts, exponential backoff)
4. **Cache Behavior**: Continue serving existing data when updates fail
5. **Time Zone**: Convert EST schedule to server time (likely UTC in cloud deployment)

## Deployment Notes

1. **Immediate Priority**: Execute manual full refresh in production to restore data access
2. **Schema Migration**: Ensure new cache tables exist before deploying scheduling
3. **Monitoring**: Use existing cache status endpoints to verify scheduling works
4. **Rollback Plan**: Manual cache refresh endpoints remain available as backup