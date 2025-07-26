#!/usr/bin/env python3
"""
Quick cache update - process recent data to populate cache for immediate use.
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Imported table")

def quick_update():
    """Quick update with limited data for immediate results."""
    print("🚀 Quick cache update starting...")
    
    # Fetch limited data (last 1000 records)
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "pageSize": 100,
        "sort[0][field]": "Created",
        "sort[0][direction]": "desc"
    }
    
    records = []
    page_count = 0
    
    print("Fetching recent records...")
    while len(records) < 1000 and page_count < 10:  # Limit to 10 pages max
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        batch_records = data.get("records", [])
        records.extend(batch_records)
        page_count += 1
        
        print(f"Fetched {len(batch_records)} records, total: {len(records)}")
        
        offset = data.get("offset")
        if not offset:
            break
        params["offset"] = offset
    
    print(f"✅ Fetched {len(records)} records")
    
    # Process records
    min_date = datetime(2025, 6, 30)
    weekly_data = defaultdict(list)
    processed = 0
    
    for record in records:
        fields = record['fields']
        created_date = fields.get('Reported At') or record.get('createdTime', '')
        
        if not created_date:
            continue
            
        try:
            dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            if dt < min_date:
                continue
                
            week_start = dt - timedelta(days=dt.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            
            def safe_float(v):
                if v is None or v == '':
                    return 0
                try:
                    return float(str(v)) if not str(v).lower() in ['nan', 'null', 'none'] else 0
                except:
                    return 0
            
            record_data = {
                'time_report_to_resolution': safe_float(fields.get('Time From Report to Resolution')),
                'time_to_in_progress': safe_float(fields.get('Time to In Progress')),
                'time_in_progress_to_done': safe_float(fields.get('Time from In Progress to Done')),
                'time_reported_to_referred': safe_float(fields.get('Time from Reported to Referred')),
                'time_referred_to_done': safe_float(fields.get('Time from Referred to Done')),
            }
            
            weekly_data[week_key].append(record_data)
            processed += 1
            
        except Exception as e:
            continue
    
    print(f"✅ Processed {processed} records into {len(weekly_data)} weeks")
    
    # Calculate averages
    rows = []
    all_records = []
    
    for week, week_records in sorted(weekly_data.items()):
        if not week_records:
            continue
            
        all_records.extend(week_records)
        
        def avg(field):
            values = [r[field] for r in week_records if r[field] > 0]
            return statistics.mean(values) if values else 0
        
        rows.append({
            'week_label': week,
            'count': len(week_records),
            'time_to_in_progress_avg': avg('time_to_in_progress'),
            'time_in_progress_to_done_avg': avg('time_in_progress_to_done'),
            'time_reported_to_referred_avg': avg('time_reported_to_referred'),
            'time_referred_to_done_avg': avg('time_referred_to_done'),
            'time_report_to_resolution_avg': avg('time_report_to_resolution'),
        })
    
    # Weighted averages
    def weighted_avg(field):
        values = [r[field] for r in all_records if r[field] > 0]
        return statistics.mean(values) if values else 0
    
    weighted = {
        'count': len(all_records),
        'time_to_in_progress_avg': weighted_avg('time_to_in_progress'),
        'time_in_progress_to_done_avg': weighted_avg('time_in_progress_to_done'),
        'time_reported_to_referred_avg': weighted_avg('time_reported_to_referred'),
        'time_referred_to_done_avg': weighted_avg('time_referred_to_done'),
        'time_report_to_resolution_avg': weighted_avg('time_report_to_resolution'),
    }
    
    # Update database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear and insert
    cursor.execute("DELETE FROM response_times_cache")
    cursor.execute("DELETE FROM response_times_weighted")
    
    for row in rows:
        cursor.execute('''
            INSERT INTO response_times_cache 
            (week_label, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
             time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['week_label'], row['count'], row['time_to_in_progress_avg'],
            row['time_in_progress_to_done_avg'], row['time_reported_to_referred_avg'],
            row['time_referred_to_done_avg'], row['time_report_to_resolution_avg']
        ))
    
    cursor.execute('''
        INSERT INTO response_times_weighted 
        (id, count, time_to_in_progress_avg, time_in_progress_to_done_avg,
         time_reported_to_referred_avg, time_referred_to_done_avg, time_report_to_resolution_avg)
        VALUES (1, ?, ?, ?, ?, ?, ?)
    ''', (
        weighted['count'], weighted['time_to_in_progress_avg'],
        weighted['time_in_progress_to_done_avg'], weighted['time_reported_to_referred_avg'],
        weighted['time_referred_to_done_avg'], weighted['time_report_to_resolution_avg']
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Cache updated! {len(rows)} weeks, {weighted['count']} total records")

if __name__ == "__main__":
    quick_update()