from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feedback, teams, components, chat, customer_pulse, ai_summary, reports, users, health
import os

app = FastAPI(title="Voice of Customer API")

# Initialize database on startup
@app.on_event("startup") 
async def startup_event():
    print("🚀 Starting Voice of Customer API...")
    
    try:
        # Verify database exists and is accessible
        import sqlite3
        from config import DB_PATH
        
        print(f"📁 Using database at: {DB_PATH}")
        
        # Test database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if feedback table exists and has data
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='feedback'")
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM feedback")
            record_count = cursor.fetchone()[0]
            print(f"✅ Database connected successfully: {record_count} feedback records found")
        else:
            print("⚠️ Feedback table not found in database")
        
        # Ensure users table exists for authentication
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        
        conn.commit()
        conn.close()
        
        # Initialize Jira vectorization for team assignments (optional)
        try:
            print("🤖 Checking Jira vectorization status...")
            from semantic_analyzer import semantic_analyzer
            vectorization_status = semantic_analyzer.get_vectorization_status()
            print(f"📊 Jira tickets: {vectorization_status.get('vectorized_tickets', 0)}/{vectorization_status.get('total_tickets', 0)} vectorized")
            
            if vectorization_status.get('total_tickets', 0) == 0:
                print("⚠️ No Jira tickets found - team assignment will use fallback methods")
        except Exception as jira_error:
            print(f"⚠️ Jira vectorization check failed (non-blocking): {jira_error}")
        
        print("🎉 Voice of Customer API startup completed")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        print("⚠️ API starting with potential database issues")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://localhost:3001", 
        "http://127.0.0.1:3001", 
        "http://localhost:3002", 
        "http://127.0.0.1:3002",
        "https://voice-of-customer.netlify.app",
        "https://*.voice-of-customer.netlify.app",
        "https://cw-voc-v1.netlify.app",
        "https://*.cw-voc-v1.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(teams.router, prefix="/teams", tags=["Teams"])
app.include_router(components.router, prefix="/components", tags=["Components"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(customer_pulse.router, prefix="/customer-pulse", tags=["Analytics"])
app.include_router(ai_summary.router, prefix="/ai-summary", tags=["AI"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(health.router, prefix="/health", tags=["Health"])

@app.get("/")
def root():
    return {"message": "Voice of Customer API is running."}