"""Read local/deployment settings without logging or sharing credentials."""
import os
from pathlib import Path
import tomllib


def setting(name, default=""):
    value = os.getenv(name)
    if value:
        return value
    try:
        path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        value = config.get(name)
        return value if isinstance(value, str) and value else default
    except (OSError, ValueError):
        return default


def ai_configured():
    return bool(setting("GEMINI_API_KEY"))
