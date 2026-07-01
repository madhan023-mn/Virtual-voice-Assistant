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
import smtplib
import random
import string
import re
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from email.message import EmailMessage

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
    email = request.form.get("email", "").strip()
    if database.create_user(username, password, email):
        return render_template("login.html", msg="Registration successful! Please sign in.")
    return render_template("login.html", error="Username already exists or invalid.")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return render_template("forgot_password.html", error="Email is required.")
        
        # Verify user by email exists (requires a query, wait we don't have a direct check in database.py but reset_password handles it)
        # We should generate a new password
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if database.reset_password(email, new_password):
            # Send email
            if cfg.EMAIL_ADDRESS and cfg.EMAIL_PASSWORD:
                try:
                    msg = EmailMessage()
                    msg.set_content(f"Your new password is: {new_password}\nPlease login and change it.")
                    msg["Subject"] = "Password Reset Request"
                    msg["From"] = cfg.EMAIL_ADDRESS
                    msg["To"] = email
                    
                    server = smtplib.SMTP("smtp.gmail.com", 587)
                    server.starttls()
                    server.login(cfg.EMAIL_ADDRESS, cfg.EMAIL_PASSWORD)
                    server.send_message(msg)
                    server.quit()
                    return render_template("login.html", msg="A new password has been sent to your email.")
                except Exception as e:
                    logger.error(f"Error sending email: {e}")
                    return render_template("forgot_password.html", error="Failed to send email. Please check server configuration.")
            else:
                return render_template("forgot_password.html", error="Email sending is not configured on the server.")
        else:
            return render_template("forgot_password.html", error="Email not found.")
            
    return render_template("forgot_password.html")

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

        # 0. Typo correction & URL scraping
        # Auto-correct user message using TextBlob
        try:
            blob = TextBlob(user_message)
            corrected_message = str(blob.correct())
            if corrected_message.lower() != user_message.lower():
                logger.info("Auto-corrected message: %s", corrected_message)
                user_message = corrected_message
        except Exception as e:
            logger.warning(f"Typo correction failed: {e}")

        # Extract URLs
        urls = re.findall(r'(https?://\S+)', user_message)
        context = ""
        for url in urls:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                text_content = soup.get_text(separator=' ', strip=True)
                context += f"\n[Context from {url}]: {text_content[:2000]}"
            except Exception as e:
                logger.warning(f"Failed to scrape URL {url}: {e}")

        # 1. Try built-in commands first
        command_result = route_command(user_message)
        if command_result is not None:
            return jsonify(command_result)

        # 2. Prepend language instruction so AI always responds in chosen language
        if lang and lang.lower() != "english":
            ai_input = f"[Respond only in {lang}. Do not switch language under any circumstance.]\n{user_message}"
        else:
            ai_input = user_message
            
        if context:
            ai_input += f"\n\nWebsite Context:{context}"

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
        return jsonify({"error": "I'm sorry, but Gemini failed to analyze the image."}), 500

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

@app.route("/api/generate/image", methods=["POST"])
def generate_image():
    """Generate an image from a text prompt using Gemini Imagen or fallback."""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "Prompt is required."}), 400

        # ── Try Gemini Imagen ─────────────────────────────────────────────────
        if cfg.GEMINI_API_KEY:
            try:
                from google import genai as google_genai
                from google.genai import types as genai_types
                client = google_genai.Client(api_key=cfg.GEMINI_API_KEY)
                response = client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=prompt,
                    config=genai_types.GenerateImagesConfig(number_of_images=1)
                )
                if response.generated_images:
                    import base64
                    img_bytes = response.generated_images[0].image.image_bytes
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    return jsonify({"image_url": f"data:image/png;base64,{b64}", "prompt": prompt})
            except Exception as img_err:
                logger.warning("Gemini Imagen failed: %s", img_err)

        # ── Fallback: describe the image via AI ───────────────────────────────
        ai_desc = get_ai_response(
            f"Describe in vivid detail what an AI-generated image of '{prompt}' would look like. "
            "Be creative and detailed as if painting a picture with words.", "img_gen"
        )
        return jsonify({
            "text": f"🎨 Image generation requires Imagen API access. Here's what it would look like:\n\n{ai_desc}",
            "prompt": prompt
        })

    except Exception as exc:
        logger.exception("Error in /api/generate/image: %s", exc)
        return jsonify({"error": "Image generation failed."}), 500


@app.route("/api/generate/video", methods=["POST"])
def generate_video():
    """Generate a video from a text prompt using Gemini Veo or fallback description."""
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "Prompt is required."}), 400

        # ── Try Gemini Veo ────────────────────────────────────────────────────
        if cfg.GEMINI_API_KEY:
            try:
                from google import genai as google_genai
                from google.genai import types as genai_types
                import time
                client = google_genai.Client(api_key=cfg.GEMINI_API_KEY)
                operation = client.models.generate_videos(
                    model="veo-2.0-generate-001",
                    prompt=prompt,
                    config=genai_types.GenerateVideosConfig(
                        number_of_videos=1,
                        duration_seconds=5,
                        enhance_prompt=True,
                    )
                )
                # Poll for completion (max 60s)
                for _ in range(12):
                    if operation.done:
                        break
                    time.sleep(5)
                    operation = client.operations.get(operation)

                if operation.done and operation.response and operation.response.generated_videos:
                    video = operation.response.generated_videos[0]
                    video_bytes = client.files.download(file=video.video)
                    import base64
                    b64 = base64.b64encode(video_bytes).decode("utf-8")
                    return jsonify({"video_url": f"data:video/mp4;base64,{b64}", "prompt": prompt})
            except Exception as vid_err:
                logger.warning("Gemini Veo failed: %s", vid_err)

        # ── Fallback: AI storyboard description ───────────────────────────────
        ai_desc = get_ai_response(
            f"Create a detailed storyboard / scene description for a short video about: '{prompt}'. "
            "Describe each scene with timestamps, camera angles, visual elements, and mood.", "vid_gen"
        )
        return jsonify({
            "text": f"🎬 Video generation requires Veo API access. Here's a storyboard for '{prompt}':\n\n{ai_desc}",
            "prompt": prompt
        })

    except Exception as exc:
        logger.exception("Error in /api/generate/video: %s", exc)
        return jsonify({"error": "Video generation failed."}), 500


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
