from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import sqlite3
import sys
import os
from datetime import datetime

router = APIRouter()

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH
from team_assignment_service import team_service

def get_db_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_description(row: sqlite3.Row) -> str:
    """
    Get the appropriate description field with enhanced logic.
    Tries multiple fields in priority order.
    """
    # Try different potential description fields in order of preference
    description_fields = [
        'notes',
        'initial_description',
        'resolution_notes'
    ]
    
    for field in description_fields:
        try:
            value = row[field]
            if value and str(value).strip() and str(value).strip() not in ['', 'N/A', 'None']:
                return str(value).strip()
        except (IndexError, KeyError):
            continue
    
    return "No description provided"

def parse_area_impacted(area_value: Any) -> str:
    """Parse area impacted value handling various formats"""
    if not area_value or str(area_value).strip() in ['', 'None', 'null']:
        return "Unknown"
    
    # Handle string values
    area_str = str(area_value).strip()
    
    # Handle list-like strings (e.g., "['Salesforce']")
    if area_str.startswith('[') and area_str.endswith(']'):
        try:
            # Remove brackets and quotes
            area_str = area_str.strip('[]')
            area_str = area_str.replace("'", "").replace('"', '')
            # Split by comma and clean
            parts = [p.strip() for p in area_str.split(',') if p.strip()]
            if parts:
                return ', '.join(parts)
        except:
            pass
    
    return area_str if area_str else "Unknown"

@router.get("/", summary="Get feedback with optional filters")
def get_feedback(
    team: Optional[str] = None, 
    priority: Optional[str] = None, 
    environment: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get feedback records directly from the database.
    Uses the original database schema with proper field mappings.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build query with optional filters
        query = """
            SELECT id, directory_link, created, week, initial_description, 
                   priority, notes, triage_rep, status, resolution_notes,
                   related_imt, related_imt_link, type_of_report, area_impacted,
                   environment, time_to_in_progress, time_from_in_progress_to_done,
                   time_from_reported_to_imt_review, time_from_imt_review_to_done,
                   time_from_report_to_resolution, source, team_routed
            FROM feedback
            WHERE 1=1
        """
        
        params = []
        
        if team:
            query += " AND team_routed = ?"
            params.append(team)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority)
            
        if environment:
            query += " AND environment = ?"
            params.append(environment)
        
        query += " ORDER BY created DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to list of dicts with proper field mappings
        results = []
        for row in rows:
            # Parse area impacted
            area_impacted = parse_area_impacted(row['area_impacted'])
            
            # Get team assignment using the service (or use existing if valid)
            existing_team = row['team_routed']
            if existing_team and existing_team != 'Unassigned' and existing_team != 'Triage':
                assigned_team = existing_team
            else:
                # Use enhanced team assignment service
                assigned_team = team_service.assign_team(
                    area_impacted=area_impacted,
                    description=get_description(row),
                    type_of_issue=row['type_of_report'] or ''
                )
            
            # Map priority (handle numeric or string values)
            priority_value = row['priority']
            if str(priority_value) == '1':
                priority = 'High'
            elif str(priority_value) == '2':
                priority = 'Medium'
            elif str(priority_value) == '3':
                priority = 'Low'
            else:
                priority = priority_value or 'Medium'
            
            # Build the response record
            record = {
                "id": row['id'],
                "description": get_description(row),
                "priority": priority,
                "team": assigned_team,
                "environment": row['environment'] or 'Unknown',
                "area_impacted": area_impacted,
                "created": row['created'] or '',
                "week": row['week'] or 'N/A',
                "issue_number": '',  # Not in original schema
                "status": row['status'] or 'New',
                "reporter_email": '',  # Not in original schema
                "slack_thread": '',  # Not in original schema
                "type_of_issue": row['type_of_report'] or '',
                "type_of_report": row['type_of_report'] or 'N/A',
                "source": row['source'] or 'N/A',
                "triage_rep": row['triage_rep'] or 'N/A'
            }
            
            results.append(record)
        
        print(f"Returning {len(results)} feedback records from database")
        return results
        
    except Exception as e:
        print(f"Database query error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@router.get("/{feedback_id}", summary="Get a single feedback record by ID")
def get_feedback_by_id(feedback_id: str) -> Dict[str, Any]:
    """Get a single feedback record by ID from the database"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, directory_link, created, week, initial_description, 
                   priority, notes, triage_rep, status, resolution_notes,
                   related_imt, related_imt_link, type_of_report, area_impacted,
                   environment, time_to_in_progress, time_from_in_progress_to_done,
                   time_from_reported_to_imt_review, time_from_imt_review_to_done,
                   time_from_report_to_resolution, source, team_routed
            FROM feedback
            WHERE id = ?
        """, (feedback_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Parse area impacted
        area_impacted = parse_area_impacted(row['area_impacted'])
        
        # Get team assignment
        existing_team = row['team_routed']
        if existing_team and existing_team != 'Unassigned' and existing_team != 'Triage':
            assigned_team = existing_team
        else:
            assigned_team = team_service.assign_team(
                area_impacted=area_impacted,
                description=get_description(row),
                type_of_issue=row['type_of_report'] or ''
            )
        
        # Map priority
        priority_value = row['priority']
        if str(priority_value) == '1':
            priority = 'High'
        elif str(priority_value) == '2':
            priority = 'Medium'
        elif str(priority_value) == '3':
            priority = 'Low'
        else:
            priority = priority_value or 'Medium'
        
        return {
            "id": row['id'],
            "description": get_description(row),
            "priority": priority,
            "team": assigned_team,
            "environment": row['environment'] or 'Unknown',
            "area_impacted": area_impacted,
            "created": row['created'] or '',
            "week": row['week'] or 'N/A',
            "issue_number": '',
            "status": row['status'] or 'New',
            "reporter_email": '',
            "slack_thread": '',
            "type_of_issue": row['type_of_report'] or '',
            "type_of_report": row['type_of_report'] or 'N/A',
            "source": row['source'] or 'N/A',
            "triage_rep": row['triage_rep'] or 'N/A',
            "created_at": row['created'] or '',
            "modified_at": row['created'] or ''
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching feedback by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        conn.close()