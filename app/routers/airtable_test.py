from fastapi import APIRouter, HTTPException
import requests
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

router = APIRouter()

@router.get("/", summary="Test Airtable connection")
def test_airtable():
    """Test endpoint to verify Airtable configuration and connectivity."""
    
    # Check if environment variables are set
    config_status = {
        "airtable_api_key_set": bool(AIRTABLE_API_KEY),
        "airtable_base_id_set": bool(AIRTABLE_BASE_ID),
        "airtable_table_name": AIRTABLE_TABLE_NAME or "Not set"
    }
    
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        return {
            "status": "error",
            "message": "Airtable environment variables not configured",
            "config": config_status
        }
    
    try:
        # Test API connection with a minimal request
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Only fetch first 3 records to test connection
        params = {"maxRecords": 3}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            record_count = len(data.get("records", []))
            
            return {
                "status": "success",
                "message": f"Successfully connected to Airtable. Found {record_count} test records.",
                "config": config_status,
                "response_info": {
                    "status_code": response.status_code,
                    "record_count": record_count
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Airtable API error: {response.status_code}",
                "config": config_status,
                "error_detail": response.text[:200]
            }
            
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Airtable request timed out",
            "config": config_status
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Connection error: {str(e)}",
            "config": config_status
        }