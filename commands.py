"""
commands.py - Command Processing Module
Handles all assistant commands and API integrations.
"""

import logging
import re
import json
import urllib.parse
from datetime import datetime
import requests
import wikipedia

from config import get_config

logger = logging.getLogger(__name__)
cfg = get_config()


# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────

def _safe_get(url: str, params: dict = None, timeout: int = 8) -> dict | None:
    """Perform a GET request with error handling."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error("HTTP request failed: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Date / Time
# ──────────────────────────────────────────────────────────────────────────────

def get_current_time() -> str:
    now = datetime.now()
    return now.strftime("The current time is %I:%M %p.")


def get_current_date() -> str:
    now = datetime.now()
    return now.strftime("Today is %A, %B %d, %Y.")


def get_day_of_week() -> str:
    return datetime.now().strftime("Today is %A.")


# ──────────────────────────────────────────────────────────────────────────────
# Wikipedia
# ──────────────────────────────────────────────────────────────────────────────

def search_wikipedia(query: str) -> str:
    """Return a Wikipedia summary for the given query."""
    if not query:
        return "Please provide a topic to search on Wikipedia."
    try:
        wikipedia.set_lang(cfg.WIKIPEDIA_LANGUAGE)
        summary = wikipedia.summary(query, sentences=4, auto_suggest=True)
        return summary
    except wikipedia.exceptions.DisambiguationError as exc:
        options = exc.options[:5]
        return f"'{query}' may refer to several things: {', '.join(options)}. Please be more specific."
    except wikipedia.exceptions.PageError:
        return f"Sorry, I couldn't find a Wikipedia page for '{query}'."
    except Exception as exc:
        logger.error("Wikipedia error: %s", exc)
        return "An error occurred while searching Wikipedia."


# ──────────────────────────────────────────────────────────────────────────────
# Weather
# ──────────────────────────────────────────────────────────────────────────────

def get_weather(city: str = None) -> str:
    """Return current weather for a city."""
    city = city or cfg.DEFAULT_CITY
    if not cfg.OPENWEATHER_API_KEY:
        return "Weather API key not configured. Please add OPENWEATHER_API_KEY to your .env file."

    data = _safe_get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "q": city,
            "appid": cfg.OPENWEATHER_API_KEY,
            "units": "metric",
        },
    )

    if not data:
        return f"Could not retrieve weather information for '{city}'."

    if data.get("cod") != 200:
        return f"City '{city}' not found. Please check the city name."

    weather_desc = data["weather"][0]["description"].capitalize()
    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    return (
        f"Weather in {city}: {weather_desc}. "
        f"Temperature: {temp:.1f}°C (feels like {feels_like:.1f}°C). "
        f"Humidity: {humidity}%. Wind speed: {wind_speed} m/s."
    )


# ──────────────────────────────────────────────────────────────────────────────
# News
# ──────────────────────────────────────────────────────────────────────────────

def get_news_headlines(category: str = "general", count: int = 5) -> str:
    """Return top news headlines."""
    if not cfg.NEWS_API_KEY:
        return "News API key not configured. Please add NEWS_API_KEY to your .env file."

    data = _safe_get(
        "https://newsapi.org/v2/top-headlines",
        params={
            "apiKey": cfg.NEWS_API_KEY,
            "language": "en",
            "category": category,
            "pageSize": count,
        },
    )

    if not data or data.get("status") != "ok":
        return "Could not retrieve news headlines at this time."

    articles = data.get("articles", [])
    if not articles:
        return "No headlines found."

    headlines = []
    for i, article in enumerate(articles[:count], 1):
        title = article.get("title", "Unknown title")
        source = article.get("source", {}).get("name", "Unknown source")
        headlines.append(f"{i}. {title} ({source})")

    return "Here are the top headlines:\n" + "\n".join(headlines)


# ──────────────────────────────────────────────────────────────────────────────
# Jokes
# ──────────────────────────────────────────────────────────────────────────────

def get_joke() -> str:
    """Return a random joke."""
    data = _safe_get(cfg.JOKE_API_URL, params={"safe-mode": True})
    if not data:
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? Because he was outstanding in his field!",
            "What do you call a bear with no teeth? A gummy bear!",
        ]
        import random
        return random.choice(jokes)

    joke_type = data.get("type")
    if joke_type == "single":
        return data.get("joke", "No joke found.")
    elif joke_type == "twopart":
        setup = data.get("setup", "")
        delivery = data.get("delivery", "")
        return f"{setup} ... {delivery}"
    return "Here's a joke: Why do programmers prefer dark mode? Because light attracts bugs!"


# ──────────────────────────────────────────────────────────────────────────────
# Random Facts
# ──────────────────────────────────────────────────────────────────────────────

def get_random_fact() -> str:
    """Return a random interesting fact."""
    data = _safe_get(cfg.FACTS_API_URL, params={"language": "en"})
    if data and "text" in data:
        return f"Here's an interesting fact: {data['text']}"
    fallback_facts = [
        "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that was still edible.",
        "A group of flamingos is called a 'flamboyance'.",
        "The shortest war in history was between Britain and Zanzibar in 1896. It lasted 38 minutes.",
        "Octopuses have three hearts.",
        "The first computer bug was an actual bug — a moth found in the Harvard Mark II computer in 1947.",
    ]
    import random
    return random.choice(fallback_facts)


# ──────────────────────────────────────────────────────────────────────────────
# Unit Conversion
# ──────────────────────────────────────────────────────────────────────────────

UNIT_CONVERSIONS = {
    # Length
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    ("meters", "feet"): 3.28084,
    ("feet", "meters"): 0.3048,
    ("cm", "inches"): 0.393701,
    ("inches", "cm"): 2.54,
    # Weight
    ("kg", "lbs"): 2.20462,
    ("lbs", "kg"): 0.453592,
    ("grams", "oz"): 0.035274,
    ("oz", "grams"): 28.3495,
    # Temperature handled separately
    # Volume
    ("liters", "gallons"): 0.264172,
    ("gallons", "liters"): 3.78541,
    ("ml", "fl oz"): 0.033814,
    ("fl oz", "ml"): 29.5735,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between units."""
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    # Temperature conversions
    if from_unit in ("celsius", "c") and to_unit in ("fahrenheit", "f"):
        result = (value * 9 / 5) + 32
        return f"{value}°C = {result:.2f}°F"
    if from_unit in ("fahrenheit", "f") and to_unit in ("celsius", "c"):
        result = (value - 32) * 5 / 9
        return f"{value}°F = {result:.2f}°C"
    if from_unit in ("celsius", "c") and to_unit in ("kelvin", "k"):
        result = value + 273.15
        return f"{value}°C = {result:.2f}K"
    if from_unit in ("kelvin", "k") and to_unit in ("celsius", "c"):
        result = value - 273.15
        return f"{value}K = {result:.2f}°C"

    key = (from_unit, to_unit)
    if key in UNIT_CONVERSIONS:
        result = value * UNIT_CONVERSIONS[key]
        return f"{value} {from_unit} = {result:.4f} {to_unit}"

    return f"Sorry, I don't know how to convert {from_unit} to {to_unit}. Supported conversions include length, weight, volume, and temperature."


