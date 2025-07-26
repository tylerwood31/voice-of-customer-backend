#!/usr/bin/env python3
"""
Comprehensive data loader to populate the full database with all 2025 Airtable data.
This will load all records into the feedback table and update response times cache.
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

def fetch_all_airtable_data():
    """Fetch all data from Airtable for 2025."""
    logger.info("🚀 Starting comprehensive Airtable data fetch...")
    
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    
    records = []
    offset = None
    
    # Fetch ALL records
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
        
        # Log progress every 1000 records
        if len(records) % 1000 == 0:
            logger.info(f"  📊 Progress: {len(records)} records fetched...")
    
    logger.info(f"✅ Fetched {len(records)} total records from Airtable")
    return records

def clear_existing_data():
    """Clear existing feedback data to avoid duplicates."""
    logger.info("🧹 Clearing existing feedback data...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM feedback")
        conn.commit()
        logger.info("✅ Cleared existing feedback data")
    except Exception as e:
        logger.error(f"❌ Error clearing data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def process_and_load_feedback_data(records):
    """Process Airtable records and load into feedback table."""
    logger.info("📥 Processing and loading feedback data...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    loaded_count = 0
    skipped_count = 0
    error_count = 0
    
    # Filter for 2025 records only
    current_year = datetime.now().year
    year_filter = datetime(current_year, 1, 1)
    
    try:
        for record in records:
            try:
                fields = record.get('fields', {})
                record_id = record.get('id', '')
                
                # Skip records without ID
                if not record_id:
                    skipped_count += 1
                    continue
                
                # Get created date for year filtering
                created_date = None
                for date_field in ['Reported On', 'Reported At', 'Created']:
                    if fields.get(date_field):
                        created_date = fields[date_field]
                        break
                
                if not created_date:
                    created_date = record.get('createdTime')
                
                # Parse and filter by year
                if created_date:
                    try:
                        if isinstance(created_date, str):
                            if 'T' in created_date:
                                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                            else:
                                dt = datetime.strptime(created_date, '%Y-%m-%d')
                            
                            # Skip records not from current year
                            if dt.year != current_year:
                                skipped_count += 1
                                continue
                                
                            created_str = dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                        else:
                            skipped_count += 1
                            continue
                    except:
                        created_str = created_date
                else:
                    # Use record creation time as fallback
                    created_str = record.get('createdTime', '')
                
                # Extract all fields with safe defaults
                def safe_get(field_name, default=''):
                    value = fields.get(field_name, default)
                    return str(value) if value is not None else default
                
                # Calculate week from created date
                try:
                    week_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    week_start = week_dt - timedelta(days=week_dt.weekday())
                    week_str = week_start.strftime('%Y-%m-%d')
                except:
                    week_str = ''
                
                # Map Airtable fields to database fields
                feedback_data = {
                    'id': record_id,
                    'directory_link': safe_get('Directory Link'),
                    'created': created_str,
                    'week': week_str,
                    'initial_description': safe_get('Initial Description'),
                    'priority': safe_get('Priority'),
                    'notes': safe_get('Notes'),
                    'triage_rep': safe_get('Triage Rep'),
                    'status': safe_get('Status'),
                    'resolution_notes': safe_get('Resolution Notes'),
                    'related_imt': safe_get('Related IMT'),
                    'related_imt_link': safe_get('Related IMT Link'),
                    'type_of_report': safe_get('Type of Report'),
                    'area_impacted': safe_get('Area Impacted'),
                    'environment': safe_get('Environment'),
                    'time_to_in_progress': safe_get('Time to In Progress'),
                    'time_from_in_progress_to_done': safe_get('Time from In Progress to Done'),
                    'time_from_reported_to_imt_review': safe_get('Time from Reported to Referred'),
                    'time_from_imt_review_to_done': safe_get('Time from Referred to Done'),
                    'time_from_report_to_resolution': safe_get('Time From Report to Resolution'),
                    'source': safe_get('Source'),
                    'team_routed': safe_get('Team Routed')
                }
                
                # Insert into database
                cursor.execute('''
                    INSERT OR REPLACE INTO feedback (
                        id, directory_link, created, week, initial_description, priority, notes,
                        triage_rep, status, resolution_notes, related_imt, related_imt_link,
                        type_of_report, area_impacted, environment, time_to_in_progress,
                        time_from_in_progress_to_done, time_from_reported_to_imt_review,
                        time_from_imt_review_to_done, time_from_report_to_resolution,
                        source, team_routed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback_data['id'], feedback_data['directory_link'], feedback_data['created'],
                    feedback_data['week'], feedback_data['initial_description'], feedback_data['priority'],
                    feedback_data['notes'], feedback_data['triage_rep'], feedback_data['status'],
                    feedback_data['resolution_notes'], feedback_data['related_imt'], feedback_data['related_imt_link'],
                    feedback_data['type_of_report'], feedback_data['area_impacted'], feedback_data['environment'],
                    feedback_data['time_to_in_progress'], feedback_data['time_from_in_progress_to_done'],
                    feedback_data['time_from_reported_to_imt_review'], feedback_data['time_from_imt_review_to_done'],
                    feedback_data['time_from_report_to_resolution'], feedback_data['source'], feedback_data['team_routed']
                ))
                
                loaded_count += 1
                
                # Progress logging
                if loaded_count % 500 == 0:
                    logger.info(f"  📈 Loaded {loaded_count} records...")
                
            except Exception as e:
                error_count += 1
                logger.warning(f"Error processing record {record.get('id', 'unknown')}: {e}")
                continue
        
        conn.commit()
        logger.info(f"✅ Feedback data loading complete!")
        logger.info(f"  📊 Loaded: {loaded_count} records")
        logger.info(f"  ⏭️  Skipped: {skipped_count} records (wrong year/no data)")
        logger.info(f"  ❌ Errors: {error_count} records")
        
    except Exception as e:
        logger.error(f"❌ Database loading failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
    
    return loaded_count

def update_response_times_cache():
    """Update response times cache with the new complete dataset."""
    logger.info("🔄 Updating response times cache with complete dataset...")
    
    try:
        # Import and run the response times cache update
        import subprocess
        result = subprocess.run([
            'python3', 'real_cache_update.py'
        ], capture_output=True, text=True, cwd='/Users/tylerwood/voice_of_customer/backend')
        
        if result.returncode == 0:
            logger.info("✅ Response times cache updated successfully")
            logger.info(f"Cache update output:\n{result.stdout}")
        else:
            logger.error(f"❌ Response times cache update failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ Error updating response times cache: {e}")

def verify_data_load():
    """Verify the data was loaded correctly."""
    logger.info("🔍 Verifying data load...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_count = cursor.fetchone()[0]
        
        # Count by environment
        cursor.execute("SELECT environment, COUNT(*) FROM feedback GROUP BY environment ORDER BY COUNT(*) DESC")
        env_counts = cursor.fetchall()
        
        # Count by priority
        cursor.execute("SELECT priority, COUNT(*) FROM feedback WHERE priority != '' GROUP BY priority ORDER BY COUNT(*) DESC")
        priority_counts = cursor.fetchall()
        
        # Count recent records (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) FROM feedback 
            WHERE created >= datetime('now', '-30 days')
        """)
        recent_count = cursor.fetchone()[0]
        
        logger.info(f"📊 Data Verification Results:")
        logger.info(f"  Total records: {total_count}")
        logger.info(f"  Recent records (30 days): {recent_count}")
        logger.info(f"  Top environments:")
        for env, count in env_counts[:5]:
            logger.info(f"    {env or 'Unknown'}: {count} records")
        logger.info(f"  Priority distribution:")
        for priority, count in priority_counts:
            logger.info(f"    {priority}: {count} records")
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
    finally:
        conn.close()

def main():
    """Main function to load all data."""
    logger.info("🚀 Starting comprehensive data load for Voice of Customer system")
    logger.info(f"📅 Loading all {datetime.now().year} data from Airtable...")
    
    try:
        # Step 1: Fetch all Airtable data
        records = fetch_all_airtable_data()
        
        # Step 2: Clear existing data
        clear_existing_data()
        
        # Step 3: Process and load feedback data
        loaded_count = process_and_load_feedback_data(records)
        
        # Step 4: Update response times cache
        update_response_times_cache()
        
        # Step 5: Verify the load
        verify_data_load()
        
        logger.info("🎉 Comprehensive data load completed successfully!")
        logger.info(f"📈 Total records loaded: {loaded_count}")
        logger.info("🔄 All systems (Feedback, Chat, Dashboard, Reports) now have complete data")
        
    except Exception as e:
        logger.error(f"❌ Data load failed: {e}")
        raise

if __name__ == "__main__":
    main()