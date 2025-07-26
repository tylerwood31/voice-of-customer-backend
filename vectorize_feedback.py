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

DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"  # adjust if needed

def embed_text(text: str) -> np.ndarray:
    """Generate an embedding for a given text using OpenAI embeddings."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

def vectorize_feedback(batch_size: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, initial_description FROM feedback WHERE embedding IS NULL")
    records = cursor.fetchall()
    print(f"Found {len(records)} feedback records to vectorize.")

    if not records:
        print("No feedback records need vectorization.")
        conn.close()
        return

    for i, (record_id, description) in enumerate(records, start=1):
        if not description:
            print(f"Skipping record {record_id} - no description")
            continue

        try:
            embedding = embed_text(description)
            cursor.execute(
                "UPDATE feedback SET embedding = ? WHERE id = ?",
                (pickle.dumps(embedding), record_id)
            )
            print(f"[{i}/{len(records)}] Vectorized feedback: {record_id}")

            if i % batch_size == 0:
                conn.commit()
                print(f"Committed batch {i//batch_size}")
        except Exception as e:
            print(f"Error processing record {record_id}: {e}")

    conn.commit()
    conn.close()
    print("All feedback records have been vectorized!")

if __name__ == "__main__":
    vectorize_feedback()