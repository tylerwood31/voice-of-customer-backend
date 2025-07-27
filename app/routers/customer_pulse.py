from fastapi import APIRouter, BackgroundTasks
import sqlite3
import json
from collections import Counter
from datetime import datetime

router = APIRouter()
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH

@router.get("/", summary="Get customer pulse analytics")
def get_customer_pulse(background_tasks: BackgroundTasks):
    """Get aggregated analytics on customer feedback patterns."""
    
    # Get data from original database
    feedback_data = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, created, priority, environment, area_impacted, 
                   status, notes, team_routed
            FROM feedback
        """)
        rows = cursor.fetchall()
        
        for row in rows:
            try:
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
                
                feedback_data.append({
                    "id": row['id'],
                    "description": row['notes'] or "",
                    "priority": priority,
                    "team": row['team_routed'] or "Unassigned",
                    "environment": row['environment'] or "Unknown",
                    "area_impacted": row['area_impacted'] or "Unknown",
                    "created": row['created'] or "",
                    "status": row['status'] or "New"
                })
            except Exception as e:
                print(f"Error parsing record: {e}")
                continue
        
        conn.close()
    except Exception as e:
        print(f"Error fetching feedback data: {e}")
    
    # Convert to tuple format for existing analytics logic
    records = []
    for record in feedback_data:
        records.append((
            record.get("id", ""),
            record.get("description", ""),
            record.get("priority", "Medium"),
            record.get("environment", "Unknown"),
            record.get("created", ""),
            record.get("status", "Unknown")
        ))
    
    # Basic analytics
    total_records = len(records)
    
    # Priority breakdown
    priority_counts = Counter([r[2] for r in records])
    
    # Environment breakdown
    environment_counts = Counter([r[3] for r in records])
    
    # Status breakdown
    status_counts = Counter([r[5] for r in records])
    
    # Trends (simplified - count by month)
    monthly_counts = {}
    for record in records:
        try:
            # Parse the created date
            created_str = record[4]
            if created_str:
                # Handle various date formats
                if "T" in created_str:
                    date_part = created_str.split("T")[0]
                else:
                    date_part = created_str.split(" ")[0]
                
                # Extract year-month
                if "-" in date_part:
                    parts = date_part.split("-")
                    if len(parts) >= 2:
                        year_month = f"{parts[0]}-{parts[1]}"
                        monthly_counts[year_month] = monthly_counts.get(year_month, 0) + 1
        except:
            continue
    
    # Sort monthly counts
    sorted_months = sorted(monthly_counts.items())
    
    # Calculate trend
    if len(sorted_months) >= 2:
        last_month_count = sorted_months[-1][1]
        prev_month_count = sorted_months[-2][1] if sorted_months[-2][1] > 0 else 1
        trend_percentage = ((last_month_count - prev_month_count) / prev_month_count) * 100
    else:
        trend_percentage = 0
    
    # Get top issues by priority
    high_priority_issues = [r for r in records if r[2] == "High"][:5]
    
    return {
        "total_feedback": total_records,
        "priority_distribution": dict(priority_counts),
        "environment_distribution": dict(environment_counts),
        "status_distribution": dict(status_counts),
        "monthly_trends": {
            "data": sorted_months[-12:],  # Last 12 months
            "trend_percentage": round(trend_percentage, 1),
            "trend_direction": "up" if trend_percentage > 0 else "down" if trend_percentage < 0 else "stable"
        },
        "high_priority_issues": [
            {
                "id": issue[0],
                "description": issue[1][:100] + "..." if len(issue[1]) > 100 else issue[1],
                "environment": issue[3],
                "created": issue[4]
            }
            for issue in high_priority_issues
        ],
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    }