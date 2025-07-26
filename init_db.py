import sqlite3

def init_db():
    conn = sqlite3.connect("../voice_of_customer.db")  # adjust path as needed
    cursor = conn.cursor()

    # Create feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            initial_description TEXT,
            priority TEXT,
            team_routed TEXT,
            environment TEXT,
            area_impacted TEXT,
            type_of_report TEXT,
            created_at TEXT,
            embedding BLOB
        )
    """)

    # Create jira_tickets table
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

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()