import os
from dotenv import load_dotenv
load_dotenv()

# Always one source of truth
DB_PATH = os.getenv("DATABASE_PATH", "/data/voice_of_customer.db")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Lead Bugs")

# Optional: turn on very loud logging in prod while we debug
DEBUG_REFRESH = os.getenv("DEBUG_REFRESH", "false").lower() == "true"

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ensure the directory exists if using a mounted disk
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ Created database directory: {db_dir}")
    except Exception as e:
        print(f"⚠️ Could not create database directory {db_dir}: {e}")

# Verify database path is accessible
try:
    # Test if we can create/access the database file
    import sqlite3
    test_conn = sqlite3.connect(DB_PATH)
    test_conn.close()
    print(f"✅ Database path accessible: {DB_PATH}")
except Exception as e:
    print(f"❌ Database path issue: {DB_PATH}, error: {e}")
    # Fallback to local path if persistent disk fails
    if DB_PATH != "./voice_of_customer.db":
        print("🔄 Falling back to local database path")
        DB_PATH = "./voice_of_customer.db"