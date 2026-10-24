from __future__ import annotations

from hashlib import sha256


def extract_event(image_bytes: bytes, mime_type: str) -> dict:
    """
    示例插件：真实OCR/LLM接入时替换这里。
    当前返回“标准层风格”dict，故意保留部分 None 让人工补全。
    """
    digest = sha256(image_bytes).hexdigest()[:8]
    return {
        "name": f"AI Draft Event {digest}",
        "venue": None,
        "start_dt": "2026-11-03 19:00",
        "end_dt": None,
        "reg_deadline_dt": None,
        "reg_method": {
            "type": "url",
            "value": None,
        },
    }
