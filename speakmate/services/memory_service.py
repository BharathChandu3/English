import json
import time
import sqlite3
from speakmate.database import get_db_context

class MemoryService:
    @staticmethod
    def update_memory_from_feedback(user_id, feedback_json):
        """
        Parses feedback dictionary and logs grammar/vocabulary weaknesses
        into the database to reinforce them in future prompts.
        Uses get_db_context to guarantee connection is always released.
        """
        if not feedback_json:
            return

        for attempt in range(3):
            try:
                feedback = json.loads(feedback_json) if isinstance(feedback_json, str) else feedback_json

                mistakes = feedback.get("feedback", {}).get("mistakes", [])
                new_vocab = feedback.get("feedback", {}).get("new_vocabulary", [])

                with get_db_context() as conn:
                    cursor = conn.cursor()

                    # 1. Store recurring grammar/structure mistakes
                    for mistake in mistakes:
                        if mistake:
                            cursor.execute("""
                            INSERT INTO ai_memory (user_id, memory_type, content, occurrences, last_seen)
                            VALUES (?, 'recurring_mistakes', ?, 1, CURRENT_TIMESTAMP)
                            ON CONFLICT(user_id, memory_type, content) DO UPDATE SET
                            occurrences = occurrences + 1,
                            last_seen = CURRENT_TIMESTAMP;
                            """, (user_id, str(mistake)[:500]))

                    # 2. Store new vocabulary words introduced during session
                    for item in new_vocab:
                        word = item.get("word", "")
                        meaning = item.get("meaning", "")
                        if word:
                            cursor.execute("""
                            INSERT INTO ai_memory (user_id, memory_type, content, occurrences, last_seen)
                            VALUES (?, 'weak_vocab', ?, 1, CURRENT_TIMESTAMP)
                            ON CONFLICT(user_id, memory_type, content) DO UPDATE SET
                            occurrences = occurrences + 1,
                            last_seen = CURRENT_TIMESTAMP;
                            """, (user_id, f"{word} ({meaning})"[:500]))
                
                # Succeeded
                break
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                print(f"Error updating AI memory: {e}")
                break
            except Exception as e:
                print(f"Error updating AI memory: {e}")
                break

    @staticmethod
    def get_memory_summary(user_id):
        """
        Compiles a summarized paragraph detailing the student's weaknesses
        to feed directly into Gemini's system instructions.
        Uses get_db_context to guarantee connection release.
        """
        for attempt in range(3):
            try:
                with get_db_context() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                    SELECT content, occurrences FROM ai_memory
                    WHERE user_id = ? AND memory_type = 'recurring_mistakes'
                    ORDER BY occurrences DESC, last_seen DESC LIMIT 5;
                    """, (user_id,))
                    mistakes = cursor.fetchall()

                    cursor.execute("""
                    SELECT content FROM ai_memory
                    WHERE user_id = ? AND memory_type = 'weak_vocab'
                    ORDER BY occurrences DESC, last_seen DESC LIMIT 5;
                    """, (user_id,))
                    vocab = cursor.fetchall()

                summary_parts = []
                if mistakes:
                    mistakes_str = ", ".join(
                        [f"'{m['content']}' (made {m['occurrences']} times)" for m in mistakes]
                    )
                    summary_parts.append(f"Student makes these recurring mistakes: {mistakes_str}.")
                if vocab:
                    vocab_str = ", ".join([v['content'] for v in vocab])
                    summary_parts.append(f"Vocabulary items to reinforce: {vocab_str}.")

                return " ".join(summary_parts) if summary_parts else "No specific learning weaknesses observed yet. Encourage natural speaking."

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                print(f"Error fetching AI memory summary: {e}")
                return "No specific learning weaknesses observed yet."
            except Exception as e:
                print(f"Error fetching AI memory summary: {e}")
                return "No specific learning weaknesses observed yet."

    @staticmethod
    def get_weak_topics(user_id):
        """
        Returns lists of weak vocabulary and mistakes for visual profile dashboards.
        """
        for attempt in range(3):
            try:
                with get_db_context() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT content, occurrences, memory_type FROM ai_memory WHERE user_id = ? ORDER BY occurrences DESC;",
                        (user_id,)
                    )
                    rows = cursor.fetchall()

                result = {"mistakes": [], "vocab": []}
                for r in rows:
                    if r['memory_type'] == 'recurring_mistakes':
                        result['mistakes'].append({"text": r['content'], "count": r['occurrences']})
                    elif r['memory_type'] == 'weak_vocab':
                        result['vocab'].append({"text": r['content'], "count": r['occurrences']})
                return result

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                print(f"Error fetching weak topics: {e}")
                return {"mistakes": [], "vocab": []}
            except Exception as e:
                print(f"Error fetching weak topics: {e}")
                return {"mistakes": [], "vocab": []}
