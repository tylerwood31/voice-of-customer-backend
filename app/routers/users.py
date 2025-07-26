from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
import hashlib
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from config import DB_PATH

router = APIRouter()

class User(BaseModel):
    email: str
    name: str
    role: str

class UserCreate(BaseModel):
    email: str
    name: str
    role: str
    password: str

class UserUpdate(BaseModel):
    name: str
    role: str
    password: str = None

def init_users_table():
    """Initialize users table and create default users"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default users if they don't exist
        default_users = [
            ('admin@coverwallet.com', 'Admin User', 'admin', 'coverwallet2025'),
            ('tyler.wood@coverwallet.com', 'Tyler Wood', 'super_admin', 'superadmin2025')
        ]
        
        for email, name, role, password in default_users:
            # Check if user already exists
            cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
            if not cursor.fetchone():
                # Hash the password
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute(
                    'INSERT INTO users (email, name, role, password_hash) VALUES (?, ?, ?, ?)',
                    (email, name, role, password_hash)
                )
        
        conn.commit()
        conn.close()
        print("✅ Users table initialized")
        
    except Exception as e:
        print(f"❌ Error initializing users table: {e}")

@router.get("/", summary="Get all users")
def get_users():
    """Get all users"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Initialize table if it doesn't exist
        init_users_table()
        
        cursor.execute('SELECT email, name, role FROM users ORDER BY email')
        users = cursor.fetchall()
        conn.close()
        
        return [{"email": user[0], "name": user[1], "role": user[2]} for user in users]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/", summary="Create a new user")
def create_user(user: UserCreate):
    """Create a new user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Initialize table if it doesn't exist
        init_users_table()
        
        # Check if user already exists
        cursor.execute('SELECT email FROM users WHERE email = ?', (user.email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="User with this email already exists")
        
        # Hash the password
        password_hash = hashlib.sha256(user.password.encode()).hexdigest()
        
        # Insert new user
        cursor.execute(
            'INSERT INTO users (email, name, role, password_hash) VALUES (?, ?, ?, ?)',
            (user.email, user.name, user.role, password_hash)
        )
        
        conn.commit()
        conn.close()
        
        return {"message": f"User {user.email} created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{email}", summary="Delete a user")
def delete_user(email: str):
    """Delete a user by email"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Initialize table if it doesn't exist
        init_users_table()
        
        # Check if user exists
        cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE email = ?', (email,))
        
        conn.commit()
        conn.close()
        
        return {"message": f"User {email} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{email}", summary="Update a user")
def update_user(email: str, user_update: UserUpdate):
    """Update a user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Initialize table if it doesn't exist
        init_users_table()
        
        # Check if user exists
        cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user
        if user_update.password:
            # Update with new password
            password_hash = hashlib.sha256(user_update.password.encode()).hexdigest()
            cursor.execute(
                'UPDATE users SET name = ?, role = ?, password_hash = ? WHERE email = ?',
                (user_update.name, user_update.role, password_hash, email)
            )
        else:
            # Update without changing password
            cursor.execute(
                'UPDATE users SET name = ?, role = ? WHERE email = ?',
                (user_update.name, user_update.role, email)
            )
        
        conn.commit()
        conn.close()
        
        return {"message": f"User {email} updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

class UserAuth(BaseModel):
    email: str
    password: str

@router.post("/auth", summary="Authenticate a user")
def authenticate_user(auth: UserAuth):
    """Authenticate a user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Initialize table if it doesn't exist
        init_users_table()
        
        # Hash the provided password
        password_hash = hashlib.sha256(auth.password.encode()).hexdigest()
        
        # Check credentials
        cursor.execute(
            'SELECT email, name, role FROM users WHERE email = ? AND password_hash = ?',
            (auth.email, password_hash)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {"email": user[0], "name": user[1], "role": user[2]}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")