# src/jarvis/config.py
# ============================================
# Centralised configuration using pydantic-settings
# All values come from the .env file
# ============================================

from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Absolute path to the project root (three levels up from this file)
BASE_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """
    All JARVIS configuration in one place.
    Values are loaded from the .env file automatically.
    If a required value is missing, pydantic raises a clear error on startup.
    """

    # --- Required ---
    groq_api_key: str

    # --- Optional API keys ---
    brave_api_key: str = ""

    # --- Model settings ---
    jarvis_model: str = "llama-3.3-70b-versatile"
    jarvis_max_tokens: int = 1024

    # --- Behaviour settings ---
    jarvis_log_level: str = "INFO"
    jarvis_voice_enabled: bool = False
    jarvis_max_history: int = 20

    model_config = ConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        # Allow extra fields so adding new .env vars doesn't break things
        extra="ignore",
    )


# Single global instance — import this everywhere
# Usage: from jarvis.config import settings
settings = Settings()