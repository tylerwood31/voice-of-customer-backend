from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional
import sqlite3
import sys
import os
import json
from datetime import datetime

router = APIRouter()

# Import new cache system
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
import intelligent_cache
from db_connection import db_conn


def get_description(initial_description: str, notes: str) -> str:
    """
    Get the appropriate description field based on data evolution.
    Starting around May 23rd, InitialDescription became the primary field.
    Before that, Notes was used.
    
    Logic: If InitialDescription is blank, use Notes field. 
    If both fields blank, return "No description".
    """
    if initial_description and initial_description.strip():
        return initial_description.strip()
    elif notes and notes.strip():
        return notes.strip()
    else:
        return "No description"

@router.get("/", summary="Get feedback with optional filters")
def get_feedback(
    team: str = None, 
    priority: str = None, 
    environment: str = None
):
    """
    Get feedback records from local database cache (fast).
    Uses the new simplified JSON storage format.
    """
    
    try:
        with db_conn() as conn:
            # Build query with optional filters
            query = "SELECT id, fields_json FROM feedback_cache"
            where_clauses = []
            params = []
            
            # For the new JSON format, we'll filter in Python since the fields are in JSON
            # This is fine for reasonable dataset sizes
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            
            # Convert to our response format
            results = []
            for row in rows:
                try:
                    fields = json.loads(row[1])
                    
                    # Map fields from Airtable format to our API format
                    # Priority mapping
                    priority_map = {1: "High", 2: "Medium", 3: "Low"}
                    priority_num = fields.get("Priority", 3)
                    mapped_priority = priority_map.get(priority_num, "Medium")
                    
                    # Environment mapping
                    environment_val = fields.get("Environment")
                    if not environment_val:
                        is_cw2 = fields.get("CW 2.0 Bug", False)
                        environment_val = "CW 2.0" if is_cw2 else "CW 1.0"
                    
                    # Area impacted mapping
                    area_impacted_raw = fields.get("Area Impacted")
                    if isinstance(area_impacted_raw, list) and area_impacted_raw:
                        area_impacted = area_impacted_raw[0]
                    elif isinstance(area_impacted_raw, str):
                        area_impacted = area_impacted_raw
                    else:
                        area_impacted = "Unknown"
                    
                    # Simple area-based team assignment
                    if area_impacted and "salesforce" in area_impacted.lower():
                        assigned_team = "Salesforce Team"
                    elif area_impacted and ("billing" in area_impacted.lower() or "payment" in area_impacted.lower()):
                        assigned_team = "Billing Team"
                    elif area_impacted and "underwriting" in area_impacted.lower():
                        assigned_team = "Underwriting Team"
                    elif area_impacted and "claims" in area_impacted.lower():
                        assigned_team = "Claims Team"
                    elif area_impacted and ("portal" in area_impacted.lower() or "dashboard" in area_impacted.lower()):
                        assigned_team = "Portal Team"
                    else:
                        assigned_team = "Triage"
                    
                    record = {
                        "id": row[0],
                        "description": fields.get("Notes", ""),
                        "priority": mapped_priority,
                        "team": assigned_team,
                        "environment": environment_val,
                        "area_impacted": area_impacted,
                        "created": fields.get("Created", fields.get("Reported On", "")),
                        "issue_number": fields.get("Issue", ""),
                        "status": fields.get("Status", "New"),
                        "reporter_email": fields.get("User Profile Email", ""),
                        "slack_thread": fields.get("Slack Thread Link", ""),
                        "type_of_issue": fields.get("Type of Issue", ""),
                        "triage_rep": fields.get("Triage Rep", "")
                    }
                    
                    # Apply filters
                    if team and record["team"] != team:
                        continue
                    if priority and record["priority"] != priority:
                        continue
                    if environment and record["environment"] != environment:
                        continue
                    
                    results.append(record)
                    
                except Exception as e:
                    print(f"Error parsing record {row[0]}: {e}")
                    continue
            
            print(f"Returning {len(results)} feedback records")
            return results
            
    except Exception as e:
        print(f"Database query error: {e}")
        import traceback
        traceback.print_exc()
        return []

@router.get("/{feedback_id}", summary="Get a single feedback record by ID")
def get_feedback_by_id(feedback_id: str):
    try:
        with db_conn() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, fields_json, created_at, modified_at
                FROM feedback_cache
                WHERE id = ?
            """, (feedback_id,))
            
            row = cursor.fetchone()
            
            if not row:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Feedback not found")
            
            # Parse the JSON fields
            fields = json.loads(row[1])
            
            # Map fields from Airtable format to our API format
            priority_map = {1: "High", 2: "Medium", 3: "Low"}
            priority_num = fields.get("Priority", 3)
            mapped_priority = priority_map.get(priority_num, "Medium")
            
            environment_val = fields.get("Environment")
            if not environment_val:
                is_cw2 = fields.get("CW 2.0 Bug", False)
                environment_val = "CW 2.0" if is_cw2 else "CW 1.0"
            
            area_impacted_raw = fields.get("Area Impacted")
            if isinstance(area_impacted_raw, list) and area_impacted_raw:
                area_impacted = area_impacted_raw[0]
            elif isinstance(area_impacted_raw, str):
                area_impacted = area_impacted_raw
            else:
                area_impacted = "Unknown"
            
            # Simple area-based team assignment
            if area_impacted and "salesforce" in area_impacted.lower():
                assigned_team = "Salesforce Team"
            elif area_impacted and ("billing" in area_impacted.lower() or "payment" in area_impacted.lower()):
                assigned_team = "Billing Team"
            elif area_impacted and "underwriting" in area_impacted.lower():
                assigned_team = "Underwriting Team"
            elif area_impacted and "claims" in area_impacted.lower():
                assigned_team = "Claims Team"
            elif area_impacted and ("portal" in area_impacted.lower() or "dashboard" in area_impacted.lower()):
                assigned_team = "Portal Team"
            else:
                assigned_team = "Triage"
            
            return {
                "id": row[0],
                "description": fields.get("Notes", ""),
                "priority": mapped_priority,
                "team": assigned_team,
                "environment": environment_val,
                "area_impacted": area_impacted,
                "created": fields.get("Created", fields.get("Reported On", "")),
                "issue_number": fields.get("Issue", ""),
                "status": fields.get("Status", "New"),
                "reporter_email": fields.get("User Profile Email", ""),
                "slack_thread": fields.get("Slack Thread Link", ""),
                "type_of_issue": fields.get("Type of Issue", ""),
                "triage_rep": fields.get("Triage Rep", ""),
                "created_at": row[2],
                "modified_at": row[3]
            }
            
    except Exception as e:
        print(f"Error fetching feedback by ID: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Internal server error")