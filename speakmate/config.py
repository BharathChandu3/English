import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "speakmate-super-secret-key-132@#$")
    
    # SQLite Database Config (local file path)
    # Easily swap to MySQL/Postgres by editing connection string in production
    DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "speakmate.db"))
    
    # Gemini API Credentials
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    # gemini-3.1-flash-lite confirmed as the working model
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"
    GEMINI_STANDARD_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"
