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
        client = None
        print("Warning: OPENAI_API_KEY not found in environment variables")
except ImportError:
    client = None
    print("Warning: OpenAI package not installed")
DB_PATH = "/Users/tylerwood/voice_of_customer/voice_of_customer.db"

def embed_text(text: str) -> np.ndarray:
    """Generate an embedding for the given text."""
    if not client:
        raise ValueError("OpenAI client not available")
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def find_related_feedback(question: str, top_n: int = 5):
    """Find top N feedback items most similar to the question."""
    if not client:
        return []
    
    try:
        query_embedding = embed_text(question)
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, initial_description, priority, team_routed, embedding
        FROM feedback
        WHERE embedding IS NOT NULL
    """)
    feedback_rows = cursor.fetchall()
    conn.close()

    similarities = []
    for f_id, description, priority, team, emb_blob in feedback_rows:
        try:
            embedding = pickle.loads(emb_blob)
            similarity = cosine_similarity(query_embedding, embedding)
            similarities.append((similarity, f_id, description, priority, team))
        except Exception as e:
            print(f"Error processing feedback {f_id}: {e}")
            continue

    similarities.sort(reverse=True, key=lambda x: x[0])
    return similarities[:top_n]

def find_related_tickets(question: str, top_n: int = 3):
    """Find top N Jira tickets most similar to the question."""
    if not client:
        return []
    
    try:
        query_embedding = embed_text(question)
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, summary, assignee, team_name, embedding
        FROM jira_tickets
        WHERE embedding IS NOT NULL
    """)
    jira_rows = cursor.fetchall()
    conn.close()

    similarities = []
    for j_id, summary, assignee, team, emb_blob in jira_rows:
        try:
            embedding = pickle.loads(emb_blob)
            similarity = cosine_similarity(query_embedding, embedding)
            similarities.append((similarity, j_id, summary, assignee, team))
        except Exception as e:
            print(f"Error processing ticket {j_id}: {e}")
            continue

    similarities.sort(reverse=True, key=lambda x: x[0])
    return similarities[:top_n]