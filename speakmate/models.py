from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    target_level = db.Column(db.String(50), default="Intermediate")
    focus_area = db.Column(db.String(100), default="General Conversation")
    streak_count = db.Column(db.Integer, default=0)
    last_active_date = db.Column(db.String(20), nullable=True)
    learning_time_seconds = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "target_level": self.target_level,
            "focus_area": self.focus_area,
            "streak_count": self.streak_count,
            "last_active_date": self.last_active_date,
            "learning_time_seconds": self.learning_time_seconds,
            "created_at": str(self.created_at) if self.created_at else ""
        }

class Lesson(db.Model):
    __tablename__ = "lessons"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="completed")
    score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vocabulary(db.Model):
    __tablename__ = "vocabulary"
    __table_args__ = (db.UniqueConstraint("user_id", "word", name="uq_user_word"),)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    meaning = db.Column(db.Text, nullable=True)
    synonyms = db.Column(db.Text, nullable=True)
    antonyms = db.Column(db.Text, nullable=True)
    examples = db.Column(db.Text, nullable=True)
    saved = db.Column(db.Integer, default=1)
    last_reviewed = db.Column(db.DateTime, default=datetime.utcnow)
    success_rate = db.Column(db.Integer, default=100)

class Grammar(db.Model):
    __tablename__ = "grammar"
    __table_args__ = (db.UniqueConstraint("user_id", "topic", name="uq_user_topic"),)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    mastery_level = db.Column(db.String(50), default="Beginner")
    last_studied = db.Column(db.DateTime, default=datetime.utcnow)

class Progress(db.Model):
    __tablename__ = "progress"
    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_user_date"),)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    grammar_score = db.Column(db.Integer, default=0)
    vocab_score = db.Column(db.Integer, default=0)
    speaking_score = db.Column(db.Integer, default=0)
    confidence_score = db.Column(db.Integer, default=0)
    date = db.Column(db.String(20), nullable=False)

class Achievement(db.Model):
    __tablename__ = "achievements"
    __table_args__ = (db.UniqueConstraint("user_id", "title", name="uq_user_title"),)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    badge_icon = db.Column(db.String(50), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

class ConversationHistory(db.Model):
    __tablename__ = "conversation_history"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    analysis_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InterviewScore(db.Model):
    __tablename__ = "interview_scores"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    confidence = db.Column(db.Integer, nullable=False)
    grammar = db.Column(db.Integer, nullable=False)
    professionalism = db.Column(db.Integer, nullable=False)
    suggestions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyChallenge(db.Model):
    __tablename__ = "daily_challenges"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_type = db.Column(db.String(100), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    user_response = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    feedback_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIMemory(db.Model):
    __tablename__ = "ai_memory"
    __table_args__ = (db.UniqueConstraint("user_id", "memory_type", "content", name="uq_user_memory"),)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    memory_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    occurrences = db.Column(db.Integer, default=1)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
