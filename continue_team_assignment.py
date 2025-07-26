#!/usr/bin/env python3
"""
Continue team assignment in smaller batches to avoid timeouts.
"""

import sqlite3
import time
import logging
import random
from src.semantic_router import find_related_tickets

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def continue_assignment():
    """Continue team assignment in smaller batches."""
    batch_size = 25  # Smaller batches to avoid timeout
    
    while True:
        # Get remaining records
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, initial_description 
            FROM feedback 
            WHERE team_routed IS NULL OR team_routed = ''
            ORDER BY created DESC
            LIMIT ?
        """, (batch_size,))
        feedback_rows = cursor.fetchall()
        conn.close()
        
        if not feedback_rows:
            logger.info("🎉 All records have been assigned!")
            break
        
        logger.info(f"📦 Processing batch of {len(feedback_rows)} records...")
        
        assigned_count = 0
        for i, (f_id, description) in enumerate(feedback_rows, 1):
            if not description or not description.strip():
                continue
            
            try:
                # Find top Jira match
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
                logger.info(f"  ✅ {i}/{len(feedback_rows)}: {f_id} → {assigned_team}")
                
                # Rate limiting
                time.sleep(random.uniform(0.3, 0.8))
                
            except Exception as e:
                logger.warning(f"  ❌ Failed to process {f_id}: {e}")
                try:
                    conn.close()
                except:
                    pass
        
        logger.info(f"✅ Batch completed: {assigned_count} records assigned")
        
        # Show current progress
        show_progress()
        
        # Brief pause between batches
        time.sleep(2)

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
    
    logger.info(f"📈 Progress: {assigned}/{total} assigned ({progress:.1f}%), {remaining} remaining")
    
    conn.close()

if __name__ == "__main__":
    continue_assignment()