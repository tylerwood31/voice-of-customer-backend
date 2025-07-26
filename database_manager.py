#!/usr/bin/env python3
"""
Robust database manager for Voice of Customer backend
Handles initialization, health checks, and data persistence
"""
import sqlite3
import os
import hashlib
import csv
from datetime import datetime
from config import DB_PATH, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.health_status = {"database": False, "tables": False, "jira_data": False}
    
    def get_health_status(self):
        """Get current health status of database components"""
        return self.health_status
    
    def test_connection(self) -> bool:
        """Test if database connection works"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            self.health_status["database"] = True
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.health_status["database"] = False
            return False
    
    def create_tables(self) -> bool:
        """Create all required tables with proper schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create feedback table with all required fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    initial_description TEXT,
                    notes TEXT,
                    priority TEXT,
                    team_routed TEXT,
                    environment TEXT,
                    area_impacted TEXT,
                    created TEXT,
                    issue_number TEXT,
                    status TEXT,
                    reporter_email TEXT,
                    slack_thread TEXT,
                    type_of_issue TEXT,
                    triage_rep TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create jira_tickets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jira_tickets (
                    id TEXT PRIMARY KEY,
                    summary TEXT,
                    description TEXT,
                    resolution TEXT,
                    assignee TEXT,
                    team_name TEXT,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create cache_metadata table for tracking updates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            self.health_status["tables"] = True
            print("✅ All database tables created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Table creation failed: {e}")
            self.health_status["tables"] = False
            return False
    
    def init_default_users(self) -> bool:
        """Initialize default users if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Default users
            default_users = [
                ('admin@coverwallet.com', 'Admin User', 'admin', 'coverwallet2025'),
                ('tyler.wood@coverwallet.com', 'Tyler Wood', 'super_admin', 'superadmin2025')
            ]
            
            for email, name, role, password in default_users:
                # Check if user exists
                cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
                if not cursor.fetchone():
                    # Create password hash
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    
                    cursor.execute(
                        'INSERT INTO users (email, name, role, password_hash) VALUES (?, ?, ?, ?)',
                        (email, name, role, password_hash)
                    )
                    print(f"✅ Created default user: {email}")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Default user creation failed: {e}")
            return False
    
    def load_jira_data(self) -> bool:
        """Load Jira tickets from CSV if not already loaded"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we already have Jira data
            cursor.execute("SELECT COUNT(*) FROM jira_tickets")
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                print(f"✅ Jira tickets already loaded ({existing_count} records)")
                self.health_status["jira_data"] = True
                conn.close()
                return True
            
            # Load from CSV - try multiple possible paths
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "data", "jira_tickets.csv"),
                os.path.join(os.getcwd(), "data", "jira_tickets.csv"),
                "data/jira_tickets.csv",
                "./data/jira_tickets.csv"
            ]
            
            csv_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    csv_path = path
                    break
            
            if not csv_path:
                print(f"⚠️ Jira CSV not found in any of these locations: {possible_paths}")
                conn.close()
                return False
            
            print(f"📂 Loading Jira tickets from {csv_path}")
            loaded_count = 0
            
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # Extract fields
                    issue_id = (row.get('Issue id') or row.get('Issue ID') or 
                               row.get('Key') or row.get('Issue Key') or '').strip()
                    
                    if not issue_id:
                        continue
                    
                    summary = (row.get('Summary') or row.get('Title') or '').strip()
                    description = (row.get('Description') or '').strip()
                    resolution = (row.get('Resolution') or '').strip()
                    assignee = (row.get('Assignee') or '').strip()
                    team_name = (row.get('Team Name') or row.get('Team') or 
                                row.get('Component/s') or '').strip()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO jira_tickets 
                        (id, summary, description, resolution, assignee, team_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (issue_id, summary, description, resolution, assignee, team_name))
                    
                    loaded_count += 1
            
            # Update metadata
            cursor.execute("""
                INSERT OR REPLACE INTO cache_metadata (key, value)
                VALUES ('jira_last_loaded', ?)
            """, (datetime.now().isoformat(),))
            
            conn.commit()
            
            # Get final counts
            cursor.execute("SELECT COUNT(*) FROM jira_tickets")
            total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM jira_tickets 
                WHERE team_name IS NOT NULL AND team_name != ''
            """)
            with_teams = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"✅ Loaded {loaded_count} Jira tickets!")
            print(f"📊 Total: {total}, With teams: {with_teams}")
            self.health_status["jira_data"] = True
            return True
            
        except Exception as e:
            print(f"❌ Jira data loading failed: {e}")
            self.health_status["jira_data"] = False
            return False
    
    def get_last_feedback_update(self) -> str:
        """Get timestamp of last feedback update"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value FROM cache_metadata 
                WHERE key = 'last_feedback_update'
            """)
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else "1970-01-01T00:00:00.000Z"
            
        except Exception as e:
            print(f"⚠️ Could not get last update timestamp: {e}")
            return "1970-01-01T00:00:00.000Z"
    
    def update_last_feedback_timestamp(self, timestamp: str):
        """Update the last feedback update timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO cache_metadata (key, value)
                VALUES ('last_feedback_update', ?)
            """, (timestamp,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Could not update timestamp: {e}")
    
    def initialize_all(self) -> bool:
        """Initialize entire database system"""
        print("🚀 Initializing database system...")
        
        success = True
        
        # Test connection
        if not self.test_connection():
            success = False
        
        # Create tables
        if success and not self.create_tables():
            success = False
        
        # Initialize users
        if success and not self.init_default_users():
            success = False
        
        # Load Jira data
        if success and not self.load_jira_data():
            success = False
        
        if success:
            print("✅ Database initialization completed successfully")
        else:
            print("❌ Database initialization had errors")
        
        return success

# Global database manager instance
db_manager = DatabaseManager()

def get_database_health():
    """Get database health status for API endpoints"""
    return db_manager.get_health_status()

def initialize_database():
    """Initialize database - called during startup"""
    return db_manager.initialize_all()