# ──────────────────────────────────────────────────────────────────────────────
# Currency Conversion
# ──────────────────────────────────────────────────────────────────────────────

def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert between currencies using exchange rate API."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if cfg.EXCHANGE_RATE_API_KEY:
        # Using exchangerate-api.com
        url = f"https://v6.exchangerate-api.com/v6/{cfg.EXCHANGE_RATE_API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
        data = _safe_get(url)
        if data and data.get("result") == "success":
            result = data.get("conversion_result", 0)
            rate = data.get("conversion_rate", 0)
            return f"{amount} {from_currency} = {result:.2f} {to_currency} (Rate: 1 {from_currency} = {rate:.4f} {to_currency})"

    # Fallback: free Open Exchange Rates (base USD only)
    data = _safe_get("https://open.er-api.com/v6/latest/USD")
    if data and data.get("result") == "success":
        rates = data.get("rates", {})
        if from_currency in rates and to_currency in rates:
            usd_amount = amount / rates[from_currency]
            result = usd_amount * rates[to_currency]
            return f"{amount} {from_currency} ≈ {result:.2f} {to_currency} (approximate)"
        return f"Currency '{from_currency}' or '{to_currency}' not found."

    return "Currency conversion service is currently unavailable."


# ──────────────────────────────────────────────────────────────────────────────
# URL Generators (browser-side open)
# ──────────────────────────────────────────────────────────────────────────────

