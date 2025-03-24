import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def init_db():
    """Initialize the SQLite database with necessary tables."""
    DATA_DIR.mkdir(exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(DATA_DIR / "db.sqlite")
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE,
        preferences TEXT,
        language TEXT DEFAULT 'en',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create itineraries table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS itineraries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        destination TEXT,
        start_date TEXT,
        end_date TEXT,
        budget TEXT,
        interests TEXT,
        itinerary_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        itinerary_id INTEGER,
        rating INTEGER,
        comments TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (itinerary_id) REFERENCES itineraries (id)
    )
    ''')
    
    # Create cache table for API responses
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_hash TEXT UNIQUE,
        response_data TEXT,
        api_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Create cache directory
    cache_dir = DATA_DIR / "cache"
    cache_dir.mkdir(exist_ok=True)

# Initialize the database when the module is imported
init_db()

def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DATA_DIR / "db.sqlite")
    conn.row_factory = sqlite3.Row
    return conn