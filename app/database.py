import sqlite3
from typing import List, Dict

DB_PATH = "../voice_of_customer.db"  # Adjust path if needed

def get_feedback_records(limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, initial_description, priority, team_routed
        FROM feedback
        ORDER BY created DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    # Convert rows into a list of dictionaries
    return [
        {"id": r[0], "description": r[1], "priority": r[2], "team": r[3]}
        for r in rows
    ]