import json
from flask import Blueprint, request, jsonify, session
from datetime import date, datetime
from speakmate.models import db, User, Progress, ConversationHistory, Achievement, Grammar, Vocabulary, InterviewScore, DailyChallenge, AIMemory
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
    try:
        row = Progress.query.filter_by(user_id=user_id, date=today_str).first()
        if row:
            setattr(row, metric_name, value)
        else:
            last = Progress.query.filter_by(user_id=user_id).order_by(Progress.date.desc()).first()
            grammar = last.grammar_score if last else 50
            vocab = last.vocab_score if last else 50
            speaking = last.speaking_score if last else 50
            confidence = last.confidence_score if last else 50
            
            scores = {
                "grammar_score": grammar,
                "vocab_score": vocab,
                "speaking_score": speaking,
                "confidence_score": confidence
            }
            scores[metric_name] = value
            
            new_progress = Progress(
                user_id=user_id,
                grammar_score=scores["grammar_score"],
                vocab_score=scores["vocab_score"],
                speaking_score=scores["speaking_score"],
                confidence_score=scores["confidence_score"],
                date=today_str
            )
            db.session.add(new_progress)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating progress metric: {e}")

# ----------------- AI CHAT API -----------------

@api_bp.route("/chat/send", methods=["POST"])
@api_login_required
def chat_send():
    user_id = session["user_id"]
    data = request.json or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"error": "Message content is empty."}), 400
        
    # 1. Fetch recent conversation history
    history_rows = ConversationHistory.query.filter_by(user_id=user_id).order_by(ConversationHistory.id.desc()).limit(10).all()
    history = [{"role": r.role, "content": r.content} for r in reversed(history_rows)]
    
    # 2. Get user memory weaknesses
    memory_summary = MemoryService.get_memory_summary(user_id)
    
    # 3. Call Gemini API
    coach_response = GeminiService.get_conversation_feedback(history, message, memory_summary)
    
    # 4. Save User Message & AI reply
    try:
        user_msg = ConversationHistory(user_id=user_id, role='user', content=message)
        ai_msg = ConversationHistory(user_id=user_id, role='assistant', content=coach_response["reply"], analysis_json=json.dumps(coach_response))
        db.session.add(user_msg)
        db.session.add(ai_msg)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving chat log: {e}")
    
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
    try:
        count = ConversationHistory.query.filter_by(user_id=user_id, role='user').count()
        if count >= 10:
            existing = Achievement.query.filter_by(user_id=user_id, title='Chatterbox').first()
            if not existing:
                achievement = Achievement(
                    user_id=user_id,
                    title='Chatterbox',
                    description='Exchanged 10+ conversation messages with your tutor.',
                    badge_icon='💬'
                )
                db.session.add(achievement)
                db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error checking chat achievement: {e}")

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
        
    try:
        existing = Grammar.query.filter_by(user_id=user_id, topic=topic).first()
        if existing:
            existing.score = max(existing.score, score)
            existing.mastery_level = mastery
            existing.last_studied = datetime.utcnow()
        else:
            new_grammar = Grammar(
                user_id=user_id,
                topic=topic,
                score=score,
                mastery_level=mastery,
                last_studied=datetime.utcnow()
            )
            db.session.add(new_grammar)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving grammar score: {e}")
    
    update_progress_metric(user_id, "grammar_score", score)
    return jsonify({"status": "success", "mastery": mastery})

# ----------------- DAILY LESSON API -----------------

@api_bp.route("/lesson/generate", methods=["POST"])
@api_login_required
def lesson_generate():
    data = request.json or {}
    difficulty = data.get("difficulty", "Intermediate")
    topic = data.get("topic", "Travel")
    lesson_data = GeminiService.generate_daily_lesson(difficulty, topic)
    return jsonify(lesson_data)

# ----------------- VOCABULARY BUILDER API -----------------

