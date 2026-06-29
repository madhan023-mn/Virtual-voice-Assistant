"""
app.py - Flask Application Entry Point
Defines all API routes and serves the frontend.
"""

import logging
import os
import uuid
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS

from config import get_config
from commands import route_command
from assistant import get_ai_response, clear_conversation
import database
import admin_db

# ──────────────────────────────────────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────────────────────────────────────

cfg = get_config()

logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = cfg.SECRET_KEY
CORS(app, origins=cfg.CORS_ORIGINS)

database.init_db()
admin_db.init_db()

# ──────────────────────────────────────────────────────────────────────────────
# Session helper
# ──────────────────────────────────────────────────────────────────────────────

def get_session_id() -> str:
    """Return or create a unique session ID."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

# ──────────────────────────────────────────────────────────────────────────────
# Frontend & Auth routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
        
    username = session["user"]
    # Check block status
    if username != 'developer' and admin_db.is_user_blocked(username):
        session.clear()
        return render_template("login.html", error="Your account has been blocked by the administrator.")
        
    return render_template("index.html", username=username)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if database.verify_user(username, password):
            if username != 'developer' and admin_db.is_user_blocked(username):
                return render_template("login.html", error="Your account has been blocked by the administrator.")
            session["user"] = username
            admin_db.log_user_login(username, request.remote_addr)
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if database.create_user(username, password):
        return render_template("login.html", msg="Registration successful! Please sign in.")
    return render_template("login.html", error="Username already exists or invalid.")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



# ──────────────────────────────────────────────────────────────────────────────
# API routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Accepts: { "message": "...", "session_id": "..." (optional) }
    Returns: { "text": "...", "action": "...", "url": "..." (optional) }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"error": "Message is required."}), 400

        session_id = data.get("session_id") or get_session_id()
        lang = (data.get("lang") or "English").strip()
        logger.info("Chat [%s]: %s", session_id[:8], user_message)

        # 1. Try built-in commands first
        command_result = route_command(user_message)
        if command_result is not None:
            return jsonify(command_result)

        # 2. Prepend language instruction so AI always responds in chosen language
        if lang and lang.lower() != "english":
            ai_input = f"[Respond only in {lang}. Do not switch language under any circumstance.]\n{user_message}"
        else:
            ai_input = user_message

        # 3. Fall through to AI response
        ai_text = get_ai_response(ai_input, session_id)
        return jsonify({"text": ai_text})

    except Exception as exc:
        logger.exception("Error in /api/chat: %s", exc)
        return jsonify({"error": "An internal error occurred.", "text": "Sorry, something went wrong. Please try again."}), 500


@app.route("/api/clear", methods=["POST"])
def clear_chat():
    """Clear conversation history for the current session."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get("session_id") or get_session_id()
        clear_conversation(session_id)
        return jsonify({"success": True, "message": "Conversation cleared."})
    except Exception as exc:
        logger.exception("Error in /api/clear: %s", exc)
        return jsonify({"error": "Failed to clear conversation."}), 500


@app.route("/api/weather", methods=["GET"])
def weather():
    """Dedicated weather endpoint."""
    try:
        from commands import get_weather
        city = request.args.get("city", "")
        result = get_weather(city if city else None)
        return jsonify({"text": result})
    except Exception as exc:
        logger.exception("Error in /api/weather: %s", exc)
        return jsonify({"error": "Weather service unavailable."}), 500


@app.route("/api/news", methods=["GET"])
def news():
    """Dedicated news endpoint."""
    try:
        from commands import get_news_headlines
        category = request.args.get("category", "general")
        count = int(request.args.get("count", 5))
        result = get_news_headlines(category, count)
        return jsonify({"text": result})
    except Exception as exc:
        logger.exception("Error in /api/news: %s", exc)
        return jsonify({"error": "News service unavailable."}), 500


@app.route("/api/joke", methods=["GET"])
def joke():
    """Return a random joke."""
    try:
        from commands import get_joke
        return jsonify({"text": get_joke()})
    except Exception as exc:
        logger.exception("Error in /api/joke: %s", exc)
        return jsonify({"error": "Joke service unavailable."}), 500


@app.route("/api/fact", methods=["GET"])
def fact():
    """Return a random fact."""
    try:
        from commands import get_random_fact
        return jsonify({"text": get_random_fact()})
    except Exception as exc:
        logger.exception("Error in /api/fact: %s", exc)
        return jsonify({"error": "Fact service unavailable."}), 500


