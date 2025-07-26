from fastapi import APIRouter, BackgroundTasks
from datetime import datetime, timezone
import sys
import os

router = APIRouter()

# Import intelligent cache system
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from intelligent_cache import intelligent_cache

@router.get("/", summary="Get intelligent cache status and statistics")
def get_cache_status():
    """Get current intelligent cache status, schedule, and statistics."""
    now = datetime.now(timezone.utc)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_weekday = weekday_names[now.weekday()]
    
    # Get cache statistics from intelligent cache
    cache_stats = intelligent_cache.get_cache_stats()
    
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_weekday": current_weekday,
        "cache_type": "intelligent_incremental",
        "cache_status": cache_stats,
        "schedule": {
            "strategy": {
                "sunday": "Full refresh - ALL records from Airtable",
                "monday_to_saturday": "Incremental updates - NEW records only",
                "page_loads": "Always use local database (fast)"
            },
            "update_frequency": "Hourly check for new records",
            "is_full_refresh_day": intelligent_cache.should_do_full_refresh()
        },
        "actions": {
            "force_incremental": "/api/cache/update-incremental",
            "force_full_refresh": "/api/cache/update-full",
            "get_stats": "/api/cache/"
        }
    }

@router.post("/update-incremental", summary="Force incremental update")
def force_incremental_update(background_tasks: BackgroundTasks):
    """Force an incremental update (new records only)."""
    background_tasks.add_task(intelligent_cache.update_cache, False)
    return {
        "message": "Incremental cache update started in background",
        "type": "incremental",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.post("/update-full", summary="Force full refresh")
def force_full_refresh(background_tasks: BackgroundTasks):
    """Force a full refresh (all records)."""
    background_tasks.add_task(intelligent_cache.update_cache, True)
    return {
        "message": "Full cache refresh started in background",
        "type": "full_refresh",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.get("/stats", summary="Get detailed cache statistics")
def get_detailed_stats():
    """Get detailed cache statistics."""
    cache_stats = intelligent_cache.get_cache_stats()
    jira_status = intelligent_cache.get_jira_vectorization_status()
    
    return {
        "cache": cache_stats,
        "jira_vectorization": jira_status
    }

@router.post("/vectorize-jira", summary="Vectorize Jira tickets")
def vectorize_jira_tickets(background_tasks: BackgroundTasks):
    """Start Jira ticket vectorization in background."""
    background_tasks.add_task(intelligent_cache.force_vectorize_jira)
    return {
        "message": "Jira vectorization started in background",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.get("/jira-status", summary="Get Jira vectorization status")
def get_jira_status():
    """Get current Jira vectorization status."""
    return intelligent_cache.get_jira_vectorization_status()

@router.get("/debug", summary="Debug environment configuration")
def debug_environment():
    """Debug endpoint to check environment configuration."""
    import os
    from config import DB_PATH, AIRTABLE_API_KEY, AIRTABLE_BASE_ID
    
    return {
        "database_path": DB_PATH,
        "db_path_exists": os.path.exists(DB_PATH),
        "db_directory_exists": os.path.exists(os.path.dirname(DB_PATH)),
        "db_directory_writable": os.access(os.path.dirname(DB_PATH), os.W_OK) if os.path.exists(os.path.dirname(DB_PATH)) else False,
        "airtable_key_configured": bool(AIRTABLE_API_KEY),
        "airtable_base_configured": bool(AIRTABLE_BASE_ID),
        "environment_vars": {
            "DATABASE_PATH": os.getenv("DATABASE_PATH"),
            "AIRTABLE_API_KEY": "***" if AIRTABLE_API_KEY else None,
            "AIRTABLE_BASE_ID": AIRTABLE_BASE_ID,
        }
    }

@router.post("/update-full-sync", summary="Force full refresh synchronously")
def force_full_refresh_sync():
    """Force a full refresh (all records) synchronously to see real-time results."""
    try:
        start_time = datetime.now(timezone.utc)
        
        # Run cache update directly (not in background)
        intelligent_cache.update_cache(True)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Get updated stats
        cache_stats = intelligent_cache.get_cache_stats()
        
        return {
            "message": "Full cache refresh completed synchronously",
            "type": "full_refresh_sync",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "duration_seconds": duration,
            "cache_stats": cache_stats
        }
        
    except Exception as e:
        import traceback
        return {
            "error": f"Cache refresh failed: {str(e)}",
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

@router.get("/test-airtable", summary="Test direct Airtable connection")
def test_airtable_connection():
    """Test Airtable connection and see what data we're getting."""
    try:
        # Test Airtable connection directly
        records = intelligent_cache.fetch_airtable_records()
        
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