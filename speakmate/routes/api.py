import json
from flask import Blueprint, request, jsonify, session
from datetime import date
from speakmate.database import get_db_context
from speakmate.services.gemini_service import GeminiService
from speakmate.services.memory_service import MemoryService

api_bp = Blueprint("api", __name__)

def api_login_required(f):
    """Decorator to require login for API routes."""
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized session. Please login."}), 401
        return f(*args, **kwargs)
    return decorated_function

def update_progress_metric(user_id, metric_name, value):
    """
    Helper to update or create a daily progress snapshot.
    Ensures charts reflect progress changes dynamically.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM progress WHERE user_id = ? AND date = ?;", (user_id, today_str))
        row = cursor.fetchone()
        
        if row:
            cursor.execute(f"""
            UPDATE progress SET {metric_name} = ? WHERE user_id = ? AND date = ?;
            """, (value, user_id, today_str))
        else:
            cursor.execute("SELECT * FROM progress WHERE user_id = ? ORDER BY date DESC LIMIT 1;", (user_id,))
            last = cursor.fetchone()
            
            grammar = last["grammar_score"] if last else 50
            vocab = last["vocab_score"] if last else 50
            speaking = last["speaking_score"] if last else 50
            confidence = last["confidence_score"] if last else 50
            
            scores = {"grammar_score": grammar, "vocab_score": vocab, "speaking_score": speaking, "confidence_score": confidence}
            scores[metric_name] = value
            
            cursor.execute("""
            INSERT INTO progress (user_id, grammar_score, vocab_score, speaking_score, confidence_score, date)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (user_id, scores["grammar_score"], scores["vocab_score"], scores["speaking_score"], scores["confidence_score"], today_str))

# ----------------- AI CHAT API -----------------

@api_bp.route("/chat/send", methods=["POST"])
@api_login_required
def chat_send():
    user_id = session["user_id"]
    data = request.json or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"error": "Message content is empty."}), 400
        
    # 1. Fetch recent conversation history (closes connection immediately)
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT role, content FROM conversation_history 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 10;
        """, (user_id,))
        history_rows = cursor.fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(history_rows)]
    
    # 2. Get user memory weaknesses
    memory_summary = MemoryService.get_memory_summary(user_id)
    
    # 3. Call Gemini API (NO DB CONNECTION IS HELD OPEN DURING NETWORK WAIT)
    coach_response = GeminiService.get_conversation_feedback(history, message, memory_summary)
    
    # 4. Save User Message & AI reply
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO conversation_history (user_id, role, content)
        VALUES (?, 'user', ?);
        """, (user_id, message))
        
        cursor.execute("""
        INSERT INTO conversation_history (user_id, role, content, analysis_json)
        VALUES (?, 'assistant', ?, ?);
        """, (user_id, coach_response["reply"], json.dumps(coach_response)))
    
    # 5. Update AI Memory in database
    MemoryService.update_memory_from_feedback(user_id, coach_response)
    
    # Calculate automated speaking and confidence metrics
    mistakes_count = len(coach_response.get("feedback", {}).get("mistakes", []))
    speaking_val = max(10, 100 - (mistakes_count * 15))
    confidence_val = min(100, max(40, len(message.split()) * 5 + 40))
    
    # Save statistics
    update_progress_metric(user_id, "speaking_score", speaking_val)
    update_progress_metric(user_id, "confidence_score", confidence_val)
    
    # Check for achievements
    check_and_unlock_chat_achievements(user_id)
    
    return jsonify(coach_response)

def check_and_unlock_chat_achievements(user_id):
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM conversation_history WHERE user_id = ? AND role = 'user';", (user_id,))
        count = cursor.fetchone()[0]
        
        if count >= 10:
            cursor.execute("""
            INSERT INTO achievements (user_id, title, description, badge_icon)
            VALUES (?, 'Chatterbox', 'Exchanged 10+ conversation messages with your tutor.', '💬')
            ON CONFLICT(user_id, title) DO NOTHING;
            """, (user_id,))

# ----------------- GRAMMAR TEACHER API -----------------

@api_bp.route("/grammar/lesson", methods=["GET"])
@api_login_required
def grammar_lesson():
    topic = request.args.get("topic", "Tenses")
    lesson_data = GeminiService.get_grammar_lesson(topic)
    return jsonify(lesson_data)