@app.route("/api/wikipedia", methods=["GET"])
def wikipedia_search():
    """Search Wikipedia."""
    try:
        from commands import search_wikipedia
        query = request.args.get("q", "")
        if not query:
            return jsonify({"error": "Query parameter 'q' is required."}), 400
        result = search_wikipedia(query)
        return jsonify({"text": result})
    except Exception as exc:
        logger.exception("Error in /api/wikipedia: %s", exc)
        return jsonify({"error": "Wikipedia search unavailable."}), 500


@app.route("/api/convert/unit", methods=["GET"])
def convert_unit():
    """Convert units."""
    try:
        from commands import convert_units
        value = float(request.args.get("value", 0))
        from_unit = request.args.get("from", "")
        to_unit = request.args.get("to", "")
        if not from_unit or not to_unit:
            return jsonify({"error": "Parameters 'from' and 'to' are required."}), 400
        result = convert_units(value, from_unit, to_unit)
        return jsonify({"text": result})
    except ValueError:
        return jsonify({"error": "Invalid value parameter."}), 400
    except Exception as exc:
        logger.exception("Error in /api/convert/unit: %s", exc)
        return jsonify({"error": "Unit conversion unavailable."}), 500


@app.route("/api/convert/currency", methods=["GET"])
def convert_currency_route():
    """Convert currencies."""
    try:
        from commands import convert_currency
        amount = float(request.args.get("amount", 0))
        from_currency = request.args.get("from", "")
        to_currency = request.args.get("to", "")
        if not from_currency or not to_currency:
            return jsonify({"error": "Parameters 'from' and 'to' are required."}), 400
        result = convert_currency(amount, from_currency, to_currency)
        return jsonify({"text": result})
    except ValueError:
        return jsonify({"error": "Invalid amount parameter."}), 400
    except Exception as exc:
        logger.exception("Error in /api/convert/currency: %s", exc)
        return jsonify({"error": "Currency conversion unavailable."}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    has_gemini = bool(cfg.GEMINI_API_KEY)
    has_openai = bool(cfg.OPENAI_API_KEY)
    has_weather = bool(cfg.OPENWEATHER_API_KEY)
    has_news = bool(cfg.NEWS_API_KEY)

    return jsonify({
        "status": "healthy",
        "ai_backend": "gemini" if has_gemini else ("openai" if has_openai else "fallback"),
        "features": {
            "ai_chat": has_gemini or has_openai,
            "weather": has_weather,
            "news": has_news,
            "wikipedia": True,
            "jokes": True,
            "facts": True,
            "unit_conversion": True,
            "currency_conversion": True,
        },
    })


# ──────────────────────────────────────────────────────────────────────────────
# Error handlers
# ──────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(exc):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(exc):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(exc):
    logger.exception("Internal server error: %s", exc)
    return jsonify({"error": "Internal server error."}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Admin & File Upload Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/upload/image", methods=["POST"])
def upload_image():
    if "file" not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "": return jsonify({"error": "No selected file"}), 400
    
    try:
        from PIL import Image
        
        # 1. Try OpenRouter First
        if cfg.OPENROUTER_API_KEY:
            try:
                import base64
                import requests
                file.stream.seek(0)
                base64_image = base64.b64encode(file.stream.read()).decode('utf-8')
                headers = {
                    "Authorization": f"Bearer {cfg.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "google/gemini-flash-1.5",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this image in detail:"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }
                    ]
                }
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                return jsonify({"text": response.json()['choices'][0]['message']['content'].strip()})
            except Exception as ex:
                logger.exception("OpenRouter image upload failed, falling back to Gemini")

        # 2. Fallback to Gemini SDK
        from google import genai
        file.stream.seek(0)
        img = Image.open(file.stream)
        client = genai.Client(api_key=cfg.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[img, "Describe this image in detail:"]
        )
        return jsonify({"text": response.text.strip()})
    except Exception as e:
        logger.exception("Gemini Image upload error")
        return jsonify({"text": "I'm sorry, but both OpenRouter and Gemini failed to analyze the image."})

