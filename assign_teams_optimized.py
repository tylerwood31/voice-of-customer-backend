#!/usr/bin/env python3
"""
Optimized team assignment script with rate limiting and retry logic.
"""

import sqlite3
import time
import logging
import random
from src.semantic_router import find_related_tickets

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def assign_teams_optimized():
    """Assign teams with rate limiting and retry logic."""
    logger.info("🚀 Starting optimized team assignment...")
    
    # Get records needing assignment
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, initial_description 
        FROM feedback 
        WHERE team_routed IS NULL OR team_routed = ''
        ORDER BY created DESC
        LIMIT 100
    """)
    feedback_rows = cursor.fetchall()
    conn.close()
    
    total_records = len(feedback_rows)
    logger.info(f"📊 Found {total_records} records needing team assignment")
    
    if total_records == 0:
        logger.info("✅ All records already have team assignments")
        return
    
    assigned_count = 0
    error_count = 0
    
    for i, (f_id, description) in enumerate(feedback_rows, 1):
        if not description or not description.strip():
            continue
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Find top Jira match with rate limiting
                jira_matches = find_related_tickets(description, top_n=1)
                
                conn = sqlite3.connect(DB_PATH, timeout=30)
                cursor = conn.cursor()
                
                if jira_matches:
                    best_match = jira_matches[0]
                    similarity, jira_id, jira_summary, assignee, team_name = best_match
                    assigned_team = team_name if team_name else "Unassigned"
                else:
                    assigned_team = "Unassigned"
                
                cursor.execute(
                    "UPDATE feedback SET team_routed = ? WHERE id = ?",
                    (assigned_team, f_id)
                )
                conn.commit()
                conn.close()
                
                assigned_count += 1
                logger.info(f"  📈 {i}/{total_records}: Assigned {f_id} to {assigned_team}")
                
                # Rate limiting: wait between requests
                time.sleep(random.uniform(0.5, 1.5))
                break
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"  ⚠️ Attempt {retry_count} failed for {f_id}: {e}")
                
                if retry_count < max_retries:
                    # Exponential backoff
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    logger.info(f"  ⏳ Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"  ❌ Failed to process {f_id} after {max_retries} attempts")
                    error_count += 1
                
                try:
                    conn.close()
                except:
                    pass
    
    logger.info(f"🎉 Batch completed!")
    logger.info(f"  📊 Successfully assigned: {assigned_count} records")
    logger.info(f"  ❌ Errors: {error_count} records")
    
    # Show progress
    show_progress()

def show_progress():
    """Show current assignment progress."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM feedback")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM feedback WHERE team_routed IS NULL OR team_routed = ''")
    remaining = cursor.fetchone()[0]
    
    assigned = total - remaining
    progress = (assigned / total) * 100
    
    logger.info(f"📈 Progress: {assigned}/{total} assigned ({progress:.1f}%)")
    logger.info(f"📋 Remaining: {remaining} records")
    
    conn.close()

if __name__ == "__main__":
    assign_teams_optimized()