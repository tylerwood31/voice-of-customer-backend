import sqlite3
from src.semantic_router import find_related_tickets
import pickle
import numpy as np

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

def assign_teams():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, initial_description FROM feedback WHERE team_routed IS NULL OR team_routed = '' OR team_routed = 'Unassigned'")
    feedback_rows = cursor.fetchall()

    for f_id, description in feedback_rows:
        if not description:
            continue

        # Find top Jira match
        jira_matches = find_related_tickets(description, top_n=1)
        if jira_matches:
            best_match = jira_matches[0]
            similarity, jira_id, jira_summary, assignee, team_name = best_match
            cursor.execute(
                "UPDATE feedback SET team_routed = ? WHERE id = ?",
                (team_name if team_name else "Unassigned", f_id)
            )
            print(f"Feedback {f_id} assigned to team: {team_name}")
    
    conn.commit()
    conn.close()
    print("Team assignment completed!")

if __name__ == "__main__":
    assign_teams()