def get_google_search_url(query: str) -> dict:
    """Return a Google search URL."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    return {"text": f"Opening Google search for '{query}'...", "url": url, "action": "open_url"}


def get_youtube_search_url(query: str) -> dict:
    """Return a YouTube search URL."""
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    return {"text": f"Opening YouTube search for '{query}'...", "url": url, "action": "open_url"}


def get_gmail_url() -> dict:
    """Return Gmail URL."""
    return {"text": "Opening Gmail...", "url": "https://mail.google.com", "action": "open_url"}


def get_whatsapp_url() -> dict:
    """Return WhatsApp Web URL."""
    return {"text": "Opening WhatsApp Web...", "url": "https://web.whatsapp.com", "action": "open_url"}


def get_stackoverflow_search_url(query: str) -> dict:
    """Return a Stack Overflow search URL."""
    url = f"https://stackoverflow.com/search?q={urllib.parse.quote(query)}"
    return {"text": f"Opening Stack Overflow search for '{query}'...", "url": url, "action": "open_url"}


def get_wolframalpha_url(query: str) -> dict:
    """Return a WolframAlpha query URL."""
    url = f"https://www.wolframalpha.com/input?i={urllib.parse.quote(query)}"
    return {"text": f"Opening WolframAlpha for '{query}'...", "url": url, "action": "open_url"}


def get_image_search_url(query: str) -> dict:
    """Return a Google Images search URL."""
    url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(query)}"
    return {"text": f"Opening image search for '{query}'...", "url": url, "action": "open_url"}


def get_calculator_url() -> dict:
    """Return the in-browser calculator action."""
    return {"text": "Opening calculator...", "action": "open_calculator"}



# ──────────────────────────────────────────────────────────────────────────────
# Dictionary (Free Dictionary API)
# ──────────────────────────────────────────────────────────────────────────────

def get_definition(word: str) -> str:
    """Return the definition of a word."""
    data = _safe_get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}")
    if not data or not isinstance(data, list):
        return f"Sorry, I couldn't find the definition for '{word}'."
    
    try:
        meaning = data[0]['meanings'][0]['definitions'][0]['definition']
        return f"Definition of {word}: {meaning}"
    except (IndexError, KeyError):
        return f"Sorry, I couldn't parse the definition for '{word}'."

# ──────────────────────────────────────────────────────────────────────────────
# Quotes (Quotable API)
# ──────────────────────────────────────────────────────────────────────────────

def get_random_quote() -> str:
    """Return a random quote."""
    data = _safe_get("https://api.quotable.io/random")
    if data and "content" in data:
        return f'"{data["content"]}" - {data.get("author", "Unknown")}'
    return '"The best way to predict the future is to invent it." - Alan Kay'

# ──────────────────────────────────────────────────────────────────────────────
# Geolocation (ip-api)
# ──────────────────────────────────────────────────────────────────────────────

def get_ip_location() -> str:
    """Return current location based on IP."""
    data = _safe_get("http://ip-api.com/json/")
    if data and data.get("status") == "success":
        city = data.get("city", "Unknown city")
        region = data.get("regionName", "Unknown region")
        country = data.get("country", "Unknown country")
        return f"Based on your IP, you are located in {city}, {region}, {country}."
    return "I couldn't determine your current location."

# ──────────────────────────────────────────────────────────────────────────────
# Maps (OpenStreetMap)
# ──────────────────────────────────────────────────────────────────────────────

def search_map(location: str) -> dict:
    """Return a map URL."""
    url = f"https://www.openstreetmap.org/search?query={urllib.parse.quote(location)}"
    return {"text": f"Opening map for '{location}'...", "url": url, "action": "open_url"}

# ──────────────────────────────────────────────────────────────────────────────
# Movies (OMDb API)
# ──────────────────────────────────────────────────────────────────────────────

def get_movie_info(title: str) -> str:
    """Return movie information."""
    if not cfg.OMDB_API_KEY:
        return "OMDb API key not configured. Please add OMDB_API_KEY to your .env file."
    
    data = _safe_get("https://www.omdbapi.com/", params={"t": title, "apikey": cfg.OMDB_API_KEY})
    if data and data.get("Response") == "True":
        year = data.get("Year", "Unknown")
        plot = data.get("Plot", "No plot available.")
        rating = data.get("imdbRating", "N/A")
        return f"{data['Title']} ({year}): {plot} (IMDb: {rating}/10)"
    return f"Sorry, I couldn't find information for the movie '{title}'."

# ──────────────────────────────────────────────────────────────────────────────
# Holidays (Nager.Date)
# ──────────────────────────────────────────────────────────────────────────────

def get_holidays(country_code: str = "US") -> str:
    """Return next upcoming public holidays."""
    year = datetime.now().year
    data = _safe_get(f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}")
    if data and isinstance(data, list):
        now = datetime.now()
        upcoming = [h for h in data if datetime.strptime(h["date"], "%Y-%m-%d") >= now]
        if upcoming:
            h = upcoming[0]
            return f"The next public holiday is {h['name']} on {h['date']}."
    return "I couldn't retrieve holiday information right now."

# ──────────────────────────────────────────────────────────────────────────────
# NASA (APOD)
# ──────────────────────────────────────────────────────────────────────────────

def get_nasa_apod() -> dict:
    """Return NASA Picture of the Day."""
    api_key = cfg.NASA_API_KEY if cfg.NASA_API_KEY else "DEMO_KEY"
    data = _safe_get(f"https://api.nasa.gov/planetary/apod?api_key={api_key}")
    if data and "url" in data:
        title = data.get("title", "NASA Picture of the Day")
        return {"text": f"Here is the NASA Picture of the Day: {title}", "url": data["url"], "action": "open_url"}
    return {"text": "Could not retrieve NASA Picture of the Day."}

# ──────────────────────────────────────────────────────────────────────────────
# Spotify
# ──────────────────────────────────────────────────────────────────────────────

def search_spotify(query: str) -> dict:
    """Open Spotify search."""
    url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
    return {"text": f"Opening Spotify for '{query}'...", "url": url, "action": "open_url"}

# ──────────────────────────────────────────────────────────────────────────────
# Hugging Face (Image Generation)
# ──────────────────────────────────────────────────────────────────────────────

def generate_image(prompt: str) -> dict:
    """Trigger image generation."""
    if not cfg.HUGGINGFACE_API_KEY:
        return {"text": "HuggingFace API key not configured. Please add HUGGINGFACE_API_KEY to your .env file."}
    
    # We will simulate the URL behavior by returning a placeholder since image generation takes time
    # and requires saving a file, which is complex for a synchronous voice response.
    # A true implementation would download the bytes and save to static/images.
    return {"text": f"I don't have full UI support to display generated images yet, but I would generate: {prompt}"}

# ──────────────────────────────────────────────────────────────────────────────
# Command Router
# ──────────────────────────────────────────────────────────────────────────────

def extract_query(text: str, keywords: list[str]) -> str:
    """Strip command keywords from user input to extract the query."""
    text_lower = text.lower()
    for kw in sorted(keywords, key=len, reverse=True):
        if kw in text_lower:
            idx = text_lower.find(kw) + len(kw)
            return text[idx:].strip(" ?.,!")
    return text.strip()


def route_command(user_input: str) -> dict | None:
    """
    Attempt to route user_input to a built-in command.
    Returns a dict with at least {"text": ...} on match, or None to fall through to AI.
    """
    text = user_input.strip()
    tl = text.lower()

    # ── Time / Date ─────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["what time", "current time", "tell me the time"]):
        return {"text": get_current_time()}

    if any(kw in tl for kw in ["what date", "today's date", "current date", "what day"]):
        return {"text": get_current_date()}

    # ── Wikipedia ───────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["search wikipedia", "wikipedia for", "wiki for"]):
        q = extract_query(text, ["search wikipedia for", "wikipedia for", "wiki for", "search wikipedia", "wikipedia", "wiki"])
        if q:
            return {"text": search_wikipedia(q)}

    # ── Weather ─────────────────────────────────────────────────────────────
    if "weather" in tl:
        q = extract_query(text, ["weather in", "weather for", "weather of", "weather"])
        return {"text": get_weather(q if q else None)}

    # ── News ─────────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["news", "headlines", "latest news"]):
        category = "general"
        for cat in ["technology", "sports", "business", "entertainment", "health", "science"]:
            if cat in tl:
                category = cat
                break
        return {"text": get_news_headlines(category)}

    # ── Jokes ────────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["joke", "make me laugh", "funny"]):
        return {"text": get_joke()}

    # ── Random Facts ────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["fact", "random fact", "interesting fact", "did you know"]):
        return {"text": get_random_fact()}

    # ── Unit Conversion ──────────────────────────────────────────────────────
    unit_match = re.search(
        r"convert\s+([\d.]+)\s+(\w+(?:\s+\w+)?)\s+to\s+(\w+(?:\s+\w+)?)", tl
    )
    if unit_match:
        try:
            val = float(unit_match.group(1))
            from_u = unit_match.group(2)
            to_u = unit_match.group(3)
            return {"text": convert_units(val, from_u, to_u)}
        except ValueError:
            pass

    # ── Currency Conversion ──────────────────────────────────────────────────
    currency_match = re.search(
        r"convert\s+([\d.]+)\s+([a-z]{3})\s+to\s+([a-z]{3})", tl
    )
    if currency_match:
        try:
            amt = float(currency_match.group(1))
            fc = currency_match.group(2)
            tc = currency_match.group(3)
            return {"text": convert_currency(amt, fc, tc)}
        except ValueError:
            pass

    # ── Browser URL actions ──────────────────────────────────────────────────
    if any(kw in tl for kw in ["search google", "google search", "google for"]):
        q = extract_query(text, ["search google for", "google search for", "google for", "search google"])
        return get_google_search_url(q)

    # ── Spotify ─────────────────────────────────────────────────────────────
    if "spotify" in tl:
        q = extract_query(text, ["play on spotify", "spotify search for", "spotify"])
        if q: return search_spotify(q)
        return search_spotify(text)

    if any(kw in tl for kw in ["youtube", "play "]):
        q = extract_query(text, ["search youtube for", "play on youtube", "youtube search for", "youtube", "play"])
        return get_youtube_search_url(q)

    if any(kw in tl for kw in ["gmail", "email", "open mail"]):
        return get_gmail_url()

    if any(kw in tl for kw in ["whatsapp"]):
        return get_whatsapp_url()

    if any(kw in tl for kw in ["stack overflow", "stackoverflow"]):
        q = extract_query(text, ["search stack overflow for", "stack overflow", "stackoverflow"])
        return get_stackoverflow_search_url(q)

    if any(kw in tl for kw in ["wolframalpha", "wolfram alpha", "calculate ", "solve "]):
        q = extract_query(text, ["wolframalpha", "wolfram alpha", "calculate", "solve"])
        return get_wolframalpha_url(q)

    if any(kw in tl for kw in ["image search", "search images", "find image"]):
        q = extract_query(text, ["image search for", "search images for", "find image of", "find images of"])
        return get_image_search_url(q)

    if any(kw in tl for kw in ["calculator", "open calculator"]):
        return get_calculator_url()


    # ── Dictionary ──────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["define ", "meaning of "]):
        q = extract_query(text, ["define", "meaning of"])
        if q: return {"text": get_definition(q)}

    # ── Quotes ──────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["quote", "inspire me"]):
        return {"text": get_random_quote()}

    # ── Geolocation ─────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["where am i", "my location"]):
        return {"text": get_ip_location()}

    # ── Maps ────────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["where is ", "map of "]):
        q = extract_query(text, ["where is", "map of"])
        if q: return search_map(q)

    # ── Movies ──────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["search movie", "find film", "movie info"]):
        q = extract_query(text, ["search movie", "find film", "movie info for", "movie info"])
        if q: return {"text": get_movie_info(q)}

    # ── Holidays ────────────────────────────────────────────────────────────
    if "holidays in" in tl or "when are the holidays" in tl:
        return {"text": get_holidays("US")}

    # ── NASA ────────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["show me nasa picture", "nasa picture of the day"]):
        return get_nasa_apod()

    # ── Spotify ─────────────────────────────────────────────────────────────
    if "spotify" in tl:
        q = extract_query(text, ["play on spotify", "spotify search for", "spotify"])
        if q: return search_spotify(q)
        return search_spotify(text)

    # ── Image Generation ────────────────────────────────────────────────────
    if any(kw in tl for kw in ["generate image", "create image"]):
        q = extract_query(text, ["generate image of", "create image of", "generate image", "create image"])
        if q: return generate_image(q)
    # No built-in command matched; fall through to AI
    return None
