import sqlite3
from typing import List, Dict, Optional

DB_PATH = "../voice_of_customer.db"  # Adjust path if needed

def get_feedback_records(
    limit: int = 50,
    team: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT id, initial_description, priority, team_routed FROM feedback WHERE 1=1"
    params = []

    if team:
        query += " AND team_routed = ?"
        params.append(team)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if search:
        query += " AND initial_description LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY created DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {"id": r[0], "description": r[1], "priority": r[2], "team": r[3]}
        for r in rows
    ]