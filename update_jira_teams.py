import sqlite3
import csv

# Database and CSV file paths
DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"
CSV_PATH = "/Users/tylerwood/Downloads/Jira (8).csv"

def update_jira_teams():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read CSV and update database
    updates_made = 0
    with open(CSV_PATH, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            issue_id = row.get('Issue id', '').strip()
            team_name = row.get('Team Name', '').strip()
            
            if issue_id and team_name:
                # Update the team_name for this issue_id in jira_tickets table
                cursor.execute(
                    "UPDATE jira_tickets SET team_name = ? WHERE id = ?",
                    (team_name, issue_id)
                )
                if cursor.rowcount > 0:
                    updates_made += 1
                    print(f"Updated {issue_id} with team: {team_name}")
    
    conn.commit()
    conn.close()
    print(f"\nCompleted! Updated {updates_made} Jira tickets with team information.")

if __name__ == "__main__":
    update_jira_teams()