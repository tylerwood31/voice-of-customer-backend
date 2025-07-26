import sqlite3
import numpy as np
import pickle
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_PATH = "../voice_of_customer.db"  # adjust path if needed

def embed_text(text: str) -> np.ndarray:
    """Generate an embedding for the given text."""
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
    query_embedding = embed_text(question)

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
        embedding = pickle.loads(emb_blob)
        similarity = cosine_similarity(query_embedding, embedding)
        similarities.append((similarity, f_id, description, priority, team))

    similarities.sort(reverse=True, key=lambda x: x[0])
    return similarities[:top_n]

if __name__ == "__main__":
    # Test the semantic search
    question = input("Enter your question: ")
    results = find_related_feedback(question)
    
    print(f"\nTop {len(results)} most related feedback items:")
    for i, (similarity, f_id, description, priority, team) in enumerate(results, 1):
        print(f"\n{i}. Similarity: {similarity:.4f}")
        print(f"   ID: {f_id}")
        print(f"   Priority: {priority}")
        print(f"   Team: {team}")
        print(f"   Description: {description[:200]}...")