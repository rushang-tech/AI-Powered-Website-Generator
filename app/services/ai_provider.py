from __future__ import annotations

import json
import os
from typing import Protocol

from dotenv import load_dotenv

from app.services.taste_engine import clean_json_response

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - dependency may be unavailable in test env
    genai = None

load_dotenv()


class AIProvider(Protocol):
    def generate_text(self, prompt: str) -> str:
        ...

    def generate_json(self, prompt: str) -> dict[str, object]:
        ...


class NullAIProvider:
    def generate_text(self, prompt: str) -> str:
        raise RuntimeError("AI provider unavailable.")

    def generate_json(self, prompt: str) -> dict[str, object]:
        raise RuntimeError("AI provider unavailable.")


class GeminiAIProvider:
    def __init__(self, api_key: str, *, model_name: str = "gemini-flash-latest") -> None:
        if genai is None:
            raise RuntimeError("google.generativeai is unavailable.")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    def generate_text(self, prompt: str) -> str:
        response = self._model.generate_content(prompt)
        return str(getattr(response, "text", "")).strip()

    def generate_json(self, prompt: str) -> dict[str, object]:
        raw = self.generate_text(prompt)
        cleaned = clean_json_response(raw)
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("AI response did not decode to a JSON object.")
        return parsed


def get_default_provider() -> AIProvider | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        return GeminiAIProvider(api_key)
    except Exception:
        return None
