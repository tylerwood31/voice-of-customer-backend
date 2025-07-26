#!/usr/bin/env python3
"""
Intelligent incremental cache system for Voice of Customer
- Sunday: Full refresh of ALL records
- Monday-Saturday: Incremental updates (new records only)
- Page loads: Always use database (fast)
"""
import sqlite3
import requests
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from config import DB_PATH, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME
from database_manager import db_manager

class IntelligentCache:
    def __init__(self):
        self.db_path = DB_PATH
        self.last_update_check = 0
        self.update_frequency = 3600  # Check for updates every hour
        
    def should_do_full_refresh(self) -> bool:
        """Determine if we should do a full refresh (Sunday)"""
        now = datetime.now(timezone.utc)
        return now.weekday() == 6  # Sunday = 6
    
    def should_check_for_updates(self) -> bool:
        """Check if it's time to look for new records - only on Sundays for production performance"""
        # Only check for updates on Sundays to avoid performance issues
        return self.should_do_full_refresh()
    
    def get_last_update_timestamp(self) -> str:
        """Get the timestamp of the last update"""
        return db_manager.get_last_feedback_update()
    
    def fetch_airtable_records(self, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch records from Airtable.
        If since_timestamp provided, only fetch newer records.
        If None, fetch all records (full refresh).
        """
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            print("❌ Airtable credentials not configured")
            return []
        
        try:
            url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
            headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
            
            all_records = []
            offset = None
            
            while True:
                params = {"pageSize": 100}
                
                # Add filter for 2025 records and incremental updates
                filter_conditions = []
                
                # Always filter for 2025 records
                filter_conditions.append("YEAR({Created}) = 2025")
                
                # Add incremental filter if needed
                if since_timestamp and not self.should_do_full_refresh():
                    filter_conditions.append(f"OR({{Created}} > '{since_timestamp}', {{Last Modified Time}} > '{since_timestamp}')")
                
                if filter_conditions:
                    if len(filter_conditions) == 1:
                        params["filterByFormula"] = filter_conditions[0]
                    else:
                        params["filterByFormula"] = f"AND({', '.join(filter_conditions)})"
                
                if offset:
                    params["offset"] = offset
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    print(f"❌ Airtable API error: {response.status_code}")
                    break
                
                data = response.json()
                records = data.get("records", [])
                
                if not records:
                    break
                
                all_records.extend(records)
                offset = data.get("offset")
                
                if not offset:
                    break
            
            print(f"📥 Fetched {len(all_records)} records from Airtable")
            return all_records
            
        except Exception as e:
            print(f"❌ Error fetching Airtable data: {e}")
            return []
    
    def map_airtable_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Map Airtable record to our database format"""
        fields = record.get("fields", {})
        
        # Priority mapping
        priority_map = {1: "High", 2: "Medium", 3: "Low"}
        priority_num = fields.get("Priority", 3)
        priority = priority_map.get(priority_num, "Medium")
        
        # Environment mapping - handle both direct value and fallback
        environment = fields.get("Environment")
        if not environment:
            is_cw2 = fields.get("CW 2.0 Bug", False)
            environment = "CW 2.0" if is_cw2 else "CW 1.0"
        
        # System impacted mapping - handle array format
        area_impacted_raw = fields.get("Area Impacted")
        if isinstance(area_impacted_raw, list) and area_impacted_raw:
            area_impacted = area_impacted_raw[0]
        elif isinstance(area_impacted_raw, str):
            area_impacted = area_impacted_raw
        else:
            area_impacted = "Unknown"
        
        return {
            "id": record["id"],
            "initial_description": fields.get("Notes", ""),
            "notes": fields.get("Notes", ""),
            "priority": priority,
            "team_routed": "Triage",  # Will be updated by team analysis
            "environment": environment,
            "area_impacted": area_impacted,
            "created": fields.get("Created", fields.get("Reported On", "")),
            "issue_number": fields.get("Issue", ""),
            "status": fields.get("Status", "New"),
            "reporter_email": fields.get("User Profile Email", ""),
            "slack_thread": fields.get("Slack Thread Link", ""),
            "type_of_issue": fields.get("Type of Issue", ""),
            "triage_rep": fields.get("Triage Rep", "")
        }
    
    def store_records_in_database(self, records: List[Dict[str, Any]], is_full_refresh: bool = False):
        """Store mapped records in database"""
        if not records:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # If full refresh, clear existing data
            if is_full_refresh:
                cursor.execute("DELETE FROM feedback")
                print("🗑️ Cleared existing feedback records for full refresh")
            
            # Insert/update records
            inserted_count = 0
            updated_count = 0
            
            for record in records:
                # Check if record exists
                cursor.execute("SELECT id FROM feedback WHERE id = ?", (record["id"],))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing record
                    cursor.execute("""
                        UPDATE feedback SET
                            initial_description = ?,
                            notes = ?,
                            priority = ?,
                            team_routed = ?,
                            environment = ?,
                            area_impacted = ?,
                            created = ?,
                            issue_number = ?,
                            status = ?,
                            reporter_email = ?,
                            slack_thread = ?,
                            type_of_issue = ?,
                            triage_rep = ?,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        record["initial_description"], record["notes"], record["priority"],
                        record["team_routed"], record["environment"], record["area_impacted"],
                        record["created"], record["issue_number"], record["status"],
                        record["reporter_email"], record["slack_thread"], record["type_of_issue"],
                        record["triage_rep"], record["id"]
                    ))
                    updated_count += 1
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO feedback (
                            id, initial_description, notes, priority, team_routed,
                            environment, area_impacted, created, issue_number, status,
                            reporter_email, slack_thread, type_of_issue, triage_rep
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record["id"], record["initial_description"], record["notes"],
                        record["priority"], record["team_routed"], record["environment"],
                        record["area_impacted"], record["created"], record["issue_number"],
                        record["status"], record["reporter_email"], record["slack_thread"],
                        record["type_of_issue"], record["triage_rep"]
                    ))
                    inserted_count += 1
            
            # Update last update timestamp
            current_time = datetime.now(timezone.utc).isoformat()
            db_manager.update_last_feedback_timestamp(current_time)
            
            conn.commit()
            conn.close()
            
            print(f"💾 Database updated: {inserted_count} new, {updated_count} updated")
            
        except Exception as e:
            print(f"❌ Database storage error: {e}")
    
    def get_feedback_from_database(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get feedback records from database (fast local query)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First check if table exists and has data
            cursor.execute("SELECT COUNT(*) FROM feedback")
            total_count = cursor.fetchone()[0]
            print(f"📊 Database has {total_count} feedback records")
            
            # Build query with optional filters
            query = """
                SELECT id, initial_description, notes, priority, team_routed,
                       environment, area_impacted, created, issue_number, status,
                       reporter_email, slack_thread, type_of_issue, triage_rep
                FROM feedback
            """
            
            where_clauses = []
            params = []
            
            if filters:
                if filters.get("team"):
                    where_clauses.append("team_routed = ?")
                    params.append(filters["team"])
                
                if filters.get("priority"):
                    where_clauses.append("priority = ?")
                    params.append(filters["priority"])
                
                if filters.get("environment"):
                    where_clauses.append("environment = ?")
                    params.append(filters["environment"])
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY created DESC"
            
            print(f"🔍 Executing query: {query} with params: {params}")
            cursor.execute(query, params)
            rows = cursor.fetchall()
            print(f"📤 Query returned {len(rows)} rows")
            
            conn.close()
            
            # Convert to dict format
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "description": row[1] or row[2],  # Use initial_description or notes
                    "priority": row[3],
                    "team": row[4],
                    "environment": row[5],
                    "area_impacted": row[6],
                    "created": row[7],
                    "issue_number": row[8],
                    "status": row[9],
                    "reporter_email": row[10],
                    "slack_thread": row[11],
                    "type_of_issue": row[12],
                    "triage_rep": row[13]
                })
            
            print(f"✅ Returning {len(results)} formatted results")
            return results
            
        except Exception as e:
            print(f"❌ Database query error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def update_cache(self, force_full_refresh: bool = False):
        """
        Update cache intelligently:
        - Sunday OR force_full_refresh: Full refresh of all records
        - Other days: Incremental update (new records only)
        """
        self.last_update_check = time.time()
        
        is_full_refresh = force_full_refresh or self.should_do_full_refresh()
        
        if is_full_refresh:
            print("🔄 Starting FULL refresh (all records)")
            records = self.fetch_airtable_records()
        else:
            print("⚡ Starting INCREMENTAL update (new records only)")
            last_timestamp = self.get_last_update_timestamp()
            print(f"📅 Looking for records newer than: {last_timestamp}")
            records = self.fetch_airtable_records(since_timestamp=last_timestamp)
        
        if records:
            # Map records to our format
            mapped_records = [self.map_airtable_record(record) for record in records]
            
            # Store in database
            self.store_records_in_database(mapped_records, is_full_refresh)
            
            # Analyze new records for team assignment
            if is_full_refresh:
                print("⚗️ Skipping team analysis for full refresh (too many records)")
            else:
                self._analyze_teams_for_new_records(mapped_records)
            
            print(f"✅ Cache update completed: {len(mapped_records)} records processed")
        else:
            print("ℹ️ No new records found")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM feedback")
            total_count = cursor.fetchone()[0]
            
            # Get last update time
            last_update = self.get_last_update_timestamp()
            
            # Get records by environment
            cursor.execute("""
                SELECT environment, COUNT(*) 
                FROM feedback 
                GROUP BY environment
            """)
            env_stats = dict(cursor.fetchall())
            
            # Get records by team
            cursor.execute("""
                SELECT team_routed, COUNT(*) 
                FROM feedback 
                GROUP BY team_routed
            """)
            team_stats = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                "total_records": total_count,
                "last_update": last_update,
                "environment_distribution": env_stats,
                "team_distribution": team_stats,
                "next_check_in_minutes": max(0, (self.update_frequency - (time.time() - self.last_update_check)) / 60),
                "is_sunday": self.should_do_full_refresh()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_teams_for_new_records(self, records: List[Dict[str, Any]]):
        """Analyze team assignments for new records only"""
        if not records:
            return
        
        try:
            from team_analyzer import analyze_team_assignment
            
            print(f"🤖 Analyzing team assignments for {len(records)} new records...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            analyzed_count = 0
            for record in records:
                try:
                    # Analyze team assignment
                    team = analyze_team_assignment(
                        issue_description=record.get("initial_description", ""),
                        issue_type=record.get("type_of_issue", ""),
                        status=record.get("status", ""),
                        area_impacted=record.get("area_impacted", "")
                    )
                    
                    # Update team assignment in database
                    cursor.execute(
                        "UPDATE feedback SET team_routed = ? WHERE id = ?",
                        (team, record["id"])
                    )
                    
                    analyzed_count += 1
                    
                    if analyzed_count % 5 == 0:
                        print(f"📊 Analyzed {analyzed_count}/{len(records)} records")
                
                except Exception as e:
                    print(f"⚠️ Team analysis failed for record {record.get('id')}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ Team analysis completed: {analyzed_count} records processed")
            
        except Exception as e:
            print(f"❌ Team analysis batch failed: {e}")
    
    def force_vectorize_jira(self):
        """Force vectorization of Jira tickets"""
        try:
            from semantic_analyzer import semantic_analyzer
            return semantic_analyzer.vectorize_jira_tickets()
        except Exception as e:
            print(f"❌ Jira vectorization failed: {e}")
            return False
    
    def get_jira_vectorization_status(self):
        """Get Jira vectorization status"""
        try:
            from semantic_analyzer import semantic_analyzer
            return semantic_analyzer.get_vectorization_status()
        except Exception as e:
            return {"error": str(e)}

# Global cache instance
intelligent_cache = IntelligentCache()