from fastapi import APIRouter
from datetime import datetime, timezone
import sys
import os

router = APIRouter()

# Import cache manager
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from cache_manager import airtable_cache

@router.get("/", summary="Get cache status and statistics")
def get_cache_status():
    """Get current cache status, schedule, and statistics."""
    now = datetime.now(timezone.utc)
    
    # Get cache info
    has_data = airtable_cache.cache_data is not None
    record_count = len(airtable_cache.cache_data) if has_data else 0
    
    if has_data:
        cache_age_seconds = now.timestamp() - airtable_cache.cache_timestamp
        cache_age_minutes = cache_age_seconds / 60
        cache_timestamp = datetime.fromtimestamp(airtable_cache.cache_timestamp, timezone.utc)
    else:
        cache_age_seconds = 0
        cache_age_minutes = 0
        cache_timestamp = None
    
    # Get cache validity and duration
    is_valid = airtable_cache.is_cache_valid()
    current_duration = airtable_cache.get_cache_duration()
    schedule_info = airtable_cache._get_schedule_info()
    
    # Calculate next refresh time
    if has_data and is_valid:
        next_refresh = cache_timestamp.timestamp() + current_duration
        next_refresh_dt = datetime.fromtimestamp(next_refresh, timezone.utc)
        time_to_refresh = next_refresh - now.timestamp()
        time_to_refresh_minutes = time_to_refresh / 60
    else:
        next_refresh_dt = "Immediate (cache invalid)"
        time_to_refresh_minutes = 0
    
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_weekday = weekday_names[now.weekday()]
    
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_weekday": current_weekday,
        "cache_status": {
            "has_data": has_data,
            "is_valid": is_valid,
            "record_count": record_count,
            "last_updated": cache_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if cache_timestamp else None,
            "age_minutes": round(cache_age_minutes, 1),
            "next_refresh": next_refresh_dt.strftime("%Y-%m-%d %H:%M:%S UTC") if isinstance(next_refresh_dt, datetime) else next_refresh_dt,
            "time_to_refresh_minutes": round(time_to_refresh_minutes, 1) if time_to_refresh_minutes > 0 else 0
        },
        "schedule": {
            "current_schedule": schedule_info,
            "cache_duration_hours": round(current_duration / 3600, 2),
            "strategy": {
                "weekdays": "1-hour refresh cycle (Monday-Friday)",
                "saturday": "Cache until Sunday 11:59 PM",
                "sunday": "Cache until 11:59 PM, then refresh for Monday"
            }
        },
        "actions": {
            "force_refresh": "/api/cache/refresh",
            "invalidate": "/api/cache/invalidate"
        }
    }

@router.post("/refresh", summary="Force cache refresh")
def force_cache_refresh():
    """Force an immediate cache refresh."""
    data = airtable_cache.get_data(force_refresh=True)
    return {
        "message": "Cache refreshed successfully",
        "records_cached": len(data),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@router.post("/invalidate", summary="Invalidate cache")
def invalidate_cache():
    """Invalidate the current cache."""
    airtable_cache.invalidate_cache()
    return {
        "message": "Cache invalidated successfully",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }