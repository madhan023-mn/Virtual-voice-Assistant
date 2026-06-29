"""
assistant.py - AI Assistant Core
Manages conversation history and AI model integration (Gemini / OpenAI).
"""

import logging
from typing import Optional
from config import get_config

logger = logging.getLogger(__name__)
cfg = get_config()

# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are ARIA (Artificial Responsive Intelligent Assistant), a highly accurate, fast, and knowledgeable AI voice assistant.

Your personality and style:
- Extremely accurate and fast in delivering relevant information
- Direct to the point, avoiding unnecessary fluff or irrelevant answers
- Concise but thorough — provide exactly what was asked
- Use natural, spoken language (avoid markdown, bullet points, or formatting in voice responses)

When a question is about real-time data (weather, news, stock prices), tell the user that those features are handled by your built-in tools.

Keep responses concise for voice — ideally 1-3 sentences unless a detailed explanation is requested. Prioritize factual accuracy and speed above all else.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Conversation History Manager
# ──────────────────────────────────────────────────────────────────────────────

class ConversationHistory:
    """Manages conversation history per session."""

    MAX_MESSAGES = 20  # Keep last N message pairs

    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}

    def get(self, session_id: str) -> list[dict]:
        return self._sessions.get(session_id, [])

    def add(self, session_id: str, role: str, content: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})
        # Trim to max messages
        if len(self._sessions[session_id]) > self.MAX_MESSAGES * 2:
            self._sessions[session_id] = self._sessions[session_id][-self.MAX_MESSAGES * 2:]

    def clear(self, session_id: str):
        self._sessions[session_id] = []


# Global conversation history store
conversation_store = ConversationHistory()


# ──────────────────────────────────────────────────────────────────────────────
# AI Backend Abstraction
# ──────────────────────────────────────────────────────────────────────────────

def _chat_with_gemini(history: list[dict], user_message: str) -> str:
    """Send a message to Google Gemini and return the response. Raises on failure."""
    from google import genai

    client = genai.Client(api_key=cfg.GEMINI_API_KEY)

    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            genai.types.Content(role=role, parts=[genai.types.Part.from_text(text=msg["content"])])
        )
    contents.append(
        genai.types.Content(role="user", parts=[genai.types.Part.from_text(text=user_message)])
    )

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=contents,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return response.text.strip()


def _chat_with_openai_compatible(
    history: list[dict],
    user_message: str,
    api_key: str,
    base_url: str = None,
    model_name: str = "gpt-4o-mini",
) -> str:
    """Send a message to an OpenAI-compatible API and return the response. Raises on failure."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=512,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _chat_with_openai(history: list[dict], user_message: str) -> str:
    return _chat_with_openai_compatible(history, user_message, api_key=cfg.OPENAI_API_KEY)


def _chat_with_groq(history: list[dict], user_message: str) -> str:
    return _chat_with_openai_compatible(
        history, user_message,
        api_key=cfg.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        model_name="llama-3.1-8b-instant",
    )


def _chat_with_openrouter(history: list[dict], user_message: str) -> str:
    return _chat_with_openai_compatible(
        history, user_message,
        api_key=cfg.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        model_name="google/gemini-pro",
    )


def _fallback_response(user_message: str) -> str:
    """Simple rule-based fallback when no AI API is available."""
    tl = user_message.lower()

    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    if any(g in tl for g in greetings):
        return "Hello! I'm ARIA, your AI assistant. How can I help you today?"

    if "how are you" in tl:
        return "I'm doing great, thank you for asking! Ready to assist you."

    if "your name" in tl or "who are you" in tl:
        return "I'm ARIA — Artificial Responsive Intelligent Assistant. I'm here to help you with questions, searches, and more!"

    if "thank" in tl:
        return "You're welcome! Is there anything else I can help you with?"

    if "bye" in tl or "goodbye" in tl:
        return "Goodbye! Have a wonderful day. Come back anytime!"

    if "help" in tl:
        return (
            "I can help you with: weather updates, news headlines, Wikipedia searches, "
            "jokes, fun facts, unit and currency conversions, and general questions."
        )

    return "I'm here to help! Could you rephrase your question?"


# ──────────────────────────────────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────────────────────────────────

def get_ai_response(user_message: str, session_id: str = "default") -> str:
    """
    Get an AI-generated response for the given user message.

    Tries each configured AI backend in priority order:
      document queries  → OpenRouter (first)
      standard queries  → Groq → Gemini → OpenAI → OpenRouter

    If a backend raises any exception it is silently skipped and the next
    one is attempted.  The simple rule-based fallback is only used when
    every configured API has failed.
    """
    history = conversation_store.get(session_id)
    conversation_store.add(session_id, "user", user_message)

    # Check if a document is present in conversation history
    has_document = any(
        "I have uploaded a document. Here is its content:" in msg.get("content", "")
        for msg in history
    )

    # Build ordered list of (name, callable) backends to try
    backends: list[tuple[str, callable]] = []

    if has_document and cfg.OPENROUTER_API_KEY:
        backends.append(("OpenRouter", lambda h, m: _chat_with_openrouter(h, m)))

    if cfg.GROQ_API_KEY:
        backends.append(("Groq", lambda h, m: _chat_with_groq(h, m)))

    if cfg.GEMINI_API_KEY:
        backends.append(("Gemini", lambda h, m: _chat_with_gemini(h, m)))

    if cfg.OPENAI_API_KEY:
        backends.append(("OpenAI", lambda h, m: _chat_with_openai(h, m)))

    if cfg.OPENROUTER_API_KEY and not (has_document and cfg.OPENROUTER_API_KEY):
        backends.append(("OpenRouter", lambda h, m: _chat_with_openrouter(h, m)))

    # Try each backend; skip silently on any error
    response = ""
    for name, fn in backends:
        try:
            result = fn(history, user_message)
            if result:
                response = result
                logger.info("AI response from %s", name)
                break
        except Exception as exc:
            logger.warning("Backend '%s' failed, trying next. Reason: %s", name, exc)

    # All APIs failed — use rule-based fallback (no error shown to user)
    if not response:
        logger.error("All AI backends failed for session '%s'. Using rule-based fallback.", session_id)
        response = _fallback_response(user_message)

    conversation_store.add(session_id, "assistant", response)
    return response


def clear_conversation(session_id: str = "default"):
    """Clear the conversation history for a session."""
    conversation_store.clear(session_id)
    logger.info("Cleared conversation for session: %s", session_id)
