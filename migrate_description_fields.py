#!/usr/bin/env python3
"""
Migration script to update existing records with proper description field logic.

Based on the data evolution around May 23rd:
- Records should use initial_description as the primary field
- For existing records where initial_description is empty but notes has content,
  copy notes content to initial_description
- This makes the data consistent and future-proof
"""

import sqlite3
import logging
from datetime import datetime

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_current_state():
    """Analyze the current state of description fields."""
    logger.info("🔍 Analyzing current state of description fields...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Total records
        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_records = cursor.fetchone()[0]
        
        # Records with initial_description
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE initial_description IS NOT NULL AND TRIM(initial_description) != ''")
        with_initial_desc = cursor.fetchone()[0]
        
        # Records with notes
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE notes IS NOT NULL AND TRIM(notes) != ''")
        with_notes = cursor.fetchone()[0]
        
        # Records with both empty
        cursor.execute("""
            SELECT COUNT(*) FROM feedback 
            WHERE (initial_description IS NULL OR TRIM(initial_description) = '') 
            AND (notes IS NULL OR TRIM(notes) = '')
        """)
        with_neither = cursor.fetchone()[0]
        
        # Records needing migration (empty initial_description but has notes)
        cursor.execute("""
            SELECT COUNT(*) FROM feedback 
            WHERE (initial_description IS NULL OR TRIM(initial_description) = '')
            AND (notes IS NOT NULL AND TRIM(notes) != '')
        """)
        need_migration = cursor.fetchone()[0]
        
        logger.info(f"📊 Current State Analysis:")
        logger.info(f"  Total records: {total_records}")
        logger.info(f"  Records with initial_description: {with_initial_desc}")
        logger.info(f"  Records with notes: {with_notes}")
        logger.info(f"  Records with neither: {with_neither}")
        logger.info(f"  Records needing migration: {need_migration}")
        
        return need_migration > 0
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise
    finally:
        conn.close()

def migrate_description_fields():
    """Migrate records to use initial_description as primary field."""
    logger.info("🔄 Starting description field migration...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Find records that need migration
        cursor.execute("""
            SELECT id, notes, initial_description, created
            FROM feedback 
            WHERE (initial_description IS NULL OR TRIM(initial_description) = '')
            AND (notes IS NOT NULL AND TRIM(notes) != '')
        """)
        
        records_to_migrate = cursor.fetchall()
        logger.info(f"📝 Found {len(records_to_migrate)} records to migrate")
        
        if not records_to_migrate:
            logger.info("✅ No records need migration")
            return
        
        # Update records - copy notes to initial_description
        migration_count = 0
        for record_id, notes, initial_desc, created in records_to_migrate:
            if notes and notes.strip():
                cursor.execute("""
                    UPDATE feedback 
                    SET initial_description = ?
                    WHERE id = ?
                """, (notes.strip(), record_id))
                migration_count += 1
                
                if migration_count % 500 == 0:
                    logger.info(f"  📈 Migrated {migration_count} records...")
        
        conn.commit()
        logger.info(f"✅ Successfully migrated {migration_count} records")
        logger.info("   Notes content has been copied to initial_description field")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_migration():
    """Verify that the migration was successful."""
    logger.info("🔍 Verifying migration results...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Records with initial_description after migration
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE initial_description IS NOT NULL AND TRIM(initial_description) != ''")
        with_initial_desc = cursor.fetchone()[0]
        
        # Records still needing migration
        cursor.execute("""
            SELECT COUNT(*) FROM feedback 
            WHERE (initial_description IS NULL OR TRIM(initial_description) = '')
            AND (notes IS NOT NULL AND TRIM(notes) != '')
        """)
        still_need_migration = cursor.fetchone()[0]
        
        # Sample a few records to verify content
        cursor.execute("""
            SELECT id, initial_description, notes, created
            FROM feedback 
            WHERE initial_description IS NOT NULL AND TRIM(initial_description) != ''
            LIMIT 3
        """)
        sample_records = cursor.fetchall()
        
        logger.info(f"📊 Migration Verification:")
        logger.info(f"  Records with initial_description: {with_initial_desc}")
        logger.info(f"  Records still needing migration: {still_need_migration}")
        
        if still_need_migration == 0:
            logger.info("✅ Migration completed successfully - all records have initial_description")
        else:
            logger.warning(f"⚠️ {still_need_migration} records still need migration")
        
        logger.info("📋 Sample migrated records:")
        for record_id, initial_desc, notes, created in sample_records:
            desc_preview = initial_desc[:100] + "..." if len(initial_desc) > 100 else initial_desc
            logger.info(f"  {record_id} ({created}): {desc_preview}")
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        raise
    finally:
        conn.close()

def main():
    """Main migration function."""
    logger.info("🚀 Starting description field migration for Voice of Customer system")
    
    try:
        # Step 1: Analyze current state
        needs_migration = analyze_current_state()
        
        if not needs_migration:
            logger.info("🎉 No migration needed - all records already have proper description fields")
            return
        
        # Step 2: Perform migration
        migrate_description_fields()
        
        # Step 3: Verify migration
        verify_migration()
        
        logger.info("🎉 Description field migration completed successfully!")
        logger.info("📝 All records now use initial_description as the primary description field")
        logger.info("🔄 API responses will now be more consistent across all time periods")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    main()