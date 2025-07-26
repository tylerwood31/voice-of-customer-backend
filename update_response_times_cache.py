#!/usr/bin/env python3
"""
Weekly batch update script for response times cache.
Runs on Sundays at 11:59 PM EST to update the cache with latest data from Airtable.
"""

import os
import sqlite3
import requests
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Imported table")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/tylerwood/voice_of_customer/backend/response_times_cache.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fetch_airtable_data():
    """Fetch data from Airtable."""
    logger.info("Starting Airtable data fetch...")
    
    if not all([AIRTABLE_API_KEY, BASE_ID]):
        raise ValueError("Missing Airtable configuration")
    
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    records = []
    offset = None
    
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        
        logger.info(f"Fetching batch from Airtable... (total so far: {len(records)})")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        batch_records = data.get("records", [])
        records.extend(batch_records)
        
        offset = data.get("offset")
        if not offset:
            break
    
    logger.info(f"✅ Fetched {len(records)} total records from Airtable")
    return records

def process_records(records):
    """Process Airtable records into weekly aggregations by environment."""
    logger.info("Processing records...")
    
    # Date filter: Only include data from 6/30/25 onwards
    min_date = datetime(2025, 6, 30)
    weekly_data = defaultdict(lambda: defaultdict(list))  # {week: {environment: [records]}}
    
    processed_count = 0
    filtered_count = 0
    
    for record in records:
        fields = record['fields']
        
        # Get created date (try multiple field names)
        created_date = fields.get('Reported On') or fields.get('Reported At') or record.get('createdTime', '')
        if not created_date:
            continue
        
        # Get environment
        environment = fields.get('Environment', 'Unknown')
        if not environment:
            environment = 'Unknown'
            
        try:
            dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            
            # Skip records before 6/30/25
            if dt < min_date:
                filtered_count += 1
                continue
            
            # Get Monday of the week
            week_start = dt - timedelta(days=dt.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            
            # Helper function for safe number conversion
            def num_or_zero(v):
                if v is None:
                    return 0
                try:
                    n = float(v)
                    return n if not (n != n) else 0  # Check for NaN
                except (ValueError, TypeError):
                    return 0
            
            # Collect metrics using the correct field names
            record_data = {
                'time_report_to_resolution': num_or_zero(fields.get('Time From Report to Resolution')),
                'time_to_in_progress': num_or_zero(fields.get('Time to In Progress')),
                'time_in_progress_to_done': num_or_zero(fields.get('Time from In Progress to Done')),
                'time_reported_to_referred': num_or_zero(fields.get('Time from Reported to Referred')),
                'time_referred_to_done': num_or_zero(fields.get('Time from Referred to Done')),
            }
            
            weekly_data[week_key][environment].append(record_data)
            processed_count += 1
            
        except Exception as e:
            logger.warning(f"Error processing record {record.get('id', 'unknown')}: {e}")
            continue
    
    total_weeks = sum(len(env_data) for env_data in weekly_data.values())
    logger.info(f"✅ Processed {processed_count} records, filtered out {filtered_count} pre-6/30/25 records")
    logger.info(f"✅ Created {total_weeks} weekly-environment buckets across {len(weekly_data)} weeks")
    
    return weekly_data

def calculate_weekly_averages(weekly_data):
    """Calculate weekly averages from the grouped data by environment."""
    logger.info("Calculating weekly averages...")
    
    rows = []
    all_records_by_env = defaultdict(list)
    
    # Process each week-environment combination
    for week, env_data in sorted(weekly_data.items()):
        for environment, records in env_data.items():
            if not records:
                continue
                
            all_records_by_env[environment].extend(records)
            
            def avg(field: str) -> float:
                values = [r[field] for r in records if r[field] and r[field] > 0]
                return statistics.mean(values) if values else 0
            
            weekly_avg = {
                'week_label': week,
                'environment': environment,
                'count': len(records),
                'time_to_in_progress_avg': avg('time_to_in_progress'),
                'time_in_progress_to_done_avg': avg('time_in_progress_to_done'),
                'time_reported_to_referred_avg': avg('time_reported_to_referred'),
                'time_referred_to_done_avg': avg('time_referred_to_done'),
                'time_report_to_resolution_avg': avg('time_report_to_resolution'),
            }
            
            rows.append(weekly_avg)
    
    # Calculate weighted averages by environment
    weighted_averages = []
    
    for environment, records in all_records_by_env.items():
        total_count = len(records)
        
        def weighted_avg(field: str) -> float:
            if total_count == 0:
                return 0
            values = [r[field] for r in records if r[field] and r[field] > 0]
            return statistics.mean(values) if values else 0
        
        weighted = {
            'environment': environment,
            'count': total_count,
            'time_to_in_progress_avg': weighted_avg('time_to_in_progress'),
            'time_in_progress_to_done_avg': weighted_avg('time_in_progress_to_done'),
            'time_reported_to_referred_avg': weighted_avg('time_reported_to_referred'),
            'time_referred_to_done_avg': weighted_avg('time_referred_to_done'),
            'time_report_to_resolution_avg': weighted_avg('time_report_to_resolution'),
        }
        
        weighted_averages.append(weighted)
    
    logger.info(f"✅ Calculated averages for {len(rows)} week-environment combinations")
    logger.info(f"✅ Calculated weighted averages for {len(weighted_averages)} environments")
    return rows, weighted_averages

def update_cache(weekly_rows, weighted_averages):
    """Update the database cache with new data."""
    logger.info("Updating database cache...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Clear existing cache
        cursor.execute("DELETE FROM response_times_cache")
        cursor.execute("DELETE FROM response_times_weighted")
        
        # Insert weekly data with environment
        for row in weekly_rows:
            cursor.execute('''
                INSERT INTO response_times_cache 
                (week_label, environment, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
                 time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['week_label'], row['environment'], row['count'], row['time_to_in_progress_avg'],
                row['time_in_progress_to_done_avg'], row['time_reported_to_referred_avg'],
                row['time_referred_to_done_avg'], row['time_report_to_resolution_avg']
            ))
        
        # Insert weighted averages for each environment
        for weighted in weighted_averages:
            cursor.execute('''
                INSERT INTO response_times_weighted 
                (environment, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
                 time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                weighted['environment'], weighted['count'], weighted['time_to_in_progress_avg'],
                weighted['time_in_progress_to_done_avg'], weighted['time_reported_to_referred_avg'],
                weighted['time_referred_to_done_avg'], weighted['time_report_to_resolution_avg']
            ))
        
        conn.commit()
        logger.info(f"✅ Updated cache with {len(weekly_rows)} weekly records and {len(weighted_averages)} weighted averages")
        
    except Exception as e:
        logger.error(f"❌ Database update failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main batch update function."""
    logger.info("🚀 Starting weekly response times cache update")
    logger.info(f"📅 Update time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}")
    
    try:
        # Fetch data from Airtable
        records = fetch_airtable_data()
        
        # Process into weekly buckets
        weekly_data = process_records(records)
        
        # Calculate averages
        weekly_rows, weighted_averages = calculate_weekly_averages(weekly_data)
        
        # Update database cache
        update_cache(weekly_rows, weighted_averages)
        
        logger.info("✅ Weekly cache update completed successfully!")
        total_records = sum(w['count'] for w in weighted_averages)
        logger.info(f"📊 Summary: {len(weekly_rows)} week-environment combinations, {total_records} total records across {len(weighted_averages)} environments")
        
    except Exception as e:
        logger.error(f"❌ Batch update failed: {e}")
        raise

if __name__ == "__main__":
    main()