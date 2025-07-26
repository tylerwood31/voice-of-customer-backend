from fastapi import APIRouter, Query, BackgroundTasks
from typing import Optional
import sqlite3
import sys
import os
from datetime import datetime

router = APIRouter()

# Import intelligent cache system
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from intelligent_cache import intelligent_cache
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
def get_feedback(
    background_tasks: BackgroundTasks,
    team: str = None, 
    priority: str = None, 
    environment: str = None
):
    """
    Get feedback records from local database cache (fast).
    Only triggers cache update on Sundays to maintain fast page loads.
    """
    
    # Only check for cache updates on Sundays to avoid performance issues
    # This ensures fast page loads throughout the week
    if intelligent_cache.should_check_for_updates():
        background_tasks.add_task(intelligent_cache.update_cache)
    
    # Always serve from local database (fast, no external API calls)
    filters = {}
    if team:
        filters["team"] = team
    if priority:
        filters["priority"] = priority
    if environment:
        filters["environment"] = environment
    
    results = intelligent_cache.get_feedback_from_database(filters)
    
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