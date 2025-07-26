from fastapi import APIRouter
import sqlite3
import requests
from collections import Counter
from datetime import datetime

router = APIRouter()
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

# Import the fetch function from feedback router
sys.path.append(os.path.join(os.path.dirname(__file__)))
try:
    from feedback import fetch_airtable_data
except ImportError:
    def fetch_airtable_data():
        return []

@router.get("/", summary="Get customer pulse analytics")
def get_customer_pulse():
    """Get aggregated analytics on customer feedback patterns."""
    # Try to get data from Airtable first
    airtable_data = fetch_airtable_data()
    
    if airtable_data:
        # Convert Airtable data to the format expected by the rest of the function
        records = []
        for record in airtable_data:
            records.append((
                record.get("id", ""),
                record.get("initial_description", ""),
                record.get("priority", "Medium"),
                record.get("environment", "Unknown"),
                record.get("area_impacted", "Bug"),
                record.get("team_routed", "Triage"),
                record.get("created", "")
            ))
    else:
        # Fallback to SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Fetch all feedback records with relevant fields
            cursor.execute("""
                SELECT id, initial_description, priority, environment, 
                       area_impacted, team_routed, created 
                FROM feedback
            """)
            
            records = cursor.fetchall()
            conn.close()
        except Exception as e:
            # Return empty data structure if database doesn't exist
            records = []
    
    # Initialize counters
    environments = Counter()
    systems = Counter()
    teams = Counter()
    priorities = Counter()
    recent_high_priority = []
    all_feedback = []
    
    for record in records:
        record_id, description, priority, environment, area_impacted, team_routed, created = record
        
        # Count environments & systems
        env = environment or "Unknown"
        sys = area_impacted or "Unknown" 
        team = team_routed or "Unassigned"
        
        environments[env] += 1
        systems[sys] += 1
        teams[team] += 1
        
        # Count priorities
        if priority:
            priorities[f"Priority {priority}"] += 1
        else:
            priorities["No Priority"] += 1
        
        # Create feedback item
        feedback_item = {
            "id": record_id,
            "description": (description or "No description")[:100] + "..." if description and len(description) > 100 else (description or "No description"),
            "priority": priority or "N/A",
            "environment": env,
            "system": sys,
            "team": team,
            "created": created
        }
        
        # Add to all feedback
        all_feedback.append(feedback_item)
            
        # Track high priority items (check for "High" or numeric priority)
        try:
            if priority and (priority.lower() == "high" or (priority.isdigit() and int(priority) <= 1)):
                recent_high_priority.append(feedback_item)
        except:
            # If priority conversion fails, skip high priority check
            pass
    
    # Sort high priority by date (most recent first)
    recent_high_priority.sort(key=lambda x: x["created"] or "", reverse=True)
    recent_high_priority = recent_high_priority[:10]  # Top 10 most recent high priority
    
    # Prepare breakdowns
    env_breakdown = [{"name": env, "count": count} for env, count in environments.most_common()]
    sys_breakdown = [{"name": sys, "count": count} for sys, count in systems.most_common()]
    team_breakdown = [{"name": team, "count": count} for team, count in teams.most_common()]
    priority_breakdown = [{"name": priority, "count": count} for priority, count in priorities.most_common()]
    
    # Calculate summary stats
    total_feedback = len(records)
    # Count high priority items (text or numeric)
    high_priority_count = 0
    for r in records:
        priority = r[2]
        try:
            if priority and (priority.lower() == "high" or (priority.isdigit() and int(priority) <= 1)):
                high_priority_count += 1
        except:
            pass
    
    assigned_count = len([r for r in records if r[5] and r[5] != "Unassigned"])
    
    return {
        "summary": {
            "total_feedback": total_feedback,
            "high_priority_count": high_priority_count,
            "assignment_rate": round((assigned_count / total_feedback) * 100, 1) if total_feedback > 0 else 0,
            "top_environment": environments.most_common(1)[0] if environments else ["Unknown", 0],
            "top_system": systems.most_common(1)[0] if systems else ["Unknown", 0],
            "top_team": teams.most_common(1)[0] if teams else ["Unassigned", 0]
        },
        "breakdowns": {
            "environments": env_breakdown,
            "systems_impacted": sys_breakdown,
            "teams": team_breakdown,
            "priorities": priority_breakdown
        },
        "recent_high_priority": recent_high_priority,
        "all_feedback": all_feedback
    }