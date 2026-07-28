import sqlite3
import os
from contextlib import contextmanager
from speakmate.config import Config

def get_db_connection():
    """Establishes connection to the SQLite database with WAL mode and busy timeout for concurrency."""
    conn = sqlite3.connect(Config.DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    # WAL mode allows concurrent readers and one writer — prevents 'database is locked'
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

@contextmanager
def get_db_context():
    """Context manager that auto-commits on success and GUARANTEES closing the DB connection."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes the database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        target_level TEXT DEFAULT 'Intermediate',
        focus_area TEXT DEFAULT 'General Conversation',
        streak_count INTEGER DEFAULT 0,
        last_active_date TEXT,
        learning_time_seconds INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Lessons Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        status TEXT DEFAULT 'completed',
        score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 3. Vocabulary Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocabulary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        meaning TEXT,
        synonyms TEXT,
        antonyms TEXT,
        examples TEXT,
        saved INTEGER DEFAULT 1,
        last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        success_rate INTEGER DEFAULT 100,
        UNIQUE(user_id, word),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 4. Grammar Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grammar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic TEXT NOT NULL,
        score INTEGER DEFAULT 0,
        mastery_level TEXT DEFAULT 'Beginner',
        last_studied TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, topic),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 5. Progress Table (daily tracker for charts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        grammar_score INTEGER DEFAULT 0,
        vocab_score INTEGER DEFAULT 0,
        speaking_score INTEGER DEFAULT 0,
        confidence_score INTEGER DEFAULT 0,
        date TEXT NOT NULL,
        UNIQUE(user_id, date),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 6. Achievements Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        badge_icon TEXT NOT NULL,
        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, title),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 7. Conversation History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        analysis_json TEXT, -- Stores JSON feedback
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 8. Interview Scores Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL, -- HR, Technical, Behavioral, Communication
        score INTEGER NOT NULL,
        confidence INTEGER NOT NULL,
        grammar INTEGER NOT NULL,
        professionalism INTEGER NOT NULL,
        suggestions TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 9. Daily Challenges Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        challenge_type TEXT NOT NULL, -- Picture, Storytelling, One Minute, Debate, Presentation, Opinion
        prompt_text TEXT NOT NULL,
        user_response TEXT NOT NULL,
        score INTEGER NOT NULL,
        feedback_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # 10. AI Memory Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        memory_type TEXT NOT NULL, -- weak_grammar, weak_vocab, recurring_mistakes
        content TEXT NOT NULL,
        occurrences INTEGER DEFAULT 1,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, memory_type, content),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
