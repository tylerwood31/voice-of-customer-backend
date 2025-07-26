from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import os
import sys
import asyncio

router = APIRouter()
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH, OPENAI_API_KEY
from semantic_analyzer import semantic_analyzer

# Initialize OpenAI client
try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        client = None
        print("⚠️ Chat: OpenAI API key not configured")
except ImportError:
    client = None
    print("⚠️ Chat: OpenAI package not available")

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
    
    if not request.question.strip():
        return ChatResponse(
            answer="Please ask a specific question about the feedback data.",
            related_feedback=[],
            related_jira=[]
        )
    
    try:
        # Find related feedback using our robust semantic analyzer
        feedback_matches = semantic_analyzer.find_related_feedback(request.question, top_n=5)
        related_feedback = []
        
        try:
            related_feedback = [
                {
                    "id": f[1], 
                    "description": f[2][:200] + "..." if len(f[2]) > 200 else f[2], 
                    "priority": f[3], 
                    "team": f[4], 
                    "similarity": round(f[0], 3)
                }
                for f in feedback_matches
            ]
        except Exception as fb_error:
            print(f"⚠️ Feedback search error: {fb_error}")

        # Find related Jira tickets using our robust semantic analyzer
        jira_matches = semantic_analyzer.find_related_jira_tickets(request.question, top_n=3)
        related_jira = []
        
        try:
            related_jira = [
                {
                    "ticket_id": j[1], 
                    "summary": j[2][:150] + "..." if len(j[2]) > 150 else j[2], 
                    "similarity": round(j[0], 3), 
                    "assignee": j[3], 
                    "team": j[4]
                }
                for j in jira_matches
            ]
        except Exception as jira_error:
            print(f"⚠️ Jira search error: {jira_error}")

        # Generate AI response
        ai_answer = generate_intelligent_response(request.question, related_feedback, related_jira)

        return ChatResponse(
            answer=ai_answer,
            related_feedback=related_feedback,
            related_jira=related_jira
        )
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        return ChatResponse(
            answer=f"I'm having trouble accessing the data right now. This might be because we're still loading the feedback database. Please try again in a few minutes.",
            related_feedback=[],
            related_jira=[]
        )

def generate_intelligent_response(question: str, feedback_data: List[Dict], jira_data: List[Dict]) -> str:
    """Generate intelligent AI response using context from feedback and Jira"""
    
    if not client:
        return "Chat functionality requires OpenAI configuration. Please contact your administrator."
    
    # Build context
    feedback_context = ""
    if feedback_data:
        feedback_context = "Related Customer Feedback:\n"
        for i, fb in enumerate(feedback_data[:3], 1):
            feedback_context += f"{i}. [{fb['id']}] {fb['description']} (Team: {fb['team']}, Priority: {fb['priority']})\n"
    
    jira_context = ""
    if jira_data:
        jira_context = "\nRelated Jira Tickets:\n"
        for i, jira in enumerate(jira_data, 1):
            jira_context += f"{i}. [{jira['ticket_id']}] {jira['summary']} (Team: {jira['team']})\n"
    
    context = feedback_context + jira_context
    
    if not context.strip():
        return "I couldn't find any relevant feedback or Jira tickets related to your question. Try rephrasing or asking about a different topic."
    
    prompt = f"""
    You are an AI assistant helping a Product Manager analyze customer feedback and development tickets.
    
    Question: "{question}"
    
    {context}
    
    Based on the related feedback and Jira tickets above, provide a helpful analysis that:
    1. Directly answers the question
    2. References specific feedback IDs or Jira tickets when relevant
    3. Identifies patterns or trends if applicable
    4. Suggests actionable insights for the PM
    
    Keep your response concise but informative (2-3 paragraphs max).
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful product management assistant with access to customer feedback and development ticket data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"⚠️ OpenAI chat response failed: {e}")
        return f"I found relevant data but couldn't generate a detailed response. Error: {str(e)}"

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
    
    if not request.question.strip():
        async def empty_response():
            yield "Please ask a specific question about the feedback data."
        return StreamingResponse(empty_response(), media_type="text/plain")
    
    try:
        # Find related feedback and Jira using robust semantic analyzer
        feedback_matches = semantic_analyzer.find_related_feedback(request.question, top_n=3)
        jira_matches = semantic_analyzer.find_related_jira_tickets(request.question, top_n=2)

        # Build context
        context_parts = []
        if feedback_matches:
            context_parts.append("Related Feedback:")
            for f in feedback_matches[:3]:
                context_parts.append(f"- [{f[1]}] {f[2][:100]}...")
        
        if jira_matches:
            context_parts.append("\nRelated Jira:")
            for j in jira_matches[:2]:
                context_parts.append(f"- [{j[1]}] {j[2][:100]}...")
        
        context_text = "\n".join(context_parts)
        
        prompt = f"""
        You are a product analyst. A PM asked: "{request.question}".
        
        Context from our data:
        {context_text}
        
        Provide a concise, helpful answer based on this context.
        """

        return StreamingResponse(stream_ai_response(prompt), media_type="text/plain")
        
    except Exception as e:
        async def error_response():
            yield f"Error processing request: {str(e)}"
        return StreamingResponse(error_response(), media_type="text/plain")