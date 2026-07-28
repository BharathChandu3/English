from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from speakmate.database import get_db_context

auth_bp = Blueprint("auth", __name__)

def update_daily_streak(user_id):
    """
    Updates the user's daily streak count when they log in or perform actions.
    If they active today, streak stays. If yesterday, increment. If older, reset to 1.
    """
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT streak_count, last_active_date FROM users WHERE id = ?;", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return
                
            current_streak = user['streak_count'] or 0
            last_active_str = user['last_active_date']
            
            today = date.today()
            today_str = today.strftime("%Y-%m-%d")
            
            if not last_active_str:
                # First active day
                new_streak = 1
                cursor.execute("UPDATE users SET streak_count = ?, last_active_date = ? WHERE id = ?;", (new_streak, today_str, user_id))
            else:
                last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
                delta = (today - last_active).days
                
                if delta == 1:
                    # Active consecutive day
                    new_streak = current_streak + 1
                    cursor.execute("UPDATE users SET streak_count = ?, last_active_date = ? WHERE id = ?;", (new_streak, today_str, user_id))
                    
                    # Check for streak achievements
                    unlock_streak_achievements(user_id, new_streak, cursor)
                elif delta > 1:
                    # Streak broken
                    new_streak = 1
                    cursor.execute("UPDATE users SET streak_count = ?, last_active_date = ? WHERE id = ?;", (new_streak, today_str, user_id))
                else:
                    # Already active today, maintain streak
                    new_streak = current_streak
                    cursor.execute("UPDATE users SET last_active_date = ? WHERE id = ?;", (today_str, user_id))
                    
            session['streak_count'] = new_streak
    except Exception as e:
        print(f"Error updating streak: {e}")

def unlock_streak_achievements(user_id, streak, cursor):
    """Helper to unlock achievements based on streak milestones."""
    milestones = {
        3: ("Consistency Starter", "Studied for 3 consecutive days!", "🔥"),
        7: ("Fluency Fanatic", "Maintained a 7-day study streak!", "⚡"),
        30: ("SpeakMate Master", "Incredible 30-day English speaking streak!", "👑")
    }
    
    if streak in milestones:
        title, desc, icon = milestones[streak]
        cursor.execute("""
        INSERT INTO achievements (user_id, title, description, badge_icon)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, title) DO NOTHING;
        """, (user_id, title, desc, icon))

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
        
        with get_db_context() as conn:
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?;", (username, email))
            if cursor.fetchone():
                flash("Username or Email already registered.", "error")
                return render_template("register.html")
                
            try:
                cursor.execute("""
                INSERT INTO users (username, email, password_hash, target_level, focus_area, streak_count, last_active_date)
                VALUES (?, ?, ?, ?, ?, 1, ?);
                """, (username, email, password_hash, target_level, focus_area, date.today().strftime("%Y-%m-%d")))
                
                user_id = cursor.lastrowid
                
                # Create a welcoming achievement
                cursor.execute("""
                INSERT INTO achievements (user_id, title, description, badge_icon)
                VALUES (?, 'Hello World!', 'Completed registration and started your English journey.', '🚀');
                """, (user_id,))
                
                # Setup initial progress metric
                cursor.execute("""
                INSERT INTO progress (user_id, grammar_score, vocab_score, speaking_score, confidence_score, date)
                VALUES (?, 50, 50, 50, 50, ?);
                """, (user_id, date.today().strftime("%Y-%m-%d")))
                
                # Setup first welcome conversation history
                welcome_text = (
                    "👋 Welcome to SpeakMate AI!\n\n"
                    "I'm your personal AI English Coach. My goal is to help you become a fluent "
                    "and confident English speaker. Don't worry about making mistakes. Let's begin!\n\n"
                    "Please introduce yourself in 5–10 sentences. I'll analyze your response."
                )
                cursor.execute("""
                INSERT INTO conversation_history (user_id, role, content)
                VALUES (?, 'assistant', ?);
                """, (user_id, welcome_text))
                
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("auth.login"))
                
            except Exception as e:
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
            
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?;", (username, username))
            user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['target_level'] = user['target_level']
            session['focus_area'] = user['focus_area']
            
            # Refresh daily streak
            update_daily_streak(user['id'])
            
            return redirect(url_for("views.dashboard"))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("views.landing"))
