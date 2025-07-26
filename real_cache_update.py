#!/usr/bin/env python3
"""
Real cache update using actual Airtable data from June 30, 2025 onwards.
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

def fetch_airtable_data():
    """Fetch all data from Airtable."""
    logger.info("Fetching Airtable data...")
    
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    
    records = []
    offset = None
    
    # Fetch ALL records (no limit)
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        
        logger.info(f"Fetching batch... (total so far: {len(records)})")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        batch_records = data.get("records", [])
        records.extend(batch_records)
        
        offset = data.get("offset")
        if not offset:  # No more records
            break
    
    logger.info(f"✅ Fetched {len(records)} records from Airtable")
    return records

def process_records(records):
    """Process Airtable records into weekly aggregations by environment."""
    logger.info("Processing records...")
    
    # Date filter: Only include data from 6/30/25 onwards
    min_date = datetime(2025, 6, 30).replace(tzinfo=None)
    weekly_data = defaultdict(lambda: defaultdict(list))  # {week: {environment: [records]}}
    
    processed_count = 0
    filtered_count = 0
    no_date_count = 0
    
    for record in records:
        fields = record['fields']
        
        # Get created date - try multiple field names
        created_date = None
        for date_field in ['Reported On', 'Reported At', 'Created']:
            if fields.get(date_field):
                created_date = fields[date_field]
                break
        
        if not created_date:
            # Try record-level createdTime
            created_date = record.get('createdTime')
        
        if not created_date:
            no_date_count += 1
            continue
        
        # Get environment
        environment = fields.get('Environment', 'Unknown')
        if not environment:
            environment = 'Unknown'
            
        try:
            # Parse date and make timezone-naive for comparison
            if isinstance(created_date, str):
                if 'T' in created_date:
                    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    dt = dt.replace(tzinfo=None)  # Make timezone-naive
                else:
                    dt = datetime.strptime(created_date, '%Y-%m-%d')
            else:
                continue
            
            # Skip records before 6/30/25
            if dt < min_date:
                filtered_count += 1
                continue
            
            # Get Monday of the week for grouping
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
            
            # Collect response time metrics
            record_data = {
                'record_id': record.get('id', 'unknown'),
                'environment': environment,
                'created_date': dt,
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
    
    # Count records after July 20, 2025 for verification
    july_20_count = 0
    july_20_date = datetime(2025, 7, 20).replace(tzinfo=None)
    for week_data in weekly_data.values():
        for env_records in week_data.values():
            for record in env_records:
                if record['created_date'] > july_20_date:
                    july_20_count += 1
    
    logger.info(f"✅ Processed {processed_count} records")
    logger.info(f"   Filtered out {filtered_count} pre-6/30/25 records")
    logger.info(f"   Skipped {no_date_count} records with no date")
    logger.info(f"   Records after July 20, 2025: {july_20_count} (should be ~328)")
    logger.info(f"   Created weekly buckets for {len(weekly_data)} weeks")
    
    # Log week breakdown
    for week in sorted(weekly_data.keys()):
        env_counts = {env: len(records) for env, records in weekly_data[week].items()}
        total_week_count = sum(env_counts.values())
        logger.info(f"   Week {week}: {total_week_count} records across {len(env_counts)} environments")
    
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
                'count': len(records),  # This is the actual count of lead bug records
                'time_to_in_progress_avg': avg('time_to_in_progress'),
                'time_in_progress_to_done_avg': avg('time_in_progress_to_done'),
                'time_reported_to_referred_avg': avg('time_reported_to_referred'),
                'time_referred_to_done_avg': avg('time_referred_to_done'),
                'time_report_to_resolution_avg': avg('time_report_to_resolution'),
            }
            
            rows.append(weekly_avg)
            logger.info(f"   {week} | {environment}: {len(records)} records")
    
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
        logger.info(f"   {environment} overall: {total_count} records")
    
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
    """Main function."""
    logger.info("🚀 Starting real cache update with actual Airtable data")
    
    try:
        # Fetch data from Airtable
        records = fetch_airtable_data()
        
        # Process into weekly buckets
        weekly_data = process_records(records)
        
        # Calculate averages
        weekly_rows, weighted_averages = calculate_weekly_averages(weekly_data)
        
        # Update database cache
        update_cache(weekly_rows, weighted_averages)
        
        logger.info("✅ Real cache update completed successfully!")
        total_records = sum(w['count'] for w in weighted_averages)
        logger.info(f"📊 Summary: {len(weekly_rows)} week-environment combinations, {total_records} total records across {len(weighted_averages)} environments")
        
    except Exception as e:
        logger.error(f"❌ Update failed: {e}")
        raise

if __name__ == "__main__":
    main()