from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional
import sqlite3
import sys
import os
import json
from datetime import datetime, timezone

router = APIRouter()

# Import new cache system
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
import intelligent_cache
from db_connection import db_conn
from semantic_analyzer import semantic_analyzer


def get_team_assignment(description: str, area_impacted: str, type_of_issue: str) -> str:
    \"\"\"
    Assign team based on semantic analysis with area-based fallback.
    \"\"\"
    try:
        # Create issue dictionary for semantic analyzer
        issue = {
            \"id\": \"temp\",
            \"description\": description or \"\",
            \"area_impacted\": area_impacted or \"\",
            \"type\": type_of_issue or \"\",
            \"status\": \"New\"
        }
        
        # Use semantic analyzer to assign team
        team_assignments = semantic_analyzer.assign_teams_to_issues([issue])
        assigned_team = team_assignments.get(\"temp\", \"Unassigned\")
        
        # If semantic assignment failed or returned generic result, use area-based fallback
        if assigned_team in [\"Triage\", \"Unassigned\"] and area_impacted:
            area_lower = area_impacted.lower()
            if \"salesforce\" in area_lower:
                return \"Salesforce Team\"
            elif \"billing\" in area_lower or \"payment\" in area_lower:
                return \"Billing Team\"
            elif \"underwriting\" in area_lower:
                return \"Underwriting Team\"
            elif \"claims\" in area_lower:
                return \"Claims Team\"
            elif \"portal\" in area_lower or \"dashboard\" in area_lower:
                return \"Portal Team\"
        
        return assigned_team
        
    except Exception as e:
        print(f\"Team assignment error: {e}\")
        # Fallback to area-based assignment
        if area_impacted:
            area_lower = area_impacted.lower()
            if \"salesforce\" in area_lower:
                return \"Salesforce Team\"
            elif \"billing\" in area_lower or \"payment\" in area_lower:
                return \"Billing Team\"
            elif \"underwriting\" in area_lower:
                return \"Underwriting Team\"
            elif \"claims\" in area_lower:
                return \"Claims Team\"
            elif \"portal\" in area_lower or \"dashboard\" in area_lower:
                return \"Portal Team\"
        
        return \"Unassigned\"

def get_description(initial_description: str, notes: str) -> str:
    """
    Get the appropriate description field based on data evolution.
    Starting around May 23rd, InitialDescription became the primary field.
    Before that, Notes was used.
    
    Logic: If InitialDescription is blank, use Notes field. 
    If both fields blank, return "No description".
    """
    # For now, just use notes field as the primary description
    # Could be enhanced later to combine multiple description sources
    if notes and notes.strip():
        return notes.strip()
    else:
        return "No description provided"

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
                    
                    # Use semantic team assignment with area-based fallback
                    assigned_team = get_team_assignment(
                        description=fields.get("Notes", ""),
                        area_impacted=area_impacted,
                        type_of_issue=fields.get("Type of Issue", "")
                    )
                    
                    # Calculate week (Monday of the created date)
                    created_date = fields.get("Created", fields.get("Reported On", ""))
                    week_start = "N/A"
                    if created_date:
                        try:
                            # Parse the date and find the Monday of that week
                            if 'T' in created_date:
                                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                            else:
                                dt = datetime.fromisoformat(created_date)
                            # Find Monday of that week (weekday 0 = Monday)
                            days_since_monday = dt.weekday()
                            from datetime import timedelta
                            monday = dt - timedelta(days=days_since_monday)
                            week_start = monday.strftime("%Y-%m-%d")
                        except:
                            week_start = "N/A"
                    
                    record = {
                        "id": row[0],
                        "description": get_description(fields.get("Notes", ""), fields.get("Resolution Notes", "")),
                        "priority": mapped_priority,
                        "team": assigned_team,
                        "environment": environment_val,
                        "area_impacted": area_impacted,
                        "created": created_date,
                        "week": week_start,
                        "issue_number": fields.get("Issue", ""),
                        "status": fields.get("Status", "New"),
                        "reporter_email": fields.get("User Profile Email", ""),
                        "slack_thread": fields.get("Slack Thread Link", ""),
                        "type_of_issue": fields.get("Type of Issue", ""),
                        "type_of_report": fields.get("Type of Issue", "N/A"),
                        "source": fields.get("Source", "N/A"),
                        "triage_rep": fields.get("Triage Rep", "N/A")
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
            
            # Use semantic team assignment with area-based fallback
            assigned_team = get_team_assignment(
                description=fields.get("Notes", ""),
                area_impacted=area_impacted,
                type_of_issue=fields.get("Type of Issue", "")
            )
            
            # Calculate week (Monday of the created date)
            created_date = fields.get("Created", fields.get("Reported On", ""))
            week_start = "N/A"
            if created_date:
                try:
                    # Parse the date and find the Monday of that week
                    if 'T' in created_date:
                        dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(created_date)
                    # Find Monday of that week (weekday 0 = Monday)
                    days_since_monday = dt.weekday()
                    from datetime import timedelta
                    monday = dt - timedelta(days=days_since_monday)
                    week_start = monday.strftime("%Y-%m-%d")
                except:
                    week_start = "N/A"
            
            return {
                "id": row[0],
                "description": get_description(fields.get("Notes", ""), fields.get("Resolution Notes", "")),
                "priority": mapped_priority,
                "team": assigned_team,
                "environment": environment_val,
                "area_impacted": area_impacted,
                "created": created_date,
                "week": week_start,
                "issue_number": fields.get("Issue", ""),
                "status": fields.get("Status", "New"),
                "reporter_email": fields.get("User Profile Email", ""),
                "slack_thread": fields.get("Slack Thread Link", ""),
                "type_of_issue": fields.get("Type of Issue", ""),
                "type_of_report": fields.get("Type of Issue", "N/A"),
                "source": fields.get("Source", "N/A"),
                "triage_rep": fields.get("Triage Rep", "N/A"),
                "created_at": row[2],
                "modified_at": row[3]
            }
            
    except Exception as e:
        print(f"Error fetching feedback by ID: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Internal server error")