from flask import Blueprint, render_template, redirect, url_for, session, request
from speakmate.database import get_db_context

views_bp = Blueprint("views", __name__)

def login_required(f):
    """Decorator to require login on private dashboard pages."""
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

@views_bp.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("views.dashboard"))
    return render_template("landing.html")

@views_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        
        # Retrieve user stats
        cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        user = cursor.fetchone()
        
        # Retrieve recent achievements
        cursor.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC LIMIT 3;", (user_id,))
        achievements = cursor.fetchall()
        
        # Retrieve latest metrics
        cursor.execute("SELECT * FROM progress WHERE user_id = ? ORDER BY date DESC LIMIT 1;", (user_id,))
        latest_progress = cursor.fetchone()
    
    # Defaults in case progress doesn't exist yet
    progress = {
        "grammar_score": latest_progress["grammar_score"] if latest_progress else 50,
        "vocab_score": latest_progress["vocab_score"] if latest_progress else 50,
        "speaking_score": latest_progress["speaking_score"] if latest_progress else 50,
        "confidence_score": latest_progress["confidence_score"] if latest_progress else 50
    }
    
    return render_template(
        "dashboard.html",
        user=user,
        achievements=achievements,
        progress=progress
    )

@views_bp.route("/chat")
@login_required
def chat():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, analysis_json FROM conversation_history 
            WHERE user_id = ? 
            ORDER BY id ASC LIMIT 50;
        """, (user_id,))
        chat_logs = cursor.fetchall()
    
    return render_template("chat.html", chat_logs=chat_logs)

@views_bp.route("/lesson")
@login_required
def lesson():
    return render_template("lesson.html")

@views_bp.route("/vocab")
@login_required
def vocab():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vocabulary WHERE user_id = ? AND saved = 1 ORDER BY last_reviewed DESC;", (user_id,))
        saved_words = cursor.fetchall()
    
    return render_template("vocab.html", saved_words=saved_words)

@views_bp.route("/grammar")
@login_required
def grammar():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic, score, mastery_level FROM grammar WHERE user_id = ?;", (user_id,))
        studied_grammar = cursor.fetchall()
    
    # Convert sqlite Rows to a dict
    grammar_progress = {row['topic']: {"score": row['score'], "mastery": row['mastery_level']} for row in studied_grammar}
    
    return render_template("grammar.html", grammar_progress=grammar_progress)

@views_bp.route("/interview")
@login_required
def interview():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM interview_scores WHERE user_id = ? ORDER BY created_at DESC LIMIT 5;", (user_id,))
        scores = cursor.fetchall()
    
    return render_template("interview.html", scores=scores)

@views_bp.route("/challenges")
@login_required
def challenges():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_challenges WHERE user_id = ? ORDER BY created_at DESC LIMIT 5;", (user_id,))
        completed_challenges = cursor.fetchall()
    
    return render_template("challenges.html", challenges=completed_challenges)

@views_bp.route("/profile")
@login_required
def profile():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        user = cursor.fetchone()
        
        cursor.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY unlocked_at DESC;", (user_id,))
        achievements = cursor.fetchall()
    
    return render_template("profile.html", user=user, achievements=achievements)

@views_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
