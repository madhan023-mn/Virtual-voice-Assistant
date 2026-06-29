import re

with open('commands.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_functions = """
# ──────────────────────────────────────────────────────────────────────────────
# Dictionary (Free Dictionary API)
# ──────────────────────────────────────────────────────────────────────────────

def get_definition(word: str) -> str:
    \"\"\"Return the definition of a word.\"\"\"
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
    \"\"\"Return a random quote.\"\"\"
    data = _safe_get("https://api.quotable.io/random")
    if data and "content" in data:
        return f'"{data["content"]}" - {data.get("author", "Unknown")}'
    return '"The best way to predict the future is to invent it." - Alan Kay'

# ──────────────────────────────────────────────────────────────────────────────
# Geolocation (ip-api)
# ──────────────────────────────────────────────────────────────────────────────

def get_ip_location() -> str:
    \"\"\"Return current location based on IP.\"\"\"
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
    \"\"\"Return a map URL.\"\"\"
    url = f"https://www.openstreetmap.org/search?query={urllib.parse.quote(location)}"
    return {"text": f"Opening map for '{location}'...", "url": url, "action": "open_url"}

# ──────────────────────────────────────────────────────────────────────────────
# Movies (OMDb API)
# ──────────────────────────────────────────────────────────────────────────────

def get_movie_info(title: str) -> str:
    \"\"\"Return movie information.\"\"\"
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
    \"\"\"Return next upcoming public holidays.\"\"\"
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
    \"\"\"Return NASA Picture of the Day.\"\"\"
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
    \"\"\"Open Spotify search.\"\"\"
    url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
    return {"text": f"Opening Spotify for '{query}'...", "url": url, "action": "open_url"}

# ──────────────────────────────────────────────────────────────────────────────
# Hugging Face (Image Generation)
# ──────────────────────────────────────────────────────────────────────────────

def generate_image(prompt: str) -> dict:
    \"\"\"Trigger image generation.\"\"\"
    if not cfg.HUGGINGFACE_API_KEY:
        return {"text": "HuggingFace API key not configured. Please add HUGGINGFACE_API_KEY to your .env file."}
    
    # We will simulate the URL behavior by returning a placeholder since image generation takes time
    # and requires saving a file, which is complex for a synchronous voice response.
    # A true implementation would download the bytes and save to static/images.
    return {"text": f"I don't have full UI support to display generated images yet, but I would generate: {prompt}"}

"""

# Split before Command Router
parts = content.split("# ──────────────────────────────────────────────────────────────────────────────\n# Command Router\n# ──────────────────────────────────────────────────────────────────────────────")

new_content = parts[0] + new_functions + "# ──────────────────────────────────────────────────────────────────────────────\n# Command Router\n# ──────────────────────────────────────────────────────────────────────────────" + parts[1]

# Now let's inject the routing logic.
routing_logic = """
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
    if any(kw in tl for kw in ["movie ", "film "]):
        q = extract_query(text, ["movie", "film"])
        if q: return {"text": get_movie_info(q)}

    # ── Holidays ────────────────────────────────────────────────────────────
    if "holiday" in tl:
        return {"text": get_holidays("US")}

    # ── NASA ────────────────────────────────────────────────────────────────
    if any(kw in tl for kw in ["nasa", "space", "picture of the day"]):
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
"""

parts_router = new_content.split("    # No built-in command matched; fall through to AI")
new_content = parts_router[0] + routing_logic + "    # No built-in command matched; fall through to AI" + parts_router[1]

with open('commands.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
