from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import os
import sys
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.semantic_router import find_related_tickets, find_related_feedback

router = APIRouter()
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH

# Initialize OpenAI client only if API key is available
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        client = None
except ImportError:
    client = None

class ChatRequest(BaseModel):
    question: str
    team: Optional[str] = None
    filters: Dict = {}

class ChatResponse(BaseModel):
    answer: str
    related_feedback: List[Dict]
    related_jira: List[Dict]

def get_related_feedback(question: str, top_n=5) -> List[Dict]:
    """Get feedback records based on search terms in question"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Simple keyword search in feedback descriptions
    cursor.execute("""
        SELECT id, initial_description, priority, team_routed
        FROM feedback
        WHERE initial_description LIKE ?
        ORDER BY created DESC
        LIMIT ?
    """, (f"%{question}%", top_n))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"id": r[0], "description": r[1], "priority": r[2], "team": r[3]}
        for r in rows
    ]

def get_related_jira(question: str, top_n=3) -> List[Dict]:
    """Get Jira tickets with basic text matching"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, summary, assignee, team_name
        FROM jira_tickets
        WHERE summary LIKE ? OR description LIKE ?
        LIMIT ?
    """, (f"%{question}%", f"%{question}%", top_n))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"id": r[0], "summary": r[1], "assignee": r[2], "team": r[3]}
        for r in rows
    ]

def generate_ai_response(question: str, feedback_context: List[Dict], jira_context: List[Dict]) -> str:
    """Generate AI response using OpenAI"""
    if not client:
        return "AI response unavailable: OpenAI API key not configured"
    
    try:
        context = f"""
        Based on the voice of customer feedback and Jira tickets, answer this question: {question}
        
        Related Feedback:
        {str(feedback_context)}
        
        Related Jira Tickets:
        {str(jira_context)}
        
        Provide a helpful summary and insights.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": context}],
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"AI response unavailable: {str(e)}"

@router.post("/", response_model=ChatResponse, summary="Ask AI about feedback and Jira")
def chat_with_data(request: ChatRequest):
    """Chat endpoint that provides AI-powered insights on feedback and Jira data"""
    
    # Find related feedback using semantic search
    feedback_matches = find_related_feedback(request.question, top_n=5)
    related_feedback = [
        {"id": f[1], "description": f[2], "priority": f[3], "team": f[4], "similarity": f[0]}
        for f in feedback_matches
    ]

    # Find related Jira tickets using semantic search
    jira_matches = find_related_tickets(request.question, top_n=3)
    related_jira = [
        {"ticket_id": j[1], "summary": j[2], "similarity": j[0], "assignee": j[3], "team": j[4]}
        for j in jira_matches
    ]

    # Build context from feedback
    context_text = "\n".join([f"- {f['description']}" for f in related_feedback])
    answer_prompt = f"""
    You are a product analyst. A PM asked: "{request.question}".
    Use this feedback context:
    {context_text}
    Provide a concise answer with references to feedback IDs and Jira tickets.
    """

    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": answer_prompt}],
                temperature=0.3
            )
            ai_answer = response.choices[0].message.content.strip()
        except Exception as e:
            ai_answer = f"AI response unavailable: {str(e)}"
    else:
        ai_answer = "AI response unavailable: OpenAI API key not configured"

    return ChatResponse(
        answer=ai_answer,
        related_feedback=related_feedback,
        related_jira=related_jira
    )

async def stream_ai_response(prompt: str):
    """Stream tokens from OpenAI API as they are generated."""
    if not client:
        yield "AI response unavailable: OpenAI API key not configured"
        return
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
            stream=True  # Enable streaming
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"AI response unavailable: {str(e)}"

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint that provides real-time AI responses."""
    # Find related feedback using semantic search
    feedback_matches = find_related_feedback(request.question, top_n=5)
    jira_matches = find_related_tickets(request.question, top_n=3)

    # Build context from feedback
    context_text = "\n".join([f"- {f[2]}" for f in feedback_matches])
    prompt = f"""
    You are a product analyst. A PM asked: "{request.question}".
    Use this feedback context:
    {context_text}
    Provide a concise answer with references to feedback IDs and Jira tickets.
    """

    return StreamingResponse(stream_ai_response(prompt), media_type="text/plain")