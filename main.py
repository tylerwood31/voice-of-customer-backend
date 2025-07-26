from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feedback, teams, components, chat, customer_pulse, ai_summary, reports, users, airtable_test, cache_status, health
import os

app = FastAPI(title="Voice of Customer API")

# Initialize database on startup
@app.on_event("startup") 
async def startup_event():
    print("🚀 Starting Voice of Customer API...")
    
    try:
        # Use robust database manager
        from database_manager import initialize_database
        
        # Initialize database system with full error handling
        success = initialize_database()
        
        if success:
            print("✅ Database system initialized successfully")
        else:
            print("⚠️ Database initialization had issues but API will continue")
        
        # Initialize cache system (will be non-blocking)
        try:
            print("🔄 Initializing cache system...")
            # This will be replaced with intelligent cache system
            pass
        except Exception as cache_error:
            print(f"⚠️ Cache initialization warning (non-blocking): {cache_error}")
        
        print("🎉 Voice of Customer API startup completed")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        print("🔄 Attempting minimal fallback initialization...")
        
        # Minimal fallback
        try:
            import sqlite3
            from config import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create essential tables
            cursor.execute("""CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY, 
                initial_description TEXT, 
                notes TEXT, 
                priority TEXT, 
                team_routed TEXT, 
                environment TEXT, 
                area_impacted TEXT, 
                created TEXT
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")
            
            conn.commit()
            conn.close()
            print("✅ Minimal fallback database created")
            
        except Exception as fallback_error:
            print(f"❌ Fallback failed: {fallback_error}")
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
app.include_router(airtable_test.router, prefix="/test-airtable", tags=["Testing"])
app.include_router(cache_status.router, prefix="/cache", tags=["Cache"])
app.include_router(health.router, prefix="/health", tags=["Health"])

@app.get("/")
def root():
    return {"message": "Voice of Customer API is running."}