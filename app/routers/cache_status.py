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