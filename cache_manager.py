"""
Cache manager for Airtable data to improve performance
"""
import json
import time
import requests
from typing import List, Dict, Any
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class AirtableCache:
    def __init__(self, cache_duration_minutes=10):
        self.cache_duration = cache_duration_minutes * 60  # Convert to seconds
        self.cache_data = None
        self.cache_timestamp = 0
        
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        return (
            self.cache_data is not None and 
            (time.time() - self.cache_timestamp) < self.cache_duration
        )
    
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
            for record in all_records:
                fields = record.get("fields", {})
                
                # Enhanced priority mapping
                priority_map = {1: "High", 2: "Medium", 3: "Low"}
                priority_num = fields.get("Priority", 3)
                priority = priority_map.get(priority_num, "Medium")
                
                # Enhanced team mapping based on status and type
                status = fields.get("Status", "New")
                issue_type = fields.get("Type of Issue", "")
                
                # More sophisticated team assignment
                if status == "Done":
                    team = "Engineering"
                elif status == "In Progress":
                    team = "Engineering" 
                elif "Reporting a Bug" in issue_type:
                    team = "Engineering"
                elif "Feature Request" in issue_type:
                    team = "Product"
                elif "Training" in issue_type:
                    team = "Support"
                else:
                    team = "Triage"
                
                # Enhanced environment mapping
                is_cw2 = fields.get("CW 2.0 Bug", False)
                environment = "CW 2.0" if is_cw2 else "CW 1.0"
                
                # Better system impacted mapping
                area_impacted = fields.get("Type of Issue", "Bug/Issue")
                if "Agent Portal" in fields.get("Notes", ""):
                    area_impacted = "Agent Portal"
                elif "Salesforce" in fields.get("Notes", ""):
                    area_impacted = "Salesforce"
                elif "Quote" in fields.get("Notes", ""):
                    area_impacted = "Quoting System"
                elif "Bind" in fields.get("Notes", ""):
                    area_impacted = "Binding System"
                elif "Upload" in fields.get("Notes", ""):
                    area_impacted = "File Upload"
                
                mapped_record = {
                    "id": record["id"],
                    "initial_description": fields.get("Notes", ""),
                    "notes": fields.get("Notes", ""),
                    "priority": priority,
                    "team_routed": team,
                    "environment": environment,
                    "area_impacted": area_impacted,
                    "created": fields.get("Created", fields.get("Reported On", "")),
                    "issue_number": fields.get("Issue", ""),
                    "status": status,
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
        if force_refresh or not self.is_cache_valid():
            print("Fetching fresh data from Airtable...")
            self.cache_data = self.fetch_from_airtable()
            self.cache_timestamp = time.time()
            print(f"Cached {len(self.cache_data)} records")
        else:
            print(f"Using cached data ({len(self.cache_data)} records)")
            
        return self.cache_data or []
    
    def invalidate_cache(self):
        """Force cache invalidation"""
        self.cache_data = None
        self.cache_timestamp = 0

# Global cache instance
airtable_cache = AirtableCache(cache_duration_minutes=10)