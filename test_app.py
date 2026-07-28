# SpeakMate AI Backend Verification Test
import sys
import os

def test_imports():
    print("Testing module imports...")
    try:
        from speakmate.config import Config
        print("[OK] Config imported successfully.")
        
        from speakmate.models import db, User, Lesson, Vocabulary, Grammar, Progress, Achievement, ConversationHistory, InterviewScore, DailyChallenge, AIMemory
        print("[OK] SQLAlchemy models imported successfully.")
        
        from speakmate.database import init_db
        print("[OK] Database module imported successfully.")
        
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
    print("\nTesting database initialization and ORM operations...")
    try:
        from speakmate.app import app
        from speakmate.models import db, User, Achievement
        from speakmate.services.memory_service import MemoryService
        
        with app.app_context():
            db.create_all()
            print("[OK] Database schema created successfully via SQLAlchemy!")
            
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Detected tables: {', '.join(tables)}")
            
            expected_tables = ["users", "lessons", "vocabulary", "grammar", "progress", "achievements", "conversation_history", "interview_scores", "daily_challenges", "ai_memory"]
            missing = [t for t in expected_tables if t not in tables]
            
            if missing:
                print(f"[FAIL] Missing tables: {missing}")
                return False
                
            print("[OK] All 10 tables are present in the SQLAlchemy schema!")
            
            # ORM CRUD test
            test_user = User.query.filter_by(username="test_verification_user").first()
            if not test_user:
                test_user = User(
                    username="test_verification_user",
                    email="test_verification@example.com",
                    password_hash="pbkdf2:sha256:dummyhash",
                    target_level="Intermediate"
                )
                db.session.add(test_user)
                db.session.commit()
                print("[OK] Test user created via SQLAlchemy ORM.")
            else:
                print("[OK] Existing test user loaded via SQLAlchemy ORM.")

            # Test MemoryService operations
            fake_feedback = {
                "feedback": {
                    "mistakes": ["Subject verb agreement error: 'They is' -> 'They are'"],
                    "new_vocabulary": [{"word": "eloquent", "meaning": "fluent or persuasive in speaking"}]
                }
            }
            MemoryService.update_memory_from_feedback(test_user.id, fake_feedback)
            summary = MemoryService.get_memory_summary(test_user.id)
            print(f"[OK] MemoryService summary generated: '{summary[:70]}...'")
            
            return True
            
    except Exception as e:
        print(f"[FAIL] Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gemini_fallback():
    print("\nTesting Gemini response wrapper fallbacks...")
    try:
        from speakmate.services.gemini_service import GeminiService
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
