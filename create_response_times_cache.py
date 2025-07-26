#!/usr/bin/env python3
"""
Create the response_times_cache table for storing weekly response time data.
"""

import sqlite3
import os

# Database path
DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

def create_cache_table():
    """Create the response_times_cache table."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_times_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_label TEXT UNIQUE NOT NULL,  -- e.g. "2025-06-30"
            count INTEGER NOT NULL,
            time_to_in_progress_avg REAL NOT NULL,
            time_in_progress_to_done_avg REAL NOT NULL,
            time_reported_to_referred_avg REAL NOT NULL,
            time_referred_to_done_avg REAL NOT NULL,
            time_report_to_resolution_avg REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create the weighted averages cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_times_weighted (
            id INTEGER PRIMARY KEY,
            count INTEGER NOT NULL,
            time_to_in_progress_avg REAL NOT NULL,
            time_in_progress_to_done_avg REAL NOT NULL,
            time_reported_to_referred_avg REAL NOT NULL,
            time_referred_to_done_avg REAL NOT NULL,
            time_report_to_resolution_avg REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create an index on week_label for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_week_label ON response_times_cache(week_label)')
    
    print("✅ Created response_times_cache and response_times_weighted tables")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_cache_table()