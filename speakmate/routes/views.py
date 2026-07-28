from flask import Blueprint, render_template, redirect, url_for, session, request
from speakmate.models import db, User, Achievement, Progress, ConversationHistory, Vocabulary, Grammar, InterviewScore, DailyChallenge

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
    user = User.query.get(user_id)
    achievements = Achievement.query.filter_by(user_id=user_id).order_by(Achievement.unlocked_at.desc()).limit(3).all()
    latest_progress = Progress.query.filter_by(user_id=user_id).order_by(Progress.date.desc()).first()
    
    # Defaults in case progress doesn't exist yet
    progress = {
        "grammar_score": latest_progress.grammar_score if latest_progress else 50,
        "vocab_score": latest_progress.vocab_score if latest_progress else 50,
        "speaking_score": latest_progress.speaking_score if latest_progress else 50,
        "confidence_score": latest_progress.confidence_score if latest_progress else 50
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
    chat_logs = ConversationHistory.query.filter_by(user_id=user_id).order_by(ConversationHistory.id.asc()).limit(50).all()
    return render_template("chat.html", chat_logs=chat_logs)

@views_bp.route("/lesson")
@login_required
def lesson():
    return render_template("lesson.html")

@views_bp.route("/vocab")
@login_required
def vocab():
    user_id = session["user_id"]
    saved_words = Vocabulary.query.filter_by(user_id=user_id, saved=1).order_by(Vocabulary.last_reviewed.desc()).all()
    return render_template("vocab.html", saved_words=saved_words)

@views_bp.route("/grammar")
@login_required
def grammar():
    user_id = session["user_id"]
    studied_grammar = Grammar.query.filter_by(user_id=user_id).all()
    grammar_progress = {row.topic: {"score": row.score, "mastery": row.mastery_level} for row in studied_grammar}
    return render_template("grammar.html", grammar_progress=grammar_progress)

@views_bp.route("/interview")
@login_required
def interview():
    user_id = session["user_id"]
    scores = InterviewScore.query.filter_by(user_id=user_id).order_by(InterviewScore.created_at.desc()).limit(5).all()
    return render_template("interview.html", scores=scores)

@views_bp.route("/challenges")
@login_required
def challenges():
    user_id = session["user_id"]
    completed_challenges = DailyChallenge.query.filter_by(user_id=user_id).order_by(DailyChallenge.created_at.desc()).limit(5).all()
    return render_template("challenges.html", challenges=completed_challenges)

@views_bp.route("/profile")
@login_required
def profile():
    user_id = session["user_id"]
    user = User.query.get(user_id)
    achievements = Achievement.query.filter_by(user_id=user_id).order_by(Achievement.unlocked_at.desc()).all()
    return render_template("profile.html", user=user, achievements=achievements)

@views_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
