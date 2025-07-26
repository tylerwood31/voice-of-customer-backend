import sqlite3
import numpy as np
import pickle
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        print("Error: OPENAI_API_KEY not found in environment variables")
        exit(1)
except ImportError:
    print("Error: OpenAI package not installed. Run: pip install openai")
    exit(1)

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"  # Adjust if needed
BATCH_SIZE = 100  # Process 100 tickets at a time

def embed_text(text: str) -> np.ndarray:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

def vectorize_jira_tickets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, summary, description FROM jira_tickets WHERE embedding IS NULL")
    tickets = cursor.fetchall()
    total = len(tickets)
    print(f"Found {total} Jira tickets to vectorize.")

    if total == 0:
        print("No Jira tickets need vectorization.")
        conn.close()
        return

    for i, (ticket_id, summary, description) in enumerate(tickets, start=1):
        text = (summary or "") + " " + (description or "")
        if not text.strip():
            print(f"Skipping ticket {ticket_id} - no content")
            continue

        try:
            embedding = embed_text(text)
            cursor.execute(
                "UPDATE jira_tickets SET embedding = ? WHERE id = ?",
                (pickle.dumps(embedding), ticket_id)
            )
            print(f"[{i}/{total}] Vectorized Jira ticket: {ticket_id}")

            if i % BATCH_SIZE == 0:
                conn.commit()
                print(f"Committed batch {i//BATCH_SIZE}")
        except Exception as e:
            print(f"Error processing ticket {ticket_id}: {e}")

    conn.commit()
    conn.close()
    print("All Jira tickets have been vectorized!")

if __name__ == "__main__":
    vectorize_jira_tickets()