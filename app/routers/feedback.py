from fastapi import APIRouter, Query
from typing import Optional
import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from parse_notes import parse_notes
except ImportError:
    # Fallback if import fails
    def parse_notes(notes):
        return "Unknown", "Unknown", notes or "No details available"

router = APIRouter()
# Import DB_PATH from config
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH

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
def get_feedback(team: str = None, priority: str = None, environment: str = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = "SELECT id, initial_description, notes, priority, team_routed, environment, area_impacted, created FROM feedback"
        filters = []
        params = []

        if team:
            filters.append("team_routed = ?")
            params.append(team)
        if priority:
            filters.append("priority = ?")
            params.append(priority)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        # Return empty list if database doesn't exist or other error
        return []

    results = []
    for r in rows:
        record_id, initial_description, notes, priority_val, team_routed, env_field, area_field, created_date = r
        
        # Use the description logic to get the appropriate description
        description = get_description(initial_description, notes)
        
        results.append({
            "id": record_id,
            "description": description,
            "priority": priority_val,
            "team": team_routed or "Unassigned",
            "environment": env_field or "Unknown",
            "system_impacted": area_field or "Unknown",
            "created": created_date or ""
        })

    return results

@router.get("/{feedback_id}", summary="Get a single feedback record by ID")
def get_feedback_by_id(feedback_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id, initial_description, priority, team_routed, environment, 
            area_impacted, created, notes, status, resolution_notes,
            type_of_report, triage_rep, related_imt, week, source
        FROM feedback
        WHERE id = ?
    """, (feedback_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Map the database columns to response fields
    initial_description = row[1]
    notes = row[7]
    
    return {
        "id": row[0],
        "initial_description": initial_description,
        "priority": row[2],
        "team_routed": row[3],
        "environment": row[4],
        "area_impacted": row[5],
        "created": row[6],
        "notes": notes,
        "status": row[8],
        "resolution_notes": row[9],
        "type_of_report": row[10],
        "triage_rep": row[11],
        "related_imt": row[12],
        "week": row[13],
        "source": row[14],
        "description": get_description(initial_description, notes)  # Computed field using logic
    }