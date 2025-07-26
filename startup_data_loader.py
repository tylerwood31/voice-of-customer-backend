#!/usr/bin/env python3
"""
Startup data loader to ensure Jira tickets are available after deployment
"""
import sqlite3
import csv
import os
from config import DB_PATH

def ensure_jira_data_loaded():
    """Ensure Jira tickets are loaded into the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jira_tickets (
                id TEXT PRIMARY KEY,
                summary TEXT,
                description TEXT,
                resolution TEXT,
                assignee TEXT,
                team_name TEXT,
                embedding BLOB
            )
        """)
        
        # Check if we already have Jira data
        cursor.execute("SELECT COUNT(*) FROM jira_tickets")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"✅ Jira tickets already loaded ({existing_count} records)")
            conn.close()
            return
        
        # Load Jira data from CSV
        csv_path = os.path.join(os.path.dirname(__file__), "data", "jira_tickets.csv")
        
        if not os.path.exists(csv_path):
            print(f"❌ Jira CSV not found at {csv_path}")
            conn.close()
            return
        
        print(f"📂 Loading Jira tickets from {csv_path}")
        loaded_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Extract fields from CSV
                issue_id = (row.get('Issue id') or 
                           row.get('Issue ID') or 
                           row.get('Key') or 
                           row.get('Issue Key') or '').strip()
                
                summary = (row.get('Summary') or 
                          row.get('Title') or '').strip()
                
                description = (row.get('Description') or 
                             row.get('Issue Description') or '').strip()
                
                resolution = (row.get('Resolution') or '').strip()
                
                assignee = (row.get('Assignee') or 
                           row.get('Assigned To') or '').strip()
                
                team_name = (row.get('Team Name') or 
                           row.get('Team') or 
                           row.get('Component/s') or '').strip()
                
                if issue_id:
                    cursor.execute("""
                        INSERT OR REPLACE INTO jira_tickets 
                        (id, summary, description, resolution, assignee, team_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (issue_id, summary, description, resolution, assignee, team_name))
                    
                    loaded_count += 1
        
        conn.commit()
        
        # Get final counts
        cursor.execute("SELECT COUNT(*) FROM jira_tickets")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jira_tickets WHERE team_name IS NOT NULL AND team_name != ''")
        with_teams = cursor.fetchone()[0]
        
        print(f"✅ Successfully loaded {loaded_count} Jira tickets!")
        print(f"📊 Total tickets: {total}, With teams: {with_teams}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error loading Jira data: {e}")

if __name__ == "__main__":
    ensure_jira_data_loaded()