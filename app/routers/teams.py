from fastapi import APIRouter
from typing import List, Dict
import sqlite3

router = APIRouter()

DB_PATH = "../voice_of_customer.db"  # Adjust path if needed

def get_all_teams() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team, tech_rep_dev, team_manager, product_manager, product_director
        FROM team_directory
        ORDER BY team
    """)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "team": r[0],
            "tech_rep_dev": r[1],
            "team_manager": r[2],
            "product_manager": r[3],
            "product_director": r[4]
        }
        for r in rows
    ]

@router.get("/", summary="Get all teams and their contacts")
def list_teams():
    return get_all_teams()