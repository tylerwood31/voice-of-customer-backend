from fastapi import APIRouter, BackgroundTasks
from datetime import datetime, timezone
import sys
import os

router = APIRouter()

# Import new intelligent cache system
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
import intelligent_cache

@router.get("/", summary="Get intelligent cache status and statistics")
def get_cache_status():
    """Get current intelligent cache status, schedule, and statistics."""
    now = datetime.now(timezone.utc)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_weekday = weekday_names[now.weekday()]
    
    # Get cache status from new cache system
    cache_status = intelligent_cache.get_status()
    
    # Get scheduler status
    try:
        from cache_scheduler import cache_scheduler
        scheduler_status = cache_scheduler.get_status()
    except Exception as e:
        scheduler_status = {"error": f"Scheduler not available: {e}"}
    
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_weekday": current_weekday,
        "cache_type": "new_architecture_with_scheduling",
        "cache_status": cache_status,
        "scheduler_status": scheduler_status,
        "schedule": {
            "strategy": {
                "full_refresh": "Sundays at 11:59 PM EST - Load all 2025 records from Airtable",
                "incremental": "Hourly 9 AM - 6 PM EST Mon-Fri - Load records modified since last update",
                "storage": "JSON fields in SQLite with WAL mode"
            }
        },
        "actions": {
            "force_incremental": "/api/cache/update-incremental",
            "force_full_refresh": "/api/cache/update-full",
            "get_status": "/api/cache/",
            "scheduler_status": "/api/cache/scheduler-status"
        }
    }

@router.post("/update-incremental", summary="Force incremental update")
def force_incremental_update(background_tasks: BackgroundTasks):
    """Force an incremental update (new records only)."""
    # Get last update time for incremental refresh
    status = intelligent_cache.get_status()
    since = status.get("last_update") if status else None
    
    background_tasks.add_task(intelligent_cache.refresh_incremental, since or "1970-01-01T00:00:00Z")
    return {
        "message": "Incremental cache update started in background",
        "type": "incremental",
        "since": since,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.post("/update-full", summary="Force full refresh")
def force_full_refresh(background_tasks: BackgroundTasks):
    """Force a full refresh (all records)."""
    background_tasks.add_task(intelligent_cache.refresh_full)
    return {
        "message": "Full cache refresh started in background",
        "type": "full_refresh",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.get("/stats", summary="Get detailed cache statistics")
def get_detailed_stats():
    """Get detailed cache statistics."""
    cache_status = intelligent_cache.get_status()
    
    return {
        "cache": cache_status
    }

@router.post("/init-schema", summary="Initialize database schema")
def init_schema():
    """Initialize the new cache database schema."""
    try:
        intelligent_cache.init_schema()
        return {
            "message": "Database schema initialized successfully",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    except Exception as e:
        return {
            "error": f"Schema initialization failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

@router.get("/debug", summary="Debug environment configuration")
def debug_environment():
    """Debug endpoint to check environment configuration."""
    import os
    from config import DB_PATH, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME
    
    return {
        "database_path": DB_PATH,
        "db_path_exists": os.path.exists(DB_PATH),
        "db_directory_exists": os.path.exists(os.path.dirname(DB_PATH)),
        "db_directory_writable": os.access(os.path.dirname(DB_PATH), os.W_OK) if os.path.exists(os.path.dirname(DB_PATH)) else False,
        "airtable_key_configured": bool(AIRTABLE_API_KEY),
        "airtable_base_configured": bool(AIRTABLE_BASE_ID),
        "airtable_table_name": AIRTABLE_TABLE_NAME,
        "environment_vars": {
            "DATABASE_PATH": os.getenv("DATABASE_PATH"),
            "AIRTABLE_API_KEY": "***" if AIRTABLE_API_KEY else None,
            "AIRTABLE_BASE_ID": AIRTABLE_BASE_ID,
            "AIRTABLE_TABLE_NAME": os.getenv("AIRTABLE_TABLE_NAME"),
        }
    }

@router.post("/update-full-sync", summary="Force full refresh synchronously")
def force_full_refresh_sync():
    """Force a full refresh (all records) synchronously to see real-time results."""
    try:
        start_time = datetime.now(timezone.utc)
        
        # Run cache refresh directly (not in background)
        result = intelligent_cache.refresh_full()
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Get updated status
        cache_status = intelligent_cache.get_status()
        
        return {
            "message": "Full cache refresh completed synchronously",
            "type": "full_refresh_sync",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "duration_seconds": duration,
            "result": result,
            "cache_status": cache_status
        }
        
    except Exception as e:
        import traceback
        return {
            "error": f"Cache refresh failed: {str(e)}",
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

@router.get("/scheduler-status", summary="Get cache scheduler status")
def get_scheduler_status():
    """Get detailed scheduler status and scheduling information."""
    try:
        from cache_scheduler import cache_scheduler
        return cache_scheduler.get_status()
    except Exception as e:
        return {
            "error": f"Scheduler not available: {str(e)}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

@router.get("/deployment-version", summary="Check deployment version")
def get_deployment_version():
    """Check which version of the code is deployed."""
    return {
        "version": "2025-07-26-new-cache-architecture-v3",
        "cache_table": "feedback_cache",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.get("/test-airtable", summary="Test direct Airtable connection")
def test_airtable_connection():
    """Test Airtable connection and see what data we're getting."""
    try:
        from airtable import fetch_all_records
        from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME
        
        # Test Airtable connection directly
        records = fetch_all_records(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        
        return {
            "success": True,
            "records_fetched": len(records),
            "sample_fields": list(records[0].get("fields", {}).keys()) if records else [],
            "sample_record_id": records[0]["id"] if records else None,
            "sample_created": records[0].get("fields", {}).get("Created") if records else None,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
    except Exception as e:
        import traceback
        return {
            "error": f"Airtable connection failed: {str(e)}",
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

@router.get("/semantic-analyzer-status", summary="Check semantic analyzer and team assignment status")
def get_semantic_analyzer_status():
    """Check semantic analyzer status and team assignment functionality."""
    try:
        from semantic_analyzer import semantic_analyzer
        
        # Get vectorization status
        vectorization_status = semantic_analyzer.get_vectorization_status()
        
        # Test team assignment on a sample record
        sample_issues = [
            {
                "id": "test1",
                "description": "User cannot log into Salesforce",
                "type": "Bug",
                "status": "New",
                "area_impacted": "Salesforce"
            }
        ]
        
        team_assignments = {}
        try:
            team_assignments = semantic_analyzer.assign_teams_to_issues(sample_issues)
        except Exception as team_error:
            team_assignments = {"error": str(team_error)}
        
        return {
            "semantic_analyzer_available": True,
            "vectorization_status": vectorization_status,
            "sample_team_assignment": team_assignments,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
    except Exception as e:
        import traceback
        return {
            "semantic_analyzer_available": False,
            "error": f"Semantic analyzer failed: {str(e)}",
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }