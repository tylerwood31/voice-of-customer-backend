#!/usr/bin/env python3
"""
Debug Airtable fields to see what data is available.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Imported table")

def debug_fields():
    """Check what fields and data we have."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Get first 10 records
    params = {"pageSize": 10}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    records = data.get("records", [])
    
    print(f"Found {len(records)} sample records")
    print("\n" + "="*50)
    
    for i, record in enumerate(records[:3]):
        fields = record['fields']
        print(f"\nRecord {i+1}:")
        print(f"  ID: {record.get('id')}")
        print(f"  Created: {record.get('createdTime')}")
        
        # Check for date fields
        reported_at = fields.get('Reported At')
        if reported_at:
            try:
                dt = datetime.fromisoformat(reported_at.replace('Z', '+00:00'))
                print(f"  Reported At: {reported_at} -> {dt}")
                print(f"  After 6/30/25: {dt >= datetime(2025, 6, 30)}")
            except:
                print(f"  Reported At: {reported_at} (parse error)")
        else:
            print(f"  Reported At: None")
        
        # Check response time fields
        response_fields = [
            'Time From Report to Resolution',
            'Time to In Progress', 
            'Time from In Progress to Done',
            'Time from Reported to Referred',
            'Time from Referred to Done'
        ]
        
        print("  Response Time Fields:")
        for field in response_fields:
            value = fields.get(field)
            print(f"    {field}: {value} (type: {type(value)})")
        
        # Show all available fields for first record
        if i == 0:
            print(f"\n  All fields in this record:")
            for key, value in fields.items():
                print(f"    '{key}': {value} (type: {type(value)})")

if __name__ == "__main__":
    debug_fields()