"""Thin Gemini wrapper: structured-output calls, with retries and model fallback.

Free-tier quota and "model overloaded" 503s are both per-model, so a single hard-coded
model makes the pipeline fail for reasons that have nothing to do with the research.
Each call walks a chain of models and reports which one actually answered.
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any

from google import genai
from google.genai import types

# Ordered most- to least-preferred. Overridable via GEMINI_MODELS (comma-separated).
DEFAULT_MODEL_CHAIN = (
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)

RETRYABLE = ("429", "RESOURCE_EXHAUSTED", "500", "502", "503", "UNAVAILABLE", "INTERNAL")


class GeminiError(RuntimeError):
    pass


def model_chain() -> list[str]:
    configured = os.environ.get("GEMINI_MODELS") or os.environ.get("GEMINI_MODEL")
    if configured:
        return [m.strip() for m in configured.split(",") if m.strip()]
    return list(DEFAULT_MODEL_CHAIN)


def make_client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set (copy .env.example to .env)")
    return genai.Client(api_key=key)


def generate_json(
    client: genai.Client,
    prompt: str,
    response_schema: dict[str, Any],
    models: list[str] | None = None,
    attempts_per_model: int = 3,
    temperature: float = 0.0,
) -> tuple[dict[str, Any], str, str]:
    """Return (parsed_json, raw_text, model_used).

    Retries a model on transient errors, then falls through to the next model.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=temperature,
    )

    chain = models or model_chain()
    last_error: Exception | None = None

    for model in chain:
        for attempt in range(attempts_per_model):
            try:
                resp = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                raw = resp.text or ""
                return json.loads(raw), raw, model
            except json.JSONDecodeError as exc:
                raise GeminiError(f"{model} returned non-JSON: {exc}") from exc
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if not any(code in message for code in RETRYABLE):
                    raise
                if attempt < attempts_per_model - 1:
                    sleep_for = min(45, 2 ** attempt * 6) + random.uniform(0, 2)
                    print(f"      (retry {model} {attempt + 1}/{attempts_per_model} "
                          f"in {sleep_for:.0f}s: {message[:60]})")
                    time.sleep(sleep_for)
                else:
                    print(f"      ({model} unavailable, falling back: {message[:60]})")

    raise GeminiError(f"all models exhausted ({', '.join(chain)}): {last_error}")
