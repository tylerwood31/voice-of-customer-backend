#!/usr/bin/env python3
"""
Batch team assignment script with better error handling and progress tracking.
"""

import sqlite3
import time
import logging
from src.semantic_router import find_related_tickets

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def assign_teams_batch():
    """Assign teams to all records in batches with error handling."""
    logger.info("🚀 Starting batch team assignment...")
    
    # First, get all records that need team assignment
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, initial_description 
        FROM feedback 
        WHERE team_routed IS NULL OR team_routed = '' OR team_routed = 'Unassigned'
        ORDER BY created DESC
    """)
    feedback_rows = cursor.fetchall()
    conn.close()
    
    total_records = len(feedback_rows)
    logger.info(f"📊 Found {total_records} records needing team assignment")
    
    if total_records == 0:
        logger.info("✅ All records already have team assignments")
        return
    
    # Process in batches of 50 to avoid database locks
    batch_size = 50
    assigned_count = 0
    error_count = 0
    
    for i in range(0, total_records, batch_size):
        batch = feedback_rows[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size
        
        logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} records)")
        
        # Process this batch
        conn = sqlite3.connect(DB_PATH, timeout=30)  # 30 second timeout
        cursor = conn.cursor()
        
        try:
            for f_id, description in batch:
                if not description or not description.strip():
                    continue
                
                try:
                    # Find top Jira match
                    jira_matches = find_related_tickets(description, top_n=1)
                    if jira_matches:
                        best_match = jira_matches[0]
                        similarity, jira_id, jira_summary, assignee, team_name = best_match
                        
                        # Assign team or "Unassigned" if no team found
                        assigned_team = team_name if team_name else "Unassigned"
                        
                        cursor.execute(
                            "UPDATE feedback SET team_routed = ? WHERE id = ?",
                            (assigned_team, f_id)
                        )
                        assigned_count += 1
                        
                        if assigned_count % 10 == 0:
                            logger.info(f"  📈 Assigned {assigned_count}/{total_records} records...")
                        
                    else:
                        # No matches found, assign as "Unassigned"
                        cursor.execute(
                            "UPDATE feedback SET team_routed = ? WHERE id = ?",
                            ("Unassigned", f_id)
                        )
                        assigned_count += 1
                        
                except Exception as e:
                    logger.warning(f"  ⚠️ Error processing record {f_id}: {e}")
                    error_count += 1
                    continue
            
            # Commit this batch
            conn.commit()
            logger.info(f"  ✅ Committed batch {batch_num} successfully")
            
        except Exception as e:
            logger.error(f"  ❌ Batch {batch_num} failed: {e}")
            conn.rollback()
            error_count += len(batch)
        finally:
            conn.close()
        
        # Small delay between batches to avoid overwhelming the system
        time.sleep(1)
    
    logger.info(f"🎉 Team assignment completed!")
    logger.info(f"  📊 Successfully assigned: {assigned_count} records")
    logger.info(f"  ❌ Errors: {error_count} records")
    
    # Show final distribution
    show_team_distribution()

def show_team_distribution():
    """Show the current team distribution."""
    logger.info("📈 Current team distribution:")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT team_routed, COUNT(*) as count
        FROM feedback 
        WHERE team_routed IS NOT NULL AND team_routed != ''
        GROUP BY team_routed 
        ORDER BY count DESC
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    for team, count in results:
        logger.info(f"  {team}: {count} records")

if __name__ == "__main__":
    assign_teams_batch()