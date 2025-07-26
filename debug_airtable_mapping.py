#!/usr/bin/env python3
"""
Debug Airtable field mapping to see what fields are actually available
"""
import requests
import json
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

def debug_airtable_fields():
    """Fetch a few records and show available fields."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("Missing Airtable credentials")
        return
    
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
        headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
        params = {"pageSize": 3}  # Just get 3 records to examine
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Airtable API error: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        records = data.get("records", [])
        
        if not records:
            print("No records found")
            return
        
        print(f"Found {len(records)} sample records")
        print("=" * 50)
        
        for i, record in enumerate(records, 1):
            fields = record.get("fields", {})
            print(f"\nRecord {i} fields:")
            for field_name, field_value in sorted(fields.items()):
                # Truncate long values for readability
                if isinstance(field_value, str) and len(field_value) > 100:
                    field_value = field_value[:100] + "..."
                print(f"  {field_name}: {field_value}")
        
        # Summary of all unique field names
        all_fields = set()
        for record in records:
            all_fields.update(record.get("fields", {}).keys())
        
        print("\n" + "=" * 50)
        print("ALL AVAILABLE FIELDS:")
        for field in sorted(all_fields):
            print(f"  - {field}")
        
        print("\n" + "=" * 50)
        print("FIELD MAPPING CHECK:")
        sample_fields = records[0].get("fields", {})
        
        # Check Environment field
        env_value = sample_fields.get("Environment", "NOT FOUND")
        print(f"Environment field: {env_value}")
        
        # Check Area Impacted field  
        area_value = sample_fields.get("Area Impacted", "NOT FOUND")
        print(f"Area Impacted field: {area_value}")
        
        # Check other environment-related fields
        cw2_value = sample_fields.get("CW 2.0 Bug", "NOT FOUND")
        print(f"CW 2.0 Bug field: {cw2_value}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_airtable_fields()