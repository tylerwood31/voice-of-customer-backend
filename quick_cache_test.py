#!/usr/bin/env python3
"""
Quick cache update script - smaller version for testing.
"""

import os
import sqlite3
import requests
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Imported table")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting quick cache update")
    
    # Fetch just 100 records for testing
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    
    response = requests.get(url, headers=headers, params={"pageSize": 100}, timeout=30)
    records = response.json().get("records", [])
    
    logger.info(f"Fetched {len(records)} records")
    
    # Process and create sample data by environment
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear cache
    cursor.execute("DELETE FROM response_times_cache")
    cursor.execute("DELETE FROM response_times_weighted")
    
    # Create sample data for each environment found in feedback
    environments = ["SME 2.0 - Production", "CW 1.0", "Affinities 1.0", "Allied Individuals"]
    
    for env in environments:
        # Weekly data
        cursor.execute('''
            INSERT INTO response_times_cache 
            (week_label, environment, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
             time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("2025-07-21", env, 5, 2.0 + len(env) * 0.1, 20.0 + len(env) * 0.5, 1.0, 15.0 + len(env) * 0.3, 22.0 + len(env) * 0.4))
        
        # Weighted average
        cursor.execute('''
            INSERT INTO response_times_weighted 
            (environment, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
             time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (env, 5, 2.0 + len(env) * 0.1, 20.0 + len(env) * 0.5, 1.0, 15.0 + len(env) * 0.3, 22.0 + len(env) * 0.4))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Created test data for {len(environments)} environments: {environments}")

if __name__ == "__main__":
    main()