from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feedback, teams, components, chat, customer_pulse, ai_summary, reports
import os

app = FastAPI(title="Voice of Customer API")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        from create_empty_db import create_empty_database
        create_empty_database()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")

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
        "https://cw-voc-v1.netlify.app"
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

@app.get("/")
def root():
    return {"message": "Voice of Customer API is running."}