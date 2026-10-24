from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Optional, Any


@dataclass
class Backend:
    name: str
    status: str
    function: Optional[Callable[..., Any]]


def load_backend(module_name: str, func_name: str) -> Backend:
    try:
        module = import_module(module_name)
        fn = getattr(module, func_name, None)
        if callable(fn):
            return Backend(name=f"{module_name}.{func_name}", status="connected", function=fn)
        return Backend(name=f"{module_name}.{func_name}", status="missing_function", function=None)
    except Exception:
        return Backend(name=f"{module_name}.{func_name}", status="not_available", function=None)


def calendar_file_bytes(payload: str | bytes) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    raise TypeError("calendar_export.generate_ics must return str or bytes")
