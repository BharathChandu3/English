import json
import time
import requests
import traceback
from speakmate.config import Config

class GeminiService:
    # Model fallback chain — gemini-3.1-flash-lite confirmed working via live test.
    MODEL_CHAIN = [
        "gemini-3.1-flash-lite",   # Primary working model
        "gemini-2.0-flash",        # Fallback
        "gemini-2.0-flash-lite",   # Fallback
        "gemini-1.5-flash",        # Fallback
    ]
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    @staticmethod
    def _call_gemini(prompt, system_instruction=None, json_mode=True):
        """
        Calls the Gemini API with automatic model fallback and 429 retry.
        Iterates through MODEL_CHAIN until a successful response is returned.
        Falls back to mock mode if all models are exhausted.
        """
        import os
        api_key = Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

        if not api_key:
            print("WARNING: GEMINI_API_KEY is not set. Using fallback mock mode.")
            return None

        headers = {"Content-Type": "application/json"}

        # Build contents payload
        if system_instruction:
            contents = [{"role": "user", "parts": [
                {"text": f"System Guidelines: {system_instruction}\n\nUser Request: {prompt}"}
            ]}]
        else:
            contents = [{"role": "user", "parts": [{"text": prompt}]}]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        # Try each model in the chain
        for model in GeminiService.MODEL_CHAIN:
            url = f"{GeminiService.BASE_URL.format(model=model)}?key={api_key}"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=25)

                if response.status_code == 200:
                    data = response.json()
                    text_response = data['candidates'][0]['content']['parts'][0]['text']
                    if json_mode:
                        # Strip markdown code fences if LLM wraps response
                        cleaned = text_response.strip()
                        if cleaned.startswith("```json"):
                            cleaned = cleaned[7:]
                        if cleaned.startswith("```"):
                            cleaned = cleaned[3:]
                        if cleaned.endswith("```"):
                            cleaned = cleaned[:-3]
                        return json.loads(cleaned.strip())
                    return text_response

                elif response.status_code == 429:
                    # Rate limited — log and try next model in chain
                    print(f"[Rate Limited] {model} is quota-exhausted. Trying next model...")
                    continue

                elif response.status_code == 404:
                    print(f"[Not Found] {model} returned 404. Trying next model...")
                    continue

                else:
                    print(f"Gemini API Error {response.status_code} on {model}: {response.text[:300]}")
                    continue

            except json.JSONDecodeError as je:
                print(f"JSON parse error from {model}: {je}")
                continue
            except Exception as e:
                print(f"Exception during Gemini call to {model}: {e}")
                continue

        # All models exhausted — return None to trigger mock fallback
        print("WARNING: All Gemini models exhausted or rate-limited. Using mock fallback.")
        return None


    @classmethod
    def get_conversation_feedback(cls, history, user_message, memory_summary=""):
        """
        Conversational Coach: Analyzes the user's message, provides detailed breakdown feedback,
        and continues the conversation by asking a natural next question.
        """
        system_instruction = (
            "You are SpeakMate AI, a professional private English tutor. Speak naturally, politely, "
            "and encourage the student. Correct errors without causing discouragement.\n"
            "Analyze the student's message across Grammar, Vocabulary, Fluency, Confidence, Naturalness, "
            "and Sentence Structure.\n"
            "You MUST respond in JSON format with the following exact keys:\n"
            "{\n"
            "  \"feedback\": {\n"
            "    \"good_points\": \"A friendly summary of what the user did well (e.g., vocabulary, tone, structure)\",\n"
            "    \"mistakes\": [\"List of corrections or grammar issues found in their message, or empty list if none\"],\n"
            "    \"better_version\": \"A native, professional, and natural rephrasing of their sentence\",\n"
            "    \"explanation\": \"A simple, clear linguistic explanation of the mistakes and suggestions\",\n"
            "    \"new_vocabulary\": [\n"
            "       {\"word\": \"useful English word related to the topic\", \"meaning\": \"definition\", \"example\": \"example sentence\"}\n"
            "    ]\n"
            "  },\n"
            "  \"next_speaking_challenge\": \"A short 1-sentence prompt or challenge related to the topic (e.g., 'Try using the word \"essential\" in your next sentence!')\",\n"
            "  \"reply\": \"Your conversational response. Express empathy, answer the user, and ask exactly ONE open-ended follow-up question to keep the conversation going.\"\n"
            "}"
        )
        
        if memory_summary:
            system_instruction += f"\n\nStudent Profile Memory (Reinforce and watch for these issues): {memory_summary}"

        # Build prompt from conversation history context
        context_prompt = "Conversation History:\n"
        for h in history[-8:]: # Keep last 8 exchanges to stay in context
            context_prompt += f"{h['role'].capitalize()}: {h['content']}\n"
        context_prompt += f"Student: {user_message}\n\nPlease analyze the Student's last message, give structured feedback, and respond."
        
        result = cls._call_gemini(context_prompt, system_instruction, json_mode=True)
        
        if not result:
            # Mock fallback if Gemini key is missing or calls fail
            result = {
                "feedback": {
                    "good_points": "You expressed yourself clearly and started the conversation naturally!",
                    "mistakes": ["No critical errors found in this short message."],
                    "better_version": user_message if len(user_message) > 5 else "Hello, I am excited to practice English with you!",
                    "explanation": "To make your responses sound more natural, try expanding with details like your background or hobbies.",
                    "new_vocabulary": [
                        {"word": "immersion", "meaning": "deep mental involvement in something", "example": "Language immersion helps you learn faster."}
                    ]
                },
                "next_speaking_challenge": "Try using the word 'enthusiastic' in your next reply!",
                "reply": f"It is great to chat with you! Let's build your confidence. What are your primary goals for learning English?"
            }
            
        return result

    @classmethod
    def get_grammar_lesson(cls, topic):
        """
        Generates explanation and a 3-question quiz for a grammar topic.
        """
        system_instruction = (
            "You are a master English Grammar Teacher. Explain the grammar topic clearly, "
            "using real-world examples. Then create a 3-question multiple choice quiz.\n"
            "You MUST respond in JSON format with the following keys:\n"
            "{\n"
            "  \"explanation\": \"Deep but easy-to-understand explanation of the grammar topic, including rules, formatting, and tips.\",\n"
            "  \"examples\": [\n"
            "     \"Example 1: description\",\n"
            "     \"Example 2: description\"\n"
            "  ],\n"
            "  \"quiz\": [\n"
            "     {\n"
            "        \"question\": \"The quiz question text with a blank represented as _____\",\n"
            "        \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],\n"
            "        \"correct_index\": 0,\n"
            "        \"explanation\": \"Explain why the correct option is right and others are wrong\"\n"
            "     }\n"
            "  ]\n"
            "}"
        )
        
        prompt = f"Create a comprehensive lesson and quiz for the grammar topic: '{topic}'."
        result = cls._call_gemini(prompt, system_instruction, json_mode=True)
        
        if not result:
            # Mock fallback
            result = {
                "explanation": f"This lesson covers the grammar rules of {topic}. Make sure to observe structure, word agreement, and tense guidelines.",
                "examples": [
                    "Incorrect: She do not go to work.",
                    "Correct: She does not go to work."
                ],
                "quiz": [
                    {
                        "question": f"Which of the following is correct for the topic: '{topic}'?",
                        "options": ["Option one", "Option two", "Option three", "Option four"],
                        "correct_index": 1,
                        "explanation": "Option two is correct because it aligns with standard subject-verb syntax."
                    },
                    {
                        "question": "Fill in the blank: She _____ studying English yesterday.",
                        "options": ["were", "is", "was", "has"],
                        "correct_index": 2,
                        "explanation": "'was' matches the singular subject 'She' and indicates the past progressive tense."
                    },
                    {
                        "question": "Choose the correct prepositions: We arrived _____ the airport _____ night.",
                        "options": ["on, at", "at, at", "in, in", "at, in"],
                        "correct_index": 1,
                        "explanation": "'at the airport' refers to a specific point, and 'at night' is a standard time expression."
                    }
                ]
            }
        return result

    @classmethod
    def get_vocab_word(cls, level="Intermediate", category="General"):
        """
        Generates Word of the Day along with definition, synonyms, antonyms, examples, and a quiz question.
        """
        system_instruction = (
            "You are a vocabulary expert. Select an interesting vocabulary word suitable for a "
            "student at the specified English level, related to the topic category.\n"
            "You MUST respond in JSON format with the following keys:\n"
            "{\n"
            "  \"word\": \"The vocabulary word\",\n"
            "  \"meaning\": \"Definition of the word\",\n"
            "  \"synonyms\": [\"synonym1\", \"synonym2\"],\n"
            "  \"antonyms\": [\"antonym1\", \"antonym2\"],\n"
            "  \"examples\": [\"Example sentence 1 showing usage\", \"Example sentence 2\"],\n"
            "  \"quiz\": {\n"
            "     \"question\": \"Multiple-choice question to test user's understanding of this word\",\n"
            "     \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],\n"
            "     \"correct_index\": 0,\n"
            "     \"explanation\": \"Linguistic breakdown of why this option is correct\"\n"
            "  }\n"
            "}"
        )
        
        prompt = f"Generate a word of the day at level: '{level}', category: '{category}'."
        result = cls._call_gemini(prompt, system_instruction, json_mode=True)
        
        if not result:
            result = {
                "word": "Resilient",
                "meaning": "Able to withstand or recover quickly from difficult conditions.",
                "synonyms": ["strong", "tough", "hardy", "flexible"],
                "antonyms": ["fragile", "vulnerable", "weak"],
                "examples": [
                    "A resilient learner is not afraid of making speaking mistakes.",
                    "She is resilient and quickly adapted to the new corporate environment."
                ],
                "quiz": {
                    "question": "Which of the following is the closest meaning of 'Resilient'?",
                    "options": ["Easily broken", "Capable of recovering quickly", "Very talkative", "Slow to understand"],
                    "correct_index": 1,
                    "explanation": "'Resilient' relates to elasticity, strength, and quick recovery, matching option 2."
                }
            }
        return result

    @classmethod
    def get_interview_response(cls, mode, history, user_message):
        """
        Interview Coach: Evaluates a candidate's answer for HR, Technical, Behavioral,
        or Communication interviews and responds with ratings and the next query.
        """
        system_instruction = (
            f"You are a professional mock interviewer conducting a '{mode}' interview.\n"
            "Be formal but constructive. Ask one question at a time. After the user answers, "
            "assess their input, rate performance from 1-100, provide specific professional suggestions, "
            "and then ask the next logical interview question.\n"
            "You MUST respond in JSON format with the following keys:\n"
            "{\n"
            "  \"score\": 85, -- score out of 100\n"
            "  \"confidence\": 80, -- confidence rating out of 100 based on word choices and filler words\n"
            "  \"grammar\": 90, -- grammar correctness out of 100\n"
            "  \"professionalism\": 85, -- tone, structure, STAR method alignment\n"
            "  \"suggestions\": \"Specific tips to make their answer stronger and more polished.\",\n"
            "  \"reply\": \"Your interviewer response. Provide brief feedback if needed, then state your next interview question.\"\n"
            "}"
        )
        
        context_prompt = f"Interview Mode: {mode}\nInterview History:\n"
        for h in history[-6:]:
            context_prompt += f"{h['role'].capitalize()}: {h['content']}\n"
        context_prompt += f"Candidate: {user_message}\n\nEvaluate the Candidate's response and state the next question."
        
        result = cls._call_gemini(context_prompt, system_instruction, json_mode=True)
        
        if not result:
            result = {
                "score": 75,
                "confidence": 70,
                "grammar": 80,
                "professionalism": 75,
                "suggestions": "Good initial answer. Try to use the STAR method (Situation, Task, Action, Result) to format behavioral responses.",
                "reply": "Thank you for sharing that. Can you describe a challenging project you worked on and how you handled difficulties?"
            }
        return result

    @classmethod
    def generate_daily_lesson(cls, difficulty, topic):
        """
        Generates interactive daily English lesson (a short dialogue and vocabulary list).
        """
        system_instruction = (
            "You are SpeakMate AI. Generate a short English dialogue lesson based on the topic "
            "and difficulty level (Beginner, Intermediate, Advanced).\n"
            "Include a roleplay script, key vocabulary, and a speaking practice prompt.\n"
            "You MUST respond in JSON format with this structure:\n"
            "{\n"
            "  \"title\": \"Lesson Title\",\n"
            "  \"intro\": \"Short description of the scenario\",\n"
            "  \"dialogue\": [\n"
            "     {\"speaker\": \"Tutor\", \"line\": \"...\"},\n"
            "     {\"speaker\": \"Student\", \"line\": \"...\"}\n"
            "  ],\n"
            "  \"key_phrases\": [\n"
            "     {\"phrase\": \"Useful phrase\", \"meaning\": \"definition\", \"context\": \"why we use it\"}\n"
            "  ],\n"
            "  \"practice_prompt\": \"A prompt directing the student to perform a roleplay reply or answer.\"\n"
            "}"
        )
        
        prompt = f"Generate a lesson. Difficulty: '{difficulty}', Topic: '{topic}'."
        result = cls._call_gemini(prompt, system_instruction, json_mode=True)
        
        if not result:
            result = {
                "title": f"Conversing about {topic}",
                "intro": f"In this dialogue, we practice common expressions used when discussing {topic}.",
                "dialogue": [
                    {"speaker": "Tutor", "line": f"Hello! What is your favorite part about studying {topic}?"},
                    {"speaker": "Student", "line": f"I really like learning practical vocabulary that helps me in daily life."}
                ],
                "key_phrases": [
                    {"phrase": "Practical vocabulary", "meaning": "Words that are highly useful in real-world scenarios.", "context": "Used to describe hands-on learning."}
                ],
                "practice_prompt": f"Tell me about a memorable experience you had related to {topic}."
            }
        return result

    @classmethod
    def get_speaking_challenge(cls, challenge_type):
        """
        Generates speaking challenge details.
        """
        system_instruction = (
            "You are SpeakMate AI. Generate a creative speaking challenge instructions.\n"
            "You MUST respond in JSON format with this structure:\n"
            "{\n"
            "  \"title\": \"Challenge Title\",\n"
            "  \"instructions\": \"Step by step guidelines for what the student needs to say.\",\n"
            "  \"prompt_media\": \"Optional description of a picture, scene, or topic (e.g. 'A crowded airport terminal')\",\n"
            "  \"target_vocabulary\": [\"vocab1\", \"vocab2\"],\n"
            "  \"time_limit_seconds\": 60\n"
            "}"
        )
        
        prompt = f"Generate a speaking challenge of type: '{challenge_type}'."
        result = cls._call_gemini(prompt, system_instruction, json_mode=True)
        
        if not result:
            result = {
                "title": "A Busy Coffee Shop",
                "instructions": "Describe this scene. Mention what people are doing, the atmosphere, and the smells. Try to speak continuously for 60 seconds.",
                "prompt_media": "An image description: A cozy, modern cafe with a barista steaming milk, customers chatting at wooden tables, and sunlight streaming through tall windows.",
                "target_vocabulary": ["aroma", "bustling", "cozy", "steaming"],
                "time_limit_seconds": 60
            }
        return result

    @classmethod
    def evaluate_challenge_response(cls, challenge_title, instructions, user_response):
        """
        Evaluates a user response to a speaking challenge.
        """
        system_instruction = (
            "You are a professional IELTS speaking examiner. Evaluate the student's speaking response.\n"
            "Return a score from 1-100 and clear, structured feedback on Pronunciation, Fluency, and Vocabulary.\n"
            "You MUST respond in JSON format with this structure:\n"
            "{\n"
            "  \"score\": 82,\n"
            "  \"fluency_score\": 80,\n"
            "  \"vocab_score\": 85,\n"
            "  \"grammar_score\": 80,\n"
            "  \"good_points\": \"Things the user expressed very well.\",\n"
            "  \"mistakes\": [\"grammar corrections or spelling errors\"],\n"
            "  \"suggestions\": \"Actionable steps to score higher on a similar task.\"\n"
            "}"
        )
        
        prompt = (
            f"Challenge Title: {challenge_title}\n"
            f"Instructions: {instructions}\n"
            f"User Response: {user_response}\n\nPlease evaluate this response."
        )
        result = cls._call_gemini(prompt, system_instruction, json_mode=True)
        
        if not result:
            result = {
                "score": 75,
                "fluency_score": 70,
                "vocab_score": 75,
                "grammar_score": 80,
                "good_points": "You spoke relevantly and structured your response sequentially.",
                "mistakes": ["A couple of grammar tense inconsistencies were spotted."],
                "suggestions": "Try to slow down your speaking slightly, focus on pronouncing consonant endings clearly, and use transitioning words like 'furthermore' or 'however'."
            }
        return result
