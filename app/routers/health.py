from fastapi import APIRouter
from datetime import datetime, timezone
import os
import sqlite3
import requests
from config import DB_PATH, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, OPENAI_API_KEY

router = APIRouter()

@router.get("/", summary="System health check")
def get_health_status():
    """Comprehensive health check for all system components."""
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": check_database_health(),
            "airtable": check_airtable_health(),
            "openai": check_openai_health(),
            "environment": check_environment_health()
        }
    }
    
    # Overall status
    component_statuses = [comp["status"] for comp in health["components"].values()]
    if "error" in component_statuses:
        health["status"] = "degraded"
    elif "warning" in component_statuses:
        health["status"] = "warning"
    
    return health

def check_database_health():
    """Check database connectivity and table existence."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Test basic connectivity
        cursor.execute("SELECT 1")
        
        # Check required tables
        tables = ["feedback", "users", "jira_tickets", "cache_metadata"]
        existing_tables = []
        
        for table in tables:
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            if cursor.fetchone():
                existing_tables.append(table)
        
        # Check data counts
        counts = {}
        for table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "healthy",
            "database_path": DB_PATH,
            "tables_found": existing_tables,
            "tables_expected": tables,
            "record_counts": counts
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_path": DB_PATH
        }

def check_airtable_health():
    """Check Airtable API connectivity."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        return {
            "status": "error",
            "error": "Airtable credentials not configured"
        }
    
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Lead%20Bugs"
        headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
        params = {"pageSize": 1}  # Just test with 1 record
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            record_count = len(data.get("records", []))
            
            return {
                "status": "healthy",
                "base_id": AIRTABLE_BASE_ID,
                "table_name": "Lead Bugs",
                "test_record_count": record_count,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000)
            }
        else:
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def check_openai_health():
    """Check OpenAI API connectivity."""
    if not OPENAI_API_KEY:
        return {
            "status": "warning",
            "error": "OpenAI API key not configured"
        }
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Simple test call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=1
        )
        
        return {
            "status": "healthy",
            "model": "gpt-4o-mini",
            "test_successful": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def check_environment_health():
    """Check environment configuration."""
    env_vars = {
        "DATABASE_PATH": os.getenv("DATABASE_PATH"),
        "AIRTABLE_API_KEY": "***" if AIRTABLE_API_KEY else None,
        "AIRTABLE_BASE_ID": AIRTABLE_BASE_ID,
        "OPENAI_API_KEY": "***" if OPENAI_API_KEY else None
    }
    
    missing_vars = [k for k, v in env_vars.items() if v is None]
    
    status = "healthy"
    if missing_vars:
        status = "warning" if len(missing_vars) < len(env_vars) else "error"
    
    return {
        "status": status,
        "environment_variables": env_vars,
        "missing_variables": missing_vars,
        "database_accessible": os.path.exists(DB_PATH) if os.path.dirname(DB_PATH) else True
    }

@router.get("/quick", summary="Quick health check")
def quick_health():
    """Quick health check for load balancers."""
    try:
        # Just test database connectivity
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {"status": "error", "error": str(e)}