@app.route("/api/upload/document", methods=["POST"])
def upload_document():
    """Upload a document (TXT, PDF, DOCX) and get an AI summary in the document's language."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        filename = file.filename.lower()
        raw_bytes = file.read()
        content = ""

        # ── Extract readable text based on file type ──────────────────────────
        if filename.endswith(".pdf"):
            try:
                import io
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
                content = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                ).strip()
            except ImportError:
                # pypdf not installed — fall back to raw decode
                content = raw_bytes.decode("utf-8", errors="ignore")
            except Exception as pdf_err:
                logger.warning("PDF extraction failed: %s", pdf_err)
                content = raw_bytes.decode("utf-8", errors="ignore")

        elif filename.endswith(".docx"):
            try:
                import io
                import docx
                doc = docx.Document(io.BytesIO(raw_bytes))
                content = "\n".join(para.text for para in doc.paragraphs if para.text).strip()
            except ImportError:
                content = raw_bytes.decode("utf-8", errors="ignore")
            except Exception as docx_err:
                logger.warning("DOCX extraction failed: %s", docx_err)
                content = raw_bytes.decode("utf-8", errors="ignore")

        else:
            # Plain text / CSV / Markdown / etc.
            # Try common encodings so non-English text is not garbled
            for enc in ("utf-8", "utf-16", "latin-1", "cp1252"):
                try:
                    content = raw_bytes.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if not content:
                content = raw_bytes.decode("utf-8", errors="replace")

        # Trim to avoid exceeding context limits (~12 000 chars)
        MAX_CHARS = 12_000
        truncated = len(content) > MAX_CHARS
        excerpt = content[:MAX_CHARS]

        if not excerpt.strip():
            return jsonify({"error": "Could not extract any readable text from the document."}), 422

        # ── Inject document context into conversation ─────────────────────────
        session_id = request.form.get("session_id") or get_session_id()
        user_lang = request.form.get("lang", "")          # optional hint from client
        from assistant import conversation_store, get_ai_response
        conversation_store.add(
            session_id, "user",
            f"I have uploaded a document. Here is its content:\n\n{excerpt}"
        )

        # ── Ask the AI for an immediate, language-aware summary ───────────────
        lang_instruction = (
            f" Respond in {user_lang}." if user_lang
            else " Detect the language of the document and respond in that same language."
        )
        summary_prompt = (
            f"The user just uploaded a document.{lang_instruction} "
            "Please provide a concise summary of the document in 3-5 sentences, "
            "highlighting the key points. Do not include any encoded or binary text — "
            "only present clean, readable information."
        )
        summary = get_ai_response(summary_prompt, session_id)

        truncation_note = " (Note: the document was very long — only the first portion was analysed.)" if truncated else ""
        return jsonify({
            "text": summary + truncation_note,
            "content": excerpt,
            "chars": len(content),
        })

    except Exception as e:
        logger.exception("Document upload error")
        return jsonify({"error": str(e)}), 500

@app.route("/api/interview/start", methods=["POST"])
def start_interview():
    try:
        data = request.get_json(force=True, silent=True) or {}
        resume_text = data.get("resume_text", "")
        session_id = data.get("session_id") or get_session_id()
        
        session["interview_active"] = True
        session["resume_text"] = resume_text
        
        clear_conversation(session_id)
        
        # Inject interviewer persona
        from assistant import conversation_store
        conversation_store.add(session_id, "user", f"Act as an expert interviewer conducting a mock interview with me based on my resume. Ask me one question at a time and wait for my response. Here is my resume text:\n\n{resume_text}\n\nStart by asking me to introduce myself.")
        
        prompt = "Hello, I'm ARIA. Let's begin your mock interview based on your resume. Could you please introduce yourself and tell me about your background?"
        conversation_store.add(session_id, "assistant", prompt)
        
        return jsonify({"text": prompt})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/interview/exit", methods=["POST"])
def exit_interview():
    session.pop("interview_active", None)
    session.pop("resume_text", None)
    return jsonify({"success": True})

@app.route("/api/admin/block", methods=["POST"])
def admin_block():
    if session.get("user") != 'developer': return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    if username:
        admin_db.set_user_blocked(username, True)
        return jsonify({"success": True})
    return jsonify({"error": "Missing username"}), 400

@app.route("/api/admin/unblock", methods=["POST"])
def admin_unblock():
    if session.get("user") != 'developer': return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    if username:
        admin_db.set_user_blocked(username, False)
        return jsonify({"success": True})
    return jsonify({"error": "Missing username"}), 400

@app.route("/api/admin/user_logs", methods=["GET"])
def admin_user_logs():
    if session.get("user") != 'developer': return jsonify({"error": "Unauthorized"}), 403
    username = request.args.get("username")
    if not username: return jsonify({"error": "Missing username"}), 400
    logs = admin_db.get_login_logs(username)
    return jsonify({"logs": logs})

# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = cfg.PORT
    debug = cfg.DEBUG
    logger.info("Starting ARIA Assistant on port %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