@api_bp.route("/grammar/submit_quiz", methods=["POST"])
@api_login_required
def grammar_submit():
    user_id = session["user_id"]
    data = request.json or {}
    topic = data.get("topic", "Tenses")
    score = int(data.get("score", 0))
    
    mastery = "Beginner"
    if score >= 90:
        mastery = "Advanced"
    elif score >= 60:
        mastery = "Intermediate"
        
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO grammar (user_id, topic, score, mastery_level, last_studied)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, topic) DO UPDATE SET
        score = MAX(score, EXCLUDED.score),
        mastery_level = EXCLUDED.mastery_level,
        last_studied = CURRENT_TIMESTAMP;
        """, (user_id, topic, score, mastery))
    
    update_progress_metric(user_id, "grammar_score", score)
    return jsonify({"status": "success", "mastery": mastery})

# ----------------- VOCABULARY BUILDER API -----------------

@api_bp.route("/vocab/daily", methods=["GET"])
@api_login_required
def vocab_daily():
    user_id = session["user_id"]
    category = request.args.get("category", "General")
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT target_level FROM users WHERE id = ?;", (user_id,))
        user_row = cursor.fetchone()
        level = user_row["target_level"] if user_row else "Intermediate"
    
    word_data = GeminiService.get_vocab_word(level, category)
    return jsonify(word_data)

@api_bp.route("/vocab/save", methods=["POST"])
@api_login_required
def vocab_save():
    user_id = session["user_id"]
    data = request.json or {}
    word = data.get("word")
    meaning = data.get("meaning")
    synonyms = ",".join(data.get("synonyms", []))
    antonyms = ",".join(data.get("antonyms", []))
    examples = " | ".join(data.get("examples", []))
    
    if not word:
        return jsonify({"error": "Word is missing."}), 400
        
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO vocabulary (user_id, word, meaning, synonyms, antonyms, examples, saved)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id, word) DO UPDATE SET saved = 1;
            """, (user_id, word, meaning, synonyms, antonyms, examples))
            
            cursor.execute("""
            INSERT INTO achievements (user_id, title, description, badge_icon)
            VALUES (?, 'Word Collector', 'Saved your first vocabulary word.', '📚')
            ON CONFLICT(user_id, title) DO NOTHING;
            """, (user_id,))
        return jsonify({"status": "success", "message": "Word saved successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/vocab/unsave", methods=["POST"])
@api_login_required
def vocab_unsave():
    user_id = session["user_id"]
    word = request.json.get("word")
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE vocabulary SET saved = 0 WHERE user_id = ? AND word = ?;", (user_id, word))
    return jsonify({"status": "success", "message": "Word removed from vocabulary."})

@api_bp.route("/vocab/submit_quiz", methods=["POST"])
@api_login_required
def vocab_submit_quiz():
    user_id = session["user_id"]
    data = request.json or {}
    success = bool(data.get("success", False))
    
    score = 100 if success else 20
    update_progress_metric(user_id, "vocab_score", score)
    return jsonify({"status": "success"})

# ----------------- INTERVIEW API -----------------

@api_bp.route("/interview/start", methods=["POST"])
@api_login_required
def interview_start():
    mode = request.json.get("mode", "HR")
    session["interview_history"] = []
    session["interview_mode"] = mode
    
    welcome_prompts = {
        "HR": "Welcome to SpeakMate AI Mock HR interview room! Let's get started. Could you tell me a little bit about yourself?",
        "Technical": "Hello. I will be evaluating your technical communication skills. Let's start. Can you describe a challenging technical architecture you built recently?",
        "Behavioral": "Welcome. In this mock session, we will focus on behavioral competencies. Tell me about a time when you had to manage a conflict within your team.",
        "Communication": "Hello! I am here to help you practice clear and structured verbal communication. Can you summarize your key professional achievements?"
    }
    
    welcome_text = welcome_prompts.get(mode, "Welcome to the Mock Interview room. Please introduce yourself.")
    session["interview_history"].append({"role": "assistant", "content": welcome_text})
    
    return jsonify({"reply": welcome_text})

@api_bp.route("/interview/answer", methods=["POST"])
@api_login_required
def interview_answer():
    user_id = session["user_id"]
    user_message = request.json.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Empty message."}), 400
        
    history = session.get("interview_history", [])
    mode = session.get("interview_mode", "HR")
    
    # Evaluate using Gemini (NO DB CONNECTION HELD OPEN)
    result = GeminiService.get_interview_response(mode, history, user_message)
    
    # Log scores in DB
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO interview_scores (user_id, mode, score, confidence, grammar, professionalism, suggestions)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (user_id, mode, result["score"], result["confidence"], result["grammar"], result["professionalism"], result["suggestions"]))
    
    # Add to session interview context
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": result["reply"]})
    session["interview_history"] = history[-6:]
    
    update_progress_metric(user_id, "confidence_score", result["confidence"])
    update_progress_metric(user_id, "speaking_score", result["score"])
    
    return jsonify(result)

