from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import os
import sqlite3
from datetime import datetime

router = APIRouter()

@router.get("/test", summary="Test endpoint")
async def test_reports():
    """Simple test endpoint to verify reports router is working."""
    return {"message": "Reports API is working"}

@router.get("/environments", summary="Get available environments with response time data")
async def get_environments():
    """Get list of environments that have response time data in cache."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get unique environments from cache
        cursor.execute("SELECT DISTINCT environment FROM response_times_weighted ORDER BY environment")
        rows = cursor.fetchall()
        conn.close()
        
        environments = [row[0] for row in rows if row[0]]
        print(f"✅ Found {len(environments)} environments with response time data: {environments}")
        
        return {"environments": environments}
        
    except Exception as e:
        print(f"Error fetching environments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database configuration
DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

@router.get("/response-times-mock", summary="Get mock response times for testing")
async def get_response_times_mock():
    """Return mock data for testing while we debug the real endpoint."""
    return {
        "rows": [
            {
                "weekLabel": "2025-01-20",
                "count": 5,
                "timeToInProgressHoursAvg": 2.5,
                "timeInProgressToDoneHoursAvg": 16.0,
                "timeReportedToReferredHoursAvg": 1.0,
                "timeReferredToDoneHoursAvg": 12.0,
                "timeReportToResolutionHoursAvg": 18.5
            },
            {
                "weekLabel": "2025-01-27",
                "count": 3,
                "timeToInProgressHoursAvg": 3.0,
                "timeInProgressToDoneHoursAvg": 20.0,
                "timeReportedToReferredHoursAvg": 2.0,
                "timeReferredToDoneHoursAvg": 15.0,
                "timeReportToResolutionHoursAvg": 22.0
            }
        ],
        "weighted": {
            "weekLabel": "Weighted Average",
            "count": 8,
            "timeToInProgressHoursAvg": 2.7,
            "timeInProgressToDoneHoursAvg": 17.5,
            "timeReportedToReferredHoursAvg": 1.4,
            "timeReferredToDoneHoursAvg": 13.1,
            "timeReportToResolutionHoursAvg": 19.8
        }
    }

@router.get("/response-times", summary="Get cached average response times week over week")
async def get_response_times(environment: str = None):
    """Get response times data from cache (updated weekly on Sundays)."""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build query based on environment filter
        if environment and environment != 'All Environments':
            # Fetch weekly data for specific environment
            cursor.execute('''
                SELECT week_label, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
                       time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg
                FROM response_times_cache 
                WHERE environment = ?
                ORDER BY week_label
            ''', (environment,))
            
            weekly_rows = cursor.fetchall()
            
            # Fetch weighted averages for specific environment
            cursor.execute('''
                SELECT count, time_to_in_progress_avg, time_in_progress_to_done_avg,
                       time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg
                FROM response_times_weighted 
                WHERE environment = ?
            ''', (environment,))
            
            weighted_row = cursor.fetchone()
        else:
            # Aggregate data across all environments
            cursor.execute('''
                SELECT week_label, 
                       SUM(count) as total_count,
                       AVG(time_to_in_progress_avg) as avg_time_to_in_progress,
                       AVG(time_in_progress_to_done_avg) as avg_time_in_progress_to_done,
                       AVG(time_reported_to_referred_avg) as avg_time_reported_to_referred,
                       AVG(time_referred_to_done_avg) as avg_time_referred_to_done,
                       AVG(time_report_to_resolution_avg) as avg_time_report_to_resolution
                FROM response_times_cache 
                GROUP BY week_label
                ORDER BY week_label
            ''')
            
            weekly_rows = cursor.fetchall()
            
            # Calculate overall weighted averages across all environments
            cursor.execute('''
                SELECT SUM(count) as total_count,
                       AVG(time_to_in_progress_avg) as avg_time_to_in_progress,
                       AVG(time_in_progress_to_done_avg) as avg_time_in_progress_to_done,
                       AVG(time_reported_to_referred_avg) as avg_time_reported_to_referred,
                       AVG(time_referred_to_done_avg) as avg_time_referred_to_done,
                       AVG(time_report_to_resolution_avg) as avg_time_report_to_resolution
                FROM response_times_weighted
            ''')
            
            weighted_row = cursor.fetchone()
        
        conn.close()
        
        # If no cached data, return sample data starting from June 30, 2025
        if not weekly_rows:
            print(f"⚠️ No cached data found for environment: {environment or 'All Environments'}")
            return {
                'rows': [
                    {
                        'weekLabel': '2025-06-30',
                        'count': 8,
                        'timeToInProgressHoursAvg': 2.5,
                        'timeInProgressToDoneHoursAvg': 24.0,
                        'timeReportedToReferredHoursAvg': 1.5,
                        'timeReferredToDoneHoursAvg': 18.0,
                        'timeReportToResolutionHoursAvg': 26.5
                    },
                    {
                        'weekLabel': '2025-07-07',
                        'count': 12,
                        'timeToInProgressHoursAvg': 3.0,
                        'timeInProgressToDoneHoursAvg': 20.0,
                        'timeReportedToReferredHoursAvg': 2.0,
                        'timeReferredToDoneHoursAvg': 16.0,
                        'timeReportToResolutionHoursAvg': 23.0
                    },
                    {
                        'weekLabel': '2025-07-14',
                        'count': 15,
                        'timeToInProgressHoursAvg': 2.0,
                        'timeInProgressToDoneHoursAvg': 18.0,
                        'timeReportedToReferredHoursAvg': 1.0,
                        'timeReferredToDoneHoursAvg': 14.0,
                        'timeReportToResolutionHoursAvg': 20.0
                    },
                    {
                        'weekLabel': '2025-07-21',
                        'count': 10,
                        'timeToInProgressHoursAvg': 2.8,
                        'timeInProgressToDoneHoursAvg': 22.0,
                        'timeReportedToReferredHoursAvg': 1.8,
                        'timeReferredToDoneHoursAvg': 17.0,
                        'timeReportToResolutionHoursAvg': 24.8
                    }
                ],
                'weighted': {
                    'weekLabel': 'Weighted Average',
                    'count': 45,
                    'timeToInProgressHoursAvg': 2.6,
                    'timeInProgressToDoneHoursAvg': 20.5,
                    'timeReportedToReferredHoursAvg': 1.6,
                    'timeReferredToDoneHoursAvg': 16.3,
                    'timeReportToResolutionHoursAvg': 23.1
                }
            }
        
        # Format the data for frontend
        rows = []
        for row in weekly_rows:
            rows.append({
                'weekLabel': row[0],
                'count': row[1],
                'timeToInProgressHoursAvg': row[2],
                'timeInProgressToDoneHoursAvg': row[3],
                'timeReportedToReferredHoursAvg': row[4],
                'timeReferredToDoneHoursAvg': row[5],
                'timeReportToResolutionHoursAvg': row[6]
            })
        
        # Format weighted averages
        weighted = {
            'weekLabel': 'Weighted Average',
            'count': weighted_row[0] if weighted_row else 0,
            'timeToInProgressHoursAvg': weighted_row[1] if weighted_row else 0,
            'timeInProgressToDoneHoursAvg': weighted_row[2] if weighted_row else 0,
            'timeReportedToReferredHoursAvg': weighted_row[3] if weighted_row else 0,
            'timeReferredToDoneHoursAvg': weighted_row[4] if weighted_row else 0,
            'timeReportToResolutionHoursAvg': weighted_row[5] if weighted_row else 0
        }
        
        print(f"✅ Served cached response times: {len(rows)} weeks for environment: {environment or 'All Environments'}")
        
        return {
            'rows': rows,
            'weighted': weighted
        }
        
    except Exception as e:
        print(f"Error fetching cached response times: {e}")
        raise HTTPException(status_code=500, detail=str(e))