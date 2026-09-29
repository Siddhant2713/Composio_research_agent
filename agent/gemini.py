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

# Transient overload: the same model is worth another try after a pause.
TRANSIENT = ("500", "502", "503", "UNAVAILABLE", "INTERNAL")
# Quota exhausted: retrying this model changes nothing, so move on immediately.
QUOTA = ("429", "RESOURCE_EXHAUSTED")

# How long to stop trying a model after it fails. Quota windows are long; overload is
# capacity and usually clears, so it gets a short rest and is then tried again.
QUOTA_COOLDOWN = 30 * 60
OVERLOAD_COOLDOWN = 10 * 60

# model -> unix time until which to skip it. Without this, a model that is overloaded at the
# start of a batch is retried three times per call for all 100 apps, which is roughly twenty
# seconds of sleeping per app spent on a model already known to be unavailable.
_cooldown: dict[str, float] = {}


def _rest(model: str, seconds: int, why: str) -> None:
    _cooldown[model] = time.time() + seconds
    print(f"      ({model} {why}; resting {seconds // 60}m)")


def _available(chain: list[str]) -> list[str]:
    now = time.time()
    return [m for m in chain if _cooldown.get(m, 0) <= now]


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
    quota_pause: int = 75,
) -> tuple[dict[str, Any], str, str]:
    """Return (parsed_json, raw_text, model_used).

    Retries a model on transient errors, then falls through to the next model.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=temperature,
        # This is a single-shot structured call with no tools, so the SDK's multi-turn
        # automatic function calling is not wanted. Disabling it silences the advisory
        # warning the SDK prints on every generate_content call.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    chain = models or model_chain()

    # Everything is resting: wait for the earliest model to come back rather than failing
    # the remaining apps in a burst.
    if not _available(chain):
        soonest = min(_cooldown[m] for m in chain)
        wait = max(0.0, min(soonest - time.time(), quota_pause))
        print(f"      (all {len(chain)} models resting — waiting {wait:.0f}s)")
        time.sleep(wait)
        for model in chain:                       # give them all one more chance
            _cooldown.pop(model, None)

    usable = _available(chain) or list(chain)
    last_error: Exception | None = None

    for model in usable:
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

                if any(code in message for code in QUOTA):
                    _rest(model, QUOTA_COOLDOWN, "out of quota")
                    break

                if not any(code in message for code in TRANSIENT):
                    raise

                if attempt < attempts_per_model - 1:
                    sleep_for = min(45, 2 ** attempt * 6) + random.uniform(0, 2)
                    print(f"      (retry {model} {attempt + 1}/{attempts_per_model} "
                          f"in {sleep_for:.0f}s: {message[:60]})")
                    time.sleep(sleep_for)
                else:
                    _rest(model, OVERLOAD_COOLDOWN, "overloaded")

    resting = sorted(m for m, until in _cooldown.items() if until > time.time())
    raise GeminiError(
        f"all models unavailable ({', '.join(usable)}); "
        f"resting: {resting or 'none'}: {last_error}"
    )
