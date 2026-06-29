# 🤖 ARIA — AI Virtual Voice Assistant

**Artificial Responsive Intelligent Assistant** — A production-ready, full-stack AI voice assistant built with Python/Flask, powered by Google Gemini or OpenAI.

![ARIA Preview](https://img.shields.io/badge/Status-Production%20Ready-7c3aed?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask)

---

## ✨ Features

### 🎙️ Voice Capabilities
- **Voice Input** — Web Speech API (Chrome/Edge)
- **Voice Output** — Browser SpeechSynthesis TTS
- **Animated Microphone** with pulse animations

### 🤖 AI Chat
- **Google Gemini 1.5 Flash** (primary)
- **OpenAI GPT-4o-mini** (fallback)
- Per-session conversation history
- Natural voice-optimised responses

### 🔧 Built-in Commands
| Command | Example |
|---------|---------|
| Time | "What time is it?" |
| Date | "What's today's date?" |
| Weather | "Weather in Tokyo" |
| News | "Latest technology news" |
| Wikipedia | "Wikipedia: Python programming" |
| Jokes | "Tell me a joke" |
| Facts | "Give me a random fact" |
| Calculator | "Open calculator" or voice |
| Unit Conversion | "Convert 100 km to miles" |
| Currency | "Convert 50 USD to GBP" |
| Google Search | "Search Google for Flask" |
| YouTube | "Play lofi music on YouTube" |
| Gmail | "Open Gmail" |
| WhatsApp | "Open WhatsApp" |
| Stack Overflow | "Stack Overflow: async Python" |
| WolframAlpha | "WolframAlpha: integral of x^2" |
| Image Search | "Search images of aurora borealis" |

### 🎨 UI / UX
- ChatGPT-like dark interface
- Glassmorphism design
- Animated background particles
- Sidebar with chat history
- Typing indicator animation
- Toast notifications
- Responsive (mobile-friendly)
- Keyboard shortcuts (`Ctrl+K`, `Ctrl+/`)
- In-browser calculator with keyboard support

---

## 📁 Project Structure

```
Virtual-Voice-Assistant/
├── app.py              # Flask app & API routes
├── assistant.py        # AI backend (Gemini / OpenAI)
├── commands.py         # Built-in command handlers
├── config.py           # Configuration & env vars
├── requirements.txt    # Python dependencies
├── Procfile            # Deployment (Render/Railway)
├── runtime.txt         # Python version
├── .env.example        # Environment variables template
├── README.md
├── templates/
│   └── index.html      # Main frontend page
└── static/
    ├── css/style.css   # All styles
    └── js/script.js    # All frontend logic
```

---

## 🚀 Quick Start (Local)

### 1. Clone / Download
```bash
cd "Virtual-Voice-Assistant"
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENWEATHER_API_KEY=your_openweathermap_key
NEWS_API_KEY=your_newsapi_key
SECRET_KEY=any-long-random-string
```

### 5. Run the Server
```bash
python app.py
```

Visit **http://localhost:5000** in Chrome or Edge.

---

## 🔑 API Keys — Where to Get Them

| Service | URL | Free Tier |
|---------|-----|-----------|
| **Gemini AI** | [aistudio.google.com](https://aistudio.google.com/app/apikey) | ✅ Yes |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/api-keys) | ❌ Paid |
| **OpenWeatherMap** | [openweathermap.org/api](https://openweathermap.org/api) | ✅ 60 calls/min |
| **NewsAPI** | [newsapi.org/register](https://newsapi.org/register) | ✅ 100 req/day |
| **ExchangeRate-API** | [exchangerate-api.com](https://www.exchangerate-api.com) | ✅ 1500/month |

> **Note:** ARIA works without any API keys using the fallback mode, but AI chat and weather/news features require their respective keys.

---

## ☁️ Deployment

### Render (Recommended)

1. Push project to a GitHub repository
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
6. Add Environment Variables in the Render dashboard
7. Deploy!

### Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Set env vars: `railway variables set GEMINI_API_KEY=...`
5. Deploy: `railway up`

### Vercel (Frontend-only fallback)
> For full-stack with backend, use Render or Railway.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main UI |
| `POST` | `/api/chat` | Main chat endpoint |
| `POST` | `/api/clear` | Clear conversation |
| `GET` | `/api/weather?city=London` | Weather data |
| `GET` | `/api/news?category=tech` | News headlines |
| `GET` | `/api/joke` | Random joke |
| `GET` | `/api/fact` | Random fact |
| `GET` | `/api/wikipedia?q=AI` | Wikipedia search |
| `GET` | `/api/convert/unit?value=100&from=km&to=miles` | Unit conversion |
| `GET` | `/api/convert/currency?amount=100&from=USD&to=EUR` | Currency conversion |
| `GET` | `/api/health` | Health check & feature status |

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in input |
| `Ctrl+K` | Focus input |
| `Ctrl+/` | Toggle sidebar |
| `Esc` | Close calculator / sidebar |

---

## 🛠️ Configuration Options (.env)

```env
# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=production
DEBUG=False
PORT=5000

# AI (use at least one)
GEMINI_API_KEY=...
OPENAI_API_KEY=...

# Features
OPENWEATHER_API_KEY=...
DEFAULT_CITY=New York
NEWS_API_KEY=...
EXCHANGE_RATE_API_KEY=...

# System
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

---

## 🔒 Security Notes

- Never commit your `.env` file
- Use strong `SECRET_KEY` in production
- Set `CORS_ORIGINS` to your domain in production
- Enable HTTPS on your deployment platform

---

## 🐛 Troubleshooting

**Voice not working?**
- Use Chrome or Edge (Firefox has limited support)
- Allow microphone permissions when prompted
- Check browser console for errors

**Weather/News not working?**
- Check your API keys in `.env`
- Visit `/api/health` to see which features are enabled

**AI chat returning generic responses?**
- Add `GEMINI_API_KEY` or `OPENAI_API_KEY` to `.env`
- Restart the server after changing `.env`

---

## 📄 License

MIT License — free to use, modify, and deploy.

---

*Built with ❤️ using Flask, Gemini AI, and Web Speech API*
