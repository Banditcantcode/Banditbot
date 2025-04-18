import os
import mysql.connector
import sqlite3
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Path to data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', '3307'))
}

def get_mysql_connection():
    """Get a connection to the MySQL database"""
    return mysql.connector.connect(**db_config)

def get_sqlite_connection():
    """Get a connection to the SQLite tickets database"""
    return sqlite3.connect(DATA_DIR / 'tickets.db')

def setup_tickets_database():
    """Create the SQLite tickets database if it doesn't exist"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id TEXT PRIMARY KEY,
        user_id INTEGER,
        channel_id INTEGER,
        category TEXT,
        created_at TIMESTAMP,
        status TEXT
    )
    ''')
    conn.commit()
    conn.close()
    print("Tickets database initialized successfully")


def get_player_from_discord(discord_id):
    """
    Get player information from Discord ID
    
    Args:
        discord_id (str): Discord ID with or without 'discord:' prefix
        
    Returns:
        dict: Player information or None if not found
    """
    if not discord_id.startswith('discord:'):
        discord_id = f"discord:{discord_id}"
    
    conn = None
    cursor = None
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query the users table
        user_query = "SELECT userId, username, license, license2, fivem, discord FROM users WHERE discord = %s"
        cursor.execute(user_query, (discord_id,))
        result = cursor.fetchone()
        
        return result
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_characters(license=None, license2=None, user_id=None):
    """
    Get character information for a player
    
    Args:
        license (str, optional): Player license
        license2 (str, optional): Player license2
        user_id (int, optional): Player userId
        
    Returns:
        list: Character information
    """
    if not license and not license2 and not user_id:
        return []
    
    conn = None
    cursor = None
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        params = []
        conditions = []
        
        if license:
            conditions.append("license = %s")
            params.append(license)
        
        if license2:
            conditions.append("license = %s")
            params.append(license2)
            
        if user_id:
            conditions.append("userId = %s")
            params.append(user_id)
            
        query = f"""
        SELECT id, citizenid, cid, name, charinfo
        FROM players 
        WHERE {" OR ".join(conditions)}
        """
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close() 