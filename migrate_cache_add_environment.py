#!/usr/bin/env python3
"""
Migration script to add environment support to response times cache.
"""

import sqlite3
import logging

# Configuration
DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_cache_tables():
    """Update cache tables to include environment support."""
    logger.info("Starting cache table migration...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Drop existing tables and recreate with environment support
        logger.info("Dropping existing cache tables...")
        cursor.execute("DROP TABLE IF EXISTS response_times_cache")
        cursor.execute("DROP TABLE IF EXISTS response_times_weighted")
        
        # Create new cache table with environment support
        logger.info("Creating new response_times_cache table with environment support...")
        cursor.execute('''
            CREATE TABLE response_times_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_label TEXT NOT NULL,  -- e.g. "2025-06-30"
                environment TEXT NOT NULL,  -- e.g. "Production", "Staging", etc.
                count INTEGER NOT NULL,
                time_to_in_progress_avg REAL NOT NULL,
                time_in_progress_to_done_avg REAL NOT NULL,
                time_reported_to_referred_avg REAL NOT NULL,
                time_referred_to_done_avg REAL NOT NULL,
                time_report_to_resolution_avg REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_label, environment)
            )
        ''')
        
        # Create new weighted averages table with environment support
        logger.info("Creating new response_times_weighted table with environment support...")
        cursor.execute('''
            CREATE TABLE response_times_weighted (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                environment TEXT NOT NULL,  -- e.g. "Production", "Staging", etc.
                count INTEGER NOT NULL,
                time_to_in_progress_avg REAL NOT NULL,
                time_in_progress_to_done_avg REAL NOT NULL,
                time_reported_to_referred_avg REAL NOT NULL,
                time_referred_to_done_avg REAL NOT NULL,
                time_report_to_resolution_avg REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(environment)
            )
        ''')
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_week_label_env ON response_times_cache(week_label, environment)")
        cursor.execute("CREATE INDEX idx_environment ON response_times_cache(environment)")
        cursor.execute("CREATE INDEX idx_weighted_env ON response_times_weighted(environment)")
        
        conn.commit()
        logger.info("✅ Cache table migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_cache_tables()