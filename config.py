import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_PATH = os.getenv("DATABASE_PATH", "./voice_of_customer.db")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")