# ----------------- SPEAKING CHALLENGES API -----------------

@api_bp.route("/challenges/start", methods=["POST"])
@api_login_required
def challenge_start():
    challenge_type = request.json.get("challenge_type", "One Minute Speech")
    challenge_data = GeminiService.get_speaking_challenge(challenge_type)
    return jsonify(challenge_data)

@api_bp.route("/challenges/submit", methods=["POST"])
@api_login_required
def challenge_submit():
    user_id = session["user_id"]
    data = request.json or {}
    challenge_type = data.get("challenge_type")
    title = data.get("title")
    instructions = data.get("instructions")
    user_response = data.get("response", "").strip()
    
    if not user_response:
        return jsonify({"error": "Response cannot be empty."}), 400
        
    evaluation = GeminiService.evaluate_challenge_response(title, instructions, user_response)
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO daily_challenges (user_id, challenge_type, prompt_text, user_response, score, feedback_json)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (user_id, challenge_type, title, user_response, evaluation["score"], json.dumps(evaluation)))
        
        cursor.execute("""
        INSERT INTO achievements (user_id, title, description, badge_icon)
        VALUES (?, 'Challenger', 'Completed a speaking challenge.', '🏆')
        ON CONFLICT(user_id, title) DO NOTHING;
        """, (user_id,))
    
    update_progress_metric(user_id, "speaking_score", evaluation["score"])
    update_progress_metric(user_id, "grammar_score", evaluation["grammar_score"])
    
    return jsonify(evaluation)

# ----------------- ANALYTICS & SETTINGS -----------------

@api_bp.route("/progress/history", methods=["GET"])
@api_login_required
def progress_history():
    user_id = session["user_id"]
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT date, grammar_score, vocab_score, speaking_score, confidence_score 
        FROM progress 
        WHERE user_id = ? 
        ORDER BY date ASC LIMIT 15;
        """, (user_id,))
        rows = cursor.fetchall()
    
    labels = []
    grammar = []
    vocab = []
    speaking = []
    confidence = []
    
    for r in rows:
        labels.append(r["date"])
        grammar.append(r["grammar_score"])
        vocab.append(r["vocab_score"])
        speaking.append(r["speaking_score"])
        confidence.append(r["confidence_score"])
        
    return jsonify({
        "labels": labels,
        "grammar": grammar,
        "vocab": vocab,
        "speaking": speaking,
        "confidence": confidence
    })

@api_bp.route("/profile/update", methods=["POST"])
@api_login_required
def profile_update():
    user_id = session["user_id"]
    data = request.json or {}
    target_level = data.get("target_level", "Intermediate")
    focus_area = data.get("focus_area", "General Conversation")
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users SET target_level = ?, focus_area = ? WHERE id = ?;
        """, (target_level, focus_area, user_id))
    
    session["target_level"] = target_level
    session["focus_area"] = focus_area
    
    return jsonify({"status": "success", "message": "Profile updated successfully."})

@api_bp.route("/settings/reset", methods=["POST"])
@api_login_required
def settings_reset():
    user_id = session["user_id"]
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation_history WHERE user_id = ?;", (user_id,))
        cursor.execute("DELETE FROM ai_memory WHERE user_id = ?;", (user_id,))
        
        welcome_text = (
            "👋 Welcome back! I've reset our conversation memory.\n\n"
            "Let's start fresh. Please introduce yourself in a few sentences, and we will begin."
        )
        cursor.execute("""
        INSERT INTO conversation_history (user_id, role, content)
        VALUES (?, 'assistant', ?);
        """, (user_id, welcome_text))
    
    return jsonify({"status": "success", "message": "Memory reset successfully."})
