"""Legacy Part C adapter file; use integrations.py for new code."""
from integrations import Backend, calendar_file_bytes, load_backend

__all__ = ["Backend", "calendar_file_bytes", "load_backend"]
