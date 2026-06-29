"""
config.py - Application Configuration
Loads environment variables and provides configuration settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    PORT = int(os.environ.get("PORT", 5000))

    # AI APIs
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

    # Weather
    OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
    DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "New York")

    # News
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

    # Currency
    EXCHANGE_RATE_API_KEY = os.environ.get("EXCHANGE_RATE_API_KEY", "")

    # New APIs
    HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")
    NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")

    # Wikipedia
    WIKIPEDIA_LANGUAGE = os.environ.get("WIKIPEDIA_LANGUAGE", "en")

    # Joke API (public, no key needed)
    JOKE_API_URL = "https://v2.jokeapi.dev/joke/Any"

    # Random Facts API (public, no key needed)
    FACTS_API_URL = "https://uselessfacts.jsph.pl/api/v2/facts/random"

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Configuration mapping
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Return the appropriate configuration object."""
    env = os.environ.get("FLASK_ENV", "production")
    return config_map.get(env, config_map["default"])()
