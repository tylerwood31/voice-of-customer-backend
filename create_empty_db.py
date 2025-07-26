import sqlite3
import os
from config import DB_PATH

def create_empty_database():
    """Create an empty database with the required schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create feedback table with minimal schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                initial_description TEXT,
                notes TEXT,
                priority TEXT,
                team_routed TEXT,
                environment TEXT,
                area_impacted TEXT,
                created TEXT
            )
        ''')
        
        # Insert sample data so the app works
        sample_data = [
            ('demo-1', 'Sample feedback record', '', 'Medium', 'Engineering', 'Production', 'System Issue', '2025-01-20'),
            ('demo-2', 'Another sample record', '', 'High', 'Support', 'Staging', 'User Interface', '2025-01-21'),
            ('demo-3', 'Third demo record', '', 'Low', 'Marketing', 'Development', 'Documentation', '2025-01-22'),
            ('demo-4', 'Customer login issues reported', '', 'High', 'Engineering', 'Production', 'Authentication', '2025-01-23'),
            ('demo-5', 'UI responsiveness problems on mobile', '', 'Medium', 'Design', 'Production', 'Mobile App', '2025-01-24'),
            ('demo-6', 'Database query performance degradation', '', 'High', 'Engineering', 'Production', 'Database', '2025-01-25'),
            ('demo-7', 'Feature request for bulk operations', '', 'Low', 'Product', 'Staging', 'Features', '2025-01-26')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO feedback 
            (id, initial_description, notes, priority, team_routed, environment, area_impacted, created)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_data)
        
        conn.commit()
        conn.close()
        print(f"✅ Database created at {DB_PATH}")
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")

if __name__ == "__main__":
    create_empty_database()