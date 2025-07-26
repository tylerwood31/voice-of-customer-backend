from fastapi import APIRouter
import sqlite3

router = APIRouter()
DB_PATH = "../voice_of_customer.db"  # Adjust if needed

@router.get("/", summary="Get unique Environment, Area Impacted, and Type of Issue values")
def get_components():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query unique values
    cursor.execute("SELECT DISTINCT environment FROM feedback WHERE environment IS NOT NULL AND environment != ''")
    environments = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT area_impacted FROM feedback WHERE area_impacted IS NOT NULL AND area_impacted != ''")
    areas = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT type_of_report FROM feedback WHERE type_of_report IS NOT NULL AND type_of_report != ''")
    types = [row[0] for row in cursor.fetchall()]

    conn.close()
    return {
        "environments": environments,
        "areas_impacted": areas,
        "types_of_issue": types
    }