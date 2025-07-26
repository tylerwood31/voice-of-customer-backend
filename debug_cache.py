#!/usr/bin/env python3
"""
Debug script to manually test and fix the cache system
"""
import intelligent_cache
from airtable import fetch_all_records
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

def debug_cache():
    print("🔍 Debugging cache system...")
    
    # Test 1: Initialize schema
    try:
        print("1. Initializing schema...")
        intelligent_cache.init_schema()
        print("✅ Schema initialized")
    except Exception as e:
        print(f"❌ Schema error: {e}")
        return
    
    # Test 2: Check current status
    try:
        print("2. Checking current status...")
        status = intelligent_cache.get_status()
        print(f"   Status: {status}")
    except Exception as e:
        print(f"❌ Status error: {e}")
    
    # Test 3: Test Airtable connection
    try:
        print("3. Testing Airtable connection...")
        records = fetch_all_records(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        print(f"✅ Airtable: {len(records)} records available")
        if records:
            print(f"   Sample record fields: {list(records[0].get('fields', {}).keys())}")
    except Exception as e:
        print(f"❌ Airtable error: {e}")
        return
    
    # Test 4: Try full refresh
    try:
        print("4. Attempting full refresh...")
        result = intelligent_cache.refresh_full()
        print(f"✅ Refresh result: {result}")
    except Exception as e:
        print(f"❌ Refresh error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check final status
    try:
        print("5. Final status check...")
        status = intelligent_cache.get_status()
        print(f"   Final status: {status}")
    except Exception as e:
        print(f"❌ Final status error: {e}")

if __name__ == "__main__":
    debug_cache()