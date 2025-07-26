"""
Cache refresh scheduler for Voice of Customer application
Handles automated cache refresh scheduling per requirements:
- Incremental updates: Hourly 9 AM - 6 PM EST, Monday-Friday  
- Full refresh: Sundays at 11:59 PM EST
"""
import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Optional
import intelligent_cache


class CacheScheduler:
    def __init__(self):
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start the cache scheduler in a background thread"""
        if self.running:
            print("⚠️ Cache scheduler already running")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        print("✅ Cache scheduler started")
        
    def stop(self):
        """Stop the cache scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("🛑 Cache scheduler stopped")
        
    def _scheduler_loop(self):
        """Main scheduler loop that runs in background thread"""
        print("🔄 Cache scheduler loop started")
        
        while self.running:
            try:
                now_utc = datetime.now(timezone.utc)
                # Convert to EST (UTC-5, or UTC-4 during daylight time)
                # For simplicity, using UTC-5 (EST standard time)
                est_offset_hours = -5
                now_est = now_utc.replace(hour=(now_utc.hour + est_offset_hours) % 24)
                
                if self._should_run_full_refresh(now_est):
                    self._run_full_refresh()
                elif self._should_run_incremental_refresh(now_est):
                    self._run_incremental_refresh()
                    
                # Sleep for 1 hour before next check
                time.sleep(3600)  # 3600 seconds = 1 hour
                
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                # Continue running even if there's an error
                time.sleep(300)  # Wait 5 minutes before retrying on error
                
    def _should_run_full_refresh(self, now_est: datetime) -> bool:
        """Check if it's time for full refresh (Sundays at 11:59 PM EST)"""
        # Sunday = 6 in Python weekday (Monday=0)
        return (now_est.weekday() == 6 and 
                now_est.hour == 23 and 
                now_est.minute == 59)
                
    def _should_run_incremental_refresh(self, now_est: datetime) -> bool:
        """Check if it's time for incremental refresh (9 AM - 6 PM EST, Mon-Fri, hourly)"""
        # Monday=0 to Friday=4
        is_weekday = now_est.weekday() < 5
        is_business_hours = 9 <= now_est.hour <= 18
        is_top_of_hour = now_est.minute == 0
        
        return is_weekday and is_business_hours and is_top_of_hour
        
    def _run_full_refresh(self):
        """Execute full cache refresh"""
        try:
            print("🔄 Starting scheduled full refresh...")
            result = intelligent_cache.refresh_full()
            total = result.get('total', 0)
            print(f"✅ Scheduled full refresh completed: {total} records")
        except Exception as e:
            print(f"❌ Scheduled full refresh failed: {e}")
            
    def _run_incremental_refresh(self):
        """Execute incremental cache refresh"""
        try:
            print("⚡ Starting scheduled incremental refresh...")
            status = intelligent_cache.get_status()
            since = status.get("last_update", "1970-01-01T00:00:00Z") if status else "1970-01-01T00:00:00Z"
            
            result = intelligent_cache.refresh_incremental(since)
            total = result.get('total', 0)
            print(f"✅ Scheduled incremental refresh completed: {total} new/updated records")
        except Exception as e:
            print(f"❌ Scheduled incremental refresh failed: {e}")
            
    def get_status(self) -> dict:
        """Get scheduler status information"""
        now_utc = datetime.now(timezone.utc)
        est_offset_hours = -5
        now_est = now_utc.replace(hour=(now_utc.hour + est_offset_hours) % 24)
        
        return {
            "running": self.running,
            "current_time_est": now_est.strftime("%Y-%m-%d %H:%M:%S EST"),
            "current_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "next_full_refresh": "Sundays at 11:59 PM EST",
            "next_incremental": "Hourly 9 AM - 6 PM EST, Monday-Friday",
            "schedule_details": {
                "full_refresh": "Sunday 23:59 EST",
                "incremental": "Mon-Fri 09:00-18:00 EST (hourly)"
            }
        }


# Global scheduler instance
cache_scheduler = CacheScheduler()