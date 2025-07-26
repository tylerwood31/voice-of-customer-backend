#!/usr/bin/env python3
"""
Load Jira tickets from CSV into the database for team assignment
"""
import sqlite3
import csv
import os
from config import DB_PATH

# Use the most recent Jira CSV file
CSV_PATH = "/Users/tylerwood/Downloads/Jira (8).csv"

def load_jira_tickets():
    """Load Jira tickets from CSV into the database."""
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists
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
    
    # Clear existing data
    cursor.execute("DELETE FROM jira_tickets")
    
    loaded_count = 0
    
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as csvfile:
            # Peek at first line to see available columns
            first_line = csvfile.readline()
            csvfile.seek(0)
            print(f"CSV columns preview: {first_line[:200]}...")
            
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Try different possible column names for each field
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
                    
                    if loaded_count % 100 == 0:
                        print(f"Loaded {loaded_count} tickets...")
        
        conn.commit()
        print(f"\nSuccessfully loaded {loaded_count} Jira tickets!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM jira_tickets")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jira_tickets WHERE team_name IS NOT NULL AND team_name != ''")
        with_teams = cursor.fetchone()[0]
        
        print(f"Total tickets: {total}")
        print(f"Tickets with team assignments: {with_teams}")
        
        # Show sample teams
        cursor.execute("SELECT DISTINCT team_name FROM jira_tickets WHERE team_name IS NOT NULL AND team_name != '' LIMIT 10")
        teams = cursor.fetchall()
        print(f"Sample teams: {[t[0] for t in teams]}")
        
    except Exception as e:
        print(f"Error loading Jira data: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("Loading Jira tickets from CSV...")
    load_jira_tickets()
    print("Done!")