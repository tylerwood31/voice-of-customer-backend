"""
Cache manager for Airtable data to improve performance
Smart caching strategy:
- Monday-Friday: Refresh every hour during business days
- Weekend: Single refresh Sunday 11:59 PM for Monday prep
- Fast page loads for PM navigation
"""
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME
from team_analyzer import analyze_team_batch

class AirtableCache:
    def __init__(self, cache_duration_minutes=10):
        self.cache_duration = cache_duration_minutes * 60  # Convert to seconds
        self.cache_data = None
        self.cache_timestamp = 0
        
    def get_cache_duration(self) -> int:
        """Get dynamic cache duration based on day of week and time"""
        now = datetime.now(timezone.utc)
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Monday-Friday (0-4): 1 hour cache
        if 0 <= weekday <= 4:
            return 3600  # 1 hour in seconds
        
        # Weekend (Saturday=5, Sunday=6): Long cache until Sunday night
        elif weekday == 5:  # Saturday
            # Cache until Sunday 11:59 PM
            return 24 * 3600 + 23 * 3600 + 59 * 60  # ~48 hours
        
        else:  # Sunday (6)
            # Check if it's close to midnight (11:59 PM)
            if now.hour == 23 and now.minute >= 59:
                return 60  # 1 minute - force refresh soon
            elif now.hour >= 23:
                return 300  # 5 minutes near midnight
            else:
                return 24 * 3600  # 24 hours until evening
        
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid using dynamic duration"""
        if self.cache_data is None:
            return False
            
        dynamic_duration = self.get_cache_duration()
        return (time.time() - self.cache_timestamp) < dynamic_duration
    
    def fetch_from_airtable(self) -> List[Dict[str, Any]]:
        """Fetch fresh data from Airtable"""
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return []
        
        try:
            url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
            headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
            
            all_records = []
            offset = None
            
            while True:
                params = {"pageSize": 100}
                if offset:
                    params["offset"] = offset
                    
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code != 200:
                    print(f"Airtable API error: {response.status_code}")
                    break
                    
                data = response.json()
                records = data.get("records", [])
                if not records:
                    break
                    
                all_records.extend(records)
                offset = data.get("offset")
                if not offset:
                    break
            
            # Map Airtable fields to our expected structure
            mapped_records = []
            
            # First pass: create records without team assignments
            initial_records = []
            for record in all_records:
                fields = record.get("fields", {})
                
                # Enhanced priority mapping
                priority_map = {1: "High", 2: "Medium", 3: "Low"}
                priority_num = fields.get("Priority", 3)
                priority = priority_map.get(priority_num, "Medium")
                
                # Prepare data for OpenAI team analysis
                status = fields.get("Status", "New")
                issue_type = fields.get("Type of Issue", "")
                description = fields.get("Notes", "")
                
                # Environment mapping - handle both direct value and fallback to CW 2.0 Bug field
                environment = fields.get("Environment")
                if not environment:
                    # Fallback to CW 2.0 Bug field logic if Environment is empty
                    is_cw2 = fields.get("CW 2.0 Bug", False)
                    environment = "CW 2.0" if is_cw2 else "CW 1.0"
                
                # System impacted mapping - handle Area Impacted as array or string
                area_impacted_raw = fields.get("Area Impacted")
                if isinstance(area_impacted_raw, list) and area_impacted_raw:
                    area_impacted = area_impacted_raw[0]  # Take first item from array
                elif isinstance(area_impacted_raw, str):
                    area_impacted = area_impacted_raw
                else:
                    area_impacted = "Unknown"
                
                # Store initial record data for team analysis
                initial_record = {
                    "id": record["id"],
                    "description": description,
                    "type": issue_type,
                    "status": status,
                    "area_impacted": area_impacted,
                    "fields": fields,
                    "priority": priority,
                    "environment": environment
                }
                initial_records.append(initial_record)
            
            # Second pass: Analyze teams with Jira matching (temporarily disabled for performance)
            print(f"Temporarily using fallback team assignment for {len(initial_records)} records...")
            # team_assignments = analyze_team_batch(initial_records)
            team_assignments = {record["id"]: "Triage" for record in initial_records}
            
            # Third pass: Build final mapped records with AI team assignments
            for initial_record in initial_records:
                fields = initial_record["fields"]
                ai_team = team_assignments.get(initial_record["id"], "Triage")
                
                mapped_record = {
                    "id": initial_record["id"],
                    "initial_description": fields.get("Notes", ""),
                    "notes": fields.get("Notes", ""),
                    "priority": initial_record["priority"],
                    "team_routed": ai_team,  # Use OpenAI-determined team
                    "environment": initial_record["environment"],
                    "area_impacted": initial_record["area_impacted"],
                    "created": fields.get("Created", fields.get("Reported On", "")),
                    "issue_number": fields.get("Issue", ""),
                    "status": initial_record["status"],
                    "reporter_email": fields.get("User Profile Email", ""),
                    "slack_thread": fields.get("Slack Thread Link", ""),
                    "type_of_issue": fields.get("Type of Issue", ""),
                    "triage_rep": fields.get("Triage Rep", "")
                }
                mapped_records.append(mapped_record)
                
            return mapped_records
            
        except Exception as e:
            print(f"Error fetching Airtable data: {e}")
            return []
    
    def get_data(self, force_refresh=False) -> List[Dict[str, Any]]:
        """Get data from cache or fetch fresh if needed"""
        now = datetime.now(timezone.utc)
        weekday = now.weekday()
        
        if force_refresh or not self.is_cache_valid():
            cache_reason = "forced" if force_refresh else "expired"
            schedule_info = self._get_schedule_info()
            print(f"Fetching fresh data from Airtable ({cache_reason})...")
            print(f"Cache schedule: {schedule_info}")
            
            self.cache_data = self.fetch_from_airtable()
            self.cache_timestamp = time.time()
            print(f"Cached {len(self.cache_data)} records at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        else:
            cache_age_minutes = (time.time() - self.cache_timestamp) / 60
            print(f"Using cached data ({len(self.cache_data)} records, {cache_age_minutes:.1f}min old)")
            
        return self.cache_data or []
    
    def _get_schedule_info(self) -> str:
        """Get human-readable cache schedule info"""
        now = datetime.now(timezone.utc)
        weekday = now.weekday()
        
        if 0 <= weekday <= 4:
            return "Weekday: 1-hour refresh cycle"
        elif weekday == 5:
            return "Saturday: Cache until Sunday 11:59 PM"
        else:
            if now.hour >= 23:
                return "Sunday evening: Preparing Monday refresh"
            else:
                return "Sunday: Cache until 11:59 PM refresh"
    
    def invalidate_cache(self):
        """Force cache invalidation"""
        self.cache_data = None
        self.cache_timestamp = 0

# Global cache instance
airtable_cache = AirtableCache(cache_duration_minutes=10)