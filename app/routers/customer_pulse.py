from fastapi import APIRouter, BackgroundTasks
import sqlite3
import json
from collections import Counter
from datetime import datetime

router = APIRouter()
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from db_connection import db_conn

@router.get("/", summary="Get customer pulse analytics")
def get_customer_pulse(background_tasks: BackgroundTasks):
    """Get aggregated analytics on customer feedback patterns."""
    
    # Get data from new cache system
    feedback_data = []
    try:
        with db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, fields_json FROM feedback_cache")
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    fields = json.loads(row[1])
                    # Map fields to expected format
                    priority_map = {1: "High", 2: "Medium", 3: "Low"}
                    priority_num = fields.get("Priority", 3)
                    priority = priority_map.get(priority_num, "Medium")
                    
                    environment = fields.get("Environment", "")
                    if not environment:
                        is_cw2 = fields.get("CW 2.0 Bug", False)
                        environment = "CW 2.0" if is_cw2 else "CW 1.0"
                    
                    area_impacted_raw = fields.get("Area Impacted")
                    if isinstance(area_impacted_raw, list) and area_impacted_raw:
                        area_impacted = area_impacted_raw[0]
                    elif isinstance(area_impacted_raw, str):
                        area_impacted = area_impacted_raw
                    else:
                        area_impacted = "Unknown"
                    
                    feedback_data.append({
                        "id": row[0],
                        "description": fields.get("Notes", ""),
                        "priority": priority,
                        "team": "Triage",
                        "environment": environment,
                        "area_impacted": area_impacted,
                        "created": fields.get("Created", fields.get("Reported On", "")),
                        "status": fields.get("Status", "New")
                    })
                except Exception as e:
                    print(f"Error parsing record {row[0]}: {e}")
                    continue
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