@api_bp.route("/vocab/daily", methods=["GET"])
@api_login_required
def vocab_daily():
    user_id = session["user_id"]
    category = request.args.get("category", "General")
    
    user_row = User.query.get(user_id)
    level = user_row.target_level if user_row else "Intermediate"
    
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
        existing = Vocabulary.query.filter_by(user_id=user_id, word=word).first()
        if existing:
            existing.saved = 1
            existing.meaning = meaning
            existing.synonyms = synonyms
            existing.antonyms = antonyms
            existing.examples = examples
            existing.last_reviewed = datetime.utcnow()
        else:
            new_vocab = Vocabulary(
                user_id=user_id,
                word=word,
                meaning=meaning,
                synonyms=synonyms,
                antonyms=antonyms,
                examples=examples,
                saved=1,
                last_reviewed=datetime.utcnow()
            )
            db.session.add(new_vocab)
            
        existing_ach = Achievement.query.filter_by(user_id=user_id, title='Word Collector').first()
        if not existing_ach:
            ach = Achievement(
                user_id=user_id,
                title='Word Collector',
                description='Saved your first vocabulary word.',
                badge_icon='📚'
            )
            db.session.add(ach)
            
        db.session.commit()
        return jsonify({"status": "success", "message": "Word saved successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route("/vocab/unsave", methods=["POST"])
@api_login_required
def vocab_unsave():
    user_id = session["user_id"]
    word = request.json.get("word")
    
    try:
        existing = Vocabulary.query.filter_by(user_id=user_id, word=word).first()
        if existing:
            existing.saved = 0
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error unsaving word: {e}")
        
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
    
    # Evaluate using Gemini
    result = GeminiService.get_interview_response(mode, history, user_message)
    
    # Log scores in DB
    try:
        new_score = InterviewScore(
            user_id=user_id,
            mode=mode,
            score=result["score"],
            confidence=result["confidence"],
            grammar=result["grammar"],
            professionalism=result["professionalism"],
            suggestions=result["suggestions"]
        )
        db.session.add(new_score)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving interview score: {e}")
    
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
    
    try:
        new_challenge = DailyChallenge(
            user_id=user_id,
            challenge_type=challenge_type,
            prompt_text=title,
            user_response=user_response,
            score=evaluation["score"],
            feedback_json=json.dumps(evaluation)
        )
        db.session.add(new_challenge)
        
        existing_ach = Achievement.query.filter_by(user_id=user_id, title='Challenger').first()
        if not existing_ach:
            ach = Achievement(
                user_id=user_id,
                title='Challenger',
                description='Completed a speaking challenge.',
                badge_icon='🏆'
            )
            db.session.add(ach)
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving daily challenge: {e}")
    
    update_progress_metric(user_id, "speaking_score", evaluation["score"])
    update_progress_metric(user_id, "grammar_score", evaluation["grammar_score"])
    
    return jsonify(evaluation)

# ----------------- ANALYTICS & SETTINGS -----------------

@api_bp.route("/progress/history", methods=["GET"])
@api_login_required
def progress_history():
    user_id = session["user_id"]
    rows = Progress.query.filter_by(user_id=user_id).order_by(Progress.date.asc()).limit(15).all()
    
    labels = []
    grammar = []
    vocab = []
    speaking = []
    confidence = []
    
    for r in rows:
        labels.append(r.date)
        grammar.append(r.grammar_score)
        vocab.append(r.vocab_score)
        speaking.append(r.speaking_score)
        confidence.append(r.confidence_score)
        
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
    
    try:
        user = User.query.get(user_id)
        if user:
            user.target_level = target_level
            user.focus_area = focus_area
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
    session["target_level"] = target_level
    session["focus_area"] = focus_area
    
    return jsonify({"status": "success", "message": "Profile updated successfully."})

@api_bp.route("/settings/reset", methods=["POST"])
@api_login_required
def settings_reset():
    user_id = session["user_id"]
    
    try:
        ConversationHistory.query.filter_by(user_id=user_id).delete()
        AIMemory.query.filter_by(user_id=user_id).delete()
        
        welcome_text = (
            "👋 Welcome back! I've reset our conversation memory.\n\n"
            "Let's start fresh. Please introduce yourself in a few sentences, and we will begin."
        )
        welcome_chat = ConversationHistory(user_id=user_id, role='assistant', content=welcome_text)
        db.session.add(welcome_chat)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"status": "success", "message": "Memory reset successfully."})
