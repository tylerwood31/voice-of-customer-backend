import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_PATH = os.getenv("DATABASE_PATH", "./voice_of_customer.db")

# Ensure the directory exists if using a mounted disk
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
    except:
        pass

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")