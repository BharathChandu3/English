from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from speakmate.models import db, User, Achievement, Progress, ConversationHistory

auth_bp = Blueprint("auth", __name__)

def update_daily_streak(user_id):
    """
    Updates the user's daily streak count when they log in or perform actions.
    If active today, streak stays. If yesterday, increment. If older, reset to 1.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return
            
        current_streak = user.streak_count or 0
        last_active_str = user.last_active_date
        
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        if not last_active_str:
            new_streak = 1
            user.streak_count = new_streak
            user.last_active_date = today_str
        else:
            try:
                last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
                delta = (today - last_active).days
            except ValueError:
                delta = 2

            if delta == 1:
                new_streak = current_streak + 1
                user.streak_count = new_streak
                user.last_active_date = today_str
                unlock_streak_achievements(user_id, new_streak)
            elif delta > 1:
                new_streak = 1
                user.streak_count = new_streak
                user.last_active_date = today_str
            else:
                new_streak = current_streak
                user.last_active_date = today_str
                
        db.session.commit()
        session['streak_count'] = new_streak
    except Exception as e:
        db.session.rollback()
        print(f"Error updating streak: {e}")

def unlock_streak_achievements(user_id, streak):
    """Helper to unlock achievements based on streak milestones."""
    milestones = {
        3: ("Consistency Starter", "Studied for 3 consecutive days!", "🔥"),
        7: ("Fluency Fanatic", "Maintained a 7-day study streak!", "⚡"),
        30: ("SpeakMate Master", "Incredible 30-day English speaking streak!", "👑")
    }
    
    if streak in milestones:
        title, desc, icon = milestones[streak]
        existing = Achievement.query.filter_by(user_id=user_id, title=title).first()
        if not existing:
            achievement = Achievement(user_id=user_id, title=title, description=desc, badge_icon=icon)
            db.session.add(achievement)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("views.dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password")
        target_level = request.form.get("target_level", "Intermediate")
        focus_area = request.form.get("focus_area", "General Conversation")
        
        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")
            
        password_hash = generate_password_hash(password)
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or Email already registered.", "error")
            return render_template("register.html")
            
        try:
            today_str = date.today().strftime("%Y-%m-%d")
            new_user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                target_level=target_level,
                focus_area=focus_area,
                streak_count=1,
                last_active_date=today_str
            )
            db.session.add(new_user)
            db.session.flush() # Populate new_user.id
            
            # Welcome achievement
            welcome_badge = Achievement(
                user_id=new_user.id,
                title="Hello World!",
                description="Completed registration and started your English journey.",
                badge_icon="🚀"
            )
            db.session.add(welcome_badge)
            
            # Initial progress snapshot
            init_progress = Progress(
                user_id=new_user.id,
                grammar_score=50,
                vocab_score=50,
                speaking_score=50,
                confidence_score=50,
                date=today_str
            )
            db.session.add(init_progress)
            
            # Initial welcome message in conversation history
            welcome_text = (
                "👋 Welcome to SpeakMate AI!\n\n"
                "I'm your personal AI English Coach. My goal is to help you become a fluent "
                "and confident English speaker. Don't worry about making mistakes. Let's begin!\n\n"
                "Please introduce yourself in 5–10 sentences. I'll analyze your response."
            )
            welcome_chat = ConversationHistory(
                user_id=new_user.id,
                role="assistant",
                content=welcome_text
            )
            db.session.add(welcome_chat)
            
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("auth.login"))
            
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration.", "error")
            print(f"Registration Error: {e}")
            
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("views.dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        
        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("login.html")
            
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['target_level'] = user.target_level
            session['focus_area'] = user.focus_area
            
            # Refresh daily streak
            update_daily_streak(user.id)
            
            return redirect(url_for("views.dashboard"))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("views.landing"))
