#!/usr/bin/env python3
"""
Find all fields that might contain time/duration data.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Imported table")

def find_time_fields():
    """Find all fields that might contain time data."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Get 50 records to find fields
    params = {"pageSize": 50}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    records = data.get("records", [])
    
    # Collect all unique field names
    all_fields = set()
    for record in records:
        all_fields.update(record['fields'].keys())
    
    print(f"Found {len(all_fields)} unique fields across {len(records)} records")
    print("\nAll fields:")
    for field in sorted(all_fields):
        print(f"  '{field}'")
    
    # Look for fields with time-related keywords
    time_keywords = ['time', 'Time', 'date', 'Date', 'duration', 'Duration', 'hour', 'Hour', 'minute', 'Minute']
    
    print(f"\nFields containing time-related keywords:")
    time_fields = []
    for field in sorted(all_fields):
        for keyword in time_keywords:
            if keyword in field:
                time_fields.append(field)
                break
    
    for field in time_fields:
        print(f"  '{field}'")
        
        # Show sample values for time fields
        sample_values = []
        for record in records[:10]:
            value = record['fields'].get(field)
            if value is not None:
                sample_values.append(value)
        
        if sample_values:
            print(f"    Sample values: {sample_values[:3]}")
        else:
            print(f"    Sample values: All None/empty")

if __name__ == "__main__":
    find_time_fields()