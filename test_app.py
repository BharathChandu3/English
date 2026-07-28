# SpeakMate AI Backend Verification Test
import sys
import os

def test_imports():
    print("Testing module imports...")
    try:
        from speakmate.config import Config
        print("[OK] Config imported successfully.")
        
        from speakmate.database import get_db_connection, init_db
        print("[OK] Database modules imported successfully.")
        
        from speakmate.services.gemini_service import GeminiService
        from speakmate.services.memory_service import MemoryService
        print("[OK] Service layers imported successfully.")
        
        from speakmate.routes.auth import auth_bp
        from speakmate.routes.views import views_bp
        from speakmate.routes.api import api_bp
        print("[OK] Blueprint modules imported successfully.")
        
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    print("\nTesting database initialization...")
    try:
        from speakmate.database import init_db, get_db_connection
        init_db()
        print("[OK] Database schema initialized successfully.")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test table listing
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Detected tables: {', '.join(tables)}")
        
        expected_tables = ["users", "lessons", "vocabulary", "grammar", "progress", "achievements", "conversation_history", "interview_scores", "daily_challenges", "ai_memory"]
        missing = [t for t in expected_tables if t not in tables]
        
        if not missing:
            print("[OK] All 10 tables are present in the SQLite schema!")
            conn.close()
            return True
        else:
            print(f"[FAIL] Missing tables: {missing}")
            conn.close()
            return False
            
    except Exception as e:
        print(f"[FAIL] Database test failed: {e}")
        return False

def test_gemini_fallback():
    print("\nTesting Gemini response wrapper fallbacks...")
    try:
        from speakmate.services.gemini_service import GeminiService
        # Triggering a request to verify structured dictionary formats
        feedback = GeminiService.get_conversation_feedback([], "Hello tutor! Let's practice English.")
        
        if feedback and "reply" in feedback and "feedback" in feedback:
            print("[OK] Gemini Service fallback output structure is verified!")
            return True
        else:
            print("[FAIL] Gemini Service output is corrupt or missing keys.")
            return False
    except Exception as e:
        print(f"[FAIL] Gemini Service evaluation test failed: {e}")
        return False

if __name__ == "__main__":
    print("====== SPEAKMATE AI VERIFICATION BOOT ======")
    imports_ok = test_imports()
    db_ok = test_database()
    gemini_ok = test_gemini_fallback()
    
    print("\n====== VERIFICATION SUMMARY ======")
    if imports_ok and db_ok and gemini_ok:
        print("ALL SYSTEMS GO! SpeakMate AI is fully ready for deployment.")
        sys.exit(0)
    else:
        print("Some checks failed. Please inspect errors above.")
        sys.exit(1)

