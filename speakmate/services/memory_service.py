import json
from datetime import datetime
from speakmate.models import db, AIMemory

class MemoryService:
    @staticmethod
    def update_memory_from_feedback(user_id, feedback_json):
        """
        Parses feedback dictionary and logs grammar/vocabulary weaknesses
        into the database to reinforce them in future prompts.
        """
        if not feedback_json:
            return

        try:
            feedback = json.loads(feedback_json) if isinstance(feedback_json, str) else feedback_json

            mistakes = feedback.get("feedback", {}).get("mistakes", [])
            new_vocab = feedback.get("feedback", {}).get("new_vocabulary", [])

            # 1. Store recurring grammar/structure mistakes
            for mistake in mistakes:
                if mistake:
                    content_str = str(mistake)[:500]
                    existing = AIMemory.query.filter_by(
                        user_id=user_id, 
                        memory_type="recurring_mistakes", 
                        content=content_str
                    ).first()
                    
                    if existing:
                        existing.occurrences += 1
                        existing.last_seen = datetime.utcnow()
                    else:
                        new_mem = AIMemory(
                            user_id=user_id,
                            memory_type="recurring_mistakes",
                            content=content_str,
                            occurrences=1,
                            last_seen=datetime.utcnow()
                        )
                        db.session.add(new_mem)

            # 2. Store new vocabulary words introduced during session
            for item in new_vocab:
                word = item.get("word", "")
                meaning = item.get("meaning", "")
                if word:
                    content_str = f"{word} ({meaning})"[:500]
                    existing = AIMemory.query.filter_by(
                        user_id=user_id, 
                        memory_type="weak_vocab", 
                        content=content_str
                    ).first()
                    
                    if existing:
                        existing.occurrences += 1
                        existing.last_seen = datetime.utcnow()
                    else:
                        new_mem = AIMemory(
                            user_id=user_id,
                            memory_type="weak_vocab",
                            content=content_str,
                            occurrences=1,
                            last_seen=datetime.utcnow()
                        )
                        db.session.add(new_mem)
                        
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error updating AI memory: {e}")

    @staticmethod
    def get_memory_summary(user_id):
        """
        Compiles a summarized paragraph detailing the student's weaknesses
        to feed directly into Gemini's system instructions.
        """
        try:
            mistakes = AIMemory.query.filter_by(
                user_id=user_id, 
                memory_type='recurring_mistakes'
            ).order_by(AIMemory.occurrences.desc(), AIMemory.last_seen.desc()).limit(5).all()

            vocab = AIMemory.query.filter_by(
                user_id=user_id, 
                memory_type='weak_vocab'
            ).order_by(AIMemory.occurrences.desc(), AIMemory.last_seen.desc()).limit(5).all()

            summary_parts = []
            if mistakes:
                mistakes_str = ", ".join(
                    [f"'{m.content}' (made {m.occurrences} times)" for m in mistakes]
                )
                summary_parts.append(f"Student makes these recurring mistakes: {mistakes_str}.")
            if vocab:
                vocab_str = ", ".join([v.content for v in vocab])
                summary_parts.append(f"Vocabulary items to reinforce: {vocab_str}.")

            return " ".join(summary_parts) if summary_parts else "No specific learning weaknesses observed yet. Encourage natural speaking."

        except Exception as e:
            print(f"Error fetching AI memory summary: {e}")
            return "No specific learning weaknesses observed yet."

    @staticmethod
    def get_weak_topics(user_id):
        """
        Returns lists of weak vocabulary and mistakes for visual profile dashboards.
        """
        try:
            rows = AIMemory.query.filter_by(user_id=user_id).order_by(AIMemory.occurrences.desc()).all()

            result = {"mistakes": [], "vocab": []}
            for r in rows:
                if r.memory_type == 'recurring_mistakes':
                    result['mistakes'].append({"text": r.content, "count": r.occurrences})
                elif r.memory_type == 'weak_vocab':
                    result['vocab'].append({"text": r.content, "count": r.occurrences})
            return result

        except Exception as e:
            print(f"Error fetching weak topics: {e}")
            return {"mistakes": [], "vocab": []}
